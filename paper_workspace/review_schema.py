"""Moved to peerreviewagents.engine.review_schema. This module is an alias for it."""
import sys

from peerreviewagents.engine import review_schema as _engine

sys.modules[__name__] = _engine
