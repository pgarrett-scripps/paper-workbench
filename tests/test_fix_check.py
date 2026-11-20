"""The engine's fix check of a draft, recorded in the draft's issue ledger, and the check-fixes command.

Every check here is written by the engine's own fix-check lane through
``peerreviewagents.scripted_fix_check``, with a script of this file in the
checker's seat and no model run. A check that did not finish is one the engine
blocked: the draft it was handed has a page turned on its side and its reader
never answers, so the new draft is never sealed. A check whose reader failed on
a draft it could still read goes on from the converter's text. A draft's PDF
comes from ``reader_fixture.pdf_bytes``, printed from the draft's own source
where typst would compile it, as CI has no typst.
"""
import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from peerreviewagents import (NO_ANSWER, check_fixes_parser, names, read_fix_check, scripted_fix_check,
                              verify_workspace)
from peerreviewagents.workspace import normalize_review, read_json

from manuscripts import line_of
from paper_workspace import revisions
from paper_workspace.__main__ import main
from paper_workspace.fix_check import problem_rows
from paper_workspace.revisions import (automation_decisions, copyedit_proposals, create_revision, fix_check_entries,
                                       head, ledger_of, open_problems, problem_status, record_fix_checks, snapshot)
from paper_workspace.scaffold_import import import_scaffold
from reader_fixture import PAGES, TURNED, pdf_bytes

FIXTURE = Path(__file__).parent / 'fixtures/scaffold-revision'
DATE = '2026-11-18'
# The problems the review of the original raises, out of severity order, as a check takes the gravest first.
RAISED = [('8 of 12 seedlings', 'Report the seedlings that did not bend.', 'minor'),
          ('protein activity', 'Say what supports the mechanism.', 'major'),
          ('in order to assess', 'Say how treatment was assigned.', 'moderate')]
# The engine's reason for a problem dealt to a checker that returned without a verdict on it.
NOT_REACHED = 'fix-1 claimed its batch and stopped without reporting, so the new draft was never read against it'
PROG = 'paper-workbench check-fixes: '
# A reader that never answers. On a draft the converter reads whole, the check goes on from the converter's text.
UNREAD = {'reader': lambda slot: NO_ANSWER}
# A check blocked in the Read stage is refused by its status. Why it stopped is the check's ``stopped``.
BLOCKED = r'is blocked, and only a complete check is recorded\.'
STOPPED = 'the reader did not seal the new draft and it could not be sealed as converted: '
# The engine's row for a problem whose lane never started because the run stopped first.
NEVER_STARTED = ('fix-1 never claimed its batch, so nothing read the draft against it; the run stopped first, '
                 'and stopped says why')


def printed(project):
    """The body of a Scaffold draft as one page of (font size, text): its headings and paragraphs, no markup."""
    source = (project / 'paper.typ').read_text().split('// >>> BODY START')[1].split('// <<< BODY END')[0]
    source = source.replace('#include "results.typ"', (project / 'results.typ').read_text())
    page = []
    for block in source.split('\n\n'):
        text = ' '.join(block.split())
        if text.startswith('= '):
            page.append((13, text[2:]))
        elif text:
            page.append((11, text))
    return page


def typst(argv, **_):
    """Stand in for typst: compile prints the draft into a PDF, and --version names the stand-in."""
    if argv[1] == '--version':
        return subprocess.CompletedProcess(argv, 0, stdout='typst stand-in\n', stderr='')
    Path(argv[5]).write_bytes(pdf_bytes([printed(Path(argv[3]))]))
    return subprocess.CompletedProcess(argv, 0, stdout='', stderr='')


def line_holding(slot, text):
    """The number and text of the first line served to the checker's ``slot`` that holds ``text``."""
    number = 1
    while text not in slot.line(number):
        number += 1
    return number, slot.line(number)


def answer(slot, problem_id, verdict, holding=None, **named):
    """Submit one verdict from the checker's ``slot``, quoting the served line that holds ``holding`` when given."""
    if holding:
        named['quote'] = line_holding(slot, holding)[1]
    return slot.submit_fix_check(problem_id, verdict, **named)


