"""Moved to peerreviewagents.engine.manuscript_tools. This module is an alias for it."""
import sys

if __name__ == '__main__':
    import runpy
    runpy.run_module('peerreviewagents.engine.manuscript_tools', run_name='__main__', alter_sys=True)
else:
    from peerreviewagents.engine import manuscript_tools as _engine
    sys.modules[__name__] = _engine
