# Frozen evidence packets

A frozen packet is a nonempty flat directory of regular files. Symlinks and nested directories are rejected. `ReviewRequest` hashes every filename and byte payload during construction, verifies the same manifest before execution, and verifies it again after synthesis.

The current source adapters address cached records by the SHA-256 digest of the exact HTTPS request URL. Each available record needs two files:

- `<url-sha256>.raw` contains the unmodified JSON response bytes.
- `<url-sha256>.json` contains metadata with the exact `source_url` and the SHA-256 digest of the raw bytes in `raw_sha256`.

The raw JSON must match the schema expected by the named source adapter. A packet miss returns `not_in_source_packet` before request accounting or network access. An invalid hash raises an error. An optional `index.json` can describe available records to the model, but it does not make a missing cache pair available.

Collectors must preserve the exact adapter URL, response bytes, retrieval timestamp, provider identity, record version when supplied by the provider, and packet creation provenance. They should build the packet before condition assignment and reuse the identical directory for every compared condition.

`evidence_mode="current"` supports eligible records from a frozen packet. `evidence_mode="historical"` remains conservative. The current adapters do not establish historical database state from a newly frozen current record, so those cards remain `version_unavailable`. A future historical collector needs a separately validated snapshot provenance contract before historical cards can become eligible.

Packet files are evidence inputs. They cannot contain benchmark keys, human reviews, candidate outputs, or grading labels.
