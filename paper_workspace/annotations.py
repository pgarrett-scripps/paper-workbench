"""Moved to peerreviewagents.engine.annotations. This module is an alias for it."""
import sys

from peerreviewagents.engine import annotations as _engine

sys.modules[__name__] = _engine
