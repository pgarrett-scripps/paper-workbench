# Manuscript review workspace

A local research prototype for scientific peer review in context. It imports a PDF, optionally uses publisher JATS XML for text and references, preserves supplementary table cells, and presents source-linked comments and proposed wording changes. It does not rerun author analyses.

## Use

Install Paper Workbench as described in the repository README. The review runs in PeerReviewAgents 0.10.0, as the `pra` plugin in a headless Claude Code session. The app code here is the viewer server, the run-folder reader, revisions, Paper Scaffold import and export, and Word review copies. PDF import requires Poppler, and the engine pins `rustypaper`.

```bash
python -m paper_workspace import manuscript.pdf workspace --xml manuscript.xml --supplements supplement-directory
python -m paper_workspace verify workspace
python -m paper_workspace serve workspace --port 38744
```

Open `http://127.0.0.1:38744`. Sources stay local unless you explicitly run a review.

The viewer supports original text, marked suggestions, and an accepted-draft preview. Accept, decline, follow-up, and undo decisions persist on disk. JSON export contains the original documents, the proposed documents, findings, and decisions. Accepting wording does not resolve a scientific concern.

## Review

```bash
python -m paper_workspace review manuscript.pdf run-output
python -m paper_workspace review manuscript.pdf run-output --reviewers 5 --literature-cutoff 2026-01-05
python -m paper_workspace review path/to/scaffold-workspace run-output
python -m paper_workspace serve run-output
```

A manuscript workspace made with `import-scaffold` stands where the PDF does too, and its current draft is reviewed, as the fix loop below says. A Paper Scaffold workspace folder stands where the PDF does. `workspace_review.py` hands the engine its built `paper.pdf` and refuses, with exit 2 and nothing written, a PDF that is missing or that `.build-state/paper.pdf.json` says no longer matches the source. It passes `--code` with the repository the workspace is in, or the workspace outside git, unless `--code` or `--no-code` is given. On an arm that `review_arms()` says reviews no code it hands over none and says so on stderr. A run folder inside that code is fine, because the engine leaves every run folder out of its snapshot. Nothing in the workspace is run.

`review` hands its arguments to the engine's `peerreview review` entry, so it takes exactly the same options. The default arm, `full-two-track`, runs three core reviewers and six specialist tracks in isolation, then an editor who rules on every finding. `--arm NAME` selects a study arm, and `--reviewer-models`, `--specialist-model`, `--editor-model` and `--recorder-model` set the model each slot is asked to run. `--citation-workers N`, from 0 to 12 and 4 by default, sets how many citation workers judge the in-text citations, and `--citation-worker-model` sets their model. Every review is a fresh panel that knows nothing of an earlier review. The viewer has no button that starts a review, so every review is started here. The command prints the run summary and exits 0 when the review completed, 2 when it never started and 1 otherwise.

This command performs model inference. It requires the `claude` CLI on `PATH`, signed in to a Claude subscription. API keys are never used. The run records its token use in `review/runtime.json` and stops at its own token and wall-clock ceilings. Without `claude`, the run is blocked at startup, records why in `review/startup.json` and launches nothing.

The run folder holds `manuscript`, the imported workspace, and `review`, the run. `python -m paper_workspace report run-output` renders `REVIEW.md` and `REVIEW.txt` from the saved run with no model call. It works on any run, finished, stopped or blocked at startup, and prints the status, the cause, the finding count, whether the review is publishable, any file it could not read and the report paths.

`serve` on a run folder shows the run as the review named `run`. `run_view.py` shows what the engine's `read_run` returns, with the citation rows from the engine's `read_citation_ledger`:

