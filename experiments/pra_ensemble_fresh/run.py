"""Frozen two-paper comparison with no automatic model retries."""
import json
import shutil
import sys
import time
from pathlib import Path

from paper_workspace.annotations import verify_workspace
from paper_workspace.ensemble import debate_reviews,observed_usage,check_budget
from paper_workspace.model_runtime import require_subscription
from paper_workspace.reviewer import review
from paper_workspace.storage import read,write,digest
from .generate import sequential,source_images


REPO=Path(__file__).resolve().parents[2]
ROOT=REPO/'runs/pra-ensemble-fresh-v1'
PAPERS=('clinical','plant')
PROTOCOL={'version':'ensemble-fresh-v1','provider':'codex','model':'gpt-5.6-terra','effort':'medium',
    'held_out_runs_authorized':False,'max_calls_per_condition':1,'observed_token_stop':750000,
    'call_timeout_seconds':900,'max_source_images':10,'image_budget_version':'evidence-v1',
    'literature_cutoff':'2026-09-25','max_total_model_calls':12,'observed_token_launch_ceiling':1500000,
    'automatic_model_retries':False,'logical_generation_calls_each':3,'tool_calls_each':[4,4,2],
    'external_request_caps_each':[6,6,2],'shared_initial_discovery':True,
    'conditions':['ensemble','sequential'],'main_finding_limit':5,'main_comment_word_limit':900,
    'label_mapping':{'clinical':{'A':'ensemble','B':'sequential'},'plant':{'A':'sequential','B':'ensemble'}},
    'evaluation':'Rate main findings and candidate bank against sources, group semantic issues, and assess additions and losses. Main-report preference is secondary.',
    'limitations':['Two convenience-sampled development papers, not confirmatory evidence.',
                  'Call and tool caps are matched. Actual token use can differ.',
                  'One same-family anonymous automated judge per paper, not expert validation.',
                  'Published articles rather than original pre-review submissions.',
                  'No human reference reviews are supplied or scored.']}


def verify():
    for name,sha in read(ROOT/'seal.json')['files'].items():
        if digest(Path(name).read_bytes())!=sha:raise ValueError('Frozen input changed: '+name)


def budget(required=1):
    verify()
    value=observed_usage(ROOT/'panel')
    if value['calls']+required>12:raise ValueError('Twelve-call study ceiling reached')
    check_budget(ROOT/'panel',1500000,12)
    if not 0<=time.time()-read(ROOT/'billing_confirmation.json')['checked_at']<86400:
        raise ValueError('Subscription verification expired')
    require_subscription(ROOT)


def seal():
    if (ROOT/'seal.json').exists():raise ValueError('Study already sealed')
    prior=read(ROOT/'prior-corpus.json')['papers']
    for key,item in read(ROOT/'prepared-papers.json').items():
        paper=verify_workspace(ROOT/'inputs'/key/'workspace')
        if any(item['doi'] in [r['doi'],*r.get('alternate_dois',[])] or paper['id'] in [r['paper_id'],*r.get('alternate_paper_ids',[])]
               or paper['title'].casefold() in [r['title'].casefold(),*[t.casefold() for t in r.get('alternate_titles',[])]] for r in prior):
            raise ValueError('Study manuscript overlaps prior local corpus')
    write(ROOT/'protocol.json',PROTOCOL)
    files=[ROOT/name for name in ('protocol.json','prior-corpus.json','preselection.json','prepared-papers.json')]
    files+=[REPO/'docs/pra-ensemble-fresh-protocol.md']
    for directory in (REPO/'paper_workspace',REPO/'experiments',ROOT/'inputs'):
        files.extend(p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    write(ROOT/'seal.json',{'created_at':time.time(),'files':{str(p):digest(p.read_bytes()) for p in sorted(set(files))}})
    for directory in ('paper_workspace','experiments'):
        shutil.copytree(REPO/directory,ROOT/'frozen-source'/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    print('Frozen two fresh manuscripts, both workflows, budgets and blinded assessment',flush=True)


def stage(key,name):
    base=ROOT/'inputs'/key
    root=ROOT/'panel'/key
    out=root/name
    budget()
    if name in ('shared','independent'):
        if out.exists():raise ValueError('Discovery already prepared or attempted')
        review(base/'workspace',out,ROOT/'billing_confirmation.json',PROTOCOL['literature_cutoff'],
            mode='independent',scaffold_root='/home/ty/Repos/paper-scaffold',model='gpt-5.6-terra',
            shared_images=[i['path'] for i in read(base/'images.json')])
    elif name in ('sequential-2','sequential-3'):
        previous=[root/'shared']+([root/'sequential-2'] if name=='sequential-3' else [])
        sequential(root,base,out,PROTOCOL,ROOT/'billing_confirmation.json',previous,final=name=='sequential-3')
    elif name=='ensemble':
        records=[]
        for origin in ('shared','independent'):
            path=root/origin/'editor-package.json'
            records.append({'review':read(path),'provenance':{'paper_id':verify_workspace(base/'workspace')['id'],
                'reviewer_id':origin,'source_review_path':str(path),'source_review_sha256':digest(path.read_bytes()),
                'origin':'fresh_independent_session'}})
        debate_reviews(base/'workspace',out,ROOT/'billing_confirmation.json',PROTOCOL['literature_cutoff'],records,
            images=source_images(base,[root/'shared',root/'independent']),model='gpt-5.6-terra',
            token_budget=750000,cache_roots=[root/s/'source-cache' for s in ('shared','independent')])
    elif name=='judge':
        from .evaluate import evaluate
        result=evaluate(root,base,PROTOCOL,budget,PROTOCOL['label_mapping'][key])
        print(json.dumps({'paper':key,'assessment':result}),flush=True)
    else:raise ValueError('Unknown stage')
    verify()
    print(json.dumps({'paper':key,'stage':name,'usage':observed_usage(ROOT/'panel')}),flush=True)


def run_all():
    orders={'clinical':('shared','independent','ensemble','sequential-2','sequential-3','judge'),
            'plant':('shared','sequential-2','sequential-3','independent','ensemble','judge')}
    for key in PAPERS:
        for name in orders[key]:
            try:
                write(ROOT/'progress.json',{'status':'running','paper':key,'stage':name})
                stage(key,name)
            except Exception as error:
                write(ROOT/'panel'/key/(name+'-failure.json'),{'error':str(error)})
                write(ROOT/'progress.json',{'status':'blocked','paper':key,'stage':name,'error':str(error),
                    'usage':observed_usage(ROOT/'panel')})
                raise
    write(ROOT/'progress.json',{'status':'complete','usage':observed_usage(ROOT/'panel')})


if __name__=='__main__':
    if sys.argv[1]=='seal':seal()
    elif sys.argv[1]=='all':run_all()
    else:stage(sys.argv[2],sys.argv[1])
