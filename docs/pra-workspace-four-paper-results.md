# Four-paper workspace panel results

The approved panel is complete. Debate produced no measured improvement on any of the four fresh papers. The investigator and its debate each directly matched 7 of 51 frozen human concerns and partially matched another 10. These are descriptive automated judgments, not expert validation or a comparison against an ordinary single-agent reviewer.

## Results by paper

| Paper | Frozen human concerns | Investigator direct | Investigator partial | Debate direct | Debate partial |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tropical plant diversity and herbivory | 8 | 1 | 3 | 1 | 3 |
| Pectin and RALF1 signalling | 9 | 0 | 1 | 0 | 1 |
| Wound-induced syncytia | 15 | 3 | 1 | 3 | 1 |
| Mitosis under confinement | 19 | 3 | 5 | 3 | 5 |
| Total | 51 | 7 | 10 | 7 | 10 |

Direct and partial matches are separate categories. A finding can match multiple related human concerns. The counts are not independent observations, and four papers do not support a generalization or significance claim. Scores from the earlier two-paper protocol should not be pooled with this run or used to infer that the new workflow improved or worsened performance on different manuscripts.

All four debates retained all five original findings. There were no added final findings, dropped findings, or unresolved handoff queues. All 20 final findings were questions, with valid source anchors. No wording edits were proposed. The evaluator classified every selected finding in each condition as supported. That classification includes reasonable requests for clarification and does not prove the allegation, its importance, its novelty, or its usefulness to an editor. It is not a measured zero false-positive rate.

## What the system actually did

All manuscripts received the real Paper Scaffold prose and readability checks. Their reports were supplied to the investigators. The new six-area coverage record was produced for all four papers. Of 24 area records, 23 passed the structural and quotation checks as examined. One replication entry contained a mismatched source quotation and was marked unresolved. That guard worked without another model call.

None of the eight reviewing calls invoked a manuscript investigation tool. The tool servers initialized, but the event receipts contain zero tool calls. The models used the supplied text, captions, and diagnostics. They did not inspect original PDF pages, supplementary figures, or external references through tools. No images therefore entered the debate or evaluator packets.

This is a material limitation. The run evaluates text-based review with advisory diagnostics and a coverage record, followed by debate. It does not demonstrate effective active evidence gathering or a benefit from figure inspection. The lower token usage cannot be attributed to a general efficiency improvement because the papers differ and tool use was absent.

## Examples from the audit

The ecology reviews questioned whether damage categories justify inferred herbivore diversity, matching a human concern. They missed the human concern about plot isolation and herbivore movement.

The plant reviews questioned the interpretation of a binding fit as high avidity. The human concern was more specific: the tension between that mechanism and an oligogalacturonide titration result. The partial match is appropriate. Questions about the binding assay did not cover the human request for missing concentration and timing details in the biological titration experiment. The reviews also missed questions about inducible PMEI3 expression.

The wound-repair reviews questioned whether fusion causes faster closure and whether labeled actin redistribution establishes a functional benefit. These matched human concerns. They did not identify several specific mechanistic and figure-level questions raised by the humans.

The confinement reviews challenged the indirect inference from lamin folding to nuclear tension, matching the human request for an independent measurement. They did not request the nuclear-to-cytoplasmic volume comparison raised by a human reviewer.

These were purposive, unblinded text checks by the coordinating task. They are not independent domain-expert adjudication. An absent human match does not by itself make an AI finding incorrect.

## Reference-list audit and sensitivity

The frozen preparation marked all 51 concerns manuscript-assessable. Subsequent inspection found two broad ecology presentation complaints, concerning results complexity and discussion length, that do not fit the intended scientific focus well. A wound-repair concern also describes the content of videos that were not included in the input. Its assessability classification was too broad for the supplied evidence.

The original reference lists and primary scores remain unchanged. A separately recorded post hoc sensitivity excludes ecology h7 and h8 and wound-repair h3. Both conditions then have 7 direct and 10 partial matches out of 48 concerns. All three excluded items were unmatched, so the conclusion of no incremental debate benefit is unchanged. This sensitivity is not a replacement primary analysis or a complete expert audit of the reference set. Reference curation needs stronger checks before an efficacy study.

## Sources and controls

The four source versions are [eLife 86988v1](https://elifesciences.org/reviewed-preprints/86988v1), [eLife 96943v1](https://elifesciences.org/reviewed-preprints/96943v1), [eLife 92593v1](https://elifesciences.org/reviewed-preprints/92593v1), and [eLife 94975v1](https://elifesciences.org/reviewed-preprints/94975v1). No selected DOI appeared in previous run JSON metadata.

The inputs are disclosed manuscript-only derivatives of eLife first-round reviewed-preprint PDFs. The plant paper corresponds to bioRxiv version 2 as used in the first eLife round. Public assessments, reviews, and embedded author responses were excluded from generation. Original files, dates, hashes, and redaction records are preserved. Untouched-page text checks and representative visual QA passed. Equivalence to private submission files cannot be independently established.

The clean PDFs contain 28, 21, 25, and 22 pages. Imported text contains 8,597, 7,524, 9,540, and 8,922 words respectively. Scaffold's prose counts use a different convention and provisional section classification. No separate video supplements or large datasets were downloaded. Citation checking remains limited, and literature search was disabled to reduce access to public review history. Public sources may have been seen during model training.

All eight generation outputs were locked before evaluation. One Sol evaluator assessed each paper with anonymous A and B labels. Each condition was labeled A on two papers. Exact source quotations, item accounting, and reference hashes were validated. The review style could still reveal the condition. There was no ordinary-review baseline, Scaffold ablation, equal-budget comparison, or independent human grading.

## Cost and verification

| Stage | Successful calls | Observed tokens |
| --- | ---: | ---: |
| Investigators | 4 | 143,867 |
| Debates | 4 | 95,487 |
| Evaluators | 4 | 140,666 |
| Total | 12 | 380,020 |

Usage comprises 340,720 input and 39,300 output tokens. The input total already includes 7,680 cached tokens. Source-preparation agents and coordination are excluded from these review-run totals. Sol medium was selected explicitly on every CLI invocation. A separately resolved model identity was unavailable in the event stream.

The run stayed below the original 1,200,000 observed-token stop. There were no retries, cap amendments, unknown-usage calls, paid API calls, or model substitutions. Account checks before and after showed zero paid credits. Both reported 5% used in the shared account window, a rounded figure that cannot establish a precise study charge.

The 45-test offline suite passed. The final study-specific tests also passed after the plan-hash guard was added. All four live exports preserve source text, five original findings, five valid dispositions, and six coverage entries. Frozen code, plan, generated outputs, and human reference hashes were checked after completion.

## Decision

This panel does not justify a claim that PRA beats a single agent. It also does not justify expanding the same experiment further yet. The next development target is explicit, verifiable evidence tasks using original figures and tables, with records of what was actually inspected. Before a larger efficacy study, the system also needs a stronger human-reference audit and a same-model ordinary-review comparator with a defined budget.

No further model trials are running. Raw reviews, scores, and the negative result are preserved in `runs/pra-workspace-four-paper-v1`. Main files are `results.json`, `analysis-summary.json`, `manual-audit.json`, and `engineering-qa.json`.

Local review viewers: [ecology](http://127.0.0.1:38748/?review=panel), [plant signalling](http://127.0.0.1:38749/?review=panel), [wound repair](http://127.0.0.1:38750/?review=panel), and [cell division](http://127.0.0.1:38751/?review=panel).
