# Engine contract

PeerReviewAgents 0.9.0 runs the review. Paper Workbench starts one and reads the run folder it writes. This page lists what the app depends on, so an engine change that breaks the app can be found before it ships.

## Ownership

The engine owns ingest, source integrity, manuscript block identities, the review plugin and its agents, tool access, the finding ledger, the editor package and the run reports. The app owns manuscript presentation, author decisions, revision workflows and exports. The benchmark owns datasets, hidden answer keys, candidate selection, controlled conditions, anonymous judging, statistics and rankings.

Neither answer keys nor human evaluation labels belong in a review. The benchmark must give the review a manuscript-only PDF and keep grading inputs outside the run folder. Engine outputs are review artifacts, not scores.

## What the app calls

Every review, report and run-reading call goes through the engine's public surface:

| Call | Used by | Model call |
| --- | --- | --- |
| `peerreviewagents.review_main(argv, prog='paper-workbench review')` | `paper-workbench review` | Yes |
| `peerreviewagents.report_main(argv, prog='paper-workbench report')` | `paper-workbench report` | No |
| `peerreviewagents.read_run(path)` | `run_view.run_review` | No |
| `peerreviewagents.read_citation_ledger(review, source_text=False)` | `run_view.citation_view` | No |
| `peerreviewagents.locate_run` and `NotARunFolder` | `run_view.locate` | No |
| `peerreviewagents.MANUSCRIPT_DIRECTORY` | `run_view.locate` | No |
| `peerreviewagents.import_paper(pdf, workspace, xml, ...)` | `paper-workbench import` | No |
| `peerreviewagents.verify_workspace` and `export_draft` | `verify`, the viewer, revisions and exports | No |

The app's `ENGINE_COMMANDS` must equal `peerreviewagents.CLI_COMMANDS`, and a test checks it, so an engine command added or renamed fails the app's tests until the app passes it on.

`paper-workbench review` hands its arguments to `review_main`, so a new engine option reaches the review and `paper-workbench review -h` names the program `paper-workbench review`. The per-slot model options `--reviewer-models`, `--specialist-model`, `--editor-model` and `--recorder-model` pass through this way, and a test checks that `review -h` lists them and that a blocked run's summary records them in `models_requested`. So do `--citation-workers N`, from 0 to 12 with a default of 4, and `--citation-worker-model`, which `PEERREVIEW_CITATION_WORKER_MODEL` also sets. A test checks that a blocked `full-two-track` run asks for the six specialist slots `spec-stats`, `spec-figures-tables`, `spec-methods-reporting`, `spec-citations`, `spec-numbers` and `spec-field` and one `cite-N` slot per worker, and that 13 workers is refused before the run folder is made. It prints the run summary and exits 0 when the review completed, 1 when it was blocked and 2 when it never started or an argument was bad. The default arm is `full-two-track`. Without `claude` on `PATH`, the starter writes `startup.json` and a blocked `runtime.json` and launches nothing.

`paper-workbench report` hands its arguments to `report_main`, and `paper-workbench report -h` names the program `paper-workbench report`. It renders `REVIEW.md` and `REVIEW.txt` for any run, a stopped or startup-blocked one included, and exits 0. It prints JSON with `status`, `cause`, `findings`, `publishable`, `not_publishable_reasons`, `problems` and one key per report path. A path that is not a run, or a symlinked run file, is named on stderr with exit 1.

The smaller helpers come from the public `peerreviewagents.workspace`:

| Import | Used by |
| --- | --- |
| `digest`, `read_json`, `write_json` | decisions, revisions, exports and tests |
| `save_review`, `normalize_review` | revisions, `revise` and tests |
| `words`, `text_of` | Paper Scaffold import and table structure |

No module under `paper_workspace/` or `tests/` imports `peerreviewagents.engine`, `.plugin`, `.cli` or `.runs`, or imports one of those modules from `peerreviewagents`. `PublicSurfaceTest` in `tests/test_engine_contract.py` fails if one comes back.

## What the app reads from a run

`run_view.py` calls `read_run`, and `read_citation_ledger` for the citation rows. It opens no run file itself. The section on the citation ledger below says how. Nothing in the app writes to `RUN/review`. `read_run` refuses a symlink anywhere under the review folder, and the app shows that refusal as a plain error. It names any file it could not read in full in `problems`, and the run panel shows each one.

| `read_run` key | What the viewer does with it |
| --- | --- |
| `body`, `appendix`, `findings_source` | the findings, body first, and whether the editor wrote its package |
| `identity.paper_id`, `identity.source_sha256`, each finding's `block_sha256` | the check that the run reviewed this manuscript version |
| `status`, `complete`, `cause`, `note`, `problems`, `publishable` | the run panel's status and warnings, and the summary of a run with no editor package |
| `not_publishable_reasons` | one run panel warning per reason, when `publishable` is false |
| `summary`, `verdict`, `escalations`, `escalation_rulings`, `limitations`, `guard_status`, `counts` | the summary and the run panel |
| `identity.arm`, `identity.reviewers`, `identity.workflow_version` | the run panel |
| `counts.quarantined` | whether a `complete-without-findings` run had nothing raised or had everything held by the guard |
| `stages.missing`, `stages.none_found`, `runtime.tokens_total`, `runtime.wall_seconds` | the run facts |
| `agents` | one line per agent, with its tokens, tool calls and state, and the tasks in `labels` when an agent ran more than one |
| `agents[].assigned_model`, `agents[].model` | each agent line shows both, as "model asked" and "model ran". A `model` of `None` shows as "model ran not recorded" and is never filled from `assigned_model` |
| `identity.models_unverified` | a run panel note naming the slots with a model asked and no model ran, when the list is not empty |
| `reports.audits` | each specialist report, read as plain text up to 400,000 bytes |
| `agents[].role` | a `citation-worker` line says the worker writes no findings |
| `citations.enabled` | whether the run panel has a citation section. A run whose plan has no citations lane has none |
| `citations.ledger` | whether the run has a ledger. `None` on a planned lane means the run wrote no ledger, so there are no ledger counts, and the engine's problem line says so |
| `citations.counts` | one line for the references and one for the uses. `resolved`, `not_found`, `not_located`, `could_not_check` and `unresolved` each keep their own count and are never added together. Empty `counts` with a ledger means the ledger could not be read, and the panel shows no rows |
| `citations.complete`, `citations.problems` | a line saying the check did not finish, and each problem line once, in the citation section. The engine puts those lines in `problems` as well, and the run panel leaves them out there |

