# Manuscript review workspace

A local research prototype for scientific peer review in context. It imports a PDF, optionally uses publisher JATS XML for text and references, preserves supplementary table cells, and presents source-linked comments and proposed wording changes. It does not rerun author analyses.

## Use

Install Paper Workbench as described in the repository README. PDF import requires `rustypaper`, Pillow and Poppler. The `paper_workbench_core` package provides the shared headless integration API.

```bash
python -m paper_workspace import manuscript.pdf workspace --xml manuscript.xml --supplements supplement-directory
python -m paper_workspace serve workspace --port 38744
python -m paper_workspace verify workspace
```

Open `http://127.0.0.1:38744`. Sources stay local unless you explicitly run a model review. The pilot sends manuscript text and selected source images to the authenticated Codex subscription and sends focused literature queries to Crossref or Europe PMC.

The viewer supports original text, marked suggestions, and an accepted-draft preview. Accept, decline, follow-up, and undo decisions persist on disk. JSON export contains the original source blocks, proposed blocks, findings, and decisions. Accepting wording does not resolve a scientific concern.

Import structured findings with `add-review workspace response.json --id review-name`. Findings contain a block ID, exact quote, kind, comment, evidence block IDs, and optional replacement. The schemas in `paper_workspace/review_schema.py` are the current reference. Ambiguous anchors remain unplaced comments. Replacements introducing numerical literals are withheld. Overlapping accepted edits and stale source hashes are rejected.

## Investigation tools

`investigation.py` exposes a bounded MCP server for source reads and searches, PDF page and supplementary figure inspection, saved evidence notes, arithmetic, DOI metadata checks, and focused literature searches. Tool logs and retrieved metadata retain provenance. Search defaults to a publication cutoff configured per paper. Abstracts and DOI metadata are not treated as full-text support.

The CLI defaults to Terra medium and also supports Sol medium and supports plain review, workspace investigation, and a panel with a debate pass. No API key, paid credit, fallback model, shell tool, author-code execution, or automatic retry is used. Inputs and code are fingerprinted before inference. Cache identity includes tool configuration, the manuscript manifest, and attached image paths and hashes. Completed calls can be recovered without another inference. Unknown usage and unresolved interrupted calls block further inference in that attempt directory. The default 250,000 observed-token stop is checked before each call. It is not a hard within-call cap.

```bash
python -m paper_workspace review workspace run-output --mode panel --literature-cutoff 2026-01-05 --billing-confirmation billing_confirmation.json
```

This command performs model inference. The billing confirmation must come from a current account check, record `no_paid_credits_verified: true`, and contain a Unix `checked_at` timestamp less than 24 hours old. The runner also requires an active ChatGPT subscription login. Do not fabricate this confirmation or use it to enable paid usage.

The first reviewer receives the full extracted text and at most three tool calls. Workspace and panel modes ask it to consider claims, comparators, measurement, interventions, replication, and internal consistency before selecting up to three uncertainties for investigation. The final response includes a short coverage record with exact source quotations. Areas can remain unresolved or be inapplicable. The record replaces the mandatory note-saving tool call. It is model-reported coverage, not proof of a complete review. No extra model session is added.

Coverage validation checks that every area appears once and that supplied quotations match the manuscript. Invalid entries remain unresolved. The validated record is saved to the run directory and included in workspace and panel JSON exports. Raw responses are retained separately. The existing viewer is unchanged and does not yet display a dedicated coverage panel.

The debate receives guarded review suggestions, the coverage record, cited source blocks, and up to three source images inspected by the first reviewer. It has two further evidence lookups. Withheld numerical replacements are passed as author questions. Debate output receives the same guards before entering the editor package. Every input finding has a stable ID. The debate must explicitly retain, merge, reject with reasons, or request verification for each one. Missing, duplicate, or invalid dispositions remain in an unendorsed verification queue. A shared source passage does not establish that two concerns are equivalent. Original suggestions and raw responses remain available, with guarded findings, dispositions, and validation records preserved in the editor package. The viewer exposes finding history beside the comments.

