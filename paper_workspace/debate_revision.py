"""Moved to peerreviewagents.engine.debate_revision. This module is an alias for it."""
import sys

from peerreviewagents.engine import debate_revision as _engine

sys.modules[__name__] = _engine
