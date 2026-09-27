"""Dispatch the already frozen anonymous judge packet through a per-paper runtime."""
import json
import time
from pathlib import Path
from experiments.pra_reliability_trial.run import ROOT, PROTOCOL, budget, INSTRUCTIONS, audit
from experiments.pra_prospective import core
from paper_workspace.annotations import verify_workspace
from paper_workspace.model_runtime import require_subscription, model_call
from paper_workspace.storage import read, write, digest


def evaluate(key):
    out=ROOT/'panel'/key
    target=out/'evaluation'
    core.verify(out/'study')
    require_subscription(ROOT)
    if list((target/'execution').rglob('*.started.json')):
        raise ValueError('Judge already attempted. No retry permitted.')
    for condition in ('single','pra'):
        if read(out/condition/'progress.json')['status']!='complete':
            raise ValueError('Both review conditions must pass validation')
    budget(1)
    inputs=read(target/'judge-inputs.json')
    prompt=INSTRUCTIONS.replace('three anonymous','two anonymous')
    prompt+='\nEligible source cards are evidence blocks identified by evidence_id. Use exact evidence_text quotations. Source identity does not establish claim validity.'
    prompt+='\nANONYMOUS REVIEWS:\n'+json.dumps(inputs['anonymous'],ensure_ascii=False)
    prompt+='\nFULL MANUSCRIPT:\n'+(ROOT/'inputs'/key/'workspace/manuscript.md').read_text()
    prompt+='\nSOURCE CARDS:\n'+json.dumps(inputs['source_cards'],ensure_ascii=False)
    prompt+='\nSOURCE IMAGES, attached in this order:\n'+json.dumps(inputs['images'],ensure_ascii=False)
    if digest(prompt)!=inputs['prompt_sha256']:
        raise ValueError('Frozen judge prompt changed')
    available=list((target/'evidence').glob('*.png'))+list((target/'additional-evidence').glob('*.png'))
    by_hash={digest(p.read_bytes()):p for p in available}
    paths=[by_hash[item['sha256']] for item in inputs['images']]
    # The runtime operates on one paper per invocation. Freshness belongs to the study seal.
    transport={k:v for k,v in PROTOCOL.items() if k!='held_out_runs_authorized'}
    amendment=target/'transport-dispatch-amendment.json'
    if amendment.exists():
        raise ValueError('Dispatch amendment already recorded')
    write(amendment,{'recorded_at':time.time(),'reason':'The legacy per-paper runtime rejects a truthy held_out_runs_authorized flag before dispatch. Generation already uses its per-paper runtime contract. Freshness and authorization remain governed by the unchanged prospective study seal.',
        'inference_calls_before_amendment':0,'transport_protocol':transport,
        'unchanged':['model','effort','prompt hash','schema','anonymous labels','paper','source cards','images','budgets','no retries'],
        'assessment_code_sha256':digest(Path(__file__).read_bytes())})
    value=model_call(transport,target/'execution',prompt,inputs['schema'],label=key+'-judge',images=paths)
    write(target/'raw.json',value)
    if sorted(c['label'] for c in value['conditions'])!=['A','B']:
        raise ValueError('Invalid condition accounting')
    paper=verify_workspace(ROOT/'inputs'/key/'workspace')
    paper={**paper,'blocks':paper['blocks']+[{'id':c['evidence_id'],'text':c['evidence_text']}
        for c in inputs['source_cards'] if c.get('eligible')]}
    checked=audit({**value,'conditions':value['conditions']+[{'label':'C','ratings':[],'matches':[]}]},
                  {**inputs['anonymous'],'C':[]},paper,inputs['images'])
    write(target/'audit.json',checked)
    mapping={label[-1]:row['condition'] for label,row in read(out/'study/private/condition-map.json')['labels'].items()}
    valid=set(checked['valid_rating_ids'])
    result={'preferred':mapping.get(value['preferred_label'],value['preferred_label']),
        'preference_reason':value['preference_reason'],'metrics':[],
        'limitation':'One fresh-context blinded model judge on one completed pair, not independent human validation.'}
    for row in value['conditions']:
        ratings=[r for r in row['ratings'] if r['finding_id'] in valid]
        result['metrics'].append({'condition':mapping[row['label']],'total':len(row['ratings']),
            'unscored':len(row['ratings'])-len(ratings),
            'assessments':{label:sum(r['assessment']==label for r in ratings) for label in
                ('justified_concern','justified_clarification','unsupported_allegation','unverifiable')},
            'excessive_requests':sum(r['resolution_proportionality']=='excessive' for r in ratings)})
    write(target/'results.json',result)
    core.verify(out/'study')
    core.report(out/'study',out/'prospective-report.json')
    print(json.dumps({'paper':key,'preferred':result['preferred']}),flush=True)


if __name__=='__main__':
    import sys
    evaluate(sys.argv[1])
