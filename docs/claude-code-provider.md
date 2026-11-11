# Claude Code subscription provider

Claude Code on a Claude subscription is the default transport for every model workflow. This covers the review modes (`ensemble`, `independent`, `plain`, `workspace`, `panel` and `self-revision`), `investigate` and `run_review`. No API key is used. Calls draw on the subscription's included usage, the same way Codex runs draw on a ChatGPT plan.

Claude Code runs are a separate condition. They do not reproduce the Codex study results, and comparisons must label the provider and model.

## Requirements

- The Claude Code CLI, installed and on `PATH`. Development used version 2.1.299. Each call receipt records the version that ran.
- A Claude subscription login (Pro, Max, Team or Enterprise). Run `claude auth login`, then check that `claude auth status` reports `"authMethod": "claude.ai"`.
- Your choice of paid extra usage in Claude settings. The engine records usage and does not gate on it, so turn extra usage off if a run that reaches its included limit should stop instead of buying more.

## Models

| Model ID | Notes |
| --- | --- |
| `claude-sonnet-5-5` | Default model. Lighter on included usage |
| `claude-opus-5-5` | Stronger, but its safeguards can refuse life-science manuscripts |

Sonnet is the default because Opus 5.5 refused a biology manuscript at the first request (see Limitations). The default is an exact model ID, not the moving `sonnet` alias, so every receipt names the model that ran. Moving to a newer Sonnet is a one-line change to `DEFAULT_MODELS` in `peerreviewagents/engine/models.py` and counts as a new condition. The review policy sets the reasoning effort, as for Codex. Fable is not offered because some plans bill it from paid usage credits. Unknown models are rejected and never substituted.

## Run a review

```bash
paper-workbench review workspaces/example runs/example-claude
paper-workbench report runs/example-claude
```

The last command writes `REVIEW.md` and `REVIEW.txt` to the run folder without any model call. `--literature-cutoff YYYY-MM-DD` sets the latest eligible publication date and defaults to today.

Add `--model claude-opus-5-5` to choose Opus. `investigate` accepts the same `--provider` and `--model` options. A model from the other provider is rejected.

Before each run the engine reads `claude auth status` and refuses anything other than a subscription login, or a session that routes through a cloud API provider.

The core API selects the provider from the model ID. `capabilities()["default_models"]` names each provider's default:

```python
ReviewRequest(workspace=..., output=..., literature_cutoff="2026-01-01",
              model=capabilities()["default_models"]["claude-code"])
```

## What each call enforces

- The process environment drops `ANTHROPIC_*` variables, so an API key cannot be used.
- Claude Code starts in print mode with `--restricted`, no built-in tools, no user, project or local settings files, no skills and no MCP servers other than the manuscript tool server. Organization-managed settings still apply.
- Switches in the CLI's environment turn off CLAUDE.md files, auto memory, attachments and model fallback. These switches are internal to Claude Code and can change between versions.
- The default Claude Code system prompt is replaced by a fixed three-sentence reviewer instruction. It is part of each request identity.
- Regular expressions in the response schema are rewritten for Claude Code's JavaScript validator. Python escapes such as `\-` that JavaScript rejects are dropped, so the patterns match exactly the same strings. Large manuscripts, with more than 950 sentence handles, need this. Request identities keep the original schema.
- The prompt and source images go in as one message, with the images in their stated order. Images must be PNG, JPEG, GIF or WebP under the 5 MB Claude limit.
- Manuscript tools use the same server, tool profile and allowances as Codex. Each approved tool is listed explicitly and anything else is denied.

The engine reads the event stream while the call runs. It rejects the call if Claude Code reports an API key session, tools outside the manuscript server, or a manuscript server that did not connect. After the call, the engine also rejects the result when:

- no subscription usage limits were reported (API key sessions never report them)
- a manuscript tool failed or was denied
- any model other than the requested one appears in the usage report
- the call ended without a structured answer or without usage

Every rejected call keeps its receipt. Unknown usage blocks further calls in that output directory, as it does for Codex.

## Receipts and usage

Call receipts sit beside the Codex ones in `calls/`, with the full event stream in `<request>.events.jsonl`. Each receipt records the requested and observed models, the Claude Code version, the subscription limit events and the observed tokens. A completed call can be recovered from its saved events without another inference.

Observed tokens count every input token Claude processes, including cache reads, plus output tokens. Like the Codex counts, they serve as launch guards and do not measure subscription charges.

## Limitations

- The engine does not limit paid extra usage. That is the operator's Claude setting.
- Claude Code adds a small amount of its own context, such as the date and platform. The engine does not control it.
- Claude Code can retry a failed network request internally, similar to Codex reconnects. The engine retries a call only when the review policy allows one bounded retry and the session crashed before it produced a result.
- Response schemas travel on the command line and are limited to 120,000 characters. Current schemas are well below that.
- Opus 5.5 safeguards can refuse life-science manuscripts. Claude Code then reports a failed call with a `[bio]` detail, and the engine stops without switching models. Rewording or trimming a manuscript to get past a refusal is not supported. Choose another model in a new output directory.
- Sonnet 5.5 sometimes marks a supported clarification as omitted when it does not fit the final five findings. The synthesis rules require such an issue to stay as a supporting secondary concern with wording for the authors, so final validation rejects the run. This happened for 3 of 29 corpus papers on the first attempt. The engine does not retry, so start a fresh run in a new output directory.

## Verification status

Offline tests drive a scripted Claude Code executable through every guard above. On 15 October 2026, live calls on an Enterprise subscription passed through this transport:

- Opus 5.5 with the manuscript tool server and an attached page image
- Sonnet 5.5 with the current discovery schema and the current synthesis schema, including the component ledger constraints

On 17 October 2026, an ensemble review of a Nature Communications preprint on PARP15 (`A-08` in the PeerReviewAgents benchmark corpus) was attempted with each model. Opus 5.5 refused the first request with a `[bio]` flag after processing 141,041 input tokens. Sonnet 5.5 accepted the same manuscript. The operator stopped a first Sonnet run, and a second one completed with 402,207 observed tokens and a complete component ledger.

On 24 October 2026, Sonnet 5.5 ensemble reviews ran on the rest of that corpus, which holds 10 Nature Communications, 10 PLOS and 10 Nature preprints. One manuscript was excluded because it exceeds the 35,000-word review limit. The other 29 now each have a complete review:

- Each review made three calls (two independent reviewers and one debate synthesis) at medium effort.
- Every call ran on the subscription with no API key, and paid extra usage stayed rejected throughout.
- Every synthesis passed final validation with a complete component ledger and four or five final findings.
- A completed review used between 0.37 and 1.53 million observed tokens, 18.2 million across all 29, and most took 3 to 5 minutes.
- Two large manuscripts first failed before any model call because Claude Code rejected the schema's regular expressions. The pattern conversion described above fixed both.
- Three syntheses failed final validation on the first attempt because a supported clarification was omitted (see Limitations). A fresh run of each paper passed.

On 27 October 2026, the review input limit was raised from 35,000 to 50,000 extracted words, including supplements. The excluded manuscript (`C-04`, 48,090 words) was then reviewed with the same settings. Its review made three calls, used 1.62 million observed tokens and took 3 minutes, so all 30 manuscripts now have a complete review.
