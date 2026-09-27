# Paper workspace redesign

Design proposal, 2026-09-24. No review trials were launched for this proposal. The older runners remain stopped. A refreshed account budget does not remove the user's requirement to keep development trials small and obtain authorization before larger validation.

## Research question

Does a structured paper workspace help an agent produce more correct and useful scientific criticism within a comparable resource budget? The coding-agent interface provides file navigation, search, persistent notes, and optional small checks. The review itself focuses on the science reported in the manuscript.

The contribution can be the infrastructure and investigation procedure. Multiple agents are a possible implementation choice, not a required result. Earlier experiments did not establish a PRA advantage. Some reference pairings were unverified, and the latest error-detection pilot stopped before completing its pair. Those results do not establish that every current implementation is worse, nor justify a superiority claim.

## Scope correction from the user

The prototype must use a non-computational experimental paper. A mechanistic cell-biology or other experimental biology paper is a suitable starting category. Computational-methods papers and software-focused papers are excluded from the prototype.

Review the manuscript, figures, tables, supplementary documents, and relevant literature. Assess study design, controls, replication, reported statistical reasoning, claim support, interpretation, and prior work. Full reproduction of the analysis is outside scope. Do not download large raw datasets, rebuild analysis environments, rewrite author code, retrain models, or rerun complete pipelines.

Optional calculations must answer a specific review question using values already reported in the paper or a small supplied table. Examples include checking denominators, percentages, unit conversions, or an explicitly stated numerical comparison. Do not infer missing inputs or turn inability to reproduce an analysis into a scientific defect. Any broader reanalysis would require a separate scope decision and user authorization.

## Reuse the existing foundation

The current PeerReviewAgents source already contains structured conversion in `peerreviewagents/ingest/structured.py`, section and bibliography ingestion in `ingest/loader.py`, deterministic prose statistics in `ingest/prose.py`, and research adapters in `research/`. This proposal is based on source inspection, not a fresh runtime validation of those components.

Keep these components where they work. Extend the converter output to retain document blocks, figures, table structure, page locations, and citation occurrences. Do not replace the parser or rewrite the bibliography with an LLM by default. Use model assistance only for an explicitly uncertain interpretation, preserving the original text and recording the correction.

## Workspace contract

Each manuscript gets an immutable input package and a writable investigation directory:

```text
paper/
  manifest.json
  original.pdf
  manuscript.md
  outline.json
  sections/
  blocks.jsonl
  figures/
  tables/
  references.jsonl
  citation_occurrences.jsonl
  statistics.json
  supplements/
  literature/
  investigations/
  findings.jsonl
  review.md
```

The manifest records manuscript version and hashes, parser version, missing inputs, extraction health, and the literature cutoff date. Blocks and references have stable IDs. Derived claims and findings link to exact source passages and available page coordinates. Missing coordinates remain unknown. Retain the whole manuscript and section hierarchy so local investigations do not miss answers elsewhere.

Counts describe words, sentences, references, figures, tables, and section coverage. State the counting convention and whether captions, equations, and bibliography are excluded. Counts and prose measures support navigation and extraction checks. They do not establish scientific quality or generate criticism merely because a value is unusual.

## Investigation tools

| Capability | Inspectable output | Boundary |
| --- | --- | --- |
| Read a section, search the manuscript, inspect a page | Exact passages with stable locations | Search the whole paper before claiming an omission |
| Resolve references and connect citation occurrences | Metadata match, ambiguity, or lookup failure | A failed lookup does not establish a fabricated reference |
| Check a cited claim | Manuscript claim beside a located source passage | DOI resolution and abstract relevance do not establish claim support |
| Search prior work | Cached queries, candidate papers, dates, and comparison notes | Missing citation requires a material effect on novelty, interpretation, or method justification |
| Check a reported numerical assertion | Small calculation using reported values, with assumptions and output | No raw-data reconstruction or full analysis rerun |
| Trace experimental claims to evidence | Claim, experiment, controls, replication, result, and competing explanation | Assess what the reported evidence supports without inventing missing data |

Crossref supplies bibliographic lookup and DOI metadata through its [REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/). Existing research adapters can supply initial literature discovery. Preserve retrieval provenance and access failures. Read relevant full text where available, and explicitly mark abstract-only support. For retrospective evaluation, distinguish prior work available at submission from later discoveries. Later papers can inform a current review but cannot establish an omission at the original submission date.

