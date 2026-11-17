"""Two review rounds built by the engine's own code, read by the viewer.

The engine has no public way to build a run folder without a model. Its own
tests submit the findings through its server as the reviewer slots would and
do the grouping in Python, so no model is started and nothing reaches the
network. This file builds two rounds that way, and a third run given analysis
code whose code lane files one code-checked finding, and drives the viewer from
them, so the hand-written fixture in test_run_view.py is checked against what
the engine writes. The third run's code is what a workspace review hands over
for a Paper Scaffold workspace, so the snapshot of it shows what the engine
takes from one and what it leaves out. Round one and the third run are written
inside that workspace, as ``paper-workbench review . reviews/NAME`` writes them,
so the snapshot also shows that no run's files are copied in as code.
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

from peerreviewagents import read_manuscript, read_run
from peerreviewagents.plugin import server as engine
from peerreviewagents.workspace import digest

import manuscripts
from paper_workspace.run_view import run_review
from paper_workspace.server import make_server
from paper_workspace.workspace_review import engine_argv
from test_run_view import CODE_EVIDENCE, PIPELINE, finding, issue
from test_workspace_review import make_workspace

FIRST =['Knockdown lowered VPS35 in twelve samples drawn from one donor.',
         'The authors conclude that VPS35 controls retromer assembly in all tissues.',
         'Each assay was repeated three times and the mean is reported in the figure.']
SECOND = ['Knockdown lowered VPS35 in twelve samples drawn from four donors.', FIRST[1], FIRST[2]]
CODE_TEXTS = ['Peptides were filtered at a false discovery rate of one percent.', FIRST[2]]
CREDENTIALS = ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'OPENAI_API_KEY')


def grouped(name, rank, members, **extra):
    return {'name': name, 'severity': 'major', 'category': 'claims-and-conclusions', 'rank': rank,
            'members': members, 'statement': f'{name} is stated more strongly than the data carry.', **extra}


def one_round(root, texts, source, quotes, issues, prior='', **ruling):
    """One reviewers-only round: core-1 raises a finding per quote, core-2 finds none, the editor groups them."""
    engine.STATE['run'] = None
    manuscripts.build(root / 'manuscript', texts, source_sha256=digest(source))
    opened = engine.ingest(str(root / 'manuscript.pdf'), str(root), arm='reviewers-only', reviewers=2,
                           prior_issues=prior)
    assert 'request_rejected' not in opened, opened
    codes = {row['slot']: row['claim_code'] for row in opened['claim_codes']}
    # The manuscript is sealed before ingest, so the engine plans no Read stage.
    assert opened['reader'] is None and 'reader' not in codes, opened
    run = engine.current()

    def token(slot):
        return engine.claim_agent(slot, codes.pop(slot))['agent_token']

    core = token('core-1')
    # The engine refuses findings and issues from a slot it has not served the whole manuscript.
    engine.read_paper(core)
    uids = []
    for quote in quotes:
        stored = engine.submit_finding(core, title='Claim', quote=quote,
                                       comment='The sentence asserts more than it shows.', severity='major')
        assert stored.get('stored'), stored
        uids.append(stored['finding_uid'])
    assert engine.submit_report(core, 'Checked.', model=run.models.get('core-1'))['closed']
    other = token('core-2')
    assert engine.submit_report(other, 'Nothing.', none_found=True, model=run.models.get('core-2'))['closed']
    editor = token('editor')
    engine.read_paper(editor)
    stored = engine.submit_issues(editor, issues(uids))
    assert 'request_rejected' not in stored, stored
    answer = engine.submit_editor(editor, summary='One question of scope.', significance='Modest.',
                                  strength_of_evidence='Weak.', verdict_reasoning='The scope is overstated.',
                                  **ruling)
    assert answer.get('accepted'), answer
    assert engine.submit_report(editor, 'Grouped.', model=run.models.get('editor'))['closed']
    engine.write_review(token('recorder'))
    engine.STATE['run'] = None


def code_round(root, code):
    """A draft-check run given ``code``: the code lane files one code-checked finding, the numbers lane none.

    The arm runs specialists and no editor, so the server writes one issue per
    finding. The manuscript is sealed before ingest, so the engine plans no reader.
    """
    engine.STATE['run'] = None
    (code / 'analysis').mkdir(parents=True, exist_ok=True)
    (code / CODE_EVIDENCE['path']).write_text(PIPELINE)
    manuscripts.build(root / 'manuscript', CODE_TEXTS, source_sha256=digest('source-code'))
    opened = engine.ingest(str(root / 'manuscript.pdf'), str(root), arm='draft-check', reviewers=0,
                           tracks=['numbers'], code=str(code))
    assert 'request_rejected' not in opened, opened
    codes = {row['slot']: row['claim_code'] for row in opened['claim_codes']}
    assert opened['reader'] is None and 'reader' not in codes, opened
    run = engine.current()

    def token(slot):
        agent = engine.claim_agent(slot, codes.pop(slot))['agent_token']
        engine.read_paper(agent)
        return agent

    lane = token('spec-code')
    assert 'request_rejected' not in engine.read_code(lane, CODE_EVIDENCE['path'])
    stored = engine.submit_finding(lane, title='The threshold in the methods is not the one in the code',
                                   quote='a false discovery rate of one percent', severity='major',
                                   comment='The methods say one percent and the pipeline filters at five.',
                                   code_path=CODE_EVIDENCE['path'], code_start_line=CODE_EVIDENCE['start_line'],
                                   code_end_line=CODE_EVIDENCE['end_line'], code_quote=CODE_EVIDENCE['text'])
    assert stored.get('stored'), stored
    assert engine.submit_report(lane, 'Checked.', model=run.models.get('spec-code'))['closed']
    numbers = token('spec-numbers')
    assert engine.submit_report(numbers, 'Nothing.', none_found=True, model=run.models.get('spec-numbers'))['closed']
    engine.write_review(engine.claim_agent('recorder', codes.pop('recorder'))['agent_token'])
    engine.STATE['run'] = None


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
        environment = {key: value for key, value in os.environ.items() if key not in CREDENTIALS}
        with mock.patch.dict(os.environ, environment, clear=True):
            plugin_root = engine.STATE.get('plugin_root')
            engine.STATE['plugin_root'] = None
            try:
                one_round(cls.first, FIRST, 'source-1', [
                    'twelve samples drawn from one donor', 'controls retromer assembly in all tissues',
                    'repeated three times'],
                    lambda uids: [grouped('The sample', 1, [uids[0]]), grouped('The scope', 2, [uids[1]]),
                                  grouped('The repeats', 3, [uids[2]])])
                # Round two reads round one's issues.json, and the editor rules on each prior issue.
                one_round(cls.second, SECOND, 'source-2', [
                    'controls retromer assembly in all tissues', 'The authors conclude'],
                    lambda uids: [grouped('The scope', 1, [uids[0]], prior_id='i02', status='persisting',
                                          status_reason='The sentence is unchanged.'),
                                  grouped('The attribution', 2, [uids[1]])],
                    prior=str(cls.first / 'review' / 'issues.json'),
                    prior_rulings=[{'prior_id': 'i01', 'status': 'resolved',
                                    'reason': 'The sample now spans four donors.'},
                                   {'prior_id': 'i03', 'status': 'unverified',
                                    'reason': 'Nobody raised it again.'}])
                # The code is what `paper-workbench review WORKSPACE RUN` hands the engine, with RUN inside it.
                argv, _ = engine_argv([str(cls.workspace), str(cls.coded), '--arm', 'draft-check'])
                code_round(cls.coded, Path(argv[argv.index('--code') + 1]))
            finally:
                engine.STATE['run'] = None
                engine.STATE['plugin_root'] = plugin_root

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

    def test_round_one_is_read_as_three_issues(self):
        review = self.view(self.first)
        self.assertEqual([(f['id'], f['group'], f['status'], f['decidable'], len(f['members']))
                          for f in review['findings']],
                         [('i01', 'required', 'new', True, 1), ('i02', 'required', 'new', True, 1),
                          ('i03', 'required', 'new', True, 1)])
        self.assertIsNone(review['run']['prior_round'])

    def test_round_two_keeps_the_prior_ids(self):
        review = self.view(self.second)
        self.assertEqual([(f['id'], f['group'], f['status'], f['prior_id'], f['decidable'])
                          for f in review['findings']],
                         [('i02', 'required', 'persisting', 'i02', True), ('i04', 'required', 'new', None, True),
                          ('i01', 'closed', 'resolved', 'i01', True), ('i03', 'closed', 'unverified', 'i03', True)])
        self.assertEqual([f['status_reason'] for f in review['findings'][2:]],
                         ['The sample now spans four donors.', 'Nobody raised it again.'])
        # The engine records the prior round by its file name and digest. Nothing names the prior run folder.
        prior = review['run']['prior_round']
        self.assertEqual(sorted(prior), ['digest', 'file', 'issues', 'tally'])
        self.assertEqual((prior['file'], prior['issues']), ('issues.json', 3))
        self.assertEqual(prior['tally'], {'new': 1, 'persisting': 1, 'regressed': 0, 'resolved': 1, 'unverified': 1})

    def test_decisions_stay_with_the_run_folder_they_were_made_in(self):
        with served(self.first) as request:
            status, decisions = request('/api/decisions', {'review_id': 'run', 'annotation_id': 'i02',
                'status': 'noted', 'revision': 0, 'author_comment': 'Narrowed the claim to HeLa cells.'})
            self.assertEqual((status, decisions['items']), (200, {'i02': 'noted'}))
        # Round two opens with no decisions, though i02 is the same issue.
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
        code = review['run']['code']
        self.assertEqual((code['reviewed'], code['kind'], code['files_opened'], code['opened']),
                         (True, 'folder', [CODE_EVIDENCE['path']], 1))
        self.assertNotIn('manifest', code)

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
        self.assertIn('paper.pdf', skipped)
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