The engine writes `protocol.json` and `manifest.json` only when the run finishes or is marked blocked. A run the starter stopped early, from a token ceiling, a timeout, a rate limit or a session error, has neither. The viewer still opens it with its status, its cause and the findings in the ledger. Each finding's `block_sha256` then pins the manuscript version. Its arm and reviewer count are empty, because `read_run` takes them only from `protocol.json` or the plan. A run blocked at startup, or stopped before it imported the manuscript, has nothing to show, so `serve` prints its status and cause and exits 1.

A run written before engine commit bfc8aae recorded no model asked per slot, so each of its agent lines shows "model asked not recorded" and its `models_unverified` is empty. A slot that ran a different model family than it was asked is in `problems` and `not_publishable_reasons`, and the run panel shows it there. A `cite-N` citation worker holds no review, so its mismatch is a `problems` line only and the run stays publishable.

Each finding keeps the annotation keys the viewer already used (`kind`, `block_id`, `quote`, `start`, `end`, `placement`, `comment`, `replacement`, `evidence_blocks`) and adds `finding_uid`, `slot`, `track`, `basis`, `basis_reason` and `escalate`. Body findings add `editor_reason`, `reviewers_raising` and `duplicate_uids`. Appendix findings add `editor_placement`, `duplicate_of` and `rebuttal_quote`.

The viewer keys a finding by `finding_uid`, because the engine's finding `id` can repeat across reviewers. `read_run` keeps one row per uid. If a uid is missing or malformed, the viewer numbers the findings instead.

## The citation ledger

Engine commit f693b56 plans six specialist lanes, `stats`, `figures-tables`, `methods-reporting`, `citations`, `numbers` and `field`. The lane that checks the manuscript's numbers against each other is `numbers`, with slot `spec-numbers`, report `audit_numbers.md` and finding track `numbers`. The app keeps no other name for it. The citations lane fills `review/citations/ledger.jsonl`, an append-only table of the reference list and every in-text use, with `citations/lookups/` and `citations/stages.json` beside it, and the writers' lock files `rows.lock` and `stages.lock`. The app never lists that folder. Citation workers `cite-1` to `cite-N` judge each use against the source text the ledger fetched. They write no findings.

The panel takes its counts and problem lines from `read_run` and its rows from `read_citation_ledger`, which gives the last row for each `row_id`. It asks for the rows only when `read_run` could count the ledger. It calls the reader with `source_text=False`, so the fetched abstract and full text stay in the run folder and each reference row says only whether a worker had them. The panel never showed that text, and the passage a worker quoted is on the use row. The reader gives the rows in reading order, with the numbers in a `row_id` compared as numbers, so `ref:r2` comes before `ref:r10`. The panel keeps that order and only moves the uses a reader should check first to the top. Rows are at most 500 of each kind and each text at most 1,500 characters, so the page stays small whatever the ledger's size.

The run panel lists the references that need a second look and every in-text use, the ones a reader should check first at the top, at most 500 of each. A reference is found in an index, has a DOI the DOI resolver does not hold, has a title neither Crossref nor Europe PMC lists, could not be checked because the lookups did not answer, or was never looked up. The panel never turns a title it could not locate, or a lookup that did not answer, into a claim that a work does not exist. A use's sentence and marker are as the paper prints them, so a superscript citation has a bare-digit marker such as `3` and a bracketed one has `[3]`. The panel shows the marker as the row gives it and adds no brackets. The only derivation the panel reads is `marker-author-year-ambiguous`, which makes an unmatched use say it matches more than one entry. Every other derivation, the `reader-link` forms included, shows the same way. A use shows its sentence, the worker's verdict (supports, partly supports, does not support or cannot tell), the source passage the worker quoted and its note. Passages and notes came from the internet or from a model, so the panel shows them escaped as quoted text, cuts each at 1,500 characters and links only `https` URLs. The abstract a worker read stays in the run folder.

A ledger that is present and cannot be read gives one citation problem line that names `review/citations/ledger.jsonl` and why. The counts are empty, the panel shows that line and no rows, and the run stays publishable. A torn last line is counted in `unreadable_rows` and the rows before it stand.

`tests/fixtures/citations` holds a ledger written by hand in the shape the engine documents in `docs/INTEGRATIONS.md`, and its README says what each row is for. No test imports the engine's private ledger module.

## Versioning

Pin the engine commit, the arm and the literature cutoff for any comparison. The run's `protocol.json` records what the run was allowed to do, including the plugin and engine provenance hashes. A change to the plugin's agents, tools or editor rules is a new condition, even when no Python signature changes.

The 0.8 engine, with `ReviewRequest`, `run_review`, presets, policies and the Codex transport, is frozen at the PeerReviewAgents `v0.8.0` release. Study code written against it runs only there.