Keep the existing parser first. If page anchoring proves inadequate, [GROBID's documented coordinate output](https://grobid.readthedocs.io/en/latest/Coordinates-in-PDF/) is a concrete alternative to assess on fixtures before changing the pipeline.

## Agent behavior

Start with one persistent agent session using a coding-agent interface. It reads the full-paper overview, identifies the central scientific claims and supporting experiments, selects a few consequential questions, and writes an investigation plan. Most work consists of reading, searching, comparing passages and figures, checking references, and revising interpretations. Small scripts are optional aids for reported-value checks and workspace operations. It retains artifacts and solved questions between steps rather than repeatedly rereading the entire manuscript in fresh role prompts.

For example, a paper claims that a protein directly regulates a cellular process. Trace the claim to the perturbation and rescue experiments, check which controls distinguish the proposed mechanism from alternative explanations, inspect whether the legends distinguish biological from technical replicates, and compare the conclusion with relevant prior work. The output is a located argument about what the experiments establish, not a replacement analysis of the raw measurements.

Run any small generated checks in an isolated workspace with resource limits. Executing or rewriting author-supplied analysis code is outside the prototype. If a review question requires unavailable raw data, record the uncertainty or a proportionate request to the authors. Do not assert an error merely because the reviewer did not rerun the analysis.

Retain a short adversarial evidence check before publication of the review. For each serious finding, explicitly seek the strongest manuscript or literature answer and record what would falsify the criticism. A separate challenger is optional and should be tested later. Do not reinstate a fixed panel merely to preserve a multi-agent narrative.

Every finding records its claim, evidence, counterevidence, executed checks, assumptions, consequence, proposed remedy, and unresolved uncertainty. Separate duplicate relationships from dispositions such as supported, answered, and unresolved. Presentation errors produce local warnings or deterministic repairs. They must not invalidate unrelated completed investigations or trigger a full rerun.

## Smallest first prototype

Build one workspace for an accessible non-computational experimental biology paper with a clear scientific question, several interpretable experiments, readable figures and legends, and available supplementary documents. Choose a paper that can be meaningfully assessed from those materials without large raw datasets or a software environment. Verify section boundaries, bibliography extraction, figure and legend pairing, and source anchors against the PDF before inference. This is an engineering fixture, not validation evidence.

Expose section reading, whole-paper search, figure and page viewing, reference lookup, and optional small calculations on reported values. Include a small literature pass covering at most three claim-driven searches and five central citation checks initially. Cache everything. Avoid building a comprehensive literature-review platform, universal statistical checker, or large reviewer panel.

Only after the workspace works, propose a one-paper comparison with three conditions:

1. A conventional one-shot review as a secondary baseline.
2. A strong plain coding agent with the same original files, figure access, retrieval access, model, and resource allowance, under the same restriction against full reanalysis.
3. The same coding agent with the PRA workspace and investigation procedure.

All conditions review the experimental science and may perform the same small reported-value checks. None may download large raw datasets, rewrite author code, or rerun an analysis pipeline. Condition 2 is the primary comparator. Count preprocessing, planning, tool loops, retries, and grading when reporting costs. Match resource allowances and final review length, then report realized usage and latency. Infrastructure may improve retrieval and evidence organization, but must not receive benchmark answers or private evidence denied to the comparator.

## Evidence required before expansion

Judge distinct, consequential, supported findings and major false allegations under blinded condition labels. Report extraction failures, unavailable evidence, and pipeline reliability separately. Count the paper as the independent unit when later assessing gains across papers. More concerns, longer reports, word counts, and human-review overlap alone are not success measures.

A small manual check is required to establish whether important purported discoveries are actually correct. Automated judges can triage and identify disagreements, but cannot be the sole ground truth for the superiority claim. Benchmark answers and previously published reviews stay outside the review workspace.

One paper is only a feasibility signal. If the new workflow produces a convincing additional finding without more serious false allegations and within the proposed budget, present the artifacts and costs to the user. Obtain authorization before a larger trial. Freeze the improved workflow before testing additional untouched papers, preserve failures, and report uncertainty. An infrastructure paper remains possible even if the multi-agent hypothesis fails, but its claims must match the evidence.

## Paper Scaffold integration and comments in context

The user proposed using Paper Scaffold to present comments and edits at their manuscript locations. The local checkout is `/home/ty/Repos/paper-scaffold`, remote `https://github.com/pgarrett-scripps/paper-scaffold`, inspected at commit `bc4ef429400ae9fc12320f7b78f124079a4bf4d3`. Repository inspection found saved review snapshots, a structural HTML comparison with red deletions and green additions, and the `reviews/ACTIONS.md` ledger. PDF and editable Word export already exist. Native Word tracked changes and anchored review comments were not verified as existing features.

Reuse the review snapshot and diff machinery. Add a separate annotation file with stable source block IDs, source hashes, exact quoted spans, evidence links, rationale, and an optional proposed replacement. Keep author questions distinct from edits. A finding requiring new data, an experimental detail, or an unverified citation remains a comment. Acceptance records an author decision and generates a separate proposed manuscript. It must not silently alter the submitted baseline or mark the underlying scientific issue resolved merely because wording changed.

For an existing scaffold manuscript, attach to its captured document structure. For PDF-only input, first construct the faithful review workspace and verify extraction against the original pages. The scaffold's migration guide itself describes a manual, verifiable process. Do not promise lossless automatic PDF-to-Typst migration. Imported figures can be adopted, and imported numbers should carry manuscript-source provenance. They do not become recomputed results and do not require recreating the author's analysis environment.

A local interface demonstration is available at `prototypes/pra_annotated_manuscript/demo.html`. It reuses the scaffold word-diff function and adds located comments, acceptance controls, a draft preview, and an exportable decision record. All example text and findings are explicitly fictional. This demonstration does not migrate a manuscript, implement native Word comments or tracked changes, or count as a review trial. No model review calls were launched.

Evaluate interface usefulness separately from scientific correctness. Later user testing can assess whether authors locate, understand, and act on valid findings more easily, while tracking harmful or scientifically misleading edits. A more convenient interface does not establish a more accurate reviewer. Larger trials still require authorization.
