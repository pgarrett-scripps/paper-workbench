"""Show a PeerReviewAgents run folder in the viewer.

``paper-workbench review paper.pdf RUN`` writes the imported manuscript to
``RUN/manuscript`` and the review to ``RUN/review``. The engine's ``read_run``
reads the run, finished or stopped, and names any file it could not read. This
module adds only what the app owns: which manuscript a served path names, the
check that the run reviewed this version of it, and the review shape the
viewer, the decisions and ``export_draft`` read, one card per issue in
``issues.json``. Nothing here makes a model call or writes to the run.

The citation ledger's rows come from the engine's ``read_citation_ledger``,
which keeps the last row written for each ``row_id`` and gives them in reading
order, ``ref:r2`` before ``ref:r10``. It is called without the fetched
abstracts and full text, because the panel never shows them.
"""
import os
import re
from collections import Counter
from pathlib import Path

from peerreviewagents import MANUSCRIPT_DIRECTORY, read_citation_ledger, read_run
from peerreviewagents import locate_run, NotARunFolder
from peerreviewagents.issues import (ISSUE_FIELDS, by_category, closed_issues, is_issue_id, required_issues,
                                     suggestion_issues)
from peerreviewagents.workspace import read_json

RUN_REVIEW_ID = 'run'
AUDIT_LIMIT = 400_000
FINDING_UID = re.compile(r'[A-Za-z0-9_-]{1,64}')
# A card with no engine id of its own is numbered run-1, run-2 and on, and takes
# no decision. A uid of that form would share an id with such a card, so it is
# not taken as an engine id. The engine's own uids are 16 hex digits.
POSITIONAL_ID = re.compile(rf'{RUN_REVIEW_ID}-\d+')
NO_ENGINE_ID = ('This card has no engine id, so a decision on it could land on another card. '
                'Re-run the review to decide on it.')
OLDER_ENGINE = ('This review was made by an older engine, re-run it. Its review folder holds editor-package.json '
                'and no issues.json, and this viewer reads only the issues.json that engine 0.10.0 writes.')
# The types the viewer reads from each issue in issues.json. A value of another
# type is a malformed file, and the run is refused with each such value named.
ISSUE_TEXT = ('id', 'name', 'statement', 'severity', 'category', 'status', 'status_reason',
              'text_unchanged_reason', 'rebuttal_quote', 'rebuttal_block_id', 'prior_id')
ISSUE_NUMBERS = ('rank', 'prior_rank', 'raised_by')
MEMBER_TEXT = ('finding_uid', 'slot', 'track', 'severity', 'kind', 'basis', 'title', 'quote', 'block_id')
TYPE_PROBLEMS_SHOWN = 8
# An issue's members carry the quote and the blocks. Their ledger rows, joined
# by finding_uid, carry the comment, the span and the suggested wording.
FROM_LEDGER = ('comment', 'start', 'end', 'block_sha256', 'placement', 'replacement', 'basis_reason',
               'counterevidence', 'source_urls')
# What a card copies from the member it is anchored to.
ANCHOR = ('block_id', 'quote', 'start', 'end', 'block_sha256')

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
    """The engine's reading of a run. A symlinked run file is refused in plain words.

    The engine's reader trusts the shape of each issue's member list, and one
    that is not a list of objects stops it with an AttributeError. That run is
    refused in plain words too, with the values named from issues.json itself.
    """
    try:
        return read_run(review)
    except ValueError as exc:
        raise RunError(str(exc)) from None
    except (AttributeError, TypeError):
        raise RunError(malformed(review)) from None


def is_text(value):
    return value is None or isinstance(value, str)


def is_text_list(value):
    return value is None or (isinstance(value, list) and all(isinstance(item, str) for item in value))


def issue_problems(rows):
    """Each value in the issues that is not of the type the viewer reads, as a line of prose."""
    problems = []
    for number, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            problems.append(f'issue {number} is not an object')
            continue
        name = f'issue {number}' + (f' ({row["id"]})' if isinstance(row.get('id'), str) else '')
        problems += [f'in {name}, {key} is not text' for key in ISSUE_TEXT if not is_text(row.get(key))]
        problems += [f'in {name}, {key} is not a whole number' for key in ISSUE_NUMBERS
                     if not (row.get(key) is None or type(row.get(key)) is int)]
        if not is_text_list(row.get('audits')):
            problems.append(f'in {name}, audits is not a list of file names')
        quotes = row.get('surviving_quotes')
        if not (quotes is None or (isinstance(quotes, list) and all(
                isinstance(quote, dict) and is_text(quote.get('quote')) and is_text(quote.get('block_id'))
                for quote in quotes))):
            problems.append(f'in {name}, surviving_quotes is not a list of quotes')
        members = row.get('members')
        if not (members is None or isinstance(members, list)):
            problems.append(f'in {name}, members is not a list')
            continue
        for index, member in enumerate(members or [], 1):
            where = f'{name} member {index}'
            if not isinstance(member, dict):
                problems.append(f'{where} is not an object')
                continue
            problems += [f'in {where}, {key} is not text' for key in MEMBER_TEXT if not is_text(member.get(key))]
            if not (member.get('escalate') is None or isinstance(member.get('escalate'), bool)):
                problems.append(f'in {where}, escalate is not true or false')
            if not is_text_list(member.get('evidence_blocks')):
                problems.append(f'in {where}, evidence_blocks is not a list of block ids')
    return problems


