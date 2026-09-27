"""Shared initial discovery and isolated sequential review continuations."""
import copy
import json
import shutil
from pathlib import Path

from paper_workspace.annotations import verify_workspace,normalize_review,save_review
from paper_workspace.evidence_handles import (build_registry,with_evidence_handles,
    constrain_manuscript_handles,hydrate_review_response,source_card_handles)
from paper_workspace.external_evidence import SourceClient,bind_sources
from paper_workspace.model_runtime import model_call,require_subscription
from paper_workspace.review_schema import REVIEW,with_external_evidence
from paper_workspace.reviewer import SELF_REVISION,HANDLE_INSTRUCTION,inspected_images
from paper_workspace.storage import read,write,digest


def original_prompt(shared):
    paths=list((shared/'execution/calls').glob('*.request.json'))
    if len(paths)!=1:raise ValueError('Shared first draft must have exactly one request')
    return read(paths[0])['prompt']


def prior_review_context(value):
    """Keep scientific history without duplicating workspace and audit metadata."""
    keys=('summary','findings','secondary_findings','limitations',
          'investigation_summary','discarded_hypotheses')
    return {key:copy.deepcopy(value[key]) for key in keys if key in value}


def source_images(base,stages):
    paper=verify_workspace(base/'workspace')
    paths=[Path(i['path']) for i in read(base/'images.json')]
    for stage in stages:
        for investigation in (stage/'investigations').glob('*'):
            if investigation.is_dir():
                paths.extend(p for p,label in inspected_images(paper,base/'workspace',investigation,10))
    unique={}
    for path in paths:unique.setdefault(digest(path.read_bytes()),path)
    if len(unique)>10:raise ValueError('Common image ceiling exceeded')
    return list(unique.values())


def sequential(root,base,out,protocol,billing,previous,final=False):
    if out.exists():raise ValueError('Sequential stage already prepared or attempted')
    paper=verify_workspace(base/'workspace')
    out.mkdir(parents=True)
    limit=2 if final else 4
    write(out/'protocol.json',protocol)
    shutil.copy2(billing,out/'billing_confirmation.json')
    require_subscription(out)
    sources=SourceClient(out/'sources',out/'source-cache',2 if final else 6,'current',protocol['literature_cutoff'])
    cards={}
    drafts=[]
    for parent in previous:
        value=read(parent/'editor-package.json')
        drafts.append(prior_review_context(value))
        for card in value.get('source_cards',[]):cards[card['evidence_id']]=card
        for path in (parent/'source-cache').glob('*'):
            if path.is_file():shutil.copy2(path,out/'source-cache'/path.name)
    write(out/'sources/cards.json',list(cards.values()))
    config={'paper':str(base/'workspace'),'output':str(out/'investigations/self-revision'),
        'cache':str(out/'source-cache'),'tool_limit':limit,'literature_cutoff':protocol['literature_cutoff'],
        'evidence_handles':True,'tool_profile':'domains-v1','source_state':str(out/'sources'),
        'external_request_limit':2 if final else 6,'evidence_mode':'current'}
    write(out/'execution/workspace/tool-config.json',config)
    schema=with_external_evidence(copy.deepcopy(REVIEW))
    if final:
        secondary=copy.deepcopy(schema['properties']['findings'])
        secondary['maxItems']=10
        schema['properties']['secondary_findings']=secondary
        schema['required'].append('secondary_findings')
        direction='This is the final ordinary revision. Return at most five primary findings under the 900-word comment budget, overriding earlier discovery directions. Put other useful supported or unresolved comments in secondary_findings, up to ten. Use an empty array when none warrant retention. Secondary questions must state uncertainty and must not present unresolved premises as established errors. Keep discarded_hypotheses for ideas you rejected. No category quotas.'
    else:
        schema['properties']['findings']['maxItems']=10
        direction='This is an intermediate ordinary revision. Return up to ten concise candidate findings, overriding earlier five-finding limits. Preserve useful concerns while seeking important omissions, and record rejected hypotheses. Do not manufacture issues to reach a count.'
    prompt=original_prompt(root/'shared').replace('At most 4 tool calls.',f'At most {limit} tool calls.')
    prompt+='\n'+SELF_REVISION.replace('You have at most two tool calls in this pass.',f'You have at most {limit} tool calls in this pass.')
    prompt+='\n'+direction+'\nYOUR PRIOR REVIEW DRAFTS, oldest to newest:\n'+json.dumps(drafts,ensure_ascii=False)
    prompt+=f'\nThis stage has at most {limit} tool calls and {2 if final else 6} external requests. Earlier-stage requests are recorded separately. These stage limits override earlier shared-allowance wording.'
    prompt+='\nPRIOR SOURCE CARDS:\n'+json.dumps([{**c,'evidence_handles':[h.model_record() for h in source_card_handles(c)]} for c in cards.values()],ensure_ascii=False)
    prompt+='\n'+HANDLE_INSTRUCTION
    active=constrain_manuscript_handles(with_evidence_handles(schema),build_registry(paper))
    images=source_images(base,previous)
    write(out/'manifest.json',{'previous':{str(p/'editor-package.json'):digest((p/'editor-package.json').read_bytes()) for p in previous},
        'images':{str(p):digest(p.read_bytes()) for p in images},'final':final,'tool_limit':limit})
    raw=model_call(protocol,out/'execution',prompt,active,tools=True,label='self-revision',images=images)
    write(out/'responses/model.json',raw)
    hydrated=hydrate_review_response(raw,build_registry(paper,sources.cards()))
    value=bind_sources(hydrated['response'],sources.cards())
    value['evidence_handle_audit']=hydrated['audit']
    write(out/'responses/hydrated.json',value)
    if final:
        extra=bind_sources({'findings':value['secondary_findings']},sources.cards())
        normalized=normalize_review(paper,extra,'secondary-'+digest(str(out))[:10])
        if any(f['placement']!='anchored' or f['invalid_evidence_blocks'] for f in normalized['findings']):
            raise ValueError('Invalid secondary evidence')
        value['secondary_findings']=normalized['findings']
    normal=save_review(base/'workspace',value,'sequential-'+digest(str(out))[:10])
    if any(f['placement']!='anchored' or f['invalid_evidence_blocks'] for f in normal['findings']):
        raise ValueError('Invalid sequential finding evidence')
    value['findings']=normal['findings']
    if final and (len(value['findings'])>5 or sum(len(f['comment'].split()) for f in value['findings'])>900):
        raise ValueError('Final review exceeds common word or finding budget')
    write(out/'editor-package.json',value)
    write(out/'progress.json',{'status':'complete'})
    return value
