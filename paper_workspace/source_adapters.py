"""Moved to peerreviewagents.engine.source_adapters. This module is an alias for it."""
import sys

from peerreviewagents.engine import source_adapters as _engine

sys.modules[__name__] = _engine
