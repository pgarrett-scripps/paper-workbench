"""Shared first-pass branches for the four-condition development pilot."""
import json
import shutil
import time
from pathlib import Path
from paper_workspace.annotations import verify_workspace, save_review
from paper_workspace.evidence_handles import (build_registry, with_evidence_handles,
    constrain_manuscript_handles, hydrate_review_response, source_card_handles)
from paper_workspace.external_evidence import SourceClient, bind_sources, validate_references
from paper_workspace.model_runtime import model_call, source_manifest, require_subscription
from paper_workspace.review_schema import COMMON, REVIEW, with_external_evidence
from paper_workspace.reviewer import HANDLE_INSTRUCTION, SELF_REVISION, handle_manuscript
from paper_workspace.storage import read, write, digest


def schema_for(paper, external=False):
    schema=with_external_evidence(REVIEW) if external else REVIEW
    return constrain_manuscript_handles(with_evidence_handles(schema),build_registry(paper))


def guarded_call(base,out,protocol,prompt,label,images,tools=False,sources=None):
    paper=verify_workspace(base/'workspace')
    raw=model_call(protocol,out/'execution',prompt,schema_for(paper,sources is not None),
                   tools=tools,label=label,images=images)
    write(out/'responses'/(label+'-model.json'),raw)
    hydrated=hydrate_review_response(raw,build_registry(paper,sources.cards() if sources else []))
    value={**hydrated['response'],'evidence_handle_audit':hydrated['audit']}
    if sources:
        value=bind_sources(value,sources.cards())
        value['source_validation']=validate_references(value,sources.cards())
    write(out/'responses'/(label+'.json'),value)
    normalized=save_review(base/'workspace',value,label+'-'+digest(str(out))[:10])
    if any(f['placement']!='anchored' or f['invalid_evidence_blocks'] for f in normalized['findings']):
        raise ValueError('Invalid manuscript evidence in review')
    value={**value,'findings':normalized['findings']}
    write(out/'responses'/(label+'-guarded.json'),value)
    return value


def prepare_out(root,out,protocol):
    if out.exists():raise ValueError('Generation directory already exists')
    out.mkdir(parents=True)
    write(out/'protocol.json',protocol)
    shutil.copy2(root/'billing_confirmation.json',out/'billing_confirmation.json')
    require_subscription(out)


def basic(root,base,out,protocol,budget):
    protocol={**protocol,'max_calls_per_condition':2,'observed_token_stop':250000}
    prepare_out(root,out,protocol)
    paper=verify_workspace(base/'workspace')
    images=[Path(i['path']) for i in read(base/'images.json')]
    prompt=COMMON+'\nGive your best scientific peer review of the supplied manuscript and figures. No tools or external resources are available. Assess only supplied evidence.\n'+HANDLE_INSTRUCTION
    prompt+='\nSOURCE SCOPE: Full extracted main text, references and supplied small supplements. Raw datasets and public peer-review histories are excluded.\n'+json.dumps({'title':paper['title'],'assets':paper['assets'],'references':paper['references']},ensure_ascii=False)
    prompt+='\n'+handle_manuscript(paper)+'\nAttached images are original manuscript figure pages in the supplied order.'
    budget(1)
    first=guarded_call(base,out,protocol,prompt,'first',images)
    write(out/'first-complete.json',{'status':'complete','condition':'basic_one'})
    revision=prompt+'\n'+SELF_REVISION.replace('You have at most two tool calls in this pass.','No tools or external resources are available.')
    revision+='\nYOUR PRIOR DRAFT:\n'+json.dumps(first,ensure_ascii=False)
    budget(1)
    second=guarded_call(base,out,protocol,revision,'second',images)
    write(out/'editor-package.json',second)
    write(out/'progress.json',{'status':'complete','conditions':['basic_one','basic_two']})


def restore_checkpoint(checkpoint,out,workspace):
    expected=read(checkpoint/'manifest.json')['files']
    observed=source_manifest(checkpoint)
    observed.pop('manifest.json',None)
    if expected!=observed:raise ValueError('Investigator checkpoint changed')
    initial=read(checkpoint/'input.json')
    for name in ('sources','source-cache'):
        if (checkpoint/name).exists():shutil.copytree(checkpoint/name,out/name)
    config={**initial['tool_config'],'paper':str(workspace),'output':str(out/'investigations/self-revision'),
            'cache':str(out/'source-cache'),'source_state':str(out/'sources'),'tool_limit':2}
    write(out/'execution/workspace/tool-config.json',config)
    for image in initial['images']:
        if digest(Path(image['path']).read_bytes())!=image['sha256']:
            raise ValueError('Checkpoint source image changed')
    return initial


def workspace_branch(root,base,out,protocol,budget):
    prepare_out(root,out,protocol)
    checkpoint=out.parent/'pra/initial-checkpoint'
    initial=restore_checkpoint(checkpoint,out,base/'workspace')
    sources=SourceClient(out/'sources',out/'source-cache',6,'current','2026-09-25')
    prompt=initial['prompt'].replace('At most 4 tool calls.','At most 2 tool calls.')
    prompt+='\n'+SELF_REVISION+'\nThe initial investigation is complete. Return the final ordinary review schema, not a new investigation inventory. Consider the full prior inventory below, including discarded and unresolved hypotheses.\nYOUR PRIOR INVESTIGATION:\n'+json.dumps(initial['review'],ensure_ascii=False)
    prompt+='\nPRIOR SOURCE CARDS:\n'+json.dumps([{**c,'evidence_handles':[h.model_record() for h in source_card_handles(c)]} for c in sources.cards()],ensure_ascii=False)
    budget(1)
    value=guarded_call(base,out,protocol,prompt,'self-revision',[Path(i['path']) for i in initial['images']],True,sources)
    write(out/'editor-package.json',value)
    write(out/'shared-first-pass.json',{'source':str(checkpoint),'manifest_sha256':digest((checkpoint/'manifest.json').read_bytes()),
        'accounting':'Include the PRA investigator receipt in logical condition cost, but count it once in incremental study usage.'})
    write(out/'progress.json',{'status':'complete'})
