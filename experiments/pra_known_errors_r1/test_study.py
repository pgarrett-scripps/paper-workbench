import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import core
import manuscript_tools
import schemas
import study
import workflow


class InvestigationTests(unittest.TestCase):
    def test_calculation_is_bounded_and_cannot_access_host(self):
        self.assertEqual(manuscript_tools.calculate("mean([2, 4, 6])"), 4)
        self.assertTrue(manuscript_tools.calculate("(3 >= 3) and not (3 > 3)"))
        self.assertEqual(manuscript_tools.calculate("(0.8 - 0.7) / 0.7"), (0.8 - 0.7) / 0.7)
        for expression in ["__import__('os').environ", "open('/etc/passwd')", "(1).__class__", "[x for x in [1]]", "10 ** 1000", "[1] * 999999", "exp(9999)"]:
            with self.assertRaises((ValueError, OverflowError)):
                manuscript_tools.calculate(expression)

    def test_tool_receipt_corresponds_to_an_executed_calculation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manuscript.txt"
            path.write_text("[E0001]\nEvidence")
            server = manuscript_tools.ManuscriptServer(path)
            result = server.call("check_calculation", {"expression": "2 + 2"})
            self.assertEqual(result["result"], 4)
            self.assertIn(result["receipt"], core.receipts_in(Path(directory)))
            core.validate_evidence({"test_receipts": [result["receipt"]]}, {}, {result["receipt"]})
            with self.assertRaises(core.Blocked):
                core.validate_evidence({"test_receipts": ["invented"]}, {}, {result["receipt"]})
            for _ in range(2):
                server.call("read_manuscript", {})
            self.assertIn("notice", server.call("check_calculation", {"expression": "1 + 1"}))
            self.assertEqual(len(core.receipts_in(Path(directory))), 1)

    def test_final_preserves_all_findings_and_enforces_limits(self):
        cases = {str(i): {"text": "word " * 160} for i in range(6)}
        value = {"summary": "Summary", "strengths": "Strengths",
                 "dispositions": {key: {"status": "retain", "reason": "Distinct", "evidence_ids": ["E0001"], "duplicate_of": ""} for key in cases},
                 "ranking": list(cases), "selected_ids": list(cases)[:5]}
        replies = {key: {"position": "retain"} for key in cases}
        body = core.validate_final(value, cases, replies, {"E0001": {}})
        self.assertLessEqual(len(body.split()), 900)
        self.assertEqual(len(cases), 6)
        bad = copy.deepcopy(value)
        bad["ranking"].pop()
        with self.assertRaises(core.Blocked):
            core.validate_final(bad, cases, replies, {})
        bad = copy.deepcopy(value)
        bad["selected_ids"] = list(cases)
        with self.assertRaises(core.Blocked):
            core.validate_final(bad, cases, replies, {})
        replies["0"]["position"] = "withdraw"
        with self.assertRaises(core.Blocked):
            core.validate_final(value, cases, replies, {})

    def test_presentation_normalization_preserves_content_and_raw_output(self):
        value = {"selected_ids": ["b", "a"], "ranking": ["a", "b"],
                 "summary": "Summary " * 53, "strengths": "Strength " * 30}
        raw = copy.deepcopy(value)
        result = core.normalize_final(value)
        self.assertEqual(value, raw)
        self.assertEqual(result["selected_ids"], ["a", "b"])
        self.assertEqual(set(result["selected_ids"]), set(value["selected_ids"]))
        self.assertEqual(len((result["summary"] + " " + result["strengths"]).split()), 80)
        self.assertEqual(result["ranking"], value["ranking"])
        value["selected_ids"] = ["missing"]
        with self.assertRaises(core.Blocked):
            core.normalize_final(value)

    def test_no_inference_after_budget_stop(self):
        protocol = core.read(core.HERE / "protocol.json")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(core, "ROOT", root), patch.object(core, "usage", return_value=[{"observed_tokens": protocol["max_total_tokens"]}]), patch.object(core.runtime, "model_call") as model:
                with self.assertRaises(core.Blocked):
                    core.call(protocol, root / "work/node", "prompt", schemas.obj({}))
                model.assert_not_called()

    def test_paired_screen_rejects_original_false_alarm(self):
        protocol = core.read(core.HERE / "protocol.json")
        protocol["paper_ids"] = ["p"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            labels = {variant: {"paper_id": "p", "variant": variant} for variant in ["original", "altered"]}
            core.write(root / "evaluation/labels.json", labels)
            for variant in labels:
                out = root / "work" / variant
                core.write(out / "anonymous_candidates.json", {"Ct": {"text": "Team concern"}, "Cs": {"text": "Single concern"}})
                core.write(out / "stage_ids.json", {"investigation_team_top": ["Ct"], "sequential_single_top": ["Cs"]})
                judgments = {cid: {"identifies_target_defect": cid == "Ct" and variant == "altered", "support": "supported", "major": True} for cid in ["Ct", "Cs"]}
                for judge in "AB":
                    core.write(out / ("judge_" + judge) / "judgment.json", {"judgments": judgments})
            with patch.object(core, "ROOT", root):
                self.assertEqual(study.summarize(protocol)["signal"], "promising_development_gain_pending_audit")
                for judge in "AB":
                    path = root / "work/original" / ("judge_" + judge) / "judgment.json"
                    value = core.read(path)
                    value["judgments"]["Ct"]["identifies_target_defect"] = True
                    core.write(path, value)
                self.assertEqual(study.summarize(protocol)["signal"], "target_not_met")

    def test_full_pipeline_parity_blinding_and_real_reply_order(self):
        import jsonschema
        protocol = core.read(core.HERE / "protocol.json")
        protocol["paper_ids"] = ["test"]
        
        source = {"E0001": {"page": 1, "text": "A manuscript with one testable claim."}}
        calls = []
        final_case = {"text": "The comparison lacks a matched control. Add one to isolate the claimed effect.",
                      "evidence_ids": ["E0001"], "counterevidence_ids": [], "kind": "missing_evidence",
                      "severity": "major", "test_receipts": []}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inp = root / "inputs/test"
            core.write(inp / "source_chunks.json", source)
            label = {"paper_id": "test", "variant": "altered", "annotation": "REFERENCE_ONLY_SECRET"}
            core.write(root / "evaluation/labels.json", {"test": label})
            core.write(root / "manifest.json", {"input_ids": ["test"]})

            def fake(protocol_arg, node, text, schema, source_arg=None, arm=None, pdf=None):
                node.mkdir(parents=True, exist_ok=True)
                jsonschema.Draft202012Validator.check_schema(schema)
                calls.append({"node": str(node.relative_to(root)), "prompt": text, "schema": schema, "tools": source_arg is not None})
                self.assertIn("A manuscript with one testable claim.", text)
                if source_arg is not None:
                    self.assertEqual(pdf, inp / "manuscript.pdf")
                if not node.name.startswith("judge_"):
                    self.assertNotIn("REFERENCE_ONLY_SECRET", text)
                if node.name == "map":
                    value = {"claims": [], "method_reconstruction": "One operation", "work_orders": {key: "Investigate " + key for key in "ABC"}}
                elif node.name.startswith("investigate_"):
                    value = {"investigation_log": "LOG_" + node.name[-1], "findings": [final_case] if node.name.endswith("A") else []}
                elif node.name == "defense":
                    value = {"answers": {"A1": {"position": "conceded", "response": "DEFENDER_ACTUAL_RESPONSE", "evidence_ids": ["E0001"], "test_receipts": []}}}
                elif node.name == "reply":
                    self.assertIn("DEFENDER_ACTUAL_RESPONSE", text)
                    value = {"replies": {"A1": {"position": "retain", "response": "The answer concedes the missing control.", "final_concern": final_case}}}
                elif node.name == "final":
                    self.assertIn("DEFENDER_ACTUAL_RESPONSE", text)
                    self.assertIn("The answer concedes", text)
                    value = {"summary": "Summary", "strengths": "Strengths", "dispositions": {"A1": {"status": "retain", "reason": "Unanswered issue", "evidence_ids": ["E0001"], "duplicate_of": ""}}, "ranking": ["A1"], "selected_ids": ["A1"]}
                else:
                    self.assertIn("REFERENCE_ONLY_SECRET", text)
                    self.assertNotIn("investigation_team", text)
                    self.assertNotIn("sequential_single", text)
                    candidates = list(schema["properties"]["judgments"]["properties"])
                    value = {"judgments": {key: {"identifies_target_defect": True,
                             "target_match_reason": "Matches", "support": "supported", "major": True,
                             "evidence_ids": ["E0001"], "support_reason": "Evidence"} for key in candidates},
                             "annotation_caveat": "No caveat"}
                jsonschema.validate(value, schema)
                return value

            with patch.object(core, "ROOT", root), patch.object(core, "call", side_effect=fake):
                workflow.generate(protocol, "test")
                study.evaluate(protocol, "test", label)
                result = study.summarize(protocol)
            self.assertEqual(len(calls), 15)
            self.assertEqual(sum(row["tools"] for row in calls), 12)
            self.assertEqual(result["missing"], [])
            self.assertEqual(result["signal"], "target_not_met")
            for row in calls:
                if row["node"].endswith("investigate_B"):
                    if "sequential_single" in row["node"]:
                        self.assertIn("LOG_A", row["prompt"])
                    else:
                        self.assertNotIn("LOG_A", row["prompt"])
            # Equal text gets one stable anonymous candidate across both arms.
            self.assertEqual(len(core.read(root / "work/test/anonymous_candidates.json")), 1)


if __name__ == "__main__":
    unittest.main()
