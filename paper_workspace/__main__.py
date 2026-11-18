"""Command line for the Paper Workbench app.

``review`` runs one PeerReviewAgents review of a manuscript PDF and ``report``
renders the reports of a run, finished or stopped, exactly as ``peerreview
review`` and ``peerreview report`` do. ``review`` also takes a Paper Scaffold
workspace folder in place of the PDF, and reviews its built PDF with its code. ``serve RUN`` opens that run in the viewer.
``review`` of a manuscript workspace reviews its current draft and adds the
problems of the finished review to that draft's issue ledger, as
``import-run`` does for a run folder. ``decide`` records the author's
decision on one of them. ``check-fixes`` runs the engine's fix check of a
manuscript workspace's current draft against the open problems in its issue
ledger, and records the verdicts there. ``import`` and ``verify`` make and
check a manuscript workspace without a model call, and the remaining
commands revise and export a workspace.
"""
import argparse
import json
import sys

from peerreviewagents.workspace import read_json

ENGINE_COMMANDS = ('review', 'check-fixes', 'report')
APP_COMMANDS = ('import', 'verify', 'port-scaffold', 'import-scaffold', 'import-run', 'decide', 'revise',
                'revision-loop', 'revision-request', 'checkout-revision', 'export-revision', 'export-review', 'serve')
__all__ = ['APP_COMMANDS', 'ENGINE_COMMANDS', 'build_parser', 'main']


def add_app_subcommands(sub):
    """Attach the workspace, revision and export commands to a subparser group."""
    p=sub.add_parser('import',help='Import a manuscript PDF into a workspace, with no model call')
    p.add_argument('pdf')
    p.add_argument('workspace')
    p.add_argument('--xml',help='Publisher JATS XML for the text and references')
    p.add_argument('--title')
    p.add_argument('--source-url',default='')
    p.add_argument('--supplements',help='Folder of supplementary files')
    p=sub.add_parser('verify',help='Check that a workspace still matches its manifest')
    p.add_argument('workspace')
    p=sub.add_parser('port-scaffold',help='Make a Paper Scaffold reading copy of a review workspace')
    p.add_argument('workspace')
    p.add_argument('output')
    p=sub.add_parser('import-scaffold',help='Import a Paper Scaffold source tree for editing, with its built PDF '
                                            'as the original draft\'s while it matches the source')
    p.add_argument('source')
    p.add_argument('output')
    p.add_argument('--title')
    from .ledger_commands import add_subcommands
    add_subcommands(sub)
    p=sub.add_parser('revise',help='Create a source revision from a review response')
    p.add_argument('workspace')
    p.add_argument('response')
    p.add_argument('--id',required=True)
    p.add_argument('--decisions',help='Explicit accepted edits. Otherwise apply the conservative automatic policy.')
    p.add_argument('--source-revision',required=True,help='Revision reviewed, or original')
    p.add_argument('--expected-version',type=int,required=True)
    p.add_argument('--no-build',action='store_true',help='Create a source-only draft without a PDF build')
    p=sub.add_parser('revision-loop',help='Run bounded copyediting rounds on a workspace')
    p.add_argument('workspace')
    p.add_argument('--id',required=True)
    p.add_argument('--max-rounds',type=int,default=2)
    p.add_argument('--max-edits',type=int,default=10)
    p.add_argument('--no-build',action='store_true')
    p=sub.add_parser('revision-request',help='Print the revision request an editing agent would receive')
    p.add_argument('workspace')
    p=sub.add_parser('checkout-revision',help='Make a saved revision the current head')
    p.add_argument('workspace')
    p.add_argument('revision')
    p.add_argument('--expected-version',type=int,required=True)
    p=sub.add_parser('export-revision',help='Export a revision through Paper Scaffold tools')
    p.add_argument('workspace')
    p.add_argument('revision')
    p.add_argument('output')
    p.add_argument('--scaffold-root',required=True)
    p.add_argument('--python',help='Python interpreter with Paper Scaffold export dependencies')
    p=sub.add_parser('export-review',help='Export revision differences into a Word review copy')
    p.add_argument('workspace')
    p.add_argument('revision')
    p.add_argument('clean_export')
    p.add_argument('output')
    p=sub.add_parser('serve',help='Open the loopback viewer on a workspace or a run folder')
    p.add_argument('workspace',help='A manuscript workspace, or a run folder from review')
    p.add_argument('--port',type=int,default=38744)
    return sub


def build_parser(prog='paper-workbench'):
    parser=argparse.ArgumentParser(prog=prog,
        description='Paper Workbench: review, revise and export a local annotated manuscript. '
                    'review, check-fixes and report run PeerReviewAgents, also available as peerreview review, '
                    'peerreview check-fixes and peerreview report.')
    sub=parser.add_subparsers(dest='command',required=True)
    # Each engine command parses its own options, so its help comes from the engine.
    sub.add_parser('review',add_help=False,
        help='Review one manuscript PDF, or a Paper Scaffold workspace with its code, into a run folder '
             '(paper-workbench review -h for its options)')
    sub.add_parser('check-fixes',add_help=False,
        help='Check the current draft of a manuscript workspace against the open problems in its issue ledger, '
             'and record the verdicts there (paper-workbench check-fixes -h for its options)')
    sub.add_parser('report',add_help=False,
        help='Render REVIEW.md and REVIEW.txt of a run, finished or stopped, with no model call')
    add_app_subcommands(sub)
    return parser


