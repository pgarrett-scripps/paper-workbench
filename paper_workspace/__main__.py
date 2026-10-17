import argparse
from pathlib import Path
from .storage import read
from .models import DEFAULT_MODELS, SUBSCRIPTION_MODELS, provider_for


MODEL_HELP=('Exact model ID. Without it, the default for --provider is used: '+
            ', '.join(f'{model} for {provider}' for provider,model in DEFAULT_MODELS.items())+'.')


def add_model_arguments(parser):
    parser.add_argument('--provider',choices=tuple(DEFAULT_MODELS),help='Subscription transport (default codex)')
    parser.add_argument('--model',choices=SUBSCRIPTION_MODELS,help=MODEL_HELP)


def resolve_model(parser,args):
    """Fill the provider default and reject a model that belongs to another provider."""
    if args.model is None:
        args.model=DEFAULT_MODELS[args.provider or 'codex']
    elif args.provider and provider_for(args.model)!=args.provider:
        parser.error(f'{args.model} is not a {args.provider} model')


def main():
    parser=argparse.ArgumentParser(description='Build and inspect a local annotated manuscript workspace')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('port-scaffold')
    p.add_argument('workspace')
    p.add_argument('output')
    p=sub.add_parser('import-scaffold')
    p.add_argument('source')
    p.add_argument('output')
    p.add_argument('--title')
    p=sub.add_parser('revise')
    p.add_argument('workspace')
    p.add_argument('response')
    p.add_argument('--id',required=True)
    p.add_argument('--decisions',help='Explicit accepted edits. Otherwise apply the conservative automatic policy.')
    p.add_argument('--source-revision',required=True,help='Revision reviewed, or original')
    p.add_argument('--expected-version',type=int,required=True)
    p.add_argument('--no-build',action='store_true',help='Create a source-only draft without a PDF build')
    p=sub.add_parser('revision-loop')
    p.add_argument('workspace')
    p.add_argument('--id',required=True)
    p.add_argument('--max-rounds',type=int,default=2)
    p.add_argument('--max-edits',type=int,default=10)
    p.add_argument('--no-build',action='store_true')
    p.add_argument('--scaffold-root',help='Record offline prose and readability checks before and after edits')
    p=sub.add_parser('revision-request')
    p.add_argument('workspace')
    p=sub.add_parser('checkout-revision')
    p.add_argument('workspace')
    p.add_argument('revision')
    p.add_argument('--expected-version',type=int,required=True)
    p=sub.add_parser('export-revision')
    p.add_argument('workspace')
    p.add_argument('revision')
    p.add_argument('output')
    p.add_argument('--scaffold-root',required=True)
    p.add_argument('--python',help='Python interpreter with Paper Scaffold export dependencies')
    p=sub.add_parser('export-review')
    p.add_argument('workspace')
    p.add_argument('revision')
    p.add_argument('clean_export')
    p.add_argument('output')
    p=sub.add_parser('import')
    p.add_argument('pdf')
    p.add_argument('output')
    p.add_argument('--xml')
    p.add_argument('--title')
    p.add_argument('--source-url',default='')
    p.add_argument('--supplements')
    p=sub.add_parser('serve')
    p.add_argument('workspace')
    p.add_argument('--port',type=int,default=38744)
    p=sub.add_parser('add-review')
    p.add_argument('workspace')
    p.add_argument('response')
    p.add_argument('--id',required=True)
    p=sub.add_parser('verify')
    p.add_argument('workspace')
    p=sub.add_parser('result-map')
    p.add_argument('workspace')
    p.add_argument('--output',required=True)
    p=sub.add_parser('review')
    p.add_argument('workspace')
    p.add_argument('output')
    p.add_argument('--billing-confirmation',required=True)
    p.add_argument('--literature-cutoff',required=True,help='Latest eligible publication date, YYYY-MM-DD')
    p.add_argument('--mode',choices=('ensemble','independent','plain','workspace','panel','self-revision'),default='ensemble')
    p.add_argument('--reviewers',type=int,default=2,help='Independent discovery reviewers for ensemble mode, from 1 to 16 (default 2)')
    p.add_argument('--token-budget',type=int,default=750000,help='Ensemble observed-token launch ceiling, not a hard cap on a running call')
    add_model_arguments(p)
    p.add_argument('--source-image',action='append',default=[],help='Original manuscript figure page to attach, at most three')
    p.add_argument('--scaffold-root',help='Use offline advisory checks from this Paper Scaffold checkout')
    p.add_argument('--legacy-tools',action='store_true',help='Use the older fixed tool profile without domain skills')
    p.add_argument('--evidence-mode',choices=('current','historical'),default='current',help='Current records or cutoff-restricted historical evidence')
    p.add_argument('--source-packet',help='Frozen source cache for comparison runs, with live source retrieval disabled')
    p.add_argument('--historical-snapshots',help='Curated, hash-verified registration snapshot directory')
    p=sub.add_parser('investigate',help='Run one focused evidence investigation with at most two tools')
    p.add_argument('workspace')
    p.add_argument('output')
    p.add_argument('--question',required=True)
    p.add_argument('--block',action='append',required=True,help='Whole source block to include, repeat up to sixteen times')
    p.add_argument('--billing-confirmation',required=True)
    p.add_argument('--literature-cutoff',required=True)
    add_model_arguments(p)
    p=sub.add_parser('confirm-billing',help='Record that this Claude subscription cannot buy paid extra usage')
    p.add_argument('output')
    p.add_argument('--provider',choices=('claude-code',),required=True)
    p.add_argument('--extra-usage-disabled',action='store_true',required=True,
                   help='Confirm that extra usage is turned off in Claude settings. Valid for 24 hours.')
    p=sub.add_parser('checks')
    p.add_argument('workspace')
    p.add_argument('--scaffold-root',required=True)
    p.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.command in ('review','investigate'):
        resolve_model(parser,args)
    if args.command=='investigate':
        from .focused_investigation import investigate
        memo=investigate(args.workspace,args.output,args.billing_confirmation,args.literature_cutoff,
                         args.question,args.block,model=args.model)
        print({'ready_for_adjudication':memo['ready_for_adjudication'],'output':str(Path(args.output)/'memo.json')})
    elif args.command=='port-scaffold':
        from .scaffold_port import port_workspace
        print(port_workspace(args.workspace,args.output)['statistics'])
    elif args.command=='import-scaffold':
        from .scaffold_import import import_scaffold
        print(import_scaffold(args.source,args.output,args.title)['statistics'])
    elif args.command=='revise':
        from .revisions import snapshot,automation_decisions,create_revision
        from .annotations import normalize_review
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
        import json
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
    elif args.command=='import':
        from .ingest import import_paper
        paper=import_paper(args.pdf,args.output,args.xml,args.title,args.source_url,args.supplements)
        print(paper['title'])
        print(paper['statistics'])
    elif args.command=='serve':
        from .server import serve
        serve(args.workspace,args.port)
    elif args.command=='add-review':
        from .annotations import save_review
        print(save_review(args.workspace,read(args.response),args.id)['annotation_counts'])
    elif args.command=='review':
        import datetime
        datetime.date.fromisoformat(args.literature_cutoff)
        from .reviewer import review
        if args.mode!='ensemble' and (args.reviewers!=2 or args.token_budget!=750000):
            parser.error('--reviewers and --token-budget apply only to ensemble mode')
        print(review(args.workspace,args.output,args.billing_confirmation,args.literature_cutoff,args.mode,args.scaffold_root,
                     domain_support=not args.legacy_tools,evidence_mode=args.evidence_mode,source_packet=args.source_packet,
                     historical_snapshots=args.historical_snapshots,model=args.model,reviewers=args.reviewers,
                     token_budget=args.token_budget,shared_images=args.source_image))
    elif args.command=='confirm-billing':
        from .billing import claude_billing_record
        from .model_runtime import auth_status
        from .storage import write
        record=claude_billing_record(auth_status(args.provider))
        write(args.output,record)
        print({'output':args.output,'subscription_type':record['subscription_type'],'valid_hours':24})
    elif args.command=='checks':
        from .scaffold_checks import build_report,compact_summary
        from .storage import write
        report=build_report(args.workspace,args.scaffold_root)
        write(args.output,report)
        print(compact_summary(report))
    elif args.command=='result-map':
        from .annotations import verify_workspace
        from .result_map import build_result_map
        from .storage import write
        result = build_result_map(verify_workspace(args.workspace))
        write(args.output,result)
        print(result['coverage'])
    else:
        from .annotations import verify_workspace
        print('Verified manuscript '+verify_workspace(args.workspace)['id'])


if __name__=='__main__':
    main()
