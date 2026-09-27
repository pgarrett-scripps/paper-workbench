# Domain tools and skills assessment

Assessed on 2026-09-25. Recommendation: add a small, selectively activated evidence layer. Start with literature and protein identity. Add structure, interaction, modification, and chemical-perturbation tools when a manuscript contains a claim those tools can help assess. No production integration or new review-model call was made during this assessment.

## What already exists

PRA has Crossref DOI metadata lookup and bounded Europe PMC literature search in `paper_workspace/investigation.py`. These are distinct from the imported manuscript's local citation-linkage checks. The local Paper Scaffold `tools/bib_audit.py` queries Crossref and falls back to DataCite on a Crossref 404. It compares registered metadata and checks available correction and withdrawal signals. I did not find a RefSourcer integration in the inspected checkout.

The bounded benchmark runner disables external tools. The production reviewer uses a tool allowlist and small call budgets. Installing an MCP in the desktop app alone will not make it available to those review processes. New capabilities need explicit integration into the PRA server, runtime allowlist, evidence recording, and experiment protocol.

## Recommended resources

| Resource | Recommendation | Review questions it could answer | Interpretation limit |
| --- | --- | --- | --- |
| Crossref, DataCite, Europe PMC | First release, extend existing code | Does the DOI identify the cited work? Is there a correction? What did a specific prior paper actually measure? | Metadata identity does not establish claim support. Abstracts and unavailable full text must be labeled separately. |
| UniProt | First biology release | Is this the intended organism, protein, isoform, sequence, domain, or residue? What evidence supports an annotated function or site? | Curated and computational annotations differ. A canonical sequence may not match the experimental construct. |
| RCSB PDB | Conditional structural skill | Does the cited structure contain the relevant chain, construct, ligand, or modeled residue? Does available validation support the local interpretation? | Distinguish deposited structures from computed models, and sequence presence from resolved coordinates. A structure does not by itself establish a cellular mechanism. |
| STRING with IntAct follow-up | Conditional interaction skill | What evidence lies behind a proposed protein association? Is there an experiment supporting the claimed relationship? | Association, co-complex membership, direct binding, and causal regulation are different claims. |
| UniMod and protein-site annotations | Conditional proteomics skill | Is a modification name, mass shift, residue specificity, or coordinate assignment consistent? | A chemically compatible modification is not proof of site localization, biological occurrence, or functional consequence. |
| PubChem and ChEMBL | Conditional perturbation skill | Is the reagent identity clear? What assays support the proposed target activity or selectivity? | Potency depends on assay conditions. A database activity does not establish selectivity at the manuscript's dose, species, or cellular context. |

