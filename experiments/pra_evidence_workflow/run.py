"""Staged evidence smoke test and two-paper ordinary-review comparison."""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO))
from paper_workspace.annotations import export_draft,save_review,verify_workspace
from paper_workspace.ingest import import_paper
from paper_workspace.model_runtime import model_call,require_subscription,source_manifest,jsonl
from paper_workspace.review_schema import COMMON,REVIEW,DEBATE
from paper_workspace.reviewer import debate_prompt,editor_package
from paper_workspace.scaffold_checks import build_report,compact_summary
from paper_workspace.storage import read,write,digest
from paper_workspace.evidence_tasks import PLAN,EVIDENCE_REVIEW,planner_prompt,prepare_evidence,validate_task_results,complete_inspected_images,normalize_plan
from experiments.pra_evidence_workflow.evaluation import EVALUATION,INSTRUCTIONS,validate

ROOT=REPO/'runs/pra-evidence-workflow-v1'
SCAFFOLD=Path('/home/ty/Repos/paper-scaffold')
PROTOCOL={'provider':'codex','model':'gpt-5.6-sol','effort':'medium','held_out_runs_authorized':False,
          'max_calls_per_condition':11,'observed_token_stop':600000,'call_timeout_seconds':600,
          'max_source_images':10,'image_budget_version':'evidence-v1',
          'stage':'evidence-workflow-v1','ordinary_source_operations':6,
          'eager_evidence_operations':4,'debate_operations':2,'literature_search':False,
          'shared_prefetched_pages':True}


def frozen(path,value):
    if path.exists() and read(path)!=value:raise ValueError('Frozen input changed: '+str(path))
    write(path,value)


def initialize():
    frozen(ROOT/'protocol.json',PROTOCOL)
    billing=read(ROOT/'billing_confirmation.json')
    if not billing.get('no_paid_credits_verified') or not 0<=time.time()-billing.get('checked_at',0)<86400:
        raise ValueError('A fresh subscription credit check is required')
    require_subscription(ROOT)


def call(workspace,label,prompt,schema,*,images=None,tool_limit=0,cutoff='2023-01-01'):
    verify_workspace(workspace)
    if tool_limit:
        write(ROOT/'execution/workspace/tool-config.json',{
            'paper':str(workspace.resolve()),'output':str((ROOT/'investigations'/label).resolve()),
            'cache':str((ROOT/'citation-cache').resolve()),'allow_literature':False,
            'tool_limit':tool_limit,'literature_cutoff':cutoff})
    write(ROOT/'progress.json',{'status':'running','stage':label})
    result=model_call(PROTOCOL,ROOT/'execution',prompt,schema,label=label,
                      tools=bool(tool_limit),images=[Path(row['path']) for row in images or []])
    frozen(ROOT/'raw'/f'{label}.json',result)
    return result


def source_context(paper,workspace):
    return json.dumps({'title':paper['title'],'original_pdf_pages':paper['statistics']['pdf_pages'],
        'original_pdf_available_through_view_page':True,'assets':paper['assets'],
        'references':paper['references']},ensure_ascii=False)+'\nMANUSCRIPT:\n'+(workspace/'manuscript.md').read_text()


def attached_images(prepared):
    unique={}
    for row in prepared['images']:
        unique.setdefault(row['sha256'],row)
    return list(unique.values())


def delivered_context(prepared):
    result={k:prepared[k] for k in ('paper_id','source_sha256','plan_sha256',
        'receipt_manifest_sha256','task_packets','images','limitations')}
    result['images']=attached_images(prepared)
    result['image_delivery']='Identical page content is attached once. Receipts remain specific to each operation.'
    return result


def validated_response(evidence,validation):
    return {**evidence,'task_results':validation['task_results'],
            'task_validation':validation['task_result_validation'],
            'unexpected_task_ids':validation['unexpected_task_ids'],
            'validation_limitation':validation['validation_limitation']}


