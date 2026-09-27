"""Three independent general reviewers, one discussion round, and an editor."""

import argparse
import json
import random
import statistics
from concurrent.futures import ThreadPoolExecutor

import core
import prompts as prompt
import schemas


def parallel(tasks):
    results, errors = {}, []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures={name:executor.submit(fn) for name,fn in tasks.items()}
        for name,future in futures.items():
            try:results[name]=future.result()
            except Exception as exc:errors.append(f'{name}: {exc}')
    if errors:raise core.Blocked('\n'.join(errors))
    return results


def generate(protocol,pid):
    root=core.ROOT
    out=root/'work'/pid
    if (out/'generation.json').exists():return core.read(out/'generation.json')
    source=core.read(root/'inputs'/pid/'source_chunks.json')
    context=prompt.SAFETY+'\nMANUSCRIPT\n'+core.source_text(source)+'\nEND MANUSCRIPT\n'
    def review(name):
        value=core.call(protocol,out/name,context+prompt.REVIEW,schemas.reviewer(source),name)
        records={}
        for i,finding in enumerate(value['findings'],1):
            identifier=f'{name}_F{i}'
            records[identifier]={**finding,'id':identifier,'origin':name,'original_sha256':core.shared.digest(finding)}
            core.resolve(finding['evidence_ids'],source)
            core.resolve(finding['counterevidence_ids'],source)
        body=core.selected(list(records),records)
        core.write(out/name/'review.json',{'review':value,'findings':records})
        (out/name/'review.md').write_text(value['summary']+'\n\n'+value['strengths']+'\n\n'+body+'\n')
        return {'review':value,'findings':records}
    core.write(root/'status.json',{'stage':'parallel_reviews','paper_id':pid})
    reviews=parallel({name:lambda name=name:review(name) for name in ['reviewer_1','reviewer_2','reviewer_3']})
    records={k:v for review in reviews.values() for k,v in review['findings'].items()}
    core.write(out/'initial_reviews.json',reviews)
    def discuss(name):
        text=context+prompt.DISCUSS+'\nYOUR ORIGINAL REVIEW ID\n'+name+'\nALL INITIAL REVIEWS\n'+json.dumps(reviews)
        value=core.call(protocol,out/(name+'_discussion'),text,schemas.discuss(source,records),name+'_discussion')
        assert set(value['positions'])==set(records)
        for position in value['positions'].values():core.resolve(position['evidence_ids'],source)
        core.write(out/(name+'_discussion')/'response.json',value)
        return value
    core.write(root/'status.json',{'stage':'parallel_discussion','paper_id':pid})
    discussion=parallel({name:lambda name=name:discuss(name) for name in reviews})
    core.write(root/'status.json',{'stage':'moderator','paper_id':pid})
    text=context+prompt.MODERATE+'\nORIGINAL REVIEWS\n'+json.dumps(reviews)+'\nDISCUSSION\n'+json.dumps(discussion)
    moderated=core.call(protocol,out/'moderator',text,schemas.moderate(source,records),'moderator')
    assert set(moderated['resolutions'])==set(records)
    issues=[]
    eligible=[]
    for fid,r in moderated['resolutions'].items():
        core.resolve(r['evidence_ids'],source)
        if r['status']=='duplicate' and (r['duplicate_of'] not in records or r['duplicate_of']==fid):
            raise core.Blocked('Invalid duplicate target')
        if r['status']!='duplicate' and r['duplicate_of']:
            raise core.Blocked('Unexpected duplicate target')
        if r['status']=='supported':
            if r['evidence_ids'] and records[fid]['evidence_ids']:eligible.append(fid)
            else:issues.append({'finding_id':fid,'issue':'Supported status without located evidence, excluded from selection'})
    if not set(moderated['selected_ids'])<=set(eligible):
        raise core.Blocked('Moderator selected an unsupported or unlocated finding')
    debate_body=core.selected(moderated['selected_ids'],records)
    core.write(out/'moderator/report.json',moderated)
    (out/'moderator/review.md').write_text(debate_body+'\n')
    core.write(root/'status.json',{'stage':'editor','paper_id':pid})
    text=context+prompt.EDIT+'\nORIGINAL REVIEWS\n'+json.dumps(reviews)+'\nDISCUSSION REPORT\n'+json.dumps(moderated)
    decision=core.call(protocol,out/'editor',text,schemas.editor(records,eligible),'editor')
    assert set(decision['dispositions'])==set(records)
    if not set(decision['selected_ids'])<=set(eligible):raise core.Blocked('Editor selected ineligible finding')
    if not all(reason.strip() for reason in decision['dispositions'].values()):raise core.Blocked('Empty disposition')
    body=core.selected(decision['selected_ids'],records)
    core.write(out/'editor/decision.json',decision)
    (out/'editor/review.md').write_text(body+'\n')
    result={'records':records,'discussion':discussion,'moderator':moderated,'editor':decision,'quality_issues':issues,
            'stage_ids':{**{name:list(value['findings']) for name,value in reviews.items()},
                         'panel_union':list(records),'post_debate':moderated['selected_ids'],'final':decision['selected_ids']}}
    core.write(out/'generation.json',result)
    return result


