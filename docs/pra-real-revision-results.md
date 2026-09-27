# Real manuscript revision trial

One experimental biology manuscript completed source import, a Sol review, a separate Sol debate, explicit editorial decisions, an immutable source revision, and PDF and Word export. Two small copyedits were applied. Both scientific questions remain open. This establishes a working revision path, not superior review quality or readiness for automatic scientific rewriting.

The local trial is `runs/pra-real-revision-v1`. The viewer is available while its server runs at <http://127.0.0.1:38756/?draft=original&review=after-debate>. Select `reviewed-1` to inspect the revised text and inherited issue ledger.

## Input and budget

The manuscript is *TDP-43-mediated alternative polyadenylation is associated with a reduction in VPS35 and VPS29 expression in frontotemporal dementia*. We reused the local publisher XML, original PDF, and supplements from `runs/pra-workspace-pilot-v1/paper-v2`. This is a development manuscript, not an unseen evaluation case. Human reviews and earlier model reviews were excluded from the new calls.

The runner requested `gpt-5.6-sol` at medium reasoning for exactly two calls. The first proposed scientific questions and copyedits. A fresh session challenged them against the source. Four original figure pages were supplied to both calls. Total observed usage was 98,336 tokens. The runner limited calls to two and checked its usage threshold between calls. It did not redeem a reset or use a paid API. Runtime events did not independently report the resolved model identity.

This was one reviewer followed by debate, not three independent reviewers. No additional inference was used to tune the results.

## Findings and decisions

| Finding | Outcome |
| --- | --- |
| Consistency of causal language in the proposed APA and retromer pathway | Kept open. Debate noticed that the Discussion and Figure 4 already call this a model, narrowing the request to consistent claim strength elsewhere. |
| Adjustment of case-control APA comparisons for covariates | Kept open. The reported mean ages differ and the group comparisons are unadjusted. The related request about tissue heterogeneity is partly redundant because the manuscript already discusses it. |
| Change “was found to associate” to “was found to be associated” | Still proposed. The source guard treats the inflection change as a changed inference term. This appears to be an overly conservative grammar restriction. |
| Add the missing “of” in “as a measure of 3′ UTR lengthening” | Applied. |
| Remove the unnecessary “as” in “are as described in S2 Table” | Applied. |

The default automatic whitelist would accept none of these proposals. The two accepted copyedits instead used explicit orchestrator decisions after source inspection and debate. The global automatic policy was not broadened. Scientific questions were not answered on the authors' behalf, and no analysis was rerun.

All five findings survived debate. The component audit accounted for 12 components and passed exact-quotation and structural checks. That audit cannot establish scientific correctness. The two scientific questions are plausible requests for clarification, not independently verified defects. Our editorial assessment is not an expert validation study.

## Integrity and export checks

- All 159 original text blocks were found in the initial reading-copy PDF.
- All 159 expected blocks, with the two accepted replacements, were found in the revised PDF and Word XML. Checks normalized whitespace and Unicode. PDF extraction used `pdftotext -layout` to retain line-final source hyphens.
- Exactly two manuscript block files changed. Original and revised workspace integrity checks passed.
- The revised ledger retains five findings, including both open scientific questions and the held copyedit.
- The original PDF, XML, and supplements remain available separately.
- All 105 unit tests passed. The live viewer checks are recorded in `viewer-audit.json`.

The PDF has 17 pages and the Word render has 30 pages. Contact-sheet inspection covered every exported page. It showed readable prose but also flattened tables and absent figure images. This was an overview inspection, not full-resolution publication layout approval. These are reading copies, not submission-ready exports. Text matching does not verify table structure, figure fidelity, or scientific meaning.

## What the trial exposed

The port preserves reading context and reference identities, but only 7 of 34 prose paragraphs are editable. Complex citations and markup conservatively lock the remaining paragraphs. The 67 reference records are inherited from the verified source workspace. Their presence does not establish citation support or a reconstructed native bibliography.

The new `port-scaffold` command makes this conversion reusable. It preserves abstract text, original block identities, page locations, references, and the original PDF. It does not recover the authors' original editable source or layout.

A post-run engineering change labels inherited citation records correctly in the Scaffold advisory report. The frozen review requests, raw responses, source snapshots, and trial manifest were preserved. The amendment hash is recorded in `results.json`.

## Next priorities

1. Support exact prose edits around protected inline citations, with tests that citation keys, numbers, and nearby scientific wording remain unchanged. The low editable coverage is the clearest product bottleneck.
2. Preserve table structure and figure placement through export. Continue using the original PDF and supplements as the authoritative visual source until that gate passes.
3. Investigate the grammar guard's inflection false positive with focused fixtures, without relaxing scientific qualification protection generally.
4. Once those engineering gaps are closed, run a small matched quality comparison with equal source access and budget. Measure supported findings, redundant requests, harmful edits, and author effort. This trial provides no new human-overlap score or evidence that PRA beats a single reviewer.

The bounded trial stopped after two calls. A larger panel was not launched.
