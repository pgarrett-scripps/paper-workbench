"""Two review rounds built by the engine's scripted review, read by the viewer.

``scripted_review`` opens a real review on a sealed manuscript with every slot
the arm plans claimed, and this file acts as each slot in turn through that
slot's own tools, so no model is started and nothing reaches the network. This
file builds two rounds that way, each a fresh panel on its own draft that knows
nothing of the other, and a third run given analysis code whose code lane
fetches two data files and files one code-checked finding, and whose code check
throws out the numbers lane's finding, and drives the viewer from them, so the
hand-written fixture in test_run_view.py is checked against what the engine
writes. Two more runs on that code have the code lane find nothing, so the one
finding is thrown out, and stop before the review is written. The code check is
the one slot ``scripted_review`` does not claim, so it alone acts through the
engine's server, which is the one private import here. The third run's code is
what a workspace review hands over for a Paper Scaffold workspace, so the
snapshot of it shows what the engine takes from one and what it leaves out.
Round one and the third run are written inside that workspace, as
``paper-workbench review . reviews/NAME`` writes them, so the snapshot also
shows that no run's files are copied in as code. test_ledger_import.py builds
its runs here too: rounds of a draft's PDF, an author's draft check with no
editor, and a review the engine opened and that stopped before any slot
reported.
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

from peerreviewagents import ReviewRefused, read_manuscript, read_run, scripted_review
# The code check's slot alone, which scripted_review does not claim.
from peerreviewagents.plugin import server as engine
from peerreviewagents.workspace import digest

import manuscripts
from paper_workspace.run_view import run_review
from paper_workspace.server import make_server
from paper_workspace.workspace_review import engine_argv
from test_run_view import (CODE_EVIDENCE, PIPELINE, SUMMARY, SUMMARY_EVIDENCE, THROWN_OUT_NOTE, finding, issue,
                           issues_document)
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


@contextmanager
def offline():
    """No credentials in the environment while a round is built, restored after."""
    environment = {key: value for key, value in os.environ.items() if key not in CREDENTIALS}
    with mock.patch.dict(os.environ, environment, clear=True):
        yield


def grouped(name, rank, members, **extra):
    return {'name': name, 'severity': 'major', 'category': 'claims-and-conclusions', 'rank': rank,
            'members': members, 'statement': f'{name} is stated more strongly than the data carry.', **extra}


def models(review):
    """The model the engine planned for each slot, which the slot's report names as the one it ran on."""
    return {row['slot']: row['model'] for row in review.opened['models']}


def refused(tool, *arguments, **named):
    """Whether the engine refuses one call of a scripted review's ``tool``."""
    try:
        tool(*arguments, **named)
    except ReviewRefused:
        return True
    return False


def one_round(root, texts, source, quotes, issues):
    """One reviewers-only round: core-1 raises a finding per quote, core-2 finds none, the editor groups them."""
    manuscripts.build(root / 'manuscript', texts, source_sha256=digest(source))
    with scripted_review(root / 'manuscript.pdf', root, arm='reviewers-only', reviewers=2) as review:
        # The manuscript is sealed before ingest, so the engine plans no Read stage.
        assert review.opened['reader'] is None and 'reader' not in review.slots, review.opened
        model = models(review)
        uids = []
        for quote in quotes:
            stored = review.submit_finding(slot='core-1', title='Claim', quote=quote,
                                           comment='The sentence asserts more than it shows.', severity='major')
            assert stored.get('stored'), stored
            uids.append(stored['finding_uid'])
        assert review.submit_report('Checked.', slot='core-1', model=model['core-1'])['closed']
        assert review.submit_report('Nothing.', slot='core-2', none_found=True, model=model['core-2'])['closed']
        review.submit_issues(issues(uids))
        answer = review.submit_editor(summary='One question of scope.', significance='Modest.',
                                      strength_of_evidence='Weak.', verdict_reasoning='The scope is overstated.')
        assert answer.get('accepted'), answer
        assert review.submit_report('Grouped.', slot='editor', model=model['editor'])['closed']
        review.write()


