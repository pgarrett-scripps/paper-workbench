"""Revision safety and loop stopping behavior, without review inference."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from peerreviewagents import verify_workspace
from peerreviewagents.workspace import normalize_review, read_json

from manuscripts import line_of
from paper_workspace.revisions import (agent_request, automation_decisions, checkout, copyedit_proposals,
    create_revision, head, run_loop, safety_reasons, snapshot)
from paper_workspace.scaffold_import import import_scaffold

FIXTURE = Path(__file__).parent / 'fixtures/scaffold-revision'


class Revisions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'workspace'
        import_scaffold(FIXTURE, self.root)
        self.paper = verify_workspace(self.root)

    def proposals(self):
        review = normalize_review(self.paper, copyedit_proposals(self.paper), 'copyedit')
        return review, automation_decisions(self.paper, review)

    def edit(self, text, quote, replacement, review_id):
        """A review of one edit on the line that holds ``text``, and a decision accepting it."""
        response = {'findings': [{'kind': 'edit', 'line': line_of(self.paper, text), 'quote': quote,
                                  'replacement': replacement}]}
        review = normalize_review(self.paper, response, review_id)
        return review, {'paper_id': self.paper.paper_id, 'review_id': review['id'],
                        'items': {f'{review_id}-1': 'accepted'}}

    def test_round_trip_preserves_original_and_all_unedited_files(self):
        before = (self.root / 'scaffold/paper.typ').read_bytes()
        review, decisions = self.proposals()
        metadata = create_revision(self.root, review, decisions, 'first', head(self.root), build=False)
        self.assertEqual(len(metadata['applied_findings']), 2)
        self.assertEqual((self.root / 'scaffold/paper.typ').read_bytes(), before)
        draft, _ = snapshot(self.root, 'first')
        source = (draft / 'scaffold/paper.typ').read_text()
        self.assertIn('to assess', source)
        # The line folds the source's double space, and the edit leaves that space as the author wrote it.
        self.assertIn('Seedlings were  imaged at 6 hours to track bending.', source)
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
        line = line_of(self.paper, 'protein activity')
        response['findings'].append({'kind': 'question', 'category': 'scientific', 'line': line,
            'quote': 'protein activity', 'comment': 'Clarify mechanistic support.', 'evidence_lines': [line]})
        review = normalize_review(self.paper, response, 'mixed')
        decisions = automation_decisions(self.paper, review)
        create_revision(self.root, review, decisions, 'mixed', head(self.root), build=False)
        ledger = read_json(self.root / 'revisions/mixed/issue-ledger.json')
        self.assertEqual(ledger[-1]['scientific_status'], 'open')
        self.assertEqual(ledger[-1]['anchor_status'], 'historical')
        self.assertEqual((ledger[-1]['finding']['document'], ledger[-1]['finding']['line']), ('paper.md', line))
        self.assertNotIn('issue_id', ledger[-1])

    def test_run_issue_cards_keep_their_issue_id_in_the_ledger(self):
        # Shaped as run_view hands them over: one card per issue, keyed by the issue id.
        review, decisions = self.proposals()
        edit = review['findings'][0]
        review['findings'][0] = {**edit, 'id': 'i01', 'source_id': 'i01', 'group': 'suggestion',
                                 'category': 'presentation', 'status': 'persisting'}
        review['findings'][1] = {'id': 'i02', 'source_id': 'i02', 'group': 'closed', 'category': 'reproducibility',
                                 'status': 'resolved', 'kind': 'issue', 'title': 'Old issue', 'members': []}
        review['findings'].append({'id': 'run-3', 'source_id': 'i02', 'group': 'required', 'status': 'new',
                                   'category': 'claims-and-conclusions', 'kind': 'issue', 'title': 'Repeat'})
        decisions['items'] = {'i01': 'accepted'}
        create_revision(self.root, review, decisions, 'issues', head(self.root), build=False)
        rows = read_json(self.root / 'revisions/issues/issue-ledger.json')[-3:]
        self.assertEqual([(row['issue_id'], row['issue_round_status'], row['scientific_status'], row['wording_decision'])
                          for row in rows],
                         [('i01', 'persisting', 'open', 'accepted'), ('i02', 'resolved', 'resolved', 'proposed'),
                          (None, 'new', 'open', 'proposed')])

    def test_stale_agent_response_stops_before_changes(self):
        response = copyedit_proposals(self.paper)
        response['source_sha256'] = 'stale'
        with self.assertRaisesRegex(ValueError, 'not bound'):
            run_loop(self.root, 'bad', provider=lambda _: response, build=False)
        self.assertEqual(read_json(self.root / 'revision-runs/bad/run.json')['status'], 'failed')
        self.assertEqual(head(self.root)['version'], 0)

    def test_numeric_removal_and_reordering_rejected(self):
        quote = 'Root bending was observed in 8 of 12 seedlings.'
        for replacement in ('Root bending was observed in 12 of 8 seedlings.', 'Root bending was observed in seedlings.'):
            review, decisions = self.edit('8 of 12', quote, replacement, 'numeric')
            with self.assertRaisesRegex(ValueError, 'Numerical'):
                create_revision(self.root, review, decisions, 'bad', head(self.root), build=False)

    def test_locked_markup_cannot_be_accepted(self):
        review, decisions = self.edit('$x^2$', 'background', 'context', 'locked')
        with self.assertRaisesRegex(ValueError, 'no editable'):
            create_revision(self.root, review, decisions, 'bad', head(self.root), build=False)

    def test_edit_across_a_line_break_in_the_source_lands_in_place(self):
        # The paragraph is wrapped over two source lines and renders as one manuscript line.
        review, decisions = self.edit('could distinguish', 'distinguish the proposed', 'separate the proposed', 'wrap')
        create_revision(self.root, review, decisions, 'wrap', head(self.root), build=False)
        source = (self.root / 'revisions/wrap/scaffold/paper.typ').read_text()
        self.assertIn('could separate the proposed mechanism', source)
        draft = verify_workspace(self.root / 'revisions/wrap')
        self.assertIn('could separate the proposed mechanism', draft.line_text(line_of(draft, 'associative')))

    def test_guard_rejects_markup_injection_and_negation_removal(self):
        quote = 'We did not measure protein activity directly.'
        for replacement in ('We did measure protein activity directly.', '#include "evil.typ"'):
            review, decisions = self.edit('not measure', quote, replacement, 'unsafe')
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
        self.assertEqual(after['editable_lines'], before['editable_lines'])
        self.assertTrue((self.root / 'reviews/agent-r1.json').exists())
        self.assertTrue((self.root / 'revisions/agent-1/reviews/agent-r2.json').exists())


if __name__ == '__main__':
    unittest.main()
