# Four-addition development retest

This comparison was frozen before new generation. It uses two papers from the previous domain panel: plant-pollinator ecology and the registered health intervention. The ecology manuscript informed the result-map changes. Neither manuscript is an unseen validation case.

For each paper, compare three anonymous reviews:

1. The saved PRA final review from the earlier panel
2. A new single reviewer with the updated tools and guidance
3. The updated investigator-plus-debate PRA final review

Generation and judging use Sol at medium effort through the verified subscription. New generation receives the same manuscript, initial figure pages, domain skills, offline scaffold checks, finite source packet, six total tool calls and six external request allowance per condition. PRA divides its six tools across investigator and debate, and uses two model calls rather than one. It is not an equal-compute comparison.

The overall cap is eight new model calls: two single reviewers, two investigator/debate pairs and two judges. The observed-token launch stop is 850,000. An in-flight call can finish above the launch stop. There are no automatic retries, extra judges, paid API credits or reset redemptions.

The judge is a fresh model invocation with no generation context, condition mapping, tool history, cost or prior preference result. It sees the manuscript, anonymous review content, a condition-neutral image union and bounded source cards. It rates each finding separately for support, specificity, materiality, edit fidelity and proportionality, then states a preference. The comparison permits a tie or uncertainty. Invalid judge source references remain unscored.

Source validity and scientific correctness remain separate. One model judge is not an independent human expert. The coordinator will inspect preference-driving issues against their sources and report any uncertainty or judge errors without silently repairing the raw rating.

The saved PRA reviews and new PRA reviews also differ through model sampling. This experiment can identify promising changes or regressions but cannot causally assign an effect to a particular feature. The existing frozen packets do not exercise unrestricted literature discovery or historical registration reconstruction. Tool-use logs will show which additions were actually used.

All original domain-panel artifacts remain unchanged. New artifacts are stored under `runs/pra-additions-retest-v1`.

## Diagnostic amendment

Before judging on September 25, 2026, completed generation exposed three strict evidence-format failures. The health single review reordered source-card fields within a purported exact quote. Ecology debate miscopied one word in a component quotation. Health debate placed a real external source ID in a manuscript-only reference field.

The recorded amendment permits anonymous assessment of completed raw final content when the primary manuscript anchors resolve and all referenced identifiers are known. It does not repair quotations, change generation, rerun models, or treat blocked output as a validated deliverable. The two amendment records and the hash-pinned diagnostic evaluator are preserved with the run. Content preference and first-pass delivery are reported separately. Judge quotation errors remain unscored.
