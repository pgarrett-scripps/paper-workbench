"""A Paper Scaffold workspace stands where the PDF does in ``paper-workbench review``.

The build record is written here the way Paper Scaffold's ``tools/build_state.py``
writes ``.build-state/paper.pdf.json``. The app's reading of it was checked once
against Scaffold's own ``check()`` on a real workspace and a copy of it with an
edited source, pins changed, the PDF replaced and the PDF removed. No test
starts a review.
"""
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from peerreviewagents import review_arms

from paper_workspace.__main__ import main
from paper_workspace.workspace_review import code_root, engine_argv, parser


def sha(data):
    return hashlib.sha256(data).hexdigest()


#: A workspace's files: its manuscript source, its code, its data and a file that may hold secrets.
WORKSPACE_FILES = {
    'paper.typ': '#include "sections/methods.typ"\n',
    'sections/methods.typ': 'Peptides were filtered at a false discovery rate of one percent.\n',
    'refs.bib': '@article{one, title={One}}\n',
    'stats.json': json.dumps({'values': {'fdr': 0.01}, 'pinned': {'analysis/pipeline.py': 'first'}}),
    'analysis/pipeline.py': 'FDR_THRESHOLD = 0.05\n',
    'data/peptides.csv': 'peptide,score\nPEPTIDE,1\n',
    'results/table.txt': 'one row\n',
    'figures/figure1.py': 'plot()\n',
    '.env': 'TOKEN=not-a-real-one\n',
}


def make_workspace(folder, *, git=True, package=None):
    """A Paper Scaffold workspace with a current build of ``paper.pdf``.

    With *git*, the workspace is its own repository through a ``.git`` file,
    as a worktree's is, which marks it without a git checkout behind it.
    *package* is a file outside the workspace the build read, as a Typst
    package is.
    """
    folder = Path(folder)
    for name, text in WORKSPACE_FILES.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text)
    if git:
        (folder / '.git').write_text('gitdir: /nowhere\n')
    (folder / 'paper.pdf').write_bytes(b'%PDF-1.4\n% built\n')
    record_build(folder, package)
    return folder.resolve()


def record_build(folder, package=None):
    """Write the record ``just paper`` leaves: each file the build read and the PDF it wrote.

    A file the build looked for and did not find is recorded as ``None``.
    ``stats.json`` is recorded without its ``pinned`` entry.
    """
    sources = {name: sha((folder / name).read_bytes()) for name in ('paper.typ', 'sections/methods.typ', 'refs.bib')}
    sources['journal.toml'] = None
    stats = json.loads((folder / 'stats.json').read_text())
    stats.pop('pinned', None)
    sources['stats.json'] = sha(json.dumps(stats, sort_keys=True).encode())
    if package:
        sources[str(package)] = sha(Path(package).read_bytes())
    (folder / '.build-state').mkdir(exist_ok=True)
    (folder / '.build-state' / 'paper.pdf.json').write_text(json.dumps({
        'schema_version': 1, 'mode': 'paper', 'sources': sources,
        'dependencies': [str(package)] if package else [], 'manuscript_id': 'paper',
        'output_hash': sha((folder / 'paper.pdf').read_bytes())}, indent=2))


def quietly(call, *args):
    """Run *call* and return its result with what it printed to stdout and to stderr."""
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        result = call(*args)
    return result, stdout.getvalue(), stderr.getvalue()


class WorkspaceReviewTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.workspace = make_workspace(self.root / 'paper')
        self.pdf = str(self.workspace / 'paper.pdf')
        self.run = str(self.root / 'run')

    def tearDown(self):
        self.temporary.cleanup()

    def test_a_workspace_stands_where_the_pdf_does_and_brings_its_code(self):
        workspace, pdf, run = str(self.workspace), self.pdf, self.run
        cases = [
            ([workspace, run], [pdf, run]),
            (['--arm', 'draft-check', workspace, run, '--reviewers', '2'],
             ['--arm', 'draft-check', pdf, run, '--reviewers', '2']),
            # An option's value spelled like the workspace stays as typed.
            (['--prior-issues', workspace, workspace, run], ['--prior-issues', workspace, pdf, run]),
        ]
        for typed, expected in cases:
            argv, note = engine_argv(typed)
            self.assertEqual(argv, [*expected, '--code', workspace], typed)
            self.assertEqual(note, f'paper-workbench review: reviewing {pdf} with the code in {workspace}. '
                                   'Give --no-code to review the paper alone.')
        with contextlib.chdir(self.workspace):
            self.assertEqual(engine_argv(['.', run])[0], [pdf, run, '--code', workspace])

    def test_the_code_is_the_repository_the_workspace_is_in(self):
        repository = self.root / 'repository'
        (repository / '.git').mkdir(parents=True)
        nested = make_workspace(repository / 'manuscript', git=False)
        self.assertEqual(code_root(nested), repository.resolve())
        argv, _ = engine_argv([str(nested), self.run])
        self.assertEqual(argv, [str(nested / 'paper.pdf'), self.run, '--code', str(repository.resolve())])
        self.assertEqual(code_root(self.workspace), self.workspace)

    def test_a_workspace_in_no_repository_is_its_own_code(self):
        bare = make_workspace(self.root / 'bare', git=False)
        if any((folder / '.git').exists() for folder in bare.parents):
            self.skipTest('the temporary folder is inside a repository')
        self.assertEqual(code_root(bare), bare)

    def test_the_author_names_other_code_or_none(self):
        other = self.root / 'other'
        other.mkdir()
        argv, note = engine_argv([str(self.workspace), self.run, '--code', str(other)])
        self.assertEqual(argv, [self.pdf, self.run, '--code', str(other)])
        self.assertIn(f'with the code in {other}.', note)
        for typed in ([str(self.workspace), self.run, '--no-code'], ['--no-c', str(self.workspace), self.run]):
            argv, note = engine_argv(typed)
            self.assertEqual(argv, [self.pdf, self.run], typed)
            self.assertEqual(note, f'paper-workbench review: reviewing {self.pdf} with no code.')
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as stop:
            engine_argv([str(self.workspace), self.run, '--code', str(other), '--no-code'])
        self.assertEqual(stop.exception.code, 2)
        self.assertIn('give --code or --no-code, not both', stderr.getvalue())

    def test_a_pdf_review_passes_through_as_typed(self):
        pdf = self.root / 'manuscript.pdf'
        pdf.write_bytes(b'%PDF-1.4\n')
        typed = [str(pdf), self.run, '--arm', 'draft-check', '--code', str(self.workspace)]
        self.assertEqual(engine_argv(typed), (typed, None))
        self.assertEqual(engine_argv([str(pdf), self.run, '--no-code']), ([str(pdf), self.run], None))

    def test_pinning_stats_is_not_a_change_to_the_source(self):
        stats = json.loads((self.workspace / 'stats.json').read_text())
        (self.workspace / 'stats.json').write_text(json.dumps({'pinned': {'analysis/pipeline.py': 'second'},
                                                               'values': stats['values']}, indent=4))
        self.assertEqual(engine_argv([str(self.workspace), self.run])[0][0], self.pdf)

    def test_a_workspace_the_review_cannot_start_from_is_refused_and_nothing_is_written(self):
        build = 'Build it with `just paper` and run the review again.'
        package = self.root / 'typst-package.typ'
        package.write_text('#let one = 1\n')

        def edit(name, text='\nedited\n'):
            return lambda folder: (folder / name).write_text((folder / name).read_text() + text)

        def stats_value(folder):
            (folder / 'stats.json').write_text(json.dumps({'values': {'fdr': 0.05}, 'pinned': {}}))

        def edit_four(folder):
            for name in ('paper.typ', 'sections/methods.typ', 'refs.bib'):
                edit(name)(folder)
            stats_value(folder)

        def newer_record(folder):
            record = folder / '.build-state' / 'paper.pdf.json'
            record.write_text(json.dumps(dict(json.loads(record.read_text()), schema_version=2)))

        cases = [
            ('missing', lambda folder: (folder / 'paper.pdf').unlink(), 'has no built paper.pdf. ' + build),
            ('no record', lambda folder: (folder / '.build-state' / 'paper.pdf.json').unlink(),
             'cannot tell whether the PDF matches the source. ' + build),
            ('newer record', newer_record, 'cannot tell whether the PDF matches the source. ' + build),
            ('source', edit('sections/methods.typ'),
             'is older than its source: sections/methods.typ changed since it was built. ' + build),
            ('stats', stats_value, 'is older than its source: stats.json changed since it was built.'),
            ('appeared', lambda folder: (folder / 'journal.toml').write_text('style = "one"\n'),
             'is older than its source: journal.toml changed since it was built.'),
            ('package', lambda folder: package.write_text('#let one = 2\n'),
             f'is older than its source: {package} changed since it was built.'),
            ('four', edit_four, 'is older than its source: paper.typ, refs.bib, sections/methods.typ and 1 more '
                                'changed since it was built.'),
            ('replaced', lambda folder: (folder / 'paper.pdf').write_bytes(b'%PDF-1.4\n% other\n'),
             'is not the file its last build wrote, so it cannot be shown to match the source. ' + build),
            ('not a workspace', lambda folder: (folder / 'paper.typ').unlink(),
             'is a folder and not a Paper Scaffold workspace: it has no paper.typ.'),
        ]
        for label, spoil, message in cases:
            package.write_text('#let one = 1\n')
            workspace = make_workspace(self.root / label, package=package)
            spoil(workspace)
            out = self.root / f'run-{label}'
            status, stdout, stderr = quietly(main, ['review', str(workspace), str(out)])
            self.assertEqual((status, stdout), (2, ''), label)
            self.assertTrue(stderr.startswith('paper-workbench review: '), stderr)
            self.assertIn(message, stderr, label)
            self.assertFalse(out.exists(), label)

    def test_a_run_folder_inside_the_code_it_hands_over_is_fine(self):
        # The engine leaves the run folder out of the code it copies, so a run lives in the workspace.
        with contextlib.chdir(self.workspace):
            for typed in (['.', 'reviews/r1'], ['.', 'reviews/r1', '--no-code']):
                expected = [self.pdf, 'reviews/r1'] + (['--code', str(self.workspace)] if len(typed) == 2 else [])
                self.assertEqual(engine_argv(typed)[0], expected, typed)

    def test_an_arm_that_reviews_no_code_is_handed_none_unless_the_author_names_some(self):
        other = self.root / 'other'
        other.mkdir()
        for arm in (name for name, row in review_arms().items() if not row['code']):
            # The author never asked for the code, so the paper is reviewed alone and the line says why.
            argv, note = engine_argv([str(self.workspace), self.run, '--arm', arm])
            self.assertEqual(argv, [self.pdf, self.run, '--arm', arm], arm)
            self.assertEqual(note, f'paper-workbench review: reviewing {self.pdf} with no code, because the {arm} '
                                   'arm reviews no code. The draft-check and full-two-track arms would review it '
                                   f'with the code in {self.workspace}.')
            argv, note = engine_argv([str(self.workspace), self.run, '--arm', arm, '--no-code'])
            self.assertEqual((argv, note), ([self.pdf, self.run, '--arm', arm],
                                            f'paper-workbench review: reviewing {self.pdf} with no code.'))
            # Code the author named passes through, for the engine to refuse.
            argv, _ = engine_argv([str(self.workspace), self.run, '--arm', arm, '--code', str(other)])
            self.assertEqual(argv, [self.pdf, self.run, '--arm', arm, '--code', str(other)], arm)

    def test_review_help_names_the_arms_that_review_code(self):
        help_text = ' '.join(parser().format_help().split())
        self.assertIn('the manuscript PDF, or a Paper Scaffold workspace folder', help_text)
        self.assertIn('A run folder inside it is fine', help_text)
        self.assertIn('Only the draft-check and full-two-track arms review code, so on any other arm a workspace '
                      'is reviewed without it.', help_text)


if __name__ == '__main__':
    unittest.main()
