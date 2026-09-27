# Matched strong-reviewer experiment status

The three-paper controlled experiment completed successfully. All 36 planned
calls succeeded, with no retries or missing judgments. The screening outcome is
improvement not demonstrated. Results are in `docs/pra-matched-reviewer-results.md`.
The fixed plan is in `docs/pra-matched-reviewer-plan.md`.

Runtime root: `runs/pra-matched-reviewers-3paper-v1`.

Runner: `experiments/pra_matched_reviewers/study.py`.

Command: `python3 experiments/pra_matched_reviewers/study.py run`.

Terminal session `91721` exited with code 0. Do not restart it or launch further
inference automatically. All three papers and both scoring passes are complete.

Six offline checks passed. They verify source-only indexing, preservation of
lower-priority findings, complete editorial dispositions, bounded connection
retries, no validation retries, and the matched end-to-end workflow. Both editor
prompts are identical before the discussion field. Reviewer requests match the
saved strong-agent request on all three papers. Source and dependency hashes are
frozen. None of the installed plugin or earlier experiment files were changed.

Reviewer 1 reuses the saved strong tool-using review. Reviewers 2 and 3 run in
parallel with its exact prompt, schema, manuscript tools, Sol model, and medium
effort. Both editor branches use the same initial reviews and complete finding
ledger. Only one receives the three focused discussion responses. Full reports
retain valid concerns below the top five. Equal-limit top-five packets and
complete retained reports are scored separately.

The subscription and zero paid credits were verified before launch. Account-wide
weekly usage was 66 percent at that check. That percentage includes other account
activity. No API-key billing, purchases, resets, or model fallback are authorized.

The budget is 36 planned new calls, with at most four extra stream-disconnection
retries and 40 total attempts. Each node may retry that explicit network error
once. Failed attempts remain saved separately. There are no retries for timeout,
authentication, schema, content, validation, or budget failures. The observed-token
stop is four million, with possible overshoot from three in-flight calls. Cached
input and unknown failed-call usage must be reported separately.

Post-run verification confirmed the shared panel, exact matched reviewer requests,
matched editor inputs except discussion, full finding preservation, top-packet
limits, source IDs, and usage. See `artifact_verification.json` in the run root.
Heartbeat `finish-peer-review-codex-pilot` is paused. The 15-concern human audit
package remains unfilled pending actual human ratings.

Stop after these three previously exposed development papers. Do not expand or
deploy. Report missing outputs and judge limitations. A single matched panel and
one editor sample per branch do not establish a general causal benefit of debate.

Top-packet mean coverage was 27.2% for reviewer 1 and 23.4% for both panel branches.
Both panels won two papers and lost one against reviewer 1. Debate and editor-only
consolidation tied on every paper. Both complete retained reports preserved the
panel union's confirmed coverage, averaging 36.7% with more concerns and words.
Full-report coverage is diagnostic and is not an equal-length superiority result.

New usage was 2,942,996 observed tokens: 1,450,240 cached input, 1,415,161 uncached
input, and 77,595 output. Inherited reviewer-1 generation accounts for another
1,042,405 recorded tokens that were not spent again. There were no failed calls,
retries, or unknown usage. No study expansion or production deployment followed.
