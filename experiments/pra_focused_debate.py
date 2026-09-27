"""Three-call development comparison of a focused evidence handoff."""
import json
import random
import shutil
import time
from pathlib import Path
from experiments.pra_focused_investigation import QUESTION, BLOCKS
from experiments.pra_review_utility import (INSTRUCTIONS, schema, assess, review_spans, hydrate_review_spans)
from experiments.pra_ensemble_fresh.evaluate import PRIMARY_FIELDS, _secondary_ensemble
from experiments.pra_prospective.core import _clean
from paper_workspace.annotations import verify_workspace
from paper_workspace.ensemble import debate_reviews, check_budget, observed_usage
from paper_workspace.focused_investigation import investigate, load_for_debate
from paper_workspace.evidence_handles import build_registry, model_catalog
from paper_workspace.judge_evidence import judge_schema, hydrate_judgment
from paper_workspace.model_runtime import model_call, require_subscription, source_manifest
from paper_workspace.run_state import tracked_stage
from paper_workspace.storage import read, write, digest

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/'runs/pra-focused-debate-v1'
OLD=REPO/'runs/pra-ensemble-clarification-v1'
BASE=OLD/'inputs/fresh'
PRIOR=OLD/'panel/fresh/ensemble'
LIMIT=550000
JUDGE={'version':'focused-debate-judge-v1','provider':'codex','model':'gpt-5.6-terra',
       'effort':'medium','held_out_runs_authorized':False,'max_calls_per_condition':1,
       'observed_token_stop':LIMIT,'call_timeout_seconds':900,
       'max_source_images':10,'image_budget_version':'evidence-v1'}


