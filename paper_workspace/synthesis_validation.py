"""Moved to peerreviewagents.engine.synthesis_validation. This module is an alias for it."""
import sys

from peerreviewagents.engine import synthesis_validation as _engine

sys.modules[__name__] = _engine
