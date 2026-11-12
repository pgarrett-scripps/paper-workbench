"""The engine surface the app depends on. PeerReviewAgents tests the engine itself.

These checks stay small on purpose, so they pass on every engine release that
keeps the aliases, the review and report commands and the review keys the app
and web/app.js read. No test starts a model session.
"""
import contextlib
import importlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from peerreviewagents.engine.annotations import export_draft, save_review, verify_workspace
from peerreviewagents.engine.storage import digest, write

from paper_workspace.__main__ import ENGINE_COMMANDS, build_parser, main

REPOSITORY = Path(__file__).resolve().parents[1]
# Runnable aliases import the engine module inside an else branch, so allow indentation.
ALIAS = re.compile(r'^\s*from peerreviewagents\.engine import (\w+) as _engine$', re.M)


def run_main(argv):
    """Call the app command line and return its exit status and printed JSON."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        status = main(argv)
    return status, json.loads(output.getvalue())


class EngineAliasSmokeTest(unittest.TestCase):
    def test_alias_modules_resolve_to_the_engine(self):
        aliases, replaced = {}, set()
        for path in sorted((REPOSITORY / 'paper_workspace').glob('*.py')):
            text = path.read_text()
            if 'sys.modules[__name__]' in text:
                replaced.add(f'paper_workspace.{path.stem}')
            match = ALIAS.search(text)
            if match:
                aliases[f'paper_workspace.{path.stem}'] = f'peerreviewagents.engine.{match.group(1)}'
        # Every module that replaces itself must be an alias this test checks, and the
        # count changes only when an alias is added or removed on purpose.
        self.assertEqual(replaced, set(aliases))
        self.assertEqual(len(aliases), 14)
        self.assertIn('paper_workspace.annotations', aliases)
        for name, target in aliases.items():
            with self.subTest(name=name):
                self.assertIs(importlib.import_module(name), importlib.import_module(target))
        self.assertEqual(list((REPOSITORY / 'paper_workbench_core').glob('*.py')), [])

    def test_parser_knows_the_app_and_engine_commands(self):
        parser = build_parser()
        self.assertEqual(ENGINE_COMMANDS, ('review', 'report'))
        for argv in (['serve', 'run'], ['verify', 'ws'], ['import', 'paper.pdf', 'ws', '--xml', 'paper.xml']):
            self.assertEqual(parser.parse_args(argv).command, argv[0])


class EngineCommandTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.pdf = self.root / 'paper.pdf'
        self.pdf.write_bytes(b'%PDF-1.4\n')

    def tearDown(self):
        self.temporary.cleanup()

    def test_review_starts_the_engine_review_and_returns_its_exit_status(self):
        calls = []

        def fake_review(pdf, out, **options):
            calls.append((pdf, out, options))
            return {'status': 'complete', 'run': out}

        with patch('peerreviewagents.review', fake_review):
            status, summary = run_main(['review', str(self.pdf), 'out', '--reviewers', '2'])
        self.assertEqual((status, summary), (0, {'status': 'complete', 'run': 'out'}))
        (pdf, out, options), = calls
        self.assertEqual((pdf, out, options['reviewers'], options['arm']), (str(self.pdf), 'out', 2, 'full-two-track'))

    def test_review_without_claude_is_blocked_at_startup_and_launches_nothing(self):
        from peerreviewagents.plugin import starter
        out = self.root / 'run'
        with patch.object(starter, 'claude_binary', return_value=None), \
                patch.object(starter, 'launch', side_effect=AssertionError('a session was launched')):
            status, summary = run_main(['review', str(self.pdf), str(out)])
        self.assertEqual((status, summary['status'], summary['stage']), (2, 'blocked', 'startup'))
        self.assertIn('claude is not installed', summary['blocked_reason'])
        self.assertTrue((out / 'review' / 'startup.json').is_file())

    def test_report_renders_a_finished_run_from_the_run_folder(self):
        from test_run_view import make_run
        make_run(self.root / 'run')
        status, paths = run_main(['report', str(self.root / 'run')])
        self.assertEqual(status, 0)
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
