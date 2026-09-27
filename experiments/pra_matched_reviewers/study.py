"""Matched strong reviewers with a shared-panel debate ablation."""

import argparse
import fcntl
import json
import random
import statistics
from concurrent.futures import ThreadPoolExecutor

import core
import prompts as prompt
import schemas


def parallel(tasks):
    results,failures={},[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={name:pool.submit(fn) for name,fn in tasks.items()}
        for name,future in futures.items():
            try:results[name]=future.result()
            except Exception as exc:failures.append(f'{name}: {exc}')
    if failures:raise core.Blocked('\n'.join(failures))
    return results


def validate_editor(value,records,source):
    if set(value['dispositions'])!=set(records):raise core.Blocked('Missing editorial disposition')
    retained={fid for fid,r in value['dispositions'].items() if r['status'] in ['major','minor','unresolved']}
    if set(value['ranking'])!=retained or len(value['ranking'])!=len(retained):
        raise core.Blocked('Every retained concern must appear exactly once in the ranking')
    for fid,row in value['dispositions'].items():
        if not row['reason'].strip():raise core.Blocked('Every disposition needs a reason')
        core.resolve(row['evidence_ids'],source)
        if row['status']=='answered' and not row['evidence_ids']:
            raise core.Blocked('Answered finding requires located manuscript evidence')
        if row['status']=='duplicate':
            if row['duplicate_of'] not in retained or row['duplicate_of']==fid:
                raise core.Blocked('Duplicate must point to another retained complete finding')
        elif row['duplicate_of']:raise core.Blocked('Unexpected merge target')
    return retained


def render_report(value,records):
    parts=['# Review',value['summary'],'## Strengths',value['strengths']]
    for status,title in [('major','Major concerns'),('minor','Minor concerns'),('unresolved','Unresolved concerns')]:
        parts.append('## '+title)
        ids=[fid for fid in value['ranking'] if value['dispositions'][fid]['status']==status]
        parts.extend(f"### {fid}\n\n{records[fid]['text']}" for fid in ids)
        if not ids:parts.append('None recorded.')
    parts+=['## Unresolved discussion',value['unresolved_note'],'## Disposition appendix']
    for fid,row in value['dispositions'].items():
        parts.append(f"### {fid}: {row['status']}\n\n{row['reason']}")
        if row['status'] in ['duplicate','answered']:parts.append(records[fid]['text'])
    return '\n\n'.join(parts)+'\n'


def generate(protocol,pid):
    root=core.ROOT
    out=root/'work'/pid
    inputs=root/'inputs'/pid
    if (out/'generation.json').exists():return core.read(out/'generation.json')
    manuscript=(inputs/'manuscript.txt').read_text()
    request=core.read(inputs/'review_request.json')
    source=core.read(inputs/'source_chunks.json')
    raw={'reviewer_1':(inputs/'reviewer_1.md').read_text()}
    def review(name):
        result=core.call(protocol,out/name,request['prompt'],request['schema'],name,manuscript=manuscript)
        body=result['content']
        (out/name/'review.md').write_text(body)
        return body
    core.write(root/'status.json',{'stage':'matched_tool_reviews','paper_id':pid})
    raw.update(parallel({name:lambda name=name:review(name) for name in ['reviewer_2','reviewer_3']}))
    core.write(out/'raw_reviews.json',raw)
    def index(name):
        paras=core.paragraphs(raw[name])
        text=prompt.SAFETY+prompt.INDEX+'\nREVIEW\n'+'\n\n'.join(f'PARAGRAPH {i}\n{p}' for i,p in enumerate(paras,1))
        value=core.call(protocol,out/(name+'_index'),text,schemas.index(len(paras)),name+'_index')
        findings=core.index_findings(value,raw[name],name)
        core.write(out/(name+'_index')/'findings.json',findings)
        return findings
    core.write(root/'status.json',{'stage':'indexing_complete_concerns','paper_id':pid})
    indexed=parallel({name:lambda name=name:index(name) for name in raw})
    records={fid:f for name in raw for fid,f in indexed[name].items()}
    core.write(out/'finding_ledger.json',records)
    context=prompt.SAFETY+'\nMANUSCRIPT\n'+core.source_text(source)+'\nORIGINAL REVIEWS\n'+json.dumps(raw)
    context+='\nIMMUTABLE FINDINGS\n'+json.dumps(records)
    def edit(branch,discussion):
        text=context+'\n'+prompt.EDITOR+'\nDISCUSSION\n'+json.dumps(discussion)
        value=core.call(protocol,out/branch,text,schemas.editor(source,records),branch)
        validate_editor(value,records,source)
        core.write(out/branch/'decision.json',value)
        (out/branch/'review.md').write_text(render_report(value,records))
        packet=core.top_packet(value['ranking'],records)
        core.write(out/branch/'top_packet.json',packet)
        return value,packet
    core.write(root/'status.json',{'stage':'editor_without_debate','paper_id':pid})
    without,without_packet=edit('editor_only',[])
    def debate(name):
        text=context+'\n'+prompt.DEBATE+'\nYOUR ORIGINAL REVIEW\n'+name
        value=core.call(protocol,out/(name+'_debate'),text,schemas.debate(source,records),name+'_debate')
        for item in value['interventions']:
            if not item['finding_ids'] or not set(item['finding_ids'])<=set(records):raise core.Blocked('Invalid discussion finding ID')
            core.resolve(item['evidence_ids'],source)
            core.resolve(item['counterevidence_ids'],source)
        core.write(out/(name+'_debate')/'discussion.json',value)
        return value
    core.write(root/'status.json',{'stage':'focused_parallel_debate','paper_id':pid})
    discussion=parallel({name:lambda name=name:debate(name) for name in raw})
    core.write(out/'discussion.json',discussion)
    core.write(root/'status.json',{'stage':'editor_with_debate','paper_id':pid})
    with_debate,with_packet=edit('debate_editor',discussion)
    stages={}
    for name,items in indexed.items():
        stages[name+'_full']=list(items)
        stages[name+'_top']=core.top_packet(list(items),records)['ids']
    stages.update(panel_union=list(records),editor_only_full=without['ranking'],editor_only_top=without_packet['ids'],
                  debate_editor_full=with_debate['ranking'],debate_editor_top=with_packet['ids'])
    result={'paper_id':pid,'records':records,'stage_ids':stages,
            'editor_only':without,'debate_editor':with_debate,
            'raw_review_word_counts':{k:len(v.split()) for k,v in raw.items()},
            'baseline_request_sha256':core.shared.digest(request),'reviewer_1_reused':True}
    core.write(out/'generation.json',result)
    return result


def evaluate(protocol,pid,generation):
    out=core.ROOT/'work'/pid
    inputs=core.ROOT/'inputs'/pid
    records=list(generation['records'].values())
    random.Random(f"{protocol['seed']}:{pid}").shuffle(records)
    key={f'C{i:02d}':r['id'] for i,r in enumerate(records,1)}
    blind={cid:{'source_quote':r['text']} for cid,r in zip(key,records)}
    core.write(out/'candidate_key.json',key)
    core.write(out/'anonymous_candidates.json',blind)
    source=core.read(inputs/'source_chunks.json')
    refs=core.read(inputs/'reference.json')['concerns']
    for judge in ['A','B']:
        dest=out/('judge_'+judge)
        if (dest/'judgment.json').exists():continue
        if (dest/'validation_failure.json').exists():continue
        ordered=blind if judge=='A' else dict(reversed(list(blind.items())))
        ordered_refs=refs if judge=='A' else list(reversed(refs))
        extra='\nConsider alternative interpretations before each judgment.\n' if judge=='B' else ''
        text=prompt.SAFETY+prompt.JUDGE+extra+'\nMANUSCRIPT\n'+core.source_text(source)
        text+='\nHUMAN-DERIVED REFERENCES\n'+json.dumps(ordered_refs)+'\nANONYMOUS CANDIDATES\n'+json.dumps(ordered)
        core.write(core.ROOT/'status.json',{'stage':'anonymous_scoring','paper_id':pid,'judge':judge})
        try:
            value=core.call(protocol,dest,text,schemas.judge(source,[r['id'] for r in refs],blind),'judge_'+judge)
            assert set(value['matches'])=={r['id'] for r in refs} and set(value['support'])==set(blind)
            for row in value['matches'].values():
                if not set(row['candidate_ids'])<=set(blind):raise core.Blocked('Unknown scored candidate ID')
            for row in value['support'].values():
                row['resolved_evidence']=core.resolve(row['evidence_ids'],source)
                row['evidence_valid']=row['label']=='insufficient_evidence' or bool(row['resolved_evidence'])
            core.write(dest/'judgment.json',value)
        except Exception as exc:
            core.write(dest/'validation_failure.json',{'reason':str(exc),'further_retry':False})


def summarize(protocol):
    root=core.ROOT
    rows,missing,audit=[],[],[]
    for pid in protocol['paper_ids']:
        out=root/'work'/pid
        if not (out/'generation.json').exists():
            missing.append({'paper_id':pid,'stage':'generation'})
            continue
        generation=core.read(out/'generation.json')
        if not (out/'candidate_key.json').exists():
            missing.append({'paper_id':pid,'stage':'scoring'})
            continue
        key=core.read(out/'candidate_key.json')
        inverse={v:k for k,v in key.items()}
        refs=core.read(root/'inputs'/pid/'reference.json')['concerns']
        js={j:core.read(out/('judge_'+j)/'judgment.json') for j in ['A','B'] if (out/('judge_'+j)/'judgment.json').exists()}
        for j in ['A','B']:
            if j not in js:missing.append({'paper_id':pid,'stage':'judge_'+j})
        for stage,ids in generation['stage_ids'].items():
            anon={inverse[i] for i in ids}
            matches={j:{rid for rid,r in v['matches'].items() if anon.intersection(r['candidate_ids'])} for j,v in js.items()}
            invalid=sum(not v['support'][i]['evidence_valid'] for v in js.values() for i in anon)
            supported={j:{i for i in anon if v['support'][i]['label']=='supported' and v['support'][i]['evidence_valid']} for j,v in js.items()}
            false={j:{i for i in anon if v['support'][i]['label']=='contradicted' and v['support'][i]['major'] and v['support'][i]['evidence_valid']} for j,v in js.items()}
            both=len(matches['A']&matches['B']) if len(js)==2 else None
            rows.append({'paper_id':pid,'stage':stage,'concerns':len(ids),'words':sum(len(generation['records'][i]['text'].split()) for i in ids),
                         'reference_count':len(refs),'matches_by_judge':{j:len(s) for j,s in matches.items()},
                         'matched_both':both,'coverage_both':both/len(refs) if both is not None else None,
                         'invalid_support_judgments':invalid,
                         'supported_both':len(supported['A']&supported['B']) if len(js)==2 and not invalid else None,
                         'contradicted_major_both':len(false['A']&false['B']) if len(js)==2 and not invalid else None})
        audit.extend({'paper_id':pid,'candidate_id':cid,**value,'human_rating':None}
                     for cid,value in core.read(out/'anonymous_candidates.json').items())
    by={(r['paper_id'],r['stage']):r for r in rows}
    comparisons={}
    for outcome,baseline in [('editor_only_top','reviewer_1_top'),('debate_editor_top','reviewer_1_top'),('debate_editor_top','editor_only_top')]:
        ids=[pid for pid in protocol['paper_ids'] if all((pid,s) in by and by[pid,s]['coverage_both'] is not None for s in [outcome,baseline])]
        ds=[by[p,outcome]['coverage_both']-by[p,baseline]['coverage_both'] for p in ids]
        comparisons[outcome+'_vs_'+baseline]={'paper_ids':ids,'mean_difference':statistics.mean(ds) if ds else None,
                                             'wins':sum(d>0 for d in ds),'ties':sum(d==0 for d in ds),'losses':sum(d<0 for d in ds)}
    valid=not missing and not any(r['invalid_support_judgments'] for r in rows)
    panel_better=valid and comparisons['debate_editor_top_vs_reviewer_1_top']['mean_difference']>0 and comparisons['debate_editor_top_vs_reviewer_1_top']['wins']>=2
    debate_better=valid and comparisons['debate_editor_top_vs_editor_only_top']['mean_difference']>0 and comparisons['debate_editor_top_vs_editor_only_top']['wins']>=2
    no_extra_false=valid and all(by[p,'debate_editor_top']['contradicted_major_both']<=by[p,b]['contradicted_major_both']
                               for p in protocol['paper_ids'] for b in ['reviewer_1_top','editor_only_top'])
    used=core.usage()
    costs={}
    for p in protocol['paper_ids']:
        out=root/'work'/p
        def tokens(node):
            return sum(r.get('observed_tokens',0) for path in (out/node).rglob('usage.jsonl') for r in core.shared.jsonl(path))
        inherited=core.read(root/'inputs'/p/'reviewer_1_response.json')['observed_tokens']
        shared_cost=inherited+sum(tokens('reviewer_'+str(n)) for n in [2,3])+sum(tokens(f'reviewer_{n}_index') for n in [1,2,3])
        complete=(out/'generation.json').exists()
        costs[p]={'complete_generation':complete,'single_reviewer_generation_tokens':inherited,
                  'shared_panel_and_index_tokens':shared_cost,
                  'editor_only_standalone_tokens':shared_cost+tokens('editor_only') if complete else None,
                  'debate_editor_standalone_tokens':shared_cost+sum(tokens(f'reviewer_{n}_debate') for n in [1,2,3])+tokens('debate_editor') if complete else None,
                  'interpretation':'Includes recorded inherited generation and required indexing, excludes judges. Cached input is included, not a billing estimate.'}
    result={'phase':'development','scientific_results':False,'rows':rows,'comparisons':comparisons,'missing':missing,
            'screening_signal':'promising_pending_human_audit' if panel_better and debate_better and no_extra_false else 'improvement_not_demonstrated' if valid else 'inconclusive',
            'usage':core.metrics_usage(),'costs':costs,'failed_attempts':sum(not u.get('ok') for u in used),
            'network_retries':len(list((root/'work').rglob('network_retry.json'))),
            'requested_models':sorted({u['model_requested'] for u in used}),
            'inherited_reviewer_1_tokens':{p:core.read(root/'inputs'/p/'reviewer_1_response.json')['observed_tokens'] for p in protocol['paper_ids']},
            'human_audit':'pending','limitations':['Three previously exposed papers, unverified historical version pairing and figure access.',
                'Reviewer 1 is a saved earlier run, not contemporaneous with new reviewers.',
                'All raw reviewer prompts, tools, schemas, model, and effort match the saved strong workflow.',
                'Indexing selects exact paragraphs but may omit or group issues imperfectly.',
                'Shared anonymous candidate scoring evaluates preserved concern text, not rewritten final-review quality.',
                'Full-report coverage has more slots and is diagnostic, not a length-controlled performance claim.',
                'Same-model judges and a single editor sample per branch do not establish scientific correctness or a general causal effect.',
                'Recorded tokens include repeated cached input and are not a monetary or credit charge.']}
    core.write(root/'report.json',result)
    random.Random(protocol['seed']).shuffle(audit)
    core.write(root/'manual_audit.json',{'items':audit[:15],'human_ratings':'empty'})
    core.write(root/'status.json',{'stage':'complete_available','screening_signal':result['screening_signal'],'missing':missing})
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['prepare','run','summarize'])
    args=parser.parse_args()
    if args.command=='prepare':
        core.prepare()
        print('Prepared and frozen',flush=True)
        return
    protocol=core.verify()
    if args.command=='summarize':
        print(json.dumps(summarize(protocol),indent=2))
        return
    with (core.ROOT/'runner.lock').open('w') as guard:
        fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        core.shared.require_subscription(core.ROOT)
        for pid in protocol['paper_ids']:
            try:
                generation=generate(protocol,pid)
                evaluate(protocol,pid,generation)
            except Exception as exc:
                core.write(core.ROOT/'work'/pid/'failure.json',{'reason':str(exc)})
                print(f'Paper stopped: {pid}: {exc}',flush=True)
        print(json.dumps(summarize(protocol),indent=2),flush=True)


if __name__=='__main__':main()
