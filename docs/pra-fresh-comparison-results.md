# Fresh manuscript comparison results

PRA found a concrete caption-to-table inconsistency that the three-pass single reviewer missed. It also raised a useful limitation of the sequential feeding design. The single reviewer found two other concerns that PRA missed. I would use the PRA review on this paper after narrowing a few categorical statements, but this is a promising development result, not established superiority.

One paper completed seven Sol medium calls. No second paper was run. No manuscript changes were applied.

## Design and source

The manuscript was [Dobson and colleagues, PLOS Biology, 2023](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3002218), an experimental Drosophila nutrition and genetics study not previously reviewed in the local workspaces. We used the published version, not the original submission. Possible training exposure remains unknown. Human-review overlap was not scored.

Both methods received the same manuscript prose, supplementary text, main figure packet, reported-table previews, full-table access, and Scaffold diagnostics. The source packet included the 28-page main PDF and eight supplementary figure PDFs. Ten reported-results spreadsheets were imported as cached table values. Raw-data spreadsheets and author analysis code were excluded.

The single reviewer made three sequential passes: initial review, source investigation, and self-revision with its own prior outputs and receipts. PRA made three calls: experiment planning, evidence interpretation, and fresh debate. This is not three independent reviewers. Both had a six-operation allowance beyond the common attached figures. The single reviewer used six operations. PRA executed four planned operations and used none of the two optional debate operations.

Call allowances were matched, but realized compute and output format were not fully matched. The baseline was instructed to return questions. The debate prompt permitted replacements and produced two scientific wording proposals. This affects the evaluator's preference for more actionable wording and must be controlled in the next comparison.

## What each method found

| Scientific topic | Single reviewer | PRA before debate | PRA after debate |
| --- | --- | --- | --- |
| Single-SNP causal sufficiency versus population association | Yes | Yes | Yes |
| Within-vial dependence in development analyses | Yes | Yes | Yes |
| Nutrient identity versus enriched diet formulations | Yes | Yes | Yes |
| Fixed order and pairing across feeding paradigms | No | Yes | Yes |
| Figure 2 caption versus reported fecundity tests | No | Yes | Yes |
| Whether mortality is localized to postembryonic stages | Yes | No | No |
| Interpretation of partial eta squared comparisons | Yes | No | No |

These are topic-level coverage observations, not seven independently validated errors. An ambiguity, an overstatement, and a demonstrated inconsistency are different outcomes.

The clearest PRA-specific gain is the caption discrepancy. The caption includes fecundity among significant interactions in the focal subset. The Results says all traits except egg laying. Original S7 spreadsheet cells F9 and F46 report the focal fecundity interaction at p = 0.12221 and p = 0.06683. The rows concern the same three-way test and support correcting the caption. This was independently checked against the source spreadsheet by the developer, without rerunning an analysis.

The fixed-order concern is also grounded in the stated design. It should qualify comparisons between feeding paradigms, not imply that all within-paradigm diet comparisons are invalid.

## What debate added

Debate retained all five scientific topics. Of 21 sentence components, it preserved 20 and resolved one question about which traits were significant by using S7. The concrete correction remained in the final review. No useful request was found to have disappeared in this audit.

The main benefit was refinement: specific locations for causal wording, a clearer restriction of the fixed-order concern to comparisons across paradigms, and a proposed caption correction. Debate did not discover a new scientific issue. It cost 97,809 observed tokens, so this result does not establish that the full debate call is worth its incremental cost.

The investigator also corrected a planning ambiguity. The planner described four genotype categories as lines. The investigator explicitly described the arithmetic result as 24 design combinations, not 24 independent biological replicates. A calculator receipt alone would not have made that interpretation valid.

## Automated evaluation and source audit

The anonymous evaluator preferred PRA after debate. All 15 ratings were nominally favorable, but only 13 passed reference validation. The valid ratings were five for the single reviewer and four for each PRA output. The two unscored ratings were both for the caption finding. They must not be counted as failed scientific findings or silently converted into validated model scores.

The evaluator reconstructed spreadsheet row labels and used literal escaped tab sequences rather than exact source quotations. It also attributed caption content to an image containing the figure, while the caption was on the following page. This illustrates why a plausible evaluation rationale cannot substitute for evidence verification. The separate developer source check confirmed the caption discrepancy using the original spreadsheet. Frozen automated grades remain unchanged.

My source audit is more cautious than the model grades:

