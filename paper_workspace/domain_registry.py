"""Moved to peerreviewagents.engine.domain_registry. This module is an alias for it."""
import sys

from peerreviewagents.engine import domain_registry as _engine

sys.modules[__name__] = _engine
