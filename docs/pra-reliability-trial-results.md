# Evidence and coverage repair results

The changes are implemented. The completed health comparison is promising, but the two-paper trial does not establish overall superiority. Health PRA passed validation and was preferred by the blind model judge. Ecology PRA stopped at an invalid advisory coverage reference before debate, so that comparison remains unjudged. The resulting reliability and inventory bugs were fixed afterward and tested offline without replacing the original trial outcomes.

## Implemented behavior

- Models select typed source handles. The system expands exact source spans and records their hashes and offsets. Scientific finding and debate references remain strict.
- The investigator can retain up to ten candidates within the existing comment budget. Debate selects up to five main findings and keeps supported secondary concerns accessible through the editor package and draft export.
- Design-specific checks cover adjustment timing, analysis populations, denominators, ecological units, model descriptions and figure reconciliation. They are conditional checks, not quotas for criticism.
- Manuscript references are restricted to a finite output vocabulary. Invalid advisory coverage is explicitly unresolved and audited rather than causing valid findings to disappear.
- Fully resolved hypotheses stay separate from supported secondary concerns.

The last two changes followed the live trial and were validated by offline replay. They have not yet received another live benchmark.

## Fresh comparison

| Paper | Single reviewer | PRA | Blind preference |
| --- | --- | --- | --- |
| Online exercise pilot randomized trial | Five validated findings | Eight investigator candidates, five validated final findings | PRA preferred, with one judge rating unscored |
| Honey bee field-warming experiment | Five validated findings | Nine emitted candidates, then stopped on a coverage reference | No comparison performed |

The source papers are the [online exercise trial](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0312992) and the [honey bee warming experiment](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0314791). They were absent from the local corpus inventory of 29 distinct manuscripts. That does not establish absence from model training data.

The conditions shared manuscripts, small scientific supplements, initial figure pages, domain guidance, advisory checks, current-record packets and total tool budgets. PRA used two generation calls instead of one. Both used Sol at medium effort. No human review history was used. The health judge assessed anonymous main reviews in a fresh model context.

## Why health PRA was preferred

Both reviews identified the central analysis-population, missing-data, anxiety-scale, efficacy and maintenance concerns. PRA combined the related efficacy and maintenance concerns, retaining their substance, and added a distinct question from the supplied protocol: whether planned depression-score monitoring and triggered contact were implemented equally across arms and might have affected the depression comparison.

The source supports asking this question. Protocol block `b0173` describes contact with participants and emergency contacts following a depression score above five. Blocks `b0176` and `b0177`, split by a page boundary, describe weekly checking. The concern remains uncertainty about implementation and differential exposure. It does not establish that a co-intervention actually biased the trial.

The judge preferred PRA for that added issue, but concatenated text from the two protocol blocks into one quotation attributed only to `b0177`. The exact-reference auditor therefore left that finding's rating unscored. The coordinator separately verified the premise against the protocol. That nonblind source check does not replace the invalid blind rating or convert it into independent expert validation.

Nine of ten judge ratings passed reference validation. All nine were assessed as justified concerns, with no scored unsupported allegation or excessive request. The remaining raw rating called the monitoring issue a justified clarification but is excluded from the validated counts. This is one model preference with a citation error on its preference-driving issue, not a robust win rate.

## What happened to the extra candidates

Health's eight investigator candidates became five final findings:

- Six candidates were represented in the main review, with efficacy and maintenance merged into one finding.
- Two remained supported secondary concerns: the feasibility satisfaction denominator and the scope of qualitative benefit claims from program completers.
- Three previously discarded hypotheses were resolved. They concerned allocation counts, masking and injury attribution.

The original inventory incorrectly labeled those three fully resolved hypotheses as supported secondary clarifications because it consulted the scientific-status label before component resolution. The final code now checks complete resolution first. Offline replay yields six selected candidates, two supported secondary concerns and three resolved hypotheses, without changing the model's original text or decisions. The two secondary concerns remain linked to their full anchored source findings.

## Ecology failure and subsequent repair

Ecology's investigator produced nine candidates but invented one coverage-note handle that was not in the supplied registry. The live code stopped, preserving the raw response. No debate, judge or replacement generation was run for that paper.

The follow-up code addresses both causes. Its output schema permits only supplied manuscript IDs. It also treats coverage as an advisory self-report rather than a reason to discard independently valid findings. A malformed coverage record becomes visibly invalid and unresolved, with its original record preserved in the audit. References supporting actual findings or debate decisions still fail closed.

Offline replay preserved all nine anchored ecology candidates and marked exactly one coverage area invalid. The original trial remains a failed PRA delivery, and no ecology preference is reported. This replay checks engineering behavior, not scientific review quality.

## Validation and cost

All 233 offline tests pass, including source identity, typed references, dynamic source-card handling, ambiguous anchors, edit safety, candidate retention, resolution classification and draft export. The finite output schema was also checked against the four saved initial model responses. It accepted the valid responses and rejected the exact malformed ecology reference. Original failed artifacts were not repaired.

Six experimental model calls were used from the eight-call allowance, totaling 389,055 observed input and output tokens. All usage receipts are known. Health PRA generation used 145,807 tokens versus 70,719 for its single reviewer, about 2.06 times as many. The remaining two calls were unused. There were no model retries, paid API calls or reset redemptions. Experimental receipts exclude orchestration and development-agent work. Rounded account-wide usage moved from 34% before generation to 36% afterward and is not a precise task attribution.

The first health judge dispatch was blocked locally before any inference because the legacy per-paper runtime rejects the outer runner's held-out flag. A recorded dispatch amendment omitted that legacy field for the single-paper judge invocation. The prompt hash, labels, schema, resources, model, effort and budgets were unchanged. Exactly one judge inference occurred.

Both prospective seals passed verification before follow-up code edits. Frozen generation and evaluator source was archived, and every sealed file hash was checked again using the archived code where the live code had subsequently changed. Original generation output, judge ratings, anonymous mappings and failure status remain intact.

## Interpretation

The candidate-preservation design worked in the completed health case and produced a useful additional protocol-based question. Delivery still failed on the other paper, and the blind judge's key supporting quotation failed validation. These results justify keeping the changes and their regression fixes, but not claiming that PRA reliably beats a single reviewer.

The next live test should use the final repaired version with a predeclared small sample and the same resource and cost accounting. No additional live trial was run after the post-trial repairs in order to preserve the bounded budget.

## Artifacts

- Protocol: [pra-reliability-trial-protocol.md](pra-reliability-trial-protocol.md)
- Implementation behavior: [pra-evidence-handles.md](pra-evidence-handles.md)
- Machine-readable summary: `runs/pra-reliability-trial-v1/summary.json`
- Frozen source: `runs/pra-reliability-trial-v1/frozen-source/`
- Source checks: `runs/pra-reliability-trial-v1/coordinator-source-audit.json`
- Original health comparison: `runs/pra-reliability-trial-v1/panel/health/evaluation/`
- Original ecology failure: `runs/pra-reliability-trial-v1/panel/ecology/pra/progress.json`
- Clearly separate offline replays: `runs/pra-reliability-trial-v1/posttrial-replay/`
