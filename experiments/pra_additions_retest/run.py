"""Two reused papers, matched current tools, saved comparator and a blind judge."""
import argparse
import json
import random
import secrets
import shutil
import time
from pathlib import Path

from paper_workspace.annotations import verify_workspace
from paper_workspace.model_runtime import model_call, source_manifest, jsonl, require_subscription
from paper_workspace.reviewer import review, inspected_images
from paper_workspace.storage import read, write, digest
from experiments.pra_debate_revision.evaluation import EVALUATION, INSTRUCTIONS, audit

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO/'runs/pra-additions-retest-v1'
PRIOR = REPO/'runs/pra-domains-v1'
KEYS = ('ecology','health')
PROTOCOL = {'provider':'codex','model':'gpt-5.6-sol','effort':'medium',
    'held_out_runs_authorized':False,'max_calls_per_condition':1,'observed_token_stop':180000,
    'call_timeout_seconds':900,'max_source_images':10,'image_budget_version':'evidence-v1',
    'max_total_model_calls':8,'observed_token_launch_stop':850000,
    'version':'additions-retest-v1','role':'known_paper_development_retest',
    'conditions':['saved_pra','updated_single','updated_pra'],
    'limits':['No automatic retry or extra judge.', 'Both current conditions get the same domain guidance, source packet, source images and six tool calls in total.',
              'PRA uses two generation calls versus one for the single reviewer.',
              'These manuscripts informed development. They are not unseen validation.',
              'Saved versus updated reviews also differ through sampling. This is not a causal feature ablation.',
              'Finite existing source packets do not test broad literature discovery or historical registry retrieval.',
              'The fresh-context model judge is not an independent human expert.']}


def immutable(path,value):
    if path.exists():
        if read(path)!=value: raise ValueError('Frozen artifact changed: '+str(path))
    else: write(path,value)


def implementation():
    return {'review':source_manifest(REPO/'paper_workspace'),
            'runner':source_manifest(Path(__file__).parent),
            'evaluator':{str(p.relative_to(REPO)):digest(p.read_bytes()) for p in
                [REPO/'experiments/pra_debate_revision/evaluation.py',REPO/'experiments/pra_evidence_workflow/evaluation.py']}}


