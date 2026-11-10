"""Moved to peerreviewagents.engine.ensemble. This module is an alias for it."""
import sys

from peerreviewagents.engine import ensemble as _engine

sys.modules[__name__] = _engine
