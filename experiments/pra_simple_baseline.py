"""Two-call tool-free baseline against two preserved workspace reviews."""
import copy
import itertools
import json
import time
from pathlib import Path

from experiments.pra_debate_revision.evaluation import INSTRUCTIONS, audit
from experiments.pra_ensemble_fresh.evaluate import (_schema, _images, _records, PRIMARY_FIELDS,
    ASSESSMENTS, validate_issue_partition, validate_criticized_excerpt)
from experiments.pra_prospective.core import _clean
from experiments.pra_three_condition.generate import guarded_call, prepare_out
from paper_workspace.annotations import verify_workspace
from paper_workspace.ensemble import check_budget, observed_usage
from paper_workspace.evidence_handles import build_registry, model_catalog
from paper_workspace.judge_evidence import judge_schema, hydrate_judgment
from paper_workspace.model_runtime import model_call, require_subscription
from paper_workspace.review_schema import COMMON
from paper_workspace.reviewer import HANDLE_INSTRUCTION, handle_manuscript
from paper_workspace.run_state import tracked_stage
from paper_workspace.storage import read, write, digest

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/'runs/pra-simple-baseline-v1'
OLD=REPO/'runs/pra-ensemble-clarification-v1'
BASE=OLD/'inputs/fresh'
MAPPING={'A':'workspace','B':'basic','C':'ensemble'}
PROTOCOL={'version':'simple-baseline-v1','provider':'codex','model':'gpt-5.6-terra','effort':'medium',
    'held_out_runs_authorized':False,'max_calls_per_condition':1,'observed_token_stop':400000,
    'call_timeout_seconds':900,'max_source_images':10,'image_budget_version':'evidence-v1',
    'max_new_calls':2,'observed_token_launch_ceiling':400000,'automatic_retries':False,
    'mapping':MAPPING,'logical_passes':{'basic':1,'workspace':3,'ensemble':3},
    'scope':'Retrospective one-paper development comparison. Existing workspace outputs and their earlier assessment were known to the coordinator, never supplied to baseline or judge.'}


def baseline_prompt(paper):
    return (COMMON+'\nGive your best scientific peer review of the supplied manuscript and figures. '
        'No tools or external resources are available. Assess only supplied evidence.\n'+HANDLE_INSTRUCTION+
        '\nSOURCE SCOPE: Full extracted main text, references and supplied small supplements. '
        'Raw datasets and public peer-review histories are excluded.\n'+
        json.dumps({'title':paper['title'],'assets':paper['assets'],'references':paper['references']},ensure_ascii=False)+
        '\n'+handle_manuscript(paper)+'\nAttached images are original manuscript figure pages in the supplied order.')


def comparison_schema():
    schema=_schema()
    schema['properties']['preferred_label']['enum']=['A','B','C','tie','uncertain']
    schema['properties']['pairwise']={'type':'array','minItems':3,'maxItems':3,'items':{
        'type':'object','additionalProperties':False,'properties':{
            'label_a':{'type':'string','enum':['A','B','C']},
            'label_b':{'type':'string','enum':['A','B','C']},
            'preferred_label':{'type':'string','enum':['A','B','C','tie','uncertain']},
            'reason':{'type':'string','minLength':1}},
        'required':['label_a','label_b','preferred_label','reason']}}
    schema['required'].append('pairwise')
    return schema


def audit_comparison(value, anonymous, paper, images):
    checked=audit(value,anonymous,paper,images)
    invalid={r['finding_id'] for r in checked['invalid_ratings']}
    for row in value['conditions']:
        findings={f['finding_id']:f for f in anonymous[row['label']]}
        for rating in row['ratings']:
            try:validate_criticized_excerpt(rating,findings[rating['finding_id']])
            except ValueError as error:
                if rating['finding_id'] not in invalid:
                    checked['invalid_ratings'].append({'finding_id':rating['finding_id'],'error':str(error)})
                    invalid.add(rating['finding_id'])
    checked['valid_rating_ids']=[i for i in checked['valid_rating_ids'] if i not in invalid]
    validate_issue_partition(value['issue_groups'],[f['finding_id'] for rows in anonymous.values() for f in rows])
    expected={frozenset(pair) for pair in itertools.combinations(MAPPING,2)}
    pairs=value.get('pairwise',[])
    seen=[]
    for row in pairs:
        pair=frozenset((row.get('label_a'),row.get('label_b')))
        if pair not in expected or row.get('preferred_label') not in pair|{'tie','uncertain'} or not row.get('reason','').strip():
            raise ValueError('Invalid pairwise preference')
        seen.append(pair)
    if len(seen)!=3 or set(seen)!=expected:
        raise ValueError('Every pair must be assessed exactly once')
    if value.get('preferred_label') not in {*MAPPING,'tie','uncertain'}:
        raise ValueError('Invalid overall preference')
    return checked


def verify():
    for name,sha in read(ROOT/'seal.json')['files'].items():
        if digest(Path(name).read_bytes())!=sha:raise ValueError('Frozen file changed: '+name)


def budget():
    verify()
    check_budget(ROOT,400000,2)
    if not 0<=time.time()-read(ROOT/'billing_confirmation.json')['checked_at']<86400:
        raise ValueError('Billing verification expired')
    require_subscription(ROOT)


