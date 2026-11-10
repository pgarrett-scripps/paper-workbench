"""Moved to peerreviewagents.engine.source_packet. This module is an alias for it."""
import sys

from peerreviewagents.engine import source_packet as _engine

sys.modules[__name__] = _engine
