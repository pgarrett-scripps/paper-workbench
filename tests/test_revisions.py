"""Revision safety and loop stopping behavior, without review inference."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from peerreviewagents import verify_workspace
from peerreviewagents.workspace import normalize_review, read_json

from manuscripts import line_of
from paper_workspace.revisions import (agent_request, apply_fix_checks, automation_decisions, checkout,
    copyedit_proposals, create_revision, head, ledger_of, ledger_rows, open_problems, problem_id, problem_status,
    record_fix_checks, run_loop, safety_reasons, snapshot)
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
        question = review['findings'][-1]['id']
        self.assertEqual([problem_status(row) for row in ledger], ['not_applicable', 'not_applicable', 'open'])
        self.assertEqual((ledger[-1]['id'], ledger[-1]['source_id'], ledger[-1]['raised_on'], ledger[-1]['statement']),
                         (f'original:mixed:{question}', question, 'original', 'Clarify mechanistic support.'))
        self.assertEqual(ledger[-1]['evidence'],
                         [{'document': 'paper.md', 'line': line, 'end_line': line, 'quote': 'protein activity'}])
        self.assertEqual(ledger[-1]['fix_checks'], [])
        self.assertNotIn('status', ledger[-1])

    def test_run_issue_cards_keep_their_issue_id_in_the_ledger(self):
        # Shaped as run_view hands them over: one card per issue, keyed by the issue id.
        review, decisions = self.proposals()
        edit = review['findings'][0]
        review['findings'][0] = {**edit, 'id': 'i01', 'source_id': 'i01', 'group': 'suggestion',
                                 'category': 'presentation', 'decidable': True}
        # A status the engine wrote on an issue is not read. Every review is a fresh panel, so its issues are open.
        review['findings'][1] = {'id': 'i02', 'source_id': 'i02', 'group': 'required', 'category': 'reproducibility',
                                 'status': 'resolved', 'kind': 'issue', 'title': 'The seed', 'decidable': True,
                                 'members': [{'document': 'paper.md', 'line': 3, 'end_line': 3, 'quote': 'seed'},
                                             {'document': 'paper.md', 'line': 3, 'end_line': 3, 'quote': 'seed'},
                                             {'document': 'S1.md', 'line': 1, 'end_line': 2, 'quote': 'random'}]}
        # A card numbered by its place has no id of the review's, so the ledger makes one.
        review['findings'].append({'id': 'run-3', 'source_id': 'i02', 'group': 'required', 'decidable': False,
                                   'category': 'claims-and-conclusions', 'kind': 'issue', 'title': 'Repeat'})
        decisions['items'] = {'i01': 'accepted'}
        create_revision(self.root, review, decisions, 'issues', head(self.root), build=False)
        rows = read_json(self.root / 'revisions/issues/issue-ledger.json')[-3:]
        self.assertEqual([(row['id'], row['source_id'], problem_status(row), row['author']['wording']) for row in rows],
                         [('original:copyedit:i01', 'i01', 'open', 'accepted'),
                          ('original:copyedit:i02', 'i02', 'open', 'proposed'),
                          ('original:copyedit:ledger-1', None, 'open', 'proposed')])
        # An issue's evidence is its members' quotes, each passage once.
        self.assertEqual(rows[1]['evidence'], [{'document': 'paper.md', 'line': 3, 'end_line': 3, 'quote': 'seed'},
                                               {'document': 'S1.md', 'line': 1, 'end_line': 2, 'quote': 'random'}])

    def test_a_review_id_already_taken_gets_a_ledger_made_id(self):
        taken = {'original:run:i01', 'original:run:ledger-1'}
        self.assertEqual(problem_id('original', 'run', 'i02', taken), 'original:run:i02')
        self.assertEqual(problem_id('original', 'run', 'i01', taken), 'original:run:ledger-2')
        self.assertEqual(problem_id('original', 'run', None, taken), 'original:run:ledger-3')
        self.assertEqual(len(taken), 5)

    def test_problem_ids_hold_across_drafts(self):
        for run_id in ('a', 'b'):
            run_loop(self.root, run_id, max_edits=1, build=False)
        first, second = (read_json(self.root / f'revisions/{run_id}-1/issue-ledger.json') for run_id in ('a', 'b'))
        # The second draft copies the first draft's rows as they are and adds its own review's.
        self.assertEqual(second[:len(first)], first)
        self.assertEqual({row['raised_on'] for row in first}, {'original'})
        self.assertTrue(second[len(first):])
        self.assertEqual({row['raised_on'] for row in second[len(first):]}, {'a-1'})
        self.assertEqual(len({row['id'] for row in second}), len(second))

    def test_a_finding_the_code_check_threw_out_joins_the_ledger_as_thrown_out_and_takes_no_decision(self):
        review, decisions = self.proposals()
        item = {'id': 'u-mean', 'finding_uid': 'u-mean', 'title': 'The mean hides the spread', 'note': 'It is a median.'}
        review['run'] = {'code_check': {'cap': 20, 'checked': 1, 'over_cap': 0,
                                        'counts': {'confirmed': 0, 'contradicted': 1, 'not-shown': 0},
                                        'thrown_out': [item]}}
        decisions['items']['u-mean'] = 'accepted'
        create_revision(self.root, review, decisions, 'checked', head(self.root), build=False)
        rows = read_json(self.root / 'revisions/checked/issue-ledger.json')
        self.assertEqual(len(rows), len(review['findings']) + 1)
        self.assertEqual((rows[-1]['id'], rows[-1]['finding'], problem_status(rows[-1]), rows[-1]['author']),
                         ('original:copyedit:u-mean', item, 'thrown_out', None))

    def test_a_run_given_no_code_adds_nothing_thrown_out_to_the_ledger(self):
        review, decisions = self.proposals()
        review['run'] = {'code_check': None}
        create_revision(self.root, review, decisions, 'plain', head(self.root), build=False)
        rows = read_json(self.root / 'revisions/plain/issue-ledger.json')
        self.assertNotIn('thrown_out', [problem_status(row) for row in rows])

    def problems(self):
        """A ledger of one problem of each kind, raised on the original by one review."""
        cards = [{'id': f'i0{n}', 'title': f'Problem {n}', 'category': 'methods', 'severity': 'major',
                  'comment': f'Statement {n}.', 'members': [{'document': 'paper.md', 'line': n, 'end_line': n,
                                                             'quote': f'quote {n}'}]} for n in (1, 2, 3)]
        cards.append({'id': 'copyedit-1', 'category': 'copyedit', 'comment': 'Shorter.', 'quote': 'in order to'})
        review = {'id': 'run', 'findings': cards, 'run': {'code_check': {'thrown_out': [
            {'id': 'u-mean', 'title': 'The mean', 'comment': 'Show each repeat.', 'quote': 'the mean'}]}}}
        decisions = {'items': {'i01': 'noted', 'i02': 'noted', 'i03': 'noted'}, 'annotations': {
            'i01': {'author_comment': 'We added the seed.', 'issue_status': 'open', 'rationale': ''},
            'i02': {'author_comment': '', 'issue_status': 'addressed', 'rationale': 'Table 2 now lists it.'},
            'i03': {'author_comment': '', 'issue_status': 'declined', 'rationale': 'Out of scope.'}}}
        return ledger_rows(review, decisions, 'original', 'p', set())

    def check(self, problem, verdict, quote='text', reason='Because.'):
        return {'id': f'original:run:{problem}', 'verdict': verdict, 'quote': quote, 'reason': reason}

    def test_status_is_read_from_the_row_and_its_latest_fix_check(self):
        ledger = self.problems()
        self.assertEqual([problem_status(row) for row in ledger],
                         ['open', 'open', 'declined', 'not_applicable', 'thrown_out'])
        ledger = apply_fix_checks(ledger, 'second', [self.check('i01', 'fixed'), self.check('i02', 'not-fixed')],
                                  '2026-11-01')
        self.assertEqual([problem_status(row) for row in ledger[:2]], ['fixed', 'open'])
        ledger = apply_fix_checks(ledger, 'third', [self.check('i02', 'fixed', 'Table 2 lists the seed.')],
                                  '2026-11-17')
        self.assertEqual(problem_status(ledger[1]), 'fixed')
        self.assertEqual(ledger[1]['fix_checks'], [
            {'draft': 'second', 'verdict': 'not-fixed', 'quote': 'text', 'reason': 'Because.', 'date': '2026-11-01'},
            {'draft': 'third', 'verdict': 'fixed', 'quote': 'Table 2 lists the seed.', 'reason': 'Because.',
             'date': '2026-11-17'}])

    def test_open_problems_are_what_a_fix_check_takes(self):
        ledger = apply_fix_checks(self.problems(), 'second', [self.check('i02', 'cannot-tell', None)], '2026-11-01')
        self.assertEqual(open_problems(ledger), [
            {'id': 'original:run:i01', 'statement': 'Statement 1.', 'severity': 'major',
             'evidence': [{'document': 'paper.md', 'quote': 'quote 1'}], 'author_reply': 'We added the seed.'},
            {'id': 'original:run:i02', 'statement': 'Statement 2.', 'severity': 'major',
             'evidence': [{'document': 'paper.md', 'quote': 'quote 2'}], 'author_reply': 'Table 2 now lists it.'}])

    def test_a_fix_check_must_name_an_open_problem_once_with_a_known_verdict(self):
        ledger = self.problems()
        cases = {'no problem in the ledger': [self.check('i09', 'fixed')],
                 'checked twice': [self.check('i01', 'fixed'), self.check('i01', 'not-fixed')],
                 'is declined': [self.check('i03', 'fixed')],
                 'is thrown_out': [self.check('u-mean', 'fixed')],
                 'not .partly.': [self.check('i01', 'partly')],
                 'needs a quote or None, and a reason': [self.check('i01', 'fixed', reason=None)]}
        for message, checks in cases.items():
            with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                apply_fix_checks(ledger, 'second', checks, '2026-11-17')
        self.assertEqual([row['fix_checks'] for row in ledger], [[]] * len(ledger))

    def test_fix_checks_are_recorded_beside_the_draft_and_frozen_into_the_next(self):
        response = copyedit_proposals(self.paper)
        line = line_of(self.paper, 'protein activity')
        response['findings'].append({'kind': 'question', 'category': 'scientific', 'line': line,
            'quote': 'protein activity', 'comment': 'Clarify mechanistic support.', 'evidence_lines': [line]})
        review = normalize_review(self.paper, response, 'mixed')
        create_revision(self.root, review, automation_decisions(self.paper, review, max_edits=1), 'mixed',
                        head(self.root), build=False)
        folder = self.root / 'revisions/mixed'
        [problem] = open_problems(ledger_of(folder))
        check = {'id': problem['id'], 'verdict': 'not-fixed', 'quote': 'protein activity',
                 'reason': 'The sentence still claims a mechanism.'}
        with self.assertRaisesRegex(ValueError, 'no problem'):
            record_fix_checks(self.root, 'mixed', [{**check, 'id': 'original:mixed:nothing'}])
        self.assertFalse((folder / 'fix-checks.json').exists())
        ledger = record_fix_checks(self.root, 'mixed', [check], date='2026-11-17')
        self.assertEqual(ledger[-1]['fix_checks'], [{'draft': 'mixed', 'verdict': 'not-fixed', 'quote': 'protein activity',
            'reason': 'The sentence still claims a mechanism.', 'date': '2026-11-17'}])
        # The frozen ledger is as the draft was made, so its manifest still holds.
        self.assertEqual(read_json(folder / 'issue-ledger.json')[-1]['fix_checks'], [])
        verify_workspace(folder)
        with self.assertRaisesRegex(ValueError, 'already has its fix checks'):
            record_fix_checks(self.root, 'mixed', [check])
        self.assertEqual(run_loop(self.root, 'next', max_rounds=1, build=False)['applied_edits'], 1)
        child = self.root / 'revisions/next-1'
        self.assertEqual(read_json(child / 'issue-ledger.json')[:len(ledger)], ledger)
        self.assertFalse((child / 'fix-checks.json').exists())
        with self.assertRaisesRegex(ValueError, 'current draft'):
            record_fix_checks(self.root, 'mixed', [check])

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
        self.assertEqual([row['status'] for row in after['historical_issues']], ['not_applicable', 'not_applicable'])
        self.assertEqual(after['editable_lines'], before['editable_lines'])
        self.assertTrue((self.root / 'reviews/agent-r1.json').exists())
        self.assertTrue((self.root / 'revisions/agent-1/reviews/agent-r2.json').exists())


if __name__ == '__main__':
    unittest.main()
