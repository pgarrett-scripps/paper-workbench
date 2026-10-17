# Paper Workbench

An evidence-linked workspace for manuscript review and revision. This private research prototype imports manuscripts, investigates claims, runs configurable independent reviewers and debate, and presents located comments and proposed edits.

The project was extracted from In Silico. It is a successor implementation to the original PeerReviewAgents workflow, with different source handling, review orchestration and revision tools. The original projects remain separate.

## Team handoff

Start with [the team handoff](HANDOFF.md) for the current architecture, setup, exact stopping point and next engineering task. The companion paper repository contains the study evidence and publication blockers.

## Install

Requires Python 3.11 or newer. From this checkout:

```bash
python -m pip install -e '.[documents,test]'
paper-workbench --help
```

Poppler is required for PDF page inspection. Word and PDF export can additionally require LibreOffice or Typst. Paper Scaffold integrations accept an explicit checkout path. Core source verification and review validation do not require those renderers.

```bash
paper-workbench import manuscript.pdf workspaces/example --xml manuscript.xml
paper-workbench serve workspaces/example --port 38744
```

Model execution is an explicit separate action. The engine supports two subscription transports at medium effort. Codex sessions run Astra, Sol, Terra, Luna, or GPT-5.5. Claude Code sessions run Sonnet 5.5 by default, or Opus 5.5, on a Claude subscription with no API key. See [the Claude Code provider guide](docs/claude-code-provider.md). Launches require a fresh accepted billing record for the selected provider, including the current Codex `included-allowance-v1` policy based on authoritative usage snapshots. These conservative checks fail closed, but they are not provider-side hard spending caps. Importing the package, inspecting a workspace or running offline tests does not start model inference.

## Shared core

One repository and one installable distribution currently contain both the app and a headless public API:

- `paper_workbench_core`: the versioned integration surface for benchmark packages and other clients.
- `paper_workspace`: the existing engine, source tools, app, revision workflow and exports. Existing imports remain valid.
- `experiments`: archived development study code, excluded from the installed distribution.
- `docs`: methods, limitations and positive and negative development findings.

The core delegates to the same engine used by the app. It does not duplicate prompts or implement a second review pipeline. See [the shared-core contract](docs/shared-core.md).

## Validation status

This is a research prototype, not a validated claim of superiority over a single agent or human reviewers. In the latest focused-evidence comparison, both reviews scored 8/10 and the judge narrowly preferred the saved review. See [the full result](docs/pra-focused-debate-results.md).

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

Tests use synthetic or local fixtures. Some optional rendering checks require local document tooling. Historical experiment scripts reference local study inputs and are not portable benchmark commands.

## Provenance

[The extraction manifest](migration/source-snapshot.json) records hashes of the imported source snapshot. The first commit preserves that snapshot before packaging changes. Raw manuscripts, model responses, caches and credentials are excluded from Git. Existing local study runs remain preserved separately. See [migration details](docs/migration.md).

The source licenses and attribution are preserved in [LICENSE](LICENSE). The repository is private. No package has been published to a registry.
