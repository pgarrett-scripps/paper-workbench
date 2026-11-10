"""Moved to peerreviewagents.engine.baseline. This module is an alias for it."""
import sys

from peerreviewagents.engine import baseline as _engine

sys.modules[__name__] = _engine
