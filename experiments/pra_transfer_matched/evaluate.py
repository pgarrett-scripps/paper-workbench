"""Anonymous source-based assessment for fresh matched-pass comparisons."""
import copy
import json
import secrets
import shutil
from pathlib import Path
from paper_workspace.annotations import verify_workspace
from paper_workspace.evidence_handles import build_registry, model_catalog
from paper_workspace.judge_evidence import judge_schema, hydrate_judgment
from paper_workspace.model_runtime import model_call
from paper_workspace.reviewer import inspected_images
from paper_workspace.storage import read, write, digest
from experiments.pra_debate_revision.evaluation import EVALUATION, INSTRUCTIONS, audit
from experiments.pra_prospective.core import _clean, _cards

def evaluate(ROOT, BASE, PACKET, PROTOCOL, budget, verify, usage):
    budget(1)
    target = ROOT / 'evaluation'
    if target.exists():
        raise ValueError('Judge already prepared or attempted')
    for condition in ('single', 'pra'):
        if read(ROOT / condition / 'progress.json')['status'] != 'complete':
            raise ValueError('Judge requires validated complete reviews')
    reviews = {'single': read(ROOT / 'single/responses/self-revision-guarded.json'),
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
    for condition, stages in [('single', ['plain', 'self-revision']), ('pra', ['workspace', 'debate'])]:
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
              'limitations': ['Two locally fresh manuscripts selected before generation. This is a small development study, not confirmatory validation.',
                  'One blinded same-family model judge, no independent expert validation.',
                  'Both conditions use two generation calls and a four-plus-two tool allowance. Actual tokens are reported separately.']}
    write(target / 'results.json', result)
    verify()
    print(json.dumps(result), flush=True)
