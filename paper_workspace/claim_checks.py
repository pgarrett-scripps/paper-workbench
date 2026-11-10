"""Moved to peerreviewagents.engine.claim_checks. This module is an alias for it."""
import sys

from peerreviewagents.engine import claim_checks as _engine

sys.modules[__name__] = _engine
