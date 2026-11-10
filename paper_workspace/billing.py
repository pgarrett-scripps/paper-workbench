"""Moved to peerreviewagents.engine.billing. This module is an alias for it."""
import sys

from peerreviewagents.engine import billing as _engine

sys.modules[__name__] = _engine
