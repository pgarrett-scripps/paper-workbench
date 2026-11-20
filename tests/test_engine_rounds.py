"""Two review rounds built by the engine's scripted review, read by the viewer.

``scripted_review`` runs a real review through the engine's own orchestrator
on a sealed manuscript, with a script of this file in each seat the arm plans
in place of a model, so no model is started and nothing reaches the network.
Each script acts through its own slot's tools, the code check's as well, so
nothing here reaches past the engine's public names. This file builds two
rounds that way, each a fresh panel on its own draft that knows nothing of the
other, and a third run given analysis code whose code lane fetches two data
files and files one code-checked finding, and whose code check throws out the
numbers lane's finding, and drives the viewer from them. Two more runs are
given that code. In one the code lane finds nothing, so the one
finding is thrown out. The other stops at an editor that never answers, before
the review is written. The third run's code is what a workspace review hands
over for a Paper Scaffold workspace, so the snapshot of it shows what the
engine takes from one and what it leaves out. Round one and the third run are
written inside that workspace, as ``paper-workbench review . reviews/NAME``
writes them, so the snapshot also shows that no run's files are copied in as
code. Three more runs show what went wrong in a run that still finished: a
code check that never answered, a reader that never answered, so the
manuscript was sealed as the converter read it, and a seat that spent past its
token ceiling after it reported. One more is the starter's stop: a seat spends
past the run's token ceiling before it reports, so the run blocks before the
editor with its findings only in the ledger. test_ledger_import.py builds its runs here
too: rounds of a draft's PDF, an author's draft check with no editor, and a
review whose reviewers never answered.
"""
import http.client
import json
import os
import tempfile
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from peerreviewagents import NO_ANSWER, ReviewRefused, read_manuscript, read_run, scripted_review
from peerreviewagents.names import TOKEN_FIELDS
from peerreviewagents.workspace import digest

import manuscripts
from paper_workspace.run_view import RunError, locate, run_review
from paper_workspace.server import make_server
from paper_workspace.workspace_review import engine_argv
from reader_fixture import pdf_bytes
from test_run_view import (CODE_EVIDENCE, PIPELINE, SUMMARY, SUMMARY_EVIDENCE, THROWN_OUT_NOTE, finding, issue,
                           issues_document, run_quietly)
from test_workspace_review import make_workspace

FIRST =['Knockdown lowered VPS35 in twelve samples drawn from one donor.',
         'The authors conclude that VPS35 controls retromer assembly in all tissues.',
         'Each assay was repeated three times and the mean is reported in the figure.']
SECOND = ['Knockdown lowered VPS35 in twelve samples drawn from four donors.', FIRST[1], FIRST[2]]
CODE_TEXTS = ['Peptides were filtered at a false discovery rate of one percent.', FIRST[2]]
# A table too large for the engine to fetch whole, so it stores only its first lines.
SCORES = 'peptide,score\n' + ''.join(f'P{n},{n}\n' for n in range(30000))
MEAN = {'title': 'The mean hides the spread of three repeats', 'quote': 'the mean is reported in the figure',
        'comment': 'With three repeats the mean says little. Show each repeat.',
        'assumed_method': 'The figure plots the mean of the three repeats.'}
CREDENTIALS = ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'OPENAI_API_KEY')
# The token ceiling one seat spends past: per seat in one round, and per run in the round the starter stops.
CEILING_TOKENS = 5000
# What the round the starter stops files before its ceiling, in the order the ledger holds it.
STOPPED_QUOTES = ['twelve samples drawn from one donor', 'controls retromer assembly in all tissues']


@contextmanager
def offline():
    """No credentials in the environment while a round is built, restored after."""
    environment = {key: value for key, value in os.environ.items() if key not in CREDENTIALS}
    with mock.patch.dict(os.environ, environment, clear=True):
        yield


def grouped(name, rank, members, **extra):
    return {'name': name, 'severity': 'major', 'category': 'claims-and-conclusions', 'rank': rank,
            'members': members, 'statement': f'{name} is stated more strongly than the data carry.', **extra}


def refused(tool, *arguments, **named):
    """Whether the engine refuses one call of a slot's ``tool``. A script catches the refusal, as a model reads it."""
    try:
        tool(*arguments, **named)
    except ReviewRefused:
        return True
    return False


