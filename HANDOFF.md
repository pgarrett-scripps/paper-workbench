# Paper Workbench team handoff

Snapshot: 12 November 2026. Start here for the current framework. The companion [paper repository](https://github.com/pgarrett-scripps/paper-workbench-paper) holds the manuscript, study evidence, figures, recovery records and publication priorities.

## Engine and app split

PeerReviewAgents runs the review. Version 0.9.0 replaced its Python orchestration with the `pra` Claude Code plugin, run headless by `peerreview review`. The debate, the six review modes, the three policies, `ReviewRequest`, `run_review` and the Codex provider are gone, with no shim. The 0.8 engine is frozen at the PeerReviewAgents `v0.8.0` release.

This repository is the workspace, viewer and revision app. It needs engine 0.9.0 or newer. It starts a review through the engine's `peerreview review` entry and reads the run folder the review writes. Make review changes in PeerReviewAgents, not here.

Engine 0.9.0 is not on PyPI yet. CI installs from PyPI, so it stays red at the install step until 0.9.0 is published.

## Get started

Accept collaborator access to the private repositories, then clone them into sibling directories. Install the engine before the app. Until 0.9.0 is on PyPI, install it from the PeerReviewAgents main branch, or with `python -m pip install -e ../PeerReviewAgents` from a checkout:

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
node tests/test_review_evidence_ui.js
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

`paper-workbench review manuscript.pdf RUN` runs one review, exactly as `peerreview review` does. It takes `--reviewers N` and `--arm NAME`, and the default arm is `full-two-track`. The run folder holds `RUN/manuscript`, the imported workspace, and `RUN/review`, with `protocol.json`, `progress.json`, `runtime.json`, `findings.jsonl`, `editor-package.json`, the `audit_<track>.md` specialist reports and `REVIEW.md`. `paper-workbench serve RUN` shows it. A run the starter stopped early, from a token ceiling, a timeout, a rate limit or a session error, has no `protocol.json` or `editor-package.json`. The viewer still opens it and shows its status, its cause and the findings it recorded. See [the engine contract](docs/shared-core.md) for the fields the viewer reads.

The viewer shows the editor's body findings first and the duplicates and appendix findings after them. Each finding shows its track, its basis, any escalation and the editor's ruling on it. A run panel shows the verdict, the specialist reports, the reviewer slots and the run limitations. Author decisions on a run are saved in `RUN/manuscript/decisions/run.json`, so the review folder stays as the run wrote it.

The engine anchors every finding to an exact source quotation and labels its basis. Author decisions and revision exports are distinct from scientific adjudication. Exact source linkage does not establish that a criticism is scientifically correct.

`experiments/` keeps the protocols and results of earlier studies. Their runners were deleted, and git history keeps them, as described in [experiments/README.md](experiments/README.md). Study code that used the 0.8 engine runs only against PeerReviewAgents `v0.8.0`. Read the paper handoff before interpreting study results.

## Where to work

| Area | Entry point |
| --- | --- |
| Running a review (engine) | `peerreviewagents/plugin/` in PeerReviewAgents |
| Reading a run folder (app) | `paper_workspace/run_view.py` |
| Viewer (app) | `paper_workspace/web/`, `paper_workspace/server.py` |
| Revisions and exports (app) | `paper_workspace/revisions.py`, `scaffold_*.py`, `word_review.py` |
| Command line (app) | `paper_workspace/__main__.py` |
| Regression checks | `tests/` here, and `tests/` in PeerReviewAgents |

## Next step

The app reads the run folder by file name in `run_view.read_run`, because the engine has no public run reader yet. That function returns the keys the engine's planned public `read_run` will return, so the switch is one import. A rename in `editor-package.json` breaks the viewer without an import error. The next engineering task is a versioned run-folder fixture shared by both repositories, so an engine change that breaks the viewer fails a test.

## Execution and collaboration

Offline inspection and tests need no model login. Tests stub the engine review and never start one. New model runs require the operator's own signed-in Claude subscription session. Do not copy account credentials. The run records its token use in `runtime.json` and stops at its own token and wall-clock ceilings. How much a run may spend is the operator's own setting.

Use a new run folder for each new attempt. Do not overwrite frozen outputs or automatically rerun the full study as a setup check.

Develop on a branch and open a pull request. Pin the engine commit, the arm, the literature cutoff and the source inputs for new comparisons. The run's `protocol.json` records what a run was allowed to do. The benchmark owns datasets, grading and statistics.
