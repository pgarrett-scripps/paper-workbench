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

from peerreviewagents import read_run
from peerreviewagents.workspace import digest, write_json

from paper_workspace.__main__ import main
from paper_workspace.run_view import RunError, locate, run_review
from paper_workspace.server import make_server

TEXT = 'Knockdown lowered VPS35 in 12 samples.'
CEILING = 'the run reached its per-run token ceiling'
SONNET, HAIKU = 'claude-sonnet-5-5', 'claude-haiku-5-5'
# The six specialist lanes of engine 0.9.0, in the order its plan lists them.
LANES = ['stats', 'figures-tables', 'methods-reporting', 'citations', 'numbers', 'field']
# A citation ledger written by hand in the shape docs/INTEGRATIONS.md gives. README.md there says what it holds.
CITATIONS = Path(__file__).resolve().parent / 'fixtures' / 'citations'
NO_LEDGER = 'this run planned a citations lane and wrote no citation ledger, so there are no ledger counts'
UNREADABLE = ('review/citations/ledger.jsonl is present and could not be read (Permission denied), '
              'so this run has no citation counts')


def finding(uid, quote, **extra):
    start = TEXT.index(quote)
    return {'id': f'core-1-1-{uid}', 'finding_uid': uid, 'kind': 'question', 'category': 'scientific',
            'severity': 'major', 'title': f'Finding {uid}', 'comment': 'Name the control.', 'block_id': 'b1',
            'quote': quote, 'start': start, 'end': start + len(quote), 'block_sha256': digest(TEXT),
            'placement': 'anchored', 'evidence_blocks': [], 'track': 'core', 'basis': 'judgement',
            'basis_reason': 'No arithmetic receipt.', 'escalate': False, **extra}


