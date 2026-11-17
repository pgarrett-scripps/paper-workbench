from pathlib import Path
import tempfile
import unittest
import zipfile

try:
    from docx import Document
    from lxml import etree as ET
except ImportError:
    Document = None

from peerreviewagents import verify_workspace
from peerreviewagents.workspace import normalize_review

from manuscripts import line_of
from paper_workspace.scaffold_import import import_scaffold
from paper_workspace.word_review import patch_document, visible, tag, NS


@unittest.skipIf(Document is None, 'Word export requires document dependencies')
class WordReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def fixture(self, texts):
        path = self.folder / 'clean.docx'
        doc = Document()
        for text in texts:
            p = doc.add_paragraph()
            p.add_run(text[:5]).bold = True
            p.add_run(text[5:])
        doc.save(path)
        return path

    def draft(self, text):
        """A Scaffold draft of one paragraph, imported and read back as the engine reads it."""
        name = f'draft-{len(list(self.folder.glob("draft-*")))}'
        project = self.folder / f'{name}-project'
        project.mkdir()
        (project / 'paper.typ').write_text('// >>> BODY START\n' + text + '\n// <<< BODY END\n')
        import_scaffold(project, self.folder / name, title='Fixture')
        return verify_workspace(self.folder / name)

    def question(self, base, text):
        """An open question raised on ``base`` that quotes ``text``, as the ledger keeps it."""
        line = line_of(base, text)
        review = normalize_review(base, {'findings': [
            {'kind': 'question', 'category': 'scientific', 'line': line, 'quote': text, 'evidence_lines': [line],
             'title': 'Check interpretation', 'comment': 'Please explain the inference.'}]}, 'q')
        return [{'scientific_status': 'open', 'origin_revision': 'original', 'finding': review['findings'][0]}]

    def patch(self, source, out, parent, current, ledger):
        return patch_document(source, out, parent, current, ledger, lambda revision: {'original': parent}[revision])

    def test_changes_cross_runs_and_roundtrip_both_views(self):
        before, after = 'This was found to associate with 12 cases.', 'This was found to be associated with 12 cases.'
        parent, current = self.draft(before), self.draft(after)
        source = self.fixture([after])
        out = self.folder / 'review.docx'
        audit = self.patch(source, out, parent, current, [])
        with zipfile.ZipFile(out) as z:
            document = ET.fromstring(z.read('word/document.xml'))
            self.assertEqual(visible(document), after)
            self.assertEqual(visible(document, True), before)
            self.assertTrue(document.findall('.//' + tag('ins')))
            self.assertTrue(document.findall('.//' + tag('del')))
            self.assertTrue(document.findall('.//' + tag('b')))
        line = line_of(current, after)
        self.assertEqual(audit['changed_pieces'], [{'document': 'paper.md', 'lines': [line, line]}])

    def test_comment_relationships_and_exact_text(self):
        text = 'A < B with 12 samples.'
        paper = self.draft(text)
        source = self.fixture([text])
        out = self.folder / 'review.docx'
        audit = self.patch(source, out, paper, paper, self.question(paper, text))
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
        line = line_of(paper, text)
        self.assertEqual((audit['comments'][0]['document'], audit['comments'][0]['lines']), ('paper.md', [line, line]))

    def test_stale_question_survives_as_unlocated(self):
        old, new = 'An old claim.', 'A new claim.'
        parent, current = self.draft(old), self.draft(new)
        source = self.fixture([new])
        out = self.folder / 'review.docx'
        audit = self.patch(source, out, parent, current, self.question(parent, old))
        self.assertEqual(len(audit['unlocated_questions']), 1)
        self.assertEqual(audit['unlocated_questions'][0]['reason'], 'The originating passage changed or is unavailable')
        with zipfile.ZipFile(out) as z:
            text = visible(ET.fromstring(z.read('word/document.xml')))
            self.assertIn('Unlocated review questions', text)
            self.assertIn(old, text)

    def test_external_source_qualifiers_survive_comment_export(self):
        text = 'The annotation establishes a mechanism.'
        paper = self.draft(text)
        source = self.fixture([text])
        ledger = self.question(paper, text)
        finding = ledger[0]['finding']
        finding['source_evidence'] = [{'evidence_id': 'source-test', 'quote': 'Curated annotation'}]
        finding['external_sources'] = [{'evidence_id': 'source-test', 'source_url': 'https://example.org/record',
            'record_version': '12', 'retrieved_at': '2026-09-25',
            'limitation': 'Annotation alone does not establish the mechanism.'}]
        finding['external_sources'] *= 2
        finding['source_evidence'].append({'evidence_id': 'source-test', 'quote': 'Second exact excerpt'})
        out = self.folder / 'review.docx'
        self.patch(source, out, paper, paper, ledger)
        with zipfile.ZipFile(out) as archive:
            comments = visible(ET.fromstring(archive.read('word/comments.xml')))
            for expected in ('https://example.org/record', 'Version: 12', 'Curated annotation',
                             'Annotation alone does not establish the mechanism.'):
                self.assertIn(expected, comments)
            self.assertEqual(comments.count('https://example.org/record'), 1)
            self.assertEqual(comments.count('Curated annotation'), 1)
            self.assertEqual(comments.count('Second exact excerpt'), 1)

    def test_a_code_checked_member_names_its_file_and_lines_in_the_comment(self):
        from test_run_view import CODE_EVIDENCE
        text = 'Peptides were filtered at a false discovery rate of one percent.'
        paper = self.draft(text)
        ledger = self.question(paper, text)
        # A run's card is one issue, and only its code-checked member carries code_evidence.
        ledger[0]['finding']['members'] = [{'basis': 'judgement'}, {'basis': 'code-checked', 'code_evidence': CODE_EVIDENCE},
                                           {'basis': 'code-checked', 'code_evidence': {**CODE_EVIDENCE, 'end_line': 4}}]
        out = self.folder / 'review.docx'
        self.patch(self.fixture([text]), out, paper, paper, ledger)
        with zipfile.ZipFile(out) as archive:
            comments = visible(ET.fromstring(archive.read('word/comments.xml')))
        for expected in ("Code checked: analysis/pipeline.py, line 2 of the run's code snapshot",
                         "Code checked: analysis/pipeline.py, lines 2 to 4 of the run's code snapshot",
                         'FDR_THRESHOLD = 0.05'):
            self.assertIn(expected, comments)

    def test_ambiguous_changed_paragraph_fails(self):
        parent, current = self.draft('Old text'), self.draft('New text')
        source = self.fixture(['New text', 'New text'])
        out = self.folder / 'review.docx'
        with self.assertRaisesRegex(ValueError, 'one exact'):
            self.patch(source, out, parent, current, [])
        self.assertFalse(out.exists())

    def test_existing_annotations_fail_without_overwrite(self):
        text = 'A claim.'
        paper = self.draft(text)
        source = self.fixture([text])
        annotated = self.folder / 'annotated.docx'
        self.patch(source, annotated, paper, paper, self.question(paper, text))
        with self.assertRaisesRegex(ValueError, 'existing annotations'):
            self.patch(annotated, self.folder / 'second.docx', paper, paper, [])

    def test_unsupported_inline_markup_fails(self):
        parent, current = self.draft('Old text'), self.draft('New text')
        source = self.fixture(['New text'])
        doc = Document(source)
        ET.SubElement(doc.paragraphs[0]._p, tag('hyperlink'))
        doc.save(source)
        with self.assertRaisesRegex(ValueError, 'unsupported Word markup'):
            self.patch(source, self.folder / 'review.docx', parent, current, [])


if __name__ == '__main__':
    unittest.main()
