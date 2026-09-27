import unittest

from experiments.pra_ensemble_fresh.evaluate import (
    _schema,
    _secondary_ensemble,
    _stage_groups,
    deduplicate_with_memberships,
    validate_criticized_excerpt,
    validate_issue_partition,
)


def finding(comment="Same concern"):
    return {"title": "Concern", "block_id": "b1", "quote": "source", "kind": "question",
            "severity": "major", "comment": comment, "replacement": "",
            "evidence_blocks": ["b1"], "counterevidence": [], "source_evidence": []}


class EnsembleFreshEvaluateTests(unittest.TestCase):
    def test_exact_dedup_preserves_all_stage_memberships(self):
        rows = deduplicate_with_memberships([
            {"finding": finding(), "stage": "shared", "role": "discovery"},
            {"finding": finding(), "stage": "independent", "role": "discovery"},
            {"finding": finding("Different concern"), "stage": "independent", "role": "discovery"},
        ])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["memberships"], [
            {"stage": "shared", "role": "discovery"},
            {"stage": "independent", "role": "discovery"},
        ])

    def test_issue_partition_rejects_omitted_or_repeated_findings(self):
        valid = [{"issue_id": "i1", "members": ["A1"], "reason": "Same question."},
                 {"issue_id": "i2", "members": ["B1"], "reason": "Different question."}]
        validate_issue_partition(valid, ["A1", "B1"])
        with self.assertRaisesRegex(ValueError, "partition"):
            validate_issue_partition([{"issue_id": "i1", "members": ["A1", "A1"], "reason": "Repeated."}], ["A1"])
        with self.assertRaisesRegex(ValueError, "partition"):
            validate_issue_partition([{"issue_id": "i1", "members": ["A1"], "reason": "Omitted."}], ["A1", "B1"])

    def test_unsupported_allegation_excerpt_must_be_exact_comment_text(self):
        source = finding("The paper never measures endpoint X.")
        validate_criticized_excerpt({"assessment": "unsupported_allegation",
                                     "criticized_excerpt": "never measures endpoint X"}, source)
        with self.assertRaisesRegex(ValueError, "exact"):
            validate_criticized_excerpt({"assessment": "unsupported_allegation",
                                         "criticized_excerpt": "does not measure endpoint X"}, source)
        with self.assertRaisesRegex(ValueError, "Only unsupported"):
            validate_criticized_excerpt({"assessment": "justified_concern",
                                         "criticized_excerpt": "paper"}, source)

    def test_schema_requires_criticized_excerpt(self):
        rating = _schema()["properties"]["conditions"]["items"]["properties"]["ratings"]["items"]
        self.assertIn("criticized_excerpt", rating["required"])
        self.assertEqual(_schema()["properties"]["conditions"]["minItems"], 3)
        self.assertEqual(_schema()["properties"]["conditions"]["maxItems"], 3)

    def test_stage_support_is_not_transferred_from_another_member(self):
        ensemble = finding("Ensemble primary")
        independent = finding("Independent candidate")
        anonymous = {"A": [{"finding_id": "A1", **ensemble}], "B": [],
                     "C": [{"finding_id": "C1", **independent}]}
        pool = [{"finding": independent, "memberships": [{"stage": "independent", "role": "discovery"}]}]
        value = {"conditions": [
            {"label": "A", "ratings": [{"finding_id": "A1", "assessment": "unsupported_allegation"}]},
            {"label": "B", "ratings": []},
            {"label": "C", "ratings": [{"finding_id": "C1", "assessment": "justified_concern"}]},
        ], "issue_groups": [{"issue_id": "i1", "members": ["A1", "C1"], "reason": "Same issue."}]}
        stages, _, _, _, _ = _stage_groups(value, anonymous, pool, {"A": "ensemble", "B": "sequential"},
                                            {("A", "A1"), ("C", "C1")})
        self.assertEqual(stages["ensemble"], [])
        self.assertEqual(stages["independent"], ["i1"])

    def test_secondary_join_uses_issue_id_not_title(self):
        package = {"source_findings": [{"source_finding_id": "old", "finding": finding()}],
                   "candidate_inventory": {"secondary_candidates": [{"issue_id": "new", "title": "Concern"}]}}
        resolved, skipped = _secondary_ensemble(package)
        self.assertEqual(resolved, [])
        self.assertEqual(skipped[0]["issue_id"], "new")

    def test_adjudicated_secondary_does_not_restore_the_old_allegation(self):
        original = finding('The experiment is invalid.')
        clarified = finding('Please clarify which observations were repeated.')
        package = {'source_findings':[{'source_finding_id':'i1','finding':original}],
                   'candidate_inventory':{'secondary_candidates':[{'issue_id':'i1'}]},
                   'adjudicated_secondary':[{'issue_id':'i1','finding':clarified}]}
        resolved, skipped = _secondary_ensemble(package)
        self.assertEqual(resolved, [clarified])
        self.assertEqual(skipped, [])
        package['adjudicated_secondary'] = []
        with self.assertRaisesRegex(ValueError, 'differ'):
            _secondary_ensemble(package)


if __name__ == "__main__":
    unittest.main()
