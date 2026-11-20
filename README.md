# Paper Workbench

An evidence-linked workspace for manuscript review and revision. This private research prototype imports manuscripts, shows a PeerReviewAgents review beside the source text, and turns located comments and proposed edits into tracked revisions.

The project was extracted from In Silico. The review itself runs in PeerReviewAgents 0.10.0, as a panel of headless Claude Code agents that the engine's own Python runs. This repository is the workspace, viewer and revision app built on that engine.

## Team handoff

Start with [the team handoff](HANDOFF.md) for the current architecture, setup and next engineering task. The companion paper repository contains the study evidence and publication blockers.

## Install

Requires Python 3.11 or newer. PeerReviewAgents 0.10.0 is not released yet, so the app pins the engine to its main branch at commit 55d5707, as GitHub's archive of that commit with the archive's hash. That engine reads manuscripts by line, has a model read each page image before every PDF review, can check the paper against its analysis code, throws out a finding when the code does not do what it said, gives the problems a review raised and checks a new draft against them. Installing the app installs that engine from GitHub, with no git needed:

```bash
python -m pip install -e '.[documents,test]'
paper-workbench --help
```

To run the app against a PeerReviewAgents checkout instead, run `python -m pip install -e ../PeerReviewAgents` after the app, and again after each reinstall of the app, which puts the pinned engine back.

Poppler is required for PDF import and page inspection. Word and PDF export can additionally require LibreOffice or Typst. Paper Scaffold integrations accept an explicit checkout path. Source verification and the viewer do not require those renderers.

## Review a manuscript

```bash
paper-workbench review manuscript.pdf runs/example
paper-workbench serve runs/example --port 38744
```

`review` is exactly `peerreview review`. It imports the PDF into `runs/example/manuscript`, where the Read stage repairs the equations and tables the converter garbled against the page images, describes each figure and seals the manuscript. The Read stage always runs on a PDF, and `--reader-model` sets its model. It then runs three core reviewers and six specialist tracks, then the editor, and writes the run to `runs/example/review` with `REVIEW.md` and `REVIEW.txt`. `--reviewers N` sets the core reviewer count and `--arm NAME` picks a study arm. `--reviewer-models`, `--specialist-model` and `--editor-model` set the model each slot is asked to run. The recorder is the engine's own Python, not an agent, so it has no model. `--citation-workers N`, 4 by default, sets how many citation workers judge each in-text citation against its source, and `--citation-worker-model` sets their model. The default arm, `full-two-track`, is the review a person should run. Every review is a fresh panel that knows nothing of an earlier review. `--code FOLDER_OR_URL` gives the review the paper's analysis code, a folder such as the paper's repository or its `analysis/` folder, or a repository URL. The engine copies the text of the code into `runs/example/code` and adds a code specialist, slot `spec-code`, which reads the manuscript and then checks what the methods say was done against what that copy of the code does. It reads the code and never runs it. Only `full-two-track` and `draft-check` review code, as `peerreviewagents.review_arms()` says, and every other arm refuses `--code`. `paper-workbench review -h` lists the rest of the options.

```bash
paper-workbench review manuscript.pdf runs/example --code ../my-paper/analysis
```

A manuscript workspace made with `import-scaffold` can also stand where the PDF does. The review then reads its current draft's built PDF, with that draft's source as the code, and adds its problems to the draft's issue ledger, as the [fix loop](#fix-loop) says. A Paper Scaffold workspace folder can stand there too, so a workspace is reviewed from inside it:

```bash
cd my-paper
just paper
paper-workbench review . reviews/r1
```

The review reads the workspace's built `paper.pdf`. It stops with a plain message, and writes nothing, when that PDF is missing or does not match the source as `just paper` last recorded it in `.build-state/paper.pdf.json`. The code reviewer is handed the repository the workspace is in, or the workspace itself outside git. The engine copies only its text source and lists what it left out, such as data, results, figures, dependencies and files that may hold secrets. `--code FOLDER_OR_URL` names other code and `--no-code` reviews the paper alone. On an arm that reviews no code, such as `reviewers-only`, a workspace review reviews the paper alone and says so, naming the arms that review code. Only a `--code` you give on such an arm is refused. The run folder can be inside the workspace, as `reviews/r1` is here. The engine leaves it, and every other review run folder, out of the code it copies and lists each with what it left out.

A review is model inference. It needs the `claude` CLI on `PATH`, signed in to a Claude subscription. It never uses an API key, and it records its own token use in `runtime.json`. How much a run may spend is the operator's own setting. Without `claude`, the run is blocked at startup and launches nothing.

