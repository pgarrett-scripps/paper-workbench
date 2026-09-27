# Evidence references and candidate preservation

The reviewer now selects immutable evidence handles instead of repeatedly copying quotations. Each handle identifies a contiguous span of a specific manuscript block or eligible external source card. The source hash, offsets and span hash are recorded when the system expands the handle into the existing review format.

Manuscript anchors, supporting manuscript evidence and external source evidence have distinct fields. The output schema now restricts manuscript references to the finite supplied registry. Unknown handles, changed sources, ambiguous manuscript anchors and mismatched source types fail validation. Invalid references in actual findings or debate decisions block the run. Coverage records require manuscript evidence. An invalid advisory coverage record is preserved in an audit, stripped of unusable evidence and marked unresolved. It cannot discard otherwise valid findings or count as examined coverage. The system does not use fuzzy matching or silently repair a model quotation.

New runs preserve the direct model response in `responses/*-model.json`, the expanded response in `responses/*.json`, and a transformation audit in `evidence_handle_audit`. Existing source-binding, quotation, edit-fidelity and debate checks still run after expansion. A valid evidence handle establishes source identity, not scientific correctness.

Manuscript spans are bounded at 350 characters. Long sentences can be split at whitespace. An edit replaces only its chosen span, and the prompt explicitly warns against writing a replacement for a larger passage. Debate component `final_quote` still quotes the model's final comment and remains subject to exact retention checks.

The investigator can produce up to ten distinct candidates without a minimum or a category quota. It retains the existing concise comment budget. Debate selects at most five main findings, while the editor package preserves all candidates, their components and dispositions. Supported secondary concerns and unresolved secondary questions remain distinct in `candidate_inventory`, which also survives draft export. Fully resolved components are categorized as resolved even when the model calls their scientific status a supported clarification. An absent candidate is not treated as evidence that the issue was examined or disproved.

Both the current single reviewer and PRA receive conditional design checks for covariate timing, denominators, analysis populations, ecological assignment units, model descriptions and figure reconciliation. These checks are applicable questions, not required criticisms. The single reviewer retains its five-finding output. PRA retains one investigator call and one debate call.

When no historical registry snapshots are configured, the prompt states that availability before generation. Reviewers are directed to request dated author documents when appropriate rather than spending calls on an unavailable resource.

Offline regression fixtures cover the saved ecology quotation typo, reordered registry fields and external source IDs placed in manuscript-only fields. The original failed outputs remain unchanged and still fail strict validation. Deterministic replay is an engineering check, not evidence of better scientific review.

The finite output constraint, coverage isolation and resolved-item classification were added after the first fresh trial. Offline replay verifies them against that trial's saved failures. They have not yet been tested together in another live review. The original frozen source and results remain archived.
