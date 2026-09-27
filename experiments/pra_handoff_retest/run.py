"""Two-call retest of exclusion preservation using frozen initial reviews."""
import argparse
import json
from pathlib import Path
import random
import secrets
import shutil
import time

from paper_workspace.annotations import save_review, verify_workspace
from paper_workspace.claim_checks import QUESTION_DEBATE, FOCUSED_DEBATE, validate_review_contract
from paper_workspace.debate_revision import issue_ledger, revision_prompt, validate_revision, revision_package
from paper_workspace.model_runtime import model_call, require_subscription, source_manifest, jsonl
from paper_workspace.storage import read, write, digest
from paper_workspace.table_evidence import evidence_paper
from experiments.pra_debate_revision.evaluation import EVALUATION, INSTRUCTIONS, audit

REPO = Path(__file__).resolve().parents[2]
OLD = REPO / 'runs/pra-claim-retest-v1'
ROOT = REPO / 'runs/pra-handoff-retest-v1'
WORK = ROOT / 'workspace'
PROTOCOL = {'provider':'codex','model':'gpt-5.6-sol','effort':'medium',
    'held_out_runs_authorized':False,'max_calls_per_condition':2,
    'observed_token_stop':250000,'call_timeout_seconds':600,'max_source_images':3,
    'version':'handoff-retest-v1','papers':1,'new_debate_calls':1,'new_evaluation_calls':1,
    'source_tools':False,'reuse_initial_reviews':True,
    'limitations':'Known-paper development retest of the handoff only. Initial reviews reused. One anonymous same-family evaluator. Not equal total generation compute or independent scientific validation.'}


def frozen(path, value):
    if path.exists():
        if read(path) != value:
            raise ValueError('Frozen input changed: ' + str(path))
    else:
        write(path, value)


