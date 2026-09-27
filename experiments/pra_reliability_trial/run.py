"""Seal two fresh papers, run matched resources, and assess anonymous reviews."""
import argparse
import copy
import json
import secrets
import time
from pathlib import Path

from paper_workspace.annotations import verify_workspace
from paper_workspace.model_runtime import jsonl, model_call, require_subscription, source_manifest
from paper_workspace.reviewer import review, inspected_images
from paper_workspace.storage import digest, read, write
from experiments.pra_prospective import core
from experiments.pra_debate_revision.evaluation import EVALUATION, INSTRUCTIONS, audit

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO/'runs/pra-reliability-trial-v1'
KEYS = ('health', 'ecology')
PROTOCOL = {'provider':'codex', 'model':'gpt-5.6-sol', 'effort':'medium',
    'held_out_runs_authorized':False, 'max_calls_per_condition':1,
    'observed_token_stop':200000, 'call_timeout_seconds':900,
    'max_source_images':10, 'image_budget_version':'evidence-v1',
    'max_total_model_calls':8, 'observed_token_launch_stop':850000,
    'no_retries':True, 'judge_only_validated_reviews':True,
    'conditions':['single','pra'], 'version':'reliability-trial-v1'}


def budget(required):
    attempts = list((ROOT/'panel').rglob('*.started.json'))
    receipts = [r for p in (ROOT/'panel').rglob('usage.jsonl') for r in jsonl(p)]
    if len(attempts)+required > PROTOCOL['max_total_model_calls']:
        raise ValueError('Eight-call limit reached')
    if any(r.get('usage_unknown') for r in receipts):
        raise ValueError('Unaccounted model usage')
    if sum(r.get('observed_tokens',0) for r in receipts) >= PROTOCOL['observed_token_launch_stop']:
        raise ValueError('Observed-token launch stop reached')
    billing = read(ROOT/'billing_confirmation.json')
    if not 0 <= time.time()-billing['checked_at'] < 86400:
        raise ValueError('Billing verification expired')


def seal_all():
    if (ROOT/'protocol.json').exists():
        raise ValueError('Trial already sealed')
    write(ROOT/'protocol.json',PROTOCOL)
    for key in KEYS:
        base = ROOT/'inputs'/key
        out = ROOT/'panel'/key
        paper = verify_workspace(base/'workspace')
        selection = read(base/'selection.json')
        write(base/'candidate.json',{'papers':[{'doi':selection['doi'],'paper_id':paper['id']} ]})
        images = read(base/'images.json')
        shared = {'manuscript':str(base/'workspace/paper.json'),
            'source_packet':str(ROOT/'packets'/key), 'images':images,
            'domain_guidance':str(REPO/'paper_workspace/domains'),
            'model':'gpt-5.6-sol', 'settings':{'effort':'medium','evidence_mode':'current'},
            'tools':['manuscript','figures','calculator','domain-sources','result-map'],
            'tool_call_budget':6, 'source_request_budget':6}
        config = {'schema_version':core.VERSION,'study_id':'reliability-trial-v1-'+key,
            'candidate_manifest':str(base/'candidate.json'),
            'prior_corpus_manifest':str(ROOT/'prior-corpus.json'),
            'prompt_paths':[str(REPO/'paper_workspace/reviewer.py'),str(REPO/'paper_workspace/discovery.py'),
                            str(REPO/'paper_workspace/debate_revision.py'),str(REPO/'paper_workspace/review_schema.py')],
            'settings_paths':[str(ROOT/'protocol.json')],
            'implementation_paths':[str(Path(__file__).parent)],
            'domain_paths':[str(REPO/'paper_workspace/domains')],
            'frozen_paths':[str(base/'selection.json'),str(base/'images.json'),str(base/'workspace/manifest.json')]+
                [str(base/'workspace'/p) for p in read(base/'workspace/manifest.json')['files']],
            'evidence_limitations':['Two new-to-local-evaluation papers, not a confirmatory sample.',
                'One fresh-context same-family model judge per paper, no human expert assessment.',
                'Both conditions receive the same initial resources and total tool budget, but PRA uses two model calls.',
                'A frozen finite source packet cannot establish comprehensive literature coverage.',
                'Judge compares the main five findings. Secondary candidate retention is reported separately.',
                'Only validated final reviews enter judging. Generation failures are reported without retries.'],
            'conditions':{
                'single':{**shared,'model_calls':1,'review_path':str(out/'single/responses/plain-guarded.json'),
                          'usage_receipts':[str(out/'single/execution/usage.jsonl')]},
                'pra':{**shared,'model_calls':2,'review_path':str(out/'pra/editor-package.json'),
                       'usage_receipts':[str(out/'pra/execution/usage.jsonl')]}}}
        write(base/'trial-protocol.json',config)
        core.seal(base/'trial-protocol.json',out/'study')
    print('Both pretrial seals created before generation',flush=True)


def generate(key,condition):
    out = ROOT/'panel'/key
    core.verify(out/'study')
    budget(1 if condition=='single' else 2)
    target = out/condition
    if target.exists():
        raise ValueError('No repeat generation attempt allowed')
    base = ROOT/'inputs'/key
    images = read(base/'images.json')
    review(base/'workspace',target,ROOT/'billing_confirmation.json','2026-09-25',
        mode='plain' if condition=='single' else 'panel',
        scaffold_root='/home/ty/Repos/paper-scaffold',domain_support=True,
        evidence_mode='current',source_packet=ROOT/'packets'/key,
        shared_images=[Path(i['path']) for i in images])


