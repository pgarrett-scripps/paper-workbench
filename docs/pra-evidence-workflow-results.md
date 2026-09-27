# Evidence workflow development results

September 24, 2026. The two-paper comparison is complete. The approved increase to a 1,000,000 observed-token stop allowed the original eleven calls to finish at 777,399 tokens. No additional papers or inference retries were added.

The workflow did not meet the prespecified improvement threshold. Ordinary review and evidence review before debate each matched five of seventeen manuscript-assessable human concerns directly. After debate, the workflow matched three. These are automated development judgments, not expert-validated accuracy estimates.

## Comparison

Each condition selected five findings per paper. Counts below refer to distinct human concerns within each paper, not the number of findings. One finding can match multiple related concerns. Direct and partial matches remain separate.

| Manuscript | Condition | Supported direct matches | Partial matches | Assessable human concerns |
| --- | --- | ---: | ---: | ---: |
| FGF-induced lens development | Ordinary Sol reviewer | 0 | 1 | 8 |
| FGF-induced lens development | Evidence before debate | 1 | 2 | 8 |
| FGF-induced lens development | Evidence after debate | 0 | 3 | 8 |
| NGR-dependent root gravitropism | Ordinary Sol reviewer | 5 | 1 | 9 |
| NGR-dependent root gravitropism | Evidence before debate | 4 | 1 | 9 |
| NGR-dependent root gravitropism | Evidence after debate | 3 | 3 | 9 |
| Both papers | Ordinary Sol reviewer | 5 | 2 | 17 |
| Both papers | Evidence before debate | 5 | 3 | 17 |
| Both papers | Evidence after debate | 3 | 6 | 17 |

All reported direct matches were linked to findings that passed the original support-rating checks. There were eighteen human concerns overall. One root-paper concern required unavailable external literature and received no match in any condition. The shared evaluator image packet contained four original pages per paper. Manuscript-level assessability does not imply that every figure was visually available to the evaluator.

The development threshold required at least two additional supported direct matches on each paper without additional unsupported major allegations. The after-debate gains were zero for the lens paper and minus two for the root paper. The threshold fails even without the evaluation flags described below.

## What was actually tested

This workflow uses an experiment planner, deterministic source executor, evidence interpreter, and fresh debate. The planner and interpreter receive the full manuscript. The planner maps up to eight experiments and requests up to three tasks. The executor supplies page images, source extracts, searches, or small calculations with immutable receipts. The interpreter preserves up to eight candidates and selects five.

Debate receives all candidates, their cited source blocks, task records, and selected original page images. It receives an evidence packet rather than the complete manuscript, with two tools available for omitted context. Neither debate used those tools. Each preserved all seven candidates through explicit dispositions and selected five findings for the editor package.

The ordinary comparator is a capable single Sol reviewer with the full manuscript, the same planner-selected raw pages, and additional source tools. It is not a text-only one-shot baseline. The ordinary reviewers used five additional tool calls on the lens paper and four on the root paper. The completed workflow and ordinary reviewer each had six-operation allowances, but actual access and compute differed. Sharing planner-selected pages strengthens the comparator and prevents treating it as fully independent of planning.

Paper Scaffold provides advisory prose, readability, and word checks. Source-linked comments, guarded edits, candidate history, and task receipts work. PDF-only citation linkage remains unavailable. Broad literature discovery, full analysis reruns, and large datasets were outside this cycle.

## Findings from the source audit

On the lens paper, the evidence review requested quantitative normalization of central MEF immunoblots if performed. Debate merged that concern with sampling and replication concerns, retaining the replication request but dropping normalization. The evaluator changed the related human concern from direct to partial. The human concern specifically targets the small p-Shc difference, while the initial finding is broader. Its direct label is therefore a borderline automated judgment, not a secure one-point advantage.

On the root paper, debate promoted an existing candidate about whether imaging establishes transcytosis. That gained one direct match. It rejected the D6PK-to-auxin mechanism concern because a Results sentence calls the mechanism plausible and the Discussion acknowledges unresolved links. Two related human concerns about the central claim and temporal model then changed from direct to partial. The ledger therefore shows a selection tradeoff, not two independently discovered failures. This audit cannot establish that the rejection was scientifically wrong. A future adjudication should compare the wording of the title, results, and conclusion explicitly before dropping the underlying concern.

Three final root-paper findings focus on quantitative reporting or replication and map to the same broad human statistical-reporting concern. Those may be useful author comments, but occupying three of five slots limits distinct scientific coverage. Both methods also missed issues such as the Le-Cre design constraint in the lens paper and the BFA trafficking discrepancy in the root paper. Better final selection alone cannot recover concerns that were never investigated.

Both ordinary and evidence workflows found an internal inconsistency in the lens manuscript's Shp2 mutation description. The source uses different residue numbers or substitutions in the Results, figure legend, and Methods. This illustrates useful source-grounded checking beyond the human reference list. It is not a demonstrated PRA-specific advantage.

