# PRA quality and validation plan

September 24, 2026. Prospective plan following the completed evidence-workflow comparison. This document does not change the frozen experiment, its failed improvement criterion, or its reported results. No new model calls are launched by this plan.

## Product objective and scientific claim

Build a review assistant for experimental biology that supplies consequential, source-supported comments, proportionate requests, and safe local wording suggestions. Each concern should show what the paper claims, what was checked, what remains uncertain, and what would resolve it. Retain debate as an explicit challenge to the interpretation of evidence.

Agent count is not a quality measure. The product must earn its complexity through additional useful findings, fewer unsupported criticisms, better prioritization, or lower author verification effort. Broad superiority to human reviewers is not the proposed claim. Comparative superiority to a capable single agent remains a hypothesis.

Stay within ordinary manuscript review. Inspect the supplied manuscript, figures, tables, supplements, and focused prior literature. Allow small calculations on reported values. Do not require author-code execution, full analysis reproduction, large datasets, or computational-methods papers for the prototype.

## Evidence motivating this revision

The last two-paper comparison found five supported direct human-concern matches for ordinary review, five before debate, and three after debate. Debate lost a quantitative request during merging and rejected a mechanism concern that matched two related human criticisms. It also promoted a useful trafficking concern and improved acknowledgment of author-side evidence. All candidates were archived, but archival preservation did not prevent loss from the selected review.

Three final comments on the root paper substantially concerned reporting or replication. Other substantive issues were never discovered. Both debate calls left their two source tools unused. Both planners requested an unsupported Boolean search. These observations motivate changes to preservation, source access, and discovery rather than more generic reviewer personas.

## First revision: preserve substance through debate

Keep the existing planner, evidence investigator, and fresh debate stages for the first revision. Do not increase the number of reviewing agents yet. The current debate is one fresh model call assessing opposing arguments, not a dialogue among three independent reviewers. Report that accurately.

Give every candidate a stable issue ID and explicit fields for its scientific target, concern, consequence, requested resolution, source evidence, counterevidence, and unresolved facts. Preserve the original wording and later versions. Multiple scientific questions on the same paragraph remain distinct.

Debate must record the strongest criticism, strongest author defense, evidence that distinguishes them, and its decision. A defense can reduce severity without resolving the question. Qualification in one sentence does not establish that the title and conclusions are appropriately qualified everywhere.

Use separate decisions for scientific status and presentation:

- Scientific status: supported concern, supported clarification, contradicted concern, or unresolved.
- Presentation: primary issue, supporting comment, merged into a named issue, or omitted from the concise summary for priority.

A low-priority finding is not scientifically rejected. A merge maps each original issue and requested resolution to its destination or explains why that component was resolved. A rejection requires a source-supported explanation of why the concern is answered or its premise fails. Missing decisive evidence leaves the issue unresolved. Neither consensus nor the presence of an evidence quote proves that the interpretation is correct.

Structural validation checks IDs, provenance, mandatory fields, and explicit disposition of each component. It cannot guarantee semantic preservation or scientific validity. Those require source-based assessment. Do not automatically promote every retained candidate as a valid criticism.

The editor package retains a short prioritized review, local comments, evidence, and an expandable unresolved or rejected record. Group related reporting requests when that improves clarity, while preserving their specific locations and requested details. Do not impose scientific-category quotas or force five findings when fewer are useful.

## Tools with specific jobs

| Capability | Existing foundation | Planned change | What it cannot establish |
| --- | --- | --- | --- |
| Compare a claim across the paper | Full text and block reads | Assemble the title, abstract, relevant results, conclusion, and limitations for a specified claim | Correctness of the mechanism |
| Check whether a concern is already answered | Literal search and source reads | Structured search terms with explicit any/all semantics, neighboring passages, source coverage, and unavailable-asset flags | That absent retrieval proves absent evidence |
| Inspect an experiment in context | Original PDF page viewer | Deliver the figure, legend, linked methods, and available supplementary material together with page provenance | Precise values from unreadable plots or inaccessible data |
| Reconcile reported facts | Block IDs and arithmetic | A source-linked table of units, doses, sample sizes, constructs, timings, and defined experimental units | Whether superficially different entries describe the same experiment |
| Check a cited claim | DOI metadata and bounded literature search | Resolve identity first, then retrieve the relevant accessible source passage and record support, limits, or uncertainty | Claim support from DOI metadata alone |

Implement the first three capabilities before expanding literature work. Use existing extracts and cached images where possible. Tool requests should identify which uncertainty the returned material could resolve. Source bundles must disclose omissions and count their underlying accesses consistently across study conditions.

Introduce citation-support retrieval separately, after manuscript checks work. Limit it initially to a few consequential cited claims. Prefer supplied or openly accessible full text. Keep metadata, abstracts, and full text distinct. A failed search cannot justify a missing-citation allegation. Broad novelty searches remain deferred.

For benchmark papers, enforce the frozen manuscript date and version, exclude review pages and later author responses, and record retrieved passages. Date filtering alone is not a complete protection against review leakage. For real confidential submissions, external queries must avoid disclosing unpublished manuscript text without authorization.

Paper Scaffold prose, readability, and word counts remain a separate editorial layer. They should improve writing assistance without being counted as discoveries of scientific flaws. Repairs to PDF bibliography and section extraction precede claims about comprehensive citation coverage.

## First implementation package

Create a versioned workflow so the completed runner remains reproducible. Prefer new modules and an explicit new protocol over silently changing behavior used by old experiments.

