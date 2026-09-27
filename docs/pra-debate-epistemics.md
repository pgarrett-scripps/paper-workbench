# Debate epistemic audit

The additive debate ledger now records three separate questions for every issue:

1. Was the issue selected for the final review?
2. Did the decision cite exact source text?
3. What kind of assertion remains after debate?

These answers are intentionally independent. Selection is an editorial decision. An exact quotation establishes traceability to a supplied source. Neither one proves that the manuscript contains a defect.

Restored investigator hypotheses receive `unverified_hypothesis` status even when the debate selects them and cites exact source text. A selected hypothesis can be a useful, source-linked author question. Structural accounting cannot convert it into a confirmed error.

Candidate findings use conservative labels such as `source_linked_concern`, `source_linked_clarification`, `concern_with_recorded_counterevidence`, and `unresolved_concern`. Every record also carries `scientific_truth_status: not_mechanically_determined`.

The audit preserves a flat decision history for each stable issue ID. Later rounds retain earlier criticisms, author defenses, decisive questions, reasons, and qualifications without embedding prior packages recursively. Repeating an unchanged decision does not add a duplicate history row.

The audit is generated offline after the existing source and component validation passes. It adds no model call and does not alter the five-finding limit. Existing version 3 artifacts remain readable. New revision packages add an `epistemic_audit` object while retaining the existing findings, source hypotheses, component decisions, and investigation context.

The audit supports inspection. It does not perform semantic truth assessment, establish expert consensus, or determine whether a cited passage logically proves a criticism or defense.
