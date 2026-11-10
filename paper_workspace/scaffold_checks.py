"""Moved to peerreviewagents.engine.scaffold_checks. This module is an alias for it."""
import sys

from peerreviewagents.engine import scaffold_checks as _engine

sys.modules[__name__] = _engine
