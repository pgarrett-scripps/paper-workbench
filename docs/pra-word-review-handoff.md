# Word review handoff

The revision workflow now exports a Word review copy with real tracked changes and native comments. This closes the gap between located browser feedback and a document an author can inspect in Word. The clean manuscript and its PDF remain available beside the review copy.

## Behavior

`export-review` takes a workspace, a saved revision, a verified clean export, and a new output directory. It verifies the draft binding and the clean export file hashes before producing output. It does not call a review model or modify the manuscript sources.

Tracked differences compare the immediate parent with the selected revision. Accepting all changes must recover the clean manuscript text. Rejecting changes in every edited paragraph must recover the parent text. Formatting on retained and inserted text follows the clean Word runs. Deleted text uses the formatting at its insertion point. Complex changed paragraphs containing fields, links, drawings, or bookmarks fail without publishing a partial package.

Open scientific questions come from the inherited issue ledger. A comment attaches to a full paragraph only when its block fingerprint and exact text match the current Word document. The exact quoted passage appears inside the comment. Stale or ambiguous questions appear in an unlocated questions appendix with a location explanation. Scientific questions are not automatically resolved by a wording change.

The output contains `review.docx` and `word-review.json`, alongside the original clean export. Its manifest records all file hashes. The viewer exposes the review copy through a download that checks both the selected draft and file integrity.

## Real manuscript check

The existing TDP-43 manuscript revision produced tracked changes in three paragraphs and comments for both open scientific questions. No questions needed the unlocated appendix. No additional review-model calls were made.

Validation included 125 unit tests, HTTP checks for mismatched drafts and changed downloads, and a browser check of the real download. The clean manuscript fidelity audit passed again, including the existing figure and table checks.

Both Word files rendered to 48 pages. Pixel comparison found 43 identical pages. The five differing pages were 6, 10, 11, 13, and 14. Those pages were inspected at readable resolution, with all pages also inspected in contact sheets. Native comment relationships, bodies, and range markers were checked structurally because headless PDF rendering does not display comment text reliably.

## Reproduce

Run with Python that provides lxml and the existing document export dependencies:

```bash
python -m paper_workspace export-review \
  runs/pra-real-revision-v2/workspace-complete \
  revised-1 \
  runs/pra-real-revision-v2/workspace-complete/exports/revised-1-final \
  runs/pra-real-revision-v2/workspace-complete/exports/revised-1-review
```

An existing output directory is never overwritten. Choose a new directory when repeating the command.

## Limits

The review copy tracks one revision step. It exports inherited open questions, not arbitrary new comments from a later review session. Editing or replying in Word does not yet update the workspace. Citation protection and source validation still happen when a source revision is created. Word export does not independently assess scientific correctness.

This engineering check adds no evidence that PRA outperforms a single reviewer. The earlier review findings and benchmark limitations remain unchanged.