def wrong_types(problems):
    """One message for every value of the wrong type, the first few of them named."""
    lines = [line[0].upper() + line[1:] for line in problems[:TYPE_PROBLEMS_SHOWN]]
    if len(problems) > TYPE_PROBLEMS_SHOWN:
        lines.append(f'{len(problems) - TYPE_PROBLEMS_SHOWN} more are not listed')
    return ("This run's review/issues.json holds values of the wrong type, so the viewer cannot show it. "
            + '. '.join(lines) + '. Re-run the review.')


def malformed(review):
    """Why the engine's reader stopped on a run, read from issues.json where the cause is there."""
    path = Path(review) / 'issues.json'
    document = None
    if path.is_file() and not path.is_symlink():
        try:
            document = read_json(path)
        except (ValueError, OSError):
            document = None
    rows = document.get('issues') if isinstance(document, dict) else None
    problems = issue_problems(rows) if isinstance(rows, list) else []
    if problems:
        return wrong_types(problems)
    return 'The engine could not read this run folder, because a run file holds a value of the wrong type. Re-run the review.'


def check_issues(rows):
    """Refuse a run whose issues hold a value the viewer would misread, naming each one."""
    problems = issue_problems(rows)
    if problems:
        raise RunError(wrong_types(problems))


def check_engine(review):
    """Refuse a review folder an engine before 0.10 wrote: editor-package.json and no issues.json.

    A 0.10 run whose editor failed has neither file, and it opens with what it recorded.
    """
    review = Path(review)
    if not os.path.lexists(review / 'issues.json') and os.path.lexists(review / 'editor-package.json'):
        raise RunError(OLDER_ENGINE)


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


def placed(row, blocks):
    """A finding with its anchor checked against this manuscript's text.

    A recorded span counts only while it still holds the quote. A member read
    from ``issues.json`` alone has no span, so its quote is anchored where it
    occurs exactly once in its block. Anything else is ``unplaced``.
    """
    row = dict(row)
    block = blocks.get(row.get('block_id'))
    text, quote = (block or {}).get('text', ''), row.get('quote')
    start, end = row.get('start'), row.get('end')
    if not (block and isinstance(quote, str) and quote):
        row.update(start=None, end=None, placement='unplaced')
        return row
    if not (type(start) is int and type(end) is int and 0 <= start <= end <= len(text) and text[start:end] == quote):
        start = text.find(quote)
        if start < 0 or text.find(quote, start + 1) >= 0:
            row.update(start=None, end=None, placement='unplaced')
            return row
        end = start + len(quote)
    row.update(start=start, end=end, placement='anchored')
    if row.get('block_sha256') is None:
        row['block_sha256'] = block.get('sha256')
    return row


def issue_card(issue, group, ledger, blocks):
    """One issue as one card and one author decision.

    Each member is joined to its ledger row by ``finding_uid`` for the comment,
    the span and the suggested wording, then placed on the manuscript. The card
    is an edit only when its one member is an anchored edit with wording, so
    accepting it applies exactly that wording. Any other issue takes a note.
    """
    members = []
    for member in issue.get('members') or []:
        if isinstance(member, dict):
            uid = member.get('finding_uid')
            row = ledger.get(uid, {}) if isinstance(uid, str) else {}
            members.append(placed({**member, **{key: row[key] for key in FROM_LEDGER if key in row}}, blocks))
    edit = (len(members) == 1 and members[0].get('kind') == 'edit' and members[0]['placement'] == 'anchored'
            and isinstance(members[0].get('replacement'), str))
    anchor = next((m for m in members if m['placement'] == 'anchored'), None) or next(
        (m for m in members if m.get('block_id')), {})
    evidence = dict.fromkeys(block for m in members for block in m.get('evidence_blocks') or [] if isinstance(block, str))
    return {**issue, 'group': group, 'source_id': issue.get('id'), 'number': issue.get('rank'),
            'title': issue.get('name'), 'comment': issue.get('statement'), 'members': members,
            'kind': 'edit' if edit else 'issue', 'escalate': any(m.get('escalate') is True for m in members),
            'evidence_blocks': list(evidence), **{key: anchor.get(key) for key in ANCHOR},
            'placement': anchor.get('placement', 'unplaced'), 'replacement': anchor.get('replacement') if edit else None}


