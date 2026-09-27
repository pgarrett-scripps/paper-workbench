# Matched strong reviewers with and without debate

The experiment isolates the addition of discussion to the same underlying panel.
It compares the saved strong reviewer, an editor consolidating three strong
reviewers, and the same editor consolidating the same reviews plus a discussion.

## Fixed inputs and reviewer workflow

Use nT89RltY10, UwcZEoNP19, and IjduZQK8gM, the same three previously exposed
development manuscripts. These are not held-out examples. Historical manuscript
and review version pairing and figure access remain unverified.

Reuse the existing strong single-agent review as reviewer 1. Generate reviewers
2 and 3 independently in parallel, with the exact saved reviewer prompt and
output schema, the same manuscript read and search tools, Sol at medium effort,
and the same manuscript bytes. Each can read, search, cross-check, and critically
revise its assessment. There is no new per-finding word cap or specialist role.
The saved prompt requests up to five concerns in a review of up to 900 words.

Reviewer 1 was generated earlier. Reusing it reduces new inference but does not
control for time-dependent model or service variation. Explicit model selection
is recorded. The CLI does not expose actual resolved model identity.

## Shared findings and two branches

Index the complete concerns in each raw review using the same paragraph-selection
prompt. The indexer returns only source paragraph IDs. The host copies the full
criticism, reasoning, qualification, and remedy verbatim in original order.
There is no total word limit on the stored finding ledger. Indexing errors remain
possible even though copied text is exact. Preserve the raw reviews for audit.

The editor-only branch receives the complete manuscript, original reports, and
the common finding ledger. The debate branch receives exactly those same inputs
plus one focused response from each reviewer. The three discussion responses run
in parallel. They address disputed claims, possible answers, and potentially
incorrect duplicate decisions, rather than restating every finding. This is one
simultaneous response round, without subsequent replies to those responses.

Both editor calls use an identical editorial prompt and schema. The only substantive
input difference is the discussion field, empty for the editor-only branch.
The editor must classify every finding and rank every retained finding. Valid
lower-priority concerns remain in major, minor, or unresolved sections. Answered
concerns require manuscript evidence. Duplicate concerns must point to a retained
finding that covers all their substantive components. Partial overlap does not
justify deleting a distinct concern.

Both full reports preserve exact finding text. An appendix retains original
answered and duplicate records and their disposition reasons. Findings in that
appendix are not counted as retained concerns in coverage calculations.

## Matched scoring

The primary outcome uses at most the first five ranked concerns within 900 words.
The host takes a prefix of complete concerns, stopping before the first concern
that exceeds the remaining word allowance. It does not truncate a concern or skip
over a higher-ranked concern to fill the budget. Apply this rule to reviewer 1
and both editor branches. Record actual concern counts and words.

Separately report coverage for every reviewer, the full panel union, and each
full retained report. Full-report and union coverage have more concern slots and
are diagnostic measures, not evidence of better performance at equal length.

Two anonymous scoring passes per paper evaluate the pooled immutable candidate
concerns against the frozen human-derived reference inventory and manuscript.
Hide candidate origins, discussion, ranks, and dispositions from both scorers.
Derive stage scores from candidate IDs. This provides consistent matching across
branches without repeatedly scoring identical text. It evaluates preserved
concerns, not the quality of editorial prose or the effect of reframing a claim.

Use fixed source IDs resolving to exact manuscript chunks for evidence. Source
existence does not establish correctness. Same-model judging and human-review
overlap are imperfect measures. Save an unfilled 15-concern human audit package.

## Decision rule and budget

Report three paired contrasts: editor-only versus reviewer 1, debate plus editor
versus reviewer 1, and debate plus editor versus editor-only. Evidence that the
complete debated architecture helps requires positive mean coverage differences
and wins on at least two of three papers for both latter contrasts, with no added
validated contradicted major concern on any paper. Missing outputs or invalid
support evidence make the screening result inconclusive. A positive result would
still require human audit and fresh papers.

The planned new workload is 36 calls: six new tool-using reviews, nine indexing
calls, six editors, nine discussion responses, and six judging calls. There is
no separate moderator agent. Both editor branches reuse the same initial reviews.

Allow at most one retry per node for an explicit stream-disconnection error, with
no more than four such retries in total. Preserve failed attempts in separate
directories. There are no automatic retries for content, schema, validation,
timeout, authentication, or budget failures. The total cap is 40 attempted calls
and four million observed tokens, including retry usage when known. Up to three
in-flight calls may overshoot the observed-token stop. Unknown usage is reported.

All inference uses the ChatGPT subscription without API-key billing, paid credits,
purchases, resets, or model fallback. Report cached input separately. Observed
token totals are not monetary charges or direct credit-consumption ratios.

Freeze inputs, prompt copies, dependency hashes, and code before inference. Stop
after the fixed three papers and report failures and results. Do not expand the
study or deploy changes to the installed plugin automatically.
