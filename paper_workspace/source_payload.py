"""Moved to peerreviewagents.engine.source_payload. This module is an alias for it."""
import sys

from peerreviewagents.engine import source_payload as _engine

sys.modules[__name__] = _engine
