"""``import-run``, ``decide`` and ``revise``: the author's side of the review loop on a manuscript workspace.

``import-run WORKSPACE RUN`` adds the problems of one finished review of the
current draft to its issue ledger with ``record_problems``, which reads the run
only through the engine's ``read_run`` and ``problems_from_run``. Running it
again on the same run adds nothing. ``paper-workbench review`` does the same
when it reviews a manuscript workspace. ``decide WORKSPACE PROBLEM STATUS``
records the author's decision on one open or declined problem in the current
draft's ledger with ``decide``, including a problem carried from an earlier
draft that a fix check found not fixed. ``revise WORKSPACE PROJECT --id ID``
makes the next draft from the author's edited Paper Scaffold project with
``revise``, which builds its PDF and freezes the current draft's ledger into
it. A refusal is one plain line and exit status 2, and changes nothing.
"""
import sys

from .revisions import AUTHOR_STATUSES, decide, latest_decision, record_problems, revise

__all__ = ['add_subcommands', 'added_line', 'decide_problem', 'import_run', 'revise_draft']


def add_subcommands(sub):
    """Attach ``import-run``, ``decide`` and ``revise`` to a subparser group."""
    p = sub.add_parser('import-run', help="Add the problems of a finished review of the current draft to its "
                                          'issue ledger')
    p.add_argument('workspace', help='a manuscript workspace made with import-scaffold')
    p.add_argument('run', help='the run folder of a finished review of the current draft\'s built PDF')
    p = sub.add_parser('decide', help='Record the decision on one open or declined problem in the current '
                                      "draft's issue ledger, whichever draft raised it")
    p.add_argument('workspace', help='a manuscript workspace made with import-scaffold')
    p.add_argument('problem', help='the problem id, such as original:first:i01')
    p.add_argument('status', choices=AUTHOR_STATUSES)
    p.add_argument('--rationale', help='why, which addressed and declined need')
    p.add_argument('--note', help='a note for the next fix check and the next draft')
    p = sub.add_parser('revise', help="Make the next draft from the author's edited Paper Scaffold project: "
                                      'build its PDF and freeze the current ledger into it')
    p.add_argument('workspace', help='a manuscript workspace made with import-scaffold')
    p.add_argument('project', help='the Paper Scaffold project folder the workspace was imported from, '
                                   'with the edits made in it')
    p.add_argument('--id', required=True, help='the new draft\'s id, such as draft-2')
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
    decision = latest_decision(row)
    print(f'{prog}: problem {row["id"]}, decided on draft {decision["draft"]}, {STANDS[decision["status"]]}',
          file=sys.stderr)
    return 0


def revise_draft(prog, workspace, project, revision_id):
    """Run ``revise`` and return its exit status."""
    try:
        record = revise(workspace, project, revision_id)
    except ValueError as exc:
        print(f'{prog}: {exc}', file=sys.stderr)
        return 2
    print(f'{prog}: made draft {record["id"]} from {record["edited_from"]}, with the ledger of draft '
          f'{record["parent"]} frozen into it, and it is the current draft.', file=sys.stderr)
    print(record['id'])
    return 0


#: What each decision means for the problem, as ``decide`` says it.
STANDS = {'open': 'is open.',
          'addressed': 'is marked addressed, and stays open until a fix check of a later draft finds it fixed.',
          'declined': 'is declined, and no fix check takes it.'}
