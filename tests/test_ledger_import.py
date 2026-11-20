"""A review's problems in the current draft's issue ledger, the author's decision on each, and review of a draft.

Every run here is written by the engine's own code through the builders in
test_engine_rounds.py, with no model and no network. Its manuscript records
the draft's built PDF as its source, as a review of that PDF does, so the
run's identity names the PDF by hash. A draft's PDF is printed from its own
source by the typst stand-in of test_fix_check.py. The Paper Scaffold build
record of a project is written here the way ``just paper`` writes it.
"""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from peerreviewagents import read_run, review_parser, verify_workspace
from peerreviewagents.workspace import digest, normalize_review

from paper_workspace.__main__ import main
from paper_workspace.ledger_commands import added_line
from paper_workspace.revisions import (DECIDED, LEDGER, RAISED, automation_decisions, copyedit_proposals,
                                       create_revision, decide, head, ledger_of, open_problems, record_problems,
                                       snapshot)
from paper_workspace.scaffold_import import import_scaffold
from reader_fixture import pdf_bytes
from test_engine_rounds import FIRST, check_round, grouped, offline, one_round, silent_round
from test_fix_check import DATE, FIXTURE, Draft, printed, typst

QUOTES = ['twelve samples drawn from one donor', 'controls retromer assembly in all tissues', 'repeated three times']
NAMES = ['The sample', 'The scope', 'The repeats']
# A PDF that is no draft of the workspace.
OTHER_PDF = b'%PDF-1.4\n% another draft\n'


def three(uids):
    """The editor's three issues, one per finding of core-1, in rank order."""
    return [grouped(name, rank, [uid]) for rank, (name, uid) in enumerate(zip(NAMES, uids), start=1)]


def reviewed(root, source, quotes=QUOTES, issues=three):
    """A finished reviewers-only review of a manuscript whose source is ``source``."""
    with offline():
        one_round(root, FIRST, source, quotes, issues)
    return root.resolve()


def checked(root, source):
    """A finished draft-check of ``source``, which runs no editor and so is not publishable."""
    with offline():
        check_round(root, FIRST, source, 'the mean is reported in the figure')
    return root.resolve()


def stopped(root, source):
    """A review of ``source`` whose reviewers never answered, so the engine stopped it."""
    with offline():
        silent_round(root, FIRST, source)
    return root.resolve()


def built_project(folder):
    """A copy of the Scaffold fixture with a PDF printed from its source and the record ``just paper`` leaves."""
    shutil.copytree(FIXTURE, folder)
    (folder / 'paper.pdf').write_bytes(pdf_bytes([printed(folder)]))
    sources = {path.name: digest(path.read_bytes()) for path in sorted(folder.glob('*')) if path.suffix != '.pdf'}
    (folder / '.build-state').mkdir()
    (folder / '.build-state' / 'paper.pdf.json').write_text(json.dumps({
        'schema_version': 1, 'mode': 'paper', 'sources': sources, 'dependencies': [], 'manuscript_id': 'paper',
        'output_hash': digest((folder / 'paper.pdf').read_bytes())}, indent=2))
    return folder.resolve()


def command(*argv, engine_run=None):
    """Run the app with ``engine_run`` in the engine's review seat, and return the status, stdout, stderr and argv."""
    given = {}

    def review_main(argv, prog):
        args = review_parser(prog=prog).parse_args(argv)
        given['argv'] = argv
        return engine_run(Path(args.workspace), Path(args.output))

    out, errors = io.StringIO(), io.StringIO()
    with mock.patch('peerreviewagents.review_main', review_main), contextlib.redirect_stdout(out), \
            contextlib.redirect_stderr(errors):
        status = main(list(argv))
    return status, out.getvalue(), errors.getvalue(), given.get('argv')


def review_of_the_pdf(pdf, run):
    """The engine's seat in ``review``: a finished review of the PDF it was handed."""
    reviewed(run, pdf.read_bytes())
    return 0


class ReviewedDraft(Draft):
    """Draft second, built, whose ledger carries the problems a review of the original raised."""

    def setUp(self):
        super().setUp()
        self.source = self.pdf.read_bytes()
        self.raised = self.folder / RAISED

    def ids(self, run, draft, key):
        """The ids the issues of ``run`` take in the ledger of ``draft``, in the run's order."""
        return [f'{draft}:{key}:{issue["id"]}' for issue in read_run(run)['issues']]

    def next_draft(self):
        """Draft third, made from draft second with the copyedit left for it, and built."""
        review = normalize_review(self.draft, copyedit_proposals(self.draft), 'next')
        with mock.patch('paper_workspace.revisions.subprocess.run', typst):
            create_revision(self.root, review, automation_decisions(self.draft, review), 'third', head(self.root))
        return snapshot(self.root, 'third')[0]