def evaluate(key):
    out = ROOT/'panel'/key
    base = ROOT/'inputs'/key
    study = out/'study'
    core.verify(study)
    require_subscription(ROOT)
    for condition in ('single','pra'):
        if read(out/condition/'progress.json')['status']!='complete':
            raise ValueError('Judge requires two validated completed review packages')
    target = out/'evaluation'
    if target.exists():
        raise ValueError('No repeat judge attempt allowed')
    budget(1)
    core.attach_reviews(study)
    packet = core.export_anonymous(study,target,secrets.randbits(64))
    mapping = {label[-1]:row['condition'] for label,row in read(study/'private/condition-map.json')['labels'].items()}
    anonymous = {row['label'][-1]:[{'finding_id':f['item_id'],**{k:v for k,v in f.items() if k!='item_id'}}
        for f in row['findings']] for row in packet['candidates']}
    images = [{'id':r['image_id'],'label':r['label'],'sha256':r['sha256']} for r in packet['images']]
    paths = [target/r['path'] for r in packet['images']]
    hashes = {r['sha256'] for r in images}
    paper = verify_workspace(base/'workspace')
    for condition,stages in [('single',['plain']),('pra',['workspace','debate'])]:
        for stage in stages:
            for path,label in inspected_images(paper,base/'workspace',out/condition/'investigations'/stage,10):
                sha = digest(path.read_bytes())
                if sha in hashes:
                    continue
                dest = target/'additional-evidence'/('image-'+str(len(images)+1)+'.png')
                dest.parent.mkdir(exist_ok=True)
                dest.write_bytes(path.read_bytes())
                paths.append(dest)
                images.append({'id':'image-'+str(len(images)+1),'label':label,'sha256':sha})
                hashes.add(sha)
    if len(paths)>10:
        raise ValueError('Image union exceeds the shared ceiling')
    # Additional inspected images are also sealed in a judge-specific input manifest.
    cards = [c['content'] for c in packet['source_cards']]
    judge_paper = {**paper,'blocks':paper['blocks']+[
        {'id':c['evidence_id'],'text':c['evidence_text']} for c in cards if c.get('eligible')]}
    schema = copy.deepcopy(EVALUATION)
    schema['properties']['conditions']['items']['properties']['label']['enum']=['A','B']
    schema['properties']['conditions'].update(minItems=2,maxItems=2)
    schema['properties']['preferred_label']['enum']=['A','B','tie','uncertain']
    prompt = INSTRUCTIONS.replace('three anonymous','two anonymous')
    prompt += '\nEligible source cards are evidence blocks identified by evidence_id. Use exact evidence_text quotations. Source identity does not establish claim validity.'
    prompt += '\nANONYMOUS REVIEWS:\n'+json.dumps(anonymous,ensure_ascii=False)
    prompt += '\nFULL MANUSCRIPT:\n'+(base/'workspace/manuscript.md').read_text()
    prompt += '\nSOURCE CARDS:\n'+json.dumps(cards,ensure_ascii=False)
    prompt += '\nSOURCE IMAGES, attached in this order:\n'+json.dumps(images,ensure_ascii=False)
    write(target/'judge-inputs.json',{'anonymous':anonymous,'images':images,
        'prompt_sha256':digest(prompt),'source_cards':cards,'schema':schema})
    value = model_call(PROTOCOL,target/'execution',prompt,schema,label=key+'-judge',images=paths)
    write(target/'raw.json',value)
    if sorted(c['label'] for c in value['conditions'])!=['A','B']:
        raise ValueError('Invalid two-condition judge accounting')
    # Reuse the tested per-rating reference auditor with an empty internal third label.
    checked = audit({**value,'conditions':value['conditions']+[{'label':'C','ratings':[],'matches':[]}]},
                    {**anonymous,'C':[]},judge_paper,images)
    write(target/'audit.json',checked)
    valid = set(checked['valid_rating_ids'])
    result = {'preferred':mapping.get(value['preferred_label'],value['preferred_label']),
        'preference_reason':value['preference_reason'],'metrics':[],
        'limitations':['One blinded fresh-context model judge per paper, not independent human validation.',
                       'Two papers do not establish superiority or domain generalization.']}
    for row in value['conditions']:
        ratings = [v for v in row['ratings'] if v['finding_id'] in valid]
        result['metrics'].append({'condition':mapping[row['label']],'total':len(row['ratings']),
            'unscored':len(row['ratings'])-len(ratings),
            'assessments':{label:sum(r['assessment']==label for r in ratings) for label in
                ('justified_concern','justified_clarification','unsupported_allegation','unverifiable')},
            'excessive_requests':sum(r['resolution_proportionality']=='excessive' for r in ratings)})
    write(target/'results.json',result)
    core.verify(study)
    core.report(study,out/'prospective-report.json')
    print(json.dumps({'paper':key,'preferred':result['preferred']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['seal','single','pra','judge'])
    parser.add_argument('--paper',choices=KEYS)
    args=parser.parse_args()
    if args.action=='seal':
        seal_all()
    elif args.action=='judge':
        evaluate(args.paper)
    else:
        generate(args.paper,args.action)
