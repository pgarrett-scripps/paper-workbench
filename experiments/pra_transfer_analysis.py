"""Summarize frozen matched-pass outcomes and export unscored expert packets."""
from pathlib import Path
import json
import shutil
from collections import Counter
from paper_workspace.storage import read, write, digest
from paper_workspace.model_runtime import jsonl

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/'runs/pra-transfer-matched-v1'


def summarize():
    results=[]
    for key in ('clinical','plant'):
        out=ROOT/'panel'/key
        result={'paper':key,'doi':read(ROOT/'inputs'/key/'selection.json')['doi'],'conditions':{}}
        for condition in ('single','pra'):
            path=out/condition
            progress=read(path/'progress.json') if (path/'progress.json').exists() else {'status':'not_started'}
            rows=jsonl(path/'execution/usage.jsonl')
            value={'status':progress['status'],'error':progress.get('error'), 'calls':len(rows),
                   'observed_tokens':sum(r.get('observed_tokens',0) for r in rows),
                   'usage_unknown':any(r.get('usage_unknown') for r in rows)}
            if (path/'editor-package.json').exists():
                package=read(path/'editor-package.json')
                value['findings']=len(package['findings'])
                value['finding_titles']=[f['title'] for f in package['findings']]
                if condition=='pra':
                    items=package['candidate_inventory']['items']
                    value['candidate_outcomes']=dict(Counter(i['selection_outcome'] for i in items if i['discovery_status']=='discovered_candidate'))
                    value['hypothesis_outcomes']=dict(Counter(i['selection_outcome'] for i in items if i['discovery_status']=='investigator_discarded_hypothesis'))
                    value['component_treatments']=dict(Counter(t for i in items for t in i['component_treatments']))
                    value['component_validation']=package['component_validation']
            result['conditions'][condition]=value
        if (out/'evaluation/results.json').exists():
            result['blind_assessment']=read(out/'evaluation/results.json')
            result['reference_audit']=read(out/'evaluation/audit.json')
            judged=read(out/'evaluation/raw.json')
            mapping=read(out/'private/condition-map.json')
            valid=set(result['reference_audit']['valid_rating_ids'])
            result['consequential_supported']={mapping[c['label']]:sum(r['finding_id'] in valid and r['assessment'] in ('justified_concern','justified_clarification') and r['materiality'] in ('major','moderate') for r in c['ratings']) for c in judged['conditions']}
        results.append(result)
    receipts=[r for p in (ROOT/'panel').rglob('usage.jsonl') for r in jsonl(p)]
    summary={'papers':results,'total_calls':len(list((ROOT/'panel').rglob('*.started.json'))),
             'observed_tokens':sum(r.get('observed_tokens',0) for r in receipts),
             'usage_unknown':any(r.get('usage_unknown') for r in receipts),
             'delivery':{c:{'complete':sum(p['conditions'][c]['status']=='complete' for p in results),'assigned':2} for c in ('single','pra')},
             'limitation':'Two manuscripts and same-family model assessments do not establish superiority. Component accounting is not semantic validation.'}
    write(ROOT/'summary.json',summary)
    return summary


def export_experts():
    for key in ('clinical','plant'):
        source=ROOT/'panel'/key/'evaluation/judge-inputs.json'
        if not source.exists():
            continue
        inputs=read(source)
        dest=REPO/'validation/next-study/pilot-expert-packets'/key
        if (dest/'manifest.json').exists():
            continue
        dest.mkdir(parents=True,exist_ok=True)
        paper=read(ROOT/'inputs'/key/'workspace/paper.json')
        write(dest/'anonymous-reviews.json',inputs['anonymous'])
        write(dest/'source-manuscript.json',paper)
        write(dest/'source-cards.json',inputs['source_cards'])
        shutil.copy2(ROOT/'inputs'/key/'workspace/original.pdf',dest/'manuscript.pdf')
        supp=ROOT/'inputs'/key/'workspace/supplements'
        if supp.exists():shutil.copytree(supp,dest/'supplements',dirs_exist_ok=True)
        shutil.copy2(REPO/'validation/next-study/expert-instructions.md',dest/'instructions.md')
        template={'status':'unscored','rater_id':'','domain_expertise':'','conflicts':'',
            'paper_title':paper['title'],'review_preference':None,'preference_reason':'',
            'ratings':[{'finding_id':f['finding_id'],'assessment':None,'materiality':None,
                'proportionality':None,'edit_fidelity':None,'source_evidence':[],
                'counterevidence':[],'confidence':None,'reason':''}
                for label in ('A','B') for f in inputs['anonymous'][label]]}
        write(dest/'ratings-template.json',template)
        write(dest/'manifest.json',{'purpose':'Independent unscored pilot spot check. Contains no model ratings or workflow mapping.',
            'files':{str(p.relative_to(dest)):digest(p.read_bytes()) for p in sorted(dest.rglob('*')) if p.is_file()}})
    print('Available anonymous expert packets exported without model scores',flush=True)


if __name__=='__main__':
    print(json.dumps(summarize(),indent=2))
    export_experts()
