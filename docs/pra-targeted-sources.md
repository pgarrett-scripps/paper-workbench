# Targeted source access

Implemented on 2026-09-25. This module extends the existing exact-record evidence client. It does not add another request budget, arbitrary URL fetches, paid services, bulk retrieval, or a model call.

## Integration API

Create the existing `SourceClient` with its normal state and cache directories, then wrap it:

```python
from paper_workspace.external_evidence import SourceClient
from paper_workspace.targeted_sources import HistoricalRegistrationStore, TargetedSources

client = SourceClient(state, cache, limit=6, mode='current', cutoff='2025-01-01')
sources = TargetedSources(client)
literature = sources.search_literature('specific mechanistic claim', 'b0042', limit=3)
identity = sources.resolve_identifier('doi', '10.1234/example', 'b0042')

snapshots = HistoricalRegistrationStore(snapshot_directory)
historical = TargetedSources(client, snapshots).historical_registration(
    'clinicaltrials', 'NCT01234567', '2020-06-01', 'b0042')
```

The wrapper calls `SourceClient.fetch`, `reserve_target`, and `store_card`. Its network calls therefore share the six-request allowance, verified cache, frozen-packet behavior, source-card store, and two-manuscript-location limit with ordinary `lookup_source` calls. A curated local snapshot does not spend a network request, but it does reserve one of the two manuscript locations.

Root integration can expose these as separate tools or route them through one dispatcher:

- `search_literature(query, block_id, limit=3)`
- `resolve_identifier(kind, identifier, block_id)` where kind is `doi`, `pmid`, `pmcid`, `nct`, or `osf`
- `historical_registration(registry, identifier, as_of, block_id)` where registry is `clinicaltrials` or `osf`

Every output is a normal evidence card with a stable `evidence_id`. Literature hits also have stable `source_id` values based on returned publication identifiers. Identifier results have their own `source_id`. These IDs identify retrieved evidence. They do not certify scientific support.

## Literature search coverage

The search uses the public Europe PMC REST search endpoint with JSON `core` results and a maximum page size of three. A cutoff adds a `FIRST_PDATE` range to the query and results later than the cutoff are excluded again during parsing. The returned coverage record states the query, cutoff, requested limit, reported total hits, returned count, truncation, and the fixed limitation that only the first relevance-ranked page was inspected.

The selected fields are publication source and IDs, PMID, PMCID, DOI, title, author string, first publication date, journal, up to six publication types, abstract, and open-access flag. Search does not perform synonym auditing, citation chasing, full-text searching, or a second page. Abstract text is a lead for review, not a substitute for checking the full paper. [Europe PMC REST service](https://europepmc.org/RestfulWebService)

## Identifier resolution

Resolution uses fixed official endpoints:

- DOI through the public Crossref v1 single-work endpoint
- PMID and PMCID through exact-field Europe PMC searches, capped at two candidates
- NCT through the ClinicalTrials.gov v2 single-study endpoint
- OSF through the public registration endpoint

The parser reports `resolved`, `ambiguous`, or `identity_mismatch`. It returns only small identity and date fields. It does not infer citation support, registration chronology, or record equivalence from a title match. Crossref describes its REST output as depositor and trusted-source metadata. Public access needs no key. [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/), [Crossref access](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)

PMID resolution uses `EXT_ID` together with `SRC:MED`, and accepts only a returned MED record. This prevents an identifier collision with another Europe PMC source. DOI resolution uses the same `api.crossref.org/works/{doi}` endpoint as the existing adapter and frozen packets.

Live literature and identifier responses remain ineligible when the client runs in historical mode. A publication cutoff narrows discovery, but it does not turn a current API response into an archived historical record.

## Historical registration snapshots

Current registry records are not historical evidence. The implementation does not rely on an undocumented or unstable live history endpoint. It reads a curated, dated, immutable snapshot set supplied by the project.

Create a snapshot set from an actual saved official JSON response. The output directory must be new or empty:

```text
python3 -m paper_workspace.targeted_sources \
  --raw official-response.json \
  --output curated-snapshot \
  --registry clinicaltrials \
  --identifier NCT01234567 \
  --captured-at 2020-01-02T00:00:00Z \
  --source-url https://clinicaltrials.gov/api/v2/studies/NCT01234567
```

The curation command limits the raw response to 2 MB, verifies that the official URL matches the registry and identifier, parses identity and selected fields through the active adapter, limits selected fields to 14 KB, writes the raw response beside derived metadata, pins both hashes, and reopens the finished set for verification. Its result includes the manifest hash for separate release pinning.

The directory contains `manifest.json`:

```json
{
  "schema_version": 1,
  "files": {
    "clinicaltrials-NCT01234567.raw.json": "sha256-of-raw-file",
    "clinicaltrials-NCT01234567.snapshot.json": "sha256-of-metadata-file"
  }
}
```

Each snapshot file contains:

```json
{
  "schema_version": 1,
  "registry": "clinicaltrials",
  "identifier": "NCT01234567",
  "effective_date": "2020-01-01",
  "captured_at": "2020-01-02T00:00:00Z",
  "source_url": "https://clinicaltrials.gov/study/NCT01234567",
  "record_version": "2020-01-01",
  "raw_file": "clinicaltrials-NCT01234567.raw.json",
  "raw_sha256": "sha256-of-captured-official-response",
  "fields": {
    "primary_outcome": "Pain at 12 weeks"
  }
}
```

The store verifies every metadata and raw file against the manifest, checks the raw hash again against snapshot metadata, permits only matching official ClinicalTrials.gov or OSF API source URLs, validates dates, and never writes during lookup. It selects the latest snapshot whose effective date is on or before `as_of`. If none exists, it returns `historical_snapshot_unavailable`. The evidence card reports curated provenance and does not certify historical completeness.

By default the effective date is the capture date. A later capture may represent an earlier official archived version only when curation supplies both `--archive-effective-date` and a nonempty `--version-locator` plus `--curator-attestation`. These fields document why that exact official response represents the earlier registry state. A current record update date alone is never accepted as historical completeness. Lookup also rejects an `as_of` date after the client's configured cutoff.

Snapshot curation is a separate acquisition step. It should preserve the raw official response outside model context, record its hash, select review-relevant fields without changing their meaning, and freeze the manifest before a comparison run. Newly fetched current records cannot be relabeled as historical snapshots.

## Fixed limits and security properties

- Six shared network requests per condition through the existing client
- Two shared manuscript block locations across exact lookup, search, resolution, and historical access
- Three literature hits from one Europe PMC page
- Two candidates for exact PMID or PMCID resolution
- No caller-supplied URLs
- HTTPS and the existing host allowlist only
- No keys, paid APIs, redirects, bulk downloads, or author data uploads
- Existing cached responses and historical snapshot artifacts are read and verified, never rewritten

Tests cover stable literature source IDs, explicit search truncation, cutoff filtering, exact and ambiguous resolution, the shared limits, immutable snapshot selection, tamper detection, official-host enforcement, and a historical lookup that performs no network request.
