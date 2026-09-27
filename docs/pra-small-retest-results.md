# Three-paper PRA retest results

The revision did not improve observed human-review coverage. Original PRA scored
higher on all three papers. Against the single agent, revised PRA tied on one
paper and scored lower on one. The third paired comparison is incomplete because
one scoring pass timed out. The formal screening outcome is inconclusive because
quality checks failed. These are exploratory development results.

All inference explicitly selected Sol at medium effort. The test is stopped.
No larger run or production plugin change followed this result.

## Coverage

Each fraction counts human-derived concerns matched by both automated scoring
passes, divided by the paper's reference inventory. All three methods used the
same new extractor and scorer. Earlier pilot scores are not pooled here.

| Paper | Revised PRA | Original PRA | Single agent |
| --- | --- | --- | --- |
| Gradient-Weight Alignment | 2/17, 11.8% | 3/17, 17.6% | Missing second pass |
| TableQA triples | 2/13, 15.4% | 7/13, 53.8% | 2/13, 15.4% |
| Attention to Activation | 4/18, 22.2% | 5/18, 27.8% | 6/18, 33.3% |

Across all three papers, mean coverage was 16.5% for revised PRA and 33.1% for
original PRA. Revised PRA lost all three comparisons, by an average 16.6 percentage
points. Across the same two papers with complete single-agent scoring, revised
PRA averaged 18.8% and the single agent 24.4%, a difference of 5.6 points.

The missing single-agent pass is not imputed. Its first pass matched 7 of 17
reference concerns, so that paper's eventual intersection could range from 0 to
7. The three-paper single-agent mean is therefore bounded by 16.2% and 30.0%.
These are logical missing-data bounds, not confidence intervals. We cannot give
a complete three-paper ranking against the single agent.

Human-review overlap measures coverage, not correctness. A useful criticism may
be absent from the human reviews, and human reviewers can be wrong. These scores
do not establish that the revised criticisms are scientifically worse.

## What worked and where information was lost

All three runs completed five specialists, two auditors, and both debate rounds.
All 57 original findings have preserved records and final dispositions: 15 were
selected, 13 merged, and 29 dropped. Every selected finding retained its original
claim, scientific importance, remedy, and limitations. The saved review packets
are exact source copies and meet the common five-concern and 900-word limits.

The revised packets averaged 699 words, versus 437 for original PRA and 629 for
the single agent. Short extracted summaries therefore do not explain this
revision's lower observed coverage.

The disposition records identify final selection as a plausible bottleneck:

- For Gradient-Weight Alignment, specialists identified missing training-only
  baselines and unclear validation splits. The editor explicitly dropped these
  in favor of selected mathematical and implementation criticisms.
- For TableQA, the ledger included contamination, efficiency, applicability, and
  novelty concerns. The editor dropped these as lower priority while selecting
  mechanism validity, matched comparisons, missing transformation details,
  uncertainty, and possible test-set tuning.

Those omissions overlap topics in the human reference inventories. This supports
investigating selection and breadth. It does not prove those omitted concerns are
more scientifically important or that selecting them would improve correctness.

Synthesis upheld 37 findings, marked 16 duplicates, qualified two, and left two
unresolved. None was refuted. Debate remained intact, but the recorded outcomes
do not demonstrate that it reliably removes incorrect criticisms. We have not
isolated debate's causal contribution from the other changes.

## Quality limitations and recovery

The first attempt stopped after 13 successful model calls because four selected
findings cited source ranges longer than the requested eight lines. A separate
frozen recovery attempt resolved their full in-bounds source locations for export,
preserved the original violations, and reused all 13 exact cached responses.
No review was regenerated. Across the three complete finding ledgers, 96 primary
or counterevidence ranges exceeded the requested length. The strict screening
gate therefore cannot pass.

One single-agent scoring pass timed out after 600 seconds. It was preserved and
not retried. The continuation finished the other planned calls with unchanged
prompts, schemas, and inputs, producing 17 of 18 judgments.

Evidence validation failed for 20 of 81 candidate-support judgments. Failures
included overlong ranges and nonexistent line numbers. Support statistics are
withheld for eight of nine paper-condition combinations, including the combination
with a missing pass. We cannot claim fewer false criticisms or improved factual
accuracy. Raw scorer labels are insufficient evidence for either conclusion.

The three papers were already exposed during development. Exact historical
manuscript-review pairing and figure access remain unverified. The two judges
use the same model and can share errors. No human audit has been completed.
The unfilled 30-item audit package is preserved.

## Resource use

| Method | Mean generation tokens per paper |
| --- | ---: |
| Revised PRA | 713,613 |
| Original PRA | 495,417 |
| Single agent | 347,468 |

Revised generation used about 44% more observed tokens than original PRA and
2.05 times the single agent. This is token accounting, not a monetary bill or a
compute-matched comparison. Saved baseline generation was reused for the retest.

The retest made 66 calls: 65 successful and one timed out. Recorded usage was
3,059,818 tokens, plus unknown usage from the timeout. Inherited successful calls
are counted once. All requests selected `gpt-5.6-sol` at medium effort through
the ChatGPT subscription. The CLI does not report resolved model identity. No
API-key billing, paid credits, purchases, resets, or model fallback were used.

## Recommended next step

Keep the finding ledger and debate. Before spending on more reviews, audit a
small set of selected and dropped findings for correctness and scientific
importance, then revise only the editor's selection rule to balance distinct
central concerns. Use the manuscript's claims and experimental structure to
define coverage, without exposing human reviews to the generation system.

Fix evidence formatting deterministically, with bounded source identifiers and
explicit validation, so citation formatting does not repeatedly derail evaluation.
Then test any selection change using the saved ledgers before considering new
generation. That would be another development experiment, not held-out validation.
No further inference is scheduled by this report.

## Reproducibility

Runtime evidence is under `runs/pra-findings-debate-3paper-v2`. The original failed
attempt remains under `runs/pra-findings-debate-3paper-v1`.

- `available_results.json` records all available metrics and missing-data bounds.
- `finding_ledger.json` under each revised generation records every disposition.
- `recovery_provenance.json` and `cache_only_replay.json` document export recovery.
- `completion_provenance.json` documents the skipped timeout and continuation.
- `manual_audit.json` contains the unfilled human audit sample.

Recompute without inference using
`python3 experiments/pra_retest_analysis/summarize_available.py`. It checks frozen
hashes, exact extracted text, complete dispositions, preserved selected findings,
and all debate rounds before writing the available results.
