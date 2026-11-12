"""Read a finished PeerReviewAgents run folder for the viewer.

``peerreview review paper.pdf RUN`` (or ``paper-workbench review``) writes the
imported manuscript to ``RUN/manuscript`` and the review to ``RUN/review``. The
viewer shows the editor's package from the review folder against the
manuscript it was run on. Nothing here makes a model call or writes to the run.
"""
import json
import re
from pathlib import Path

from peerreviewagents.engine.storage import read
from peerreviewagents.plugin.server import MANUSCRIPT_DIRECTORY, RUN_DIRECTORY

RUN_REVIEW_ID = 'run'
AUDIT = re.compile(r'audit_([a-z0-9-]{1,40})\.md')
AUDIT_LIMIT = 400_000
FINDING_UID = re.compile(r'[A-Za-z0-9_-]{1,64}')
RUN_KEYS = ('synthesis_policy', 'workflow_version', 'review_guard_status', 'findings_delivered',
            'quarantined_findings_count', 'escalated_count', 'findings_by_track', 'reviewer_count')


def locate(path):
    """Split a served path into the manuscript workspace and the run's review folder.

    A run folder, or the review folder inside it, gives both. Any other path
    is a workspace with no run, and the review folder is ``None``.
    """
    path = Path(path).resolve()
    for run in (path, path.parent):
        review = run / RUN_DIRECTORY
        if review in (path, path / RUN_DIRECTORY) and (review / 'protocol.json').is_file():
            manuscript = run / MANUSCRIPT_DIRECTORY
            if not (manuscript / 'paper.json').is_file():
                raise ValueError(f'The run in {run} has no imported manuscript. '
                                 f'It stopped before import, see {review / "progress.json"}')
            return manuscript, review
    return path, None


def run_file(review, name):
    """A file directly inside the review folder, or ``None``. Symlinks are never followed."""
    path = review / name
    if path.is_symlink() or not path.is_file() or path.resolve().parent != review.resolve():
        return None
    return path


def run_json(review, name):
    path = run_file(review, name)
    return read(path) if path else None


def recorded_findings(review):
    """The server's finding ledger, for a run that stopped before the editor wrote a package."""
    path = run_file(review, 'findings.jsonl')
    if not path:
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def audits(review):
    """Each specialist's audit report, by track, as plain text."""
    reports = {}
    for path in sorted(review.iterdir()):
        match = AUDIT.fullmatch(path.name)
        if match and run_file(review, path.name) and path.stat().st_size <= AUDIT_LIMIT:
            reports[match.group(1)] = path.read_text(encoding='utf-8', errors='replace')
    return reports


def run_review(review, paper):
    """The run as a review that the viewer, the decisions and ``export_draft`` read.

    Body findings come first, then the editor's appendix, each marked with its
    ``section``. A finding's ``id`` is its ``finding_uid``, because the engine's
    own ``id`` repeats across reviewers. The run's manifest must name this
    manuscript, so no finding is anchored to a different version.
    """
    review = Path(review)
    package = run_json(review, 'editor-package.json') or {}
    protocol = run_json(review, 'protocol.json') or {}
    progress = run_json(review, 'progress.json') or {}
    runtime = run_json(review, 'runtime.json') or {}
    if package:
        findings = ([{**row, 'section': 'body'} for row in package.get('findings') or []]
                    + [{**row, 'section': 'appendix'} for row in package.get('appendix') or []])
    else:
        findings = [{**row, 'section': 'body'} for row in recorded_findings(review)]
    if findings:
        manifest = run_json(review, 'manifest.json') or {}
        if (manifest.get('paper_id'), manifest.get('source_sha256')) != (paper['id'], paper['source_sha256']):
            raise ValueError('The run reviewed a different manuscript version')
    uids = [row.get('finding_uid') for row in findings]
    unique = len(set(uids)) == len(uids) and all(isinstance(uid, str) and FINDING_UID.fullmatch(uid) for uid in uids)
    for number, row in enumerate(findings, 1):
        row['source_id'] = row.get('id')
        row['id'] = row['finding_uid'] if unique else f'{RUN_REVIEW_ID}-{number}'
        row['number'] = number
    stages = progress.get('stages') or {}
    run = {key: package.get(key) for key in RUN_KEYS}
    run.update({
        'arm': package.get('arm') or protocol.get('arm'),
        'reviewer_count': run['reviewer_count'] or protocol.get('reviewers'),
        'status': progress.get('status') or runtime.get('status'),
        'error': progress.get('error') or runtime.get('blocked_reason'),
        'edited': bool(package),
        'missing_stages': stages.get('missing') or [],
        'none_found': stages.get('none_found') or [],
        'reviewer_provenance': package.get('reviewer_provenance') or [],
        'verdict': package.get('verdict'),
        'escalation_rulings': package.get('escalation_rulings') or [],
        'limitations': package.get('limitations') or [],
        'audits': audits(review),
        'tokens_total': runtime.get('tokens_total'),
        'wall_seconds': runtime.get('wall_seconds'),
    })
    summary = package.get('summary') or (
        f'The run stopped before the editor wrote its package: {run["error"]}' if run['error']
        else 'The editor has not written a package for this run.')
    return {'id': RUN_REVIEW_ID, 'paper_id': paper['id'], 'source_sha256': paper['source_sha256'],
            'summary': summary, 'findings': findings, 'run': run}
