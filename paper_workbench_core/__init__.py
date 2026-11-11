"""Compatibility name for the headless API, which now lives in peerreviewagents.engine.

The api, baseline and config submodules are aliases for the engine modules, so
``paper_workbench_core.api`` and ``peerreviewagents.engine.api`` are one object.
"""
from .api import (
    API_VERSION, ReviewRequest, capabilities, load_manuscript, evidence_registry,
    validate_review, run_review, review_request_from_preset,
    SavedDraftSynthesisRequest, run_saved_draft_synthesis,
)
from .config import CONFIG_VERSION, review_presets, resolved_review_config

__version__ = '0.2.0'
__all__ = ['API_VERSION', 'ReviewRequest', 'capabilities', 'load_manuscript',
           'evidence_registry', 'validate_review', 'run_review', 'CONFIG_VERSION',
           'review_presets', 'resolved_review_config', 'review_request_from_preset',
           'SavedDraftSynthesisRequest', 'run_saved_draft_synthesis']
