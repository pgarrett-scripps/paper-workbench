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

The current supported workflows are `independent` and `ensemble`. Both have manuscript tools. Independent is not a tool-free baseline. The current transport supports only Codex subscription execution with Terra and Sol at medium effort. Arbitrary models and provider APIs require a separately designed transport extension. Do not silently route unsupported candidates through a different pipeline.

The older PeerReviewAgents graph is a distinct benchmark backend. Its scores must retain a different workflow identifier. Pin the pipeline commit, model settings, source inputs and evidence access when comparing models.

## Packaging boundary

The initial distribution bundles the engine and app resources, but importing the core does not import the web server or require document exporters. Document dependencies are optional. Keeping the existing `paper_workspace` modules avoids a risky physical move while the stable integration surface is established.

Before 1.0, consumers should pin a Git commit rather than follow the main branch. Changes to prompts, schemas, tool access or selection policy require a new benchmark condition, even when Python function signatures remain unchanged.
