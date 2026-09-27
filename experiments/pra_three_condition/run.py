"""Bounded four-condition Terra pilot with shared initial reviews."""
import json
import shutil
import sys
import time
from pathlib import Path
from .prepare import ROOT,PAPERS
from .generate import basic,workspace_branch
from paper_workspace.annotations import verify_workspace
from paper_workspace.model_runtime import jsonl,require_subscription
from paper_workspace.reviewer import review
from paper_workspace.storage import read,write,digest

REPO=Path(__file__).resolve().parents[2]
CONDITIONS=['basic_one','basic_two','workspace','pra']
ORDERS={key:[CONDITIONS[i] for i in order] for key,order in zip(PAPERS,
    [(0,1,3,2),(1,2,0,3),(2,3,1,0),(3,0,2,1)])}
PROTOCOL={'provider':'codex','model':'gpt-5.6-terra','effort':'medium',
 'held_out_runs_authorized':False,'max_calls_per_condition':1,'observed_token_stop':250000,
 'call_timeout_seconds':900,'max_source_images':10,'image_budget_version':'evidence-v1',
 'max_total_model_calls':24,'observed_token_launch_stop':1800000,'no_retries':True,
 'version':'four-condition-v1','conditions':CONDITIONS,'label_orders':ORDERS,
 'passes':{'basic_one':1,'basic_two':2,'workspace':2,'pra':2},
 'shared_initial_drafts':[['basic_one','basic_two'],['workspace','pra']],
 'final_findings_each':5,'final_word_budget_each':900,'workspace_tool_allowance':[4,2],
 'external_requests_per_workspace_condition':6,'live_public_retrieval':True,
 'primary_assessment':'Consequential source-supported issues, unsupported premises, proportionality, retention, delivery and cost. Preference is secondary.'}


def usage(root=ROOT):
    scope=root/'panel' if root==ROOT else root
    rows=[r for p in scope.rglob('usage.jsonl') for r in jsonl(p)]
    attempts=list(scope.rglob('*.started.json'))
    return {'calls':len(attempts),'receipts':len(rows),'observed_tokens':sum(r.get('observed_tokens',0) for r in rows),
        'unknown':any(r.get('usage_unknown') for r in rows)}


def verify():
    for name,sha in read(ROOT/'seal.json')['files'].items():
        if digest(Path(name).read_bytes())!=sha:raise ValueError('Frozen input changed: '+name)


def budget(required):
    verify()
    u=usage()
    if u['unknown'] or u['calls']!=u['receipts']:raise ValueError('Unresolved model usage')
    if u['calls']+required>24 or u['observed_tokens']>=1800000:raise ValueError('Study model budget reached')
    if not 0<=time.time()-read(ROOT/'billing_confirmation.json')['checked_at']<86400:raise ValueError('Billing check expired')
    require_subscription(ROOT)


def seal():
    if (ROOT/'seal.json').exists():raise ValueError('Study already sealed')
    prior=read(ROOT/'prior-corpus.json')['papers']
    for key,item in PAPERS.items():
        paper=verify_workspace(ROOT/'inputs'/key/'workspace')
        if paper['statistics']['total_words']>25000:raise ValueError('Manuscript word limit exceeded')
        if any(item['doi']==r['doi'] or paper['id']==r['paper_id'] or paper['title'].casefold()==r['title'].casefold() for r in prior):
            raise ValueError('Selected paper overlaps prior corpus')
    write(ROOT/'protocol.json',PROTOCOL)
    files=[ROOT/'protocol.json',ROOT/'prior-corpus.json',ROOT/'preselection.json',ROOT/'prepared-papers.json',REPO/'docs/pra-four-condition-protocol.md']
    for directory in [REPO/'paper_workspace',Path(__file__).parent,ROOT/'inputs']:
        files += [p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    files += [REPO/'experiments/pra_debate_revision/evaluation.py',REPO/'experiments/pra_evidence_workflow/evaluation.py',REPO/'experiments/pra_prospective/core.py']
    write(ROOT/'seal.json',{'created_at':time.time(),'files':{str(p):digest(p.read_bytes()) for p in sorted(set(files))}})
    for p in files:
        if p.is_relative_to(REPO) and not p.is_relative_to(REPO/'runs'):
            dest=ROOT/'frozen-source'/p.relative_to(REPO)
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(p,dest)
    print('Four manuscripts and four-condition workflow sealed before generation',flush=True)


def stage(key,condition):
    base=ROOT/'inputs'/key
    out=ROOT/'panel'/key/condition
    if condition=='basic':basic(ROOT,base,out,PROTOCOL,budget)
    elif condition=='workspace':workspace_branch(ROOT,base,out,PROTOCOL,budget)
    elif condition=='pra':
        budget(2)
        if out.exists():raise ValueError('No repeat generation permitted')
        review(base/'workspace',out,ROOT/'billing_confirmation.json','2026-09-25',mode='panel',
            scaffold_root='/home/ty/Repos/paper-scaffold',domain_support=True,evidence_mode='current',
            shared_images=[Path(i['path']) for i in read(base/'images.json')],model='gpt-5.6-terra')
    elif condition=='judge':
        from .evaluate import evaluate
        parent=ROOT/'panel'/key
        evaluate(parent,base,PROTOCOL,budget,verify,lambda:usage(parent),ORDERS[key])
    print(json.dumps({'paper':key,'stage':condition,'usage':usage()}),flush=True)


def all_stages():
    for key in PAPERS:
        for condition in ('pra','workspace','basic','judge'):
            try:stage(key,condition)
            except Exception as exc:
                write(ROOT/'panel'/key/(condition+'-failure.json'),{'error':str(exc)})
                print(json.dumps({'paper':key,'stage':condition,'error':str(exc)}),flush=True)
                u=usage()
                if u['unknown'] or u['calls']!=u['receipts']:return
    write(ROOT/'completion.json',{'usage':usage(),'status':'bounded_stages_finished'})


if __name__=='__main__':
    if sys.argv[1]=='seal':seal()
    elif sys.argv[1]=='all':all_stages()
    else:stage(sys.argv[2],sys.argv[1])
