# Three general reviewers

Read `docs/pra-three-reviewer-plan.md` for the fixed experiment and decision rule.
The prototype makes three independent general reviews, three simultaneous
discussion responses, a moderator report, and an editor decision per manuscript.
The model and effort are pinned in `protocol.json`.

Run offline checks from the repository root:

```sh
/home/ty/Repos/PeerReviewAgents/.venv/bin/python -m unittest discover -s experiments/pra_three_reviewers -p 'test_*.py' -v
```

Prepare immutable inputs and freeze runner hashes:

```sh
python3 experiments/pra_three_reviewers/study.py prepare
```

After verifying ChatGPT authentication and recording current absence of paid
credits in `billing_confirmation.json` under the run root, start:

```sh
python3 experiments/pra_three_reviewers/study.py run
```

The root is `runs/pra-three-reviewers-3paper-v1`. Preserve all failed responses.
No model calls are retried automatically. The account runner is reused from the
frozen original pilot without changing its source. The installed plugin and all
earlier experiments remain unchanged.

`report.json` contains available results and missing outputs. `work` preserves
every initial review, discussion response, moderator report, editorial disposition,
source evidence, anonymous scoring input, response, and usage record. The human
audit package contains no fabricated human ratings.

Recompute the report without model calls:

```sh
python3 experiments/pra_three_reviewers/study.py summarize
```
