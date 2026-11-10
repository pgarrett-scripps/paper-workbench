"""Moved to peerreviewagents.engine.source_adapters_extra. This module is an alias for it."""
import sys

from peerreviewagents.engine import source_adapters_extra as _engine

sys.modules[__name__] = _engine
