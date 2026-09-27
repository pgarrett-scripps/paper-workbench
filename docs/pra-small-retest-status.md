# Three-paper PRA retest status

Updated 2026-09-16.

The bounded retest has finished with all three revised reviews and 17 of 18
judgments. One failed judgment remains missing. The report is in
`docs/pra-small-retest-results.md`. No coverage improvement was observed.
The strict screening result is inconclusive. No further inference is scheduled.
The fixed plan is in `docs/pra-small-retest-plan.md`.

Nine offline checks passed, including execution of the real frozen PRA graph
with mocked model responses. They cover the complete panel, two debate rounds,
cross-round information flow, immutable selected findings, complete dispositions,
exact source extraction, and invalid evidence handling. All three actual input
manuscripts passed the engine's readability check.

Code and input hashes were frozen before model execution. The installed plugin
and the completed ten-paper pilot are unchanged. The new adapter retains debate
and gives specialists investigative tasks. Definitive synthesis outcomes without
a valid source location remain unresolved.

Runtime root: `runs/pra-findings-debate-3paper-v2`.

Runner: `experiments/pra_findings_debate_recovery/study.py`.

The completed command was
`python3 experiments/pra_retest_completion/finish_available.py` in terminal
session `18488`, which exited with code 0. Sessions `17209` and `60802` exited with code 2 and must not be
restarted. Check live process state before launching anything.
An empty sandbox process listing does not prove the host process stopped.

The account check confirmed ChatGPT authentication and zero paid credits, with
16 percent of the weekly Codex allowance used before launch, and 20 percent at
the recovery check, then 24 percent before continuing unaffected scoring. The experiment
requests `gpt-5.6-sol` at medium effort. No API keys or automatic fallback are used.
The limits are 72 completed calls and six million observed tokens, with possible
one-call overshoot. Expected inference is 66 calls.

Heartbeat `finish-peer-review-codex-pilot` has been repurposed and renamed
"Finish three-paper PRA retest". It is paused after reporting completion.
It must not expand to more papers automatically.

The experiment saved an available-results report and an unfilled 30-item audit
package. Treat results as a development signal. This small
previously exposed subset cannot establish general superiority or isolate the
causal contribution of debate.

## Export recovery

Attempt 1 stopped after all 13 first-paper model calls succeeded, using 506,083
observed tokens. Four of five selected findings had evidence ranges exceeding
the requested eight lines. The cited coordinates were within the actual source.
The final renderer rejected those ranges, so no comparison was scored.

The original runner, responses, and failure remain frozen. Attempt 2 copies their
hashes and usage, changes only final export handling and quality reporting, and
preserves every original finding and debate input. The exporter resolves complete
in-bounds ranges directly from the manuscript. It keeps the length violations
visible. It still rejects nonexistent or blank locations. Exact source locations
do not establish that a criticism is scientifically correct.

Ten offline tests passed. The complete first-paper graph replayed using all 13
exact request-cache matches, with a guard forbidding new model inference. No
review was regenerated and no findings were rewritten. The original protocol,
prompts, model, paper selection, and total limits remain unchanged. Inherited
usage counts against those same limits.

All revised reviews and all unfailed scoring calls have finished. Because the
range-length quality check failed, the strict screening result must be reported
as inconclusive. The completed coverage comparisons can still show an exploratory
direction of change. The recovery and all deviations must accompany those results.

## Missing judgment

The second scoring pass for the saved single-agent review of nT89RltY10 timed
out after 600 seconds. Its response file does not exist and its incurred token
usage is unknown. At that point, 47 calls had succeeded and one had failed, with
2,338,550 observed tokens excluding the unknown failed-call usage.

The continuation runs only unattempted scoring calls and skips that failed
request. It does not rerun any review or retry failed inference. Frozen prompts,
schema, manuscript text, and scoring logic are unchanged. The constructed request
hashes exactly match all six previously attempted judging requests. Source hashes
and details are in `completion_provenance.json` and `completion_prompt_check.json`.

Completion produced 17 of 18 judgments, nine concern packets, and the unfilled
manual audit package. The missing pass must remain missing. Do not average
different paper subsets across conditions or claim a complete three-paper result.
Report available paired comparisons and any missing-data bounds explicitly.

## Final accounting

There were 66 inference attempts, 65 successful and one timeout. Observed usage
was 3,059,818 tokens, plus unknown usage for the timeout. The original 13 cached
responses are counted once. All requested models were Sol at medium effort.

Revised PRA had lower coverage than original PRA on all three papers, averaging
16.5% versus 33.1%. On the same two papers with complete single-agent comparisons,
revised PRA averaged 18.8% versus 24.4%, with one tie and one loss. The incomplete
third single-agent comparison is not imputed. Support statistics remain withheld
for eight of nine paper-condition combinations. Human audit is pending.
