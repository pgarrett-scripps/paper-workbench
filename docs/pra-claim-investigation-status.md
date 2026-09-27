# Claim investigation status

The new prototype and three-paper protocol are frozen. Five offline tests passed,
including a complete mocked experiment, reference isolation, equal stage and tool
access, evidence exchange ordering, exact finding preservation, output limits,
calculation receipts, and budget stops.

Subscription authentication and zero paid credits were verified on September 17,
2026 at 04:57 UTC. The account reported 70 percent weekly usage. All workers select
Sol at medium effort. No resets, credit purchases, or model fallback are authorized.

Runner: `experiments/pra_claim_investigation/study.py`.
Run root: `runs/pra-claim-investigation-v1`.
The new run compares an investigation team, a six-stage sequential controller,
and the saved historical strong review. The primary output limit is unchanged.
Earlier experiments remain preserved and stopped.

The first four calls completed successfully. Their reconstruction exposed a
benchmark applicability problem before any new scoring: the supplied TableQA
manuscript already answers parts of human reference requests about additional
models, time and token use, and verification iterations.

The runner was deliberately interrupted at the parallel investigation boundary.
All active calls saved their outputs before exit. Session 47801 exited with code
130. Do not restart this frozen experiment. No comparative result was produced.

Recorded usage is 945,328 tokens, including 761,088 cached input tokens, 166,371
uncached input tokens, and 17,869 output tokens. All four calls succeeded, with
13 calculation receipts, no unknown usage, and no retries. Frozen hashes still
verify. Approximately four million observed tokens remain within this redesign's
five-million-token allowance.

The project continues with benchmark integrity repair. Public OpenReview metadata
requests returned a browser challenge. Saved responses are under
`runs/pra-version-audit-v1`. Review details and the revised execution route are in
`docs/pra-benchmark-integrity.md`. No superiority result is available yet.

The next input preparation is complete. Three deterministic FLAWS cases have
version-pinned originals, altered PDFs, exact source differences, and separate
annotations. All eight documented edit blocks passed source-presence checks,
and changed PDF pages were inspected. See
`docs/pra-known-error-next-experiment.md` for the next bounded comparison and
`runs/pra-known-error-preparation-v1/input_feasibility.json` for the checks.
No known-error benchmark inference has started. The project heartbeat remains active.
