# Citation ledger fixture

`ledger.jsonl` and `stages.json` are written by hand, in the shape PeerReviewAgents documents in
`docs/INTEGRATIONS.md` under "Building a ledger fixture". The engine exports no fixture writer, and no file in this
repo imports `peerreviewagents.engine`. `view.json` is what `paper_workspace.run_view.run_review` makes of this
ledger for the run panel, and the viewer test renders it.

## The format

1. `ledger.jsonl` is JSON lines, one object per line, append-only. The last line written for a `row_id` is that row.
2. A reference row has `kind` `reference`, `row_id` `ref:<reference_id>`, `reference_id`, `label`, `raw` and
   `printed`, and a `resolution` object once it was looked up.
3. A use row has `kind` `use`, `row_id` `use:<block>:<sentence>:<reference_id>`, `reference_id`, `sentence`,
   `marker` and `derivation`, and a `verdict` once a worker judged it. The sentence is as the paper prints it, with
   no link markup. The marker is as printed too, bare digits for a superscript citation and `[12]` inside a
   bracketed run. A marker that matches no reference has a `reference_id` of `null` and a row id ending in
   `unmatched-<marker>`.
4. `stages.json` holds one object per stage (`fill`, `resolve`, `judge`) with `done` and its counts. The engine reads
   `complete` and `lookups` from it, and `remaining`, `retry_after` and `unchecked_reason` from the resolve stage.

## What the ledger holds

Six references and eight in-text uses, chosen so that every state the panel shows has a row. The paper prints its
citations as superscripts, so each use came from a reader link (`reader-link`) and its marker is bare digits.

1. References: 1 and 5 found in an index, 2 a DOI the DOI resolver does not hold, 3 a title neither index lists,
   4 lookups that did not answer, 6 never looked up. Reference 5 is marked retracted and its printed year differs.
2. Uses: one each of supports, partly supports and does not support from `cite-1`, two cannot tell from `cite-2`
   with no source text, two never judged, and one marker `7` that the reader linked to a label no reference row
   carries (`reader-link-unmatched`). The use of reference 4
   was claimed by `cite-2` and then released, so its last row is open.
3. The abstract for references 1 and 5 is in the resolution, and the one for reference 1 carries an `<img onerror>`
   tag and an instruction to the worker. The quoted passage and the worker note carry markup too. The viewer must
   show them escaped and must not show the abstract.
4. The resolve and judge stages are not done, so the check is incomplete. The resolve stage stopped with 2 rows
   still owed a lookup and no reason recorded, so the engine adds its line saying the run never took them up again.

## Changing it

1. Edit `ledger.jsonl` or `stages.json` by hand. Append a line to change a row, as the engine does.
2. Run `tests/test_run_view.py`. If the panel view changed, print `run_review(...)['run']['citations']` for the
   `make_run` folder with `json.dumps(view, indent=1, ensure_ascii=False)` plus a newline, and save it as
   `view.json`.
3. Run `node tests/test_review_evidence_ui.js`, which renders `view.json`.
