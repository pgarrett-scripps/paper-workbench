"""Create a traceable Scaffold reading copy from an immutable review workspace."""
import json
import re
import shutil
import tempfile
from pathlib import Path

from peerreviewagents import verify_workspace
from peerreviewagents.workspace import digest, read_json, write_json

from .scaffold_import import import_scaffold
from .source_edits import TEXT_LITERAL, literal_value


SPECIAL = re.compile(r'[#*$@_<>\[\]{}\\`]|//|/\*|\*/')


def port_workspace(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    paper = verify_workspace(source)
    if output.exists():
        raise ValueError('Port output already exists')
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('Source and output must not overlap')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.port-', dir=output.parent) as temporary:
        project = Path(temporary) / 'project'
        project.mkdir()
        (project / 'blocks').mkdir()
        provenance = {'source_paper_id': paper['id'], 'source_sha256': paper['source_sha256'],
                      'source_url': paper.get('source_url'), 'blocks': [], 'references':paper['references'],
                      'pdf_pages':paper['statistics']['pdf_pages'],
                      'limitations': ['This is an extracted reading copy, not the original manuscript layout.',
                                      'Tables and captions are preserved as text. Original figures and formatting remain in the source PDF.',
                                      'Citation text is preserved. BibTeX citation keys are not reconstructed.']}
        abstract = [b for b in paper['blocks'] if b['section'] == 'Abstract' and b['kind'] == 'paragraph']
        abstract_ids = {b['id'] for b in abstract}
        config = ('#let paper-title = ' + json.dumps(paper['title'], ensure_ascii=False) + '\n'
                  '#let paper-abstract = [\n' + '\n\n'.join('#text(' + json.dumps(b['text'], ensure_ascii=False) + ')' for b in abstract) + '\n]\n'
                  '#let paper-authors = ()\n#let paper-affiliations = ()\n#let paper-keywords = ()\n#let paper-date = none\n')
        (project / 'config.typ').write_text(config)
        lines = ['#set page(paper: "us-letter", margin: 0.9in)', '#set text(size: 10pt)',
                 '#import "config.typ": *', '#text(size: 15pt, weight: "bold", paper-title)',
                 '#heading(level: 1, numbering: none)[Abstract]', '#paper-abstract',
                 '#set heading(numbering: "1.")', '// >>> BODY START']
        for block in paper['blocks']:
            if block['id'] in abstract_ids:
                provenance['blocks'].append({'original_id': block['id'], 'text': block['text'],
                    'source_sha256': block['sha256'], 'file': 'config.typ', 'role': 'abstract', 'page': block.get('page'), 'citations':block.get('citations',[])})
                continue
            if block['kind'] == 'heading' and block['text'].strip() == 'Abstract':
                continue
            name = f'blocks/{block["id"]}.typ'
            text = block['text']
            plain = (block['kind'] == 'paragraph' and not SPECIAL.search(text)
                     and not any(re.match(r'^\s*(?:[-+=]|\d+[.)])\s', line) for line in text.splitlines()))
            if block['kind'] == 'heading':
                content = '= ' + text if not SPECIAL.search(text) and '\n' not in text else '#heading(level: 1)[' + '#text(' + json.dumps(text,ensure_ascii=False) + ')]'
            else:
                content = text if plain else '#text(' + json.dumps(text, ensure_ascii=False) + ')'
            (project / name).write_text(content + '\n')
            lines.append(f'#include "{name}"')
            provenance['blocks'].append({'original_id': block['id'], 'source_sha256': block['sha256'],
                'text': text, 'file': name, 'role': block['kind'], 'page': block.get('page'), 'plain': plain,
                'citations':block.get('citations',[]), 'section':block['section'],
                'document':block.get('document','main'), 'table':block.get('table')})
        lines.append('// <<< BODY END')
        (project / 'paper.typ').write_text('\n\n'.join(lines) + '\n')
        write_json(project / 'pra-port.json', provenance)
        originals = project / 'source'
        originals.mkdir()
        for name, sha in read_json(source / 'manifest.json')['files'].items():
            if name not in ('original.pdf', 'original.xml') and not name.startswith('supplements/'):
                continue
            target = originals / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
            if digest(target.read_bytes()) != sha:
                raise ValueError('Source changed while porting')
        result = import_scaffold(project, output, title=paper['title'])
    return result


def port_context(root, blocks):
    """Decode literal prose with exact string spans while keeping code locked."""
    path = root / 'pra-port.json'
    if not path.is_file():
        return None
    port = read_json(path)
    records = {row['file']: row for row in port['blocks'] if row['role'] != 'abstract'}
    result = []
    for block in blocks:
        # Include directives route the document and are not manuscript prose.
        if block['source_id'] == 'paper.typ' and block['text'].startswith('#include '):
            continue
        row = records.get(block['source_id'])
        if row:
            if row['role'] == 'heading' and block['text'] == '= ' + row['text']:
                block['text'] = row['text']
                block['sha256'] = digest(block['text'])
            literal = literal_value(block['text'])
            if literal:
                value, start, end = literal
                block['text'] = value
                block['sha256'] = digest(block['text'])
                block['kind'] = 'reference' if row['role'] == 'reference' else row['role']
                block['source_span'] = None
                block['locked'] = True
                if row['role'] == 'paragraph':
                    location = block['source_location']
                    block['source_span'] = {**location, 'start': location['start'] + start,
                        'end': location['start'] + end, 'encoding': 'json-string'}
                    block['editable'] = True
                    block['locked'] = False
                    block.pop('lock_reason', None)
            block['origin_block_id'] = row['original_id']
            block['page'] = row.get('page')
            block['page_mapping'] = 'original_pdf'
            block['citations'] = row.get('citations', [])
            block['section'] = row.get('section', block['section'])
            block['document'] = row.get('document', block['document'])
            if row['role'] == 'table':
                block['table'] = row.get('table') or [line.split('\t') for line in block['text'].splitlines()]
        result.append(block)
    config = (root / 'config.typ').read_bytes().decode('utf-8')
    abstracts = []
    rows = [row for row in port['blocks'] if row['role'] == 'abstract']
    declaration = re.search(r'(?m)^#let paper-abstract = \[\n(.*?)\n\]\n', config, re.S)
    if declaration is None:
        raise ValueError('Ported abstract declaration is missing')
    expressions = list(TEXT_LITERAL.finditer(declaration.group(1)))
    if len(expressions) != len(rows) or TEXT_LITERAL.sub('', declaration.group(1)).strip():
        raise ValueError('Ported abstract must contain only its literal text declarations')
    for row, expression in zip(rows, expressions):
        value = literal_value(expression.group())[0]
        start = declaration.start(1) + expression.start()
        span = {'file': 'config.typ', 'start': declaration.start(1) + expression.start(1),
                'end': declaration.start(1) + expression.end(1), 'encoding': 'json-string',
                'file_sha256': digest((root/'config.typ').read_bytes())}
        abstracts.append({'id': 'port-' + row['original_id'], 'origin_block_id': row['original_id'],
            'text': value, 'sha256': digest(value), 'section': 'Abstract', 'kind': 'paragraph',
            'source_id': 'config.typ', 'source_span': span, 'editable': True, 'locked': False,
            'source_location': {'file':'config.typ','start':start,'end':start+len(expression.group()),
                                'file_sha256':digest((root/'config.typ').read_bytes())},
            'page':row.get('page'), 'page_mapping':'original_pdf', 'bbox':None,
            'citations':row.get('citations',[]), 'document':'main', 'table':None})
    blocks[:] = abstracts + result
    return port
