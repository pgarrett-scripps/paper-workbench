"""Versioned facade over the existing engine, with no duplicated pipeline."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

API_VERSION = 'paper-workbench-core-v1'


def capabilities():
    """Advertise supported execution, without starting providers or the UI."""
    return {'api_version': API_VERSION, 'artifact_version': 'paper-workbench-run-v1',
            'workflows': ['independent', 'ensemble'], 'provider': 'codex',
            'models': ['gpt-5.6-terra', 'gpt-5.6-sol'], 'reasoning_effort': 'medium',
            'billing': 'verified_subscription_without_paid_credits',
            'tool_access': 'bounded_manuscript_tools', 'automatic_retries': False,
            'limitations': ['Independent mode includes tools and is not a tool-free baseline.',
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
    workflow: Literal['independent', 'ensemble'] = 'ensemble'
    model: str = 'gpt-5.6-terra'
    reviewers: int = 2
    token_budget: int = 750000
    scaffold_root: Path | None = None
    source_images: tuple[Path, ...] = field(default_factory=tuple)

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
    review(workspace, output, request.billing_confirmation, request.literature_cutoff,
           mode=request.workflow, model=request.model, reviewers=request.reviewers,
           token_budget=request.token_budget, scaffold_root=request.scaffold_root,
           shared_images=request.source_images)
    engine = source_manifest(Path(paper_workspace.__file__).parent)
    artifact = {'api_version': API_VERSION, 'artifact_version': 'paper-workbench-run-v1',
                'paper_id': paper['id'], 'source_manifest_sha256': source_hash,
                'workflow': request.workflow, 'model_requested': request.model,
                'engine_source': engine, 'editor_package': read(output/'editor-package.json'),
                'usage': observed_usage(output), 'output_directory': str(output),
                'limitation': 'A pipeline artifact is not a benchmark score. The benchmark owns blinding, grading and hidden answer keys.'}
    write(output/'core-artifact.json', artifact)
    return artifact
