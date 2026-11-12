# Configurable independent discovery and debate

The review CLI now defaults to two independent whole-paper discovery sessions, followed by one fresh evidence-based debate. Set `--reviewers 3` or a higher count to expand discovery. Counts from 1 through 16 are accepted, subject to the launch budget. Larger counts have not been validated as more effective.

Each reviewer receives the same manuscript workspace and initial figure pages, with its own source cache and tool state. It does not receive another reviewer's findings. Sessions currently run sequentially to control subscription usage. Independence refers to separate contexts, not different models or scientifically independent evidence.

Under the default agentic-v1 policy, each discovery session runs at high effort with a thirty call tool allowance and no candidate cap. Under `--policy standard-v1`, each can return up to ten candidates and use four manuscript or domain tool calls. The pool preserves every candidate and discarded hypothesis with reviewer provenance. Similar comments are not deleted automatically. The debate records an explicit scientific decision and a destination for every sentence component. Several source issues can map into one final comment.

The debate can introduce up to five new candidates, each with a uniquely located manuscript anchor and an explicit evidence-based decision. Supported secondary candidates remain in the editor package even when they do not fit the five-finding summary. Unresolved candidates remain marked as unresolved. Neither agreement nor retention establishes correctness.

Workflow `ensemble-v2` requires each new candidate to contain its own decision and component treatment. The runtime assigns the matching issue and component IDs, then applies the existing evidence and retention checks. Missing judgments and duplicate decisions fail validation. The runtime never supplies a scientific decision. Historical v1 artifacts remain unchanged.

Workflow `ensemble-v3` additionally requires an adjudicated, anchored secondary comment for a retained concern that has deferred components and no primary destination. The wording must reflect the accepted author defense and any remaining uncertainty. Source comments remain available separately for audit. Unanchored unresolved investigator notes can remain audit-only. Secondary comments cannot contain unguarded manuscript replacements. This avoids presenting a rejected broad allegation as though it were the final scientific judgment.

Discovery, ordinary revision, and debate share guidance to retain consequential clarification questions without asserting unverified defects. Source evidence that answers the question can resolve it. Missing decisive information alone is not a reason to discard it.

When an otherwise valid component reference differs only in its first-letter capitalization or one trailing punctuation mark, a restricted repair can select the unique matching span from the same final comment. It records both versions and revalidates the entire result. It cannot rewrite a comment, change its scientific status, redirect a component, paraphrase a quotation, or repair a manuscript quotation.

Debate is one fresh model session that weighs criticism and author defense. It is not a conversation among multiple independently running debaters. It receives the pooled ledger, full manuscript, source cards, and original images. It has the policy's debate tool calls, two under standard-v1 and eight under agentic-v1. The existing source-handle validation, conservative edit guard, secondary inventory, and manuscript annotation export remain in use.

## Synthesis validation before submission

Core 0.1.6 exposes `validate_synthesis` only to the synthesis session, for debate and ordinary synthesis. The prompt asks the model to write final findings first, map retained components to actual final text, check the complete draft, and correct reported errors before submitting. Two local checks are allowed separately from the two source calls. This adds no generation session or network request, although submitting a draft to the tool uses additional context tokens. A durable receipt preserves each draft, validation result and allowance reservation across server restarts.

Preflight uses the same source handles, candidate normalization, evidence checks, exact destination checks and restricted formatting recovery as final validation. It does not invent missing comments, decide a scientific status, relax evidence requirements or publish a review. Final validation remains mandatory even if the model skips preflight or edits its response afterward. The final audit records whether a passing check covered the exact submitted draft.

A reference recovery failure now reports the later validation error that remained after a permitted formatting correction. Previously, that error could be hidden behind the initial quotation error. Diagnostics identify missing final findings, absent destination text and a rejected hypothesis with an unresolved component. Secondary-comment errors identify the issue and missing or unexpected fields. Required author-facing comments cannot be replaced with null to bypass validation. Original study outputs and frozen execution code are unaffected.

An offline replay of 23 saved main-study syntheses accepted all 19 previously completed outputs and rejected all four recorded failures. No new model calls were used. This checks validator behavior and error visibility. It does not establish a lower failure rate in new reviews.

