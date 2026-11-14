# Engine and app split map

Historical record. This inventory planned the 0.8 split. Engine 0.9.0 later removed the Python review orchestration, and this app no longer carries `paper_workbench_core` or the aliases for the removed modules. See [the engine contract](shared-core.md) for the current boundary.

Snapshot: 9 November 2026, `main` at `c88cbba` (core 0.1.8). This is an inventory. No code has moved.

The review engine moves to PeerReviewAgents (package `peerreviewagents`, new breaking release). Paper Workbench keeps the app: the `serve` viewer, the revision workflow, proposed edits and exports. `paper_workbench_core` stays here as a thin shim that re-exports the engine API.

## Headline

1. No engine module imports an app module. Every boundary edge points from the app to the engine or to a shared module, so the cut is clean at the import level.
2. The engine is 38 `paper_workspace` modules (7,045 lines) plus `paper_workbench_core/api.py`, `baseline.py` and `config.py` (576 lines) plus 21 domain packs (63 files).
3. The app is 11 modules (2,290 lines) plus `web/` (3 files).
4. Four modules are shared (489 lines). All four should live in the engine, with the app importing them.
5. The hard parts are not imports. They are engine identity hashes, tool servers launched by file path, the insilico benchmark's location check, and frozen `experiments/` scripts (section 6).

## 1. Module classification

Line counts are `wc -l`. "Lazy" means the module is imported inside a function.

### `paper_workspace/` ENGINE (38 modules, 7,045 lines)

| Module | Lines | Purpose |
| --- | ---: | --- |
| `billing.py` | 95 | Validates Codex and Claude subscription billing records before a launch |
| `calculator.py` | 62 | Restricted arithmetic and manuscript access behind the calculation tool |
| `claim_checks.py` | 87 | Output contracts for evidence reconciliation and matched scientific review |
| `debate_epistemics.py` | 156 | Epistemic audit records for additive debate |
| `debate_evidence.py` | 111 | Fixed source-only tool server body for the debate-v2 profile |
| `debate_presentation.py` | 45 | Derives presentation labels from validated component destinations |
| `debate_revision.py` | 375 | Component-preserving debate schema, prompt, validator and editor package |
| `debate_tools.py` | 9 | Stdio entry file for the debate tool server, launched by path |
| `discovery.py` | 87 | Reviewer coverage record without extra inference |
| `domain_registry.py` | 84 | Loads and routes the domain skills under `domains/` |
| `ensemble.py` | 284 | Independent reviewers followed by one audited synthesis |
| `ensemble_debate.py` | 381 | Synthesis additions to the debate ledger with anchored references |
| `ensemble_references.py` | 117 | Formatting-only repair of synthesis component references |
| `evidence_handles.py` | 486 | Typed immutable handles for manuscript and external evidence spans |
| `evidence_tasks.py` | 820 | Executes and validates bounded evidence task plans |
| `external_evidence.py` | 200 | Bounded public-source retrieval and evidence cards |
| `focused_investigation.py` | 162 | The `investigate` command: one bounded evidence memo |
| `ingest.py` | 177 | PDF and JATS import into source blocks (rustypaper, pdftotext) |
| `investigation.py` | 293 | Manuscript tool server: reads, searches, page views, literature |
| `investigation_policy.py` | 73 | Targeted investigation instruction and tool-result tracing |
| `judge_evidence.py` | 52 | Exact source references for blinded model judges |
| `manuscript_tools.py` | 6 | Stdio entry file for the manuscript tool server, launched by path |
| `model_runtime.py` | 651 | Codex and Claude Code transports, receipts, usage, `source_manifest` |
| `models.py` | 17 | Model catalog and per-provider defaults |
| `reconciliation_tasks.py` | 137 | Locates reconciliation targets before a model chooses concerns |
| `result_map.py` | 150 | Result links and reported-quantity comparisons (tool and `result-map`) |
| `review_schema.py` | 31 | Located review schemas and shared reviewer instructions |
| `reviewer.py` | 471 | The `review` command: plain, workspace, panel, self-revision, ensemble |
| `run_report.py` | 211 | The `report` command: REVIEW.md and REVIEW.txt from saved run JSON |
| `run_state.py` | 138 | Durable stage state with process identity and interruption detection |
| `source_adapters.py` | 142 | Exact-record public source queries |
| `source_adapters_extra.py` | 160 | Additional exact-record adapters (STRING and others) |
| `source_packet.py` | 30 | Frozen source packet manifests for comparison runs |
| `source_payload.py` | 15 | Removes duplicate table rows from tool payloads |
| `supplement_view.py` | 42 | Renders one supplement page for the tool server (pdfinfo, pdftoppm) |
| `synthesis_validation.py` | 201 | Synthesis preflight against the production validator |
| `table_evidence.py` | 90 | Read-only evidence from reported-results workbooks (openpyxl) |
| `targeted_sources.py` | 397 | Identifier resolution, literature search, historical registration snapshots |

