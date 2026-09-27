# PRA domain expansion implementation plan

Prepared on 2026-09-25. Status: implementation specification. The domain research and build assignments are complete. New domain skills and connectors are not yet implemented, installed, or manuscript-validated by this planning work.

## Decision

Build a broad, modular review system around the existing manuscript workspace, investigation, debate, and editing loop. Support a paper through the combination of its subject, study design, measurement methods, and evidence needs. A manuscript can belong to several domains. Only the relevant skills and tools enter a particular review.

Keep the investigator and debate workflow. More domain coverage should not automatically mean more reviewers, more model calls, or larger prompts. First improve what the existing reviewers can inspect and how they retain evidence. New lookups must answer specific unresolved manuscript questions.

The build catalog below contains 21 domain packages and 12 shared work packages. It is a comprehensive initial backlog, not a claim to cover every specialty. Each domain package contains several focused skills. Coverage can be partial and must be labeled honestly.

Build independent domain packages concurrently once their shared interface is fixed. Do not wait for a paper benchmark in one domain before building the others. This central schedule supersedes the slower rollout suggestions in the domain research appendices. Credentials, source terms, and scientific validation remain capability-specific dependencies.

Full author-analysis reproduction, large raw-data downloads, and computational-paper benchmarks remain outside the prototype. Small calculations and static checks are useful when they address a review question. Uncertainty, ambiguity, and inaccessible evidence remain valid outcomes.

## What the current system needs

The existing implementation provides an imported manuscript with stable block locations, local Scaffold diagnostics, bounded manuscript and literature tools, source-anchored findings, an investigation stage, a debate ledger, and a revision interface. This is the foundation to extend.

The review and debate prompts currently assume experimental biology. The runtime has a fixed tool allowlist. External URLs do not have the same validated evidence structure as manuscript quotes. The initial search areas are useful for experimental papers but do not adequately describe qualitative or theoretical work. These are shared implementation changes, not problems each domain agent should solve independently.

Recent transfer reviews exposed three distinct limitations: a relevant question may never be investigated, an accepted author defense can disappear from the final wording, and valid evidence can be attached to an incorrect block. Adding databases will only help the first problem directly. Evidence transport, debate reconciliation, and validation must improve with the domain expansion. See [the transfer results](pra-transfer-two-results.md).

## Target review path

1. Import the manuscript, references, figures, tables, and supplements with stable locations and extraction-quality flags.
2. Assemble a paper profile from quoted manuscript evidence: domains, design, central claims, measurements, organisms or populations, and named records.
3. Load shared review instructions plus the most relevant domain and methods skills. Resolve ambiguous classifications without forcing a checklist onto the paper.
4. Run local Scaffold and consistency checks. Present their results as advisory evidence with manuscript locations.
5. Investigate consequential uncertainties. Use narrowly scoped literature, registry, or domain-record lookups when they can change the review judgment.
6. Preserve findings, unresolved questions, counterevidence, and the inspected source cards before debate.
7. Debate the scientific interpretation and proposed disposition of each issue. A missing database record cannot by itself dismiss or establish a concern.
8. Validate final comments against their supporting and qualifying evidence. Preserve deferred issues in a visible appendix even when they do not fit the main review.
9. Give the editor an anchored review, evidence trail, proposed edits, and unresolved author questions. Keep scientific findings separate from optional copy edits.
10. On an accepted revision, invalidate affected checks, retain the previous history, and re-review only the affected claims within a bounded loop.

## Shared implementation backlog

