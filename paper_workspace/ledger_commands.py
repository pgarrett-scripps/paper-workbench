"""``import-run`` and ``decide``: an engine review's problems in the current draft's ledger, and the author's decision on each.

``import-run WORKSPACE RUN`` adds the problems of one finished review of the
current draft to its issue ledger with ``record_problems``, which reads the run
only through the engine's ``read_run`` and ``problems_from_run``. Running it
again on the same run adds nothing. ``paper-workbench review`` does the same
when it reviews a manuscript workspace. ``decide WORKSPACE PROBLEM STATUS``
records the author's decision on one of those problems with ``decide``. A
refusal is one plain line and exit status 2, and changes nothing.
"""
import sys

from .revisions import AUTHOR_STATUSES, decide, record_problems

__all__ = ['add_subcommands', 'added_line', 'decide_problem', 'import_run']


def add_subcommands(sub):
    """Attach ``import-run`` and ``decide`` to a subparser group."""
    p = sub.add_parser('import-run', help="Add the problems of a finished review of the current draft to its "
                                          'issue ledger')
    p.add_argument('workspace', help='a manuscript workspace made with import-scaffold')
    p.add_argument('run', help='the run folder of a finished review of the current draft\'s built PDF')
    p = sub.add_parser('decide', help='Record the decision on one problem a review of the current draft raised')
    p.add_argument('workspace', help='a manuscript workspace made with import-scaffold')
    p.add_argument('problem', help='the problem id, such as original:first:i01')
    p.add_argument('status', choices=AUTHOR_STATUSES)
    p.add_argument('--rationale', help='why, which addressed and declined need')
    p.add_argument('--note', help='a note for the next fix check and the next draft')
    return sub


def added_line(result):
    """One line saying what one review added to the ledger of the current draft."""
    if result['already']:
        return f'the review at {result["run"]} is already in the ledger of draft {result["draft"]}, so nothing was added.'
    added = result['added']
    named = f', {added[0]} to {added[-1]}' if len(added) > 1 else f', {added[0]}' if added else ''
    lines = [f'added {len(added)} problems from {result["run"]} to the ledger of draft {result["draft"]}{named}.']
    if result['left_out']:
        lines.append(f'{result["left_out"]} of its issues quote no passage or have no severity the engine '
                     'takes, so they are not problems a fix check can read and were left out.')
    if result['not_publishable_reasons']:
        lines.append('The review is not publishable as a peer review: '
                     + ', and '.join(reason.rstrip('.') for reason in result['not_publishable_reasons']) + '.')
    return ' '.join(lines)


def import_run(prog, workspace, run):
    """Run ``import-run`` and return its exit status."""
    try:
        result = record_problems(workspace, run)
    except ValueError as exc:
        print(f'{prog}: {exc}', file=sys.stderr)
        return 2
    print(f'{prog}: {added_line(result)}', file=sys.stderr)
    for problem in result['added']:
        print(problem)
    return 0


def decide_problem(prog, workspace, problem, status, rationale=None, note=None):
    """Run ``decide`` and return its exit status."""
    try:
        row = decide(workspace, problem, status, rationale, note)
    except ValueError as exc:
        print(f'{prog}: {exc}', file=sys.stderr)
        return 2
    print(f'{prog}: problem {row["id"]} {STANDS[row["author"]["status"]]}', file=sys.stderr)
    return 0


#: What each decision means for the problem, as ``decide`` says it.
STANDS = {'open': 'is open.',
          'addressed': 'is marked addressed, and stays open until a fix check of a later draft finds it fixed.',
          'declined': 'is declined, and no fix check takes it.'}
