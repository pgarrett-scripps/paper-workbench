"""Prepare two new development sources without opening review histories."""
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

from paper_workspace.ingest import import_paper
from paper_workspace.scaffold_checks import build_report, compact_summary
from paper_workspace.storage import read, write, digest

ROOT = Path(__file__).resolve().parents[2] / 'runs/pra-transfer-two-v1'
PAPERS = {
    'sleep': ('plosone', '10.1371/journal.pone.0308652', [('S1_Fig.pdf', 1), ('S1_Fig.pdf', 2), ('S2_Fig.pdf', 1)]),
    'yeast': ('plosbiology', '10.1371/journal.pbio.3002491', [('S1_Fig.pdf', 1), ('S5_Fig.pdf', 1)]),
}


def prepare(key):
    root = ROOT / key
    source = root / 'sources'
    journal, doi, supplement_images = PAPERS[key]
    if not (root / 'workspace').exists():
        tree = ET.parse(source / 'main.xml')
        body = tree.getroot().find('body')
        for pdf in sorted((source / 'supplements').glob('*.pdf')):
            sec = ET.SubElement(body, 'sec')
            ET.SubElement(sec, 'title').text = 'Supplement extracted text ' + pdf.stem
            pages = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True).split('\f')
            for n, text in enumerate(pages, 1):
                if text.strip():
                    ET.SubElement(sec, 'p', {'id':pdf.stem + '-page-' + str(n)}).text = (
                        pdf.name + ' page ' + str(n) + '. Layout extraction, not reconstructed table rows.\n' + text.strip())
        tree.write(source / 'import.xml', encoding='utf-8', xml_declaration=True)
        import_paper(source / 'main.pdf', root / 'workspace', xml=source / 'import.xml',
                     source_url='https://journals.plos.org/' + journal + '/article?id=' + doi,
                     supplements=source / 'supplements')
    paper = read(root / 'workspace/paper.json')
    diagnostics = build_report(root / 'workspace', Path('/home/ty/Repos/paper-scaffold'))
    write(root / 'diagnostics.json', diagnostics)
    pages = subprocess.check_output(['pdftotext', '-layout', str(source / 'main.pdf'), '-'], text=True).split('\f')
    chosen = [(source / 'main.pdf', n, 'Main PDF page ' + str(n))
              for n, text in enumerate(pages, 1) if re.search(r'^\s*Fig\s+\d+\.', text, re.M)]
    chosen += [(source / 'supplements' / file, n, file + ' page ' + str(n)) for file, n in supplement_images]
    images = []
    for n, (pdf, page, label) in enumerate(chosen, 1):
        prefix = root / 'images' / ('image-' + str(n))
        prefix.parent.mkdir(exist_ok=True)
        target = prefix.with_suffix('.png')
        if not target.exists():
            subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-singlefile', '-scale-to', '1900', '-png', str(pdf), str(prefix)], check=True, capture_output=True)
        images.append({'id':'image-' + str(n), 'path':str(target), 'label':label, 'sha256':digest(target.read_bytes())})
    write(root / 'images.json', images)
    context = '\n\n'.join(f"[{b['id']}] {b['section']} | {b['kind']}\n{b['text']}" for b in paper['blocks'])
    context += '\nADVISORY PAPER SCAFFOLD CHECKS\n' + json.dumps(compact_summary(diagnostics), ensure_ascii=False)
    context += '\nSOURCE AVAILABILITY: Published article prose, references, figure captions, selected original figure pages, all supplementary figure PDF text, and available methods tables are supplied. Attached images are enumerated separately. PDF text extraction can flatten figure and table layout, so verify visual cell alignment in attached pages. Other supplementary pixels, videos, raw data, author code, external literature, and human review histories are unavailable. Do not infer absence from inaccessible material. Do not rerun author analyses. These are published versions, not the manuscripts originally peer reviewed.'
    write(root / 'context.json', {'text':context})
    write(root / 'source-selection.json', {
        'doi':doi, 'title':paper['title'], 'new_to_local_experiments':True,
        'selection_basis':'Unused experimental biology paper with public source materials and a different scientific focus from the other paper. Selected before generation.',
        'human_reviews_delivered':False, 'xml_subarticles_removed':True,
        'excluded':'Human review histories, raw datasets, movies, uncropped gel archive, and author code.',
        'images':images, 'source_files':{str(p.relative_to(source)):digest(p.read_bytes()) for p in source.rglob('*') if p.is_file()},
    })
    print(json.dumps({'paper':key, 'blocks':len(paper['blocks']), 'context_chars':len(context), 'images':len(images)}), flush=True)


if __name__ == '__main__':
    for key in PAPERS:
        prepare(key)
