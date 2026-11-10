"""Moved to peerreviewagents.engine.debate_presentation. This module is an alias for it."""
import sys

from peerreviewagents.engine import debate_presentation as _engine

sys.modules[__name__] = _engine
