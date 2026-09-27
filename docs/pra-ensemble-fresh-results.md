# Two fresh manuscripts: incomplete development comparison

Both workflows generated reviews for the clinical and plant manuscripts. The clinical blind judge preferred the ensemble scientific draft. The plant blind judge was interrupted before producing an answer. This is one completed automated assessment, not a two-paper win or evidence of superiority.

## Design

The frozen comparison used Terra at medium reasoning. Two independent reviewers plus one debate were compared with one review plus two ordinary revisions. Both conditions had three logical generation calls and tool allowances of 4, 4, and 2. The initial draft was shared and counted once in actual study spending. Each final primary review allowed five findings and 900 comment words. Secondary comments were retained separately.

Two fresh non-computational development manuscripts were selected before generation and excluded from the future confirmatory sample. The study used published articles and supplements, not original submission versions. No human reviews were supplied or scored. One anonymous same-family automated judge was planned per paper, with reversed label order across papers. The confirmatory 24-paper study remains untouched.

## Observations

| Manuscript | Ensemble delivery | Sequential delivery | Blind assessment |
| --- | --- | --- | --- |
| Pregnancy insomnia trial, DOI 10.1371/journal.pone.0322931 | Failed on a missing new-candidate decision | Complete | Preferred the unchanged ensemble scientific draft in a forensic assessment |
| Carrot priming study, DOI 10.1371/journal.pone.0318753 | Complete | Complete | Unavailable, final judge interrupted |

For the clinical manuscript, both primary reviews received three justified-concern ratings and two justified-clarification ratings. Neither received an unsupported or unverifiable rating. The judge preferred ensemble because it additionally asked for reconciliation of conflicting depression reporting. It considered the sequential review more precise about the comparator limitation.

The second independent clinical reviewer added zero semantic issue groups beyond the shared first draft. All five supported groups remained in both final drafts. The judge grouped the added depression clause with the anxiety-reporting issue, so finding-level group counts do not capture this finer addition. There were also two unanchored unresolved ensemble hypotheses, which were explicitly unscored. These observations do not support increasing the reviewer count by default.

The clinical ensemble model emitted a new scientific candidate but omitted its required decision from the separate decisions array. Validation correctly blocked delivery. A predeclared forensic assessment compared the saved scientific comments without inventing the missing decision. Its preference is evidence about a draft, not successful pipeline delivery.

On the plant manuscript, the ensemble produced five primary findings and retained five anchored secondary candidates plus one unresolved hypothesis. The sequential workflow produced four primary findings and one secondary finding. The second independent reviewer raised additional questions about post hoc testing, concentration coding, tolerance interpretation, biochemical units, and statistical ranking. Debate retained the repeated-measurement question that sequential revision dropped. These are descriptive observations, not independently validated gains. No blind plant preference or supported-issue score is available.

## Spending and interruption

Twelve calls were attempted, with eleven completed receipts totaling 1,343,700 observed tokens. The final plant judge has only a start event, no answer, and no completion receipt. Its process is absent and its token usage is unknown. The known total is therefore a lower bound. No retry or additional paper was launched.

| Manuscript | Ensemble generation tokens | Sequential generation tokens |
| --- | ---: | ---: |
| Clinical | 325,001 | 456,177 |
| Plant | 275,951 | 323,707 |

These logical condition totals each include the shared initial draft. Actual study usage counts each shared call once. The completed clinical judge used 162,440 tokens. The failed clinical delivery still incurred generation cost.

The sequential prompts accidentally repeated the initial editor package's result map and audit metadata. This added approximately 210,000 characters on the clinical paper and 59,000 on the plant paper. Call counts and tool limits were matched, but prompt overhead was avoidable and could affect both cost and quality. The observed cost difference cannot establish an intrinsic efficiency advantage for ensemble.

## Post-study changes

After recording closure and verifying all frozen hashes, three offline changes were made:

1. New debate candidates must embed their decisions. Deterministic ID assignment removes the duplicated bookkeeping that caused the clinical failure. Missing or conflicting judgments still fail. No historical decision was fabricated.
2. Sequential revision receives scientific review history without redundant workspace maps, handle audits, or domain-profile metadata. Full artifacts remain on disk and source cards remain supplied separately.
3. Usage reporting now marks unmatched call starts and receipts as unknown, rather than requiring consumers to infer uncertainty from their counts.

The workflow version is now `ensemble-v2`. All 279 offline tests passed. These fixes have not been tested in another live trial. Frozen v1 source, inputs, failed delivery, prompts, and completed judgments remain preserved under `runs/pra-ensemble-fresh-v1`. Its `closure.json` records verification before production code changed. Rechecking production files against the old seal will now correctly report differences.

## Decision

Keep two independent reviewers plus debate as the development default. Preserve the complete issue inventory and avoid interpreting reviewer agreement as evidence. Before a larger study, the corrected workflow needs a completed small comparison with compact baseline prompts and reliable final assessment capture. The missing plant judgment, clinical delivery failure, baseline context overhead, and limited automated evaluation prevent treating this trial as publication-ready confirmation.
