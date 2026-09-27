# Domain review development release

Built on 2026-09-25 from the [domain expansion plan](pra-domain-expansion-plan.md). This document distinguishes working software from scientific validation.

## Implemented

- A project-owned catalog of 21 domain packages with original reviewer skills, source notes, maturity labels, and 84 scientific evaluation cases. Mathematics, computing, and humanities explicitly have limited methods coverage.
- Manuscript-grounded selection of up to two domain packages by default. Matching passages are saved with the profile. The router accepts both current imported manuscripts and legacy section layouts, excludes reference sections, and falls back to shared guidance when no supported trigger matches.
- One bounded source tool exposing 18 adapter types. These retrieve selected record fields, not entire scientific databases or author datasets.
- A shared six-request allowance, two source investigation locations, content-verified caching, typed unavailable states, stable source IDs, and historical-version exclusions.
- Exact external evidence references in findings and debate decisions. Source cards include identifiers, manuscript locations, selected fields, date or version when available, raw-response hashes, and interpretation limits.
- Additive debate history. Earlier hypotheses and findings survive normalization and later rounds. New findings and hypotheses receive stable IDs. Current selected wording and prior author defenses stay available without recursively copying whole review histories.
- External evidence attached to findings, displayed in the review interface, retained in revision packages, and included in exported Word comments.
- Domain-neutral shared prompts and design-sensitive investigation questions. Domain selection does not add a model call.
- A comparison runner with independent condition budgets, a common frozen source packet, shared initial figure pages, anonymous condition labels, source-checked judge ratings, immutable generation artifacts, and a 16-call panel ceiling.

The single-reviewer condition receives six tool calls. PRA receives four investigator calls and two debate calls. Both receive the same domain skills, tools, initial source images, manuscript text, and frozen source availability. PRA still uses two generation model calls versus one for the baseline. This is not an equal-compute comparison.

## Active source adapters

| Family | Active types | Scope |
| --- | --- | --- |
| Literature and references | Crossref, DataCite, Europe PMC | DOI metadata and exact PMID abstracts. Existing bounded Europe PMC search remains available in live mode. Metadata is not claim verification. |
| Molecular biology | UniProt, STRING identity, STRING interactions, Ensembl, Reactome | Protein identity and selected annotations, taxon-specific identity, one exact association pair, gene or transcript metadata, pathway or reaction context |
| Structures and proteomics | RCSB PDB, PRIDE | Entry and deposition metadata. Coordinate analysis, peptide mapping, spectra, and file-level audits are not implemented. |
| Chemistry | PubChem, ChEMBL | Exact CID properties and exact assay metadata. No general chemical-name resolution or activity search. |
| Health and registration | ClinicalTrials.gov, OSF | Current trial records and public registration fields. Historical protocol comparison is unavailable without a separately established historical source. |
| Ecology and environment | GBIF taxonomy, GBIF occurrence, NASA CMR | Exact taxon, occurrence, or collection metadata. No occurrence search, population reconstruction, or granule download. |
| Social and economic metadata | World Bank | Exact indicator definitions. Country-year values and causal inference are not supplied by the adapter. |

Other resources in the domain catalog remain documented candidates. They do not silently fall back to browser access, paid services, or fabricated tools. Examples include IntAct, UniMod, ClinVar, NeuroMorpho, CellML, NOAA, Materials Project, and astronomy catalog adapters. The RCSB implementation currently uses its public API, not an installed MCP server.

The [machine-readable capability inventory](../runs/pra-domains-v1/capabilities.json) identifies active adapters and records the public smoke checks. A successful endpoint check establishes access and parsing for that example, not review quality or complete provider coverage.

## Verification before paper reviews

The full local suite passed 171 tests before the paper trial. Focused checks cover wrong record identity, current data misused historically, cache tampering, stable IDs, frozen source packets, separate condition budgets, source-target limits, malformed evidence, exact source quotes, section-layout compatibility, and additive debate history. All 21 skills passed the skill validator. JavaScript syntax and Python compilation passed.

Thirteen adapter types returned usable records in live public checks, including the repaired compact ClinicalTrials.gov record. The other active types have local parser tests or implementation checks, but no successful live record check is claimed here. Scientific case fixtures have not been counted as successful model evaluations.

Pretrial inspection found and fixed these issues:

