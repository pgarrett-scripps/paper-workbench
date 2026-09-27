# Tool-free baseline comparison

The anonymous judge preferred the full ensemble pipeline over a one-pass tool-free reviewer on the burrowing owl manuscript. It also preferred the tool-free reviewer over ordinary three-pass workspace revision. This is one retrospective development case, not evidence of reliable superiority across papers.

## Results

| Condition | Passes | Supported main findings | Unsupported allegations | Excessive requests | Generation tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tool-free basic review | 1 | 4 of 4 | 0 | 0 | 72,555 |
| Ordinary workspace revision | 3 | 4 of 4 | 0 | 0 | 242,989 |
| Two independent reviewers plus debate | 3 | 5 of 5 | 0 | 0 | 236,186 |

The judge's pairwise preferences were ensemble over basic, ensemble over workspace, and basic over workspace. All 13 finding ratings passed reference and accounting validation. No ratings were unscored or classified unverifiable. Supported means a model judgment of justified concern or clarification, not independently established expert correctness.

All three reviews identified the same four core issues: differential outcome availability, direct-effect interpretation after conditioning on parental departure, verification of ectoparasite-treatment efficacy, and inconsistent descriptions of randomization. The ensemble additionally asked the authors to qualify their attribution of annual treatment differences to ambient food availability. The judge considered that distinct concern supported and proportionate.

The tool-free baseline was a strong comparator. The judge preferred its explanation of the causal estimand and remedies to the ordinary workspace review. The extra ordinary passes and workspace did not add a supported issue on this manuscript. Ensemble's additional issue originated in its second independent reviewer and survived debate. This comparison does not establish that debate was needed to retain it.

## Cost and integrity

Only two new calls were made: 72,555 tokens for the tool-free review and 90,845 for the fresh anonymous three-way assessment, totaling 163,400 observed tokens. The workspace and ensemble outputs were reused unchanged from the completed clarification study. Their generation costs in the table are historical logical costs, not additional spending in this run.

The ensemble used approximately 3.25 times the generation tokens of the basic reviewer for one additional supported issue in this case. The result supports a quality advantage according to this judge, not a cost-efficiency advantage. Pairwise judgments from the same call are dependent.

The basic reviewer received the same prepared main manuscript, references, six small supplementary tables, and initial original figure image. It had no tools, domain checklist, scaffold diagnostics, result map, other reviews, or prior judge feedback. Neutral review guidance, the clarification policy, source handles, and the conservative edit guard were common infrastructure. This evaluates a tool-free structured review rather than an unstructured chat transcript.

The judge received anonymous primary reports, manuscript evidence, the union of inspected source images, and any eligible source records. It received no workflow labels or earlier judgments. The labels were fixed before baseline generation: A workspace, B basic, C ensemble. Secondary inventories were outside this primary-report comparison.

All input and code hashes passed the final seal check. There were no failed new calls, retries, fallback models, paid credits, or resets. All 294 offline tests passed before generation. Artifacts are preserved under `runs/pra-simple-baseline-v1`, including frozen source, protocol, prompt, anonymous inputs, raw model output, audits, costs, and completion status.

## Interpretation

We can say that on this manuscript a blind model judge preferred the full pipeline to a straightforward one-pass tool-free review, citing one additional supported scientific issue. We cannot say the pipeline reliably outperforms tool-free agents, improves quality per token, or that tools and debate individually caused the advantage.

The coordinator already knew this paper's ensemble result when selecting it for the inexpensive added baseline. It remains a development paper excluded from confirmatory sampling. Generation and judging used Terra at medium reasoning, with one anonymous same-family judge and no expert adjudication or human-review overlap measurement.

Keep the tool-free arm in any larger frozen comparison. It provides a useful quality and cost reference and prevents improvements over a weaker workspace revision arm from being mistaken for improvements over a straightforward reviewer. A broader superiority claim needs untouched papers and blinded expert assessment of at least a prespecified subset.
