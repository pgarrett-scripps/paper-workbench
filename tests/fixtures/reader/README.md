# Read manuscript fixture

`paper.json` is what `/api/paper` serves for a manuscript the engine's own Read stage wrote, under `read`, and for
the Scaffold port of that manuscript, under `ported`. `generate.py` writes it with `tests/reader_fixture.py`, which
runs `peerreviewagents.scripted_read`, the engine's public way to read a manuscript with a script in place of the
model. No model runs and nothing goes on the network. The viewer test renders both halves, and
`test_reader_fixture` builds it again and fails when it is not what the engine writes now.

## What the reader does

`reader_fixture.py` writes a three page PDF and splices the pieces a converter is known to leave behind into the
draft. The third page is turned a quarter turn. The pinned converter returns nothing from a turned page while
Poppler reads its words, so the import records it as a lost page. The script then:

1. views every page, repairs an equation with an unclosed brace and describes a figure, folding the paragraph of
   its axis numbers into the description
2. re-reads a paragraph of run-together cells as a kept sentence, a table and a caption, folding a stray heading
   into the table
3. cuts a stray phrase out of a paragraph, a prose-only re-read with every character the converter's
4. puts back the text of the lost page and seals with a note that carries markup

## What the manuscript holds

1. Three parts of one re-read with `original.part` and `original.of`. `original.absorbed` is on the table only,
   the first part that is not prose.
2. A cut paragraph that is part 1 of 1, and a figure description with its own `absorbed`.
3. `ai_read` with `read` true, the note, the lost page and the lines its added piece became, and `gone`, which
   counts the two absorbed pieces. The viewer does not show `gone`.
4. A note with its whitespace folded to single spaces, as the engine stores every note.
5. The port names the reader as `ai_model`, has `read` false and no lost page, and keeps every `original` whole.

## Regenerating it

1. Run `python tests/fixtures/reader/generate.py tests/fixtures/reader` from the repo root with the pinned engine and
   Poppler installed.
2. Check the diff. Nothing changes unless the engine, the port or the script did.
3. Run `python -m unittest discover -s tests -p 'test_reader_fixture.py'` and `node tests/test_review_evidence_ui.js`.
