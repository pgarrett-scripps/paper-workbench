"""Create a traceable Scaffold reading copy from an immutable review workspace.

Every map row of the source manuscript becomes one record of ``pra-port.json`` and,
except for the title and the abstract, one Typst file under ``blocks/``. Importing
the tree back writes the same lines the source manuscript holds, document for
document, and the port is refused when it does not. Each record keeps the lines it
was read from as its ``origin``, so a ported piece points back at the source.
"""
import json
import re
import tempfile
from pathlib import Path

from peerreviewagents import MAIN_DOCUMENT, verify_workspace
from peerreviewagents.workspace import digest, read_json, write_json

from .scaffold_import import import_scaffold, plain_prose, span_entry
from .source_edits import TEXT_LITERAL, literal_value


PORT = 'pra-port.json'
PORT_SCHEMA = 'paper-workbench-port-v2'
CONFIG = 'config.typ'
SPECIAL = re.compile(r'[#*$@_<>\[\]{}\\`]|//|/\*|\*/')
EQUATION = re.compile(r'\$\$ (.*?)(?: \\tag\{([^{}]+)\})? \$\$')
LITERAL_HEADING = re.compile(r'#heading\(level: (\d+)\)\[(#text\("(?:[^"\\]|\\.)*"\))\]', re.S)
ABSTRACT = re.compile(r'(?m)^#let paper-abstract = \[\n(.*?)\n\]\n', re.S)
#: The fields of a record that are a piece's own, passed to the engine as they stand. ``source`` and
#: ``original`` say whether a model wrote the piece and keep the converter's reading of one it read again.
PIECE_FIELDS = ('kind', 'text', 'level', 'latex', 'number', 'table', 'section', 'page', 'bbox',
                'citations', 'confidence', 'source', 'original')
DESCRIPTION = 'Figure description: '
LIMITATIONS = ['This is an extracted reading copy, not the original manuscript layout.',
               'Tables and captions are preserved as text. Original figures and formatting remain in the source PDF.',
               'Citation text is preserved. BibTeX citation keys are not reconstructed.']


def _cells(line):
    if not (line.startswith('| ') and line.endswith(' |')):
        raise ValueError('Table line is not a Markdown table row')
    return [cell.replace('\\|', '|') for cell in line[2:-2].split(' | ')]


def recovered(kind, lines):
    """The piece fields a row's lines were rendered from, read back off the lines."""
    first = lines[0]
    if kind == 'table':
        if len(lines) < 2 or set(_cells(lines[1])) != {'---'}:
            raise ValueError('Table piece has no delimiter row')
        rows = [_cells(line) for index, line in enumerate(lines) if index != 1]
        return {'text': '\n'.join('\t'.join(row) for row in rows), 'table': rows}
    if len(lines) != 1:
        raise ValueError(f'A {kind} piece of {len(lines)} lines cannot be ported')
    if kind == 'title' and first.startswith('# '):
        return {'text': first[2:]}
    heading = re.fullmatch(r'(#{2,6}) (.*)', first)
    if kind == 'heading' and heading:
        return {'text': heading.group(2), 'level': len(heading.group(1)) - 1}
    equation = EQUATION.fullmatch(first)
    if kind == 'equation' and equation:
        return {'text': equation.group(1), 'latex': equation.group(1), 'number': equation.group(2)}
    if kind == 'figure' and first.startswith('Figure: '):
        return {'text': first[len('Figure: '):]}
    if kind == 'caption':
        for prefix in ('Figure: ', 'Caption: '):
            if first.startswith(prefix):
                return {'text': first[len(prefix):]}
    if kind == 'figure-description' and first.startswith(DESCRIPTION):
        return {'text': first[len(DESCRIPTION):]}
    if kind in ('title', 'heading', 'equation', 'figure', 'caption', 'figure-description'):
        raise ValueError(f'A {kind} line is not in the form the engine renders: {first}')
    return {'text': first}


def _literal(text):
    return '#text(' + json.dumps(text, ensure_ascii=False) + ')'


def _content(record):
    """The Typst one block file holds for a record."""
    text = record['text']
    if record['kind'] == 'paragraph' and plain_prose(text):
        return text
    if record['kind'] == 'heading':
        if text and text == text.strip() and not SPECIAL.search(text):
            return '=' * record['level'] + ' ' + text
        return f'#heading(level: {record["level"]})[' + _literal(text) + ']'
    return _literal(text)


