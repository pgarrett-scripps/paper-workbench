# Plan for evidence-driven manuscript review

This is a proposed development plan based on the completed two-paper and four-paper panels. It does not authorize or launch another model run.

## Recommendation

Keep the manuscript workspace and the debate stage. Change how candidate findings are discovered. Build a compact, source-linked account of the actual experiments, turn important uncertainties into executable evidence tasks, and give debate the resulting observations and counterevidence. Test this against a capable ordinary single-agent reviewer before expanding the study.

The objective is more specific, supported scientific feedback at a defensible cost. More tool calls, more comments, or a more detailed coverage record are not success criteria.

## What the comparison tells us

The four-paper investigator and debate outputs each directly matched 7 of 51 frozen human concerns and partially matched another 10. Debate retained all 20 original findings. It used 95,487 additional tokens, approximately 66% of investigator token usage, without changing the overlap scores. No reviewing call invoked an investigation tool.

The before-and-after text nevertheless shows a plausible narrower role for debate. For example, the plant debate explicitly acknowledged root-level summaries and reported biological replicates while retaining a request to clarify statistical units. The confinement debate acknowledged fixed-cell evidence while narrowing the inference about adaptation of individual lineages. These are author-side counterarguments and qualifications. They have not been independently shown to improve review usefulness or correctness.

The main apparent bottleneck is discovery. The system repeatedly found general causal-inference and replication questions while missing specific concerns about induction, treatment timing, experimental comparators, volume normalization, and visual evidence. Prompts instructed it to inspect evidence, but those instructions did not cause tool use. A self-reported examined status with a valid quotation did not establish that an experimental question was resolved.

The available data do not show that the workspace beats a plain reviewer. They also do not prove that the initial reviews are incorrect. The automated support judge accepted every selected finding, including reasonable questions. That criterion is too weak to establish a useful scientific contribution by itself.

## Proposed workflow

### 1. Build the experiment map before writing criticism

Use the existing immutable manuscript blocks, page locations, captions, and reference records. Add an explicit inventory of accessible original PDF pages, figure panels, tables, and supplements. Distinguish content available through a tool from content already attached, and distinguish both from genuinely unavailable content. Keep provisional PDF extraction labels visible.

A first Sol call creates a concise experiment map. Each entry records the claim, intervention or comparison, outcome, experimental unit, relevant methods, figure or table location, and unresolved facts. Cap this at eight major experiment entries for the prototype. Link every recorded fact to its source and use unknown where the input does not establish it. Do not let the map invent treatments or controls.

This call produces at most three prioritized evidence tasks, rather than a finished five-point critique. Questions should arise from the manuscript's actual experiments. Human reviews remain hidden. The existing six areas can guide coverage, but are not a checklist of presumed defects.

### 2. Execute specific evidence tasks

A second Sol call investigates the tasks using the existing bounded tools. For a task that depends on a figure or table, deliver or retrieve the actual page. For an apparent missing method, search the relevant methods and available supplements for the detail that would resolve it. Permit small calculations on reported quantities. No full analysis reruns, large datasets, or author-code execution.

Useful task forms include:

- Reconstruct which groups received an intervention, at what dose and time, and identify the comparison supporting the claim.
- Reconcile the biological and statistical units reported in the methods and a figure caption.
- Determine whether an image or plotted outcome distinguishes the proposed mechanism from a concrete alternative.
- Check whether a derived measurement measures the quantity named in the conclusion.

These are general task forms. Questions learned from the six development papers must not be inserted into fresh-paper prompts as answers to find.

For each task, save the requested check, observations, supporting evidence, author-side explanation, remaining uncertainty, and source-delivery receipts. An evidence-dependent task cannot be marked completed without the required source access. A receipt proves that material was returned or attached, not that the model interpreted it correctly. The observation and scientific inference still need assessment.

Use four evidence operations in this stage and preserve two for debate. Count automatically attached pages against the same source-access allowance. Cache and reuse source material within the review. Return bounded source extracts rather than repeatedly copying the entire paper into each handoff.

Produce at most eight candidate findings with provenance. Keep all candidates and unresolved tasks. The editor selects at most five final findings, so early selection does not permanently erase potentially useful observations. The ordinary comparator receives the same final finding allowance.

### 3. Keep debate, with a specific job

Keep one fresh debate call. Give it the complete candidate ledger, task results, original evidence, and counterevidence. For each important allegation, it must state the strongest author defense, identify what evidence distinguishes the competing interpretations, and retain, narrow, reject, or leave the concern unresolved. It may use the two reserved evidence operations when a consequential disagreement can be resolved.

Do not add more rounds or a large specialist team yet. Do not force a rejection or a change just to make debate look productive. Preserve every candidate and its disposition. Evaluate debate on material corrections, avoided unsupported allegations, lost valid findings, and final coverage. A more polished defense paragraph alone does not establish a benefit.

