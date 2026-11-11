# Paper Workbench team handoff

Snapshot: 11 October 2026. Start here for the current framework. The companion [paper repository](https://github.com/pgarrett-scripps/paper-workbench-paper) holds the manuscript, study evidence, figures, recovery records and publication priorities.

## Engine and app split

Version 0.2.0 moves the review engine (ingest, reviewers, synthesis, tools, domain packs and the headless API) to PeerReviewAgents as `peerreviewagents.engine`. The app needs engine 0.8.0 or newer. This repository is now the workspace and revision app. Its engine module names, and all of `paper_workbench_core`, are aliases for the engine modules, so imports and test patches through those names reach the engine. Make engine changes in PeerReviewAgents, not here. See [the split map](docs/engine-split-map.md).

Engine 0.8.0 is not on PyPI yet. CI installs it from the PeerReviewAgents main branch.

## Get started

Accept collaborator access to the private repositories, then clone them into sibling directories. Install the engine before the app. Until 0.8.0 is on PyPI, install it from the PeerReviewAgents main branch, or with `python -m pip install -e ../PeerReviewAgents` from a checkout:

```bash
git clone https://github.com/pgarrett-scripps/paper-workbench.git
git clone https://github.com/pgarrett-scripps/paper-workbench-paper.git
cd paper-workbench
python3 -m venv .venv
. .venv/bin/activate
python -m pip install 'peerreviewagents @ git+https://github.com/pgarrett-scripps/PeerReviewAgents@main'
python -m pip install -e '.[documents,test]'
paper-workbench --help
python -m unittest discover -s tests -p 'test_*.py'
```

Use Python 3.11 or newer. PDF import and page inspection also require Poppler. Optional document export needs the renderer for that export path. The paper repository has its own locked toolchain and setup guide. The framework's optional dependencies are not fully locked, so record installed versions when preparing a new experiment.

To inspect a manuscript without model inference:

```bash
paper-workbench import manuscript.pdf workspaces/example --xml manuscript.xml
paper-workbench verify workspaces/example
paper-workbench serve workspaces/example --port 38744
```

Replace the source filenames with your own files. Omit `--xml` for PDF-only input. Open `http://127.0.0.1:38744`. Existing localhost browser tabs on Ty's machine are not shared deployments.

## Current architecture

The supported integration surface is `peerreviewagents.engine.api`, still importable as `paper_workbench_core`. Use `ReviewRequest` and `run_review` for configurable manuscript-only, independent workspace, or ensemble workflows. Ensemble defaults to two independent reviewers followed by synthesis. A request that names no policy runs agentic-v1, at high effort with no finding cap. `standard-v1` is the bounded study budget. The API supports debate and ordinary synthesis policies. See [the core contract](docs/shared-core.md) and, in PeerReviewAgents, `peerreviewagents/engine/config.py` and `peerreviewagents/engine/api.py` for the executable settings.

The engine imports source blocks and references, provides bounded source and literature tools, preserves evidence receipts, validates quotes and issue accounting, and exports located comments and proposed edits. Author decisions and revision exports are distinct from scientific adjudication. Exact source linkage does not establish that a criticism is scientifically correct.

The legacy CLI `review --mode panel` and many files under `experiments/` describe earlier workflows. They are not interchangeable with the current core ensemble API. Frozen historical scripts must retain their original inputs and code. Read the paper handoff before interpreting study results.

## Where to work

Engine rows are paths in PeerReviewAgents under `peerreviewagents/engine/`. App rows are paths in this repository.

| Area | Entry point |
| --- | --- |
| Public requests and integration (engine) | `api.py`, `config.py` |
| Independent reviews and synthesis orchestration (engine) | `ensemble.py` |
| Synthesis decisions and component contract (engine) | `ensemble_debate.py`, `debate_revision.py` |
| Synthesis preflight and feedback (engine) | `synthesis_validation.py`, `ensemble_references.py` |
| Tool access and model transport (engine) | `investigation.py`, `model_runtime.py` |
| Model catalog and review policies (engine) | `models.py`, `review_policy.py` |
| Viewer and revisions (app) | `paper_workspace/web/`, `paper_workspace/server.py`, `paper_workspace/revisions.py` |
| Regression checks | `tests/` here, and `tests/engine/` in PeerReviewAgents |

## Exact stopping point

Core version 0.1.6 at commit `87975b61d68d85027585e09d5a2392a276bad879` added two bounded synthesis preflight checks and clearer validation feedback. It is committed source, not a published package release. The main study used an earlier frozen engine. Do not substitute the current code when reproducing its execution.

The subsequent four-paper recovery completed three syntheses. Paper `0317140` still failed because the model supplied 14 issue decisions and five final comments but omitted all 38 required component records. This is a traceability failure, not proof that all scientific points were lost. The [recovery results](https://github.com/pgarrett-scripps/paper-workbench-paper/blob/master/study/synthesis-recovery-20261011-v1/RESULTS.md) preserve every attempt.

Core 0.1.7 requires complete component structure in the synthesis response contract and names missing, duplicated, misassigned and unknown component identifiers in preflight and final validation records. Offline regression cases cover each failure and an offline replay of the saved 0317140 drafts. Final validation remains strict. See [the component ledger contract](docs/pra-configurable-ensemble.md#component-ledger-contract). The change has not been tested with a model. The next step is a separately recorded, bounded synthesis trial.

Core 0.1.8 adds a Claude Code transport so collaborators can run every model workflow on a Claude subscription instead of a ChatGPT plan. Use `--provider claude-code` for the Sonnet 5.5 default, or select `claude-opus-5-5`, whose safeguards can refuse life-science manuscripts. Sonnet 5.5 has completed ensemble reviews of all 30 benchmark corpus manuscripts. The 30th, at 48,090 words, needed the review input limit raised from 35,000 to 50,000 extracted words. Three syntheses failed final validation on the first attempt and passed on a fresh run. Claude runs are a separate condition from the Codex study. See [the provider guide](docs/claude-code-provider.md).

## Execution and collaboration

Offline inspection and tests need no model login. New model runs require the operator's own authenticated subscription session. Do not copy account credentials. The engine supports the Claude Code transport, the default, and the Codex transport. Consult `capabilities()` for the accepted model IDs of each. The engine records usage in each run's `usage.jsonl` and does not gate on it, so how much a run may spend is the operator's own setting.

Token limits are launch guards, not hard within-call caps. Unknown usage or interrupted execution must be reconciled before continuing. Use a new output directory for each new attempt. Do not overwrite frozen outputs or automatically rerun the full study as a setup check.

Develop on a branch and open a pull request. Pin the engine commit, dependencies, prompts, tool settings, model request and source inputs for new comparisons. The benchmark owns datasets, grading and statistics. Reuse the core API instead of duplicating the pipeline.
