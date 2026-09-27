"""One development reviewer call measuring targeted tool uptake."""
import shutil
from pathlib import Path
from paper_workspace.reviewer import review
from paper_workspace.storage import read, write
from paper_workspace.run_state import tracked_stage

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO/'runs/pra-tool-uptake-v1'
BASE = REPO/'runs/pra-ensemble-clarification-v1/inputs/fresh'


def main():
    out = ROOT/'review'
    if out.exists():
        raise ValueError('The single authorized attempt already exists. No automatic retry.')
    shutil.copytree(REPO/'paper_workspace', ROOT/'frozen-source/paper_workspace',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    write(ROOT/'scope.json', {'version': 'tool-uptake-v1', 'max_new_calls': 1,
        'model': 'gpt-5.6-terra', 'effort': 'medium', 'automatic_retries': False,
        'source': str(BASE), 'scope': 'Known development paper. No prior reviews or judge outputs supplied. Tests tool exposure and uptake, not comparative review quality.'})
    with tracked_stage(ROOT/'worker-state.json', 'targeted-review', timeout=1000):
        review(BASE/'workspace', out, ROOT/'billing_confirmation.json', '2026-09-25',
               mode='independent', scaffold_root='/home/ty/Repos/paper-scaffold',
               model='gpt-5.6-terra', shared_images=[i['path'] for i in read(BASE/'images.json')])
    print(read(out/'tool-policy-audit.json'))


if __name__ == '__main__':
    main()
