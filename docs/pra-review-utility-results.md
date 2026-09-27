# Overall review usefulness reassessment

The exploratory blind judge preferred ensemble and rated its overall usefulness 9 out of 10, compared with 8 for each alternative. These are holistic model ratings, not scores computed from issue counts or calibrated measurements of scientific quality. The point-reference audit failed, so the assessment remains provisional.

| Review | Overall usefulness | Judge-emitted substantive points | Validated point count |
| --- | ---: | ---: | --- |
| One-pass tool-free | 8/10 | 4 | Unavailable |
| Three-pass ordinary workspace | 8/10 | 4 | Unavailable |
| Two independent reviewers plus debate | 9/10 | 5 | Unavailable |

The judge favored ensemble for coverage, actionability, and calibration. It considered the shared central concerns useful in all three reports, but credited ensemble's additional qualification of the ambient-food explanation and its more careful treatment of causal claims. It identified concrete strengths in both comparators rather than treating them as poor reviews.

All judge-emitted points were classified as valid concerns or clarifications. However, the judge copied manuscript quotations into every `review_excerpt` field, instead of quoting the actual reviewed comments. All 13 points therefore failed the predefined review-traceability check. They remain unscored. A zero validated count in the machine output means no point passed that check, not that the reviews contained zero valid points. No excerpts were silently replaced and no scientific judgment was fabricated.

The raw pairwise preferences were ensemble over both alternatives and workspace over basic. The latter reverses the preceding judge's basic-over-workspace preference, while the two overall usefulness ratings here are equal. This is another reason not to overinterpret small differences or aggregate these assessments as independent replications.

The revised evaluation framework now makes holistic preference the primary outcome. Anchored usefulness scores and accuracy, importance, actionability, calibration, coverage, and prioritization ratings explain that preference. Distinct valid points are supporting evidence. Semantic grouping prevents duplicate formulations, supporting observations, or artificial splitting from earning extra credit.

After preserving this failure, the next-version evaluator replaced free-text review quotations with immutable review-span handles, separate from manuscript evidence handles. A selected span must belong to the finding being assessed. Unknown or cross-review handles fail validation. Three focused offline tests pass, including deduplication, invented-excerpt rejection, and cross-review reference rejection. This repair has not received another live judge call.

The reassessment used one Terra medium call with 91,340 observed tokens. No manuscript reviews were regenerated, no paid credits or reset were used, and no retry was launched. Protocol, inputs, raw model response, reference receipts, provisional results, and the original completion record remain in `runs/pra-review-utility-v1`. The source and inputs passed the original end-of-run hash check before the reference-interface repair.

The rubric was changed after earlier results were known at the user's request. It is an exploratory reassessment of one development paper, not new confirmatory evidence. Preserve previous evaluations and freeze the new rubric before applying it to additional manuscripts.
