# Two-paper matched-pass transfer results

Both fresh-paper blind model assessments preferred PRA over two-pass self-revision. All four review workflows delivered successfully, and all 20 finding assessments passed source-reference validation. The workflows produced the same number of judge-supported consequential final comments. The advantage was the judge's preference for issue selection and wording, not a demonstrated increase in the count of valid findings.

The shared design check, two-pass baseline, frozen transfer test, retention analysis and larger-study preparation are complete. The larger study has not been launched, and no independent human ratings have been obtained.

## Results

| Paper | Self-revision generation tokens | PRA generation tokens | Supported major or moderate final comments | Blind preference |
| --- | --- | --- | --- | --- |
| Clinical melatonin trial | 127,885 | 132,354 | 5 of 5 for each workflow | PRA |
| Soybean drought experiment | 114,120 | 117,976 | 5 of 5 for each workflow | PRA |

Each condition used two generation calls with Terra at medium effort and an identical four-plus-two tool allowance. PRA used approximately 3.5% more generation tokens on the clinical paper and 3.4% more on the plant paper. This is a close resource comparison, not an exact FLOP match.

The source papers were the [clinical melatonin trial](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0321635) and the [soybean drought experiment](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0332803). Both were absent from the local development corpus. This does not establish absence from model training data. Sources were selected by recorded metadata rules before review generation, not by whether PRA performed well.

## Clinical comparison

Both reviews raised four shared questions: reconciling withdrawals with ITT denominators, defining PSQI component scales, supplying responder data for NNT claims, and reporting harms by arm.

PRA added a question about recorded concomitant analgesic use and interpretation of the pain outcome. The judge preferred that additional issue and PRA's more careful distinction between ambiguity and established error. The self-revising review instead supplied a useful conclusion edit addressing the stated clinical-importance threshold. PRA retained threshold context in its NNT comment but did not provide that conclusion edit as a separate action.

The judge classified the baseline's five comments as one justified concern and four justified clarifications. It classified PRA's five as justified clarifications. All were rated major or moderate and proportionate. Preference therefore did not mean that PRA alone produced valid feedback.

## Plant comparison

Both reviews identified the design-description conflict, the anomalous shoot-weight uncertainty and limits of the root photographs. PRA also identified a photosynthesis interaction claim that conflicts with Table 1, combined it with a related warning about interpreting a marginal effect under an interaction, and requested a matched-control clarification for the Bacillin drench.

The self-revising baseline emphasized whether the PEG application established sustained root-zone water potentials and whether the measured outcomes supported a claim about nodule efficiency. Those were useful concerns. PRA retained related nitrogen-mechanism and PEG-scope questions as secondary clarifications, but they do not reproduce every detail of the baseline comments.

The judge preferred PRA principally for the interaction correction central to the abstract. Both final reviews received three justified-concern and two justified-clarification ratings. The baseline had three major comments and PRA had two. The overall preference is a tradeoff, not a finding that PRA dominated every measure.

A separate nonblind coordinator check confirmed that the original PDF itself displays the anomalous value 2.160 ± 15 and the nonsignificant photosynthetic-rate interaction. Those details were not introduced by XML extraction. This confirms source reporting, not the correct underlying uncertainty or biological result.

## Retention through debate

For the clinical paper, all five investigator candidates remained in the main review. The component ledger records 19 preserved components, three resolved components and one deferred component. Historical outcome switching remained unresolved because historical registry evidence was unavailable. That status is not an allegation that switching occurred.

For the plant paper, five of six investigator candidates were represented in the final review, with two statistical concerns merged. The sixth candidate, about the nitrogen interpretation, remained in the secondary inventory. Debate also recovered a narrower root-caption concern from a discarded hypothesis and put it in the main review. A PEG-scope question remained secondary. The component ledger records 16 preserved, two resolved and four deferred components.

No candidate disappeared from the structured accounting. This does not prove complete semantic preservation. The coordinator inspected the major topic changes, but the blind judges compared final reports, not investigator versus debate. A concern in the secondary inventory is a model-classified candidate, not an independently validated scientific fact.

