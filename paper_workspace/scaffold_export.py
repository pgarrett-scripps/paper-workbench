"""Export a captured draft through explicitly selected Paper Scaffold tools."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from peerreviewagents.workspace import digest, write_json

from .export_evidence import append_supplements, preserve_source_evidence
from .revisions import snapshot


WORKER = '''
import json, sys, subprocess
from pathlib import Path
def diagnostic(kind, error, traceback):
    if isinstance(error, subprocess.CalledProcessError):
        print(error.stderr or '', file=sys.stderr)
    sys.__excepthook__(kind, error, traceback)
sys.excepthook = diagnostic
sys.path.insert(0, sys.argv[1])
from manuscript_snapshot import resolve_source, query_numbers, project_word
import export_docx
root = Path(sys.argv[2])
stats_path, assets_path = root / 'stats-rendered.json', root / 'assets.json'
stats = json.loads(stats_path.read_text()).get('values', {}) if stats_path.exists() else {}
assets = json.loads(assets_path.read_text()).get('values', {}) if assets_path.exists() else {}
for path in root.rglob('*.typ'):
    if path.name in ('stats.typ', 'assets.typ', 'wordcount.typ'):
        continue
    path.write_text(resolve_source(path.read_text(), stats, assets, str(path.relative_to(root))))
front = root / 'front-matter.json'
numbers = query_numbers(root, front_matter=front)
project_word(root, numbers, front_matter=front)
export_docx.ROOT = root
export_docx.SRC = root / 'paper.word.typ'
export_docx.OUT = Path(sys.argv[3])
raise SystemExit(export_docx.main())
'''


def normalize_heading_colors(path):
    """Keep editable Word headings black when Pandoc supplies its default styles."""
    with zipfile.ZipFile(path) as archive:
        entries = [(item, archive.read(item)) for item in archive.infolist()]
    namespace = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    w = '{' + namespace + '}'
    ET.register_namespace('w', namespace)
    styles = ET.fromstring(next(data for item, data in entries if item.filename == 'word/styles.xml'))
    for style in styles.findall(w + 'style'):
        identifier = style.get(w + 'styleId', '').lower()
        if identifier not in ('title', 'subtitle') and not identifier.startswith('heading'):
            continue
        run = style.find(w + 'rPr')
        if run is None:
            run = ET.SubElement(style, w + 'rPr')
        color = run.find(w + 'color')
        if color is None:
            color = ET.SubElement(run, w + 'color')
        color.attrib.clear()
        color.set(w + 'val', '000000')
    rendered = ET.tostring(styles, encoding='utf-8', xml_declaration=True)
    with zipfile.ZipFile(path, 'w') as archive:
        for item, data in entries:
            archive.writestr(item, rendered if item.filename == 'word/styles.xml' else data)


def export_revision(root, revision_id, output, scaffold_root, python=None):
    """No source analysis scripts or project build recipes are executed."""
    source, paper = snapshot(root, revision_id)
    if paper.get('source_format') != 'scaffold-typst':
        raise ValueError('Native document export requires Paper Scaffold sources')
    output = Path(output).resolve()
    workspace = Path(root).resolve()
    if output.exists():
        raise ValueError('Export output already exists')
    if output.is_relative_to(source / 'scaffold'):
        raise ValueError('Export output cannot be inside immutable sources')
    if output.is_relative_to(workspace) and output.relative_to(workspace).parts[0] != 'exports':
        raise ValueError('Exports inside a workspace must use its exports directory')
    tools = Path(scaffold_root).resolve() / 'tools'
    for name in ('manuscript_snapshot.py', 'resolve_typst.py', 'export_docx.py'):
        if not (tools / name).is_file():
            raise ValueError('Selected Paper Scaffold tools are incomplete')
    tool_hashes = {p.relative_to(tools).as_posix(): digest(p.read_bytes())
                   for p in sorted(tools.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.export-', dir=output.parent) as temp:
        stage = Path(temp)
        project = stage / 'project'
        shutil.copytree(source / 'scaffold', project)
        # The exporter prefers a project filter if present. Supply the selected
        # trusted tool version so manuscript-provided Lua is never executed.
        (project / 'tools').mkdir(exist_ok=True)
        shutil.copyfile(tools / 'refs_div.lua', project / 'tools/refs_div.lua')
        artifacts = stage / 'artifacts'
        artifacts.mkdir()
        commands = [
            ['typst', 'compile', '--root', str(project), str(project / 'paper.typ'), str(artifacts / 'paper.pdf')],
            [python or sys.executable, '-c', WORKER, str(tools), str(project), str(artifacts / 'paper.docx')],
        ]
        logs = []
        for command in commands:
            result = subprocess.run(command, cwd=stage, capture_output=True, text=True, timeout=180)
            logs.append({'tool': Path(command[0]).name, 'exit_code': result.returncode,
                         'stdout': result.stdout, 'stderr': result.stderr})
            if result.returncode:
                raise ValueError('Document export failed. Draft preserved. ' + result.stderr[-2000:] + result.stdout[-1000:])
        normalize_heading_colors(artifacts / 'paper.docx')
        evidence = None
        port = project / 'pra-port.json'
        if port.is_file():
            evidence, main_figures = preserve_source_evidence(
                project / 'source', artifacts / 'source-evidence', paper)
            supplements = project / 'source' / 'supplements'
            evidence.update(append_supplements(
                artifacts / 'paper.docx', supplements, paper.get('blocks', []), main_figures))
            if evidence.get('tables_embedded'):
                from .document_render import remove_flattened_tables
                evidence['flattened_tables_removed'] = remove_flattened_tables(
                    artifacts / 'paper.docx', paper['blocks'], evidence.pop('embedded_table_texts'))
            from .document_render import render_word_pdf
            (artifacts / 'paper.pdf').rename(artifacts / 'source-build.pdf')
            logs.append(render_word_pdf(artifacts / 'paper.docx', artifacts / 'paper.pdf'))
        snapshot(root, revision_id)
        if any(digest((tools / name).read_bytes()) != sha for name, sha in tool_hashes.items()):
            raise ValueError('Scaffold tools changed during export')
        record = {'paper_id': paper['id'], 'revision_id': revision_id,
                  'source_sha256': paper['source_sha256'], 'tools': tool_hashes, 'logs': logs,
                  'files': {p.relative_to(artifacts).as_posix(): digest(p.read_bytes())
                            for p in artifacts.rglob('*') if p.is_file()},
                  'format': ('Editable Word and a PDF rendered from the same document for ported manuscripts. '
                             'Verified source evidence is retained separately for ported manuscripts. '
                             'Review history is stored in the workspace.'),
                  'source_evidence': evidence,
                  'limitations': ['Word layout and citation style can differ from the compiled PDF.',
                                  'A local CSL file is needed to reproduce a specified citation style.',
                                  'Word tracked changes and embedded review comments are not exported.',
                                  'Ported reading copies do not reconstruct publisher layout.',
                                  'For ported manuscripts, source-build.pdf is the text-only Typst build and paper.pdf renders the rich Word document.'],
                  'visual_qa': 'Not performed by the exporter. Inspect rendered outputs before publication.'}
        write_json(artifacts / 'export.json', record)
        artifacts.rename(output)
    return record