def _records(base):
    records = []
    for document in base.document_names():
        for index, row in enumerate(base.pieces(document)):
            start, end = row['lines']
            lines = base.range_text(start, end, document).split('\n')
            record = {'document': document, 'kind': row['kind'], 'section': row.get('section'),
                      'page': row.get('page'), 'bbox': row.get('bbox'),
                      'citations': row.get('citations') or [], 'source': row.get('source'),
                      'original': row.get('original'), 'confidence': row.get('confidence'),
                      **recovered(row['kind'], lines), 'origin': {'document': document, 'lines': row['lines']}}
            main = document == MAIN_DOCUMENT
            if main and index == 0 and row['kind'] == 'title':
                record['file'] = None
            elif row['kind'] == 'figure-description':
                # A model's description of a figure image is not the authors' words, so it stays in the
                # reading copy and is never written into the Typst source the manuscript is built from.
                record['file'] = None
            elif main and row['kind'] == 'heading' and record['text'].strip() == 'Abstract':
                record['file'] = None
            elif main and row['kind'] == 'paragraph' and row.get('section') == 'Abstract':
                record['file'] = CONFIG
            else:
                record['file'] = f'blocks/{len(records) + 1:04d}.typ'
            records.append(record)
    return records


def supplements_of(manifest):
    """The file each supplement document was imported from, by name, as the manifest's assets record it."""
    found = {}
    for asset in manifest.get('assets') or []:
        path = asset.get('path') if isinstance(asset, dict) else None
        if asset and isinstance(asset.get('document'), str) and isinstance(path, str) and path.startswith('supplements/'):
            found[asset['document']] = Path(path).name
    return found


def piece_model(manifest):
    """The model that wrote the source's pieces whose ``source`` is not ``text``, or ``''``.

    The Read stage's model where one read the pages, and otherwise the model the
    writer of the manifest named for its own pieces. The port writes those pieces
    again, and the engine writes a model's piece only with the model's name. No
    page is read in a port, so the ported manifest says the pieces were written by
    that model and not that it read them.
    """
    read = manifest.get('ai_read') or {}
    return str((read.get('reader_model') if read.get('read') else '') or read.get('ai_model') or '')


def port_workspace(source, output):
    """Write a Scaffold project from a manuscript workspace and import it as a new workspace."""
    source, output = Path(source).resolve(), Path(output).resolve()
    base = verify_workspace(source)
    if output.exists():
        raise ValueError('Port output already exists')
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('Source and output must not overlap')
    manifest = base.manifest
    records = _records(base)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.port-', dir=output.parent) as temporary:
        project = Path(temporary) / 'project'
        (project / 'blocks').mkdir(parents=True)
        abstract = [record for record in records if record['file'] == CONFIG]
        (project / CONFIG).write_text(
            '#let paper-title = ' + json.dumps(base.title, ensure_ascii=False) + '\n'
            '#let paper-abstract = [\n' + '\n\n'.join(_literal(record['text']) for record in abstract) + '\n]\n'
            '#let paper-authors = ()\n#let paper-affiliations = ()\n#let paper-keywords = ()\n#let paper-date = none\n',
            encoding='utf-8')
        lines = ['#set page(paper: "us-letter", margin: 0.9in)', '#set text(size: 10pt)',
                 '#import "config.typ": *', '#text(size: 15pt, weight: "bold", paper-title)',
                 '#heading(level: 1, numbering: none)[Abstract]', '#paper-abstract',
                 '#set heading(numbering: "1.")', '// >>> BODY START']
        for record in records:
            if record['file'] and record['file'].startswith('blocks/'):
                (project / record['file']).write_text(_content(record) + '\n', encoding='utf-8')
                lines.append(f'#include "{record["file"]}"')
        lines.append('// <<< BODY END')
        (project / 'paper.typ').write_text('\n\n'.join(lines) + '\n', encoding='utf-8')
        write_json(project / PORT, {
            'schema': PORT_SCHEMA, 'source_paper_id': base.paper_id,
            'source_sha256': (manifest.get('source') or {}).get('sha256'),
            'source_url': manifest.get('source_url'), 'references': read_json(source / 'references.json'),
            'pages': manifest.get('pages') or [], 'box_convention': manifest.get('box_convention'),
            'supplements': supplements_of(manifest), 'limitations': LIMITATIONS,
            'ai_model': piece_model(manifest), 'records': records})
        for name, sha in manifest['files'].items():
            if not name.startswith(('original/', 'supplements/')):
                continue
            target = project / 'source' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((source / name).read_bytes())
            if digest(target.read_bytes()) != sha:
                raise ValueError('Source changed while porting')

        def same_lines(folder, ported):
            if ported.document_names() != base.document_names() or ported.documents != base.documents:
                raise ValueError('The ported manuscript does not read line for line as its source')
            if ported.manifest.get('box_convention') != manifest.get('box_convention'):
                raise ValueError('The ported manuscript writes its boxes in another convention than its source')

        return import_scaffold(project, output, title=base.title, check=same_lines)


