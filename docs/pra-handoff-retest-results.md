# Exclusion handoff retest results

The fresh blinded evaluator preferred the updated post-debate review over both the saved single reviewer and the saved investigator selection. Debate restored the collection-order question, retained the four existing topics, and framed the recovered question more precisely around comparisons between feeding protocols. This supports the specific handoff fix on this known paper. It does not establish general superiority.

## Comparison

The Drosophila manuscript and evidence packet were unchanged. The initial single review and investigator output were reused exactly. Two new Sol medium calls produced the revised debate and a fresh anonymous evaluation. The debate received all four investigator findings, all three discarded hypotheses, and the investigation records. It did not receive the single review, prior grades, or an instruction to restore a particular question.

The evaluator saw three anonymously labeled selected reviews, the same source packet, and the same judging instructions as the preceding retest. The labels were randomized before generation. All outputs contained at most five scientific questions, with no proposed manuscript replacements. This test did not rerun discovery or evaluate the later deterministic reconciliation task inventory.

| Output | Selected questions | Evaluator preference |
| --- | ---: | --- |
| Saved single reviewer | 5 | Not preferred |
| Saved investigator selection | 4 | Not preferred |
| Updated debate | 5 | Preferred |

The evaluator selected an overall winner, not a full numerical ranking. Its rationale explicitly compared the single reviewer with the updated debate and described the investigator as omitting the order issue.

## What changed in debate

The recovered question asks whether the statement that effects were less pronounced in the parental feeding protocol was supported by a direct comparison between protocols. It identifies the fixed collection sequence and associated differences, while explicitly preserving valid diet contrasts within the parental protocol. It offers descriptive qualification if a direct comparison addressing order or carryover is unavailable.

The single reviewer covered the same broad topic. Its opening question about separating parental effects from collection order risked suggesting that randomized diet contrasts within the protocol were also invalid. Its final request did narrow the scope to comparisons between protocols. The evaluator preferred the updated debate's more consistent distinction. The advantage is therefore completeness relative to the investigator and precision relative to the single review, rather than a larger set of scientific topics than the single reviewer found.

All four original topics remained: SNP sufficiency, shared-vial dependence, transformed effect-size interpretation, and nutrient versus formulation attribution. Of 25 recorded components, 22 were preserved and three resolved. All 21 components from the original four findings were preserved. The three discarded hypotheses were handled explicitly:

- The sex-interaction concern was resolved using the distinction between lower-order and three-way tests.
- The collection-order note was partly resolved and partly restored. Standardized offspring medium answered the broad within-protocol objection, while the narrower cross-protocol question remained.
- The Results statement excluding egg laying from the significant focal interactions was resolved against S7.

This did not recover the separate Figure 2 caption discrepancy or the specific postembryonic-stage question missed in earlier discovery. The handoff fix preserves recorded concerns. It does not guarantee discovery of unrecorded ones.

## Evaluation and source audit

All 14 evaluator ratings passed exact-reference validation. For both the single reviewer and updated debate, the evaluator assigned four justified concerns and one justified clarification. The investigator received three concerns and one clarification. No finding was labeled unsupported, unverifiable, or excessive. These identical coarse ratings for the two five-question reviews mean the preference rests on scope and wording, not a demonstrated improvement in validated finding counts.

My unblinded source audit agrees that the recovered question is usefully narrower. The Methods describes the sequential collections from the same parents, and the Results describes parental variation as less pronounced. Asking whether that comparison is descriptive or statistically supported is proportionate. This does not establish that the paper's reported within-protocol effects are wrong.

There was one internal debate quotation failure. A calorie-related component quoted “do not correlate linearly” where the source says “do not linearly correlate.” The source supports the underlying observation, but the quotation is not exact. The normal debate validator correctly stopped completion. The original failure was retained, with no repaired model output or regeneration.

The planned blind evaluation then assessed the five selected questions separately as an exploratory comparison. Their manuscript anchors passed validation, and the recovered collection-order decision had exact source references. The review viewer explicitly marks the debate output as unvalidated. The experiment completed, but the debate has not passed the normal pipeline completion gate. All 144 software tests passed.

## Cost and limits

| New call | Input tokens | Output tokens | Observed total |
| --- | ---: | ---: | ---: |
| Updated debate | 95,780 | 8,332 | 104,112 |
| Blinded evaluator | 95,689 | 6,310 | 101,999 |
| Total | 191,469 | 14,642 | 206,111 |

Neither call reported cached input. There were no retries, paid credits, model fallbacks, or usage resets. The reused single review originally cost 95,224 observed tokens and the investigator 96,653. Those are historical costs, not additional spending in this retest. Generating the investigator plus this debate costs more than the single review, so this is not a compute-matched comparison. The CLI requested Sol, but its event stream does not independently expose the resolved model identity.

This is one known development paper with one same-family model judge. The judging system remains generous, and exact-reference checks cannot establish scientific correctness. No human-review overlap or independent expert validation was performed. A larger panel is not justified by this result alone. A small fresh-paper test of the complete workflow would be the next informative quality check.

Artifacts are preserved under `runs/pra-handoff-retest-v1`. The local review is available at [the retest workspace](http://127.0.0.1:38760/?review=after-debate).
