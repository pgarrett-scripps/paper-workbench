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

On a run given code, the engine's code check reads each finding that rests on
how a number was computed against the code. ``read_run`` hands on what it found
as ``code_check``, from ``issues.json``, or from the check's own file on a run
that stopped before the review was written. This module opens no run file of
its own for it.
"""
import os
import re
from collections import Counter
from pathlib import Path

from peerreviewagents import MANUSCRIPT_DIRECTORY, cited_text, read_citation_ledger, read_run
from peerreviewagents import locate_run, NotARunFolder
from peerreviewagents.issues import ISSUE_FIELDS, by_category, is_issue_id, required_issues, suggestion_issues
from peerreviewagents.names import CODE_CHECK_VERDICTS

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
# Every review is a fresh panel, so the viewer reads nothing about an earlier round.
ISSUE_TEXT = ('id', 'name', 'statement', 'severity', 'category', 'rebuttal_document', 'rebuttal_quote')
ISSUE_NUMBERS = ('rank', 'raised_by', 'rebuttal_line')
MEMBER_TEXT = ('finding_uid', 'slot', 'track', 'severity', 'kind', 'basis', 'title', 'quote', 'anchor_text',
               'document', 'fingerprint')
MEMBER_NUMBERS = ('line', 'end_line', 'start', 'end')
TYPE_PROBLEMS_SHOWN = 8
# An issue's members carry the quote and where the engine placed it. Their ledger
# rows, joined by finding_uid, carry the comment, the span, the suggested wording
# and, on a code-checked finding, the file, lines and text the engine found in the
# run's code snapshot.
FROM_LEDGER = ('comment', 'start', 'end', 'anchor_text', 'placement', 'replacement', 'basis_reason',
               'counterevidence', 'source_urls', 'code_evidence')
# What the run panel says about the code a run was reviewed against. The snapshot's
# own manifest, which names every file, stays in the run folder. `source_cut` counts
# the program source files a cap left out, and the data counts say how many data
# files the code ships and what the reviewers fetched of them.
CODE_VIEW = ('reviewed', 'kind', 'source', 'commit', 'branch', 'dirty', 'snapshot', 'files_in_snapshot',
             'files_skipped', 'truncated', 'source_cut', 'files_opened', 'opened', 'searches',
             'data_listed', 'data_fetched', 'data_partial', 'data_refused', 'data_bytes')
# What the panel shows of each data file a reviewer fetched. A partial one holds
# only the first `stored_bytes` of its `bytes`. `changed` is empty, or says in the
# engine's words how the file changed after the snapshot listed it.
DATA_VIEW = ('path', 'bytes', 'stored_bytes', 'partial', 'changed')
CONTRADICTED = 'contradicted'
# What the panel shows of the code check. A check that answered only some claims is
# `incomplete`, with the engine's reason, and `not_checked` counts the claims it never read
# against the code. `silent` is a check that filed no report at all, which `checked: 0`
# cannot tell from one that reported and settled nothing.
CODE_CHECK_VIEW = ('cap', 'silent', 'checked', 'not_checked', 'over_cap', 'incomplete', 'incomplete_reason',
                   'counts')
# What a finding the code check threw out keeps from the check's row. Its comment
# and offsets come from its ledger row, and the slot and track are the finding's own.
THROWN_OUT_VIEW = ('finding_uid', 'title', 'severity', 'basis', 'assumed_method', 'quote', 'document', 'line',
                   'end_line', 'code_evidence', 'note')
# Where a finding sits in the manuscript.
SPAN = ('document', 'line', 'end_line', 'start', 'end', 'anchor_text')
# What a card copies from the member it is anchored to.
ANCHOR = (*SPAN, 'quote', 'page', 'bbox', 'fingerprint')

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


def is_text(value):
    return value is None or isinstance(value, str)


def is_text_list(value):
    return value is None or (isinstance(value, list) and all(isinstance(item, str) for item in value))


def is_line(value):
    """A line number: a whole number that is not true or false."""
    return type(value) is int


def is_number(value):
    return value is None or is_line(value)


def is_line_list(value):
    return value is None or (isinstance(value, list) and all(is_line(item) for item in value))


def issue_problems(rows):
    """Each value in the issues that is not of the type the viewer reads, as a line of prose."""
    problems = []
    for number, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            problems.append(f'issue {number} is not an object')
            continue
        name = f'issue {number}' + (f' ({row["id"]})' if isinstance(row.get('id'), str) else '')
        problems += [f'in {name}, {key} is not text' for key in ISSUE_TEXT if not is_text(row.get(key))]
        problems += [f'in {name}, {key} is not a whole number' for key in ISSUE_NUMBERS if not is_number(row.get(key))]
        if not is_text_list(row.get('audits')):
            problems.append(f'in {name}, audits is not a list of file names')
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
            problems += [f'in {where}, {key} is not a whole number' for key in MEMBER_NUMBERS
                         if not is_number(member.get(key))]
            if not (member.get('escalate') is None or isinstance(member.get('escalate'), bool)):
                problems.append(f'in {where}, escalate is not true or false')
            if not is_line_list(member.get('evidence_lines')):
                problems.append(f'in {where}, evidence_lines is not a list of line numbers')
    return problems


def wrong_types(problems, record="This run's review/issues.json"):
    """One message for every value of the wrong type, the first few of them named."""
    lines = [line[0].upper() + line[1:] for line in problems[:TYPE_PROBLEMS_SHOWN]]
    if len(problems) > TYPE_PROBLEMS_SHOWN:
        lines.append(f'{len(problems) - TYPE_PROBLEMS_SHOWN} more are not listed')
    return (f'{record} holds values of the wrong type, so the viewer cannot show it. '
            + '. '.join(lines) + '. Re-run the review.')


def check_issues(rows):
    """Refuse a run whose issues hold a value the viewer would misread, naming each one."""
    problems = issue_problems(rows)
    if problems:
        raise RunError(wrong_types(problems))


def code_check_problems(rows):
    """Each value in the code check's rows that is not of the type the viewer reads, as a line of prose.

    ``read_run`` works out the cap, the counts and how many were checked, and
    hands on each row as the check wrote it.
    """
    problems = []
    for number, row in enumerate(rows, 1):
        where = f'code_check row {number}'
        if not isinstance(row.get('finding_uid'), str):
            problems.append(f'in {where}, finding_uid is not text')
        if row.get('verdict') not in CODE_CHECK_VERDICTS:
            problems.append(f'in {where}, verdict is not one of {", ".join(CODE_CHECK_VERDICTS)}')
        problems += [f'in {where}, {key} is not text' for key in ('title', 'quote', 'note', 'assumed_method')
                     if not is_text(row.get(key))]
        evidence = row.get('code_evidence')
        if not (evidence is None or (isinstance(evidence, dict) and isinstance(evidence.get('path'), str)
                                     and is_line(evidence.get('start_line')) and is_line(evidence.get('end_line'))
                                     and isinstance(evidence.get('text'), str))):
            problems.append(f'in {where}, code_evidence is not a file, its lines and their text')
        elif row.get('verdict') == CONTRADICTED and evidence is None:
            problems.append(f'in {where}, a contradicted finding has no code_evidence')
    return problems


def code_check_of(run):
    """What the run's code check did, as ``read_run`` hands it on, or ``None`` on a run that had none.

    A run given no code has none. A row holding a value of another type is
    refused with each such value named.
    """
    check = run['code_check']
    if check is None:
        return None
    problems = code_check_problems(check['checks'])
    if problems:
        raise RunError(wrong_types(problems, "This run's code check"))
    return check


def fetched_data(code):
    """The data files a reviewer fetched from the run's code, by path, as the snapshot's manifest records them.

    The engine lists every data file the code ships and copies one in only when
    a reviewer reads it. A text file over its size cap is stored as its first
    whole lines, and ``partial`` says so. A run given no code has no manifest.
    """
    manifest = code['manifest']
    rows = manifest['data'] if manifest else []
    return {row['path']: {key: row.get(key) for key in DATA_VIEW} for row in rows if row.get('fetched') is True}


def data_of(evidence, data):
    """The fetched data file a piece of code evidence quotes, or ``None`` when it quotes source."""
    return data.get(evidence['path']) if isinstance(evidence, dict) else None


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
    or a run that stopped before its manuscript was sealed, raises
    :class:`RunError` with a plain message. ``read_run``'s ``manuscript`` says
    which: a ``draft`` is a paper the Read stage started on and never sealed,
    so it has no line numbers, and ``absent`` is a run that stopped before the
    import. Neither has lines to show.
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
    run = recorded(review)
    if not run['manuscript']['sealed']:
        stopped = ('before the Read stage sealed its manuscript' if run['manuscript']['state'] == 'draft'
                   else 'before it imported its manuscript')
        raise RunError(f'The run in {root} stopped {stopped}, so there is nothing to show. '
                       f'Status: {run["status"]}. Cause: {run["cause"] or "not recorded"}')
    return root / MANUSCRIPT_DIRECTORY, review


def main_document(base):
    """The name of the manuscript's own document. The engine lists it first."""
    return base.document_names()[0]


