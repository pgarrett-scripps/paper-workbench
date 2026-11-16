import io
import json
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader, PdfWriter
from PIL import Image

from peerreviewagents import verify_workspace
from peerreviewagents.workspace import digest

import manuscripts
from paper_workspace.export_evidence import extract_main_figures, preserve_source_evidence
from paper_workspace.scaffold_export import export_pieces
from paper_workspace.scaffold_port import port_workspace


def three_blank_pages():
    writer = PdfWriter()
    for width in (200, 300, 400):
        writer.add_blank_page(width=width, height=500)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def one_large_jpeg_page():
    stream = io.BytesIO()
    Image.new('RGB', (1200, 1100), (20, 40, 60)).save(stream, 'PDF')
    return stream.getvalue()


def ported(root, pdf, captions, supplements=None):
    """A PDF import's workspace with ``captions``, ported to Scaffold, and the export's view of its pieces."""
    source = root / 'imported'
    (source / 'original').mkdir(parents=True)
    # The engine digests the folder as it stands, so the source files are written first.
    (source / 'original' / 'original.pdf').write_bytes(pdf)
    for name, data in (supplements or {}).items():
        (source / 'supplements').mkdir(exist_ok=True)
        (source / 'supplements' / name).write_bytes(data)
    pieces = [{'kind': 'caption', 'text': text, 'page': page} for text, page in captions]
    manuscripts.build(source, [], boxed=False, extra=pieces)
    output = root / 'ported'
    port_workspace(source, output)
    return output, export_pieces(verify_workspace(output))


class ExportEvidence(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_copies_assets_and_exact_figure_pages(self):
        output, pieces = ported(self.root, three_blank_pages(),
                                [('Fig 1 A result', 2), ('S1 Fig Another result', 3)],
                                {'S1_Fig.png': b'original image'})
        destination = self.root / 'evidence'
        result, main_figures = preserve_source_evidence(output / 'scaffold' / 'source', destination, pieces)

        self.assertEqual(result['main_figure_pages'], [2])
        self.assertEqual(main_figures, [])
        self.assertEqual(len(PdfReader(destination / 'main-figure-source-pages.pdf').pages), 1)
        self.assertEqual(digest((destination / 'supplements/S1_Fig.png').read_bytes()), digest(b'original image'))
        stored = json.loads((destination / 'manifest.json').read_text())
        self.assertEqual(stored['files']['supplements/S1_Fig.png'], digest(b'original image'))

    def test_extracts_only_one_large_rgb_jpeg_for_one_caption(self):
        output, pieces = ported(self.root, one_large_jpeg_page(), [('Fig 1 A verified result.', 1)])
        original = output / 'scaffold' / 'source' / 'original' / 'original.pdf'
        extracted, fallbacks = extract_main_figures(original, self.root / 'figures', pieces)

        self.assertEqual(fallbacks, [])
        self.assertEqual(len(extracted), 1)
        caption = next(piece for piece in pieces if piece['kind'] == 'caption')
        # The figure points back at the lines of the manuscript the port read its caption from.
        self.assertEqual(extracted[0]['origin'], {'document': 'paper.md', 'lines': caption['lines']})
        self.assertEqual(extracted[0]['caption'], 'Fig 1 A verified result.')
        self.assertEqual(extracted[0]['mode'], 'RGB')
        self.assertGreaterEqual(extracted[0]['width'], 1000)
        self.assertEqual(digest(Path(extracted[0]['path']).read_bytes()), extracted[0]['sha256'])

    def test_two_main_captions_on_one_page_fall_back(self):
        output, pieces = ported(self.root, one_large_jpeg_page(),
                                [('Fig 1 A verified result.', 1), ('Fig 2 Another result.', 1)])
        original = output / 'scaffold' / 'source' / 'original' / 'original.pdf'
        extracted, fallbacks = extract_main_figures(original, self.root / 'ambiguous', pieces)
        self.assertEqual(extracted, [])
        self.assertEqual(fallbacks[0]['reason'], 'main_caption_count')


if __name__ == '__main__':
    unittest.main()
