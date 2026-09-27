# Rebuild PRA around investigations

The user requested a substantial redesign aimed at beating strong single agents.
Prior runs changed reviewer organization while still mostly asking agents to write
and consolidate critiques. This experiment changes the intermediate product to
paper-specific investigations with inspectable evidence.

## Architecture

1. Reconstruct the paper's claims, method operations, supporting evidence, and
   dependencies. Create three specific work orders from the manuscript alone.
2. Independently investigate implementation and reproduction, identification of
   the claimed effect, and boundaries of applicability. Return reconstructions,
   comparison checks, smallest counterexamples, and atomic concerns. Arithmetic
   or logical checks can execute through a bounded calculator with saved receipts.
3. A defender answers every concern from the manuscript. The defender must concede
   gaps when the paper has no answer and cannot invent an author response.
4. An investigator representative reads those answers, rechecks the evidence, and
   defends, narrows, or withdraws each allegation. This is a sequential exchange.
5. An adjudicator resolves every concern and selects up to five for the final review.
   All retained lower-ranked concerns survive in an appendix. Text is copied exactly
   from the corrected concern ledger, and withdrawn allegations remain auditable.

The full team has six model stages after the shared map: three investigations,
defense, reply, and adjudication. This is a new local prototype, not a plugin release.

## Stronger comparison

The main comparator is a sequential single-controller workflow. It performs the
same three work orders in sequence, carrying all prior explicit notes, then audits
its findings, resolves that audit, and selects its final concerns. It gets the same
six stages, shared map, schemas, tools, model, effort, and stopping policy. It can
benefit from earlier investigations during later ones. The team keeps initial
investigations independent, then exchanges findings through separate roles.

Both workflows use fresh CLI subprocesses with explicit memory carried in prompts.
This is a comparison of orchestration and information flow. It is not a persistent
native-session comparison, and hidden reasoning is not transferred between calls.
A saved historical strong single review is a secondary practical baseline.

Use only Sol at medium effort through the ChatGPT subscription. Disable API-key
billing, external retrieval, plugins, shell execution, and model fallback inside
the review workers. No paid credits, resets, or purchases are authorized.

## Fixed experiment

Use TableQA, Gradient-Weight Alignment, and Attention to Activation, in that order.
All are previously exposed development papers, and the earlier TableQA reference
inventory was inspected during diagnosis. The new prompts contain no paper-specific
reference concerns. No result from these papers will establish general superiority.
Historical version pairing and full figure access are still unverified.

Freeze code, prompts, manuscript bytes, source IDs, and reference inventories before
inference. Finish all generation before loading references for scoring. The model
workspaces and tools expose manuscripts only. Keep earlier experiments unchanged.

Primary output remains at most five distinct concerns and 900 words, now including
the new arms' brief summary and strengths. Each concern is at most 160 words.
Do not bundle unrelated problems to increase coverage. Full-report coverage is
secondary and cannot substitute for a primary win. All valid findings are preserved.

Score the same anonymous candidate pool with two Sol passes. Exact candidate text
gets a stable digest ID, and duplicate text is scored once. Hide origins, stage
decisions, and debate positions. Reverse reference and candidate order in the second
pass. Measure reference coverage, supported concerns, contradicted major concerns,
completion, and actual resource use. No judge rewrites a concern for scoring.
Same-model agreement is still fallible and human-review overlap is not correctness.

The prespecified practical target is a gain of at least 15 percentage points in
mean per-paper reference coverage, with wins on all three papers, against both
the sequential controller and saved strong reviewer. There must be no additional
jointly judged contradicted major concern on any paper. This is an engineering
screen, not statistical significance. Missing outputs make it incomplete.

Preserve 15 anonymous concerns for manual audit. Before any scientific superiority
claim, audit correctness and matching and repeat the frozen design on papers not
used for development. Do not tune the scorer or replace failed outputs to get a win.

## Bounded execution

The design requires 45 new calls: 13 generation calls and two scoring calls per
paper. Allow at most three additional attempts, only for explicit stream
disconnection, with no more than one retry per node. Other failures stop generation.

Each generation stage has at most 18 manuscript or calculation tool calls. Both
arms have the same observed-token stop of 800,000, excluding the identical shared
map. The global stop is five million observed tokens. Already running calls may
overshoot a stop, and equal allowances do not mean equal actual computation.
Report cached input, uncached input, output, inherited usage, and unknown usage
separately. None of these totals is a dollar or subscription-credit charge.

Inspect failure mechanisms and save the evidence whether or not this architecture
meets the target. Do not expand this particular frozen run or silently restart it
with new prompts. Further development must use a separate recorded version.

## Research context

[ScholarPeer](https://arxiv.org/abs/2601.22638) reports a framework combining technical
auditing and contextual evidence. It motivates testing active investigation rather
than assuming discussion alone improves review. This prototype does not reproduce
its literature retrieval pipeline or claim its results transfer here.

[Tran and Kiela](https://arxiv.org/abs/2604.02460) report that single agents can match
or outperform multi-agent systems on multi-hop reasoning under equal thinking-token
budgets. That is a different task, but it supports using a strengthened sequential
comparator and reporting actual usage instead of attributing every gain to agents.
