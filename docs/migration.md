# Migration from In Silico

Paper Workbench begins as a source extraction, not a rename of the journal or of PeerReviewAgents. The original repositories and local working files remain intact.

The first commit preserves the extracted engine, app resources, domain packages, tests, development experiments and results documents. These source files had not yet been committed in In Silico. `migration/source-snapshot.json` records the original repository commit and hashes of each extracted file, including the untracked implementation. Packaging and the public core API are a separate commit.

The local extraction snapshot is preserved at `/home/ty/Repos/insilico/tmp/paper-workbench-source-snapshot.tar.gz`. Original run artifacts remain at `/home/ty/Repos/insilico/runs`. They contain source manuscripts, model responses, cache data and evaluation records. They are not included in the GitHub repository. Development protocols and results, including negative results, are retained under `docs/`.

The benchmark agent owns `benchmarks/peer_review` in In Silico and that directory is not part of this extraction. Its older PeerReviewAgents backend remains a distinct workflow. It can depend on a pinned Paper Workbench commit through the public core API when the supported execution conditions fit.

Historical experiment scripts remain available for provenance. Some contain absolute paths, source hashes and model conditions from earlier runs. They must not be treated as fresh portable benchmark commands or silently rewritten to rerun prior studies. Installable runtime code is independent of those experiments.

The original MIT code license and CC BY documentation attribution remain in LICENSE. Third-party manuscripts and private drafts are not transferred into repository history.

New implementation work should use the Paper Workbench checkout. In Silico still serves its existing journal workflow. Its source copies are retained temporarily to avoid breaking the benchmark agent and existing local studies. They are not a second development target for the extracted engine.