UniProt supplies stable sequence identifiers with manual and automatic annotations and associated evidence. The EBI Proteins API also supports mapped proteomics peptides. A useful peptide tool should report mapping against a specified organism, proteome release, and isoform policy. It must not claim global peptide uniqueness from a limited lookup. [UniProt API paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12230682/), [Proteins API documentation](https://www.ebi.ac.uk/proteins/api/doc/).

RCSB provides search, data, and sequence-coordinate APIs. Its organization also maintains `rcsb-mcp`, with tools for structural discovery, inspection, and sequence mapping. Prefer evaluating that implementation before writing a separate PDB connector. Start with metadata and existing validation information, retrieving a coordinate subset only when necessary. Do not make folding, docking, or molecular dynamics part of routine review. [RCSB API overview](https://www.rcsb.org/docs/programmatic-access/web-apis-overview), [RCSB MCP](https://github.com/rcsb/rcsb-mcp).

STRING's default functional network represents functional associations. Even its physical network can describe proteins in the same complex without direct binding. Its evidence can also be transferred across species. A review adapter should expose evidence channels, organism, source publications, and transfer status rather than return only a combined score. IntAct can provide more detailed interaction evidence for follow-up. Neither a missing edge nor a high score decides whether a manuscript claim is correct. [STRING interpretation guide](https://string-db.org/help/scores/), [IntAct data access](https://www.ebi.ac.uk/training/online/courses/intact-quick-tour/getting-data-from-intact/).

The public UniMod XML was accessible in the live check and can support a small cached modification dictionary. Protein-specific PTM occurrence needs separate evidence. PhosphoSitePlus is a potential later resource, but its downloads currently require a requested data-use license. Do not make it a dependency of the initial freely accessible path or assume permission to redistribute it in a shipped product. [UniMod XML](https://www.unimod.org/xml/unimod.xml), [PhosphoSitePlus download terms](https://www.phosphosite.org/staticDownloads.action).

Europe PMC exposes literature and eligible full-text retrieval. Search relevant metadata broadly, then retrieve accessible full text selectively. A paywalled result must remain a relevant but incompletely assessed result. PubChem and ChEMBL provide structured chemical and assay access suitable for a later perturbation module. [Europe PMC service](https://europepmc.org/RestfulWebService), [PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest), [ChEMBL services](https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services).

## Skills to add around those tools

The skill should define when a lookup is warranted, how to match the experimental context, and what the result can justify. An MCP supplies access. It does not supply the reasoning contract.

1. Literature and citation evidence. Resolve reference identity, identify a specific unresolved claim, retrieve the relevant prior methods or results, and record what they support or leave uncertain. Avoid treating citation counts or automated citation sentiment as validity scores.
2. Molecular identity and perturbation. Resolve taxon, accession, isoform, construct, coordinate system, and reagent identity before judging functional or mechanistic claims.
3. Structural and interaction evidence. Distinguish experimental evidence from predicted models, modeled from unresolved residues, biological assemblies from crystallographic contacts, and association from direct binding.
4. Proteomics and PTMs. Check peptide mapping, declared database scope, modification definitions, localization versus identification, and reported uncertainty without rerunning spectra or a full search pipeline.

Each skill returns a compact evidence card attached to an existing manuscript claim or a new source-anchored question. It must include an immutable evidence ID, source URL, query, accession and taxon where relevant, exact source field or passage, retrieval date, database release or record version when available, evidence type, and unresolved limitations. Preserve the raw response and a content hash outside the model context. Debate must receive both the result and its limitations.

## Reuse versus installation

Google DeepMind's public Science Skills repository includes UniProt, PDB, STRING, and literature skills. I inspected its UniProt and Europe PMC instructions, plus two preprint retrieval recipes. These offer useful API patterns, but they should be adapted to PRA's scope and provenance contract. In particular, the inspected Europe PMC skill restricts search to open-access content, which is undesirable as the sole discovery search for a peer review. Respect upstream licenses when reusing code or instructions. [Science Skills](https://github.com/google-deepmind/science-skills).

K-Dense's scientific-agent-skills collection also provides database and literature workflows. Its broader scope includes analysis, modeling, and reproduction tasks. Selectively inspect and reuse relevant lookup components rather than installing the full collection into every review agent. Neither collection's availability establishes an improvement in peer-review quality. [K-Dense collection](https://github.com/K-Dense-AI/scientific-agent-skills).

The plugin catalog returned Scite and Consensus as available, uninstalled literature connectors, but no relevant catalog result for the specific UniProt, PDB, and STRING search. That does not mean external MCP implementations are absent. Scite is a possible later addition for citation context, but the first release can use the existing literature path without a new account dependency. Its citation classifications should remain leads to inspect, not adjudication. [Scite API](https://scite.ai/api).

## Fit with the failures already observed

These resources could reveal identity mismatches, residue-numbering errors, unsupported interaction interpretations, or a relevant prior experiment. They will not resolve most cohort, exclusion, replication, or debate-retention failures merely by being installed. For the recent yeast paper, an interaction lookup might identify prior evidence, but the decisive abundance-restoration control already exists in the manuscript. Correctly carrying that control into the final review remains an internal reasoning task.

External evidence must not introduce circular confirmation. Exclude the manuscript and its preprint family when seeking independent support. For retrospective benchmarks, distinguish evidence available at the review cutoff from later database annotations. A current record with old supporting citations is not automatically a historically valid snapshot. Record uncertainty when an appropriate historical version cannot be recovered. Current correction checks can still be useful to authors, but should be a separate endpoint from retrospective review performance.

## Bounded implementation and evaluation

First implement a common cached evidence-card adapter, the Scaffold bibliography bridge, and UniProt identity lookup. Integrate selected RCSB MCP capabilities only for structural questions. Add other modules when a paper needs them. Load one relevant domain skill at a time and retain the existing investigator and debate stages.

Suggested initial retrieval budget: at most six external requests per paper, at most two unresolved targets, up to three literature hits per search, and up to two selected full texts. A paper with no relevant question uses no external request. These are proposed limits, not measured optima. Return short field selections to the model, enforce timeouts, cache responses, and report unavailable or ambiguous outcomes explicitly. Query public identifiers and the minimum search terms needed rather than uploading entire manuscripts.

Validate the adapters offline with cached examples for wrong species, isoform and residue mapping, compatible versus incompatible modification definitions, predicted versus experimental structures, indirect associations, unavailable records, and conflicting evidence. Then use one suitable paper for a paired test with and without the added tools. Give the single baseline the same tool access and budgets. Judge whether retrieval changes a review decision correctly, whether unsupported claims or excessive requests increase, and what the marginal token cost is. Count successful lookups separately from useful scientific findings.

Other domains can use the same architecture. Chemistry can use PubChem and ChEMBL. Clinical research can compare manuscript statements with trial registry records. Ecology can use taxonomic and occurrence records with geographic and sampling context. These should remain later domain modules, not additions to the current biology prototype by default. [ClinicalTrials.gov API](https://clinicaltrials.gov/data-api/api), [GBIF API documentation](https://techdocs.gbif.org/en/openapi/).

## Live checks and scope

Five read-only checks succeeded: UniProt entry P04637, RCSB entry 4HHB, STRING's identifier resolver for human TP53, Europe PMC metadata for a public PMID, and the UniMod XML dictionary. These checked access and basic response parsing only. They did not validate MCP deployment, peptide search, structural interpretation, interaction evidence retrieval, or production reliability.

The UniProt response was 874,741 bytes for one extensively annotated protein. That is direct evidence for filtering and caching before exposing results to an agent. The UniMod dictionary was about 2.5 MB. No bulk author data or unpublished manuscript was sent. No paid service was connected, no plugin or scientific skill was installed, and no review-model calls were made.

Artifacts are in `runs/pra-domain-tools-assessment`, including `smoke-checks.json`, cached public responses, and the inspected skill definitions. Those definitions were evaluated as source material, not activated as instructions for this task.
