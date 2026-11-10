"""The engine surface the app depends on. PeerReviewAgents tests the engine itself.

These checks stay small on purpose, so they pass on every engine release that
keeps the aliases, the CLI pass-through and the review keys the app and
web/app.js read.
"""
import importlib
import re
import tempfile
import unittest
from pathlib import Path

from peerreviewagents.engine.annotations import export_draft, save_review, verify_workspace
from peerreviewagents.engine.storage import digest, write

REPOSITORY = Path(__file__).resolve().parents[1]
ALIAS = re.compile(r'^from peerreviewagents\.engine import (\w+) as _engine$', re.M)


class EngineAliasSmokeTest(unittest.TestCase):
    def test_alias_modules_and_cli_pass_through_resolve(self):
        aliases = {}
        for package in ('paper_workspace', 'paper_workbench_core'):
            for path in sorted((REPOSITORY / package).glob('*.py')):
                match = ALIAS.search(path.read_text())
                if match:
                    aliases[f'{package}.{path.stem}'] = f'peerreviewagents.engine.{match.group(1)}'
        self.assertIn('paper_workbench_core.api', aliases)
        self.assertIn('paper_workspace.annotations', aliases)
        for name, target in aliases.items():
            with self.subTest(name=name):
                self.assertIs(importlib.import_module(name), importlib.import_module(target))
        core = importlib.import_module('paper_workbench_core')
        for name in core.__all__:
            self.assertTrue(hasattr(core, name), name)
        from paper_workspace.__main__ import build_parser
        parser = build_parser()
        self.assertEqual(parser.parse_args(['serve', 'ws']).command, 'serve')
        self.assertEqual(parser.parse_args(['verify', 'ws']).command, 'verify')


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
