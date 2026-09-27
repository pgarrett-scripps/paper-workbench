# Manuscript workspace implementation and first pilot

Date: 2026-09-24

The local workspace is implemented and the first bounded pilot is complete. The investigation found a concrete visual reporting discrepancy that the plain reviewer missed. The debate then omitted that finding because it relied on text and did not reopen the figure. This supports building a better evidence handoff, not a claim that PRA outperforms a single agent.

## What is working

- PDF import with optional publisher JATS XML, stable source blocks, section word counts, references, source hashes, and conservative PDF page links.
- Supplementary DOCX tables with cell boundaries, figure previews, and original source files.
- Located comments, red deletions and green additions, original and accepted-draft views, durable decisions, undo, and JSON export.
- Source reads and searches, original page and figure inspection, saved evidence notes, bounded arithmetic, DOI identity checks, and focused literature search.
- A reusable `paper_workspace review` command with plain, workspace, and panel modes. Reviews use Sol medium with subscription authentication and explicit call limits.
- An editor package that preserves all source findings and carries unmatched findings into an unendorsed verification queue.

The system preserves the submitted source. Accepting wording does not resolve a scientific concern. Ambiguous anchors, invented numerical literals, stale source hashes, and overlapping accepted edits receive explicit handling.

## Paper and scope

The development paper was [TDP-43-mediated alternative polyadenylation is associated with a reduction in VPS35 and VPS29 expression in frontotemporal dementia](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3003573), published January 5, 2026. It combines postmortem tissue and cell experiments. The publisher identifies it as CC0.

The workspace contains 19 original PDF pages, 159 source blocks, 67 references, five supplementary figures, and nine supplementary tables. Small supplements total about 3.4 MB. The raw data workbook and unedited blot supplement were deliberately excluded and their existence was disclosed to reviewers. No author code, large data download, or analysis rerun was performed.

PDF extraction alone recovered only three bibliography blocks. Publisher XML supplied the complete bibliography. A later import correction recovered 61 DOI identifiers already present in reference text, leaving all 159 source blocks unchanged. Citation tools now also resolve those identifiers from frozen reference text. Bibliographic identity is not treated as verification that a reference supports a claim.

This is a published final manuscript selected for development. It is not an original submission or a held-out benchmark. Human review reports were not retrieved. Possible training exposure is not controlled.

## Small panel and findings

| Output | Findings | Observed tokens | Completed evidence tools |
| --- | ---: | ---: | ---: |
| Plain Sol review | 5 | 41,881 | 0 |
| Workspace Sol investigation | 4 | 272,733 | 7 |
| Compact Sol debate over both reviews | 5 | 28,076 | 0 |

Observed tokens include cached input. These are not measured dollar costs or subscription-credit charges. The workspace call reported 218,368 cached input tokens. Its other input plus output totaled 54,365 tokens, compared with 41,881 for the plain review. The two modes also differ in actual computation and tool execution.

Every CLI call explicitly requested `gpt-5.6-sol` with medium effort. The CLI event stream did not report a separate resolved-model identity. No fallback was permitted.

Both valid reviewers raised causal overinterpretation, possible confounding of the case-control comparison, and unsupported claims about early occurrence or accelerated progression.

The plain reviewer additionally raised a qPCR interpretation question and found an internal numerical inconsistency in supplementary Table S6. The adjusted TMEM106B coefficient is printed as -0.0086, outside its printed interval from -0.0073 to 0.0056. Direct inspection of the original DOCX table confirmed those printed values. The intended correction cannot be inferred.

The workspace reviewer inspected original PDF page 8 and supplementary Figure S5. It found that S5 labels the groups sgControl and sgTDP-43, whereas the methods describe scramble shRNA and TDP-43 shRNA. A subsequent implementing-agent visual check confirmed the labels. This supports asking the authors to reconcile the reporting. It does not establish which perturbation was used or prove the experiment is wrong.

The debate retained the plain review's five concern locations and dropped the figure-label question because the disputed words were absent from its text evidence. It had figure tools available but did not use them. This is a failure to carry visual evidence into the editorial stage, not evidence that the image concern was disproved.