def evaluate(protocol,pid,generation):
    root=core.ROOT
    out=root/'work'/pid
    records=generation['records']
    candidates=[{'origin_id':fid,'source_quote':core.render(f)} for fid,f in records.items()]
    baseline=core.read(root/'inputs'/pid/'single_agent_packet.json')
    candidates += [{'origin_id':'single_'+c['id'],'source_quote':c['source_quote']} for c in baseline['concerns']]
    assert sum(len(c['source_quote'].split()) for c in baseline['concerns'])<=900
    random.Random(f"{protocol['seed']}:{pid}").shuffle(candidates)
    key={f'C{i:02d}':c['origin_id'] for i,c in enumerate(candidates,1)}
    blind={identifier:{'source_quote':c['source_quote']} for identifier,c in zip(key,candidates)}
    core.write(out/'candidate_key.json',key)
    core.write(out/'anonymous_candidates.json',blind)
    source=core.read(root/'inputs'/pid/'source_chunks.json')
    refs=core.read(root/'inputs'/pid/'reference.json')['concerns']
    for judge in ['A','B']:
        dest=out/('judge_'+judge)
        if (dest/'judgment.json').exists():continue
        if any(not u.get('ok') for u in core.shared.jsonl(dest/'usage.jsonl')):continue
        ordered=blind if judge=='A' else dict(reversed(list(blind.items())))
        ordered_refs=refs if judge=='A' else list(reversed(refs))
        extra='\nConsider an alternative interpretation for every match and support label.\n' if judge=='B' else ''
        text=prompt.SAFETY+prompt.JUDGE+extra+'\nMANUSCRIPT\n'+core.source_text(source)
        text+='\nHUMAN-DERIVED REFERENCES\n'+json.dumps(ordered_refs)+'\nANONYMOUS CANDIDATES\n'+json.dumps(ordered)
        core.write(root/'status.json',{'stage':'scoring','paper_id':pid,'judge':judge})
        try:
            value=core.call(protocol,dest,text,schemas.judge(source,[r['id'] for r in refs],blind),'judge_'+judge)
            assert set(value['matches'])=={r['id'] for r in refs}
            assert set(value['support'])==set(blind)
            for row in value['matches'].values():
                if not set(row['candidate_ids'])<=set(blind):raise core.Blocked('Unknown candidate ID')
            for row in value['support'].values():
                row['resolved_evidence']=core.resolve(row['evidence_ids'],source)
                row['evidence_valid']=row['label']=='insufficient_evidence' or bool(row['resolved_evidence'])
            core.write(dest/'judgment.json',value)
        except Exception as exc:
            core.write(dest/'failure.json',{'error':str(exc),'retry':False})


