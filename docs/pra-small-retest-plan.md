# Three-paper PRA revision test

The revision preserves complete findings, assigns concrete investigations to the
existing specialists, and retains two advocate-skeptic debate rounds. Verification
is part of debate. There is no additional verifier agent or general-review stage.

## Fixed scope

Use three of the ten existing development papers, selected by shuffling the
frozen manifest with seed 20260917 before any revised output exists:

- nT89RltY10, On Gradient-Weight Alignment
- UwcZEoNP19, Triples as the Key: Structuring Makes Decomposition and Verification Easier in LLM-based TableQA
- IjduZQK8gM, From Attention to Activation: Unraveling the Enigmas of Large Language Models

Compare revised PRA, saved original full PRA, and the saved strong single agent.
All use GPT-5.6 Sol at medium effort and the same manuscript text. No new papers,
literature retrieval, figure processing, model changes, or production deployment
are included. This subset is developmental, not held out. It cannot establish
statistical superiority or generality. Debate itself is not a new invention.
The proposed contribution is preserving findings and checking evidence through
debate, if the measurements show a benefit.

## Revision

Keep the existing plugin graph: five specialist reviewers, two factual auditors,
two advocate-skeptic rounds, debate synthesis, and final editor. A local experiment
adapter supplies revised node behavior on a frozen engine snapshot. The installed
plugin and the completed pilot remain unchanged.

Each specialist performs manuscript-specific checks within its existing remit:

- Scientific validity: reconstruct central claims and assumptions, examine a
  counterexample or alternative explanation, check the stated conclusion.
- Data analysis: check quantitative comparisons, controls, uncertainty, data
  splits, and whether reported numbers support the claim.
- Contribution and context: distinguish the claimed advance from cited methods
  using supplied evidence. Do not invent external novelty claims.
- Reporting and reproducibility: reconstruct the actual procedure, inspect
  appendix details, and identify consequential missing information.
- Ethics: investigate only manuscript-triggered concerns about data provenance,
  evaluation populations, or claims of practical benefit. Abstain when inapplicable.

The two auditors retain methods-completeness and citation-integrity tasks. They
produce evidence records rather than unsupported checklists.

Findings have stable IDs, a complete claim, manuscript line references, scientific
importance, a remedy, counterevidence, and access limitations. Keep every original
record. Manuscript spans are resolved deterministically, never reconstructed as
model-written quotations. A valid span proves location, not scientific truth.

Round 1: the advocate seeks the strongest manuscript-based defense or existing
answer to each concern. The skeptic tests its assumptions and explains why any
remaining problem matters. Neither sees the other side's current-round answer.
Round 2: both see the first exchange and must respond to the opposing evidence,
explicitly retaining, revising, or conceding positions. Repetition is not evidence.

Synthesis records upheld, qualified, refuted, unresolved, or duplicate for every
finding ID, with reasons and manuscript spans. The editor chooses up to five
complete original findings and records a disposition for every other finding.
It cannot silently replace a detailed criticism with a short summary. Qualified
or unresolved concerns remain explicitly conditional. Refuted concerns cannot
be selected. The complete ledger and debate remain available for audit.

## Fair comparison and checks

Re-extract concern packets from all nine final reviews using the same prompt.
The extractor selects source paragraph IDs and returns no rewritten criticism.
Source text is copied by code. It must include the detailed argument and remedy
where present, avoid duplicate introductory summaries, and stay within five
concerns and 900 quoted words. Native revised findings also pass this normalizer.
This separates an extraction correction from a workflow improvement.

Use the same frozen human-derived reference inventory. Two anonymized scoring
passes evaluate reference coverage and manuscript support. Evidence uses original
manuscript line ranges and exact text resolved by code. Keep missing evidence
and uncertainty visible. No scorer may see condition names or generation logs.
All three conditions are rescored with the new evaluator. Earlier scores are
reported separately and never pooled with the new scores.

Before inference, test permanent IDs, exact span resolution, two-round information
flow, complete dispositions, preservation of final finding text, and rejection of
invalid selections. Freeze source and input hashes. Preserve failed attempts.

## Decision rule and budget

The fixed subset is a screening test. Call the revision promising only if mean
coverage confirmed by both judges exceeds both comparison arms, it improves over
each on at least two of three papers, and it does not add validated contradicted
major concerns. Report insufficient evidence, scorer disagreement, all failures,
and resource use. If a quality check fails, label the comparison inconclusive.
Even a promising result requires human audit and fresh papers before any claim.

Expected inference is 66 calls: 39 revised-generation calls, nine common extraction
calls, and 18 scoring calls. Stop at 72 observed calls or six million observed
tokens, with possible one-call overshoot. There is no automatic model fallback,
blind retry, credit purchase, or API-key billing. Saved baseline generation is
reused. Report both newly consumed usage and standalone generation cost.

Stop after this subset and report the result. Do not expand automatically.