1. Add the issue and decision schemas, component-preserving merge checks, and separate priority and validity fields.
2. Add claim-context and experiment-context retrieval plus structured manuscript search. Fix the valid-ID interface and distinguish a correctly unresolved task from a malformed completion.
3. Revise the debate instructions and editor export to use these records. Surface the concrete requested resolution and any unresolved verification in local comments.
4. Add offline regression cases for a lost quantification request, a genuinely rebutted criticism, a claim qualified in Results but overstated elsewhere, an unavailable supplement, a duplicated reporting issue, and a valid concern absent from the human reference list.

Use both positive and negative cases. A preservation test must not reward keeping a disproven allegation. Existing manuscripts can test engineering and identify development failures, but cannot become fresh validation data.

## Smallest informative live check

First test the debate change while reusing the two saved candidate sets and source material. Do not regenerate planners or investigators. This isolates the decision and preservation behavior more directly than rerunning the entire system with several changes at once.

Proposed maximum: two Sol medium debate calls and one blinded paired evaluation per paper, four calls total. Use a 250,000 observed-token launch stop, no automatic retries, and no paid credits. As in the existing runner, a call started below the stop can cross it. Record input, cached input, output, source operations, and elapsed time. This is a proposed new development budget, not an extension of the completed eleven-call budget.

Freeze the new prompt, schemas, and assessment rules before these calls. Compare old and revised debate on supported corrections, harmful deletions, preserved concrete requests, and distinct useful concerns. Inspect all material changes against sources. Do not call recovery of known concerns a generalization result. Do not use an altered human-overlap threshold to reinterpret the prior failed experiment.

Advance only if the revision repairs the demonstrated preservation failure without keeping contradicted criticisms, introduces no source-confirmed serious unsupported allegation in the inspected changes, and delivers a consequential improvement beyond wording polish. Otherwise fix offline. Small samples do not estimate population error rates.

## Evaluation for a defensible paper

Move human-review overlap to a secondary endpoint in a new, prospectively frozen study. Preserve and report the old overlap-based result. The new primary question is whether users receive more distinct, consequential, source-supported findings at an acceptable unsupported-criticism rate and cost.

Assess validity, consequence, actionability, requested-work burden, distinct coverage, and edit fidelity separately. A request for an unnecessary new experiment can be specific without being a good review. Report ungradable findings separately rather than counting them as correct or silently excluding them from all denominators. Publish counts and denominators before any summary score.

Measure debate by both gains and losses. Count validated corrections and useful additions alongside useful findings wrongly rejected or weakened. Keep clarification separate from an established error. Evidence that an ambiguity is present may justify clarification even when the author's actual intent cannot be determined. Pilot this rule with unambiguous fixtures before model grading.

Use a capable single-agent reviewer with the same model, materials, tools, output allowance, and opportunity for iterative checking as the main comparator. Include a single agent with comparable total compute on a bounded subset to distinguish workflow structure from additional inference. Retain the before-debate condition as an ablation. A text-only one-shot baseline is contextual, not the principal opponent.

Control review length and the number of independently scorable issues. Grouping many issues under one heading must not provide an unfair five-item advantage. Evaluate the concise review separately from the full product's comment ledger.

Use automated grading for coverage, but supplement it with a modest blinded expert audit. A feasible development audit is 24 to 30 comments, combining a randomly selected balanced sample and a separately reported sample of consequential debate disagreements. Have a second assessor check disputed cases and some agreed cases. Do not use the enriched disagreement sample to estimate overall precision. If experts cannot be obtained, describe the study as automated evaluation with source spot-checks and narrow the accuracy claims.

After the small development check, propose a fresh, stratified feasibility panel of roughly 12 to 20 experimental papers across two or three areas. This is a planning range, not a power calculation or approval to run it. Freeze selection and exclusions, keep final test papers unused during development, and base a confirmatory sample size on observed variation and a prespecified practically useful effect. Use the paper as the primary statistical unit, account for related findings, and report uncertainty. If feasible, add prospective manuscripts to reduce exposure to public review history.

Separate scientific review quality from interface usefulness. A small author or reviewer task can measure time to locate and verify evidence, understand the request, and decide what to change. Preference, adoption, and polished prose are not substitutes for scientific validity. Publication may support an author-assistance claim even if universal review superiority is not demonstrated.

## Related work and positioning

Multi-agent discussion alone is not a new contribution. MARG already uses interacting agents to produce scientific feedback and reports a user study of helpfulness and specificity. Its historical results do not establish how the present models compare. [MARG](https://arxiv.org/abs/2401.04259).

A 2026 randomized study evaluated feedback to human reviewers at ICLR 2025 and reported improvements in review informativeness. This supports studying useful review improvements, but it does not validate autonomous scientific error detection by PRA. [Review Feedback Agent study](https://www.nature.com/articles/s42256-026-01188-x).

General debate research also reports failures to beat strong single-agent baselines. These are not peer-review experiments, but they reinforce the need to control compute and test the contribution of debate itself. [Multi-agent debate evaluation](https://arxiv.org/abs/2502.08788).

The prospective contribution is a reproducible workflow for evidence-based review of experimental manuscripts, with explicit disagreement, preserved scientific questions, local author actions, and measured gains and harms from debate. Novelty requires a fuller related-work comparison before submission. The strongest claim must follow the results, including any remaining negative findings.

## Release decision

A supervised author-facing beta and a claim of validated superiority are separate milestones. Before beta, verify source integrity, edit reversibility, provenance, honest handling of missing assets, and useful local comments on the intended paper types. Address privacy and source-content prompt injection as part of handling user manuscripts. Before a superiority claim, require evidence from the frozen comparative study and independent assessment. A large agent team, attractive interface, or high model-judge score does not substitute for either milestone.
