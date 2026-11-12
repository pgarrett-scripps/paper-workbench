"""Paper Workbench app: workspace server, revisions and exports.

PeerReviewAgents runs the review. The app starts one through the engine's
public ``review_main``, the entry ``peerreview review`` uses, and reads the
run folder with ``read_run``. The storage, annotation and ingest helpers it
still needs are not public yet, so it imports them from ``peerreviewagents.engine``.
"""
__version__ = '0.2.0'
