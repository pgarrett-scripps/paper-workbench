# Biology domain review plan

Planned on 2026-09-25. This document extends the shared evidence-card design in `pra-domain-tools-assessment.md`. It proposes domain skills and bounded data lookups for biological peer review. It does not recommend bulk installation, raw-data reanalysis, sequence searches across whole databases, structure prediction, or new model calls.

## Recommendation

Build three reusable adapters first: biological identity, public study accession, and database evidence record. Put domain reasoning in small skills that invoke those adapters only after a reviewer states a manuscript claim and the unresolved question. Add the RCSB MCP as the first specialized connector after evaluation. Use ordinary REST clients for the other initial sources. A dedicated MCP adds little value when a source has a stable, narrow API and the review needs only one record.

Build molecular and cell biology, proteomics and post-translational modifications, structural biology, genetics or genomics, microbiology, neuroscience, physiology, and plant biology as parallel packages against shared interfaces. Their specialized resources should activate only for a paper in that domain. The [central expansion plan](pra-domain-expansion-plan.md) controls integration and evaluation. Verified access in this document means provider-documented access unless a live smoke test is explicitly cited.

Every result must use the common evidence card and add domain fields when relevant: taxon, strain or cultivar, assembly, accession with version, gene or protein identifier, transcript or isoform, construct, coordinate system, sample or study accession, evidence code, database release, retrieval date, and whether the record is curated, submitted, computed, or predicted. Current database content must not be presented as evidence that was available at a historical review cutoff.

## Shared skills and adapters

### Biological identity and coordinate skill

Concrete tasks:

- Resolve organism, strain, cultivar, assembly, gene symbol, transcript, protein accession, isoform, construct, and residue or variant coordinate before evaluating a claim.
- Translate identifiers only when the source mapping is explicit. Preserve the input identifier and every intermediate mapping.
- Detect common mismatches such as human versus mouse orthologs, canonical versus experimental isoforms, mature versus precursor protein numbering, and GRCh37 versus GRCh38 coordinates.