The displayed editor package now contains five selected findings and one explicitly unendorsed verification item. All six are anchored to source text. Both proposed wording edits are available for inspection, and all nine findings from the two input reviews are preserved in the package ledger.

## Failure accounting and protocol deviations

Five total model attempts were made. Three yielded valid review outputs. One initial workspace attempt was interrupted when its launcher exited with code 143, leaving unknown token usage. A second attempt generated a response but all four MCP requests were rejected by the CLI approval path. That response was excluded from the comparison. It consumed 164,093 observed tokens, including 118,784 cached input tokens.

The tool failure was repaired with explicit per-invocation approvals for the eight bounded manuscript tools. No global approval setting, shell access, model fallback, API credential, or paid credit was enabled. The next workspace call completed all seven requested tools successfully.

The workspace investigation reached its continuation's 250,000 observed-token stop, so the original full-context challenge did not launch. The final remaining attempt used a separately frozen compact evidence packet and included all prior attempts in its accounting. It stayed within five total attempts. The overall 500,000 observed-token check was applied before the last call, not during it.

Total observed usage was 506,783 tokens across completed receipts, plus unknown usage from the interrupted attempt. This includes failed work. Planned blinded grading and order-reversal grading were dropped. No larger trial was launched.

The plain review did not exercise MCP tools, so equivalent effective tool access is not established despite identical advertised source and tool opportunities. Reviewer prompts, output limits, and the final compact debate configuration are preserved. These deviations prevent a clean efficacy comparison.

## Checks and post-pilot changes

Fourteen deterministic tests pass. They cover source integrity, Unicode offsets, ambiguous quotes, overlapping edits, numerical guards, gene identifiers, table extraction, DOI recovery, bounded arithmetic, tool limits, evidence preservation, and image handoff. HTTP checks passed for durable decisions, undo, stale-tab rejection, cross-origin rejection, immutable source export, and keeping scientific issues open.

Browser inspection verified the real manuscript's red/green edit rendering and passage navigation. Original PDF pages 3 and 8 and supplementary Figure S5 were visually inspected. Citation lookup resolved a known DOI through Crossref, and the date-bounded Europe PMC search returned three records. This verifies the tools, not complete literature coverage.

After the pilot, the reusable panel runner was updated to attach up to three previously inspected source images to the debate. It now carries unmatched findings into a verification queue instead of silently dropping them. These changes have deterministic tests but have not had a new model trial. No improvement claim is made for them yet.

The implementing agent performed unblinded source spot-checks. There was no independent domain-expert assessment and no blinded automated quality score. Counts of source anchors measure placement reliability, not scientific correctness.

## Decision

Keep the workspace infrastructure. Keep the debate, with source images and a complete findings ledger carried forward. Limit tools to investigations that add evidence, because repeated full-context searches increase token use. Preserve figure-based concerns that cannot yet be verified instead of treating missing text evidence as a rebuttal.

Do not claim superiority, publish a validation result, or launch a larger benchmark from this pilot. The next authorized small test should use a fresh experimental paper and a working tool configuration for both conditions, measure evidence-supported unique findings and false allegations, and verify that the repaired debate retains valid visual findings. A larger trial still requires user authorization.

## Artifacts

- Application and usage: `paper_workspace/README.md`
- Original source and current viewer: `runs/pra-workspace-pilot-v1/paper-v2`
- Completed plain review and source spot-checks: `runs/pra-workspace-pilot-v1`
- Excluded tool-failure attempt: `runs/pra-workspace-pilot-v1-r1`
- Successful investigation and evidence notes: `runs/pra-workspace-pilot-v1-r2`
- Compact debate, total ledger, and editor package: `runs/pra-workspace-pilot-v1-r3`
- Frozen code snapshots: `frozen-source` within each run directory

Native Word tracked changes, Word comments, full PDF layout reconstruction, and PDF annotation writeback remain unimplemented. The current export is an inspectable JSON review package.
