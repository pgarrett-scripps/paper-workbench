"""Versioned facade over the existing engine, with no duplicated pipeline."""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .config import get_review_preset, resolved_review_config, review_presets

API_VERSION = 'paper-workbench-core-v1'


def capabilities():
    """Advertise supported execution, without starting providers or the UI."""
    from paper_workspace.models import CODEX_MODELS
    return {'api_version': API_VERSION, 'artifact_version': 'paper-workbench-run-v1',
            'workflows': ['manuscript-only', 'independent', 'ensemble'], 'provider': 'codex',
            'configuration_version': 'paper-workbench-config-v1',
            'presets': list(review_presets()),
            'models': list(CODEX_MODELS), 'reasoning_effort': 'medium',
            'billing': 'verified_subscription_with_bounded_usage_policy',
            'tool_access': 'workflow-specific',
            'tool_access_by_workflow': {'manuscript-only': 'none',
                                        'independent': 'bounded_manuscript_tools',
                                        'ensemble': 'bounded_manuscript_tools'},
            'automatic_retries': False,
            'limitations': ['Manuscript-only mode has no review tools or external access.',
                           'Independent mode includes tools and is not a tool-free baseline.',
                           'Other providers and arbitrary models are not supported by this engine yet.',
                           'Evidence validation establishes provenance, not scientific correctness.']}


def load_manuscript(workspace):
    from paper_workspace.annotations import verify_workspace
    return verify_workspace(Path(workspace))


def evidence_registry(workspace, source_cards=()):
    from paper_workspace.evidence_handles import build_registry
    return build_registry(load_manuscript(workspace), list(source_cards))


def validate_review(workspace, response, review_id='external-review'):
    """Normalize a source-bound review without saving it or executing a model."""
    from paper_workspace.annotations import normalize_review
    return normalize_review(load_manuscript(workspace), response, review_id)


@dataclass(frozen=True)
class ReviewRequest:
    workspace: Path
    output: Path
    billing_confirmation: Path
    literature_cutoff: str
    workflow: Literal['manuscript-only', 'independent', 'ensemble'] = 'ensemble'
    model: str = 'gpt-5.6-terra'
    reviewers: int = 2
    token_budget: int = 750000
    scaffold_root: Path | None = None
    source_images: tuple[Path, ...] = field(default_factory=tuple)
    preset: str | None = None

    def __post_init__(self):
        from datetime import date
        if self.workflow not in capabilities()['workflows']:
            raise ValueError('Unsupported Paper Workbench workflow')
        if self.model not in capabilities()['models']:
            raise ValueError('Unsupported Paper Workbench model. No fallback is permitted.')
        if type(self.reviewers) is not int or not 1 <= self.reviewers <= 16:
            raise ValueError('Reviewer count must be between one and sixteen')
        if type(self.token_budget) is not int or self.token_budget <= 0:
            raise ValueError('Token launch budget must be a positive integer')
        if self.workflow == 'manuscript-only' and self.reviewers != 1:
            raise ValueError('Manuscript-only review requires exactly one reviewer')
        if self.preset is not None:
            get_review_preset(self.preset)
        date.fromisoformat(self.literature_cutoff)
        if Path(self.workspace).resolve() == Path(self.output).resolve():
            raise ValueError('Use a separate run output directory')


