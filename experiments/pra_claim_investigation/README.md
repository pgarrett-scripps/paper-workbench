# Claim investigation experiment

This prototype changes the work agents perform. They reconstruct claims and
method steps, execute bounded arithmetic or logical checks, investigate separate
dependencies, exchange evidence, and adjudicate an immutable concern ledger.
It does not modify the installed PRA plugin or previous experiment artifacts.

The comparator is a sequential single-controller workflow with complete explicit
notes carried across the same six stages. Both use the same shared map, tools,
schemas, final limits, Sol model, and medium effort. CLI calls are fresh sessions.
This does not preserve hidden reasoning as a native continuing session would.

Run offline tests before freezing:

```sh
/home/ty/Repos/PeerReviewAgents/.venv/bin/python -m unittest discover -s experiments/pra_claim_investigation -p 'test_*.py' -v
```

Prepare with `study.py prepare`. Record current subscription authentication and
zero paid credit status in the run root's `billing_confirmation.json`. Launch
`study.py run` with the same Python interpreter. Use `study.py summarize` for
analysis without inference. Frozen source changes require a new experiment root.

The runner stages manuscript text only. Its local MCP server exposes manuscript
reading, literal search, and a bounded expression evaluator. It has no shell,
arbitrary Python evaluation, external retrieval, public review access, or delegation.
Successful calculations have deterministic receipts validated against actual logs.
Receipts prove expression execution, not scientific applicability.

Full protocol and decision rules: `docs/pra-claim-investigation-plan.md`.
