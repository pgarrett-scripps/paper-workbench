"""Offline checks for billing guards, provenance, extraction, and scoring."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import common
import study
from prompts import PLAIN_SCHEMA


class StudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.protocol = common.read_json(common.HERE / "protocol.claude.json")

    def tearDown(self):
        self.temp.cleanup()

    def test_api_overrides_removed_and_fast_mode_disabled(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "not-a-real-key",
                                   "ANTHROPIC_BASE_URL": "http://invalid",
                                   "PEERREVIEW_PROVIDER": "anthropic",
                                   "CLAUDECODE": "1",
                                   "CLAUDE_CODE_USE_BEDROCK": "1"}):
            env = common.clean_env()
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertNotIn("ANTHROPIC_BASE_URL", env)
        self.assertNotIn("PEERREVIEW_PROVIDER", env)
        self.assertNotIn("CLAUDE_CODE_USE_BEDROCK", env)
        self.assertNotIn("CLAUDECODE", env)
        self.assertEqual(env["CLAUDE_CODE_DISABLE_FAST_MODE"], "1")

    def test_login_required_without_model_call(self):
        with patch.object(common, "auth_status", return_value={"loggedIn": False}):
            with self.assertRaisesRegex(common.StudyBlocked, "cannot access"):
                common.require_subscription(self.root)

    def test_api_login_rejected(self):
        with patch.object(common, "auth_status", return_value={"loggedIn": True, "authMethod": "api_key"}):
            with self.assertRaisesRegex(common.StudyBlocked, "Subscription authentication"):
                common.require_subscription(self.root)

    def test_billing_confirmation_required(self):
        with patch.object(common, "auth_status", return_value={"loggedIn": True, "authMethod": "claude.ai"}):
            with self.assertRaisesRegex(common.StudyBlocked, "extra usage"):
                common.require_subscription(self.root)
            common.write_json(self.root / "billing_confirmation.json", {"extra_usage_disabled": True})
            self.assertTrue(common.require_subscription(self.root)["loggedIn"])

    def test_fable_and_missing_model_rejected(self):
        for envelope in ({}, {"modelUsage": {"claude-fable-5-1": {}}}):
            with self.assertRaises(common.StudyBlocked):
                common.verify_model(envelope)
        self.assertEqual(common.verify_model({"modelUsage": {"claude-opus-5": {}}}), ["claude-opus-5"])

    def test_protocol_cannot_change_provider_or_model(self):
        for key, value in [("model", "fable"), ("provider", "anthropic"), ("live_retrieval", True)]:
            with self.assertRaises(common.StudyBlocked):
                common.validate_protocol({**self.protocol, key: value})

    def envelope(self, model="claude-opus-5"):
        return {"structured_output": {"content": "Example response"},
                "modelUsage": {model: {}},
                "usage": {"input_tokens": 10, "output_tokens": 20,
                          "cache_read_input_tokens": 30, "cache_creation_input_tokens": 40}}

    def test_call_is_pinned_recorded_and_resumable(self):
        result = subprocess.CompletedProcess([], 0, json.dumps(self.envelope()), "")
        with patch.object(common.subprocess, "run", return_value=result) as run:
            first = common.model_call(self.protocol, self.root, "test", PLAIN_SCHEMA)
            second = common.model_call(self.protocol, self.root, "test", PLAIN_SCHEMA)
        self.assertEqual(first, second)
        self.assertEqual(run.call_count, 1)
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--model") + 1], "claude-opus-5")
        self.assertNotIn("--fallback-model", command)
        self.assertIn("--safe-mode", command)
        self.assertIn("--restricted", command)
        self.assertEqual(command[command.index("--tools") + 1], "")
        usage = common.jsonl(self.root / "usage.jsonl")
        self.assertEqual(len(usage), 1)
        self.assertEqual(usage[0]["observed_tokens"], 100)

    def test_failed_call_cannot_silently_retry(self):
        result = subprocess.CompletedProcess([], 0, json.dumps(self.envelope("claude-fable-5-1")), "")
        with patch.object(common.subprocess, "run", return_value=result) as run:
            for _ in range(2):
                with self.assertRaises(common.StudyBlocked):
                    common.model_call(self.protocol, self.root, "test", PLAIN_SCHEMA)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(len(common.jsonl(self.root / "usage.jsonl")), 1)

    def test_timeout_preserved(self):
        with patch.object(common.subprocess, "run", side_effect=subprocess.TimeoutExpired("claude", 1)):
            with self.assertRaises(common.StudyBlocked):
                common.model_call(self.protocol, self.root, "test", PLAIN_SCHEMA)
        record = common.jsonl(self.root / "usage.jsonl")[0]
        self.assertFalse(record["ok"])
        self.assertIn("unknown", record["error"])

    def test_observed_budget_stop(self):
        common.append_json(self.root / "usage.jsonl", {"observed_tokens": self.protocol["observed_token_stop"]})
        with patch.object(common.subprocess, "run") as run:
            with self.assertRaisesRegex(common.StudyBlocked, "token stop"):
                common.model_call(self.protocol, self.root, "test", PLAIN_SCHEMA)
            run.assert_not_called()

    def test_source_quote_cannot_be_invented(self):
        value = {"concerns": [{"id": "C1", "claim": "Missing control", "source_quote": "No control was reported."}]}
        common.validate_concerns(value, "No control\nwas reported.", maximum=5)
        with self.assertRaises(common.StudyBlocked):
            common.validate_concerns(value, "We used a control.", maximum=5)
        with self.assertRaises(common.StudyBlocked):
            common.validate_concerns({"concerns": value["concerns"] * 2}, "No control was reported.")

    def test_judgment_requires_complete_ids_and_real_quotes(self):
        refs, candidates = [{"id": "R1"}], [{"id": "C1"}]
        judgment = {
            "matches": [{"reference_id": "R1", "candidate_ids": ["C1"], "matched": True, "reason": "same issue"}],
            "support": [{"candidate_id": "C1", "label": "supported", "major": True,
                         "evidence_quote": "No control was included.", "reason": "explicit"}],
        }
        study.validate_judgment(judgment, refs, candidates, "No control was included.")
        with self.assertRaises(common.StudyBlocked):
            study.validate_judgment(judgment, refs, candidates, "A control was included.")
        with self.assertRaises(common.StudyBlocked):
            study.validate_judgment({**judgment, "matches": []}, refs, candidates, "No control was included.")

if __name__ == "__main__":
    unittest.main()
