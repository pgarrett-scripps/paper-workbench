# Paper Workbench

An evidence-linked workspace for manuscript review and revision. This research prototype imports manuscripts, investigates claims, runs configurable independent reviewers and debate, and presents located comments and proposed edits.

The project was extracted from In Silico. It is a successor implementation to the original PeerReviewAgents workflow, with different source handling, review orchestration and revision tools. The original projects remain separate.

## Team handoff

Start with [the team handoff](HANDOFF.md) for the current architecture, setup, exact stopping point and next engineering task. The [companion paper repository](https://github.com/pgarrett-scripps/paper-workbench-paper) contains the study evidence and publication blockers. Access to it may be restricted.

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

Model execution is an explicit separate action. The current engine supports authenticated Codex subscription sessions with Astra, Sol, Terra, Luna, or GPT-5.5 at medium effort. Launches require a fresh accepted billing record, including the current `included-allowance-v1` policy based on authoritative usage snapshots. This conservative check fails closed, but it is not a provider-side hard spending cap. Importing the package, inspecting a workspace or running offline tests does not start model inference.

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

## License

Source code is released under the MIT License and documentation under `docs/` under CC BY 4.0. The original In Silico attribution is preserved. See [LICENSE](LICENSE). No package has been published to a registry.

## Security

The tool never needs credentials committed to a workspace or this repository. Model runs use the operator's own authenticated session. Please report security problems privately to the maintainer through GitHub rather than in a public issue.
