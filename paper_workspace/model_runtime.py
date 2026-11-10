"""Moved to peerreviewagents.engine.model_runtime. This module is an alias for it."""
import sys

from peerreviewagents.engine import model_runtime as _engine

sys.modules[__name__] = _engine