def blocked(run, problems):
    """The engine's fix check of ``problems`` into ``run``, blocked before any checker sat.

    The draft it is handed has a page turned on its side, which the converter
    reads too little of to seal, and its reader never answers, so the new
    draft is never sealed and the engine blocks the check.
    """
    turned = Path(run).with_name(Path(run).name + '.pdf')
    turned.write_bytes(pdf_bytes(PAGES, TURNED))
    check = scripted_fix_check(turned, run, problems, UNREAD)
    assert check.status == 'blocked', (check.status, check.blocked_reason)


class Draft(unittest.TestCase):
    """A workspace whose current draft, built, takes the problems a review of the original raised."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temp = Path(temporary.name).resolve()
        self.root = self.temp / 'workspace'
        import_scaffold(FIXTURE, self.root)
        paper = verify_workspace(self.root)
        response = copyedit_proposals(paper)
        for quote, comment, severity in RAISED:
            line = line_of(paper, quote)
            response['findings'].append({'kind': 'question', 'category': 'scientific', 'line': line, 'quote': quote,
                                         'comment': comment, 'severity': severity, 'evidence_lines': [line]})
        review = normalize_review(paper, response, 'first')
        # One of the two copyedits goes into this draft, and the other is left for the next.
        with patch('paper_workspace.revisions.subprocess.run', typst):
            create_revision(self.root, review, automation_decisions(paper, review, max_edits=1), 'second',
                            head(self.root))
        self.folder, self.draft = snapshot(self.root, 'second')
        self.pdf = self.folder / 'artifacts/paper.pdf'
        self.minor, self.major, self.moderate = [row['id'] for row in open_problems(ledger_of(self.folder))]

    def first_check(self, slot):
        """The checker of a first check: a verdict quoting the draft, one resting on a quote gone, one not reached."""
        self.quoted = line_holding(slot, 'protein activity')
        answer(slot, self.major, 'not-fixed', 'protein activity', note='The sentence still names no support.')
        answer(slot, self.moderate, 'fixed', searches=['in order to assess'], note='The sentence was rewritten.')

    def checks(self, ledger):
        """Each problem's fix checks, by id, for the problems that have any."""
        return {row['id']: row['fix_checks'] for row in ledger if row['fix_checks']}