- Vial dependence merits a consequential question. A density covariate does not itself document a treatment of residual within-vial correlation. The [survival documentation](https://stat.ethz.ch/R-manual/R-patched/library/survival/html/cluster.html) illustrates clustered uncertainty explicitly. This does not establish how much any reported estimate would change.
- The baseline's postembryonic concern is useful, but its suggestion that no intermediate measurements existed is too broad. The Methods mentions scoring pupation. The appropriate question is whether reported stage-specific observations support the exclusive interpretation.
- Effect-size interpretation needs statistical review. The [effectsize documentation](https://easystats.github.io/effectsize/reference/F_to_eta2.html) permits approximate F-based conversions in settings where sums of squares are difficult to obtain. A targeted question about this paper's degrees of freedom and interpretation is preferable to declaring the general approach invalid.
- Both methods should acknowledge the existing caloric-composition limitation more carefully. Repeating a caveat is useful only when tied to a remaining overstatement or unresolved scientific consequence.
- Causal language can reasonably be narrowed, but the quality of the population evidence and the limits of sufficiency claims need domain judgment. No experimental defect was independently established by this software check.

This was one same-family evaluator and an unblinded developer source audit. It is not independent expert validation. The 15-item blinded audit packet contains source passages, the source PDF, and a blank assessment form. It has not been sent to anyone.

## Cost and stopping

| Stage | Observed tokens | Cached input included |
| --- | ---: | ---: |
| Single initial review | 53,503 | 0 |
| Single investigation | 243,054 | 160,768 |
| Single self-revision | 333,890 | 213,248 |
| PRA planning | 58,053 | 0 |
| PRA evidence review | 93,965 | 0 |
| PRA debate | 97,809 | 0 |
| Anonymous evaluation | 89,389 | 0 |
| Total | 969,663 | 374,016 |

The initial 450,000-token launch stop halted after the three baseline calls at 630,447 observed tokens. A running call can cross that stop. A documented budget-only amendment, made before PRA generation or evaluation, raised the launch limit to 1.1 million to finish the same paper. No baseline calls were repeated and no second paper was added.

PRA generation used 249,827 observed tokens versus 630,447 for the three-pass single reviewer. This is not a claim of 2.5-fold credit savings. The baseline includes 374,016 cached input tokens. Excluding cached input, the observed totals are 256,431 for the baseline and 249,827 for PRA, and neither quantity by itself determines subscription charges.

The inexpensive initial single review already contained the same five scientific themes as its final review. The expensive extra passes did not add distinct themes. The next comparator should therefore include that efficient initial output, not assume that three passes are the best use of a single agent's budget. It did not receive a separate automated grade here.

Account usage was 17 percent before preparation, 18 percent after the baseline, and 19 percent at completion. These are shared account readings, not an attribution of all usage to this experiment. Preparation and orchestration are outside the table. No paid credits, fallback models, or usage reset were used. The CLI explicitly requested Sol, but the event stream did not independently expose the resolved model identity.

## Infrastructure limits and changes

Preflight removed eight peer-review subarticles bundled in the publisher XML. It also corrected Figure 2 delivery from its caption page 9 to actual figure page 8. These fixes occurred before inference. Mathematical layout remains a limitation: a fraction in the XML is flattened into adjacent text and requires the PDF for interpretation.

After freezing the completed run, source tools were changed to remove duplicate table arrays only when the complete identical rows already appear in the text. Source text, identifiers, and fingerprints remain unchanged. Offline replay reduced the largest observed tool response from 103,502 to 44,064 characters, a 57.4 percent reduction. This is a payload reduction, not a measured reduction in model tokens or a new quality result. All 128 tests passed.

The frozen run, source snapshots, raw responses, invalid grades, budget amendment, and original receipts remain available under `runs/pra-fresh-comparison-v1`.

## Next development priorities

1. Add explicit claim-to-caption-to-table reconciliation with source cell addresses and inherited header context. This targets the most concrete gain from this paper and the evaluator's failed quotations.
2. Add a check connecting claimed biological stage to the actual measured endpoints. That targets a consequential issue the single reviewer found and PRA missed.
3. Keep debate, but constrain it to evidence disputes, narrowed claims, and component preservation. Measure whether those changes justify its additional cost.
4. Enforce identical allowed output types in the comparison schema. Use compact evidence delivery and actual cost reporting, including the efficient initial single review.

No further model trial is needed to implement these changes. A second paper would become more informative after those specific fixes and a small independent audit of the disagreements.