def summarize(protocol):
    root=core.ROOT
    rows, missing, audit = [], [], []
    for pid in protocol['paper_ids']:
        out=root/'work'/pid
        if not (out/'generation.json').exists():
            missing.append({'paper_id':pid,'stage':'generation'})
            continue
        generation=core.read(out/'generation.json')
        if not (out/'candidate_key.json').exists():
            missing.append({'paper_id':pid,'stage':'evaluation'})
            continue
        key=core.read(out/'candidate_key.json')
        inverse={v:k for k,v in key.items()}
        refs=core.read(root/'inputs'/pid/'reference.json')['concerns']
        js={j:core.read(out/('judge_'+j)/'judgment.json') for j in ['A','B'] if (out/('judge_'+j)/'judgment.json').exists()}
        for j in ['A','B']:
            if j not in js:missing.append({'paper_id':pid,'stage':'judge_'+j})
        stage_ids={**generation['stage_ids'],'saved_single_agent':[i for i in inverse if i.startswith('single_')]}
        for stage,ids in stage_ids.items():
            anon={inverse[i] for i in ids}
            matched={j:{ref for ref,row in v['matches'].items() if anon.intersection(row['candidate_ids'])} for j,v in js.items()}
            supported={j:{i for i in anon if v['support'][i]['label']=='supported' and v['support'][i]['evidence_valid']} for j,v in js.items()}
            contradicted={j:{i for i in anon if v['support'][i]['label']=='contradicted' and v['support'][i]['major'] and v['support'][i]['evidence_valid']} for j,v in js.items()}
            invalid=sum(not v['support'][i]['evidence_valid'] for v in js.values() for i in anon)
            complete=len(js)==2
            both=len(matched['A']&matched['B']) if complete else None
            rows.append({'paper_id':pid,'stage':stage,'concerns':len(ids),'reference_count':len(refs),
                         'matched_by_judge':{j:len(s) for j,s in matched.items()},'matched_both':both,
                         'coverage_both':both/len(refs) if complete else None,
                         'supported_both':len(supported['A']&supported['B']) if complete and not invalid else None,
                         'contradicted_major_both':len(contradicted['A']&contradicted['B']) if complete and not invalid else None,
                         'invalid_support_judgments':invalid})
        for candidate,body in core.read(out/'anonymous_candidates.json').items():
            audit.append({'paper_id':pid,'candidate_id':candidate,**body,'human_rating':None})
    by={(r['paper_id'],r['stage']):r for r in rows}
    comparisons={}
    for baseline in ['reviewer_1','saved_single_agent','post_debate']:
        pids=[p for p in protocol['paper_ids'] if (p,'final') in by and (p,baseline) in by and
              by[p,'final']['coverage_both'] is not None and by[p,baseline]['coverage_both'] is not None]
        diffs=[by[p,'final']['coverage_both']-by[p,baseline]['coverage_both'] for p in pids]
        comparisons[baseline]={'paper_ids':pids,'mean_difference':statistics.mean(diffs) if diffs else None,
                               'wins':sum(d>0 for d in diffs),'ties':sum(d==0 for d in diffs),'losses':sum(d<0 for d in diffs)}
    usage=core.usage()
    quality=any(core.read(root/'work'/p/'generation.json')['quality_issues'] for p in protocol['paper_ids'] if (root/'work'/p/'generation.json').exists())
    invalid=any(r['invalid_support_judgments'] for r in rows)
    complete=not missing and not quality and not invalid and not any(not r.get('ok') for r in usage)
    no_added_false=complete and all(by[p,'final']['contradicted_major_both']<=by[p,b]['contradicted_major_both']
                                    for p in protocol['paper_ids'] for b in ['reviewer_1','saved_single_agent'])
    promising=no_added_false and all(comparisons[b]['mean_difference']>0 and comparisons[b]['wins']>=2 for b in ['reviewer_1','saved_single_agent'])
    costs={p:{'panel_generation_tokens':sum(u.get('observed_tokens',0) for path in (root/'work'/p).rglob('usage.jsonl')
                                         if not path.parent.name.startswith('judge_') for u in core.shared.jsonl(path)),
              'reviewer_1_tokens':sum(u.get('observed_tokens',0) for u in core.shared.jsonl(root/'work'/p/'reviewer_1/usage.jsonl')),
              'saved_single_agent_tokens':sum(u.get('observed_tokens',0) for u in core.shared.jsonl(root/'inputs'/p/'single_agent_usage.jsonl') if u['label']!='extract_final_concerns')}
           for p in protocol['paper_ids']}
    result={'phase':'development','scientific_results':False,'rows':rows,'comparisons':comparisons,'missing':missing,
            'screening_signal':'promising_pending_human_audit' if promising else 'improvement_not_demonstrated' if complete else 'inconclusive',
            'calls':len(usage),'observed_tokens':sum(u.get('observed_tokens',0) for u in usage),
            'unknown_usage_calls':sum('observed_tokens' not in u for u in usage),'costs':costs,
            'requested_models':sorted({u['model_requested'] for u in usage}), 'human_audit':'pending',
            'limitations':['Previously exposed development papers with unverified manuscript-review version pairing.',
                           'Same-model automated judges do not establish correctness.',
                           'Panel union has more concern slots and is a diagnostic only.',
                           'Coverage is derived from a jointly scored anonymous candidate pool, not independent scoring per final review.',
                           'The first reviewer is a constituent baseline, and its findings can enter the final review.',
                           'Saved single-agent packets were selected by the prior common extractor.',
                           'A post-debate versus final contrast does not isolate debate causally.',
                           'Actual resolved model identity is absent from the CLI event stream.']}
    core.write(root/'report.json',result)
    random.Random(protocol['seed']).shuffle(audit)
    core.write(root/'manual_audit.json',{'items':audit[:15],'sampling':'15 random candidate concerns, no human ratings supplied'})
    core.write(root/'status.json',{'stage':'complete_available','screening_signal':result['screening_signal'],'missing':missing,'human_audit':'pending'})
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['prepare','run','summarize'])
    args=parser.parse_args()
    if args.command=='prepare':
        core.prepare()
        print('Prepared and frozen')
        return
    protocol=core.verify()
    if args.command=='run':
        core.shared.require_subscription(core.ROOT)
        for pid in protocol['paper_ids']:
            try:
                generation=generate(protocol,pid)
                evaluate(protocol,pid,generation)
            except Exception as exc:
                core.write(core.ROOT/'work'/pid/'failure.json',{'error':str(exc),'retry':False})
                print(f'Paper stopped: {pid}: {exc}',flush=True)
    result=summarize(protocol)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
