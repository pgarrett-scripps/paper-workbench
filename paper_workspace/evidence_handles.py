"""Moved to peerreviewagents.engine.evidence_handles. This module is an alias for it."""
import sys

from peerreviewagents.engine import evidence_handles as _engine

sys.modules[__name__] = _engine
