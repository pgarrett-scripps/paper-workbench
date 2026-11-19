"""The loop an author runs over three drafts, each step through the app's own commands.

The original is imported from a built Paper Scaffold project and reviewed.
The author decides on each problem, edits the project's source and makes
draft-2 with ``revise``, whose PDF the fix check reads. The problem the check
found not fixed is decided again on draft-2, the source is edited once more,
and ``revise`` makes draft-3. The review is written by
``peerreviewagents.scripted_review`` through the builders in
test_engine_rounds.py, and the fix check by
``peerreviewagents.scripted_fix_check``, with no model run. typst is the stand-in of test_fix_check.py.
"""
import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from peerreviewagents import check_fixes_parser, review_parser, scripted_fix_check, verify_workspace
from peerreviewagents.workspace import read_json

from paper_workspace.__main__ import main
from paper_workspace.revisions import DECIDED, FIX_CHECKS, LEDGER, head, ledger_of, ledger_view, snapshot
from reader_fixture import pdf_bytes
from test_fix_check import answer, printed, typst
from test_ledger_import import NAMES, built_project, review_of_the_pdf

DECIDE = 'paper-workbench decide: '
REVISE = 'paper-workbench revise: '
ADDRESSED = 'is marked addressed, and stays open until a fix check of a later draft finds it fixed.'


def run(*argv, checker=None, compiler=None):
    """Run the app as the author does, and return its status, stdout and stderr.

    The engine's review seat writes a finished review of the PDF it is handed,
    its fix check seat runs ``checker`` as the checker and writes the check,
    and ``compiler``, when given, stands in for typst.
    """
    def review(argv, prog):
        args = review_parser(prog=prog).parse_args(argv)
        return review_of_the_pdf(Path(args.workspace), Path(args.output))

    def check_fixes(argv, prog):
        args = check_fixes_parser(prog=prog).parse_args(argv)
        with scripted_fix_check(args.workspace, args.output, args.problems) as check:
            checker(check)
            check.write()
        return 0

    out, errors = io.StringIO(), io.StringIO()
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch('peerreviewagents.review_main', review))
        stack.enter_context(mock.patch('paper_workspace.fix_check.check_fixes_main', check_fixes))
        if compiler:
            stack.enter_context(mock.patch('paper_workspace.revisions.subprocess.run', compiler))
        stack.enter_context(contextlib.redirect_stdout(out))
        stack.enter_context(contextlib.redirect_stderr(errors))
        status = main(list(argv))
    return status, out.getvalue(), errors.getvalue()


def edit(path, old, new):
    """Edit the author's project as a person or an agent would, replacing ``old`` once."""
    text = path.read_text()
    assert text.count(old) == 1, (path, old)
    path.write_text(text.replace(old, new))


def failing(argv, **_):
    """typst that cannot compile the draft, as an error in its source makes it."""
    if argv[1] == '--version':
        return subprocess.CompletedProcess(argv, 0, stdout='typst stand-in\n', stderr='')
    return subprocess.CompletedProcess(argv, 1, stdout='', stderr='error: unknown variable: donors\n')