def sealed(root, texts, source):
    """A manuscript of ``texts`` sealed under ``root``, and the PDF beside it, whose bytes are ``source``.

    The engine reads the PDF it is handed, and plans no Read stage for a
    manuscript already sealed from it, so the PDF's hash is the source the
    manuscript records.
    """
    data = source.encode() if isinstance(source, str) else source
    manuscripts.build(root / 'manuscript', texts, source_sha256=digest(data))
    (root / 'manuscript.pdf').write_bytes(data)
    return root / 'manuscript.pdf'


def reported(slot, text, **named):
    """``slot``'s report on the model the engine planned for it, which the report names as the one it ran on."""
    assert slot.submit_report(text, model=slot.model, **named)['closed'], slot


def ran(review, status):
    """Check the scripted ``review`` ended in ``status`` and planned no reader for its sealed manuscript."""
    assert (review.status, 'reader' in review.ran) == (status, False), (review.status, review.blocked_reason,
                                                                         review.ran)


def one_round(root, texts, source, quotes, issues):
    """One reviewers-only round: core-1 raises a finding per quote, core-2 finds none, the editor groups them."""
    uids = []

    def first(slot):
        slot.whole_paper()
        for quote in quotes:
            stored = slot.submit_finding(title='Claim', quote=quote, comment='The sentence asserts more than it shows.',
                                         severity='major')
            assert stored.get('stored'), stored
            uids.append(stored['finding_uid'])
        reported(slot, 'Checked.')

    def editor(slot):
        slot.whole_paper()
        slot.submit_issues(issues(uids))
        answer = slot.submit_editor(summary='One question of scope.', significance='Modest.',
                                    strength_of_evidence='Weak.', verdict_reasoning='The scope is overstated.')
        assert answer.get('accepted'), answer
        reported(slot, 'Grouped.')

    scripts = {'core-1': first, 'core-2': lambda slot: reported(slot, 'Nothing.', none_found=True), 'editor': editor}
    ran(scripted_review(sealed(root, texts, source), root, scripts, arm='reviewers-only', reviewers=2), 'complete')


def code_round(root, code, lane_finds=True, written=True):
    """A run given ``code``, with the code check the engine plans on a run with code.

    The code lane fetches a small data file whole and a large one in part, is
    refused the built PDF, which is binary, and files one code-checked finding,
    or none when ``lane_finds`` is false. The numbers lane files a finding that
    names the method it assumed, and the code check throws it out with the data
    line that says otherwise. The run is a draft-check, whose arm runs
    specialists and no editor, so the server writes one issue per finding it
    keeps. When ``written`` is false it is a full-two-track review whose one
    core reviewer finds nothing and whose editor never answers, so the run
    stops before the recorder writes the review.
    """
    (code / 'analysis').mkdir(parents=True, exist_ok=True)
    (code / CODE_EVIDENCE['path']).write_text(PIPELINE)
    (code / SUMMARY_EVIDENCE['path']).write_text(SUMMARY)
    (code / 'analysis' / 'scores.csv').write_text(SCORES)
    thrown = []

    def lane(slot):
        slot.whole_paper()
        slot.read_code(CODE_EVIDENCE['path'])
        whole = slot.read_code(SUMMARY_EVIDENCE['path'])
        assert (whole.get('data'), whole.get('partial')) == (True, False), whole
        part = slot.read_code('analysis/scores.csv')
        assert (part.get('data'), part.get('partial')) == (True, True), part
        assert refused(slot.read_code, 'paper.pdf')
        if not lane_finds:
            return reported(slot, 'Nothing.', none_found=True)
        stored = slot.submit_finding(
            title='The threshold in the methods is not the one in the code',
            quote='a false discovery rate of one percent', severity='major',
            comment='The methods say one percent and the pipeline filters at five.',
            code_path=CODE_EVIDENCE['path'], code_start_line=CODE_EVIDENCE['start_line'],
            code_end_line=CODE_EVIDENCE['end_line'], code_quote=CODE_EVIDENCE['text'])
        assert stored.get('stored'), stored
        reported(slot, 'Checked.')

    def numbers(slot):
        slot.whole_paper()
        stored = slot.submit_finding(severity='major', **MEAN)
        assert stored.get('stored'), stored
        thrown.append(stored['finding_uid'])
        reported(slot, 'One.')

    def check(slot):
        # The code check reads no paper. It is handed the findings that rest on a method and reads the code.
        claims = slot.method_claims()
        assert [row['finding_uid'] for row in claims['claims']] == thrown, claims
        verdict = slot.submit_code_check(thrown[0], 'contradicted', code_path=SUMMARY_EVIDENCE['path'],
                                         code_start_line=SUMMARY_EVIDENCE['start_line'],
                                         code_end_line=SUMMARY_EVIDENCE['end_line'],
                                         code_quote=SUMMARY_EVIDENCE['text'], note=THROWN_OUT_NOTE)
        assert 'request_rejected' not in verdict, verdict
        reported(slot, 'Checked one.')

    scripts = {'spec-code': lane, 'spec-numbers': numbers, 'code-check': check}
    plan = {'arm': 'draft-check', 'reviewers': 0}
    if not written:
        scripts.update(core=lambda slot: reported(slot, 'Nothing.', none_found=True), editor=lambda slot: NO_ANSWER)
        plan = {'arm': 'full-two-track', 'reviewers': 1}
    review = scripted_review(sealed(root, CODE_TEXTS, 'source-code'), root, scripts, tracks=['numbers'],
                             code=str(code), **plan)
    ran(review, 'complete' if lane_finds and written else 'complete-without-findings' if written else 'blocked')


