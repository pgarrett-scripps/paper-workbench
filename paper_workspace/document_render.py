"""Render rich ported exports while keeping document changes traceable."""
import re
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unicodedata


def remove_flattened_tables(docx_path, blocks, embedded_table_texts):
    """Remove exact text duplicates after structured source tables are embedded."""
    from docx import Document
    def normalized(value):
        return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value))
    embedded = {normalized(text) for text in embedded_table_texts}
    tables = {normalized(block['text']) for block in blocks
              if block.get('kind') == 'table' and normalized(block['text']) in embedded}
    table_documents = {block.get('document') for block in blocks
                       if block.get('kind') == 'table' and normalized(block['text']) in tables}
    labels = {normalized(block['text']) for block in blocks if block.get('kind') == 'supplement'
              and block.get('document') in table_documents and re.fullmatch(r'S\d+ Table', block['text'])}
    document = Document(docx_path)
    removed = []
    for paragraph in list(document.paragraphs):
        text = normalized(paragraph.text)
        if text in tables:
            removed.append(text)
            paragraph._element.getparent().remove(paragraph._element)
        elif text in labels and paragraph.style.name not in ('Heading 1', 'Heading 2'):
            paragraph._element.getparent().remove(paragraph._element)
    if len(removed) != len(tables):
        raise ValueError('Could not locate every flattened table before structured export')
    document.save(docx_path)
    return len(removed)


def render_word_pdf(docx_path, destination):
    """Use an isolated local LibreOffice profile and fail on missing output."""
    executable = shutil.which('soffice') or shutil.which('libreoffice')
    if not executable:
        raise ValueError('Rich PDF export requires local LibreOffice')
    docx_path, destination = Path(docx_path).resolve(), Path(destination).resolve()
    with tempfile.TemporaryDirectory(prefix='.word-pdf-', dir=destination.parent) as temporary:
        stage = Path(temporary)
        profile = stage / 'profile'
        command = [executable, '-env:UserInstallation=' + profile.as_uri(), '--headless',
                   '--norestore', '--convert-to', 'pdf', '--outdir', str(stage), str(docx_path)]
        environment = {**os.environ, 'GSETTINGS_BACKEND': 'memory', 'SAL_USE_VCLPLUGIN': 'gen'}
        result = subprocess.run(command, capture_output=True, text=True, timeout=180, env=environment)
        rendered = stage / (docx_path.stem + '.pdf')
        if result.returncode or not rendered.is_file() or not rendered.read_bytes().startswith(b'%PDF-'):
            raise ValueError('Rich PDF export failed. ' + result.stderr[-1500:] + result.stdout[-500:])
        from pypdf import PdfReader
        pages = len(PdfReader(rendered).pages)
        if not pages:
            raise ValueError('Rich PDF export contains no pages')
        shutil.copyfile(rendered, destination)
        return {'tool': Path(executable).name, 'pages': pages, 'exit_code': result.returncode,
                'stdout': result.stdout, 'stderr': result.stderr}
