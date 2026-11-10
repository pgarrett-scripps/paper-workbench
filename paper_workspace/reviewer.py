"""Moved to peerreviewagents.engine.reviewer. This module is an alias for it."""
import sys

from peerreviewagents.engine import reviewer as _engine

sys.modules[__name__] = _engine