def check_round(root, texts, source, quote):
    """A finished draft-check of ``texts`` with the numbers specialist alone and no code.

    The specialist files one finding on ``quote``. The arm runs no editor, so
    the server writes one issue for it and the run is not publishable.
    """
    def numbers(slot):
        slot.whole_paper()
        stored = slot.submit_finding(title=MEAN['title'], quote=quote, comment=MEAN['comment'], severity='major')
        assert stored.get('stored'), stored
        reported(slot, 'One.')

    ran(scripted_review(sealed(root, texts, source), root, {'spec-numbers': numbers}, arm='draft-check',
                        reviewers=0, tracks=['numbers']), 'complete')


def silent_round(root, texts, source):
    """A reviewers-only review of ``texts`` whose reviewers never answer, so it stops before any finding."""
    ran(scripted_review(sealed(root, texts, source), root, {'core': lambda slot: NO_ANSWER}, arm='reviewers-only',
                        reviewers=2), 'blocked')


def numbers_lane(slot):
    """The numbers specialist filing the one finding of MEAN, which names the method it assumed."""
    slot.whole_paper()
    stored = slot.submit_finding(severity='major', **MEAN)
    assert stored.get('stored'), stored
    reported(slot, 'One.')


def silent_code_round(root, code):
    """A draft-check given ``code`` whose code check never answers, so the one claim it was handed is not checked.

    The code lane finds nothing, and the numbers lane files the finding of
    MEAN, which rests on a method, so the code check is handed it.
    """
    (code / 'analysis').mkdir(parents=True, exist_ok=True)
    (code / CODE_EVIDENCE['path']).write_text(PIPELINE)
    scripts = {'spec-code': lambda slot: (slot.whole_paper(), reported(slot, 'Nothing.', none_found=True)),
               'spec-numbers': numbers_lane, 'code-check': lambda slot: NO_ANSWER}
    ran(scripted_review(sealed(root, CODE_TEXTS, 'source-code'), root, scripts, arm='draft-check', reviewers=0,
                        tracks=['numbers'], code=str(code)), 'complete')


def unread_round(root):
    """A draft-check of a PDF no manuscript was sealed from, whose reader never answers.

    The engine seals the manuscript as converted and the numbers lane reviews
    the converter's text.
    """
    root.mkdir(parents=True)
    pdf = root / 'manuscript.pdf'
    pdf.write_bytes(pdf_bytes([[(11, FIRST[2])]]))
    review = scripted_review(pdf, root, {'reader': lambda slot: NO_ANSWER, 'spec-numbers': numbers_lane},
                             arm='draft-check', reviewers=0, tracks=['numbers'])
    assert (review.status, review.summary['read']['reader_failed']) == ('complete', True), review.summary


def ceiling_round(root):
    """A reviewers-only round whose core-2 reports and then spends past its token ceiling of 5000.

    Each seat the round has no script for answers with the engine's default.
    """
    def over(slot):
        slot.whole_paper()
        reported(slot, 'Nothing.', none_found=True)
        slot.spend(slot.task.token_ceiling + 1)

    ran(scripted_review(sealed(root, FIRST, 'source-ceiling'), root, {'core-2': over}, arm='reviewers-only',
                        reviewers=2, per_agent_tokens=CEILING_TOKENS), 'complete')


