# Two-paper workspace pilot results

The approved two-paper pilot is complete. Adding debate produced no measured improvement over the same investigator working with manuscript tools and Paper Scaffold diagnostics. This result does not establish that the workspace improves on an ordinary single-agent review.

## Results

Each paper received one Sol medium investigation and one Sol medium debate of that investigation. The original investigator output was reused as the baseline. Each condition selected at most five findings. All generation outputs were frozen before one condition-label-blinded Sol evaluator assessed each paper. Human reference concerns were frozen before generation and hidden from the reviewers.

| Manuscript | Human concerns | Investigator direct | Investigator partial | Debate direct | Debate partial |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rice drought and microbiome selection | 8 | 3 | 3 | 3 | 3 |
| Synaptic vesicle replenishment | 15 | 3 | 3 | 3 | 3 |

Direct and partial matches are separate categories. All 23 human concerns were classified as manuscript-assessable. Related concerns can match the same AI finding, so the counts are not independent observations. Related control concerns were preserved rather than regrouped after seeing results.

The evaluator rated all five findings in each condition as supported. This is one automated judgment per paper, not independent verification of correctness or evidence of a zero false-positive rate. Exact quotation and item-accounting checks constrain the evaluator but cannot establish scientific validity.

Debate retained all ten original findings. All selected findings have source locations. There are no unresolved placement queues or invalid source dispositions. The rice panel contains comments only. The synaptic panel includes one wording edit. Original findings and debate dispositions remain available in the export.

Both rice reviews found a numerical inconsistency beyond the frozen human concern list. Manuscript page 16 says that a balance contains 32 ASVs, followed by numerator and denominator counts of 17 and 25. An unblinded visual check confirmed the discrepancy. This supports asking for reconciliation, without assuming which number should change.

Both rice reviews missed the request to benchmark results against healthy, well-watered plants. Both synaptic reviews missed the request for conductance traces needed to assess the capacitance measurements. Their comments about animal-level replication also do not address the distinct human concern about paired recordings versus separate controls.

These examples suggest that discovering specific experimental and measurement concerns remains a bottleneck. Debate preserved and refined existing concerns but did not recover additional human concerns here. This is a development observation, not a general finding about debate.

## Actual Paper Scaffold reuse

The integration directly calls `readability.metrics` and `prose_check.check` from the local Paper Scaffold checkout. The recorded version is 3.24.2 at revision `bc4ef429400ae9fc12320f7b78f124079a4bf4d3`. Reports preserve tool hashes and environment provenance.

Reviewers receive word counts, readability measurements, and source-linked prose advisories. Reports include overall, section, document, and block measurements. Prose checks cover doubled words, spelling, long sentences, verbose phrases, double hedges, repeated openers, and repeated words. Technical terminology can produce unhelpful warnings. These are advisory signals, not scientific defects.

The rice report contains 12,098 prose words and 116 advisories. The synaptic report contains 6,195 prose words and 71 advisories. Counts exclude recognized headings, references, and tables but include captions and supplementary prose. PDF classification is provisional, so these are not authoritative journal word counts.

Citation integration is incomplete. Scaffold's bibliography checker expects BibTeX records and citation keys that these PDF imports do not reliably provide. Structured citation-ID linkage is available for XML inputs but unavailable for both pilot PDFs. Individual reference identity lookup through Crossref remains available. It does not establish that a reference supports a claim. Literature search was disabled to reduce access to public reviews, so this pilot does not evaluate missing-literature discovery.

## Source integrity and limitations

The papers are experimental biology studies with public first-round reviews. Source selection, URLs, dates, hashes, and derivations are recorded in `runs/pra-workspace-two-paper-v1/source-selection.json`.

The eLife version-one PDFs combine manuscripts with assessments and reviews. Review material was removed using true PDF redactions and removal of review-only pages. Scientific text preservation was checked, including on mixed pages. The clean workspaces contain 48 rice pages and 19 synaptic pages. Human reviews remain outside the generation workspaces.

These are journal-formatted derivatives of original preprints, not byte-identical private submissions. The bioRxiv PDF endpoint returned HTTP 429 during preparation. Equivalence to the private submission cannot be independently established. Public manuscripts and reviews may also have appeared in training. Prompt isolation cannot eliminate that risk.

Two papers and one automated evaluator per paper cannot establish generalization, statistical significance, or expert-level correctness. Manual checks were purposive and unblinded. No plain one-shot baseline, Scaffold ablation, or equal-budget comparison was run. The five-finding selection limit also constrains coverage. These papers are now development material and should not be reused as a clean held-out validation set.

## Cost and operational amendment

Exactly six successful model calls used explicit CLI selection of Sol medium. The event stream did not expose a separately resolved model identity. There were no inference retries, replacement papers, or extra review conditions.

| Stage | Observed tokens |
| --- | ---: |
| Two investigations | 400,279 |
| Two debates | 53,860 |
| Two evaluations | 86,268 |
| Total | 540,407 |

The total includes 519,156 input tokens, of which 295,680 were cached, and 21,251 output tokens. Cached tokens are already included in the input total. Preparation, implementation agents, and the coordinating task are excluded. Subscription usage percentages are rounded and shared across the account, so they cannot provide a precise study cost.

The original 400,000 observed-token stop halted execution after three completed calls. The first investigation alone used 304,679 tokens. An operational amendment raised the stop to 700,000 to finish the authorized pilot. The six-call cap, scientific inputs, prompts, conditions, and evaluation rules were unchanged. Completed responses were reused from cache without repeated inference. See `runs/pra-workspace-two-paper-v1/budget-amendment.json`.

## Engineering checks and next step

The 39-test suite passed. Source sanitization, human reference quotations, evaluation accounting, output anchoring, and live panel exports were checked. Neither live export contains accepted manuscript changes. Saved audits distinguish engineering checks from scientific adjudication.

The next useful change is a targeted discovery pass for experimental controls, comparators, measurement validity, treatment timing, experimental units, and numerical consistency. It should produce investigable questions tied to passages and figures. Domain-specific checks need selective activation rather than a universal checklist. Debate can remain as an evidence challenge and reconciliation step, but this pilot provides no reason to add debate rounds.

Before a larger study, compare the revised workspace against a same-model ordinary review with explicit, comparable budgets on fresh papers. No additional trial has been launched or larger study authorized.

Machine-readable results: `runs/pra-workspace-two-paper-v1/results.json`.

Local viewers: [rice review](http://127.0.0.1:38746/?review=panel) and [synaptic review](http://127.0.0.1:38747/?review=panel).
