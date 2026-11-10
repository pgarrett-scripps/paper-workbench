"""Moved to peerreviewagents.engine.investigation. This module is an alias for it."""
import sys

from peerreviewagents.engine import investigation as _engine

sys.modules[__name__] = _engine
