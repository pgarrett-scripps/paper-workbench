"""Replay reference-only recovery and spend the pilot's one remaining judge call."""
import argparse
import json
import shutil
from pathlib import Path

from experiments.pra_debate_revision.evaluation import EVALUATION,INSTRUCTIONS,audit
from experiments.pra_three_condition.evaluate import ALLOWED
from experiments.pra_prospective.core import _clean
from paper_workspace.annotations import verify_workspace,save_review
from paper_workspace.debate_revision import revision_package
from paper_workspace.ensemble import observed_usage,check_budget
from paper_workspace.ensemble_debate import augment_ledger
from paper_workspace.ensemble_references import recover
from paper_workspace.evidence_handles import build_registry,model_catalog
from paper_workspace.judge_evidence import judge_schema,hydrate_judgment
from paper_workspace.model_runtime import model_call,source_manifest,require_subscription
from paper_workspace.storage import read,write,digest


def run(output):
    root=Path(output).resolve()
    target=root/'reference-recovery'
    if target.exists():raise ValueError('Recovery already prepared or attempted')
    check_budget(root,500000,2)
    protocol=read(root/'protocol.json')
    mapping=protocol['blinded_mapping']
    base=Path('runs/pra-four-condition-v1/inputs/behavior').resolve()
    paper=verify_workspace(base/'workspace')
    original_manifest=read(root/'manifest.json')
    images=original_manifest['images']
    for item in images:
        if digest(Path(item['path']).read_bytes())!=item['sha256']:raise ValueError('Source image changed')
    for path,sha in original_manifest['input_hashes'].items():
        if digest(Path(path).read_bytes())!=sha:raise ValueError('Original comparison input changed')
    raw_path=root/'ensemble/responses/debate.json'
    raw=read(raw_path)
    sources_path=root/'ensemble/sources/cards.json'
    cards=read(sources_path) if sources_path.exists() else []
    ledger=augment_ledger(raw,read(root/'ensemble/debate-ledger.json'),paper,cards,validate=False)
    recovered=recover(raw,ledger,paper,cards)
    if recovered['recovered'] is None:raise ValueError('Reference recovery did not fully validate the saved draft')
    final=recovered['recovered']
    if final['findings']!=raw['findings']:raise ValueError('Scientific review must remain identical')
    write(target/'reference-audit.json',{k:v for k,v in recovered.items() if k!='recovered'})
    write(target/'protocol.json',protocol)
    shutil.copy2(root/'billing_confirmation.json',target/'billing_confirmation.json')
    require_subscription(target)
    package=revision_package(final,ledger,recovered['audit'])
    records=read(root/'ensemble/input-reviews.json')
    package.update(workflow_version='ensemble-v1',reviewer_count=len(records),
        reviewer_provenance=[r['provenance'] for r in records],
        candidate_origins={i['issue_id']:i.get('origin',i.get('provenance')) for i in ledger['issues']})
    write(target/'editor-package.json',package)
    save_review(base/'workspace',package,'ensemble-reference-recovered-v1')
    shutil.copytree('paper_workspace',target/'frozen-source/paper_workspace',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(__file__,target/'frozen-source/recovery.py')
    manifest={'code':source_manifest(Path('paper_workspace')),'original_draft_sha256':digest(raw_path.read_bytes()),
              'recovery_runner_sha256':digest(Path(__file__).read_bytes()),
              'original_delivery':'failed reference validation','scientific_content_changed':False,
              'new_generation_calls':0,'planned_remaining_judge_calls':1}
    write(target/'manifest.json',manifest)
    reviews={name:read(root/'inputs'/f'{name}.json') for name in ('basic_two','old_pra')}
    reviews['ensemble']=package
    anonymous={}
    for label,name in mapping.items():
        anonymous[label]=[{'finding_id':label+str(index),**_clean({k:f[k] for k in ALLOWED if k in f})}
                          for index,f in enumerate(reviews[name]['findings'],1)]
    registry=build_registry(paper,cards)
    schema=judge_schema(EVALUATION,registry,images)
    prompt=INSTRUCTIONS+'\nREFERENCE FORMAT OVERRIDE: For text references use evidence_handle from SOURCE SPANS. For image references use image_id and visual_observation.'
    prompt+='\nANONYMOUS REVIEWS:\n'+json.dumps(anonymous,ensure_ascii=False)
    prompt+='\nSOURCE SPANS:\n'+json.dumps(model_catalog(registry),ensure_ascii=False)
    prompt+='\nSOURCE IMAGES, attached in order:\n'+json.dumps([{k:v for k,v in i.items() if k!='path'} for i in images])
    write(target/'evaluation/inputs.json',{'anonymous':anonymous,'images':images,'schema':schema,'prompt_sha256':digest(prompt)})
    check_budget(root,500000,2)
    print('Reference-only recovery validated. Running the planned blind assessment.',flush=True)
    try:
        response=model_call(protocol,target/'evaluation/execution',prompt,schema,tools=False,
                            label='ensemble-pilot-judge',images=[i['path'] for i in images])
        write(target/'evaluation/raw-model.json',response)
        hydrated=hydrate_judgment(response,registry,images)
        write(target/'evaluation/reference-audit.json',hydrated)
        value=hydrated['response']
        write(target/'evaluation/raw.json',value)
        judge_paper={**paper,'blocks':paper['blocks']+[{'id':c['evidence_id'],'text':c['evidence_text']} for c in cards if c.get('eligible')]}
        checked=audit(value,anonymous,judge_paper,images)
        write(target/'evaluation/audit.json',checked)
        valid=set(checked['valid_rating_ids'])
        metrics=[]
        for row in value['conditions']:
            ratings=[r for r in row['ratings'] if r['finding_id'] in valid]
            metrics.append({'condition':mapping[row['label']],'findings':len(row['ratings']),
                'unscored':len(row['ratings'])-len(ratings),
                'assessments':{status:sum(r['assessment']==status for r in ratings) for status in
                    ('justified_concern','justified_clarification','unsupported_allegation','unverifiable')},
                'excessive_requests':sum(r['resolution_proportionality']=='excessive' for r in ratings)})
        result={'preferred':mapping.get(value['preferred_label'],value['preferred_label']),
            'reason':value['preference_reason'],'provisional':bool(checked['invalid_ratings']),
            'metrics':metrics,'usage':observed_usage(root),
            'original_delivery':'failed reference validation, fixed offline without changing scientific text',
            'limitations':protocol['limits']}
        if source_manifest(Path('paper_workspace'))!=manifest['code']:raise ValueError('Implementation changed during evaluation')
        write(target/'results.json',result)
        write(target/'progress.json',{'status':'complete','usage':observed_usage(root)})
        print(json.dumps(result),flush=True)
    except Exception as error:
        write(target/'progress.json',{'status':'blocked','error':str(error),'usage':observed_usage(root)})
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output')
    run(parser.parse_args().output)
