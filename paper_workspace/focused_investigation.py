"""Moved to peerreviewagents.engine.focused_investigation. This module is an alias for it."""
import sys

from peerreviewagents.engine import focused_investigation as _engine

sys.modules[__name__] = _engine
