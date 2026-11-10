"""Moved to peerreviewagents.engine.investigation_policy. This module is an alias for it."""
import sys

from peerreviewagents.engine import investigation_policy as _engine

sys.modules[__name__] = _engine
