# Four-condition Terra pilot

The four-condition comparison is complete. Results are mixed. PRA has promising examples of better qualification and more proportionate requests, but this pilot does not show a reliable overall advantage over basic review. It also exposed one delivery defect and a disputed automated assessment.

## Design

Four locally fresh published papers were reviewed with gpt-5.6-terra at medium effort under four conditions:

1. Basic scientific review, one pass and no tools.
2. Basic scientific review, two ordinary passes and no tools.
3. Full workspace with an investigator pass followed by ordinary revision.
4. Full workspace with the same investigator pass followed by structured debate.

The basic arms share their first draft. The workspace arms share an immutable investigator checkpoint, including the evidence and external-request state captured before debate. Ordinary revision does not see the debate output. All final reviews have a five-finding ceiling and the same approximate word guidance. These are paired, dependent comparisons with matched pass counts for the three two-pass conditions, not equal token budgets.

Inputs, generation and judging code, prompts and label assignments were frozen before generation. Every method occupied each anonymous label position once across the four papers. Each paper received one fresh-context Terra judge with item-level source assessment, all six pairwise preferences and an overall preference. There were no review-generation retries or model substitutions.

## Blind preferences

| Paper | Preferred review | Debate versus ordinary workspace revision | Qualification |
| --- | --- | --- | --- |
| Molecular biology | PRA | PRA preferred | Post-hoc assessment of a presentation-only recovery. Original PRA delivery failed |
| Ecology | Basic one and basic two tied | Tie | Two ratings unscored. The judge's interpretation of the PRA comment is disputed |
| Experimental behavior | Basic two | Ordinary workspace revision preferred | All item ratings passed validation |
| Observational public health | PRA | PRA preferred | All item ratings passed validation |

The two debate preferences, one loss and one tie must not be described as four successful frozen-workflow comparisons. The molecular review was assessed only after a documented administrative recovery. The ecology preference is provisional because of invalid item ratings and a substantive disagreement about what the review actually requested.

The basic second pass was preferred to the first on molecular biology and behavior, tied on ecology, and was less preferred on public health. More passes did not consistently improve preference. Full workspace ordinary revision was preferred to basic two on molecular biology and public health, and less preferred on ecology and behavior.

## Item-level assessments

| Paper | Basic one | Basic two | Ordinary workspace | PRA |
| --- | --- | --- | --- | --- |
| Molecular biology, recovered assessment | 5 supported | 5 supported | 5 supported | 5 supported |
| Ecology | 5 supported | 5 supported | 3 supported, 1 unscored | 4 supported, 1 unscored |
| Behavior | 5 supported | 4 supported | 5 supported | 4 supported |
| Public health | 5 supported | 4 supported | 4 supported | 4 supported |

Supported means a validated model rating of justified concern or justified clarification. It is not expert-established correctness. All 74 final entries were assessed, with 72 ratings passing reference and accounting checks. The two unscored ecology ratings alleged unsupported and excessive requests, but failed the meaningful-specificity evidence requirement. They remain unscored, not converted into supported comments or counted as zero errors.

One proposed edit in the one-pass behavioral review was judged to introduce an unsupported assertion, despite the underlying criticism being judged useful. The second basic pass omitted that edit. Concern quality and edit fidelity are therefore separate outcomes.

Entry counts are not distinct scientific discovery counts. Reviews can merge related issues, and fewer well-chosen comments can be preferred to a longer list. These data do not measure exhaustive recall or overlap with human reviewers.

## What the individual papers showed

The molecular reviews all detected substantial problems. The recovered PRA draft was preferred for distinguishing documented contradictions from unresolved questions about exposure timing, reagent identity, behavioral aggregation, imaging and pathway claims. The ordinary-workspace review was also strong. The delivery failure occurred in its structured bookkeeping, not in a missing review draft.

In ecology, the basic reviews added useful questions about apiary placement and the distinction between visitation counts and pollinator abundance. Debate retained the ordination-interpretation concern that ordinary revision omitted as a separate finding. It also narrowed the pooled-visitation criticism. However, the judge characterized both workspace comments as requiring female-only analysis, even though PRA explicitly recognized male-flower visits and offered a limited interpretation as an alternative. That assessment needs independent review. The detailed nonblind check is recorded in the case audit.

On behavior, the basic reviews identified an interim-analysis and multiplicity issue absent from the shared investigator draft. Debate preserved the four investigator candidates but did not discover that missing issue. Ordinary workspace revision added a useful stress-table reporting concern that the debate report did not include. This is primarily a discovery and addition problem, not evidence that debate deleted those issues from the initial candidate inventory.

