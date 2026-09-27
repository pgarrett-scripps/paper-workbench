# Two fresh manuscript comparisons

The investigator workflow is promising, but these results do not establish reliable superiority over a single reviewer. One anonymous Sol judge preferred the investigator before debate on the sleep paper. The other preferred the review after debate on the yeast paper. The yeast debate failed its internal evidence gate, and one of its evaluator ratings remains unscored. That preference is exploratory.

Both papers were selected before generation and were unused in the local experiments. They are published versions, not original peer-reviewed submissions. Fresh to this experiment does not mean unseen during model training. Human review histories were excluded. This is a development comparison with automated assessment and limited unblinded source checks, not a human-overlap study.

| Paper | Automated preference | Production debate gate | Main lesson |
| --- | --- | --- | --- |
| [Fly sleep and ageing](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0308652) | Investigator before debate | Passed | Investigator and single reviewer found different useful questions. The judge and debate disagreed about an already-qualified molecular hypothesis. |
| [Yeast growth polarity](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3002491) | After debate, exploratory | Failed | Debate improved proportionality but introduced evidence-reference errors and an incompletely qualified abundance caveat. |

## What the judge rated

These counts are the automated evaluator's assessments with valid source references. They are not independently established defects. The evaluator assigned no unsupported-allegation ratings, which does not settle the source concerns identified below.

| Paper and condition | Selected questions | Concern | Clarification | Unscored | Excessive requests |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sleep, single | 5 | 2 | 3 | 0 | 0 |
| Sleep, investigator | 5 | 4 | 1 | 0 | 0 |
| Sleep, after debate | 4 | 3 | 1 | 0 | 0 |
| Yeast, single | 5 | 3 | 2 | 0 | 1 |
| Yeast, investigator | 5 | 4 | 1 | 0 | 0 |
| Yeast, after debate | 5 | 3 | 1 | 1 | 0 |

The concern and clarification categories describe different evaluator judgments. They are not a numerical quality scale. One same-family judge per paper cannot establish that PRA is better in general. PRA also received two generation calls against the single reviewer's one.

## Information gained, omitted, and disputed

On sleep, the investigator identified a direct cross-strain testing question absent from the single review. The single reviewer identified a different concern about an inactivity threshold used to exclude presumed dead flies. The investigator did not record that concern, so debate could not recover it from the candidate ledger. The single review also asked about anticipation-ratio components. This was a discovery difference, not a debate deletion.

Debate retained four investigator topics and removed the Pdf mechanism question. All source issues and components received dispositions. The removed question remains in the full ledger. The judge preferred keeping it and called it a justified concern. My unblinded source check is less persuaded: block b0029 presents an attractive hypothesis and describes its broader occurrence as a possibility. The debate's omission is defensible, while the evaluator argues that the extension still deserves qualification. Preserve this disagreement for expert assessment rather than declaring either model correct.

On yeast, the investigator added a nonadditivity question absent from the single review's selected five. The single reviewer separately challenged pathway independence. Debate retained all five investigator topics and more clearly allowed qualification instead of new experiments. The judge cited that proportionality as a reason for preferring it. Debate did not add a distinct new scientific topic.

A manual check found a substantive scope concern in the final PI4P question. It mentions lower protein abundance for both PH deletion and efr3 deletion as complicating localization interpretation. However, b0027 describes restoring the PH-deleted protein's abundance without restoring localization or function. Debate itself accepted that control in hypothesis-2. The broader PI4P-specificity question remains reasonable, but its final wording should separate the PH control from the remaining efr3 caveat. This is a case where accepted counterevidence was not fully reflected in the selected comment.

The sentence ledger accounted for all 41 components across both papers. This is not a semantic-retention score. For example, the sleep debate marked the factual sentence about separate ANOVAs as resolved while also carrying that fact into the final question. Future evaluation should track scientific requests and their scope, not treat every sentence as an independent concern.

## Evidence and execution failures

The yeast debate had three invalid internal references representing two error types. A correct CRIB-GFP quotation was assigned to b0044 instead of b0038 in two places. Another quotation omitted the source's figure citation before the period. The gate correctly rejected the package. No quote or block ID was repaired.

The planned judge still evaluated the selected question text under the exploratory fallback specified before inference. Its actin rating C5 cited a real sentence under b0076 instead of b0039. That rating remains unscored. The raw preference is retained, but its supporting ratings are incomplete. Neither failure triggered a retry.

All conditions received identical source text and images within each paper. Source and code hashes, anonymous label mappings, requests, raw answers, gates, and usage receipts were frozen. Final questions used the same question-only format and five-question allowance. No external literature search, author code execution, or data reanalysis occurred.

## Changes made after the experiment

Added an explicit measurement-and-selection check to the next structured investigator version. It follows outcome definitions, aggregation, thresholds, missingness, exclusions, and selection that depends on the outcome signal. The production discovery prompt uses the same guidance within its existing measurement area. The structured comparison now requires four checks instead of three, within its existing maximum of four. This adds no model call, though the extra check can increase output tokens.

Strengthened the shared debate instructions to compare final comments with resolved hypotheses and accepted author defenses. Partial controls must remain scoped in the final comment. A defeated explanation must not reappear elsewhere as an unresolved caveat.

These changes are unbenchmarked. They were made after all eight calls and after verifying the experiment freeze. The original outputs and scores remain unchanged. The 144-test suite passes, including the updated gate that rejects missing or unsupported measurement-selection checks.

## Next priorities

1. Use immutable source-span handles and resolve quotations mechanically. This can prevent mismatched ID and quotation pairs. It cannot establish that the selected evidence supports the interpretation.
2. Represent each scientific request with its premise, scope, author defense, remaining question, and final destination. Keep disputed or lower-priority questions visible in the editor queue without endorsing them automatically.
3. Test the new measurement-selection direction on a small fresh case, with the same tools available to the baseline. Add a targeted missing-issue search only if discovery gaps persist. Avoid another full independent review by default.
4. Connect imported references to Paper Scaffold's BibTeX-based checks. Current pilot checks cover extracted citation linkage only. The repository already has bounded Crossref metadata and Europe PMC search tools. Use those selectively for specific citation questions after the bibliography conversion works. Metadata identity and abstract retrieval do not establish claim support or prove a missing citation.
5. Obtain limited independent assessment of the disputed cases before using preference scores as publication evidence. The Pdf disagreement and the PH abundance-control case are useful test items. Do not tune prompts to force the current judge's preferred answer.

No further inference was launched. More agents and broad new integrations are not the immediate priority.

## Cost and artifacts

Eight Sol medium calls completed without retries, using 549,656 observed tokens. The final call began at 472,544 tokens, below the frozen 500,000-token launch stop, and completed above it as the protocol allowed. This launch stop is not a hard completion cap. No paid credits or reset were used. The shared account meter moved from 21% to 23%, which is rounded account usage rather than exact experiment attribution.

| Stage | Sleep tokens | Yeast tokens |
| --- | ---: | ---: |
| Single | 60,408 | 70,332 |
| Investigator | 60,320 | 69,984 |
| Debate | 67,443 | 77,654 |
| Evaluator | 66,403 | 77,112 |

Protocol: `docs/pra-transfer-two-protocol.md`.

Artifacts: `runs/pra-transfer-two-v1`. Each paper contains immutable raw outputs, candidate and selected reviews, the full debate ledger, a flow audit, source checks, and an anonymous evaluation. `source-audit-final.json` records the completed manual audit and takes precedence over the pending-audit status retained in the frozen automated-results files. `failure-cases.json` preserves the concrete cases for later regression assessment.
