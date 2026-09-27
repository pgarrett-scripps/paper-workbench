# Validation study status

Updated 2026-09-16, recovery revision 5.

## Active execution

The ten-paper development pilot runs through the existing PeerReviewAgents
engine with the Codex provider. Every review, baseline, extraction, and scoring
call selects `gpt-5.6-sol` at medium effort. Codex is authenticated through
ChatGPT. API credential overrides are removed. The last account check showed
zero paid credits. No purchases, resets, or model fallback are authorized.

The development pilot is complete. The process exited with code 0 after saving
40 reviews, ten reference inventories, 80 judgments, and a 150-item unfilled
manual-audit package. All forty scored packets meet the common limits, and all
ten paired-panel hashes match. The heartbeat is paused.

Preliminary mean coverage confirmed by both scoring passes is 21.9% for one-shot,
20.7% for the single agent, 16.5% for full PRA, and 18.0% without debate. These
results do not establish a PRA advantage. Evidence verification failed for 160
of 396 support judgments, and PRA's extracted packets were substantially shorter.
Support statistics are withheld for 24 of 40 paper-condition combinations.

See `docs/validation-pilot-results.md` for the full development report, resource
accounting, and next steps. Human audit, exact version pairing, figure access,
and a corrected frozen evaluation protocol remain necessary before scientific
claims or a larger held-out run.

Active runner:
`/home/ty/Repos/insilico/experiments/peerreview_validation_v5/study.py`

Active runtime root:
`/home/ty/Repos/insilico/runs/peerreview-validation-codex-v5/`

The completed terminal session ID is `51702`. The command was:

```bash
python3 /home/ty/Repos/insilico/experiments/peerreview_validation_v5/study.py pilot
```

The heartbeat `finish-peer-review-codex-pilot` was paused after completion, then
repurposed for the separate three-paper retest described in
`docs/pra-small-retest-status.md`. It must not restart this completed pilot. Any future run must
inspect existing processes before starting anything. Sandboxed process listings
may not show the host process, so an empty sandbox list does not prove it stopped.
Read runtime `status.json`, `generation/`, `evaluation/`, and `report.json` for
current progress. Never edit the frozen runner after model calls have started.

## Evaluation recovery

The original and revisions 2 and 3 stopped on PDF quote-layout mismatches.
Their runners, manuscripts, model answers, and logs remain frozen in separate
roots. The four completed reviews and scoring responses were copied forward
with source hashes in each root's `recovery_provenance.json`. Recovery has not
rerun completed reviews or requested replacement model answers.

Revision 4 permits exact whitespace matching, word-internal hyphens at actual
source line breaks, and omission of the exact repeated ICLR 2025 header paired
with a page number. It rejects paraphrases and arbitrary lexical changes.
All 23 nonempty evidence quotes already generated match under these rules.
The model, prompts, and input corpus are unchanged. The validation policy changed.

Any future unmatched quote is retained and flagged for human audit. It is never
accepted as verified evidence. Support and false-major statistics for an affected
condition are null, with explicit quote-failure counts. Human-concern coverage
is a separate provisional metric. The manual audit includes a complete unmatched
quote queue separately from its random sample. This permits the development
pipeline to finish without concealing evaluator failures.

Twenty-three offline tests pass, including source-quote rejection, exact PDF layout
cases, and withholding support statistics when an evaluator supplies an unmatched
quote. Existing judgments are revalidated without new model inference.

## Execution and provenance checks

- Live Codex structured output and manuscript-only reading tools succeeded.
- Child calls disable shell, browser, apps, installed plugins, and delegation.
  The outer runner executes the frozen PRA specialist and editor prompts.
- The single agent can read and search only its staged manuscript through MCP.
- Full and no-debate PRA reuse identical specialist reports and audits.
- Original first-paper generation used 595,233 observed tokens across 20 calls,
  including concern extraction. This excludes reference extraction and scoring.
  It counts the shared panel once in actual consumption.
- The CLI reports requested model selection but not resolved backend identity.
- Public dataset URLs, forum URLs, and hashes are in `public_data_provenance.json`.
  Automatic approval review allowed execution after that provenance was verified.
  The private Nature Methods correspondence is not an input.

## Scientific limitations

These historical candidates have prior development exposure. Exact original
submission and first-review versions remain unverified. The extracted text does
not establish figure access. Development outputs cannot support held-out claims.

Two blinded scoring prompts use the same model and can share errors. Actual
human ratings are still needed. The per-condition token stop can overshoot by
one call and does not establish matched computational budgets.

The next scientific milestone is verified manuscript-review pairing, scorer
audit, and budget calibration, followed by a separately frozen held-out protocol
and corpus. No scientific validation result or completed paper is claimed yet.

## Output-length recovery

The original baseline path enforced a 900-word raw-review cap in addition to the
extracted packet cap. PRA enforced only the extracted packet cap, and its raw
letters exceeded 900 words. Revision 5 removes this asymmetric extra gate.
Every scored packet must contain at most five concerns and 900 total quoted
words. Raw review lengths and requested-limit deviations are reported for every
condition. This is not a raw-output-length-matched experiment.

The stopped 902-word baseline and all completed reviews and scoring answers are
reused. The model, prompts, and corpus remain unchanged, but output-validation
policy changed during development. Prior roots remain frozen. The active root's
`recovery_provenance.json` records the change and copied artifact hashes.
The original process exited with code 2 before the new process was launched.
ChatGPT login and zero paid credits were reverified. The monitor points to the
new session and runner. No review generation was repeated for recovery.
