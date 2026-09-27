# Paused after the minimal pilot stopped

The restricted runner exited after an output-validation failure. The one-pair comparison remains incomplete. The unattended automation is paused and the saved STOP requires explicit user authorization before further model inference. Neither the second pair nor a new architecture trial ran.

There were 22 completed inference calls and 1,654,025 observed tokens, including 591,616 cached input tokens, 984,995 uncached input tokens, and 77,414 output tokens. This includes the inherited calls exactly once. There were no failed inference calls or unknown usage. The reduced 2,300,000 observed-token stop was not reached.

On the altered paper, the sequential single editor marked finding B4 as a duplicate of A5, while A5 was marked answered. The frozen validator allows duplicate targets only when retained or unresolved, so it rejected the final response. This is a disposition consistency failure, not a scientific performance result. The raw response and all findings remain unchanged. See `runs/pra-known-errors-v1-r1/offline_failure_diagnosis.json`.

Only the original control was graded. Both systems had five top concerns labeled supported by both automated judges, with no jointly contradicted major concern and no corresponding planted-error allegation. This does not establish an advantage. The altered-paper team review and paired error-detection score are missing. The aggregate zero detections in the incomplete report are placeholders over zero complete pairs, not measured detection failures.

A possible repair is to represent duplicate relationships separately from the final answered or retained disposition, with cycle and evidence checks. No repair has been applied to the frozen run. After a validated offline repair, completing the already-started pair would nominally require eight more Sol calls. Those calls are not running or scheduled. Any continuation requires approval.

The following sections record prior execution history and are superseded by this paused state.

# Current scope: one minimal pilot only

The user explicitly prioritized conserving credits and requires authorization for a larger trial. Only the first already-started original and altered paper pair will finish. The second pair is deferred. Further model inference after this pilot requires approval.

The active entry point is `experiments/pra_minimal_continuation.py`, session 5131. It reuses the frozen r1 workflow and caches, restricts generation and grading to the first pair, and writes an authorization STOP at completion or failure. Its source hash and scope are recorded in `runs/pra-known-errors-v1-r1/minimal_pilot_control.json`. An offline test verified that only those two inputs run and score, followed by the stop.

The reduced observed-token stop is 2,300,000 including inherited usage, with 250,000 reserved for scoring and at most 33 total calls. In-flight calls can overshoot the stop. At restart 15 calls had used 1,134,938 observed tokens. No inference failed and no usage was unknown. The prior broader session 36370 was stopped cleanly at a saved boundary. Do not resume that broader entry point.

The unattended continuation follows the restricted runner and must pause after reporting the pilot. The original two-pair success criterion remains incomplete even if the single pair looks promising. The following sections preserve the earlier execution history.

# Paired known-error experiment status

The experiment is running through the signed-in Codex subscription with Sol at medium reasoning effort. The current runner is `experiments/pra_known_errors_r1/study.py`. Its code, protocol, manuscript inputs, and evaluation annotations are frozen in `runs/pra-known-errors-v1-r1/manifest.json`.

The first two deterministic FLAWS selections each contribute an original and altered manuscript. Both systems receive a complete manuscript, a shared claim map, and the same tools and six-stage allowance. Primary reports have at most five concerns and 900 words. Actual compute will be reported separately.

The team uses three independent investigations, a manuscript defense, a response to that defense, and final adjudication. The sequential single performs the same work orders while retaining all explicit prior notes. Neither receives target annotations during generation. Two anonymous grading passes follow generation.

Seven offline checks passed before launch. They cover bounded calculations, receipt verification, budget stops, preservation and limits of final findings, full mock workflow isolation and debate ordering, and rejection of a paired original false alarm. No effectiveness result is available yet.

The run has a 4,054,672 observed-token stop, including a 400,000-token evaluation reserve. It projects the cost of the second pair from the first before proceeding. In-flight calls can exceed stops. The launch account check showed 75 percent weekly use and zero paid credits. No reset, API billing, or model fallback is authorized.

The active terminal session is 36370. The existing 15-minute unattended continuation follows this run, inspects results, and may prepare a new frozen version for justified improvements within the remaining allowance. It must never duplicate a running process or resume the older experiment halted for benchmark integrity.

This is a development test. A positive screen needs a manual audit and cannot establish statistical superiority from two pairs. Error detection is a separate endpoint from coverage of published human review concerns. Public benchmark exposure and uncertain annotation validity remain limitations.

## Presentation correction

The original execution stopped after seven successful model calls, costing 520,312 observed tokens. The editor returned selected IDs out of ranking order and 83 introductory words against an 80-word limit. This was an output validation failure, with no failed inference or unknown usage.

Execution revision r1 preserves the original root and protocol. It mechanically sorts the same selected IDs by the model ranking and trims excess introductory words. Raw and normalized output are saved separately. No concern text, selection membership, model prompt, scoring rule, or budget changed. Seven exact request caches were inherited with file hashes and lineage. A mocked inference guard verified recovery of the completed 576-word team review without any new model call.

The r1 root already includes the 520,312 inherited tokens. Do not add parent usage again. At restart, 3,534,360 observed tokens remained under the unchanged allowance. The old session 15794 exited successfully after recording the validation failure. The active replacement is session 36370, and the existing unattended continuation now follows it.