Retain source-linked comments and optional wording changes in the existing UI. Only propose edits supported by the manuscript. Do not invent numerical corrections, missing methods, results, or citations.

## What to reuse and what to defer

Reuse the source anchors, source-integrity checks, annotation UI, arithmetic tools, image handoff, citation metadata lookup, raw-response preservation, and guarded editor package. Keep Paper Scaffold prose, readability, and word counts as a separate editorial layer. Do not optimize those warnings as scientific-review findings.

Defer broad literature discovery, extensive citation-support analysis, new specialist teams, more debate rounds, and manuscript reconstruction into an authoring system. Missing literature remains important, but reliable source-dated retrieval and protection against public-review leakage require a separate experiment. DOI identity checks do not answer whether a cited paper supports a claim.

## Smallest informative next test

First implement and test the task executor offline. Use saved development papers to test source locations, unavailable assets, wrong-page requests, exact quotations, numerical provenance, and missing-method searches. These are engineering cases and cannot establish generalization.

Then run at most one live evidence-stage smoke test on a development paper. Its purpose is to confirm that required source access occurs, produces interpretable observations, and stays within a reasonable budget. Do not score known human-concern recovery as a new efficacy result. If access fails, stop and fix the infrastructure before selecting fresh evaluation papers.

After that gate, use two fresh experimental papers. Generate three outputs per paper:

| Output | How it is generated |
| --- | --- |
| Ordinary single-agent review | One capable Sol session with the same manuscript, supplements, page tools, and opportunity to inspect evidence |
| Evidence workflow before debate | Experiment-map call followed by evidence-investigation call |
| Evidence workflow after debate | Reuse that investigation and add one debate call |

The intermediate condition is reused, so it adds no separate generation call. This requires four generation calls and one automated evaluation call per paper, or ten calls across two papers. Including the development smoke test gives eleven calls at most.

Use Sol medium throughout. Give both review approaches the same source access, final five-finding limit, and six-operation allowance. The ordinary reviewer should be explicitly encouraged to inspect key evidence and work through its review, rather than being restricted to a short text-only answer. It does not receive human reference concerns or the other condition's findings.

Use a proposed 600,000 observed-token stop for the smoke test and two-paper comparison combined, checked between calls without automatic increases. A single call can exceed the remaining allowance, so this is not a hard within-call ceiling. Save actual input, cached input, output, tool-use, and elapsed-time totals by stage. Preparation usage is separate. Equal maximum opportunities do not guarantee equal consumed tokens. If the workflow uses substantially more compute, report that and do not claim an efficiency advantage or isolate architecture from compute.

This proposed trial has not started. Its final source list, evaluation rules, and budget must be frozen before any new generation.

## Improve evaluation before the next comparison

Audit the human reference list before generation. Separate substantive scientific concerns from editorial requests, group duplicate concerns while preserving their quotations, and distinguish material assessable from the supplied manuscript from unavailable video or data content. Freeze the definitions and denominators before viewing model outputs.

Use a label-blinded evaluator on all three outputs, with order fixed before scoring. Supply the same necessary source evidence for both methods. Do not silently discard critical image evidence to satisfy an attachment limit. Resolve how that evidence is provided during the offline implementation stage. Report direct and partial human overlap separately.

Also assess whether each criticism identifies a specific scientific issue, whether its inference follows from the source, whether counterevidence defeats it, and whether acting on it could materially affect interpretation or reporting. Being phrased as an author question must not automatically earn a supported rating. Keep reasonable clarification requests distinct from demonstrated defects.

Limit manual assessment to a small blinded sample, ideally six to ten findings reviewed by someone with relevant scientific expertise. Include substantive changes made by debate and randomly selected findings. If such assessment is unavailable, retain that limitation and make no expert-correctness claim. Manual samples and automated scores should not be presented as precise false-positive estimates.

## Decision gates

The engineering gate requires real source access for evidence-dependent tasks, useful source-specific observations, preserved raw findings, and honest unresolved states when evidence is missing.

For the two-paper development comparison, a promising result would be at least two additional distinct, supported direct human-concern matches per paper over the ordinary single agent, without adding materially unsupported major allegations. This is a proposed practical threshold, not a statistical significance test. Count related reference concerns conservatively. Record valid additional concerns outside the human list separately.

Assess debate separately. It earns further investment if it corrects a consequential interpretation, prevents an unsupported allegation, or adds a validated concern without losing useful findings. If it only rewrites the same review, keep it optional and do not frame it as the source of scientific improvement.

If these gates fail, do not expand to more papers or claim success from greater tool activity. Inspect task selection, evidence access, and inference quality. If they pass, seek authorization for a larger fresh-paper study. The defensible publication target is then a measured improvement in specific evidence-grounded review findings, with costs and limits reported. Superiority remains a hypothesis until supported by that study.
