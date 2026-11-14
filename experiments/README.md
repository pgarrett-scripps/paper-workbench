# Earlier studies

These folders keep the protocols, READMEs and result files of studies run on the 0.8 engine and earlier. The manuscript repository may cite them.

The Python runners that produced them are deleted. They imported engine modules that no release since 0.8.0 has, so they could not run here. Git history keeps them. To read one, check out the last commit that had it:

```bash
git log --diff-filter=D --format=%h -1 -- experiments/pra_prospective/core.py
git show <that commit>^:experiments/pra_prospective/core.py
```

Study code written for the 0.8 engine runs only against the PeerReviewAgents `v0.8.0` release.
