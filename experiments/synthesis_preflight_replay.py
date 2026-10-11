"""Replay saved synthesis responses offline without changing study outcomes."""
import argparse
from collections import Counter
from pathlib import Path

from paper_workspace.annotations import verify_workspace
from paper_workspace.storage import digest, read, write
from paper_workspace.synthesis_validation import validate_draft


def replay(study, output):
    study, output = Path(study).resolve(), Path(output).resolve()
    if output.is_relative_to(study) or output.exists():
        raise ValueError('Use a fresh output outside the original study')
    rows = []
    for attempt in sorted((study/'attempts').glob('*/review-c')):
        debate = attempt/'core-run/debate'
        raw = debate/'responses/debate-model.json'
        if not raw.exists():
            continue
        inputs = [raw, debate/'debate-ledger.json', attempt/'receipt.json', attempt/'manuscript-workspace/paper.json']
        cards_path = debate/'sources/cards.json'
        if cards_path.exists():
            inputs.append(cards_path)
        hashes = {str(path.relative_to(study)): digest(path.read_bytes()) for path in inputs}
        paper = verify_workspace(attempt/'manuscript-workspace')
        result = validate_draft(read(raw), read(debate/'debate-ledger.json'), paper,
                                read(cards_path) if cards_path.exists() else None)
        assert all(digest((study/path).read_bytes()) == sha for path, sha in hashes.items())
        original = read(attempt/'receipt.json')['status']
        rows.append({'paper': attempt.parent.name, 'original_delivery': original,
                     'preflight_valid': result['valid'], 'error': result.get('error'),
                     'problem_counts': dict(Counter(p['code'] for p in result['problems'])),
                     'problems': result['problems'], 'input_sha256': hashes})
    result = {'kind': 'offline_synthesis_preflight_replay', 'new_model_calls': 0,
              'original_results_changed': False, 'responses': len(rows),
              'outcomes': dict(Counter(f"{row['original_delivery']} -> {'valid' if row['preflight_valid'] else 'invalid'}" for row in rows)),
              'papers': rows,
              'limitation': 'This tests validation and diagnostics on saved outputs. It does not measure whether models use feedback successfully in fresh reviews.'}
    write(output, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = replay(args.study, args.output)
    print({key: result[key] for key in ('responses', 'outcomes', 'new_model_calls')})
