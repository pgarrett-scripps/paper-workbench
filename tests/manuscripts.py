"""Manuscripts for the tests, written by the engine's own writer and read back by its reader.

A test never writes paper.md, map.json or manifest.json by hand. It passes the
pieces to ``write_manuscript``, as the engine's own tests do, and reads the
workspace back with ``read_manuscript``.
"""
import tempfile
from pathlib import Path

from peerreviewagents import MAIN_DOCUMENT, read_manuscript, write_manuscript
from peerreviewagents.workspace import digest

TITLE = 'QA'
PAPER_ID = 'qa'
SOURCE_SHA256 = digest('qa-source')
# One US Letter page in points, and the box of every paragraph on it.
PAGE = {'page': 1, 'width': 612.0, 'height': 792.0, 'rotation': 0}
BOX = [72.0, 100.0, 540.0, 112.0]

# The run's manuscript: the sentence the findings quote, then two passages that
# cite the reference list below. The paper prints its citations as superscripts,
# and the reader wrote each marker as a link to the entry it matched, which is
# how a PDF import reaches the citation ledger. Marker 7 links to a label no
# entry carries.
TEXT = 'Knockdown lowered VPS35 in 12 samples.'
CITING = [
    ('Retromer returns cargo from endosomes to the Golgi[1](#ref-1). VPS35 loss stops that retrieval '
     'completely in neurons[1](#ref-1). The D620N variant abolishes retromer assembly[5](#ref-5). '
     'Earlier screens reported the same phenotype[3](#ref-3). A second cohort agreed[4](#ref-4).'),
    ('Our model follows the neuronal sorting rule[2](#ref-2). The pathway was first mapped in '
     'yeast[6](#ref-6). Similar results appear in a later survey[7](#ref-7).'),
]
FIXTURE_DOI = {'one': '10.5555/fixture.one', 'missing': '10.5555/fixture.missing',
               'retracted': '10.5555/fixture.retracted'}
REFERENCES = [
    {'id': 'r1', 'label': '1', 'title': 'Retromer and the retrieval of endosomal cargo',
     'first_author': 'Seaman', 'year': '2021', 'venue': 'Journal of Cell Science', 'doi': FIXTURE_DOI['one'],
     'raw': '1. Seaman M. Retromer and the retrieval of endosomal cargo. Journal of Cell Science. 2021.'},
    {'id': 'r2', 'label': '2', 'title': 'A sorting rule for endosomal cargo in neurons',
     'first_author': 'Okafor', 'year': '2022', 'venue': 'Neuron Reports', 'doi': FIXTURE_DOI['missing'],
     'raw': '2. Okafor A. A sorting rule for endosomal cargo in neurons. Neuron Reports. 2022.'},
    {'id': 'r3', 'label': '3', 'title': 'Screens for retromer phenotypes in a thesis collection',
     'first_author': 'Lindqvist', 'year': '2015', 'venue': None, 'doi': None,
     'raw': '3. Lindqvist P. Screens for retromer phenotypes in a thesis collection. 2015.'},
    {'id': 'r4', 'label': '4', 'title': 'A second cohort of VPS35 carriers',
     'first_author': 'Haddad', 'year': '2020', 'venue': 'Movement Disorders', 'doi': None,
     'raw': '4. Haddad R. A second cohort of VPS35 carriers. Movement Disorders. 2020.'},
    {'id': 'r5', 'label': '5', 'title': 'The D620N variant and retromer binding',
     'first_author': 'Moreno', 'year': '2019', 'venue': 'Cell Reports', 'doi': FIXTURE_DOI['retracted'],
     'raw': '5. Moreno L. The D620N variant and retromer binding. Cell Reports. 2019.'},
    {'id': 'r6', 'label': '6', 'title': 'Mapping the retromer pathway in yeast',
     'first_author': 'Brandt', 'year': '1998', 'venue': 'Journal of Cell Biology', 'doi': None,
     'raw': '6. Brandt K. Mapping the retromer pathway in yeast. Journal of Cell Biology. 1998.'},
]


def pieces(texts, title=TITLE, boxed=True):
    """A title and one paragraph per text, each paragraph on page 1 in ``BOX`` when ``boxed``."""
    place = {'page': 1, 'bbox': list(BOX)} if boxed else {}
    return [{'kind': 'title', 'text': title}] + [{'kind': 'paragraph', 'text': text, **place} for text in texts]


def build(folder, texts, title=TITLE, paper_id=PAPER_ID, source_sha256=SOURCE_SHA256, boxed=True,
          documents=None, references=None, extra=(), assets=None):
    """Write a manuscript of ``texts`` into ``folder`` and return it as the engine reads it.

    ``extra`` is further pieces at the end of paper.md, and ``documents`` adds
    further documents after it, each a name and its pieces. ``references`` is
    the reference list the import read, and ``assets`` the source files it recorded.
    """
    folder = Path(folder)
    main = pieces(texts, title, boxed) + list(extra)
    write_manuscript(folder, {MAIN_DOCUMENT: main, **(documents or {})},
                     title=title, paper_id=paper_id, parser='test',
                     source={'file': 'original/original.pdf', 'sha256': source_sha256, 'pages': 1},
                     pages=[PAGE] if boxed else None, references=references, assets=assets)
    return read_manuscript(folder)


def run_manuscript(folder, boxed=True, extra=()):
    """The manuscript of the test run: ``TEXT`` and the citing passages, with the reference list."""
    return build(folder, [TEXT, *CITING], boxed=boxed, references=REFERENCES, extra=extra)


def line_of(base, text, document=MAIN_DOCUMENT):
    """The first line of ``document`` that holds ``text``."""
    return next(line for line in range(1, base.line_count(document) + 1) if text in base.line_text(line, document))


def fingerprint_of(text):
    """The fingerprint the engine gives a paragraph of ``text``."""
    with tempfile.TemporaryDirectory() as folder:
        base = build(Path(folder) / 'manuscript', [text])
        return base.piece_at(line_of(base, text))['fingerprint']
