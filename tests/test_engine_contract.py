"""The engine surface the app depends on. PeerReviewAgents tests the engine itself.

These checks stay small on purpose, so they pass on every engine release that
keeps the review and report commands and the review keys the app and
web/app.js read. No test starts a model session, and none patches the engine.
"""
import ast
import contextlib
import hashlib
import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from peerreviewagents import CLI_COMMANDS, MANUSCRIPT_STATES, export_draft, review_arms, verify_workspace
from peerreviewagents.workspace import save_review

import manuscripts
from manuscripts import line_of
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
        self.assertEqual(ENGINE_COMMANDS, ('review', 'check-fixes', 'report'))
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

    def test_review_help_lists_the_per_slot_model_options(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
            main(['review', '-h'])
        for flag in ('--reviewer-models', '--specialist-model', '--editor-model', '--recorder-model',
                     '--citation-workers', '--citation-worker-model', '--reader-model', '--code'):
            self.assertIn(flag, output.getvalue())
        # The reader always runs on a PDF review, so there is no switch to turn it off.
        self.assertNotIn('--no-ai-read', output.getvalue())
        # Every review is a fresh panel, so there is no option that hands it an earlier review.
        self.assertNotIn('--prior-issues', output.getvalue())


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
                                        '--reviewers', '2', '--reviewer-models', 'claude-haiku-5-5,claude-opus-5-5',
                                        '--editor-model', 'claude-opus-5-5', '--recorder-model', 'claude-sonnet-5-5',
                                        '--reader-model', 'claude-haiku-5-5'])
        self.assertEqual((status, summary['status'], summary['stage']), (2, 'blocked', 'startup'))
        self.assertIn('claude is not installed', summary['blocked_reason'])
        # The options reach the engine, which records them in its summary. The reader is the Read
        # stage's slot, which reads the page images before any reviewer starts.
        self.assertEqual((summary['arm'], summary['reviewers']), ('reviewers-only', 2))
        self.assertEqual(summary['models_requested'], {'reader': 'claude-haiku-5-5', 'core-1': 'claude-haiku-5-5',
                                                       'core-2': 'claude-opus-5-5', 'editor': 'claude-opus-5-5',
                                                       'recorder': 'claude-sonnet-5-5'})
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

    def test_review_plans_the_six_specialist_lanes_and_the_citation_workers(self):
        empty = self.root / 'bin'
        empty.mkdir()
        with patch.dict(os.environ, {'PATH': str(empty)}):
            status, summary = run_main(['review', str(self.pdf), str(self.root / 'run'), '--arm', 'full-two-track',
                                        '--reviewers', '2', '--citation-workers', '2',
                                        '--citation-worker-model', 'claude-opus-5-5'])
        self.assertEqual((status, summary['status'], summary['stage']), (2, 'blocked', 'startup'))
        requested = summary['models_requested']
        self.assertLessEqual({f'spec-{lane}' for lane in ('stats', 'figures-tables', 'methods-reporting',
                                                          'citations', 'numbers', 'field')}, set(requested))
        self.assertEqual({slot: model for slot, model in requested.items() if slot.startswith('cite-')},
                         {'cite-1': 'claude-opus-5-5', 'cite-2': 'claude-opus-5-5'})
        self.assertNotIn('spec-consistency', requested)
        # The engine accepts 0 to 12 workers and refuses more before it plans anything.
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit):
            main(['review', str(self.pdf), str(self.root / 'other'), '--citation-workers', '13'])
        self.assertIn('--citation-workers', stderr.getvalue())
        self.assertFalse((self.root / 'other').exists())

    def test_review_hands_the_analysis_code_to_the_code_lane(self):
        code = self.root / 'paper-repo'
        (code / 'analysis').mkdir(parents=True)
        (code / 'analysis' / 'pipeline.py').write_text('FDR_THRESHOLD = 0.05\n')
        empty = self.root / 'bin'
        empty.mkdir()
        with patch.dict(os.environ, {'PATH': str(empty)}):
            status, summary = run_main(['review', str(self.pdf), str(self.root / 'run'), '--arm', 'draft-check',
                                        '--code', str(code)])
        self.assertEqual((status, summary['status'], summary['stage']), (2, 'blocked', 'startup'))
        self.assertIn('spec-code', summary['models_requested'])

    def test_review_of_a_workspace_reviews_its_built_pdf_with_its_code(self):
        from test_workspace_review import make_workspace
        workspace = make_workspace(self.root / 'paper')
        pdf = workspace / 'paper.pdf'
        empty = self.root / 'bin'
        empty.mkdir()
        for extra, code in (([], True), (['--no-code'], False)):
            out = self.root / f'run-{len(extra)}'
            stderr = io.StringIO()
            with patch.dict(os.environ, {'PATH': str(empty)}), contextlib.redirect_stderr(stderr):
                status, summary = run_main(['review', str(workspace), str(out), '--arm', 'draft-check', *extra])
            self.assertEqual((status, summary['status'], summary['stage']), (2, 'blocked', 'startup'), extra)
            # The workspace's code reaches the plan as the code lane, and --no-code keeps it out.
            self.assertEqual('spec-code' in summary['models_requested'], code, extra)
            self.assertIn(f'reviewing {pdf} with ' + (f'the code in {workspace}.' if code else 'no code.'),
                          stderr.getvalue())
            # The run records the built PDF as the manuscript it was asked to review.
            identity = json.loads((out / 'review' / 'manifest.json').read_text())
            self.assertEqual((identity['pdf'], identity['source_sha256']),
                             (str(pdf), hashlib.sha256(pdf.read_bytes()).hexdigest()), extra)

    def test_a_workspace_review_on_an_arm_with_no_code_reviews_the_paper_alone(self):
        from test_workspace_review import make_workspace
        workspace = make_workspace(self.root / 'paper')
        pdf = workspace / 'paper.pdf'
        other = self.root / 'paper-repo'
        other.mkdir()
        empty = self.root / 'bin'
        empty.mkdir()
        for arm in (name for name, row in review_arms().items() if not row['code']):
            # The app picked the code, so the arm runs without it and the line on stderr says so.
            out = self.root / f'run-{arm}'
            stderr = io.StringIO()
            with patch.dict(os.environ, {'PATH': str(empty)}), contextlib.redirect_stderr(stderr):
                status, summary = run_main(['review', str(workspace), str(out), '--arm', arm])
            self.assertEqual((status, summary['status'], summary['stage'], summary['arm']),
                             (2, 'blocked', 'startup', arm))
            self.assertNotIn('spec-code', summary['models_requested'], arm)
            self.assertIn(f'reviewing {pdf} with no code, because the {arm} arm reviews no code. The draft-check '
                          'and full-two-track arms would review it', stderr.getvalue())
            self.assertFalse((out / 'code').exists(), arm)
            # Code the author named on such an arm is the engine's to refuse, before anything is written.
            out = self.root / f'named-{arm}'
            stderr, stdout = io.StringIO(), io.StringIO()
            with patch.dict(os.environ, {'PATH': str(empty)}), contextlib.redirect_stderr(stderr), \
                    contextlib.redirect_stdout(stdout):
                status = main(['review', str(workspace), str(out), '--arm', arm, '--code', str(other)])
            self.assertEqual((status, stdout.getvalue()), (2, ''), arm)
            self.assertIn('runs no specialists', stderr.getvalue(), arm)
            self.assertFalse((out / 'code').exists(), arm)

    def test_review_arms_says_which_arms_the_engine_hands_code(self):
        # A workspace review hands its code only to an arm whose row says code, so the row must be what review does.
        code = self.root / 'paper-repo'
        (code / 'analysis').mkdir(parents=True)
        (code / 'analysis' / 'pipeline.py').write_text('FDR_THRESHOLD = 0.05\n')
        empty = self.root / 'bin'
        empty.mkdir()
        for arm, row in review_arms().items():
            out = self.root / f'run-{arm}'
            stderr, stdout = io.StringIO(), io.StringIO()
            with patch.dict(os.environ, {'PATH': str(empty)}), contextlib.redirect_stderr(stderr), \
                    contextlib.redirect_stdout(stdout):
                status = main(['review', str(self.pdf), str(out), '--arm', arm, '--code', str(code)])
            self.assertEqual(status, 2, arm)
            if row['code']:
                summary = json.loads(stdout.getvalue())
                self.assertEqual((summary['status'], summary['stage']), ('blocked', 'startup'), arm)
                self.assertIn('spec-code', summary['models_requested'], arm)
            else:
                self.assertEqual(stdout.getvalue(), '', arm)
                self.assertIn('runs no specialists', stderr.getvalue(), arm)
                self.assertFalse((out / 'code').exists(), arm)

    def test_review_refuses_code_it_cannot_review(self):
        code = self.root / 'paper-repo'
        code.mkdir()
        cases = [(['--code', str(self.root / 'missing')], 'No code folder at'),
                 (['--arm', 'single', '--code', str(code)], 'runs no specialists')]
        for extra, message in cases:
            out = self.root / f'run-{len(extra)}'
            stderr, stdout = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
                status = main(['review', str(self.pdf), str(out), *extra])
            self.assertEqual(status, 2, extra)
            self.assertIn(message, stderr.getvalue())
            self.assertFalse((out / 'code').exists(), extra)

    def test_report_renders_a_finished_run_from_the_run_folder(self):
        from test_run_view import make_run
        make_run(self.root / 'run')
        status, report = run_main(['report', str(self.root / 'run')])
        self.assertEqual((status, report['status'], report['findings'], report['issues'], report['required'],
                          report['suggestions']), (0, 'complete', 3, 2, 1, 1))
        self.assertEqual((report['publishable'], report['not_publishable_reasons']), (True, []))
        # The summary keys come first, then one key per report path.
        paths = {key: value for key, value in report.items()
                 if key not in ('status', 'cause', 'findings', 'issues', 'required', 'suggestions', 'publishable',
                                'not_publishable_reasons', 'problems')}
        self.assertTrue(paths)
        for path in paths.values():
            self.assertTrue(Path(path).is_file(), path)
        text = (self.root / 'run' / 'review' / 'REVIEW.md').read_text()
        self.assertIn('One central question.', text)
        # REVIEW.md renders from issues.json: the required changes, then the suggestions by category.
        self.assertLess(text.index('## Required changes'), text.index('### 1. The knockdown control is not named'))
        self.assertLess(text.index('## Suggestions'), text.index('### 2. The opening sentence needs an article'))
        # The engine renders the citation ledger into REVIEW.md as its own section.
        self.assertIn('\n## Citations\n', text)


