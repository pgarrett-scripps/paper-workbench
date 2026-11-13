"""Show a PeerReviewAgents run folder in the viewer.

``paper-workbench review paper.pdf RUN`` writes the imported manuscript to
``RUN/manuscript`` and the review to ``RUN/review``. The engine's ``read_run``
reads the run, finished or stopped, and names any file it could not read. This
module adds only what the app owns: which manuscript a served path names, the
check that the run reviewed this version of it, and the review shape the
viewer, the decisions and ``export_draft`` read. Nothing here makes a model
call or writes to the run.

The citation ledger's rows come from the engine's ``read_citation_ledger``,
which keeps the last row written for each ``row_id`` and gives them in reading
order, ``ref:r2`` before ``ref:r10``. It is called without the fetched
abstracts and full text, because the panel never shows them.
"""
import re
from collections import Counter
from pathlib import Path

from peerreviewagents import MANUSCRIPT_DIRECTORY, read_citation_ledger, read_run
from peerreviewagents import locate_run, NotARunFolder

RUN_REVIEW_ID = 'run'
AUDIT_LIMIT = 400_000
FINDING_UID = re.compile(r'[A-Za-z0-9_-]{1,64}')

# The citation ledger, as the run panel shows it.
CITATION_ROWS = 500
CITATION_TEXT = 1_500
REFERENCE_STATES = ('yes', 'no', 'not located', 'could not check')
VERDICTS = ('supports', 'partly supports', 'does not support', 'cannot tell')
CITATION_COUNTS = ('references', 'resolved', 'not_found', 'not_located', 'could_not_check', 'unresolved',
                   'mismatched', 'retracted', 'candidates', 'errors', 'uses', 'uses_unmatched', 'uses_judged',
                   'supported', 'partly_supported', 'not_supported', 'cannot_tell', 'uses_unjudged',
                   'unreadable_rows')
# The order the panel lists in-text uses: the ones a reader has to look at first.
USE_ORDER = {'does not support': 0, 'partly supports': 1, 'unmatched': 2, 'cannot tell': 3, None: 4, 'supports': 5}


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


def clip(value, limit=CITATION_TEXT):
    """A ledger value as text the panel can show, cut to ``limit`` characters, or ``None``."""
    if isinstance(value, int) and not isinstance(value, bool):
        value = str(value)
    if not isinstance(value, str) or not value.strip():
        return None
    return value if len(value) <= limit else value[:limit] + ' [shortened by the viewer]'


def https_url(value):
    """A source address the panel may link to: https only."""
    value = clip(value, 2_000)
    return value if value and value.startswith('https://') else None


def bibliographic(entry):
    """The title, first author, year, venue and DOI of a printed or indexed work, as text."""
    entry = entry if isinstance(entry, dict) else {}
    return {key: clip(entry.get(key), 600) for key in ('title', 'first_author', 'year', 'venue', 'doi')}


def reference_entry(row):
    """One reference row as the panel shows it. The abstract and full text are left out."""
    resolution = row.get('resolution') if isinstance(row.get('resolution'), dict) else None
    found = resolution or {}
    exists = found.get('exists')
    if resolution is None:
        state = 'never looked up'
    else:
        state = exists if exists in REFERENCE_STATES else 'not recorded'
    record, candidate = found.get('record'), found.get('candidate')
    return {
        'row_id': clip(row.get('row_id'), 200),
        'label': clip(row.get('label'), 40),
        'printed': bibliographic(row.get('printed')),
        'state': state,
        'mismatched': [field for field in found.get('mismatched') or [] if isinstance(field, str)][:8],
        'retracted': found.get('retracted') is True,
        'retraction_notice': clip(found.get('retraction_notice'), 400),
        'printed_doi_registered': found.get('printed_doi_registered'),
        'printed_doi_source': clip(found.get('printed_doi_source'), 40),
        'record': bibliographic(record) if isinstance(record, dict) else None,
        'candidate': bibliographic(candidate) if isinstance(candidate, dict) else None,
        'error': bool(found.get('error')),
        'lookups': [clip(one.get('status'), 40) for one in found.get('requests') or [] if isinstance(one, dict)][:12],
        'has_source_text': found.get('has_source_text') is True,
        'source_url': https_url(found.get('full_text_url') or found.get('abstract_url') or found.get('source_url')),
    }


def needs_a_look(entry):
    """Whether a reference is anything but found in an index with every printed field matching."""
    return (entry['state'] != 'yes' or entry['mismatched'] or entry['retracted'] or entry['candidate']
            or entry['error'] or entry['printed_doi_registered'] is False)


