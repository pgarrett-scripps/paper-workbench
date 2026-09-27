import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from experiments.pra_prospective.core import attach_reviews, export_anonymous, import_ratings, read, report, seal, verify


REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "experiments/pra_prospective/fixture"


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class ProspectiveEvaluation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.fixture = self.root / "fixture"
        shutil.copytree(FIXTURE, self.fixture)
        shutil.copy(REPO / "experiments/pra_prospective/core.py", self.root / "core.py")
        shutil.copy(REPO / "experiments/pra_prospective/cli.py", self.root / "cli.py")
        self.study = self.root / "study"

    def tearDown(self):
        self.temp.cleanup()

    def frozen(self):
        return seal(self.fixture / "protocol.json", self.study)

    def attach(self):
        outputs = self.fixture / "outputs"
        outputs.mkdir()
        for name in ("single-review.json", "pra-review.json"):
            shutil.copy(self.fixture / "review-templates" / name, outputs / name)
        return attach_reviews(self.study)

    def exported(self):
        self.frozen()
        self.attach()
        out = self.root / "public"
        export_anonymous(self.study, out, 14)
        return out / "assessment-packet.json"

    def rating(self, packet, item="A1", quote="84 participants"):
        return {
            "provenance": {
                "assessor_id": "expert-001",
                "expertise": "Trial methods",
                "independence_attestation": "Independent and blinded",
                "rated_at": "2026-09-25",
                "source_sha256": hashlib.sha256(packet.read_bytes()).hexdigest(),
            },
            "ratings": [{
                "item_id": item,
                "assessment": "supported",
                "importance": 2,
                "actionability": 2,
                "evidence_block_id": "b0001",
                "evidence_quote": quote,
                "reason": "The totals conflict.",
            }],
        }

    def test_offline_freeze_export_import_report(self):
        packet = self.exported()
        public = read(packet)
        self.assertEqual([row["label"] for row in public["candidates"]], ["Review A", "Review B"])
        self.assertNotIn("condition", packet.read_text())
        self.assertEqual(public["manuscript"]["blocks"][0]["id"], "b0001")
        self.assertEqual(public["source_cards"], [])
        mapping = read(self.study / "private/condition-map.json")
        self.assertEqual(set(row["condition"] for row in mapping["labels"].values()), {"single", "pra"})
        ratings = self.root / "ratings.json"
        dump(ratings, self.rating(packet))
        imported = import_ratings(self.study, packet, ratings)
        self.assertEqual(imported["completion"]["rated"], 1)
        summary = report(self.study, self.root / "report.json")
        self.assertEqual(summary["rating_status"], "incomplete")
        self.assertEqual(summary["missing_item_ids"], ["B1"])
        self.assertEqual(summary["expert_correctness"]["supported"], 1)
        self.assertEqual(summary["model_preference"]["status"], "separate_not_imported")

    def test_prior_corpus_overlap_rejected(self):
        prior = read(self.fixture / "prior-corpus.json")
        prior["papers"][0]["doi"] = "10.5555/heldout.fixture.001"
        dump(self.fixture / "prior-corpus.json", prior)
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.frozen()

    def test_doi_url_prefix_cannot_evade_overlap(self):
        prior = read(self.fixture / "prior-corpus.json")
        prior["papers"][0]["doi"] = "https://doi.org/10.5555/heldout.fixture.001"
        dump(self.fixture / "prior-corpus.json", prior)
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.frozen()

    def test_shared_source_identifier_is_not_paper_overlap(self):
        candidates = read(self.fixture / "candidates.json")
        prior = read(self.fixture / "prior-corpus.json")
        candidates["papers"][0]["candidate_records"] = [{"identifier": "shared-source-1"}]
        prior["papers"][0]["candidate_records"] = [{"identifier": "shared-source-1"}]
        dump(self.fixture / "candidates.json", candidates)
        dump(self.fixture / "prior-corpus.json", prior)
        self.frozen()

    def test_unequal_resources_rejected(self):
        protocol = read(self.fixture / "protocol.json")
        protocol["conditions"]["pra"]["source_request_budget"] = 7
        dump(self.fixture / "protocol.json", protocol)
        with self.assertRaisesRegex(ValueError, "equal models"):
            self.frozen()

    def test_missing_equal_resources_are_rejected(self):
        protocol = read(self.fixture / "protocol.json")
        protocol["conditions"]["single"]["model"] = None
        protocol["conditions"]["pra"]["model"] = None
        dump(self.fixture / "protocol.json", protocol)
        with self.assertRaisesRegex(ValueError, "missing resource"):
            self.frozen()

    def test_seal_rejects_existing_review_outputs(self):
        outputs = self.fixture / "outputs"
        outputs.mkdir()
        shutil.copy(self.fixture / "review-templates/single-review.json", outputs / "single-review.json")
        with self.assertRaisesRegex(ValueError, "before review outputs"):
            self.frozen()

    def test_frozen_file_and_metadata_tampering_rejected(self):
        self.frozen()
        (self.fixture / "prompt.txt").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "failed verification"):
            verify(self.study)
        shutil.copy(FIXTURE / "prompt.txt", self.fixture / "prompt.txt")
        snapshot = read(self.study / "pretrial-snapshot.json")
        snapshot["protocol"]["conditions"]["pra"]["model_calls"] = 99
        dump(self.study / "pretrial-snapshot.json", snapshot)
        with self.assertRaisesRegex(ValueError, "metadata"):
            verify(self.study)

    def test_added_file_in_frozen_directory_is_rejected(self):
        packet = self.fixture / "packet"
        packet.mkdir()
        dump(packet / "index.json", {"records": []})
        protocol = read(self.fixture / "protocol.json")
        protocol["conditions"]["single"]["source_packet"] = "packet"
        protocol["conditions"]["pra"]["source_packet"] = "packet"
        dump(self.fixture / "protocol.json", protocol)
        self.frozen()
        (packet / "added.raw").write_text("late", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "directory"):
            verify(self.study)

    def test_wrong_or_fabricated_quote_rejected(self):
        packet = self.exported()
        ratings = self.root / "ratings.json"
        dump(ratings, self.rating(packet, quote="a fabricated quotation"))
        with self.assertRaisesRegex(ValueError, "quote failed"):
            import_ratings(self.study, packet, ratings)

    def test_invalid_date_and_cannot_assess_semantics(self):
        packet = self.exported()
        value = self.rating(packet)
        value["provenance"]["rated_at"] = "September 25"
        path = self.root / "bad-date.json"
        dump(path, value)
        with self.assertRaisesRegex(ValueError, "ISO date"):
            import_ratings(self.study, packet, path)
        value["provenance"]["rated_at"] = "2026-09-25"
        value["ratings"][0].update({"assessment": "cannot_assess", "evidence_block_id": "", "evidence_quote": ""})
        path = self.root / "cannot-assess.json"
        dump(path, value)
        result = import_ratings(self.study, packet, path)
        self.assertFalse(result["ratings"][0]["quote_validated"])
        self.assertEqual(result["ratings"][0]["quote_validation"], "not_applicable")

    def test_anonymous_export_tampering_rejected(self):
        packet = self.exported()
        packet.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Anonymous export"):
            verify(self.study)

    def test_review_source_cards_are_resolved_and_sanitized(self):
        raw = self.fixture / "source.raw"
        raw.write_text("public raw response", encoding="utf-8")
        protocol = read(self.fixture / "protocol.json")
        protocol["conditions"]["single"]["source_packet"] = "source.raw"
        protocol["conditions"]["pra"]["source_packet"] = "source.raw"
        dump(self.fixture / "protocol.json", protocol)
        self.frozen()
        card = {"evidence_id": "source-real", "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
                "evidence_text": "registered enrollment is 86", "limitation": "Curated record", "workflow": "secret",
                "fields":{"condition":"biological condition", "model":"animal model"},
                "captured_at":"2026-09-25T00:00:00Z", "effective_date":"2020-01-01",
                "version_locator":"version-1", "curator_attestation":"Curated archive provenance only"}
        outputs = self.fixture / "outputs"
        outputs.mkdir()
        for name in ("single-review.json", "pra-review.json"):
            review = read(self.fixture / "review-templates" / name)
            review["source_cards"] = [card, {"evidence_id": "unused-failure", "status": "unavailable", "limitation": "Optional lookup failed"}]
            review["findings"][0]["source_evidence"] = [{"evidence_id": "source-real", "quote": "enrollment is 86"}]
            dump(outputs / name, review)
        attach_reviews(self.study)
        public = export_anonymous(self.study, self.root / "public", 1)
        self.assertEqual(public["source_cards"][0]["evidence_id"], "source-real")
        self.assertEqual(len(public["source_cards"]), 1)
        self.assertNotIn("workflow", json.dumps(public))
        copied = self.root / "public" / public["source_cards"][0]["path"]
        self.assertNotIn("secret", copied.read_text())
        exported_card = public['source_cards'][0]['content']
        self.assertEqual(exported_card['fields'],card['fields'])
        for key in ('captured_at','effective_date','version_locator','curator_attestation'):
            self.assertEqual(exported_card[key],card[key])

    def test_dangling_review_source_evidence_is_rejected(self):
        self.frozen()
        outputs = self.fixture / "outputs"
        outputs.mkdir()
        for name in ("single-review.json", "pra-review.json"):
            review = read(self.fixture / "review-templates" / name)
            review["findings"][0]["source_evidence"] = [{"evidence_id": "missing", "quote": "claim"}]
            dump(outputs / name, review)
        attach_reviews(self.study)
        with self.assertRaisesRegex(ValueError, "Dangling"):
            export_anonymous(self.study, self.root / "public", 1)

    def test_wrong_manuscript_rejected(self):
        packet = self.exported()
        ratings = self.rating(packet)
        other = self.root / "other-packet.json"
        shutil.copy(packet, other)
        path = self.root / "ratings.json"
        dump(path, ratings)
        with self.assertRaisesRegex(ValueError, "recorded anonymous packet"):
            import_ratings(self.study, other, path)

    def test_no_ratings_report_is_honestly_unscored(self):
        self.frozen()
        summary = report(self.study, self.root / "report.json")
        self.assertEqual(summary["rating_status"], "unscored")
        self.assertEqual(summary["rated_items"], 0)
        self.assertEqual(summary["attested_independent_assessors"], 0)

    def test_observed_usage_receipts_are_sealed_and_reported(self):
        protocol = read(self.fixture / "protocol.json")
        protocol["conditions"]["single"]["usage_receipts"] = ["outputs/single-usage.json"]
        protocol["conditions"]["pra"]["usage_receipts"] = ["outputs/pra-usage.json"]
        dump(self.fixture / "protocol.json", protocol)
        self.frozen()
        outputs = self.fixture / "outputs"
        outputs.mkdir()
        for name in ("single-review.json", "pra-review.json"):
            shutil.copy(self.fixture / "review-templates" / name, outputs / name)
        dump(self.fixture / "outputs/single-usage.json", {"observed_tokens": 120, "input_tokens": 100, "output_tokens": 20, "usage_unknown": True})
        dump(self.fixture / "outputs/pra-usage.json", {"observed_tokens": 240, "input_tokens": 200, "output_tokens": 40})
        attach_reviews(self.study)
        summary = report(self.study, self.root / "usage-report.json")
        self.assertEqual(summary["cost"]["observed_by_condition"]["single"]["status"], "partial")
        self.assertEqual(summary["cost"]["observed_by_condition"]["pra"]["status"], "known")


if __name__ == "__main__":
    unittest.main()
