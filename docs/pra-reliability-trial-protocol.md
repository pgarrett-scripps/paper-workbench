# Reliability and coverage trial

This small prospective comparison tests the integrated evidence-handle and candidate-inventory workflow on two manuscripts absent from the locally inventoried prior evaluation corpus. It does not isolate individual feature effects and cannot establish superiority from two cases.

The papers were selected by topic and source availability before new review generation:

- An online exercise pilot randomized trial in older adults, DOI 10.1371/journal.pone.0312992
- A field warming experiment involving honey bees, DOI 10.1371/journal.pone.0314791

Both conditions receive the same source manuscript, bounded small scientific supplements, domain guidance, advisory Scaffold checks, initial figure pages and finite current-record source packet. Human review histories, author responses and raw research datasets are excluded. Available protocol documents remain part of the manuscript evidence. No full analysis reruns are performed.

The conditions are a single reviewer with current tools and an investigator-plus-debate PRA review. The single reviewer produces up to five findings in one call. The investigator can record up to ten candidates, and debate selects at most five main findings in the second call. Secondary concerns are preserved separately and are not added to the judge's main-review comparison. Six total tool calls and six external source requests are available per condition, with PRA dividing tools four plus two. This matches resources, not model compute.

All generation and judging use Sol at medium effort through the verified subscription. The cap is eight model calls across two papers, including two blind judges. The observed-token launch stop is 850,000. An already running call can finish above the launch stop. No automatic retries, additional judges, paid API calls or reset redemptions are authorized by this protocol.

Before generation, the prospective harness seals manuscripts, source packets, figure bytes, implementation, prompt sources, settings and prior-corpus identities. The local corpus inventory includes run workspaces and published review metadata. Local absence does not imply that a pretrained model has never encountered a public paper.

Each fresh-context judge sees two randomized anonymous main reviews, manuscript evidence, eligible source cards and a shared union of inspected original images. It rates individual support, specificity, materiality, proportionality and edit fidelity, then selects a review or declares a tie or uncertainty. It receives no workflow labels, previous preferences, generation context, tool history or costs. The existing rubric is used, with two labels instead of three. Invalid judge quotations remain unscored.

Only validated completed review packages enter the blind comparison. A failed generation remains a delivery failure and is not silently repaired or rerun. If a pair cannot be judged, the remaining budget stays unused. Model preference, delivery reliability, candidate retention and cost are separate outcomes. No model result is imported as independent human expert validation.

The main questions are whether exact source references survive the workflow, whether supported secondary concerns remain accessible, and whether judges prefer the resulting main reviews. The coordinator will inspect preference-driving claims against original sources and report disagreements separately, without altering the blind ratings.

Artifacts are stored under `runs/pra-reliability-trial-v1`. The runner is `experiments/pra_reliability_trial/run.py`.
