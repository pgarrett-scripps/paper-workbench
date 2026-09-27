# PeerReviewAgents validation study

Planning draft, 2026-09-15. Updated for mostly automated evaluation with limited manual checks. This is a proposal, not a registered protocol or a report of new experiments.

Execution update, 2026-09-16: the user authorized unattended preparation and pilot
execution, initially specified Claude Opus, then requested the Codex plugin.
The active development runner selects GPT-5.6 Sol at medium effort. Current progress
and launch instructions are recorded in [the study status](validation-study-status.md).

## Active execution route: Codex subscription

The user requested the Codex plugin route after Claude authentication proved
inaccessible to this runner. The active development protocol selects
`gpt-5.6-sol` at medium effort for all review agents, baselines, and automated
scoring. The existing PRA engine runs with `provider: codex`, using fresh Codex
CLI sessions authenticated through ChatGPT. A minimal live inference check
succeeded on 2026-09-16. No separate model API key is used.

Codex documents [ChatGPT subscription authentication](https://learn.chatgpt.com/docs/auth)
and [non-interactive structured execution](https://learn.chatgpt.com/docs/non-interactive-mode).
The local account check reported no paid credits. Child sessions strip API
credential overrides and require ChatGPT login. Usage-limit failures stop the
runner. Account billing settings are not changed and credits are not purchased.

Codex pilot artifacts are separate from the earlier Claude preparation. The
prior Claude Opus protocol is retained for provenance. Codex JSON events do not
report resolved backend model identity, so the runner records explicit CLI
selection without claiming independently observed identity.

The full and no-debate conditions run the plugin engine with the same frozen
panel. Baselines run fresh Codex sessions. The strong single-agent condition
has manuscript-only reading and search tools, with delegation disabled.
Automated scoring uses two blinded prompts with the same model. These are
correlated sensitivity checks, supplemented by a limited human audit.

## Recommended paper

**Does a structured peer-review workflow recover more substantive human-review concerns than a strong single agent, at a comparable inference budget?**

Build a focused automated evaluation with a small blinded manual audit. Measure reference-concern coverage, evidence support, resource use, and the effect of debate. Agreement with published reviewers and automated evidence judgments must remain distinct from verified scientific correctness.

Working title: **Evaluating the added value of structured agents for scientific peer review**.

Superiority is a hypothesis. A finding that the simpler workflow performs as well, or that debate removes useful criticism, also answers the research question.

## Existing foundation

The current Nature Methods correspondence describes the software and review record, without reporting a validation dataset. A separate empirical paper has a distinct contribution.

The sibling PeerReviewAgents repository already contains an evaluation harness, corpus freezing, resumable runs, cost accounting, a one-call baseline, and paired analyses. Its historical protocol in `docs/EVALUATION.md` evaluated version 0.4.0, with an eight-role panel and sequential debate.

The historical report at `data/eval/iclr-2025-publication/comparison.md` reports accuracy of 0.80 versus 0.70 and Spearman correlations of approximately 0.545 versus 0.598 for the workflow and one-call baseline, respectively. Both paired difference intervals include zero. This report was inspected for planning, not independently reproduced. It does not validate the current five-referee architecture.

In Silico preserves specialist, audit, debate, synthesis, and editor outputs. These support tracing concerns through the workflow. Use previously examined papers for development, with new papers held out for evaluation. Do not pool results across architecture versions.

## Bounded corpus

Planning target: 10 development papers and 60 held-out papers, from one source and a limited subject range. These are workload targets, not a power calculation. Use pilot variability, scoring reliability, and costs to set the final sample size before held-out generation. If the feasible sample cannot resolve a useful difference, describe the study as exploratory.

The CS platform discussed is **OpenReview**. It is the easiest engineering starting point because a local harness already exists. Choose one venue and year, with recoverable original submissions and public first-round reviews. Keep the topic range within what investigators can manually audit.

If biological relevance is the priority, use one subject cluster from eLife Reviewed Preprints instead. F1000Research is another candidate with version-associated reviews. Choose through a short data-feasibility check before inspecting comparative performance. Do not add both biology and CS to the initial paper.

Require exact manuscript-review pairing, usable figures and supplements, substantive human reviews, and no prior use for tuning. Prefer two or more first-round reviews, with the eligibility rule fixed before sampling. Sample reproducibly from all eligible records in a date range. Record exclusions. Historical In Silico reviews can be pilot material, but mismatched inputs or generation settings should not enter the primary comparison.

## Four conditions

| Condition | What it establishes |
|---|---|
| Strong one-shot review | Practical low-cost baseline with a developed prompt and shared generic rubric |
| Strong single-agent workflow | Main comparator, allowed to reread, inspect files, calculate, critique, and revise within a common inference allowance |
| Full PeerReviewAgents | Frozen five-referee workflow, audits, debate, synthesis, and editor |
| PeerReviewAgents without debate | The same specialist and audit reports given to the editor without debate or debate synthesis |

Use a pinned general-purpose harness for the single-agent condition, such as Claude Code if compatible with the selected model and controls. Give it a substantive assignment and adequate resources. Develop its prompt on pilot papers. Specify whether delegation is disabled. The result applies to this configuration, not every possible use of Claude Code.

Use the same model snapshot for all generation roles in the main experiment. Standardize manuscript rendering, supplements, tool permissions, reasoning settings, and output allowance. Give the single agent the same total inference budget ceiling as the full workflow. Freeze the accounting rule on the pilot and report actual input, output, reasoning tokens where available, cached tokens, cost, and latency. Equal ceilings do not establish identical underlying computation.

Use isolated local evidence packages and disable live external retrieval in the main experiment. All conditions receive the same manuscript, supplements, and any curated dated literature packet. Exclude target-paper reviews, decisions, rebuttals, later versions, and scoring files. This tests a controlled review setting. It does not validate unrestricted search or the production mixture of models.

Ask each condition to nominate up to five ranked substantive concerns in its final review, with a common word allowance, evidence, and a reasonable remedy. Permit abstention. Compare final outputs as the primary product, with intermediate bundles analyzed separately. A longer list should not win merely through volume.

The no-debate condition measures the marginal quality and cost of adding debate to a fixed panel. It uses less inference, so it cannot isolate adversarial prompting from additional computation. Do not make that stronger causal claim.

## Reference construction and automated scoring

Published human reviews are an incomplete, sometimes mistaken reference. They identify concerns reviewers raised, not all concerns that are scientifically valid.

Before scoring outputs, automatically extract and deduplicate substantive concerns from human reports. Preserve exact source passages, version identifiers, severity, and manuscript locations. A second evaluator checks extraction fidelity. Freeze the inventory before comparing generated reviews. Faithful extraction does not imply scientific correctness.

Use two evaluation models from different families where feasible, separate from the generation model. Mask system names and randomize presentation. Require evidence passages for each judgment. Different evaluators may share errors, so consensus is not proof of truth.

For matching, require the same underlying problem and its application to this manuscript. Shared vocabulary or generic requests do not count. For evidence support, distinguish supported, contradicted, and insufficient-evidence concerns. Assess novel concerns even when humans did not mention them. Absence from the reference is not a false positive.

Freeze evaluator prompts on development data. Retain each evaluator's labels and report results by evaluator, under a conservative agreement rule, and with sensitivity analysis for disputed matches. If rankings depend on evaluator choice, disclose that instability.

Do not let evaluation rewrite or improve generated criticisms. Human-check sampled extraction and matching against original wording. Author agreement, later revisions, and acceptance decisions are not automatic evidence that a concern is correct.

## Limited manual audit

Reserve approximately 120 to 160 scoring items for a blinded audit, rather than rereviewing every manuscript. Include reference extraction, semantic matches and nonmatches, and evidence-support judgments. Sample across systems and manuscripts. Include major criticisms, novel concerns, and evaluator disagreements, alongside a random sample of agreements to catch shared errors.

Predeclare sampling rules and keep sampling probabilities. Report error rates by audit category. Weight appropriately if estimating overall rates after oversampling difficult cases. One qualified assessor can perform the main audit, with a second person checking roughly 20 percent and disputed cases if feasible. Keep independent labels before adjudication and disclose developer involvement.

A provisional allowance is 6 to 12 hours of manual work, including reading relevant manuscript context. Replace that estimate with pilot timing. A small audit calibrates the automated scorer. It does not certify every generated criticism.

Develop the scorer on pilot data and audit its frozen behavior on held-out output. If the audit reveals a major defect, identify the failed evaluation and document a revised analysis. Do not silently adjust the scorer to obtain a favorable ranking.

## Endpoints and statistics

Primary endpoint: per-paper coverage of distinct substantive reference concerns within the five available output slots. The denominator is the frozen human-derived concern set, not all scientifically valid concerns. Empty output slots earn no coverage. Predeclare handling of papers with no eligible reference concerns.

Primary contrast: full PeerReviewAgents versus the strong single-agent workflow.

Secondary outcomes include major-concern coverage, automated evidence-support estimates, contradicted major criticisms, insufficient-evidence concerns, supported additional concerns, completion rate, cost, latency, and debate's marginal effect. Keep contradicted and insufficient-evidence labels separate. Call automated labels evaluator estimates, not ground-truth precision.

Show coverage together with evidence support and false-criticism flags. Predeclare what increase in unsupported criticism would undermine an added-value interpretation. Lack of statistical significance on an error endpoint does not establish equal reliability.

Use manuscripts as the unit of inference. Report paired effect sizes and paper-level bootstrap intervals. Hundreds of comments from a few manuscripts are not hundreds of independent observations. Identify secondary analyses as exploratory or handle multiplicity for additional formal claims.

Predeclare retries, failure handling, and malformed-output rules. Include all costs and report attempted-paper outcomes alongside successful-run comparisons. Select 10 held-out papers in advance for two additional runs of the primary pair if affordable. Repeats estimate within-paper stability, not additional independent manuscripts.

Acceptance prediction, score correlation, text similarity, and overall LLM preference should not drive the paper.

## Why keep the debate ablation

Trace reference concerns from specialists through debate, synthesis, and the final letter. Ask whether debate preserves supported concerns and removes weak ones, or suppresses useful minority criticism and amplifies unsupported claims. Audit a few cases within the existing manual allowance.

Descriptive tracing does not establish stage-level causality. The no-debate intervention estimates that stage's overall marginal effect, subject to its inference-budget difference. Avoid a large grid of specialist, model, round-count, and search ablations.

## Version matching and leakage

Use the manuscript actually reviewed, not the latest published article. Public PDFs may embed reviews or editorial assessments. Remove those and verify inputs. OpenReview submissions and reviews can both be edited, so the latest API response alone is insufficient evidence of their original state.

The local pinned-preprint helper can select old versions, but a preprint predating journal receipt is only a candidate match. Verify the actual content correspondence.

Keep references and annotations outside generation workspaces. Record source identifiers, timestamps, hashes, model snapshot, code revision, prompts, and tool logs. Prefer recent records where feasible, while acknowledging that disabling retrieval does not eliminate training-data contamination.

Freeze the corpus, evaluation rules, analysis, model configuration, and retry policy before held-out generation. Release source identifiers and hashes when source terms do not permit redistribution of manuscripts or reviews.

## Execution and stopping point

1. **Pilot:** Verify 10 manuscript-review pairs, run four conditions, construct references, and manually test scoring. Measure cost, runtime, and audit effort.
2. **Freeze:** Choose one corpus source, final sample size, inference allowance, endpoints, and interpretation rules. Timestamp the protocol.
3. **Evaluate:** Run the held-out comparison, score blindly with both evaluators, and complete the fixed manual audit.
4. **Write:** Analyze paired effects and debate behavior, release reproducibility artifacts, and report the observed result.

At 60 held-out papers, four conditions produce 240 reviews and up to 1,200 nominated concerns before deduplication. Estimate API cost from pilot measurements, including evaluator calls and retries. Historical inexpensive-model costs are not current budget quotes.

A provisional timeline is four to six weeks with intermittent investigator effort, assuming usable source pairs and a functioning runner. The immediate deliverable is a scored 10-paper pilot, not a new platform.

Proceed if pairing is reliable, the scoring audit supports the metrics, and the workload is feasible. A favorable pilot effect should not be the sole criterion. If the full workflow ties or loses, report the limitation and any supported simplification.

## Paper shape and limits

Figure 1: corpus selection, exact-version matching, experimental conditions, and scorer calibration.

Figure 2: reference coverage, support estimates, and resource use across conditions, with paired uncertainty intervals.

Figure 3: marginal effect of debate and concern retention through the workflow, including successes and failures.

The defensible conclusion concerns reference-concern recovery under specified conditions, supported by an audited automated evaluation. Stronger claims about scientific correctness require more independent expert adjudication. A single-source, single-model study should not claim general superiority across science.

Do not add model training, prospective author outcomes, a new synthetic-error dataset, or a broad cross-disciplinary benchmark to this initial paper.

## Relevant sources

Multi-agent peer review already has substantial prior work. [MARG](https://arxiv.org/abs/2401.04259) examines helpfulness and specificity of feedback. [ScholarPeer](https://arxiv.org/abs/2601.22638) evaluates a search-oriented workflow and includes expert comparisons. [ReviewGrounder](https://arxiv.org/abs/2604.14261) uses paper-specific rubrics derived partly from human reviews. The contribution here should be a credible controlled comparison and measured value of specific workflow stages, rather than simply another multi-agent pipeline.

Source documentation: [OpenReview data retrieval](https://docs.openreview.net/how-to-guides/data-retrieval-and-modification/how-to-get-all-notes-for-submissions-reviews-rebuttals-etc), [eLife Reviewed Preprints](https://elifesciences.org/inside-elife/14e77604/elife-s-new-model-introducing-reviewed-preprints), and [F1000Research peer review](https://f1000research.com/for-authors/peer-review).

[FLAWS](https://arxiv.org/abs/2511.21843) provides controlled inserted-error cases. Reusing a small existing benchmark is a possible later extension, but synthetic error detection is different from real-world review usefulness. Unmodified papers are not guaranteed to be error-free.
