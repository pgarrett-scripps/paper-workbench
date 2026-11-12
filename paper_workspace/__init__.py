"""Paper Workbench app: workspace server, revisions and exports.

PeerReviewAgents runs the review. The app starts one through the engine's
``peerreview review`` entry and reads the run folder it writes. It imports
engine modules directly from ``peerreviewagents.engine``.
"""
__version__ = '0.2.0'
