"""A PeerReviewAgents run folder in the viewer: the run's review, its decisions and its export."""
import contextlib
import http.client
import io
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from peerreviewagents import ISSUES_SCHEMA_VERSION, read_run
from peerreviewagents.issues import ISSUE_FIELDS, MEMBER_FIELDS
from peerreviewagents.workspace import digest, write_json

from paper_workspace.__main__ import main
from paper_workspace.run_view import RunError, locate, run_review
from paper_workspace.server import make_server

TEXT = 'Knockdown lowered VPS35 in 12 samples.'
CEILING = 'the run reached its per-run token ceiling'
SONNET, HAIKU = 'claude-sonnet-5-5', 'claude-haiku-5-5'
# The six specialist lanes of engine 0.10.0, in the order its plan lists them.
LANES = ['stats', 'figures-tables', 'methods-reporting', 'citations', 'numbers', 'field']
# A citation ledger written by hand in the shape docs/INTEGRATIONS.md gives. README.md there says what it holds.
CITATIONS = Path(__file__).resolve().parent / 'fixtures' / 'citations'
NO_LEDGER = 'this run planned a citations lane and wrote no citation ledger, so there are no ledger counts'
UNREADABLE = ('review/citations/ledger.jsonl is present and could not be read (Permission denied), '
              'so this run has no citation counts')


def finding(uid, quote, **extra):
    start = TEXT.index(quote)
    return {'id': f'core-1-1-{uid}', 'finding_uid': uid, 'slot': 'core-1', 'kind': 'question',
            'severity': 'major', 'title': f'Finding {uid}', 'comment': 'Name the control.', 'block_id': 'b1',
            'quote': quote, 'start': start, 'end': start + len(quote), 'block_sha256': digest(TEXT),
            'placement': 'anchored', 'evidence_blocks': [], 'track': 'core', 'basis': 'judgement',
            'basis_reason': 'No arithmetic receipt.', 'escalate': False, **extra}


# The ledger of the run make_run writes: two findings the editor pooled into one
# major issue, and one suggested edit that is a minor issue of its own.
AA11 = finding('aa11', 'lowered VPS35', escalate=True)
BB22 = finding('bb22', '12 samples', slot='spec-numbers', track='numbers', severity='minor',
               comment='Say how the 12 samples were drawn.')
CC33 = finding('cc33', 'Knockdown', kind='edit', severity='minor', replacement='The knockdown',
               comment='Start with an article.')


def member(row):
    """The member the editor writes for a ledger finding: its uid, slot, quote and blocks, never its span."""
    return {key: row.get(key) for key in MEMBER_FIELDS}


def issue(number, name, severity, category, rows, **extra):
    """One issue row with every field the engine writes on every row."""
    return {**dict.fromkeys(ISSUE_FIELDS), 'id': f'i{number:02d}', 'name': name, 'severity': severity,
            'category': category, 'rank': number, 'statement': f'{name}, as the editor states it.',
            'members': [member(row) for row in rows], 'raised_by': len({row['slot'] for row in rows}),
            'status': 'new', 'surviving_quotes': [], 'audits': [], **extra}


ISSUES = [issue(1, 'The knockdown control is not named', 'major', 'claims-and-conclusions', [AA11, BB22]),
          issue(2, 'The opening sentence needs an article', 'minor', 'presentation', [CC33])]


def issues_document(issues=ISSUES, **extra):
    """``review/issues.json`` with every top-level key docs/INTEGRATIONS.md lists."""
    return {'schema_version': ISSUES_SCHEMA_VERSION, 'issues_source': 'editor', 'issues_source_reason': None,
            'issue_ids_used': [row['id'] for row in issues], 'summary': 'One central question.',
            'issues': issues, 'counts': {},
            'verdict': {'significance': 'High', 'strength_of_evidence': 'Weak', 'reasoning': 'Correlation.',
                        'basis': 'judgement', 'limitation': 'Advisory.'},
            'limitations': ['The editor read no supplement.'],
            'escalation_rulings': [{'finding_uid': 'aa11', 'ruling': 'Accepted.'}], 'escalated_count': 1,
            'prior_round': None, 'stages': {}, 'audits': ['audit_numbers.md', 'audit_stats.md'],
            'findings_by_track': {'core': 2, 'numbers': 1}, 'findings_delivered': 3, 'findings_submitted': 3,
            'quarantined_findings': [], 'quarantined_findings_count': 0, 'review_guard_status': 'clean',
            'reviewer_count': 3, 'reviewer_provenance': [], 'arm': 'full-two-track', 'synthesis_policy': 'editor',
            'finding_schema_version': None, 'workflow_version': None, **extra}


