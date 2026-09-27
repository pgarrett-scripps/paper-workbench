# Revised debate: one-paper development result

September 24, 2026. The authorized small check completed with two Sol medium calls and 92,303 observed tokens. No reset, paid-credit purchase, new paper, or model retry was used.

The revised debate repaired the observed loss of a mechanistic concern on this development paper. One blinded automated judge preferred the revised review to both the saved old debate and saved ordinary review. That is a promising preference on one reused paper, not demonstrated superiority. Basic support ratings did not distinguish the conditions.

## What changed in the system

The versioned debate module preserves stable candidate IDs and every original sentence component. Each decision separates scientific status from editorial priority, records opposing arguments and the decisive question, and maps retained content to exact passages in the selected review. Resolved components need source quotations and a reason. Deferred components remain in the full ledger. Structural checks cannot establish whether a paraphrase preserves the scientific meaning.

The source-only tool profile adds explicit any/all literal search, claim-context retrieval, and experiment-context retrieval alongside original page viewing. Retrieval reports truncation, coverage, and provisional source mapping. It does not assert that a figure has been correctly linked to its methods. Tools cannot access external literature or run author code.

The reviewer received the full manuscript rather than only the old selected evidence packet. This trial therefore evaluates a bundle of preservation rules, source context, and tool-interface changes. It does not isolate the effect of any one change. The model made zero optional tool calls, so this run supplies no evidence that the new tools themselves improve quality.

The viewer and JSON export now expose the original component, its treatment, the author defense, the decisive question, and its final destination. Scientific assessment is labeled as a model judgment. One empty proposed replacement was converted to an author question by the existing edit guard. No replacement text was invented.

The revised workflow is an explicit development path. The generic earlier panel command has not silently switched to it. The original experiment and negative result remain unchanged.

## What the review did differently

| Issue | Earlier debate | Revised debate |
| --- | --- | --- |
| D6PK localization versus functional mechanism | Dropped the concern because parts of the paper call the mechanism plausible | Retained a request to keep model framing consistent across the paper, without making new experiments mandatory |
| Redistribution versus transcytosis | Retained | Retained alongside the distinct functional interpretation question |
| Figure-specific reporting and temporal uncertainty | Separate selected findings | Combined while retaining the requested sample structure and timing information |
| Acylation and lipid-interaction inference | Candidate omitted from the final five | Selected a request to distinguish indirect evidence from established biochemical claims |
| Membrane-anchor rescue | Retained with acknowledgment of convergent evidence | Retained with the acknowledgment and construct-level reporting requests |

All seven original candidates received decisions. Twenty-two of twenty-four sentence components were marked preserved and two resolved. These are accounting counts, not twenty-two independently valid findings or two corrected errors. One resolved component was an acknowledgment of supporting rescue evidence that also remains present in the final review. This reveals a limitation of sentence-level treatment labels.

The revised review contains five selected findings and 522 comment words. The ordinary review contains five findings and 420 words. The old debate contains five findings and 363 words. Grouping also packs more original issues into the same five headings. Neither the word budget nor the heading count establishes a matched amount of scientific content.

## Automated quality assessment

The evaluator received the same full manuscript and four-image union for all conditions, with no human reference list or workflow identities. It assessed support, consequence, specificity, proportionality, and an overall preference. All fifteen ratings passed the source-reference and accounting checks.

| Condition | Findings labeled justified concerns | Excessive requests identified | Unscored ratings |
| --- | ---: | ---: | ---: |
| Saved ordinary review | 5 | 0 | 0 |
| Saved old debate | 5 | 0 | 0 |
| Revised debate | 5 | 0 | 0 |

The judge preferred revised debate for combining broad scientific coverage with requests that often permit reporting or qualification. It considered the ordinary review similarly strong and sharper on D6PK causality. It considered the old debate sound but less comprehensive on mechanism and acylation.

This is one same-family model preference with fixed label positions. All conditions receiving the maximum support count indicates that this coarse metric has little discriminatory value here. The result is not an estimate of true precision, and it does not establish that the revised review contains fewer incorrect premises. No human-overlap result was recalculated or substituted for the earlier failed criterion.

## Orchestrator source audit

I inspected all five revised comments against their cited manuscript passages. The NPA distinction is grounded in the GCaMP figure legend and the stronger auxin wording in the Results summary. The mechanism comment now acknowledges the explicit model caveat while retaining a proportionate consistency request. The biochemical comment points to stronger statements in the abstract, headings, and conclusion alongside the prediction and perturbation experiments. These are recoveries or refinements of existing candidates, not newly discovered issues.

The figure-specific reporting requests remain identifiable after merging. The replacement guard left five author questions, all with exact source anchors. No author text was changed.

There are still judgment calls worth independent review. The rescue comment could overstate the need to qualify an inference supported by two different anchors. The phrase that the trajectories are not quantitatively assessable may be stronger than necessary, since the figures do show quantitative trajectories even though uncertainty and sampling are incompletely documented. These are reasons to examine proportionality, not mechanically endorse every comment.

I would currently choose the revised review over the old debate on this paper. Compared with the ordinary review, I see a useful tradeoff rather than a decisive scientific win. The revised review preserves more candidate detail but is longer. This audit is an informed source check by the system developer, not blinded expert validation.

## Usage and verification

| Call | Input tokens | Cached input | Output tokens | Observed total |
| --- | ---: | ---: | ---: | ---: |
| Revised debate | 36,035 | 0 | 8,610 | 44,645 |
| Blinded quality evaluation | 40,248 | 0 | 7,410 | 47,658 |
| Total | 76,283 | 0 | 16,020 | 92,303 |

The launch stop was 180,000 tokens. Preparation and orchestration usage are separate. Explicit CLI selection was Sol medium, while the event stream did not independently expose the resolved model identity. The debate took approximately 159 seconds and evaluation approximately 137 seconds.

Before inference, all 84 offline tests and the JavaScript syntax check passed. After completion, an additional regression case hardened the validator against overlapping occurrences of a source quote. The final suite contains 85 tests. The frozen trial code, raw outputs, and grades remain preserved. The post-run amendment records the validator change and adds no model calls. The local viewer loaded the five anchored questions and the new decision-ledger rendering.

## Next work without more model calls

A blinded audit packet is prepared with all fifteen findings, exact source passages, the clean PDF, and a blank assessment form. It contains no model grades or workflow key and has not been sent to anyone. This makes a limited independent review possible without another generation run.

The next substantive decision should be informed by that audit, especially the rescued mechanism concern, the breadth of the biochemical qualification, and the burden of the rescue-control request. A separate assessment of retained scientific components will be more informative than another maximum support score. A future live test should use an untouched paper, matched output scope, and a frozen evaluation plan. A larger benchmark remains premature.

The [revised review viewer](http://127.0.0.1:38754/?review=revised-debate) shows the full decision ledger. Code is in `paper_workspace/debate_revision.py` and `paper_workspace/debate_evidence.py`, with the bounded runner in `experiments/pra_debate_revision/`. Artifacts are under `runs/pra-debate-revision-v2`, including the frozen source snapshot, protocol, raw responses, evaluation, usage, source audit, and expert-audit packet.
