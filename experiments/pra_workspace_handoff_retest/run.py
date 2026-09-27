"""One development debate over saved reviews with verified image handoff."""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from paper_workspace.annotations import export_draft, save_review, verify_workspace
from paper_workspace.model_runtime import jsonl, model_call, require_subscription, source_manifest
from paper_workspace.review_schema import DEBATE
from paper_workspace.reviewer import debate_prompt, editor_package, inspected_images
from paper_workspace.storage import digest, read, write

ROOT = REPO / 'runs/pra-workspace-handoff-retest-v1'
BASE = REPO / 'runs/pra-workspace-pilot-v1'
PAPER = BASE / 'paper-v2'


def run(execute=False):
    ROOT.mkdir(parents=True, exist_ok=True)
    paper = verify_workspace(PAPER)
    inputs = [BASE / 'responses/plain.json',
              REPO / 'runs/pra-workspace-pilot-v1-r2/responses/workspace.json']
    reviews = [read(path) for path in inputs]
    images = inspected_images(paper, PAPER,
                              REPO / 'runs/pra-workspace-pilot-v1-r2/investigations/workspace')
    if len(images) != 2:
        raise ValueError('The two previously inspected source images must be verified')
    prompt = debate_prompt(paper, reviews)
    prompt += '\nATTACHED SOURCE IMAGES:\n' + '\n'.join(
        f'{i + 1}: {label}' for i, (path, label) in enumerate(images))
    protocol = {
        'provider': 'codex', 'model': 'gpt-5.6-sol', 'effort': 'medium',
        'live_retrieval': True, 'held_out_runs_authorized': False,
        'max_calls_per_condition': 1, 'observed_token_stop': 100000,
        'call_timeout_seconds': 600, 'tool_limit': 2,
        'literature_cutoff': '2026-01-05', 'stage': 'image_handoff_regression',
        'interpretation': 'Known development case, not an efficacy comparison. Images and debate instructions both changed.',
    }
    criteria = {
        'frozen_before_inference': True,
        'input_findings': sum(len(r['findings']) for r in reviews),
        'checks': [
            'Every source finding has exactly one valid disposition or remains explicitly unendorsed in the queue.',
            'The image concern receives an evidence-based disposition, never rejection solely because image labels are absent from extracted text.',
            'Every final or queued finding has a valid source anchor, with unresolved anchors reported.',
            'All original findings and dispositions survive editor export without changing source text.',
        ],
        'scientific_assessment': 'Unblinded source checks by implementing agent. No superiority score or independent expert validation.',
        'spending': 'One new Sol medium call. No retries or additional initial reviews. The token stop is checked before calls, not a hard within-call cap.',
    }
    manifest = {
        'code': source_manifest(REPO / 'paper_workspace'),
        'runner': source_manifest(HERE),
        'source_manifest_sha256': digest((PAPER / 'manifest.json').read_bytes()),
        'inputs': {str(p.relative_to(REPO)): digest(p.read_bytes()) for p in inputs},
        'images': [{'path': str(p), 'label': label, 'sha256': digest(p.read_bytes())} for p, label in images],
        'prompt_sha256': digest(prompt), 'protocol': protocol, 'criteria': criteria,
    }
    if (ROOT / 'manifest.json').exists() and read(ROOT / 'manifest.json') != manifest:
        raise ValueError('Frozen retest inputs changed. Inspect before using a new run directory.')
    write(ROOT / 'manifest.json', manifest)
    write(ROOT / 'protocol.json', protocol)
    write(ROOT / 'criteria.json', criteria)
    (ROOT / 'prompt.txt').write_text(prompt)
    for source, name in [(REPO / 'paper_workspace', 'paper_workspace'), (HERE, 'runner')]:
        destination = ROOT / 'frozen-source' / name
        if not destination.exists():
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    write(ROOT / 'execution/workspace/tool-config.json', {
        'paper': str(PAPER), 'output': str(ROOT / 'investigation'),
        'cache': str(ROOT / 'literature-cache'), 'tool_limit': 2,
        'literature_cutoff': protocol['literature_cutoff'],
    })
    if not execute:
        print(json.dumps({'status': 'prepared', 'images': len(images), 'input_findings': criteria['input_findings']}))
        return
    billing = read(ROOT / 'billing_confirmation.json')
    if not billing.get('no_paid_credits_verified') or not 0 <= time.time() - billing.get('checked_at', 0) < 86400:
        raise ValueError('A fresh zero-paid-credit account verification is required')
    require_subscription(ROOT)
    write(ROOT / 'progress.json', {'status': 'running', 'stage': protocol['stage']})
    try:
        result = model_call(protocol, ROOT / 'execution', prompt, DEBATE,
                            tools=True, label=protocol['stage'], images=[p for p, label in images])
        write(ROOT / 'response.json', result)
        package = editor_package(result, reviews)
        write(ROOT / 'editor-package.json', package)
        normalized = save_review(PAPER, package, 'panel-handoff-retest-v1')
        exported = export_draft(paper, normalized, {
            'paper_id': paper['id'], 'review_id': normalized['id'], 'items': {},
        })
        write(ROOT / 'review-package.json', exported)
        rows = jsonl(ROOT / 'execution/usage.jsonl')
        progress = {
            'status': 'complete', 'new_calls': len(rows),
            'observed_tokens': sum(r.get('observed_tokens', 0) for r in rows),
            'unknown_usage_attempts': sum(bool(r.get('usage_unknown')) for r in rows),
            'annotation_counts': normalized['annotation_counts'],
            'editor_findings': package['editor_findings_count'],
            'verification_queue': package['verification_queue_count'],
            'input_findings_preserved': len(exported['source_findings']),
            'dispositions_exported': len(exported['source_dispositions']),
        }
        write(ROOT / 'progress.json', progress)
        print(json.dumps(progress, indent=2))
    except Exception as exc:
        write(ROOT / 'progress.json', {'status': 'blocked', 'error': str(exc)})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    run(parser.parse_args().execute)
