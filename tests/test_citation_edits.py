"""Citation-aware revisions preserve source identity and encoded literal text."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from peerreviewagents import verify_workspace
from peerreviewagents.workspace import normalize_review

import manuscripts
from manuscripts import line_of
from paper_workspace.revisions import create_revision, head, snapshot
from paper_workspace.scaffold_import import import_scaffold, scaffold_spans, span_at
from paper_workspace.scaffold_port import port_workspace

RESULT = 'We used 12 samples [1,2] in order to assess the "signal". We did not infer causality.'


class CitationEdits(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def port(self):
        source = self.root / 'input'
        cited = {'citations': ['r1', 'r2'], 'page': 1, 'bbox': list(manuscripts.BOX)}
        manuscripts.build(source, [], title='Fixture', extra=[
            {'kind': 'heading', 'level': 1, 'text': 'Abstract', 'section': 'Abstract'},
            {'kind': 'paragraph', 'text': 'We may observe an association [1].', 'section': 'Abstract', **cited},
            {'kind': 'heading', 'level': 1, 'text': 'Results', 'section': 'Results'},
            {'kind': 'paragraph', 'text': RESULT, 'section': 'Results', **cited}])
        output = self.root / 'workspace'
        port_workspace(source, output)
        return output, verify_workspace(output)

    def source_of(self, root, paper, line):
        """The source file that holds ``line`` and its spans entry."""
        entry = span_at(scaffold_spans(root, paper), 'paper.md', line)
        return Path(root) / 'scaffold' / entry['file'], entry

    def apply(self, root, paper, line, replacements, rid='edit'):
        review = normalize_review(paper, {'findings': [
            {'kind': 'edit', 'category': 'copyedit', 'document': 'paper.md', 'line': line,
             'quote': quote, 'replacement': replacement} for quote, replacement in replacements]}, rid)
        decisions = {'paper_id': paper.paper_id, 'review_id': rid,
                     'items': {finding['id']: 'accepted' for finding in review['findings']}}
        return create_revision(root, review, decisions, rid, head(root), build=False)

    def test_multiple_edits_decode_quotes_and_reimport_current_text(self):
        root, paper = self.port()
        line = line_of(paper, 'in order to')
        file, _ = self.source_of(root, paper, line)
        before = file.read_bytes()
        self.apply(root, paper, line, [('in order to', 'to'), ('the "signal"', 'the "measured signal"')])
        path, revised = snapshot(root, 'edit')
        current = line_of(revised, 'to assess')
        self.assertIn('[1,2] to assess the "measured signal"', revised.line_text(current))
        self.assertIn('not infer causality', revised.line_text(current))
        self.assertEqual(revised.piece_at(current)['citations'], paper.piece_at(line)['citations'])
        self.assertEqual(file.read_bytes(), before)
        self.apply(root, revised, current, [('measured signal', 'observed signal')], rid='second')
        self.assertIn('observed signal', snapshot(root, 'second')[1].line_text(current))

    def test_abstract_reimports_edited_literal(self):
        root, paper = self.port()
        self.apply(root, paper, line_of(paper, 'We may observe'), [('We may observe', 'We may detect')])
        path, updated = snapshot(root, 'edit')
        line = line_of(updated, 'We may detect')
        self.assertEqual(updated.line_text(line), 'We may detect an association [1].')
        file, entry = self.source_of(path, updated, line)
        self.assertEqual((file.name, entry['encoding']), ('config.typ', 'json-string'))

    def test_reimport_mismatch_never_promotes_a_revision(self):
        root, paper = self.port()

        def wrong_projection(project, *args, **kwargs):
            # The written source reads back as other text than the edit the author approved.
            for file in Path(project, 'blocks').glob('*.typ'):
                file.write_text(file.read_text().replace('causality', 'causation'))
            return import_scaffold(project, *args, **kwargs)

        with patch('paper_workspace.revisions.import_scaffold', side_effect=wrong_projection):
            with self.assertRaisesRegex(ValueError, 'approved text projection'):
                self.apply(root, paper, line_of(paper, 'in order to'), [('in order to', 'to')])
        self.assertEqual(head(root)['version'], 0)
        self.assertFalse((root / 'revisions/edit').exists())

    def test_partial_citation_edit_and_negation_removal_fail(self):
        root, paper = self.port()
        line = line_of(paper, 'in order to')
        for quote, replacement in [('1,2', '2,1'), ('[1,2]', '(1,2)'), ('not infer', 'infer')]:
            with self.subTest(quote=quote), self.assertRaisesRegex(ValueError, 'source-aware'):
                self.apply(root, paper, line, [(quote, replacement)])
            self.assertEqual(head(root)['version'], 0)

    def test_code_characters_remain_literal_inside_json_string(self):
        root, paper = self.port()
        self.apply(root, paper, line_of(paper, 'in order to'),
                   [('the "signal"', 'the "signal" (#include "missing.typ")')])
        path, updated = snapshot(root, 'edit')
        line = line_of(updated, 'missing.typ')
        file, _ = self.source_of(path, updated, line)
        self.assertIn('\\"missing.typ\\"', file.read_text())
        self.assertIn('#include "missing.typ"', updated.line_text(line))
        self.assertFalse((path / 'scaffold/missing.typ').exists())

    def test_native_citation_edits_preserve_keys_and_block_markup(self):
        project = self.root / 'project'
        project.mkdir()
        (project / 'paper.typ').write_text('// >>> BODY START\nIn order to assess @doe2024 and @roe2023, we used 12 samples.\n// <<< BODY END\n')
        root = self.root / 'workspace'
        import_scaffold(project, root)
        paper = verify_workspace(root)
        line = line_of(paper, 'In order to assess')
        self.assertTrue(self.source_of(root, paper, line)[1]['editable'])
        for quote, replacement in [('doe2024', 'zoe2024'), ('@doe2024 and @roe2023', '@roe2023 and @doe2024'),
                                   ('In order to', '#include "evil.typ"')]:
            with self.subTest(quote=quote), self.assertRaisesRegex(ValueError, 'source-aware'):
                self.apply(root, paper, line, [(quote, replacement)])
        text = paper.line_text(line)
        replacement = text.replace('In order to', 'To')
        self.apply(root, paper, line, [(text, replacement)])
        self.assertEqual(snapshot(root, 'edit')[1].line_text(line), replacement)


if __name__ == '__main__':
    unittest.main()
