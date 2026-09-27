# Claim reconciliation retest results

The changes improved source traceability and matched the output formats, but this trial did not improve PRA's review quality. The anonymous evaluator preferred the single reviewer. I also prefer its selected review on this paper, with narrower wording for a few claims. The useful engineering result is a more precise diagnosis: the investigator can correctly read the evidence and still choose the wrong statement to check.

This was one known development manuscript, the Dobson Drosophila study used in the preceding trial. Prior model reviews and public human reviews were excluded from inference. These are not fresh validation results or evidence of human-review overlap.

## What was changed and tested

- Ten reported-results workbooks were converted into 743 addressed source rows. Worksheet names, raw cached cell values, source hashes, and 116 merged ranges were retained. Blank cells were not filled down or interpreted as zero. No author analysis was rerun.
- Both initial reviewers received the same complete table register, manuscript prose, supplementary text, advisory Scaffold checks, and three main figure pages. The register replaced duplicated, unaddressed table transcription. No interactive tool calls or external searches were used in this bounded comparison.
- Both could retain eight candidates and select five scientific questions within the same word allowance. Question-only output and empty replacements were enforced, removing the earlier edit-versus-question advantage.
- The investigator had explicit tasks for reported results, endpoint scope, and experimental design. Each required source evidence and an author defense.
- Debate retained opposing arguments and explicit sentence-component dispositions, with instructions to concentrate on source disputes and consequential questions.

The single condition used one Sol medium call. PRA used one investigator call and one debate call. The initial comparison has equal call counts. The final PRA comparison has twice as many generation calls, so this is not a compute-matched superiority test. All conditions received the improved infrastructure.

## Findings and selection

| Topic | Single candidates | Single selected | Investigator selected | After debate |
| --- | --- | --- | --- | --- |
| SNP association versus causal sufficiency | Yes | Yes | Yes | Yes |
| Shared-vial dependence | Yes | Yes | Yes | Yes |
| Interpretation of transformed effect sizes | Yes | Yes | Yes | Yes |
| Nutrient versus formulation attribution | Yes | Yes | Yes | Yes |
| Fixed collection order across feeding paradigms | Yes | Yes | No | No |
| Whether reproductive failure is localized to mortality stages | Yes | No | No | No |
| Figure 2 caption versus S7 tests | No | No | No | No |

The single reviewer retained six candidates and selected five. The investigator produced four candidates and selected all four. It mentioned collection order in discarded hypotheses, recognizing that it limits comparisons between paradigms without invalidating within-paradigm contrasts. That is a reason to narrow the question, not necessarily to omit it. This useful topic was lost before debate.

Debate preserved all four investigator topics and all 21 sentence components. It made no new scientific discovery. Its wording more clearly acknowledged the existing dietary caveat and framed effect-size interpretation as a request for justification. It could not recover the collection-order question from the candidate ledger because that question was not in the ledger. Its full manuscript access also did not lead it to add the caption discrepancy.

## Anonymous evaluation and source audit

Labels were randomized before generation. The evaluator received the three selected reviews without method names, prior grades, investigation records, or debate records. It received the same source packet. This was one same-family automated evaluator. Stylistic clues may still reveal workflow.

The evaluator preferred the single reviewer because it covered the four shared topics and added the consequential collection-order clarification. It noted that the latter primarily affects comparisons across feeding paradigms and that the nutrient concern was overstated as major.

Twelve of 13 ratings passed exact-reference validation. The investigator's nutrient finding was unscored because its evaluation quotation silently omitted citation marker `[37]`. The automated rating remains unchanged and unscored. This is a failed evidence reference, not proof that the scientific question was wrong. No substantive rating used the new cell register, since neither method selected the caption discrepancy. Therefore this trial does not demonstrate improved table-based grading reliability, although investigator check records successfully used exact cell references.

Validated ratings were:

| Output | Concern | Clarification | Unscored |
| --- | ---: | ---: | ---: |
| Single | 4 | 1 | 0 |
| Investigator selection | 2 | 1 | 1 |
| After debate | 3 | 1 | 0 |

