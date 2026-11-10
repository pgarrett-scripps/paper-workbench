"""Moved to peerreviewagents.engine.api. This module is an alias for it."""
import sys

from peerreviewagents.engine import api as _engine

sys.modules[__name__] = _engine
