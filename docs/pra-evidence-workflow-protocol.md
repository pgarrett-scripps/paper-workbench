# Evidence workflow development protocol

The user authorized this cycle on September 24, 2026. This protocol implements the proposal in `pra-evidence-workflow-plan.md`. It is a development comparison, not a confirmatory study or an authorization to expand indefinitely.

## Fixed scope and budget

Use subscription-backed Sol at medium effort for every model call. Permit at most eleven calls and stop launching calls once observed usage reaches 600,000 tokens. A call already running can cross that threshold. Preparation and orchestration usage are separate. No paid API, paid credit purchase, automatic retries, model fallback, full analysis reruns, large datasets, or author-code execution.

First run one evidence-stage smoke test on a previously used development paper. Require a delivered original PDF image, valid task-bound receipts and source quotations, preserved candidates, and interpretable source-specific observations. This is an engineering gate, not an efficacy result. If it fails, preserve the result and fix offline before any further live run.

After the gate passes, select exactly two fresh experimental biology papers with public first-round reviews. Exclude all previously used sources and computational-methods papers. Freeze clean manuscript versions, source hashes, reference concerns, diagnostics, prompts, schemas, and code before review generation. Preserve the original smoke code snapshot separately from the final study snapshot.

## Conditions and source access

For each fresh paper make four generation calls and one evaluation call:

1. A planner maps at most eight experiments and requests at most three concrete evidence tasks. It sees the manuscript and advisory Paper Scaffold diagnostics, but no human reviews.
2. The runner executes at most four requested operations. Require one or two original PDF page views. Other operations may read manuscript blocks, search the manuscript, or calculate small expressions. Save immutable task-bound receipts, source hashes, results, and copied page images.
3. An ordinary single reviewer receives the full manuscript and the same selected raw page images, without planner instructions or findings. It may use the remaining operations from a total allowance of six and return at most five findings. Sharing selected pages strengthens this comparator but means it is not an independently chosen page-access baseline. Charge planning cost to PRA and disclose the shared-page design.
4. An evidence interpreter receives the map, tasks, delivered evidence, actual page images, and full manuscript. It has no additional tools in this stage. It preserves at most eight candidates and selects at most five for the pre-debate condition. Each task records observations, the strongest author defense, remaining uncertainty, and exact source references. Receipts prove delivery only. Invalid completion claims are downgraded to unresolved.
5. A fresh debate call receives every candidate, validated task records, delivered evidence, and the page images. It may use two additional source operations and selects at most five findings. Every candidate receives a disposition. Preserve discarded and unresolved findings in the editor package.

Steps 1, 3, 4, and 5 are the four generation calls. Step 2 is deterministic execution. Before-debate output is an intermediate condition with four source operations. The completed workflow and ordinary reviewer each have six-operation allowances. Equal allowances do not equalize consumed compute. Report actual model and tool usage by stage and distinguish eager source operations from model-requested operations.

Repeated requests for identical page content keep separate operation receipts but produce one image attachment. The ordinary reviewer is charged for the unique raw pages it actually receives. The evidence workflow is charged for every executed operation, including redundant requests. If no planned page is delivered, stop before further generation on that paper.

Retain anchored comments and optional supported edits. Prose checks, readability, word counts, and citation metadata remain advisory. Broad literature discovery is disabled in this cycle because source-dated retrieval and review leakage need separate validation.

## Reference preparation

Archive the original public reviews and preserve exact quotes. Use only substantive first-round reviewer concerns that apply to the supplied manuscript version. Exclude editorial requests, duplicate concerns, and already-answered allegations with a recorded rationale. Group duplicate scientific issues before generation. Keep an inclusion and exclusion ledger.

For each included concern record the relevant source assets and whether it is assessable from the supplied manuscript. Unavailable movies, raw data, or essential omitted supplements make that concern unassessable. Freeze both the all-concern and assessable denominators. Public first-version manuscripts may not be identical to confidential submission files, and that uncertainty must remain explicit.

## Evaluation

Finish and lock generation for both papers before exposing any evaluator to human reference concerns. Use one fresh, label-blinded Sol evaluator per paper for ordinary, before-debate, and after-debate outputs. Rotate labels using two prespecified orders, ordinary/evidence/debate and debate/ordinary/evidence. Three positions cannot be balanced across two papers.

Give the evaluator the full manuscript and the complete union of original images delivered to or inspected by either generation condition. Deduplicate by verified content hash. The new protocol explicitly permits up to ten source images per call while legacy protocols retain their previous limits. Never silently truncate the shared image packet. Stop if the complete packet exceeds ten. Human concerns requiring visual evidence outside this packet cannot receive confident visual validity judgments. The evaluator must use unverifiable where decisive evidence is absent. Manuscript-level assessability and actual evaluator access are distinct.

Rate each finding as a justified concern, justified clarification, unsupported allegation, or unverifiable. Questions can contain unsupported premises. Assess specificity separately and require a concrete experimental target, scientific consequence, and resolution for a meaningful label. Record materiality, exact textual evidence or supplied image references, counterevidence, and edit fidelity. Validate source references mechanically without claiming this establishes scientific correctness.

Score direct and partial human overlap separately for both denominators. Additional valid findings outside human reviews are not false positives. Retain all raw outputs and frozen metrics, including negative results. No independent expert grading is available in this cycle, so do not claim expert-validated correctness or a precise false-positive rate.

## Decision

A promising signal is at least two additional distinct, supported direct human-concern matches per paper over the ordinary reviewer, without additional materially unsupported major allegations. This is a practical development threshold, not a significance test. Audit decisive matches against source evidence and group related concerns conservatively.

Evaluate debate separately on consequential corrections, avoided unsupported allegations, gained useful findings, and lost useful findings. Merely rephrasing a review is not a demonstrated benefit. If the gate fails, preserve the result and diagnose the bottleneck instead of expanding the panel. Seek authorization before a larger fresh-paper study.

## Adapter amendment before first review generation

The first fresh-paper planner completed, but execution rejected a range such as `b0092–b0096` where individual block IDs were required. The same plan used Boolean syntax in a literal-only search. The raw output and original study snapshot are retained. No fresh-paper review findings or evaluation scores existed when this amendment was made.

Normalize only unambiguous source-ID ranges over existing manuscript blocks, preserving every referenced block and recording the transformation. Expanded map references may contain up to twenty-four individual IDs. The planner output schema and prompt remain unchanged, and source-reading operations retain their twelve-block cap. Do not infer or replace unknown references.

Reject unsupported Boolean search syntax as a failed source operation rather than returning a misleading empty match list. Required failed searches leave their task unresolved. No additional searches, rewritten scientific tasks, model retries, or increased budgets are permitted. Reuse the completed planner output and freeze an amended executable snapshot before review generation continues. Report this repair as a development-run deviation.
