"""Moved to peerreviewagents.engine.ensemble_debate. This module is an alias for it."""
import sys

from peerreviewagents.engine import ensemble_debate as _engine

sys.modules[__name__] = _engine