def _abstracts(root, hashes):
    config = (root / CONFIG).read_bytes().decode('utf-8')
    declaration = ABSTRACT.search(config)
    if declaration is None:
        raise ValueError('Ported abstract declaration is missing')
    body = declaration.group(1)
    if TEXT_LITERAL.sub('', body).strip():
        raise ValueError('Ported abstract must contain only its literal text declarations')
    found = []
    for expression in TEXT_LITERAL.finditer(body):
        value = literal_value(expression.group())[0]
        found.append((value, {'kind': 'paragraph', 'file': CONFIG,
                              'start': declaration.start(1) + expression.start(1),
                              'end': declaration.start(1) + expression.end(1),
                              'file_sha256': hashes[CONFIG], 'editable': True, 'encoding': 'json-string'}))
    return found


def _decoded(record, segment):
    """The text a block file holds for its record, and where that text sits in the file."""
    kind, text = record['kind'], segment['text']
    if kind == 'paragraph' and segment['kind'] == 'paragraph':
        return text, span_entry(segment, kind, editable=True)
    if kind == 'heading':
        if segment['kind'] == 'heading':
            value, level = segment['heading'], segment['level']
        else:
            match = LITERAL_HEADING.fullmatch(text)
            literal = literal_value(match.group(2)) if match else None
            if literal is None:
                raise ValueError(f'{segment["file"]} no longer holds its ported heading')
            value, level = literal[0], int(match.group(1))
        if value != record['text'] or level != record['level']:
            raise ValueError(f'{segment["file"]} no longer holds its ported heading')
        return value, span_entry(segment, kind, editable=False)
    literal = literal_value(text)
    if literal is None:
        raise ValueError(f'{segment["file"]} no longer holds a single text literal')
    value, start, end = literal
    if kind == 'paragraph':
        return value, {**span_entry(segment, kind, editable=True), 'start': segment['start'] + start,
                       'end': segment['start'] + end, 'encoding': 'json-string'}
    if value != record['text']:
        raise ValueError(f'{segment["file"]} no longer holds its ported {kind}')
    return value, span_entry(segment, kind, editable=False)


def ported_items(root, found, hashes):
    """``(document, piece, entry)`` for each record of a ported tree, in the source's order."""
    port = read_json(root / PORT)
    if not isinstance(port, dict) or port.get('schema') != PORT_SCHEMA:
        raise ValueError(f'{PORT} is not a port record this version reads')
    if not (isinstance(port.get('supplements'), dict)
            and all(isinstance(name, str) for name in port['supplements'].values())):
        raise ValueError(f'{PORT} does not name the file of each supplement document')
    if not isinstance(port.get('ai_model'), str):
        raise ValueError(f'{PORT} does not name the model that wrote its ai pieces')
    by_file = {}
    for segment in found:
        by_file.setdefault(segment['file'], []).append(segment)
    abstracts = iter(_abstracts(root, hashes))
    used, items = set(), []
    for record in port['records']:
        piece = {key: record[key] for key in PIECE_FIELDS if record.get(key) is not None}
        if record.get('page') is not None:
            piece['page_mapping'] = 'original_pdf'
        name = record['file']
        if name is None:
            entry = {'kind': record['kind'], 'file': None, 'editable': False}
        elif name == CONFIG:
            item = next(abstracts, None)
            if item is None:
                raise ValueError('Ported abstract holds fewer paragraphs than its record')
            piece['text'], entry = item
        else:
            segments = by_file.get(name, [])
            if len(segments) != 1:
                raise ValueError(f'{name} must hold exactly one ported piece')
            used.add(name)
            piece['text'], entry = _decoded(record, segments[0])
        entry['origin'] = record['origin']
        items.append((record['document'], piece, entry))
    if next(abstracts, None) is not None:
        raise ValueError('Ported abstract holds more paragraphs than its record')
    if set(by_file) - used:
        raise ValueError('Ported scaffold holds text outside its block files: '
                         + ', '.join(sorted(set(by_file) - used)))
    return items, port