`serve RUN` opens the run in the viewer. The unit is the editor's issue, with one card and one author decision each. The required changes, major and moderate, come first in rank order, then the minor suggestions under their categories. Each card shows how many reviewers raised it and its member findings as evidence, each with its track, its basis (`computed`, `two-quotes`, `code-checked` or `judgement`), whether a specialist escalated it and the editor's ruling. A `code-checked` finding also names the file and lines of the run's code snapshot it quotes, and shows that code. The run panel says which code the run was reviewed against, at which commit, which files a reviewer opened and which data files a reviewer fetched, whole or only in part. It counts what the code check found. A finding the code check threw out, because the code does not do what it said, is no issue and takes no decision. It is listed after the issues, marked as thrown out, with what it took the code to do and the code that contradicts it. A Word review copy names the file and lines in the comment, says how much of a data file the review read, and comments a thrown-out finding as thrown out, never as an open question. Every member is marked on the manuscript text. Every piece a model wrote is labelled with the model's name, and a page that came only from the model is named above the manuscript with a link to the lines it became. A note the reading model left about the document is shown above the manuscript as that model's account, not the authors' text. A run that stopped before its import, or before the Read stage sealed its manuscript, says which. A card says nothing about an earlier review. Each review is its own run folder with its own decisions, so a later review opens with none. A run that is not publishable says so above its comments, with every reason. A run folder from an engine before 0.10 is refused with a message to re-run it. A run panel shows the verdict, the specialist audit reports, one line per agent with the model asked and the model ran, and the run limitations. Its citation section counts each reference state on its own, lists the references to check and shows every worker verdict with the source passage it quoted, as quoted text, and says when the check did not finish. A run that stopped early, from a token ceiling, a timeout, a rate limit or a session error, opens with its status, its cause and the findings it recorded. `paper-workbench report RUN` renders the two report files of any run, finished or stopped, with no model call.

To inspect a manuscript without model inference:

```bash
paper-workbench import manuscript.pdf workspaces/example --xml manuscript.xml
paper-workbench verify workspaces/example
paper-workbench serve workspaces/example --port 38744
```

## Fix loop

A fix loop runs on a manuscript workspace made from a Paper Scaffold project with `import-scaffold`, whose drafts are kept under `revisions/`. Build the project with `just paper` first, so the original draft has the built PDF a review and a fix check read.

1. Review. `paper-workbench review WORKSPACE RUN` reviews the current draft's built PDF, with that draft's source as the code, and adds the problems of the finished review to the draft's issue ledger. Every review is a fresh panel that knows nothing of an earlier one.
2. Decide. `paper-workbench decide WORKSPACE PROBLEM STATUS --rationale TEXT` marks a problem open, addressed or declined. Addressed and declined need a rationale, and `--note` leaves a note for the fix check. In `serve`, the cards of a review also take a wording decision.
3. Revise. Edit the source in the project folder the workspace was imported from, by hand or with an agent. `paper-workbench revise WORKSPACE PROJECT --id DRAFT` builds the next draft's PDF from it and freezes the current draft's issue ledger into it, one row per problem under an id that never changes. It needs `typst` on `PATH`, and it refuses, and says why, when nothing changed or the build fails. The viewer's revision button instead applies the wording a review's cards accepted.
4. Check fixes. `paper-workbench check-fixes WORKSPACE RUN` checks the current draft against the open problems in its ledger.
5. Decide again. A problem the check found not fixed is still open, and `decide` takes it on the new draft. Then edit and revise again.

Review the new draft whenever you want new problems found. It reads nothing of the ledger, and its problems are new rows that match no earlier one.

```bash
paper-workbench import-scaffold ../my-paper my-workspace
paper-workbench review my-workspace runs/r1
paper-workbench decide my-workspace original:r1:i02 declined --rationale "Out of scope for this paper"
paper-workbench revise my-workspace ../my-paper --id draft-2
paper-workbench check-fixes my-workspace runs/fixes-1
paper-workbench decide my-workspace original:r1:i01 addressed --rationale "The methods now name each donor"
paper-workbench revise my-workspace ../my-paper --id draft-3
```

`review` on a manuscript workspace prints the ids it added, or why it added none. `paper-workbench import-run WORKSPACE RUN` adds a review run the same way, such as one started by hand with the draft's `artifacts/paper.pdf`. It reads the run through the engine's `read_run` and `problems_from_run` and takes only a finished review of the current draft's built PDF, checked by hash. It refuses an unfinished run or a review of another PDF and says why. Adding the same run twice adds nothing. A finished review the engine calls not publishable, such as a `draft-check` run with no editor, is added with the engine's reasons printed beside it. `decide` takes any open or declined problem in the current draft's ledger, whichever draft raised it. Each decision records the draft it was made on. The decisions made on earlier drafts stay on the row and on its card, beside the fix checks, and an earlier draft's frozen ledger is never rewritten. A problem that is fixed, thrown out or a copyedit takes no decision. A fix check of the draft a problem was raised on leaves that problem out, because that draft is the text it was raised on.

