"""Moved to peerreviewagents.engine.external_evidence. This module is an alias for it."""
import sys

from peerreviewagents.engine import external_evidence as _engine

sys.modules[__name__] = _engine
