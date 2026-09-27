"""Codex subscription and manuscript-only tool checks."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import common
from manuscript_tools import tool_result
from prompts import PLAIN_SCHEMA


class CodexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.protocol = common.read_json(common.HERE / "protocol.json")

    def tearDown(self):
        self.temp.cleanup()

    def test_api_credentials_removed(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "example", "CODEX_API_KEY": "example"}):
            env = common.clean_env()
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("CODEX_API_KEY", env)

    def test_chatgpt_and_credit_check_required(self):
        common.write_json(self.root / "protocol.json", self.protocol)
        with patch.object(common, "auth_status", return_value={"loggedIn": True, "authMethod": "chatgpt"}):
            with self.assertRaisesRegex(common.StudyBlocked, "credit"):
                common.require_subscription(self.root)
            common.write_json(self.root / "billing_confirmation.json", {"no_paid_credits_verified": True})
            self.assertTrue(common.require_subscription(self.root)["loggedIn"])

    def test_codex_events_cache_and_tool_isolation(self):
        def invoke(command, **kwargs):
            common.write_json(command[command.index("--output-last-message") + 1], {"content": "Example"})
            events = [{"type": "item.completed", "item": {"type": "mcp_tool_call", "tool": "read_manuscript", "status": "completed"}},
                      {"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 20}}]
            return subprocess.CompletedProcess(command, 0, "\n".join(json.dumps(e) for e in events), "")
        with patch.object(common.subprocess, "run", side_effect=invoke) as run:
            common.model_call(self.protocol, self.root, "test", PLAIN_SCHEMA, tools=True)
            common.model_call(self.protocol, self.root, "test", PLAIN_SCHEMA, tools=True)
        self.assertEqual(run.call_count, 1)
        command = run.call_args.args[0]
        self.assertIn('forced_login_method="chatgpt"', command)
        self.assertIn("features.shell_tool=false", command)
        self.assertIn("features.plugins=false", command)
        self.assertIn("mcp_servers.manuscript.required=true", command)
        record = common.jsonl(self.root / "usage.jsonl")[0]
        self.assertEqual(record["observed_tokens"], 120)
        self.assertEqual(record["models_observed"], [])
        self.assertEqual(record["model_requested"], "gpt-5.6-sol")

    def test_failed_codex_turn_is_preserved(self):
        response = subprocess.CompletedProcess([], 1, json.dumps({"type": "turn.failed", "error": "quota"}), "")
        with patch.object(common.subprocess, "run", return_value=response) as run:
            for _ in range(2):
                with self.assertRaises(common.StudyBlocked):
                    common.model_call(self.protocol, self.root, "test", PLAIN_SCHEMA)
        self.assertEqual(run.call_count, 1)

    def test_manuscript_tools_expose_only_supplied_lines(self):
        lines = ["First sentence", "Control experiment", "Last sentence"]
        self.assertIn("2: Control experiment", tool_result(lines, "read_manuscript", {"start_line": 2, "end_line": 2})["content"][0]["text"])
        self.assertNotIn("First sentence", tool_result(lines, "search_manuscript", {"query": "CONTROL"})["content"][0]["text"])
        with self.assertRaises(ValueError):
            tool_result(lines, "read_file", {"path": "/etc/passwd"})


if __name__ == "__main__":
    unittest.main()
