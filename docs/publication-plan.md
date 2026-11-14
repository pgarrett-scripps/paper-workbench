# Paper Workbench publication roadmap

Status: proposed plan, 6 October 2026. Updated 12 November 2026 for the PeerReviewAgents 0.9.0 engine, whose study arms replace the 0.8 workflows and the debate. No new inference or study launch is authorized by this document. Dataset size and execution budget remain provisional until calibration. Preserve historical results and freeze the main study before running it.

## Position and intended contribution

Working title: **Paper Workbench: an evidence-linked framework for manuscript review and revision**.

The research question is whether structured manuscript access, targeted evidence gathering and auditable review synthesis improve useful scientific feedback and its translation into manuscript revisions. The specialist tracks and the editor are one configurable strategy whose value must be measured. It is not a result we assume in advance.

Build a full research article with Introduction, Results, Methods and Discussion, approximately 4,000 to 6,000 main-text words if the findings justify that length. Preserve the existing Nature Methods correspondence as a historical manuscript. Reuse appropriate Paper Scaffold authoring infrastructure, not its old specialist-panel narrative.

Scope includes scientific critique, reporting gaps, citation verification, prose assistance and source-linked revision. Full reproduction of author analyses, large data downloads and autonomous invention of results are outside the study. Begin with noncomputational life-science manuscripts.

## Verified starting point

- The private Paper Workbench repository exists at https://github.com/pgarrett-scripps/paper-workbench. The original In Silico repository and historical runs remain intact.
- The review engine is PeerReviewAgents 0.9.0, a separate repository. It owns manuscript loading, evidence access, review validation and review execution. The benchmark consumes the engine rather than copying it.
- The application provides manuscript presentation, located review findings, author decisions, revision workflows and exports. These capabilities need empirical validation as part of the contribution.
- The engine's study arms are `full-two-track`, `reviewers-only`, `single`, `single-revision` and `manuscript-only`. `manuscript-only` is one reviewer with the manuscript text only, no pages and no lookups. The 0.8 workflows, `independent`, `ensemble` and the debate, are frozen at the PeerReviewAgents `v0.8.0` release.
- An arm is a setting of one workflow, recorded in `protocol.json` beside the workflow hash. The reviewer count and the arm are configurable, but that does not yet establish a composable framework.
- A review runs in headless Claude Code on a Claude subscription, with the model pinned per agent. The 0.8 Codex transport is gone. A provider-neutral interface is a design goal, not demonstrated portability.
- The completed subscription benchmark v2 attempted 10 review workflows across five models. Nine produced valid outputs and 18 grades were valid. It used 48 model sessions and 1,972,015 observed tokens. This was live inference on one fictional manuscript and its corrected counterpart, not a real-paper validation cohort. All four fully completed model pairs detected the planted targets without target false alarms. There are no expert-adjudicated grades. This is an engineering pilot with a ceiling effect, not evidence for model rankings.
- The focused debate development comparison, on the 0.8 engine, did not establish improvement. Both reviews received 8/10 and contained the same five valid issue groups. The judge narrowly preferred the saved review. Structural preservation of issues did not preserve every useful qualification. See `docs/pra-focused-debate-results.md`.
- Initial extraction passed local tests and package smoke checks. Hosted CI was blocked by an account billing or spending-limit issue. Local changes need fresh validation before a release is frozen.

Local benchmark evidence: `/home/ty/Repos/insilico/runs/subscription-benchmark-v2/completion.json` and `/home/ty/Repos/insilico/runs/subscription-benchmark-v2/report/results.json`.

## Distinction from existing work

Multi-agent reviewing and context-aware evidence investigation already exist. MARG and ScholarPeer are direct related work. A larger agent roster, a debate stage or the word framework is insufficient novelty. Our candidate distinction is the combined manuscript representation, configurable evidence investigation, preservation of findings through synthesis, and reversible revision workflow. Establish this through a related-work comparison and measured benefits before claiming novelty.

- MARG: https://arxiv.org/abs/2401.04259
- ScholarPeer: https://arxiv.org/abs/2601.22638
- Expert assessment of AI reviews: https://arxiv.org/abs/2605.20668
- FLAWS controlled error detection benchmark: https://arxiv.org/abs/2511.21843

The expert-assessment literature also supports evaluating correctness, significance and evidence instead of treating overlap with published reviewers as complete ground truth. We do not need to match the largest studies to publish a bounded framework evaluation, but our claims must match our smaller sample and limited expert assessment.

## Work package 1: freeze a bounded framework release

