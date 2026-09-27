"""Descriptive reporting for the frozen four-condition development run."""
from collections import Counter
from pathlib import Path
from paper_workspace.model_runtime import jsonl
from paper_workspace.storage import read,write,digest
from experiments.pra_three_condition.prepare import ROOT,PAPERS
from experiments.pra_three_condition.run import CONDITIONS,usage
from experiments.pra_three_condition.evaluate import REVIEW_PATHS


def tokens(rows):
    return sum(row.get('observed_tokens',0) for row in rows)


def verify_archive():
    repo=ROOT.parents[1]
    for name,sha in read(ROOT/'seal.json')['files'].items():
        original=Path(name)
        archived=ROOT/'frozen-source'/original.relative_to(repo)
        path=archived if archived.is_file() else original
        if digest(path.read_bytes())!=sha:raise ValueError('Frozen archive or input changed: '+str(path))


def summarize():
    verify_archive()
    papers=[]
    for key in PAPERS:
        root=ROOT/'panel'/key
        rows={name:jsonl(root/name/'execution/usage.jsonl') for name in ('basic','workspace','pra','evaluation')}
        first_basic=[r for r in rows['basic'] if r['label']=='first']
        first_pra=[r for r in rows['pra'] if r['label']=='workspace']
        logical={'basic_one':first_basic,'basic_two':rows['basic'],
                 'workspace':first_pra+rows['workspace'],'pra':rows['pra']}
        record={'paper':key,'title':read(ROOT/'inputs'/key/'workspace/paper.json')['title'],
                'doi':PAPERS[key]['doi'],'conditions':{},'failures':[read(p) for p in root.glob('*-failure.json')]}
        for condition in CONDITIONS:
            reviewpath=root/REVIEW_PATHS[condition]
            value=read(reviewpath) if reviewpath.exists() else None
            record['conditions'][condition]={'delivered':value is not None,
                'generation_tokens':tokens(logical[condition]),'logical_calls':len(logical[condition]),
                'findings':value.get('findings',[]) if value else []}
        result=root/'evaluation/results.json'
        if result.exists():
            record['evaluation']=read(result)
            raw=read(root/'evaluation/raw.json')
            mapping=read(root/'private/condition-map.json')
            valid={tuple(row) for row in read(root/'evaluation/audit.json')['valid_rating_ids']}
            for row in raw['conditions']:
                ratings=[r for r in row['ratings'] if (row['label'],r['finding_id']) in valid]
                record['conditions'][mapping[row['label']]]['quality']={
                    'supported_consequential':sum(r['assessment'] in ('justified_concern','justified_clarification') and r['materiality'] in ('major','moderate') for r in ratings),
                    'valid_ratings':len(ratings),'all_ratings':len(row['ratings']),
                    'assessment_counts':dict(Counter(r['assessment'] for r in ratings)),
                    'excessive_requests':sum(r['resolution_proportionality']=='excessive' for r in ratings),
                    'unsupported_edits':sum(r['edit_fidelity']=='introduces_unsupported_claim' for r in ratings)}
        package=root/'pra/editor-package.json'
        if package.exists():
            value=read(package)
            record['pra_retention']={
                'source_candidates':len(value.get('source_findings',[])),
                'final_findings':len(value['findings']),
                'component_treatments':dict(Counter(c['treatment'] for d in value.get('decisions',[]) for c in d['components'])),
                'decisions':value.get('decisions',[]),
                'secondary_inventory':value.get('candidate_inventory',{}).get('secondary_candidates',[])}
        record['tools']=[{'path':str(path.relative_to(root)),'calls':len(jsonl(path)),
            'names':[r.get('tool') for r in jsonl(path)]} for path in root.glob('*/investigations/*/tool-log.jsonl')]
        record['external_requests']={str(path.relative_to(root)):len(read(path).get('requests',[])) for path in root.glob('*/sources/requests.json')}
        record['incremental_usage']={'calls':sum(len(r) for r in rows.values()),'tokens':sum(tokens(r) for r in rows.values())}
        papers.append(record)
    result={'papers':papers,'usage':usage(),'limitation':'Paired development observations. One model judge per paper. No expert validation or human-review overlap measurement.'}
    recovery=ROOT.parent/'pra-four-condition-recovery-v1'
    if (recovery/'panel/molecular/evaluation/results.json').exists():
        result['molecular_recovery']=read(recovery/'panel/molecular/evaluation/results.json')
        result['recovery_usage']=usage(recovery/'panel')
        result['total_including_recovery']={k:result['usage'][k]+result['recovery_usage'][k] for k in ('calls','observed_tokens')}
    write(ROOT/'summary.json',result)
    return result


if __name__=='__main__':
    import json
    result=summarize()
    print(json.dumps({'usage':result['usage'],'papers':[{'paper':p['paper'],
        'preferred':p.get('evaluation',{}).get('preferred'),
        'conditions':{c:{k:v for k,v in r.items() if k!='findings'} for c,r in p['conditions'].items()},
        'tools':p['tools'],'external_requests':p['external_requests'],'failures':p['failures']} for p in result['papers']]},indent=2))
