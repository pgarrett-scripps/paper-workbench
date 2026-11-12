"""Revision safety and loop stopping behavior, without review inference."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from peerreviewagents import verify_workspace
from peerreviewagents.workspace import normalize_review, read_json

from paper_workspace.revisions import (agent_request, automation_decisions, checkout, copyedit_proposals,
    create_revision, head, run_loop, safety_reasons, snapshot)
from paper_workspace.scaffold_import import import_scaffold

FIXTURE = Path(__file__).parent / 'fixtures/scaffold-revision'


class Revisions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'workspace'
        self.paper = import_scaffold(FIXTURE, self.root)

    def proposals(self):
        review = normalize_review(self.paper, copyedit_proposals(self.paper), 'copyedit')
        return review, automation_decisions(self.paper, review)

    def test_round_trip_preserves_original_and_all_unedited_files(self):
        before = (self.root / 'scaffold/paper.typ').read_bytes()
        review, decisions = self.proposals()
        metadata = create_revision(self.root, review, decisions, 'first', head(self.root), build=False)
        self.assertEqual(len(metadata['applied_findings']), 2)
        self.assertEqual((self.root / 'scaffold/paper.typ').read_bytes(), before)
        draft, _ = snapshot(self.root, 'first')
        self.assertIn('to assess', (draft / 'scaffold/paper.typ').read_text())
        self.assertIn('were imaged', (draft / 'scaffold/paper.typ').read_text())
        for name in ('config.typ', 'references.bib', 'results.typ'):
            self.assertEqual((draft / 'scaffold' / name).read_bytes(), (FIXTURE / name).read_bytes())
        self.assertIn('changes.patch', read_json(draft / 'manifest.json')['files'])
        verify_workspace(self.root)
        verify_workspace(draft)

    def test_loop_converges_and_rollback_preserves_draft(self):
        result = run_loop(self.root, 'loop', max_rounds=3, build=False)
        self.assertEqual(result['status'], 'no_eligible_edits')
        self.assertEqual(result['applied_edits'], 2)
        self.assertEqual(len(result['rounds']), 2)
        checkout(self.root, 'original', head(self.root))
        self.assertEqual(head(self.root), {'revision_id': 'original', 'version': 2})
        snapshot(self.root, 'loop-1')
        with self.assertRaises(FileExistsError):
            run_loop(self.root, 'loop', build=False)

    def test_budget_stops(self):
        result = run_loop(self.root, 'limited', max_edits=1, build=False)
        self.assertEqual(result['status'], 'edit_limit')
        self.assertEqual(result['applied_edits'], 1)

    def test_changed_head_rejects_stale_decisions(self):
        review, decisions = self.proposals()
        old = head(self.root)
        create_revision(self.root, review, decisions, 'first', old, build=False)
        with self.assertRaisesRegex(ValueError, 'Draft changed'):
            create_revision(self.root, review, decisions, 'second', old, build=False)

    def test_failed_build_never_promotes_draft(self):
        review, decisions = self.proposals()
        with patch('paper_workspace.revisions.subprocess.run', side_effect=FileNotFoundError('typst')):
            with self.assertRaises(FileNotFoundError):
                create_revision(self.root, review, decisions, 'failed', head(self.root))
        self.assertEqual(head(self.root)['revision_id'], 'original')
        self.assertFalse((self.root / 'revisions/failed').exists())

    def test_unsupported_edit_stays_open_despite_category(self):
        response = copyedit_proposals(self.paper)
        response['findings'][0]['replacement'] = 'to demonstrate causality'
        review = normalize_review(self.paper, response, 'model')
        decisions = automation_decisions(self.paper, review)
        self.assertEqual(decisions['items']['model-1'], 'proposed')
        self.assertIn('Outside the automatic language policy', decisions['assessments']['model-1']['reasons'])

    def test_scientific_findings_survive_accepted_copyedits(self):
        response = copyedit_proposals(self.paper)
        block = next(b for b in self.paper['blocks'] if 'protein activity' in b['text'])
        response['findings'].append({'kind': 'question', 'category': 'scientific', 'block_id': block['id'],
            'quote': 'protein activity', 'comment': 'Clarify mechanistic support.', 'evidence_blocks': [block['id']]})
        review = normalize_review(self.paper, response, 'mixed')
        decisions = automation_decisions(self.paper, review)
        create_revision(self.root, review, decisions, 'mixed', head(self.root), build=False)
        ledger = read_json(self.root / 'revisions/mixed/issue-ledger.json')
        self.assertEqual(ledger[-1]['scientific_status'], 'open')
        self.assertEqual(ledger[-1]['anchor_status'], 'historical')

    def test_stale_agent_response_stops_before_changes(self):
        response = copyedit_proposals(self.paper)
        response['source_sha256'] = 'stale'
        with self.assertRaisesRegex(ValueError, 'not bound'):
            run_loop(self.root, 'bad', provider=lambda _: response, build=False)
        self.assertEqual(read_json(self.root / 'revision-runs/bad/run.json')['status'], 'failed')
        self.assertEqual(head(self.root)['version'], 0)

    def test_numeric_removal_and_reordering_rejected(self):
        block = next(b for b in self.paper['blocks'] if '8 of 12' in b['text'])
        for replacement in ('Root bending was observed in 12 of 8 seedlings.', 'Root bending was observed in seedlings.'):
            response = {'findings': [{'kind': 'edit', 'block_id': block['id'],
                'quote': 'Root bending was observed in 8 of 12 seedlings.', 'replacement': replacement}]}
            review = normalize_review(self.paper, response, 'numeric')
            decisions = {'paper_id': self.paper['id'], 'review_id': review['id'], 'items': {'numeric-1': 'accepted'}}
            with self.assertRaisesRegex(ValueError, 'Numerical'):
                create_revision(self.root, review, decisions, 'bad', head(self.root), build=False)

    def test_locked_markup_cannot_be_accepted(self):
        block = next(b for b in self.paper['blocks'] if '$x^2$' in b['text'])
        response = {'findings': [{'kind': 'edit', 'block_id': block['id'], 'quote': 'background', 'replacement': 'context'}]}
        review = normalize_review(self.paper, response, 'locked')
        decisions = {'paper_id': self.paper['id'], 'review_id': review['id'], 'items': {'locked-1': 'accepted'}}
        with self.assertRaisesRegex(ValueError, 'no editable'):
            create_revision(self.root, review, decisions, 'bad', head(self.root), build=False)

    def test_guard_rejects_markup_injection_and_negation_removal(self):
        block = next(b for b in self.paper['blocks'] if 'not measure' in b['text'])
        for replacement in ('We did measure protein activity directly.', '#include "evil.typ"'):
            review = normalize_review(self.paper, {'findings': [{'kind': 'edit', 'block_id': block['id'],
                'quote': 'We did not measure protein activity directly.', 'replacement': replacement}]}, 'unsafe')
            decisions = {'paper_id': self.paper['id'], 'review_id': review['id'], 'items': {'unsafe-1': 'accepted'}}
            with self.assertRaisesRegex(ValueError, 'source-aware'):
                create_revision(self.root, review, decisions, 'bad', head(self.root), build=False)

    def test_guard_allows_association_inflection_in_grammar_correction(self):
        quote = 'A higher response in treated cells was found to associate with protein abundance.'
        replacement = 'Treated cells were found to have a higher response associated with protein abundance.'
        self.assertEqual(safety_reasons(quote, replacement), [])
        self.assertEqual(safety_reasons('Associating the response', 'An associated response'), [])
        self.assertTrue(safety_reasons('Associating the response', 'The response'))

    def test_guard_still_rejects_changes_to_protected_claim_terms(self):
        cases = [
            ('The response may be associated with treatment.',
             'The response is associated with treatment.'),
            ('The response was not associated with treatment.',
             'The response was associated with treatment.'),
            ('The response was associated with treatment.',
             'Treatment causes the response.'),
            ('The response was associated in 8 of 12 samples.',
             'The response was associated in 12 of 8 samples.'),
        ]
        for quote, replacement in cases:
            with self.subTest(replacement=replacement):
                self.assertTrue(safety_reasons(quote, replacement))

    def test_literal_guard_allows_encoding_syntax_but_not_paragraph_boundaries(self):
        self.assertTrue(safety_reasons('quoted', r'\"quoted\"'))
        self.assertEqual(safety_reasons('quoted', r'\"quoted\"', literal=True), [])
        self.assertTrue(safety_reasons('quoted', 'quoted\nnext', literal=True))

    def test_source_tampering_blocks_rollback(self):
        review, decisions = self.proposals()
        create_revision(self.root, review, decisions, 'first', head(self.root), build=False)
        (self.root / 'scaffold/paper.typ').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            checkout(self.root, 'original', head(self.root))

    def test_new_source_file_is_detected(self):
        (self.root / 'scaffold/unrecorded.typ').write_text('New content')
        with self.assertRaisesRegex(ValueError, 'inventory changed'):
            verify_workspace(self.root)

    def test_agent_handoff_tracks_current_draft(self):
        before = agent_request(self.root)
        run_loop(self.root, 'agent', build=False)
        after = agent_request(self.root)
        self.assertNotEqual(before['source_sha256'], after['source_sha256'])
        self.assertEqual(after['head']['revision_id'], 'agent-1')
        self.assertEqual(len(after['historical_issues']), 2)
        self.assertTrue((self.root / 'reviews/agent-r1.json').exists())
        self.assertTrue((self.root / 'revisions/agent-1/reviews/agent-r2.json').exists())


if __name__ == '__main__':
    unittest.main()
