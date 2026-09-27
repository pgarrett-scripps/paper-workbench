"""Four-paper domain development panel with frozen sources and bounded inference."""
import argparse
import json
from pathlib import Path
import random
import secrets
import shutil
import time

from paper_workspace.annotations import verify_workspace
from paper_workspace.external_evidence import SourceClient
from paper_workspace.model_runtime import model_call, source_manifest, jsonl, require_subscription
from paper_workspace.reviewer import review, inspected_images
from paper_workspace.storage import read, write, digest
from experiments.pra_debate_revision.evaluation import EVALUATION, INSTRUCTIONS, audit

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO/'runs/pra-domains-v1'
KEYS = ('development', 'chemistry', 'health', 'ecology')
PROTOCOL = {'provider': 'codex', 'model': 'gpt-5.6-sol', 'effort': 'medium',
            'held_out_runs_authorized': False, 'max_calls_per_condition': 1,
            'observed_token_stop': 180000, 'call_timeout_seconds': 900,
            'max_source_images': 10, 'image_budget_version': 'evidence-v1',
            'version': 'domain-panel-v1', 'study_role': 'development_and_frozen_transfer',
            'max_total_model_calls': 16, 'max_total_observed_tokens': 1300000,
            'limitation': 'Exploratory present-day review of four published manuscripts. Three transfer papers are frozen after development. Not historical human-review overlap or equal-compute superiority.'}


def frozen(path, value):
    if path.exists() and read(path) != value:
        raise ValueError('Frozen artifact changed: ' + str(path))
    if not path.exists():
        write(path, value)


def check_budget(required):
    attempts = list((ROOT/'panel').glob('**/*.started.json'))
    receipts = [row for path in (ROOT/'panel').glob('**/usage.jsonl') for row in jsonl(path)]
    if len(attempts) + required > PROTOCOL['max_total_model_calls']:
        raise ValueError('Panel model-call budget is exhausted')
    if any(row.get('usage_unknown') for row in receipts):
        raise ValueError('Panel has an unaccounted model-call cost')
    if sum(row.get('observed_tokens', 0) for row in receipts) >= PROTOCOL['max_total_observed_tokens']:
        raise ValueError('Panel observed-token stop reached')
    billing = read(ROOT/'billing_confirmation.json')
    if not 0 <= time.time()-billing['checked_at'] < 86400:
        raise ValueError('Refresh the account credit verification before launching')


def prepare_development():
    target = ROOT/'heldout-inputs/development'
    original = REPO/'runs/pra-transfer-two-v1/yeast'
    if not (target/'workspace').exists():
        shutil.copytree(original/'workspace', target/'workspace',
                        ignore=shutil.ignore_patterns('reviews', 'decisions', 'exports', 'revisions'))
    # The existing published manuscript is explicitly development, not fresh validation.
    images = read(original/'images.json')[:3]
    frozen(target/'images.json', images)
    paper = verify_workspace(target/'workspace')
    frozen(target/'selection.json', {'title': paper['title'], 'doi': '10.1371/journal.pbio.3002491',
        'role': 'previously_seen_development', 'candidate_records': [
            {'provider': 'crossref', 'identifier': '10.1371/journal.pbio.3002491'}],
        'limitations': ['Three shared original figure pages. Remaining supplied figures are available through bounded manuscript tools.',
                       'Previously used development paper. Its result is not fresh confirmation.']})


def prepare_packet(key):
    source = ROOT/'heldout-inputs'/key
    paper = verify_workspace(source/'workspace')
    selected = read(source/'selection.json')
    records = selected.get('candidate_records', [])[:6]
    packet = ROOT/'packets'/key
    client = SourceClient(ROOT/'packet-preparation'/key, packet, limit=12, cutoff='2026-09-25')
    statuses = []
    for item in records:
        card = client.lookup(item['provider'], item['identifier'], 'public-source-preparation')
        statuses.append({'provider': item['provider'], 'identifier': item['identifier'], 'status': card['status']})
    frozen(packet/'index.json', {'records': statuses,
        'limitation': 'Finite public source packet prepared before review generation. Unlisted searches and records are unavailable. This does not establish historical availability.'})
    frozen(ROOT/'panel'/key/'input.json', {'source': str(source), 'paper_id': paper['id'],
        'manuscript_manifest': digest((source/'workspace/manifest.json').read_bytes()),
        'selection': digest((source/'selection.json').read_bytes()),
        'images': read(source/'images.json'), 'packet': source_manifest(packet)})


