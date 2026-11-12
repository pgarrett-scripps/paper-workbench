"""Read a PeerReviewAgents run folder for the viewer.

``paper-workbench review paper.pdf RUN`` writes the imported manuscript to
``RUN/manuscript`` and the review to ``RUN/review``. The viewer opens a finished
run and also one the starter stopped early, from a token ceiling, a timeout, a
rate limit or a session error, and shows what that run recorded. Nothing here
makes a model call or writes to the run.

``read_run`` reads what every run records, with the keys the engine's planned
public ``read_run`` returns, so switching to it is one import.
"""
import json
import re
from pathlib import Path

from peerreviewagents.engine.storage import read
from peerreviewagents.plugin.server import MANUSCRIPT_DIRECTORY, RUN_DIRECTORY

RUN_REVIEW_ID = 'run'
# The engine's finished statuses. Its planned public status constants replace these.
COMPLETE = ('complete', 'complete-without-findings')
# The starter writes startup.json and runtime.json first, the server progress.json,
# and write_review or mark_blocked protocol.json. Any one of them marks a run.
RUN_MARKERS = ('protocol.json', 'progress.json', 'runtime.json', 'startup.json')
AUDIT = re.compile(r'audit_([a-z0-9-]{1,40})\.md')
AUDIT_LIMIT = 400_000
FINDING_UID = re.compile(r'[A-Za-z0-9_-]{1,64}')
RUN_KEYS = ('synthesis_policy', 'workflow_version', 'review_guard_status', 'findings_delivered',
            'quarantined_findings_count', 'escalated_count', 'findings_by_track', 'reviewer_count')


class RunError(ValueError):
    """A run folder the viewer cannot open, with a message for the person who ran it."""


def is_run(review):
    return review.is_dir() and any((review / name).is_file() for name in RUN_MARKERS)


def locate(path):
    """Split a served path into the manuscript workspace and the run's review folder.

    A run folder, or the review folder inside it, gives both. Any other path
    is a workspace with no run, and the review folder is ``None``. A run that
    stopped before it imported the manuscript raises :class:`RunError` with
    the cause the run recorded.
    """
    path = Path(path).resolve()
    for run in (path, path.parent):
        review = run / RUN_DIRECTORY
        if review in (path, path / RUN_DIRECTORY) and is_run(review):
            manuscript = run / MANUSCRIPT_DIRECTORY
            if not (manuscript / 'paper.json').is_file():
                recorded = read_run(review)
                raise RunError(f'The run in {run} stopped before it imported the manuscript, so there is '
                               f'nothing to show. Status: {recorded["status"] or "not recorded"}. '
                               f'Cause: {recorded["error"] or "not recorded"}')
            return manuscript, review
    return path, None


def run_file(review, name):
    """A file the run wrote directly inside its review folder, or ``None`` when it is absent.

    The viewer never follows a symbolic link, and says so rather than acting
    as though the file were missing.
    """
    path = review / name
    if path.is_symlink():
        raise RunError(f'{path} is a symbolic link. The viewer reads only files the run wrote in place.')
    if not path.exists():
        return None
    if not path.is_file() or path.resolve().parent != review.resolve():
        raise RunError(f'{path} is not a file the run wrote in its review folder.')
    return path


def run_json(review, name):
    path = run_file(review, name)
    return read(path) if path else None


def latest_per_uid(rows):
    """The latest row of each finding, in the order findings first appeared, as the engine pools them."""
    latest, order = {}, []
    for index, row in enumerate(rows):
        uid = row.get('finding_uid')
        key = uid if isinstance(uid, str) and uid else ('row', index)
        if key not in latest:
            order.append(key)
        latest[key] = row
    return [latest[key] for key in order]


def recorded_findings(review):
    """The server's finding ledger. It has one row per submission, so a finding can repeat."""
    path = run_file(review, 'findings.jsonl')
    if not path:
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            raise RunError(f'Line {number} of {path} is not a JSON record.') from None
        if not isinstance(row, dict):
            raise RunError(f'Line {number} of {path} is not a JSON object.')
        rows.append(row)
    return latest_per_uid(rows)


def audits(review):
    """Each specialist's audit report, by track, as plain text."""
    reports = {}
    for path in sorted(review.iterdir()):
        match = AUDIT.fullmatch(path.name)
        if not match or not run_file(review, path.name):
            continue
        with path.open('rb') as stream:
            data = stream.read(AUDIT_LIMIT + 1)
        text = data[:AUDIT_LIMIT].decode('utf-8', errors='replace')
        if len(data) > AUDIT_LIMIT:
            text += f'\n\n[The viewer shows the first {AUDIT_LIMIT:,} bytes of this report.]'
        reports[match.group(1)] = text
    return reports


