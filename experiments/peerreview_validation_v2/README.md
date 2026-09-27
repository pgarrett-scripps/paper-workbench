# Codex subscription pilot

The active runner uses the existing PeerReviewAgents engine with its Codex
subscription provider. Its specialist, audit, debate, and editor prompts come
from a frozen copy of the plugin engine. The production plugin is unchanged.

Every generation, extraction, and scoring call explicitly selects `gpt-5.6-sol`
at medium effort through the authenticated Codex CLI. The CLI event stream does
not report the resolved backend model, so logs distinguish requested identity
from observed identity. There is no automatic model or provider fallback.
The previous Claude protocol is preserved in `protocol.claude.json`.

## Scope

Ten seeded candidates come from the historical 20-paper local OpenReview corpus.
They have prior development exposure and unverified original-version pairing.
Their extracted text does not establish figure access. They are development
execution checks and cannot support held-out scientific claims.

The four conditions are one-shot, single-agent with local reading tools,
full PRA, and PRA without debate. Both PRA conditions reuse the identical saved
panel. The no-debate editor cannot receive downstream debate or decision text.
Standalone no-debate cost includes the reused panel's original inference.

Single-agent reading tools expose only the staged manuscript through a small
local MCP server. They accept line ranges or literal search text, never paths.
Child Codex sessions disable shell, browser, connectors, installed plugins,
and delegation. Other calls have no manuscript tools. Disabling child plugin
loading prevents recursion while the outer runner executes the PRA engine.
The traces record tool use for inspection before confirmatory work.

## Run

```bash
python3 experiments/peerreview_validation_v2/study.py prepare
python3 experiments/peerreview_validation_v2/study.py preflight
python3 experiments/peerreview_validation_v2/study.py pilot
```

Preparation stores the pilot under `runs/peerreview-validation-codex-v2/`, separate
from the earlier Claude preparation. Preflight reports unverified historical
pairing even when authentication works. The pilot command explicitly marks
execution as development, checks one paper through generation and scoring,
then proceeds through the remaining candidates and exports the manual audit.

Codex must be signed in through ChatGPT. Before execution, the run directory
must contain `billing_confirmation.json` recording `no_paid_credits_verified`,
the verification time, and source of the account credit check. This is an
observation of account status, not a billing-setting change. The runner strips
API credential overrides, requires ChatGPT login, makes no credit purchases,
and stops when the CLI reports failure or a usage limit. Refresh the account
check before resuming if billing settings have changed.

For individual stages:

```bash
python3 experiments/peerreview_validation_v2/study.py run --limit 1 --development-smoke
python3 experiments/peerreview_validation_v2/study.py score --limit 1 --development-smoke
python3 experiments/peerreview_validation_v2/study.py summarize
python3 experiments/peerreview_validation_v2/study.py audit
```

Commands reuse successful responses. Failed attempts are preserved and block
blind retries. Changed protocol or runner files require a separate study root
once model calls have started. The runner does not schedule its own wakeups.

## Provenance and interpretation

Preparation verifies corpus hashes and snapshots the PRA source. Protocol,
runner, prompts, manuscript, human review, and engine hashes are checked before
execution. Runtime outputs stay in the ignored runs directory.

Structured answers, CLI events, tool traces, errors, usage, and timing are saved.
Cached input is a subset of Codex input tokens and is not added a second time.
The per-condition token stop checks completed calls and can overshoot by one
call. It is a usage guard, not proof of matched computational budgets.

Two blinded GPT-5.6 Sol scoring passes vary order and instructions. They are
correlated sensitivity checks. Exact source and manuscript quote checks are
deterministic. The exported human audit has empty ratings for an actual assessor.

```bash
/home/ty/Repos/PeerReviewAgents/.venv/bin/python -m unittest discover -s experiments/peerreview_validation -p 'test_*.py' -v
```

The offline tests consume no model usage. Before a scientific study, verify
original versions and figure access, audit the scorer, calibrate resource
allowances, and freeze a separate held-out corpus and protocol.

## Recovery revision

The first pilot completed all four reviews for its first paper. Scoring stopped
when a judge joined PDF line-end hyphenation in three otherwise matching quotes.
Revision 2 accepts either whitespace-normalized exact matching or exact matching
after removing only a letter-to-letter hyphen at a newline. It never accepts
paraphrases, arbitrary character edits, or ordinary within-line hyphen removal.
The original text, failed validation, and CLI answers remain in the first root.
Newly validated judgments record the matching mode. Completed generation and
scoring artifacts are copied with provenance and reused without fresh inference.
The model, prompts, corpus, and experimental protocol remain identical.
