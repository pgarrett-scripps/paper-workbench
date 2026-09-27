# Changes after the two-paper pilot

The user authorized routine improvements on September 24, 2026. These changes address observed investigation and handoff limitations without adding reviewers, model calls, or a new scientific trial.

## Implemented

The reusable workspace investigator now considers six areas before choosing detailed investigations: claims, comparators, measurement, interventions, replication, and internal consistency. These are questions to examine, not presumed defects. Domain-specific checks are applied only where relevant. The response records areas as examined, unresolved, or inapplicable, with short explanations and source quotations. The finding limit remains five.

The record is saved as part of the existing response rather than requiring a separate note-saving tool call. The investigator now has three evidence tool calls instead of four calls that included a mandatory note. Debate still has two lookups. This reduces the maximum tool interactions by one. Actual token savings and review quality have not been measured. Plain mode also receives three tool calls, without the new coverage instructions or schema.

The record is validated for complete area accounting and exact quotation identity. Invalid or missing entries become unresolved in the validated record. This validation does not verify the scientific judgment or prove that a check was thorough. A superficially valid record can still describe weak investigation. Raw output is preserved alongside the validated record.

The reusable runner now applies source placement and numerical edit guards before passing suggestions to debate. The final debate output also receives those guards before entering the editor package. Raw investigator and debate responses remain saved separately. Coverage records are included in workspace and panel JSON exports. The existing viewer has no dedicated coverage panel yet.

## Preservation and verification

Before changing shared code, all 17 workspace source files recorded in the completed pilot manifest were copied into `runs/pra-workspace-two-paper-v1/code-snapshot/paper_workspace/`. Each copied file matches the manifest hash. The completed pilot's prompts, model outputs, evaluation labels, and results remain unchanged. Historical review schemas and investigation instructions remain available for the frozen experiment code.

Offline tests exercise complete and malformed coverage records, source quotation validation, preservation of uncertainty, numerical-edit withholding through the entire mocked investigator-to-debate flow, raw response preservation, source immutability, and coverage export. The full suite passes 42 tests. Mocked calls use synthetic responses and do not contact a model.

These changes are implemented but not scientifically validated. No new review or evaluation model calls were made for this update.

## Decisions held for discussion

Adding specialist teams, removing debate, reconstructing manuscripts into Typst, exhaustive literature retrieval, and broad benchmarking would materially change the system or its cost. None was started. The next empirical comparison should use fresh papers and explicitly compare the workspace against a same-model ordinary reviewer with comparable budgets. A larger study still requires user authorization.
