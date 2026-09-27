"""Frozen experiment inputs, exact evidence spans, and subscription calls."""

import importlib.util
import json
import random
import re
import shutil
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'peerreview_validation_v5'
_shared_spec = importlib.util.spec_from_file_location('pra_previous_common', BASE / 'common.py')
shared = importlib.util.module_from_spec(_shared_spec)
_shared_spec.loader.exec_module(shared)

ROOT = HERE.parents[1] / 'runs/pra-findings-debate-3paper-v1'
read = shared.read_json
write = shared.write_json
Blocked = shared.StudyBlocked


def paragraphs(text):
    return [p.strip() for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]


def numbered(text):
    return '\n'.join(f'L{i}: {line}' for i, line in enumerate(text.splitlines(), 1))


def resolve_spans(spans, manuscript):
    lines = manuscript.splitlines()
    result = []
    for span in spans:
        a, b = span.get('start'), span.get('end')
        if type(a) is not int or type(b) is not int or not 1 <= a <= b <= len(lines) or b-a >= 8:
            raise Blocked(f'Invalid manuscript span: {span}')
        text = '\n'.join(lines[a-1:b])
        if not text.strip():
            raise Blocked('Evidence span contains no text')
        result.append({'start': a, 'end': b, 'text': text})
    return result


def attach_evidence(row, manuscript):
    value = dict(row)
    try:
        value['resolved_evidence'] = resolve_spans(row.get('evidence', []), manuscript)
        value['evidence_spans_valid'] = True
    except Blocked as exc:
        value['resolved_evidence'] = []
        value['evidence_spans_valid'] = False
        value['evidence_error'] = str(exc)
    if 'counterevidence' in row:
        try:
            value['resolved_counterevidence'] = resolve_spans(row['counterevidence'], manuscript)
            value['counterevidence_spans_valid'] = True
        except Blocked as exc:
            value['resolved_counterevidence'] = []
            value['counterevidence_spans_valid'] = False
            value['counterevidence_error'] = str(exc)
    return value


def exactly_ids(rows, expected, key='finding_id'):
    actual = [row[key] for row in rows]
    if len(actual) != len(set(actual)) or set(actual) != set(expected):
        raise Blocked(f'Missing, unknown, or duplicate {key} values')


def prepare(root):
    protocol = read(HERE / 'protocol.json')
    parent = Path(protocol['parent_root'])
    _, old = shared.verify_study(parent)
    chosen = list(old['papers'])
    random.Random(protocol['seed']).shuffle(chosen)
    chosen = chosen[:3]
    if [p['paper_id'] for p in chosen] != protocol['paper_ids']:
        raise Blocked('Protocol IDs do not match the fixed sampling rule')
    if (root / 'manifest.json').exists():
        verify(root)
        return
    root.mkdir(parents=True, exist_ok=True)
    manifest = {'created_at': time.time(), 'papers': [], 'parent_manifest_sha256': shared.digest((parent/'manifest.json').read_bytes())}
    for item in chosen:
        pid = item['paper_id']
        target = root / 'inputs' / pid
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(parent / item['manuscript'], target / 'manuscript.txt')
        shutil.copy2(parent / 'evaluation' / pid / 'reference/reference.json', target / 'reference.json')
        for condition, original in [('pra_original', 'pra_full'), ('single_agent', 'single_agent')]:
            source = parent / 'generation' / pid / original
            destination = root / 'saved_baselines' / pid / condition
            destination.mkdir(parents=True, exist_ok=True)
            for name in ['review.md', 'result.json', 'usage.jsonl']:
                shutil.copy2(source/name, destination/name)
        manifest['papers'].append({'paper_id': pid, 'title': item['title'], 'source_url': item['source_url'],
                                   'version_verified': False, 'prior_development_exposure': True})
    shutil.copytree(parent/'source/peerreviewagents', root/'source/peerreviewagents',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(parent/'public_data_provenance.json', root/'parent_public_data_provenance.json')
    write(root/'protocol.json', protocol)
    for name in ['inputs', 'saved_baselines', 'source']:
        manifest[name+'_files'] = shared.source_manifest(root/name)
    manifest['runner_files'] = shared.source_manifest(HERE)
    manifest['shared_runner_files'] = shared.source_manifest(BASE)
    manifest['protocol_sha256'] = shared.digest(protocol)
    write(root/'manifest.json', manifest)
    write(root/'status.json', {'stage': 'prepared', 'scientific_results': False})
    print('Prepared fixed three-paper development test', flush=True)


def verify(root):
    protocol, manifest = read(root/'protocol.json'), read(root/'manifest.json')
    shared.validate_protocol(protocol)
    if shared.digest(protocol) != manifest['protocol_sha256']:
        raise Blocked('Protocol changed after freezing')
    for name in ['inputs', 'saved_baselines', 'source']:
        if shared.source_manifest(root/name) != manifest[name+'_files']:
            raise Blocked(f'Frozen {name} changed')
    if shared.source_manifest(HERE) != manifest['runner_files'] or shared.source_manifest(BASE) != manifest['shared_runner_files']:
        raise Blocked('Frozen runner changed. A changed attempt requires a separate root.')
    return protocol, manifest


def call(root, protocol, out, prompt, schema, label):
    identity = shared.digest({'prompt': prompt, 'schema': schema, 'tools': False, 'protocol': protocol})
    cached = out/'calls'/f'{identity}.json'
    if not cached.exists():
        usage = [row for p in root.glob('**/usage.jsonl') if 'saved_baselines' not in p.parts for row in shared.jsonl(p)]
        if len(usage) >= protocol['max_total_calls'] or sum(r.get('observed_tokens',0) for r in usage) >= protocol['max_total_tokens']:
            raise Blocked('Global subset budget reached')
    return shared.model_call(protocol, out, prompt, schema, label=label)


def packet_from_paragraphs(value, review, maximum=900):
    source = paragraphs(review)
    if len(value['concerns']) > 5:
        raise Blocked('Too many normalized concerns')
    used, concerns = set(), []
    for i, row in enumerate(value['concerns'], 1):
        ids = row['paragraph_ids']
        if not ids or len(ids) != len(set(ids)) or any(type(n) is not int or not 1 <= n <= len(source) for n in ids):
            raise Blocked('Invalid selected paragraph IDs')
        if used.intersection(ids):
            raise Blocked('A paragraph was counted in more than one concern')
        used.update(ids)
        quote = '\n\n'.join(source[n-1] for n in sorted(ids))
        concerns.append({'id': f'C{i}', 'source_quote': quote, 'source_paragraph_ids': sorted(ids)})
    if sum(len(c['source_quote'].split()) for c in concerns) > maximum:
        raise Blocked('Normalized packet exceeds common word limit')
    return concerns
