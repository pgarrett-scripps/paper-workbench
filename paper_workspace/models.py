"""Moved to peerreviewagents.engine.models. This module is an alias for it."""
import sys

from peerreviewagents.engine import models as _engine

sys.modules[__name__] = _engine
