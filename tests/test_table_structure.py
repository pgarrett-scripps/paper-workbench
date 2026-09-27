from pathlib import Path
import tempfile
import unittest
import zipfile

from paper_workspace.table_structure import word_tables, enrich_tables


class TableStructure(unittest.TestCase):
    def test_exact_merges_and_text_match_without_mutating_source(self):
        xml = '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl>
        <w:tblGrid><w:gridCol/><w:gridCol/></w:tblGrid>
        <w:tr><w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr><w:p><w:r><w:t>Heading</w:t></w:r></w:p></w:tc></w:tr>
        <w:tr><w:tc><w:tcPr><w:vMerge w:val="restart"/></w:tcPr><w:p><w:r><w:t>Group</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>12</w:t></w:r></w:p></w:tc></w:tr>
        <w:tr><w:tc><w:tcPr><w:vMerge/></w:tcPr><w:p/></w:tc><w:tc><w:p><w:r><w:t>14</w:t></w:r></w:p></w:tc></w:tr>
        </w:tbl></w:body></w:document>'''
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'source/supplements/S1.docx'
            path.parent.mkdir(parents=True)
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('word/document.xml', xml)
            table = word_tables(path)[0]
            self.assertEqual(table['structure']['rows'][0][0]['colspan'], 2)
            self.assertEqual(table['structure']['rows'][1][0]['rowspan'], 2)
            self.assertEqual(len(table['structure']['rows'][2]), 1)
            paper = {'blocks': [{'kind': 'table', 'text': table['text'], 'document': 'S1.docx'}]}
            updated = enrich_tables(root, paper)
            self.assertNotIn('table_structure', paper['blocks'][0])
            self.assertIn('table_structure', updated['blocks'][0])
            paper['blocks'][0]['text'] += ' changed'
            self.assertNotIn('table_structure', enrich_tables(root, paper)['blocks'][0])


if __name__ == '__main__':
    unittest.main()