1. Consolidate the current shared-core and benchmark integration changes with their owner. Run relevant tests, resolve the hosted CI blocker when account access permits, and tag an immutable study release.
2. Introduce a versioned configuration covering workflow recipe, reviewer count, prompts, model, evidence profile, synthesis policy, revision policy and budget. Persist the resolved configuration and code hashes with every run.
3. Define stable stage inputs and outputs for manuscript access, candidate findings, evidence checks, synthesis decisions and proposed patches. Preserve provenance and unresolved findings across stages.
4. Use three engine arms: `manuscript-only`, one reviewer with no evidence tools, `single`, one reviewer with the workspace and evidence tools, and `full-two-track`, core reviewers and six specialist tracks with the editor. Enforce tool restrictions in execution, not only in prompts. The manuscript-only baseline must still receive a fair, complete rendering of the manuscript and permitted figures. The engine's `manuscript-only` arm gives text only, with no pages, so baseline figure access must be decided before the study is frozen.
5. Expose a model transport interface without claiming arbitrary-provider support. A second working adapter is required before claiming demonstrated cross-provider portability. It is not necessary to implement many providers for the first paper.
6. Restrict follow-up synthesis to findings affected by new evidence. Preserve unrelated recommendations and uncertainty language. Test semantic information retention in addition to identifier coverage.
7. Preserve anchored edits, original text, version history and reversibility. Bounded automated revision must leave missing data or author decisions unresolved rather than manufacture answers.

Do not build a general workflow programming language, add tools to meet a quota, or expand to every scientific domain before evaluation. Use existing domain resources when they answer a concrete review question.

## Work package 2: freeze evaluation protocol and repair judging

The benchmark owns sampling, hidden labels, anonymity, judge prompts, statistics and reports. The core owns review execution. Freeze their versions separately and record both.

Before the main study:

- Add the true manuscript-only baseline and verify it cannot access the evidence tools or other candidate outputs.
- Correct the current evidence mismatch. Text-only graders cannot reliably adjudicate figure-based or externally sourced findings. Supply the relevant original images and frozen evidence cards to judges, or explicitly mark those judgments unavailable.
- Use a balanced, prespecified judge assignment across conditions and models. Do not let differing judge identities become a model-ranking confound. Prefer a second model family for sensitivity analysis if available. Otherwise disclose shared-family dependence.
- Separate passage anchoring and schema validity from scientific correctness. A valid citation handle is not proof that a criticism is correct.
- Keep human reviews, benchmark keys and other reviews outside candidate workspaces. Exclude every manuscript previously used for prompt development from the main cohort.
- Use fixed, cached retrieval inputs for controlled comparisons. A publication cutoff alone does not make live search reproducible. Report live retrieval as a separate deployment experiment if included.
- Record model identity limitations, runtime settings, failed attempts, incomplete grades, usage and revision history. Do not silently replace failed runs or count unknown usage as zero.

Use two fresh development papers to calibrate cost, judge rubrics and execution. Exclude these from the final cohort. Estimate a session and token envelope before requesting the larger launch. The previous one-paper synthetic pilot demonstrates that even a small paper count can consume substantial tokens.

## Work package 3: primary real-manuscript study

Provisional design: 24 fresh manuscripts across three life-science domains, eight per domain. Candidate domains are molecular and cellular biology, plant biology, and ecology. Verify availability, licensing and comparable source materials before finalizing strata. When comparing against public human reviews, use the manuscript version those reviewers actually assessed.

Run one fixed model, provisionally Terra, across three conditions on every paper:

| Condition | Manuscript and evidence access | Review strategy |
| --- | --- | --- |
| A, `manuscript-only` | Complete manuscript, no external review tools | One reviewer, one pass |
| B, `single` | Structured workspace and allowed evidence tools | One reviewer, one pass |
| C, `full-two-track` | Same workspace and allowed evidence tools | Core reviewers and six specialist tracks, then the editor |

This produces 72 review outputs, not 72 model calls. C consumes additional reviewer, specialist and editor sessions. A versus B estimates the workspace-plus-tools bundle. B versus C compares deployable workflows with different effort, so it cannot by itself isolate the specialist tracks or the editor, or prove efficiency.

Prespecify C versus B as the primary usefulness comparison. Report B versus A and C versus A as secondary comparisons with appropriate uncertainty and multiplicity handling. A null result is a valid finding. Do not change the primary comparison after seeing results.

On eight prespecified papers, compare `full-two-track` with `reviewers-only`, which keeps the core reviewers and the editor and drops the specialist tracks. This is the specialist-track ablation. Preserve the full finding ledgers and editor packages so an evaluator can identify useful findings gained, lost, weakened or appropriately rejected. A debate ablation needs the frozen PeerReviewAgents `v0.8.0` engine and is not part of this study.

