# Shared core contract

Keep the reusable engine inside Paper Workbench initially. A separate benchmark project installs a pinned commit of the `paper-workbench` distribution and imports `paper_workbench_core`. A separate core repository is unnecessary until it needs its own release cycle or independent maintainers.

## Ownership

The core owns source integrity, manuscript block identities, evidence handles, review normalization, bounded tool access, review execution and provenance. The app owns manuscript presentation, author decisions, revision workflows and exports. The benchmark owns datasets, hidden answer keys, candidate selection, controlled conditions, anonymous judging, statistics and rankings.

Neither answer keys nor human evaluation labels belong in `ReviewRequest`. The benchmark must prepare a manuscript-only workspace and keep grading inputs outside it. Core outputs are review artifacts, not scores.

## API version 1

```python
from pathlib import Path
from paper_workbench_core import (
    capabilities, load_manuscript, evidence_registry,
    validate_review, ReviewRequest, run_review,
)

paper = load_manuscript(Path("workspaces/example"))
registry = evidence_registry(Path("workspaces/example"))
supported = capabilities()

request = ReviewRequest(
    workspace=Path("workspaces/example"),
    output=Path("runs/example-terra"),
    billing_confirmation=Path("local-billing-verification.json"),
    literature_cutoff="2026-09-25",
    workflow="ensemble",
    model="gpt-5.6-terra",
    reviewers=2,
)
# Explicit inference, only after the benchmark authorizes this run:
# artifact = run_review(request)
```

`load_manuscript`, `evidence_registry`, `validate_review`, `capabilities` and request construction do not call a model or start the web server. `validate_review` normalizes source references and proposed edits. It does not determine whether a scientific concern is true.

`run_review` uses the existing engine. It rejects existing output directories, unsupported models and unsupported workflows. It returns a `paper-workbench-run-v1` artifact containing the editor package, requested model, workflow, manuscript identity, engine file hashes and observed usage. Unknown usage and execution failures remain errors with underlying run files preserved. Token budgets are launch guards, not hard within-session caps. Independent mode retains its existing per-session guard.

The supported workflows are `manuscript-only`, `independent` and `ensemble`. Manuscript-only mode receives extracted text and supplied source images with review tools disabled. Independent and ensemble modes have manuscript tools. The transport supports Codex subscription execution with Astra, Sol, Terra, Luna, and GPT-5.5, and Claude Code subscription execution with Opus 5.5 and Sonnet 5.5, all at medium effort. The model ID selects the provider. See [the Claude Code provider guide](claude-code-provider.md). Arbitrary models and provider APIs require a separately designed transport extension. Do not silently route unsupported candidates through a different pipeline.

The older PeerReviewAgents graph is a distinct benchmark backend. Its scores must retain a different workflow identifier. Pin the pipeline commit, model settings, source inputs and evidence access when comparing models.

## Packaging boundary

The initial distribution bundles the engine and app resources, but importing the core does not import the web server or require document exporters. Document dependencies are optional. Keeping the existing `paper_workspace` modules avoids a risky physical move while the stable integration surface is established.

Before 1.0, consumers should pin a Git commit rather than follow the main branch. Changes to prompts, schemas, tool access or selection policy require a new benchmark condition, even when Python function signatures remain unchanged.

## Subscription model comparisons and structured calls

Version 0.1.1 advertises five explicitly supported Codex subscription models:
Astra, Sol, Terra, Luna, and GPT-5.5. Check `capabilities()["models"]` for their
exact request IDs, then verify the current account can select those models.
Medium reasoning remains fixed. No unknown model is substituted or retried.

`StructuredRequest` and `run_structured` expose one tool-free structured call
through the same subscription transport. External benchmarks own grading
prompts and JSON schemas. The request contains `output`, `billing_confirmation`,
`model`, `prompt`, and `schema`, with optional positive `token_budget` and
`timeout_seconds`. The output directory must be new. Authentication and recent
zero-paid-credit verification are required. No manuscript tools are enabled.

The returned artifact preserves the requested model, structured value, and
observed usage. `usage_summary(output)` also reads durable receipts for failed
or interrupted workflows. A usage summary is not proof of successful inference.
Unknown usage must not be interpreted as zero. Codex events do not currently
expose the resolved model ID, so requested-model pinning remains the available
identity evidence. Claude Code reports the models it used, and any model other
than the requested one rejects the call.

Version 0.1.8 adds `claude-opus-5-5` and `claude-sonnet-5-5` through Claude
Code. `capabilities()["models_by_provider"]` lists the IDs for each transport, and
`capabilities()["default_models"]` names Terra for Codex and Sonnet 5.5 for Claude.
The `provider` key still names the default Codex transport for older clients.
A Claude run needs a `claude-subscription-v1` billing record from
`paper-workbench confirm-billing`, and neither provider accepts the other's
record.


## Versioned review presets

`review_presets()` describes three presets. `review_request_from_preset()`
constructs a validated request. Each completed run preserves its resolved
configuration, configuration hash and both core and engine source hashes.
The preset names are `manuscript-only-single-v1`, `workspace-independent-v1`
and `workspace-ensemble-v1`. Current presets are bounded strategies, not an
arbitrary workflow language or demonstrated multi-provider framework.

Manuscript-only execution denies review tools and external access. Source
images are checked, deduplicated by content and capped at ten without silent
truncation. Missing visual content is recorded. Preparation must establish
whether the delivered packet is scientifically sufficient for a comparison.
`StructuredRequest.source_images` gives external judges the same image access.

## Included allowance execution policy

The legacy recent zero-credit verification remains supported. Accounts with
available credits can instead supply an `included-allowance-v1` record from the
Codex app usage tool. It must be less than five minutes old, report Pro or Plus
included limits, show every available window below 25 percent used, and report
no reached spending or usage limit. Missing or invalid evidence fails closed.
The record does not assert that the credit balance is zero.

The coordinator refreshes this evidence before every workflow, maintains a
separate cumulative study budget and checks usage between workflows. This is
a conservative launch guard, not a provider-side hard spending cap. A running
call may exceed its launch estimate. This policy never purchases credits,
uses a reset, enables API billing or changes account settings.

Pricing behavior is documented at https://learn.chatgpt.com/docs/pricing.
Account-specific included allowance comes from the current usage snapshot,
not from converting token counts to estimated subscription dollars.
