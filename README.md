# Paper Workbench

An evidence-linked workspace for manuscript review and revision. This private research prototype imports manuscripts, investigates claims, runs configurable independent reviewers and debate, and presents located comments and proposed edits.

The project was extracted from In Silico. Its review engine now lives in PeerReviewAgents as `peerreviewagents.engine` (0.8.0). This repository is the workspace and revision app built on that engine.

## Team handoff

Start with [the team handoff](HANDOFF.md) for the current architecture, setup, exact stopping point and next engineering task. The companion paper repository contains the study evidence and publication blockers.

## Install

Requires Python 3.11 or newer. The app needs `peerreviewagents` 0.8.0 or newer, which is not on PyPI yet. Install the engine from its main branch first, then this app:

```bash
python -m pip install 'peerreviewagents @ git+https://github.com/pgarrett-scripps/PeerReviewAgents@main'
python -m pip install -e '.[documents,test]'
paper-workbench --help
```

A PeerReviewAgents checkout works too, with `python -m pip install -e ../PeerReviewAgents` as the first command.

Poppler is required for PDF page inspection. Word and PDF export can additionally require LibreOffice or Typst. Paper Scaffold integrations accept an explicit checkout path. Core source verification and review validation do not require those renderers.

```bash
paper-workbench import manuscript.pdf workspaces/example --xml manuscript.xml
paper-workbench serve workspaces/example --port 38744
```

Model execution is an explicit separate action. The engine supports two subscription transports. Claude Code is the default and runs Sonnet 5.5, or Opus 5.5, on a Claude subscription with no API key. Codex sessions run Astra, Sol, Terra, Luna, or GPT-5.5 on a ChatGPT subscription. The review policy sets the reasoning effort. See [the Claude Code provider guide](docs/claude-code-provider.md). Each run checks that it uses the subscription login and refuses API keys and cloud API providers. Usage is recorded in the run's `usage.jsonl`, and how much a run may spend is the operator's own setting. Importing the package, inspecting a workspace or running offline tests does not start model inference. `paper-workbench report RUN` turns a saved run into readable `REVIEW.md` and `REVIEW.txt` files.

## Engine and app

Version 0.2.0 splits the project into two packages:

- `peerreviewagents.engine` (in PeerReviewAgents): ingest, reviewers, synthesis, investigation tools, domain packs and the headless API.
- `paper_workspace` (here): the viewer server, revisions, Paper Scaffold import and export, and Word review copies. This code imports the engine directly.
- Engine module names under `paper_workspace`, and all of `paper_workbench_core`, are aliases for the engine modules, so imports and test patches through those names reach the engine.
- `paper-workbench` keeps the app commands. Engine commands such as `import`, `verify`, `add-review`, `review` and `report` pass through to the engine, which also serves them as `peerreview <command>`.
- `experiments` and `docs` hold archived study code and development findings, as before.

The headless API keeps its name, and its version is `paper-workbench-core-v2`. New clients should import `peerreviewagents.engine.api`. See [the shared-core contract](docs/shared-core.md) and [the split map](docs/engine-split-map.md).

CI installs the engine from the PeerReviewAgents main branch, then this package with its test dependencies.

## Validation status

This is a research prototype, not a validated claim of superiority over a single agent or human reviewers. In the latest focused-evidence comparison, both reviews scored 8/10 and the judge narrowly preferred the saved review. See [the full result](docs/pra-focused-debate-results.md).

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

Tests use synthetic or local fixtures. Some optional rendering checks require local document tooling. Historical experiment scripts reference local study inputs and are not portable benchmark commands.

## Provenance

[The extraction manifest](migration/source-snapshot.json) records hashes of the imported source snapshot. The first commit preserves that snapshot before packaging changes. Raw manuscripts, model responses, caches and credentials are excluded from Git. Existing local study runs remain preserved separately. See [migration details](docs/migration.md).

The source licenses and attribution are preserved in [LICENSE](LICENSE). The repository is private. No package has been published to a registry.
