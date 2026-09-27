"""Two-pass self-revision versus saved investigator and debate on one paper."""
import copy
import json
import shutil
import sys
import time
from pathlib import Path
from experiments.pra_reliability_retest import run as assessment
from paper_workspace.annotations import save_review, verify_workspace
from paper_workspace.evidence_handles import build_registry, hydrate_review_response
from paper_workspace.external_evidence import SourceClient, bind_sources, validate_references
from paper_workspace.model_runtime import jsonl, model_call, require_subscription
from paper_workspace.storage import read, write, digest

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / 'runs/pra-compute-match-v1'
PREVIOUS = REPO / 'runs/pra-reliability-retest-v4-terra'
BASE = assessment.BASE
PROTOCOL = {**assessment.PROTOCOL, 'model': 'gpt-5.6-terra',
    'version': 'compute-match-v1', 'max_total_model_calls': 2,
    'observed_token_launch_stop': 220000,
    'study_type': 'Retrospective repeat-paper, matched model passes with observed token accounting',
    'prior_run': str(PREVIOUS), 'self_revision_tool_limit': 2,
    'condition_total_tool_ceiling': 6,
    'limitations': ['Original review and PRA outcome were known before this comparison was planned.',
        'Two passes per review condition, not an exact token or FLOP match.',
        'Original single pass allowed six tool calls and PRA investigation allowed four. Both used zero.',
        'A fresh self-revision context receives its own prior review and the original source prompt.']}
REVISION = '''SECOND PASS: Reconsider and improve your own draft review against the entire supplied manuscript and figures. Check the scientific validity, specificity and proportionality of each concern. Resolve misunderstandings or unsupported premises. Look for important omissions as well as mistakes in the draft. Keep useful concerns, refine or remove weak ones, and add a new issue only when the available evidence supports it. Return your best final scientific review, with at most five distinct findings under the same overall word budget. This is ordinary self-revision. Do not simulate multiple reviewers or a debate. No other review or assessment is supplied. Reselect source handles from the manuscript or tool results for the final output. A previous review is a fallible draft, not source evidence. You have at most two tool calls in this pass. No prior human peer review may be consulted.'''


def verify():
    for name, sha in read(ROOT / 'seal.json')['files'].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError('Frozen input changed: ' + name)


def budget(required):
    verify()
    rows = [r for p in ROOT.rglob('usage.jsonl') for r in jsonl(p)]
    attempts = list(ROOT.rglob('*.started.json'))
    if len(rows) != len(attempts) or any(r.get('usage_unknown') for r in rows):
        raise ValueError('Unresolved model usage')
    if len(attempts) + required > 2 or sum(r['observed_tokens'] for r in rows) >= 220000:
        raise ValueError('Two-call comparison budget exhausted')
    if not 0 <= time.time() - read(ROOT / 'billing_confirmation.json')['checked_at'] < 86400:
        raise ValueError('Billing check expired')
    require_subscription(ROOT)


def prepare():
    if (ROOT / 'seal.json').exists():
        raise ValueError('Comparison already prepared')
    for name, sha in read(PREVIOUS / 'seal.json')['files'].items():
        if digest(Path(name).read_bytes()) != sha:
            raise ValueError('Original generation seal changed: ' + name)
    write(ROOT / 'protocol.json', PROTOCOL)
    # The frozen first pass made no tool calls, so the shared allowance is intact.
    first_calls = list((PREVIOUS / 'single/execution/calls').glob('*.request.json'))
    if len(first_calls) != 1:
        raise ValueError('Expected one saved single-review request')
    request = read(first_calls[0])
    for condition in ('single', 'pra'):
        if read(PREVIOUS / condition / 'progress.json')['status'] != 'complete':
            raise ValueError('Original condition did not complete')
        for event_file in (PREVIOUS / condition / 'execution/calls').glob('*.events.jsonl'):
            if any(r.get('item', {}).get('type') == 'mcp_tool_call' for r in jsonl(event_file)):
                raise ValueError('Saved tool usage requires explicit shared-budget reconstruction')
    draft = read(PREVIOUS / 'single/responses/plain-guarded.json')
    fields = ('title', 'block_id', 'quote', 'kind', 'severity', 'comment', 'replacement',
              'counterevidence', 'evidence_blocks', 'source_evidence', 'source_urls')
    own_draft = {'summary': draft['summary'], 'findings': [
        {k: f[k] for k in fields if k in f} for f in draft['findings']],
        'limitations': draft['limitations']}
    prompt = request['prompt'].replace('At most 6 tool calls.', 'At most 2 tool calls.')
    prompt += '\n' + REVISION + '\nYOUR PRIOR DRAFT:\n' + json.dumps(own_draft, ensure_ascii=False)
    write(ROOT / 'revision-inputs.json', {'prompt': prompt, 'schema': request['schema'],
        'prompt_sha256': digest(prompt), 'previous_request_sha256': digest(first_calls[0].read_bytes())})
    for rel in ('pra/editor-package.json', 'pra/progress.json'):
        dest = ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PREVIOUS / rel, dest)
    write(ROOT / 'reused-receipts.json', {c: jsonl(PREVIOUS / c / 'execution/usage.jsonl')
                                         for c in ('single', 'pra')})
    config = read(PREVIOUS / 'single/execution/workspace/tool-config.json')
    config.update(output=str(ROOT / 'single/investigations/plain'),
                  cache=str(ROOT / 'single/source-cache'),
                  source_state=str(ROOT / 'single/sources'), tool_limit=2)
    write(ROOT / 'single/execution/workspace/tool-config.json', config)
    write(ROOT / 'single/protocol.json', PROTOCOL)
    shutil.copy2(ROOT / 'billing_confirmation.json', ROOT / 'single/billing_confirmation.json')
    files = [ROOT / 'protocol.json', ROOT / 'revision-inputs.json', ROOT / 'reused-receipts.json',
             ROOT / 'pra/editor-package.json', ROOT / 'pra/progress.json',
             ROOT / 'single/execution/workspace/tool-config.json', Path(__file__).resolve(),
             REPO / 'experiments/pra_reliability_retest/run.py',
             REPO / 'experiments/pra_debate_revision/evaluation.py',
             REPO / 'experiments/pra_evidence_workflow/evaluation.py',
             REPO / 'experiments/pra_prospective/core.py']
    files += [Path(name) for name in read(PREVIOUS / 'seal.json')['files']]
    files += [PREVIOUS / c / 'execution/usage.jsonl' for c in ('single', 'pra')]
    files += [first_calls[0], PREVIOUS / 'single/responses/plain-guarded.json']
    write(ROOT / 'seal.json', {'recorded_at': time.time(),
        'files': {str(p): digest(p.read_bytes()) for p in sorted(set(files))}})
    for path in files:
        if path.is_relative_to(REPO) and not path.is_relative_to(REPO / 'runs'):
            dest = ROOT / 'frozen-source' / path.relative_to(REPO)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
    print('Matched-pass comparison sealed', flush=True)


