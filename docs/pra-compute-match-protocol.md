# Matched-pass ecology comparison

This development comparison asks whether investigator plus debate improves the final review beyond a second ordinary self-revision pass by a single reviewer.

## Conditions

The single-review condition reuses its completed Terra review of the ecology manuscript and receives one additional self-revision pass. That pass sees its own draft, the original manuscript prompt, scientific supplements, figures, domain guidance and advisory checks. It receives no PRA output or earlier assessment. Its instructions permit checking mistakes, preserving useful concerns and finding important omissions, without simulating a debate.

PRA reuses the completed investigator plus debate review from `pra-reliability-retest-v4-terra`. Both conditions therefore use two generation calls with Terra at medium effort. Both final outputs permit up to five findings with the same approximate 900-word comment budget.

The original single review allowed six tools and PRA investigation allowed four. Both used zero, as verified from their event logs. The additional self-revision receives at most two tool calls, matching debate. Its accessible source packet is unchanged. Actual total tool use must remain within six. This is a disclosed difference in initial allowances, not a claim of identical historical settings.

## Assessment

One fresh-context Terra judge receives randomized anonymous labels, the two final reviews, manuscript source spans, referenced external cards and the union of shared or inspected source images. It receives no workflow names, prior preference, component ledger or cost information.

The existing quality rubric assesses support, materiality, specificity, proportionality and edit fidelity. Source handles are expanded and independently checked. Invalid assessments remain unscored. Preference is distinct from scientific validation.

The coordinator separately inspects changes between the first and second single-review passes and compares the final issue coverage. This inspection is not blinded and is reported separately.

## Cost and limitations

Only two new calls are authorized within this runner: self-revision and judge. No automatic retries or model substitutions are permitted. The launch threshold is 220,000 newly observed tokens, checked between calls. Generation cost comparisons include the reused first pass and both reused PRA calls. Incremental cost excludes those historical calls.

This matches model passes, model choice and evidence access, not exact tokens, hidden reasoning work or FLOPs. Actual token totals and their ratio determine how closely the conditions match in practice.

The paper, earlier reviews and PRA preference were known before this comparison was planned. Reuse limits cost but makes this a retrospective development comparison. It is not another independent paper or a held-out benchmark. One same-family model judge cannot establish scientific superiority.
