# Four-addition development retest results

The result is mixed. One blind model judge preferred the earlier PRA review for ecology. The other preferred updated PRA for health. Useful concerns were gained, other concerns were missed, and three of four new review pipelines failed strict evidence-format validation. This does not establish an overall improvement or readiness to ship the updated workflow.

## Comparison

Two previously used manuscripts were reviewed again using Sol at medium effort. Each anonymous comparison contained the saved earlier PRA review, a new single reviewer with current tools, and the updated investigator-plus-debate review. One fresh-context Sol judge assessed each paper without condition names or prior results. These are model assessments, not independent human expert reviews.

| Paper | Preferred content | Main reason |
| --- | --- | --- |
| Plant-pollinator ecology, PLOS ONE 0309939 | Earlier PRA | Stronger balance of design, selection, exclusion and claim-scope concerns. It explicitly identified an interaction-model discrepancy the new reviews did not explain. |
| Uganda mHealth trial, PLOS ONE 0308923 | Updated PRA | Balanced coverage of missing outcomes, eligibility inconsistency, effect labeling, adherence claims and registration uncertainty. |

Each review contained five findings. All 15 ecology ratings and 14 of 15 health ratings passed reference validation. All 29 scored findings were judged justified concerns or clarifications, with no scored unsupported allegations or excessive requests. This is a judgment from one model per paper, not proof of correctness. The unscored health rating copied the single review's malformed registry quotation. It remains unscored, even though the dates themselves are supported. The health preference is retained as the judge's raw preference with that audit limitation.

The judges selected an overall favorite among three reviews. They did not provide a complete pairwise ranking. The single reviewer not being selected as the overall favorite does not establish that updated PRA beat it on both papers.

## What improved and what was lost

- Ecology's figure/model mismatch was recovered by both updated conditions and retained through debate. Figure 3 names a simple regression but cites the multiple-regression table. Its plotted equation and fit statistic require reconciliation. Different standardized and partial coefficients alone do not establish an error.
- Both updated health conditions identified the conflict between eligibility requiring at most six months of ART and a baseline category containing 75 participants with more than six months of ART. Updated PRA kept this as a clarification rather than declaring an enrollment violation.
- Health debate retained the investigator's five main issues and carefully distinguished uncertain historical registration from proven outcome switching.
- The updated health investigator did not explicitly identify the concern about adjusting for the post-treatment variable “simply forgot.” The current single reviewer and earlier PRA did. The omission existed before debate.
- The earlier health PRA's baseline denominator and arm-count correction was absent from both updated conditions. The updated single reviewer instead found a different inconsistency in missed-pill questionnaire counts.
- Ecology's earlier PRA explicitly reconciled the Results' three interactions with Table 2's two-interaction model description. Updated PRA asked generally about interaction strategy but lost that concrete discrepancy.

The coordinator checked these differences against manuscript blocks and the original ecology figure page. This was a nonblind source check, preserved separately from the judge ratings.

## Delivery failures

| New condition | First-pass result | Failure |
| --- | --- | --- |
| Ecology single | Validated deliverable | None |
| Ecology PRA | Blocked after completed debate | A component quotation used “an arbitrary” where the source says “as arbitrary.” |
| Health single | Blocked after completed review | Correct registry dates were combined in an order that was not an exact source quotation. |
| Health PRA | Blocked after completed debate | An eligible external source ID was also placed in manuscript-only `evidence_blocks`. |

All raw content was preserved. A documented amendment made before judging allowed diagnostic content comparisons without repairing or certifying the blocked reviews. Updated PRA therefore produced zero validated final packages from two attempts, despite one preferred raw review. The updated single condition produced one validated package from two attempts. Two cases do not establish a population failure rate or prove the additions caused these failures, but these are real observed reliability problems.

## Which additions were exercised

Both current conditions received the result map, shared original figure pages, domain guidance and offline Paper Scaffold checks. Ecology made no optional tool calls. The health single reviewer made one current-registry lookup and one historical-registration request. The health investigator made one current-registry lookup and two historical-registration requests. Both debate stages made no optional tool calls.

No historical snapshot set was configured, and every historical request correctly returned unavailable. Neither review converted that absence into proof of outcome switching. No reviewer called `inspect_results`, `record_comparison`, identifier resolution or literature search. Result maps were present in the initial context, but the numerical comparison tool was not used. Broad literature discovery remains untested here.

Scaffold word counts, readability and prose checks ran as advisory checks. Extracted citation linkage was checked. Scaffold's BibTeX citation checker was unavailable because these extracted workspaces do not contain the required BibTeX entries and citation keys. Citation validity or missing-literature coverage was not established by this study.

The epistemic debate ledger was generated, but strict validation blocked both new PRA final packages. The prospective evaluation infrastructure was not used to label these known manuscripts as held-out validation. This was deliberately a development retest.

## Cost and integrity

Eight model calls completed with known usage, no retries and no additional judge: 484,230 observed generation tokens and 86,426 judge tokens, totaling 570,656. This is input plus output usage, not a dollar charge or an uncached-token count. Current PRA generation used 297,403 tokens across the two papers versus 186,827 for current single reviews, about 1.59 times as much.

No paid API calls or reset redemptions were used. Rounded account-wide weekly usage moved from 32% to 33%, which cannot be attributed precisely to this experiment. Frozen generation source, paper inputs, anonymous accounting and all eight receipts were verified at closeout. The original domain-panel artifacts were left unchanged.

## Next changes supported by this test

1. Replace repeated model-written quotations with typed evidence handles and exact source spans. Distinguish manuscript blocks from external source cards in the schema. Keep strict checks and record any correction, without silently accepting near matches.
2. Preserve a broader candidate inventory before selecting the final five. Record supported secondary concerns even when they do not fit in the main review. Track discovery omissions separately from debate removals.
3. Give the existing investigator a small design-specific checklist. For trials, check adjustment timing, analysis populations and denominator consistency. For ecology, reconcile model descriptions, figure captions and interactions. Use the current call budget before adding more agents.
4. Make unavailable historical and citation capabilities explicit before generation, avoiding repeat requests to an unconfigured resource. Add the extracted-reference to BibTeX bridge before claiming full citation-check coverage.
5. Test these reliability fixes offline with the preserved failures. Then freeze the workflow for a small genuinely unseen comparison. A larger benchmark is premature until the delivery gates are dependable.

The immediate priority is reliable evidence handling and coverage retention. This retest does not support adding more domains or more model stages as the next intervention.

## Artifacts

- Protocol: [pra-additions-retest-protocol.md](pra-additions-retest-protocol.md)
- Machine-readable summary: `runs/pra-additions-retest-v1/summary.json`
- Generation freeze: `runs/pra-additions-retest-v1/freeze.json`
- Diagnostic amendment: `runs/pra-additions-retest-v1/diagnostic-evaluation-amendment-v2.json`
- Coordinator source checks: `runs/pra-additions-retest-v1/coordinator-source-audit-final.json`
- Per-paper judge output, labels, audits and diagnostic results: `runs/pra-additions-retest-v1/panel/{ecology,health}/evaluation/`
- Unmodified new model responses and reference diagnostics: `runs/pra-additions-retest-v1/panel/{ecology,health}/{single,panel}/`

These reused papers informed development. Sampling variation, a small sample, unequal generation compute and one same-family model judge per paper prevent causal feature attribution or a superiority claim.