A subsequent code audit identified an architectural constraint on that interpretation. Every final debate finding must map to a component of the existing candidate ledger. There is no explicit path for a genuinely new issue. An offline diagnostic rejected the independently anchored stress-table finding for this reason, even though adding it stayed within the five-finding ceiling. This limits debate's ability to compensate for first-pass omissions. Details are in `docs/pra-discovery-bottleneck.md`.

On public health, PRA was preferred for a supported causal-language correction and for making further proportional-hazards analysis conditional. The basic first pass retained a useful complex-sampling question that its second pass omitted. Debate's benefit here was calibration and actionability, not more supported final entries.

## Delivery defect and implemented correction

Original delivery was successful for all four papers in each basic condition and ordinary workspace revision. PRA delivered successfully on three of four papers.

On molecular biology, hypothesis-2 was labeled supporting while one component was preserved in final finding 2. The validator rejected that inconsistency. An offline replay changed only the presentation label to merged. All eight issues, 20 components and five final findings then passed the existing full validator. No review text, scientific status, evidence reference or component destination changed.

The subsequent blind assessment used this recovered draft and the originally assigned anonymous labels. It is reported separately as post-hoc recovery, while the original delivery remains failed.

After all experimental model calls and the original seal verification finished, the reusable reviewer was updated to recover only this exact redundant-presentation conflict. It derives the presentation label from component destinations, writes a change receipt and revalidates the entire output. Invalid quotations, unsupported source accounting, missing components and conflicting scientific status still fail. Raw model outputs remain unchanged. All 249 offline tests passed after this change. The corrected release has not received a new prospective live trial.

## Tools and resources

No optional MCP tools or live external requests were used by the review models. Workspace conditions received the supplied figures, domain instructions, scaffold diagnostics and result map. The results cannot establish a benefit from PDB, UniProt, literature search or other external integrations. More available tools did not translate into observed tool use in this pilot.

| Paper | Basic one tokens | Basic two tokens | Ordinary workspace tokens | PRA tokens |
| --- | ---: | ---: | ---: | ---: |
| Molecular biology | 66,266 | 137,891 | 192,012 | 230,377 |
| Ecology | 82,082 | 169,729 | 212,818 | 171,296 |
| Behavior | 54,253 | 114,325 | 145,498 | 126,479 |
| Public health | 64,280 | 132,417 | 201,297 | 143,331 |
| Mean | 66,720 | 138,591 | 187,906 | 167,871 |

These are logical condition costs, including each condition's shared first pass. Do not sum the columns to obtain incremental study usage. The complete study used 24 new calls and 2,013,735 observed input and output tokens. Shared generation was counted once in incremental usage. No paid credits or reset were used. Account-wide rounded consumption moved from 41% to 45%, which is not an exact task-specific charge.

The initial 1.8 million token launch threshold stopped the final judgments after generation had finished. A documented resource amendment increased the judging-only threshold to 2.2 million while preserving the original 24-call ceiling. It authorized only the two remaining planned assessments, including the separately labeled molecular recovery. There were no extra review generations, changed scientific prompts, repeated judges or outcome-dependent paper substitutions.

## Recommended next step

Keep the four-condition design. It separates the effect of an ordinary second pass, the full workspace package and the debate procedure much better than a single PRA-versus-baseline comparison.

Do not expand the study simply to obtain a favorable result. First address two specific limitations:

1. Require a judge that rejects a criticism to quote the actual reviewed premise, as well as source counterevidence. Independently check the disputed ecology judgment and the flagged manuscript edit. Exact source handles alone do not prevent the judge from mischaracterizing a review.
2. Improve discovery coverage before adding more integrations. The behavioral interim-analysis omission arose before debate. Test a lighter initial review prompt with targeted workspace checks, while preserving the candidate inventory and debate record. This is a proposed next version, not a change made during this panel.

Retain debate for its demonstrated ability to refine requests and preserve an auditable decision record, but do not claim that it universally improves reviews. Keep the manuscript workspace, located comments and reversible editing infrastructure as separate product benefits. Those benefits need their own usability and edit-fidelity evaluation.

The larger 24-paper study remains unlaunched. These four manuscripts are development cases and should be excluded from an untouched validation sample after any tuning.

## Sources and artifacts

- [Molecular biology source](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0311159)
- [Ecology source](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0307357)
- [Behavior source](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0305998)
- [Public-health source](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0319093)
- Protocol: `docs/pra-four-condition-protocol.md`
- Nonblind case audit: `docs/pra-four-condition-case-audit.md`
- Full machine summary, inputs, original outputs and judges: `runs/pra-four-condition-v1/`
- Separate molecular recovery and judgment: `runs/pra-four-condition-recovery-v1/`
- Original input and code hashes: `seal.json`, `frozen-source/` and `closeout-integrity.json` in the original run
- Resource amendment: `runs/pra-four-condition-v1/resource-amendment.json`