`check-fixes` is the engine's `peerreview check-fixes` on the current draft's built PDF. It writes the problems file itself, to `RUN/problems.json`, from every open problem that draft has no verdict on yet, in severity order, so it takes no `--problems`. The engine gives each problem it reaches a verdict, `fixed`, `not-fixed` or `cannot-tell` in its own words. A `fixed` or `not-fixed` verdict rests on a quote from the new draft or on whether the quote the problem was raised on is still there, and `cannot-tell` gives a reason. It raises nothing new. The app records the verdicts in the draft's ledger, beside the frozen ledger in `fix-checks.json`, and the next draft carries them in its own ledger. A problem is fixed when its latest verdict says so, and a declined problem is never checked again. A check takes at most 40 problems. A problem it did not reach is recorded as not checked, with why, and the next check of the same draft, into a new run folder, takes it again. A blocked or stopped check, or one that cannot be read whole, records nothing and says why. A check is model inference with its own token and wall-clock ceilings, and it needs `claude` on `PATH` as a review does. The viewer shows each problem's latest verdict, its basis and the quote from the new draft, or that the check did not reach it, with the earlier checks below.

## Engine and app

- PeerReviewAgents owns the review and the fix check: ingest, the plugin, its agents and tools, the domain packs and the report writer. Its public Python surface is `review`, `review_main`, `review_parser`, `review_arms`, `check_fixes_main`, `check_fixes_parser`, `read_fix_check`, the problems file in `peerreviewagents.problems`, `report_main`, `read_run`, `read_citation_ledger`, `locate_run`, `NotARunFolder`, `import_paper`, `write_manuscript`, `read_manuscript`, `cited_text`, `citation_uses`, `write_reports`, `verify_workspace`, `export_draft`, the run constants and the helpers in `peerreviewagents.workspace`.
- The engine writes every manuscript as `paper.md`, one document per supplement, `map.json` and `manifest.json`. The app names a place in it by document and line, and a highlight on the page is the passage's page and box from `map.json` plus the quote. `import-scaffold` writes a Typst manuscript through `write_manuscript`, so it is the same base a PDF import writes.
- `paper_workspace` (here) owns the viewer server, author decisions, revisions, Paper Scaffold import and export, and Word review copies.
- `paper-workbench review`, `check-fixes` and `report` hand off to the engine. `check-fixes` writes the problems file from the ledger first and records what the engine's `read_fix_check` reads back. Every other command, including `import`, `verify` and `serve`, belongs to the app.
- The app calls the engine only through that surface. It uses `locate_run` and `NotARunFolder` to tell a run folder from a workspace, and takes `digest`, `read_json`, `write_json`, `save_review`, `normalize_review` and `text_of` from `peerreviewagents.workspace`. A test fails if any module imports a private engine module, apart from the two test tools the engine contract names.
- `experiments` holds the protocols and results of earlier studies. The experiment runners and most study records in `docs` were deleted, and git history keeps them. Study code that used the 0.8 engine runs only against PeerReviewAgents `v0.8.0`.

See [the engine contract](docs/shared-core.md) for what the app reads from a run.

CI runs the viewer checks first, with Node only. It then installs this package with its test dependencies, which brings the pinned engine commit from GitHub, and runs the Python tests with Poppler. No test runs typst. A test that builds a draft hands it a stand-in that writes the PDF.

## Validation status

This is a research prototype, not a validated claim of superiority over a single agent or human reviewers. No controlled comparison of the engine 0.9 or 0.10 workflow is reported in this repository. The last one, a focused debate comparison on the 0.8 engine, scored both reviews 8/10 and the judge narrowly preferred the saved review. See [the full result](docs/pra-focused-debate-results.md). That debate workflow is frozen at the PeerReviewAgents `v0.8.0` release.

```bash
python -m unittest discover -s tests -p 'test_*.py'
node tests/test_review_evidence_ui.js
```

Tests use synthetic or local fixtures and never start a review or a fix check. A review in a test is run by the engine's `scripted_review`, and a fix check by its `scripted_fix_check`, through the engine's own orchestrator with a script in each seat in place of a model. The read manuscript fixture is built by the engine's scripted reader with no model, which needs Poppler. Some optional rendering checks require local document tooling.

## Provenance

[The extraction manifest](migration/source-snapshot.json) records hashes of the imported source snapshot. The first commit preserves that snapshot before packaging changes. Raw manuscripts, model responses, caches and credentials are excluded from Git. Existing local study runs remain preserved separately. See [migration details](docs/migration.md).

The source licenses and attribution are preserved in [LICENSE](LICENSE). The repository is private. No package has been published to a registry.
