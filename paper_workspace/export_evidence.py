"""Preserve verified source evidence in exports from ported manuscripts."""
from copy import deepcopy
import json
from pathlib import Path
import re
import shutil

from .storage import digest


def _natural(path):
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r'(\d+)', path.name)]


def _figure_captions(blocks):
    captions = {}
    for block in blocks:
        text = block.get('text', '')
        match = re.match(r'(S\d+) Fig\s+(.+)', text)
        if match:
            captions[match.group(1) + '_Fig'] = text.removesuffix(' (TIF)')
    return captions


def append_supplements(docx_path, supplements, blocks, main_figures=()):
    """Append verified main figures, supplements, and tables to a reading copy."""
    from docx import Document
    from docx.enum.section import WD_ORIENT, WD_SECTION
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt

    supplements = Path(supplements)
    figures = sorted(supplements.glob('S*_Fig.png'), key=_natural)
    tables = sorted(supplements.glob('S*_Table.docx'), key=_natural)
    main_figures = list(main_figures)
    if not main_figures and not figures and not tables:
        return {'main_figures_embedded': 0, 'figures_embedded': 0, 'tables_embedded': 0}

    doc = Document(docx_path)
    embedded_table_texts = []
    previous = doc.sections[-1]
    previous_width = previous.page_width or Inches(8.5)
    previous_height = previous.page_height or Inches(11)
    section = doc.add_section(WD_SECTION.NEW_PAGE)
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = previous_height, previous_width
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)
    heading = doc.add_heading('Verified source figures and supplementary materials', level=1)
    heading.paragraph_format.space_after = Pt(8)
    note = doc.add_paragraph(
        'The following figures and tables come from the verified source package. '
        'Main figures are extracted from publisher PDF image objects. Supplementary files are exact source copies. '
        'These materials preserve supplied evidence and do not reconstruct the publisher layout.'
    )
    note.paragraph_format.space_after = Pt(10)

    captions = _figure_captions(blocks)
    usable_width = section.page_width - section.left_margin - section.right_margin
    usable_height = section.page_height - section.top_margin - section.bottom_margin - Inches(2.8)
    all_figures = []
    for item in main_figures:
        all_figures.append((Path(item['path']), item['caption'],
                            'Extracted from the publisher PDF on source page ' + str(item['page']) + '.'))
    for image in figures:
        label = image.stem.replace('_', ' ')
        all_figures.append((image, captions.get(image.stem, label), None))

    for index, (image, figure_caption, provenance) in enumerate(all_figures):
        if index:
            doc.add_page_break()
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        from PIL import Image
        with Image.open(image) as source_image:
            ratio = source_image.width / source_image.height
        width = usable_width
        height = int(width / ratio)
        if height > usable_height:
            height = usable_height
            width = int(height * ratio)
        paragraph.add_run().add_picture(str(image), width=width, height=height)
        caption = doc.add_paragraph(figure_caption)
        caption.style = 'Caption'
        caption.paragraph_format.keep_with_next = False
        if provenance:
            source_note = doc.add_paragraph(provenance)
            source_note.paragraph_format.space_after = Pt(4)

    for table_path in tables:
        source = Document(table_path)
        title = doc.add_heading(table_path.stem.replace('_', ' '), level=2)
        title.paragraph_format.page_break_before = True
        title.paragraph_format.keep_with_next = True
        seen_table = False
        for element in source._body._body:
            if element.tag.endswith('}tbl'):
                seen_table = True
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                rows = [[' '.join(re.sub(r'\s+', ' ', ''.join(node.text or '' for node in paragraph.findall('.//w:t', ns))).strip()
                                 for paragraph in cell.findall('w:p', ns))
                         for cell in row.findall('w:tc', ns)] for row in element.findall('w:tr', ns)]
                embedded_table_texts.append('\n'.join('\t'.join(row) for row in rows))
            if element.tag.endswith('}sectPr') or (not seen_table and element.tag.endswith('}p')):
                continue
            copied = deepcopy(element)
            if copied.tag.endswith('}tbl'):
                properties = next((child for child in copied if child.tag.endswith('}tblPr')), None)
                if properties is not None:
                    for child in list(properties):
                        if child.tag.endswith('}tblpPr'):
                            properties.remove(child)
            body = doc._body._body
            insertion = len(body) - 1 if body[-1].tag.endswith('}sectPr') else len(body)
            body.insert(insertion, copied)
        doc.add_paragraph('Source file: ' + table_path.name)

    doc.save(docx_path)
    return {'main_figures_embedded': len(main_figures),
            'figures_embedded': len(figures), 'tables_embedded': len(embedded_table_texts),
            'embedded_table_texts': embedded_table_texts}


