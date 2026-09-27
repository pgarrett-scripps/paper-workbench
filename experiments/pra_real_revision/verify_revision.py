"""Check a ported export offline without starting review inference."""
import argparse
from collections import Counter
from pathlib import Path
import re
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

from pypdf import PdfReader

from paper_workspace.revisions import snapshot
from paper_workspace.storage import digest, read, write

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
NUMBER = re.compile(r'(?<![\w.])[+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?')


def normalize(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text))


def document_xml(path):
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read('word/document.xml'))


def cell_fingerprint(table):
    rows = []
    for row in table.findall('w:tr', NS):
        cells = []
        for cell in row.findall('w:tc', NS):
            span = cell.find('w:tcPr/w:gridSpan', NS)
            merge = cell.find('w:tcPr/w:vMerge', NS)
            cells.append((normalize(''.join(t.text or '' for t in cell.findall('.//w:t', NS))),
                          span.attrib if span is not None else {}, merge.attrib if merge is not None else None))
        rows.append(cells)
    return rows


def verify_export(workspace, revision, export):
    source, paper = snapshot(workspace, revision)
    export = Path(export).resolve()
    record = read(export / 'export.json')
    assert record['paper_id'] == paper['id'] and record['source_sha256'] == paper['source_sha256']
    for name, expected in record['files'].items():
        path = (export / name).resolve()
        assert path.is_relative_to(export) and digest(path.read_bytes()) == expected, name
    xml = document_xml(export / 'paper.docx')
    word = normalize(''.join(t.text or '' for t in xml.findall('.//w:t', NS)))
    pdf = subprocess.run(['pdftotext', '-layout', str(export / 'paper.pdf'), '-'],
                         capture_output=True, text=True, check=True).stdout
    word_missing = [b['id'] for b in paper['blocks'] if normalize(b['text']) not in word]
    prose = [b for b in paper['blocks'] if b['kind'] != 'table']
    pdf_missing = [b['id'] for b in prose if normalize(b['text']) not in normalize(pdf)]
    assert not word_missing and not pdf_missing, (word_missing, pdf_missing)
    pages = [page.extract_text() for page in PdfReader(export / 'paper.pdf').pages]
    table_results = []
    actual_tables = [cell_fingerprint(t) for t in xml.findall('.//w:tbl', NS)]
    for path in sorted((export / 'source-evidence/supplements').glob('S*_Table.docx')):
        original = source / 'scaffold/source/supplements' / path.name
        assert digest(path.read_bytes()) == digest(original.read_bytes()), path.name
        source_xml = document_xml(path)
        for table in source_xml.findall('.//w:tbl', NS):
            assert cell_fingerprint(table) in actual_tables, path.name
        label = path.stem.replace('_', ' ')
        start = [i for i, text in enumerate(pages) if text.strip() and text.strip().splitlines()[0].strip() == label]
        assert len(start) == 1, (label, start)
        end = next(i for i in range(start[0], len(pages)) if 'Source file: ' + path.name in pages[i])
        expected_text = ' '.join(t.text or '' for t in source_xml.findall('.//w:tbl//w:t', NS))
        number_counts = lambda text: Counter(NUMBER.findall(unicodedata.normalize('NFKC', text).replace('\u2212', '-').replace('\u2010', '-')))
        expected = number_counts(expected_text)
        missing = expected - number_counts('\n'.join(pages[start[0]:end+1]))
        assert not missing, (path.name, missing)
        table_results.append({'source': path.name, 'pages': [start[0]+1, end+1],
                              'cell_text_and_merge_spans_match': True,
                              'pdf_numeric_literals_preserved': sum(expected.values())})
    return {'source_sha256': paper['source_sha256'], 'export': str(export), 'model_calls': 0,
            'word_blocks_matched': len(paper['blocks']), 'pdf_non_table_blocks_matched': len(prose),
            'tables': table_results, 'pages': len(pages),
            'empty_text_pages': [i+1 for i, text in enumerate(pages) if not text.strip()],
            'export_hashes_verified': True, 'visual_qa': 'Separate rendered-page inspection required.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace')
    parser.add_argument('revision')
    parser.add_argument('export')
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    result = verify_export(arguments.workspace, arguments.revision, arguments.export)
    write(arguments.output, result)
    print('Export fidelity verified without review inference.')
