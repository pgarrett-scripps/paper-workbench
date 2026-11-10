"""Moved to peerreviewagents.engine.ingest. This module is an alias for it."""
import sys

from peerreviewagents.engine import ingest as _engine

sys.modules[__name__] = _engine
