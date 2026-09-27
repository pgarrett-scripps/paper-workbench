# Three-general-reviewer experiment status

The run ended with one complete paper and two incomplete papers after connection
failures. The screening result is inconclusive. No retries are running.
See `docs/pra-three-reviewer-results.md` for the partial results and
`docs/pra-three-reviewer-plan.md` for the frozen hypothesis and decision rule.

Runtime root: `runs/pra-three-reviewers-3paper-v1`.

Runner: `experiments/pra_three_reviewers/study.py`.

The command `python3 experiments/pra_three_reviewers/study.py run` finished in
terminal session `27800` with exit code 0 after recording the incomplete results.
It must not be restarted automatically. All failure records are preserved.

Five offline tests passed. They exercise parallel independent review execution,
one discussion round, editorial selection, shared anonymous candidate scoring,
exact source chunks, preservation of selected text, and accounting for requests
already in flight. All input and runner hashes are frozen. Saved baseline packet
hashes match their original review files.

All calls select `gpt-5.6-sol` at medium effort. ChatGPT authentication and zero
paid credits were verified before launch. The account-wide weekly allowance was
59 percent used at that check. This includes account activity beyond this task
and is not a cost estimate for this experiment.

The fixed limit is 30 calls and 2.5 million observed tokens, with possible overshoot
from up to three in-flight requests. Failed calls are preserved without automatic
retry. Failed scoring passes remain missing while unaffected planned calls finish.
No purchases, resets, API-key billing, model fallback, or larger run are authorized.

The experiment saves all three initial reviews, one discussion response per
reviewer, a moderator report, and an editor decision. Findings retain their IDs
and exact text. Two anonymous scoring passes per paper cover the shared concern
pool. Results distinguish the first reviewer, full panel union, moderator selection,
final review, and saved single agent. The panel union has more concern slots and
is a diagnostic only.

Completed-paper source IDs, selected finding text, stage dispositions, and the
557-word final packet were verified. Initial review calls overlapped in time.
The unfilled 15-concern audit sample is preserved. Heartbeat
`finish-peer-review-codex-pilot` is paused. Do not claim expert validation or a
causal benefit from debate.

On nT89RltY10, reviewer 1 matched 1 of 17 reference concerns, the panel union
matched 4, the moderator and final editor matched 3, and the saved single agent
matched 5. Reviewer 2 alone also matched 4. The editor retained the moderator's
selection unchanged. A supported concern about evaluation breadth was omitted.

UwcZEoNP19 completed all three reviews and discussion responses, but its moderator
call disconnected. All three initial calls for IjduZQK8gM disconnected. These are
execution failures, not evidence that the architecture performed worse on those
papers. There are no final outputs or scores for either incomplete paper.

The run attempted 20 calls, with 16 successful and four failed. Recorded usage
is 549,040 tokens plus unknown usage for the four failed calls. No paid credits,
API keys, model fallbacks, purchases, or resets were used. Completing the remaining
papers would require a documented new attempt. No further inference is scheduled.
