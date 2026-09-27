"""Focused offline checks for four-arm blinded judge accounting."""
import copy
import unittest

from experiments.pra_three_condition.evaluate import LABELS, audit_four, schema


class FourConditionEvaluateTest(unittest.TestCase):
    def setUp(self):
        self.paper = {"blocks": [{"id": "b1", "text": "The sample contained five plants."}]}
        self.images = []
        self.anonymous = {label: [{"finding_id": label + "1", "kind": "question"}]
                          for label in LABELS}

    def rating(self, label):
        return {"finding_id": label + "1", "assessment": "justified_clarification",
                "specificity": "limited", "target": "", "scientific_consequence": "",
                "requested_resolution": "", "materiality": "moderate",
                "evidence": [{"block_id": "b1", "quote": "five plants", "image_id": "", "visual_observation": ""}],
                "counterevidence": [], "decisive_evidence_accessible": True,
                "reason": "The sample count needs clarification.", "edit_fidelity": "not_an_edit",
                "resolution_proportionality": "proportionate", "resolution_reason": "A clarification is sufficient."}

    def value(self):
        pairs = [("A", "B"), ("A", "C"), ("A", "D"), ("B", "C"), ("B", "D"), ("C", "D")]
        return {"conditions": [{"label": label, "ratings": [self.rating(label)], "matches": []}
                                for label in LABELS],
                "preferred_label": "A", "preference_reason": "A has the clearest supported issues.",
                "pairwise": [{"label_a": first, "label_b": second, "preferred_label": first,
                              "reason": "The first review is more actionable."} for first, second in pairs]}

    def test_schema_requires_four_conditions_and_six_pairs(self):
        value = schema()
        self.assertEqual(value["properties"]["conditions"]["minItems"], 4)
        self.assertEqual(value["properties"]["pairwise"]["minItems"], 6)

    def test_audit_accepts_all_four_conditions_and_pairs(self):
        checked = audit_four(self.value(), self.anonymous, self.paper, self.images)
        self.assertEqual(len(checked["valid_rating_ids"]), 4)
        self.assertFalse(checked["invalid_ratings"])

    def test_audit_rejects_duplicate_or_outside_pair_preference(self):
        value = self.value()
        value["pairwise"][-1] = copy.deepcopy(value["pairwise"][0])
        with self.assertRaisesRegex(ValueError, "cover each label pair"):
            audit_four(value, self.anonymous, self.paper, self.images)

        value = self.value()
        value["pairwise"][0]["preferred_label"] = "C"
        with self.assertRaisesRegex(ValueError, "pair member"):
            audit_four(value, self.anonymous, self.paper, self.images)


if __name__ == "__main__":
    unittest.main()
