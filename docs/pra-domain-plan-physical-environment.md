# Physical science and environment review plan

Prepared on 2026-09-25. This is a build specification, not a claim that these connectors are implemented or that their review quality has been established. Provider documentation was checked during planning. Unless explicitly stated otherwise, endpoints have not been live-tested by PRA.

The central [domain expansion plan](pra-domain-expansion-plan.md) controls scheduling, common budgets, and acceptance. Domain packages can be built in parallel after the shared interfaces are fixed. Review remains focused on manuscript claims, reported methods, and bounded public evidence. Full analysis reproduction and large data downloads remain outside routine scope.

## Chemistry and pharmacology

Build skills for chemical identity, assay interpretation, analytical characterization, and reported reaction consistency. Extract the compound, stereochemistry, salt or mixture, concentration basis, purity claim, assay endpoint, units, conditions, comparator, and supporting manuscript locations.

Use [PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest) for compound records and [ChEMBL web services](https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services) for assay-specific activity context. A name or connectivity match must not silently become a stereochemical identity match. IC50, EC50, Ki, and Kd are different quantities. Activity from another assay does not directly refute a manuscript value.

Use [NIST Chemistry WebBook](https://webbook.nist.gov/chemistry/) for reference physical properties and spectra with phase, temperature, pressure, units, reference, and measurement context. Its [name search documentation](https://webbook.nist.gov/chemistry/name-ser/) cautions that name search is incomplete. Treat this as bounded reference retrieval, not a promised general REST integration.

Local checks can compare stated formula, molecular mass, stoichiometry, concentration, conversion, and yield when the required values are explicit. Preserve rounding and uncertainty. Inspect reported characterization and controls before asking for additional experiments. Do not reconstruct spectra, perform docking, predict synthetic routes, or infer structure from a database name match.

Fixtures: salt versus parent mismatch, stereoisomers, activity measured in a different assay, incompatible concentration units, reference property at a different temperature, correctly reported low yield, and an unresolved compound name.

## Materials and crystallography

Build a sample-to-property evidence map that preserves composition, phase, processing, geometry, measurement conditions, uncertainty, and specimen independence. A calculated value is not an experimental reference value.

The [Crystallography Open Database](https://www.crystallography.net/cod/) provides public-domain small-molecule, inorganic, and mineral structures. Retain the original deposition and publication provenance. [OPTIMADE](https://www.optimade.org/) supplies a common query standard across materials providers. Each provider still controls its content, API deployment, and terms. Implement a provider allowlist with a narrow result limit rather than querying every provider.

[Materials Project](https://docs.materialsproject.org/downloading-data/using-the-api/getting-started) requires an API key. It is an optional connector with explicit configuration, not an anonymous-access dependency. Capture calculation method and assumptions when supplied.

[IUCr checkCIF](https://checkcif.iucr.org/) can validate submitted crystallographic files. Initially read an existing validation report and map its alerts to manuscript responses. Do not automatically upload an unpublished CIF. An alert requires interpretation and can have a satisfactory author explanation. Static inspection of a supplied CIF may check identifiers, units, symmetry metadata, and consistency without rerunning refinement.

Fixtures: polymorph mismatch, experimental versus computed record, wrong composition, temperature mismatch, a justified validation alert, missing uncertainty, and unavailable keyed access.

## Ecology, evolution, biodiversity, and agriculture

Build skills for taxonomic identity, sampling and detection, spatial and temporal dependence, intervention or management claims, and environmental context. Distinguish sampling units, sites, organisms, repeated measurements, and subsamples. Inspect detectability, effort, occupancy or abundance terminology, seasonality, and reference population before interpreting a contrast.

Use [GBIF species services](https://techdocs.gbif.org/en/openapi/v1/species) for names and taxonomic matches. Use [occurrence services](https://techdocs.gbif.org/en/openapi/v1/occurrence) for a small number of relevant records and their dates, coordinates, uncertainty, provenance, and quality flags. A record establishes reported occurrence under its source limitations. No hit does not establish absence, and records do not constitute independent standardized samples.

Plant identity and cultivar checks reuse the biology package. WoRMS, OBIS, environmental archives, and agricultural statistics are discovery candidates requiring provider and terms audits before implementation. Their names in this plan do not establish API readiness.

Fixtures: synonym versus accepted taxon, fuzzy match requiring resolution, introduced versus native range claim, duplicate occurrences, coordinate uncertainty crossing a boundary, seasonal mismatch, pseudoreplication, and a defensible sampling limitation that should not be called a fatal flaw.

## Earth science, climate, and environmental observation

Build skills for dataset lineage, spatial reference, temporal coverage, calibration, baseline definition, missingness, and uncertainty. Trace a reported quantity to collection, product version, variable, aggregation, unit, spatial resolution, time window, and processing level.

[NASA Common Metadata Repository](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html) supports collection and granule metadata discovery. Use metadata to check product identity and coverage. This does not justify downloading satellite rasters or climate cubes, or claiming the derived analysis is correct. Some underlying data access requires authentication even when metadata search is public.

[NOAA Climate Data Online v2](https://www.ncei.noaa.gov/cdo-web/webservices/v2) requires a token and documents request limits. Build it as an optional configured source for station, dataset, variable, and small observation queries. A nearby station is not automatically a substitute for the manuscript station. Current corrected data cannot establish what was available at an earlier review date.

USGS water and earthquake services, PANGAEA, and discipline-specific geochronology resources belong in source discovery. Confirm current endpoints, version semantics, and terms before adding adapters. Do not make a vague general geoscience search tool stand in for those audits.

Fixtures: collection-version mismatch, spatial reference mismatch, nominal versus effective resolution, climatological baseline mismatch, cumulative versus instantaneous measure, flagged observations, unavailable historical version, and a missing NOAA token.

## Physics, engineering, and metrology

Build mainly local reasoning and consistency skills. Review measurement definitions, calibration traceability, uncertainty budgets, repeatability, independent replication, controls, instrumental resolution, saturation, boundary conditions, model assumptions, scaling, and dimensional consistency.

Pin the applicable edition of the [BIPM SI Brochure](https://www.bipm.org/en/publications/si-brochure) and relevant [JCGM metrology guidance](https://www.bipm.org/en/committees/jc/jcgm/publications). Record the edition used. Use these as references for units and uncertainty concepts, not as APIs or an automatic compliance score. Check reproduction rights before embedding standard text. SI Brochure content is published under CC BY 4.0.

Small calculations may verify dimensional consistency, reported ratios, order of magnitude, or explicit uncertainty propagation with stated assumptions. Unreported covariance must not be silently set to zero. Do not run simulations, redesign devices, perform safety certification, or reconstruct an entire analysis. A paper's relevance to a regulated standard does not imply the manuscript establishes compliance.

Fixtures: Celsius versus kelvin in a ratio, standard error versus standard deviation, dependent uncertainty terms, logarithmic units, instrument resolution versus accuracy, rounded quantities that remain consistent, and a missing parameter that prevents a valid calculation.

## Astronomy and space science

Build skills for object identity, coordinates and epoch, catalog version, selection function, observation provenance, calibration, and measurement context.

[SIMBAD](https://simbad.cds.unistra.fr/simbad/sim-fscript) provides object and reference queries. [VizieR TAP](https://tapvizier1.cds.unistra.fr/adql/) provides catalog access. Resolve identifiers and preserve coordinate frame, epoch, units, uncertainties, and originating catalog. Cross-matching requires a justified tolerance. A catalog label or non-detection is not a final physical classification.

[NASA ADS API documentation](https://ui.adsabs.harvard.edu/help/api/api-docs.html) provides astronomy literature access with token-based configuration. It is optional. Shared literature search remains available without it. Avoid downloading surveys, reducing telescope data, or treating multiple catalogs that reuse the same observation as independent evidence.

Fixtures: alias resolution, proper-motion or epoch mismatch, angular-unit mismatch, reused observation, catalog selection effects, upper limit versus detection, and ambiguous nearby objects.

## Common acceptance

Every module must include a supported concern, a benign near-match that should not be flagged, an unresolved case, and a source failure. Add scientific boundary cases listed above. A source card must preserve query, exact fields, units and context, version or unknown-version status, retrieval time, supporting publication, and a content hash.

Judge retrieval and scientific interpretation separately. A successful API request does not mean a valid review finding. New domain findings and source qualifications must survive investigator-to-debate-to-editor handoff and manuscript revision export.