All ratings were nominally favorable and no request was classified as excessive. That limited discrimination remains an evaluation concern. Exact quotations establish source identity, not scientific correctness. In particular, the evaluator classified closely related effect-size questions differently across conditions. I would treat that topic as requiring statistical clarification, not as an independently established analysis error.

My unblinded source audit supports a cautious preference for the single review's broader selected coverage. The collection-order question is warranted when restricted to cross-paradigm comparisons. Vial clustering warrants a robustness question, but the size of any resulting inferential change is unknown. The nutrient caveat should be tied to specific remaining claims because the Discussion already acknowledges it. None of these checks substitutes for independent domain review.

Two known missed issues explain the next engineering change:

1. The investigator correctly reported S7 fecundity interaction values of 0.12221 and 0.06683 and correctly found that the Results paragraph excludes egg laying. It declared that check consistent without checking the Figure 2 caption, which includes fecundity and omits development. The original source rows still support the discrepancy. Correct arithmetic or table reading does not establish cross-location coverage.
2. Its endpoint check focused on an already qualified mitoribosome mechanism. It missed the specific statement that the variation was exclusively postembryonic. The Methods says pupation and eclosion were scored daily. The question should connect that specific stage claim to reported observations, without asserting that no intermediate measurements existed. The single review's unselected mortality candidate also needs that qualification.

## Follow-up engineering completed without another model trial

A new deterministic preflight builds an explicit inventory of statements to reconcile. On this manuscript it identifies 15 candidate targets from statistical figure-caption statements and exclusive stage claims. The inventory directly links the Figure 2 statement to the related Results passages and S7, and the postembryonic statement to the Methods passage describing pupation and eclosion.

Each target now has a stable ID and exact source statement. A target-specific completion audit requires the caption statement, related manuscript evidence, and linked table cells before accepting a caption comparison as complete. A stage comparison requires the stage statement and linked measurement evidence. Missing and unresolved targets remain open. A generic check of another consistent passage cannot close them.

The new module and command are reusable local preflight infrastructure. The frozen retest runner still represents the workflow actually evaluated. The follow-up gate has not been tested through another model review and is not yet integrated into the default reviewer command. It must not be described as a measured quality improvement. Its text patterns are not exhaustive, candidate links can be semantically wrong, and some targets may lack decisive accessible evidence.

The investigator instructions were also updated after generation to retain proportionate unresolved questions as anchored candidates, even when unselected. A scoped question must not disappear merely because a broader allegation would be invalid. This instruction change has not received a new model trial. The original prompt remains in the frozen request and source snapshot.

All 137 tests passed after this follow-up. Tests include blank versus zero handling, missing formula caches, immutable source values, matched question-only schemas, exact quotations, incomplete comparisons, supplementary versus main figure identity, and preservation accounting. The local viewer serves all three selected outputs with anchored manuscript comments.

## Cost and interruption

| Completed call | Observed tokens |
| --- | ---: |
| Single | 95,224 |
| Investigator | 96,653 |
| Debate | 100,886 |
| Replacement evaluator | 101,113 |
| Known total | 393,876 |

No cached input was reported for these completed calls. The original evaluator was interrupted when the launcher exited with signal 15. It left no answer or usage completion and no live study process remained. After inspection, one documented evaluation-only recovery used the exact frozen prompt, labels, reviews, and source packet. No generation was repeated and no result-dependent prompt was changed. This is an explicit exception to the initial four-attempt plan: five attempts, four completed outputs. The interrupted call has unknown usage, so 393,876 is not the exact total cost and the original total token ceiling cannot be verified.

Shared account use moved from 19 percent before execution to 20 percent at recovery. These readings include other account activity and are not an exact attribution. No paid credits, fallback models, or usage reset were used. The CLI requested Sol explicitly, but its event stream did not independently report the resolved model identity.

The complete artifacts and original failure are preserved under `runs/pra-claim-retest-v1`. No additional manuscript or model trial was run.

## Decision

Keep the addressed source register, matched output contracts, complete finding history, and debate accounting. Do not promote this investigator prompt as superior. The next small experiment should test target-specific investigation and ensure that proportionate discarded questions are included in the debate ledger. Run that before a larger panel. Independent assessment of disagreements remains necessary before publication claims.
