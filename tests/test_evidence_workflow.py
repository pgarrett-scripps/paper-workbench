"""Offline integrity checks for the staged evidence workflow runner."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

WORKFLOW = Path(__file__).resolve().parents[1] / "experiments" / "pra_evidence_workflow"
sys.path.insert(0, str(WORKFLOW))

import evaluation
import run as workflow
from paper_workspace import model_runtime
from paper_workspace.storage import digest, write


class EvidenceWorkflowIntegrity(unittest.TestCase):
    def test_repeated_eager_page_is_attached_once_without_erasing_operation_receipts(self):
        prepared={'images':[{'path':'a.png','sha256':'same','receipt_id':'one'},
                            {'path':'b.png','sha256':'same','receipt_id':'two'}]}
        self.assertEqual(len(workflow.attached_images(prepared)),1)
        self.assertEqual(len(prepared['images']),2)

    def test_development_gate_requires_gain_on_each_paper_without_extra_major_allegations(self):
        papers=[{'id':'paper-1'},{'id':'paper-2'}]
        metrics=[{'paper':paper['id'],'condition':condition,
                  'direct_assessable_either':score,'unsupported_major':0}
                 for paper in papers for condition,score in [('ordinary',1),('debate',3)]]
        self.assertTrue(workflow.development_gate(metrics,papers)['automatic_criterion_met'])
        metrics[-1]['direct_assessable_either']=2
        self.assertFalse(workflow.development_gate(metrics,papers)['automatic_criterion_met'])
        metrics[-1]['direct_assessable_either']=3
        metrics[-1]['unsupported_major']=1
        self.assertFalse(workflow.development_gate(metrics,papers)['automatic_criterion_met'])

    def setUp(self):
        self.paper = {
            "id": "paper-test",
            "source_sha256": "source-hash",
            "blocks": [
                {"id": "b1", "text": "The experiment used a matched control."},
                {"id": "b2", "text": "The outcome was measured after 24 hours."},
            ],
        }
        self.anonymous = {
            label: [{"finding_id": label + "1", "kind": "question"}]
            for label in ("A", "B", "C")
        }
        self.concerns = [{"id": "h1", "quote": "human source"}]
        self.images = [{"id": "image-1", "label": "Original PDF page 2", "sha256": "image-hash"}]

    def rating(self, label, assessment="justified_concern", use_image=False):
        text_reference = {
            "block_id": "b1",
            "quote": "matched control",
            "image_id": "",
            "visual_observation": "",
        }
        image_reference = {
            "block_id": "",
            "quote": "",
            "image_id": "image-1",
            "visual_observation": "The plotted groups are visually distinct.",
        }
        evidence = [image_reference if use_image else text_reference]
        counterevidence = []
        if assessment == "unsupported_allegation":
            counterevidence = evidence
            evidence = []
        if assessment == "unverifiable":
            evidence = []
            counterevidence = []
        return {
            "finding_id": label + "1",
            "assessment": assessment,
            "specificity": "meaningful" if assessment.startswith("justified_") else "limited",
            "target": "Matched control",
            "scientific_consequence": "The comparison determines whether the effect is attributable to treatment.",
            "requested_resolution": "Report the comparison explicitly.",
            "materiality": "major",
            "evidence": evidence,
            "counterevidence": counterevidence,
            "decisive_evidence_accessible": assessment != "unverifiable",
            "reason": "The source establishes the relevant comparison.",
            "edit_fidelity": "not_an_edit",
        }

    def condition(self, label, **rating_options):
        return {
            "label": label,
            "ratings": [self.rating(label, **rating_options)],
            "matches": [{
                "human_concern_id": "h1",
                "finding_ids": [label + "1"],
                "match": "direct",
                "reason": "The same concrete comparison is addressed.",
            }],
        }

    def valid_evaluation(self):
        return {
            "conditions": [
                self.condition("A"),
                self.condition("B", assessment="unsupported_allegation", use_image=True),
                self.condition("C", assessment="unverifiable"),
            ],
            "limitations": ["Offline validation fixture."],
        }

    def test_evaluation_accepts_complete_three_condition_accounting(self):
        value = self.valid_evaluation()
        evaluation.validate(value, self.anonymous, self.concerns, self.paper, self.images)

    def test_evaluation_rejects_missing_labels_findings_and_human_concerns(self):
        value = self.valid_evaluation()
        value["conditions"] = value["conditions"][:2]
        with self.assertRaisesRegex(ValueError, "three anonymous labels"):
            evaluation.validate(value, self.anonymous, self.concerns, self.paper, self.images)

        value = self.valid_evaluation()
        value["conditions"][0]["ratings"] = []
        with self.assertRaisesRegex(ValueError, "finding assessment"):
            evaluation.validate(value, self.anonymous, self.concerns, self.paper, self.images)

        value = self.valid_evaluation()
        value["conditions"][0]["matches"] = []
        with self.assertRaisesRegex(ValueError, "human-concern assessment"):
            evaluation.validate(value, self.anonymous, self.concerns, self.paper, self.images)

    def test_evaluation_rejects_forged_text_and_image_evidence(self):
        value = self.valid_evaluation()
        value["conditions"][0]["ratings"][0]["evidence"][0]["quote"] = "not in source"
        with self.assertRaisesRegex(ValueError, "Invalid source evidence"):
            evaluation.validate(value, self.anonymous, self.concerns, self.paper, self.images)

        value = self.valid_evaluation()
        ref = value["conditions"][1]["ratings"][0]["counterevidence"][0]
        ref["image_id"] = "image-missing"
        with self.assertRaisesRegex(ValueError, "Invalid source evidence"):
            evaluation.validate(value, self.anonymous, self.concerns, self.paper, self.images)

    def test_evaluation_requires_support_for_justified_and_unsupported_labels(self):
        value = self.valid_evaluation()
        value["conditions"][0]["ratings"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "lacks accessible supporting evidence"):
            evaluation.validate(value, self.anonymous, self.concerns, self.paper, self.images)

        value = self.valid_evaluation()
        value["conditions"][1]["ratings"][0]["counterevidence"] = []
        with self.assertRaisesRegex(ValueError, "lacks accessible counterevidence"):
            evaluation.validate(value, self.anonymous, self.concerns, self.paper, self.images)

    def test_evaluation_requires_unverifiable_evidence_to_be_inaccessible(self):
        value = self.valid_evaluation()
        value["conditions"][2]["ratings"][0]["decisive_evidence_accessible"] = True
        with self.assertRaisesRegex(ValueError, "Unverifiable judgment claims decisive evidence is accessible"):
            evaluation.validate(value, self.anonymous, self.concerns, self.paper, self.images)

    def test_evaluation_rejects_cross_condition_and_repeated_match_ids(self):
        value = self.valid_evaluation()
        value["conditions"][0]["matches"][0]["finding_ids"] = ["B1"]
        with self.assertRaisesRegex(ValueError, "Unknown or repeated"):
            evaluation.validate(value, self.anonymous, self.concerns, self.paper, self.images)

        value = self.valid_evaluation()
        value["conditions"][0]["matches"][0]["finding_ids"] = ["A1", "A1"]
        with self.assertRaisesRegex(ValueError, "Unknown or repeated"):
            evaluation.validate(value, self.anonymous, self.concerns, self.paper, self.images)

    def workspace(self, root):
        workspace = root / "workspace"
        workspace.mkdir()
        paper = {
            "id": "paper-test",
            "source_sha256": "source",
            "blocks": [
                {"id": "b1", "text": "First exact quote.", "sha256": digest("First exact quote.")},
                {"id": "b2", "text": "Second exact quote.", "sha256": digest("Second exact quote.")},
            ],
        }
        write(workspace / "paper.json", paper)
        write(workspace / "manifest.json", {
            "files": {"paper.json": digest((workspace / "paper.json").read_bytes())}
        })
        return workspace, paper

    def finding(self, block_id, quote, title):
        return {
            "title": title,
            "block_id": block_id,
            "quote": quote,
            "kind": "question",
            "severity": "major",
            "comment": "Clarify this evidence.",
            "replacement": "",
            "evidence_blocks": [block_id],
            "counterevidence": "",
            "source_urls": [],
        }

    def test_selected_review_uses_unique_one_based_indices_in_requested_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace, paper = self.workspace(root)
            response = {
                "summary": "Candidates",
                "findings": [
                    self.finding("b1", "First exact quote.", "First"),
                    self.finding("b2", "Second exact quote.", "Second"),
                ],
                "limitations": [],
                "investigation_summary": "Checked both.",
                "discarded_hypotheses": [],
                "selected_finding_numbers": [2, 1],
                "task_results": [],
            }
            candidates, selected = workflow.selected_review(paper, workspace, response, "evidence-test")
            self.assertEqual([row["title"] for row in candidates["findings"]], ["First", "Second"])
            self.assertEqual([row["title"] for row in selected["findings"]], ["Second", "First"])

            duplicate = {**response, "selected_finding_numbers": [1, 1]}
            with self.assertRaisesRegex(ValueError, "Invalid selected"):
                workflow.selected_review(paper, workspace, duplicate, "duplicate-test")
            out_of_range = {**response, "selected_finding_numbers": [3]}
            with self.assertRaisesRegex(ValueError, "Invalid selected"):
                workflow.selected_review(paper, workspace, out_of_range, "range-test")

    def test_validated_response_replaces_raw_task_results_with_fail_closed_results(self):
        raw = {
            "summary": "Candidate review",
            "findings": [],
            "selected_finding_numbers": [],
            "task_results": [{"id": "t1", "status": "completed"}],
        }
        validation = {
            "task_results": [{"id": "t1", "status": "unresolved"}],
            "task_result_validation": [{"id": "t1", "valid": False}],
            "unexpected_task_ids": [],
            "validation_limitation": "Invalid task claims were downgraded.",
        }
        result = workflow.validated_response(raw, validation)
        self.assertEqual(result["task_results"], validation["task_results"])
        self.assertEqual(result["task_validation"], validation["task_result_validation"])
        self.assertNotIn("findings", result["task_validation"][0])

    def test_support_counts_excludes_unsupported_direct_overlap(self):
        row = {
            "ratings": [
                {"finding_id": "A1", "assessment": "unsupported_allegation"},
                {"finding_id": "A2", "assessment": "justified_clarification"},
            ],
            "matches": [
                {"human_concern_id": "h1", "finding_ids": ["A1"], "match": "direct"},
                {"human_concern_id": "h2", "finding_ids": ["A2"], "match": "direct"},
            ],
        }
        counts = workflow.support_counts(row, {"h1", "h2"})
        self.assertEqual(counts["direct_all_justified_concern"], 0)
        self.assertEqual(counts["direct_all_justified_clarification"], 1)
        self.assertEqual(counts["direct_all_either"], 1)
        self.assertEqual(counts["direct_assessable_either"], 1)

    def test_image_registry_is_complete_deduplicated_and_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared_image = root / "prepared.png"
            duplicate_image = root / "duplicate.png"
            ordinary_image = root / "ordinary.png"
            debate_image = root / "debate.png"
            prepared_image.write_bytes(b"page-one")
            duplicate_image.write_bytes(b"page-one")
            ordinary_image.write_bytes(b"page-two")
            debate_image.write_bytes(b"page-three")
            prepared = {"images": [{
                "path": str(prepared_image),
                "label": "Original PDF page 1",
                "receipt_id": "receipt-1",
                "sha256": digest(prepared_image.read_bytes()),
            }]}
            inspected = [
                [(duplicate_image, "Original PDF page 1"), (ordinary_image, "Original PDF page 2")],
                [(debate_image, "Original PDF page 3")],
            ]
            with patch.object(workflow, "ROOT", root), patch.object(
                workflow, "complete_inspected_images", side_effect=inspected
            ) as inspect:
                registry = workflow.image_registry({}, root / "workspace", {"id": "paper-1"}, prepared)
            self.assertEqual(inspect.call_count, 2)
            self.assertEqual([row["label"] for row in registry], [
                "Original PDF page 1", "Original PDF page 2", "Original PDF page 3",
            ])
            self.assertEqual([row["id"] for row in registry], ["image-1", "image-2", "image-3"])
            self.assertEqual(len({row["sha256"] for row in registry}), 3)

    def test_image_registry_rejects_tampered_and_over_cap_packets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "page.png"
            image.write_bytes(b"page")
            prepared = {"images": [{
                "path": str(image), "label": "Page", "receipt_id": "r", "sha256": "wrong",
            }]}
            with patch.object(workflow, "ROOT", root), patch.object(workflow, "complete_inspected_images", return_value=[]):
                with self.assertRaisesRegex(ValueError, "Image evidence changed"):
                    workflow.image_registry({}, root / "workspace", {"id": "paper-1"}, prepared)

            prepared = {"images": []}
            paths = []
            for number in range(11):
                path = root / f"page-{number}.png"
                path.write_bytes(f"page-{number}".encode())
                paths.append((path, f"Page {number}"))
            with patch.object(workflow, "ROOT", root), patch.object(
                workflow, "complete_inspected_images", side_effect=[paths[:6], paths[6:]]
            ):
                with self.assertRaisesRegex(ValueError, "exceeds the fixed cap"):
                    workflow.image_registry({}, root / "workspace", {"id": "paper-1"}, prepared)

    def successful_model_run(self, value):
        def run(command, **kwargs):
            answer = Path(command[command.index("--output-last-message") + 1])
            answer.write_text(json.dumps(value))
            kwargs["stdout"].write(json.dumps({
                "type": "turn.completed",
                "usage": {"input_tokens": 2, "output_tokens": 1},
            }) + "\n")
            return SimpleNamespace(returncode=0)
        return run

    def protocol(self, **changes):
        value = {
            "provider": "codex",
            "model": "gpt-5.6-sol",
            "effort": "medium",
            "held_out_runs_authorized": False,
            "max_calls_per_condition": 1,
            "observed_token_stop": 100,
            "call_timeout_seconds": 30,
        }
        value.update(changes)
        return value

    def test_runtime_image_cap_requires_explicit_evidence_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = []
            for number in range(5):
                path = root / f"image-{number}.png"
                path.write_bytes(str(number).encode())
                images.append(path)
            with self.assertRaisesRegex(model_runtime.StudyBlocked, "bounded protocol allowance"):
                model_runtime.model_call(self.protocol(), root / "default", "prompt", {"type": "object"}, images=images)

            opted_in = self.protocol(max_source_images=10, image_budget_version="evidence-v1")
            with patch.object(model_runtime.subprocess, "run", side_effect=self.successful_model_run({"ok": True})):
                result = model_runtime.model_call(
                    opted_in, root / "opted-in", "prompt", {"type": "object"}, images=images
                )
            self.assertEqual(result, {"ok": True})


if __name__ == "__main__":
    unittest.main()
