# Domain package contract v1

Implementation contract for the parallel domain builders. Packages live in `paper_workspace/domains/<id>/`. IDs use lowercase words joined with hyphens.

Each package contains `manifest.json`, `skills/<id>/SKILL.md`, and `fixtures/cases.json`. Write original, concise review instructions. Read the local skill-creator skill before authoring. This is a project-owned catalog consumed by PRA, not a global skill installation.

Manifest shape:

```json
{
  "schema_version": 1,
  "id": "molecular-biology",
  "catalog_id": "D01",
  "name": "Molecular and cell biology",
  "description": "Review molecular perturbations and context-specific evidence.",
  "triggers": ["gene expression", "knockdown", "cell line"],
  "skills": ["skills/molecular-biology/SKILL.md"],
  "providers": ["uniprot", "string", "intact"],
  "source_notes": [{"url": "https://www.uniprot.org/", "purpose": "Protein identity", "access": "public", "status": "documented"}],
  "maturity": {"instructions": "implemented", "sources": "documented", "live_access": "not_tested", "manuscript_evaluation": "not_evaluated"},
  "limitations": ["An annotation does not establish the manuscript mechanism."],
  "provenance": {"kind": "original", "date": "2026-09-25", "attribution": "Original PRA instructions informed by linked primary documentation."}
}
```

Use precise trigger phrases, not common words such as study, model, control, or data. The coordinator routes from manuscript narrative only and saves matching block IDs. Do not embed routing claims unsupported by manuscript text.

`providers` lists useful dependencies, including planned providers. The shared registry exposes implemented adapters separately. A listed provider is not a promise of runtime availability. Use exact provider IDs from this vocabulary where applicable: crossref, datacite, europepmc, uniprot, rcsb, string, intact, pride, unimod, ensembl, clinvar, ncbi-datasets, reactome, go, expression-atlas, neuromorpho, cellml, tair, pubchem, chembl, clinicaltrials, osf, aea, census, worldbank, fred, gbif, nasa-cmr, noaa, cod, optimade, materials-project, simbad, vizier, ads. Other providers can be declared as documented or audit-required candidates in source notes.

Each SKILL.md needs valid name and description frontmatter. Its body must tell the reviewer what to investigate, which context or identifier differences matter, what evidence can rebut the concern, and what cannot be inferred. Reference available generic manuscript tools and the proposed `lookup_source` tool only. Call it with provider, identifier, and a manuscript block ID. Describe unavailable resources as optional, never pretend a listed resource is connected. Do not embed whole source manuals or generic instructions repeated by the shared prompt.

Each cases.json is an array of at least four cases with `id`, `kind`, `manuscript_excerpt`, `source_record`, `expected_disposition`, and `rationale`. Cover a supported concern, a benign near-match, an unresolved or ambiguous case, and unavailable evidence. These are scientific evaluation cases for a later blind assessment, not proof that the model follows the skill. Include at least one positive routing phrase in a relevant example.

Builders own only their assigned domain directories. Do not alter the shared runtime, schemas, or another builder's package. No review-model calls, paid dependencies, external uploads, or bulk downloads. No em dashes or semicolons in authored prose.