class LedgerImportTest(ReviewedDraft):
    """``record_problems`` and ``decide`` on the ledger of draft second and of the draft made from it."""

    def test_a_finished_review_adds_its_problems_as_open_rows_and_a_second_time_adds_nothing(self):
        run = reviewed(self.temp / 'Round 1', self.source)
        result = record_problems(self.root, run, DATE)
        ids = self.ids(run, 'second', 'round-1')
        self.assertEqual(result, {'draft': 'second', 'run': str(run), 'added': ids, 'left_out': 0,
                                  'not_publishable_reasons': [], 'already': False})
        rows = {row['id']: row for row in ledger_of(self.folder) if row['raised_on'] == 'second'}
        self.assertEqual(list(rows), ids)
        for (name, quote), problem in zip(zip(NAMES, QUOTES), ids):
            row = rows[problem]
            self.assertEqual((row['title'], row['review_id'], row['raised_as'], row['severity']),
                             (name, 'round-1', 'problem', 'major'))
            self.assertEqual(row['statement'], f'{name} is stated more strongly than the data carry.')
            self.assertEqual([(span['quote'], span['line']) for span in row['evidence']], [(quote, None)])
            self.assertEqual((row['wording'], row['decisions'], row['fix_checks']), (None, [], []))
        record = json.loads(self.raised.read_text())
        self.assertEqual(record['runs'], [{'run': str(run), 'review_id': 'round-1', 'date': DATE,
                                           'pdf_sha256': digest(self.source), 'added': 3, 'left_out': 0,
                                           'not_publishable_reasons': []}])
        before = self.raised.read_bytes()
        self.assertEqual(record_problems(self.root, run, DATE),
                         {'draft': 'second', 'run': str(run), 'added': [], 'left_out': 0,
                          'not_publishable_reasons': [], 'already': True})
        self.assertEqual(self.raised.read_bytes(), before)
        self.assertEqual(self.ids(run, 'second', 'round-1'), ids)

    def test_a_check_of_the_draft_leaves_out_the_problems_raised_on_it(self):
        run = reviewed(self.temp / 'round-1', self.source)
        added = record_problems(self.root, run, DATE)['added']
        # The draft is the text these problems were raised on, so a check of it has nothing to show.
        self.assertEqual([row['id'] for row in open_problems(ledger_of(self.folder), 'second')],
                         [self.minor, self.major, self.moderate])
        self.assertEqual([row['id'] for row in open_problems(ledger_of(self.folder))][-3:], added)

    def test_a_review_of_another_pdf_is_refused_and_nothing_is_written(self):
        run = reviewed(self.temp / 'other', OTHER_PDF)
        with self.assertRaises(ValueError) as refused:
            record_problems(self.root, run, DATE)
        self.assertEqual(str(refused.exception), (
            f'The review at {run} is of another PDF than draft second: it read {read_run(run)["identity"]["pdf"]} '
            f'with hash {digest(OTHER_PDF)[:12]}, and the PDF of draft second has hash {digest(self.source)[:12]}.'))
        self.assertFalse(self.raised.exists())

    def test_a_review_that_did_not_finish_is_refused_and_nothing_is_written(self):
        run = stopped(self.temp / 'stopped', self.source)
        review = read_run(run)
        self.assertFalse(review['complete'])
        with self.assertRaisesRegex(ValueError, rf'^The review at {run} is {review["status"]}.*, and only a '
                                                'finished review adds problems to a ledger\\.$'):
            record_problems(self.root, run, DATE)
        with self.assertRaisesRegex(ValueError, 'run folder'):
            record_problems(self.root, self.temp / 'nothing', DATE)
        self.assertFalse(self.raised.exists())

    def test_an_authors_check_with_no_editor_is_added_with_why_it_is_not_publishable(self):
        run = checked(self.temp / 'check', self.source)
        reasons = read_run(run)['not_publishable_reasons']
        self.assertTrue(reasons)
        result = record_problems(self.root, run, DATE)
        self.assertEqual((result['added'], result['not_publishable_reasons']),
                         (self.ids(run, 'second', 'check'), reasons))
        self.assertEqual(json.loads(self.raised.read_text())['runs'][0]['not_publishable_reasons'], reasons)
        self.assertIn('The review is not publishable as a peer review: ', added_line(result))

    def test_the_author_decides_on_each_open_problem_in_the_ledger_of_the_draft(self):
        run = reviewed(self.temp / 'round-1', self.source)
        sample, scope, repeats = record_problems(self.root, run, DATE)['added']
        raised = self.raised.read_bytes()
        row = decide(self.root, sample, 'addressed', 'The donors are now named.', 'See the methods.')
        # Addressed is the author's word, and the problem stays open until a check of a later draft finds it fixed.
        self.assertEqual((row['status'], row['wording'], row['decisions']), ('open', None, [
            {'draft': 'second', 'status': 'addressed', 'note': 'See the methods.',
             'rationale': 'The donors are now named.'}]))
        self.assertEqual(decide(self.root, scope, 'declined', 'The claim is about one tissue.')['status'], 'declined')
        self.assertNotIn(scope, [problem['id'] for problem in open_problems(ledger_of(self.folder))])
        reply = next(problem for problem in open_problems(ledger_of(self.folder)) if problem['id'] == sample)
        self.assertEqual(reply['author_reply'], 'See the methods.\n\nThe donors are now named.')
        # A second decision on the same draft replaces the first, and a rationale left out keeps the one it gave.
        self.assertEqual(decide(self.root, sample, 'open')['decisions'], [
            {'draft': 'second', 'status': 'open', 'note': 'See the methods.', 'rationale': 'The donors are now named.'}])
        # A problem carried from the original takes a decision on this draft too.
        self.assertEqual(decide(self.root, self.major, 'declined', 'Out of scope.')['decisions'], [
            {'draft': 'second', 'status': 'declined', 'note': '', 'rationale': 'Out of scope.'}])
        # The decisions sit beside the draft, and the problems the review raised are as it raised them.
        self.assertEqual(self.raised.read_bytes(), raised)
        before = (self.folder / DECIDED).read_bytes()
        copyedit = next(row['id'] for row in ledger_of(self.folder) if row['raised_as'] == 'copyedit')
        refusals = [
            ((repeats, 'declined'), 'An addressed or declined problem needs a rationale.'),
            ((repeats, 'declined', '   '), 'An addressed or declined problem needs a rationale.'),
            ((repeats, 'declined', 'x' * 2001), 'A rationale is at most 2000 characters.'),
            ((repeats, 'open', None, 'x' * 4001), 'A note is at most 4000 characters.'),
            ((repeats, 'fixed', 'Done.'), "A decision is one of open, addressed, declined, not 'fixed'."),
            (('second:round-1:i99', 'declined', 'No.'), 'The ledger of draft second has no problem second:round-1:i99.'),
            ((copyedit, 'declined', 'No.'), f'Problem {copyedit} is a copyedit, which has no scientific status, so it '
                                            'takes no decision.'),
        ]
        for given, message in refusals:
            with self.assertRaises(ValueError, msg=given) as refused:
                decide(self.root, *given)
            self.assertEqual(str(refused.exception), message)
        self.assertEqual((self.folder / DECIDED).read_bytes(), before)

    def test_a_fresh_review_of_a_later_draft_adds_new_rows_and_matches_none_to_the_old(self):
        first = reviewed(self.temp / 'round-1', self.source)
        sample, scope, repeats = record_problems(self.root, first, DATE)['added']
        decide(self.root, scope, 'declined', 'The claim is about one tissue.')
        third = self.next_draft()
        carried = {row['id']: row for row in ledger_of(third)}
        self.assertEqual(carried[scope]['decisions'], [
            {'draft': 'second', 'status': 'declined', 'note': '', 'rationale': 'The claim is about one tissue.'}])
        # Draft third is not the PDF round one read, so round one is not a review of it.
        with self.assertRaisesRegex(ValueError, 'is of another PDF than draft third'):
            record_problems(self.root, first, DATE)
        # Round two is a fresh panel on draft third. It raises the scope again and knows nothing of round one.
        second = reviewed(self.temp / 'round-2', (third / 'artifacts/paper.pdf').read_bytes(), QUOTES[1:2],
                          lambda uids: [grouped('The scope', 1, uids)])
        added = record_problems(self.root, second, DATE)['added']
        self.assertEqual(added, self.ids(second, 'third', 'round-2'))
        ledger = {row['id']: row for row in ledger_of(third)}
        self.assertEqual(ledger[added[0]]['decisions'], [])
        self.assertEqual([ledger[problem]['title'] for problem in (scope, added[0])], ['The scope', 'The scope'])
        self.assertEqual({problem: ledger[problem] for problem in carried}, carried)
        self.assertFalse(set(added) & set(carried))
        # A problem carried from draft second is decided again on draft third, and the decision made on draft
        # second stays on its row, as the ledger frozen into draft third still has it.
        frozen = (third / LEDGER).read_bytes()
        decide(self.root, scope, 'addressed', 'The claim now names the tissue.')
        self.assertEqual(next(row for row in ledger_of(third) if row['id'] == scope)['decisions'], [
            {'draft': 'second', 'status': 'declined', 'note': '', 'rationale': 'The claim is about one tissue.'},
            {'draft': 'third', 'status': 'addressed', 'note': '', 'rationale': 'The claim now names the tissue.'}])
        self.assertEqual((third / LEDGER).read_bytes(), frozen)
        verify_workspace(third)
        # A check of draft third takes round one's open problems and the original's, and not its own. The scope
        # is addressed now, not declined, so it is open again.
        self.assertEqual([row['id'] for row in open_problems(ledger_of(third), 'third')],
                         [self.minor, self.major, self.moderate, sample, scope, repeats])


