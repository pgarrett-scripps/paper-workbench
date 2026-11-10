"""Moved to peerreviewagents.engine.config. This module is an alias for it."""
import sys

from peerreviewagents.engine import config as _engine

sys.modules[__name__] = _engine