- The unit is the issue from `review/issues.json`, with one card and one author decision each, keyed by the issue id. The required changes, major and moderate, come first in rank order. The minor suggestions follow under their categories. A card shows its severity, category, statement, how many reviewers raised it, the specialist reports behind it and any rebuttal quotation.
- Each card lists its member findings as evidence. A member is joined to its ledger row by `finding_uid` for its comment, span and suggested wording, and shows its slot, track, basis with the reason the engine gave, whether a specialist escalated it and the escalation ruling. A `code-checked` member also shows the file, the line or lines and the code it quotes from the run's code snapshot, and says how much of the file the review read when it is a data file. The run panel says which code the run was reviewed against. Every member is marked on the manuscript text by its document, line and offsets, across a line break too, and pinned with its issue's number. A span that no longer covers its text is shown unplaced on its line. A card whose one member is an anchored edit takes the wording decision, and every other card takes a note.
- A run that is not publishable, because the editor failed or the review is over the size limit, says so above its comments with every reason from `not_publishable_reasons`. It is never shown as an empty review.
- A run folder from an engine before 0.10, with `editor-package.json` and no `issues.json`, is refused with "This review was made by an older engine, re-run it." An `issues.json` with a value of the wrong type is refused in one message naming the issue and the field.
- A card with no engine id is numbered by its place and takes no decision. Saved decisions that match no card are counted once above the cards, and the decisions file is left as it is.
- A run panel shows the arm, status, verdict, specialist audit reports, one line per agent with its model asked, model ran, tokens and tasks, a note naming any slot whose model ran was not recorded, findings by track and run limitations. A `complete-without-findings` status says whether the reviewers raised nothing, the guard quarantined all they raised or the code check threw it all out. It also shows why a run stopped, a limit that fired after the review was written, and every file the engine could not read in full. On a run given code it says which data files a reviewer fetched, whole or only in part, and counts the code check's verdicts. The Required changes, Suggestions and Escalated filters keep those cards only.
- A finding the code check threw out, because the code does not do what it said, is in no issue and is never a card. On the All view it is listed after every issue under "Thrown out: the code does not do what the finding said", marked as not an open issue, with what it took the code to do, the code that contradicts it and the check's note. It takes no decision.
- A citation section shows the engine's citation ledger. References found in an index, DOIs the DOI resolver does not hold, titles neither Crossref nor Europe PMC lists, references that could not be checked and references never looked up each keep their own count. It lists the references to check and every in-text use with the worker's verdict, the source passage it quoted and its note, escaped as quoted text. It says when the check did not finish. A reference it could not locate or could not check is never shown as a work that does not exist.
- A run without `issues.json` shows the findings recorded in `findings.jsonl` as cards of their own, keeping the latest row for each finding, and says that the run has not written its issues. A finding that no issue holds is shown the same way, after the issues.
- A run the starter stopped early, from a token ceiling, a timeout, a rate limit or a session error, has no `protocol.json` or `manifest.json`. It still opens, with its status, its cause and its recorded findings. Each finding's fingerprint pins the manuscript version. The panel shows no arm or reviewer count for it, because `read_run` takes those only from `protocol.json`.
- Every piece a model wrote is labelled on the manuscript with the model's name. A piece the reader read again from the page image shows the converter's reading under a closed toggle. A piece read again as several says which part it is, a prose part the reader cut says every character in it is the converter's, and debris folded into a piece is listed under it as the converter read it. A note the reading model left about the document is shown above the manuscript as that model's account, not the authors' text and not a finding. A figure description says it is not the authors' words. A page the converter returned no text from is named above the manuscript and linked to the first line the engine says it became, because every line shown for it came from the model. In a manuscript no model read the pages of, such as a port, each such piece names the model the writer named and says there is no page image to compare it with.
- A run blocked at startup, stopped before its import or stopped before the Read stage sealed its manuscript has nothing to show. `read_run`'s manuscript state says which, and `serve` names it with the status and cause and exits 1. `report` still writes a report that says why. A manuscript whose manifest has no `schema_version` is refused with the engine's message.
- A run on a different manuscript version is refused. A symlinked run file is refused with an error, and files outside the review folder are never read.

