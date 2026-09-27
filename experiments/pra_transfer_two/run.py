"""Bounded stage runner with immutable inputs and explicit failed-output grading."""
import argparse
import json
from pathlib import Path
import random
import secrets
import shutil
import time

from paper_workspace.annotations import verify_workspace, save_review
from paper_workspace.storage import read, write, digest
from paper_workspace.model_runtime import model_call, require_subscription, source_manifest, jsonl
from paper_workspace.claim_checks import CANDIDATE_REVIEW, QUESTION_DEBATE, INVESTIGATE, FOCUSED_DEBATE, validate_review_contract, audit_checks
from paper_workspace.review_schema import COMMON
from paper_workspace.debate_revision import issue_ledger, revision_prompt, validate_revision, revision_package
from experiments.pra_debate_revision.evaluation import EVALUATION, INSTRUCTIONS, audit

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / 'runs/pra-transfer-two-v1'
PROTOCOL = {'provider':'codex', 'model':'gpt-5.6-sol', 'effort':'medium',
    'held_out_runs_authorized':False, 'max_calls_per_condition':8,
    'observed_token_stop':500000, 'call_timeout_seconds':900,
    'max_source_images':10, 'image_budget_version':'evidence-v1',
    'version':'transfer-two-v1', 'papers':2, 'tools':False,
    'limitations':'Two new development papers. Unequal generation compute. One same-family anonymous judge each. Published versions, no human overlap endpoint.'}


def frozen(path, value):
    if path.exists():
        if read(path) != value:
            raise ValueError('Frozen artifact changed: ' + str(path))
    else:
        write(path, value)


def freeze():
    frozen(ROOT / 'protocol.json', PROTOCOL)
    for key in ('sleep', 'yeast'):
        root = ROOT / key
        verify_workspace(root / 'workspace')
        if not (root / 'evaluation/labels.json').exists():
            seed = secrets.randbits(64)
            order = ['single', 'before_debate', 'after_debate']
            random.Random(seed).shuffle(order)
            frozen(root / 'evaluation/labels.json', dict(zip('ABC', order)))
            frozen(root / 'evaluation/randomization.json', {'seed':seed})
    frozen(ROOT / 'freeze.json', {
        'system':source_manifest(REPO / 'paper_workspace'),
        'runner':source_manifest(Path(__file__).parent),
        'protocol':PROTOCOL,
        'protocol_text':digest((REPO / 'docs/pra-transfer-two-protocol.md').read_bytes()),
        'evaluator':{str(p.relative_to(REPO)):digest(p.read_bytes()) for p in (
            REPO / 'experiments/pra_debate_revision/evaluation.py', REPO / 'experiments/pra_evidence_workflow/evaluation.py')},
        'papers':{key:{name:digest((ROOT / key / name).read_bytes()) for name in (
            'context.json', 'images.json', 'source-selection.json', 'workspace/manifest.json', 'evaluation/labels.json')}
            for key in ('sleep', 'yeast')}})
    if not (ROOT / 'frozen-source').exists():
        for src, name in ((REPO / 'paper_workspace','paper_workspace'), (Path(__file__).parent,'experiment')):
            shutil.copytree(src, ROOT / 'frozen-source' / name, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))


def call(root, label, prompt, schema, images):
    require_subscription(ROOT)
    if not 0 <= time.time() - read(ROOT / 'billing_confirmation.json')['checked_at'] < 86400:
        raise ValueError('Stale credit verification')
    frozen(root / 'requests' / (label + '.json'), {'prompt':prompt,'schema':schema,'images':images})
    write(root / 'progress.json', {'status':'running','stage':label})
    value = model_call(PROTOCOL, ROOT / 'execution', prompt, schema,
                       label=root.name + '-' + label, images=[Path(i['path']) for i in images])
    frozen(root / 'raw' / (label + '.json'), value)
    return value


