# Three general reviewers and one discussion round

The hypothesis is that independent complete reviews recover more useful issues
than a panel divided into specialties. Debate and editing then need to preserve
the useful breadth while removing unsupported or redundant concerns. Improvement
is a hypothesis to test, not an expected result.

Use the same three development papers: nT89RltY10, UwcZEoNP19, and IjduZQK8gM.
Every new call selects Sol at medium effort through the ChatGPT subscription.
There is no Astra, paid-credit purchase, API-key billing, or model fallback.

For each paper:

1. Three general reviewers read the complete supplied manuscript independently
   in parallel. They have the same task and no specialty or access to each
   other's initial review. Each produces at most five complete concerns.
2. In one discussion round, each reviewer reads all three initial reviews and
   responds to every concern. These responses run in parallel. Reviewers defend,
   challenge, or concede claims based on manuscript evidence. This is a single
   response round, without subsequent replies to the discussion responses.
3. A moderator reads the discussion, resolves each finding, and recommends up to
   five supported concerns. The moderator preserves disagreements and explains
   what changed.
4. The editor reads the original reviews and moderator report, selects up to five
   supported concerns, and records a reason for every selection or omission.

The workflow requires eight generation calls per paper, or 24 in total. This is
an experimental orchestration prototype. It does not replace the installed plugin.
Every finding has an immutable ID and text. Selected concerns are copied exactly.
No synthesis step silently rewrites a criticism. Original summaries, strengths,
discussion, dispositions, and final concern packets are all saved.

## Evaluation without repeated scoring

The primary comparisons are the final panel output versus reviewer 1 alone and
versus the saved strong single-agent review. Reviewer 1 is fixed in advance, not
chosen as the best or worst of three. It uses exactly the same prompt and input
as the other two reviewers. Its findings may be selected into the final review,
so it is a constituent baseline. The saved single agent provides another baseline
using its prior manuscript-tool workflow. None is compute matched to the panel.

For each paper, pool the original findings and saved baseline concerns under
shuffled anonymous IDs. Two scoring passes assess the same candidate pool against
the frozen human-review inventory and manuscript. Neither sees reviewer identities,
discussion outcomes, or final selections. The second pass reverses ordering and
explicitly considers alternative interpretations.

Derive coverage from the IDs retained at each stage. This gives reviewer 1, 2,
and 3 results, the complete panel union, moderator recommendations, final output,
and the saved single agent without additional inference. The panel union can
contain 15 concerns, so it is a diagnostic ceiling, not a fair five-slot competitor.
The other review packets contain at most five concerns and 900 words.

Joint candidate scoring is a change from earlier evaluations and may introduce
context effects. Score the saved single agent again in this same pool. Do not pool
older scores with this experiment. Saved baseline concern selection is reused,
while new structured findings require no model extraction. Report this difference.

Evidence citations must be selected from fixed source IDs, each resolving to an
exact eight-line manuscript chunk or a shorter final chunk. There are no generated
numeric ranges, no truncation, and no inferred replacement citations. The schema
constrains IDs to the actual source set. Source existence still does not establish
correctness. Missing evidence remains explicit and is not silently repaired.

## Decision rule, limits, and reporting

Call the result promising only if final mean coverage confirmed by both passes
exceeds both primary baselines, wins on at least two of three papers against each,
and adds no validated contradicted major concerns on any paper. Missing outputs,
invalid evidence, or protocol failures make the screening outcome inconclusive.
Even a promising result needs human audit and fresh papers. Support labels from
the same model are not expert validation.

The fixed budget is 30 attempted calls: 24 generation calls and six judging
calls. The observed-token stop is 2.5 million, with possible overshoot from up to
three in-flight requests. Each call has a 600-second timeout. Preserve failures,
leave missing outputs missing, and never automatically retry failed inference.
All observed usage, including failed calls when available, counts toward limits.

Report final coverage, stage losses, correctness limitations, and generation
tokens relative to both baselines. Do not claim that a pre/post selection contrast
isolates debate's causal effect. Preserve an unfilled 15-concern human audit sample.
Stop after the three papers without expanding the run or deploying the prototype.