def finding_card(row, ledger, blocks):
    """A ledger finding no issue holds, as a card of its own with itself as the one member."""
    issue = {**dict.fromkeys(ISSUE_FIELDS), 'id': row.get('finding_uid'), 'name': row.get('title'),
             'severity': row.get('severity'), 'statement': row.get('comment'), 'members': [row], 'raised_by': 1,
             'surviving_quotes': [], 'audits': []}
    return issue_card(issue, 'ledger', ledger, blocks)


def run_review(review, paper):
    """The run as a review that the viewer, the decisions and ``export_draft`` read.

    The unit is the editor's issue. Required changes come first in rank order,
    then the suggestions grouped by category, then the prior round's resolved
    and unverified issues. A finding that no issue holds, which is every
    finding of a run that stopped before the editor wrote ``issues.json``, is a
    card of its own after them. A card's ``id`` is its issue id, or the
    finding's ``finding_uid`` for a finding no issue holds. A card whose id is
    missing, malformed or repeated is numbered by its place instead and is not
    ``decidable``, because a decision keyed on its place would land on another
    card once the order changed.
    """
    check_engine(review)
    run = recorded(review)
    # With an empty ledger the engine rebuilds the findings from the members, so they are checked first.
    check_issues(run['issues'])
    check_version(run, paper)
    blocks = {block['id']: block for block in paper['blocks']}
    ledger = {row['finding_uid']: row for row in run['findings'] if isinstance(row.get('finding_uid'), str)}
    issues = run['issues']
    held = {member.get('finding_uid') for issue in issues for member in issue.get('members') or []
            if isinstance(member, dict) and isinstance(member.get('finding_uid'), str)}
    findings = ([issue_card(issue, 'required', ledger, blocks) for issue in required_issues(issues)]
                + [issue_card(issue, 'suggestion', ledger, blocks)
                   for _, rows in by_category(suggestion_issues(issues)) for issue in rows]
                + [issue_card(issue, 'closed', ledger, blocks) for issue in closed_issues(issues)])
    top = max((card['number'] for card in findings if type(card['number']) is int), default=0)
    loose = [finding_card(row, ledger, blocks) for row in run['findings']
             if not (isinstance(row.get('finding_uid'), str) and row['finding_uid'] in held)]
    for number, card in enumerate(loose, top + 1):
        card['number'] = number
    findings += loose
    uses = Counter(card['source_id'] for card in findings if isinstance(card['source_id'], str))
    for number, card in enumerate(findings, 1):
        value = card['source_id']
        engine_id = (isinstance(value, str) and uses[value] == 1 and not POSITIONAL_ID.fullmatch(value)
                     and bool(FINDING_UID.fullmatch(value) if card['group'] == 'ledger' else is_issue_id(value)))
        card['id'] = value if engine_id else f'{RUN_REVIEW_ID}-{number}'
        card['decidable'] = engine_id
    stages = run['stages'] or {}
    none_found = list(stages.get('none_found') or [])
    per_slot = Counter(row.get('slot') for row in run['findings'])
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
        'findings_source': run['findings_source'],
        'issues_source': run['issues_source'],
        'prior_round': run['prior_round'],
        'counts': run['counts'],
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
        'findings_by_track': dict(Counter(row['track'] for row in run['findings'] if row.get('track'))),
        'verdict': run['verdict'],
        'escalation_rulings': run['escalation_rulings'],
        'limitations': run['limitations'],
        'audits': audit_texts(run['reports']['audits']),
        'citations': citations,
        'tokens_total': run['runtime']['tokens_total'],
        'wall_seconds': run['runtime']['wall_seconds'],
    }
    if run['findings_source'] == 'issues':
        summary = run['summary'] or 'The editor wrote no summary.'
    elif run['cause']:
        summary = f'The run stopped before the editor wrote its issues: {run["cause"]}'
    elif run['findings_source'] == 'ledger' and run['complete']:
        # An older engine's folder never reaches here: check_engine refused it above.
        summary = 'The run finished without a readable issues.json, so its findings are not grouped into issues.'
    elif run['findings_source'] == 'ledger':
        summary = f'The run has not written its issues. Its last recorded status is {run["status"]}.'
    else:
        summary = run['summary'] or f'The run recorded no findings. Its last recorded status is {run["status"]}.'
    return {'id': RUN_REVIEW_ID, 'paper_id': paper['id'], 'source_sha256': paper['source_sha256'],
            'summary': summary, 'findings': findings, 'run': view}


def applicable(review, decisions):
    """The decisions an export or a revision applies: none keyed on a card with no engine id.

    Such a card is numbered by its place, so a decision saved under its number
    may have been made on another card. It is left in the decisions file and
    not applied.
    """
    placed = {item['id'] for item in review['findings'] if item.get('decidable') is False}
    if not placed:
        return decisions
    return {**decisions, 'items': {key: value for key, value in decisions.get('items', {}).items()
                                   if key not in placed}}
