"""Separately labeled engineering replay of the molecular delivery failure."""
import json
import shutil
import time
from pathlib import Path
from experiments.pra_three_condition.prepare import ROOT
from experiments.pra_three_condition.run import PROTOCOL,ORDERS,usage,verify
from experiments.pra_three_condition.evaluate import evaluate
from experiments.pra_presentation_recovery import recover
from paper_workspace.annotations import verify_workspace,save_review
from paper_workspace.debate_revision import revision_package
from paper_workspace.model_runtime import require_subscription
from paper_workspace.storage import read,write,digest

REPLAY=ROOT.parent/'pra-four-condition-recovery-v1'
TARGET=REPLAY/'panel/molecular'


def prepare():
    verify()
    original=ROOT/'panel/molecular'
    base=ROOT/'inputs/molecular'
    value=read(original/'pra/responses/debate.json')
    paper=verify_workspace(base/'workspace')
    ledger=read(original/'pra/debate-ledger.json')
    result=recover(value,ledger,paper)
    if result['recovered'] is None:raise ValueError('No presentation-only recovery available')
    if result['recovered']['findings']!=value['findings']:raise ValueError('Review text changed')
    if TARGET.exists():raise ValueError('Replay already prepared')
    for condition in ('basic','workspace','pra'):
        for directory in ('responses','sources','source-cache','investigations'):
            if (original/condition/directory).exists():
                shutil.copytree(original/condition/directory,TARGET/condition/directory)
        for name in ('editor-package.json','progress.json'):
            if (original/condition/name).exists():
                shutil.copy2(original/condition/name,TARGET/condition/name)
    final=result['recovered']
    normalized=save_review(base/'workspace',final,'four-condition-molecular-replay')
    if any(f['placement']!='anchored' or f['invalid_evidence_blocks'] for f in normalized['findings']):
        raise ValueError('Recovered review has invalid anchors')
    guarded={**final,'findings':normalized['findings']}
    package=revision_package(guarded,ledger,result['audit'])
    write(TARGET/'pra/editor-package.json',package)
    write(TARGET/'pra/progress.json',{'status':'complete','scope':'Post-hoc presentation-only engineering replay. Original study delivery remains failed.'})
    write(REPLAY/'recovery.json',{**result,'source_sha256':digest((original/'pra/responses/debate.json').read_bytes()),
        'original_study_status':'failed_delivery','new_generation_calls':0,
        'label_schedule':'Uses the originally frozen molecular label order.',
        'quality_scope':'Any subsequent blind preference is a post-hoc assessment of the recovered draft, not a successful original workflow.'})


def budget(required):
    verify()
    a,b=usage(),usage(REPLAY/'panel')
    if not (ROOT/'completion.json').exists():raise ValueError('Original run is not finished')
    if a['unknown'] or b['unknown'] or a['calls']!=a['receipts'] or b['calls']!=b['receipts']:
        raise ValueError('Unresolved usage')
    if a['calls']+b['calls']+required>24 or a['observed_tokens']+b['observed_tokens']>=2200000:
        raise ValueError('Original 24-call ceiling or amended judging allowance exhausted')
    if time.time()-read(ROOT/'billing_confirmation.json')['checked_at']>=86400:raise ValueError('Billing check expired')
    require_subscription(ROOT)


def judge():
    protocol={**PROTOCOL,'observed_token_launch_stop':2200000,'resource_amendment':'judging-only-v1'}
    evaluate(TARGET,ROOT/'inputs/molecular',protocol,budget,verify,lambda:usage(REPLAY/'panel'),ORDERS['molecular'])


def finish_judging():
    write(ROOT/'resource-amendment.json',{'created_at':time.time(),'original_observed_usage':usage(),
        'original_launch_threshold':1800000,'amended_judging_launch_threshold':2200000,
        'max_total_calls_including_recovery':24,'additional_generation_calls':0,
        'reason':'All planned review generation completed, but observed usage exceeded the estimate. Finish only the two remaining planned assessments within the original call ceiling.',
        'scope':['public_health original final reviews','molecular post-hoc presentation-only recovery'],
        'unchanged':['review text','generation prompts','judge prompt and schema','model and effort','label schedule','original failure outcomes']})
    protocol={**PROTOCOL,'observed_token_launch_stop':2200000,'resource_amendment':'judging-only-v1'}
    evaluate(ROOT/'panel/public_health',ROOT/'inputs/public_health',protocol,budget,verify,
             lambda:usage(ROOT/'panel/public_health'),ORDERS['public_health'])
    judge()
    write(ROOT/'judging-completion.json',{'original_run_usage':usage(),'recovery_usage':usage(REPLAY/'panel'),
        'status':'All four planned paper assessments attempted, with molecular recovery separate from original delivery.'})


if __name__=='__main__':
    import sys
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='judge':judge()
    elif sys.argv[1]=='finish':finish_judging()
    else:raise ValueError('Unknown stage')
