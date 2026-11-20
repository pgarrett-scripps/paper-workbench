"""``paper-workbench check-fixes``: the engine's fix check of a workspace's current draft, recorded in its ledger.

The open problems of the current draft's issue ledger are written as the
engine's problems file inside the run folder, the engine checks the draft's
built PDF against them through ``check_fixes_main``, and what
``read_fix_check`` reads back is recorded with ``record_fix_checks``. A run
that is blocked or stopped, or that cannot be read whole, changes nothing in
the ledger, and the command says why.
"""
import argparse
import sys
from pathlib import Path

from peerreviewagents import ISSUE_SEVERITIES, check_fixes_main, check_fixes_parser, read_fix_check
from peerreviewagents.names import FIX_VERDICTS, PROBLEMS_SCHEMA_VERSION
from peerreviewagents.problems import MAX_PROBLEMS, normalize, problems_in_document
from peerreviewagents.workspace import write_json

from .revisions import head, ledger_of, open_problems, record_fix_checks, snapshot
from .workspace_review import WorkspaceRefused, with_manuscript

PROG = 'paper-workbench check-fixes'
# The problems file the app writes for the engine, at the top of the run folder.
PROBLEMS = 'problems.json'


def parser(prog=PROG):
    """The engine's check-fixes parser, taking a workspace for the PDF and writing its own problems file."""
    built = check_fixes_parser(prog=prog)
    built.description = ('Check the current draft of a manuscript workspace against the open problems in its '
                         'issue ledger, with headless Claude Code agents, and record each '
                         'verdict in the ledger. Nothing new is raised.')
    built.epilog = (f'The problems file is written from the ledger to RUN/{PROBLEMS}: every open problem the '
                    'draft has no verdict on yet, in severity order. A check that is blocked or stopped, or '
                    'that cannot be read whole, records nothing. A problem the check did not reach is recorded '
                    'as not checked, and the next check of the same draft, into a new run folder, takes it again.')
    # The engine's parser offers no public way to change an argument's help, so each action is found by name.
    for action in built._actions:
        if action.dest == 'workspace':
            action.help = 'a manuscript workspace, whose current draft is checked from its built PDF'
        elif action.dest == 'output':
            action.help = 'a new run folder for this check'
        elif action.dest == 'problems':
            action.required = False
            action.help = argparse.SUPPRESS
    return built


def problem_rows(ledger, draft):
    """The problems a check of ``draft`` takes from its ledger, and a line for each one left out.

    Every open problem with no verdict from a check of this draft goes, in
    severity order, up to the engine's limit for one problems file. A problem
    the engine would refuse, such as one with no severity, is left out and
    named, so it does not stop the check of the rest.
    """
    rows, notes = [], []
    for row in open_problems(ledger, draft):
        reasons = problems_in_document([row], f'problem {row["id"]}')
        if reasons:
            notes.append(f'problem {row["id"]} is left out of this check: {", and ".join(reasons)}.')
        else:
            rows.append(row)
    rows.sort(key=lambda row: ISSUE_SEVERITIES.index(row['severity']))
    if len(rows) > MAX_PROBLEMS:
        notes.append(f'{len(rows) - MAX_PROBLEMS} open problems wait for a later check, as one check takes '
                     f'at most {MAX_PROBLEMS}.')
    return rows[:MAX_PROBLEMS], notes


def prepare(argv, command, args):
    """The draft, the run folder and the engine's arguments, with the problems file written into the run folder.

    Raises :class:`WorkspaceRefused` with the reason when no check can start,
    before anything is written.
    """
    root = Path(args.workspace).resolve()
    try:
        draft = head(root)['revision_id']
        folder, _ = snapshot(root, draft)
    except (ValueError, OSError) as exc:
        raise WorkspaceRefused(f'{root} is not a manuscript workspace with a current draft: {exc}') from exc
    rows, notes = problem_rows(ledger_of(folder), draft)
    for note in notes:
        print(f'{PROG}: {note}', file=sys.stderr)
    if not rows:
        raise WorkspaceRefused(f'Draft {draft} has no open problem left to check.')
    pdf = folder / 'artifacts' / 'paper.pdf'
    if not pdf.is_file():
        raise WorkspaceRefused(f'Draft {draft} has no built PDF, as it was made with --no-build. '
                               'Check a draft that was built.')
    run = Path(args.output).resolve()
    if run.exists() and (not run.is_dir() or {child.name for child in run.iterdir()} - {PROBLEMS}):
        raise WorkspaceRefused(f'{run} already holds files. Give a new run folder for each fix check.')
    engine = with_manuscript(command, argv, args, str(pdf))
    path = run / PROBLEMS
    write_json(path, normalize({'schema_version': PROBLEMS_SCHEMA_VERSION, 'problems': rows}))
    return root, draft, run, [*engine, '--problems', str(path)]


def check_fixes(argv):
    """Run one fix check of a workspace's current draft, record it in the ledger, and return the exit status."""
    argv = list(argv)
    command = parser()
    args = command.parse_args(argv)
    if args.problems is not None:
        command.error('the problems come from the issue ledger of the current draft, so --problems is not taken')
    try:
        root, draft, run, engine = prepare(argv, command, args)
    except WorkspaceRefused as exc:
        # Nothing was run and no usage was spent, which is the engine's code 2.
        print(f'{PROG}: {exc}', file=sys.stderr)
        return 2
    status = check_fixes_main(engine, prog=PROG)
    try:
        ledger = record_fix_checks(root, draft, read_fix_check(run))
    except ValueError as exc:
        print(f'{PROG}: {exc} The ledger of draft {draft} is unchanged.', file=sys.stderr)
        return status or 1
    verdicts = [check['verdict'] for row in ledger for check in row['fix_checks'] if check['run'] == str(run)]
    counts = ', '.join(f'{verdict} {verdicts.count(verdict)}' for verdict in FIX_VERDICTS)
    print(f'{PROG}: recorded on draft {draft}: {counts}, not checked {verdicts.count(None)}.', file=sys.stderr)
    return status
