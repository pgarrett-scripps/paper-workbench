"""Immutable inputs, discrete source evidence, and bounded subscription calls."""

import importlib.util
import json
import shutil
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent/'peerreview_validation_v5'
spec = importlib.util.spec_from_file_location('previous_common', BASE/'common.py')
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
ROOT = HERE.parents[1]/'runs/pra-three-reviewers-3paper-v1'
read, write, Blocked = shared.read_json, shared.write_json, shared.StudyBlocked
lock = threading.Lock()
inflight = 0


def chunks(text):
    lines = text.splitlines()
    return {f'E{i//8+1:04d}': {'start': i+1, 'end': min(i+8,len(lines)), 'text': '\n'.join(lines[i:i+8])}
            for i in range(0,len(lines),8) if '\n'.join(lines[i:i+8]).strip()}


def source_text(evidence):
    return '\n\n'.join(f'[{key}]\n{row["text"]}' for key,row in evidence.items())


def resolve(ids, evidence):
    if len(ids) != len(set(ids)) or any(i not in evidence for i in ids):
        raise Blocked('Unknown or repeated source ID')
    return [{'id': i, **evidence[i]} for i in ids]


def render(f):
    return (f"{f['claim']}\nWhy it matters: {f['why_it_matters']}\n"
            f"Remedy: {f['remedy']}\nLimitations: {f['limitations']}\n"
            f"Evidence: {', '.join(f['evidence_ids']) or 'not located'}. "
            f"Counterevidence: {', '.join(f['counterevidence_ids']) or 'not located'}.")


def selected(ids, records):
    if len(ids)>5 or len(ids)!=len(set(ids)) or any(i not in records for i in ids):
        raise Blocked('Invalid concern selection')
    body='\n\n'.join(render(records[i]) for i in ids)
    if len(body.split())>900:
        raise Blocked('Selected complete findings exceed 900 words')
    return body


def prepare():
    if (ROOT/'manifest.json').exists():
        verify()
        return
    protocol=read(HERE/'protocol.json')
    parent=Path(protocol['parent_root'])
    old_spec=importlib.util.spec_from_file_location('retest_core',HERE.parent/'pra_findings_debate_recovery/core.py')
    old=importlib.util.module_from_spec(old_spec)
    old_spec.loader.exec_module(old)
    old.verify(parent)
    ROOT.mkdir(parents=True,exist_ok=True)
    for pid in protocol['paper_ids']:
        target=ROOT/'inputs'/pid
        target.mkdir(parents=True)
        for name in ['manuscript.txt','reference.json']:
            shutil.copy2(parent/'inputs'/pid/name,target/name)
        shutil.copy2(parent/'normalization'/pid/'single_agent/packet.json',target/'single_agent_packet.json')
        shutil.copy2(parent/'saved_baselines'/pid/'single_agent/review.md',target/'single_agent_review.md')
        shutil.copy2(parent/'saved_baselines'/pid/'single_agent/usage.jsonl',target/'single_agent_usage.jsonl')
        write(target/'source_chunks.json',chunks((target/'manuscript.txt').read_text()))
    shutil.copy2(parent/'parent_public_data_provenance.json',ROOT/'public_data_provenance.json')
    write(ROOT/'protocol.json',protocol)
    write(ROOT/'manifest.json',{'created_at':time.time(),'runner_files':shared.source_manifest(HERE),
          'shared_runner_files':shared.source_manifest(BASE),'input_files':shared.source_manifest(ROOT/'inputs'),
          'protocol_sha256':shared.digest(protocol),'parent_manifest_sha256':shared.digest((parent/'manifest.json').read_bytes())})
    write(ROOT/'status.json',{'stage':'prepared'})


def verify():
    protocol,manifest=read(ROOT/'protocol.json'),read(ROOT/'manifest.json')
    shared.validate_protocol(protocol)
    assert shared.digest(protocol)==manifest['protocol_sha256'], 'Frozen protocol changed'
    for path,key in [(HERE,'runner_files'),(BASE,'shared_runner_files'),(ROOT/'inputs','input_files')]:
        assert shared.source_manifest(path)==manifest[key], f'Frozen {key} changed'
    return protocol


def usage():
    return [r for p in (ROOT/'work').rglob('usage.jsonl') for r in shared.jsonl(p)]


def call(protocol,out,text,schema,label):
    global inflight
    identity=shared.digest({'prompt':text,'schema':schema,'tools':False,'protocol':protocol})
    cached=(out/'calls'/f'{identity}.json').exists()
    with lock:
        prior=usage()
        if not cached and (len(prior)+inflight>=protocol['max_total_calls'] or
                           sum(r.get('observed_tokens',0) for r in prior)>=protocol['max_total_tokens']):
            raise Blocked('Global experiment budget reached')
        inflight+=1
    try:
        return shared.model_call(protocol,out,text,schema,label=label)
    finally:
        with lock:
            inflight-=1