class LedgerCommandTest(ReviewedDraft):
    """``import-run`` and ``decide`` from the command line, and ``review`` of a manuscript workspace."""

    def test_import_run_prints_the_ids_it_added_and_a_second_run_adds_nothing(self):
        run = reviewed(self.temp / 'round-1', self.source)
        ids = self.ids(run, 'second', 'round-1')
        status, out, errors, _ = command('import-run', str(self.root), str(run))
        self.assertEqual((status, out.split()), (0, ids))
        self.assertEqual(errors, f'paper-workbench import-run: added 3 problems from {run} to the ledger of draft '
                                 f'second, {ids[0]} to {ids[-1]}.\n')
        self.assertEqual(command('import-run', str(self.root), str(run))[:3], (
            0, '', f'paper-workbench import-run: the review at {run} is already in the ledger of draft second, '
                   'so nothing was added.\n'))
        other = reviewed(self.temp / 'other', OTHER_PDF)
        status, out, errors, _ = command('import-run', str(self.root), str(other))
        self.assertEqual((status, out), (2, ''))
        self.assertTrue(errors.startswith(f'paper-workbench import-run: The review at {other} is of another PDF '
                                          'than draft second'), errors)

    def test_decide_records_the_decision_and_says_where_the_problem_stands(self):
        run = reviewed(self.temp / 'round-1', self.source)
        sample = record_problems(self.root, run, DATE)['added'][0]
        status, _, errors, _ = command('decide', str(self.root), sample, 'declined', '--rationale', 'Out of scope.',
                                       '--note', 'Kept for the discussion.')
        self.assertEqual((status, errors), (0, f'paper-workbench decide: problem {sample}, decided on draft second, '
                                               'is declined, and no fix check takes it.\n'))
        self.assertEqual(decide(self.root, sample, 'addressed')['decisions'], [
            {'draft': 'second', 'status': 'addressed', 'note': 'Kept for the discussion.', 'rationale': 'Out of scope.'}])
        self.assertEqual(command('decide', str(self.root), self.major, 'open')[:3], (
            0, '', f'paper-workbench decide: problem {self.major}, decided on draft second, is open.\n'))
        copyedit = next(row['id'] for row in ledger_of(self.folder) if row['raised_as'] == 'copyedit')
        self.assertEqual(command('decide', str(self.root), copyedit, 'declined', '--rationale', 'No.')[:3], (
            2, '', f'paper-workbench decide: Problem {copyedit} is a copyedit, which has no scientific status, so it '
                   'takes no decision.\n'))

    def test_review_of_a_manuscript_workspace_reviews_the_current_draft_and_adds_its_problems(self):
        run = self.temp / 'round-1'
        code = self.folder / 'scaffold'
        status, _, errors, argv = command('review', str(self.root), str(run), engine_run=review_of_the_pdf)
        self.assertEqual((status, argv), (0, [str(self.pdf), str(run), '--code', str(code)]))
        ids = self.ids(run, 'second', 'round-1')
        self.assertEqual(errors.splitlines(), [
            f'paper-workbench review: reviewing draft second, {self.pdf}, with the code in {code}. Give --no-code to '
            'review the paper alone.',
            f'paper-workbench review: added 3 problems from {run.resolve()} to the ledger of draft second, {ids[0]} '
            f'to {ids[-1]}.'])
        self.assertEqual([row['id'] for row in ledger_of(self.folder) if row['raised_on'] == 'second'], ids)
        # An arm that reviews no code is handed none, and the problems still go into the ledger.
        later = self.temp / 'round-2'
        status, _, errors, argv = command('review', str(self.root), str(later), '--arm', 'reviewers-only',
                                          engine_run=review_of_the_pdf)
        self.assertEqual((status, argv), (0, [str(self.pdf), str(later), '--arm', 'reviewers-only']))
        self.assertIn('because the reviewers-only arm reviews no code. The draft-check and full-two-track arms would '
                      f'review it with the code in {code}.', errors)
        self.assertIn(f'added 3 problems from {later.resolve()} to the ledger of draft second', errors)

    def test_a_review_that_stops_adds_nothing_and_says_why(self):
        run = self.temp / 'stopped'

        def stops(pdf, output):
            stopped(output, pdf.read_bytes())
            return 1

        status, _, errors, _ = command('review', str(self.root), str(run), '--no-code', engine_run=stops)
        self.assertEqual(status, 1)
        self.assertRegex(errors.splitlines()[-1], rf'^paper-workbench review: no problems were added to the ledger: '
                                                  rf'The review at {run.resolve()} is \S+.*, and only a finished '
                                                  'review adds problems to a ledger\\.$')
        self.assertFalse(self.raised.exists())

    def test_a_draft_that_cannot_be_reviewed_is_refused_before_the_engine_starts(self):
        unbuilt = self.temp / 'unbuilt'
        import_scaffold(FIXTURE, unbuilt)
        cases = [
            (self.folder, f'{self.folder} is a draft kept inside the manuscript workspace {self.root}. Give the '
                          'workspace, and its current draft is reviewed.'),
            (unbuilt, f'Draft original of {unbuilt.resolve()} has no built PDF, so it cannot be reviewed. Review a '
                      'draft that was built.'),
        ]
        for workspace, message in cases:
            out = self.temp / f'run-{workspace.name}'
            status, stdout, errors, argv = command('review', str(workspace), str(out))
            self.assertEqual((status, stdout, argv), (2, '', None), workspace)
            self.assertEqual(errors, f'paper-workbench review: {message}\n')
            self.assertFalse(out.exists())


