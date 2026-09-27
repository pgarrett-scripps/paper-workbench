# Manuscript workspace handoff retest

The revised debate retained the figure-based concern that the earlier debate discarded, preserved the reported numerical inconsistency, and explicitly accounted for all nine incoming findings. This is a successful regression check on one known development paper. It does not establish that the complete workflow is better than a single reviewer.

## What changed

Two Sol implementation agents improved the evidence handoff and model runner. The main task integrated their changes into the schema, viewer, export, and a one-call retest.

- Every incoming finding has a stable ID and an explicit debate disposition: retained, merged, rejected, or needs verification.
- Distinct concerns at the same source passage remain distinct. Missing, malformed, or duplicate dispositions leave findings in an unendorsed verification queue.
- Supplement images are verified against the manuscript manifest. PDF page images are regenerated from the verified original and compared before handoff.
- The editor export contains all original findings, dispositions, validation records, and the selected report. The viewer shows the debate history alongside located comments and edits.
- Cache identity includes tool configuration and source-image identity. Completed calls can be recovered without inference. Unknown usage, failed attempts, and incomplete interrupted attempts cannot silently bypass accounting or trigger retries.

The reusable default panel remains one investigation followed by one evidence-focused debate. This retest supplied two existing reviews to exercise reconciliation without paying to generate them again.

## Frozen development check

Paper: TDP-43-mediated alternative polyadenylation is associated with a reduction in VPS35 and VPS29 expression in frontotemporal dementia, DOI 10.1371/journal.pbio.3003573.

The retest reused the original plain review and the valid workspace review. It attached S5 Fig and original PDF page 8, both inspected during the earlier investigation. The debate received the cited source passages and had two optional evidence lookups. It used neither lookup and performed no literature retrieval or reanalysis.

The run requested `gpt-5.6-sol` at medium effort through the existing ChatGPT subscription. The CLI does not report a resolved model identity. Code, schema, input hashes, image hashes, prompt, and success criteria were frozen before inference in `runs/pra-workspace-handoff-retest-v1/`.

| Check | Result |
| --- | --- |
| Incoming findings accounted for | 9 of 9, each with one structurally valid disposition |
| Final findings anchored to source | 5 of 5 |
| Image-based concern | Retained as a request to clarify perturbation labels and replication reporting |
| Numerical inconsistency | Retained as a question, no invented correction |
| Original findings and disposition history in export | All preserved |
| Original manuscript changed | No |
| New model calls | 1 |
| Observed model tokens | 31,419, comprising 28,624 input and 2,795 output |
| Unknown usage in this retest | None |

These token figures cover only the new debate. They exclude implementation agents and the current task. Earlier pilot costs, including an interrupted attempt with unknown usage, remain recorded separately in the original pilot report.

## Scientific interpretation

Three pairs of overlapping concerns were merged: causal interpretation, case-control confounding, and claims about timing or progression. The numerical issue and S5 figure issue were retained separately. The qPCR interpretation concern from the plain review was rejected with an explicit rationale and remains available in the history.

The S5 image uses guide-style condition labels while the Methods specify shRNA. This supports a narrow clarification request. It does not establish that the experiment was performed incorrectly. The displayed observations do not establish biological independence.

The qPCR rejection is an editorial judgment, not a validated finding that the original concern was wrong. In particular, asking for assay validation is not equivalent to alleging an invalid assay. A later assessment should examine whether debate suppresses useful clarification requests as well as unsupported allegations.

All nine dispositions passed structural checks. This means that IDs, reasons, source references, and final finding references were coherent. It does not certify the scientific reasoning. The five-finding output limit can still affect which concerns are selected, although the complete input history is preserved.

The implementing agent assessed this known case without blinding. No independent expert review or human-review comparison was performed. Both the prompt and image handoff changed, so the result cannot isolate which modification caused the difference. One development paper and one stochastic run cannot support an efficacy or superiority claim.

## Validation and next boundary

All 31 deterministic tests passed. Local HTTP checks confirmed persistent decisions, undo, conflict handling, cross-origin rejection, preserved source text, and open scientific issues. JavaScript syntax passed, and the revised review was inspected in the browser.

The next useful study would use previously unreviewed experimental biology manuscripts and matched source access. Compare a single investigator against that same investigator followed by debate, with the model, source files, and reporting limits fixed. Score supported consequential concerns, unsupported allegations, lost useful findings, edit fidelity, and token cost. Published reviews would provide a reference set, not exhaustive ground truth. A single-agent baseline needs the same images and tools to distinguish infrastructure gains from debate gains.

No larger trial has been launched. That remains subject to the user's authorization.

## Local artifacts

- `experiments/pra_workspace_handoff_retest/run.py`: one-call retest runner
- `runs/pra-workspace-handoff-retest-v1/criteria.json`: criteria recorded before inference
- `runs/pra-workspace-handoff-retest-v1/manifest.json`: frozen inputs and code fingerprints
- `runs/pra-workspace-handoff-retest-v1/response.json`: raw debate response
- `runs/pra-workspace-handoff-retest-v1/editor-package.json`: complete finding history and selected findings
- `runs/pra-workspace-handoff-retest-v1/review-package.json`: source-preserving export
- `runs/pra-workspace-handoff-retest-v1/execution/usage.jsonl`: call receipt and usage

Viewer: [Revised debate with source images](http://127.0.0.1:38744/?review=panel-handoff-retest-v1).
