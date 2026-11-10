"""Command line for the Paper Workbench app.

The workspace, revision and export commands run here. The engine commands
(import, verify, add-review, review, report and the rest) pass through to
peerreviewagents.engine, which also serves them as ``peerreview <command>``.
"""
import argparse
import json

from peerreviewagents.engine.__main__ import (
    COMMANDS as ENGINE_COMMANDS, MODEL_HELP, add_model_arguments, add_subcommands,
    dispatch as engine_dispatch, resolve_model)
from peerreviewagents.engine.storage import read

APP_COMMANDS = ('port-scaffold', 'import-scaffold', 'revise', 'revision-loop', 'revision-request',
                'checkout-revision', 'export-revision', 'export-review', 'serve')
__all__ = ['APP_COMMANDS', 'ENGINE_COMMANDS', 'MODEL_HELP', 'add_model_arguments',
           'build_parser', 'main', 'resolve_model']


def add_app_subcommands(sub):
    """Attach the workspace, revision and export commands to a subparser group."""
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
    p.add_argument('--scaffold-root',help='Record offline prose and readability checks before and after edits')
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
    p=sub.add_parser('serve',help='Open the loopback review and revision viewer')
    p.add_argument('workspace')
    p.add_argument('--port',type=int,default=38744)
    return sub


def build_parser(prog='paper-workbench'):
    parser=argparse.ArgumentParser(prog=prog,
        description='Paper Workbench: review, revise and export a local annotated manuscript workspace. '
                    'Engine commands run peerreviewagents.engine, also available as peerreview <command>.')
    sub=parser.add_subparsers(dest='command',required=True)
    add_app_subcommands(sub)
    add_subcommands(sub)
    return parser


def dispatch(parser,args):
    """Run one parsed app command, or hand an engine command to the engine."""
    if args.command in ENGINE_COMMANDS:
        engine_dispatch(parser,args)
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
            build=not args.no_build,scaffold_root=args.scaffold_root))
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


def main(argv=None):
    parser=build_parser()
    dispatch(parser,parser.parse_args(argv))


if __name__=='__main__':
    main()