def evidence_prompt(paper,workspace,plan,prepared):
    rules=COMMON.replace('Give at most five distinct, consequential findings',
                         'Produce at most eight distinct candidate findings and select at most five by selected_finding_numbers')
    return rules+'''\nComplete the supplied evidence tasks using the actual source pages and tool results below. These operations were executed by the runner. Do not claim to have performed additional searches or inspections. Cite the receipt IDs for each task and exact manuscript quotations. Distinguish observations from interpretation, articulate the author's strongest explanation, and state unresolved evidence honestly. A delivered page is not proof that its contents support an allegation. Task or map wording is a hypothesis to test, not a finding to endorse. Report all candidate findings, then select the strongest at most five by one-based finding numbers. Do not omit a concrete design or measurement issue in favor of a generic statistical comment. No tools or network are available in this interpretation stage.\nEXPERIMENT MAP AND TASKS:\n'''+json.dumps(plan,ensure_ascii=False)+'\nDELIVERED EVIDENCE:\n'+json.dumps(delivered_context(prepared),ensure_ascii=False)+'\n'+source_context(paper,workspace)


def selected_review(paper,workspace,response,review_id):
    all_findings=save_review(workspace,response,review_id+'-candidates')['findings']
    numbers=response['selected_finding_numbers']
    if (len(numbers)>5 or len(set(numbers))!=len(numbers)
            or any(type(n) is not int or not 1<=n<=len(all_findings) for n in numbers)):
        raise ValueError('Invalid selected finding numbers')
    candidates={**response,'findings':all_findings}
    selected={**response,'findings':[all_findings[n-1] for n in numbers]}
    save_review(workspace,selected,review_id)
    return candidates,selected


def lock_code(name,extra):
    value={'protocol':PROTOCOL,'code':source_manifest(REPO/'paper_workspace'),
           'runner':source_manifest(HERE),
           'study_plan_sha256':digest((REPO/'docs/pra-evidence-workflow-protocol.md').read_bytes()),**extra}
    frozen(ROOT/f'{name}-manifest.json',value)
    for path,relative in [(REPO/'paper_workspace','paper_workspace'),(HERE,'runner')]:
        target=ROOT/'frozen-source'/name/relative
        if not target.exists():shutil.copytree(path,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))


def smoke():
    initialize()
    workspace=ROOT/'workspaces/smoke'
    original=REPO/'runs/pra-workspace-four-paper-v1/workspaces/paper-2'
    if not (workspace/'paper.json').exists():
        old=verify_workspace(original)
        import_paper(original/'original.pdf',workspace,None,old['title'],old.get('source_url',''))
    paper=verify_workspace(workspace)
    plan=read(ROOT/'smoke-plan.json')
    lock_code('smoke',{'source_manifest_sha256':digest((workspace/'manifest.json').read_bytes()),'plan':plan})
    prepared=prepare_evidence(workspace,plan,ROOT/'evidence/smoke',operation_limit=4)
    if not prepared['images']:raise ValueError('Smoke test must supply an original page')
    result=call(workspace,'smoke-evidence',evidence_prompt(paper,workspace,plan,prepared),
                EVIDENCE_REVIEW,images=attached_images(prepared))
    validation=validate_task_results(paper,result,prepared)
    frozen(ROOT/'smoke-validation.json',validation)
    selected_review(paper,workspace,validated_response(result,validation),'smoke')
    print(json.dumps(validation,indent=2))


def prepare_study():
    gate=read(ROOT/'smoke-gate.json')
    if not gate.get('passed'):raise ValueError('Evidence-stage smoke gate has not passed')
    selection=read(ROOT/'source-selection.json')
    papers=selection['papers']
    if {p['id'] for p in papers}!={'paper-1','paper-2'} or len(papers)!=2:
        raise ValueError('Exactly two fresh papers are required')
    if len({p['doi'].lower() for p in papers})!=2:raise ValueError('Duplicate source DOI')
    for item in papers:
        workspace=ROOT/'workspaces'/item['id']
        if not (workspace/'paper.json').exists():
            import_paper(item['pdf'],workspace,None,item['title'],item['source_url'])
        paper=verify_workspace(workspace)
        if paper['source_sha256']!=digest(Path(item['pdf']).read_bytes()):raise ValueError('Selected PDF changed')
        if paper['statistics']['total_words']>15000:raise ValueError('Paper exceeds bounded text size')
        text=(workspace/'manuscript.md').read_text().casefold()
        if any(s in text for s in ('elife assessment','public review:','reviewer #','author response:')):
            raise ValueError('Review history remains in manuscript')
        concerns=read(item['human_concerns'])['concerns']
        if not concerns or len({c['id'] for c in concerns})!=len(concerns):raise ValueError('Invalid concern IDs')
        human=Path(item['human_reviews']).read_text()
        for c in concerns:
            if not c['quote'] or c['quote'] not in human:raise ValueError('Invalid human quotation')
            if type(c['manuscript_assessable']) is not bool:raise ValueError('Missing assessability decision')
        frozen(ROOT/'diagnostics'/f"{item['id']}.json",build_report(workspace,SCAFFOLD))
    lock_code('study',{'selection':selection,'smoke_gate':gate,
        'sources':{p['id']:digest((ROOT/'workspaces'/p['id']/'manifest.json').read_bytes()) for p in papers},
        'diagnostics':{p['id']:digest((ROOT/'diagnostics'/f"{p['id']}.json").read_bytes()) for p in papers},
        'human_reference_hashes':{p['id']:{k:digest(Path(p[k]).read_bytes()) for k in ('human_reviews','human_concerns')} for p in papers}})
    return papers


