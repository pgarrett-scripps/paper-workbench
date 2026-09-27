# Health and social science domain plan

Assessed on 2026-09-25. This plan covers clinical research, epidemiology and public health, psychology and behavioral science, social science and economics, and qualitative and mixed methods. It extends the common evidence-card architecture proposed in [the domain tools assessment](pra-domain-tools-assessment.md). It does not install a service, make a review-model call, give clinical advice, or propose routine reanalysis of participant-level data.

The first implementation should be a registration and protocol comparison skill. It has the best combination of public structured evidence, consequential review questions, and deterministic checks. The next packages should cover study-design reporting, measurement and construct validity, causal-claim discipline, and qualitative or mixed-method integrity. Public population metadata should remain a targeted verification tool rather than a general fact-checking layer.

## Confirmed capabilities

The following capabilities are documented by their primary providers. They are available as public web or API resources, subject to the access limits noted here. They have not yet been integrated into PRA.

| Resource | Confirmed access | Useful review evidence | Access and interpretation limits |
| --- | --- | --- | --- |
| [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/about-api) | Public REST API for current study records. NLM documents API v2 as the modern programmatic route. | Identifiers, study dates, arms, eligibility, enrollment, outcome definitions, analysis populations, results, and linked documents when deposited. | The main API serves the current record. Historical versions and uploaded protocols may require separate web or document retrieval. Registry content is sponsor-supplied and may be incomplete. |
| [WHO ICTRP](https://www.who.int/tools/clinical-trials-registry-platform/the-ictrp-search-portal) | Public cross-registry search and CSV or XML downloads. WHO groups duplicate records and exposes the 24-item Trial Registration Data Set. | Trials outside ClinicalTrials.gov, prospective-registration status, duplicate registry IDs, recruitment dates, outcomes, results links, and protocol URLs when supplied. | The real-time web service has conditions and may carry a cost. Crawling requires permission. Downloaded data have attribution, currency, and noncommercial conditions. WHO does not endorse record accuracy. |
| [OSF API v2](https://github.com/CenterForOpenScience/developer.osf.io/blob/master/swagger-spec/swagger.yaml) | Public GET access for public registrations, schema responses, files, logs, identifiers, and related resources. Registrations are time-stamped, read-only snapshots. | Psychology and social-science preregistrations, registered reports, analysis plans, hypotheses, exclusions, stopping rules, and public amendments. | Embargoed and private content is unavailable. Files may need separate retrieval. Schema forms vary. Project content is not necessarily a registration. OSF has announced project-workflow changes for 2027, so adapters must use documented registration routes. |
| [AEA RCT Registry data](https://docs.socialscienceregistry.org/) | Official documentation states that registry metadata can be downloaded as CSV or JSON. Registration is free and records can carry amendments and additional material. | Economics and social-science trial IDs, intervention arms, outcomes, sample plans, registration timing, amendments, and linked analysis plans. | A record can be retrospective. An amendment date alone does not show what changed, so retain version or amendment text where available. Availability does not establish adherence. |
| [SPIRIT and CONSORT 2025](https://www.consort-spirit.org/) | Official checklists and explanation documents for randomized-trial protocols and reports. | Randomization, masking, allocation, intervention, outcome, harms, participant flow, analysis, and protocol-report completeness. | These are reporting guidelines. Missing reporting can create an unresolved concern, but checklist completion cannot establish low bias or sound conduct. Copyright and reuse terms must be checked before embedding checklist text. |
| [STROBE](https://www.strobe-statement.org/) | Official downloadable checklists for cohort, case-control, and cross-sectional reports. | Setting, participant selection, variables, measurement, bias, study size, missing data, confounding, sensitivity analyses, and generalizability. | STROBE explicitly says it is not a study-quality instrument. Its authors request contact for republication or derivative STROBE work. Store item identifiers and links unless reuse permission is clear. |
| [APA Journal Article Reporting Standards](https://www.apa.org/pubs/journals/resources/apa-style-jars.html) | APA provides JARS-Quant, JARS-Qual, and JARS-Mixed guidance, including reviewer notes. | Psychology-specific reporting, quantitative design, qualitative methodological integrity, researcher perspective, and mixed-method integration. | Some material is copyrighted or tied to APA publications. Use links and short item summaries until reuse rights are confirmed. Reporting adequacy and evidential strength remain separate judgments. |
| [COREQ record](https://www.equator-network.org/reporting-guidelines/coreq/) and [APA JARS-Qual and JARS-Mixed paper](https://www.apa.org/pubs/journals/releases/amp-amp0000151.pdf) | Public descriptions and full guidance are available for interviews, focus groups, qualitative work, and mixed methods. | Research-team position, sampling, setting, data collection, analytic process, reflexivity, evidence for interpretations, and integration across methods. | COREQ is specific to interviews and focus groups. A checklist cannot decide saturation, reflexivity, credibility, or interpretive adequacy without reading the manuscript's evidence. |
| [COSMIN tools](https://www.cosmin.nl/cosmin-tools/) | COSMIN publishes a taxonomy and tools for studies of measurement properties and patient-reported outcome measures. | Content validity, structural validity, reliability, measurement error, invariance, responsiveness, and interpretability. | COSMIN materials have explicit copyright and permission guidance. They are specialized. Do not apply them as a generic scale-quality score or copy their full content without permission. |
| [US Census Data API](https://www.census.gov/data/developers.html) | Public dataset discovery and API access. Census training materials document limited use without a key and higher-volume use with a free key. | Definition, universe, geography, year, table, variable, estimate, and margin-of-error checks for US population claims. | Dataset vintages, variable concepts, geographic boundaries, inflation basis, and survey uncertainty must match the manuscript. Current values cannot validate historical claims. |
| [World Bank Indicators API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation) | Public indicator metadata and values through an HTTP API. | Country, indicator definition, unit, time period, source, and update checks for international development claims. | Cross-country comparability varies. Revisions and source-method changes matter. Country aggregates cannot validate individual-level or causal claims. |
| [FRED and ALFRED API](https://fred.stlouisfed.org/docs/api/fred/overview.html) | REST access to current and archival economic series. ALFRED supports vintage-sensitive questions. | Series identity, units, frequency, seasonal adjustment, observation date, release vintage, and revisions. | Every API request requires a registered key. Some underlying series carry third-party restrictions. FRED aggregates sources, so the original source remains preferable where practical. This is an optional adapter, not a keyless baseline dependency. |

No relevant installed MCP was found in the prior assessment. Public APIs and local HTTP adapters are sufficient for the first release. An MCP would still require explicit PRA runtime integration, allowlisting, provenance capture, and an evaluation. The inspected Google DeepMind Science Skills and K-Dense collections contain reusable literature and scientific-database patterns, but the prior assessment did not identify a ready-made, validated package for these health and social-science review contracts. Reuse their adapter patterns only after license and behavior review.

## Proposed reviewer skills

These are implementation proposals, not confirmed product capabilities.

### 1. Registration, protocol, and reported-outcome comparison

Activate when a manuscript reports a prospective study, intervention, trial registration ID, registered report, preregistration, protocol DOI, or analysis plan.

The skill should resolve identifiers in this order: exact ID in the manuscript, DOI or URL, secondary IDs, then a cautious title and investigator search. It should never silently choose a fuzzy match. It should retrieve the earliest relevant registered state, the state before enrollment or data access when recoverable, later amendments, the protocol or statistical analysis plan, and the manuscript's corresponding passages.

Compare:

1. Registration date, first enrollment or data-access date, completion date, and publication date.
2. Study type, design, arms, interventions, allocation, masking, setting, and recruitment status.
3. Eligibility, target and actual sample size, stopping rules, exclusions, analysis population, and attrition.
4. Primary and secondary outcomes, exact construct, instrument, scoring, metric, time point, and analysis.
5. Confirmatory and exploratory labels, subgroup and interaction plans, multiplicity handling, and adverse events where relevant.
6. Amendments, their dates, stated reasons, and whether changes preceded access to outcomes.
7. Registered results and manuscript values when both are present.

Return a field-level comparison with `match`, `difference`, `unclear`, `not_registered`, or `not_reported`. Preserve exact source text, timestamps, version identity, and manuscript blocks. Label a difference as potentially consequential only after assessing whether it changes the tested question, analysis flexibility, or interpretation. Do not call every registry-manuscript wording difference outcome switching. Do not infer misconduct.

### 2. Design and reporting audit

First classify the design with supporting manuscript text. Supported routes should include randomized parallel and cluster trials, crossover trials, cohort studies, case-control studies, cross-sectional studies, diagnostic-accuracy studies, prediction models, interrupted time series, difference-in-differences, regression discontinuity, instrumental variables, surveys, systematic reviews, and qualitative or mixed-method studies.

Route the paper to compact, source-linked question sets derived from the applicable guideline. Use CONSORT or SPIRIT for randomized trials, STROBE and a relevant extension for observational work, APA JARS for psychology, and COREQ or JARS-Qual for suitable qualitative work. Add PRISMA, STARD, TRIPOD, CHEERS, RECORD, or SQUIRE later only when a paper's design requires them and reuse terms have been reviewed.

The output should distinguish `reported`, `partially_reported`, `not_located`, `not_applicable`, and `substantive_concern`. A missing item is initially a reporting gap. A substantive concern requires a claim-to-design argument, such as differential attrition threatening the comparison or outcome assessment that is not comparable across groups.

### 3. Measurement and construct-validity audit

Build a construct-to-variable map for every central claim. Record the construct, operational variable, instrument or coding rule, respondent or data source, language and population, timing, scoring, transformations, thresholds, and evidence offered for validity and reliability.

Checks should cover:

1. Whether the measure represents the claimed construct and population.
2. Instrument version, translation, adaptation, licensing status, and scoring direction.
3. Multi-item scale composition, reverse coding, missing-item rules, reliability uncertainty, and measurement invariance across compared groups or time.
4. Common-method and informant overlap, proxy outcomes, diagnostic verification, recall period, reactivity, and ceiling or floor effects.
5. Administrative-code definitions, survey universes, changing variable definitions, and comparability across years or geographies.
6. Whether a statistically significant change is distinguishable from a meaningful change when the manuscript makes that claim.

Use COSMIN concepts only for suitable measurement-property questions. Never reduce validity to Cronbach's alpha, treat a cited validation in another population as universal, or infer construct validity from database metadata.

### 4. Causal-claim audit

Activate when the title, abstract, results, or discussion uses causal language or recommends an intervention based on an observational contrast. Extract the target causal claim before examining the model.

The reviewer should state the units, treatment or exposure, comparator, outcome, time horizon, assignment mechanism, target population, and implied estimand. Then inspect temporal ordering, selection, confounding, measurement, interference, positivity or overlap, missingness, post-treatment adjustment, clustering, and specification choices. For natural experiments, inspect the design-specific identifying assumptions and diagnostics actually reported.

A small local DAG representation may be used to expose assumptions, but the agent must not invent a graph and present it as author intent. The tool should flag adjustment for plausible mediators or colliders as a question to resolve, not an automatic error. It should distinguish association, prediction, mediation, and causal effects. It should not calculate propensity scores, fit new models, or demand a full reanalysis during routine review.

### 5. Qualitative and mixed-method integrity

Activate from the design, not from the presence of quotations. For qualitative work, inspect the fit among the research question, methodological orientation, sampling, recruitment, setting, researcher position, data generation, recording and transcription, coding, analytic development, deviant cases, stopping rationale, and evidence supporting interpretations.

Avoid universal rules such as requiring member checking, inter-rater reliability, or saturation for every qualitative tradition. Evaluate whether the authors' own methodological claims are coherent and sufficiently evidenced. Protect participant privacy by using manuscript excerpts only. Do not upload transcripts or attempt recoding.

For mixed methods, separately map the qualitative and quantitative samples, timing, priority, analysis, and limitations. Then identify where integration occurs, such as design, sampling, analysis, joint display, or interpretation. Ask whether the integrated inference follows from both strands and whether discordant findings are examined. Merely placing two methods in one paper is not demonstrated integration.

### 6. Public metadata verification

Activate only for a consequential numerical or definitional claim tied to a named public series. Resolve the provider, dataset, series or variable ID, universe, geography, unit, frequency, adjustment, time period, release date, and historical vintage. Prefer the originating agency over an aggregator. Return a small evidence card, not a replacement analysis.

This skill can identify a wrong denominator, geography, vintage, unit, survey universe, seasonal adjustment, or revised value. It cannot establish the manuscript's causal explanation, reconstruct restricted microdata, or validate a derived estimate without its complete transformation chain.

## Practical build packages

### Package H1: registry resolver and comparison core

Implement ClinicalTrials.gov v2, OSF public registrations, and AEA RCT Registry downloads behind a common `RegistrationRecord`. Add WHO ICTRP as a manual or cached-download fallback for non-US registries. Store registry ID, canonical URL, provider, retrieved time, record version, registration and study dates, arms, eligibility, sample plans, outcomes, analysis-plan links, amendments, and raw-response hash.

Add deterministic normalization for dates, sample counts, arm names, outcome components, and time points. Keep original text beside every normalized value. Generate a comparison matrix against manuscript claims and a short list of unresolved consequential differences.

Offline fixtures should cover prospective and retrospective records, changed primary outcomes, wording-only changes, added time points, changed sample size with an explanation, duplicate ICTRP records, inaccessible protocols, embargoed OSF content, and ambiguous title matches.

### Package H2: design router and reporting evidence

Implement design classification with quoted support and confidence. Store guideline metadata as versioned local question maps containing item IDs, short original summaries, applicability rules, source URLs, and reuse status. Do not embed full copyrighted checklist text by default.

Test misclassification boundaries, including cohort versus repeated cross-section, randomized encouragement versus ordinary RCT, prediction versus causal modeling, quality improvement versus observational research, and qualitative description versus mixed methods.

### Package H3: construct and measurement map

Add a structured `MeasureRecord` and manuscript search for instrument names, scoring, timing, thresholds, missingness, reliability, validity, and invariance. Permit a targeted DOI or literature lookup for the exact instrument version and population through the existing bounded literature path. Add optional COSMIN-linked prompts without reproducing the tool.

Test changed instrument versions, translated scales, reverse scoring, composite outcomes, proxy outcomes, administrative definitions, and validation evidence from a mismatched population.

### Package H4: causal-claim discipline

Add a causal-language detector followed by human-readable claim extraction. Implement design-specific assumption cards and an optional local DAG text format. No external service is needed. The output should recommend calibrated language when assumptions are unsupported and preserve counterevidence when authors report suitable diagnostics or sensitivity analyses.

Test adjusted association presented causally, post-treatment control, immortal-time risk, time-varying exposure, difference-in-differences without trend evidence, regression discontinuity without continuity checks, instrumental variables without a defensible instrument discussion, and a valid randomized estimate that should not be weakened merely because masking was impossible.

### Package H5: qualitative and mixed-method audit

Implement a methodology router and evidence map informed by JARS-Qual, JARS-Mixed, and COREQ where applicable. It should request exact manuscript passages for sampling, researcher perspective, data generation, analysis, interpretive evidence, and integration. No external API is required.

Test several traditions so the skill does not impose one paradigm's quality criteria on another. Include interview studies, focus groups, ethnography, reflexive thematic analysis, framework analysis, qualitative evidence synthesis, convergent mixed methods, and explanatory sequential work.

### Package H6: public series verifier

Start with US Census and World Bank because both have public discovery and retrieval paths without a paid account. Add FRED or ALFRED only when a user-supplied key and accepted terms are available. Capture series metadata, observation, vintage, source, query, response hash, and all relevant qualifiers.

Test geography and year mismatches, ACS one-year versus five-year estimates, margin-of-error omission, constant versus current currency, revised macroeconomic values, seasonal adjustment, and a claim that cannot be resolved from aggregate metadata.

## Shared evidence and tool contract

Every external result should use the common evidence card and add domain fields where relevant:

```text
evidence_id
manuscript_claim_id
source_provider
source_record_id
canonical_url
query_or_lookup
retrieved_at
record_version_or_vintage
source_timestamp
exact_source_field_or_excerpt
normalized_value
comparison_status
interpretation
limitations
raw_response_hash
```

Protocol and registration comparisons also need an `as_of` date and a clear distinction among first registered, pre-enrollment, pre-analysis, current, and unknown states. Public-series evidence needs dataset, variable or series, universe, geography, unit, frequency, adjustment, observation period, and release vintage. Checklist evidence needs guideline name, version, item ID, applicability rationale, manuscript location, and whether the result is only a reporting gap.

Default limits should remain small: at most two registry candidates, one confirmed record family, two historical states, two linked protocol documents, and three public-series queries per paper. A paper with no relevant trigger should make no domain request. Cache public responses. Send identifiers and narrow search terms rather than manuscript text. Never send participant data, transcripts, unpublished datasets, or protected health information.

These are selection caps within the central plan's shared request allowance, not additive network budgets. Reserve the required history and document requests before a comparison. If they cannot fit, report the unresolved comparison or use an explicitly larger run configuration.

## Evaluation and release gates

Evaluate each package independently before combining them. Use public or synthetic fixtures with known answers, then a blinded paired review on suitable manuscripts. The baseline must receive the same manuscript and general literature access. Count retrieval success separately from a correct review decision.

Required measures are identifier precision, field-extraction accuracy, comparison accuracy, historically correct version selection, false positive rate for consequential discrepancies, supported-finding retention through debate, source fidelity, added requests and tokens, and reviewer usefulness. For reporting and qualitative packages, also measure inappropriate checklist application. For causal review, measure both overclaim detection and erroneous weakening of justified causal claims.

Release gates:

1. Exact-ID paths never substitute a different record.
2. Fuzzy matches require explicit uncertainty and cannot generate a discrepancy finding until resolved.
3. Every comparison is traceable to manuscript text and a versioned external field.
4. The system separates absent reporting, absent registration, disagreement, and unavailable evidence.
5. Current records are never represented as historical records without version evidence.
6. Reporting-guideline output does not become a numeric quality score.
7. The reviewer does not give clinical advice, infer misconduct, or expose participant-level information.
8. The tool does not run heavy reanalysis or depend on a paid service.

## Recommended order

Build H1 first with ClinicalTrials.gov and OSF, then add AEA and the ICTRP fallback. Build H2 and H3 next because they improve review structure without requiring broad external access. Add H4 and H5 after the evidence-handoff behavior is stable, since both depend on nuanced reviewer judgment. Add H6 last and only for named, consequential series claims.

The initial end-to-end experiment should use one prospectively registered trial and one preregistered psychology or social-science study with public version history. The test should ask whether the added package finds a real, consequential protocol-report difference while avoiding a false finding from harmless wording or a documented amendment.
