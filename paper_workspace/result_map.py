"""Moved to peerreviewagents.engine.result_map. This module is an alias for it."""
import sys

from peerreviewagents.engine import result_map as _engine

sys.modules[__name__] = _engine
