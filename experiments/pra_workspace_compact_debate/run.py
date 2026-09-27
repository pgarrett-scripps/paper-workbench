"""Final compact debate within the original five-attempt allowance."""
import json,sys,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO))
from paper_workspace.annotations import verify_workspace,save_review
from paper_workspace.storage import read,write,digest
from paper_workspace.model_runtime import model_call,require_subscription,source_manifest,jsonl
from paper_workspace.review_schema import REVIEW
from paper_workspace.reviewer import debate_prompt
ROOT=REPO/'runs/pra-workspace-pilot-v1-r3'
BASE=REPO/'runs/pra-workspace-pilot-v1'
PAPER=BASE/'paper-v2'
ROOT.mkdir(exist_ok=True)
protocol={'provider':'codex','model':'gpt-5.6-sol','effort':'medium','live_retrieval':True,'held_out_runs_authorized':False,'max_calls_per_condition':5,'observed_token_stop':500000,'call_timeout_seconds':600,'stage':'compact_debate','tool_limit':2,'interpretation':'Engineering continuation with changed debate context. No matched efficacy comparison.'}
paper=verify_workspace(PAPER)
reviews=[read(BASE/'responses/plain.json'),read(REPO/'runs/pra-workspace-pilot-v1-r2/responses/workspace.json')]
prompt=debate_prompt(paper,reviews)
manifest={'code':source_manifest(REPO/'paper_workspace'),'runner':source_manifest(HERE),'source_sha256':digest((PAPER/'manifest.json').read_bytes()),'prompt_sha256':digest(prompt),'protocol':protocol}
if (ROOT/'manifest.json').exists() and read(ROOT/'manifest.json')!=manifest:raise ValueError('Frozen continuation changed')
write(ROOT/'manifest.json',manifest)
write(ROOT/'protocol.json',protocol)
shutil.copy2(BASE/'billing_confirmation.json',ROOT/'billing_confirmation.json')
require_subscription(ROOT)
ledger=ROOT/'execution/usage.jsonl'
if not ledger.exists():
    inherited=[]
    for directory in [BASE,REPO/'runs/pra-workspace-pilot-v1-r1',REPO/'runs/pra-workspace-pilot-v1-r2']:
        inherited.extend({**r,'inherited_from':str(directory)} for r in jsonl(directory/'execution/usage.jsonl'))
    inherited.append({'label':'workspace_interrupted','ok':False,'usage_unknown':True,'inherited_from':str(BASE),'launcher_exit_code':143})
    ledger.parent.mkdir(parents=True,exist_ok=True)
    ledger.write_text(''.join(json.dumps(r)+'\n' for r in inherited))
write(ROOT/'execution/workspace/tool-config.json',{'paper':str(PAPER),'output':str(ROOT/'investigation'),'cache':str(ROOT/'literature-cache'),'tool_limit':2,'literature_cutoff':'2026-01-05'})
write(ROOT/'progress.json',{'status':'running','stage':'compact_debate'})
try:
    result=model_call(protocol,ROOT/'execution',prompt,REVIEW,tools=True,label='compact_debate')
    write(ROOT/'response.json',result)
    save_review(PAPER,result,'workspace_challenged')
    rows=jsonl(ledger)
    final={'status':'complete','total_attempts':len(rows),'completed_valid_reviews':3,'observed_tokens':sum(r.get('observed_tokens',0) for r in rows),'unknown_usage_attempts':sum(bool(r.get('usage_unknown')) for r in rows),'grading':'Unblinded implementing-agent source spot-checks only, no automated judge calls'}
    write(ROOT/'progress.json',final)
    print(json.dumps(final,indent=2))
except Exception as exc:
    write(ROOT/'progress.json',{'status':'blocked','error':str(exc)})
    raise