Data: `domains/` holds 21 domain packs, each with `manifest.json`, `skills/<name>/SKILL.md` and `fixtures/cases.json` (63 files, 1,379 lines). ENGINE.

### `paper_workspace/` APP (11 modules, 2,290 lines)

| Module | Lines | Purpose |
| --- | ---: | --- |
| `__main__.py` | 213 | The `paper-workbench` CLI. Must be split (section 4) |
| `server.py` | 309 | Loopback viewer with durable decisions and native revisions (`serve`) |
| `revisions.py` | 367 | Versioned source edits, revision loop, checkout, agent request |
| `source_edits.py` | 45 | Citation-protecting source codecs for prose edits |
| `scaffold_import.py` | 424 | Imports a Paper Scaffold source tree for editing |
| `scaffold_port.py` | 147 | Makes a Scaffold reading copy from a review workspace |
| `scaffold_export.py` | 147 | Exports a revision through Paper Scaffold tools and typst |
| `document_render.py` | 60 | Renders Word and PDF exports |
| `export_evidence.py` | 244 | Keeps verified source figures and tables in Word and PDF exports |
| `word_review.py` | 240 | Word review copy with tracked changes and comments |
| `table_structure.py` | 94 | Recovers Word table geometry for the viewer and Scaffold import |

Data: `web/app.js` (209), `web/index.html` (4), `web/style.css` (9). APP.

### `paper_workspace/` SHARED (4 modules, 489 lines)

| Module | Lines | Purpose | Used by |
| --- | ---: | --- | --- |
| `storage.py` | 27 | `digest`, `read`, `write` (JSON and hashing) | 24 engine modules, 8 app modules |
| `annotations.py` | 129 | `verify_workspace`, `normalize_review`, `save_review`, `export_draft` | 9 engine modules, 4 app modules |
| `scaffold_checks.py` | 331 | Offline Paper Scaffold readability and prose checks | `reviewer` (lazy), `revisions` (lazy), `checks` CLI |
| `__init__.py` | 2 | Version string only (stale `0.1.0`) | `core/api.py` imports the package to hash its directory |

`paper_workspace/README.md` (117 lines, package data) covers both halves and needs splitting.

### `paper_workbench_core/`

| Module | Lines | Bucket | Purpose |
| --- | ---: | --- | --- |
| `api.py` | 376 | ENGINE | Versioned facade: requests, `run_review`, `run_structured`, saved-draft synthesis |
| `baseline.py` | 96 | ENGINE | Single-pass manuscript-only review with tool isolation |
| `config.py` | 104 | ENGINE | Versioned review presets and resolved configuration |
| `__init__.py` | 15 | SHIM (stays) | Re-exports the public API, `__version__ = '0.1.8'` |

## 2. Boundary import edges

### ENGINE to APP

None.

### APP to ENGINE

| App module | Engine module | Names | Load |
| --- | --- | --- | --- |
| `__main__` | `models` | `DEFAULT_MODELS`, `SUBSCRIPTION_MODELS`, `provider_for` | top |
| `__main__` | `billing` | `claude_billing_record` | lazy |
| `__main__` | `model_runtime` | `auth_status` | lazy |
| `__main__` | `focused_investigation` | `investigate` | lazy |
| `__main__` | `ingest` | `import_paper` | lazy |
| `__main__` | `reviewer` | `review` | lazy |
| `__main__` | `run_report` | `write_reports` | lazy |
| `__main__` | `result_map` | `build_result_map` | lazy |
| `scaffold_import` | `ingest` | `words` | top |
| `table_structure` | `ingest` | `text_of` | top |

The `__main__` edges disappear once the engine commands move (section 4). Only two function edges remain, both small `ingest` helpers. Import them from the engine so word counts stay identical to the importer.

### APP to SHARED