def image_registry(paper,workspace,item,prepared):
    images=list(prepared['images'])
    for stage in ('ordinary','debate'):
        for path,label in complete_inspected_images(paper,workspace,ROOT/'investigations'/f"{item['id']}-{stage}"):
            images.append({'path':str(path),'label':label,'sha256':digest(path.read_bytes())})
    by={}
    for image in images:
        if digest(Path(image['path']).read_bytes())!=image['sha256']:raise ValueError('Image evidence changed')
        by.setdefault(image['sha256'],{k:image[k] for k in ('path','label','sha256')})
    rows=sorted(by.values(),key=lambda r:(r['label'],r['sha256']))
    if len(rows)>10:raise ValueError('Complete shared image packet exceeds the fixed cap')
    return [{'id':f'image-{n}',**row} for n,row in enumerate(rows,1)]


def support_counts(row,assessable):
    ratings={r['finding_id']:r for r in row['ratings']}
    counts={}
    for scope in ('all','assessable'):
        for support in ('justified_concern','justified_clarification','either'):
            labels={'justified_concern','justified_clarification'} if support=='either' else {support}
            counts[f'direct_{scope}_{support}']=sum(
                m['match']=='direct' and (scope=='all' or m['human_concern_id'] in assessable)
                and any(ratings[fid]['assessment'] in labels for fid in m['finding_ids'])
                for m in row['matches'])
    return counts


def usage_details(usage,papers):
    rows=[]
    for item in usage:
        receipt=read(ROOT/'execution/calls'/f"{item['request_sha256']}.json")
        events=receipt.get('events',[])
        turns=[e.get('usage',{}) for e in events if e.get('type')=='turn.completed']
        calls=[e['item'] for e in events if e.get('type')=='item.completed'
               and e.get('item',{}).get('type')=='mcp_tool_call']
        rows.append({**item,
            'input_tokens':sum(t.get('input_tokens',0) for t in turns),
            'cached_input_tokens':sum(t.get('cached_input_tokens',0) for t in turns),
            'output_tokens':sum(t.get('output_tokens',0) for t in turns),
            'model_requested_tool_calls':len(calls),
            'tools_requested':[c.get('tool') for c in calls]})
    operations={}
    for paper in papers:
        pid=paper['id']
        prepared=read(ROOT/'evidence'/pid/'prepared-evidence.json')
        operations[pid]={'eager_evidence_operations':len(prepared['receipts']),
            'successful_eager_operations':sum(r['status']=='succeeded' for r in prepared['receipts']),
            'eager_page_operations':len(prepared['images']),
            'prefetched_page_deliveries':len(attached_images(prepared)),
            'shared_evaluator_images':len(read(ROOT/'responses'/pid/'images.json')),
            'ordinary_model_tool_calls':sum(r['model_requested_tool_calls'] for r in rows if r['label']==pid+'-ordinary'),
            'debate_model_tool_calls':sum(r['model_requested_tool_calls'] for r in rows if r['label']==pid+'-debate')}
    return rows,operations


def development_gate(metrics,papers):
    rows=[]
    for paper in papers:
        by={r['condition']:r for r in metrics if r['paper']==paper['id']}
        ordinary,debate=by['ordinary'],by['debate']
        gain=debate['direct_assessable_either']-ordinary['direct_assessable_either']
        no_extra_unsupported=debate['unsupported_major']<=ordinary['unsupported_major']
        rows.append({'paper':paper['id'],'supported_direct_gain':gain,
                     'no_additional_unsupported_major':no_extra_unsupported,
                     'automatic_criterion_met':gain>=2 and no_extra_unsupported})
    return {'papers':rows,'automatic_criterion_met':all(r['automatic_criterion_met'] for r in rows),
            'limitation':'A development threshold based on one automated evaluator per paper. Decisive matches still need source audit and independent expert validation.'}


