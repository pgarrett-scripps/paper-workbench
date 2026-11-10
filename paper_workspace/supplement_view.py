"""Moved to peerreviewagents.engine.supplement_view. This module is an alias for it."""
import sys

from peerreviewagents.engine import supplement_view as _engine

sys.modules[__name__] = _engine
