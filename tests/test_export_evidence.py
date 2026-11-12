import json
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader, PdfWriter
from PIL import Image

from peerreviewagents.engine.storage import digest

from paper_workspace.export_evidence import extract_main_figures, preserve_source_evidence


class ExportEvidence(unittest.TestCase):
    def test_copies_assets_and_exact_figure_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source'
            source.mkdir()
            writer = PdfWriter()
            for width in (200, 300, 400):
                writer.add_blank_page(width=width, height=500)
            with (source / 'original.pdf').open('wb') as stream:
                writer.write(stream)
            (source / 'original.xml').write_text('<article/>')
            supplements = source / 'supplements'
            supplements.mkdir()
            (supplements / 'S1_Fig.png').write_bytes(b'original image')
            paper = {'blocks': [
                {'kind': 'caption', 'text': 'Fig 1 A result', 'page': 2},
                {'kind': 'caption', 'text': 'S1 Fig Another result', 'page': 3},
            ]}

            destination = root / 'evidence'
            result, main_figures = preserve_source_evidence(source, destination, paper)

            self.assertEqual(result['main_figure_pages'], [2])
            self.assertEqual(main_figures, [])
            self.assertEqual(len(PdfReader(destination / 'main-figure-source-pages.pdf').pages), 1)
            self.assertEqual(digest((destination / 'supplements/S1_Fig.png').read_bytes()),
                             digest(b'original image'))
            stored = json.loads((destination / 'manifest.json').read_text())
            self.assertEqual(stored['files']['supplements/S1_Fig.png'], digest(b'original image'))

    def test_extracts_only_one_large_rgb_jpeg_for_one_caption(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = root / 'original.pdf'
            Image.new('RGB', (1200, 1100), (20, 40, 60)).save(original, 'PDF')
            paper = {'blocks': [{
                'id': 'caption-1', 'origin_block_id': 'source-caption-1',
                'kind': 'caption', 'page': 1, 'text': 'Fig 1 A verified result.'
            }]}
            extracted, fallbacks = extract_main_figures(original, root / 'figures', paper)

            self.assertEqual(fallbacks, [])
            self.assertEqual(len(extracted), 1)
            self.assertEqual(extracted[0]['origin_block_id'], 'source-caption-1')
            self.assertEqual(extracted[0]['mode'], 'RGB')
            self.assertGreaterEqual(extracted[0]['width'], 1000)
            self.assertEqual(digest(Path(extracted[0]['path']).read_bytes()), extracted[0]['sha256'])

            ambiguous = {'blocks': paper['blocks'] + [{
                'id': 'caption-2', 'kind': 'caption', 'page': 1, 'text': 'Fig 2 Another result.'
            }]}
            extracted, fallbacks = extract_main_figures(original, root / 'ambiguous', ambiguous)
            self.assertEqual(extracted, [])
            self.assertEqual(fallbacks[0]['reason'], 'main_caption_count')


if __name__ == '__main__':
    unittest.main()
