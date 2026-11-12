"""Show a PeerReviewAgents run folder in the viewer.

``paper-workbench review paper.pdf RUN`` writes the imported manuscript to
``RUN/manuscript`` and the review to ``RUN/review``. The engine's ``read_run``
reads the run, finished or stopped, and names any file it could not read. This
module adds only what the app owns: which manuscript a served path names, the
check that the run reviewed this version of it, and the review shape the
viewer, the decisions and ``export_draft`` read. Nothing here makes a model
call or writes to the run.
"""
import re
from collections import Counter
from pathlib import Path

from peerreviewagents import MANUSCRIPT_DIRECTORY, read_run
from peerreviewagents import locate_run, NotARunFolder

RUN_REVIEW_ID = 'run'
AUDIT_LIMIT = 400_000
FINDING_UID = re.compile(r'[A-Za-z0-9_-]{1,64}')


class RunError(ValueError):
    """A run folder the viewer cannot open, with a message for the person who ran it."""


def recorded(review):
    """The engine's reading of a run. A symlinked run file is refused in plain words."""
    try:
        return read_run(review)
    except ValueError as exc:
        raise RunError(str(exc)) from None


def locate(path):
    """Split a served path into the manuscript workspace and the run's review folder.

    A run folder, or the review folder inside it, gives both. A workspace
    gives itself, and the review folder is ``None``. A path that is neither,
    or a run that stopped before it imported the manuscript, raises
    :class:`RunError` with a plain message.
    """
    path = Path(path).resolve()
    try:
        root, review = locate_run(path)
    except NotARunFolder:
        if not (path / 'manifest.json').is_file():
            raise RunError(f'{path} is neither a manuscript workspace nor a run folder') from None
        return path, None
    except ValueError as exc:
        raise RunError(str(exc)) from None
    manuscript = root / MANUSCRIPT_DIRECTORY
    if not (manuscript / 'paper.json').is_file():
        run = recorded(review)
        raise RunError(f'The run in {root} stopped before it imported the manuscript, so there is '
                       f'nothing to show. Status: {run["status"]}. Cause: {run["cause"] or "not recorded"}')
    return manuscript, review


def check_version(run, paper):
    """Refuse a run that reviewed another version of this manuscript.

    The run names the manuscript it reviewed, and each finding pins its block
    by hash, so a run that stopped before naming it is still checked.
    """
    identity = run['identity']
    blocks = {block['id']: block.get('sha256') for block in paper['blocks']}
    same = ((identity['paper_id'], identity['source_sha256']) == (paper['id'], paper['source_sha256'])
            and all(blocks.get(row.get('block_id')) == row['block_sha256']
                    for row in run['findings'] if row.get('block_sha256') is not None))
    if not same:
        raise RunError('The run reviewed a different manuscript version')


def audit_texts(paths):
    """Each specialist's audit report, by track, as plain text."""
    texts = {}
    for track, path in paths.items():
        path = Path(path)
        if not path.is_file():
            continue
        with path.open('rb') as stream:
            data = stream.read(AUDIT_LIMIT + 1)
        text = data[:AUDIT_LIMIT].decode('utf-8', errors='replace')
        if len(data) > AUDIT_LIMIT:
            text += f'\n\n[The viewer shows the first {AUDIT_LIMIT:,} bytes of this report.]'
        texts[track] = text
    return texts


def run_review(review, paper):
    """The run as a review that the viewer, the decisions and ``export_draft`` read.

    Body findings come first, then the editor's appendix, each marked with its
    ``section``. A run with no editor package shows its recorded findings. A
    finding's ``id`` is its ``finding_uid``, because the engine's own ``id``
    repeats across reviewers.
    """
    run = recorded(review)
    check_version(run, paper)
    findings = ([{**row, 'section': 'body'} for row in run['body']]
                + [{**row, 'section': 'appendix'} for row in run['appendix']])
    uids = [row.get('finding_uid') for row in findings]
    unique = len(set(uids)) == len(uids) and all(isinstance(uid, str) and FINDING_UID.fullmatch(uid) for uid in uids)
    for number, row in enumerate(findings, 1):
        row['source_id'] = row.get('id')
        row['id'] = row['finding_uid'] if unique else f'{RUN_REVIEW_ID}-{number}'
        row['number'] = number
    edited = run['findings_source'] == 'editor-package'
    stages = run['stages'] or {}
    none_found = list(stages.get('none_found') or [])
    per_slot = Counter(row.get('slot') for row in findings)
    view = {
        'arm': run['identity']['arm'],
        'reviewer_count': run['identity']['reviewers'],
        'workflow_version': run['identity']['workflow_version'],
        'status': run['status'],
        'cause': run['cause'],
        'note': run['note'],
        'problems': run['problems'],
        'publishable': run['publishable'],
        'not_publishable_reasons': run['not_publishable_reasons'],
        'edited': edited,
        'escalated_count': len(run['escalations']),
        'review_guard_status': run['guard_status'],
        'quarantined_findings_count': run['counts']['quarantined'],
        'findings_delivered': run['counts']['findings_delivered'],
        'missing_stages': list(stages.get('missing') or []),
        'none_found': none_found,
        'agents': [{**row, 'findings': per_slot.get(row.get('slot'), 0), 'none_found': row.get('slot') in none_found}
                   for row in run['agents']],
        'findings_by_track': dict(Counter(row['track'] for row in findings if row.get('track'))),
        'verdict': run['verdict'],
        'escalation_rulings': run['escalation_rulings'],
        'limitations': run['limitations'],
        'audits': audit_texts(run['reports']['audits']),
        'tokens_total': run['runtime']['tokens_total'],
        'wall_seconds': run['runtime']['wall_seconds'],
    }
    if edited:
        summary = run['summary'] or 'The editor wrote no summary.'
    elif run['cause']:
        summary = f'The run stopped before the editor wrote its package: {run["cause"]}'
    elif run['complete']:
        summary = 'The run finished without an editor package.'
    else:
        summary = f'The run has not written an editor package. Its last recorded status is {run["status"]}.'
    return {'id': RUN_REVIEW_ID, 'paper_id': paper['id'], 'source_sha256': paper['source_sha256'],
            'summary': summary, 'findings': findings, 'run': view}