def prepare():
    if (ROOT/'seal.json').exists():raise ValueError('Already prepared')
    labels=['saved','updated']
    random.SystemRandom().shuffle(labels)
    write(ROOT/'mapping.json',dict(zip(('A','B'),labels)))
    write(ROOT/'protocol.json',{**JUDGE,'max_new_calls':3,'launch_budget':LIMIT,
        'automatic_retries':False,'question':QUESTION,'blocks':BLOCKS,
        'scope':'One known development paper. Coordinator-selected question. Updated debate has additional evidence and model effort. Judge is blinded to workflow, not an independent expert.'})
    shutil.copytree(REPO/'paper_workspace',ROOT/'frozen-source/paper_workspace',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    paths=[Path(__file__),REPO/'experiments/pra_review_utility.py',REPO/'experiments/pra_focused_investigation.py',
           ROOT/'mapping.json',ROOT/'protocol.json',PRIOR/'editor-package.json',PRIOR/'input-reviews.json',BASE/'images.json']
    paths += [REPO/'paper_workspace'/p for p in source_manifest(REPO/'paper_workspace')]
    manifest=read(BASE/'workspace/manifest.json')
    paths += [BASE/'workspace/manifest.json']+[BASE/'workspace'/p for p in manifest['files']]
    paths += [Path(i['path']) for i in read(BASE/'images.json')]
    write(ROOT/'seal.json',{'files':{str(p):digest(p.read_bytes()) for p in paths}})


def verify():
    for p,sha in read(ROOT/'seal.json')['files'].items():
        if digest(Path(p).read_bytes())!=sha:raise ValueError('Frozen input changed: '+p)


def budget():
    verify()
    check_budget(ROOT,LIMIT,3)
    confirmation=read(ROOT/'billing_confirmation.json')
    if not 0<=time.time()-confirmation['checked_at']<86400:raise ValueError('Billing check expired')
    require_subscription(ROOT)


def judge():
    target=ROOT/'judge'
    target.mkdir(exist_ok=False)
    mapping=read(ROOT/'mapping.json')
    paper=verify_workspace(BASE/'workspace')
    paths={'saved':PRIOR/'editor-package.json','updated':ROOT/'debate/editor-package.json'}
    anonymous={}
    for label,name in mapping.items():
        package=read(paths[name])
        secondary,skipped=_secondary_ensemble(package)
        if skipped:raise ValueError('Secondary findings lack anchored evidence')
        findings=[*package['findings'],*secondary]
        anonymous[label]=[{'finding_id':label+str(i),**_clean({k:f[k] for k in PRIMARY_FIELDS if k in f})}
                          for i,f in enumerate(findings,1)]
    _,memo_images=load_for_debate(BASE/'workspace',ROOT/'investigator')
    images=[]
    image_paths=[]
    for p in [*[Path(i['path']) for i in read(BASE/'images.json')],*memo_images]:
        sha=digest(p.read_bytes())
        if sha in [i['sha256'] for i in images]:continue
        name='image-'+str(len(images)+1)
        dest=target/'evidence'/f'{name}.png'
        dest.parent.mkdir(exist_ok=True)
        shutil.copy2(p,dest)
        images.append({'id':name,'label':'Original manuscript or supplement page','sha256':sha})
        image_paths.append(dest)
    registry=build_registry(paper)
    spans=review_spans(anonymous)
    active=judge_schema(schema(spans,mapping),registry,images)
    instructions=INSTRUCTIONS.replace('three anonymous peer reviews','two anonymous peer reviews').replace('Compare all three pairs','Compare the single pair')
    prompt=instructions+'\nExplain meaningful omissions or loss of useful qualifications between the reviews in your pairwise reason. Do not reward extra wording that adds no actionable information.'
    prompt+='\nANONYMOUS REVIEWS:\n'+json.dumps(anonymous,ensure_ascii=False)
    prompt+='\nREVIEW QUOTATION FORMAT OVERRIDE: Select review_handle from REVIEW SPANS for each assessed point. Source evidence uses separate evidence_handle identifiers. Use a whole-comment handle when a point spans multiple sentences.'
    prompt+='\nREVIEW SPANS:\n'+json.dumps(spans,ensure_ascii=False)
    prompt+='\nSOURCE SPANS:\n'+json.dumps(model_catalog(registry),ensure_ascii=False)
    prompt+='\nSOURCE IMAGES:\n'+json.dumps(images,ensure_ascii=False)
    write(target/'input.json',{'anonymous':anonymous,'review_spans':spans,'images':images,
          'schema':active,'prompt':prompt,'source_review_sha256':{label:digest(paths[name].read_bytes()) for label,name in mapping.items()}})
    raw=model_call(JUDGE,target/'execution',prompt,active,tools=False,label='blind-usefulness',images=image_paths)
    write(target/'raw-model.json',raw)
    hydrated=hydrate_judgment(raw,registry,images)
    write(target/'reference-audit.json',hydrated)
    value=hydrate_review_spans(hydrated['response'],spans)
    write(target/'ratings.json',value)
    result=assess(value,anonymous,mapping)
    old=set(result['metrics']['saved']['valid_groups'])
    new=set(result['metrics']['updated']['valid_groups'])
    result['valid_group_changes']={'shared':sorted(old&new),'saved_only':sorted(old-new),'updated_only':sorted(new-old)}
    result['usage']=observed_usage(ROOT)
    result['limitation']='One known paper and one same-family AI judge. Additional effort and evidence are confounded. Group differences reflect model judgment, not mechanically verified information loss. No general superiority claim.'
    write(ROOT/'results.json',result)


def run():
    for name in ('investigator','debate','judge'):
        budget()
        if (ROOT/name).exists():raise ValueError('Stage already attempted. No automatic retry: '+name)
        with tracked_stage(ROOT/'worker-state.json',name,1100):
            if name=='investigator':
                memo=investigate(BASE/'workspace',ROOT/name,ROOT/'billing_confirmation.json','2026-09-25',QUESTION,BLOCKS)
                if not memo['ready_for_adjudication']:raise ValueError('Repaired memo failed validation. Preserved without handoff.')
            elif name=='debate':
                debate_reviews(BASE/'workspace',ROOT/name,ROOT/'billing_confirmation.json','2026-09-25',
                    read(PRIOR/'input-reviews.json'),images=[i['path'] for i in read(BASE/'images.json')],
                    model='gpt-5.6-terra',token_budget=LIMIT-observed_usage(ROOT)['observed_tokens'],
                    cache_roots=[OLD/'panel/fresh'/s/'source-cache' for s in ('shared','independent')],
                    evidence_memos=[ROOT/'investigator'])
            else:judge()
            verify()
        print(name,observed_usage(ROOT),flush=True)
    write(ROOT/'completion.json',{'status':'complete','usage':observed_usage(ROOT)})


if __name__=='__main__':
    import sys
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':run()
    else:raise ValueError('Unknown command')
