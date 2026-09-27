"""Resume the bounded retest after a documented local initialization failure."""
import sys
from pathlib import Path
from . import run
from paper_workspace.storage import read, write, digest

run.ROOT = run.REPO / 'runs/pra-reliability-retest-v3'
run.PROTOCOL = {**run.PROTOCOL, 'version': 'reliability-retest-v3',
                'pre_dispatch_failure': str(run.REPO / 'runs/pra-reliability-retest-v2'),
                'transport_amendment': 'Permit CLI state initialization outside the outer filesystem sandbox. The inner review process remains read-only with only bounded manuscript tools.'}

if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'seal':
        run.seal()
        seal = read(run.ROOT / 'seal.json')
        seal['files'][str(Path(__file__).resolve())] = digest(Path(__file__).read_bytes())
        write(run.ROOT / 'seal.json', seal)
        dest = run.ROOT / 'frozen-source/experiments/pra_reliability_retest/launch.py'
        dest.write_bytes(Path(__file__).read_bytes())
    elif action == 'judge':
        run.evaluate()
    elif action in ('single', 'pra'):
        run.generate(action)
    else:
        raise ValueError('Unknown action')