| App module | Shared module | Names |
| --- | --- | --- |
| `__main__` | `annotations` | `normalize_review`, `save_review`, `verify_workspace` |
| `__main__` | `scaffold_checks` | `build_report`, `compact_summary` |
| `__main__` | `storage` | `read`, `write` |
| `revisions` | `annotations` | `export_draft`, `save_review`, `verify_workspace` |
| `revisions` | `scaffold_checks` | `build_report` (lazy) |
| `server` | `annotations` | `export_draft`, `verify_workspace` |
| `scaffold_port` | `annotations` | `verify_workspace` |
| `revisions`, `server`, `scaffold_port`, `scaffold_import`, `scaffold_export`, `export_evidence`, `word_review` | `storage` | `digest`, `read`, `write` |

### ENGINE to SHARED

`storage` is imported by 24 engine modules, including all three core modules. `annotations` is imported by `core.api`, `core.baseline`, `ensemble`, `evidence_tasks`, `focused_investigation`, `investigation`, `reconciliation_tasks`, `reviewer` and `synthesis_validation` (lazy). `reviewer` imports `scaffold_checks` lazily for `--scaffold-root`. `core.api` imports the `paper_workspace` package itself to hash its directory.

### Where each shared module should live

| Module | Recommendation | Reason |
| --- | --- | --- |
| `storage.py` | Engine, app imports it | `digest` defines every identity hash. Two copies could drift |
| `annotations.py` | Engine, app imports it | Normalization and anchoring are engine work. `export_draft` is app logic (it applies accepted edits), but it copies about 25 engine output keys and 6 engine tests use it to check the handoff. Keep it in the engine as the editor-package contract |
| `scaffold_checks.py` | Engine, app imports it | `review --scaffold-root` runs it before inference. The revision loop reuses it |
| `__init__.py` | Both get their own | The engine needs its own package marker and version. The app keeps `paper_workspace/__init__.py` |

### Couplings that are not imports

1. `model_runtime` launches `manuscript_tools.py` and `debate_tools.py` by file path from its own directory. Both files insert `parents[1]` on `sys.path` and import `paper_workspace.investigation` or `paper_workspace.debate_evidence` by absolute name.
2. `debate_presentation.py` imports `paper_workspace.debate_revision` by absolute name.
3. `reviewer`, `ensemble`, `focused_investigation` and `core.api` hash `Path(__file__).parent` with `source_manifest`. Today that hash covers app files too (`server.py`, `web/`).
4. `core/baseline.py` hashes `Path(__file__).parents[1] / 'paper_workspace'`, a path computed from the core's location.
5. `core.api` and `core.baseline` call the private `ensemble._prepare`.
6. `export_draft` and `web/app.js` read engine output keys such as `component_decisions`, `epistemic_audit`, `coverage_record` and `task_results`. A rename in the engine breaks the viewer without any import error.

## 3. Tests

`tests/` has 60 files: 57 `test_*.py`, 2 HTTP check scripts, 1 JavaScript UI test, plus `fixtures/scaffold-revision/` (4 files). They hold 401 test functions.

| Bucket | Files | Notes |
| --- | ---: | --- |
| ENGINE | 44 | Includes the ambiguous engine-side files listed below |
| APP | 11 | `test_citation_edits`, `test_document_render`, `test_export_evidence`, `test_revisions`, `test_scaffold_import`, `test_scaffold_port`, `test_table_structure`, `test_word_review`, `check_paper_workspace_http`, `check_revision_http`, `test_review_evidence_ui.js`. Keep `fixtures/scaffold-revision/` with them |
| EXPERIMENTS | 5 | `test_ensemble_fresh_evaluate`, `test_four_condition_evaluate`, `test_prospective`, `test_review_utility`, `test_simple_baseline` import only from `experiments/`. They go wherever `experiments/` goes |

Ambiguous files:

1. `test_run_report.py` and `test_claude_runtime.py` drive `paper_workspace.__main__.main` for `report`, `confirm-billing` and `review` argument parsing. They follow the engine CLI.
2. `test_debate_revision.py` and `test_tool_receipts.py` spawn `python -m paper_workspace.debate_tools` and `paper_workspace.manuscript_tools`. They are engine tests, but the module paths change.
3. `test_scaffold_checks.py` imports only the shared `scaffold_checks`. Engine if the recommendation holds.
4. `test_paper_workspace.py` sounds like an app test but exercises `calculator`, `investigation` and `reviewer`. Engine.
5. Six engine tests (`test_paper_workspace`, `test_review_export`, `test_discovery`, `test_hypothesis_handoff`, `test_domain_sources`, `test_debate_revision`) use `export_draft`. They stay engine only if `export_draft` stays in the engine.
6. `test_review_evidence_ui.js` checks how the viewer renders engine output. It stays with the app but needs an engine output fixture.

