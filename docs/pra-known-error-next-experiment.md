# Next experiment: investigate documented errors with paired controls

The minimal pilot stopped on output validation and all inference is now paused.
Further inference, the second pair, and any larger trial require user approval.
See `pra-known-error-status.md`.
The design below records the earlier two-pair plan, which is now deferred.

The objective remains a materially better review system. This is the next bounded
development test after the reference applicability problem described in
`docs/pra-benchmark-integrity.md`. It is not a result or a replacement analysis of
the old human-review benchmark.

## Prepared input evidence

Three cases were selected deterministically from the 48-paper OpenAI general-CS
extension of [FLAWS](https://huggingface.co/datasets/xasayi/FLAWS), at dataset revision
`a20a57860ed4afc8a046a73abab6bd1222068762`. Selection used the first three paper IDs
after sorting by SHA-256 of `20260920:` plus the ID. No system outputs were used.

The selected cases are `2406.10461v2`, `2506.02761v2`, and `2407.08422v2`. Each now
has its altered PDF, original and altered LaTeX, error and location annotations,
and the version-pinned original PDF retrieved from arXiv. All eight original text
blocks occur in the original LaTeX and not in the altered LaTeX. All eight modified
blocks occur in the altered LaTeX and not in the original. Relevant changed PDF
pages were rendered and visually inspected. This establishes edit presence and
readability, not the scientific correctness of every benchmark annotation.

Artifacts are under `runs/pra-known-error-preparation-v1`. Key files are
`sample_selection.json`, `download_manifest.json`, `original_downloads.json`, and
`input_feasibility.json`. ZIP ranges were checked against entry names, sizes, and
CRCs. The download helper is `experiments/pra_known_error_preparation/fetch_sample.py`.
The frozen paired experiment is now running at `runs/pra-known-errors-v1-r1`.
Its implementation is `experiments/pra_known_errors_r1`. Seven offline checks passed
before launch. See `docs/pra-known-error-status.md` for current operational status.

## Required next implementation

Create a separate runner and frozen root. Reuse the investigation architecture
from `experiments/pra_claim_investigation`, preserving that stopped version unchanged.
Use shared JSON Schema definitions for source IDs. Repeating every evidence enum
in each case object unnecessarily enlarges the structured response schema.

Calibrate the new run from the recorded four-call trial. Its three investigations
alone used 755,412 observed tokens, nearly the original complete-arm allowance.
Reduce redundant manuscript reads and tool round trips before launching another
large batch. Give both arms the same efficient tool policy. Preserve a complete
initial reading, allow targeted rereads, and provide bounded calculations with
validated execution receipts. Equal caps are not proof of equal actual compute.

For the first comparison use the first two selected paper pairs in fixed order.
Keep the third in reserve and do not call it an untouched scientific holdout.
The curator has inspected its annotation for input feasibility.

Both the investigation team and the sequential single controller must review both
the original and altered version in isolated sessions. Neither sees the other
version, error annotations, file names revealing the condition, or benchmark
judgments. All prompts ask for an ordinary critical review without asserting
that a planted error exists. Use the same final five-concern and 900-word allowance.
Retain complete findings separately, with no inference that more slots prove a win.

Provide the same figure access to both arms if implemented. If only text is exposed,
record that limitation and audit whether the target depends on unavailable visual
evidence or external sources. Do not silently feed the target passage to an agent
or discard a missed case after seeing performance. An annotation can be uncertain
even when the edit is real. Keep such uncertainty visible.

Two blinded scoring passes assess every final concern against its manuscript and
the documented error. A hit must identify the actual defect, not merely criticize
the paper generally or quote a changed passage. On the paired original, check
whether the system makes the corresponding inserted-error allegation despite its
absence. Originals are not otherwise assumed error-free. Also assess all final
concerns for evidence support and contradicted major criticism.

Report error detection, the paired allegation check, and total supported concerns
separately. A promising engineering result requires more correctly detected errors
for the team without additional corresponding allegations on controls or additional
validated major false criticisms. Two pairs cannot establish statistical significance.
Audit disagreements before any claim of superiority. Keep all outcomes and costs.

At six model stages per arm plus a shared map and two scoring passes per input,
the first two pairs require 60 new calls. Before freezing, verify that the efficient
tool and context policy makes this feasible within the remaining 4,054,672 observed
tokens from the original five-million allowance. Include any retry and grading
costs. Do not launch more work than the remaining budget can plausibly finish.
If it cannot fit, reduce duplicated processing or use a clearly labeled first-pair
instrumentation test before spending on the full comparison. Do not weaken the
baseline or change success criteria after seeing outputs.

All inference remains Sol medium through the subscription. Verify login and zero
paid credits at launch. No API-key billing, paid credits, purchases, resets, or
model fallback. Freeze before inference and preserve old roots and failures.
