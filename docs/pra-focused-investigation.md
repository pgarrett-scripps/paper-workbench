# Focused evidence investigation

The previous full-context tool check used 245,314 reported tokens for one manuscript link-map lookup. It reorganized text already supplied. This implementation separates a focused evidence investigation from full-manuscript review.

## Implementation

The new `python -m paper_workspace investigate` command accepts one scientific question and one to sixteen whole manuscript blocks, with a 4,000-word packet ceiling. It also supplies the section and asset inventories and selected domain guidance. The full paper remains accessible through tools. Omitting a passage from the packet is explicitly not evidence that the manuscript omitted it.

Each investigation allows one Terra or Sol medium session, at most two tool calls and two external requests. It returns an evidence memo rather than another review. Actual receipts and exact source quotes are checked before the memo is marked ready for adjudication. A failed check does not trigger another model call. The memo never automatically replaces a finding or claims scientific verification.

Version 2 selects immutable source handles from the packet and subsequent read or search results. Only handles actually exposed to that investigator are accepted. The system inserts the original source spans, avoiding model-composed quotations. This repair has offline validation only.

Tool audits distinguish visual inspection, external retrieval, derived checks, expanded manuscript context, rereads and reorganized manuscript text. These describe operations, not verified scientific novelty. Tool-check provenance is now retained in the debate ledger.

The supplement viewer can render one requested page of an available original PDF, even without a prebuilt image preview. It verifies the source against the manuscript manifest, validates page bounds and returns source identity and page metadata. Existing image previews remain supported. Handoff rechecks rendered images against the original source before passing them onward.

The focused command is available for evidence follow-up. Automatic selection of questions and integration of its memos into a live full panel are not enabled by this change.

## Single development check

One new Terra medium call uses six owl manuscript blocks addressing the parental-departure question. The coordinator selected this question from prior development findings. The investigator receives the question and source material, without earlier reviews or judge ratings. It may inspect original supplement table pages to assess what supports the claim and what remains uncertain.

This tests source access, traceability and the cost of a narrow follow-up. Comparing its usage with a full-review session does not measure matched-task efficiency or review quality. No blind judge, full panel or additional paper is included.

Run artifacts are saved under `runs/pra-focused-investigation-v1`. The observed-token launch guard cannot enforce a hard token cap within a running session. There are no automatic retries, paid credits or usage resets.

## Observed result and repair

The single version 1 session completed with two successful tools: view_supplement for original S1 PDF page 1, followed by read_blocks for the extracted table entries and definitions. The operations were classified as visual inspection and expanded manuscript context. No external lookup occurred.

The memo used the model rankings to strengthen the authors' defense that treatment predictors retain explanatory value after adjustment for parental departure. It also preserved the distinction between an adjusted association and an identified direct causal effect. This was a targeted follow-up to a known question, not discovery of a new issue.

One of six proposed source quotations joined table rows with an ellipsis. It failed exact-source validation, so the original memo remains marked not ready for adjudication. Its other five quotes passed. The original raw response and failure are preserved. No model retry or judge call was run.

After the failure, version 2 replaced composed quotations with source-handle selection and checked exposure against the actual packet and tool results. Offline tests reject invented and unexposed handles and hydrate valid selections with exact source text. Image responses now expose page count, source identity and limitations as well as the receipt. The live version 1 run had logged these metadata but transmitted only the image label and receipt.

The session reported 118,453 tokens, including 70,912 cached input tokens. The earlier full-review tool session reported 245,314, including 157,184 cached input tokens. The narrow task used about 52 percent fewer reported tokens, but this is not a matched-task efficiency benchmark. Overall pipeline savings are not established because the discovery and final review stages still have costs.

Validation passed 66 targeted tests. Manual checks confirmed that the rendered original S1 table was legible and that the inspected image passes source-verified handoff. The handle repair and transport metadata repair have not been retested with live inference.

## Remaining work

Use the focused path for specific unresolved questions rather than a mandatory extra investigation on every finding. Before automatic panel integration, test whether a debate uses the evidence memo appropriately, preserves unresolved questions and actually improves the final review. A failed quotation audit or a successful tool receipt alone must not become a quality score.
