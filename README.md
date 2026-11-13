# Paper Workbench

An evidence-linked workspace for manuscript review and revision. This private research prototype imports manuscripts, shows a PeerReviewAgents review beside the source text, and turns located comments and proposed edits into tracked revisions.

The project was extracted from In Silico. The review itself runs in PeerReviewAgents 0.9.0 or newer, as the `pra` plugin in a headless Claude Code session. This repository is the workspace, viewer and revision app built on that engine.

## Team handoff

Start with [the team handoff](HANDOFF.md) for the current architecture, setup and next engineering task. The companion paper repository contains the study evidence and publication blockers.

## Install

Requires Python 3.11 or newer. The app needs `peerreviewagents` 0.9.0 or newer, which is not on PyPI yet. Until it is, install the engine from its main branch first, then this app:

```bash
python -m pip install 'peerreviewagents @ git+https://github.com/pgarrett-scripps/PeerReviewAgents@main'
python -m pip install -e '.[documents,test]'
paper-workbench --help
```

A PeerReviewAgents checkout works too, with `python -m pip install -e ../PeerReviewAgents` as the first command.

Poppler is required for PDF import and page inspection. Word and PDF export can additionally require LibreOffice or Typst. Paper Scaffold integrations accept an explicit checkout path. Source verification and the viewer do not require those renderers.

## Review a manuscript

```bash
paper-workbench review manuscript.pdf runs/example
paper-workbench serve runs/example --port 38744
```

`review` is exactly `peerreview review`. It imports the PDF into `runs/example/manuscript`, runs three core reviewers and six specialist tracks, then the editor, and writes the run to `runs/example/review` with `REVIEW.md` and `REVIEW.txt`. `--reviewers N` sets the core reviewer count and `--arm NAME` picks a study arm. `--reviewer-models`, `--specialist-model`, `--editor-model` and `--recorder-model` set the model each slot is asked to run. `--citation-workers N`, 4 by default, sets how many citation workers judge each in-text citation against its source, and `--citation-worker-model` sets their model. The default arm, `full-two-track`, is the review a person should run. `paper-workbench review -h` lists the rest of the options.

A review is model inference. It needs the `claude` CLI on `PATH`, signed in to a Claude subscription. It never uses an API key, and it records its own token use in `runtime.json`. How much a run may spend is the operator's own setting. Without `claude`, the run is blocked at startup and launches nothing.

`serve RUN` opens the run in the viewer. Each finding shows its track, its basis (`computed`, `two-quotes` or `judgement`), whether a specialist escalated it and the editor's ruling. The editor's body findings come first, and duplicates and appendix findings follow in a separate appendix. A run panel shows the verdict, the specialist audit reports, one line per agent with the model asked and the model ran, and the run limitations. Its citation section counts each reference state on its own, lists the references to check and shows every worker verdict with the source passage it quoted, as quoted text, and says when the check did not finish. A run that stopped early, from a token ceiling, a timeout, a rate limit or a session error, opens with its status, its cause and the findings it recorded. `paper-workbench report RUN` renders the two report files of any run, finished or stopped, with no model call.

To inspect a manuscript without model inference:

```bash
paper-workbench import manuscript.pdf workspaces/example --xml manuscript.xml
paper-workbench verify workspaces/example
paper-workbench serve workspaces/example --port 38744
```

## Engine and app

- PeerReviewAgents owns the review: ingest, the plugin, its agents and tools, the domain packs and the report writer. Its public Python surface is `review`, `review_main`, `report_main`, `read_run`, `read_citation_ledger`, `locate_run`, `NotARunFolder`, `import_paper`, `write_reports`, `verify_workspace`, `export_draft`, the run constants and the helpers in `peerreviewagents.workspace`.
- `paper_workspace` (here) owns the viewer server, author decisions, revisions, Paper Scaffold import and export, and Word review copies.
- `paper-workbench review` and `report` hand off to the engine. Every other command, including `import`, `verify` and `serve`, belongs to the app.
- The app calls the engine only through that surface. It uses `locate_run` and `NotARunFolder` to tell a run folder from a workspace, and takes `digest`, `read_json`, `write_json`, `save_review`, `normalize_review`, `words` and `text_of` from `peerreviewagents.workspace`. A test fails if any module imports a private engine module.
- `experiments` holds the protocols and results of earlier studies. The experiment runners and most study records in `docs` were deleted, and git history keeps them. Study code that used the 0.8 engine runs only against PeerReviewAgents `v0.8.0`.

See [the engine contract](docs/shared-core.md) for what the app reads from a run.

CI runs the viewer checks first, with Node only. It then installs this package with its test dependencies from PyPI, so the Python tests fail at the install step until PeerReviewAgents 0.9.0 is published there.

## Validation status

This is a research prototype, not a validated claim of superiority over a single agent or human reviewers. No controlled comparison of the engine 0.9 workflow is reported in this repository. The last one, a focused debate comparison on the 0.8 engine, scored both reviews 8/10 and the judge narrowly preferred the saved review. See [the full result](docs/pra-focused-debate-results.md). That debate workflow is frozen at the PeerReviewAgents `v0.8.0` release.

```bash
python -m unittest discover -s tests -p 'test_*.py'
node tests/test_review_evidence_ui.js
```

Tests use synthetic or local fixtures and never start a review. Some optional rendering checks require local document tooling.

## Provenance

[The extraction manifest](migration/source-snapshot.json) records hashes of the imported source snapshot. The first commit preserves that snapshot before packaging changes. Raw manuscripts, model responses, caches and credentials are excluded from Git. Existing local study runs remain preserved separately. See [migration details](docs/migration.md).

The source licenses and attribution are preserved in [LICENSE](LICENSE). The repository is private. No package has been published to a registry.
