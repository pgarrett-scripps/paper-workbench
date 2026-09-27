# Reconciliation preflight tools

`paper_workspace.table_evidence` reads selected reported-results workbooks into a source register. It preserves literal cached cells, source hashes, worksheet names, addresses, merged ranges, and missing formula caches. It does not execute formulas or reconstruct raw analyses.

`paper_workspace.claim_checks` defines the matched question-only review contracts and structured investigation records used in the completed claim retest. `paper_workspace.reconciliation_tasks` adds a stricter, subsequent target inventory and completion audit. These versions remain separate so the evaluated workflow can be reconstructed accurately.

Generate targets without a model call:

```bash
/home/ty/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m paper_workspace.reconciliation_tasks runs/pra-claim-retest-v1/workspace --catalog runs/pra-claim-retest-v1/table-catalog.json --output runs/pra-claim-retest-v1/post-run-targets.json
```

For a new workspace, call `build_catalog` with the explicitly selected reported-result XLSX paths, then `build_tasks` with the verified paper and catalog. `task_prompt` supplies the task-specific response instructions. An orchestrator should preserve all target dispositions and run `audit_tasks` before describing the investigation as complete. These functions are available for integration but do not replace the default reviewer automatically.

Each comparison result identifies its task, comparison status, matched outcome and test, strongest author defense, and exact evidence. A compared caption task needs evidence from its own target statement, a linked manuscript passage, and linked table cells. A compared stage task needs the specific stage claim and linked measurement evidence. Unresolved or inapplicable tasks can be recorded without inventing a manuscript defect.

Source-link candidates are found from explicit figure references and measurement language. Supplementary figures have distinct identities from main figures. This does not infer a complete scientific claim graph or guarantee that a proposed link concerns the same experiment. Exact-reference and task-accounting checks do not validate scientific interpretation. The inventory deliberately remains an investigation queue, not a list of alleged errors.

The follow-up target gate has passed local tests and source inspection. It has not yet been evaluated in a new model trial. Preserve that distinction when reporting progress or preparing a paper.

The current investigator prompt also asks that useful scoped questions remain anchored candidates for debate rather than appearing only in discarded hypotheses. This was a post-generation instruction change and remains unbenchmarked.
