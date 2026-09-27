# Manuscript revision and automation

The next product milestone is a dependable round trip from a manuscript to located review findings, a revised source draft, and publishable document files. This milestone does not establish that PRA produces better scientific reviews than the matched single reviewer. Earlier experimental results remain unchanged.

## Implemented order

1. Native Paper Scaffold import and source revisions. The importer copies a bounded project, records exact character offsets, and hashes the baseline. Accepted edits produce separate drafts. A successful PDF build is required by default before the active draft changes. Rollback selects an earlier draft and keeps all later history.
2. Scientific findings and copyedits have separate categories. The automatic policy accepts a narrow set of language transformations. A model cannot authorize a scientific rewrite merely by labeling it a copyedit. All other findings remain available for consideration.
3. The revision loop records its requests, responses, decisions, source diffs, and stop reason. Each new draft inherits a historical issue ledger. The viewer supports draft selection, author responses, issue tracking, and revision creation. An author's addressed status is distinct from evidence that a scientific problem is resolved.
4. Citation work remains limited. Native BODY citation keys can be compared with a lexical BibTeX inventory. Word export uses Paper Scaffold's bibliography parser and citation checks. Reference identity and claim support still need a dedicated evidence workflow.

## What unattended operation means now

The built-in loop runs without a model. It normalizes repeated horizontal spaces and replaces the exact phrase `in order to` with `to`. It performs at most two rounds and ten edits by default. Configurable limits permit at most five rounds and one hundred edits per run. It stops on convergence, an edit limit, a round limit, a repeated source fingerprint, a stale review, or a validation failure.

This intentionally small policy exercises the complete editing lifecycle without spending review tokens. It is not the scientific review engine. The existing investigation and debate remain the scientific review path, and their findings can be handed to the revision workflow. A broader unattended scientific rewriting policy has not been enabled.

For an agent integration, `revision-request` emits the active draft, source identity, historical issues, and edit policy. An orchestrator supplies a review bound to that identity. `revise` validates the response and creates a new draft using explicit decisions or the conservative automatic policy. The Python `run_loop` also accepts a provider callback, invoked against each newly imported draft. Any callback that launches model inference must use the existing subscription runtime and its separate call and usage limits. The revision loop bounds rounds and accepted edits, it does not impose a hard token cap on an arbitrary callback.

The CLI does not start a model, select a more expensive model, redeem a reset, run author analysis code, or publish a document. Sol remains the intended model for the next limited scientific test.

## Commands

Run from the In Silico checkout with its Python environment.

For an existing verified PDF or JATS workspace, `python -m paper_workspace port-scaffold /path/to/workspace /path/to/new-workspace` creates a conservative Scaffold reading copy. It retains the original PDF, source provenance, abstract, and table rows. Rich exports preserve supported source tables and figures, without reconstructing the publisher layout or native bibliography keys. See [the completed real manuscript fixes](pra-real-revision-improvements.md) for coverage and validation.

```bash
python -m paper_workspace import-scaffold /path/to/manuscript /path/to/workspace
python -m paper_workspace revision-loop /path/to/workspace --id language-pass --max-rounds 2 --max-edits 10 --scaffold-root /path/to/paper-scaffold
python -m paper_workspace revision-request /path/to/workspace
python -m paper_workspace serve /path/to/workspace --port 38755
```

A model or external agent can return a review response as JSON with `paper_id`, `source_sha256`, and `findings`. Each finding contains `category`, `kind`, `block_id`, `quote`, `replacement`, `comment`, and `evidence_blocks`. Categories are `scientific` and `copyedit`. Existing reviews without a category default to scientific. Use an empty replacement for a question.

```bash
python -m paper_workspace revise /path/to/workspace response.json --id revision-2 --source-revision language-pass-1 --expected-version 1
python -m paper_workspace checkout-revision /path/to/workspace original --expected-version 2
python -m paper_workspace export-revision /path/to/workspace language-pass-1 /path/to/workspace/exports/language-pass-1 --scaffold-root /path/to/paper-scaffold --python /path/to/python-with-export-dependencies
```

The version is the active draft pointer's optimistic concurrency token, returned by `revision-request`. It increments on revision creation and rollback. Do not guess it. A review of an older draft cannot overwrite a newer draft.

The default `revise` policy selects eligible copyedits. `--decisions path.json` instead supplies explicit accepted wording decisions using the normalized finding IDs for the chosen review ID. Source guards still apply. `--no-build` is an explicit source-only mode and does not establish document validity.

