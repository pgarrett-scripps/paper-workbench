# Configurable ensemble development pilot

The anonymous Terra judge preferred the new pooled review over the previous PRA review and the two-pass basic review on one behavioral paper, *Is executive attention affected by environmental lighting conditions?* This is a development result, not evidence of general superiority.

## Comparison

| Review | Main findings | Justified concerns | Justified clarifications | Unsupported allegations | Excessive requests |
| --- | ---: | ---: | ---: | ---: | ---: |
| Previous PRA | 4 | 2 | 2 | 0 | 0 |
| Two-pass basic review | 4 | 2 | 2 | 0 | 0 |
| Pooled independent drafts and debate | 5 | 2 | 3 | 0 | 0 |

All 13 finding ratings passed source-reference and accounting checks. These checks do not independently establish scientific correctness. The judge preferred the pooled review because it combined the primary-table inconsistency, ANT trial processing and accuracy, allocation ambiguity, lighting-mechanism overinterpretation, and interim-analysis status. It considered the allocation question more consequential than the basic review's additional multiplicity question.

The pooled review therefore combined useful concerns from both discovery paths. It did not exhaust the issue space. It still missed the explicit multiplicity question present in the ordinary second pass. Debate added zero new candidates in this run, despite the new supported path for doing so.

## Retention and delivery

The pool contained nine original findings, three discarded hypotheses, and 33 sentence components. Eight source findings mapped into five primary comments. The ninth remained a supported secondary clarification about covariate handling and claims about confounding. The three discarded hypotheses were resolved with recorded evidence. Component accounting recorded 24 preserved, four deferred, and five resolved spans.

The blind judge evaluated the main reviews only. It did not rate the supported secondary inventory. Mapped components and retained records are not proof of complete semantic preservation.

The initial debate failed strict delivery validation. Two component quotations differed from their final comment in sentence punctuation or initial capitalization. The original failed response and progress record remain unchanged. A restricted deterministic repair updated only those two reference strings. It changed no finding, scientific status, component destination, or treatment. Full validation passed afterward. Future ensemble runs now include that repair with receipts.

## Cost and limits

- Two new Terra medium calls: one pooled debate and one anonymous judge.
- 132,942 observed tokens total, including the failed-delivery debate. No generation retry, paid API credits, or reset was used.
- The debate reused a saved basic first-pass draft and an independently generated investigator draft. Their prompts and tool access differed.
- The pooled review has three logical generation calls when its two reused discovery calls are counted. Both comparators have two. This was not a matched-compute experiment.
- The paper was already used in development. The fresh default two-reviewer runner and configured three-reviewer runner were exercised in offline simulations, not by new live discovery calls in this pilot.
- One judge, the same model family as generation, one fixed anonymous ordering, and no expert adjudication cannot establish a robust preference.
- The complete offline suite passes 266 tests.

Keep the default at two reviewers. The next useful experiment is a small fresh, matched-compute comparison, measuring distinct supported issues, false premises, secondary-comment quality, delivery failures, and cost. A third reviewer should justify its added expense through supported novelty. There is no basis yet for claiming saturation or expanding the default.

## Artifacts

- Original frozen protocol and failure: `runs/pra-ensemble-pilot-v1/`
- Pooled source ledger: `runs/pra-ensemble-pilot-v1/ensemble/debate-ledger.json`
- Recovered package and reference receipts: `runs/pra-ensemble-pilot-v1/reference-recovery/`
- Blind assessment: `runs/pra-ensemble-pilot-v1/reference-recovery/evaluation/`
- Result summary: `runs/pra-ensemble-pilot-v1/reference-recovery/results.json`

The original and recovery stages each preserve their source snapshot. The anonymous condition mapping was fixed before debate generation. No previous judge assessment or human peer-review report was supplied to this judge.