def revise():
    budget(1)
    out = ROOT / 'single'
    if (out / 'progress.json').exists():
        raise ValueError('Self-revision already attempted')
    inputs = read(ROOT / 'revision-inputs.json')
    paper = verify_workspace(BASE / 'workspace')
    config = read(out / 'execution/workspace/tool-config.json')
    sources = SourceClient(out / 'sources', out / 'source-cache', 6, 'current', '2026-09-25',
                           frozen_cache=assessment.PACKET, frozen_hashes=config['source_packet_manifest'])
    write(out / 'progress.json', {'status': 'running', 'stage': 'self-revision'})
    try:
        raw = model_call(PROTOCOL, out / 'execution', inputs['prompt'], inputs['schema'],
            tools=True, label='self-revision', images=[Path(i['path']) for i in read(BASE / 'images.json')])
        write(out / 'responses/self-revision-model.json', raw)
        hydrated = hydrate_review_response(raw, build_registry(paper, sources.cards()))
        value = {**hydrated['response'], 'evidence_handle_audit': hydrated['audit']}
        value = {**bind_sources(value, sources.cards()),
                 'source_validation': validate_references(value, sources.cards())}
        normalized = save_review(BASE / 'workspace', value, 'compute-match-self-revision-v1')
        if any(f['placement'] != 'anchored' or f['invalid_evidence_blocks'] for f in normalized['findings']):
            raise ValueError('Self-revision contains invalid manuscript evidence')
        write(out / 'responses/plain-guarded.json', {**value, 'findings': normalized['findings']})
        write(out / 'progress.json', {'status': 'complete', 'new_calls': 1, 'reused_calls': 1})
        verify()
        print('Self-revision complete', flush=True)
    except Exception as exc:
        write(out / 'progress.json', {'status': 'blocked', 'error': str(exc)})
        raise


def evaluate():
    assessment.ROOT = ROOT
    assessment.PROTOCOL = PROTOCOL
    assessment.budget = budget
    assessment.verify = verify
    assessment.evaluate()
    result = read(ROOT / 'evaluation/results.json')
    reused = read(ROOT / 'reused-receipts.json')
    new_rows = [r for p in ROOT.rglob('usage.jsonl') for r in jsonl(p)]
    revision = sum(r['observed_tokens'] for r in new_rows if r['label'] == 'self-revision')
    self_tokens = sum(r['observed_tokens'] for r in reused['single']) + revision
    pra_tokens = sum(r['observed_tokens'] for r in reused['pra'])
    result.update(condition_names={'single': 'two-pass self-revision', 'pra': 'investigator plus debate'},
        condition_generation_tokens={'two-pass self-revision': self_tokens, 'pra': pra_tokens},
        token_ratio_self_revision_to_pra=self_tokens / pra_tokens,
        new_observed_tokens=sum(r['observed_tokens'] for r in new_rows),
        limitations=PROTOCOL['limitations'] + ['One fresh-context same-family model judge, not expert validation.',
            'Generation outputs were reused to minimize costs. Do not count this as another independent paper.'])
    write(ROOT / 'summary.json', result)
    write(ROOT / 'evaluation/results.json', result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'prepare':
        prepare()
    elif action == 'revise':
        revise()
    elif action == 'judge':
        evaluate()
    else:
        raise ValueError('Unknown action')
