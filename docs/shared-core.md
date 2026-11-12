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
| `peerreviewagents.locate_run` and `NotARunFolder` | `run_view.locate` | No |
| `peerreviewagents.MANUSCRIPT_DIRECTORY` | `run_view.locate` | No |
| `peerreviewagents.import_paper(pdf, workspace, xml, ...)` | `paper-workbench import` | No |
| `peerreviewagents.verify_workspace` and `export_draft` | `verify`, the viewer, revisions and exports | No |

The app's `ENGINE_COMMANDS` must equal `peerreviewagents.CLI_COMMANDS`, and a test checks it, so an engine command added or renamed fails the app's tests until the app passes it on.

`paper-workbench review` hands its arguments to `review_main`, so a new engine option reaches the review and `paper-workbench review -h` names the program `paper-workbench review`. The per-slot model options `--reviewer-models`, `--specialist-model`, `--editor-model` and `--recorder-model` pass through this way, and a test checks that `review -h` lists them and that a blocked run's summary records them in `models_requested`. It prints the run summary and exits 0 when the review completed, 1 when it was blocked and 2 when it never started or an argument was bad. The default arm is `full-two-track`. Without `claude` on `PATH`, the starter writes `startup.json` and a blocked `runtime.json` and launches nothing.

`paper-workbench report` hands its arguments to `report_main`, and `paper-workbench report -h` names the program `paper-workbench report`. It renders `REVIEW.md` and `REVIEW.txt` for any run, a stopped or startup-blocked one included, and exits 0. It prints JSON with `status`, `cause`, `findings`, `publishable`, `not_publishable_reasons`, `problems` and one key per report path. A path that is not a run, or a symlinked run file, is named on stderr with exit 1.

The smaller helpers come from the public `peerreviewagents.workspace`:

| Import | Used by |
| --- | --- |
| `digest`, `read_json`, `write_json` | decisions, revisions, exports and tests |
| `save_review`, `normalize_review` | revisions, `revise` and tests |
| `words`, `text_of` | Paper Scaffold import and table structure |

No module under `paper_workspace/` or `tests/` imports `peerreviewagents.engine`, `.plugin`, `.cli` or `.runs`, or imports one of those modules from `peerreviewagents`. `PublicSurfaceTest` in `tests/test_engine_contract.py` fails if one comes back.

## What the app reads from a run

`run_view.py` calls `read_run` and never opens a run file itself. Nothing in the app writes to `RUN/review`. `read_run` refuses a symlink anywhere under the review folder, and the app shows that refusal as a plain error. It names any file it could not read in full in `problems`, and the run panel shows each one.

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

The engine writes `protocol.json` and `manifest.json` only when the run finishes or is marked blocked. A run the starter stopped early, from a token ceiling, a timeout, a rate limit or a session error, has neither. The viewer still opens it with its status, its cause and the findings in the ledger. Each finding's `block_sha256` then pins the manuscript version. Its arm and reviewer count are empty, because `read_run` takes them only from `protocol.json` or the plan. A run blocked at startup, or stopped before it imported the manuscript, has nothing to show, so `serve` prints its status and cause and exits 1.

A run written before engine commit bfc8aae recorded no model asked per slot, so each of its agent lines shows "model asked not recorded" and its `models_unverified` is empty. A slot that ran a different model family than it was asked is in `problems` and `not_publishable_reasons`, and the run panel shows it there.

Each finding keeps the annotation keys the viewer already used (`kind`, `block_id`, `quote`, `start`, `end`, `placement`, `comment`, `replacement`, `evidence_blocks`) and adds `finding_uid`, `slot`, `track`, `basis`, `basis_reason` and `escalate`. Body findings add `editor_reason`, `reviewers_raising` and `duplicate_uids`. Appendix findings add `editor_placement`, `duplicate_of` and `rebuttal_quote`.

The viewer keys a finding by `finding_uid`, because the engine's finding `id` can repeat across reviewers. `read_run` keeps one row per uid. If a uid is missing or malformed, the viewer numbers the findings instead.

## Versioning

Pin the engine commit, the arm and the literature cutoff for any comparison. The run's `protocol.json` records what the run was allowed to do, including the plugin and engine provenance hashes. A change to the plugin's agents, tools or editor rules is a new condition, even when no Python signature changes.

The 0.8 engine, with `ReviewRequest`, `run_review`, presets, policies and the Codex transport, is frozen at the PeerReviewAgents `v0.8.0` release. Study code written against it runs only there.