| ID | Work package | Required implementation and completion evidence |
| --- | --- | --- |
| C01 | Skill and capability registry | Versioned manifests with triggers, design applicability, resource dependencies, source revisions, license status, input/output schemas, limits, fixtures, and measured maturity. Reject duplicate IDs and invalid dependencies. Runtime loads selected skills only. |
| C02 | Manuscript evidence model | Stable claim, entity, reference, table-cell, figure-panel, and supplement handles. Preserve exact text and extraction uncertainty. A figure's missing OCR is not evidence that a feature is absent. Link annotations back to Scaffold and export locations. |
| C03 | External evidence model | Source cards with record ID, field or excerpt, URL, request, retrieval time, version, publication time, hash, access status, and interpretation limits. Bind every external claim to a validated card. Support conflicts, corrections, superseded records, and unknown versions. |
| C04 | Shared connector runtime | Provider-specific adapters over bounded HTTP or evaluated MCP transports. Central timeouts, rate limits, retry accounting, authentication, caching, byte limits, and redacted receipts. Preserve raw permitted evidence outside prompts. Validate responses and never treat tool errors as negative scientific evidence. |
| C05 | Paper and methods routing | Replace biology-only defaults. Combine domain, study design, methods, and claim triggers. Support mixed-domain papers, low-confidence routes, and methods-only fallback. Select skills using available manuscript content without adding a mandatory router model call. |
| C06 | Literature and bibliography | Connect Scaffold reference checking to imported references using canonical IDs. Separate bibliographic validity, citation support, prior-work search, corrections, and data availability. Resolve preprint and journal versions. Use broad metadata discovery with targeted accessible full text. |
| C07 | General scientific checks | Map outcome definitions, measurement thresholds, exclusions, missingness, comparators, experimental units, clustering, uncertainty, multiplicity, and claim scope. Include appropriate qualitative and theoretical alternatives. Small arithmetic requires explicit inputs, units, and assumptions. |
| C08 | Reporting and registration | Versioned design-specific reporting questions, registration identity, protocol comparison, amendment chronology, and data/reagent availability checks. Current-record APIs need a separate history retrieval path for historical comparisons. Return unknown historical state when unavailable. Distinguish reporting gaps from demonstrated design flaws. Do not turn checklist counts into a quality score. |
| C09 | Debate and persistent issue ledger | Track individual actionable questions, supporting evidence, and author defenses across every round. Distinguish supported concern, clarification, unresolved issue, contradicted allegation, and presentation deferral. Resolution needs a linked explanation. A word limit is not a scientific resolution. |
| C10 | Manuscript revision and interface | Show source cards, source limitations, conflicting evidence, review coverage, and deferred questions at the relevant location. Export comments and tracked proposals to Scaffold and Word workflows. Preserve citation keys. Never automatically invent data, references, or a substantive scientific change. |
| C11 | Bounded revision loop | Classify copy edits versus changes to scientific meaning. Apply edits according to the existing user policy. Recheck stale anchors and affected claims. Record author responses separately from verified evidence. Add iteration, token, and no-progress stop conditions plus rollback. |
| C12 | Evaluation and release accounting | Preserve single, before-debate, and after-debate artifacts. Validate inputs before judging. Freeze test manuscripts and source packets. Track source correctness, coverage, retention, false findings, actionable value, costs, and gate failures separately. Display maturity per capability rather than one blanket supported label. |

Concrete integration points are `paper_workspace/review_schema.py`, `discovery.py`, `investigation.py`, `model_runtime.py`, `claim_checks.py`, `debate_revision.py`, `reviewer.py`, and `scaffold_checks.py`. Keep old experiment outputs immutable and version new protocols and schemas.

The existing ledger also needs an explicit round-trip audit. Carry both original discarded hypotheses and subsequently stored source hypotheses into later revisions. Preserve their identities and evidence without recursively nesting whole prior review packets. A compact canonical issue history should survive normalization, export, and re-import.

## Domain build catalog

Each row is an independently assignable package. Method skills and resource adapters can be reused across rows. The resources named here are a mixture of documentation-verified candidates and audit-required extensions. Exact access and verification status are described in the linked appendices. Inclusion in this table does not mean an API has been connected.

