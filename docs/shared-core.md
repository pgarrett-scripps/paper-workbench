# Engine contract

PeerReviewAgents 0.9.0 runs the review. Paper Workbench starts one and reads the run folder it writes. This page lists what the app depends on, so an engine change that breaks the app can be found before it ships.

## Ownership

The engine owns ingest, source integrity, manuscript block identities, the review plugin and its agents, tool access, the finding ledger, the editor package and the run reports. The app owns manuscript presentation, author decisions, revision workflows and exports. The benchmark owns datasets, hidden answer keys, candidate selection, controlled conditions, anonymous judging, statistics and rankings.

Neither answer keys nor human evaluation labels belong in a review. The benchmark must give the review a manuscript-only PDF and keep grading inputs outside the run folder. Engine outputs are review artifacts, not scores.

## What the app calls

| Call | Used by | Model call | Planned public name |
| --- | --- | --- | --- |
| `peerreviewagents.plugin.starter.main(argv)` | `paper-workbench review` | Yes | `cli.main.review_main(argv, prog=)` |
| `peerreviewagents.cli.main.report(argv)` | `paper-workbench report` | No | `cli.main.report_main(argv)` |
| `peerreviewagents.import_paper(pdf, workspace, xml, ...)` | `paper-workbench import` | No | already public |
| `peerreviewagents.plugin.server.RUN_DIRECTORY` and `MANUSCRIPT_DIRECTORY` | `run_view.locate` | No | |
| `peerreviewagents.engine.annotations.verify_workspace` and `export_draft` | `verify`, the viewer and exports | No | top-level `verify_workspace` and `export_draft` |
| `peerreviewagents.engine.annotations` and `storage` | decisions, revisions and exports | No | |

`paper-workbench review` hands its arguments to the starter's own entry, so a new engine option reaches the review. The entry prints the run summary and exits 0 when the review completed, 2 when it never started and 1 otherwise. The default arm is `full-two-track`. Without `claude` on `PATH`, the starter writes `startup.json` and a blocked `runtime.json` and launches nothing. Until `review_main(argv, prog=)` lands, `paper-workbench review -h` names the program `peerreview review`.

`paper-workbench report` passes a finished run to `cli.main.report`. A run with no `protocol.json` has no review to report, so the app prints its recorded status and cause and exits 1 without calling the engine.

None of these entries, except `import_paper`, is part of the engine's public surface yet, which is `review`, `import_paper` and `write_reports`. The review and report calls sit only in `__main__.run_engine`, and the run reader only in `run_view.read_run`. `verify_workspace` and `export_draft` are imported in `__main__.py`, `server.py`, `revisions.py` and `scaffold_port.py`. The switch to the public names is a change to those imports.

## What the app reads from a run

`run_view.py` reads these files from `RUN/review`. It never writes to them. A symlinked run file is refused with an error rather than treated as missing.

| File | Keys the viewer reads |
| --- | --- |
| `startup.json` | `problems`, the start-up probe's failures |
| `runtime.json` | `status`, `blocked_reason`, `tokens_total`, `wall_seconds` |
| `progress.json` | `status`, `error`, `arm`, `reviewers`, `stages.missing`, `stages.none_found` |
| `protocol.json` | `arm`, `reviewers` |
| `manifest.json` | `paper_id`, `source_sha256`, checked against the manuscript |
| `editor-package.json` | `summary`, `findings`, `appendix`, `verdict`, `escalation_rulings`, `reviewer_provenance`, `findings_by_track`, `escalated_count`, `limitations`, `arm`, `reviewer_count`, `review_guard_status` |
| `findings.jsonl` | the latest row per `finding_uid`, shown when there is no editor package |
| `audit_<track>.md` | each specialist report, shown as plain text |

Any of `protocol.json`, `progress.json`, `runtime.json` or `startup.json` marks a run folder. The engine writes `protocol.json` and `manifest.json` only when the run finishes or is marked blocked. A run the starter stopped early, from a token ceiling, a timeout, a rate limit or a session error, has neither. The viewer still opens it with its status, its cause and its recorded findings. Without a manifest it checks each finding's `block_sha256` against the manuscript block instead. A run blocked at startup, or stopped before it imported the manuscript, has nothing to show, so `serve` prints its status and cause and exits 1.

`run_view.read_run(review)` returns `status`, `error`, `findings`, `manifest` and `audits` for any run, finished or not. It matches the engine's planned public `read_run(path)`, so the app switches to that with one import. `run_view.COMPLETE` holds the finished statuses until the engine publishes its status constants.

Each finding keeps the annotation keys the viewer already used (`kind`, `block_id`, `quote`, `start`, `end`, `placement`, `comment`, `replacement`, `evidence_blocks`) and adds `finding_uid`, `track`, `basis`, `basis_reason` and `escalate`. Body findings add `editor_reason`, `reviewers_raising` and `duplicate_uids`. Appendix findings add `editor_placement`, `duplicate_of` and `rebuttal_quote`.

The viewer keys a finding by `finding_uid`, because the engine's finding `id` can repeat across reviewers. If the uids repeat or are malformed, it numbers the findings instead.

## Versioning

Pin the engine commit, the arm and the literature cutoff for any comparison. The run's `protocol.json` records what the run was allowed to do, including the plugin and engine provenance hashes. A change to the plugin's agents, tools or editor rules is a new condition, even when no Python signature changes.

The 0.8 engine, with `ReviewRequest`, `run_review`, presets, policies and the Codex transport, is frozen at the PeerReviewAgents `v0.8.0` release. Study code written against it runs only there.
