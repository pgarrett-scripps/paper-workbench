# Codex development pilot results

The pilot completed ten papers, four review conditions, 80 scoring passes, and a
150-item blinded manual-audit package. The current results do not support a
claim that full PeerReviewAgents outperforms one-shot or single-agent review.
They also do not establish that it is worse. This was a development run with
unverified manuscript versions and substantial evaluation limitations.

## Preliminary comparison

Coverage is the unweighted mean across ten papers of the fraction of frozen
human-derived concerns matched by both automated scoring passes. Each review
contributes at most five extracted concerns and 900 quoted words. Published
human concerns are incomplete references, not scientific ground truth.

| Condition | Coverage confirmed by both passes | Mean quoted words scored | Mean generation tokens |
| --- | ---: | ---: | ---: |
| One-shot | 21.9% | 658 | 50,274 |
| Single agent with manuscript tools | 20.7% | 676 | 364,132 |
| Full PRA | 16.5% | 214 | 549,748 |
| PRA without debate | 18.0% | 237 | 354,291 |

Full PRA exceeded the single agent on two papers, tied on two, and trailed on six.
Its mean paired coverage difference was minus 4.2 percentage points. Full PRA
used about 1.51 times the single agent's recorded generation tokens. These are
exploratory observations. No significance or general-superiority claim is made.

Generation tokens include concern extraction. The no-debate estimate includes
its reused panel's original cost, representing standalone execution. Actual run
consumption counts each shared panel only once. Budgets and raw output lengths
were not matched. The same GPT-5.6 Sol model at medium effort generated reviews
and supplied both correlated scoring passes.

## What the pilot exposed

The evaluator could not verify 160 of 396 evidence quotations against the supplied
manuscript text, even after explicit PDF layout handling. A mismatch is not proof
that the criticism is wrong. It may reflect altered mathematics, paraphrasing,
layout, or another extraction problem. Support and false-major statistics are
withheld for 24 of 40 paper-condition combinations. Automated scientific accuracy
cannot be claimed from these outputs.

The extracted PRA packets were much shorter than the baseline packets. In one
saved no-debate example, the extractor selected short summary clauses while the
original letter contained longer discussion. The current normalization therefore
needs an audit for information loss before using it to compare workflows.
Identical maximum allowances did not produce equally detailed evidence packets.

The ten papers have prior development exposure. Their exact original submission
and first-review versions are unverified, and extracted text does not establish
figure access. Model familiarity with public papers remains possible. Multiple
runner revisions corrected validation and output-length problems during this
pilot. All prior runners, responses, and recovery provenance remain preserved.

## Completed artifacts

The active run is `/home/ty/Repos/insilico/runs/peerreview-validation-codex-v5/`.
It contains 40 successful review outputs, ten human-reference inventories with
160 concerns, 80 judgments, `report.json`, and `aggregate_summary.json`.

The 150-item audit is a simple random sample from 998 items: 28 reference
extractions, 94 matches, and 28 support assessments. Its ratings are empty.
The separate 160-entry unmatched-evidence queue is for diagnosis and triage,
not an additional required random sample or a request for 160 more human labels.

There were 300 recorded model calls and 13,955,691 observed tokens, including
reference extraction and evaluation. All recorded calls returned successfully.
This total excludes connection probes and counts cached input only once per
reported input total. It is not a dollar-cost estimate. Authentication used the
ChatGPT subscription, with no API keys, credit purchases, or usage resets.

Reproduce the aggregate summary with:

```bash
python3 /home/ty/Repos/insilico/experiments/peerreview_validation_analysis/summarize_pilot.py
```

## Recommended next step

Do not expand to the held-out study yet. First, use the existing audit to check
reference validity, semantic matching, and extraction fidelity. Make generation
or extraction preserve complete criticisms and their evidence in a common
structured format. Use manuscript line or span identifiers for evidence instead
of asking the evaluator to recreate long quotations. Retain raw predictions and
measure validation failure rates.

Then verify exact manuscript-review versions and figure availability, rerun a
small explicitly labeled development check, and freeze the final protocol before
collecting held-out results. Keep the hypothesis open to a negative result or a
more specific benefit such as better evidence checking. The current data do not
justify writing a paper around an assumed overall win.
