"""Paper Workbench app: workspace server, revisions and exports.

PeerReviewAgents runs the review. The app starts one through the engine's
public ``review_main``, the entry ``peerreview review`` uses, and reads the
run folder with ``read_run``. The storage, annotation and ingest helpers it
also needs come from the public ``peerreviewagents.workspace``, and no module
imports an engine name that is not public.
"""
__version__ = '0.2.0'