def source_sha256(base):
    return (base.manifest.get('source') or {}).get('sha256')


def pinned(row, base):
    """Whether a finding's fingerprint, where it has one, is the passage's on the line it names."""
    fingerprint = row.get('fingerprint')
    if fingerprint is None:
        return True
    if not is_line(row.get('line')):
        return False
    piece = base.piece_at(row['line'], row.get('document') or main_document(base))
    return piece is not None and piece.get('fingerprint') == fingerprint


def check_version(run, base):
    """Refuse a run that reviewed another version of this manuscript.

    The run names the manuscript it reviewed, and each finding and each issue
    member pins the passage it quoted by its fingerprint, so a run that stopped
    before naming the manuscript is still checked.
    """
    identity = run['identity']
    members = [member for issue in run['issues'] for member in issue.get('members') or [] if isinstance(member, dict)]
    same = ((identity['paper_id'], identity['source_sha256']) == (base.paper_id, source_sha256(base))
            and all(pinned(row, base) for row in [*run['findings'], *members]))
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
        'document': clip(row.get('document'), 200),
        'line': row.get('line') if is_line(row.get('line')) else None,
        'end_line': row.get('end_line') if is_line(row.get('end_line')) else None,
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
    quoted text. ``no_network`` is true when the resolve stage reached no lookup
    host, so the panel says no reference was checked.
    """
    if not citations.get('enabled'):
        return None
    counts = citations.get('counts') or {}
    stages = counts.get('stages') if isinstance(counts.get('stages'), dict) else {}
    resolve = stages.get('resolve') if isinstance(stages.get('resolve'), dict) else {}
    view = {
        'complete': citations.get('complete') is True,
        # The engine records hosts_reached false when every lookup of the run failed to reach a host,
        # the machine offline or behind a firewall, so no reference was checked at all.
        'no_network': resolve.get('hosts_reached') is False,
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


def span_holds(row, base):
    """Whether a recorded span still covers the text it was anchored to.

    ``start`` is an offset into ``line`` and ``end`` one into ``end_line``, as
    the engine records them on every citation, and ``cited_text`` reads that
    span off the manuscript, a quote across a line break included.
    """
    document, text = row.get('document'), row.get('anchor_text')
    numbers = [row.get(key) for key in ('line', 'end_line', 'start', 'end')]
    if document not in base.documents or not (isinstance(text, str) and text) or not all(map(is_line, numbers)):
        return False
    line, end_line, start, end = numbers
    if not (1 <= line <= end_line <= base.line_count(document)
            and 0 <= start <= len(base.line_text(line, document))
            and 0 <= end <= len(base.line_text(end_line, document))):
        return False
    return cited_text(base, row) == text


def placed(row, base):
    """A finding with its anchor checked against this manuscript's text.

    The engine places every citation and records where, on the issue member as
    on the ledger row, so the viewer reads that span and never searches the line
    for the quote again. A span counts only while it still covers its text. One
    the engine did not place, or that no longer holds, is ``unplaced`` and keeps
    its line. The page and the box are the passage's on that line, from the
    manuscript's map.
    """
    row = dict(row)
    row['document'] = row.get('document') or main_document(base)
    if span_holds(row, base):
        row['placement'] = 'anchored'
    else:
        row.update(start=None, end=None, anchor_text=None, placement='unplaced')
    piece = base.piece_at(row['line'], row['document']) if is_line(row.get('line')) else None
    row.update(page=(piece or {}).get('page'), bbox=(piece or {}).get('bbox'))
    return row


def evidence_of(members):
    """The further lines an issue's members cite, each once, in the member's own document."""
    seen = dict.fromkeys((member['document'], line) for member in members
                         for line in member.get('evidence_lines') or [] if is_line(line))
    return [{'document': document, 'line': line} for document, line in seen]


def issue_card(issue, group, ledger, base):
    """One issue as one card and one author decision.

    Each member is joined to its ledger row by ``finding_uid`` for the comment,
    the span and the suggested wording, then placed on the manuscript. The card
    is an edit only when its one member is an anchored edit with wording, so
    accepting it applies exactly that wording. Any other issue takes a note.
    The rebuttal quote is on the issue's own ``rebuttal_document``, and an empty
    one names the main document, as the engine reads it.
    """
    members = []
    for member in issue.get('members') or []:
        if isinstance(member, dict):
            uid = member.get('finding_uid')
            row = ledger.get(uid, {}) if isinstance(uid, str) else {}
            members.append(placed({**member, **{key: row[key] for key in FROM_LEDGER if key in row}}, base))
    edit = (len(members) == 1 and members[0].get('kind') == 'edit' and members[0]['placement'] == 'anchored'
            and isinstance(members[0].get('replacement'), str))
    anchor = next((m for m in members if m['placement'] == 'anchored'), None) or next(
        (m for m in members if is_line(m.get('line'))), {})
    return {**issue, 'group': group, 'source_id': issue.get('id'), 'number': issue.get('rank'),
            'title': issue.get('name'), 'comment': issue.get('statement'), 'members': members,
            'kind': 'edit' if edit else 'issue', 'escalate': any(m.get('escalate') is True for m in members),
            'evidence': evidence_of(members), 'rebuttal_document': issue.get('rebuttal_document') or main_document(base),
            **{key: anchor.get(key) for key in ANCHOR},
            'placement': anchor.get('placement', 'unplaced'), 'replacement': anchor.get('replacement') if edit else None}


def finding_card(row, ledger, base):
    """A ledger finding no issue holds, as a card of its own with itself as the one member."""
    issue = {**dict.fromkeys(ISSUE_FIELDS), 'id': row.get('finding_uid'), 'name': row.get('title'),
             'severity': row.get('severity'), 'statement': row.get('comment'), 'members': [row], 'raised_by': 1,
             'audits': []}
    return issue_card(issue, 'ledger', ledger, base)


def thrown_out(check, ledger, data, base):
    """The findings the code check threw out: the code does not do what each one said.

    The engine keeps such a finding out of every issue, so it is no card and
    takes no decision. Each one shows the check's row, the code that disproved
    it and the note written for the authors, with the comment and the span of
    its ledger row, placed on the manuscript as a member is.
    """
    items = []
    for row in check['checks']:
        if row['verdict'] != CONTRADICTED:
            continue
        finding = ledger.get(row['finding_uid'], {})
        item = {key: row.get(key) for key in THROWN_OUT_VIEW}
        item.update(id=row['finding_uid'], slot=row.get('finding_slot'), track=row.get('finding_track'),
                    comment=finding.get('comment'), start=finding.get('start'), end=finding.get('end'),
                    anchor_text=finding.get('anchor_text'), code_data=data_of(row['code_evidence'], data))
        items.append(placed(item, base))
    return items


def run_review(review, base):
    """The run as a review that the viewer, the decisions and ``export_draft`` read.

    The unit is the editor's issue. Required changes come first in rank order,
    then the suggestions grouped by category. A finding that no issue holds, which is every
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
    check_version(run, base)
    ledger = {row['finding_uid']: row for row in run['findings'] if isinstance(row.get('finding_uid'), str)}
    issues = run['issues']
    check = code_check_of(run)
    data = fetched_data(run['code'])
    # A finding the code check contradicted is in no issue, and it is never shown as one of its own either.
    held = {member.get('finding_uid') for issue in issues for member in issue.get('members') or []
            if isinstance(member, dict) and isinstance(member.get('finding_uid'), str)}
    held |= {row['finding_uid'] for row in check['checks'] if row['verdict'] == CONTRADICTED} if check else set()
    findings = ([issue_card(issue, 'required', ledger, base) for issue in required_issues(issues)]
                + [issue_card(issue, 'suggestion', ledger, base)
                   for _, rows in by_category(suggestion_issues(issues)) for issue in rows])
    top = max((card['number'] for card in findings if type(card['number']) is int), default=0)
    loose = [finding_card(row, ledger, base) for row in run['findings']
             if not (isinstance(row.get('finding_uid'), str) and row['finding_uid'] in held)]
    for number, card in enumerate(loose, top + 1):
        card['number'] = number
    findings += loose
    # A member whose code evidence is a data file says whether the review read all of it.
    for card in findings:
        for member in card['members']:
            member['code_data'] = data_of(member.get('code_evidence'), data)
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
        'counts': run['counts'],
        'escalated_count': len(run['escalations']),
        'review_guard_status': run['guard_status'],
        'quarantined_findings_count': run['counts']['quarantined'],
        'findings_delivered': run['counts']['findings_delivered'],
        'missing_stages': list(stages.get('missing') or []),
        'none_found': none_found,
        # Each agent row keeps `assigned_model`, the model asked, beside `model`, the model ran,
        # which is None when nothing observed it. Neither stands in for the other. The engine's
        # `ending` and `detail` say how the agent finished, `in process` for the recorder it ran
        # itself, and its token fields hold the spend and the widest call. None means not recorded.
        'agents': [{**row, 'findings': per_slot.get(row.get('slot'), 0), 'none_found': row.get('slot') in none_found}
                   for row in run['agents']],
        'models_unverified': list(run['identity'].get('models_unverified') or []),
        'findings_by_track': dict(Counter(row['track'] for row in run['findings'] if row.get('track'))),
        'verdict': run['verdict'],
        'escalation_rulings': run['escalation_rulings'],
        'limitations': run['limitations'],
        'audits': audit_texts(run['reports']['audits']),
        'citations': citations,
        # `reviewed` is false for a run given no code, and every other key is then empty.
        'code': {**{key: run['code'][key] for key in CODE_VIEW}, 'data': list(data.values())},
        # `None` on a run given no code. A finding it threw out is listed here and in no card. A
        # check that filed no report is `silent`, a silent or failed check is `incomplete`, and the
        # claims it never answered stand as filed.
        'code_check': check and {**{key: check[key] for key in CODE_CHECK_VIEW},
                                 'thrown_out': thrown_out(check, ledger, data, base)},
        # The engine's record of the Read stage, or `None` for a manuscript sealed before the run,
        # which planned no reader. A reader that failed left the manuscript sealed as converted, so
        # every finding was made against the converter's text: `reader_failed` with its `reason`.
        'read': run['read'],
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
    return {'id': RUN_REVIEW_ID, 'paper_id': base.paper_id, 'source_sha256': source_sha256(base),
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
