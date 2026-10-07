"""Public headless API shared by Paper Workbench and benchmark adapters."""
from .api import (
    API_VERSION, ReviewRequest, capabilities, load_manuscript, evidence_registry,
    validate_review, run_review, StructuredRequest, run_structured, usage_summary,
    review_request_from_preset,
)
from .config import CONFIG_VERSION, review_presets, resolved_review_config

__version__ = '0.1.1'
__all__ = ['API_VERSION', 'ReviewRequest', 'capabilities', 'load_manuscript',
           'evidence_registry', 'validate_review', 'run_review', 'StructuredRequest',
           'run_structured', 'usage_summary', 'CONFIG_VERSION', 'review_presets',
           'resolved_review_config', 'review_request_from_preset']