def prepare():
    if (ROOT/'freeze.json').exists(): raise ValueError('Study already prepared')
    ROOT.mkdir(parents=True,exist_ok=True)
    records={}
    for key in KEYS:
        base=ROOT/'inputs'/key
        old=PRIOR/'heldout-inputs'/key
        shutil.copytree(old/'workspace',base/'workspace',ignore=shutil.ignore_patterns('reviews','decisions','exports','revisions'))
        shutil.copytree(PRIOR/'packets'/key,base/'packet')
        images=[]
        for n,item in enumerate(read(old/'images.json'),1):
            path=base/'images'/f'figure-{n}.png'
            path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(item['path'],path)
            images.append({'id':f'image-{n}','path':str(path),'label':item['label'],'sha256':digest(path.read_bytes())})
        write(base/'images.json',images)
        shutil.copyfile(PRIOR/'panel'/key/'panel/editor-package.json',base/'saved-pra.json')
        paper=verify_workspace(base/'workspace')
        records[key]={'paper_id':paper['id'],'files':source_manifest(base),
                      'role':'previously_seen_development','prior_review':'pra-domains-v1/panel/'+key+'/panel/editor-package.json'}
    shutil.copytree(REPO/'paper_workspace',ROOT/'frozen-source/paper_workspace',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    write(ROOT/'protocol.json',PROTOCOL)
    immutable(ROOT/'freeze.json',{'implementation':implementation(),'protocol':PROTOCOL,'inputs':records,
                                 'frozen_at':time.time()})


def verify():
    frozen=read(ROOT/'freeze.json')
    if implementation()!=frozen['implementation'] or PROTOCOL!=frozen['protocol']:
        raise ValueError('Frozen implementation or protocol changed')
    for key,record in frozen['inputs'].items():
        base=ROOT/'inputs'/key
        # Review output and author decisions are mutable workspace products, not source inputs.
        actual={k:v for k,v in source_manifest(base).items() if not any('/'+part+'/' in '/'+k for part in ('reviews','decisions','exports','revisions'))}
        if actual!=record['files']: raise ValueError('Frozen paper inputs changed: '+key)
        verify_workspace(base/'workspace')
    return frozen


def budget(required):
    attempts=list((ROOT/'panel').rglob('*.started.json'))
    receipts=[r for p in (ROOT/'panel').rglob('usage.jsonl') for r in jsonl(p)]
    if len(attempts)+required>PROTOCOL['max_total_model_calls']: raise ValueError('Eight-call ceiling reached')
    if any(r.get('usage_unknown') for r in receipts): raise ValueError('A model cost is unaccounted')
    if sum(r.get('observed_tokens',0) for r in receipts)>=PROTOCOL['observed_token_launch_stop']:
        raise ValueError('Observed-token launch stop reached')
    billing=read(ROOT/'billing_confirmation.json')
    if not 0<=time.time()-billing['checked_at']<86400: raise ValueError('Refresh billing verification')


def run(key,stage):
    verify()
    require_subscription(ROOT)
    base=ROOT/'inputs'/key
    out=ROOT/'panel'/key
    images=read(base/'images.json')
    if stage in ('single','panel'):
        target=out/stage
        if target.exists(): raise ValueError('No repeat generation attempt is allowed')
        budget(1 if stage=='single' else 2)
        review(base/'workspace',target,ROOT/'billing_confirmation.json','2026-09-25',
            mode='plain' if stage=='single' else 'panel', scaffold_root='/home/ty/Repos/paper-scaffold',
            domain_support=True,evidence_mode='current',source_packet=base/'packet',
            shared_images=[Path(i['path']) for i in images])
    else:
        target=out/'evaluation'
        if target.exists(): raise ValueError('No repeat judge attempt is allowed')
        for condition in ('single','panel'):
            if read(out/condition/'progress.json')['status']!='complete': raise ValueError('Generation gate did not pass')
        budget(1)
        conditions={'saved_pra':read(base/'saved-pra.json'),
                    'updated_single':read(out/'single/responses/plain-guarded.json'),
                    'updated_pra':read(out/'panel/editor-package.json')}
        immutable(out/'generation-lock.json',{k:digest(json.dumps(v,sort_keys=True)) for k,v in conditions.items()})
        order=list(conditions)
        seed=secrets.randbits(64)
        random.Random(seed).shuffle(order)
        mapping=dict(zip('ABC',order))
        immutable(target/'private/labels.json',mapping)
        (target/'private/labels.json').chmod(0o600)
        immutable(target/'private/randomization.json',{'seed':seed})
        anonymous={label:[{'finding_id':f'{label}{n}',**{k:f.get(k) for k in
            ('title','block_id','quote','kind','severity','comment','replacement','evidence_blocks','counterevidence','source_evidence')}}
            for n,f in enumerate(conditions[name]['findings'],1)] for label,name in mapping.items()}
        immutable(target/'anonymous.json',anonymous)
        paper=verify_workspace(base/'workspace')
        card_keys=('evidence_id','provider','identifier','evidence_mode','eligible','status','source_url','record_version','cutoff','evidence_text','limitation','effective_date','captured_at')
        cards={c['evidence_id']:{k:c[k] for k in card_keys if k in c} for value in conditions.values() for c in value.get('source_cards',[])}
        judge_paper={**paper,'blocks':paper['blocks']+[{'id':c['evidence_id'],'text':c['evidence_text']} for c in cards.values() if c.get('eligible')]}
        union=list(images)
        hashes={i['sha256'] for i in union}
        for condition,stages in [('single',['plain']),('panel',['workspace','debate'])]:
            for label in stages:
                for path,title in inspected_images(paper,base/'workspace',out/condition/'investigations'/label,limit=10):
                    fingerprint=digest(path.read_bytes())
                    if fingerprint not in hashes:
                        union.append({'id':'image-'+str(len(union)+1),'path':str(path),'label':title,'sha256':fingerprint})
                        hashes.add(fingerprint)
        if len(union)>10: raise ValueError('Image union exceeds cap')
        attached=[]
        public_images=[]
        for i,item in enumerate(union,1):
            path=target/'evidence'/f'image-{i}.png'
            path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(item['path'],path)
            attached.append(path)
            public_images.append({k:item[k] for k in ('id','label','sha256')})
        immutable(target/'images.json',public_images)
        prompt=INSTRUCTIONS+'\nApply methods appropriate to this manuscript domain. Cite eligible source cards using their evidence_id as block_id and an exact evidence_text quote. A successful source lookup does not establish scientific validity.\nANONYMOUS REVIEWS:\n'+json.dumps(anonymous,ensure_ascii=False)
        prompt+='\nFULL MANUSCRIPT:\n'+(base/'workspace/manuscript.md').read_text()
        prompt+='\nSOURCE CARDS:\n'+json.dumps(list(cards.values()),ensure_ascii=False)
        prompt+='\nSHARED SOURCE IMAGES, attached in this order:\n'+json.dumps(public_images,ensure_ascii=False)
        value=model_call(PROTOCOL,target/'execution',prompt,EVALUATION,label=key+'-judge',images=attached)
        immutable(target/'raw.json',value)
        checked=audit(value,anonymous,judge_paper,public_images)
        immutable(target/'audit.json',checked)
        valid=set(checked['valid_rating_ids'])
        result={'preferred':mapping.get(value['preferred_label'],value['preferred_label']),
                'preference_reason':value['preference_reason'],'metrics':[],
                'limitation':'One blinded fresh-context model judge, not independent human validation. Reused development papers.'}
        for row in value['conditions']:
            ratings=[r for r in row['ratings'] if r['finding_id'] in valid]
            result['metrics'].append({'condition':mapping[row['label']],'total':len(row['ratings']),'unscored':len(row['ratings'])-len(ratings),
                'assessments':{label:sum(r['assessment']==label for r in ratings) for label in ('justified_concern','justified_clarification','unsupported_allegation','unverifiable')},
                'supported_major':sum(r['materiality']=='major' and r['assessment'] in ('justified_concern','justified_clarification') for r in ratings),
                'excessive_requests':sum(r['resolution_proportionality']=='excessive' for r in ratings)})
        immutable(target/'results.json',result)
    print(json.dumps({'paper':key,'stage':stage,'status':'complete'}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('paper',choices=KEYS+('all',))
    parser.add_argument('stage',choices=('prepare','single','panel','evaluate'))
    args=parser.parse_args()
    if args.stage=='prepare': prepare()
    elif args.paper=='all': raise ValueError('Run one paper stage at a time')
    else: run(args.paper,args.stage)
