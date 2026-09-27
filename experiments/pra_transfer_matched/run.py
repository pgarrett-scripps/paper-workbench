"""Frozen two-paper, matched-pass development comparison."""
import json
import shutil
import sys
import time
from pathlib import Path
from .prepare import ROOT, PAPERS
from .evaluate import evaluate
from paper_workspace.annotations import verify_workspace
from paper_workspace.model_runtime import jsonl, require_subscription
from paper_workspace.reviewer import review
from paper_workspace.storage import read, write, digest

REPO=Path(__file__).resolve().parents[2]
PROTOCOL={'provider':'codex','model':'gpt-5.6-terra','effort':'medium',
 'held_out_runs_authorized':False,'max_calls_per_condition':1,'observed_token_stop':200000,
 'call_timeout_seconds':900,'max_source_images':10,'image_budget_version':'evidence-v1',
 'max_total_model_calls':10,'observed_token_launch_stop':850000,'no_retries':True,
 'version':'transfer-matched-v1','conditions':['two-pass self-revision','investigator plus debate'],
 'generation_calls_each':2,'tool_allowance_each':[4,2],'final_findings_each':5,
 'primary_assessment':'Consequential source-supported issues, unsupported premises, proportionality, retention, delivery and cost. Preference is secondary.'}


def usage(root=ROOT):
    rows=[r for p in (root/'panel' if root==ROOT else root).rglob('usage.jsonl') for r in jsonl(p)]
    attempts=list((root/'panel' if root==ROOT else root).rglob('*.started.json'))
    return {'calls':len(attempts),'receipts':len(rows),'observed_tokens':sum(r.get('observed_tokens',0) for r in rows),
            'unknown':any(r.get('usage_unknown') for r in rows)}


def verify():
    for name,sha in read(ROOT/'seal.json')['files'].items():
        if digest(Path(name).read_bytes())!=sha:
            raise ValueError('Frozen input changed: '+name)


def budget(required):
    verify()
    u=usage()
    if u['unknown'] or u['calls']!=u['receipts']:
        raise ValueError('Unresolved model usage')
    if u['calls']+required>10 or u['observed_tokens']>=850000:
        raise ValueError('Study model budget reached')
    if not 0<=time.time()-read(ROOT/'billing_confirmation.json')['checked_at']<86400:
        raise ValueError('Billing check expired')
    require_subscription(ROOT)


def seal():
    if (ROOT/'seal.json').exists():
        raise ValueError('Study already sealed')
    prior=read(ROOT/'prior-corpus.json')['papers']
    for key,item in PAPERS.items():
        paper=verify_workspace(ROOT/'inputs'/key/'workspace')
        if any(item['doi']==r['doi'] or paper['id']==r['paper_id'] or paper['title'].casefold()==r['title'].casefold() for r in prior):
            raise ValueError('Selected paper overlaps prior corpus')
    write(ROOT/'protocol.json',PROTOCOL)
    files=[ROOT/'protocol.json',ROOT/'prior-corpus.json',ROOT/'preselection.json',
           REPO/'docs/pra-transfer-matched-protocol.md']
    for d in [REPO/'paper_workspace',Path(__file__).parent,ROOT/'inputs',ROOT/'packets']:
        files += [p for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    files += [REPO/'experiments/pra_debate_revision/evaluation.py',REPO/'experiments/pra_evidence_workflow/evaluation.py',REPO/'experiments/pra_prospective/core.py']
    write(ROOT/'seal.json',{'created_at':time.time(),'files':{str(p):digest(p.read_bytes()) for p in sorted(set(files))}})
    for p in files:
        if p.is_relative_to(REPO) and not p.is_relative_to(REPO/'runs'):
            dest=ROOT/'frozen-source'/p.relative_to(REPO)
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(p,dest)
    print('Both manuscripts and workflow sealed before any model generation',flush=True)


def generate(key,condition):
    budget(2)
    out=ROOT/'panel'/key/condition
    if out.exists():
        raise ValueError('No repeat generation permitted')
    base=ROOT/'inputs'/key
    review(base/'workspace',out,ROOT/'billing_confirmation.json','2026-09-25',
           mode='self-revision' if condition=='single' else 'panel',
           scaffold_root='/home/ty/Repos/paper-scaffold',domain_support=True,evidence_mode='current',
           source_packet=ROOT/'packets'/key,shared_images=[Path(i['path']) for i in read(base/'images.json')],model='gpt-5.6-terra')
    print(json.dumps({'paper':key,'condition':condition,'usage':usage()}),flush=True)


def judge(key):
    out=ROOT/'panel'/key
    evaluate(out,ROOT/'inputs'/key,ROOT/'packets'/key,PROTOCOL,budget,verify,lambda:usage(out))


def all_stages():
    for key in PAPERS:
        for condition in ('single','pra'):
            try:
                generate(key,condition)
            except Exception as exc:
                write(ROOT/'panel'/key/(condition+'-failure.json'),{'error':str(exc)})
                print(json.dumps({'paper':key,'condition':condition,'error':str(exc)}),flush=True)
                if usage()['unknown']:
                    return
        if all((ROOT/'panel'/key/c/'progress.json').exists() and read(ROOT/'panel'/key/c/'progress.json')['status']=='complete' for c in ('single','pra')):
            try:
                judge(key)
            except Exception as exc:
                write(ROOT/'panel'/key/'judge-failure.json',{'error':str(exc)})
                print(json.dumps({'paper':key,'judge_error':str(exc)}),flush=True)
                if usage()['unknown']:
                    return
    write(ROOT/'completion.json',{'usage':usage(),'status':'bounded_stages_finished'})


if __name__=='__main__':
    action=sys.argv[1]
    if action=='seal':seal()
    elif action=='all':all_stages()
    elif action=='judge':judge(sys.argv[2])
    elif action in ('single','pra'):generate(sys.argv[2],action)
    else:raise ValueError('Unknown stage')
