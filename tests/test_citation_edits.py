"""Citation-aware revisions preserve source identity and encoded literal text."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from paper_workspace.annotations import normalize_review
from paper_workspace.revisions import create_revision, head, snapshot
from paper_workspace.scaffold_import import import_scaffold
from paper_workspace.scaffold_port import port_workspace
from paper_workspace.storage import digest, write


class CitationEdits(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def port(self):
        source = self.root / 'input'
        source.mkdir()
        texts = [('a', 'Abstract', 'We may observe an association [1].'),
                 ('b', 'Results', 'We used 12 samples [1,2] in order to assess the "signal". We did not infer causality.')]
        blocks = [{'id': bid, 'section': section, 'kind': 'paragraph', 'text': text,
                   'sha256': digest(text), 'page': 1, 'citations': ['r1', 'r2']}
                  for bid, section, text in texts]
        write(source / 'paper.json', {'id': 'input', 'title': 'Fixture', 'source_sha256': 'input',
            'blocks': blocks, 'references': [], 'statistics': {'pdf_pages': 1}})
        write(source / 'manifest.json', {'files': {'paper.json': digest((source / 'paper.json').read_bytes())}})
        output = self.root / 'workspace'
        paper = port_workspace(source, output)
        return output, paper

    def apply(self, root, paper, block, replacements, rid='edit'):
        review = normalize_review(paper, {'findings': [
            {'kind': 'edit', 'category': 'copyedit', 'block_id': block['id'],
             'quote': quote, 'replacement': replacement} for quote, replacement in replacements]}, rid)
        decisions = {'paper_id': paper['id'], 'review_id': rid,
                     'items': {finding['id']: 'accepted' for finding in review['findings']}}
        return create_revision(root, review, decisions, rid, head(root), build=False)

    def test_multiple_edits_decode_quotes_and_reimport_current_text(self):
        root, paper = self.port()
        block = paper['blocks'][1]
        before = (root / 'scaffold' / block['source_id']).read_bytes()
        self.apply(root, paper, block, [('in order to', 'to'), ('the "signal"', 'the "measured signal"')])
        path, revised = snapshot(root, 'edit')
        current = next(b for b in revised['blocks'] if b['origin_block_id'] == 'b')
        self.assertIn('[1,2] to assess the "measured signal"', current['text'])
        self.assertIn('not infer causality', current['text'])
        self.assertEqual(current['citations'], block['citations'])
        self.assertEqual((root / 'scaffold' / block['source_id']).read_bytes(), before)
        self.apply(root, revised, current, [('measured signal', 'observed signal')], rid='second')
        self.assertIn('observed signal', snapshot(root, 'second')[1]['blocks'][1]['text'])

    def test_abstract_reimports_edited_literal(self):
        root, paper = self.port()
        self.apply(root, paper, paper['blocks'][0], [('We may observe', 'We may detect')])
        updated = snapshot(root, 'edit')[1]['blocks'][0]
        self.assertEqual(updated['text'], 'We may detect an association [1].')
        self.assertEqual(updated['source_span']['encoding'], 'json-string')

    def test_reimport_mismatch_never_promotes_a_revision(self):
        root, paper = self.port()
        def wrong_projection(*args, **kwargs):
            result = import_scaffold(*args, **kwargs)
            result['blocks'][0]['text'] = 'Unexpected changed text.'
            return result
        with patch('paper_workspace.scaffold_import.import_scaffold', side_effect=wrong_projection):
            with self.assertRaisesRegex(ValueError, 'approved text projection'):
                self.apply(root, paper, paper['blocks'][1], [('in order to', 'to')])
        self.assertEqual(head(root)['version'], 0)
        self.assertFalse((root / 'revisions/edit').exists())

    def test_partial_citation_edit_and_negation_removal_fail(self):
        root, paper = self.port()
        block = paper['blocks'][1]
        for quote, replacement in [('1,2', '2,1'), ('[1,2]', '(1,2)'), ('not infer', 'infer')]:
            with self.subTest(quote=quote), self.assertRaises(ValueError):
                self.apply(root, paper, block, [(quote, replacement)])
            self.assertEqual(head(root)['version'], 0)

    def test_code_characters_remain_literal_inside_json_string(self):
        root, paper = self.port()
        self.apply(root, paper, paper['blocks'][1], [('the "signal"', 'the "signal" (#include "missing.typ")')])
        path, updated = snapshot(root, 'edit')
        block = updated['blocks'][1]
        source = (path / 'scaffold' / block['source_id']).read_text()
        self.assertIn('\\"missing.typ\\"', source)
        self.assertIn('#include "missing.typ"', block['text'])
        self.assertFalse((path / 'scaffold/missing.typ').exists())

    def test_native_citation_edits_preserve_keys_and_block_markup(self):
        project = self.root / 'project'
        project.mkdir()
        (project / 'paper.typ').write_text('// >>> BODY START\nIn order to assess @doe2024 and @roe2023, we used 12 samples.\n// <<< BODY END\n')
        root = self.root / 'workspace'
        paper = import_scaffold(project, root)
        block = paper['blocks'][0]
        self.assertTrue(block['editable'])
        for quote, replacement in [('doe2024', 'zoe2024'), ('@doe2024 and @roe2023', '@roe2023 and @doe2024'),
                                   ('In order to', '#include "evil.typ"')]:
            with self.subTest(quote=quote), self.assertRaises(ValueError):
                self.apply(root, paper, block, [(quote, replacement)])
        replacement = block['text'].replace('In order to', 'To')
        self.apply(root, paper, block, [(block['text'], replacement)])
        self.assertEqual(snapshot(root, 'edit')[1]['blocks'][0]['text'], replacement)


if __name__ == '__main__':
    unittest.main()
