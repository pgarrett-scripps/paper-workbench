"""Moved to peerreviewagents.engine.run_report. This module is an alias for it."""
import sys

from peerreviewagents.engine import run_report as _engine

sys.modules[__name__] = _engine
