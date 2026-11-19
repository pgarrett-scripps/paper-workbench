"""A manuscript the engine's own Read stage wrote, with a script in place of the model.

``read_paper`` writes a three page PDF and opens a run on it with ``peerreviewagents.scripted_read``,
with the pieces a converter is known to leave behind spliced into the draft. The script does what a
reader does. It views every page, repairs the equation, describes the figure and folds its axis
numbers into the description, re-reads a paragraph of run-together cells as a sentence, a table and
a caption with a stray heading folded into the table, cuts a stray phrase out of a paragraph, puts
back the text of the page the converter returned nothing from and seals with a note.
``tests/fixtures/reader/paper.json`` is ``build``'s result, and ``test_reader_fixture`` checks it is
still what the engine writes.
"""
import tempfile
import textwrap
from pathlib import Path

from peerreviewagents import read_manuscript, scripted_read

from paper_workspace.scaffold_port import port_workspace
from paper_workspace.server import paper_view

FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'reader' / 'paper.json'

LOST_PAGE_TEXT = ('The stop block was checked against the reference block at the end of each day. No '
                  'check moved the stop by more than the smallest division of the scale, so every '
                  'reading was kept.')
# What the PDF prints, page by page, as (font size, text). The third page is turned, and the
# pinned converter returns nothing from a turned page while Poppler reads its words, so the
# import records it as lost and the reader has to put its text back.
TURNED = {3}
PAGES = [
    [(18, 'Widget Readings on a Level Bench'),
     (13, 'Abstract'),
     (11, 'We describe repeated readings of small widgets on a level bench. The readings were taken '
          'under the same conditions on three days. This document is synthetic prose written for '
          'software tests and reports no real experiment.'),
     (13, '1 Methods'),
     (11, 'Each widget was placed against the stop and read with the same instrument. The observer '
          'checked the scale against a reference block before every reading.')],
    [(13, '2 Results'),
     (11, 'The blue widgets read the same on every day. The green widgets differed by less than the '
          'smallest division of the scale.')],
    [(11, LOST_PAGE_TEXT)],
]

# What the converter left for the Read stage, in the shape it writes a piece: an equation with a
# brace it never closed, a heading that is the edge of that equation, a table read as one paragraph
# of run-together cells behind a sentence of the paper, a figure's axis numbers read as a paragraph,
# a figure it has the caption of and no image, and a paragraph with debris inside it.
RESULTS = {'section': '2 Results', 'page': 2}
CONVERTER_LEFT = [
    {'kind': 'equation', 'text': 'E = m c^{2', 'latex': 'E = m c^{2', 'number': '(1)', 'confidence': 1.0,
     **RESULTS},
    {'kind': 'heading', 'text': 'with $\\{$', **RESULTS},
    {'kind': 'paragraph', 'text': 'The current was logged every hour. Hour Current (mA) 1 4.5 2 9.0', **RESULTS},
    {'kind': 'paragraph', 'text': '0 10 20 30 40 mm', **RESULTS},
    {'kind': 'caption', 'text': 'Figure 1: The bench, the instrument and the widgets.', **RESULTS},
    {'kind': 'paragraph', 'text': 'The readings held across the week qn,s,d else and no widget moved.',
     **RESULTS},
]

DESCRIBED = ('A photograph of the bench with the instrument clamped at the left and three widgets in a '
             'row. The scale under them is marked from 0 to 40 mm.')
# The note carries markup, which the viewer must escape. The engine folds every run of whitespace
# in a note to one space, so a note never holds a line break.
NOTE = ('Table 1 came back as a paragraph of run-together cells and is a table again. The <b>axis</b> '
        'numbers of Figure 1 were a paragraph of their own and are folded into its description.')


def pdf_bytes(pages, turned=()):
    """A PDF that prints each page's lines in Helvetica, with nothing compressed.

    A page whose number is in ``turned`` is shown rotated a quarter turn.
    """
    def quoted(text):
        return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

    objects = {1: '<< /Type /Catalog /Pages 2 0 R >>',
               2: '<< /Type /Pages /Kids [' + ' '.join(f'{4 + 2 * at} 0 R' for at in range(len(pages)))
                  + f'] /Count {len(pages)} >>',
               3: '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>'}
    for at, page in enumerate(pages):
        drawn, y = [], 720
        for size, text in page:
            for line in textwrap.wrap(text, 90 if size == 11 else 60):
                drawn.append(f'BT /F1 {size} Tf 72 {y} Td ({quoted(line)}) Tj ET')
                y -= size + 4
            y -= 12
        content = '\n'.join(drawn) + '\n'
        rotate = ' /Rotate 90' if at + 1 in turned else ''
        objects[4 + 2 * at] = (f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]{rotate} '
                               f'/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * at} 0 R >>')
        objects[5 + 2 * at] = f'<< /Length {len(content.encode("latin-1"))} >>\nstream\n{content}endstream'
    out, offsets = bytearray(b'%PDF-1.4\n'), []
    for number in sorted(objects):
        offsets.append(len(out))
        out += f'{number} 0 obj\n{objects[number]}\nendobj\n'.encode('latin-1')
    table = len(out)
    out += f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n'.encode('ascii')
    out += ''.join(f'{offset:010d} 00000 n \n' for offset in offsets).encode('ascii')
    out += f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{table}\n%%EOF\n'.encode('ascii')
    return bytes(out)


def read_paper(root):
    """Run the scripted Read stage on the fixture PDF under ``root`` and return the sealed workspace."""
    root = Path(root)
    paper = root / 'paper.pdf'
    paper.write_bytes(pdf_bytes(PAGES, TURNED))
    with scripted_read(paper, root / 'run', CONVERTER_LEFT) as read:
        for page in range(1, len(PAGES) + 1):
            read.view_page(page)
        read.replace_equation(read.find('E = m c^{2'), 2, 'E = m c^{2}', number='(1)')
        read.describe_figure(read.find('Figure 1: The bench'), 2, DESCRIBED, absorb=[read.find('0 10 20 30 40 mm')])
        read.reread_piece(read.find('logged every hour'), 2, [
            {'kind': 'paragraph', 'keep': 'The current was logged every hour.'},
            {'kind': 'table', 'rows': [['Hour', 'Current (mA)'], ['1', '4.5'], ['2', '9.0']]},
            {'kind': 'caption', 'text': 'Table 1: Current by hour.'},
        ], absorb=[read.find('with $\\{$')])
        read.reread_piece(read.find('no widget moved'), 2, [{'kind': 'paragraph', 'remove': ['qn,s,d else']}])
        read.add_piece(read.find('no widget moved'), 'paragraph', 3, text=LOST_PAGE_TEXT)
        read.seal(note=NOTE)
    return read.workspace


def build():
    """What ``/api/paper`` serves for the read manuscript under ``read``, and for its Scaffold port under ``ported``."""
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        workspace = read_paper(root)
        port_workspace(workspace, root / 'ported')
        return {'read': paper_view(read_manuscript(workspace)),
                'ported': paper_view(read_manuscript(root / 'ported'))}
