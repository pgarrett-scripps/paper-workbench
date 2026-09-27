# Matched strong-reviewer experiment

The fixed protocol is documented in `docs/pra-matched-reviewer-plan.md`.
Reviewer 1 reuses the saved strong tool-using review. New reviewers 2 and 3 use
its exact prompt, output schema, model, effort, and manuscript tools. Both editor
branches receive the same review ledger. Only one receives the focused discussion.

Offline checks:

```sh
/home/ty/Repos/PeerReviewAgents/.venv/bin/python -m unittest discover -s experiments/pra_matched_reviewers -p 'test_*.py' -v
```

Prepare and freeze:

```sh
python3 experiments/pra_matched_reviewers/study.py prepare
```

After verifying subscription authentication and zero paid credits, record the
current check in the run root's `billing_confirmation.json`, then execute:

```sh
python3 experiments/pra_matched_reviewers/study.py run
```

The root is `runs/pra-matched-reviewers-3paper-v1`. A process lock prevents duplicate
runners. Stream-disconnection retries are limited by the frozen protocol and are
saved as separate attempts. Content and validation failures are not retried.
Do not edit frozen source. Preserve all raw reports, findings, branches, and failures.

Recompute the available summary without inference:

```sh
python3 experiments/pra_matched_reviewers/study.py summarize
```
