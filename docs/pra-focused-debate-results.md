# Focused evidence and debate comparison

This record describes the system up to PeerReviewAgents `v0.8.0`.

## Prespecified development comparison

The same owl paper and the same two saved independent reviewer drafts are reused. The saved ensemble review is compared with a new debate supplied with one validated focused evidence memo and the inspected original supplement pages. The question concerns what supports the interpretation of treatment effects after adjustment for parental departure.

The authorized sequence contains three new Terra medium sessions: one repaired focused investigation, one debate and one anonymous usefulness judgment. The overall observed-token launch ceiling is 550,000. This is not a hard cap within a running model session. There are no automatic retries, paid credits or usage resets.

The memo handoff rebuilds the source and tool audits, rejects altered content or mismatched manuscripts, and verifies inspected images against original sources. The debate retains the full original issue ledger. Every issue and component requires a disposition. The memo is a fallible interpretation and cannot itself establish scientific validity.

The judge receives randomly assigned A/B review labels, identical manuscript and image evidence, and no workflow labels, prior judgments or focused memo. It assesses holistic usefulness, scientific accuracy, actionability, calibration, coverage and prioritization. It also identifies distinct valid points and consequential differences. Exact review spans and manuscript source handles are separate to avoid the earlier quotation error.

This is one known development paper, with a coordinator-selected question and one same-family AI judge. Added evidence and extra model effort are confounded with the intervention. It cannot establish general superiority, independent expert validity or the isolated effect of debate.

Artifacts: `runs/pra-focused-debate-v1`. Existing reviews and failed earlier evidence notes remain unchanged. Automatic investigations for every paper are not enabled.

Offline validation before launch: 56 targeted tests passed, including two-condition judge accounting, memo tamper rejection, source handles, tool receipts and debate preservation.

## Result

The blind judge narrowly preferred the saved review with medium confidence. Both reviews scored 8 out of 10 and contained the same five distinct valid issue groups. All point ratings passed traceability checks. The judge found no unsupported or partly valid points in either review.

| Measure | Saved review | Updated review |
| --- | --- | --- |
| Overall usefulness | 8/10 | 8/10 |
| Distinct valid issue groups | 5 | 5 |
| Calibration | 5/5 | 4/5 |
| Scientific accuracy | 5/5 | 5/5 |
| Actionability | 5/5 | 5/5 |
| Coverage | 4/5 | 4/5 |

The other judged dimensions were equal at 5/5. No entire valid issue group was gained or lost. The updated debate accounted for all 12 source issues and 33 components and retained five primary findings, with no secondary findings. This structural accounting did not prevent loss of useful detail.

The updated causal interpretation acknowledged that the models adjusted for parental departure while retaining uncertainty about a direct causal pathway. However, its full rewrite omitted useful wording elsewhere. The saved review specified that an unresolved attrition problem should limit interpretation to juveniles with observed dispersal timing. It also retained clearer distinctions between total and direct effects and more detail about manipulation-check timing. The judge preferred those qualifications. Successful source access did not translate into a better final review on this case.

## Tool use and repaired handoff

The repaired investigation selected six valid manuscript source handles. It inspected original S1 PDF page 1 and attempted a literal search with a long keyword sequence. That search returned no matches. The memo accurately reported that limitation and did not assert that the missing search results established absence of evidence. The inspected image passed source verification before debate and was also supplied to the blind judge as part of the common evidence set.

The original tool audit counted the completed empty search as returned evidence. After the trial, audit version 2 was corrected to distinguish an execution receipt from an evidence-bearing result. The separate postrun audit records one evidence-bearing check out of two tool calls. The original run remains unchanged and its version 1 audit remains reproducible. Search guidance now calls for one short contiguous phrase or direct reading of known block IDs. These repairs were checked offline without another model session.

## Cost and decision

| New session | Reported tokens |
| --- | ---: |
| Focused investigation | 129,182 |
| Debate | 81,212 |
| Blind judge | 94,672 |
| Total | 305,066 |

The investigation total includes 80,128 cached input tokens. These counts are not dollar costs. The new generation work was 210,394 tokens, excluding the judge and reused discovery drafts. Counting the same two discovery drafts, the logical updated review workflow was 369,114 tokens versus 236,186 for the saved workflow, about 56 percent more. This additional cost produced no demonstrated usefulness gain in the one-case assessment.

Do not promote the updated review or enable mandatory focused investigation in every panel. Keep the saved review as the preferred artifact. The next design should constrain follow-up changes to the relevant finding and preserve unrelated final-review text and fallback recommendations. Focus investigations on missing evidence that could change a decision, rather than rechecking a question already handled well. That design still needs evaluation.

After the empty-search repair, 57 targeted tests passed and the historical memo still passed its versioned handoff verification. No additional live calls, automatic retries or larger study were run.