def read_run(review):
    """What a run recorded, whether it finished or stopped.

    ``status`` and ``error`` come from the server's progress file, then the
    starter's runtime file, then the start-up probe. ``findings`` is the
    ledger with the latest row per ``finding_uid``. ``manifest`` is the
    manuscript the run reviewed, or ``None`` when the run stopped before it
    wrote one. ``audits`` maps each specialist track to its report.
    """
    review = Path(review)
    progress = run_json(review, 'progress.json') or {}
    runtime = run_json(review, 'runtime.json') or {}
    startup = run_json(review, 'startup.json') or {}
    manifest = run_json(review, 'manifest.json')
    problems = startup.get('problems') or []
    error = progress.get('error') or runtime.get('blocked_reason') or (
        'the start-up probe failed: ' + ', '.join(map(str, problems)) if problems else None)
    status = progress.get('status') or runtime.get('status') or ('blocked' if problems else None)
    return {
        'status': status,
        'error': error,
        'findings': recorded_findings(review),
        'manifest': {'paper_id': manifest.get('paper_id'), 'source_sha256': manifest.get('source_sha256')}
        if manifest else None,
        'audits': audits(review),
    }


def check_version(manifest, findings, paper):
    """Refuse a run that reviewed another version of this manuscript.

    The manifest names the manuscript. A run that stopped before writing one
    still pins each finding to a block hash, so those are checked instead.
    """
    if manifest is not None:
        same = (manifest['paper_id'], manifest['source_sha256']) == (paper['id'], paper['source_sha256'])
    else:
        blocks = {block['id']: block.get('sha256') for block in paper['blocks']}
        same = all(blocks.get(row['block_id']) == row.get('block_sha256')
                   for row in findings if row.get('block_id') is not None)
    if not same:
        raise RunError('The run reviewed a different manuscript version')


def run_review(review, paper):
    """The run as a review that the viewer, the decisions and ``export_draft`` read.

    Body findings come first, then the editor's appendix, each marked with its
    ``section``. A run with no editor package shows its recorded findings. A
    finding's ``id`` is its ``finding_uid``, because the engine's own ``id``
    repeats across reviewers.
    """
    review = Path(review)
    recorded = read_run(review)
    package = run_json(review, 'editor-package.json')
    protocol = run_json(review, 'protocol.json') or {}
    progress = run_json(review, 'progress.json') or {}
    runtime = run_json(review, 'runtime.json') or {}
    edited = package is not None
    package = package or {}
    if edited:
        findings = ([{**row, 'section': 'body'} for row in package.get('findings') or []]
                    + [{**row, 'section': 'appendix'} for row in package.get('appendix') or []])
    else:
        findings = [{**row, 'section': 'body'} for row in recorded['findings']]
    check_version(recorded['manifest'], findings, paper)
    uids = [row.get('finding_uid') for row in findings]
    unique = len(set(uids)) == len(uids) and all(isinstance(uid, str) and FINDING_UID.fullmatch(uid) for uid in uids)
    for number, row in enumerate(findings, 1):
        row['source_id'] = row.get('id')
        row['id'] = row['finding_uid'] if unique else f'{RUN_REVIEW_ID}-{number}'
        row['number'] = number
    stages = progress.get('stages') or {}
    run = {key: package.get(key) for key in RUN_KEYS}
    run.update({
        'arm': package.get('arm') or protocol.get('arm') or progress.get('arm'),
        'reviewer_count': run['reviewer_count'] or protocol.get('reviewers') or progress.get('reviewers'),
        'status': recorded['status'],
        'error': recorded['error'],
        'edited': edited,
        'missing_stages': stages.get('missing') or [],
        'none_found': stages.get('none_found') or [],
        'reviewer_provenance': package.get('reviewer_provenance') or [],
        'verdict': package.get('verdict'),
        'escalation_rulings': package.get('escalation_rulings') or [],
        'limitations': package.get('limitations') or [],
        'audits': recorded['audits'],
        'tokens_total': runtime.get('tokens_total'),
        'wall_seconds': runtime.get('wall_seconds'),
    })
    if edited:
        summary = package.get('summary') or 'The editor wrote no summary.'
    elif recorded['error']:
        summary = f'The run stopped before the editor wrote its package: {recorded["error"]}'
    elif recorded['status'] in COMPLETE:
        summary = 'The run finished without an editor package.'
    else:
        summary = (f'The run has not written an editor package. Its last recorded status is '
                   f'{recorded["status"] or "unknown"}.')
    return {'id': RUN_REVIEW_ID, 'paper_id': paper['id'], 'source_sha256': paper['source_sha256'],
            'summary': summary, 'findings': findings, 'run': run}
