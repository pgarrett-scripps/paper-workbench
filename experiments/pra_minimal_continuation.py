"""Finish only the already-started pair under the user's reduced spending scope."""

import fcntl
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent / 'pra_known_errors_r1'))
import core
import study
import workflow


def main():
    protocol = core.verify()
    control = core.read(core.ROOT / 'minimal_pilot_control.json')
    if core.runtime.digest(HERE.read_bytes()) != control['runner_sha256']:
        raise core.Blocked('Restricted continuation changed after freezing')
    ids = core.read(core.ROOT / 'manifest.json')['input_ids'][:2]
    if ids != control['input_ids']:
        raise core.Blocked('Restricted input IDs changed')
    with (core.ROOT / 'runner.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        core.runtime.require_subscription(core.ROOT)
        stop = core.ROOT / 'STOP'
        if stop.exists():
            if not stop.read_text().startswith('User requests minimum trials only.'):
                raise core.Blocked('Another stop instruction is active')
            stop.rename(core.ROOT / 'user_scope_stop.txt')
        original_call = core.call

        def bounded_call(protocol, node, text, schema, source=None, arm=None, pdf=None):
            identity = core.runtime.digest({'prompt': text, 'schema': schema, 'tools': source is not None, 'protocol': protocol})
            cached = any((node / f'attempt_{attempt}' / 'calls' / f'{identity}.json').exists()
                         and core.read(node / f'attempt_{attempt}' / 'calls' / f'{identity}.json').get('ok') for attempt in (1, 2))
            if not cached:
                used = core.usage()
                limit = control['max_total_observed_tokens']
                if not node.name.startswith('judge_'):
                    limit -= control['evaluation_reserve']
                if sum(row.get('observed_tokens', 0) for row in used) >= limit or len(used) >= control['max_total_calls']:
                    raise core.Blocked('Reduced pilot spending stop reached')
            return original_call(protocol, node, text, schema, source, arm, pdf)

        core.call = bounded_call
        for iid in ids:
            try:
                workflow.generate(protocol, iid)
                print('Generation complete: ' + iid, flush=True)
            except Exception as exc:
                core.write(core.ROOT / 'minimal_pilot_failure.json', {'input_id': iid, 'stage': 'generation', 'reason': str(exc)})
                break
        labels = core.read(core.ROOT / 'evaluation/labels.json')
        for iid in ids:
            if not all((core.ROOT / 'work' / iid / arm / 'generation.json').exists() for arm in ['investigation_team', 'sequential_single']):
                continue
            try:
                study.evaluate(protocol, iid, labels[iid])
                print('Scoring complete: ' + iid, flush=True)
            except Exception as exc:
                core.write(core.ROOT / 'minimal_pilot_scoring_failure.json', {'input_id': iid, 'reason': str(exc)})
                break
        report = study.summarize(protocol)
        complete = all(iid not in report['missing'] for iid in ids)
        result = {'scope': 'One previously started original and altered pair only',
                  'complete': complete, 'comparison': report['comparison'],
                  'usage': report['usage'], 'scientific_superiority_established': False,
                  'original_two_pair_screen': 'Not completed. Second pair not authorized under reduced scope.',
                  'larger_trial_requires_user_authorization': True,
                  'further_inference_requires_user_authorization': True}
        core.write(core.ROOT / 'minimal_pilot_report.json', result)
        core.write(core.ROOT / 'status.json', {'stage': 'minimal_pilot_finished' if complete else 'minimal_pilot_stopped',
                   'requires_user_authorization_for_further_inference': True})
        stop.write_text('Minimal pilot finished or stopped. Further model inference requires explicit user authorization.\n')
        print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