## Paper Scaffold checks

The optional adapter genuinely reuses `readability.metrics` and `prose_check.check` from an explicitly selected Paper Scaffold checkout. It reports prose word counts, readability, and source-linked advisory findings. It records the checkout revision, tool hashes, and optional dependency versions. The imported manuscript stays unchanged.

```bash
python -m paper_workspace checks workspace --scaffold-root /path/to/paper-scaffold --output scaffold-report.json
python -m paper_workspace review workspace run-output --mode panel --literature-cutoff 2026-01-05 --billing-confirmation billing_confirmation.json --scaffold-root /path/to/paper-scaffold
```

The checks operate on extracted plain text and skip headings, references, and tables. They include captions and supplementary prose. Their word convention differs from the importer totals. Readability and prose warnings are editorial cues, not evidence of scientific defects. Scaffold's Typst authoring rules and journal limits are not imposed on imported manuscripts.

Scaffold's bibliography checker requires BibTeX entries and citation keys, so it is not currently reused for extracted references. The adapter checks conservative citation-ID linkage for XML imports. PDF-only linkage is explicitly unavailable. The investigation tools still support focused Crossref identity checks, which cannot establish whether a citation supports a scientific claim.

The approved two-paper pilot uses these checks before inference and compares an investigator with its subsequent debate. Its protocol and leakage controls are documented in `docs/pra-workspace-two-paper-plan.md`.

That pilot is complete and found no measured overlap improvement from debate. The later four-paper panel also found no overlap improvement and no reviewer-requested tool calls. See `docs/pra-workspace-two-paper-results.md` and `docs/pra-workspace-four-paper-results.md` for the frozen results. Historical experiment prompts and result files have not been rewritten to use subsequent workflow changes.

## Evidence workflow experiment

The next development runner is `experiments/pra_evidence_workflow/run.py`. It implements an experiment map, deterministic source checks, evidence interpretation, and a fresh debate. This is a staged investigation workflow, not three independent reviewers. The reusable `evidence_tasks.py` module validates a bounded plan and executes its manuscript searches, source reads, original PDF page views, and small calculations before the evidence model call. Original page images are attached to that call. Immutable receipts record what was actually delivered.

The evidence response preserves at most eight candidates and selects at most five. Task records include observations, an author-side explanation, unresolved evidence, and receipt IDs. Invalid completion claims become unresolved before debate receives them. Debate sees every candidate and can use two further source operations. Exports retain the experiment map, validated task records, source provenance, candidate history, and dispositions. The existing comment viewer remains available, while the detailed task audit is currently in JSON exports.

The authorized cycle uses one reused-paper smoke test and a two-paper comparison against an ordinary Sol reviewer. Both conditions receive the same planner-selected raw page images. Human reviews are withheld until generation is locked. Evaluation separates justified concerns, justified clarifications, unsupported allegations, and unverifiable findings. It uses the complete verified image union for all three anonymous outputs, including the before-debate intermediate. Source delivery and exact quotations are engineering checks, not scientific correctness guarantees.

The fixed cycle permits eleven Sol medium calls and a 600,000 observed-token stop checked between calls. No automatic retries or wider panel expansion are enabled. The generic `review --mode panel` command still uses the earlier investigator-plus-debate workflow. Use the experiment runner only with its frozen protocol and prepared inputs. See `docs/pra-evidence-workflow-protocol.md` and `docs/pra-evidence-workflow-status.md` for scope and current status.

Only this invocation's eight manuscript tools receive explicit per-tool approval. They read the selected source, save local evidence notes and receipts, perform bounded arithmetic, or query the two public literature services. Global Codex settings are untouched. The configuration follows the [official OpenAI MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

The first development pilot completed three valid review outputs across five attempts. Two infrastructure failures are preserved. Planned model grading was dropped to conserve the attempt allowance. See `docs/pra-workspace-pilot-results.md` for evidence, usage, limitations, and the post-pilot image-handoff correction.

## Revised debate development path

