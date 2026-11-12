# Engine contract

PeerReviewAgents 0.9.0 runs the review. Paper Workbench starts one and reads the run folder it writes. This page lists what the app depends on, so an engine change that breaks the app can be found before it ships.

## Ownership

The engine owns ingest, source integrity, manuscript block identities, the review plugin and its agents, tool access, the finding ledger, the editor package and the run reports. The app owns manuscript presentation, author decisions, revision workflows and exports. The benchmark owns datasets, hidden answer keys, candidate selection, controlled conditions, anonymous judging, statistics and rankings.

Neither answer keys nor human evaluation labels belong in a review. The benchmark must give the review a manuscript-only PDF and keep grading inputs outside the run folder. Engine outputs are review artifacts, not scores.

## What the app calls

| Call | Used by | Model call |
| --- | --- | --- |
| `peerreviewagents.review(pdf, out, reviewers=, arm=, ...)` | `paper-workbench review` | Yes |
| `peerreviewagents.import_paper(pdf, workspace, xml, ...)` | `paper-workbench import` | No |
| `peerreviewagents.plugin.starter.build_parser()` and `exit_code(summary)` | `paper-workbench review` options and exit status | No |
| `peerreviewagents.cli.main.report(argv)` | `paper-workbench report` | No |
| `peerreviewagents.plugin.server.RUN_DIRECTORY` and `MANUSCRIPT_DIRECTORY` | `run_view.locate` | No |
| `peerreviewagents.engine.annotations` and `storage` | the viewer, decisions, revisions and exports | No |

`review` returns the run summary and exits 0 when the review completed, 2 when it never started and 1 otherwise. The default arm is `full-two-track`. Without `claude` on `PATH`, `review` returns a blocked summary at the `startup` stage and launches nothing.

`starter.build_parser`, `starter.exit_code`, `cli.main.report` and the two directory names are not part of the engine's public surface, which is only `review`, `import_paper` and `write_reports`. The app uses them so its `review` command takes exactly the options of `peerreview review`.

## What the app reads from a run

`run_view.py` reads these files from `RUN/review`. It never writes to them and never follows a symlink.

| File | Keys the viewer reads |
| --- | --- |
| `protocol.json` | `arm`, `reviewers`. Its presence marks a run folder |
| `manifest.json` | `paper_id`, `source_sha256`, checked against the manuscript |
| `progress.json` | `status`, `error`, `stages.missing`, `stages.none_found` |
| `runtime.json` | `status`, `blocked_reason`, `tokens_total`, `wall_seconds` |
| `editor-package.json` | `summary`, `findings`, `appendix`, `verdict`, `escalation_rulings`, `reviewer_provenance`, `findings_by_track`, `escalated_count`, `limitations`, `arm`, `reviewer_count`, `review_guard_status` |
| `findings.jsonl` | every recorded finding, shown when there is no editor package |
| `audit_<track>.md` | each specialist report, shown as plain text |

Each finding keeps the annotation keys the viewer already used (`kind`, `block_id`, `quote`, `start`, `end`, `placement`, `comment`, `replacement`, `evidence_blocks`) and adds `finding_uid`, `track`, `basis`, `basis_reason` and `escalate`. Body findings add `editor_reason`, `reviewers_raising` and `duplicate_uids`. Appendix findings add `editor_placement`, `duplicate_of` and `rebuttal_quote`.

The viewer keys a finding by `finding_uid`, because the engine's finding `id` can repeat across reviewers. If the uids repeat or are malformed, it numbers the findings instead.

## Versioning

Pin the engine commit, the arm and the literature cutoff for any comparison. The run's `protocol.json` records what the run was allowed to do, including the plugin and engine provenance hashes. A change to the plugin's agents, tools or editor rules is a new condition, even when no Python signature changes.

The 0.8 engine, with `ReviewRequest`, `run_review`, presets, policies and the Codex transport, is frozen at the PeerReviewAgents `v0.8.0` release. Study code written against it runs only there.
