# Clarification changes and repeated evaluation

Both completed anonymous assessments preferred ensemble. One assessed unchanged saved plant reviews. The other assessed the updated workflow on one fresh ecology manuscript. Both are development observations from a single Terra judge per manuscript, not independent expert validation or proof of superiority.

## Results

| Manuscript | Ensemble supported primary findings | Sequential supported primary findings | Preferred review | Delivery |
| --- | ---: | ---: | --- | --- |
| Saved carrot study, DOI 10.1371/journal.pone.0318753 | 5 of 5 | 4 of 4 | Ensemble | Saved reviews unchanged, new judge completed |
| Fresh burrowing owl study, DOI 10.1371/journal.pone.0306660 | 5 of 5 | 4 of 4 | Ensemble | Both updated workflows completed without delivery repair |

Neither main review received an unsupported-allegation or unverifiable rating on either manuscript. All ratings passed the source-reference and accounting checks. These checks establish reference validity, not scientific truth.

For the carrot manuscript, the ensemble main report retained the repeated-measurement clarification and a post hoc procedure clarification. Sequential revision had dropped the repeated-measurement question because the design was not fully specified. The judge rated that question useful and proportionate. The independent second review supplied five additional supported issue groups beyond the shared initial review. Ensemble retained ten groups across primary and secondary comments, versus five for sequential revision. One unanchored ensemble hypothesis remained unscored. Legacy secondary comments are still the saved original formulations, not retroactively rewritten adjudicated comments.

The plant judge's preference prose incorrectly said the primary reports shared four problems. Its explicit membership lists share three groups. The report above uses the per-finding ratings and membership lists. This internal inconsistency is preserved in `saved-assessment-audit.json` and illustrates why a judge's narrative should not be treated as ground truth.

For the fresh owl manuscript, each independent reviewer emitted four findings. Their union contained five supported issue groups. The second reviewer added a concern about attributing annual treatment differences to ambient food availability. The initial and sequential reviews did not discover it. Debate retained the four shared initial concerns and the additional issue. No supported group was lost from either workflow's own discovery history.

The judge preferred ensemble for this additional coverage. It considered sequential revision somewhat more explicit about mediation, while finding ensemble's requested causal qualification sufficient. A source spot check confirmed the additional concern's basis: the discussion attributes annual effects to food differences, the food-timing confidence interval includes zero, and the second food sampling occurred after mean control dispersal. The review requested a qualification, not a new experiment or an assertion that food had no effect.

Debate also kept the randomization clarification. The second reviewer had dismissed the abstract/methods discrepancy partly because region was modeled as a random effect. The final review correctly distinguished statistical adjustment from an allocation block. Sequential revision retained this clarification too.

## Implemented changes

- Discovery, sequential revision, and debate share a policy to retain consequential clarification questions without asserting an unverified defect. Applying it to both conditions avoids giving ensemble exclusive access to the improvement.
- Ensemble v3 requires explicit adjudicated secondary wording for retained issues with deferred components and no primary destination, including issues with a mixture of resolved and deferred components. The source candidate remains separately available for audit.
- Unanchored unresolved investigator notes can remain audit-only. They cannot masquerade as author-facing findings. Secondary replacements are disallowed until they pass a dedicated edit workflow.
- New-candidate decisions remain embedded in their candidates. Deterministic IDs prevent the duplicated bookkeeping that caused the earlier clinical failure. Missing scientific judgments are never invented.
- Source-handle conversion and constraints now cover nullable schema branches used by secondary findings.
- Sequential revision preserves scientific history without re-inserting redundant workspace maps and audit metadata.
- Evaluation writes owner identity, heartbeat, deadline, and terminal state. Local recovery requires the identical saved request and cannot launch inference. An actual completed assessment was recovered with identical output and zero new calls.

The fresh paper produced no secondary comments and no debate-only new candidates. Consequently, this live run exercised the overall v3 workflow but did not exercise those two new-output branches. Their validation is offline. Do not describe the earlier clinical failure mode as live-revalidated.

## Budget and preservation

Exactly seven new calls completed, totaling 608,355 observed tokens. No new-run usage is unknown. No model retries, paid credits, or resets were used. The old interrupted plant judge remains preserved with unknown usage and is not included as zero in this new-run total.

| Fresh-paper generation | Logical tokens |
| --- | ---: |
| Two independent reviews plus debate | 236,186 |
| Initial review plus two ordinary revisions | 242,989 |

Each logical total includes the shared initial call. Actual spending counts it once. The saved plant judge used 116,129 tokens and the fresh judge used 92,504. Tool and call ceilings were matched. The small token difference on one paper is not an efficiency result.

Fresh-study inputs, protocol, and source were frozen before generation. The end-of-run seal check passed and is recorded in `final-seal-verification.json`. Raw outputs, decisions, failures from prior studies, anonymous inputs, source hashes, usage receipts, and the frozen source copy remain available in `runs/pra-ensemble-clarification-v1`. The owl paper is excluded from future confirmatory sampling.

After that final seal check, a status-only hardening change added process-namespace awareness. A sandbox that cannot see the owner process now reports unverified status instead of falsely declaring interruption. It changes no review prompt or scientific output. All 293 offline tests pass after this change.

## Interpretation and next step

Keep two independent reviewers plus one debate as the development default. The fresh result supports the value of independent discovery and shows debate retained the additional finding. It does not isolate debate's value from a simpler editor receiving the same pooled findings. Neither human-review overlap nor expert correctness was measured.

Stop adding agents and tools for now. Before a larger scientific study, freeze this workflow and use the complete pooled draft as an additional ablation if the aim is to claim debate itself helps. Include review delivery, supported gains, losses, false premises, and actual token use as outcomes. A small blinded expert audit remains necessary for claims that extend beyond same-family model preference. Any larger trial requires separate authorization.