`debate_revision.py` provides a versioned component-preserving debate schema, prompt, validator, and editor package. `debate_evidence.py` provides a fixed source-only tool profile with explicit any/all search and bounded claim or experiment context. Every original component receives a treatment, and scientific status is separate from editorial priority. Exact quotations and complete accounting are checked without asserting scientific correctness.

The viewer and export support the new decision ledger. The generic panel command above retains its earlier behavior. The revised path has only been exercised in the bounded one-paper runner at `experiments/pra_debate_revision/run.py`, using saved candidates. Its completed trial used two Sol calls and 92,303 observed tokens. A model judge preferred the revised review, but the paper was reused and the result is not a superiority claim.

See `docs/pra-debate-revision-protocol.md` and `docs/pra-debate-revision-results.md`. The completed run's inputs and source are frozen under `runs/pra-debate-revision-v2`. Code changes after the run intentionally prevent silently resuming it under changed inputs. Use a separately frozen attempt for future experiments.

## Boundaries

- PDF layout and reading order can be imperfect. Source-page links support inspection, and unresolved anchors are explicit.
- Publisher XML is preferred when available. PDF-only references remain provisional.
- The prototype preserves text and references rather than reconstructing a complete editable Typst paper. Paper Scaffold supplied the interaction concept, but this package does not depend on that sibling checkout.
- JSON export is implemented. Native Word comments, tracked changes, and PDF annotation writeback are not implemented.
- Literature search is focused and bounded. It does not establish exhaustive novelty or citation coverage.
- Model output remains provisional. Source anchoring prevents misplaced edits, but it cannot prove a scientific allegation correct.
- The pilot is a development demonstration on a published final paper, not a held-out benchmark or a claim of superiority over single agents.

## Verification

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
node --check paper_workspace/web/app.js
```

Tests cover Unicode anchors, ambiguous quotes, source tampering, overlap rejection, numerical guards, retained unplaced comments, table extraction, tool limits, restricted arithmetic, distinct concerns on shared passages, malformed debate dispositions, source-image provenance, export history, cache identity, interrupted-call recovery, and usage accounting. A separate one-call development retest is defined in `experiments/pra_workspace_handoff_retest/run.py`. It reuses the saved reviews and does not constitute an efficacy benchmark.

## Native Scaffold revisions

The real manuscript continuation now supports citation-aware source edits, all prose paragraphs in the tested port, preserved source figures and structured tables, and version-bound Word and PDF downloads. See [the completed fixes and validation](../docs/pra-real-revision-improvements.md). This is workflow validation with no new review inference or superiority claim.

Native Scaffold projects now support immutable source snapshots, exact prose anchors, separate revised drafts, PDF build gates, rollback, and a bounded unattended copyediting loop. Scientific concerns remain distinct from wording decisions. See [the revision workflow](../docs/pra-revision-loop.md) for commands, the agent handoff contract, validation, and current limits.

```bash
python -m paper_workspace import-scaffold /path/to/manuscript /path/to/workspace
python -m paper_workspace revision-loop /path/to/workspace --id language-pass --max-rounds 2 --max-edits 10
python -m paper_workspace revision-request /path/to/workspace
```

The built-in loop is offline and deliberately narrow. It makes no model calls. Existing investigation and debate outputs can be handed to the revision path, and a provider callback can supply fresh version-bound proposals. Model inference retains the separate subscription runtime's budget controls. Native Word export creates a clean manuscript, with review history retained in the workspace rather than embedded as Word tracked changes.

### Word review copies

After exporting a saved revision, run `python -m paper_workspace export-review WORKSPACE REVISION CLEAN_EXPORT NEW_OUTPUT`. The new package adds a Word copy with tracked changes from the immediate parent and comments for inherited open scientific questions. Exact paragraph matches are required for located comments. Uncertain locations remain in an appendix. The viewer offers the verified review copy beside the clean Word and PDF downloads.

See [Word review handoff](../docs/pra-word-review-handoff.md) for validation and current limits.
