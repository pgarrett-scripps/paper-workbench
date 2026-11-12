"""Paper Workbench app: workspace server, revisions and exports.

PeerReviewAgents runs the review. The app starts one through
``peerreviewagents.review`` and reads the run folder it writes. The few
engine module names left in this package are aliases for the engine modules
that still exist, such as ``annotations`` and ``storage``.
"""
__version__ = '0.2.0'