def execute_study(papers):
    initialize()
    for item in papers:
        pid=item['id']
        workspace=ROOT/'workspaces'/pid
        paper=verify_workspace(workspace)
        report=compact_summary(read(ROOT/'diagnostics'/f'{pid}.json'))
        raw_plan=call(workspace,pid+'-plan',planner_prompt(paper,(workspace/'manuscript.md').read_text(),report),PLAN)
        plan,changes=normalize_plan(paper,raw_plan)
        frozen(ROOT/'planning'/pid/'normalized-plan.json',plan)
        frozen(ROOT/'planning'/pid/'normalization-audit.json',{
            'raw_plan_sha256':digest((ROOT/'raw'/f'{pid}-plan.json').read_bytes()),
            'normalized_plan_sha256':digest((ROOT/'planning'/pid/'normalized-plan.json').read_bytes()),
            'changes':changes,'limitation':'Deterministic source-reference syntax normalization only. No review task or scientific claim is repaired.'})
        prepared=prepare_evidence(workspace,plan,ROOT/'evidence'/pid,operation_limit=4)
        images=attached_images(prepared)
        if not images:raise ValueError('No planned original PDF page was delivered')
        ordinary_prompt=COMMON+'''\nGive a thorough scientific review as an ordinary single reviewer. You have the full manuscript, selected original PDF pages, and tools for any additional evidence. Inspect key figures and methods, test alternative explanations, and resolve important uncertainties before selecting your strongest five findings. The attached pages are original source material, not annotations or findings from another reviewer. Page viewing, manuscript search, and small arithmetic are available. Literature search is disabled. Six source operations are allowed in total, including the attached pages. You have '''+str(6-len(images))+''' additional tool calls. Do not claim material is unavailable merely because no separate figure file is listed.\nATTACHED PAGES:\n'''+json.dumps([r['label'] for r in images])+'\n'+source_context(paper,workspace)
        ordinary=call(workspace,pid+'-ordinary',ordinary_prompt,REVIEW,images=images,
                      tool_limit=6-len(images),cutoff=item['literature_cutoff'])
        ordinary={**ordinary,'findings':save_review(workspace,ordinary,'ordinary')['findings']}
        frozen(ROOT/'responses'/pid/'ordinary.json',ordinary)
        evidence=call(workspace,pid+'-evidence',evidence_prompt(paper,workspace,plan,prepared),EVIDENCE_REVIEW,images=images)
        validation=validate_task_results(paper,evidence,prepared)
        frozen(ROOT/'responses'/pid/'task-validation.json',validation)
        evidence=validated_response(evidence,validation)
        candidates,selected=selected_review(paper,workspace,evidence,'evidence')
        frozen(ROOT/'responses'/pid/'candidates.json',candidates)
        frozen(ROOT/'responses'/pid/'evidence.json',selected)
        debate_text=debate_prompt(paper,[candidates])+'''\nThe source review contains up to eight candidates. Select at most five. Preserve every candidate through an explicit disposition, including candidates not selected in the preliminary review. Task observations are fallible interpretations, not established facts. Challenge concrete allegations against the delivered evidence and author-side alternatives. Do not preserve a concern merely to agree with the investigator. Source access receipts establish delivery only. You have two further tools. Original PDF pages remain available. Literature search is disabled.\nDELIVERED EVIDENCE:\n'''+json.dumps(delivered_context(prepared),ensure_ascii=False)
        final=call(workspace,pid+'-debate',debate_text,DEBATE,images=images,tool_limit=2,cutoff=item['literature_cutoff'])
        final={**final,'findings':save_review(workspace,final,'debate-selected')['findings']}
        frozen(ROOT/'responses'/pid/'debate.json',final)
        package=editor_package(final,[candidates],paper)
        package['task_results']=validation['task_results']
        package['task_validation']=validation['task_result_validation']
        package['experiment_map']=plan['experiment_map']
        package['evidence_provenance']={k:prepared[k] for k in
            ('source_sha256','plan_sha256','receipt_manifest_sha256','execution_log_sha256')}
        review=save_review(workspace,package,'panel')
        frozen(ROOT/'responses'/pid/'editor-package.json',package)
        frozen(ROOT/'responses'/pid/'review-package.json',export_draft(paper,review,{'paper_id':paper['id'],'items':{}}))
        frozen(ROOT/'responses'/pid/'images.json',image_registry(paper,workspace,item,prepared))
    frozen(ROOT/'generation-lock.json',{str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in sorted((ROOT/'responses').rglob('*.json'))})
    metrics=[]
    for index,item in enumerate(papers):
        pid=item['id']
        workspace=ROOT/'workspaces'/pid
        paper=verify_workspace(workspace)
        expected=read(ROOT/'study-manifest.json')['human_reference_hashes'][pid]
        if any(digest(Path(item[k]).read_bytes())!=sha for k,sha in expected.items()):raise ValueError('Human reference changed')
        conditions={c:read(ROOT/'responses'/pid/f'{c}.json') for c in ('ordinary','evidence','debate')}
        order=['ordinary','evidence','debate'] if index==0 else ['debate','ordinary','evidence']
        mapping=dict(zip(('A','B','C'),order))
        anonymous={label:[{'finding_id':f'{label}{n}',**{k:f.get(k) for k in
            ('title','block_id','quote','kind','severity','comment','replacement','evidence_blocks','counterevidence','placement','edit_withheld')}}
            for n,f in enumerate(conditions[c]['findings'],1)] for label,c in mapping.items()}
        concerns=read(item['human_concerns'])['concerns']
        images=read(ROOT/'responses'/pid/'images.json')
        prompt=INSTRUCTIONS+'\nHUMAN REFERENCE CONCERNS:\n'+json.dumps(concerns,ensure_ascii=False)
        prompt+='\nANONYMOUS REVIEWS:\n'+json.dumps(anonymous,ensure_ascii=False)
        prompt+='\nSHARED IMAGE REGISTRY:\n'+json.dumps([{k:r[k] for k in ('id','label','sha256')} for r in images])
        prompt+='\nSOURCE LIMITATIONS:\n'+json.dumps(item.get('limitations',[]))+'\n'+source_context(paper,workspace)
        result=call(workspace,pid+'-evaluation',prompt,EVALUATION,images=images)
        validate(result,anonymous,concerns,paper,images)
        frozen(ROOT/'evaluation'/pid/'label-map.json',mapping)
        frozen(ROOT/'evaluation'/pid/'validated.json',result)
        for row in result['conditions']:
            assessable={c['id'] for c in concerns if c['manuscript_assessable']}
            metrics.append({'paper':pid,'condition':mapping[row['label']],'all_concerns':len(concerns),
                'assessable_concerns':len(assessable),
                **support_counts(row,assessable),
                'direct_all':sum(m['match']=='direct' for m in row['matches']),
                'partial_all':sum(m['match']=='partial' for m in row['matches']),
                'direct_assessable':sum(m['match']=='direct' and m['human_concern_id'] in assessable for m in row['matches']),
                'partial_assessable':sum(m['match']=='partial' and m['human_concern_id'] in assessable for m in row['matches']),
                'assessments':{s:sum(r['assessment']==s for r in row['ratings']) for s in
                    ('justified_concern','justified_clarification','unsupported_allegation','unverifiable')},
                'meaningful_specificity':sum(r['specificity']=='meaningful' for r in row['ratings']),
                'unsupported_major':sum(r['assessment']=='unsupported_allegation' and r['materiality']=='major' for r in row['ratings'])})
    usage=jsonl(ROOT/'execution/usage.jsonl')
    details,operations=usage_details(usage,papers)
    result={'status':'complete','metrics':metrics,'calls':len(usage),
            'observed_tokens':sum(r.get('observed_tokens',0) for r in usage),'usage_by_call':details,
            'source_operations':operations,
            'development_gate':development_gate(metrics,papers),
            'limitations':['Two-paper development comparison','One automated evaluator per paper',
              'No independent domain-expert grading','Ordinary reviewer also receives planner-selected raw pages',
              'Equal source-operation allowances do not equalize consumed model tokens','Three label positions cannot be balanced across two papers']}
    frozen(ROOT/'results.json',result)
    write(ROOT/'progress.json',{'status':'complete','calls':len(usage),'observed_tokens':result['observed_tokens']})
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['smoke','prepare','study'])
    args=parser.parse_args()
    try:
        if args.stage=='smoke':smoke()
        elif args.stage=='prepare':prepare_study()
        else:execute_study(prepare_study())
    except Exception as exc:
        write(ROOT/'progress.json',{'status':'blocked','error':str(exc)})
        raise
