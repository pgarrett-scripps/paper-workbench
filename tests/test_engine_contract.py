"""The engine surface the app depends on. PeerReviewAgents tests the engine itself.

These checks stay small on purpose, so they pass on every engine release that
keeps the review and report commands and the review keys the app and
web/app.js read. No test starts a model session, and none patches the engine.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from peerreviewagents import CLI_COMMANDS, export_draft, verify_workspace
from peerreviewagents.engine.annotations import save_review
from peerreviewagents.engine.storage import digest, write

from paper_workspace.__main__ import ENGINE_COMMANDS, build_parser, main


def run_main(argv):
    """Call the app command line and return its exit status and printed JSON."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        status = main(argv)
    return status, json.loads(output.getvalue())


class AppCommandTest(unittest.TestCase):
    def test_parser_knows_the_app_and_engine_commands(self):
        parser = build_parser()
        self.assertEqual(ENGINE_COMMANDS, ('review', 'report'))
        self.assertEqual(ENGINE_COMMANDS, CLI_COMMANDS)
        for argv in (['serve', 'run'], ['verify', 'ws'], ['import', 'paper.pdf', 'ws', '--xml', 'paper.xml']):
            self.assertEqual(parser.parse_args(argv).command, argv[0])

    def test_engine_command_help_names_the_app(self):
        for command in ENGINE_COMMANDS:
            output = io.StringIO()
            with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as stop:
                main([command, '-h'])
            self.assertEqual(stop.exception.code, 0)
            self.assertTrue(output.getvalue().startswith(f'usage: paper-workbench {command}'), output.getvalue())


class EngineCommandTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.pdf = self.root / 'paper.pdf'
        self.pdf.write_bytes(b'%PDF-1.4\n')

    def tearDown(self):
        self.temporary.cleanup()

    def test_review_without_claude_is_blocked_at_startup_and_launches_nothing(self):
        out = self.root / 'run'
        empty = self.root / 'bin'
        empty.mkdir()
        # With no claude on PATH the engine cannot launch a session, so nothing is patched.
        with patch.dict(os.environ, {'PATH': str(empty)}):
            status, summary = run_main(['review', str(self.pdf), str(out), '--arm', 'reviewers-only',
                                        '--reviewers', '2'])
        self.assertEqual((status, summary['status'], summary['stage']), (2, 'blocked', 'startup'))
        self.assertIn('claude is not installed', summary['blocked_reason'])
        # The options reach the engine, which records them in its summary.
        self.assertEqual((summary['arm'], summary['reviewers']), ('reviewers-only', 2))
        self.assertTrue((out / 'review' / 'startup.json').is_file())
        # The run never imported the manuscript, so serve says why in plain words.
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(main(['serve', str(out)]), 1)
        self.assertIn('claude is not installed', stderr.getvalue())
        # report renders any run, and its report says why this one stopped.
        status, report = run_main(['report', str(out)])
        self.assertEqual((status, report['status']), (0, 'blocked'))
        self.assertIn('claude is not installed', report['cause'])

    def test_report_renders_a_finished_run_from_the_run_folder(self):
        from test_run_view import make_run
        make_run(self.root / 'run')
        status, report = run_main(['report', str(self.root / 'run')])
        self.assertEqual((status, report['status'], report['findings']), (0, 'complete', 2))
        self.assertEqual((report['publishable'], report['not_publishable_reasons']), (True, []))
        # The summary keys come first, then one key per report path.
        paths = {key: value for key, value in report.items()
                 if key not in ('status', 'cause', 'findings', 'publishable', 'not_publishable_reasons', 'problems')}
        self.assertTrue(paths)
        for path in paths.values():
            self.assertTrue(Path(path).is_file(), path)
        self.assertIn('One central question.', (self.root / 'run' / 'review' / 'REVIEW.md').read_text())


class EngineOutputContractTest(unittest.TestCase):
    def test_review_and_export_keys_the_app_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = 'A claim with 12 samples.'
            write(root / 'paper.json', {'id': 'qa', 'title': 'QA', 'source_sha256': 'qa',
                'blocks': [{'id': 'b1', 'text': text, 'sha256': digest(text)}],
                'statistics': {'pdf_pages': 1}})
            write(root / 'manifest.json', {'files': {'paper.json': digest((root / 'paper.json').read_bytes())}})
            review = save_review(root, {'summary': 'One edit and one question.', 'findings': [
                {'kind': 'edit', 'block_id': 'b1', 'quote': '12 samples', 'replacement': '12 donors',
                 'evidence_blocks': ['b1']},
                {'kind': 'question', 'block_id': 'b1', 'quote': 'A claim', 'comment': 'Name the cohort.',
                 'evidence_blocks': ['b1']}]}, 'qa')
            paper = verify_workspace(root)
        # server.py, revisions.py and web/app.js read these review keys.
        self.assertLessEqual({'id', 'findings', 'summary', 'raw_response'}, set(review))
        edit, question = review['findings']
        for finding in (edit, question):
            self.assertLessEqual({'id', 'kind', 'block_id', 'block_sha256', 'start', 'end', 'placement',
                                  'quote', 'category', 'evidence_blocks'}, set(finding))
        self.assertEqual((edit['kind'], edit['placement'], edit['start'], edit['end'], edit['replacement']),
                         ('edit', 'anchored', 13, 23, '12 donors'))
        self.assertEqual((question['kind'], question['comment']), ('question', 'Name the cohort.'))
        decisions = {'paper_id': 'qa', 'review_id': 'qa', 'revision': 0,
                     'items': {edit['id']: 'accepted', question['id']: 'noted'}, 'annotations': {}}
        exported = export_draft(paper, review, decisions)
        # revisions.py applies proposed_blocks, and the viewer download carries the rest.
        self.assertEqual([(b['id'], b['text']) for b in exported['proposed_blocks']],
                         [('b1', 'A claim with 12 donors.')])
        self.assertEqual([b['text'] for b in exported['original_blocks']], [text])
        self.assertEqual([f['issue_status'] for f in exported['findings']], ['open', 'open'])


if __name__ == '__main__':
    unittest.main()