def stopped_round(root):
    """A reviewers-only round the starter stops at its per-run token ceiling of 5000, before the editor.

    core-1 files a finding for each of STOPPED_QUOTES and spends past the
    ceiling before it reports, so its stage is missing and the panel starts
    nothing again. core-2 finds nothing. The findings are in the ledger and
    there are no issues.
    """
    def greedy(slot):
        slot.whole_paper()
        for quote in STOPPED_QUOTES:
            assert slot.submit_finding(title='Claim', quote=quote, comment=f'Say what carries "{quote}".',
                                       severity='major').get('stored')
        slot.spend(8 * CEILING_TOKENS)

    scripts = {'core-1': greedy, 'core-2': lambda slot: (slot.whole_paper(), reported(slot, 'Nothing.',
                                                                                        none_found=True))}
    ran(scripted_review(sealed(root, FIRST, 'source-stopped'), root, scripts, arm='reviewers-only', reviewers=2,
                        per_run_tokens=CEILING_TOKENS), 'blocked')


@contextmanager
def served(root):
    """The viewer's server on one run folder, and a function that sends it a request."""
    server = make_server(root, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(path, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
        headers = {'Host': f'127.0.0.1:{server.server_port}'}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        try:
            connection.request('POST' if body is not None else 'GET', path,
                               body=json.dumps(body).encode() if body is not None else None, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    try:
        yield request
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class EngineRoundsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name).resolve()
        cls.workspace = make_workspace(cls.root / 'workspace')
        cls.first, cls.second = cls.workspace / 'reviews' / 'first', cls.root / 'second'
        cls.coded = cls.workspace / 'reviews' / 'coded'
        cls.disproved, cls.unwritten = cls.root / 'disproved', cls.root / 'unwritten'
        cls.silent_code, cls.unread, cls.ceiling = cls.root / 'silent-code', cls.root / 'unread', cls.root / 'ceiling'
        cls.stopped = cls.root / 'stopped'
        with offline():
            one_round(cls.first, FIRST, 'source-1', [
                'twelve samples drawn from one donor', 'controls retromer assembly in all tissues',
                'repeated three times'],
                lambda uids: [grouped('The sample', 1, [uids[0]]), grouped('The scope', 2, [uids[1]]),
                              grouped('The repeats', 3, [uids[2]])])
            # Round two is a fresh panel on the revised draft. It reads nothing of round one.
            one_round(cls.second, SECOND, 'source-2', [
                'controls retromer assembly in all tissues', 'The authors conclude'],
                lambda uids: [grouped('The scope', 1, [uids[0]]), grouped('The attribution', 2, [uids[1]])])
            # The code is what `paper-workbench review WORKSPACE RUN` hands the engine, with RUN inside it.
            argv, _ = engine_argv([str(cls.workspace), str(cls.coded), '--arm', 'draft-check'])
            code_round(cls.coded, Path(argv[argv.index('--code') + 1]))
            # The same run with the code lane finding nothing, and the same run stopped before its review.
            code_round(cls.disproved, cls.root / 'code', lane_finds=False)
            code_round(cls.unwritten, cls.root / 'code', written=False)
            silent_code_round(cls.silent_code, cls.root / 'silent-code-source')
            unread_round(cls.unread)
            ceiling_round(cls.ceiling)
            stopped_round(cls.stopped)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def view(self, root):
        return run_review(root / 'review', read_manuscript(root / 'manuscript'))

    def test_the_fixture_has_the_keys_the_engine_writes(self):
        row = json.loads((self.first / 'review' / 'findings.jsonl').read_text().splitlines()[0])
        self.assertEqual(sorted(finding('aa11', 'Knockdown')), sorted(row))
        written = json.loads((self.second / 'review' / 'issues.json').read_text())['issues']
        self.assertEqual({tuple(sorted(row)) for row in written}, {tuple(sorted(issue(1, 'x', 'major', 'y', [])))})
        # The engine writes every top-level key on every run, code_check as None on a run given no code.
        for root in (self.first, self.second, self.coded):
            document = json.loads((root / 'review' / 'issues.json').read_text())
            self.assertEqual(sorted(issues_document()), sorted(document))
        self.assertIsNone(json.loads((self.first / 'review' / 'issues.json').read_text())['code_check'])

    def test_every_agent_row_carries_the_engines_ending_and_token_fields(self):
        run = self.view(self.first)['run']
        agents = {row['slot']: row for row in run['agents']}
        # The engine asks no model of the recorder. Its one stream row is the run itself, and the viewer reads
        # the engine's own word for it and adds no guess of its own.
        recorder = agents.pop('recorder')
        self.assertEqual((recorder['ending'], recorder['assigned_model'], recorder['model']),
                         ('in process', None, None))
        self.assertEqual(recorder['detail'], 'the run itself: every recorder tool was called in this process, with '
                                             'no model')
        self.assertNotIn('in_process', recorder)
        self.assertEqual({field: recorder[field] for field in TOKEN_FIELDS}, dict.fromkeys(TOKEN_FIELDS, 0))
        # Every other seat answered through its script, and the engine records the spend it books for one.
        self.assertEqual(sorted(agents), ['core-1', 'core-2', 'editor'])
        for slot, row in agents.items():
            self.assertEqual((row['state'], row['ending']), ('done', 'answered'), slot)
            self.assertTrue(row['assigned_model'], slot)
            self.assertEqual({field: row[field] for field in TOKEN_FIELDS},
                             {'tokens_cumulative': 1000, 'tokens_input_uncached': 200, 'tokens_cache_write': 200,
                              'tokens_cache_read': 500, 'tokens_output': 100, 'tokens_peak_context': 1000}, slot)
        # A slot with no model asked is not one whose model is unverified.
        self.assertEqual((run['models_unverified'], run['publishable']), ([], True))

    def test_a_seat_that_spent_past_its_ceiling_says_so_in_the_engines_words(self):
        run = self.view(self.ceiling)['run']
        agents = {row['slot']: row for row in run['agents']}
        over = agents['core-2']
        self.assertEqual((over['state'], over['ending'], over['detail']),
                         ('over the token ceiling', 'over the token ceiling',
                          f'the seat spent {CEILING_TOKENS + 1} tokens against a ceiling of {CEILING_TOKENS}'))
        self.assertEqual((over['tokens'], over['tokens_cumulative']), (CEILING_TOKENS + 1, CEILING_TOKENS + 1))
        # It reported before it spent, so its report stands, and the other seats answered as usual.
        self.assertEqual((over['none_found'], agents['core-1']['ending'], agents['editor']['ending']),
                         (True, 'answered', 'answered'))
        self.assertEqual((run['status'], run['publishable']), ('complete', True))

    def test_round_one_is_read_as_three_issues(self):
        review = self.view(self.first)
        self.assertEqual([(f['id'], f['group'], f['decidable'], len(f['members'])) for f in review['findings']],
                         [('i01', 'required', True, 1), ('i02', 'required', True, 1), ('i03', 'required', True, 1)])
        # The run panel says nothing about an earlier round.
        self.assertNotIn('prior_round', review['run'])

    def test_round_two_is_a_fresh_panel_with_ids_of_its_own(self):
        review = self.view(self.second)
        self.assertEqual([(f['id'], f['group'], f['title'], f['decidable']) for f in review['findings']],
                         [('i01', 'required', 'The scope', True), ('i02', 'required', 'The attribution', True)])
        # Round one's issues are not shown here, and no card is grouped as closed.
        self.assertEqual({f['group'] for f in review['findings']}, {'required'})
        self.assertNotIn('prior_round', review['run'])

    def test_decisions_stay_with_the_run_folder_they_were_made_in(self):
        with served(self.first) as request:
            status, decisions = request('/api/decisions', {'review_id': 'run', 'annotation_id': 'i02',
                'status': 'noted', 'revision': 0, 'author_comment': 'Narrowed the claim to HeLa cells.'})
            self.assertEqual((status, decisions['items']), (200, {'i02': 'noted'}))
        # Round two opens with no decisions, though it has an issue i02 too. Its ids are its own.
        with served(self.second) as request:
            self.assertEqual(request('/api/decisions?review=run')[1]['items'], {})
            status, decisions = request('/api/decisions', {'review_id': 'run', 'annotation_id': 'i02',
                'status': 'noted', 'revision': 0})
            self.assertEqual((status, decisions['items']), (200, {'i02': 'noted'}))
        self.assertTrue((self.first / 'manuscript' / 'decisions' / 'run.json').is_file())

    def test_the_code_fixture_has_the_keys_the_engine_writes(self):
        # The orchestrator runs the lanes in its own order, so the code lane's row is found by its slot.
        rows = [json.loads(line) for line in (self.coded / 'review' / 'findings.jsonl').read_text().splitlines()]
        [row] = [row for row in rows if row['slot'] == 'spec-code']
        self.assertEqual(row['basis'], 'code-checked')
        self.assertEqual(sorted(finding('aa11', 'x', basis='code-checked', code_evidence=CODE_EVIDENCE)), sorted(row))
        self.assertEqual(row['code_evidence'], CODE_EVIDENCE)
        # A finding with no code carries no code_evidence key at all.
        plain = json.loads((self.first / 'review' / 'findings.jsonl').read_text().splitlines()[0])
        self.assertNotIn('code_evidence', plain)

    def test_a_code_checked_finding_shows_its_file_and_lines(self):
        review = self.view(self.coded)
        self.assertEqual([(f['group'], len(f['members'])) for f in review['findings']], [('required', 1)])
        member = review['findings'][0]['members'][0]
        self.assertEqual((member['slot'], member['basis'], member['code_evidence']),
                         ('spec-code', 'code-checked', CODE_EVIDENCE))
        self.assertTrue(member['basis_reason'].startswith(f"The code quoted is what {CODE_EVIDENCE['path']} holds"))
        self.assertIsNone(member['code_data'])
        code = review['run']['code']
        self.assertEqual((code['reviewed'], code['kind'], code['opened']), (True, 'folder', 3))
        self.assertEqual(code['files_opened'][0], CODE_EVIDENCE['path'])
        self.assertNotIn('manifest', code)

    def test_the_run_panel_says_which_data_files_were_fetched_and_which_in_part(self):
        code = self.view(self.coded)['run']['code']
        rows = {row['path']: row for row in code['data']}
        self.assertEqual(sorted(rows), ['analysis/scores.csv', SUMMARY_EVIDENCE['path']])
        whole, part = rows[SUMMARY_EVIDENCE['path']], rows['analysis/scores.csv']
        self.assertEqual((whole['partial'], whole['bytes'], whole['stored_bytes']), (False, len(SUMMARY), len(SUMMARY)))
        self.assertEqual((part['partial'], part['bytes']), (True, len(SCORES)))
        self.assertLess(part['stored_bytes'], part['bytes'])
        self.assertEqual(sorted(whole), ['bytes', 'changed', 'partial', 'path', 'stored_bytes'])
        # The built PDF is listed as data and refused, because it cannot be read as text.
        self.assertEqual((code['data_fetched'], code['data_partial'], code['data_refused']), (2, 1, 1))
        self.assertEqual(code['data_bytes'], whole['stored_bytes'] + part['stored_bytes'])
        self.assertEqual(code['source_cut'], 0)
        self.assertGreaterEqual(code['data_listed'], 3)

    def test_a_finding_the_code_check_threw_out_is_no_card_and_shows_the_code_that_disproved_it(self):
        check = json.loads((self.coded / 'review' / 'issues.json').read_text())['code_check']
        self.assertEqual(check['counts'], {'confirmed': 0, 'contradicted': 1, 'not-shown': 0})
        self.assertEqual(check['checks'][0]['code_evidence'], SUMMARY_EVIDENCE)
        review = self.view(self.coded)
        titles = [member['title'] for card in review['findings'] for member in card['members']]
        self.assertNotIn(MEAN['title'], titles)
        self.assertEqual(len(review['findings']), 1)
        shown = review['run']['code_check']
        self.assertEqual((shown['checked'], shown['over_cap'], shown['counts']), (1, 0, check['counts']))
        [item] = shown['thrown_out']
        self.assertEqual({key: item[key] for key in MEAN}, MEAN)
        self.assertEqual((item['slot'], item['track'], item['severity'], item['note']),
                         ('spec-numbers', 'numbers', 'major', THROWN_OUT_NOTE))
        self.assertEqual(item['code_evidence'], SUMMARY_EVIDENCE)
        self.assertEqual(item['code_data'], {'path': SUMMARY_EVIDENCE['path'], 'bytes': len(SUMMARY),
                                             'stored_bytes': len(SUMMARY), 'partial': False, 'changed': ''})
        # It is placed on the manuscript as a member is, by its ledger row's span.
        self.assertEqual((item['placement'], item['anchor_text'], item['id']),
                         ('anchored', MEAN['quote'], item['finding_uid']))
        # The engine's own reading still has it on the ledger, and the viewer counts it nowhere as a finding of an issue.
        self.assertIn(item['finding_uid'], [row['finding_uid'] for row in read_run(self.coded)['findings']])
        self.assertEqual(review['run']['findings_source'], 'issues')

    def test_a_run_whose_only_finding_the_code_check_threw_out_is_a_finished_review_with_nothing_open(self):
        run = read_run(self.disproved)
        self.assertEqual((run['status'], run['publishable'], run['findings_source']),
                         ('complete-without-findings', True, 'issues'))
        # The guard held nothing, so the code check is what left the review empty.
        self.assertEqual((run['counts']['quarantined'], run['code_check']['counts']['contradicted']), (0, 1))
        review = self.view(self.disproved)
        self.assertEqual(review['findings'], [])
        shown = review['run']
        self.assertEqual((shown['status'], shown['publishable'], shown['findings_source'],
                          shown['quarantined_findings_count']), ('complete-without-findings', True, 'issues', 0))
        [item] = shown['code_check']['thrown_out']
        self.assertEqual((item['title'], item['code_evidence'], item['note']),
                         (MEAN['title'], SUMMARY_EVIDENCE, THROWN_OUT_NOTE))

    def test_a_run_stopped_before_its_review_shows_what_the_code_check_threw_out(self):
        # read_run reads the check's own file on a run that has no issues.json yet.
        self.assertFalse((self.unwritten / 'review' / 'issues.json').exists())
        review = self.view(self.unwritten)
        self.assertEqual(review['run']['findings_source'], 'ledger')
        titles = [member['title'] for card in review['findings'] for member in card['members']]
        self.assertEqual(len(titles), 1)
        self.assertNotIn(MEAN['title'], titles)
        shown = review['run']['code_check']
        self.assertEqual((shown['cap'], shown['checked'], shown['counts']['contradicted']),
                         (read_run(self.unwritten)['code_check']['cap'], 1, 1))
        self.assertIsInstance(shown['cap'], int)
        [item] = shown['thrown_out']
        self.assertEqual((item['title'], item['code_evidence'], item['placement']),
                         (MEAN['title'], SUMMARY_EVIDENCE, 'anchored'))

    def test_a_code_check_that_never_answered_is_shown_incomplete_and_its_claim_stands(self):
        engine = read_run(self.silent_code)['code_check']
        self.assertTrue(engine['incomplete_reason'].startswith('1 method claim(s) were not read against the code'),
                        engine)
        review = self.view(self.silent_code)
        # The lane filed no report, which the engine says as `silent`, not only as nothing checked.
        self.assertEqual(review['run']['code_check'], {
            'cap': engine['cap'], 'silent': True, 'checked': 0, 'not_checked': 1, 'over_cap': 0, 'incomplete': True,
            'incomplete_reason': engine['incomplete_reason'],
            'counts': {'confirmed': 0, 'contradicted': 0, 'not-shown': 0}, 'thrown_out': []})
        # The claim the check never read is a card as its reviewer filed it.
        self.assertEqual([card['title'] for card in review['findings']], [MEAN['title']])
        # A check that answered every claim it was handed is neither silent nor incomplete.
        whole = self.view(self.coded)['run']['code_check']
        self.assertEqual((whole['silent'], whole['incomplete'], whole['not_checked'], whole['incomplete_reason']),
                         (False, False, 0, None))

    def test_a_manuscript_whose_reader_failed_says_so_and_one_never_read_by_design_does_not(self):
        # The viewer shows the engine's record of the Read stage as the folder holds it.
        engine = read_run(self.unread)['read']
        self.assertEqual(self.view(self.unread)['run']['read'], engine)
        self.assertEqual((engine['reader_failed'], engine['sealed']), (True, True))
        self.assertTrue(engine['reason'])
        # A manuscript sealed before the run needs no reader, so the run planned none and has no record of one.
        self.assertIsNone(self.view(self.silent_code)['run']['read'])
        self.assertIsNone(self.view(self.first)['run']['read'])

    def test_a_run_stopped_at_its_token_ceiling_opens_with_what_it_recorded(self):
        engine = read_run(self.stopped)
        self.assertEqual(locate(self.stopped), (self.stopped / 'manuscript', self.stopped / 'review'))
        review = self.view(self.stopped)
        self.assertEqual([(f['group'], f['comment']) for f in review['findings']],
                         [('ledger', f'Say what carries "{quote}".') for quote in STOPPED_QUOTES])
        run = review['run']
        self.assertEqual((run['status'], run['cause'], run['findings_source'], run['missing_stages']),
                         ('blocked', engine['cause'], 'ledger', ['core-1', 'editor']))
        # The cause names the seat's own ending and the stop after it, so the stage is missing because the run ran out.
        self.assertIn('core-1 (over the token ceiling, and nothing was started again)', run['cause'])
        self.assertIn(f'this run reached its token ceiling of {CEILING_TOKENS:,}', run['cause'])
        self.assertEqual((run['tokens_total'], run['problems']), (engine['runtime']['tokens_total'], []))
        self.assertEqual(review['summary'], f'The run stopped before the editor wrote its issues: {engine["cause"]}')
        with served(self.stopped) as request:
            status, served_review = request('/api/review?review=run')
        self.assertEqual((status, served_review['run']['status'], served_review['run']['cause']),
                         (200, 'blocked', engine['cause']))
        self.assertEqual([f['id'] for f in served_review['findings']], [f['id'] for f in review['findings']])

    def test_a_stopped_runs_findings_pin_the_version_its_manuscript_names(self):
        # A manuscript of the same paper and source whose first sentence reads otherwise is another version.
        other = self.root / 'other-version'
        manuscripts.build(other, SECOND, source_sha256=digest(b'source-stopped'))
        with self.assertRaisesRegex(RunError, 'different manuscript version'):
            run_review(self.stopped / 'review', read_manuscript(other))

    def test_report_renders_what_the_stopped_run_recorded(self):
        status, output, _ = run_quietly(['report', str(self.stopped)])
        self.assertEqual(status, 0)
        summary = json.loads(output)
        self.assertEqual((summary['status'], summary['cause']), ('blocked', read_run(self.stopped)['cause']))
        self.assertTrue((self.stopped / 'review' / 'REVIEW.md').is_file())

    def test_a_run_given_no_code_has_no_code_check(self):
        review = self.view(self.first)
        self.assertIsNone(review['run']['code_check'])
        self.assertEqual(review['run']['code']['data'], [])

    def test_a_workspace_review_hands_over_its_code_and_the_engine_leaves_out_its_data(self):
        code = read_run(self.coded)['code']
        self.assertEqual((code['reviewed'], code['kind'], code['source'], code['commit']),
                         (True, 'folder', str(self.workspace), ''))
        copied = [row['path'] for row in code['manifest']['files']]
        skipped = {row['path']: row['reason'] for row in code['manifest']['skipped']}
        self.assertIn(CODE_EVIDENCE['path'], copied)
        # Data, results and figures are folders the engine never walks into, and .env may hold secrets.
        for folder in ('data', 'results', 'figures'):
            self.assertTrue(skipped[folder].startswith('not looked at'), skipped)
            self.assertFalse([path for path in copied if path.startswith(folder + '/')], copied)
        self.assertEqual(skipped['.env'], 'may hold secrets')
        # The built PDF and the statistics file are data, listed with their size and never copied up front.
        data = {row['path']: row for row in code['manifest']['data']}
        self.assertEqual((data['paper.pdf']['readable'], data['paper.pdf']['fetched']), (False, False))
        self.assertEqual(data['stats.json']['fetched'], False)
        self.assertNotIn('stats.json', copied)
        self.assertEqual(code['data_listed'], len(data))
        # The run is written inside the code, beside round one's run, and no file of either is copied in.
        self.assertEqual(skipped['reviews/coded'], 'not looked at: the run folder this review is being written into')
        self.assertEqual(skipped['reviews/first'], 'not looked at: a PeerReviewAgents run folder')
        self.assertFalse([path for path in copied if path.startswith('reviews/')], copied)
        self.assertEqual(code['files_skipped'], len(skipped))

    def test_a_run_given_no_code_says_so(self):
        code = self.view(self.first)['run']['code']
        self.assertIs(code['reviewed'], False)
        self.assertEqual(code['files_opened'], [])
        self.assertEqual(self.view(self.first)['findings'][0]['members'][0].get('code_evidence'), None)


if __name__ == '__main__':
    unittest.main()
