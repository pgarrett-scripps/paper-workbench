# Preserved findings and investigative debate

This recovery attempt changes only final export handling and quality reporting.
The first attempt stopped after 13 successful model calls because four selected
findings cited exact manuscript locations longer than the requested eight lines.
The new exporter validates the complete locations against the manuscript and
preserves all original records and violations. It does not shorten evidence,
change debate inputs, or rerun completed inference. Any such violation makes the
strict screening result inconclusive. Coverage comparisons remain exploratory.
The frozen protocol, prompts, model, papers, and overall usage limits are unchanged.

This experimental adapter keeps the frozen PRA graph, five specialists, two
auditors, and two advocate-skeptic rounds. Stable findings pass through debate and
editorial selection without being rewritten. Every finding receives a disposition.
Definitive synthesis outcomes without valid manuscript locations become unresolved.

The plan is in `docs/pra-small-retest-plan.md`. The fixed protocol selects three
previously exposed development papers. It compares revised generation with saved
original PRA and single-agent reviews, applying the same new source-paragraph
extractor and two scoring passes to all three conditions.

Run offline checks from the repository root:

```sh
/home/ty/Repos/PeerReviewAgents/.venv/bin/python -m unittest discover -s experiments/pra_findings_debate_recovery -p 'test_*.py' -v
```

The recovery root copies the frozen inputs, source, successful model responses,
and usage from attempt 1. `recovery_provenance.json` records original and updated
hashes. The first paper is replayed with a cache-only guard before further inference.

After verifying ChatGPT subscription authentication and recording current absence
of paid credits in the run's billing confirmation, execute the fixed experiment:

```sh
python3 experiments/pra_findings_debate_recovery/study.py run
```

Outputs are under `runs/pra-findings-debate-3paper-v2`. The runner saves complete
panel records, debate turns, resolutions, editorial dispositions, selected review
text, common extracted packets, both judgments, resource use, and a report.
`manual_audit.json` contains an unfilled sample for later human assessment.

Successful calls are cached. Failed inference is preserved and not retried
automatically. The runner refuses changed source or input hashes. Stop after this
subset. A promising automated result does not establish correctness or superiority.