## Scientific support and failure reporting

All 20 final comments were judged supported and consequential. Across the two papers, self-revision received four justified-concern and six justified-clarification ratings. PRA received three justified-concern and seven justified-clarification ratings. Neither received a scored unsupported allegation or excessive request.

Randomized labeling happened to place PRA as Review B in both comparisons. No order-reversed assessment was run, so position bias was not separately measured. The larger study plan requires balanced label positions within domains.

These are model judgments with valid references. Exact reference validation is not a correctness guarantee. Counts describe final review entries, some of which combine related scientific issues. They are not an exhaustive count of unique scientific discoveries.

Both workflows succeeded on both assigned papers. There were no model retries, failures, unaccounted usage receipts or unscored finding assessments in this trial. Source preparation required converting a publisher checklist from legacy Word into DOCX. The original file and conversion provenance were retained, and both workflows received the same content.

## What changed in the system

A conditional design check now asks what changed between groups, what changed alongside it, what remained fixed and whether the causal attribution matches the manipulated contrast. It explicitly avoids treating every mixture substitution as confounding. The check is shared by both conditions.

The reusable reviewer now supports a self-revision mode with four tools in the initial pass and two in the second pass. It shares source-request state, supplies its own guarded draft and preserves the existing evidence and edit protections. Both raw and normalized outputs remain available. A regression test checks the shared budget and prevents unsupported numerical edits from being carried into the second pass.

All 238 tests passed before generation. Code, prompts, input workspaces, figures and source packets were frozen before the first live call and verified again at closeout. No prompts were tuned between the two manuscripts.

## Tools and cost

Neither condition used an optional MCP tool call in this run. Both received manuscript text, initial source figures, domain guidance and precomputed advisory checks. The result cannot establish incremental benefit from live database or literature integrations, or isolate the new design check from the rest of the workflow.

Ten experimental calls consumed 623,748 observed input and output tokens. This includes eight generation calls totaling 492,335 tokens and two judges totaling 131,413 tokens. Development work, preparation and orchestration are outside those model receipts. No paid credits or account resets were used. Rounded account-wide consumption moved from 37% to 39%, which is not a precise task attribution.

## Larger validation study prepared

The draft study targets 24 new manuscripts across six domains, comparing the same two-pass workflows. It specifies frozen sampling and exclusion rules, delivery and scientific-quality endpoints, paper-level paired analysis, explicit handling of failures, and an eight-paper independent expert substudy with two raters per paper.

Anonymous, unscored expert packets are ready for both pilot papers. They contain the reviews, source manuscript, supporting documents and empty rating templates, without model scores or the workflow mapping. No expert has been contacted, recruited or asked to rate them.

The projected larger run is 120 model calls and approximately 7.5 million observed tokens at this pilot's mean, or 9.7 million with 30% headroom. This is a rough scenario from two papers, not a dollar quote, account-credit forecast or power calculation. Expert time is additional. The larger run is not launched.

## Decision

Keep the shared design check, source-handle protections and candidate-preserving debate. These two transfer results justify controlled validation of the workflow. They do not yet establish a statistically reliable or expert-confirmed advantage, and they do not justify claiming superiority to human peer review.

The next scientific uncertainty is whether independent domain experts agree with the model preferences and whether an advantage holds across a larger, frozen sample. The prepared study addresses that question. Additional integrations and repeated tuning on these two papers would not answer it.

## Artifacts

- Frozen pilot protocol: `docs/pra-transfer-matched-protocol.md`
- Complete trial and machine summary: `runs/pra-transfer-matched-v1/summary.json`
- Input/code seal and archived implementation: `runs/pra-transfer-matched-v1/seal.json` and `frozen-source/`
- Independent-assessment plan: `validation/next-study/protocol.md`
- Planned sampling: `validation/next-study/sampling-plan.json`
- Cost projection: `validation/next-study/budget.json`
- Unscored expert materials: `validation/next-study/pilot-expert-packets/`
- Publication outline: `validation/next-study/paper-outline.md`
