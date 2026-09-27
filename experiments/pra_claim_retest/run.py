"""A bounded development retest with complete source cells and matched outputs."""
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
from paper_workspace.scaffold_checks import compact_summary
from paper_workspace.table_evidence import build_catalog, catalog_text, evidence_paper
from paper_workspace.claim_checks import (CANDIDATE_REVIEW, QUESTION_DEBATE, INVESTIGATE,
    FOCUSED_DEBATE, validate_review_contract, audit_checks)
from paper_workspace.review_schema import COMMON
from paper_workspace.debate_revision import issue_ledger, revision_prompt, validate_revision, revision_package
from experiments.pra_debate_revision.evaluation import EVALUATION, INSTRUCTIONS, audit

REPO = Path(__file__).resolve().parents[2]
OLD = REPO / 'runs/pra-fresh-comparison-v1'
ROOT = REPO / 'runs/pra-claim-retest-v1'
WORK = ROOT / 'workspace'
PROTOCOL = {
    'provider':'codex', 'model':'gpt-5.6-sol', 'effort':'medium',
    'held_out_runs_authorized':False, 'max_calls_per_condition':4,
    'observed_token_stop':450000, 'call_timeout_seconds':900,
    'max_source_images':3, 'version':'claim-retest-v1',
    'papers':1, 'single_calls':1, 'pra_calls':2, 'evaluation_calls':1,
    'tools':False, 'shared_pages':[4,8,12],
    'limitations':'Known development manuscript. Same inputs and output allowance, unequal total calls. One anonymous same-family evaluator, no human-overlap or independent expert endpoint.'}


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
    source = ROOT / 'sources'
    source.mkdir(exist_ok=True)
    for path in sorted((OLD / 'sources/supplements').glob('S*_Table.xlsx')):
        target = source / path.name
        if not target.exists():
            shutil.copy2(path, target)
        if digest(target.read_bytes()) != digest(path.read_bytes()):
            raise ValueError('Reported table source changed')
    catalog = build_catalog(source.glob('*.xlsx'))
    frozen(ROOT / 'table-catalog.json', catalog)
    images = []
    for page in PROTOCOL['shared_pages']:
        src = OLD / 'images' / f'main-{page}.png'
        dest = ROOT / 'images' / src.name
        dest.parent.mkdir(exist_ok=True)
        if not dest.exists():
            shutil.copy2(src, dest)
        if digest(src.read_bytes()) != digest(dest.read_bytes()):
            raise ValueError('Source image changed')
        images.append({'id':f'image-{len(images)+1}', 'path':str(dest),
                       'label':f'Original PDF page {page}', 'sha256':digest(dest.read_bytes())})
    frozen(ROOT / 'images.json', images)
    blocks = []
    for block in paper['blocks']:
        if block['kind'] == 'reference':
            continue
        if block['kind'] == 'table':
            # Complete cell values replace the lossy unaddressed table transcription.
            title = block['text'].split(' Cached reported values')[0]
            blocks.append(f"[{block['id']}] TABLE SOURCE {title}. All populated cells are in the register below.")
        else:
            blocks.append(f"[{block['id']}] {block['section']} | page {block.get('page')} | {block['kind']}\n{block['text']}")
    ctx = '\n\n'.join(blocks) + '\n\n' + catalog_text(catalog)
    ctx += '\nADVISORY SCAFFOLD CHECKS\n' + json.dumps(compact_summary(read(OLD / 'diagnostics.json')), ensure_ascii=False)
    ctx += '\nSOURCE LIMITS: Main prose and supplementary text are delivered. Ten reported-result tables are complete as cached values. Only original PDF pages 4, 8, and 12 are attached as images. Other figure pixels, external literature, source datasets, and author code are unavailable in this run. Figure 2 caption text is on page 9. Mathematical layout may be flattened. Do not allege absence from inaccessible material. Cell-register rows are source evidence only, never manuscript edit anchors. Anchor findings to original b-prefixed blocks, with b-prefixed evidence_blocks. You may cite cell addresses in comments and use t-prefixed row IDs and exact register quotations in claim_checks, debate decisions, and evaluation references.'
    frozen(ROOT / 'context.json', {'text':ctx})
    selection = read(OLD / 'source-selection.json')
    frozen(ROOT / 'source-provenance.json', {'selection':selection, 'development_reuse':True,
        'prior_findings_delivered_to_models':False, 'human_review_history_delivered':False,
        'manuscript_manifest':digest((WORK / 'manifest.json').read_bytes()),
        'table_workbooks':[{k:b[k] for k in ('file','sha256')} for b in catalog['books']]})
    if not (ROOT / 'evaluation/labels.json').exists():
        seed = secrets.randbits(64)
        order = ['single','before_debate','after_debate']
        random.Random(seed).shuffle(order)
        frozen(ROOT / 'evaluation/labels.json', dict(zip('ABC', order)))
        frozen(ROOT / 'evaluation/randomization.json', {'seed':seed})
    frozen(ROOT / 'freeze.json', {
        'protocol':PROTOCOL, 'context_sha256':digest(ctx),
        'catalog_sha256':digest((ROOT / 'table-catalog.json').read_bytes()),
        'images':images, 'system':source_manifest(REPO / 'paper_workspace'),
        'runner':source_manifest(Path(__file__).parent),
        'evaluation':{str(p.relative_to(REPO)):digest(p.read_bytes()) for p in (
            REPO / 'experiments/pra_debate_revision/evaluation.py',
            REPO / 'experiments/pra_evidence_workflow/evaluation.py')},
        'protocol_text':digest((REPO / 'docs/pra-claim-retest-protocol.md').read_bytes())})
    if not (ROOT / 'frozen-source').exists():
        for src, name in [(REPO / 'paper_workspace','paper_workspace'), (Path(__file__).parent,'experiment')]:
            shutil.copytree(src, ROOT / 'frozen-source' / name, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    return paper, catalog, images, ctx


def call(label, prompt, schema, images):
    verify_workspace(WORK)
    frozen(ROOT / 'requests' / (label + '.json'), {'prompt':prompt, 'schema':schema, 'images':images})
    write(ROOT / 'progress.json', {'status':'running','stage':label})
    print('Starting ' + label, flush=True)
    value = model_call(PROTOCOL, ROOT / 'execution', prompt, schema, label=label,
                       images=[Path(i['path']) for i in images])
    frozen(ROOT / 'raw' / (label + '.json'), value)
    return value


def save_candidates(label, value, paper, augmented, required):
    validate_review_contract(value, paper)
    checks = audit_checks(value, augmented, required)
    frozen(ROOT / 'audits' / (label + '-checks.json'), checks)
    candidates = save_review(WORK, value, label + '-candidates')
    selected = {**value, 'findings':[value['findings'][n-1] for n in value['selected_finding_numbers']],
                'claim_check_audit':checks, 'source_findings':candidates['findings']}
    review = save_review(WORK, selected, label)
    frozen(ROOT / 'responses' / (label + '.json'), review)
    return review


def run():
    paper, catalog, images, ctx = prepare()
    require_subscription(ROOT)
    if not 0 <= time.time() - read(ROOT / 'billing_confirmation.json')['checked_at'] < 86400:
        raise ValueError('Stale account credit check')
    augmented = evidence_paper(paper, catalog)
    common = COMMON.replace('Give at most five distinct, consequential findings',
        'Produce at most eight distinct candidate findings and select at most five by one-based selected_finding_numbers')
    common += '\nReturn only scientific questions with empty replacements. Keep all candidate comments together under 900 words. No quotas for defects. Both investigation and selection are your task in this one call. No tools or follow-up call are available to the initial reviewer. Use the complete delivered evidence. Claim_checks are an optional compact audit field unless further instructions require them. Source references must be exact.\n'
    shared = '\nTITLE:\n' + paper['title'] + '\nATTACHED IMAGES:\n' + json.dumps([{k:i[k] for k in ('id','label')} for i in images]) + '\nSOURCE PACKET:\n' + ctx
    single_raw = call('single', common + '\nPerform a thorough ordinary scientific peer review, testing your concerns against author explanations and selecting the most consequential supported questions.\n' + shared, CANDIDATE_REVIEW, images)
    single = save_candidates('single', single_raw, paper, augmented, False)
    before_raw = call('investigator', common + INVESTIGATE + shared, CANDIDATE_REVIEW, images)
    before = save_candidates('before-debate', before_raw, paper, augmented, True)
    ledger = issue_ledger(before_raw)
    frozen(ROOT / 'ledger.json', ledger)
    prompt = revision_prompt(paper, ctx, ledger).replace('Use the full manuscript below, original attached pages, and at most two optional source tool calls. Call a tool when missing context could change a consequential decision. Do not perform ritual lookups when the decisive evidence is already supplied.',
        'Use the complete delivered prose, reported cell register, and original attached pages. No tools are available in this run.')
    debate = call('debate', prompt + '\n' + FOCUSED_DEBATE, QUESTION_DEBATE, images)
    validate_review_contract(debate, paper, max_findings=5)
    structure = validate_revision(debate, ledger, augmented)
    frozen(ROOT / 'audits/debate.json', structure)
    final = save_review(WORK, revision_package(debate, ledger, structure), 'after-debate')
    frozen(ROOT / 'responses/after-debate.json', final)
    frozen(ROOT / 'generation-lock.json', {p.name:digest(p.read_bytes()) for p in sorted((ROOT / 'raw').glob('*.json')) if p.stem != 'evaluation'})
    conditions = {'single':single, 'before_debate':before, 'after_debate':final}
    mapping = read(ROOT / 'evaluation/labels.json')
    anonymous = {label:[{'finding_id':f'{label}{n}', **{k:f[k] for k in (
        'title','block_id','quote','kind','severity','comment','replacement','evidence_blocks','counterevidence')}}
        for n,f in enumerate(conditions[name]['findings'], 1)] for label,name in mapping.items()}
    frozen(ROOT / 'evaluation/anonymous.json', anonymous)
    prompt = INSTRUCTIONS + '\nThe table register supplies exact, source-addressed rows. Cite its t-prefixed row IDs as block_id with an exact substring of the rendered cell values in quote. Read outcome, model, and group labels from their own rows. Never invent filled-down labels or alter the quoted numeric precision. For prose use the original b-prefixed blocks. Equal question-only format applies to all conditions. Check every embedded premise, including claims that a measurement was never collected or that two differently defined tests should agree. An unresolved ambiguity should not automatically receive justified_concern.\nREVIEWS:\n' + json.dumps(anonymous, ensure_ascii=False) + shared
    grade = call('evaluation', prompt, EVALUATION, images)
    checked = audit(grade, anonymous, augmented, images)
    frozen(ROOT / 'evaluation/audit.json', checked)
    valid = set(checked['valid_rating_ids'])
    metrics = []
    for row in grade['conditions']:
        ratings = [r for r in row['ratings'] if r['finding_id'] in valid]
        metrics.append({'condition':mapping[row['label']], 'total':len(row['ratings']),
            'unscored':len(row['ratings'])-len(ratings),
            'assessments':{s:sum(r['assessment']==s for r in ratings) for s in (
                'justified_concern','justified_clarification','unsupported_allegation','unverifiable')},
            'excessive_requests':sum(r['resolution_proportionality']=='excessive' for r in ratings)})
    usage = jsonl(ROOT / 'execution/usage.jsonl')
    result = {'metrics':metrics, 'preferred':mapping.get(grade['preferred_label'],grade['preferred_label']),
        'preference_reason':grade['preference_reason'], 'calls':len(usage),
        'observed_tokens':sum(r['observed_tokens'] for r in usage),
        'limitations':PROTOCOL['limitations'], 'source_audit':'pending'}
    frozen(ROOT / 'automated-results.json', result)
    write(ROOT / 'progress.json', {'status':'automated_evaluation_complete','source_audit':'pending'})
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if args.prepare_only:
        paper, catalog, images, ctx = prepare()
        print(json.dumps({'blocks':len(paper['blocks']), 'table_rows':len(catalog['blocks']),
                          'context_characters':len(ctx), 'images':len(images)}))
    else:
        run()
