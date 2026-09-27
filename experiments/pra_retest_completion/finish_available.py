"""Finish unattempted scoring calls without retrying failed inference."""

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'pra_findings_debate_recovery'))
import core
import study
import prompts as prompt
import schemas as schema


def main():
    root = core.ROOT
    protocol, _ = core.verify(root)
    core.shared.require_subscription(root)
    provenance = core.read(root/'completion_provenance.json')
    if core.shared.source_manifest(HERE) != provenance['completion_runner_files']:
        raise core.Blocked('Completion runner changed after freezing')
    skipped = []
    for entry in core.read(root/'evaluation/condition_key.json'):
        pid, condition = entry['paper_id'], entry['condition']
        candidates = study.normalize(root, protocol, pid, condition)
        refs = core.read(root/'inputs'/pid/'reference.json')['concerns']
        manuscript = (root/'inputs'/pid/'manuscript.txt').read_text()
        for judge in ['A', 'B']:
            out = root/'evaluation'/pid/entry['anonymous_id']/judge
            if (out/'judgment.json').exists():
                continue
            failures = [u for u in core.shared.jsonl(out/'usage.jsonl') if not u.get('ok')]
            if failures:
                skipped.append({**entry, 'judge': judge, 'reason': failures[-1].get('error'),
                                'request_sha256': failures[-1]['request_sha256']})
                continue
            core.write(root/'status.json', {'stage': 'scoring_remaining', 'paper_id': pid,
                                           'anonymous_id': entry['anonymous_id'], 'judge': judge,
                                           'skipped_failed_calls': skipped})
            ordered_refs = refs if judge == 'A' else list(reversed(refs))
            ordered_candidates = candidates if judge == 'A' else list(reversed(candidates))
            extra = '\nActively consider an alternative interpretation before each judgment.\n' if judge == 'B' else ''
            text = prompt.SAFETY + prompt.JUDGE + extra + '\nNUMBERED MANUSCRIPT\n' + core.numbered(manuscript)
            text += '\nREFERENCE CONCERNS\n' + json.dumps(ordered_refs) + '\nANONYMOUS CANDIDATES\n' + json.dumps(ordered_candidates)
            value = core.call(root, protocol, out, text, schema.JUDGE, f'judge_{judge}')
            study.validate_judgment(value, refs, candidates, manuscript)
            core.write(out/'judgment.json', value)
            print(json.dumps({'paper_id': pid, 'anonymous_id': entry['anonymous_id'], 'judge': judge}), flush=True)
    study.audit(root)
    core.write(root/'completion_manifest.json', {'stage': 'available_scoring_complete',
              'skipped_failed_calls': skipped, 'scientific_results': False,
              'judgments_available': len(list((root/'evaluation').rglob('judgment.json'))),
              'judgments_expected': 18, 'human_audit': 'pending'})
    core.write(root/'status.json', core.read(root/'completion_manifest.json'))
    print('Available scoring complete. Missing judgments remain missing.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        core.write(core.ROOT/'status.json', {'stage': 'blocked', 'reason': str(exc), 'updated_at': time.time()})
        raise
