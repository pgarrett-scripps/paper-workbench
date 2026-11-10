"""Moved to peerreviewagents.engine.debate_epistemics. This module is an alias for it."""
import sys

from peerreviewagents.engine import debate_epistemics as _engine

sys.modules[__name__] = _engine
