"""Moved to peerreviewagents.engine.table_evidence. This module is an alias for it."""
import sys

from peerreviewagents.engine import table_evidence as _engine

sys.modules[__name__] = _engine
