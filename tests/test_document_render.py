from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from docx import Document
except ImportError:
    Document = None

from paper_workspace.document_render import remove_flattened_tables, render_word_pdf


class DocumentRender(unittest.TestCase):
    @unittest.skipIf(Document is None, 'Word export requires python-docx')
    def test_remove_only_exact_duplicates_of_embedded_tables(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'paper.docx'
            doc = Document()
            doc.add_paragraph('Group\tCount\nControl\t12')
            doc.add_paragraph('Other\t14')
            doc.add_table(rows=1, cols=1).cell(0, 0).text = 'Control 12'
            doc.save(path)
            blocks = [{'kind': 'table', 'text': 'Group\tCount\nControl\t12'},
                      {'kind': 'table', 'text': 'Other\t14'}]
            count = remove_flattened_tables(path, blocks, ['Group\tCount\nControl\t12'])
            self.assertEqual(count, 1)
            current = Document(path)
            self.assertEqual([p.text for p in current.paragraphs], ['Other\t14'])
            self.assertEqual(len(current.tables), 1)

    def test_missing_renderer_does_not_publish_output(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'paper.pdf'
            with patch('paper_workspace.document_render.shutil.which', return_value=None):
                with self.assertRaisesRegex(ValueError, 'requires local LibreOffice'):
                    render_word_pdf(Path(folder) / 'paper.docx', output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
