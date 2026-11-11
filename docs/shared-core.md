# Shared core contract

Keep the reusable engine inside Paper Workbench initially. A separate benchmark project installs a pinned commit of the `paper-workbench` distribution and imports `paper_workbench_core`. A separate core repository is unnecessary until it needs its own release cycle or independent maintainers.

## Ownership

The core owns source integrity, manuscript block identities, evidence handles, review normalization, bounded tool access, review execution and provenance. The app owns manuscript presentation, author decisions, revision workflows and exports. The benchmark owns datasets, hidden answer keys, candidate selection, controlled conditions, anonymous judging, statistics and rankings.

Neither answer keys nor human evaluation labels belong in `ReviewRequest`. The benchmark must prepare a manuscript-only workspace and keep grading inputs outside it. Core outputs are review artifacts, not scores.

## API version 2

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

The supported workflows are `manuscript-only`, `independent` and `ensemble`. Manuscript-only mode receives extracted text and supplied source images with review tools disabled. Independent and ensemble modes have manuscript tools. The transport supports Claude Code subscription execution with Opus 5.5 and Sonnet 5.5, the default, and Codex subscription execution with Astra, Sol, Terra, Luna, and GPT-5.5. The review policy sets the reasoning effort. The model ID selects the provider. See [the Claude Code provider guide](claude-code-provider.md). Arbitrary models and provider APIs require a separately designed transport extension. Do not silently route unsupported candidates through a different pipeline.

The older PeerReviewAgents graph is a distinct benchmark backend. Its scores must retain a different workflow identifier. Pin the pipeline commit, model settings, source inputs and evidence access when comparing models.

## Packaging boundary

The initial distribution bundles the engine and app resources, but importing the core does not import the web server or require document exporters. Document dependencies are optional. Keeping the existing `paper_workspace` modules avoids a risky physical move while the stable integration surface is established.

Before 1.0, consumers should pin a Git commit rather than follow the main branch. Changes to prompts, schemas, tool access or selection policy require a new benchmark condition, even when Python function signatures remain unchanged.

## Subscription models and usage

`capabilities()["models_by_provider"]` lists the exact request IDs for each
transport: `claude-opus-5-5` and `claude-sonnet-5-5` through Claude Code, and
Astra, Sol, Terra, Luna, and GPT-5.5 through Codex. `capabilities()["provider"]`
names Claude Code as the default transport, and
`capabilities()["default_models"]` names Sonnet 5.5 for Claude Code and Terra
for Codex. Verify that the current account can select a model before a
comparison. No unknown model is substituted.

Codex events do not currently expose the resolved model ID, so requested-model
pinning remains the available identity evidence. Claude Code reports the models
it used, and any model other than the requested one rejects the call.

Each run checks for the provider's subscription login and refuses API keys and
cloud API providers. Observed usage is recorded in the run's `usage.jsonl` and
is not gated, as `capabilities()["usage_policy"]` states. How much a run may
spend is the operator's own setting. Unknown usage must not be interpreted as
zero.

## Versioned review presets

`review_presets()` describes five presets. `review_request_from_preset()`
constructs a validated request. Each completed run preserves its resolved
configuration, configuration hash and both core and engine source hashes.
The preset names are `manuscript-only-single-v1`, `workspace-independent-v1`,
`workspace-ensemble-v1`, `workspace-ensemble-ordinary-v1` and
`workspace-agentic-v1`. Current presets are bounded strategies, not an
arbitrary workflow language or demonstrated multi-provider framework.

Manuscript-only execution denies review tools and external access. Source
images are checked, deduplicated by content and capped at ten without silent
truncation. Missing visual content is recorded. Preparation must establish
whether the delivered packet is scientifically sufficient for a comparison.
