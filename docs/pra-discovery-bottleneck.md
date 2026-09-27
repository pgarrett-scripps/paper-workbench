# Discovery and retention diagnosis

This is a post-hoc inspection of the four-condition pilot and current validator. No new model calls were made. It separates recorded discovery, refinement, editorial selection and retention. Absence from a saved output does not establish what a model internally considered.

## Observed differences

| Case | Recorded path | Implication |
| --- | --- | --- |
| Behavioral interim-analysis concern | Present in both basic reviews, absent from the investigator findings, discarded hypotheses and coverage record, absent from debate | An initial recorded-discovery gap |
| Behavioral stress-table reporting concern | Absent from the investigator, added by ordinary workspace revision, absent from debate | A second pass can add an issue, but the debate has a structural restriction |
| Ecology ordination interpretation | Present in investigator and debate, omitted as a separate concern by ordinary workspace revision | Editorial selection differs, even with a shared first draft |
| Public-health complex sampling | Present in basic first pass, absent from its second-pass findings and discarded hypotheses | A concern can disappear during ordinary revision too |
| Molecular interaction testing | Present in investigator, retained as secondary by debate, omitted from the ordinary final list with a stated reason | Absence from the main report does not necessarily mean lost information |

## Structural restriction

The debate requires exactly one decision for every existing ledger issue and requires every selected final finding to contain a preserved component from that ledger. It has no explicit new-candidate mechanism. It can restore a previously discarded hypothesis, but a genuinely distinct new issue has no valid provenance path into the final review.

An offline diagnostic confirmed this restriction. The original four-finding behavioral debate passed validation. Appending the independently anchored stress-table finding from ordinary revision, still within the five-finding ceiling, failed with `Selected finding has no preserved source component`. The probe did not change any model output and did not establish the scientific correctness of that extra finding. Its record is `runs/pra-four-condition-v1/posthoc-audits/discovery-gate.json`.

This rule was built to prevent silent loss or invented issue lineage. Its consequence is that the debate is principally an adjudication stage, with discovery bounded by the initial ledger. The pipeline currently has one investigator and one fresh model session that evaluates opposing arguments. It is not a panel of independent discovering reviewers.

## What remains uncertain

Each condition was generated once per paper. Prompt changes, supplied diagnostics, output structure and model variability are confounded. The pilot cannot estimate how much issue variation is random. No optional tools were used, so differing database retrievals do not explain these differences.

The five-finding final ceiling measures a selected report, not all potentially useful concerns. The investigator can emit ten candidates but actually emitted only four to six in these papers. Expanding that numerical ceiling alone would not resolve the observed omissions.

## Recommended next version

Use two independent whole-paper discovery passes before exposing either reviewer to the other's findings. Preserve every proposed issue with its own source evidence and origin. Deduplicate by the actual scientific concern and requested resolution, not merely a shared paragraph. Debate the combined inventory, check author defenses and preserve supported secondary or unresolved comments separately from the short summary.

Add an explicit path for newly discovered issues during checking. New issues need fresh source anchors and their own provenance and validation. They must not be squeezed into an unrelated earlier component to pass the current guard. Keep scientific status separate from editorial priority.

Start with two discoverers. The relevant outcome is additional supported, consequential, nonduplicate concerns per extra token, together with unsupported allegations and information lost through synthesis. More independent outputs can also produce duplicate or incorrect concerns. Neither reviewer count nor a pass with no new findings proves exhaustive coverage.

The cheapest next pilot could combine the already saved basic and investigator drafts from one paper, run one debate over their union, and obtain one blind assessment against existing comparators. That would test the potential of combining independent discoveries without new discovery calls. It would be a development comparison with unequal total generation effort, not a publication-ready estimate of ensemble superiority. A later controlled study should compare equal call or measured token budgets and use papers untouched by tuning.