def run_engine(command,argv):
    """Run an engine command through the engine's public entry and return its exit status.

    The engine parses the options, so a new engine option reaches the review.
    A Paper Scaffold workspace stands where the PDF does, and
    ``workspace_review`` turns it into the engine's arguments first.
    ``check-fixes`` takes a manuscript workspace, and ``fix_check`` writes
    the problems from its ledger and records what the engine found. A review
    of a manuscript workspace adds the problems of the finished review to its
    current draft's ledger, and says why when it adds none.
    """
    if command=='check-fixes':
        from .fix_check import check_fixes
        return check_fixes(argv)
    if command=='review':
        from peerreviewagents import review_main
        from .ledger_commands import added_line
        from .revisions import record_problems
        from .workspace_review import WorkspaceRefused, engine_argv, ledger_target
        prog='paper-workbench review'
        try:
            engine,note=engine_argv(argv)
            target=ledger_target(argv)
        except WorkspaceRefused as exc:
            # Nothing was written and no usage was spent, which is the engine's code 2.
            print(f'{prog}: {exc}',file=sys.stderr)
            return 2
        if note:
            print(note,file=sys.stderr)
        status=review_main(engine,prog=prog)
        if target is None:
            return status
        try:
            result=record_problems(*target)
        except ValueError as exc:
            print(f'{prog}: no problems were added to the ledger: {exc}',file=sys.stderr)
            return status or 1
        print(f'{prog}: {added_line(result)}',file=sys.stderr)
        return status
    from peerreviewagents import report_main
    return report_main(argv,prog='paper-workbench report')


def dispatch(parser,args):
    """Run one parsed app command."""
    if args.command=='import':
        from peerreviewagents import import_paper
        paper=import_paper(args.pdf,args.workspace,args.xml,args.title,args.source_url,args.supplements)
        print(json.dumps(paper['statistics'],indent=2))
    elif args.command=='verify':
        from peerreviewagents import verify_workspace
        from .run_view import source_sha256
        paper=verify_workspace(args.workspace)
        print(json.dumps({'paper_id':paper.paper_id,'source_sha256':source_sha256(paper),
                          'pieces':len(paper.rows),
                          'lines':{name:paper.line_count(name) for name in paper.document_names()},
                          'status':'verified'},indent=2))
    elif args.command=='port-scaffold':
        from .scaffold_port import port_workspace
        print(port_workspace(args.workspace,args.output)['statistics'])
    elif args.command=='import-scaffold':
        from .workspace_review import import_project
        manifest,note=import_project(args.source,args.output,args.title)
        print(manifest['statistics'])
        if note:
            print(f'paper-workbench import-scaffold: {note}',file=sys.stderr)
    elif args.command=='import-run':
        from .ledger_commands import import_run
        return import_run('paper-workbench import-run',args.workspace,args.run)
    elif args.command=='decide':
        from .ledger_commands import decide_problem
        return decide_problem('paper-workbench decide',args.workspace,args.problem,args.status,
                              args.rationale,args.note)
    elif args.command=='revise':
        from peerreviewagents.workspace import normalize_review
        from .revisions import snapshot,automation_decisions,create_revision
        _,paper=snapshot(args.workspace,args.source_revision)
        review=normalize_review(paper,read_json(args.response),args.id)
        decisions=read_json(args.decisions) if args.decisions else automation_decisions(paper,review)
        print(create_revision(args.workspace,review,decisions,args.id,
            {'revision_id':args.source_revision,'version':args.expected_version},build=not args.no_build))
    elif args.command=='revision-loop':
        from .revisions import run_loop
        print(run_loop(args.workspace,args.id,max_rounds=args.max_rounds,max_edits=args.max_edits,
            build=not args.no_build))
    elif args.command=='revision-request':
        from .revisions import agent_request
        print(json.dumps(agent_request(args.workspace),indent=2,ensure_ascii=False))
    elif args.command=='checkout-revision':
        from .revisions import head,checkout
        expected=head(args.workspace)
        expected['version']=args.expected_version
        print(checkout(args.workspace,args.revision,expected))
    elif args.command=='export-revision':
        from .scaffold_export import export_revision
        print(export_revision(args.workspace,args.revision,args.output,args.scaffold_root,args.python))
    elif args.command=='export-review':
        from .word_review import export_review
        print(export_review(args.workspace,args.revision,args.clean_export,args.output))
    elif args.command=='serve':
        from .server import serve
        serve(args.workspace,args.port)
    else:
        parser.error(f'unknown command {args.command}')
    return 0


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    from .run_view import RunError
    try:
        if argv and argv[0] in ENGINE_COMMANDS:
            return run_engine(argv[0],argv[1:])
        parser=build_parser()
        return dispatch(parser,parser.parse_args(argv))
    except RunError as exc:
        # A run the viewer or the report cannot open is a plain message, not a traceback.
        print(f'paper-workbench: {exc}',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
