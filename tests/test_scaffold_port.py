"""A port preserves scientific text while exposing only safe source edits."""
from pathlib import Path
import tempfile
import unittest

from peerreviewagents import verify_workspace
from peerreviewagents.workspace import read_json

import manuscripts
from manuscripts import BOX, line_of
from paper_workspace.scaffold_import import scaffold_spans, span_at
from paper_workspace.scaffold_port import port_workspace

PDF = b'Original PDF fixture bytes'
LITERAL = 'A citation [1] and #include "bad.typ" are literal text.'
TABLE = [['Group', 'Count'], ['Control', '12']]


def source_manuscript(folder, results=(), ai_model=''):
    """A PDF import's workspace: an abstract, results that cite, a reference list and a supplement table.

    ``results`` is further pieces at the end of the results, such as the pieces a model read, and
    ``ai_model`` is the model that wrote them.
    """
    folder = Path(folder)
    (folder / 'original').mkdir(parents=True)
    # The engine digests the folder as it stands, so the PDF is written first and the manifest covers it.
    (folder / 'original' / 'original.pdf').write_bytes(PDF)
    placed = {'page': 1, 'bbox': list(BOX)}
    pieces = [
        {'kind': 'heading', 'level': 1, 'text': 'Abstract', 'section': 'Abstract'},
        {'kind': 'paragraph', 'text': 'An association may exist.', 'section': 'Abstract', **placed},
        {'kind': 'heading', 'level': 1, 'text': 'Results', 'section': 'Results'},
        {'kind': 'paragraph', 'text': 'There were 12 samples.', 'section': 'Results', **placed},
        {'kind': 'paragraph', 'text': LITERAL, 'section': 'Results', 'citations': ['ref1'], **placed},
        *results,
        {'kind': 'heading', 'level': 1, 'text': 'References', 'section': 'References'},
        {'kind': 'reference', 'text': '1 Reference text', 'section': 'References'},
    ]
    supplement = [{'kind': 'table', 'text': 'Group Count Control 12', 'table': TABLE, 'section': 'Supplement S1'}]
    return manuscripts.build(folder, [], title='Real source test', extra=pieces,
                             documents={'S1.md': supplement},
                             references=[{'id': 'ref1', 'label': '1', 'raw': 'Reference text'}],
                             ai_model=ai_model)


class ScaffoldPort(unittest.TestCase):
    def test_literal_markup_stays_readable_and_encoded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'original'
            base = source_manuscript(source)
            output = root / 'ported'
            port_workspace(source, output)
            ported = verify_workspace(output)
            self.assertEqual(ported.document_names(), ['paper.md', 'S1.md'])
            self.assertEqual(ported.documents, base.documents)
            spans = scaffold_spans(output, ported)

            def entry(text, document='paper.md'):
                return span_at(spans, document, line_of(ported, text, document))

            self.assertEqual(ported.line_text(line_of(ported, 'literal text')), LITERAL)
            self.assertEqual((entry(LITERAL)['editable'], entry(LITERAL)['encoding']), (True, 'json-string'))
            # The abstract is declared in config.typ as a literal, so it is edited there.
            abstract = entry('An association')
            self.assertEqual((abstract['file'], abstract['encoding']), ('config.typ', 'json-string'))
            plain = entry('There were 12 samples.')
            self.assertTrue(plain['editable'])
            self.assertNotIn('encoding', plain)
            self.assertFalse(entry('1 Reference text')['editable'])
            self.assertFalse(entry('| Group', 'S1.md')['editable'])
            cited = ported.piece_at(line_of(ported, 'literal text'))
            self.assertEqual((cited['citations'], cited['page'], cited['bbox'], cited['page_mapping']),
                             (['ref1'], 1, BOX, 'original_pdf'))
            table = ported.pieces('S1.md')[0]
            self.assertEqual((table['kind'], table['section'], table['document']), ('table', 'Supplement S1', 'S1.md'))
            self.assertEqual(read_json(output / 'references.json'), read_json(source / 'references.json'))
            self.assertEqual((output / 'original' / 'original.pdf').read_bytes(), PDF)
            self.assertGreater(ported.manifest['statistics']['reference_words'], 0)
            with self.assertRaisesRegex(ValueError, 'already exists'):
                port_workspace(source, output)

    def test_the_pieces_a_model_read_keep_whose_they_are_and_stay_out_of_the_source(self):
        # An equation the model read again keeps the converter's reading, and a figure description
        # is the model's own words. The port keeps both as the engine wrote them, and the description
        # is never written into the Typst source the manuscript is built from. The port writes those
        # pieces again, so the ported manifest names the same model, and says no page was read in the port.
        # A part of a re-read keeps which part it is, and debris folded into a piece stays under it, so
        # the port keeps original whole and the debris never reaches the Typst source.
        equation ={'kind': 'equation', 'latex': 'x = 1', 'text': 'x = 1', 'section': 'Results', 'page': 1,
                    'bbox': list(BOX), 'source': 'ai-reconstructed',
                    'original': {'kind': 'paragraph', 'text': 'x - 1 and more', 'piece': 'p0003', 'part': 1, 'of': 2}}
        description = {'kind': 'figure-description', 'text': 'A bar chart of two groups.', 'section': 'Results',
                       'page': 1, 'source': 'ai',
                       'original': {'absorbed': [{'piece': 'p0009', 'kind': 'paragraph', 'text': '120 100 80'}]}}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            base = source_manuscript(root / 'original', results=[equation, description],
                                     ai_model='claude-sonnet-5-5')
            output = root / 'ported'
            port_workspace(root / 'original', output)
            ported = verify_workspace(output)
            self.assertEqual(ported.documents, base.documents)
            read = ported.manifest['ai_read']
            self.assertEqual((read['read'], read['ai_model'], read['ai_pieces'], read['lost_pages']),
                             (False, 'claude-sonnet-5-5', 2, []))
            read = [(row['kind'], row['source'], row.get('original')) for row in ported.rows
                    if row['source'] != 'text']
            self.assertEqual(read, [('equation', 'ai-reconstructed', equation['original']),
                                    ('figure-description', 'ai', description['original'])])
            spans = scaffold_spans(output, ported)
            entry = span_at(spans, 'paper.md', line_of(ported, 'Figure description: A bar chart'))
            self.assertEqual((entry['file'], entry['editable']), (None, False))
            typst = ''.join(path.read_text() for path in (output / 'scaffold').rglob('*.typ'))
            self.assertNotIn('A bar chart', typst)
            self.assertNotIn('120 100 80', typst)


if __name__ == '__main__':
    unittest.main()
