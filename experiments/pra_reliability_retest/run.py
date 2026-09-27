"""Bounded repeat-paper development assessment with immutable input hashes."""
import argparse
import copy
import json
import secrets
import shutil
import time
from pathlib import Path
from paper_workspace.annotations import verify_workspace
from paper_workspace.evidence_handles import build_registry, model_catalog
from paper_workspace.judge_evidence import judge_schema, hydrate_judgment
from paper_workspace.model_runtime import jsonl, model_call, require_subscription
from paper_workspace.reviewer import review, inspected_images
from paper_workspace.storage import read, write, digest
from experiments.pra_debate_revision.evaluation import EVALUATION, INSTRUCTIONS, audit
from experiments.pra_prospective.core import _clean, _cards

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / 'runs/pra-reliability-retest-v2'
OLD = REPO / 'runs/pra-reliability-trial-v1'
BASE = OLD / 'inputs/ecology'
PACKET = OLD / 'packets/ecology'
PROTOCOL = {'provider': 'codex', 'model': 'gpt-5.6-sol', 'effort': 'medium',
    'held_out_runs_authorized': False, 'max_calls_per_condition': 1,
    'observed_token_stop': 200000, 'call_timeout_seconds': 900,
    'max_source_images': 10, 'image_budget_version': 'evidence-v1',
    'max_total_model_calls': 4, 'observed_token_launch_stop': 400000,
    'no_retries': True, 'study_type': 'repeat-paper development retest',
    'prior_run': str(OLD), 'version': 'reliability-retest-v2'}


def usage():
    rows = [r for p in ROOT.rglob('usage.jsonl') for r in jsonl(p)]
    return {'calls': len(list(ROOT.rglob('*.started.json'))),
            'observed_tokens': sum(r.get('observed_tokens', 0) for r in rows),
            'unknown': any(r.get('usage_unknown') for r in rows), 'receipts': len(rows)}


def verify():
    for name, sha in read(ROOT / 'seal.json')['files'].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError('Frozen input changed: ' + name)


def budget(required):
    verify()
    record = usage()
    if record['unknown'] or record['calls'] != record['receipts']:
        raise ValueError('Unresolved usage')
    if record['calls'] + required > 4 or record['observed_tokens'] >= 400000:
        raise ValueError('Retest budget exhausted')
    billing = read(ROOT / 'billing_confirmation.json')
    if not 0 <= time.time() - billing['checked_at'] < 86400:
        raise ValueError('Billing verification expired')
    require_subscription(ROOT)


def seal():
    if (ROOT / 'seal.json').exists():
        raise ValueError('Retest already sealed')
    write(ROOT / 'protocol.json', PROTOCOL)
    files = [ROOT / 'protocol.json', Path(__file__),
             REPO / 'experiments/pra_debate_revision/evaluation.py',
             REPO / 'experiments/pra_evidence_workflow/evaluation.py',
             REPO / 'experiments/pra_prospective/core.py']
    for directory in (REPO / 'paper_workspace', BASE, PACKET):
        files += [p for p in directory.rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and p.suffix != '.pyc']
    files += [Path(i['path']) for i in read(BASE / 'images.json')]
    record = {'created_at': time.time(), 'study_type': PROTOCOL['study_type'],
              'prior_exposure': 'Both prior reviews and the ecology failure have been inspected. This is not a fresh or confirmatory paper.',
              'files': {str(p): digest(p.read_bytes()) for p in sorted(set(files))}}
    write(ROOT / 'seal.json', record)
    for p in files:
        if p.is_relative_to(REPO) and not p.is_relative_to(REPO / 'runs'):
            dest = ROOT / 'frozen-source' / p.relative_to(REPO)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
    print('Development retest sealed', flush=True)


def generate(condition):
    budget(1 if condition == 'single' else 2)
    target = ROOT / condition
    if target.exists():
        raise ValueError('Generation already attempted')
    review(BASE / 'workspace', target, ROOT / 'billing_confirmation.json', '2026-09-25',
           mode='plain' if condition == 'single' else 'panel',
           scaffold_root='/home/ty/Repos/paper-scaffold', domain_support=True,
           evidence_mode='current', source_packet=PACKET,
           shared_images=[Path(i['path']) for i in read(BASE / 'images.json')])
    print(json.dumps({'condition': condition, 'usage': usage()}), flush=True)


