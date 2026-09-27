"""One development test of a focused original-table investigation."""
import shutil
from pathlib import Path
from paper_workspace.focused_investigation import investigate
from paper_workspace.run_state import tracked_stage
from paper_workspace.storage import write

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/'runs/pra-focused-investigation-v1'
BASE=REPO/'runs/pra-ensemble-clarification-v1/inputs/fresh/workspace'
QUESTION=('What evidence supports the claim that treatment effects on juvenile dispersal are independent of parental departure? '
          'Inspect the relevant original supplement model table and its definitions, not only the caption. '
          'Identify the strongest author defense and any remaining distinction between an adjusted association and a direct causal effect. '
          'Report what the table actually establishes, and keep anything not established as uncertainty.')
BLOCKS=['b0024','b0035','b0036','b0038','b0043','b0054']


def main():
    if (ROOT/'investigator').exists() or (ROOT/'frozen-source').exists():
        raise ValueError('This single-call development attempt already exists')
    write(ROOT/'selection.json',{'question':QUESTION,'blocks':BLOCKS,'max_new_model_calls':1,
        'scope':'Known owl development paper. Coordinator selected a prior review question. No review outputs or judge ratings are supplied to the investigator. Not a blind discovery or quality comparison.'})
    shutil.copytree(REPO/'paper_workspace',ROOT/'frozen-source/paper_workspace',
                    ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    with tracked_stage(ROOT/'worker-state.json','focused-investigation',timeout=700):
        memo=investigate(BASE,ROOT/'investigator',ROOT/'billing_confirmation.json',
                         '2026-09-25',QUESTION,BLOCKS)
    print({'ready_for_adjudication':memo['ready_for_adjudication'],
           'tool_audit':memo['tool_policy_audit']})


if __name__=='__main__':
    main()
