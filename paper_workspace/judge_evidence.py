"""Moved to peerreviewagents.engine.judge_evidence. This module is an alias for it."""
import sys

from peerreviewagents.engine import judge_evidence as _engine

sys.modules[__name__] = _engine
