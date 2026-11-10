"""Moved to peerreviewagents.engine.ensemble_references. This module is an alias for it."""
import sys

from peerreviewagents.engine import ensemble_references as _engine

sys.modules[__name__] = _engine