Two subsequent development calls reused discovery from the original empty-output failure. The first still failed because secondary-comment feedback was too generic. Feedback was revised to name issue IDs and missing fields. In the second call, preflight identified two absent destination quotations. The next check passed, and the final five-finding submission passed independent production validation. The model changed ledger wording after preflight, so the submitted draft hash did not match the preflight hash. Final validation remained mandatory. Both attempts are preserved. Together they used 492,803 observed tokens, with no discovery reruns or judge calls. This is outcome-selected development, not a new failure-rate estimate or evidence of improved scientific review quality.

Exact offline and live receipts are under `docs/validation/`. The raw development archive is attached to the private paper repository's draft `study-results-v1` release as `pwb-synthesis-validation-development-20261011.tar.gz`. The archive excludes billing records and includes both frozen development code snapshots.

### Component ledger contract

Core 0.1.7 uses preflight version `synthesis-preflight-v2`. In the four-paper synthesis recovery, paper 0317140 failed after its first check contained all 38 component records but was rejected for one unknown evidence handle. The next check and the final response kept all 14 issue decisions with empty component arrays. The feedback named neither the missing identifiers nor the fact that the first ledger had been complete.

The synthesis schema now requires exactly one outer decision per known issue, restricts issue and component identifiers to the ledger, and requires at least one component per decision when every issue has components. The prompt lists the required component identifiers for each issue. New candidates keep runtime-assigned identifiers.

Every preflight result reports `component_ledger` counts, including when another error stops validation. Problems name missing, duplicated, misassigned and unknown component identifiers, and missing or duplicate decisions. The production `synthesis-validation.json` records the same diagnostics. Final validation is unchanged and still rejects any incomplete ledger. No draft is repaired.

An offline replay of the three saved 0317140 drafts reported 38 of 38 components accounted for in the first check and named all 38 missing identifiers in the second check and final response. No new model calls were used. This tests diagnostics on saved outputs only. It does not show that a model will use the feedback in a fresh synthesis. The receipt is `docs/validation/component-ledger-replay-20261012.json`.

## Run

This workflow ran on the 0.8 engine, with its `--model`, `--policy`, `--token-budget` and `--mode` options and the `ensemble_review` Python call. Engine 0.9.0 removed all of them, and the workflow is frozen at the PeerReviewAgents `v0.8.0` release. A current review is `paper-workbench review manuscript.pdf RUN`, as described in [the engine contract](shared-core.md).

## Evidence and remaining questions

Offline tests exercise two and three reviewer sessions, separate contexts and source state, source candidate preservation, new debate findings, and launch-budget stops. They do not prove scientific quality or exhaustive discovery.

The first live development check reuses two previously independent behavioral-paper drafts, then makes one new debate call and one new blind judge call. Those drafts used different prompts and tool access. This deliberately inexpensive comparison tests pooling and debate, while the new discovery runner is exercised offline. It is not a fresh matched-compute benchmark of the complete new workflow.

That check preferred the pooled review over the previous PRA review and two-pass basic review. All five pooled primary findings received supported ratings. The original debate delivery failed on two component-reference formatting errors, which were repaired offline without changing the scientific review. See [pilot results](pra-ensemble-pilot-results.md) for the retained failure record, cost, and limitations.

Before increasing the default, measure the third reviewer's additional supported issues, false premises, and token cost on held-out papers. More candidates or agreement alone are not success criteria. Preserve all failures and distinguish primary findings, supported secondary findings, and unresolved questions.

The next two-paper development comparison generated both workflows on two fresh manuscripts. Only the clinical blind assessment completed. It preferred the ensemble scientific draft, although ensemble delivery failed on a missing new-candidate decision. The plant judge was interrupted without a completed answer. The v2 contract addresses the clinical failure and has offline tests, but has not been validated by another live review. See [fresh comparison results](pra-ensemble-fresh-results.md) for the incomplete trial, baseline prompt overhead, and usage uncertainty.

The subsequently authorized clarification check is specified in [the follow-up protocol](pra-ensemble-clarification-protocol.md). Its evaluator records process identity, heartbeat, deadline, and completion or failure. `evaluate(..., resume=True)` only recovers an identical saved request. It cannot launch a model call. A new assessment uses a separate attempt and retains the earlier failure.

That check completed both assessments. The saved plant judge and fresh owl judge each preferred ensemble, with five supported primary findings versus four for sequential revision. The fresh workflow delivered without repair and retained one supported addition from the second reviewer. Its secondary and debate-only new-candidate branches were not exercised by that manuscript. See [clarification results](pra-ensemble-clarification-results.md) for costs, preserved failures, and limits on interpretation.