def make_run(root, issues=True, ledger=True):
    """A run folder as ``peerreview review`` leaves it, with two issues over three findings.

    With ``ledger`` the run holds the citation ledger fixture, as a run that
    planned the citations lane leaves it.
    """
    manuscript, review = root / 'manuscript', root / 'review'
    # The engine writes the plan into both the protocol and the manifest.
    plan = {'arm': 'full-two-track', 'reviewers': 3, 'specialists': LANES, 'citation_workers': ['cite-1']}
    write_json(manuscript / 'paper.json', {'id': 'qa', 'title': 'QA', 'source_sha256': 'qa-source',
        'blocks': [{'id': 'b1', 'text': TEXT, 'sha256': digest(TEXT)}], 'statistics': {'pdf_pages': 1}})
    write_json(manuscript / 'manifest.json', {'files': {'paper.json': digest((manuscript / 'paper.json').read_bytes())}})
    write_json(review / 'startup.json', {'problems': []})
    # `models` and each agent's `assigned_model` are the plan. An agent's `model` is what it reported
    # running, and the stream rows below carry the model each task was seen running.
    write_json(review / 'protocol.json', {'arm': 'full-two-track', 'reviewers': 3, 'plan': plan,
        'models': {'core-1': SONNET, 'recorder': HAIKU, 'spec-citations': SONNET, 'spec-numbers': SONNET,
                   'cite-1': HAIKU},
        'reviewer_models': [SONNET, 'claude-opus-5-5', HAIKU],
        'agents': {
            'core-1': {'role': 'core', 'track': 'core', 'tool_calls': 3, 'model': SONNET, 'assigned_model': SONNET},
            'recorder': {'role': 'recorder', 'track': 'ingest', 'tool_calls': 4, 'model': None,
                         'assigned_model': HAIKU},
            'spec-citations': {'role': 'specialist', 'track': 'citations', 'tool_calls': 2, 'model': SONNET,
                               'assigned_model': SONNET},
            'spec-numbers': {'role': 'specialist', 'track': 'numbers', 'tool_calls': 2, 'model': SONNET,
                             'assigned_model': SONNET},
            'cite-1': {'role': 'citation-worker', 'track': 'citations', 'tool_calls': 6, 'model': HAIKU,
                       'assigned_model': HAIKU}}})
    write_json(review / 'manifest.json', {'paper_id': 'qa', 'source_sha256': 'qa-source',
                                          'citation_ledger': 'citations/ledger.jsonl', 'plan': plan})
    if ledger:
        (review / 'citations').mkdir()
        for name in ('ledger.jsonl', 'stages.json'):
            shutil.copyfile(CITATIONS / name, review / 'citations' / name)
    write_json(review / 'progress.json', {'status': 'complete', 'error': None, 'arm': 'full-two-track', 'reviewers': 3,
        'stages': {'missing': [], 'none_found': ['spec-citations']}})
    # The stream names the recorder by its two tasks, and the last row is a label-only placeholder.
    write_json(review / 'runtime.json', {'status': 'complete', 'tokens_total': 900, 'wall_seconds': 120, 'agents': [
        {'label': 'core-1', 'agentType': 'pra:core', 'tokens': 500, 'toolCalls': 9, 'state': 'completed',
         'model': 'claude-sonnet-5-5'},
        {'label': 'ingest', 'agentType': 'pra:recorder', 'tokens': 120, 'toolCalls': 5, 'state': 'completed',
         'model': HAIKU},
        {'label': 'write review', 'agentType': 'pra:recorder', 'tokens': 280, 'toolCalls': 7,
         'state': 'completed', 'model': HAIKU},
        {'label': 'spec-field'}]})
    (review / 'findings.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in (AA11, BB22, CC33)))
    if issues:
        write_json(review / 'issues.json', issues_document())
    (review / 'audit_stats.md').write_text('# Statistics audit\n')
    (review / 'audit_numbers.md').write_text('# Numbers audit\n')
    return manuscript, review


def stop_run(review):
    """Leave the run as the starter does after a token ceiling: no protocol, manifest or issues.

    The ledger has a second, later row for ``aa11``, as the server appends one per submission.
    """
    for name in ('protocol.json', 'manifest.json', 'issues.json'):
        (review / name).unlink()
    write_json(review / 'progress.json', {'status': 'blocked', 'error': CEILING, 'arm': 'reviewers-only',
        'reviewers': 2, 'stages': {'missing': ['editor'], 'none_found': []}})
    write_json(review / 'runtime.json', {'status': 'blocked', 'blocked_reason': CEILING,
                                    'tokens_total': 4000, 'wall_seconds': 300})
    with (review / 'findings.jsonl').open('a') as stream:
        stream.write(json.dumps(finding('aa11', 'lowered VPS35', comment='Name the knockdown control.')) + '\n')


def run_quietly(argv):
    """Call the app command line and return its exit status, its stdout and its stderr."""
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
        status = main(argv)
    return status, stdout.getvalue(), stderr.getvalue()


class RunReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.manuscript, self.review = make_run(self.root)
        self.paper = json.loads((self.manuscript / 'paper.json').read_text())

    def tearDown(self):
        self.temporary.cleanup()

    def test_locate_accepts_the_run_folder_or_its_review_folder(self):
        self.assertEqual(locate(self.root), (self.manuscript, self.review))
        self.assertEqual(locate(self.review), (self.manuscript, self.review))
        self.assertEqual(locate(self.manuscript), (self.manuscript, None))
        (self.manuscript / 'paper.json').unlink()
        with self.assertRaisesRegex(RunError, 'stopped before it imported the manuscript'):
            locate(self.root)

    def test_a_folder_that_is_neither_a_workspace_nor_a_run_is_a_plain_error(self):
        (self.root / 'empty').mkdir()
        for path in (self.root / 'empty', self.root / 'missing'):
            status, output, message = run_quietly(['serve', str(path)])
            self.assertEqual((status, output), (1, ''))
            self.assertEqual(message,
                             f'paper-workbench: {path} is neither a manuscript workspace nor a run folder\n')

    def write_issues(self, issues=ISSUES, **extra):
        write_json(self.review / 'issues.json', issues_document(issues, **extra))

    def test_one_card_per_issue_required_changes_first(self):
        review = run_review(self.review, self.paper)
        self.assertEqual((review['id'], review['paper_id'], review['summary']), ('run', 'qa', 'One central question.'))
        self.assertEqual([(f['id'], f['group'], f['number'], f['kind'], f['severity'], f['raised_by'])
                          for f in review['findings']],
                         [('i01', 'required', 1, 'issue', 'major', 2), ('i02', 'suggestion', 2, 'edit', 'minor', 1)])
        pooled, edit = review['findings']
        self.assertEqual((pooled['title'], pooled['comment'], pooled['category'], pooled['escalate']),
                         ('The knockdown control is not named', 'The knockdown control is not named, as the editor '
                          'states it.', 'claims-and-conclusions', True))
        # Each member is joined to its ledger row for the comment and the span, and every one is placed.
        self.assertEqual([(m['finding_uid'], m['slot'], m['comment'], m['placement'], TEXT[m['start']:m['end']])
                          for m in pooled['members']],
                         [('aa11', 'core-1', 'Name the control.', 'anchored', 'lowered VPS35'),
                          ('bb22', 'spec-numbers', 'Say how the 12 samples were drawn.', 'anchored', '12 samples')])
        # The card is anchored where its first member is, so it can be found on the page.
        self.assertEqual((pooled['block_id'], pooled['quote'], pooled['placement'], pooled['replacement']),
                         ('b1', 'lowered VPS35', 'anchored', None))
        # One member that is an anchored edit makes the issue an edit, which accepting applies.
        self.assertEqual((edit['start'], edit['end'], edit['replacement'], edit['block_sha256']),
                         (0, 9, 'The knockdown', digest(TEXT)))
        run = review['run']
        self.assertEqual((run['arm'], run['status'], run['escalated_count'], run['findings_source'],
                          run['issues_source'], run['prior_round']),
                         ('full-two-track', 'complete', 1, 'issues', 'editor', None))
        self.assertEqual((run['counts']['issues'], run['counts']['required'], run['counts']['suggestions']), (2, 1, 1))
        self.assertNotIn('edited', run)
        self.assertEqual(run['none_found'], ['spec-citations'])
        self.assertEqual(run['escalation_rulings'], [{'finding_uid': 'aa11', 'ruling': 'Accepted.'}])
        self.assertEqual((run['tokens_total'], run['wall_seconds']), (900, 120))
        self.assertEqual(run['audits'], {'numbers': '# Numbers audit\n', 'stats': '# Statistics audit\n'})
        self.assertEqual(run['findings_by_track'], {'core': 2, 'numbers': 1})
        self.assertEqual((run['publishable'], run['not_publishable_reasons']), (True, []))

    def test_suggestions_follow_the_required_changes_grouped_by_category(self):
        rows = [issue(1, 'Wording', 'minor', 'presentation', [CC33]),
                issue(2, 'Cohort', 'minor', 'methods-and-reporting', [BB22]),
                issue(3, 'Control', 'moderate', 'claims-and-conclusions', [AA11])]
        self.write_issues(rows)
        findings = run_review(self.review, self.paper)['findings']
        self.assertEqual([(f['id'], f['group'], f['category']) for f in findings],
                         [('i03', 'required', 'claims-and-conclusions'),
                          ('i02', 'suggestion', 'methods-and-reporting'), ('i01', 'suggestion', 'presentation')])

    def test_a_prior_round_gives_each_issue_its_status(self):
        closed = {'rank': None, 'members': [], 'raised_by': 0}
        rows = [issue(1, 'The knockdown control is not named', 'major', 'claims-and-conclusions', [AA11, BB22],
                      status='persisting', prior_id='i01', prior_rank=1, status_reason='The control is still unnamed.'),
                issue(2, 'The opening sentence needs an article', 'minor', 'presentation', [CC33]),
                issue(3, 'The scale bar is missing', 'minor', 'figures-and-tables', [], status='resolved',
                      prior_id='i02', prior_rank=2, status_reason='Figure 1 now has a scale bar.', **closed),
                issue(4, 'The seed is not reported', 'moderate', 'reproducibility', [], status='unverified',
                      prior_id='i03', prior_rank=3, status_reason='No reviewer looked at the code.', **closed)]
        prior = {'file': 'issues.json', 'digest': '0123456789abcdef', 'issues': 3,
                 'tally': {'persisting': 1, 'regressed': 0, 'resolved': 1, 'unverified': 1}}
        self.write_issues(rows, prior_round=prior)
        review = run_review(self.review, self.paper)
        self.assertEqual([(f['id'], f['group'], f['status'], f['prior_id'], f['number']) for f in review['findings']],
                         [('i01', 'required', 'persisting', 'i01', 1), ('i02', 'suggestion', 'new', None, 2),
                          ('i03', 'closed', 'resolved', 'i02', None), ('i04', 'closed', 'unverified', 'i03', None)])
        self.assertEqual(review['findings'][2]['status_reason'], 'Figure 1 now has a scale bar.')
        # A closed issue has no members, so it has no anchor and nothing to accept.
        self.assertEqual([(f['placement'], f['kind'], f['members']) for f in review['findings'][2:]],
                         [('unplaced', 'issue', [])] * 2)
        run = review['run']
        self.assertEqual(run['prior_round'], prior)
        self.assertEqual((run['counts']['resolved'], run['counts']['unverified']), (1, 1))

    def test_issues_the_server_made_are_shown_with_the_reason_the_run_is_not_publishable(self):
        rows = [issue(n, row['title'], row['severity'], 'claims-and-conclusions', [row])
                for n, row in enumerate((AA11, BB22, CC33), 1)]
        self.write_issues(rows, issues_source='server', issues_source_reason='this arm has no editor')
        review = run_review(self.review, self.paper)
        self.assertEqual([f['id'] for f in review['findings']], ['i01', 'i02', 'i03'])
        run = review['run']
        self.assertEqual((run['issues_source'], run['publishable']), ('server', False))
        self.assertTrue(any('synthesised by the server' in line and 'this arm has no editor' in line
                            for line in run['not_publishable_reasons']), run['not_publishable_reasons'])

    def test_an_old_run_folder_shows_its_findings_and_why_it_is_not_a_review(self):
        # An engine before 0.10 wrote editor-package.json and no issues.json. The app does not read the package.
        (self.review / 'issues.json').rename(self.review / 'editor-package.json')
        review = run_review(self.review, self.paper)
        self.assertEqual([(f['id'], f['group'], f['number']) for f in review['findings']],
                         [('aa11', 'ledger', 1), ('bb22', 'ledger', 2), ('cc33', 'ledger', 3)])
        run = review['run']
        self.assertEqual((run['findings_source'], run['publishable']), ('ledger', False))
        self.assertTrue(any('no readable issues.json' in line for line in run['not_publishable_reasons']),
                        run['not_publishable_reasons'])
        self.assertEqual(review['summary'],
                         'The run finished without a readable issues.json, so its findings are not grouped into issues.')

    def test_an_unknown_schema_stamp_is_a_problem_and_the_findings_are_shown_ungrouped(self):
        self.write_issues(schema_version='review-issues-v9')
        review = run_review(self.review, self.paper)
        self.assertEqual([f['group'] for f in review['findings']], ['ledger'] * 3)
        self.assertTrue(any("'review-issues-v9'" in line for line in review['run']['problems']),
                        review['run']['problems'])
        self.assertFalse(review['run']['publishable'])

    def test_findings_no_issue_holds_follow_the_issues(self):
        self.write_issues(ISSUES[:1])
        findings = run_review(self.review, self.paper)['findings']
        self.assertEqual([(f['id'], f['group'], f['number'], f['kind']) for f in findings],
                         [('i01', 'required', 1, 'issue'), ('cc33', 'ledger', 2, 'edit')])
        self.assertEqual([m['finding_uid'] for m in findings[1]['members']], ['cc33'])

    def test_a_member_without_its_ledger_row_is_placed_by_its_quote(self):
        # With an empty ledger the engine rebuilds the findings from the members, which carry no span.
        (self.review / 'findings.jsonl').write_text('')
        findings = run_review(self.review, self.paper)['findings']
        self.assertEqual([[(m['placement'], m['start']) for m in f['members']] for f in findings],
                         [[('anchored', TEXT.index('lowered VPS35')), ('anchored', TEXT.index('12 samples'))],
                          [('anchored', 0)]])
        # Without its ledger row the edit has no wording, so the issue takes a note instead.
        self.assertEqual((findings[1]['kind'], findings[1]['replacement']), ('issue', None))

    def test_a_member_whose_quote_is_not_in_its_block_is_unplaced(self):
        rows = json.loads(json.dumps(ISSUES))
        rows[0]['members'][1]['quote'] = 'twelve donors'
        self.write_issues(rows)
        lines = [json.loads(line) for line in (self.review / 'findings.jsonl').read_text().splitlines()]
        lines[1]['quote'] = 'twelve donors'
        (self.review / 'findings.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in lines))
        pooled = run_review(self.review, self.paper)['findings'][0]
        self.assertEqual([(m['placement'], m['start']) for m in pooled['members']],
                         [('anchored', TEXT.index('lowered VPS35')), ('unplaced', None)])
        self.assertEqual(pooled['placement'], 'anchored')

    def test_each_agent_is_one_row_and_placeholders_are_dropped(self):
        agents = {row['slot']: row for row in run_review(self.review, self.paper)['run']['agents']}
        self.assertEqual(list(agents), ['cite-1', 'core-1', 'recorder', 'spec-citations', 'spec-numbers'])
        recorder = agents['recorder']
        self.assertEqual((recorder['labels'], recorder['tokens'], recorder['session_calls'], recorder['tool_calls']),
                         (['ingest', 'write review'], 400, 12, 4))
        self.assertEqual((agents['spec-citations']['none_found'], agents['spec-citations']['tokens']), (True, None))
        # A citation worker is its own row and holds no review.
        self.assertEqual((agents['cite-1']['role'], agents['cite-1']['track'], agents['cite-1']['findings']),
                         ('citation-worker', 'citations', 0))
        self.assertEqual((agents['spec-numbers']['role'], agents['spec-numbers']['track']), ('specialist', 'numbers'))

    def test_each_agent_keeps_the_model_asked_beside_the_model_ran(self):
        run = run_review(self.review, self.paper)['run']
        self.assertEqual({row['slot']: (row['assigned_model'], row['model']) for row in run['agents']},
                         {'cite-1': (HAIKU, HAIKU), 'core-1': (SONNET, SONNET), 'recorder': (HAIKU, HAIKU),
                          'spec-citations': (SONNET, SONNET), 'spec-numbers': (SONNET, SONNET)})
        self.assertEqual((run['models_unverified'], run['publishable'], run['problems']), ([], True, []))
        protocol = json.loads((self.review / 'protocol.json').read_text())
        # A slot nothing observed has no model ran, never its model asked, and is named as unverified.
        protocol['agents']['spec-citations']['model'] = None
        write_json(self.review / 'protocol.json', protocol)
        run = run_review(self.review, self.paper)['run']
        row = next(row for row in run['agents'] if row['slot'] == 'spec-citations')
        self.assertEqual((row['assigned_model'], row['model']), (SONNET, None))
        self.assertEqual((run['models_unverified'], run['publishable'], run['problems']),
                         (['spec-citations'], True, []))
        # A slot that ran another model family is a problem, and the review is not publishable.
        protocol['agents']['spec-citations']['model'] = 'claude-opus-5-5'
        write_json(self.review / 'protocol.json', protocol)
        run = run_review(self.review, self.paper)['run']
        self.assertEqual((run['models_unverified'], run['publishable']), ([], False))
        for lines in (run['problems'], run['not_publishable_reasons']):
            self.assertTrue(any(line.startswith('spec-citations was assigned') and 'ran claude-opus-5-5' in line
                                for line in lines), lines)

    def test_a_review_without_findings_is_publishable_unless_the_guard_held_some(self):
        self.write_issues([], findings_delivered=0, findings_submitted=0, escalation_rulings=[], escalated_count=0)
        (self.review / 'findings.jsonl').write_text('')
        for name in ('progress.json', 'runtime.json'):
            record = json.loads((self.review / name).read_text())
            write_json(self.review / name, {**record, 'status': 'complete-without-findings'})
        run = run_review(self.review, self.paper)['run']
        self.assertEqual((run['status'], run['quarantined_findings_count'], run['publishable']),
                         ('complete-without-findings', 0, True))
        held = finding('cc33', '12 samples')
        (self.review / 'quarantined.jsonl').write_text(json.dumps(held) + '\n' + json.dumps(held) + '\n')
        run = run_review(self.review, self.paper)['run']
        self.assertEqual((run['quarantined_findings_count'], run['publishable']), (2, False))
        self.assertTrue(any('quarantined 2' in reason for reason in run['not_publishable_reasons']),
                        run['not_publishable_reasons'])

    def test_a_repeated_issue_id_falls_back_to_positional_ids(self):
        rows = json.loads(json.dumps(ISSUES))
        rows[1]['id'] = 'i01'
        self.write_issues(rows)
        self.assertEqual([f['id'] for f in run_review(self.review, self.paper)['findings']], ['run-1', 'run-2'])

    def test_a_malformed_finding_uid_falls_back_to_positional_ids(self):
        (self.review / 'issues.json').unlink()
        with (self.review / 'findings.jsonl').open('a') as stream:
            stream.write(json.dumps(finding('not a uid', '12 samples')) + '\n')
        self.assertEqual([f['id'] for f in run_review(self.review, self.paper)['findings']],
                         ['run-1', 'run-2', 'run-3', 'run-4'])

    def test_a_run_on_another_manuscript_version_is_refused(self):
        write_json(self.review / 'manifest.json', {'paper_id': 'qa', 'source_sha256': 'other'})
        with self.assertRaisesRegex(ValueError, 'different manuscript version'):
            run_review(self.review, self.paper)

    def test_a_run_without_issues_shows_the_recorded_findings(self):
        (self.review / 'issues.json').unlink()
        write_json(self.review / 'progress.json', {'status': 'blocked', 'error': 'editor timed out', 'stages': {}})
        write_json(self.review / 'runtime.json', {'status': 'blocked', 'tokens_total': 900, 'wall_seconds': 120})
        review = run_review(self.review, self.paper)
        self.assertEqual([(f['id'], f['group']) for f in review['findings']],
                         [('aa11', 'ledger'), ('bb22', 'ledger'), ('cc33', 'ledger')])
        self.assertEqual((review['run']['findings_source'], review['run']['publishable']), ('ledger', False))
        self.assertEqual(review['summary'], 'The run stopped before the editor wrote its issues: editor timed out')

    def test_the_ledger_keeps_the_latest_row_of_each_finding(self):
        with (self.review / 'findings.jsonl').open('a') as stream:
            stream.write(json.dumps(finding('aa11', 'lowered VPS35', comment='Second submission.')) + '\n')
        # A member takes its comment from the latest row.
        pooled = run_review(self.review, self.paper)['findings'][0]
        self.assertEqual([m['comment'] for m in pooled['members']],
                         ['Second submission.', 'Say how the 12 samples were drawn.'])
        (self.review / 'issues.json').unlink()
        findings = run_review(self.review, self.paper)['findings']
        self.assertEqual([(f['id'], f['comment']) for f in findings],
                         [('aa11', 'Second submission.'), ('bb22', 'Say how the 12 samples were drawn.'),
                          ('cc33', 'Start with an article.')])

    def test_an_empty_editor_summary_is_not_reported_as_missing_issues(self):
        self.write_issues(summary='')
        review = run_review(self.review, self.paper)
        self.assertEqual((review['summary'], review['run']['findings_source']), ('The editor wrote no summary.', 'issues'))

    def test_a_symlinked_run_file_is_an_error_not_a_missing_file(self):
        package = self.review / 'issues.json'
        outside = self.root / 'outside.json'
        package.rename(outside)
        package.symlink_to(outside)
        with self.assertRaisesRegex(RunError, 'Refusing to read issues.json: a run file must not be a symlink'):
            run_review(self.review, self.paper)
        package.unlink()
        secret = self.root / 'secret.md'
        secret.write_text('outside the review folder')
        (self.review / 'audit_leak.md').symlink_to(secret)
        with self.assertRaisesRegex(RunError, 'Refusing to read audit_leak.md'):
            run_review(self.review, self.paper)
        status, _, message = run_quietly(['serve', str(self.root)])
        self.assertEqual(status, 1)
        self.assertIn('Refusing to read audit_leak.md', message)

    def test_the_engine_problems_reach_the_run_panel(self):
        (self.review / 'runtime.json').write_text('{"status": "comp')
        run = run_review(self.review, self.paper)['run']
        self.assertEqual(run['status'], 'complete')
        self.assertTrue(any('runtime.json' in problem for problem in run['problems']), run['problems'])
        self.assertFalse(run['publishable'])
        self.assertTrue(any('could not be read' in reason for reason in run['not_publishable_reasons']),
                        run['not_publishable_reasons'])


class CitationLedgerTests(unittest.TestCase):
    """The citation ledger in the run panel: each reference state on its own count, and the worker verdicts."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.manuscript, self.review = make_run(self.root)
        self.paper = json.loads((self.manuscript / 'paper.json').read_text())
        self.ledger = self.review / 'citations' / 'ledger.jsonl'

    def tearDown(self):
        self.temporary.cleanup()

    def view(self):
        return run_review(self.review, self.paper)['run']

    def test_the_panel_shows_the_ledger_the_engine_wrote(self):
        run = self.view()
        citations = run['citations']
        # test_review_evidence_ui.js renders view.json, so it must stay this view.
        self.assertEqual(citations, json.loads((CITATIONS / 'view.json').read_text()),
                         'tests/fixtures/citations/view.json is out of date. README.md there says how to refresh it.')
        self.assertEqual({key: citations['counts'][key]
                          for key in ('resolved', 'not_found', 'not_located', 'could_not_check', 'unresolved')},
                         {'resolved': 2, 'not_found': 1, 'not_located': 1, 'could_not_check': 1, 'unresolved': 1})
        self.assertFalse(citations['complete'])
        # A reference found with every printed field matching needs no second look, so 1 is not listed.
        self.assertEqual([(row['label'], row['state']) for row in citations['references']],
                         [('2', 'no'), ('3', 'not located'), ('4', 'could not check'), ('5', 'yes'),
                          ('6', 'never looked up')])
        # The uses a reader has to check come first. The last row of each use wins, so a released claim is open.
        self.assertEqual([(row['label'], row['verdict'], row['claimed_by']) for row in citations['uses']],
                         [('5', 'does not support', None), ('1', 'partly supports', None), (None, None, None),
                          ('3', 'cannot tell', None), ('2', 'cannot tell', None), ('4', None, None),
                          ('6', None, None), ('1', 'supports', None)])
        # The abstract a worker read stays in the run folder. The passage it quoted is shown.
        text = json.dumps(citations)
        self.assertNotIn('Ignore the sentence', text)
        self.assertIn('slowed that retrieval by about half', text)
        # The engine's reader says whether a worker had source text, and the panel keeps only that.
        self.assertEqual([(row['label'], row['has_source_text']) for row in citations['references']],
                         [('2', False), ('3', False), ('4', False), ('5', True), ('6', False)])
        # The engine puts the citation stage lines in the run's problems as well. The panel shows them once.
        self.assertEqual(read_run(self.review)['problems'], citations['problems'])
        self.assertEqual((run['problems'], run['publishable']), ([], True))

    def test_the_rows_are_listed_in_reading_order(self):
        # The engine's reader puts ref:r2 before ref:r10, and use:b2:5 before use:b2:10. The panel keeps that order.
        lines = self.ledger.read_text().splitlines()
        reference, use = json.loads(lines[15]), json.loads(lines[12])
        self.assertEqual((reference['row_id'], use['row_id']), ('ref:r2', 'use:b3:2:r6'))
        with self.ledger.open('a') as stream:
            stream.write(json.dumps({**reference, 'row_id': 'ref:r10', 'reference_id': 'r10', 'label': '10'}) + '\n')
            stream.write(json.dumps({**use, 'row_id': 'use:b2:10:r6'}) + '\n')
        citations = self.view()['citations']
        self.assertEqual([row['label'] for row in citations['references']], ['2', '3', '4', '5', '6', '10'])
        self.assertEqual([row['row_id'] for row in citations['uses'] if row['reference_id'] and not row['verdict']],
                         ['use:b2:5:r4', 'use:b2:10:r6', 'use:b3:2:r6'])

    def test_a_planned_lane_without_a_ledger_says_there_are_no_counts(self):
        shutil.rmtree(self.review / 'citations')
        run = self.view()
        self.assertEqual(run['citations'], {'complete': False, 'problems': [NO_LEDGER], 'ledger': False,
                                            'readable': False, 'counts': {}, 'references': [],
                                            'references_not_shown': 0, 'uses': [], 'uses_not_shown': 0})
        self.assertEqual((run['problems'], run['publishable']), ([], True))

    def test_a_run_without_a_citations_lane_has_no_citations_panel(self):
        shutil.rmtree(self.review / 'citations')
        plan = {'arm': 'full-two-track', 'reviewers': 3, 'citation_workers': [],
                'specialists': [lane for lane in LANES if lane != 'citations']}
        protocol = json.loads((self.review / 'protocol.json').read_text())
        for slot in ('spec-citations', 'cite-1'):
            del protocol['agents'][slot], protocol['models'][slot]
        write_json(self.review / 'protocol.json', {**protocol, 'plan': plan})
        write_json(self.review / 'manifest.json', {'paper_id': 'qa', 'source_sha256': 'qa-source',
                                                   'citation_ledger': None, 'plan': plan})
        progress = json.loads((self.review / 'progress.json').read_text())
        write_json(self.review / 'progress.json', {**progress, 'stages': {'missing': [], 'none_found': []}})
        run = self.view()
        self.assertEqual((run['citations'], run['problems'], run['publishable']), (None, [], True))

    def test_a_torn_ledger_line_is_counted_and_the_rows_before_it_stand(self):
        with self.ledger.open('ab') as stream:
            stream.write(b'{"kind": "use", "row_id": "use:b2:1:r1", "verdict": "does not')
        citations = self.view()['citations']
        self.assertEqual((citations['counts']['unreadable_rows'], len(citations['uses'])), (1, 8))
        self.assertIn('1 line(s) of the citation ledger could not be read and were skipped', citations['problems'])
        self.assertEqual((citations['uses'][-1]['row_id'], citations['uses'][-1]['verdict']),
                         ('use:b2:1:r1', 'supports'))

    def test_reading_the_run_writes_nothing_to_it(self):
        # The viewer only reads a run. The engine's readers must not add a file to the review folder.
        before = sorted(str(path.relative_to(self.review)) for path in self.review.rglob('*'))
        self.view()
        self.assertEqual(sorted(str(path.relative_to(self.review)) for path in self.review.rglob('*')), before)

    @unittest.skipIf(os.name != 'posix' or os.geteuid() == 0, 'needs a user that file modes apply to')
    def test_a_read_only_run_shows_its_citations(self):
        # A run copied or archived without write access shows the same citation panel.
        folders = [self.review, *(path for path in self.review.rglob('*') if path.is_dir())]
        for folder in folders:
            folder.chmod(0o555)
        try:
            self.assertEqual(self.view()['citations'], json.loads((CITATIONS / 'view.json').read_text()))
        finally:
            for folder in folders:
                folder.chmod(0o755)

    @unittest.skipIf(os.name != 'posix' or os.geteuid() == 0, 'needs a user that file modes apply to')
    def test_an_unreadable_ledger_is_named_and_shows_no_counts(self):
        self.ledger.chmod(0)
        try:
            run = self.view()
        finally:
            self.ledger.chmod(0o644)
        citations = run['citations']
        self.assertEqual((citations['ledger'], citations['readable'], citations['counts'], citations['uses']),
                         (True, False, {}, []))
        # The line names the file in the run folder and is shown once, in the citation section.
        self.assertIn(UNREADABLE, citations['problems'])
        self.assertNotIn(UNREADABLE, run['problems'])
        # A citation ledger the viewer cannot open does not hold the review back.
        self.assertEqual((run['publishable'], run['not_publishable_reasons']), (True, []))

    def test_a_symlinked_ledger_is_refused(self):
        outside = self.root / 'outside.jsonl'
        self.ledger.rename(outside)
        self.ledger.symlink_to(outside)
        with self.assertRaisesRegex(RunError, 'citations/ledger.jsonl'):
            run_review(self.review, self.paper)

    def test_long_ledger_text_is_shortened(self):
        row = json.loads(self.ledger.read_text().splitlines()[-1])
        with self.ledger.open('a') as stream:
            stream.write(json.dumps({**row, 'sentence': 'x' * 5_000}) + '\n')
        use = next(use for use in self.view()['citations']['uses'] if use['row_id'] == row['row_id'])
        self.assertEqual(use['sentence'], 'x' * 1_500 + ' [shortened by the viewer]')

    def test_a_citation_worker_on_another_model_is_reported_and_the_run_stays_publishable(self):
        protocol = json.loads((self.review / 'protocol.json').read_text())
        protocol['agents']['cite-1']['model'] = 'claude-opus-5-5'
        write_json(self.review / 'protocol.json', protocol)
        run = self.view()
        self.assertTrue(any(line.startswith(f'cite-1 was assigned {HAIKU} but ran claude-opus-5-5')
                            for line in run['problems']), run['problems'])
        self.assertEqual((run['publishable'], run['not_publishable_reasons']), (True, []))


class StoppedRunTests(unittest.TestCase):
    """A run the starter stopped mid-session has progress, runtime and the ledger, and nothing else."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.manuscript, self.review = make_run(self.root)
        stop_run(self.review)
        self.paper = json.loads((self.manuscript / 'paper.json').read_text())

    def tearDown(self):
        self.temporary.cleanup()

    def test_a_stopped_run_opens_with_what_it_recorded(self):
        self.assertEqual(locate(self.root), (self.manuscript, self.review))
        review = run_review(self.review, self.paper)
        self.assertEqual([(f['id'], f['group'], f['comment']) for f in review['findings']],
                         [('aa11', 'ledger', 'Name the knockdown control.'),
                          ('bb22', 'ledger', 'Say how the 12 samples were drawn.'),
                          ('cc33', 'ledger', 'Start with an article.')])
        run = review['run']
        self.assertEqual((run['status'], run['cause'], run['findings_source'], run['missing_stages']),
                         ('blocked', CEILING, 'ledger', ['editor']))
        self.assertEqual((run['tokens_total'], run['wall_seconds'], run['problems']), (4000, 300, []))
        self.assertEqual(review['summary'], f'The run stopped before the editor wrote its issues: {CEILING}')
        make_server(self.root, 0).server_close()

    def test_without_a_manifest_the_block_hashes_pin_the_version(self):
        rows = [json.loads(line) for line in (self.review / 'findings.jsonl').read_text().splitlines()]
        rows[-1]['block_sha256'] = digest('An earlier version of the sentence.')
        (self.review / 'findings.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
        with self.assertRaisesRegex(RunError, 'different manuscript version'):
            run_review(self.review, self.paper)

    def test_report_renders_what_the_stopped_run_recorded(self):
        status, output, _ = run_quietly(['report', str(self.root)])
        self.assertEqual(status, 0)
        summary = json.loads(output)
        self.assertEqual((summary['status'], summary['cause']), ('blocked', CEILING))
        self.assertTrue((self.review / 'REVIEW.md').is_file())

    def test_a_startup_blocked_run_cannot_be_served_and_its_report_says_why(self):
        run = self.root / 'startup-only'
        write_json(run / 'review' / 'startup.json', {'problems': ['claude is not installed']})
        write_json(run / 'review' / 'runtime.json', {'status': 'blocked',
            'blocked_reason': 'the start-up probe failed: claude is not installed'})
        status, _, message = run_quietly(['serve', str(run)])
        self.assertEqual(status, 1)
        self.assertIn('stopped before it imported the manuscript', message)
        self.assertIn('claude is not installed', message)
        self.assertNotIn('Traceback', message)
        status, output, _ = run_quietly(['report', str(run)])
        self.assertEqual(status, 0)
        self.assertIn('claude is not installed', json.loads(output)['cause'])


class RunServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.manuscript, self.review = make_run(self.root)
        self.server = make_server(self.root, 0)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temporary.cleanup()

    def request(self, path, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        headers = {'Host': f'127.0.0.1:{self.port}'}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        try:
            connection.request('POST' if body is not None else 'GET', path,
                               body=json.dumps(body).encode() if body is not None else None, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_the_run_is_listed_shown_decided_and_exported(self):
        self.assertEqual(self.request('/api/reviews'), (200, ['run']))
        status, review = self.request('/api/review?review=run')
        self.assertEqual(status, 200)
        self.assertEqual([f['id'] for f in review['findings']], ['i01', 'i02'])
        self.assertEqual(review['run']['verdict']['basis'], 'judgement')
        self.assertEqual(review['run']['citations']['counts']['references'], 6)
        # One decision per issue: a note on the pooled issue, and the edit accepted.
        status, decisions = self.request('/api/decisions', {'review_id': 'run', 'annotation_id': 'i01',
            'status': 'noted', 'revision': 0, 'author_comment': 'Named the control in Methods.'})
        self.assertEqual((status, decisions['items']), (200, {'i01': 'noted'}))
        status, body = self.request('/api/decisions', {'review_id': 'run', 'annotation_id': 'i01',
            'status': 'accepted', 'revision': 1})
        self.assertEqual((status, body), (400, {'error': 'Invalid decision for this finding'}))
        status, decisions = self.request('/api/decisions', {'review_id': 'run', 'annotation_id': 'i02',
            'status': 'accepted', 'revision': 1})
        self.assertEqual((status, decisions['items']), (200, {'i01': 'noted', 'i02': 'accepted'}))
        # Decisions live in the manuscript workspace. The review folder stays as the run wrote it.
        saved = json.loads((self.manuscript / 'decisions' / 'run.json').read_text())
        self.assertEqual(saved['annotations']['i01']['author_comment'], 'Named the control in Methods.')
        self.assertFalse((self.review / 'decisions').exists())
        status, exported = self.request('/api/export?review=run')
        self.assertEqual((status, exported['review_id'], exported['run']['arm']), (200, 'run', 'full-two-track'))
        self.assertEqual([(f['id'], [m['finding_uid'] for m in f['members']]) for f in exported['findings']],
                         [('i01', ['aa11', 'bb22']), ('i02', ['cc33'])])
        self.assertEqual([b['text'] for b in exported['proposed_blocks']], ['The knockdown lowered VPS35 in 12 samples.'])

    def test_a_mismatched_run_is_an_error_not_a_misplaced_review(self):
        write_json(self.review / 'manifest.json', {'paper_id': 'qa', 'source_sha256': 'other'})
        status, body = self.request('/api/review?review=run')
        self.assertEqual((status, body), (400, {'error': 'The run reviewed a different manuscript version'}))

    def test_a_stopped_run_is_served_with_its_status(self):
        stop_run(self.review)
        status, review = self.request('/api/review?review=run')
        self.assertEqual(status, 200)
        self.assertEqual((review['run']['status'], review['run']['cause']), ('blocked', CEILING))
        self.assertEqual([f['id'] for f in review['findings']], ['aa11', 'bb22', 'cc33'])


if __name__ == '__main__':
    unittest.main()