Document export requires Typst and a Python environment with the selected Scaffold checkout's export dependencies, including `pypandoc-binary` and `bibtexparser`. Ported rich exports additionally use `python-docx`, Pillow, `pypdf`, and local LibreOffice on PATH. The exporter invokes the selected trusted Scaffold adapters. It does not run the manuscript's analysis or build scripts. Draft sources are copied into a temporary export directory, helper values are resolved from saved declarations, and only complete PDF and DOCX outputs are published to the requested export directory. Export directories cannot overwrite previous outputs. For ports, `paper.pdf` renders the rich Word document and `source-build.pdf` preserves the compact Typst reading copy.

## Protection and limitations

Plain top-level BODY paragraphs, including native citation keys, are editable. Ported prose and abstract paragraphs also support edits through exact JSON string spans. The editor decodes a string, applies approved text changes, and encodes it again so quoted manuscript content cannot become executable Typst. Numeric bracket citations and native citation keys must remain unchanged and in order, including edits that touch only part of a marker. Equations, calls, raw code, headings, and other complex native Typst regions remain locked. A source location alone never authorizes a patch.

The native import is a revision adapter, not yet a complete replacement for the existing scientific PDF and JATS import. General native reading blocks cover BODY sources and do not evaluate complex Typst. The verified reading-copy port additionally includes its abstract, original reference records, section identities, and supplementary table rows. Full scientific review still needs the rendered paper, figures, and supplements.

Character offsets preserve Unicode and CRLF. All accepted edits must match the decoded source span and file hash. A changed source inventory, an overlap, changed citation markers, a removed or reordered number, or a change to selected negation and qualification terms blocks revision creation. Association inflections share one protected concept so a grammar correction from associate to associated does not fail solely on inflection. Reimported text must exactly match the approved text projection before a revision can be promoted. These mechanical checks cannot prove semantic equivalence. Complex scientific rewrites remain outside automatic acceptance.

Historical findings retain their original version and anchors. They are not silently relocated after wording changes. New reviews must be anchored against the new draft. Author responses travel with the review package and issue ledger.

Source import is capped at 250 MiB. Prepare manuscript inputs and required assets without large analysis datasets. Source symlinks are rejected. Repository metadata, environments, and common generated directories are excluded from the copy.

The DOCX is a clean editable manuscript. It does not yet embed native Word tracked changes or review comments. Its layout and citation style can differ from the PDF. A local CSL file is needed to reproduce a specified citation style. The workspace and source diff retain the editing history.

## Bounded validation

The engineering fixture in `tests/fixtures/scaffold-revision` includes prose, protected numbers and qualifications, a literal included Results file, a citation, and a native equation. It is synthetic and supplies no evidence about peer review quality.

The successful artifact run is `runs/pra-scaffold-roundtrip-v3`. It applied two eligible copyedits, compiled the revised PDF, and stopped on the next round because no eligible edits remained. The revised source preserved untouched files. The Paper Scaffold advisory report went from one verbose-phrase finding to zero. A readability score did not improve, illustrating why style scores must not serve as a scientific quality reward.

Both exported documents rendered successfully and their single pages were visually inspected. Word retains a native editable equation. PDF and Word use different reference styles in this fixture, which has no local CSL. Earlier fixture attempts exposed missing Scaffold front matter and heading numbering requirements. Those failed exports preserved the manuscript and did not publish partial outputs.

No new review inference was run for this implementation. Unit tests cover stale versions, source tampering, locked syntax, overlaps, number changes, failed builds, preserved scientific concerns, bounded stopping, and rollback. The HTTP check covers browser actions and persistence separately.

Final validation passed 104 unit tests, the native revision HTTP check, the legacy viewer HTTP check, and JavaScript syntax validation. A final offline provider handoff applied two short copyedits, preserved all three historical findings, and left one scientific question open. It stopped on the second round with no eligible edits. Before and after Scaffold reports were recorded. The active draft is `agent-handoff-1`, whose source fingerprint matches the visually inspected document exports.

## Next small scientific test

Use one native experimental manuscript with its rendered PDF and supplements. Preserve a frozen starting draft. Give the same source access and token allowance to PRA and a single reviewer. Compare supported scientific findings, excessive requests, factual regressions in proposed edits, issue retention through debate, useful accepted edits, and author effort. Score the before and after manuscripts blind to condition when possible. Human reviewer overlap remains a secondary measure.

Before broader automation, expand the edit policy with evidence from that test. A review agent should propose an edit, a challenge step should inspect its scientific meaning against the manuscript, and a local gate should validate its exact source patch and artifact build. Agreement between agents alone must not count as verification. If the challenge cannot establish the change, keep the proposal and its unresolved question available without modifying the draft.