The tests mention `paper_workspace` 226 times, including 39 `mock.patch` targets. Every one needs the new module path.

## 4. CLI subcommands

`paper_workspace/__main__.py` defines 18 subcommands.

| Engine (9) | App (9) |
| --- | --- |
| `import` | `serve` |
| `verify` | `revise` |
| `add-review` | `revision-loop` |
| `result-map` | `revision-request` |
| `review` | `checkout-revision` |
| `investigate` | `export-revision` |
| `confirm-billing` | `export-review` |
| `report` | `port-scaffold` |
| `checks` | `import-scaffold` |

The engine CLI also takes `add_model_arguments`, `resolve_model` and `MODEL_HELP`. `revise` stays in the app but calls the engine's `normalize_review`.

`import`, `verify` and `add-review` are part of the app quick start (`import`, `verify`, `serve` in HANDOFF.md and the README). Recommendation: the engine owns them, and `paper-workbench` keeps pass-through aliases for `import`, `verify`, `add-review`, `review` and `report` for at least one release so the documented commands keep working.

PeerReviewAgents already ships `peerreview` (the LangGraph panel CLI) and `peerreview-mcp`. Where the engine commands land is a decision for the PeerReviewAgents task.

## 5. What travels with the engine

### Package data

1. `domains/*/manifest.json` and `domains/*/skills/*/SKILL.md` (already in `package-data`).
2. `domains/*/fixtures/cases.json` (21 files) are in the repository but not in `package-data`, and no runtime code loads them. Decide whether to ship them.
3. `manuscript_tools.py` and `debate_tools.py` must sit beside `model_runtime.py`, because they are launched by path.
4. The engine half of `paper_workspace/README.md`.
5. `web/*` stays with the app.

### Dependencies by module

| Package | Engine users | App users | Current extra |
| --- | --- | --- | --- |
| `rustypaper` | `ingest` | none | `documents` (`==0.2.1`) |
| `Pillow` | `ingest` | `export_evidence` | `documents`, `test` |
| `openpyxl` | `table_evidence` | none | `test` only |
| `python-docx` | none | `document_render`, `export_evidence` | `documents`, `test` |
| `lxml` | none | `word_review` | `documents`, `test` |
| `pypdf` | none | `document_render`, `export_evidence` | `test` only |

`openpyxl` and `pypdf` are runtime imports but sit only in the `test` extra today. Fix both during the split.

External programs. Engine: `pdftotext`, `pdftoppm`, `pdfinfo` (Poppler), the `codex` CLI and the `claude` CLI. App: `typst`, `pdftoppm` (viewer page images) and a Paper Scaffold checkout for export. `scaffold_checks` (engine) also loads a Scaffold checkout.

### rustypaper pin

The current pin is `rustypaper==0.2.1` in the `documents` extra. 0.2.2 is released (tag `v0.2.2`). PeerReviewAgents declares `rustypaper>=0.2` as a hard dependency. `ingest` writes the parser version into each imported workspace, so the parser is part of the condition. Recommendation: pin `rustypaper==0.2.2` exactly in the engine, record the bump as a new import condition, and replace the `>=0.2` floor.

### Python and platform

1. Paper Workbench requires Python 3.11 or newer. PeerReviewAgents declares 3.10 to 3.13. A quick search found no 3.11-only syntax, but the engine has never been tested on 3.10. Recommendation: raise the PeerReviewAgents floor to 3.11.
2. `external_evidence.py` imports `fcntl` at module top, so the engine cannot import on Windows. PeerReviewAgents claims OS independence and ships a Windows Claude installer. `revisions.py` (app) also uses `fcntl`. `run_state.py` reads process identity through `ctypes`.
3. PeerReviewAgents hard-depends on `langgraph`, `langchain-*`, `textual`, `fastapi` and `uvicorn`. Paper Workbench has zero hard dependencies today. Unless the breaking release moves those into an extra (for example `legacy`), the app inherits all of them.

