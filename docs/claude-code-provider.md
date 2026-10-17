# Claude Code subscription provider

Core 0.1.8 can run every model workflow through Claude Code on a Claude subscription. This covers the review modes (`ensemble`, `independent`, `plain`, `workspace`, `panel` and `self-revision`), `investigate`, `run_review` and `run_structured`. No API key is used. Calls draw on the subscription's included usage, the same way Codex runs draw on a ChatGPT plan.

Claude Code runs are a separate condition. They do not reproduce the Codex study results, and comparisons must label the provider and model.

## Requirements

- The Claude Code CLI, installed and on `PATH`. Development used version 2.1.299. Each call receipt records the version that ran.
- A Claude subscription login (Pro, Max, Team or Enterprise). Run `claude auth login`, then check that `claude auth status` reports `"authMethod": "claude.ai"`.
- Paid extra usage turned off in Claude settings, so a run that reaches its included limit stops instead of buying more usage.

## Models

| Model ID | Notes |
| --- | --- |
| `claude-sonnet-5-5` | Default for `--provider claude-code`. Lighter on included usage |
| `claude-opus-5-5` | Stronger, but its safeguards can refuse life-science manuscripts |

Sonnet is the default because Opus 5.5 refused a biology manuscript at the first request (see Limitations). The default is an exact model ID, not the moving `sonnet` alias, so every receipt names the model that ran. Moving to a newer Sonnet is a one-line change to `DEFAULT_MODELS` in `paper_workspace/models.py` and counts as a new condition. Reasoning effort stays at medium, as for Codex. Fable is not offered because some plans bill it from paid usage credits. Unknown models are rejected and never substituted.

## Run a review

```bash
paper-workbench confirm-billing billing.json --provider claude-code --extra-usage-disabled
paper-workbench review workspaces/example runs/example-claude \
  --provider claude-code --billing-confirmation billing.json --literature-cutoff 2026-01-01
paper-workbench report runs/example-claude
```

The last command writes `REVIEW.md` and `REVIEW.txt` to the run folder without any model call.

Add `--model claude-opus-5-5` to choose Opus. `investigate` accepts the same two options. A model from the other provider is rejected.

`confirm-billing` reads `claude auth status`, refuses anything other than a subscription login, and writes a record valid for 24 hours. The flag is your statement that extra usage is off. Refresh the record each day you run reviews. A Codex billing record cannot start a Claude run, and a Claude record cannot start a Codex run.

The core API selects the provider from the model ID. `capabilities()["default_models"]` names each provider's default:

```python
ReviewRequest(workspace=..., output=..., billing_confirmation=Path("billing.json"),
              literature_cutoff="2026-01-01", model=capabilities()["default_models"]["claude-code"])
```

## What each call enforces

- The process environment drops `ANTHROPIC_*` variables, so an API key cannot be used.
- Claude Code starts in print mode with `--restricted`, no built-in tools, no user, project or local settings files, no skills and no MCP servers other than the manuscript tool server. Organization-managed settings still apply.
- Switches in the CLI's environment turn off CLAUDE.md files, auto memory, attachments and model fallback. These switches are internal to Claude Code and can change between versions.
- The default Claude Code system prompt is replaced by a fixed three-sentence reviewer instruction. It is part of each request identity.
- The prompt and source images go in as one message, with the images in their stated order. Images must be PNG, JPEG, GIF or WebP under the 5 MB Claude limit.
- Manuscript tools use the same server, tool profile and allowances as Codex. Each approved tool is listed explicitly and anything else is denied.

The engine reads the event stream while the call runs. It stops the call immediately if Claude Code reports an API key session, tools outside the manuscript server, or paid extra usage that is enabled or in use. After the call, the engine rejects the result when:

- no subscription usage limits were reported (API key sessions never report them)
- a manuscript tool failed or was denied
- any model other than the requested one appears in the usage report
- the call ended without a structured answer or without usage

Every rejected call keeps its receipt. Unknown usage blocks further calls in that output directory, as it does for Codex.

## Receipts and usage

Call receipts sit beside the Codex ones in `calls/`, with the full event stream in `<request>.events.jsonl`. Each receipt records the requested and observed models, the Claude Code version, the subscription limit events and the observed tokens. A completed call can be recovered from its saved events without another inference.

Observed tokens count every input token Claude processes, including cache reads, plus output tokens. Like the Codex counts, they serve as launch guards and do not measure subscription charges.

## Limitations

- The extra usage confirmation is an operator statement. The live checks enforce it, but one model request can complete before a paid usage signal arrives.
- Claude Code adds a small amount of its own context, such as the date and platform. The engine does not control it.
- Claude Code can retry a failed network request internally, similar to Codex reconnects. The engine never retries a call.
- Response schemas travel on the command line and are limited to 120,000 characters. Current schemas are well below that.
- Opus 5.5 safeguards can refuse life-science manuscripts. Claude Code then reports a failed call with a `[bio]` detail, and the engine stops without switching models. Rewording or trimming a manuscript to get past a refusal is not supported. Choose another model in a new output directory.

## Verification status

Offline tests drive a scripted Claude Code executable through every guard above. On 15 October 2026, live calls on an Enterprise subscription passed through this transport:

- Opus 5.5 with the manuscript tool server and an attached page image
- Sonnet 5.5 with the current discovery schema and the current synthesis schema, including the component ledger constraints

On 17 October 2026, an ensemble review of a Nature Communications preprint on PARP15 (`A-08` in the PeerReviewAgents benchmark corpus) was attempted with each model. Opus 5.5 refused the first request with a `[bio]` flag after processing 141,041 input tokens. Sonnet 5.5 accepted the same manuscript and began using the manuscript tools, but the operator stopped the run before it finished. A complete review of a manuscript has not yet been run with Claude Code.
