# Four-condition pilot case audit

These are nonblind coordinator checks after outputs were generated. They do not replace the frozen model ratings or independent expert assessment.

## Molecular biology delivery failure

The original PRA output failed the existing validation rule that presentation must agree with preserved component destinations. The affected record was hypothesis-2. It was labeled supporting, while one of its components pointed to exact text in final finding 2.

An offline engineering replay changed only hypothesis-2.presentation from supporting to merged. The existing full validator then passed all eight issues, 20 components and five selected findings. Scientific status, review text, source evidence and component destinations were unchanged. The original run remains a failed delivery in the frozen benchmark.

This exposes redundant model-authored bookkeeping. A narrow future correction can derive presentation from verified destinations, preserve the original label in an audit receipt and still reject invalid references, missing components and contradictory scientific status. It does not require another model generation.

## Ecology judge disagreement

The blind judge preferred the two basic reviews and tied them. It treated the pooled-visitation criticism in both workspace reviews as an unsupported, excessive demand for female-only analysis. Both associated item ratings were left unscored because their meaningful-specificity fields supplied counterevidence without the required evidence entry.

The ordinary workspace comment explicitly prioritizes visits to female flowers and asks whether the association persists for that subset, while allowing a narrower interpretation instead. The PRA comment is more qualified. It asks why total orchard visitation is an appropriate proxy, requests sex-specific analyses only if available and otherwise asks for an association-level interpretation. Its counterevidence explicitly recognizes that male-flower visits matter for pollen acquisition.

The manuscript describes pollination as depending on both flower sexes. That supports caution about an exclusively female interpretation. It does not, by itself, establish that PRA demanded exclusively female analysis. The judge's rationale appears to overstate the actual PRA request and underrecognize its stated counterevidence and fallback qualification. An expert could still decide the comment is unnecessary or weak. That is different from accepting this automated unsupported-allegation classification as ground truth.

A useful future evaluator change is to require an exact excerpt from the reviewed comment for the premise being rejected, along with source counterevidence. This would make review mischaracterization easier to detect. Exact excerpts still would not prove the scientific judgment correct. The current frozen judgments are not edited or rerun to obtain a preferred outcome.

Sources are the original [carob paper](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0307357), the saved anonymous reviews, the raw judge response and its audit under `runs/pra-four-condition-v1/panel/ecology/evaluation/`.
