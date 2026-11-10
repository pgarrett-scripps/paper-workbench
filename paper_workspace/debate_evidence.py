"""Moved to peerreviewagents.engine.debate_evidence. This module is an alias for it."""
import sys

from peerreviewagents.engine import debate_evidence as _engine

sys.modules[__name__] = _engine