def make_run(root, package=True, ledger=True):
    """A run folder as ``peerreview review`` leaves it, with one body finding and one duplicate.

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
    body = finding('aa11', 'lowered VPS35', track='field', escalate=True, editor_reason='Central claim.',
                   reviewers_raising=2, duplicate_uids=['bb22'])
    appendix = finding('bb22', '12 samples', track='numbers', editor_placement='duplicate', duplicate_of='aa11',
                       editor_reason='Same objection.', rebuttal_quote=None)
    (review / 'findings.jsonl').write_text(json.dumps(body) + '\n' + json.dumps(appendix) + '\n')
    if package:
        write_json(review / 'editor-package.json', {'summary': 'One central question.', 'arm': 'full-two-track',
            'findings': [body], 'appendix': [appendix], 'escalated_count': 1, 'reviewer_count': 3,
            'review_guard_status': 'clean', 'findings_by_track': {'field': 1, 'numbers': 1},
            'verdict': {'significance': 'High', 'strength_of_evidence': 'Weak', 'reasoning': 'Correlation.',
                        'basis': 'judgement', 'limitation': 'Advisory.'},
            'escalation_rulings': [{'finding_uid': 'aa11', 'ruling': 'Accepted.'}],
            'reviewer_provenance': [{'slot': 'core-1', 'track': 'core', 'model': SONNET, 'assigned_model': SONNET,
                                     'attempt': 1, 'tool_calls': 3, 'findings': 1, 'none_found': False}]})
    (review / 'audit_stats.md').write_text('# Statistics audit\n')
    (review / 'audit_numbers.md').write_text('# Numbers audit\n')
    return manuscript, review


def stop_run(review):
    """Leave the run as the starter does after a token ceiling: no protocol, manifest or package.

    The ledger has a second, later row for ``aa11``, as the server appends one per submission.
    """
    for name in ('protocol.json', 'manifest.json', 'editor-package.json'):
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

    def test_body_then_appendix_keyed_by_finding_uid(self):
        review = run_review(self.review, self.paper)
        self.assertEqual((review['id'], review['paper_id'], review['summary']), ('run', 'qa', 'One central question.'))
        self.assertEqual([(f['id'], f['section'], f['number'], f['source_id']) for f in review['findings']],
                         [('aa11', 'body', 1, 'core-1-1-aa11'), ('bb22', 'appendix', 2, 'core-1-1-bb22')])
        run = review['run']
        self.assertEqual((run['arm'], run['status'], run['edited'], run['escalated_count']),
                         ('full-two-track', 'complete', True, 1))
        self.assertEqual(run['none_found'], ['spec-citations'])
        self.assertEqual(run['escalation_rulings'], [{'finding_uid': 'aa11', 'ruling': 'Accepted.'}])
        self.assertEqual((run['tokens_total'], run['wall_seconds']), (900, 120))
        self.assertEqual(run['audits'], {'numbers': '# Numbers audit\n', 'stats': '# Statistics audit\n'})
        self.assertEqual(run['findings_by_track'], {'field': 1, 'numbers': 1})

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
        package = json.loads((self.review / 'editor-package.json').read_text())
        package['findings'], package['appendix'] = [], []
        write_json(self.review / 'editor-package.json', package)
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

    def test_missing_or_malformed_finding_uids_fall_back_to_positional_ids(self):
        original = json.loads((self.review / 'editor-package.json').read_text())
        for uid in (None, 'not a uid'):
            with self.subTest(uid=uid):
                package = json.loads(json.dumps(original))
                package['appendix'][0]['finding_uid'] = uid
                write_json(self.review / 'editor-package.json', package)
                self.assertEqual([f['id'] for f in run_review(self.review, self.paper)['findings']],
                                 ['run-1', 'run-2'])

    def test_a_run_on_another_manuscript_version_is_refused(self):
        write_json(self.review / 'manifest.json', {'paper_id': 'qa', 'source_sha256': 'other'})
        with self.assertRaisesRegex(ValueError, 'different manuscript version'):
            run_review(self.review, self.paper)

    def test_a_run_without_an_editor_package_shows_the_recorded_findings(self):
        (self.review / 'editor-package.json').unlink()
        write_json(self.review / 'progress.json', {'status': 'blocked', 'error': 'editor timed out', 'stages': {}})
        write_json(self.review / 'runtime.json', {'status': 'blocked', 'tokens_total': 900, 'wall_seconds': 120})
        review = run_review(self.review, self.paper)
        self.assertEqual([(f['id'], f['section']) for f in review['findings']], [('aa11', 'body'), ('bb22', 'body')])
        self.assertFalse(review['run']['edited'])
        self.assertIn('editor timed out', review['summary'])

    def test_the_ledger_keeps_the_latest_row_of_each_finding(self):
        (self.review / 'editor-package.json').unlink()
        with (self.review / 'findings.jsonl').open('a') as stream:
            stream.write(json.dumps(finding('aa11', 'lowered VPS35', comment='Second submission.')) + '\n')
        findings = run_review(self.review, self.paper)['findings']
        self.assertEqual([(f['finding_uid'], f['comment']) for f in findings],
                         [('aa11', 'Second submission.'), ('bb22', 'Name the control.')])
        # Saved decisions stay attached, because the ids are still the finding uids.
        self.assertEqual([f['id'] for f in findings], ['aa11', 'bb22'])

    def test_an_empty_editor_summary_is_not_reported_as_a_missing_package(self):
        package = json.loads((self.review / 'editor-package.json').read_text())
        package['summary'] = ''
        write_json(self.review / 'editor-package.json', package)
        review = run_review(self.review, self.paper)
        self.assertEqual((review['summary'], review['run']['edited']), ('The editor wrote no summary.', True))

    def test_a_symlinked_run_file_is_an_error_not_a_missing_file(self):
        package = self.review / 'editor-package.json'
        outside = self.root / 'outside.json'
        package.rename(outside)
        package.symlink_to(outside)
        with self.assertRaisesRegex(RunError, 'Refusing to read editor-package.json: a run file must not be a symlink'):
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

    def test_the_references_are_listed_in_reading_order(self):
        # The engine orders rows by row_id as text, which puts ref:r10 before ref:r2.
        row = json.loads(self.ledger.read_text().splitlines()[15])
        self.assertEqual(row['row_id'], 'ref:r2')
        with self.ledger.open('a') as stream:
            stream.write(json.dumps({**row, 'row_id': 'ref:r10', 'reference_id': 'r10', 'label': '10'}) + '\n')
        self.assertEqual([row['label'] for row in self.view()['citations']['references']],
                         ['2', '3', '4', '5', '6', '10'])

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
        self.assertEqual([(f['id'], f['comment']) for f in review['findings']],
                         [('aa11', 'Name the knockdown control.'), ('bb22', 'Name the control.')])
        run = review['run']
        self.assertEqual((run['status'], run['cause'], run['edited'], run['missing_stages']),
                         ('blocked', CEILING, False, ['editor']))
        self.assertEqual((run['tokens_total'], run['wall_seconds'], run['problems']), (4000, 300, []))
        self.assertEqual(review['summary'], f'The run stopped before the editor wrote its package: {CEILING}')
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
        self.assertEqual([f['id'] for f in review['findings']], ['aa11', 'bb22'])
        self.assertEqual(review['run']['verdict']['basis'], 'judgement')
        self.assertEqual(review['run']['citations']['counts']['references'], 6)
        status, decisions = self.request('/api/decisions', {'review_id': 'run', 'annotation_id': 'bb22',
            'status': 'noted', 'revision': 0, 'author_comment': 'Merged with 1.'})
        self.assertEqual((status, decisions['items']), (200, {'bb22': 'noted'}))
        # Decisions live in the manuscript workspace. The review folder stays as the run wrote it.
        saved = json.loads((self.manuscript / 'decisions' / 'run.json').read_text())
        self.assertEqual(saved['annotations']['bb22']['author_comment'], 'Merged with 1.')
        self.assertFalse((self.review / 'decisions').exists())
        status, exported = self.request('/api/export?review=run')
        self.assertEqual((status, exported['review_id'], exported['run']['arm']), (200, 'run', 'full-two-track'))
        self.assertEqual([f['finding_uid'] for f in exported['findings']], ['aa11', 'bb22'])

    def test_a_mismatched_run_is_an_error_not_a_misplaced_review(self):
        write_json(self.review / 'manifest.json', {'paper_id': 'qa', 'source_sha256': 'other'})
        status, body = self.request('/api/review?review=run')
        self.assertEqual((status, body), (400, {'error': 'The run reviewed a different manuscript version'}))

    def test_a_stopped_run_is_served_with_its_status(self):
        stop_run(self.review)
        status, review = self.request('/api/review?review=run')
        self.assertEqual(status, 200)
        self.assertEqual((review['run']['status'], review['run']['cause']), ('blocked', CEILING))
        self.assertEqual([f['id'] for f in review['findings']], ['aa11', 'bb22'])


if __name__ == '__main__':
    unittest.main()