Author decisions on a run are saved in `manuscript/decisions/run.json`. The review folder stays as the run wrote it. Each review is its own run folder, so a later review opens with no decisions, and a card says nothing about an earlier review.

## Fix loop

A fix loop runs on a native Scaffold workspace, imported with `import-scaffold` from a project built with `just paper`, so the original draft keeps its built PDF as `artifacts/paper.pdf`:

1. Review. `review WORKSPACE RUN` reviews the current draft's built PDF with its `scaffold/` source as the code, as a fresh panel that knows nothing of an earlier review, and adds the problems of the finished review to the draft's ledger. `import-run WORKSPACE RUN` adds a run folder the same way.
2. Decide. `decide WORKSPACE PROBLEM STATUS --rationale TEXT` marks a problem raised on the current draft open, addressed or declined. In `serve` the author also accepts or declines each card's wording. Addressed is the author's own assessment and leaves the problem open.
3. Revise. The viewer's revision button, or `revise`, builds the next draft. `revisions/DRAFT/issue-ledger.json` holds one row per problem under an id that never changes, such as `original:run:i03`, and the draft's manifest covers it.
4. Check fixes. `check-fixes` reads the current draft against the open problems in its ledger.
5. Fresh review. Review the new draft when you want new problems found. It reads nothing of the ledger, and its problems are new rows that match no earlier one.

```bash
python -m paper_workspace import-scaffold path/to/project path/to/workspace
python -m paper_workspace review path/to/workspace runs/r1
python -m paper_workspace decide path/to/workspace original:r1:i02 addressed --rationale "Reworded the claim"
python -m paper_workspace check-fixes path/to/workspace runs/fixes-1
```

`ledger_commands.py` holds `import-run` and `decide`. Both call `revisions.py`: `record_problems` reads the run through the engine's `read_run` and `problems_from_run` and takes a finished review only when the PDF it read is the current draft's built PDF by hash, and `decide` records one decision. Each refuses with one line on stderr, exit 2 and nothing changed. The problems of a review are kept beside the frozen ledger in `revisions/DRAFT/raised-problems.json` until the next draft copies them. A run added twice adds nothing, and a complete review the engine calls not publishable is added with its reasons printed.

`fix_check.py` writes `RUN/problems.json` in the engine's `review-problems-v1` schema from `open_problems(ledger, draft)`: every open problem the current draft has no verdict on yet, in severity order, each with its id, statement, severity, the quotes it was raised on and the author's note as `author_reply`. A problem the engine would refuse, such as one with no severity, is left out and named on stderr. It then hands the draft's built `artifacts/paper.pdf` and that file to the engine's `check_fixes_main`, the entry `peerreview check-fixes` uses, and takes the engine's other options as they are. It refuses, with exit 2 and nothing run, a folder that is not a workspace, a draft made with `--no-build`, a draft with no open problem left to check, a run folder that already holds files and any `--problems`.

The engine gives each problem it reaches one verdict from `peerreviewagents.names.FIX_VERDICTS`, which are `fixed`, `not-fixed` and `cannot-tell`. A `fixed` or `not-fixed` verdict rests on its basis: `quote` for a passage of the new draft, `old-quote-gone` when every quote the problem was raised on is gone and `old-quote-stands` when one is still there word for word. A `cannot-tell` verdict gives a reason instead, such as a fix that lives in the code. One check takes at most 40 problems, ten to a checker. `record_fix_checks` reads what `read_fix_check` returns and records one entry per problem in `revisions/DRAFT/fix-checks.json`, beside the frozen ledger: the run, the date, the verdict, the basis, the passage of the new draft as `evidence`, each quote it was raised on with whether it is still present, the searches, the reason and the checker's note. A problem past the cap or reached by no checker is entered as not checked, with why, and the next check of the same draft takes it again. Each check needs its own run folder and is recorded once. The next draft copies every entry into its own ledger. A check that is blocked, stopped or cannot be read whole records nothing, prints why and exits 1 or the engine's code. The stderr line after a recorded check counts each verdict and the problems not checked.

