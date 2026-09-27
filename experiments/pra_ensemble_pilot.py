"""Two-call development comparison using preserved independent discovery drafts."""
import argparse
import json
import shutil
from pathlib import Path

from experiments.pra_debate_revision.evaluation import EVALUATION,INSTRUCTIONS,audit
from experiments.pra_three_condition.evaluate import ALLOWED
from experiments.pra_prospective.core import _clean
from paper_workspace.annotations import verify_workspace
from paper_workspace.ensemble import debate_reviews,observed_usage,check_budget
from paper_workspace.evidence_handles import build_registry,model_catalog
from paper_workspace.judge_evidence import judge_schema,hydrate_judgment
from paper_workspace.model_runtime import model_call,source_manifest
from paper_workspace.storage import read,write,digest


def run(output):
    root=Path(output).resolve()
    old=Path('runs/pra-four-condition-v1').resolve()
    base=old/'inputs/behavior'
    if (root/'protocol.json').exists():raise ValueError('Pilot already prepared or attempted')
    billing=root/'billing_confirmation.json'
    if not billing.exists():raise ValueError('Fresh subscription billing verification required')
    paper=verify_workspace(base/'workspace')
    originals={'basic_first':old/'panel/behavior/basic/responses/first-guarded.json',
        'investigator':old/'panel/behavior/pra/responses/workspace-guarded.json',
        'basic_two':old/'panel/behavior/basic/responses/second-guarded.json',
        'old_pra':old/'panel/behavior/pra/editor-package.json'}
    images=read(base/'images.json')
    for item in images:
        if digest(Path(item['path']).read_bytes())!=item['sha256']:raise ValueError('Image changed')
    mapping={'A':'old_pra','B':'ensemble','C':'basic_two'}
    protocol={'provider':'codex','model':'gpt-5.6-terra','effort':'medium',
        'held_out_runs_authorized':False,'max_calls_per_condition':1,'observed_token_stop':500000,
        'call_timeout_seconds':900,'max_source_images':10,'image_budget_version':'evidence-v1',
        'max_new_calls':2,'total_observed_token_launch_ceiling':500000,'automatic_retries':False,
        'version':'ensemble-development-pilot-v1','paper_id':paper['id'],
        'blinded_mapping':mapping,'primary':'Supported consequential issues, unsupported premises, retention, and cost.',
        'limits':['Known development paper, not held out.',
                  'Reused independent drafts have different discovery prompts and tool access.',
                  'Ensemble has three logical generation calls, comparators have two.',
                  'Fresh two-reviewer and three-reviewer orchestration is tested offline, not in this live pilot.',
                  'One anonymous model judgment is not expert validation.']}
    write(root/'protocol.json',protocol)
    for name,path in originals.items():write(root/'inputs'/f'{name}.json',read(path))
    for directory in ('paper_workspace','experiments'):
        shutil.copytree(directory,root/'frozen-source'/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    manifest={'code':source_manifest(Path('paper_workspace')),
        'runner_sha256':digest(Path(__file__).read_bytes()),
        'input_hashes':{str(p):digest(p.read_bytes()) for p in originals.values()},
        'paper_manifest_sha256':digest((base/'workspace/manifest.json').read_bytes()),'images':images}
    write(root/'manifest.json',manifest)
    def verify():
        if source_manifest(Path('paper_workspace'))!=manifest['code']:raise ValueError('Implementation changed')
        if digest(Path(__file__).read_bytes())!=manifest['runner_sha256']:raise ValueError('Pilot runner changed')
        verify_workspace(base/'workspace')
        for path,sha in manifest['input_hashes'].items():
            if digest(Path(path).read_bytes())!=sha:raise ValueError('Comparator changed')
    records=[{'review':read(path),'provenance':{'paper_id':paper['id'],
              'source_review_path':str(path),'source_review_sha256':digest(path.read_bytes()),
              'origin':'reused_independent_'+name}}
             for name,path in originals.items() if name in ('basic_first','investigator')]
    try:
        check_budget(root,500000,2)
        verify()
        print('Running one pooled debate on two preserved independent drafts',flush=True)
        cutoff=read(old/'panel/behavior/pra/protocol.json')['literature_cutoff']
        debate_reviews(base/'workspace',root/'ensemble',billing,cutoff,records,
            images=[i['path'] for i in images],token_budget=500000,
            cache_roots=[old/'panel/behavior/pra/initial-checkpoint/source-cache'])
        verify()
        check_budget(root,500000,2)
        reviews={name:read(root/'inputs'/f'{name}.json') for name in ('basic_two','old_pra')}
        reviews['ensemble']=read(root/'ensemble/editor-package.json')
        anonymous={}
        cards={}
        for label,name in mapping.items():
            review=reviews[name]
            anonymous[label]=[{'finding_id':label+str(index),**_clean({k:f[k] for k in ALLOWED if k in f})}
                              for index,f in enumerate(review['findings'],1)]
            cited={r['evidence_id'] for f in review['findings'] for r in f.get('source_evidence',[])}
            for card in review.get('source_cards',[]):
                if card['evidence_id'] in cited:cards[card['evidence_id']]=card
            if not cited<=cards.keys():raise ValueError('Missing judge source cards')
        registry=build_registry(paper,list(cards.values()))
        schema=judge_schema(EVALUATION,registry,images)
        prompt=INSTRUCTIONS+'\nREFERENCE FORMAT OVERRIDE: For text references use evidence_handle from SOURCE SPANS. For image references use image_id and visual_observation.'
        prompt+='\nANONYMOUS REVIEWS:\n'+json.dumps(anonymous,ensure_ascii=False)
        prompt+='\nSOURCE SPANS:\n'+json.dumps(model_catalog(registry),ensure_ascii=False)
        prompt+='\nSOURCE IMAGES, attached in order:\n'+json.dumps([{k:v for k,v in i.items() if k!='path'} for i in images])
        write(root/'evaluation/inputs.json',{'anonymous':anonymous,'images':images,'source_cards':list(cards.values()),'schema':schema,'prompt_sha256':digest(prompt)})
        print('Running one blind three-way assessment',flush=True)
        raw=model_call(protocol,root/'evaluation/execution',prompt,schema,tools=False,
                       label='ensemble-pilot-judge',images=[i['path'] for i in images])
        write(root/'evaluation/raw-model.json',raw)
        hydrated=hydrate_judgment(raw,registry,images)
        write(root/'evaluation/reference-audit.json',hydrated)
        value=hydrated['response']
        write(root/'evaluation/raw.json',value)
        judge_paper={**paper,'blocks':paper['blocks']+[{'id':c['evidence_id'],'text':c['evidence_text']} for c in cards.values() if c.get('eligible')]}
        checked=audit(value,anonymous,judge_paper,images)
        write(root/'evaluation/audit.json',checked)
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
                'metrics':metrics,'usage':observed_usage(root),'limitations':protocol['limits']}
        write(root/'results.json',result)
        verify()
        write(root/'progress.json',{'status':'complete','usage':observed_usage(root)})
        print(json.dumps(result),flush=True)
    except Exception as error:
        write(root/'progress.json',{'status':'blocked','error':str(error),'usage':observed_usage(root)})
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output')
    run(parser.parse_args().output)