class EngineOutputContractTest(unittest.TestCase):
    def test_review_and_export_keys_the_app_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = manuscripts.build(root, ['A claim with 12 samples.'])
            line = line_of(paper, '12 samples')
            review = save_review(root, {'summary': 'One edit and one question.', 'findings': [
                {'kind': 'edit', 'line': line, 'quote': '12 samples', 'replacement': '12 donors',
                 'evidence_lines': [line]},
                {'kind': 'question', 'line': line, 'quote': 'A claim', 'comment': 'Name the cohort.',
                 'evidence_lines': [line]}]}, 'qa')
            paper = verify_workspace(root)
        # server.py, revisions.py and web/app.js read these review keys.
        self.assertLessEqual({'id', 'findings', 'summary', 'raw_response'}, set(review))
        edit, question = review['findings']
        for finding in (edit, question):
            self.assertLessEqual({'id', 'kind', 'document', 'line', 'end_line', 'start', 'end', 'placement',
                                  'quote', 'anchor_text', 'category', 'evidence_lines', 'fingerprint'}, set(finding))
        self.assertEqual((edit['kind'], edit['document'], edit['line'], edit['end_line'], edit['placement'],
                          edit['start'], edit['end'], edit['replacement']),
                         ('edit', 'paper.md', line, line, 'anchored', 13, 23, '12 donors'))
        self.assertEqual((question['kind'], question['comment']), ('question', 'Name the cohort.'))
        decisions = {'paper_id': paper.paper_id, 'review_id': 'qa', 'revision': 0,
                     'items': {edit['id']: 'accepted', question['id']: 'noted'}, 'annotations': {}}
        exported = export_draft(paper, review, decisions)
        # revisions.py checks a rebuilt draft against proposed_documents, and the viewer download carries the rest.
        self.assertEqual(exported['proposed_documents'], {'paper.md': '# QA\n\nA claim with 12 donors.\n'})
        self.assertEqual(exported['original_documents'], paper.documents)
        self.assertEqual([f['issue_status'] for f in exported['findings']], ['open', 'open'])

    def test_the_manuscript_state_the_viewer_names(self):
        # run_view tells a run whose Read stage never sealed from one that never imported by the
        # draft state of read_run's manuscript key, so a rename of that state fails here.
        self.assertIn('draft', MANUSCRIPT_STATES)


