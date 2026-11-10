"""Moved to peerreviewagents.engine.calculator. This module is an alias for it."""
import sys

from peerreviewagents.engine import calculator as _engine

sys.modules[__name__] = _engine
