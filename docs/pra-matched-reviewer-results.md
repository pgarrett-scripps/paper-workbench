# Matched strong-reviewer experiment results

Subsequent integrity finding, September 17, 2026: the supplied TableQA manuscript
already answers parts of several human reference requests. Exact revision pairing
remains unverified. The numerical results below are preserved, but they must not
be treated as a reliable ranking of scientific review quality. See the separate
[benchmark integrity audit](pra-benchmark-integrity.md).

All three papers completed successfully. The full panel reports retained the
combined panel's confirmed reference coverage. Under the common top-five limit,
both panel variants beat the single reviewer on two papers and lost on one, with
a lower mean overall. Adding debate produced no additional measured coverage
over editor-only consolidation on any paper.

The prespecified screening outcome is improvement not demonstrated. This is a
three-paper development result, not a finding that debate cannot help or that
the broader panel reports are scientifically worse. The run is stopped.

## Matched comparison

Reviewer 1 is the saved strong tool-using review. New reviewers 2 and 3 used its
exact prompt, schema, manuscript bytes, read and search tools, explicit Sol model
selection, and medium effort. Their calls overlapped in time on every paper.
The two editor branches received the same complete reports and immutable finding
ledger, with identical prompts and schemas. Only one received the discussion.
Saved request files verify those matches.

Reviewer 1 was generated earlier, so model or service variation over time remains
possible. It was not selected from the new reviewers after seeing their scores.
The two new reviewer workflows made between 18 and 26 manuscript read or search
calls each, confirming that these were tool-using reviews rather than one-shot
structured responses.

## Primary result: at most five concerns and 900 words

The fractions below count reference concerns matched by both automated judges.
The reviewers and final packets may contain fewer than five concerns. No text was
truncated to fill the word budget.

| Paper | Single strong reviewer | Three reviewers + editor | Three reviewers + debate + editor |
| --- | ---: | ---: | ---: |
| Gradient-Weight Alignment | 3/17 | 4/17 | 4/17 |
| TableQA triples | 4/13 | 1/13 | 1/13 |
| Attention to Activation | 6/18 | 7/18 | 7/18 |
| Mean per-paper coverage | 27.2% | 23.4% | 23.4% |

Each panel branch won two comparisons and lost one against the single reviewer.
The mean difference was negative 3.9 percentage points. Debate and editor-only
consolidation tied on all three papers, including the identities of the confirmed
reference concerns, not merely their counts. They did change some selected
findings, priorities, and duplicate decisions.

All numbers come from this experiment's common candidate-pool scoring. They must
not be pooled with earlier experiments. The saved Gradient-Weight Alignment
review text was unchanged, but its measured overlap was 3/17 here versus 5/17 in
the previous experiment. This run indexed complete paragraphs differently and
used new scoring calls with a different candidate pool. We cannot separate those
effects from judge variability. This instability limits trust in small score
differences and needs audit before claims of scientific superiority.

## Full reports: preservation worked

| Paper | Single reviewer, full concerns | Full panel union | Full editor-only report | Full debated report |
| --- | ---: | ---: | ---: | ---: |
| Gradient-Weight Alignment | 3/17 | 5/17 | 5/17 | 5/17 |
| TableQA triples | 4/13 | 4/13 | 4/13 | 4/13 |
| Attention to Activation | 6/18 | 9/18 | 9/18 | 9/18 |

Both full report variants retained every confirmed reference match present in
the complete panel. Mean full-report coverage was 36.7%, versus 27.2% for the
single reviewer. This is a coverage diagnostic with more concerns and words,
not a fair equal-length superiority claim.

The editor-only reports retained 10, 7, and 10 findings. The debated reports
retained 11, 7, and 10. Their retained concern text ranged from 1,066 to 1,436
words. The original ledger contains 47 indexed findings, all preserved verbatim.
Duplicate records remain in the disposition appendix and are not counted as
retained concerns. The indexer included some minor concerns beyond the five main
sections in the original reviews. Raw review lengths ranged from 635 to 869 words.

TableQA explains the poor average top-five result. Concerns about contamination,
module details, and verification or regeneration procedures survived in the full
reports but fell below the top five. The editors prioritized verification logic,
mechanism measurement, attribution of gains, uncertainty, and possible test-set
selection. Some of those may be useful criticisms absent from the human reference
inventory. Lower overlap therefore does not itself establish poorer scientific
judgment. It does show that prioritization changes the measured result substantially.

## Debate and correctness

Discussion changed which findings were retained on some papers, but it added no
confirmed coverage in either the top-five or full-report comparison. No concern
was removed as fully answered in either branch. Most removals were duplicate
classifications. The experiment provides no measured reason to pay for debate
as the default stage on this small sample.

Both judges labeled every top-packet concern supported. No major concern was
jointly labeled contradicted, and all evidence-ID validation checks passed.
These are automated labels, not proof of correctness. One model generated and
judged the material, human-review overlap is incomplete, and no expert audit has
been performed. Exact historical manuscript-review pairing and figure access
remain unverified. One editor draw per branch also leaves stochastic variation
uncontrolled. The unfilled 15-concern audit package is preserved.

## Resource use

All 36 planned new calls succeeded. No retry was needed, no usage is missing,
and no extra calls were launched. Every call explicitly selected Sol at medium
effort through ChatGPT subscription. No API-key billing, paid credits, purchases,
resets, or model fallback were used. Actual resolved model identity is not exposed
by the CLI event stream.

New recorded usage totaled 2,942,996 tokens:

- 1,450,240 cached input tokens.
- 1,415,161 uncached input tokens.
- 77,595 output tokens.

The three inherited reviewer-1 generations totaled 1,042,405 observed tokens.
They were reused and are excluded from new usage. Estimated standalone workflow
totals below include that inherited generation and required indexing, but exclude
judging. They count shared work once per hypothetical standalone workflow.

| Workflow | Mean observed tokens per paper |
| --- | ---: |
| Strong reviewer alone | 347,468 |
| Three reviewers + editor | 1,047,185 |
| Three reviewers + debate + editor | 1,184,856 |

These totals include repeated cached input. They are not monetary charges,
credit-consumption ratios, or precise measures of reasoning effort. The actual
experiment reused the shared panel across branches rather than generating it twice.

## Practical implication

Keep the strong single-agent workflow as the economical default. A panel may be
useful when broader issue discovery is valuable enough to justify additional
review work. Preserve its full findings and make the top-five summary a navigation
aid rather than the only deliverable. This experiment does not support making
debate a default stage based on measured coverage.

Before another architectural change or larger run, use the saved audit material
to check concern correctness, prioritization, and the instability of automated
matching. No additional inference, study expansion, or deployment is scheduled.

## Reproducibility

All evidence is in `runs/pra-matched-reviewers-3paper-v1`. Key files are
`report.json`, `artifact_verification.json`, the per-paper `generation.json`,
both editor decisions and reports, original call requests, and `manual_audit.json`.
The frozen runner and dependency hashes pass verification. Source citations,
paragraph copying, all dispositions, final renderings, and top-packet limits were
checked after execution. The installed plugin remains unchanged.
