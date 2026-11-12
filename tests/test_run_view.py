"""A PeerReviewAgents run folder in the viewer: the run's review, its decisions and its export."""
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from peerreviewagents.engine.storage import digest, write

from paper_workspace.run_view import locate, run_review
from paper_workspace.server import make_server

TEXT = 'Knockdown lowered VPS35 in 12 samples.'


def finding(uid, quote, **extra):
    start = TEXT.index(quote)
    return {'id': f'core-1-1-{uid}', 'finding_uid': uid, 'kind': 'question', 'category': 'scientific',
            'severity': 'major', 'title': f'Finding {uid}', 'comment': 'Name the control.', 'block_id': 'b1',
            'quote': quote, 'start': start, 'end': start + len(quote), 'block_sha256': digest(TEXT),
            'placement': 'anchored', 'evidence_blocks': [], 'track': 'core', 'basis': 'judgement',
            'basis_reason': 'No arithmetic receipt.', 'escalate': False, **extra}


def make_run(root, package=True):
    """A run folder as ``peerreview review`` leaves it, with one body finding and one duplicate."""
    manuscript, review = root / 'manuscript', root / 'review'
    write(manuscript / 'paper.json', {'id': 'qa', 'title': 'QA', 'source_sha256': 'qa-source',
        'blocks': [{'id': 'b1', 'text': TEXT, 'sha256': digest(TEXT)}], 'statistics': {'pdf_pages': 1}})
    write(manuscript / 'manifest.json', {'files': {'paper.json': digest((manuscript / 'paper.json').read_bytes())}})
    write(review / 'protocol.json', {'arm': 'full-two-track', 'reviewers': 3})
    write(review / 'manifest.json', {'paper_id': 'qa', 'source_sha256': 'qa-source'})
    write(review / 'progress.json', {'status': 'complete', 'error': None,
        'stages': {'missing': [], 'none_found': ['spec-citations']}})
    write(review / 'runtime.json', {'status': 'complete', 'tokens_total': 900, 'wall_seconds': 120})
    body = finding('aa11', 'lowered VPS35', track='field', escalate=True, editor_reason='Central claim.',
                   reviewers_raising=2, duplicate_uids=['bb22'])
    appendix = finding('bb22', '12 samples', editor_placement='duplicate', duplicate_of='aa11',
                       editor_reason='Same objection.', rebuttal_quote=None)
    (review / 'findings.jsonl').write_text(json.dumps(body) + '\n' + json.dumps(appendix) + '\n')
    if package:
        write(review / 'editor-package.json', {'summary': 'One central question.', 'arm': 'full-two-track',
            'findings': [body], 'appendix': [appendix], 'escalated_count': 1, 'reviewer_count': 3,
            'review_guard_status': 'clean', 'findings_by_track': {'field': 1, 'core': 1},
            'verdict': {'significance': 'High', 'strength_of_evidence': 'Weak', 'reasoning': 'Correlation.',
                        'basis': 'judgement', 'limitation': 'Advisory.'},
            'escalation_rulings': [{'finding_uid': 'aa11', 'ruling': 'Accepted.'}],
            'reviewer_provenance': [{'slot': 'core-1', 'track': 'core', 'model': 'claude-sonnet-5-5',
                                     'attempt': 1, 'tool_calls': 3, 'findings': 1, 'none_found': False}]})
    (review / 'audit_stats.md').write_text('# Statistics audit\n')
    outside = root / 'secret.md'
    outside.write_text('outside the review folder')
    (review / 'audit_leak.md').symlink_to(outside)
    return manuscript, review


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
        with self.assertRaisesRegex(ValueError, 'stopped before import'):
            locate(self.root)

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
        # A symlinked report is never read, so the viewer cannot serve a file outside the run.
        self.assertEqual(run['audits'], {'stats': '# Statistics audit\n'})

    def test_repeated_finding_uids_fall_back_to_positional_ids(self):
        package = json.loads((self.review / 'editor-package.json').read_text())
        package['appendix'][0]['finding_uid'] = 'aa11'
        write(self.review / 'editor-package.json', package)
        self.assertEqual([f['id'] for f in run_review(self.review, self.paper)['findings']], ['run-1', 'run-2'])

    def test_a_run_on_another_manuscript_version_is_refused(self):
        write(self.review / 'manifest.json', {'paper_id': 'qa', 'source_sha256': 'other'})
        with self.assertRaisesRegex(ValueError, 'different manuscript version'):
            run_review(self.review, self.paper)

    def test_a_run_without_an_editor_package_shows_the_recorded_findings(self):
        (self.review / 'editor-package.json').unlink()
        write(self.review / 'progress.json', {'status': 'blocked', 'error': 'editor timed out', 'stages': {}})
        review = run_review(self.review, self.paper)
        self.assertEqual([(f['id'], f['section']) for f in review['findings']], [('aa11', 'body'), ('bb22', 'body')])
        self.assertFalse(review['run']['edited'])
        self.assertIn('editor timed out', review['summary'])


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
        write(self.review / 'manifest.json', {'paper_id': 'qa', 'source_sha256': 'other'})
        status, body = self.request('/api/review?review=run')
        self.assertEqual((status, body), (400, {'error': 'The run reviewed a different manuscript version'}))


if __name__ == '__main__':
    unittest.main()