def extract_main_figures(original_pdf, destination, paper):
    """Losslessly extract unambiguous large image objects from recorded figure pages."""
    from pypdf import PdfReader

    original_pdf = Path(original_pdf)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(original_pdf)
    captions_by_page = {}
    for block in paper.get('blocks', []):
        match = re.match(r'Fig\s+(\d+)\s+(.+)', block.get('text', ''))
        page = block.get('page')
        if block.get('kind') == 'caption' and match and isinstance(page, int):
            captions_by_page.setdefault(page, []).append((int(match.group(1)), block))

    extracted = []
    fallbacks = []
    for page, captions in sorted(captions_by_page.items()):
        if len(captions) != 1:
            fallbacks.append({'page': page, 'reason': 'main_caption_count', 'count': len(captions)})
            continue
        if not 1 <= page <= len(reader.pages):
            fallbacks.append({'page': page, 'reason': 'page_out_of_range'})
            continue
        images = list(reader.pages[page - 1].images)
        if len(images) != 1:
            fallbacks.append({'page': page, 'reason': 'pdf_image_count', 'count': len(images)})
            continue
        number, block = captions[0]
        image = images[0]
        width, height = image.image.size
        if image.image.mode != 'RGB' or width < 1000 or height < 1000:
            fallbacks.append({'page': page, 'reason': 'image_not_large_rgb',
                              'mode': image.image.mode, 'width': width, 'height': height})
            continue
        suffix = Path(image.name).suffix.lower()
        if suffix not in ('.jpg', '.jpeg'):
            fallbacks.append({'page': page, 'reason': 'image_not_jpeg', 'name': image.name})
            continue
        filename = f'figure-{number}-publisher-pdf-page-{page}.jpg'
        path = destination / filename
        path.write_bytes(image.data)
        extracted.append({
            'figure': number,
            'page': page,
            'origin_block_id': block.get('origin_block_id') or block.get('id'),
            'caption': block['text'],
            'path': str(path),
            'file': filename,
            'sha256': digest(image.data),
            'source_pdf_sha256': digest(original_pdf.read_bytes()),
            'pdf_image_name': image.name,
            'mode': image.image.mode,
            'width': width,
            'height': height,
            'provenance': 'Lossless extraction of the sole large RGB JPEG image object on the recorded publisher PDF page.',
        })
    return extracted, fallbacks


def preserve_source_evidence(source, destination, paper):
    """Copy source assets and extract exact PDF pages that contain main figures."""
    from pypdf import PdfReader, PdfWriter

    source = Path(source)
    destination = Path(destination)
    destination.mkdir(parents=True)
    copied = []
    for name in ('original.pdf', 'original.xml'):
        path = source / name
        if path.is_file():
            shutil.copy2(path, destination / name)
            copied.append(destination / name)
    supplements = source / 'supplements'
    if supplements.is_dir():
        shutil.copytree(supplements, destination / 'supplements')
        copied.extend(path for path in (destination / 'supplements').rglob('*') if path.is_file())

    pages = sorted({block['page'] for block in paper.get('blocks', [])
                    if block.get('kind') == 'caption'
                    and re.match(r'Fig\s+\d+', block.get('text', ''))
                    and isinstance(block.get('page'), int)})
    figure_pdf = None
    original = source / 'original.pdf'
    main_figures = []
    extraction_fallbacks = []
    if original.is_file():
        main_figures, extraction_fallbacks = extract_main_figures(
            original, destination / 'main-figures', paper)
        copied.extend(destination / 'main-figures' / item['file'] for item in main_figures)
    if pages and original.is_file():
        reader = PdfReader(original)
        writer = PdfWriter()
        for page in pages:
            if not 1 <= page <= len(reader.pages):
                raise ValueError('Main figure source page is outside the original PDF')
            writer.add_page(reader.pages[page - 1])
        figure_pdf = destination / 'main-figure-source-pages.pdf'
        with figure_pdf.open('wb') as stream:
            writer.write(stream)
        copied.append(figure_pdf)

    manifest = {
        'purpose': 'Exact source evidence retained with a ported manuscript reading copy.',
        'main_figure_pages': pages,
        'main_figure_page_artifact': figure_pdf.name if figure_pdf else None,
        'main_figure_extractions': [{key: value for key, value in item.items() if key != 'path'}
                                    for item in main_figures],
        'main_figure_extraction_fallbacks': extraction_fallbacks,
        'limitations': [
            'Main figures are preserved as complete publisher PDF pages because standalone originals were not supplied.',
            'Supplementary assets are exact source copies. Their inclusion does not reconstruct publisher layout.',
        ],
        'files': {path.relative_to(destination).as_posix(): digest(path.read_bytes())
                  for path in sorted(copied)},
    }
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    return manifest, main_figures
