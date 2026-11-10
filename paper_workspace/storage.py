"""Moved to peerreviewagents.engine.storage. This module is an alias for it."""
import sys

from peerreviewagents.engine import storage as _engine

sys.modules[__name__] = _engine