| ID | Domain package | Focused skills to build | Resource starting points |
| --- | --- | --- | --- |
| D01 | Molecular and cell biology | Entity and reagent identity, perturbation specificity, rescue and control interpretation, localization, interaction and pathway evidence, biological versus technical replication | UniProt, GO, Reactome, STRING, IntAct, Expression Atlas. Audit RRID, Cellosaurus, and assay-specific reporting resources. |
| D02 | Structural biology | Experimental versus predicted structure, construct and residue mapping, coordinate coverage, assembly versus contact, validation and uncertainty | RCSB PDB APIs or evaluated official MCP, wwPDB validation, AlphaFold DB with prediction labels |
| D03 | Proteomics and modifications | Deposition metadata, peptide and isoform mapping, modification definitions, localization versus identification, protein inference and reported false-discovery scope | PRIDE, ProteomeXchange, UniProt, UniMod. PhosphoSitePlus is conditional on its license. |
| D04 | Genetics and genomics | Assembly and transcript identity, variant normalization, assertion provenance, population applicability, deposition and sample design | NCBI Datasets, Ensembl, ClinVar. Audit population and assay-specific archives before adding them. |
| D05 | Microbiology and microbiome | Strain and sample identity, contamination and sampling questions, genotype versus resistance phenotype, cluster version and transmission claims | NCBI records and Pathogen Detection, proposed BV-BRC. Community-level claims also use ecological methods. |
| D06 | Neuroscience and behavior | Anatomy and coordinate context, behavioral endpoint validity, unit of replication, atlas or morphology comparability, acquisition and analysis reporting | NeuroMorpho, literature. Audit Allen and EBRAINS before connecting. Reuse measurement and psychology skills. |
| D07 | Physiology and animal research | Preparation and condition matching, intervention timing, randomization and exclusions, physiological interpretation, model assumptions and units | Literature, CellML and Physiome for named models. Audit ARRIVE guidance for appropriate animal designs. |
| D08 | Plants and agricultural biology | Cultivar and assembly identity, developmental and growth context, field or greenhouse replication, homology and expression scope | Ensembl Plants, Expression Atlas, public TAIR releases with terms controls |
| D09 | Chemistry and pharmacology | Chemical identity and stereochemistry, assay comparability, characterization, dose and concentration, reaction and yield consistency | PubChem, ChEMBL, NIST Chemistry WebBook |
| D10 | Clinical interventions and diagnostics | Registry and protocol comparison, outcomes and harms, allocation and masking, participant flow, diagnostic reference standards, clinical claim calibration | ClinicalTrials.gov, public protocols, design-specific CONSORT, SPIRIT and STARD references. ICTRP downloads are a candidate fallback subject to deployment terms. Its web service and crawling have separate conditions. |
| D11 | Epidemiology and public health | Target population and estimand, temporal ordering, confounding, selection and missingness, surveillance denominators, prediction versus causal claims | STROBE-linked methods, public registrations, exact public-series metadata. Link records rather than upload participant data. |
| D12 | Psychology and behavioral science | Preregistration, construct and instrument mapping, scoring and exclusions, manipulation checks, confirmatory versus exploratory claims | OSF, APA JARS, targeted instrument literature, COSMIN concepts where applicable |
| D13 | Economics and quantitative social science | Identification assumptions, survey populations and weights, repeated observations, administrative definitions, units and historical vintages | AEA RCT Registry, Census, World Bank, optional FRED or ALFRED |
| D14 | Qualitative, mixed methods, and education | Methodological coherence, sampling rationale, reflexivity, interpretive evidence, context and transferability, integration of qualitative and quantitative strands | JARS-Qual, JARS-Mixed, applicable COREQ guidance, source literature. No universal saturation or inter-rater rule. |
| D15 | Ecology, evolution, and conservation | Taxon identity, sampling effort and detectability, site independence, space and season, range claims and management inference | GBIF, shared plant tools. Audit WoRMS and OBIS for marine applications. |
| D16 | Earth, environment, and climate | Product lineage, spatial reference, temporal baseline, calibration and uncertainty, station or collection comparability | NASA CMR, optional NOAA CDO. Audit USGS and PANGAEA routes. |
| D17 | Materials and crystallography | Composition and phase, processing and specimen dependence, structure record identity, characterization and property conditions | COD, allowlisted OPTIMADE providers, existing checkCIF reports, optional Materials Project |
| D18 | Physics, engineering, and metrology | Dimensional reasoning, calibration, uncertainty and covariance, instrument limits, boundary conditions, scaling and reported model assumptions | BIPM SI and JCGM references, local calculations, exact literature |
| D19 | Astronomy and space science | Object identity, coordinate epoch and frame, selection function, upper limits, calibration and observation provenance | SIMBAD, VizieR, optional NASA ADS |
| D20 | Mathematics and computing | Definitions and assumptions, claim-to-proof or evidence mapping, benchmark split and leakage claims, comparison fairness, complexity and uncertainty reporting | Manuscript evidence, bounded mathematical checks, bibliographic and version records. No code reproduction or initial computational-paper pilot. |
| D21 | Humanities and interpretive scholarship | Primary versus secondary sources, edition and translation identity, quotation context, archival provenance, argument scope and counterexamples | Bibliographic records and author-supplied primary sources. Specialized archive connectors require a separate audit. Initial status is limited methods coverage. |

