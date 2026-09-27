"""Finish the approved six calls after documenting the observed-token amendment."""
import importlib.util
import sys
import time
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
from paper_workspace import model_runtime
from paper_workspace.storage import read,write,digest

spec=importlib.util.spec_from_file_location('frozen_pilot',REPO/'experiments/pra_workspace_two_paper/run.py')
pilot=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def run():
    papers,original_protocol=pilot.prepared()
    root=pilot.ROOT
    rows=model_runtime.jsonl(root/'execution/usage.jsonl')
    if any(row.get('usage_unknown') or not row.get('ok') for row in rows):
        raise ValueError('A failed or unknown-usage inference cannot be resumed automatically')
    if model_runtime.unresolved_attempts(root/'execution'):
        raise ValueError('Wait for the current invocation to finish before continuation')
    amended={**original_protocol,'observed_token_stop':700000}
    amendment={
        'original_manifest_sha256':digest((root/'manifest.json').read_bytes()),
        'original_observed_token_stop':400000,'amended_observed_token_stop':700000,
        'max_model_calls_unchanged':6,
        'reason':'The first investigator used 304679 observed tokens, including 237184 cached input tokens. The account remained at 4 percent usage after starting at 3 percent. Complete the already authorized two-paper comparison without adding conditions, retries, or duplicate inference.',
        'scientific_inputs_changed':False,'protocol_for_remaining_uncached_calls':amended,
        'code_sha256':digest(Path(__file__).read_bytes()),
    }
    path=root/'budget-amendment.json'
    if path.exists() and read(path)!=amendment:raise ValueError('Continuation amendment changed')
    write(path,amendment)
    original_call=model_runtime.model_call

    def cached_or_remaining(protocol,out,prompt,schema,*,tools=False,label='call',images=None):
        paths=[Path(p).resolve() for p in (images or [])]
        identity=model_runtime.request_identity(original_protocol,prompt,schema,tools,paths,Path(out)/'workspace')
        original_receipt=Path(out)/'calls'/f'{identity}.json'
        selected=original_protocol if original_receipt.exists() else amended
        return original_call(selected,out,prompt,schema,tools=tools,label=label,images=paths)

    pilot.model_call=cached_or_remaining
    try:
        pilot.execute(papers,original_protocol)
        results=read(root/'results.json')
        results['operational_amendment']='budget-amendment.json'
        write(root/'results.json',results)
    except Exception as exc:
        write(root/'progress.json',{'status':'blocked','error':str(exc)})
        raise


if __name__=='__main__':run()
