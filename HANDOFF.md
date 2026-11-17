# Paper Workbench team handoff

Snapshot: 16 November 2026. Start here for the current framework. The companion [paper repository](https://github.com/pgarrett-scripps/paper-workbench-paper) holds the manuscript, study evidence, figures, recovery records and publication priorities.

## Engine and app split

PeerReviewAgents runs the review. Version 0.9.0 replaced its Python orchestration with the `pra` Claude Code plugin, run headless by `peerreview review`. The debate, the six review modes, the three policies, `ReviewRequest`, `run_review` and the Codex provider are gone, with no shim. The 0.8 engine is frozen at the PeerReviewAgents `v0.8.0` release. Version 0.10.0 replaced per-finding placement with issues. The editor groups the findings into issues with ids that carry across rounds, and `review/issues.json` is the review that `REVIEW.md` renders from. Engine main after that replaced block ids with a line-based manuscript: `paper.md`, one document per supplement, `map.json` with the page and box of each piece, and `manifest.json`. A finding names its document, its line and its offsets. Engine main at e7c8b65 adds the Read stage: an import writes a draft, and the reader, slot `reader`, repairs equations and tables against the page images, describes each figure and seals the manuscript before any reviewer starts. Each map row says in `source` whether the converter or a model wrote it, and the viewer labels every piece a model wrote. Engine main at 5244583 marks every such line for the reviewer, records the lines each lost page became, makes `write_manuscript` name the model behind any model-written piece with `ai_model=`, refuses an unstamped manuscript and says in `read_run`'s `manuscript.state` whether a run's manuscript is absent, a draft or sealed. Engine main at 3f475ca lets the reader re-read any piece on a page it has viewed as several pieces, with `original.part` and `original.of`, cut debris out of prose without typing it, fold debris pieces into the piece they belong to under `original.absorbed`, and leave a note on the document in `ai_read.note`, which the viewer shows as that model's account. Engine main at 23cb205 writes `original.absorbed` on one part of a re-read only, the first part that is not prose, adds `scripted_read`, a public way to build a read manuscript with a script in place of the model, and counts in `ai_read.gone` the absorbed, withdrawn and merged pieces that are no longer in the manuscript. The reader fixture is built through `scripted_read`, and the viewer does not show `gone`. Engine main at 4aae006 always runs the reader on a PDF review and drops `--no-ai-read`, `PEERREVIEW_AI_READ` and `ai_read=` with no shim. It adds a code reviewer: `--code FOLDER_OR_URL` snapshots the paper's analysis code into `RUN/code/` and plans one more specialist, `spec-code`, whose findings have basis `code-checked` and carry `code_evidence`, the file, lines and text the server found in the snapshot. The viewer shows that file and those lines on the finding, the run panel says which code was reviewed, and a Word review copy names them in the comment. Engine main at e88914d plans no Read stage for a run opened over a manuscript that is already sealed: `ingest` returns `reader: null` and mints no reader claim code, and a reader claim on a sealed manuscript is refused in words. Engine main at 496b2fa leaves out of a code snapshot the run folder being written and every other PeerReviewAgents run folder under the code, each listed in `skipped` with its reason, and makes `review_arms()` public, one row per arm saying among other things whether it reviews code. A workspace review can now write its run inside the workspace, and the app hands a workspace's code only to an arm whose row says it reviews code.

This repository is the workspace, viewer and revision app. It pins engine 0.10.0 and is tested against PeerReviewAgents main at commit 496b2fa. It starts a review through the engine's public `review_main`, the entry `peerreview review` uses, and reads the run folder with the engine's `read_run`. Make review changes in PeerReviewAgents, not here.

Engine 0.10.0 is not on PyPI yet. CI installs from PyPI, so it stays red at the install step until 0.10.0 is published.

## Get started

Accept collaborator access to the private repositories, then clone them into sibling directories. Install the engine before the app. Until 0.10.0 is on PyPI, install it from the PeerReviewAgents main branch, or with `python -m pip install -e ../PeerReviewAgents` from a checkout:

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

`paper-workbench review manuscript.pdf RUN` runs one review, exactly as `peerreview review` does. It takes `--reviewers N`, `--arm NAME` and the per-slot model options `--reviewer-models`, `--specialist-model`, `--editor-model` and `--recorder-model`, with `--citation-workers N` and `--citation-worker-model` for the citation workers, and the default arm is `full-two-track`. `--prior-issues PATH` takes the previous round's `RUN/review/issues.json`, so a later round keeps the issue ids and rules on each prior issue. `--code FOLDER_OR_URL` gives the review the manuscript's analysis code, such as the paper repository or its `analysis/` folder, and an arm that `review_arms()` says reviews no code refuses it. A Paper Scaffold workspace folder can stand where the PDF does, as in `paper-workbench review . reviews/one` from inside it. The app then reviews the workspace's built `paper.pdf`, refused when its build record says it does not match the source, and hands the engine the repository the workspace is in as the code, unless `--code` or `--no-code` says otherwise. On an arm that reviews no code it stops and says to give `--no-code`. The run folder can be inside the workspace, because the engine leaves run folders out of its code snapshot. The viewer has no way to start a review, so a later round starts here. The run folder holds `RUN/manuscript`, the imported workspace, and `RUN/review`, with `protocol.json`, `progress.json`, `runtime.json`, `findings.jsonl`, `issues.json`, the `audit_<track>.md` specialist reports, the citation ledger in `citations/ledger.jsonl` and `REVIEW.md`. `paper-workbench serve RUN` shows it. A run the starter stopped early, from a token ceiling, a timeout, a rate limit or a session error, has no `protocol.json` or `issues.json`. The viewer still opens it and shows its status, its cause and the findings it recorded. See [the engine contract](docs/shared-core.md) for the fields the viewer reads.

The viewer shows one card and one author decision per issue. The required changes, major and moderate, come first in rank order, then the minor suggestions under their categories. Each card shows how many reviewers raised it, its status against a prior round and its member findings as evidence, each with its track, its basis, any escalation and the editor's ruling on it. Every member is marked on the manuscript text. A run that is not publishable says why above its comments. A run panel shows the verdict, the specialist reports, one line per agent with the model asked and the model ran, the citation ledger and the run limitations. Author decisions on a run are saved in `RUN/manuscript/decisions/run.json`, so the review folder stays as the run wrote it. A later round is a new run folder and opens with no decisions. A run folder from an engine before 0.10 is refused with a message to re-run it.

The engine anchors every finding to an exact source quotation by document, line and offsets, and labels its basis. The viewer reads that span off the manuscript and never searches for the quote again. Author decisions and revision exports are distinct from scientific adjudication. Exact source linkage does not establish that a criticism is scientifically correct.

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

The app reads a run only through the engine's public `read_run`, so a renamed key in a run file is the engine's to absorb. The viewer still reads `read_run`'s result keys by name, and a rename there breaks it without an import error. The next engineering task is a versioned run-folder fixture shared by both repositories, so an engine change that breaks the viewer fails a test. Every engine import is a public name, and a test fails if a private one comes back.

## Execution and collaboration

Offline inspection and tests need no model login. Tests stub the engine review and never start one. New model runs require the operator's own signed-in Claude subscription session. Do not copy account credentials. The run records its token use in `runtime.json` and stops at its own token and wall-clock ceilings. How much a run may spend is the operator's own setting.

Use a new run folder for each new attempt. Do not overwrite frozen outputs or automatically rerun the full study as a setup check.

Develop on a branch and open a pull request. Pin the engine commit, the arm, the literature cutoff and the source inputs for new comparisons. The run's `protocol.json` records what a run was allowed to do. The benchmark owns datasets, grading and statistics.