def code_round(root, code, lane_finds=True, written=True):
    """A draft-check run given ``code``, with the code check the engine plans on a run with code.

    The code lane fetches a small data file whole and a large one in part, is
    refused the built PDF, which is binary, and files one code-checked finding,
    or none when ``lane_finds`` is false. The numbers lane files a finding that
    names the method it assumed, and the code check throws it out with the data
    line that says otherwise. The arm runs specialists and no editor, so the
    server writes one issue per finding it keeps. When ``written`` is false the
    run stops before the recorder writes the review. The manuscript is sealed
    before ingest, so the engine plans no reader.
    """
    (code / 'analysis').mkdir(parents=True, exist_ok=True)
    (code / CODE_EVIDENCE['path']).write_text(PIPELINE)
    (code / SUMMARY_EVIDENCE['path']).write_text(SUMMARY)
    (code / 'analysis' / 'scores.csv').write_text(SCORES)
    manuscripts.build(root / 'manuscript', CODE_TEXTS, source_sha256=digest('source-code'))
    with scripted_review(root / 'manuscript.pdf', root, arm='draft-check', reviewers=0, tracks=['numbers'],
                         code=str(code)) as review:
        assert review.opened['reader'] is None and 'reader' not in review.slots, review.opened
        model = models(review)
        review.read_code(CODE_EVIDENCE['path'])
        whole = review.read_code(SUMMARY_EVIDENCE['path'])
        assert (whole.get('data'), whole.get('partial')) == (True, False), whole
        part = review.read_code('analysis/scores.csv')
        assert (part.get('data'), part.get('partial')) == (True, True), part
        assert refused(review.read_code, 'paper.pdf')
        if lane_finds:
            stored = review.submit_finding(
                slot='spec-code', title='The threshold in the methods is not the one in the code',
                quote='a false discovery rate of one percent', severity='major',
                comment='The methods say one percent and the pipeline filters at five.',
                code_path=CODE_EVIDENCE['path'], code_start_line=CODE_EVIDENCE['start_line'],
                code_end_line=CODE_EVIDENCE['end_line'], code_quote=CODE_EVIDENCE['text'])
            assert stored.get('stored'), stored
            assert review.submit_report('Checked.', slot='spec-code', model=model['spec-code'])['closed']
        else:
            assert review.submit_report('Nothing.', slot='spec-code', none_found=True,
                                        model=model['spec-code'])['closed']
        stored = review.submit_finding(slot='spec-numbers', severity='major', **MEAN)
        assert stored.get('stored'), stored
        assert review.submit_report('One.', slot='spec-numbers', model=model['spec-numbers'])['closed']
        # The code check reads no paper. It is handed the findings that rest on a method and reads the code.
        # scripted_review does not claim its slot, so it acts through the engine's server.
        codes = {row['slot']: row['claim_code'] for row in review.opened['claim_codes']}
        check = engine.claim_agent('code-check', codes['code-check'])['agent_token']
        claims = engine.method_claims(check)
        assert [row['finding_uid'] for row in claims['claims']] == [stored['finding_uid']], claims
        verdict = engine.submit_code_check(check, stored['finding_uid'], 'contradicted',
                                           code_path=SUMMARY_EVIDENCE['path'],
                                           code_start_line=SUMMARY_EVIDENCE['start_line'],
                                           code_end_line=SUMMARY_EVIDENCE['end_line'],
                                           code_quote=SUMMARY_EVIDENCE['text'], note=THROWN_OUT_NOTE)
        assert 'request_rejected' not in verdict, verdict
        assert engine.submit_report(check, 'Checked one.', model=model['code-check'])['closed']
        if written:
            review.write()


def check_round(root, texts, source, quote):
    """A finished draft-check of ``texts`` with the numbers specialist alone and no code.

    The specialist files one finding on ``quote``. The arm runs no editor, so
    the server writes one issue for it and the run is not publishable.
    """
    manuscripts.build(root / 'manuscript', texts, source_sha256=digest(source))
    with scripted_review(root / 'manuscript.pdf', root, arm='draft-check', reviewers=0, tracks=['numbers']) as review:
        stored = review.submit_finding(slot='spec-numbers', title=MEAN['title'], quote=quote, comment=MEAN['comment'],
                                       severity='major')
        assert stored.get('stored'), stored
        assert review.submit_report('One.', slot='spec-numbers', model=models(review)['spec-numbers'])['closed']
        review.write()


def opened_round(root, texts, source):
    """A reviewers-only review of ``texts`` that stopped before any slot reported, as a run stopped early leaves it."""
    manuscripts.build(root / 'manuscript', texts, source_sha256=digest(source))
    scripted_review(root / 'manuscript.pdf', root, arm='reviewers-only', reviewers=2).close()


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

    def test_the_engine_runs_the_recorder_in_process_with_no_model(self):
        # The recorder is the engine's own Python, so the run asks no model of it, and it alone is in process.
        agents = self.view(self.first)['run']['agents']
        recorder = next(row for row in agents if row['slot'] == 'recorder')
        self.assertEqual((recorder['in_process'], recorder['assigned_model'], recorder['model']), (True, None, None))
        self.assertEqual([row['slot'] for row in agents if row['in_process']], ['recorder'])

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
        row = json.loads((self.coded / 'review' / 'findings.jsonl').read_text().splitlines()[0])
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
