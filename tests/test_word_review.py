from pathlib import Path
import tempfile
import unittest
import zipfile

try:
    from docx import Document
    from lxml import etree as ET
except ImportError:
    Document = None

from paper_workspace.storage import digest
from paper_workspace.word_review import patch_document, visible, tag, NS


@unittest.skipIf(Document is None, 'Word export requires document dependencies')
class WordReviewTests(unittest.TestCase):
    def fixture(self, folder, texts):
        path = Path(folder) / 'clean.docx'
        doc = Document()
        for text in texts:
            p = doc.add_paragraph()
            p.add_run(text[:5]).bold = True
            p.add_run(text[5:])
        doc.save(path)
        return path

    def paper(self, text):
        return {'blocks': [{'id': 'b1', 'text': text}]}

    def question(self, text):
        return [{'scientific_status': 'open', 'origin_revision': 'original', 'finding': {
            'id': 'q1', 'block_id': 'b1', 'block_sha256': digest(text.encode()),
            'quote': text, 'title': 'Check interpretation', 'comment': 'Please explain the inference.'}}]

    def test_changes_cross_runs_and_roundtrip_both_views(self):
        with tempfile.TemporaryDirectory() as folder:
            before, after = 'This was found to associate with 12 cases.', 'This was found to be associated with 12 cases.'
            source = self.fixture(folder, [after])
            out = Path(folder) / 'review.docx'
            audit = patch_document(source, out, self.paper(before), self.paper(after), [])
            with zipfile.ZipFile(out) as z:
                document = ET.fromstring(z.read('word/document.xml'))
                self.assertEqual(visible(document), after)
                self.assertEqual(visible(document, True), before)
                self.assertTrue(document.findall('.//' + tag('ins')))
                self.assertTrue(document.findall('.//' + tag('del')))
                self.assertTrue(document.findall('.//' + tag('b')))
            self.assertEqual(audit['changed_blocks'], ['b1'])

    def test_comment_relationships_and_exact_text(self):
        with tempfile.TemporaryDirectory() as folder:
            text = 'A < B with 12 samples.'
            source = self.fixture(folder, [text])
            out = Path(folder) / 'review.docx'
            audit = patch_document(source, out, self.paper(text), self.paper(text), self.question(text))
            with zipfile.ZipFile(out) as z:
                document = ET.fromstring(z.read('word/document.xml'))
                self.assertEqual(visible(document), text)
                for name in ('commentRangeStart', 'commentRangeEnd', 'commentReference'):
                    self.assertEqual(document.xpath('.//w:' + name + '/@w:id', namespaces=NS), ['0'])
                comments = ET.fromstring(z.read('word/comments.xml'))
                self.assertIn(text, visible(comments))
                rels = ET.fromstring(z.read('word/_rels/document.xml.rels'))
                self.assertEqual(len([r for r in rels if r.get('Type').endswith('/comments')]), 1)
            self.assertEqual(len(audit['comments']), 1)

    def test_stale_question_survives_as_unlocated(self):
        with tempfile.TemporaryDirectory() as folder:
            old, new = 'An old claim.', 'A new claim.'
            source = self.fixture(folder, [new])
            out = Path(folder) / 'review.docx'
            audit = patch_document(source, out, self.paper(old), self.paper(new), self.question(old))
            self.assertEqual(len(audit['unlocated_questions']), 1)
            with zipfile.ZipFile(out) as z:
                text = visible(ET.fromstring(z.read('word/document.xml')))
                self.assertIn('Unlocated review questions', text)
                self.assertIn(old, text)

    def test_external_source_qualifiers_survive_comment_export(self):
        with tempfile.TemporaryDirectory() as folder:
            text = 'The annotation establishes a mechanism.'
            source = self.fixture(folder, [text])
            ledger = self.question(text)
            finding = ledger[0]['finding']
            finding['source_evidence'] = [{'evidence_id': 'source-test', 'quote': 'Curated annotation'}]
            finding['external_sources'] = [{'evidence_id': 'source-test', 'source_url': 'https://example.org/record',
                'record_version': '12', 'retrieved_at': '2026-09-25',
                'limitation': 'Annotation alone does not establish the mechanism.'}]
            finding['external_sources'] *= 2
            finding['source_evidence'].append({'evidence_id': 'source-test', 'quote': 'Second exact excerpt'})
            out = Path(folder)/'review.docx'
            patch_document(source, out, self.paper(text), self.paper(text), ledger)
            with zipfile.ZipFile(out) as archive:
                comments = visible(ET.fromstring(archive.read('word/comments.xml')))
                for expected in ('https://example.org/record', 'Version: 12', 'Curated annotation',
                                 'Annotation alone does not establish the mechanism.'):
                    self.assertIn(expected, comments)
                self.assertEqual(comments.count('https://example.org/record'), 1)
                self.assertEqual(comments.count('Curated annotation'), 1)
                self.assertEqual(comments.count('Second exact excerpt'), 1)

    def test_ambiguous_changed_paragraph_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.fixture(folder, ['New text', 'New text'])
            out = Path(folder) / 'review.docx'
            with self.assertRaisesRegex(ValueError, 'one exact'):
                patch_document(source, out, self.paper('Old text'), self.paper('New text'), [])
            self.assertFalse(out.exists())

    def test_existing_annotations_fail_without_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            text = 'A claim.'
            source = self.fixture(folder, [text])
            annotated = Path(folder) / 'annotated.docx'
            patch_document(source, annotated, self.paper(text), self.paper(text), self.question(text))
            with self.assertRaisesRegex(ValueError, 'existing annotations'):
                patch_document(annotated, Path(folder) / 'second.docx', self.paper(text), self.paper(text), [])

    def test_unsupported_inline_markup_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.fixture(folder, ['New text'])
            doc = Document(source)
            node = ET.SubElement(doc.paragraphs[0]._p, tag('hyperlink'))
            doc.save(source)
            with self.assertRaisesRegex(ValueError, 'unsupported Word markup'):
                patch_document(source, Path(folder) / 'review.docx', self.paper('Old text'), self.paper('New text'), [])


if __name__ == '__main__':
    unittest.main()