1. Current citation metadata could have been treated as historical evidence. All current records now remain ineligible for historical source support unless a historical pathway is implemented.
2. A cache hit changed the evidence ID. Transport state is now excluded from identity.
3. Large trial records exceeded the model-facing limit. The trial adapter now selects named fields and discloses omitted descriptions and capped outcome lists.
4. The ecology skill described occurrence checks through the taxon adapter. Occurrence now has a separate exact-ID adapter and explicit semantics.
5. Imported section indexes used a different shape than the synthetic routing fixture. Routing now handles the actual imported format and has regression coverage.
6. Initial trigger phrases missed ordinary randomized-trial and nanoparticle manuscripts. Common domain and design phrases were added before any review generation.

## Paper evaluation

| Paper | Blind preference | Valid finding ratings | Development interpretation |
| --- | --- | --- | --- |
| Yeast, reused development case | Single reviewer | 13 of 15 | PRA retained a useful author-defense qualification but missed mechanistic questions identified by the baseline |
| Nanoparticle chemistry, fresh | PRA after debate | 14 of 15 | Similar core findings across methods, with a questionable part of the judge's preference rationale |
| Registered health trial, fresh | PRA after debate | 15 of 15 | Both methods used the registry, and debate restored a concrete reporting correction |
| Plant-pollinator ecology, fresh | Single reviewer | 15 of 15 | Baseline found a numerical figure/table discrepancy absent from PRA discovery |

The panel is split two to two. None of these results establishes superiority. Five of the 21 domain packages were exercised by these manuscripts. The [complete results and costs](../runs/pra-domains-v1/panel-summary.json) link the condition-level outcomes, and each paper has a separate limited coordinator source audit.

The evaluation uses Sol through the verified Codex subscription. No paid API credits or reset were used to launch it. The account usage meter showed 26% used before review calls.

One previously seen yeast paper is the development case. Three freshly selected published manuscripts cover experimental nanoparticle chemistry, a registered randomized health intervention, and a plant-pollinator ecology study. Selection records disclose available and omitted source material. Public peer-review histories were not supplied.

The development judge preferred the single reviewer for its pathway-independence and spatial Rho1-activity questions. The PRA debate accounted for all 25 tracked components across nine issues and correctly kept the protein-abundance rescue qualification in the final PI4P comment. This is an improvement in evidence retention, not a preference win.

Two judge ratings for the sequential LatA/MBC concern cited an exact manuscript quotation under the wrong block ID. The quotation is in `b0076`, not the supplied `b0032`. Those ratings remain unscored in the automated results. Manual location checking is recorded separately and does not rewrite the judge output or turn the model's scientific judgments into ground truth.

The chemistry judge preferred the post-debate review, citing technically careful wording and proportionate remedies. It rated all five final findings as supported concerns with valid source references. One single-reviewer rating had an invalid source reference and remains unscored. Its preference rationale is less secure than the tally suggests. The judge used a reference title about an inverse co-ion rule to criticize the baseline's counterion discussion, while the manuscript itself invokes oppositely charged ions. A reference title alone cannot settle that physical interpretation. The central salt-comparison concern remains shared by all three reviews.

The health judge preferred the post-debate review, and all 15 finding ratings passed source checks. Both the baseline and PRA successfully used the frozen trial registry with exact external quotations. The health debate restored two previously discarded hypotheses. Its final review included a baseline reporting correction: 46 of 75 is about 61.3%, while 22.3% uses the full denominator of 206. The prose and table also report different arm counts. This was a minor reporting finding, not a demonstration of a major quality advantage. The final review correctly avoided alleging randomization failure or outcome switching. The baseline separately emphasized registration chronology, which remains an editorial prioritization difference.

All four PRA outputs passed the issue and sentence-component accounting gate. Development, chemistry, health, and ecology tracked 25, 33, 27, and 30 components respectively. Debate restored zero, two, two, and three previously discarded hypotheses, sometimes by retaining only a narrower concern. These are accounting outcomes, not proof that every scientific detail survived or that each restored question was useful.

The ecology judge preferred the single reviewer, with all 15 ratings passing reference checks. Its strongest distinguishing finding was visible in the supplied figure page: Figure 3 reports a slope of 0.473 and R squared of 0.39, while the table labeled SLR reports a slope of 1.1841 and adjusted R squared of 0.48. The figure caption also labels Table 2g as SLR although Table 2 describes multiple regression. Different fitted models need not have matching slopes. The labeled SLR values and caption nevertheless warrant reconciliation. This numerical question was absent from PRA's initial findings and recorded hypotheses. It was a discovery miss, not a question deleted by debate.

