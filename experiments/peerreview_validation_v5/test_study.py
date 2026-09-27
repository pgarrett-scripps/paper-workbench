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

    def test_pdf_line_hyphenation_only(self):
        self.assertEqual(common.quote_match_mode("The final performance", "The fi-\nnal performance"), "pdf_line_wrapping")
        self.assertEqual(common.quote_match_mode("The final performance", "The final performance"), "whitespace")
        self.assertFalse(common.quote_present("The final accuracy", "The fi-\nnal performance"))
        self.assertFalse(common.quote_present("A wellknown result", "A well-known result"))
        self.assertFalse(common.quote_present("A control group", "A treatment group"))
        self.assertEqual(common.quote_match_mode("out-of-distribution", "out-\nof-distribution"), "pdf_line_wrapping")
        self.assertEqual(common.quote_match_mode("LoR-VP and ILM-VP", "LoR-\nVP and ILM-\nVP"), "pdf_line_wrapping")
        self.assertTrue(common.quote_present("parameter-efficient visual design", "parameter-\nefficient vi-\nsual design"))
        self.assertFalse(common.quote_present("out-of-distribution", "out of distribution"))
        self.assertFalse(common.quote_present("parameter-efficient visual design", "parameter-\nefficient causal design"))

    def test_pdf_header_requires_page_number_and_exact_known_header(self):
        quote = "This result holds across all models."
        source = "This result holds\n\n  17\nPublished as a conference paper at ICLR 2025\n\nacross all models."
        self.assertEqual(common.quote_match_mode(quote, source), "pdf_page_header")
        self.assertFalse(common.quote_present(quote, source.replace("Published as a conference paper at ICLR 2025", "This result needs independent verification")))

    def test_baseline_raw_length_does_not_override_common_packet_limit(self):
        raw = "word " * 902
        packet = {"concerns": [{"id": "C1", "claim": "Example", "source_quote": "word word"}]}
        item = {"paper_id": "test", "manuscript": "input.txt", "version_verified": False}
        (self.root / "input.txt").write_text("A manuscript.")
        (self.root / "generation/test/one_shot").mkdir(parents=True)
        with patch.object(study, "model_call", side_effect=[{"content": raw}, packet]):
            study.baseline(self.root, item, "one_shot", self.protocol)
        result = common.read_json(self.root / "generation/test/one_shot/result.json")
        self.assertEqual(result["raw_review_word_count"], 902)
        self.assertEqual(result["scored_quote_word_count"], 2)
        self.assertTrue(result["ok"])
        oversized = {"concerns": [{"id": "C1", "claim": "Example", "source_quote": raw}]}
        with patch.object(study, "model_call", side_effect=[{"content": raw}, oversized]):
            with self.assertRaisesRegex(common.StudyBlocked, "common word allowance"):
                study.baseline(self.root, item, "one_shot", self.protocol)

    def test_summary_withholds_support_statistics_for_unmatched_evidence(self):
        refs, candidates = [{"id": "R1"}], [{"id": "C1"}]
        entry = {"paper_id": "test", "anonymous_id": "review_1", "condition": "one_shot"}
        common.write_json(self.root / "evaluation/condition_key.json", [entry])
        for judge, quote in (("A", "No control was included."), ("B", "An invented sentence.")):
            judgment = {"matches": [{"reference_id": "R1", "candidate_ids": ["C1"], "matched": True, "reason": "same issue"}],
                        "support": [{"candidate_id": "C1", "label": "supported", "major": True,
                                     "evidence_quote": quote, "reason": "test"}]}
            study.validate_judgment(judgment, refs, candidates, "No control was included.")
            common.write_json(self.root / f"evaluation/test/review_1/{judge}/judgment.json", judgment)
        with patch.object(study, "verify_study", return_value=(self.protocol, {"papers": []})), patch("builtins.print"):
            study.summarize(self.root)
        metric = common.read_json(self.root / "report.json")["paper_metrics"][0]
        self.assertFalse(metric["support_statistics_complete"])
        self.assertIsNone(metric["n_supported_both_evaluators"])
        self.assertIsNone(metric["n_false_major_both_evaluators"])
        self.assertEqual(metric["n_invalid_evidence_B"], 1)
        self.assertEqual(metric["coverage_agreement"], 1.0)

    def test_judgment_requires_complete_ids_and_real_quotes(self):
        refs, candidates = [{"id": "R1"}], [{"id": "C1"}]
        judgment = {
            "matches": [{"reference_id": "R1", "candidate_ids": ["C1"], "matched": True, "reason": "same issue"}],
            "support": [{"candidate_id": "C1", "label": "supported", "major": True,
                         "evidence_quote": "No control was included.", "reason": "explicit"}],
        }
        study.validate_judgment(judgment, refs, candidates, "No control was included.")
        study.validate_judgment(judgment, refs, candidates, "A control was included.")
        self.assertFalse(judgment["support"][0]["evidence_valid"])
        self.assertEqual(judgment["support"][0]["label"], "supported")
        self.assertEqual(judgment["support"][0]["validation_status"], "unmatched_quote_pending_audit")
        with self.assertRaises(common.StudyBlocked):
            study.validate_judgment({**judgment, "matches": []}, refs, candidates, "No control was included.")

if __name__ == "__main__":
    unittest.main()