def use_entry(row, labels):
    """One in-text use and the verdict a citation worker left on it."""
    reference = row.get('reference_id') if isinstance(row.get('reference_id'), str) else None
    verdict = row.get('verdict') if row.get('verdict') in VERDICTS else None
    return {
        'row_id': clip(row.get('row_id'), 200),
        'reference_id': reference,
        'label': labels.get(reference),
        'marker': clip(row.get('marker'), 120),
        'section': clip(row.get('section'), 200),
        'block_id': clip(row.get('block_id'), 200),
        'sentence': clip(row.get('sentence')),
        'ambiguous': row.get('derivation') == 'marker-author-year-ambiguous',
        'verdict': verdict,
        'passage': clip(row.get('passage')),
        'note': clip(row.get('note')),
        'judged_by': clip(row.get('judged_by'), 64) if verdict else None,
        'claimed_by': None if verdict else clip(row.get('claimed_by'), 64),
        'source_kind': clip(row.get('source_kind'), 40),
        'source_url': https_url(row.get('source_url')),
    }


def citation_view(citations, review):
    """The citation ledger as the run panel shows it, or ``None`` for a run that planned no citations lane.

    The counts and problem lines are ``read_run``'s. The rows are
    ``read_citation_ledger``'s, read only when ``read_run`` could count the
    ledger. The references are the ones that need a second look, and the uses
    are listed with the ones a reader should check first at the top, at most
    ``CITATION_ROWS`` of them. Text in a row came from the manuscript, from an
    index on the internet or from a worker, and the panel shows it escaped as
    quoted text.
    """
    if not citations.get('enabled'):
        return None
    counts = citations.get('counts') or {}
    view = {
        'complete': citations.get('complete') is True,
        'problems': [line for line in citations.get('problems') or [] if isinstance(line, str)],
        'ledger': citations.get('ledger') is not None,
        'readable': bool(counts),
        'counts': {key: counts[key] for key in CITATION_COUNTS
                   if isinstance(counts.get(key), int) and not isinstance(counts.get(key), bool)},
        'references': [],
        'references_not_shown': 0,
        'uses': [],
        'uses_not_shown': 0,
    }
    if not view['ledger'] or not view['readable']:
        return view
    try:
        # The fetched abstract and full text stay in the run folder. The panel shows
        # only whether a worker had them, and the passage the worker quoted.
        ledger = read_citation_ledger(review, source_text=False)
    except ValueError as exc:
        raise RunError(str(exc)) from None
    labels = {row.get('reference_id'): clip(row.get('label'), 40) for row in ledger['references']
              if isinstance(row.get('reference_id'), str)}
    # The reader gives the rows in reading order, ref:r2 before ref:r10, and the
    # sort is stable, so each verdict group keeps that order.
    references = [reference_entry(row) for row in ledger['references']]
    uses = sorted((use_entry(row, labels) for row in ledger['uses']),
                  key=lambda use: USE_ORDER[use['verdict'] if use['reference_id'] else 'unmatched'])
    flagged = [entry for entry in references if needs_a_look(entry)]
    view['references'] = flagged[:CITATION_ROWS]
    view['references_not_shown'] = max(0, len(flagged) - CITATION_ROWS)
    view['uses'] = uses[:CITATION_ROWS]
    view['uses_not_shown'] = max(0, len(uses) - CITATION_ROWS)
    return view


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
    citations = citation_view(run['citations'], run['review'])
    # The citation stage lines are in `problems` too. The panel shows them once, with the ledger.
    shown_with_citations = set(citations['problems']) if citations else set()
    view = {
        'arm': run['identity']['arm'],
        'reviewer_count': run['identity']['reviewers'],
        'workflow_version': run['identity']['workflow_version'],
        'status': run['status'],
        'cause': run['cause'],
        'note': run['note'],
        'problems': [line for line in run['problems'] if line not in shown_with_citations],
        'publishable': run['publishable'],
        'not_publishable_reasons': run['not_publishable_reasons'],
        'edited': edited,
        'escalated_count': len(run['escalations']),
        'review_guard_status': run['guard_status'],
        'quarantined_findings_count': run['counts']['quarantined'],
        'findings_delivered': run['counts']['findings_delivered'],
        'missing_stages': list(stages.get('missing') or []),
        'none_found': none_found,
        # Each agent row keeps `assigned_model`, the model asked, beside `model`, the model ran,
        # which is None when nothing observed it. Neither stands in for the other.
        'agents': [{**row, 'findings': per_slot.get(row.get('slot'), 0), 'none_found': row.get('slot') in none_found}
                   for row in run['agents']],
        'models_unverified': list(run['identity'].get('models_unverified') or []),
        'findings_by_track': dict(Counter(row['track'] for row in findings if row.get('track'))),
        'verdict': run['verdict'],
        'escalation_rulings': run['escalation_rulings'],
        'limitations': run['limitations'],
        'audits': audit_texts(run['reports']['audits']),
        'citations': citations,
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