def freeze(key):
    root = ROOT/'panel'/key
    source = ROOT/'heldout-inputs'/key
    expected = read(root/'input.json')
    verify_workspace(source/'workspace')
    if digest((source/'workspace/manifest.json').read_bytes()) != expected['manuscript_manifest']:
        raise ValueError('Frozen manuscript changed')
    if digest((source/'selection.json').read_bytes()) != expected['selection'] or read(source/'images.json') != expected['images']:
        raise ValueError('Frozen source selection changed')
    if source_manifest(ROOT/'packets'/key) != expected['packet']:
        raise ValueError('Frozen source packet changed')
    for item in expected['images']:
        if digest(Path(item['path']).read_bytes()) != item['sha256']:
            raise ValueError('Frozen source image changed')
    version = 'development' if key == 'development' else 'transfer'
    amendment = read(ROOT/'execution-budget-amendment.json')
    if amendment['model_call_ceiling'] != 16 or amendment['new_observed_token_launch_stop'] != PROTOCOL['max_total_observed_tokens']:
        raise ValueError('Execution budget amendment does not match the bounded protocol')
    original = read(ROOT/(version+'-freeze.json'))
    if original['system'] != source_manifest(REPO/'paper_workspace'):
        raise ValueError('Scientific implementation changed after the original freeze')
    frozen(ROOT/(version+'-execution-v2-freeze.json'), {'system': source_manifest(REPO/'paper_workspace'),
        'runner': source_manifest(Path(__file__).parent), 'protocol': PROTOCOL,
        'transfer_inputs': {k:digest((ROOT/'panel'/k/'input.json').read_bytes()) for k in KEYS[1:]} if version=='transfer' else {},
        'execution_budget_amendment': digest((ROOT/'execution-budget-amendment.json').read_bytes()),
        'evaluator': {str(p.relative_to(REPO)):digest(p.read_bytes()) for p in (
            REPO/'experiments/pra_debate_revision/evaluation.py', REPO/'experiments/pra_evidence_workflow/evaluation.py')}})
    return root, source, expected