Systematic reviews, evidence synthesis, surveys, measurement studies, imaging, animal work, laboratory experiments, and observational or qualitative designs are cross-domain routes. Do not duplicate their methods inside every domain package. Add PRISMA-linked search and selection checks, effect-size and denominator consistency, and synthesis-scope checks without rerunning a meta-analysis. Pin reporting-guideline versions and audit reuse rights before incorporating material.

Domain research and detailed review tasks:

- [Biology packages and source limitations](pra-domain-plan-biology.md)
- [Health and social science packages and source limitations](pra-domain-plan-health-social.md)
- [Physical science and environment packages and source limitations](pra-domain-plan-physical-environment.md)
- [Initial tools assessment and prior public API smoke checks](pra-domain-tools-assessment.md)

## Skills and resource acquisition

Write PRA-specific skills around review decisions. Each skill should teach what triggers an investigation, what evidence to inspect, how to compare contexts, how to recognize a benign explanation, and when to stop. A catalog of database commands alone is insufficient.

Reuse selected, audited instructions or helpers from [Google DeepMind Science Skills](https://github.com/google-deepmind/science-skills) and [K-Dense scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills). Pin the source revision and preserve required attribution. Check the license of each reused component and the terms of its data source separately. Do not import entire collections or treat their existence as validation of peer-review performance.

Evaluate the provider-maintained [RCSB MCP](https://github.com/rcsb/rcsb-mcp) for structural access. Most bounded lookups can use direct APIs under our common runtime. Installing a desktop connector alone does not expose it to PRA's restricted review process. Every exposed tool needs explicit runtime integration and receipt coverage.

Builders may discover additional resources within their assigned domain. Add a candidate when it addresses a concrete review failure or a common consequential question. Implement it only after documenting access, terms, response structure, cost, and a meaningful fixture. Keep speculative or inaccessible sources in the backlog with an explicit reason. A paid or account-dependent service is optional and must not silently become a baseline dependency.

## Required package contract

Proposed layout under a common package root:

```text
domains/<domain_id>/manifest.json
domains/<domain_id>/skills/<skill_id>/SKILL.md
domains/<domain_id>/references/source-notes.md
domains/<domain_id>/fixtures/
domains/<domain_id>/tests/
sources/<provider_id>/
```

The coordinator fixes actual repository paths and interfaces before implementation starts. Provider adapters have one owner and are shared rather than copied into domain packages.

Every manifest must declare:

- Domain, design, and claim triggers with positive and negative examples.
- Prerequisite entities and required manuscript evidence.
- Supported review questions and explicit exclusions.
- Skill source, pinned revision, license, attribution, and review date.
- Required and optional providers, access mode, tool schemas, and budget requests.
- Normalized evidence fields plus domain context such as organism, isoform, assay, vintage, or coordinate frame.
- Positive findings, benign near-matches, ambiguous records, unavailable sources, and interpretation-boundary fixtures.
- Current maturity, known limitations, and evaluation receipts.

Use separate maturity fields for source documentation, adapter implementation, fixture testing, live access, and manuscript review evaluation. A package can pass local tests while its authenticated connector remains unavailable. Never compress these distinctions into a single validated flag.

## Evidence and cost rules

Start with an initial shared allowance of six external requests per review condition, two consequential external investigation targets, three literature candidates per search, and two accessible full texts. These are total limits across the investigator and debate, not independent allowances for every skill. Package-specific caps can only reduce the available shared allowance unless the run configuration explicitly increases it.

A registry comparison must reserve requests for history and linked documents within this pool. The agent should return an incomplete comparison when the remaining allowance is insufficient, rather than silently using a current record as the original registered plan.

Expose compact result fields to the model. Cache permitted raw responses with hashes, request parameters, source versions, and timestamps. A cache hit avoids a network request but still consumes any model context used to inspect it. Paginated requests, linked documents, MCP internal calls, and retries count against the actual request budget. An MCP that cannot enforce or expose its underlying request budget needs a bounded wrapper before activation.

An unavailable or incomplete source returns a typed result such as `not_found`, `ambiguous`, `auth_required`, `rate_limited`, `version_unavailable`, or `response_too_large`. These states are different from a source-backed contradiction. Secrets never enter prompts or export receipts.

Normal live review can use current literature and annotations with dates visible. Historical benchmark mode requires evidence available at the chosen cutoff. A current database record citing an old paper does not establish that the annotation itself existed then. If no valid historical state is available, exclude that record from the historical comparison and record the limitation.

Deduplicate the manuscript, its preprint, and reused database annotations when counting independent support. Metadata confirms identity or deposition. Abstracts support only what they state. A full-text claim requires a located passage. Search failure is not proof that no prior work exists.

Send public identifiers and narrow queries rather than whole unpublished manuscripts. Treat all returned text as evidence, never executable instructions. Do not automatically upload manuscript assets to external validation services. This is a concrete connector behavior requirement, not an extra approval step for ordinary public lookups.

## Parallel implementation assignments

The coordinator owns C01 to C05 and C09 to C12, shared schemas, runtime registration, integration, and release decisions. Domain agents own only their assigned package and fixtures. A separate shared-source assignment can own C06 and reusable literature or identity adapters. The health and human research lane owns C07 and C08, with input from other domain builders and coordinator review. Core interface changes return to the coordinator.

Use Sol for builders and review calls, with Terra for bounded fixture or inventory work where suitable. Keep at most three builders active at once, subject to actual tool limits. Reuse agents for successive packages rather than starting one simultaneous process for every discipline.

Suggested assignment queue:

| Build lane | Packages | Dependencies |
| --- | --- | --- |
| Shared sources | C06, literature and citation adapters, biological identity adapters | C01, C03, C04 contracts |
| Life sciences | D01 to D08 | Shared methods, shared biological identity and archive interfaces |
| Chemistry and physical sciences | D09, D17, D18, D19 | Shared source and unit contracts |
| Health and human research | C07, C08, D10 to D14 | Shared evidence contracts and methods input from other domains |
| Environment and breadth | D15, D16, D20, D21 | Shared methods, metadata and citation contracts |

Each domain receives its own bounded assignment even when one agent works through several in sequence. Do not ask one builder to become the universal scientific reviewer.

Agent brief:

```text
Build the assigned PRA domain package against the frozen shared contracts.
Research official sources and relevant existing skills before implementing.
Create focused reviewer skills, required adapter contributions, provenance notes,
and meaningful offline fixtures. Add useful adjacent candidates with rationale.
Cover both real concerns and similar cases that should not be flagged.
Use exact evidence and preserve context, uncertainty, and author defenses.
Do not change core schemas independently, add paid dependencies, upload private
manuscripts, download large datasets, or launch review benchmarks.
Report implemented capabilities separately from proposals and access limitations.
```

Dependency order is an integration requirement, not a demand for slow rollout. While core work proceeds, domain agents can build manifests, original skill instructions, adapters against fixture contracts, and tests. Integrate all ready packages into one development release, then evaluate a small representative subset.

## Acceptance before model trials

Check the actual behavior of each adapter: exact identity, schema interpretation, source version, bounded output, cache identity, access failure, and request accounting. Include ambiguous names, incorrect context, stale records, conflicting evidence, and malformed responses. Offline fixtures should be redistributable, otherwise keep a retrieval recipe and use synthetic test records.

Check the review chain with a small set of deliberately constructed cases. One real concern should survive, one superficially similar nonissue should be dismissed for the correct reason, and one uncertainty should remain unresolved. A qualifying author control must remain in the final comment if it limits the criticism. Verify source-card and manuscript-anchor round trips through normalization, debate, editing, export, and another review round.

Do not write tests that merely look for phrases in prompts. Prompt instructions need behavioral evaluation. Deterministic tests can verify data transport, budgets, validation, and exact reference preservation. They cannot establish domain judgment on their own.

## Bounded cross-domain evaluation

The proposed first panel is four papers: one molecular or biochemical study, one experimental chemistry or materials study, one registered clinical or observational health study, and one ecology study. Choose papers with accessible manuscripts and relevant supplements, clear domain-tool triggers, and manageable length. Use one of these as a development paper and freeze the other three before inspecting their review outcomes.

This panel does not evaluate every implemented package. In particular, psychology, economics, qualitative, and mixed-method review remain manuscript-unevaluated unless one of the selected papers genuinely exercises those routes. Report only the skills and sources actually used on each paper as evaluated.

For each paper, run a tool-equipped single reviewer and the investigator-plus-debate workflow with the same Sol model, manuscript packet, available capabilities, and total external request allowance. Save the investigator output as the before-debate condition. Let an anonymous judge compare the three review artifacts using manuscript and source evidence, with condition labels hidden and presentation order randomized. One single call, one investigator call, one debate call, and one judge call gives a maximum of 16 planned model calls across four papers. No automatic retries or extra judges are included.

This tests the deployed workflow with a capable baseline. It does not isolate tool benefit, and the two-stage workflow receives more model computation. Report measured token and time differences explicitly. If a later study claims superiority under equal compute, it needs a separately specified matched-budget baseline. Avoid a large ablation matrix now.

Use the development paper to fix failures and freeze the resulting configuration before running the other three. Do not tune between frozen-paper results. Rerunning a paper after seeing its weaknesses is a development result, not fresh confirmation. A historical human-review comparison is eligible only if the manuscript version and evidence cutoff can be respected. For other papers, use present-day review quality and label the evaluation accordingly.

Score source fidelity and valid anchors before preference. Then assess supported consequential findings, unsupported claims, author defenses omitted from final wording, actionable questions retained or resolved, missed issues, reference accuracy, edit fidelity, request cost, model tokens, and latency. Mark a gate failure as a failure rather than silently repairing it for a cleaner score. Store rejected raw output for diagnosis.

An anonymous model judge remains exploratory, especially if it is from the same model family. Manually check the central preference-driving claims against their sources. Published human comments are another reference, not complete ground truth. Before a publication claim of better review quality, obtain limited independent domain assessment on a frozen sample and predefine the claims and analysis. Four papers can reveal transfer failures and promise, not establish superiority across 21 domains.

## Completion and next action

The next implementation step is C01, C03, and C04: freeze manifests, evidence cards, and the shared connector interface. Dispatch domain builders against those contracts immediately, with C05, C06, C09, and C10 integrated in parallel. Extend existing local checks and preserve the full issue history before adding any review-model experiment.

The development release is complete when every catalog package has its declared skills or an explicit limited-coverage status, implemented sources meet their acceptance tests, and the end-to-end review and editing path preserves evidence. Domains without manuscript evaluation remain labeled unevaluated. Broader implementation does not require broader claims about performance.
