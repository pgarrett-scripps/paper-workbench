"""Command line for the Paper Workbench app.

``review`` runs one PeerReviewAgents review of a manuscript PDF and ``report``
re-renders a finished run, exactly as ``peerreview review`` and ``peerreview
report`` do. ``serve RUN`` opens that run in the viewer. ``import`` and
``verify`` make and check a manuscript workspace without a model call, and the
remaining commands revise and export a workspace.
"""
import argparse
import json
import sys
from pathlib import Path

from peerreviewagents.engine.storage import read

ENGINE_COMMANDS = ('review', 'report')
APP_COMMANDS = ('import', 'verify', 'port-scaffold', 'import-scaffold', 'revise', 'revision-loop',
                'revision-request', 'checkout-revision', 'export-revision', 'export-review', 'serve')
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
    p=sub.add_parser('import-scaffold',help='Import a Paper Scaffold source tree for editing')
    p.add_argument('source')
    p.add_argument('output')
    p.add_argument('--title')
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
                    'review and report run PeerReviewAgents, also available as peerreview review and peerreview report.')
    sub=parser.add_subparsers(dest='command',required=True)
    # Each engine command parses its own options, so its help comes from the engine.
    sub.add_parser('review',add_help=False,
        help='Review one manuscript PDF into a run folder (paper-workbench review -h for its options)')
    sub.add_parser('report',add_help=False,
        help='Re-render REVIEW.md and REVIEW.txt of a finished run, with no model call')
    add_app_subcommands(sub)
    return parser


def unfinished_run(argv):
    """The review folder ``report`` names when it holds a run that never finished, else ``None``.

    Only the run path is read here. Every option still goes to the engine.
    """
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('run',nargs='?')
    parser.add_argument('--workspace')
    parser.add_argument('--output-dir')
    known,_=parser.parse_known_args(argv)
    if not known.run:
        return None
    from peerreviewagents.plugin.server import RUN_DIRECTORY
    from .run_view import is_run
    path=Path(known.run).resolve()
    for review in (path,path/RUN_DIRECTORY):
        if is_run(review) and not (review/'protocol.json').is_file():
            return review
    return None


def run_engine(command,argv):
    """Run an engine command through the engine's own entry and return its exit status.

    The engine parses the options, so a new engine option reaches the review.
    """
    if command=='review':
        # Becomes peerreviewagents.cli.main.review_main(argv,prog='paper-workbench review').
        from peerreviewagents.plugin.starter import main as review_main
        return review_main(argv)
    review=unfinished_run(argv)
    if review:
        from .run_view import read_run
        recorded=read_run(review)
        print(f'The run in {review.parent} did not finish, so it has no review to report. '
              f'Status: {recorded["status"] or "not recorded"}. Cause: {recorded["error"] or "not recorded"}. '
              f'Open what it recorded with paper-workbench serve {review.parent}',file=sys.stderr)
        return 1
    # Becomes peerreviewagents.cli.main.report_main(argv).
    from peerreviewagents.cli.main import report
    return report(argv)


def dispatch(parser,args):
    """Run one parsed app command."""
    if args.command=='import':
        from peerreviewagents import import_paper
        paper=import_paper(args.pdf,args.workspace,args.xml,args.title,args.source_url,args.supplements)
        print(json.dumps(paper['statistics'],indent=2))
    elif args.command=='verify':
        from peerreviewagents.engine.annotations import verify_workspace
        paper=verify_workspace(args.workspace)
        print(json.dumps({'paper_id':paper['id'],'source_sha256':paper['source_sha256'],
                          'blocks':len(paper['blocks']),'status':'verified'},indent=2))
    elif args.command=='port-scaffold':
        from .scaffold_port import port_workspace
        print(port_workspace(args.workspace,args.output)['statistics'])
    elif args.command=='import-scaffold':
        from .scaffold_import import import_scaffold
        print(import_scaffold(args.source,args.output,args.title)['statistics'])
    elif args.command=='revise':
        from peerreviewagents.engine.annotations import normalize_review
        from .revisions import snapshot,automation_decisions,create_revision
        _,paper=snapshot(args.workspace,args.source_revision)
        review=normalize_review(paper,read(args.response),args.id)
        decisions=read(args.decisions) if args.decisions else automation_decisions(paper,review)
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
