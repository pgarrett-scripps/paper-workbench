# Manuscript review workspace

A local research prototype for scientific peer review in context. It imports a PDF, optionally uses publisher JATS XML for text and references, preserves supplementary table cells, and presents source-linked comments and proposed wording changes. It does not rerun author analyses.

## Use

Install Paper Workbench as described in the repository README. The review runs in PeerReviewAgents 0.9.0 or newer, as the `pra` plugin in a headless Claude Code session. The app code here is the viewer server, the run-folder reader, revisions, Paper Scaffold import and export, and Word review copies. PDF import requires Poppler, and the engine pins `rustypaper`.

```bash
python -m paper_workspace import manuscript.pdf workspace --xml manuscript.xml --supplements supplement-directory
python -m paper_workspace verify workspace
python -m paper_workspace serve workspace --port 38744
```

Open `http://127.0.0.1:38744`. Sources stay local unless you explicitly run a review.

The viewer supports original text, marked suggestions, and an accepted-draft preview. Accept, decline, follow-up, and undo decisions persist on disk. JSON export contains the original source blocks, proposed blocks, findings, and decisions. Accepting wording does not resolve a scientific concern.

## Review

```bash
python -m paper_workspace review manuscript.pdf run-output
python -m paper_workspace review manuscript.pdf run-output --reviewers 5 --literature-cutoff 2026-01-05
python -m paper_workspace serve run-output
```

`review` hands its arguments to the engine's `peerreview review` entry, so it takes exactly the same options. The default arm, `full-two-track`, runs three core reviewers and six specialist tracks in isolation, then an editor who rules on every finding. `--arm NAME` selects a study arm, and `--reviewer-models`, `--specialist-model`, `--editor-model` and `--recorder-model` set the model each slot is asked to run. `--citation-workers N`, from 0 to 12 and 4 by default, sets how many citation workers judge the in-text citations, and `--citation-worker-model` sets their model. The command prints the run summary and exits 0 when the review completed, 2 when it never started and 1 otherwise.

This command performs model inference. It requires the `claude` CLI on `PATH`, signed in to a Claude subscription. API keys are never used. The run records its token use in `review/runtime.json` and stops at its own token and wall-clock ceilings. Without `claude`, the run is blocked at startup, records why in `review/startup.json` and launches nothing.

The run folder holds `manuscript`, the imported workspace, and `review`, the run. `python -m paper_workspace report run-output` renders `REVIEW.md` and `REVIEW.txt` from the saved run with no model call. It works on any run, finished, stopped or blocked at startup, and prints the status, the cause, the finding count, whether the review is publishable, any file it could not read and the report paths.

`serve` on a run folder shows the run as the review named `run`. `run_view.py` shows what the engine's `read_run` returns, and opens only the citation ledger itself:

- The editor package's body findings come first, numbered in the manuscript. Duplicates and appendix findings follow in a collapsed appendix, each linked to the finding it duplicates and with any rebuttal quotation.
- Each finding shows its track, its basis with the reason the engine gave, whether a specialist escalated it, the editor's reason and the escalation ruling.
- A run panel shows the arm, status, verdict, specialist audit reports, one line per agent with its model asked, model ran, tokens and tasks, a note naming any slot whose model ran was not recorded, findings by track and run limitations. A `complete-without-findings` status says whether the reviewers raised nothing or the guard quarantined all they raised. It also shows why a run stopped, a limit that fired after the review was written, and every file the engine could not read in full. An Escalated filter keeps only escalated findings.
- A citation section shows the engine's citation ledger. References found in an index, DOIs the DOI resolver does not hold, titles neither Crossref nor Europe PMC lists, references that could not be checked and references never looked up each keep their own count. It lists the references to check and every in-text use with the worker's verdict, the source passage it quoted and its note, escaped as quoted text. It says when the check did not finish. A reference it could not locate or could not check is never shown as a work that does not exist.
- A run without an editor package shows the findings recorded in `findings.jsonl`, keeping the latest row for each finding, and says that the editor did not finish.
- A run the starter stopped early, from a token ceiling, a timeout, a rate limit or a session error, has no `protocol.json` or `manifest.json`. It still opens, with its status, its cause and its recorded findings. Each finding's block hash pins the manuscript version. The panel shows no arm or reviewer count for it, because `read_run` takes those only from `protocol.json`.
- A run blocked at startup, or stopped before it imported the manuscript, has nothing to show. `serve` prints its status and cause and exits 1, and `report` still writes a report that says why.
- A run on a different manuscript version is refused. A symlinked run file is refused with an error, and files outside the review folder are never read.

Author decisions on a run are saved in `manuscript/decisions/run.json`. The review folder stays as the run wrote it.

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

Tests cover the run-folder reader, finished, stopped and startup-blocked runs in the viewer, the review and report commands against the installed engine with `claude` off `PATH`, Unicode anchors, source tampering, overlap rejection, revisions, Scaffold import and export, and Word review copies. No test starts a review.

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

After exporting a saved revision, run `python -m paper_workspace export-review WORKSPACE REVISION CLEAN_EXPORT NEW_OUTPUT`. The new package adds a Word copy with tracked changes from the immediate parent and comments for inherited open scientific questions. Exact paragraph matches are required for located comments. Uncertain locations remain in an appendix. The viewer offers the verified review copy beside the clean Word and PDF downloads.

See [Word review handoff](../docs/pra-word-review-handoff.md) for validation and current limits.
