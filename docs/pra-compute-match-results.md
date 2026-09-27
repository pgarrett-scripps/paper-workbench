# Matched-pass comparison results

The blind model judge preferred PRA over a two-pass self-revising single reviewer on the ecology manuscript. Their observed generation-token totals differed by approximately 0.13%. Both final reviews contained five supported findings according to that judge, and all ten finding assessments passed source-reference validation.

This supports further testing of the structured debate workflow. It does not establish general superiority, and the single-agent revision identified a consequential issue absent from PRA.

## Comparison

| Measure | Two-pass self-revision | Investigator plus debate |
| --- | --- | --- |
| Generation calls, including reused calls | 2 | 2 |
| Observed generation tokens | 147,742 | 147,927 |
| Final findings | 5 | 5 |
| Validated model assessments | 5 of 5 | 5 of 5 |
| Justified concerns | 1 | 0 |
| Justified clarifications | 4 | 5 |
| Unsupported allegations | 0 | 0 |
| Excessive requests | 0 | 0 |
| Blind preference | | Preferred |

The same Terra model selection, medium effort, manuscript, scientific supplements and initial figures were used. Self-revision received the original prompt and its own prior draft. It did not receive PRA, earlier judge feedback or a paper-specific hint about the missing concern.

The original single pass allowed six tool calls, while PRA investigation allowed four. Both used zero. Self-revision and debate each had a two-call allowance and used zero. Thus actual tool use matched, but the initial allowances were not identical. The conditions also had different first-pass instructions, so this assesses the two workflows as a whole rather than isolating debate alone.

Pass count and observed tokens are close. Hidden reasoning work, FLOPs and billing units are not independently measured.

## Why the judge preferred PRA

The judge favored three aspects of PRA:

- It treated the null community-level pollen result as insufficient to establish or exclude a species-specific change.
- It asked for the hive crossover details without calling the two descriptions definitively contradictory.
- It requested complete reporting and multiplicity information for the time-specific statistical tests.

The self-revising reviewer retained a stronger assertion that the hive schedule was contradictory. Its useful request for clarification remained supported, but the judge considered PRA's framing more precise. A source-valid concern can still contain overconfident wording.

These are the preferences of one fresh-context model judge. The source-reference checks establish traceability, not the truth of every judgment.

## What self-revision added that PRA missed

Self-revision retained its four original broad concerns and added a fifth: changing the proportion of B. pilosa pollen also changed the rest of the diet mixture. The judge classified this as a major justified concern about attributing a whole-composition effect specifically to one component.

The relevant manuscript passages are `b0020` and `b0021`, which describe the diet formulations, and `b0047`, which attributes increased larval efficiency to the increased B. pilosa proportion. The question is what causal contrast the mixture experiment supports. It does not invalidate the observed difference between the formulated diets.

PRA did not contain this concern before or after debate. It was therefore an investigator discovery gap, not a finding removed by debate. PRA instead retained the pointwise-testing concern, which the judge rated a moderate justified clarification.

The final preference is consequently not evidence that PRA found every important issue, or that its unique issue was more consequential than the single review's unique issue. The judge traded off issue coverage against precision across the whole report. Category counts alone do not explain or determine that preference.

## Cost and integrity

Only two new calls were made: self-revision, using 74,258 observed tokens, and the judge, using 80,635. Incremental usage was 154,893 observed input and output tokens. The generation comparison includes the historical first single pass of 73,484 tokens and the historical PRA total of 147,927 tokens.

There were no new failed calls, retries, model substitutions, paid credits or reset redemptions. Earlier capacity failures belong to the preceding trial and are not silently incorporated into this comparison's known-usage total.

The source, prompt, schema, code and reused review hashes were frozen before the new inference. The original PRA output and earlier assessment were preserved. Anonymous labels and source-reference receipts were recorded. All ten assessments passed the existing auditor, with no unscored ratings. No production review prompts were changed during this comparison.

## Interpretation and next change

The additional single-agent pass improved its coverage but did not erase the judge's preference for PRA at almost identical observed generation cost. That is a promising development result for the full workflow, not proof that debate alone caused the advantage.

The immediate scientific limitation is discovery coverage. More debate cannot recover a concern that was never proposed unless it independently identifies it. A useful next shared design check is to identify the actual manipulated contrast: when one component changes, what else necessarily changes, and does the claimed attribution exceed that contrast? This should apply conditionally to mixtures, substitution experiments and bundled interventions, and be made available to both comparison conditions.

Keep the recorded self-revision concern as a development example. Do not add it to the completed PRA review or rescore the original output. After a shared checklist update, test on new papers rather than repeatedly optimizing this paper.

This is a retrospective development comparison on one reused ecology manuscript. The coordinator knew the previous result, the judge comes from the same model family, and there is no independent human adjudication. It is not a new independent paper, a replicated win rate or publishable evidence of broad superiority by itself.

## Artifacts

- Protocol: `docs/pra-compute-match-protocol.md`
- Trial: `runs/pra-compute-match-v1/`
- Result and costs: `summary.json`
- Blind model output: `evaluation/raw-model.json`
- Expanded source references: `evaluation/raw.json`
- Rating audit: `evaluation/audit.json`
- Self-revision: `single/responses/plain-guarded.json`
- Coordinator change inventory: `coordinator-change-audit.json`
- Frozen inputs and code: `seal.json` and `frozen-source/`
