"""Moved to peerreviewagents.engine.targeted_sources. This module is an alias for it."""
import sys

if __name__ == '__main__':
    import runpy
    runpy.run_module('peerreviewagents.engine.targeted_sources', run_name='__main__', alter_sys=True)
else:
    from peerreviewagents.engine import targeted_sources as _engine
    sys.modules[__name__] = _engine
