# Three-general-reviewer experiment: partial results

Only one of the three papers completed the full workflow and evaluation.
Connection failures interrupted the other two papers. The experiment is
inconclusive and paused, with no automatic retries or additional inference.

On the completed paper, the panel improved over the prespecified first reviewer,
but remained below the saved single agent. It also scored below reviewer 2 alone.
One paper cannot establish whether this architecture improves reviews in general.

The two single-reviewer conditions are not identical. Reviewer 1 is a new
one-shot review with the manuscript embedded in the prompt, no tools, a structured
finding format, and a requested 100-word limit per finding. The saved single
agent uses a different prompt explicitly requesting cross-checking and critical
revision, manuscript read and search tools, and a free-form review of up to 900
words. On this paper it made 10 manuscript reads and 14 manuscript searches.
Both explicitly selected the same Sol model at medium effort. This experiment
therefore does not compare three copies of the saved strong single-agent workflow
against one identical copy. That difference limits architectural conclusions.

## Completed paper

The completed manuscript is On Gradient-Weight Alignment, nT89RltY10. Coverage
counts reference concerns matched by both automated scoring passes out of 17.
All candidates were scored together with anonymous IDs and the same manuscript.

| Output | Concerns available | Confirmed reference matches | Coverage |
| --- | ---: | ---: | ---: |
| Reviewer 1, prespecified baseline | 5 | 1/17 | 5.9% |
| Reviewer 2 | 5 | 4/17 | 23.5% |
| Reviewer 3 | 5 | 3/17 | 17.6% |
| Full panel union, diagnostic only | 15 | 4/17 | 23.5% |
| Moderator output after discussion | 5 | 3/17 | 17.6% |
| Final editor output | 5 | 3/17 | 17.6% |
| Saved single agent | 5 | 5/17 | 29.4% |

The three-reviewer union covered the same confirmed reference concerns as
reviewer 2 alone. The additional reviewers therefore added no confirmed coverage
beyond that reviewer on this paper. Reviewer 2 was identified after evaluation,
so it is a diagnostic observation, not a prospectively selected baseline.

The moderator selected five concerns and the editor retained exactly those five.
One concern about the breadth of evaluation was lost between the complete panel
and the moderator output. Both scorers matched that issue to reviewer_2_F5.
The moderator marked the finding supported, but did not select it. The editor's
reason was that its quantitative-evaluation and efficiency points were covered
elsewhere. The retained concerns did not preserve the broader-scope reference
match. This is a concrete example of partial overlap being treated as redundancy.

The moderator classified six findings as supported and nine as duplicates.
No finding was classified as unsupported or uncertain. These outcomes do not
demonstrate that discussion corrected false criticisms or caused a quality gain.

## Verification and correctness limits

All three initial review calls overlapped in time. Reviewers had no access to
each other's initial responses. Every discussion response addressed all 15
finding IDs. All moderator resolutions and editor dispositions were saved.
The final concern packet contains 557 words, below the 900-word limit, with
all selected finding text preserved exactly.

Fixed source IDs worked on the completed paper. All reviewer, discussion,
moderator, and scorer citations resolved to exact supplied chunks. None required
the line-range recovery used in the earlier experiment. The two judges labeled
all 20 pooled candidate concerns supported, with no invalid evidence IDs.
That confirms citation formatting, not scientific correctness. Uniform support
labels should be checked in the pending human audit.

Coverage is overlap with human-derived concerns. It does not measure all useful
criticisms. Same-model scoring passes are correlated, and manuscript-review
version pairing and figure access remain unverified. Shared candidate scoring
also introduces context effects. Earlier experiment scores are not pooled here.

## Incomplete papers and usage

- UwcZEoNP19: all three initial reviews and discussion responses were saved.
  The moderator call failed with a stream-disconnection error. There is no final
  panel output or evaluation for this paper.
- IjduZQK8gM: all three initial reviewer calls failed with stream-disconnection
  errors. There is no completed initial panel, discussion, or final review.

The CLI reported that streams disconnected before completion while sending to
the Codex response endpoint. This does not establish whether the cause was local
connectivity or a backend problem. Failed responses were not retried or replaced.
The process exited after saving an incomplete report and the unfilled 15-concern
human audit package.

There were 20 attempts, comprising 16 successful calls and four failed calls.
Observed usage was 549,040 tokens, plus unknown usage from the four failures.
No inference continued after the run ended. Every request selected Sol at medium
effort through ChatGPT subscription, without paid credits or API-key billing.

For the completed paper only:

| Generation method | Observed tokens |
| --- | ---: |
| Reviewer 1 alone | 26,540 |
| Three reviewers, discussion, moderator, and editor | 258,357 |
| Saved single agent with manuscript tools | 302,652 |

The panel used 9.73 times the tokens of reviewer 1 and about 14.6% fewer than the
saved single agent on this paper. Scoring is excluded from these generation
figures. The saved single-agent run was reused. This is not a compute-matched
comparison or an estimate of monetary charges. Costs for incomplete papers
cannot be interpreted as completed-review costs, and missing usage is not zero.
The saved single agent's 302,652 recorded tokens include 253,824 cached input
tokens. Reviewer 1's 26,540 recorded tokens include zero cached input tokens.
Repeated context and cached input make these totals unsuitable as direct credit
or monetary-cost ratios, or as precise ratios of reasoning effort.

## Implication

This architecture produced more confirmed coverage than its prespecified
one-shot constituent on one paper. It has not demonstrated an advantage over
the saved single agent, and the three-paper test remains incomplete. Selection
still discarded a distinct concern that had survived discussion.

The saved outputs support examining why a broad concern was treated as already
covered. No new specialist, verifier, or extra debate round is justified by this
partial result. Completing the planned comparison would require explicitly
resuming failed inference in a documented new attempt, within a stated budget.
The current run and heartbeat are paused.

## Saved artifacts

Runtime evidence is under `runs/pra-three-reviewers-3paper-v1`:

- `report.json`: available scores, missing papers, and usage.
- `artifact_verification.json`: source, preservation, and concurrency checks.
- `work/nT89RltY10/generation.json`: complete findings and all stage selections.
- `work/UwcZEoNP19`: completed initial reviews and discussion responses.
- `manual_audit.json`: 15 unfilled candidate assessments from the completed paper.

The frozen runner and all failed-call records are preserved. No installed plugin
or production workflow was changed.