class PublicSurfaceTest(unittest.TestCase):
    PRIVATE = ('engine', 'plugin', 'cli', 'runs')
    # test_engine_rounds.py builds its rounds with scripted_review, which does not claim the code check's
    # slot, so that one slot acts through the engine's own server. The engine has no public ledger writer
    # either, so the fixture generator imports its ledger module. No test runs the generator.
    ALLOWED = ['tests/fixtures/citations/generate.py: ' + 'peerreviewagents.' + 'engine',
               'tests/test_engine_rounds.py: ' + 'peerreviewagents.' + 'plugin']

    def test_the_app_and_its_tests_use_only_public_engine_names(self):
        # A dotted name catches an import, a lazy import or a patch target. The AST catches
        # `from peerreviewagents import runs`. The pattern is built here so this file does not match it.
        dotted = re.compile(r'peerreviewagents\.(%s)\b' % '|'.join(self.PRIVATE))
        root = Path(__file__).resolve().parents[1]
        found = []
        for folder in ('paper_workspace', 'tests'):
            for path in sorted((root / folder).rglob('*.py')):
                source, name = path.read_text(), path.relative_to(root)
                found += [f'{name}: {match.group(0)}' for match in dotted.finditer(source)]
                for node in ast.walk(ast.parse(source)):
                    if isinstance(node, ast.ImportFrom) and node.module == 'peerreviewagents':
                        found += [f'{name}: from peerreviewagents import {alias.name}'
                                  for alias in node.names if alias.name in self.PRIVATE]
        self.assertEqual(found, self.ALLOWED)


if __name__ == '__main__':
    unittest.main()
