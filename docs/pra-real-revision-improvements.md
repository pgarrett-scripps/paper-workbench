# Completed manuscript workflow fixes

The issues exposed by the real manuscript trial were fixed and checked on the same source without another review-model call. This is engineering validation, not a new review-quality comparison.

## Result

| Check | Earlier trial | Completed continuation |
| --- | --- | --- |
| Editable prose paragraphs | 7 of 34 | 34 of 34, including abstract and citation-bearing prose |
| Applied copyedits | 2 | All 3 previously proposed edits |
| Scientific questions still open | 2 | 2 |
| Structured tables in Word and PDF | 0 | 9 |
| Embedded main figures | 0 | 4 extracted from publisher PDF image objects |
| Embedded supplementary figures | 0 | 5 |
| Additional review-model calls | Not applicable | 0 |

The final workspace is `runs/pra-real-revision-v2/workspace-complete`, with active draft `revised-1`. The final export directory is `exports/revised-1-final`. Earlier trials, model outputs, intermediate exports, original manuscripts, and supplements are preserved.

The viewer at <http://127.0.0.1:38757/?draft=revised-1> exposes verified Word and PDF downloads, displays tables with their original cell merges, and shows the open scientific questions alongside the revised draft. The original review and complete debate are available on the original draft under `replay-full`. This replay retains prior findings, counterevidence, and component decisions and is explicitly labeled as using no new inference.

## Underlying changes

The source editor supports exact plain-text spans and encoded string spans. It validates the original decoded text and file hash, applies accepted edits, encodes literal manuscript text safely, and then requires the reimported manuscript to match the approved text projection exactly. Changes to numeric bracket citations and native citation keys are rejected, including partial-marker edits and reordered keys. Complex native source syntax remains locked.

The grammar guard now recognizes association inflections as the same protected concept. The previously held correction from associate to associated passes. Negation, selected uncertainty terms, inference terms, and numerical values remain protected. This does not expand the default automatic whitelist or establish semantic equivalence for arbitrary edits.

The port preserves original sections, document identities, reference records, and supplementary table rows. The table display recovers actual horizontal and vertical cell spans from the original Word XML. It requires an exact text match and leaves uncertain geometry as a plain-text fallback.

Word export embeds source tables and figures. Main figure extraction requires exactly one caption and one large RGB JPEG object on the recorded PDF page. Ambiguous cases retain the source pages instead of guessing an image association. The four extracted figures were inspected against the original pages. Export records include source and extracted-file hashes. These are publisher-PDF images, not claims to have recovered author-original graphics.

The PDF is rendered from the same rich Word document. The compact Typst source build remains separately available as `source-build.pdf`. Exact flattened table duplicates are removed only after matching the embedded source tables. A pagination fix removes the extra blank page after S6 Table. Downloads are bound to the selected manuscript version and checked against recorded file hashes before serving.

## Validation

- All 159 expected source blocks appear in the Word XML after the three accepted edits.
- All 150 non-table blocks appear in extracted PDF text. Table text is validated separately because line wrapping and column ordering change text extraction.
- All nine Word tables preserve source cell text, row order, and horizontal and vertical merge spans.
- Every expected numeric literal from the nine source tables appears on the corresponding PDF table pages.
- The final PDF has 48 pages with no empty text pages. Figure and table pages were visually inspected. The final S6 and S7 pages were rechecked after the pagination correction.
- The original manuscript, all citation IDs, and all text outside the three accepted replacements are unchanged.
- All 119 unit tests pass. Local HTTP checks cover revision creation, rollback, version-bound downloads, and changed-file rejection. Browser checks confirm nine structured tables, visible open questions, successful Word and PDF downloads, and no JavaScript errors.
- The bounded offline loop stops with no further eligible copyedits. It does not treat the two scientific questions as resolved.

The reusable offline audit is:

```bash
python -m experiments.pra_real_revision.verify_revision \
  runs/pra-real-revision-v2/workspace-complete revised-1 \
  runs/pra-real-revision-v2/workspace-complete/exports/revised-1-final \
  --output runs/pra-real-revision-v2/final-fidelity-audit.json
```

Use an environment with the document export dependencies. This audit makes no model calls.

## Scope

The output is a usable manuscript review packet with editable prose and preserved evidence. It is not a reconstruction of the publisher's original layout or a journal submission template. The figure and table adapters currently support the supplied source formats and naming conventions, with explicit fallbacks for unsupported cases. General native Typst equations and complex calls remain protected.

These changes remove the concrete workflow blockers found in the trial. They do not change the previous scientific-review benchmark results or establish superiority over a single reviewer. That assessment still requires a matched comparison and independent judgment of supported findings and harmful edits.
