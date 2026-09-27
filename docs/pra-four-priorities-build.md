# Four review infrastructure priorities

Implemented after the four-paper domain pilot. This build changes review infrastructure and prepares a prospective assessment workflow. It does not add a new model review or change the pilot results.

## 1. Figure, table and claim comparison

The default domain-enabled reviewer and the tool-equipped single-reviewer baseline receive the same source-derived result map. It links manuscript references to extracted captions and tables, retains numeric spans and source hashes, and flags differing model labels for inspection. Original figure pixels remain necessary for plotted values.

Two bounded tools expose the map and record comparisons of exact reported quantities. Comparisons include outcome, model, population, denominator, contrast direction, timepoint, units, scale and metric. Unknown context or different model definitions prevents an automatic equivalence claim. Recorded differences remain unverified reconciliation questions.

The map and comparison records survive the review interface and revision export. [Implementation and usage](pra-result-map.md).

## 2. Debate history and assertion status

The additive ledger now keeps a flat decision history with earlier criticisms, author defenses, decisive questions, reasons and qualifications. Unchanged decisions are deduplicated across rounds. A restored discarded hypothesis remains an unverified hypothesis even when the debate selects it for the final review.

Assertion status, editorial inclusion, exact source linkage and scientific truth status are separate fields. Source validation does not label a criticism scientifically confirmed. The audit is displayed in the interface and retained in exported review packages. [Audit semantics](pra-debate-epistemics.md).

## 3. Targeted source access

The existing source client now supports exact identifier resolution, a focused Europe PMC search with explicit coverage and truncation, and curated dated registration snapshots backed by pinned raw records. These actions share the existing request and manuscript-location limits.

Current metadata and search results remain ineligible for historical source support. A historical snapshot must match its pinned raw record. An archive captured after its claimed effective date requires explicit version provenance and curator attestation. This records curated provenance, not independent proof of historical completeness. Automatic registry-history reconstruction remains unavailable.

The review CLI accepts `--historical-snapshots`. Snapshot curation has a separate offline CLI. [Source API, curation and limits](pra-targeted-sources.md).

## 4. Prospective assessment workflow

A separate evaluation package prepares a frozen protocol, applies prior-paper exclusion and resource-parity checks, seals generation outputs, exports anonymous evidence packets, imports attributable independent assessments and reports completion, missing judgments, costs and outcomes separately.

This infrastructure cannot supply independent experts or establish their expertise by validating a form. The included exercise uses synthetic assessments only. Scientific correctness, model preference and overlap with human reviews remain distinct outcomes. [Evaluation commands and protocol](pra-prospective-evaluation.md).

## Verification and development artifacts

Offline checks on existing papers produced these artifacts:

- [Ecology result map](../runs/pra-priorities-v1/ecology-result-map.json): the Figure 3 caption links to Table 2 and triggers a model-label comparison. Plotted values remain untranscribed.
- [Ecology quantity comparison](../runs/pra-priorities-v1/ecology-comparison.json): different SLR and multiple-regression slopes with unresolved units and scale remain an incomplete comparison, not a confirmed discrepancy.
- [Health debate audit](../runs/pra-priorities-v1/health-recomputed-audit.json): the two restored questions remain unverified hypotheses despite valid source accounting.
- [Registration snapshot exercise](../runs/pra-priorities-v1/snapshot-smoke.json): a record captured in 2026 is unavailable as 2024 evidence. The test reuses a cached public response and makes no new network request.

These are known-paper development checks, not fresh scientific validation. The original pilot artifacts remain unchanged. No large raw datasets or author analyses were rerun.

Final verification passed 212 Python tests, JavaScript syntax checks, and the evidence-interface rendering test. A synthetic assessment exercise completed the pretrial seal, output attachment, anonymous export, rating import and reporting path. It correctly reported unscored before import, incomplete after one of two items was rated, and unknown usage where no receipts were supplied. [Verification record](../runs/pra-priorities-v1/verification.json).

The final portable evidence export also preserves historical capture and effective dates, curator provenance, and scientific fields named model or condition. Workflow metadata is removed through a field allowlist without deleting those scientific meanings. The final synthetic fixture was sealed after this correction.

No new model review calls or actual expert assessments were performed in this build. The next scientific step is to run a separately budgeted fresh-paper comparison and collect independent ratings. The infrastructure does not establish assessor identity, guarantee blinding from writing style, prove corpus completeness, or establish that declared generation settings were followed merely by freezing them. Runtime manifests and receipts remain part of the study audit.