class FixCheckTest(Draft):
    def check(self, run, script, unread=False):
        """The engine's fix check of the draft's PDF on its open problems, with ``script`` as the checker, as read.

        When ``unread`` is true the reader never answers, so the check reads
        the converter's text of the draft.
        """
        problems = open_problems(ledger_of(self.folder), 'second')
        scripted_fix_check(self.pdf, run, problems, {**(UNREAD if unread else {}), 'fix-check': script})
        return read_fix_check(run)

    def test_the_verdict_names_are_the_engines(self):
        self.assertIs(revisions.FIX_VERDICTS, names.FIX_VERDICTS)

    def test_a_check_is_recorded_beside_the_draft_and_frozen_into_the_next(self):
        self.assertNotIn('in order to assess', self.draft.line_text(line_of(self.draft, 'to assess')))
        run = self.temp / 'check-1'
        check = self.check(run, self.first_check)
        # The checker returned with the minor problem unanswered, so the engine calls the check incomplete, and
        # every entry it writes says so, the two with verdicts as well.
        self.assertTrue(check['complete'])
        self.assertIn(NOT_REACHED, check['incomplete_reason'])
        whole = {'lane': 'fix-1', 'check_incomplete': check['incomplete_reason'], 'read_failed': ''}
        ledger = record_fix_checks(self.root, 'second', check, date=DATE)
        line, quote = self.quoted
        self.assertEqual(self.checks(ledger), {
            self.major: [{'draft': 'second', 'run': str(run), 'date': DATE, 'verdict': 'not-fixed', 'basis': 'quote',
                          'evidence': {'document': 'paper.md', 'line': line, 'end_line': line, 'page': 1,
                                       'section': 'Methods', 'quote': quote},
                          'old_evidence': [{'document': 'paper.md', 'quote': 'protein activity', 'present': True}],
                          'searches': [], 'reason': '', 'note': 'The sentence still names no support.', **whole}],
            self.moderate: [{'draft': 'second', 'run': str(run), 'date': DATE, 'verdict': 'fixed',
                             'basis': 'old-quote-gone', 'evidence': None,
                             'old_evidence': [{'document': 'paper.md', 'quote': 'in order to assess', 'present': False}],
                             'searches': ['in order to assess'], 'reason': '', 'note': 'The sentence was rewritten.',
                             **whole}],
            self.minor: [{'draft': 'second', 'run': str(run), 'date': DATE, 'verdict': None, 'basis': '',
                          'evidence': None, 'old_evidence': [], 'searches': [], 'reason': NOT_REACHED, 'note': '',
                          **whole}]})
        by_id = {row['id']: row for row in ledger}
        self.assertEqual([problem_status(by_id[key]) for key in (self.major, self.moderate, self.minor)],
                         ['open', 'fixed', 'open'])
        # A problem the check did not reach goes to the next check of the same draft, and one with a verdict
        # waits for a later draft.
        self.assertEqual([row['id'] for row in open_problems(ledger, 'second')], [self.minor])
        self.assertEqual([row['id'] for row in open_problems(ledger)], [self.minor, self.major])
        # The frozen ledger is as the draft was made, so its manifest still holds.
        self.assertEqual(self.checks(read_json(self.folder / 'issue-ledger.json')), {})
        verify_workspace(self.folder)

        before = (self.folder / 'fix-checks.json').read_bytes()
        with self.assertRaisesRegex(ValueError, f'The fix check at {run} is already recorded on draft second'):
            record_fix_checks(self.root, 'second', read_fix_check(run))
        self.assertEqual((self.folder / 'fix-checks.json').read_bytes(), before)

        def second_check(slot):
            self.assertEqual(slot.fix_queue()['count'], 1)
            answer(slot, self.minor, 'cannot-tell', reason='The draft does not say how many seedlings were scored.',
                   note='The results still count only the seedlings that bent.')
        again = self.temp / 'check-2'
        ledger = record_fix_checks(self.root, 'second', self.check(again, second_check), date=DATE)
        minor = next(row for row in ledger if row['id'] == self.minor)
        # The second check answered the one problem it was given, so it is not incomplete.
        self.assertEqual([(entry['run'], entry['verdict'], bool(entry['check_incomplete']))
                          for entry in minor['fix_checks']],
                         [(str(run), None, True), (str(again), 'cannot-tell', False)])
        self.assertEqual((problem_status(minor), open_problems(ledger, 'second')), ('open', []))

        # The next draft carries every check in its own frozen ledger, and the checked draft takes no more.
        self.assertEqual(revisions.run_loop(self.root, 'next', max_rounds=1, build=False)['applied_edits'], 1)
        child = self.root / 'revisions/next-1'
        self.assertEqual(read_json(child / 'issue-ledger.json')[:len(ledger)], ledger)
        self.assertFalse((child / 'fix-checks.json').exists())
        with self.assertRaisesRegex(ValueError, 'Record fix checks on the current draft'):
            record_fix_checks(self.root, 'second', read_fix_check(run))

    def test_a_check_whose_reader_failed_says_so_on_every_entry(self):
        # A check whose reader read the pages says nothing of it.
        self.assertEqual({entry['read_failed'] for entry in fix_check_entries(
            self.check(self.temp / 'read', self.first_check), DATE)}, {''})
        run = self.temp / 'unread'
        check = self.check(run, self.first_check, unread=True)
        # The reader never answered, so the draft was sealed as converted and the check went on from that text.
        # The engine says so on its record of the Read stage, with the reason each entry carries.
        self.assertTrue(check['complete'])
        self.assertEqual((check['read']['reader_failed'], check['read']['sealed']), (True, True))
        # The attempts are the reader's real sessions: the one that never answered and the retry.
        self.assertEqual(check['read']['attempts'], 2)
        reason = check['read']['reason']
        self.assertTrue(reason)
        ledger = record_fix_checks(self.root, 'second', check, date=DATE)
        self.assertEqual({entry['read_failed'] for entries in self.checks(ledger).values() for entry in entries},
                         {reason})

    def test_a_check_that_is_not_complete_or_not_read_whole_changes_nothing(self):
        stopped = self.temp / 'stopped'
        blocked(stopped, open_problems(ledger_of(self.folder), 'second'))
        check = read_fix_check(stopped)
        with self.assertRaisesRegex(ValueError, BLOCKED) as refused:
            record_fix_checks(self.root, 'second', check)
        # The cause is kept once, as stopped, and the refusal leaves it to the command to print.
        self.assertTrue(check['stopped'].startswith(STOPPED), check['stopped'])
        self.assertNotIn(check['stopped'], str(refused.exception))
        self.assertEqual({row['reason'] for row in check['unchecked']}, {NEVER_STARTED})
        # A run blocked in the Read stage says the reader failed, that nothing was sealed, and why.
        read = check['read']
        self.assertEqual((read['reader_failed'], read['sealed'], read['reason']), (True, False, check['stopped']))
        self.assertIsInstance(read['attempts'], int)
        damaged = self.temp / 'damaged'
        self.check(damaged, self.first_check)
        # A process killed while writing leaves a file that is not JSON.
        (damaged / 'review/fix-check.json').write_text('{"status": ')
        with self.assertRaisesRegex(ValueError, 'could not be read whole: fix-check.json is not valid JSON'):
            record_fix_checks(self.root, 'second', read_fix_check(damaged))
        self.assertFalse((self.folder / 'fix-checks.json').exists())
        self.assertEqual(ledger_of(self.folder), read_json(self.folder / 'issue-ledger.json'))

    def test_a_problem_past_the_cap_is_entered_as_not_checked_with_the_reason(self):
        paper = self.temp / 'paper.pdf'
        paper.write_bytes(pdf_bytes([[(11, 'Readings on a level bench were repeated.')]]))
        rows = [{'id': f'p{n:02d}', 'statement': 'The bench is not named.', 'severity': 'major',
                 'evidence': [{'document': '', 'quote': 'level bench'}]} for n in range(1, 42)]

        def first(slot):
            # Each lane is handed its own batch. Only the lane holding p01 answers, so the rest are not reached.
            if 'p01' in [row['id'] for row in slot.fix_queue()['problems']]:
                answer(slot, 'p01', 'fixed', 'level bench', note='The bench is named.')
        scripted_fix_check(paper, self.temp / 'run', rows, {'fix-check': first})
        check = read_fix_check(self.temp / 'run')
        entries = fix_check_entries(check, DATE)
        self.assertEqual([entry['id'] for entry in entries], [row['id'] for row in rows])
        # Each problem with no verdict keeps the engine's reason and the lane it was dealt to, if any.
        self.assertEqual([(entry['verdict'], entry['lane'], entry['reason']) for entry in entries[::20]],
                         [('fixed', 'fix-1', ''), (None, 'fix-3', NOT_REACHED.replace('fix-1', 'fix-3')),
                          (None, '', "past this check's limit of 40 problems: it was never dealt to a checker")])
        self.assertEqual({entry['check_incomplete'] for entry in entries}, {check['incomplete_reason']})
        # The engine writes a row for every problem with no verdict and says why a check is incomplete, so a
        # check missing either is refused, not entered with a reason the engine did not give.
        with self.assertRaisesRegex(ValueError, 'has no verdict on problem p02 and no row saying why'):
            fix_check_entries({**check, 'unchecked': []}, DATE)
        with self.assertRaisesRegex(ValueError, 'is incomplete and does not say why'):
            fix_check_entries({**check, 'incomplete_reason': None}, DATE)