def evaluate():
    budget(1)
    target = ROOT / 'evaluation'
    if target.exists():
        raise ValueError('Judge already prepared or attempted')
    for condition in ('single', 'pra'):
        if read(ROOT / condition / 'progress.json')['status'] != 'complete':
            raise ValueError('Judge requires validated complete reviews')
    reviews = {'single': read(ROOT / 'single/responses/plain-guarded.json'),
               'pra': read(ROOT / 'pra/editor-package.json')}
    order = ['single', 'pra']
    if secrets.randbits(1):
        order.reverse()
    allowed = ('title', 'block_id', 'quote', 'kind', 'severity', 'comment',
               'replacement', 'evidence_blocks', 'counterevidence', 'source_evidence')
    anonymous, mapping, cards = {}, {}, {}
    packet_hashes = {digest(p.read_bytes()) for p in PACKET.rglob('*') if p.is_file()}
    for label, condition in zip(('A', 'B'), order):
        mapping[label] = condition
        anonymous[label] = [{'finding_id': label + str(i),
                            **_clean({k: f[k] for k in allowed if k in f})}
                           for i, f in enumerate(reviews[condition]['findings'], 1)]
        cited = {s['evidence_id'] for f in anonymous[label] for s in f.get('source_evidence', [])}
        for card in _cards(reviews[condition]):
            if card['evidence_id'] not in cited:
                continue
            if card.get('raw_sha256') not in packet_hashes:
                raise ValueError('Source card not backed by frozen packet')
            if card['evidence_id'] in cards and cards[card['evidence_id']] != card:
                raise ValueError('Conflicting source cards')
            cards[card['evidence_id']] = card
        for f in anonymous[label]:
            for s in f.get('source_evidence', []):
                if not s['quote'] or s['quote'] not in cards.get(s['evidence_id'], {}).get('evidence_text', ''):
                    raise ValueError('Invalid cited source')
    paper = verify_workspace(BASE / 'workspace')
    images, paths, hashes = [], [], set()
    available = [(Path(i['path']), i['label']) for i in read(BASE / 'images.json')]
    for condition, stages in [('single', ['plain']), ('pra', ['workspace', 'debate'])]:
        for stage in stages:
            available += inspected_images(paper, BASE / 'workspace', ROOT / condition / 'investigations' / stage, 10)
    for path, label in available:
        sha = digest(path.read_bytes())
        if sha in hashes:
            continue
        dest = target / 'evidence' / ('image-' + str(len(images) + 1) + '.png')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        paths.append(dest)
        images.append({'id': 'image-' + str(len(images) + 1), 'label': label, 'sha256': sha})
        hashes.add(sha)
    if len(images) > 10:
        raise ValueError('Image limit exceeded')
    registry = build_registry(paper, list(cards.values()))
    schema = copy.deepcopy(EVALUATION)
    schema['properties']['conditions']['items']['properties']['label']['enum'] = ['A', 'B']
    schema['properties']['conditions'].update(minItems=2, maxItems=2)
    schema['properties']['preferred_label']['enum'] = ['A', 'B', 'tie', 'uncertain']
    schema = judge_schema(schema, registry, images)
    prompt = INSTRUCTIONS.replace('three anonymous', 'two anonymous')
    prompt += '\nREFERENCE FORMAT OVERRIDE: For text references return only evidence_handle selected from SOURCE SPANS. For image references return image_id and visual_observation. Never copy quotes or combine spans. Cite multiple handles when evidence crosses source blocks. Exact source identity does not prove scientific correctness.'
    prompt += '\nANONYMOUS REVIEWS:\n' + json.dumps(anonymous, ensure_ascii=False)
    prompt += '\nSOURCE SPANS, manuscript order followed by external cards:\n' + json.dumps(model_catalog(registry), ensure_ascii=False)
    prompt += '\nSOURCE IMAGES, attached in order:\n' + json.dumps(images, ensure_ascii=False)
    write(ROOT / 'private/condition-map.json', mapping)
    write(target / 'judge-inputs.json', {'anonymous': anonymous, 'source_cards': list(cards.values()),
        'images': images, 'schema': schema, 'prompt_sha256': digest(prompt),
        'registry_sha256': registry.manifest_sha256})
    raw = model_call(PROTOCOL, target / 'execution', prompt, schema, label='ecology-judge', images=paths)
    write(target / 'raw-model.json', raw)
    hydrated = hydrate_judgment(raw, registry, images)
    write(target / 'reference-audit.json', hydrated)
    value = hydrated['response']
    write(target / 'raw.json', value)
    judge_paper = {**paper, 'blocks': paper['blocks'] + [
        {'id': c['evidence_id'], 'text': c['evidence_text']} for c in cards.values() if c.get('eligible')]}
    checked = audit({**value, 'conditions': value['conditions'] + [{'label': 'C', 'ratings': [], 'matches': []}]},
                    {**anonymous, 'C': []}, judge_paper, images)
    write(target / 'audit.json', checked)
    valid = set(checked['valid_rating_ids'])
    metrics = []
    for row in value['conditions']:
        ratings = [r for r in row['ratings'] if r['finding_id'] in valid]
        metrics.append({'condition': mapping[row['label']], 'total': len(row['ratings']),
            'unscored': len(row['ratings']) - len(ratings),
            'assessments': {s: sum(r['assessment'] == s for r in ratings) for s in
                ('justified_concern', 'justified_clarification', 'unsupported_allegation', 'unverifiable')},
            'excessive_requests': sum(r['resolution_proportionality'] == 'excessive' for r in ratings)})
    result = {'preferred': mapping.get(value['preferred_label'], value['preferred_label']),
              'preference_reason': value['preference_reason'], 'metrics': metrics, 'usage': usage(),
              'limitations': ['Repeat-paper development assessment after inspecting prior outputs.',
                  'One blinded same-family model judge, no independent expert validation.',
                  'Same initial sources and tool budget, PRA uses twice the generation calls.']}
    write(target / 'results.json', result)
    verify()
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['seal', 'single', 'pra', 'judge'])
    args = parser.parse_args()
    if args.action == 'seal':
        seal()
    elif args.action == 'judge':
        evaluate()
    else:
        generate(args.action)