def prepare():
    frozen(ROOT / 'protocol.json', PROTOCOL)
    if not WORK.exists():
        shutil.copytree(OLD / 'workspace', WORK, ignore=shutil.ignore_patterns('reviews'))
    paper = verify_workspace(WORK)
    for name in ('single','investigator'):
        frozen(ROOT / 'inputs' / (name + '.json'), read(OLD / 'raw' / (name + '.json')))
    frozen(ROOT / 'context.json', read(OLD / 'context.json'))
    frozen(ROOT / 'table-catalog.json', read(OLD / 'table-catalog.json'))
    images = []
    for image in read(OLD / 'images.json'):
        src = Path(image['path'])
        dest = ROOT / 'images' / src.name
        dest.parent.mkdir(exist_ok=True)
        if not dest.exists():
            shutil.copy2(src,dest)
        if digest(dest.read_bytes()) != image['sha256']:
            raise ValueError('Source image changed')
        images.append({**image,'path':str(dest)})
    frozen(ROOT / 'images.json', images)
    ledger = issue_ledger(read(ROOT / 'inputs/investigator.json'))
    frozen(ROOT / 'ledger.json', ledger)
    for name, label in (('single','single'), ('investigator','before-debate')):
        value = read(ROOT / 'inputs' / (name + '.json'))
        selected = {**value,'findings':[value['findings'][n-1] for n in value['selected_finding_numbers']]}
        saved = save_review(WORK, selected, label)
        frozen(ROOT / 'responses' / (label + '.json'), saved)
    if not (ROOT / 'evaluation/labels.json').exists():
        seed = secrets.randbits(64)
        order = ['single','before_debate','after_debate']
        random.Random(seed).shuffle(order)
        frozen(ROOT / 'evaluation/labels.json',dict(zip('ABC',order)))
        frozen(ROOT / 'evaluation/randomization.json',{'seed':seed})
    frozen(ROOT / 'freeze.json', {
        'protocol':PROTOCOL,'system':source_manifest(REPO / 'paper_workspace'),
        'runner':source_manifest(Path(__file__).parent),
        'source_manifest':digest((WORK / 'manifest.json').read_bytes()),
        'context':digest((ROOT / 'context.json').read_bytes()),
        'tables':digest((ROOT / 'table-catalog.json').read_bytes()),
        'inputs':source_manifest(ROOT / 'inputs'),'ledger':digest((ROOT / 'ledger.json').read_bytes()),
        'images':images,'labels':read(ROOT / 'evaluation/labels.json'),
        'protocol_text':digest((REPO / 'docs/pra-handoff-retest-protocol.md').read_bytes()),
        'evaluator':{str(p.relative_to(REPO)):digest(p.read_bytes()) for p in (
            REPO / 'experiments/pra_debate_revision/evaluation.py',
            REPO / 'experiments/pra_evidence_workflow/evaluation.py')}})
    if not (ROOT / 'frozen-source').exists():
        for src, label in ((REPO / 'paper_workspace','paper_workspace'), (Path(__file__).parent,'experiment')):
            shutil.copytree(src,ROOT / 'frozen-source' / label,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    return paper, images, read(ROOT / 'context.json')['text'], ledger


def call(label, prompt, schema, images):
    require_subscription(ROOT)
    if not 0 <= time.time()-read(ROOT / 'billing_confirmation.json')['checked_at'] < 86400:
        raise ValueError('Stale credit verification')
    frozen(ROOT / 'requests' / (label + '.json'),{'prompt':prompt,'schema':schema,'images':images})
    write(ROOT / 'progress.json',{'status':'running','stage':label})
    result = model_call(PROTOCOL,ROOT / 'execution',prompt,schema,label=label,
                        images=[Path(i['path']) for i in images])
    frozen(ROOT / 'raw' / (label + '.json'),result)
    return result


def debate():
    paper, images, ctx, ledger = prepare()
    prompt = revision_prompt(paper,ctx,ledger).replace(
        'Use the full manuscript below, original attached pages, and at most two optional source tool calls. Call a tool when missing context could change a consequential decision. Do not perform ritual lookups when the decisive evidence is already supplied.',
        'Use the complete delivered prose, source cell register, and original attached pages. No tools are available in this run.')
    prompt += '\n' + FOCUSED_DEBATE
    value = call('debate',prompt,QUESTION_DEBATE,images)
    validate_review_contract(value,paper,max_findings=5)
    checked = validate_revision(value,ledger,evidence_paper(paper,read(ROOT / 'table-catalog.json')))
    frozen(ROOT / 'debate-audit.json',checked)
    saved = save_review(WORK,revision_package(value,ledger,checked),'after-debate')
    frozen(ROOT / 'responses/after-debate.json',saved)
    frozen(ROOT / 'generation-lock.json',{
        'inputs':source_manifest(ROOT / 'inputs'),
        'debate':digest((ROOT / 'raw/debate.json').read_bytes()),
        'responses':source_manifest(ROOT / 'responses')})
    write(ROOT / 'progress.json',{'status':'debate_complete','evaluation':'pending'})
    print(json.dumps(checked,indent=2),flush=True)


def evaluate():
    paper, images, ctx, ledger = prepare()
    expected = read(ROOT / 'generation-lock.json')
    actual = {'inputs':source_manifest(ROOT / 'inputs'),
              'debate':digest((ROOT / 'raw/debate.json').read_bytes()),
              'responses':source_manifest(ROOT / 'responses')}
    if expected != actual:
        raise ValueError('Review outputs changed after generation')
    conditions = {'single':read(ROOT / 'responses/single.json'),
                  'before_debate':read(ROOT / 'responses/before-debate.json'),
                  'after_debate':read(ROOT / 'responses/after-debate.json')}
    mapping = read(ROOT / 'evaluation/labels.json')
    anonymous = {label:[{'finding_id':f'{label}{n}',**{k:f[k] for k in (
        'title','block_id','quote','kind','severity','comment','replacement','evidence_blocks','counterevidence')}}
        for n,f in enumerate(conditions[name]['findings'],1)] for label,name in mapping.items()}
    frozen(ROOT / 'evaluation/anonymous.json',anonymous)
    # Reuse the prior judging instructions, excluding its old reviews and labels.
    prior_prompt = read(OLD / 'requests/evaluation.json')['prompt']
    instructions = prior_prompt.split('\nREVIEWS:\n',1)[0]
    prompt = instructions + '\nREVIEWS:\n' + json.dumps(anonymous,ensure_ascii=False)
    prompt += '\nTITLE:\n' + paper['title'] + '\nATTACHED IMAGES:\n' + json.dumps(
        [{k:i[k] for k in ('id','label')} for i in images]) + '\nSOURCE PACKET:\n' + ctx
    value = call('evaluation',prompt,EVALUATION,images)
    checked = audit(value,anonymous,evidence_paper(paper,read(ROOT / 'table-catalog.json')),images)
    frozen(ROOT / 'evaluation/audit.json',checked)
    valid = set(checked['valid_rating_ids'])
    metrics = []
    for condition in value['conditions']:
        ratings = [r for r in condition['ratings'] if r['finding_id'] in valid]
        metrics.append({'condition':mapping[condition['label']], 'total':len(condition['ratings']),
            'unscored':len(condition['ratings'])-len(ratings),
            'assessments':{s:sum(r['assessment']==s for r in ratings) for s in (
                'justified_concern','justified_clarification','unsupported_allegation','unverifiable')},
            'excessive_requests':sum(r['resolution_proportionality']=='excessive' for r in ratings)})
    usage = jsonl(ROOT / 'execution/usage.jsonl')
    result = {'preferred':mapping.get(value['preferred_label'],value['preferred_label']),
        'preference_reason':value['preference_reason'],'metrics':metrics,'new_calls':len(usage),
        'new_observed_tokens':sum(r['observed_tokens'] for r in usage),
        'limitations':PROTOCOL['limitations'],'source_audit':'pending'}
    frozen(ROOT / 'automated-results.json',result)
    write(ROOT / 'progress.json',{'status':'evaluation_complete','source_audit':'pending'})
    print(json.dumps(result,indent=2),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage',choices=['prepare','debate','evaluate'])
    args = parser.parse_args()
    {'prepare':prepare,'debate':debate,'evaluate':evaluate}[args.stage]()