def prepare():
    if (ROOT/'seal.json').exists():raise ValueError('Already prepared')
    paper=verify_workspace(BASE/'workspace')
    write(ROOT/'protocol.json',PROTOCOL)
    write(ROOT/'baseline-prompt.json',{'prompt':baseline_prompt(paper)})
    for name,stage in [('workspace','sequential-3'),('ensemble','ensemble')]:
        write(ROOT/'inputs'/f'{name}.json',read(OLD/'panel/fresh'/stage/'editor-package.json'))
    files=[Path(__file__),REPO/'docs/pra-simple-baseline-protocol.md',ROOT/'protocol.json',ROOT/'baseline-prompt.json']
    for folder in (REPO/'paper_workspace',REPO/'experiments',BASE,OLD/'panel/fresh',ROOT/'inputs'):
        files.extend(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    write(ROOT/'seal.json',{'created_at':time.time(),'files':{str(p):digest(p.read_bytes()) for p in sorted(set(files))}})


def judge():
    budget()
    target=ROOT/'evaluation'
    paper=verify_workspace(BASE/'workspace')
    _,_,cards,_=_records(OLD/'panel/fresh')
    reviews={name:read(ROOT/'inputs'/f'{name}.json') for name in ('workspace','ensemble')}
    reviews['basic']=read(ROOT/'basic/editor-package.json')
    anonymous={label:[{'finding_id':label+str(i),**_clean({k:f[k] for k in PRIMARY_FIELDS if k in f})}
                      for i,f in enumerate(reviews[name]['findings'],1)] for label,name in MAPPING.items()}
    images,paths=_images(OLD/'panel/fresh',BASE,paper,target)
    registry=build_registry(paper,list(cards.values()))
    schema=judge_schema(comparison_schema(),registry,images)
    prompt=INSTRUCTIONS+'\nAll three labels are primary reports. Compare every pair and give an overall preference. '
    prompt+='Group every finding exactly once by the same scientific question and resolution, not topic alone. '
    prompt+='For unsupported_allegation, criticized_excerpt must quote the actual finding comment exactly. Leave it empty otherwise.'
    prompt+='\nREFERENCE FORMAT OVERRIDE: Select evidence_handle for text references. Use image_id and visual_observation for images.'
    prompt+='\nANONYMOUS REVIEWS:\n'+json.dumps(anonymous,ensure_ascii=False)
    prompt+='\nSOURCE SPANS:\n'+json.dumps(model_catalog(registry),ensure_ascii=False)
    prompt+='\nSOURCE IMAGES:\n'+json.dumps(images,ensure_ascii=False)
    write(target/'inputs.json',{'anonymous':anonymous,'images':images,'schema':schema,'prompt_sha256':digest(prompt)})
    raw=model_call(PROTOCOL,target/'execution',prompt,schema,tools=False,label='three-way-baseline-judge',images=paths)
    write(target/'raw-model.json',raw)
    hydrated=hydrate_judgment(raw,registry,images)
    write(target/'reference-audit.json',hydrated)
    value=hydrated['response']
    write(target/'raw.json',value)
    judge_paper={**paper,'blocks':paper['blocks']+[{'id':c['evidence_id'],'text':c['evidence_text']} for c in cards.values() if c.get('eligible')]}
    checked=audit_comparison(value,anonymous,judge_paper,images)
    write(target/'audit.json',checked)
    valid=set(checked['valid_rating_ids'])
    group={i:g['issue_id'] for g in value['issue_groups'] for i in g['members']}
    metrics={}
    for row in value['conditions']:
        ratings=[r for r in row['ratings'] if r['finding_id'] in valid]
        metrics[MAPPING[row['label']]]={'findings':len(row['ratings']),'unscored':len(row['ratings'])-len(ratings),
            'assessments':{name:sum(r['assessment']==name for r in ratings) for name in ASSESSMENTS},
            'supported_groups':sorted({group[r['finding_id']] for r in ratings if r['assessment'] in ASSESSMENTS[:2]}),
            'excessive_requests':sum(r['resolution_proportionality']=='excessive' for r in ratings)}
    result={'preferred':MAPPING.get(value['preferred_label'],value['preferred_label']),
        'reason':value['preference_reason'],'provisional':bool(checked['invalid_ratings']),
        'pairwise':[{**r,'condition_a':MAPPING[r['label_a']],'condition_b':MAPPING[r['label_b']],
                     'preferred':MAPPING.get(r['preferred_label'],r['preferred_label'])} for r in value['pairwise']],
        'metrics':metrics,'issue_groups':value['issue_groups'],'usage':observed_usage(ROOT),
        'limitations':[PROTOCOL['scope'],'One same-family automated judge, not expert validation.',
                      'Main reports only. Different pass counts and actual token budgets. No causal isolation of tools or debate.']}
    write(ROOT/'results.json',result)


def run():
    with tracked_stage(ROOT/'state.json','simple-baseline-comparison',2200):
        budget()
        out=ROOT/'basic'
        prepare_out(ROOT,out,PROTOCOL)
        with tracked_stage(ROOT/'stage.json','tool-free-review',1080):
            first=guarded_call(BASE,out,PROTOCOL,read(ROOT/'baseline-prompt.json')['prompt'],'basic',
                               [Path(i['path']) for i in read(BASE/'images.json')])
            if len(first['findings'])>5 or sum(len(f['comment'].split()) for f in first['findings'])>900:
                raise ValueError('Baseline exceeds common output budget')
            write(out/'editor-package.json',first)
        verify()
        with tracked_stage(ROOT/'stage.json','blind-three-way-judge',1080):judge()
        verify()
        write(ROOT/'completion.json',{'status':'complete','usage':observed_usage(ROOT),'frozen_inputs_verified':True})


if __name__=='__main__':
    import sys
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':run()
    else:raise ValueError('Unknown command')
