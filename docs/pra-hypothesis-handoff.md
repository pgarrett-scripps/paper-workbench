# Preserve investigator exclusions through debate

Debate now receives every recorded discarded hypothesis alongside the candidate findings. Each exclusion has its own tracked ID and sentence components. The original note is preserved as an unendorsed investigator hypothesis, without fabricating a manuscript anchor.

Every hypothesis requires an explicit debate decision:

- Restore a useful, narrower question with an exact manuscript anchor and source evidence. It counts toward the same five-finding limit.
- Resolve it with source evidence and an explanation for each component.
- Defer it explicitly if evidence or editorial priority prevents selection. The note stays available in the handoff and export.

A missing or duplicate decision fails validation. A restored question without source support or a valid anchor fails validation. A rejected hypothesis with unresolved components fails validation. Scientific status and selection remain separate, so a lower-priority question can remain unresolved without being labeled false.

The normal panel reviewer now uses this handoff and the component validator. Existing experimental callers of `issue_ledger` receive the same exclusion records. Earlier run snapshots and results remain unchanged. Old ledgers without a version marker retain the older package format when replayed.

The viewer shows these records as previously discarded hypotheses with the debate arguments, component dispositions, and links to restored findings. The JSON review export retains the original notes and investigation context. This change does not add unendorsed hypotheses to the manuscript's selected review comments.

An offline replay of the previous investigator output includes all four findings and all three discarded hypotheses, including the collection-order concern. Reusing the old debate output against the new ledger fails because it has no decisions for those hypotheses. This is a regression check, not a new scientific review or a revision of the old benchmark score.

These controls prevent recorded exclusions from silently disappearing. They cannot guarantee that a model recognizes every valid concern or makes the right scientific decision. A concern the investigator never records is still outside this preservation guarantee. The update adds no model stage, although fuller handoff records can increase tokens within the existing debate call.
