# Citation ledger fixture

`ledger.jsonl` and `stages.json` are written by `generate.py` through the engine's own citation ledger code, from the
test run's manuscript (`manuscripts.run_manuscript`). Nothing goes on the network. Every lookup goes to the
generator's opener, which answers from canned bodies and raises `OSError` for any other address, which the engine
records as a host that did not answer. `view.json` is what `paper_workspace.run_view.run_review` makes of this ledger
for the run panel, and the viewer test renders it.

The engine has no public ledger writer, so `generate.py` imports its internal ledger module. It is the one file in
this repo allowed to, and `test_engine_contract.PublicSurfaceTest` names it. No test runs the generator.

## The rows

1. `ledger.jsonl` is JSON lines, one object per line, append-only. The last line written for a `row_id` is that row.
2. A reference row has `kind` `reference` and `row_id` `ref:<reference_id>`, with its printed fields, and a
   `resolution` once it was looked up.
3. A use row has `kind` `use` and `row_id` `use:<document>:<piece first line>:<sentence>:<reference_id>`. It holds
   `document`, `line`, `end_line`, `start` and `end`, the span of its sentence as the engine placed it, with the
   sentence, the printed marker and how the marker was read. A marker that matches no reference has a
   `reference_id` of `null` and a row id ending in `unmatched-<marker>`.
4. `stages.json` holds one object per stage (`fill`, `resolve`, `judge`) with `done` and its counts.

## What the ledger holds

Six references and eight in-text uses, chosen so that every state the panel shows has a row. The paper prints its
citations as superscripts, and the reader wrote each marker as a link to its entry, so each use came from a reader
link and its marker is bare digits.

1. References: 1 and 5 found in an index, 2 a DOI the DOI resolver does not hold, 3 a title neither index lists,
   4 lookups that did not answer, 6 never looked up. Reference 5 is marked retracted and its printed year differs.
2. Uses: one each of supports, partly supports and does not support from `cite-1`, two cannot tell from `cite-2`
   with no source text, two never judged, and one marker `7` that links to a label no reference carries. The use
   of reference 4 was claimed by `cite-2` and then released, so its last row is open.
3. The abstract for reference 1 carries an `<img onerror>` tag and an instruction to the worker, and the one for
   reference 5 carries JATS markup. The quoted passage and the worker note carry markup too. The viewer must show
   them escaped and must not show the abstract.
4. The resolve and judge stages are not done, so the check is incomplete.

## Regenerating it

1. Run `python tests/fixtures/citations/generate.py tests/fixtures/citations` from the repo root with the pinned
   engine installed. It writes `ledger.jsonl`, `stages.json` and `view.json` over the files here.
2. Check the diff. The timestamps change on every run, and nothing else should change unless the engine or the
   generator did.
3. Run `python -m unittest discover -s tests -p 'test_run_view.py'` and `node tests/test_review_evidence_ui.js`.
