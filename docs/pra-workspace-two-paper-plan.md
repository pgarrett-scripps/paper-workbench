# Two-paper manuscript workspace pilot

The user authorized this development pilot on September 24, 2026. The study tests whether an evidence-focused debate improves an investigator's review of two experimental biology manuscripts. It does not test superiority at an equal inference budget.

## Source and reference controls

Use two previously unreviewed manuscripts with a documented version corresponding to available first-round public human reviews. Prefer original submissions or clean original preprints over published final manuscripts. Save the version evidence, dates, download locations, and content hashes. Do not combine a submitted PDF with final-publication XML. Exclude computational-methods manuscripts and do not download large datasets or execute author code.

Keep reports and author correspondence outside manuscript workspaces. Record all substantive human concerns with exact quotations before generating reviews. Split compound concerns conservatively. Mark concerns that cannot reasonably be assessed from the manuscript. Praise, editorial logistics, and purely cosmetic requests do not enter the scientific concern denominator.

Generation receives manuscript source files, their extracted blocks, and advisory diagnostics only. Public literature search is disabled for this pilot to reduce access to already published assessments. The fixed-reference Crossref tool remains available for identity metadata. No reference concern list or human review enters a generation prompt or tool directory.

Public preprints may have been seen during model training. Prompt separation cannot remove that possibility. Any uncertainty about which draft humans assessed must be reported and prevents treating this as a clean validation set.

## Paper Scaffold integration

Reuse the local checkout's plain-text `readability.metrics` and `prose_check.check` functions directly. Record the checkout revision and tool hashes. Provide counts and source-linked advisory findings to the investigator. Do not run Typst cleaning over extracted prose or enforce Scaffold's authoring conventions on imported papers.

These counts use Scaffold's word convention and exclude headings, references, and tables. They are distinct from the workspace's inclusive Unicode extraction counts. Captions and supplementary prose can still contribute. Neither a reading grade nor a style warning establishes a scientific defect.

Scaffold's bibliography checker expects BibTeX and citation keys. That checker cannot currently be reused faithfully on provisional extracted reference records. The integration reports this limitation. Structured citation-ID linkage is checked where XML supplies it, and existing Crossref checks resolve individual reference identities. Claim support and missing prior work still require scientific assessment.

## Conditions and spending

For each manuscript, generate one Sol medium investigation with the complete extracted text, advisory checks, and at most three tool calls. Preserve its output as the single-investigator baseline. Run one Sol medium debate on that same review, its cited passages, and verified images already inspected, with two further lookups available.

Score the five selected findings at most per condition. Preserve all earlier findings and unresolved items in the editor package, but do not count an unendorsed queue as successful final review coverage.

Across two papers, allow four review calls and two evaluation calls. No automatic retries, replacement papers selected after seeing performance, fallback models, paid API calls, or analysis reruns. The account must be authenticated through the subscription with zero paid credits verified. A 400,000 observed-token stop is checked before each call, not a hard within-call limit. Calls have a ten-minute timeout. An interrupted call with unknown usage stops the run.

## Evaluation

Freeze all generation outputs before evaluation. Use one Sol evaluator per paper, with neutral A and B labels and reversed label order across papers. Supply the frozen human concern list, source text, available inspected images, and both candidate reports. Do not reveal the condition mapping. Review style may still make the condition inferable.

Report direct and partial overlap separately. Direct overlap requires the same concrete concern, not simply the same topic. Use the number of manuscript-assessable human concerns as the primary reference denominator, and also report overlap across all reference concerns. A missing-control or requested-experiment critique can be assessable from the manuscript even though performing the experiment is outside this system.

Independently ask the evaluator to label every generated finding as supported, partly supported, unsupported, or unverifiable, and to assess factual fidelity of edits. Require exact manuscript quotations for supported judgments. Validate all IDs, complete item accounting, and quotations in code. Score normalized review suggestions after placement and numerical-edit guards, preserving unresolved items and reporting their counts. Both conditions share the same inspected image packet, deduplicated by content and sorted without condition priority, with at most four images. These are structural safeguards, not proof that the judge is right.

The implementing task will spot-check a small set of matches, nonmatches, and changed findings against the original source. Those checks are unblinded. They do not replace independent domain-expert assessment. No significance test or generalized overlap estimate is justified with two papers.

## Decision after the pilot

Keep the result even if debate reduces coverage or suppresses a useful finding. Inspect why each changed finding was retained, merged, or rejected. Decide whether the next engineering change should address evidence access, investigation targeting, debate selection, or reference matching. No larger study is authorized by this plan.

## Recorded operational amendment

After the original token stop halted execution at three completed calls, the stop was raised from 400,000 to 700,000 observed tokens to finish the authorized two-paper pilot. The six-call cap and all scientific inputs, prompts, conditions, and evaluation rules stayed unchanged. Completed outputs were reused without repeated inference. The original stop above is retained as the prespecified value. See `runs/pra-workspace-two-paper-v1/budget-amendment.json` and `docs/pra-workspace-two-paper-results.md` for the amendment and actual usage.
