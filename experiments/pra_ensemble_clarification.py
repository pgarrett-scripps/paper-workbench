"""One saved assessment and one fresh comparison with explicit launch limits."""
import shutil
import signal
import sys
import time
from pathlib import Path

from experiments.pra_ensemble_fresh.evaluate import evaluate, STAGES
from experiments.pra_ensemble_fresh.generate import sequential, source_images
from paper_workspace.annotations import verify_workspace
from paper_workspace.ensemble import debate_reviews, observed_usage, check_budget
from paper_workspace.model_runtime import require_subscription
from paper_workspace.reviewer import review
from paper_workspace.run_state import tracked_stage, inspect_state
from paper_workspace.storage import read, write, digest

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/'runs/pra-ensemble-clarification-v1'
OLD=REPO/'runs/pra-ensemble-fresh-v1'
PROTOCOL={'version':'ensemble-clarification-v1','provider':'codex','model':'gpt-5.6-terra','effort':'medium',
    'held_out_runs_authorized':False,'max_calls_per_condition':1,'observed_token_stop':900000,
    'call_timeout_seconds':900,'max_source_images':10,'image_budget_version':'evidence-v1',
    'literature_cutoff':'2026-09-25','max_total_model_calls':7,'observed_token_launch_ceiling':900000,
    'automatic_model_retries':False,'logical_generation_calls_each':3,'tool_calls_each':[4,4,2],
    'external_request_caps_each':[6,6,2],'shared_initial_discovery':True,
    'main_finding_limit':5,'main_comment_word_limit':900,
    'label_mapping':{'plant':{'A':'sequential','B':'ensemble'},'fresh':{'A':'ensemble','B':'sequential'}},
    'prior_unknown_usage':'The old plant judge has unknown usage. This newly authorized run records new spending separately, without claiming the old call was free.'}


def budget(required=1):
    value=observed_usage(ROOT/'panel')
    if value['calls']+required>7:raise ValueError('Seven-call ceiling reached')
    check_budget(ROOT/'panel',900000,7)
    if not 0<=time.time()-read(ROOT/'billing_confirmation.json')['checked_at']<86400:
        raise ValueError('Subscription verification expired')
    require_subscription(ROOT)


def prepare_saved():
    root=ROOT/'panel/plant'
    if root.exists():raise ValueError('Saved reassessment already prepared')
    records=[]
    for stage in STAGES:
        source=OLD/'panel/plant'/stage
        target=root/stage
        path=source/'editor-package.json'
        write(target/'editor-package.json',read(path))
        records.append({'stage':stage,'path':str(path),'sha256':digest(path.read_bytes())})
        for directory in ('source-cache','investigations'):
            if (source/directory).exists():shutil.copytree(source/directory,target/directory)
    write(root/'saved-review-manifest.json',{'sources':records,'scientific_reviews_changed':False,
        'prior_attempt':str(OLD/'panel/plant/evaluation'),'reason':'Explicitly authorized new assessment after interrupted judge. No review generation repeated.'})


def freeze():
    if (ROOT/'seal.json').exists():raise ValueError('Already frozen')
    paths=[ROOT/'protocol.json', ROOT/'preselection.json', REPO/'docs/pra-ensemble-clarification-protocol.md']
    for folder in (REPO/'paper_workspace', REPO/'experiments', ROOT/'inputs/fresh'):
        paths.extend(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    write(ROOT/'seal.json',{'created_at':time.time(),'files':{str(p):digest(p.read_bytes()) for p in paths}})
    for name in ('paper_workspace','experiments'):
        shutil.copytree(REPO/name,ROOT/'frozen-source'/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))


def verify():
    for name,sha in read(ROOT/'seal.json')['files'].items():
        if digest(Path(name).read_bytes())!=sha:raise ValueError('Frozen file changed: '+name)


def fresh_stage(name):
    verify()
    budget()
    base=ROOT/'inputs/fresh'
    root=ROOT/'panel/fresh'
    out=root/name
    if name in ('shared','independent'):
        if out.exists():raise ValueError('Stage already attempted')
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
            token_budget=900000,cache_roots=[root/s/'source-cache' for s in ('shared','independent')])
    elif name=='judge':
        evaluate(root,base,PROTOCOL,budget,PROTOCOL['label_mapping']['fresh'])
    else:raise ValueError('Unknown stage')
    verify()
    print(name,observed_usage(ROOT/'panel'),flush=True)


def main(command):
    if command=='status':
        print(inspect_state(ROOT/'worker-state.json'))
        print(observed_usage(ROOT/'panel'))
        return
    if command=='seal':
        freeze()
        return
    def stop(signum, frame):raise SystemExit('Worker received termination signal')
    signal.signal(signal.SIGTERM, stop)
    with tracked_stage(ROOT/'worker-state.json',command,7500):
        if command=='saved':
            if not (ROOT/'panel/plant').exists():prepare_saved()
            evaluate(ROOT/'panel/plant',OLD/'inputs/plant',PROTOCOL,budget,PROTOCOL['label_mapping']['plant'])
        elif command=='fresh':
            for name in ('shared','sequential-2','sequential-3','independent','ensemble','judge'):
                with tracked_stage(ROOT/'stage-state.json',name,1100):fresh_stage(name)
            write(ROOT/'completion.json',{'status':'complete','usage':observed_usage(ROOT/'panel')})
        elif command=='recover-saved':
            evaluate(ROOT/'panel/plant',OLD/'inputs/plant',PROTOCOL,budget,PROTOCOL['label_mapping']['plant'],resume=True)
        else:raise ValueError('Unknown command')


if __name__=='__main__':main(sys.argv[1])
