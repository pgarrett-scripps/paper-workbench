"""Check the shared-panel intervention against the installed PRA runtime."""

import copy
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import common
import worker


@unittest.skipUnless(importlib.util.find_spec("peerreviewagents"), "Run with the PRA Python environment")
class RuntimeTests(unittest.TestCase):
    def setUp(self):
        from peerreviewagents.agents.editor import editor_in_chief
        self.editor = editor_in_chief
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.protocol = common.read_json(common.HERE / "protocol.claude.json")
        self.manifest = {"papers": [{"paper_id": "test", "version_verified": False}]}
        self.panel = {
            "reports": [{"reviewer": "scientific_validity", "body": "A panel concern"}],
            "audits": [{"auditor": "methods_completeness", "body": "An audit concern"}],
            "manuscript_md": "The study reports results without a control condition.",
            "manuscript_title": "Test paper", "config": {}, "errors": [],
            "debate": [], "debate_synthesis": "", "panel_complete": True,
        }
        self.path = self.root / "generation/test/pra_full/panel_state.json"
        common.write_json(self.path, self.panel)

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, node):
        raw = "The manuscript reports a treatment effect without a control condition. Please establish whether the observed difference can be separated from baseline variation."
        with patch.object(worker, "verify_study", return_value=(self.protocol, self.manifest)), \
             patch.object(worker, "require_subscription"), \
             patch.object(self.editor, "node", side_effect=node), \
             patch.object(worker, "model_call", return_value={"concerns": [{"id": "C1", "claim": "Missing control", "source_quote": raw}]}), \
             patch.object(sys, "argv", ["worker.py", str(self.root), "test", "pra_no_debate"]):
            worker.main()

    def test_no_debate_receives_identical_panel_and_no_downstream_information(self):
        captured = []

        def node(state):
            captured.append(copy.deepcopy(state))
            return {"decision_letter": "The manuscript reports a treatment effect without a control condition. Please establish whether the observed difference can be separated from baseline variation."}

        self.invoke(node)
        self.assertEqual(captured[0]["reports"], self.panel["reports"])
        self.assertEqual(captured[0]["audits"], self.panel["audits"])
        self.assertEqual(captured[0]["debate"], [])
        self.assertEqual(captured[0]["debate_synthesis"], "")
        self.assertFalse(captured[0]["config"]["enable_debate"])
        self.assertEqual(captured[0]["config"]["reasoning_model"], "claude-opus-5")
        result = common.read_json(self.root / "generation/test/pra_no_debate/result.json")
        self.assertTrue(result["ok"])
        shared = common.read_json(self.root / "generation/test/pra_no_debate/shared_panel.json")
        self.assertEqual(shared["sha256"], common.digest(self.path.read_bytes()))

    def test_downstream_contamination_rejected(self):
        self.panel["decision_letter"] = "A decision that must never reach the no-debate condition"
        common.write_json(self.path, self.panel)
        with self.assertRaisesRegex(common.StudyBlocked, "downstream"):
            self.invoke(lambda state: self.fail("Editor must not run on a contaminated panel"))


if __name__ == "__main__":
    unittest.main()
