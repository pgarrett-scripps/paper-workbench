import io
from pathlib import Path
import tempfile
import unittest
import zipfile

from peerreviewagents import verify_workspace

import manuscripts
from paper_workspace.scaffold_import import scaffold_spans
from paper_workspace.scaffold_port import port_workspace
from paper_workspace.table_structure import word_tables

XML = '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl>
<w:tblGrid><w:gridCol/><w:gridCol/></w:tblGrid>
<w:tr><w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr><w:p><w:r><w:t>Heading</w:t></w:r></w:p></w:tc></w:tr>
<w:tr><w:tc><w:tcPr><w:vMerge w:val="restart"/></w:tcPr><w:p><w:r><w:t>Group</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>12</w:t></w:r></w:p></w:tc></w:tr>
<w:tr><w:tc><w:tcPr><w:vMerge/></w:tcPr><w:p/></w:tc><w:tc><w:p><w:r><w:t>14</w:t></w:r></w:p></w:tc></w:tr>
</w:tbl></w:body></w:document>'''
SUPPLEMENT = {'id': 'S1', 'label': 'S1.docx', 'kind': 'supplement', 'path': 'supplements/S1.docx',
              'preview': None, 'available': 'file', 'document': 'S1.md'}


def word_file():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr('word/document.xml', XML)
    return stream.getvalue()


class TableStructure(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def ported(self, cells, name):
        """A PDF import whose supplement S1.md was read from S1.docx, ported, with the table's spans entry."""
        source = self.root / name
        (source / 'supplements').mkdir(parents=True)
        (source / 'supplements' / 'S1.docx').write_bytes(word_file())
        table = {'kind': 'table', 'text': ' '.join(' '.join(row) for row in cells), 'table': cells,
                 'section': 'Supplement S1'}
        manuscripts.build(source, ['Main text.'], documents={'S1.md': [table]}, assets=[SUPPLEMENT])
        output = self.root / f'{name}-ported'
        port_workspace(source, output)
        return output, scaffold_spans(output, verify_workspace(output))['S1.md'][0]

    def test_word_merges_are_read_exactly(self):
        path = self.root / 'S1.docx'
        path.write_bytes(word_file())
        table = word_tables(path)[0]
        self.assertEqual(table['structure']['rows'][0][0]['colspan'], 2)
        self.assertEqual(table['structure']['rows'][1][0]['rowspan'], 2)
        self.assertEqual(len(table['structure']['rows'][2]), 1)

    def test_a_ported_table_takes_the_geometry_of_its_one_matching_word_table(self):
        output, entry = self.ported([['Heading', ''], ['Group', '12'], ['', '14']], 'matching')
        path = output / 'scaffold/source/supplements/S1.docx'
        self.assertEqual(entry['table_structure'], word_tables(path)[0]['structure'])
        self.assertEqual(entry['table_structure_source'], 'source/supplements/S1.docx')
        self.assertEqual(path.read_bytes(), word_file())

    def test_a_table_whose_text_differs_takes_no_geometry(self):
        _, entry = self.ported([['Heading', ''], ['Group', '12'], ['', '15']], 'changed')
        self.assertNotIn('table_structure', entry)


if __name__ == '__main__':
    unittest.main()
