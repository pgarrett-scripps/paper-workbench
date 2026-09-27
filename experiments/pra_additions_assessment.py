"""Diagnostic judging after a source-format gate failure, with unchanged generation."""
from experiments.pra_additions_retest.run import *
from paper_workspace.annotations import normalize_review


def load_condition(out, name):
    folder=out/name
    progress=read(folder/'progress.json')
    if progress['status']=='complete':
        path=folder/('responses/plain-guarded.json' if name=='single' else 'editor-package.json')
        return read(path), {'deliverable':True,'stage':'complete'}
    raw=folder/('responses/plain.json' if name=='single' else 'responses/debate.json')
    if not raw.exists():
        raise ValueError('No completed raw review available for this diagnostic comparison')
    value=read(raw)
    cards=folder/'sources/cards.json'
    value={**value,'source_cards':read(cards) if cards.exists() else []}
    return value, {'deliverable':False,'stage':progress['status'],'gate_error':progress.get('error'),
                   'input':'Completed raw model output, not a validated deliverable'}


def evaluate(key):
    verify()
    amendment=read(ROOT/'diagnostic-evaluation-amendment-v2.json')
    if digest(Path(__file__).read_bytes())!=amendment['assessment_code_sha256']:
        raise ValueError('Diagnostic assessment code changed')
    require_subscription(ROOT)
    base=ROOT/'inputs'/key
    out=ROOT/'panel'/key
    target=out/'evaluation'
    if target.exists(): raise ValueError('No repeat judge attempt allowed')
    images=read(base/'images.json')
    single_value,single_status=load_condition(out,'single')
    panel_value,panel_status=load_condition(out,'panel')
    paper=verify_workspace(base/'workspace')
    for value in (single_value,panel_value):
        normalized=normalize_review(paper,value,'diagnostic')
        known_sources={c['evidence_id'] for c in value.get('source_cards',[]) if c.get('eligible')}
        if any(f['placement']!='anchored' or set(f['invalid_evidence_blocks'])-known_sources
               for f in normalized['findings']):
            raise ValueError('Diagnostic raw review has missing manuscript anchors or unknown evidence')
    immutable(out/'diagnostic-condition-status.json',{'updated_single':single_status,'updated_pra':panel_status})
    budget(1)
    conditions={'saved_pra':read(base/'saved-pra.json'),
                'updated_single':single_value,
                'updated_pra':panel_value}
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

    result['pipeline_status']={'updated_single':single_status,'updated_pra':panel_status}
    immutable(target/'diagnostic-results.json',result)
    print(json.dumps({'paper':key,'status':'evaluated','preferred':result['preferred']}),flush=True)


if __name__=='__main__':
    import sys
    evaluate(sys.argv[1])