def run(key, stage):
    freeze()
    root = ROOT / key
    paper = verify_workspace(root / 'workspace')
    ctx = read(root / 'context.json')['text']
    images = read(root / 'images.json')
    shared = '\nTITLE:\n' + paper['title'] + '\nATTACHED IMAGES:\n' + json.dumps([{k:i[k] for k in ('id','label')} for i in images]) + '\nSOURCE PACKET:\n' + ctx
    if stage in ('single','investigator'):
        common = COMMON.replace('Give at most five distinct, consequential findings',
            'Produce at most eight distinct candidate findings and select at most five by one-based selected_finding_numbers')
        common += '\nReturn only scientific questions with empty replacements. Keep all candidate comments together under 900 words. No quotas for defects. Both investigation and selection are your task in this one call. No tools or follow-up call are available to this initial reviewer. Use the complete delivered evidence. Claim_checks are optional unless further instructions require them. All source quotations must be exact.\n'
        direction = INVESTIGATE if stage == 'investigator' else 'Perform a thorough ordinary scientific peer review, testing your concerns against author explanations and selecting the most consequential supported questions.'
        value = call(root, stage, common + direction + shared, CANDIDATE_REVIEW, images)
        validate_review_contract(value, paper)
        checked = audit_checks(value, paper, stage == 'investigator')
        frozen(root / 'audits' / (stage + '.json'), checked)
        label = 'before-debate' if stage == 'investigator' else 'single'
        candidates = save_review(root / 'workspace', value, label + '-candidates')
        selected = {**value,'findings':[value['findings'][n-1] for n in value['selected_finding_numbers']],
                    'claim_check_audit':checked, 'source_findings':candidates['findings']}
        saved = save_review(root / 'workspace', selected, label)
        frozen(root / 'responses' / (label + '.json'), saved)
    elif stage == 'debate':
        ledger = issue_ledger(read(root / 'raw/investigator.json'))
        frozen(root / 'ledger.json', ledger)
        prompt = revision_prompt(paper, ctx, ledger).replace(
            'Use the full manuscript below, original attached pages, and at most two optional source tool calls. Call a tool when missing context could change a consequential decision. Do not perform ritual lookups when the decisive evidence is already supplied.',
            'Use the complete delivered source packet and original attached pages. No tools are available in this run.')
        prompt += '\nATTACHED IMAGES:\n' + json.dumps([{k:i[k] for k in ('id','label')} for i in images]) + '\n' + FOCUSED_DEBATE
        value = call(root, stage, prompt, QUESTION_DEBATE, images)
        validate_review_contract(value, paper, max_findings=5)
        try:
            checked = validate_revision(value, ledger, paper)
        except ValueError as exc:
            checked = {'structural_validity':False, 'error':str(exc),
                       'limitation':'Exploratory selected-question comparison only. The internal debate audit failed. Raw output is unrepaired and production acceptance is blocked.'}
        frozen(root / 'audits/debate.json', checked)
        package = revision_package(value, ledger, checked)
        if not checked['structural_validity']:
            package['summary'] = 'Exploratory output. Internal debate validation failed. ' + package['summary']
        saved = save_review(root / 'workspace', package, 'after-debate')
        frozen(root / 'responses/after-debate.json', saved)
        frozen(root / 'generation-lock.json', {'raw':{p.name:digest(p.read_bytes()) for p in (root / 'raw').glob('*.json') if p.stem != 'evaluation'}, 'responses':source_manifest(root / 'responses')})
    else:
        frozen(root / 'generation-lock.json', {'raw':{p.name:digest(p.read_bytes()) for p in (root / 'raw').glob('*.json') if p.stem != 'evaluation'}, 'responses':source_manifest(root / 'responses')})
        mapping = read(root / 'evaluation/labels.json')
        conditions = {name:read(root / 'responses' / (name.replace('_','-') + '.json')) for name in mapping.values()}
        anonymous = {label:[{'finding_id':f'{label}{n}', **{k:f[k] for k in ('title','block_id','quote','kind','severity','comment','replacement','evidence_blocks','counterevidence')}} for n,f in enumerate(conditions[name]['findings'], 1)] for label,name in mapping.items()}
        frozen(root / 'evaluation/anonymous.json', anonymous)
        value = call(root, 'evaluation', INSTRUCTIONS + '\nREVIEWS:\n' + json.dumps(anonymous, ensure_ascii=False) + shared, EVALUATION, images)
        checked = audit(value, anonymous, paper, images)
        frozen(root / 'evaluation/audit.json', checked)
        valid = set(checked['valid_rating_ids'])
        metrics = []
        for row in value['conditions']:
            ratings = [r for r in row['ratings'] if r['finding_id'] in valid]
            metrics.append({'condition':mapping[row['label']], 'total':len(row['ratings']), 'unscored':len(row['ratings'])-len(ratings),
                'assessments':{s:sum(r['assessment']==s for r in ratings) for s in ('justified_concern','justified_clarification','unsupported_allegation','unverifiable')},
                'excessive_requests':sum(r['resolution_proportionality']=='excessive' for r in ratings)})
        frozen(root / 'automated-results.json', {'preferred':mapping.get(value['preferred_label'],value['preferred_label']), 'preference_reason':value['preference_reason'], 'metrics':metrics, 'source_audit':'pending', 'production_debate_pass':read(root / 'audits/debate.json')['structural_validity']})
    write(root / 'progress.json', {'status':'stage_complete','stage':stage})
    print(json.dumps({'paper':key,'stage':stage,'usage':sum(r['observed_tokens'] for r in jsonl(ROOT / 'execution/usage.jsonl'))}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('paper', choices=['sleep','yeast'])
    p.add_argument('stage', choices=['single','investigator','debate','evaluate','freeze'])
    a = p.parse_args()
    freeze() if a.stage == 'freeze' else run(a.paper, a.stage)
