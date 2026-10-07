# Saved draft ordinary synthesis

`SavedDraftSynthesisRequest` runs one ordinary synthesis stage over the exact independent drafts saved by a completed ensemble debate run. It does not launch reviewer discovery again.

The request requires the original ensemble output, the same manuscript workspace, the original frozen source packet, and the complete original image set. The public API verifies the manuscript manifest, model, debate origin, input review hashes, evidence packet hashes, source cache stability, image hashes, synthesis token budget, and two-tool synthesis allowance before accepting the result.

Call `run_saved_draft_synthesis(request)` with a fresh output directory. The returned artifact uses the standard `editor_package` shape. Its `usage` covers only the new synthesis stage. `reused_discovery_usage` preserves the original ensemble usage as a separate record. The synthesis provenance records zero new discovery calls, one generation call, the original artifact and review hashes, preserved raw evidence hashes, packet manifest, and image hashes.

The route accepts only `synthesis_policy="ordinary"`. It cannot be used to replace or relabel the original debate result.
