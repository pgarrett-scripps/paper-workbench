"""Moved to peerreviewagents.engine.evidence_tasks. This module is an alias for it."""
import sys

from peerreviewagents.engine import evidence_tasks as _engine

sys.modules[__name__] = _engine