## Evaluation integrity

All generation artifacts were locked before either evaluator received human concerns. One fresh Sol evaluator per paper rated three anonymous conditions using prespecified label orders. Exact quotations, source identities, finding accounting, and reference accounting were checked mechanically. The same model family generated and judged the reviews, and no independent domain expert graded this cycle.

Two lens-paper support ratings failed the unchanged validator. The evaluator labeled the ordinary review's growth-factor concentration question and the corresponding debate question as justified clarifications while also declaring decisive evidence inaccessible. The raw judgments remain unchanged. They are unscored and excluded from supported counts. Neither was linked to a human match, so the reported overlap counts are unaffected.

The completion driver reused the existing evaluator response, recorded individual validation failures, and made only the remaining planned evaluation call. It did not relax the rubric or rerun the judge. This partial-scoring procedure is a disclosed post-result handling change. The original all-or-nothing validator failure remains preserved. Overall status is complete with evaluation flags.

Of thirty ratings, twenty-eight passed the checks and were labeled justified concerns by the automated judges. Two remain unvalidated. No validated rating was labeled an unsupported major allegation. This does not establish that all allegations are correct or that the true unsupported rate is zero. All thirty findings have exact manuscript anchors, which verifies placement rather than scientific truth.

## Usage

All eleven calls explicitly selected subscription-backed Sol at medium effort. The event stream did not separately expose the resolved model identity. No paid-credit purchase or fallback model was used. Preparation and orchestration tokens are outside this ledger.

| Stage across both papers | Observed total | Uncached input | Cached input | Output |
| --- | ---: | ---: | ---: | ---: |
| Ordinary reviewers | 363,076 | 109,135 | 246,784 | 7,157 |
| Evidence before debate, including planning | 197,404 | 153,244 | 29,440 | 14,720 |
| Evidence after debate, including planning | 267,204 | 217,580 | 29,440 | 20,184 |
| Two evaluations | 109,726 | 86,620 | 6,912 | 16,194 |
| Reused-paper engineering smoke | 37,393 | 33,788 | 0 | 3,605 |

Before-debate usage is included in after-debate usage and must not be added again. Total usage is ordinary plus after-debate plus evaluation plus smoke, or 777,399 observed tokens. PRA used fewer observed generation tokens overall, but more uncached input and output. These measurements do not establish a billing-cost or subscription-credit advantage.

The original 600,000 stop prevented further launches after eight calls reached 628,552 tokens. The user then approved a 1,000,000 stop solely to finish this same comparison. Completed request identities were reused. The final count is exactly eleven calls.

## Limitations and prospective changes

The two fresh papers are a convenience sample of experimental biology with substantive public reviews. Clean PDFs are disclosed derivatives of first-version reviewed preprints and may differ from confidential submissions. Source curators and the orchestrator were not blinded to public reviews. Generation sessions received clean source material without the human references. Prior training exposure to public reviews cannot be excluded. Related reference concerns and unbalanced label positions further limit inference.

An adapter repair occurred after the first planner output but before review generation. It expanded unambiguous existing block-ID ranges and rejected unsupported Boolean syntax in literal search. Original outputs and the initial study snapshot remain preserved. Both papers had one failed planned search, and both interpreters correctly reported the dependent task unresolved. Four other tasks completed. A generic invalid-receipt label must not be mistaken for a false model claim of completion.

The next revision should preserve the infrastructure and test targeted changes rather than increase the panel now:

1. Preserve each concern's concrete experimental target and requested resolution through merges. A disposition alone does not demonstrate that its useful content survived.
2. Evaluate disputed claims across title, results, and conclusion before rejection. Use a source lookup when the evidence packet is insufficient, and retain uncertainty when the check is unresolved.
3. Group related reporting questions under one selected issue where appropriate. Preserve the detailed local comments while reserving review slots for distinct scientific threats.
4. Repair the planner interface with explicit literal-search syntax and valid source IDs. Prioritize checks that can change an interpretation rather than trivial arithmetic. Distinguish honest unavailable evidence from malformed task completion.
5. Clarify the evaluator's prospective rule for consequential ambiguities versus confirmed errors. Do not rescore this run under a revised rule or treat development-paper improvements as fresh validation.

Use existing artifacts for offline regression checks first. Any new model comparison should have a fixed small budget and a frozen prospective protocol. This result does not justify a larger study or a claim that PRA outperforms a single agent.

## Saved outputs

The final source-linked reviews are available in the [lens viewer](http://127.0.0.1:38752/?review=panel) and [root viewer](http://127.0.0.1:38753/?review=panel).

The artifact directory is `runs/pra-evidence-workflow-v1`. It contains raw responses, immutable source receipts, generation locks, original and amended study snapshots, the approval and budget overlay, the completion-driver manifest, individual evaluation audits, and `results.json`. The fixed base protocol remains in `docs/pra-evidence-workflow-protocol.md`. Historical snapshots and results have not been rewritten.
