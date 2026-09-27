"""One fresh manuscript with a three-pass single reviewer and staged PRA."""
import argparse
import json
from pathlib import Path
import random
import shutil
import subprocess
import time

from paper_workspace.annotations import save_review,verify_workspace
from paper_workspace.storage import read,write,digest
from paper_workspace.model_runtime import model_call,require_subscription,source_manifest,jsonl
from paper_workspace.review_schema import COMMON,REVIEW
from paper_workspace.evidence_tasks import PLAN,EVIDENCE_REVIEW,planner_prompt,normalize_plan,prepare_evidence,validate_task_results,complete_inspected_images
from paper_workspace.debate_revision import DEBATE_REVISION,issue_ledger,revision_prompt,validate_revision,revision_package
from paper_workspace.scaffold_checks import build_report,compact_summary
from experiments.pra_evidence_workflow.run import delivered_context,validated_response,selected_review
from experiments.pra_debate_revision.evaluation import EVALUATION,INSTRUCTIONS,audit

REPO=Path(__file__).resolve().parents[2]
ROOT=REPO/'runs/pra-fresh-comparison-v1'
WORK=ROOT/'workspace'
PROTOCOL={'provider':'codex','model':'gpt-5.6-sol','effort':'medium','held_out_runs_authorized':False,
 'max_calls_per_condition':7,'observed_token_stop':450000,'call_timeout_seconds':900,
 'max_source_images':10,'image_budget_version':'evidence-v1','version':'fresh-comparison-v1',
 'papers':1,'single_calls':3,'pra_calls':3,'evaluation_calls':1,
 'source_operations_per_method':6,'shared_main_pages':[4,8,12],
 'limitations':'Fresh to local development, not a confirmatory held-out study. Equal call allowances, not exact realized compute. No human-overlap endpoint.'}


def frozen(path,value):
    if path.exists():
        if read(path)!=value:raise ValueError('Frozen input changed: '+str(path))
    else:write(path,value)


def context(paper):
    blocks=[]
    for block in paper['blocks']:
        if block['kind']=='reference':continue
        item={k:block.get(k) for k in ('id','section','kind','page','text')}
        if block['kind']=='table' and len(item['text'])>1800:
            item['text']=item['text'][:1800]+'\n[TABLE PREVIEW ENDS. Retrieve this block ID for its complete reported values.]'
        blocks.append(item)
    return json.dumps({'title':paper['title'],'blocks':blocks,
       'page_registry':read(ROOT/'source-selection.json')['page_registry'],
       'source_access':'The packet contains the complete main PDF followed by all eight supplementary figure PDFs. Supplementary text is included. Long reported-results tables are previews, complete blocks are available through source tools. S11-S26 raw-data spreadsheets and code are outside this review. Lack of raw data is not a manuscript defect.'},ensure_ascii=False)