class Project(unittest.TestCase):
    """A built Paper Scaffold project and the workspace imported from it."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temp = Path(temporary.name).resolve()
        self.project = built_project(self.temp / 'project')
        self.root = self.temp / 'workspace'
        status, _, errors = run('import-scaffold', str(self.project), str(self.root))
        self.assertEqual((status, errors), (0, ''))

    def revise(self, revision_id, compiler=typst):
        return run('revise', str(self.root), str(self.project), '--id', revision_id, compiler=compiler)

    def unchanged(self):
        """The workspace is as it was: the original is current, and no draft or staging folder was left."""
        self.assertEqual(head(self.root), {'revision_id': 'original', 'version': 0})
        self.assertFalse((self.root / 'revisions' / 'draft-2').exists())
        self.assertEqual([path.name for path in self.root.iterdir() if path.name.startswith('.revision-')], [])
        verify_workspace(self.root)


class ReviewLoopTest(Project):
    def test_review_decide_revise_check_decide_again_and_revise(self):
        # Draft 1, the original: the engine reviews its PDF and the author decides on each problem.
        status, _, errors = run('review', str(self.root), str(self.temp / 'round-1'), '--no-code')
        self.assertEqual(status, 0, errors)
        sample, scope, repeats = [row['id'] for row in ledger_of(self.root)]
        self.assertEqual([row['title'] for row in ledger_of(self.root)], NAMES)
        for problem, status, rationale, stands in [
                (sample, 'addressed', 'The methods name the donor.', ADDRESSED),
                (scope, 'declined', 'The claim is about roots, as the title says.', 'is declined, and no fix check '
                                                                                    'takes it.'),
                (repeats, 'addressed', 'Each result gives its repeats.', ADDRESSED)]:
            self.assertEqual(run('decide', str(self.root), problem, status, '--rationale', rationale), (
                0, '', f'{DECIDE}problem {problem}, decided on draft original, {stands}\n'))
        original_decisions = (self.root / DECIDED).read_bytes()

        # The author edits the project's source and makes draft-2 from it.
        edit(self.project / 'paper.typ', 'We did not measure protein activity directly.',
             'We did not measure protein activity directly. The seedlings came from one donor line.')
        edit(self.project / 'results.typ', 'in 8 of 12 seedlings.', 'in 8 of 12 seedlings, in each of three repeats.')
        self.assertEqual(self.revise('draft-2'), (0, 'draft-2\n', (
            f'{REVISE}made draft draft-2 from {self.project}, with the ledger of draft original frozen into it, and '
            'it is the current draft.\n')))
        second, _ = snapshot(self.root, 'draft-2')
        self.assertEqual(head(self.root), {'revision_id': 'draft-2', 'version': 1})
        self.assertEqual(read_json(second / 'revision.json')['edited_from'], str(self.project))
        self.assertEqual((second / 'artifacts/paper.pdf').read_bytes(), pdf_bytes([printed(self.project)]))
        patch = (second / 'changes.patch').read_text()
        for text in ['--- before/paper.typ\n+++ after/paper.typ\n',
                     '+Seedlings were  imaged at 6 hours in order to track bending. We did not measure protein '
                     'activity directly. The seedlings came from one donor line.\n',
                     '--- before/results.typ\n+++ after/results.typ\n',
                     '+Root bending was observed in 8 of 12 seedlings, in each of three repeats. The study was not '
                     'designed to establish causality.\n']:
            self.assertIn(text, patch)
        # The ledger of the original, with each decision on it, is frozen into draft-2.
        self.assertEqual([(row['id'], [decision['draft'] for decision in row['decisions']], row['fix_checks'])
                          for row in read_json(second / LEDGER)],
                         [(sample, ['original'], []), (scope, ['original'], []), (repeats, ['original'], [])])
        frozen = (second / LEDGER).read_bytes()

        # The fix check of draft-2 takes the two open problems: the sample is not fixed, the repeats are.
        def checker(check):
            answer(check, sample, 'not-fixed', 'one donor line', note='One donor line is still one donor.')
            answer(check, repeats, 'fixed', 'three repeats', note='The result names its repeats.')

        self.assertEqual(run('check-fixes', str(self.root), str(self.temp / 'check-1'), checker=checker), (
            0, '', 'paper-workbench check-fixes: recorded on draft draft-2: fixed 1, not-fixed 1, cannot-tell 0, '
                   'not checked 0.\n'))

        # The problem found not fixed is decided again on draft-2, and the fixed one takes no decision.
        self.assertEqual(run('decide', str(self.root), sample, 'addressed', '--rationale',
                             'The methods now name four donor lines.'), (
            0, '', f'{DECIDE}problem {sample}, decided on draft draft-2, {ADDRESSED}\n'))
        self.assertEqual(run('decide', str(self.root), repeats, 'declined', '--rationale', 'No.'), (
            2, '', f'{DECIDE}Problem {repeats} is fixed, as a fix check found, so it takes no decision.\n'))
        second_files = {name: (second / name).read_bytes() for name in (LEDGER, FIX_CHECKS, DECIDED)}
        self.assertEqual(second_files[LEDGER], frozen)

        # The author edits the source again and makes draft-3, which freezes draft-2's checks and decisions.
        edit(self.project / 'paper.typ', 'from one donor line.', 'from four donor lines.')
        self.assertEqual(self.revise('draft-3')[:2], (0, 'draft-3\n'))
        third, _ = snapshot(self.root, 'draft-3')
        self.assertEqual(read_json(third / 'revision.json')['parent'], 'draft-2')
        self.assertEqual({row['id']: ([decision['draft'] for decision in row['decisions']],
                                      [check['verdict'] for check in row['fix_checks']])
                          for row in read_json(third / LEDGER)},
                         {sample: (['original', 'draft-2'], ['not-fixed']), scope: (['original'], []),
                          repeats: (['original'], ['fixed'])})

        # A declined problem is decided again on draft-3, and no earlier draft's files change.
        self.assertEqual(run('decide', str(self.root), scope, 'addressed', '--rationale',
                             'The claim now names roots alone.'), (
            0, '', f'{DECIDE}problem {scope}, decided on draft draft-3, {ADDRESSED}\n'))
        self.assertEqual({name: (second / name).read_bytes() for name in second_files}, second_files)
        self.assertEqual((self.root / DECIDED).read_bytes(), original_decisions)
        # The card reads each problem as /api/ledger hands it over, every decision beside every fix check.
        rows = {row['id']: row for row in ledger_view(ledger_of(third))}
        self.assertEqual(rows[sample]['decisions'], [
            {'draft': 'original', 'status': 'addressed', 'note': '', 'rationale': 'The methods name the donor.'},
            {'draft': 'draft-2', 'status': 'addressed', 'note': '', 'rationale': 'The methods now name four donor '
                                                                                  'lines.'}])
        self.assertEqual([(check['draft'], check['verdict'], check['note']) for check in rows[sample]['fix_checks']],
                         [('draft-2', 'not-fixed', 'One donor line is still one donor.')])
        self.assertEqual({key: row['status'] for key, row in rows.items()},
                         {sample: 'open', scope: 'open', repeats: 'fixed'})
        self.assertEqual([decision['draft'] for decision in rows[scope]['decisions']], ['original', 'draft-3'])
        for folder in (self.root, second, third):
            verify_workspace(folder)


class ReviseTest(Project):
    """``revise`` refuses with the reason, and leaves the current draft current, when it can make no draft."""

    def test_a_project_with_no_change_makes_no_draft(self):
        self.assertEqual(self.revise('draft-2'), (2, '', (
            f'{REVISE}Nothing changed: the source from {self.project} is the source of draft original, file for '
            'file, so no draft was made.\n')))
        self.unchanged()

    def test_a_project_that_does_not_build_makes_no_draft(self):
        edit(self.project / 'results.typ', 'in 8 of 12 seedlings.', 'in 8 of #donors seedlings.')
        self.assertEqual(self.revise('draft-2', compiler=failing), (2, '', (
            f'{REVISE}Draft compilation failed. Current draft preserved. error: unknown variable: donors\n\n')))
        self.unchanged()

    def test_a_folder_that_is_not_the_project_outside_the_workspace_is_refused(self):
        inside, empty = (self.root / 'scaffold').resolve(), self.temp / 'empty'
        empty.mkdir()
        cases = [(inside, f'The project {inside} and the workspace {self.root} overlap. Revise from the project '
                          'folder the workspace was imported from, outside the workspace.'),
                 (empty, f'{empty} is not a Paper Scaffold project: it has no paper.typ.')]
        for folder, message in cases:
            self.assertEqual(run('revise', str(self.root), str(folder), '--id', 'draft-2', compiler=typst),
                             (2, '', f'{REVISE}{message}\n'), folder)
        self.unchanged()


if __name__ == '__main__':
    unittest.main()