def run(key, stage):
    root, source, expected = freeze(key)
    images = [Path(i['path']) for i in expected['images']]
    write(ROOT/'protocol.json', PROTOCOL)
    require_subscription(ROOT)
    if stage in ('single', 'panel'):
        output = root/stage
        if (output/'progress.json').exists():
            if read(output/'progress.json')['status'] == 'complete':
                print('Already completed: '+key+' '+stage)
                return
            raise ValueError('An earlier generation attempt needs inspection. No automatic retry.')
        check_budget(1 if stage == 'single' else 2)
        review(source/'workspace', output, ROOT/'billing_confirmation.json', '2026-09-25',
               mode='plain' if stage == 'single' else 'panel',
               scaffold_root='/home/ty/Repos/paper-scaffold', domain_support=True,
               evidence_mode='current', source_packet=ROOT/'packets'/key, shared_images=images)
    else:
        if (root/'evaluation/results.json').exists():
            print('Already evaluated: '+key)
            return
        if any(read(root/c/'progress.json')['status'] != 'complete' for c in ('single', 'panel')):
            raise ValueError('Both generation conditions must pass before preference evaluation')
        check_budget(1)
        conditions = {'single': read(root/'single/responses/plain-guarded.json'),
                      'before_debate': read(root/'panel/responses/workspace-guarded.json'),
                      'after_debate': read(root/'panel/editor-package.json')}
        frozen(root/'generation-lock.json', {k:digest(json.dumps(v,sort_keys=True)) for k,v in conditions.items()})
        mapping_path = root/'evaluation/labels.json'
        if not mapping_path.exists():
            order = list(conditions)
            seed = secrets.randbits(64)
            random.Random(seed).shuffle(order)
            frozen(mapping_path, dict(zip('ABC', order)))
            frozen(root/'evaluation/randomization.json', {'seed': seed})
        mapping = read(mapping_path)
        anonymous = {label:[{'finding_id':f'{label}{n}', **{k:f.get(k) for k in
            ('title','block_id','quote','kind','severity','comment','replacement','evidence_blocks','counterevidence','source_evidence')}}
            for n,f in enumerate(conditions[condition]['findings'],1)] for label,condition in mapping.items()}
        frozen(root/'evaluation/anonymous.json', anonymous)
        paper = verify_workspace(source/'workspace')
        cards = {c['evidence_id']: c for review_value in conditions.values() for c in review_value.get('source_cards', [])}
        judge_paper = {**paper, 'blocks': paper['blocks'] + [
            {'id':c['evidence_id'], 'text':c['evidence_text']} for c in cards.values() if c.get('eligible')]}
        evidence_images = list(expected['images'])
        hashes = {i['sha256'] for i in evidence_images}
        for condition, stages in [('single',['plain']),('panel',['workspace','debate'])]:
            for name in stages:
                for path, label in inspected_images(paper, source/'workspace', root/condition/'investigations'/name, limit=10):
                    sha = digest(path.read_bytes())
                    if sha not in hashes:
                        evidence_images.append({'id':'image-'+str(len(evidence_images)+1), 'path':str(path), 'label':label, 'sha256':sha})
                        hashes.add(sha)
        if len(evidence_images)>10:
            raise ValueError('Judge image packet exceeds its cap. No silent image truncation.')
        frozen(root/'evaluation/images.json', evidence_images)
        prompt = INSTRUCTIONS + '\nThis is a cross-domain manuscript. Apply its appropriate methods, not an experimental-biology checklist. Eligible external source cards can be cited using their evidence_id as block_id and exact evidence_text quotes. A successful lookup does not validate interpretation.\nANONYMOUS REVIEWS:\n' + json.dumps(anonymous,ensure_ascii=False)
        prompt += '\nFULL MANUSCRIPT:\n' + (source/'workspace/manuscript.md').read_text()
        prompt += '\nSOURCE CARDS:\n' + json.dumps(list(cards.values()),ensure_ascii=False)
        prompt += '\nSOURCE IMAGES:\n' + json.dumps(evidence_images)
        value = model_call(PROTOCOL, root/'evaluation/execution', prompt, EVALUATION,
                           label=key+'-judge', images=[Path(i['path']) for i in evidence_images])
        frozen(root/'evaluation/raw.json', value)
        checked = audit(value, anonymous, judge_paper, evidence_images)
        frozen(root/'evaluation/audit.json', checked)
        valid = set(checked['valid_rating_ids'])
        result = {'preferred': mapping.get(value['preferred_label'],value['preferred_label']),
                  'preference_reason':value['preference_reason'], 'metrics':[], 'source_audit':'pending',
                  'limitation':'One anonymous model judge with source-identity checks. Not independent expert validation.'}
        for row in value['conditions']:
            ratings = [r for r in row['ratings'] if r['finding_id'] in valid]
            result['metrics'].append({'condition':mapping[row['label']], 'total':len(row['ratings']),
                'unscored':len(row['ratings'])-len(ratings),
                'assessments':{s:sum(r['assessment']==s for r in ratings) for s in
                    ('justified_concern','justified_clarification','unsupported_allegation','unverifiable')}})
        frozen(root/'evaluation/results.json',result)
    print(json.dumps({'paper':key,'stage':stage,'status':'complete'}), flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('paper',choices=KEYS)
    parser.add_argument('stage',choices=('prepare','single','panel','evaluate'))
    args=parser.parse_args()
    if args.paper=='development' and args.stage=='prepare':
        prepare_development()
    prepare_packet(args.paper) if args.stage=='prepare' else run(args.paper,args.stage)