class ImportProjectTest(unittest.TestCase):
    """``import-scaffold`` keeps a project's built PDF as the original draft's, so the original can be reviewed."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temp = Path(temporary.name).resolve()

    def test_a_built_project_is_imported_with_its_pdf_and_reviewed_into_the_ledger(self):
        project = built_project(self.temp / 'project')
        root = self.temp / 'workspace'
        status, out, errors, _ = command('import-scaffold', str(project), str(root))
        self.assertEqual((status, errors), (0, ''))
        manifest = json.loads((root / 'manifest.json').read_text())
        stats = manifest['statistics']
        self.assertGreater(stats['pieces'], 0)
        self.assertEqual(out, f'paper-workbench import-scaffold: imported "{manifest["title"]}" as paper '
                              f'{manifest["paper_id"]} into {root}: {stats["pieces"]} pieces, '
                              f'{stats["total_words"]:,} words and {stats["reference_entries"]} references, '
                              "with its built PDF as the original draft's.\n")
        pdf = root / 'artifacts' / 'paper.pdf'
        self.assertEqual(pdf.read_bytes(), (project / 'paper.pdf').read_bytes())
        verify_workspace(root)
        run = self.temp / 'review'
        status, _, errors, argv = command('review', str(root), str(run), '--no-code', engine_run=review_of_the_pdf)
        self.assertEqual((status, argv), (0, [str(pdf.resolve()), str(run)]))
        self.assertIn(f'paper-workbench review: reviewing draft original, {pdf.resolve()}, with no code.', errors)
        problems = [row for row in ledger_of(root) if row['raised_on'] == 'original']
        self.assertEqual([row['title'] for row in problems], NAMES)

    def test_a_project_whose_pdf_is_not_its_build_is_imported_with_no_pdf_and_a_note(self):
        build = 'Build the project with `just paper` and import it again.'
        cases = [('unbuilt', lambda folder: (folder / 'paper.pdf').unlink(), 'has no built paper.pdf.'),
                 ('stale', lambda folder: (folder / 'results.typ').write_text('Edited.\n'),
                  'is older than its source: results.typ changed since it was built.')]
        for label, spoil, reason in cases:
            project = built_project(self.temp / f'project-{label}')
            spoil(project)
            root = self.temp / f'workspace-{label}'
            status, out, errors, _ = command('import-scaffold', str(project), str(root))
            self.assertEqual(status, 0, label)
            self.assertTrue(out.startswith('paper-workbench import-scaffold: imported '), out)
            self.assertTrue(out.endswith(' references, with no PDF.\n'), out)
            self.assertIn(reason, errors, label)
            self.assertTrue(errors.startswith('paper-workbench import-scaffold: '), errors)
            self.assertTrue(errors.endswith(' The original draft has no PDF, so it cannot be reviewed or checked. '
                                            f'{build}\n'), errors)
            self.assertFalse((root / 'artifacts').exists(), label)


if __name__ == '__main__':
    unittest.main()
