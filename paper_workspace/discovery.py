"""Moved to peerreviewagents.engine.discovery. This module is an alias for it."""
import sys

from peerreviewagents.engine import discovery as _engine

sys.modules[__name__] = _engine