The ecology investigator also supplied a malformed quotation ending in `at the_re.` in its replication coverage record. That area correctly remains unresolved despite a second valid quote. This is separate from the final finding-accounting gate. Original outputs and flags remain unchanged.

The original 900,000 observed-token launch stop underestimated repeated context input during tool use. After 11 calls had started and 711,852 completed tokens were recorded, the coordinator raised that operational stop to 1,300,000 to complete the already approved four-paper panel. The ceiling remains 16 calls. The account meter had moved from 26% to 28%, with no paid credits. The [execution amendment](../runs/pra-domains-v1/execution-budget-amendment.json) preserves the original freezes and records that no review prompts, skills, source packets, models, tool allowances, or judge criteria changed. This is a launch stop, so a final in-flight call can exceed it.

The runner stores raw outputs and gate failures rather than repairing them silently. A failed gate remains a failure. Model preference and source validity are separate outcomes, and a four-paper panel cannot establish broad superiority or replace independent domain assessment.

The completed panel used exactly 16 Sol calls and 1,006,434 reported input-plus-output tokens, including repeated context input. All calls have usage receipts. There were no retries, additional judges, paid API credits, or reset redemptions. The account-wide weekly meter moved from 26% before reviews to 28% afterward. That meter includes other account activity and is not an exact task-specific charge.

This panel tests current manuscript review, not retrospective agreement with human reviewers. Published human reviews were not supplied or scored. The frozen packets were deliberately small, and only the health paper elicited external database lookup. This establishes the registry integration but does not establish that 18 adapters improve review quality or that literature discovery works well across domains.

## Post-panel fixes and next priorities

The four priorities below now have an [implementation follow-up](pra-four-priorities-build.md). That work adds infrastructure and offline checks without changing the pilot results or claiming fresh validation.

After all model calls completed, repeated quotations from one source were consolidated into one source card per finding in revision transport, the interface, and Word comments. Every exact excerpt remains available. Regression checks exercise multiple quotations and legacy duplicate cards. No scientific prompts or model outputs were changed, and the pretrial source snapshot remains archived. The final local suite passes 173 tests. JavaScript syntax also passes, and the health manuscript interface displays the registry card beside its anchored review question.

The next quality improvement should target discovery and evidence comparison, not simply increase the number of reviewers or connectors:

1. Build an inspectable figure/table/claim map for the main results, with explicit checks for model identity, outcome, denominator, units, and effect labels. Distinguish expected differences between models from contradictory reporting. Use the ecology discrepancy as a development fixture, not fresh validation.
2. Preserve the additive debate ledger and external-source limits. Do not promote a restored hypothesis to a confirmed defect merely because it survived accounting checks.
3. Expand source access only where a manuscript question requires it. The catalog already records the remaining sources and their access limitations. Priority candidates include identifier resolution, historical registration records, and literature discovery with explicit search coverage.
4. Before a publication claim, freeze the improved workflow and assess fresh papers with independent domain judgments on a small set of consequential findings. Compare against the same tool-equipped single reviewer and report both cost and failures. Keep model preference separate from correctness and human-review overlap.

No larger model trial was launched after this panel.

## Using the development release

The normal review CLI now selects domain guidance and exposes the source tool. It still requires the existing fresh subscription and credit verification file.

```text
python3 -m paper_workspace review MANUSCRIPT_WORKSPACE RUN_DIRECTORY \
  --billing-confirmation BILLING_JSON \
  --literature-cutoff YYYY-MM-DD \
  --mode panel \
  --scaffold-root /path/to/paper-scaffold
```

Use `--evidence-mode historical` to prevent current database records from supporting historical claims. This mode currently returns unavailable historical state for external record support. It is deliberately more limited than ordinary current review. Use `--source-packet PATH` for fixed-source comparisons, which disables live retrieval outside that packet. `--legacy-tools` retains the older tool profile without loading domain packages.

The source catalog is project-owned. No global plugin installation, new paid account, or third-party skill bundle is required. Some planned capabilities need more adapter work or access arrangements before they can be advertised as active.