Use a filtered UniProt REST response for protein identity and evidence, NCBI Datasets for gene, genome, taxonomy, and accession metadata, and Ensembl REST for archive, overlap, sequence, homology, variation, and variant recoding. NCBI recommends its Datasets command line client for complex requests because it supplies validation and retry handling. A key is optional and supports higher NCBI request rates. Ensembl exposes its release through the API and provides a separate GRCh37 server. [NCBI Datasets API](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/), [NCBI Gene data model](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/data-processing/gene-processing/gene/), [NCBI API keys](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/api-keys/), [Ensembl REST endpoints](https://rest.ensembl.org/documentation/)

Implementation: verified public REST or local command line methods. No MCP is needed initially. Cache only selected JSON fields and the raw response. Never infer biological equivalence from identifier mapping alone.

### Public study accession skill

Concrete tasks:

- Verify that a claimed deposition exists, is public when the manuscript says it is public, and matches the stated organism, assay, sample count, and file types.
- Distinguish project metadata, processed results, and raw files.
- Report reviewer-only credentials or embargoed records as inaccessible rather than absent.

Start with record metadata from PRIDE for proteomics and NCBI or EMBL-EBI archive landing records for genomic and expression studies. Do not download spectra, FASTQ files, expression matrices, or genome collections during routine review. PRIDE has a documented public REST API for projects, files, and run metadata. ProteomeXchange submissions can remain private during review and may require credentials from the authors. [PRIDE Archive API](https://www.ebi.ac.uk/pride/ws/archive/v2/docs/api-guide.html), [ProteomeXchange submission guidance](https://www.proteomexchange.org/docs/guidelines_px.pdf)

Implementation: verified REST and metadata-page access. Add archive-specific adapters only when recurring review traffic justifies them.

### Database evidence record skill

Concrete tasks:

- Retrieve a specific annotation, classification, interaction, modification, phenotype, expression result, or model record.
- Expose provenance, evidence type, supporting citation, version, and conflicts rather than only the database summary.
- State exactly what the record can support and what remains a manuscript-level inference.

Implementation: a shared HTTP adapter with source schemas. Do not create a universal biology search MCP. It would hide source-specific evidence semantics and encourage broad, low-value retrieval.

## Domain modules

### Molecular and cell biology

High-value review questions:

- Does the named gene or protein, organism, compartment, pathway, and perturbation match the cited biological entity?
- Is a function annotation supported by experiment, author statement, phylogenetic inference, or computation?
- Does a pathway record document the asserted reaction or only place the entity somewhere in a larger process?
- Is a claimed expression pattern measured in the relevant tissue, cell type, condition, and assay?

Initial sources: UniProt for protein identity and annotation evidence, Gene Ontology annotations for evidence-coded function, Reactome for curated pathway events, and Expression Atlas for curated study-level expression context. Use GO annotations only with evidence codes and references. Treat ontology ancestry as classification, not experimental proof. Reactome pathways are models assembled from cited evidence, not direct measurements in every cell type. Expression Atlas reanalyzes public datasets with standardized pipelines, which may differ from the manuscript analysis. Its downloadable outputs are available by experiment and its copyrightable site material is CC BY 4.0. [Gene Ontology evidence guide](https://geneontology.org/docs/guide-go-evidence-codes/), [Reactome Content Service](https://reactome.org/dev/content-service), [Expression Atlas overview](https://www.ebi.ac.uk/gxa/about.html), [Expression Atlas downloads](https://www.ebi.ac.uk/gxa/download), [Expression Atlas licence](https://www.ebi.ac.uk/gxa/licence.html)

Add interaction-evidence review using STRING and IntAct through the shared adapter layer. Preserve species, identifiers, experimental method, source publication, and whether the result is an association, co-complex observation, or direct interaction. STRING functional association does not establish direct binding or causal regulation. Multiple databases citing the same experiment are not independent confirmations. See [STRING evidence scores](https://string-db.org/help/scores/) and [IntAct data access](https://www.ebi.ac.uk/training/online/courses/intact-quick-tour/getting-data-from-intact/).

Implementation: proposed methods skill over verified public APIs or downloads. Prefer source records and short field selections. Do not run enrichment analysis as part of routine peer review.

### Proteomics and post-translational modifications

High-value review questions:

- Does the PXD accession exist, and do its metadata and files match the declared instrument, organism, quantification design, and analysis type?
- Is a peptide compatible with the stated protein, isoform policy, enzyme, and residue numbering?
- Is a modification name or mass shift consistent with UniMod specificity?
- Does the evidence establish peptide identification, modification localization, protein inference, abundance change, or only one of these?

Use PRIDE and ProteomeXchange for deposition metadata, UniProt or the EBI Proteins API for sequence and peptide mapping, and a pinned UniMod release for modification definitions. PhosphoSitePlus remains optional because downloadable data require a requested data-use license. It must not be redistributed or made an initial dependency. [Proteins API](https://www.ebi.ac.uk/proteins/api/doc/), [UniMod XML](https://www.unimod.org/xml/unimod.xml), [PhosphoSitePlus downloads](https://www.phosphosite.org/staticDownloads.action)

Interpretation contract: mass compatibility is not localization. A localized site is not evidence of biological regulation. Missing public files are not proof that data were never deposited. Protein inference cannot be resolved by checking one canonical sequence. The routine skill may inspect metadata, reported thresholds, peptide sequences, and modification definitions. It must not rerun database searching, false-discovery estimation, quantification, or spectrum interpretation.

Implementation: verified REST and small cached dictionary methods. Candidate instructions exist in [Google DeepMind Science Skills](https://github.com/google-deepmind/science-skills) and [K-Dense scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills). Adapt their lookup patterns to PRA provenance and limits instead of installing either collection wholesale.

### Structural biology

High-value review questions:

- Is the structure experimental or computed, and what method, resolution or uncertainty information applies?
- Does the deposited construct contain the claimed chain, mutation, ligand, interface, and residue?
- Is the relevant residue present in sequence, modeled in coordinates, and locally supported by validation?
- Is the stated assembly biological, author-assigned, software-assigned, or only a crystal contact?

Use RCSB PDB Data, Search, Sequence Coordinates, ModelServer, and validation fields. Retrieve coordinate subsets only when metadata and sequence mapping cannot answer the question. RCSB APIs include experimental entries and computed structure models, so every query must filter or label content type. The APIs are public and rate limited. AlphaFold DB predictions are CC BY 4.0, but prediction confidence does not establish a conformation, interaction, ligand pose, or cellular mechanism. [RCSB API overview](https://www.rcsb.org/docs/programmatic-access/web-apis-overview), [wwPDB validation through RCSB](https://www.rcsb.org/news/feature/67edb6c196cbbd16fc52edb0), [AlphaFold DB](https://alphafold.ebi.ac.uk/)

Implementation: evaluate the official [RCSB MCP](https://github.com/rcsb/rcsb-mcp) first. This is the strongest MCP candidate because structural discovery, sequence mapping, and focused inspection form a coherent tool family. Wrap it with a PRA skill that enforces construct mapping, experimental-versus-predicted labeling, and validation limits. Do not add folding, docking, molecular dynamics, or image-based structural judgment to the initial module.

### Genetics and genomics

High-value review questions:

- Is the variant represented on the stated assembly, transcript, strand, and allele, and is the reported consequence transcript specific?
- Does a public classification concern the same variant-condition pair, inheritance context, and date?
- Does a claimed gene, ortholog, locus, or genome assembly resolve to the stated organism and version?
- Does a repository accession support the declared sample design and data availability statement?

Use NCBI Datasets and Ensembl REST for identity, assembly, transcript, orthology, and consequence context. Use ClinVar only for human variant-condition assertions. ClinVar is a submission archive, does not independently verify all submitted classifications, exposes conflicts and review status, and updates weekly. Preserve SCV, RCV, or VCV accession and version, condition, submitter, review status, date, assembly, and supporting citations. [ClinVar introduction](https://www.ncbi.nlm.nih.gov/clinvar/intro/), [ClinVar access methods](https://www.ncbi.nlm.nih.gov/clinvar/docs/access/), [ClinVar use policy](https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/)

Interpretation contract: a predicted consequence is not a demonstrated molecular effect. Population frequency is cohort and ancestry dependent. A ClinVar label is not a patient-specific diagnosis and conflicting submissions must remain visible. Orthology does not establish conserved phenotype. Routine review should validate identifiers and reported database interpretations, not call variants, rerun association tests, or calculate polygenic scores.

Implementation: verified public REST or E-utilities methods. No initial MCP. gnomAD and other population resources are useful later, after their current API stability, attribution, and terms are verified for the intended deployment.

### Microbiology

High-value review questions:

- Does the strain, isolate, taxon, assembly, BioSample, and BioProject identity agree across the manuscript and deposition?
- Are claimed antimicrobial resistance or virulence determinants reported by a documented pipeline, and are they genes, alleles, or phenotype measurements?
- Does a reported pathogen cluster have the cited version and membership?
- Are contamination, completeness, assembly fragmentation, reference choice, and sampling source acknowledged?

Use NCBI Datasets for taxonomy and assembly metadata. Add NCBI Pathogen Detection only for supported bacterial and fungal pathogens. Its results update as often as daily, cluster accessions are versioned, and cluster membership can change. NCBI explicitly states that SNP thresholds alone do not determine an outbreak and epidemiological evidence is required. BV-BRC has a public REST data API and is a proposed later source for bacterial and viral records, subject to endpoint and field-level validation before production use. [NCBI Pathogen Detection help](https://www.ncbi.nlm.nih.gov/pathogens/pathogens_help/), [Pathogen Detection pipeline](https://www.ncbi.nlm.nih.gov/pathogens/docs/data_processing/), [Pathogen Detection FAQ](https://www.ncbi.nlm.nih.gov/pathogens/faq/), [BV-BRC API architecture](https://www.bv-brc.org/docs/system_documentation/system_architecture.html)

Interpretation contract: genotype does not prove phenotypic resistance. Cluster membership does not prove transmission or outbreak membership. Absence from a database may reflect scope, pipeline thresholds, or update timing. Do not run assembly, taxonomic classification, phylogenetics, metagenomics, or AMR calling in the initial skill.

Implementation: NCBI access is verified. BV-BRC is proposed and requires a smoke test plus terms review. Use REST, not an MCP.

### Neuroscience

High-value review questions:

- Does a cited atlas record match species, age, sex, brain region, coordinate space, assay, and cell-type taxonomy?
- Is a neuronal morphology record from the claimed species, region, cell class, and experimental preparation?
- Are cross-species or cross-atlas anatomical mappings explicit rather than assumed?

Start with NeuroMorpho.Org for published neuronal reconstructions. Its REST API exposes neuron metadata, morphometry, and literature. The service asks clients to limit requests, use delays for larger queries, identify their user agent, use direct file links rather than scraping pages, and cite both the original work and the repository. Data are CC BY 4.0. [NeuroMorpho API](https://www.neuromorpho.org/api.jsp), [NeuroMorpho terms](https://www.neuromorpho.org/useterm.jsp)

Allen Brain Atlas and EBRAINS are proposed second-stage resources. Their present APIs, dataset-specific terms, coordinate-space metadata, and authentication requirements must be verified before adapter work. Do not treat an atlas average as evidence for the manuscript cohort. Do not compare expression values across platforms without confirming normalization and sampling context.

Implementation: a narrow NeuroMorpho REST adapter is feasible. Atlas access should remain manual or literature-led until one recurring review question justifies a connector. No initial MCP and no image registration, spike sorting, connectome analysis, or raw electrophysiology reanalysis.

### Physiology

High-value review questions:

- Does a cited mathematical model exist in the stated version, and do its variables, units, initial values, equations, and parameter values match the manuscript description?
- Is a reported physiological range tied to the same species, preparation, temperature, state, and measurement method?
- Can the manuscript distinguish a model assumption from an experimentally constrained quantity?

Use the Physiome Model Repository and CellML for model identity and source inspection. CellML is an XML standard for model structure, equations, units, and metadata. The repository provides version history and permanent model URLs. The format and documentation can be freely used, but copyright and license for each deposited model remain model specific and must be checked. libCellML is the maintained C++ and Python implementation. [CellML models](https://www.cellml.org/model/index), [CellML API guidance](https://www.cellml.org/tools/api), [CellML FAQ and repository limits](https://www.cellml.org/getting-started/faq), [CellML terms](https://www.cellml.org/about/terms)

Implementation: proposed local methods skill using XML parsing and libCellML validation after dependency review. Initial scope is static consistency checks only. Do not simulate a model, fit parameters, or reproduce figures unless a separate reanalysis task is authorized. A repository model can confirm implementation details, but it cannot validate the physiological assumptions or manuscript conclusions.

### Plant biology

High-value review questions:

- Does the gene identifier, cultivar or accession, genome assembly, and annotation release match the experiment?
- Is an ortholog or gene-family claim supported across the relevant plant genomes?
- Does a reported tissue or condition expression pattern come from a comparable developmental stage, organ ontology, genotype, and treatment?
- Is a phenotype annotation direct, curated, computational, or transferred from another species?

Use Ensembl Plants through the Ensembl REST service for genome, gene, homology, and variation context. Use Expression Atlas for curated plant expression experiments and their downloadable per-study outputs. For Arabidopsis, TAIR is authoritative but mixed-access. Public Data Releases are CC BY 4.0, while current subscriber releases and some services require an account and paid subscription. PRA must not assume subscription access or redistribute subscriber data. [Ensembl REST](https://rest.ensembl.org/documentation/), [Expression Atlas plant experiments](https://www.ebi.ac.uk/gxa/plant/experiments), [TAIR terms](https://phoenixbioinformatics.atlassian.net/wiki/spaces/COM/pages/42216430/TAIR+Terms+of+Use)

Interpretation contract: gene identifiers and annotations are release specific. Cultivar, ecotype, ploidy, and subgenome matter. Homology is not functional equivalence. Expression in a curated atlas does not establish the same response under a manuscript's growth conditions. Avoid generalizing Arabidopsis evidence to crops without an explicit orthology and context argument.

Implementation: verified public Ensembl and Expression Atlas access. TAIR public data are conditionally usable under their stated license. Current subscriber content is optional and user-provided only. Use REST or bounded downloads, not an MCP.

## Candidate source material to adapt

The verified candidates are Google DeepMind Science Skills for UniProt, PDB, STRING, and literature access, K-Dense scientific-agent-skills for broader database workflows, and RCSB's own MCP for structural tools. Treat all three as implementation references. Review their licenses and pin a revision before reusing text or code. Their reasoning contracts are not a substitute for PRA's evidence card, cutoff handling, source exclusions, and request budgets.

Proposed internal skills:

1. `biology-identity`: UniProt, NCBI Datasets, and Ensembl identity and coordinate resolution.
2. `biology-deposition`: accession status and study metadata across PRIDE first, then genomic and expression archives.
3. `biology-annotation-evidence`: evidence-coded GO, pathway, expression, and source-record inspection.
4. `proteomics-ptm-review`: PRIDE, peptide mapping, UniMod, localization language, and protein inference cautions.
5. `structure-review`: RCSB MCP with construct, assembly, coordinate coverage, and validation rules.
6. `genomic-variant-review`: assembly and transcript normalization plus ClinVar assertion provenance.
7. `microbiology-record-review`: strain, assembly, AMR record, and versioned cluster context.
8. `neuroscience-atlas-review`: morphology first, atlas metadata later.
9. `physiology-model-review`: CellML identity, equations, units, provenance, and static validation.
10. `plant-record-review`: plant gene release, cultivar, homology, and expression context.

Only one or two domain skills should be loaded for a paper. Shared identity resolution should be callable underneath them without exposing a second set of overlapping instructions.

## Implementation sequence and acceptance tests

Freeze the three shared adapter contracts first. Build `biology-identity`, `biology-deposition`, and specialist skills concurrently against those contracts. Integrate each package when its source and fixture checks pass. Evaluate additional MCP transports only when a repeated access pattern justifies them. No package should begin with bulk database downloads.

Each adapter needs cached fixtures for correct resolution, ambiguous symbol, wrong taxon, retired accession, version mismatch, missing record, unavailable private record, rate limit, and malformed response. Domain fixtures should include canonical versus experimental isoform, mature-protein numbering, compatible mass with unsupported localization, PDB sequence present but coordinates absent, computed versus experimental structure, conflicting ClinVar submissions, changing pathogen cluster versions, NeuroMorpho preparation mismatch, CellML unit mismatch, and plant cultivar or assembly mismatch.

Acceptance requires that the tool returns a bounded evidence card, records the exact query and version, exposes conflicts and limitations, makes no conclusion beyond the source evidence, and performs zero requests when no manuscript claim warrants a lookup. Evaluate each skill on whether it changes a review judgment correctly, not on retrieval success alone.
