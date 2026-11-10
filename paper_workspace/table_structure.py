"""Recover display geometry from exact source Word tables without guessing merges."""
import copy
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

from peerreviewagents.engine.ingest import text_of

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{' + NS['w'] + '}'


def normalized(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text))


def word_tables(path):
    with zipfile.ZipFile(path) as archive:
        if archive.getinfo('word/document.xml').file_size > 5_000_000:
            raise ValueError('Supplement document exceeds text limit')
        root = ET.fromstring(archive.read('word/document.xml'))
    result = []
    for table in root.findall('w:body/w:tbl', NS):
        if table.findall('.//w:tbl', NS) or table.findall('.//w:hMerge', NS):
            continue
        rows, plain, active = [], [], {}
        columns = len(table.findall('w:tblGrid/w:gridCol', NS))
        for row in table.findall('w:tr', NS):
            rendered, texts, column, next_active = [], [], 0, {}
            before = row.find('w:trPr/w:gridBefore', NS)
            if before is not None:
                column = int(before.get(W + 'val', '0'))
                if column:
                    rendered.append({'text': '', 'colspan': column, 'rowspan': 1})
            for cell in row.findall('w:tc', NS):
                text = ' '.join(text_of(p) for p in cell.findall('w:p', NS))
                texts.append(text)
                span = cell.find('w:tcPr/w:gridSpan', NS)
                width = int(span.get(W + 'val', '1')) if span is not None else 1
                if not 1 <= width <= 100 or not 0 <= column <= 100:
                    raise ValueError('Unsupported source table column span')
                merge = cell.find('w:tcPr/w:vMerge', NS)
                if merge is not None and merge.get(W + 'val', 'continue') == 'continue':
                    origin = active.get(column)
                    if origin is None or origin['colspan'] != width:
                        raise ValueError('Unresolved source table vertical merge')
                    origin['rowspan'] += 1
                    next_active[column] = origin
                else:
                    item = {'text': text, 'colspan': width, 'rowspan': 1}
                    rendered.append(item)
                    if merge is not None:
                        next_active[column] = item
                column += width
            active = next_active
            columns = max(columns, column)
            if not 1 <= columns <= 100:
                raise ValueError('Unsupported source table width')
            rows.append(rendered)
            plain.append('\t'.join(texts))
        result.append({'text': '\n'.join(plain), 'structure': {'columns': columns, 'rows': rows}})
    return result


def enrich_tables(source_root, paper):
    """Attach verified display metadata while preserving the stored manuscript."""
    paper = copy.deepcopy(paper)
    source_root = Path(source_root).resolve()
    supplements = source_root / 'source/supplements'
    if not supplements.is_dir():
        return paper
    inventory = {}
    for path in sorted(supplements.glob('*.docx')):
        if path.is_symlink() or not path.resolve().is_relative_to(source_root):
            continue
        try:
            tables = word_tables(path)
        except (ValueError, KeyError, zipfile.BadZipFile, ET.ParseError):
            paper.setdefault('warnings', []).append('Table geometry could not be recovered from ' + path.name + '. Exact text and the source file remain available.')
            continue
        for table in tables:
            inventory.setdefault(normalized(table['text']), []).append((path.name, table['structure']))
    for block in paper.get('blocks', []):
        if block.get('kind') != 'table':
            continue
        candidates = inventory.get(normalized(block['text']), [])
        if block.get('document') not in (None, 'main'):
            candidates = [item for item in candidates if item[0] == block['document']]
        if len(candidates) == 1:
            block['table_structure'] = candidates[0][1]
            block['table_structure_source'] = 'source/supplements/' + candidates[0][0]
    return paper