def initialize():
    paper=verify_workspace(WORK)
    frozen(ROOT/'protocol.json',PROTOCOL)
    if not (ROOT/'diagnostics.json').exists():write(ROOT/'diagnostics.json',build_report(WORK,Path('/home/ty/Repos/paper-scaffold')))
    text=(WORK/'manuscript.md').read_text().lower()
    for marker in ('reviewer #','decision letter','author response:','reviewer 1:'):
        if marker in text:raise ValueError('Review material appears in manuscript')
    images=[]
    for number in PROTOCOL['shared_main_pages']:
        path=ROOT/'images'/f'main-{number}.png'
        path.parent.mkdir(exist_ok=True)
        if not path.exists():subprocess.run(['pdftoppm','-f',str(number),'-l',str(number),'-scale-to','1500','-singlefile','-png',str(WORK/'original.pdf'),str(path.with_suffix(''))],check=True,capture_output=True)
        images.append({'path':str(path),'label':f'Original main PDF page {number}','sha256':digest(path.read_bytes())})
    frozen(ROOT/'images.json',images)
    frozen(ROOT/'freeze.json',{'source':digest((WORK/'manifest.json').read_bytes()),'selection':digest((ROOT/'source-selection.json').read_bytes()),
       'protocol':PROTOCOL,'runner':source_manifest(Path(__file__).parent),'system':source_manifest(REPO/'paper_workspace'),
       'dependencies':{str(p.relative_to(REPO)):digest(p.read_bytes()) for p in [REPO/'experiments/pra_evidence_workflow/run.py',REPO/'experiments/pra_debate_revision/evaluation.py',REPO/'experiments/pra_evidence_workflow/evaluation.py']},
       'diagnostics':digest((ROOT/'diagnostics.json').read_bytes()),'protocol_text':digest((REPO/'docs/pra-fresh-comparison-protocol.md').read_bytes())})
    if not (ROOT/'frozen-source').exists():
        for src,name in [(REPO/'paper_workspace','paper_workspace'),(Path(__file__).parent,'experiment')]:
            shutil.copytree(src,ROOT/'frozen-source'/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    return paper,images


def call(label,prompt,schema,images,limit=0,profile='legacy'):
    verify_workspace(WORK)
    if limit:write(ROOT/'execution/workspace/tool-config.json',{'paper':str(WORK),'output':str(ROOT/'investigations'/label),
        'cache':str(ROOT/'cache'),'allow_literature':False,'tool_limit':limit,'tool_profile':profile,'literature_cutoff':'2023-08-21'})
    frozen(ROOT/'requests'/f'{label}.json',{'prompt':prompt,'schema':schema,'images':images,'tool_limit':limit,'tool_profile':profile})
    write(ROOT/'progress.json',{'status':'running','stage':label})
    print('Starting '+label,flush=True)
    value=model_call(PROTOCOL,ROOT/'execution',prompt,schema,tools=bool(limit),label=label,images=[Path(i['path']) for i in images])
    frozen(ROOT/'raw'/f'{label}.json',value)
    return value


def save(label,value):
    review=save_review(WORK,value,label)
    if any(f.get('placement')!='anchored' for f in review['findings']):raise ValueError('Unanchored generation preserved for failure audit')
    frozen(ROOT/'responses'/f'{label}.json',review)
    return review


def run():
    paper,images=initialize()
    require_subscription(ROOT)
    billing=read(ROOT/'billing_confirmation.json')
    if not 0<=time.time()-billing['checked_at']<86400:raise ValueError('Stale credit verification')
    ctx=context(paper)
    advisory='\nADVISORY CHECKS:\n'+json.dumps(compact_summary(read(ROOT/'diagnostics.json')),ensure_ascii=False)
    shared='\nSOURCE PACKET:\n'+ctx+advisory+'\nATTACHED MAIN FIGURE PAGES:\n'+json.dumps([i['label'] for i in images])
    rules=COMMON+'\nFocus on consequential scientific questions. No copyedits in this scientific comparison. Use kind question and empty replacement. At most five selected findings and 900 comment words. Do not pad. Do not access public reviews or external literature. Source limitations are disclosed below.'
    single1=call('single-initial',rules+'\nYou are one reviewer working through three sequential passes. First identify provisional concerns and competing explanations from the supplied manuscript and figures. Subsequent passes can investigate and revise these. No tools in this first pass.'+shared,REVIEW,images)
    single2=call('single-investigate',rules+'\nContinue your own review. You have four source-tool calls to investigate the provisional concerns or discover better ones. Use read_blocks for full table values, literal search for author defenses, view_page for supporting figures, and calculate for small arithmetic. Do not call external citation or literature tools. Revise your review using the evidence. These are your prior notes, not another reviewer vote:\n'+json.dumps(single1,ensure_ascii=False)+shared,REVIEW,images,4)
    single_images={i['sha256']:i for i in images}
    for path,label_text in complete_inspected_images(paper,WORK,ROOT/'investigations/single-investigate'):
        single_images[digest(path.read_bytes())]={'path':str(path),'label':label_text,'sha256':digest(path.read_bytes())}
    single_receipts=jsonl(ROOT/'investigations/single-investigate/tool-log.jsonl')
    single=call('single-final',rules+'\nComplete your own review after checking its premises, counterevidence, and requested work. You have two final source checks through structured search_source, claim_context, experiment_context, or view_page. Keep supported concerns, narrow overstatements, and remove premises the paper answers. You may add a better concern supported by the paper. Prior working reviews:\n'+json.dumps([single1,single2],ensure_ascii=False)+'\nYOUR SOURCE CHECK RECEIPTS:\n'+json.dumps(single_receipts,ensure_ascii=False)+shared,REVIEW,list(single_images.values()),2,'debate-v2')
    single=save('single-final',single)
    plan_raw=call('pra-plan',planner_prompt(paper,ctx,compact_summary(read(ROOT/'diagnostics.json')))+'\nThe same three main figure pages are attached. You may inspect other pages from the packet. Tables are previews in this context, retrieve complete table blocks when decisive. Use literal search only, without Boolean expressions.',PLAN,images)
    plan,changes=normalize_plan(paper,plan_raw)
    frozen(ROOT/'planning/plan.json',plan)
    frozen(ROOT/'planning/normalization.json',changes)
    prepared=prepare_evidence(WORK,plan,ROOT/'evidence',operation_limit=4)
    frozen(ROOT/'planning/prepared.json',prepared)
    evidence_images={i['sha256']:i for i in images+prepared['images']}
    evidence_prompt=rules.replace('Give at most five distinct, consequential findings','Produce up to eight candidate findings').replace('At most five selected findings','Up to eight candidate findings, at most five selected findings')+'\nInvestigate the supplied tasks from the delivered evidence. Return task_results with valid task IDs, receipt IDs, exact source quotations, observations, author defenses, and remaining uncertainty. Completed means required evidence was delivered and the stated observation follows. Delivered evidence is not itself proof of a concern. No extra tools in this interpretation stage. Select the strongest at most five using selected_finding_numbers. Each comment should address one scientific issue, under 140 words.\nPLAN:\n'+json.dumps(plan,ensure_ascii=False)+'\nDELIVERED EVIDENCE:\n'+json.dumps(delivered_context(prepared),ensure_ascii=False)+shared
    evidence=call('pra-evidence',evidence_prompt,EVIDENCE_REVIEW,list(evidence_images.values()))
    validation=validate_task_results(paper,evidence,prepared)
    frozen(ROOT/'task-audit.json',validation)
    candidates,selected=selected_review(paper,WORK,validated_response(evidence,validation),'before-debate')
    frozen(ROOT/'responses/candidates.json',candidates)
    frozen(ROOT/'responses/before-debate.json',selected)
    ledger=issue_ledger(candidates)
    frozen(ROOT/'planning/ledger.json',ledger)
    debate=call('pra-debate',revision_prompt(paper,ctx,ledger)+'\nSame source previews and access limitations apply. No copyedits.\nDELIVERED EVIDENCE:\n'+json.dumps(delivered_context(prepared),ensure_ascii=False)+advisory,DEBATE_REVISION,list(evidence_images.values()),2,'debate-v2')
    structural=validate_revision(debate,ledger,paper)
    frozen(ROOT/'debate-audit.json',structural)
    final=save('after-debate',revision_package(debate,ledger,structural))
    frozen(ROOT/'generation-lock.json',{p.name:digest(p.read_bytes()) for p in (ROOT/'raw').glob('*.json')})
    registry=dict(evidence_images)
    for label in ('single-investigate','single-final','pra-debate'):
        for path,label_text in complete_inspected_images(paper,WORK,ROOT/'investigations'/label):
            registry[digest(path.read_bytes())]={'path':str(path),'label':label_text,'sha256':digest(path.read_bytes())}
    shared_images=[{'id':f'image-{n}',**row} for n,row in enumerate(sorted(registry.values(),key=lambda r:(r['label'],r['sha256'])),1)]
    if len(shared_images)>10:raise ValueError('Shared evaluation images exceed frozen cap')
    conditions={'single':single,'before_debate':selected,'after_debate':final}
    order=list(conditions)
    random.Random(20260925).shuffle(order)
    mapping=dict(zip(('A','B','C'),order))
    anonymous={label:[{'finding_id':f'{label}{n}',**{k:f.get(k) for k in ('title','block_id','quote','kind','severity','comment','replacement','evidence_blocks','counterevidence')}} for n,f in enumerate(conditions[c]['findings'],1)] for label,c in mapping.items()}
    frozen(ROOT/'evaluation/labels.json',mapping)
    frozen(ROOT/'evaluation/anonymous.json',anonymous)
    frozen(ROOT/'evaluation/images.json',shared_images)
    prompt=INSTRUCTIONS+'\nREVIEWS:\n'+json.dumps(anonymous,ensure_ascii=False)+'\nSHARED IMAGES:\n'+json.dumps([{k:i[k] for k in ('id','label','sha256')} for i in shared_images])+'\nTITLE:\n'+paper['title']+'\nCOMPLETE IMPORTED MANUSCRIPT INCLUDING REPORTED TABLES:\n'+(WORK/'manuscript.md').read_text()
    grade=call('evaluation',prompt,EVALUATION,shared_images)
    checked=audit(grade,anonymous,paper,shared_images)
    frozen(ROOT/'evaluation/audit.json',checked)
    valid=set(checked['valid_rating_ids'])
    metrics=[]
    for row in grade['conditions']:
        ratings=[r for r in row['ratings'] if r['finding_id'] in valid]
        metrics.append({'condition':mapping[row['label']],'total':len(row['ratings']),'unscored':len(row['ratings'])-len(ratings),
          'assessments':{s:sum(r['assessment']==s for r in ratings) for s in ('justified_concern','justified_clarification','unsupported_allegation','unverifiable')},
          'excessive_requests':sum(r['resolution_proportionality']=='excessive' for r in ratings)})
    usage=jsonl(ROOT/'execution/usage.jsonl')
    write(ROOT/'results.json',{'metrics':metrics,'preferred':mapping.get(grade['preferred_label'],grade['preferred_label']),
      'preference_reason':grade['preference_reason'],'calls':len(usage),'observed_tokens':sum(r['observed_tokens'] for r in usage),
      'limitations':PROTOCOL['limitations'],'source_audit':'Pending, automated ratings are not scientific ground truth'})
    write(ROOT/'progress.json',{'status':'generation_and_automated_evaluation_complete','source_audit':'pending'})
    print(json.dumps(read(ROOT/'results.json'),indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    if args.prepare_only:initialize()
    else:run()
