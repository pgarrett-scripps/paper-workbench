"""Frozen matched review setup and bounded subscription execution."""

import importlib.util
import json
import re
import shutil
import threading
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'peerreview_validation_v5'
UTIL=HERE.parent/'pra_three_reviewers'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shared=load('matched_shared',BASE/'common.py')
utility=load('matched_utility',UTIL/'core.py')
shapes=load('matched_shapes',UTIL/'schemas.py')
ROOT=HERE.parents[1]/'runs/pra-matched-reviewers-3paper-v1'
read,write,Blocked=shared.read_json,shared.write_json,shared.StudyBlocked
chunks,source_text,resolve=utility.chunks,utility.source_text,utility.resolve
lock=threading.Lock()
inflight=0


def paragraphs(text):
    return [p.strip() for p in re.split(r'\n\s*\n',text.strip()) if p.strip()]


def usage():
    return [r for p in (ROOT/'work').rglob('usage.jsonl') for r in shared.jsonl(p)]


def prepare():
    if (ROOT/'manifest.json').exists():
        verify()
        return
    protocol=read(HERE/'protocol.json')
    parent=Path(protocol['parent_root'])
    _,old=shared.verify_study(parent)
    for pid in protocol['paper_ids']:
        item=next(p for p in old['papers'] if p['paper_id']==pid)
        dest=ROOT/'inputs'/pid
        dest.mkdir(parents=True,exist_ok=True)
        shutil.copy2(parent/item['manuscript'],dest/'manuscript.txt')
        shutil.copy2(parent/'evaluation'/pid/'reference/reference.json',dest/'reference.json')
        source=parent/'generation'/pid/'single_agent'
        candidates=[(p,read(p)) for p in (source/'calls').glob('*.json') if not p.name.endswith(('.request.json','.schema.json','.answer.json'))]
        candidates=[(p,r) for p,r in candidates if r.get('label')=='single_agent' and r.get('ok')]
        if len(candidates)!=1:raise Blocked('Expected one saved strong-agent generation response')
        path,response=candidates[0]
        request=read(path.with_name(path.stem+'.request.json'))
        write(dest/'review_request.json',request)
        write(dest/'reviewer_1_response.json',response)
        (dest/'reviewer_1.md').write_text(response['value']['content'])
        assert (source/'workspace/manuscript.txt').read_bytes()==(dest/'manuscript.txt').read_bytes()
        assert response['model_requested']==protocol['model'] and response['tools'] is True
        assert '-c' in response['command'] and 'model_reasoning_effort="medium"' in response['command']
        write(dest/'source_chunks.json',chunks((dest/'manuscript.txt').read_text()))
    shutil.copy2(parent/'public_data_provenance.json',ROOT/'public_data_provenance.json')
    write(ROOT/'protocol.json',protocol)
    write(ROOT/'manifest.json',{'created_at':time.time(),'runner_files':shared.source_manifest(HERE),
          'shared_files':shared.source_manifest(BASE),'utility_files':shared.source_manifest(UTIL),
          'input_files':shared.source_manifest(ROOT/'inputs'),'protocol_sha256':shared.digest(protocol),
          'parent_manifest_sha256':shared.digest((parent/'manifest.json').read_bytes())})
    write(ROOT/'status.json',{'stage':'prepared'})


def verify():
    protocol,manifest=read(ROOT/'protocol.json'),read(ROOT/'manifest.json')
    shared.validate_protocol(protocol)
    assert shared.digest(protocol)==manifest['protocol_sha256']
    for path,key in [(HERE,'runner_files'),(BASE,'shared_files'),(UTIL,'utility_files'),(ROOT/'inputs','input_files')]:
        assert shared.source_manifest(path)==manifest[key],f'Frozen {key} changed'
    return protocol


def is_network_failure(record):
    return not record.get('ok') and 'stream disconnected before completion' in record.get('error','')


def call(protocol,node,text,schema,label,manuscript=None):
    global inflight
    tools_enabled=manuscript is not None
    identity=shared.digest({'prompt':text,'schema':schema,'tools':tools_enabled,'protocol':protocol})
    for attempt in [1,2]:
        out=node/f'attempt_{attempt}'
        cache=out/'calls'/f'{identity}.json'
        if cache.exists():
            value=read(cache)
            if value.get('ok'):return value['value']
            if attempt==1 and is_network_failure(value):continue
            raise Blocked('Previous attempt failed and is not eligible for another retry')
        with lock:
            prior=usage()
            if len(prior)+inflight>=protocol['max_total_calls'] or sum(u.get('observed_tokens',0) for u in prior)>=protocol['max_total_tokens']:
                raise Blocked('Global experiment budget reached')
            if attempt==2:
                marker=node/'network_retry.json'
                if not marker.exists():
                    if len(list((ROOT/'work').rglob('network_retry.json')))>=protocol['max_network_retries']:
                        raise Blocked('Network retry allowance exhausted')
                    write(marker,{'authorized_policy':protocol['network_retry_policy'],'reserved_at':time.time()})
            inflight+=1
        try:
            if attempt==2:time.sleep(15)
            if manuscript is not None:
                (out/'workspace').mkdir(parents=True,exist_ok=True)
                (out/'workspace/manuscript.txt').write_text(manuscript)
            return shared.model_call(protocol,out,text,schema,tools=tools_enabled,label=label)
        except Exception:
            if attempt==1 and cache.exists() and is_network_failure(read(cache)):continue
            raise
        finally:
            with lock:inflight-=1
    raise Blocked('Both network attempts failed')


def index_findings(value,body,reviewer):
    source=paragraphs(body)
    used=set()
    records={}
    previous=0
    for n,item in enumerate(value['concerns'],1):
        ids=item['paragraph_ids']
        if not ids or ids!=sorted(set(ids)) or any(type(i) is not int or not 1<=i<=len(source) for i in ids):
            raise Blocked('Invalid source paragraph IDs')
        if min(ids)<=previous or used.intersection(ids):raise Blocked('Extraction reordered or duplicated source text')
        used.update(ids)
        previous=max(ids)
        quote='\n\n'.join(source[i-1] for i in ids)
        fid=f'{reviewer}_F{n}'
        records[fid]={'id':fid,'reviewer':reviewer,'source_paragraph_ids':ids,'text':quote,'text_sha256':shared.digest(quote.encode())}
    return records


def top_packet(order,records):
    if len(order)!=len(set(order)) or any(i not in records for i in order):raise Blocked('Invalid ranking')
    selected=[]
    words=0
    for fid in order[:5]:
        count=len(records[fid]['text'].split())
        if words+count>900:break
        selected.append(fid)
        words+=count
    return {'ids':selected,'words':words,'omitted_for_word_budget':order[len(selected):5]}


def metrics_usage():
    totals={'attempts':len(usage()),'observed_tokens':0,'cached_input_tokens':0,'uncached_input_tokens':0,'output_tokens':0,'unknown_usage_calls':0}
    for p in (ROOT/'work').glob('**/calls/*.json'):
        r=read(p)
        if 'label' not in r or 'request_sha256' not in r:continue
        if 'observed_tokens' not in r:
            totals['unknown_usage_calls']+=1
            continue
        totals['observed_tokens']+=r['observed_tokens']
        for event in r.get('events',[]):
            if event.get('type')!='turn.completed':continue
            u=event['usage']
            cached=u.get('cached_input_tokens',0)
            totals['cached_input_tokens']+=cached
            totals['uncached_input_tokens']+=max(0,u.get('input_tokens',0)-cached)
            totals['output_tokens']+=u.get('output_tokens',0)
    return totals
