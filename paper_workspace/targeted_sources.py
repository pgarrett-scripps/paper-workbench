"""Moved to peerreviewagents.engine.targeted_sources. This module is an alias for it."""
import sys

from peerreviewagents.engine import targeted_sources as _engine

sys.modules[__name__] = _engine