def run_review(request: ReviewRequest):
    """Explicit inference entry point. Importing or constructing requests is offline."""
    from paper_workspace.reviewer import review
    from paper_workspace.ensemble import observed_usage
    from paper_workspace.model_runtime import source_manifest
    from paper_workspace.storage import read, write, digest
    import paper_workspace
    if not isinstance(request, ReviewRequest):
        raise TypeError('Expected ReviewRequest')
    workspace, output = Path(request.workspace).resolve(), Path(request.output).resolve()
    if output.exists():
        raise FileExistsError('Use a new run directory. The public API never retries an existing run.')
    paper = load_manuscript(workspace)
    source_hash = digest((workspace/'manifest.json').read_bytes())
    resolved_config = resolved_review_config(request)
    if request.workflow == 'manuscript-only':
        from .baseline import run_manuscript_only
        run_manuscript_only(request, paper, resolved_config)
    else:
        review(workspace, output, request.billing_confirmation, request.literature_cutoff,
               mode=request.workflow, model=request.model, reviewers=request.reviewers,
               token_budget=request.token_budget, scaffold_root=request.scaffold_root,
               shared_images=request.source_images)
    engine = source_manifest(Path(paper_workspace.__file__).parent)
    core_engine = source_manifest(Path(__file__).parent)
    artifact = {'api_version': API_VERSION, 'artifact_version': 'paper-workbench-run-v1',
                'paper_id': paper['id'], 'source_manifest_sha256': source_hash,
                'workflow': request.workflow, 'model_requested': request.model,
                'resolved_configuration': resolved_config,
                'resolved_configuration_sha256': digest(json.dumps(resolved_config, sort_keys=True)),
                'engine_source': engine, 'core_source': core_engine,
                'editor_package': read(output/'editor-package.json'),
                'usage': observed_usage(output), 'output_directory': str(output),
                'limitation': 'A pipeline artifact is not a benchmark score. The benchmark owns blinding, grading and hidden answer keys.'}
    write(output/'core-artifact.json', artifact)
    return artifact


def review_request_from_preset(name, *, workspace, output, billing_confirmation,
                               literature_cutoff, model=None, token_budget=None,
                               scaffold_root=None, source_images=()):
    """Construct a request from one named preset, with explicit runtime overrides."""
    preset = get_review_preset(name)
    return ReviewRequest(
        workspace=Path(workspace), output=Path(output),
        billing_confirmation=Path(billing_confirmation), literature_cutoff=literature_cutoff,
        workflow=preset.workflow, model=preset.model if model is None else model,
        reviewers=preset.reviewers,
        token_budget=preset.token_budget if token_budget is None else token_budget,
        scaffold_root=scaffold_root, source_images=tuple(source_images), preset=name,
    )


@dataclass(frozen=True)
class StructuredRequest:
    """One tool-free structured subscription call, suitable for external graders."""
    output: Path
    billing_confirmation: Path
    model: str
    prompt: str
    schema: dict
    token_budget: int = 100000
    timeout_seconds: int = 900
    source_images: tuple[Path, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.model not in capabilities()['models']:
            raise ValueError('Unsupported subscription model. No fallback is permitted.')
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ValueError('A nonempty prompt is required')
        if not isinstance(self.schema, dict) or self.schema.get('type') != 'object':
            raise ValueError('An object JSON schema is required')
        for value in (self.token_budget, self.timeout_seconds):
            if type(value) is not int or value <= 0:
                raise ValueError('Call limits must be positive integers')
        if len(self.source_images) > 10 or any(not Path(path).is_file() for path in self.source_images):
            raise ValueError('Supply at most ten existing structured-call source images')


def run_structured(request: StructuredRequest):
    """Use the shared transport with subscription checks, no tools and no retry."""
    from paper_workspace.ensemble import _prepare, observed_usage
    from paper_workspace.model_runtime import model_call
    from paper_workspace.storage import write
    if not isinstance(request, StructuredRequest):
        raise TypeError('Expected StructuredRequest')
    output = Path(request.output).resolve()
    protocol = {'provider': 'codex', 'model': request.model, 'effort': 'medium',
                'held_out_runs_authorized': False, 'max_calls_per_condition': 1,
                'observed_token_stop': request.token_budget,
                'call_timeout_seconds': request.timeout_seconds, 'mode': 'structured',
                'max_source_images': 10, 'image_budget_version': 'evidence-v1'}
    _prepare(output, request.billing_confirmation, protocol)
    try:
        value = model_call(protocol, output, request.prompt, request.schema, tools=False,
                           label='structured', images=request.source_images)
        artifact = {'api_version': API_VERSION, 'model_requested': request.model,
                    'value': value, 'usage': observed_usage(output)}
        write(output / 'structured-artifact.json', artifact)
        return artifact
    finally:
        write(output / 'usage-summary.json', observed_usage(output))


def usage_summary(output):
    """Read durable usage receipts, including failed or interrupted workflows."""
    from paper_workspace.ensemble import observed_usage
    return observed_usage(Path(output))