## 6. Risks and parts that do not cut cleanly

### Risks

1. **insilico location check.** `benchmarks/peer_review/workbench.py` requires `paper_workspace` to sit beside `paper_workbench_core` in one distribution, and `fingerprint()` hashes only those two directories. After the split the check still passes, because the app keeps `paper_workspace`, but the fingerprint silently stops covering the engine. insilico must fingerprint the `peerreviewagents` engine instead. Its pin `paper-workbench>=0.1.4,<0.2` only protects it if the slimmed release is 0.2.0 or later. Recommendation: release the slimmed app as 0.2.0.
2. **insilico uses both halves.** `revision_study.py` imports app modules (`revisions`, `scaffold_export`, `scaffold_port`) and engine modules (`annotations`, `storage`). `revision_semantic.py` uses `from paper_workbench_core import api`, so the shim must keep `api` as an importable submodule, not just top-level names. `workbench.api()` also requires `capabilities()["api_version"] == "paper-workbench-core-v1"`.
3. **Frozen experiments.** `experiments/` has 159 Python files that import engine modules by their `paper_workspace.<module>` names (storage 51, annotations 38, model_runtime 35, reviewer 20 and more). Frozen scripts must keep their original code. Recommendation: tag `c88cbba` (tags stop at `v0.1.5`) and run frozen experiments only from that tag, instead of keeping per-module shims.
4. **Engine identity changes scope.** `source_manifest` hashes the package directory. After the move the hash covers only engine files. `run_saved_draft_synthesis` rejects saved drafts whose `engine_source` differs, and `reviewer` and `focused_investigation` refuse to resume when the code hash changed. Finish or abandon every in-flight run directory before the split. If the engine lands at the top level of `peerreviewagents`, the hash would also cover the legacy LangGraph code.
5. **Name collisions.** PeerReviewAgents already has `ingest`, `storage`, `web`, `reports` and `runtime` subpackages. The engine's `ingest.py` and `storage.py` collide at the top level. Recommendation: put the engine in its own subpackage, which also fixes the hash scope in risk 4.
6. **Tool servers launched by path.** The two entry files and `debate_presentation` use absolute `paper_workspace` imports, and the tests spawn them with `-m paper_workspace...`. All must change together.
7. **Viewer schema coupling.** `web/app.js` and `export_draft` read engine output keys without an import. Recommendation: a versioned editor-package fixture tested in both repositories.
8. **Backend identifiers.** insilico distinguishes `paper_workbench_core_v1` from `peerreviewagents_panel_v1`. Once both come from one package, run artifacts must record the engine package and version so the two are never confused.
9. **Documentation.** `docs/shared-core.md` says to keep the engine inside Paper Workbench. HANDOFF.md, both READMEs and `docs/claude-code-provider.md` point at engine paths. The 83 `docs/pra-*.md` study records describe engine experiments. Deciding which move is a paper-lead call.

### Parts that do not cut cleanly

1. `annotations.export_draft`: app behavior inside an engine module, used by engine tests.
2. `scaffold_checks`: needed by `review` and by the revision loop.
3. `import`, `verify`, `add-review` and `checks`: engine commands that the app workflow documents.
4. `ingest.words` and `ingest.text_of`: engine helpers the app needs.
5. `paper_workspace` as a name: the app keeps it, while 159 experiment files and insilico use it to mean the engine.

## Estimates (agent time)

| Step | Estimate | Main work |
| --- | --- | --- |
| (a) Land the engine in PeerReviewAgents | 90 to 150 agent minutes plus test run time | Copy 41 modules, the 3 core modules and `domains/` into a subpackage (relative imports survive), fix 3 absolute self-imports and the path-launched servers, set package data, extras, Python floor and the rustypaper pin, add the engine CLI, move 44 tests and rewrite about 226 module paths, handle the name collisions and `fcntl` |
| (b) Slim this repository | 60 to 90 agent minutes plus test run time | Delete 38 engine modules and `domains/`, depend on `peerreviewagents`, rewrite 30 app import lines, make `paper_workbench_core` a re-export shim (keep `api` and `config` submodules and `api_version`), split the CLI with pass-through aliases, drop the engine tests, update docs, tag the pre-split commit |
| insilico follow-up (separate repository) | About 30 agent minutes | Point `fingerprint()` and the location check at the new engine, then bump the pin |

The offline test suite was not run for this inventory, so its run time is not included.
