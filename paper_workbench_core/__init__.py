"""Public headless API shared by Paper Workbench and benchmark adapters."""
from .api import (
    API_VERSION, ReviewRequest, capabilities, load_manuscript, evidence_registry,
    validate_review, run_review,
)

__version__ = '0.1.0'
__all__ = ['API_VERSION', 'ReviewRequest', 'capabilities', 'load_manuscript',
           'evidence_registry', 'validate_review', 'run_review']