class CheckFixesCommandTest(Draft):
    """``paper-workbench check-fixes``, with the engine's lane run by a script in place of the model session."""

    def command(self, *argv, script=None, stopped=False, unread=False, after=None):
        """Run the command with ``script`` as the checker, and return its status, stderr and what the engine got.

        When ``stopped`` is true the engine is handed a draft it cannot seal and
        blocks the check, and exits 1. When ``unread`` is true the reader never
        answers, and the check reads the converter's text of the draft.
        ``after`` is handed the run folder once the engine is done with it.
        """
        given = {}

        def engine(argv, prog):
            args = check_fixes_parser(prog=prog).parse_args(argv)
            given.update(argv=argv, problems=read_json(args.problems))
            if stopped:
                blocked(args.output, args.problems)
            else:
                scripted_fix_check(args.workspace, args.output, args.problems,
                                   {**(UNREAD if unread else {}), 'fix-check': script})
            if after:
                after(Path(args.output))
            return 1 if stopped else 0

        errors = io.StringIO()
        with patch('paper_workspace.fix_check.check_fixes_main', engine), contextlib.redirect_stderr(errors):
            returned = main(['check-fixes', *argv])
        return returned, errors.getvalue(), given

    def written(self, *answers):
        """A checker that submits each of ``answers``, after which the engine writes the check."""
        def script(slot):
            for problem_id, verdict, holding, named in answers:
                answer(slot, problem_id, verdict, holding, **named)
        return script

    def test_the_command_checks_the_open_problems_and_records_the_verdicts(self):
        run = self.temp / 'check-1'
        open_rows = {row['id']: row for row in open_problems(ledger_of(self.folder))}
        status, errors, given = self.command(str(self.root), str(run), script=self.written(
            (self.minor, 'fixed', '8 of 12 seedlings', {'note': 'The seedlings that did not bend are reported.'}),
            (self.major, 'not-fixed', 'protein activity', {'note': 'Still no support.'})))
        # The checker left the moderate problem unanswered, so the check is incomplete, and a line under the
        # counts says why in the engine's words.
        reason = read_fix_check(run)['incomplete_reason']
        self.assertIn(NOT_REACHED, reason)
        self.assertEqual((status, errors), (0, PROG + 'recorded on draft second: fixed 1, not-fixed 1, '
                                                      'cannot-tell 0, not checked 1.\n'
                                            + PROG + 'This check is incomplete, so a problem not checked is still '
                                                     f'open: {reason.rstrip(".")}.\n'))
        self.assertEqual(given['argv'], [str(self.pdf), str(run), '--problems', str(run / 'problems.json')])
        # The problems file is the open problems of the ledger, the gravest first.
        self.assertEqual(given['problems'], {'schema_version': names.PROBLEMS_SCHEMA_VERSION, 'problems': [
            open_rows[key] for key in (self.major, self.moderate, self.minor)]})
        self.assertEqual({key: [entry['verdict'] for entry in entries]
                          for key, entries in self.checks(ledger_of(self.folder)).items()},
                         {self.major: ['not-fixed'], self.moderate: [None], self.minor: ['fixed']})

        # The next check of the draft, into a new run folder, takes only the problem the first did not reach.
        status, errors, given = self.command(str(self.root), str(self.temp / 'check-2'), script=self.written(
            (self.moderate, 'fixed', None, {'searches': ['in order to assess'], 'note': 'Rewritten.'})))
        self.assertEqual([row['id'] for row in given['problems']['problems']], [self.moderate])
        self.assertEqual((status, errors), (0, PROG + 'recorded on draft second: fixed 1, not-fixed 0, '
                                                      'cannot-tell 0, not checked 0.\n'))
        self.assertEqual(self.command(str(self.root), str(self.temp / 'check-3'), script=self.written()),
                         (2, PROG + 'Draft second has no open problem left to check.\n', {}))

    def test_a_problem_the_engine_would_refuse_is_left_out_and_named(self):
        ledger = ledger_of(self.folder)
        unrated = {**next(row for row in ledger if row['id'] == self.minor), 'id': 'original:first:unrated',
                   'severity': None}
        rows, notes = problem_rows([*ledger, unrated], 'second')
        self.assertEqual([row['id'] for row in rows], [self.major, self.moderate, self.minor])
        self.assertEqual(len(notes), 1)
        self.assertTrue(notes[0].startswith('problem original:first:unrated is left out of this check: '), notes)
        self.assertIn('severity', notes[0])

    def test_a_check_whose_reader_failed_says_so_under_its_counts(self):
        run = self.temp / 'unread'
        status, errors, _ = self.command(str(self.root), str(run), unread=True, script=self.written(
            (self.minor, 'fixed', '8 of 12 seedlings', {'note': 'Reported.'}),
            (self.major, 'not-fixed', 'protein activity', {'note': 'Still no support.'}),
            (self.moderate, 'fixed', None, {'searches': ['in order to assess'], 'note': 'Rewritten.'})))
        read = read_fix_check(run)['read']
        self.assertTrue(read['reader_failed'])
        reason = read['reason']
        self.assertEqual((status, errors), (0, PROG + 'recorded on draft second: fixed 2, not-fixed 1, '
                                                      'cannot-tell 0, not checked 0.\n'
                                            + PROG + 'The reader did not read the pages of draft second, so the '
                                                     f"check read the converter's text: {reason.rstrip('.')}.\n"))

    def test_a_check_that_is_not_complete_or_not_read_whole_leaves_the_ledger_unchanged(self):
        status, errors, _ = self.command(str(self.root), str(self.temp / 'stopped'), stopped=True)
        self.assertEqual(status, 1)
        self.assertRegex(errors, BLOCKED + r' The ledger of draft second is unchanged\.\n')
        # Why the run stopped is printed once, and the line for its problems points there in the engine's words.
        check = read_fix_check(self.temp / 'stopped')
        self.assertEqual([row['id'] for row in check['unchecked']], [self.major, self.moderate, self.minor])
        self.assertEqual(errors.count(check['stopped']), 1, errors)
        self.assertTrue(errors.endswith(f'{PROG}Stopped: {check["stopped"].rstrip(".")}.\n'
                                        f'{PROG}No verdict on {self.major}, {self.moderate}, {self.minor} '
                                        f'(fix-1): {NEVER_STARTED}.\n'), errors)

        def damaged(run):
            # A process killed while writing leaves a file that is not JSON.
            (run / 'review/fix-check.json').write_text('{"status": ')
        status, errors, _ = self.command(str(self.root), str(self.temp / 'damaged'), script=self.first_check,
                                         after=damaged)
        self.assertEqual(status, 1)
        self.assertIn('could not be read whole', errors)
        self.assertIn('The ledger of draft second is unchanged.', errors)
        self.assertFalse((self.folder / 'fix-checks.json').exists())

    def test_the_command_refuses_before_any_check_starts(self):
        run = self.temp / 'run'
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors), self.assertRaises(SystemExit) as stop:
            main(['check-fixes', str(self.root), str(run), '--problems', 'mine.json'])
        self.assertEqual(stop.exception.code, 2)
        self.assertIn('the problems come from the issue ledger of the current draft, so --problems is not taken',
                      errors.getvalue())
        used = self.temp / 'used'
        used.mkdir()
        (used / 'notes.txt').write_text('kept')
        self.assertEqual(self.command(str(self.root), str(used)),
                         (2, PROG + f'{used} already holds files. Give a new run folder for each fix check.\n', {}))
        self.assertEqual([path.name for path in used.iterdir()], ['notes.txt'])
        status, errors, given = self.command(str(self.temp), str(run))
        self.assertEqual((status, given), (2, {}))
        self.assertTrue(errors.startswith(PROG + f'{self.temp} is not a manuscript workspace with a current draft'))
        # A draft made with no PDF has nothing for the engine to read.
        review = normalize_review(self.draft, copyedit_proposals(self.draft), 'second-copyedit')
        create_revision(self.root, review, automation_decisions(self.draft, review), 'unbuilt', head(self.root),
                        build=False)
        self.assertEqual(self.command(str(self.root), str(run)),
                         (2, PROG + 'Draft unbuilt has no built PDF, as it was made with --no-build. Check a draft '
                                    'that was built.\n', {}))
        self.assertFalse(run.exists())


if __name__ == '__main__':
    unittest.main()
