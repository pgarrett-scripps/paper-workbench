# Prospective PRA evaluation

This package prepares a frozen comparison for independent assessment. It does not run a reviewer, call a model, recruit an expert, or contact anyone. Review generation remains a separate authorized step through the existing reviewer. The package accepts completed review artifacts after both conditions have used the protocol resources.

## Study contract

The protocol names exactly two conditions, `single` and `pra`. Both must record the same nonempty manuscript, raw source packet, figure list, domain guidance, tools, model, settings, tool call budget, and source request budget. Each condition separately records its model call budget. This makes the shared resources explicit while preserving the actual compute difference between one single-reviewer call and a multi-call PRA workflow.

The pretrial seal records these inputs before either review output exists:

- Candidate paper and source manifest
- Prior corpus manifest
- Prompt text and model settings
- Review implementation and domain guidance files
- Every file below the manuscript and source packet paths
- Every image byte
- Any other paths listed in `frozen_paths`

Candidate and prior corpus paper identifiers are normalized and compared before the seal. DOI URL and `doi:` prefixes are removed before comparison. DOI and paper ID must not overlap. Shared database record identifiers do not make two papers identical. A detected paper overlap blocks the study. The snapshot stores the hash and byte count of every file plus a hash of its own metadata. Recursive directory manifests detect files added after the seal. Python cache files are excluded.

After generation by a separately authorized runner, `attach-reviews` verifies the pretrial seal and creates a separate immutable generation snapshot. It includes both raw review outputs and any declared usage receipts. Status is then `reviews_attached`. Missing receipts remain unknown and are never inferred from planned budgets.

The package does not infer that a paper is fresh merely because its filename is new. The candidate manifest and the complete known prior corpus manifest are required study inputs. Corpus completeness remains an investigator responsibility and must be disclosed.

## Command line workflow

Run the offline integration fixture from the repository root:

```text
python3 -m experiments.pra_prospective seal \
  experiments/pra_prospective/fixture/protocol.json /tmp/pra-prospective-study

python3 -m experiments.pra_prospective verify /tmp/pra-prospective-study

# Generate the two fixture outputs outside the sealed inputs, then attach them.
mkdir -p experiments/pra_prospective/fixture/outputs
cp experiments/pra_prospective/fixture/review-templates/*.json \
  experiments/pra_prospective/fixture/outputs/
python3 -m experiments.pra_prospective attach-reviews /tmp/pra-prospective-study

python3 -m experiments.pra_prospective export \
  /tmp/pra-prospective-study /tmp/pra-prospective-public --seed 20260925

python3 -m experiments.pra_prospective report \
  /tmp/pra-prospective-study /tmp/pra-prospective-report.json
```

The export creates `assessment-packet.json` with randomized labels, portable manuscript blocks, sanitized source cards, evidence limitations, and generically named image and source files with hashes. Cards come from the actual review outputs and retain their scientific evidence IDs. Each card must point to a raw hash present in the frozen packet. Dangling IDs, conflicting cards, and quotations absent from the cited card block export rather than being repaired. Raw packet files are not copied into the assessor packet. Only sanitized card files are written. The export does not include condition names, workflow paths, generation metadata, debate ledgers, or costs. The seed and condition mapping are saved separately at `STUDY/private/condition-map.json` with owner-only file permissions. Review writing style can still reveal a workflow, so the blinding is procedural rather than guaranteed.

Copy `fixture/ratings-template.json` for each assessor. Set `source_sha256` to the anonymous packet hash. Then import it:

```text
python3 -m experiments.pra_prospective import-ratings \
  /tmp/pra-prospective-study \
  /tmp/pra-prospective-public/assessment-packet.json \
  /path/to/completed-ratings.json
```

The import requires a pseudonymous assessor ID, expertise statement, independence attestation, ISO rating date, and packet hash. The packet path and hash must match the recorded export. Every assessed item needs a supported, partly supported, unsupported, or cannot assess disposition. Any substantive disposition also needs an exact quotation from a named block in the portable frozen manuscript. A cannot assess rating records quote validation as not applicable. The package validates source identity and quotation location. It does not verify assessor identity or decide whether the scientific interpretation is correct.

## Output separation

The report presents independent expert correctness as its own result. It keeps three other outcome families separate:

- Model preference
- Human review overlap
- Observed cost receipts and planned condition budgets

Model preference and human review overlap remain separate and are not imported. Cost reports distinguish sealed observed receipts from planned budgets. Missing receipts are unknown. Receipts with token values plus an unknown-usage flag are partial. Pretrial reports do not read unsealed receipt paths. This prevents a model preference from being counted as expert correctness and prevents human review overlap from being treated as a complete scientific gold standard.

When no ratings exist, report status is `unscored`. When any assessor leaves items unrated, status is `incomplete` and the missing item IDs remain visible. Missing judgments are not converted to negative scores. A complete status means that all anonymous items received a rating. It does not establish reviewer superiority, domain generalization, assessor consensus, or publication readiness.

## Python integration API

The public functions in `experiments.pra_prospective.core` are:

- `seal(protocol_path, study_path)` validates parity and prior corpus exclusion, then creates the pretrial snapshot before review outputs exist.
- `attach_reviews(study_path)` verifies the pretrial snapshot, then freezes review outputs and optional usage receipts separately.
- `verify(study_path)` checks snapshot metadata and every frozen file.
- `export_anonymous(study_path, output_path, seed)` creates the public packet and private mapping.
- `import_ratings(study_path, packet_path, ratings_path)` validates provenance, identity, and quotations before storing an immutable assessor record.
- `report(study_path, output_path)` reports complete, incomplete, or unscored results without merging distinct outcome families.

All artifact writes are create-once. Repeating a command with identical content is safe. A command that would alter an existing artifact fails. Use a new study directory for a protocol amendment and preserve the prior snapshot.

## Verification coverage

`tests/test_prospective.py` exercises the complete offline path and checks existing outputs at seal time, missing resources, prior paper overlap, benign shared source identifiers, unequal budgets, recursive file tampering, snapshot metadata tampering, substituted packets, invalid dates, fabricated quotations, cannot assess semantics, portable evidence, receipt reporting, partial ratings, and honest unscored reporting. The fixture is synthetic and tests integration behavior only. It supplies no evidence about scientific review quality.