`problem_status` reads a row's status: `fixed` when its latest verdict is `fixed` and `open` while it is `not-fixed` or `cannot-tell`. A not-checked entry leaves the earlier verdict standing. The viewer shows each problem's latest verdict with its basis, the quote from the new draft and the checker's note, or that the check did not reach it and why, with earlier checks under a toggle. The verdict names come from the engine.

## Retired experiment runners

Engine 0.8 removed the study-only modules behind the staged evidence workflow, the revised debate, the two-paper and four-paper pilots, the handoff retests, the ensemble and reliability trials, and the transfer and domain studies. Engine 0.9 removed the remaining Python review orchestration. Every experiment runner is deleted, and git history keeps them. `experiments/` keeps the study protocols and result files, and [its README](../experiments/README.md) says how to recover a runner. The study records in `docs/` that described only the deleted system were deleted too, and git history keeps them. Study code that used the 0.8 engine runs only against PeerReviewAgents `v0.8.0`.

## Boundaries

- PDF layout and reading order can be imperfect. Source-page links support inspection, and unresolved anchors are explicit.
- Publisher XML is preferred when available. PDF-only references remain provisional.
- The prototype preserves text and references rather than reconstructing a complete editable Typst paper. Paper Scaffold supplied the interaction concept, but this package does not depend on that sibling checkout.
- JSON export is implemented. Native Word comments, tracked changes, and PDF annotation writeback are not implemented.
- Model output remains provisional. Source anchoring prevents misplaced edits, but it cannot prove a scientific allegation correct.

## Verification

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_review_evidence_ui.js
node --check paper_workspace/web/app.js
```

Tests cover the run-folder reader, finished, stopped and startup-blocked runs in the viewer, the review and report commands against the installed engine with `claude` off `PATH`, the fix check recorded from checks the engine's `scripted_fix_check` writes with no model, Unicode anchors, source tampering, overlap rejection, revisions, Scaffold import and export, and Word review copies. No test starts a review.

## Native Scaffold revisions

The real manuscript continuation supports citation-aware source edits, all prose paragraphs in the tested port, preserved source figures and structured tables, and version-bound Word and PDF downloads. See [the completed fixes and validation](../docs/pra-real-revision-improvements.md). This is workflow validation with no new review inference or superiority claim.

Native Scaffold projects support immutable source snapshots, exact prose anchors, separate revised drafts, PDF build gates, rollback, and a bounded unattended copyediting loop. Scientific concerns remain distinct from wording decisions. See [the revision workflow](../docs/pra-revision-loop.md) for commands, the agent handoff contract, validation, and current limits.

```bash
python -m paper_workspace import-scaffold /path/to/manuscript /path/to/workspace
python -m paper_workspace revision-loop /path/to/workspace --id language-pass --max-rounds 2 --max-edits 10
python -m paper_workspace revision-request /path/to/workspace
```

The built-in loop is offline and deliberately narrow. It makes no model calls. A provider callback can supply fresh version-bound proposals. Native Word export creates a clean manuscript, with review history retained in the workspace rather than embedded as Word tracked changes.

### Word review copies

After exporting a saved revision, run `python -m paper_workspace export-review WORKSPACE REVISION CLEAN_EXPORT NEW_OUTPUT`. The new package adds a Word copy with tracked changes from the immediate parent and comments for inherited open scientific questions. Each comment names the draft its problem was raised on and its ledger id. A problem the author declined or a fix check found fixed gets no comment. A finding the code check threw out is commented as thrown out, with the code that contradicts it, and is never an open question. Exact paragraph matches are required for located comments. Uncertain locations remain in an appendix. The viewer offers the verified review copy beside the clean Word and PDF downloads.

See [Word review handoff](../docs/pra-word-review-handoff.md) for validation and current limits.