After the main comparison is technically sound, an optional second-model replication on eight prespecified papers tests whether conclusions depend on Terra. Avoid multiplying all models by all domains and workflows in the first study.

Choose final sample size based on calibration, feasible budget and precision for a declared practically meaningful effect. Twenty-four papers is a bounded starting proposal, not a claim of adequate statistical power for every comparison. Cluster inference at paper level. Multiple findings, judges and manuscript variants are not independent papers.

## Outcomes and limited expert calibration

Primary outcome: anonymous pairwise preference for overall scientific usefulness, including explicit ties and reasons. Randomize display order and conceal workflow labels. Preserve content rather than truncating reviews merely to equalize their lengths.

Key secondary outcomes:

- Number of distinct valid and consequential concerns, after deduplication.
- Unsupported major criticisms, misleading recommendations and overstatement.
- Actionability, prioritization and uncertainty calibration.
- Findings and useful qualifications gained or lost during synthesis.
- Source and citation accuracy, including whether retrieved evidence changes a decision.
- Completion rate, runtime and observed token use, with failure-inclusive reporting.
- Overlap with published reviewer concerns, interpreted as supplementary coverage.

AI judges provide the scalable assessment but are not ground truth. Propose expert assessment on eight prespecified, stratified papers, with a second expert on four to estimate agreement. Review consequential disagreements separately and label that enriched sample separately from representative sampling. Confirm expert availability before promising expert validation in the manuscript. Without it, label findings as AI-judged and narrow scientific quality claims.

A small controlled error suite can supplement the real-paper study. Use approximately six source manuscripts with matched original and consistently altered versions, subject to expert verification and budget. Score only the prespecified planted targets as known labels. An unaltered manuscript is not assumed flawless. Do not use a single fictional pair as the main quality figure.

## Work package 4: validate the review-to-revision contribution

On six prespecified manuscripts, carry selected findings through located comments, proposed edits, acceptance or rejection, export and bounded re-review. Measure:

- Correct location and preservation of source identity.
- Whether the change addresses the criticism without changing unrelated meaning.
- Unsupported factual additions, fabricated citations and deletion of essential qualifications.
- Preservation of manuscript structure, references and figure links.
- Reversibility and successful export of accepted changes.

Use manual checks for scientific meaning on this subset. Demonstrating patch integrity alone does not establish that a manuscript became scientifically better. Do not claim author productivity improvements without an actual user study.

## Manuscript and figure plan

1. Framework architecture and one end-to-end example from source passage to evidence, criticism and revision.
2. Main three-condition comparison with paper-level paired outcomes and uncertainty.
3. Specialist-track ablation, showing useful concerns and qualifications gained, retained, lost or rejected.
4. Quality, token use and completion tradeoffs, with limited second-model replication if completed.
5. Revision validation, combining aggregate error measurements with a concrete manuscript example.

Include a corpus and condition table. Put full prompts, configurations, source inventories, judge calibration, failure taxonomy and additional examples in supplementary material. Use the benchmark package to generate reproducible figures from frozen artifacts. Keep benchmark engineering and a broad model leaderboard distinct from the framework paper's primary claim.

## Preprint and release gates

arXiv is the likely first venue for a framework and AI evaluation article. Category fit and moderation still apply. bioRxiv is an option only if the final manuscript fits biological research scope and presents suitable new research data. It should not be chosen solely because some example manuscripts concern biology. Its screening guidance excludes commentary-only submissions and requires research context for tool descriptions.

- arXiv submission guidance: https://info.arxiv.org/help/submit/index.html
- bioRxiv screening guidance: https://connect.biorxiv.org/news/2022/06/13/screening_procedures

Before submission, require a frozen release, reproducible benchmark protocol, completed primary comparisons, transparent failure accounting, appropriately scoped claims and validated revision examples. Plan an archival code release and shareable evaluation artifacts, respecting manuscript licenses. The repository remains private until public release is separately authorized.

The defensible paper can show which configurations help, where they fail and how traceable revision works. It does not need to claim that the full workflow always wins. If the full workflow does not improve usefulness or deliver another measured practical benefit, revise the product defaults and paper claims accordingly.

## Immediate implementation order

1. Consolidate current code and write the study protocol and related-work comparison.
2. Confirm the three arms, the true baseline, finding preservation and judge evidence parity.
3. Run offline validation and then the separately authorized two-paper calibration.
4. Freeze release, corpus and analysis plan, and obtain the larger execution budget before launch.
5. Execute the real-paper comparison, targeted ablation and revision assessment, then write results from preserved artifacts.

Start the new manuscript outline and figure placeholders while engineering proceeds. Do not fabricate results or expand the old correspondence with unsupported claims.
