"""Prepare selected public held-out domain manuscripts without review histories."""
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from paper_workspace.ingest import import_paper
from paper_workspace.storage import digest, read, write


ROOT = Path(__file__).resolve().parents[2] / 'runs/pra-domains-v1/heldout-inputs'
PAPERS = {
    'chemistry': {
        'doi': '10.1371/journal.pone.0314208',
        'figures': [1, 3, 7],
        'basis': 'Experimental nanoparticle synthesis and materials characterization with several condition-dependent physical and biological claims.',
        'records': [{'provider': 'crossref', 'identifier': '10.1371/journal.pone.0314208'}],
        'included': 'Published main XML and PDF. No scientific supplement was supplied by the article.',
        'omitted': 'Publisher review attachments, author responses, raw instrument data, and external datasets.'
    },
    'health': {
        'doi': '10.1371/journal.pone.0308923',
        'figures': [1],
        'basis': 'Registered randomized health intervention with participant flow, attrition, and reported clinical outcomes.',
        'records': [
            {'provider': 'crossref', 'identifier': '10.1371/journal.pone.0308923'},
            {'provider': 'clinicaltrials', 'identifier': 'NCT04718974'}
        ],
        'included': 'Published main XML and PDF.',
        'omitted': 'Large manuscript dataset, analysis files, publisher review attachments, author responses, and external patient data.'
    },
    'ecology': {
        'doi': '10.1371/journal.pone.0309939',
        'figures': [1, 2, 3],
        'basis': 'Field introduction of managed honey bees with spatial sampling, biodiversity outcomes, and taxonomic claims.',
        'records': [
            {'provider': 'crossref', 'identifier': '10.1371/journal.pone.0309939'},
            {'provider': 'gbif', 'identifier': '1341976'}
        ],
        'included': 'Published main XML and PDF plus the small scientific spatial-autocorrelation figure supplement.',
        'omitted': 'Large species tables, raw observations, remaining supplements, publisher review attachments, and author responses.'
    }
}


def sanitize_xml(source, target):
    tree = ET.parse(source)
    root = tree.getroot()
    blocked = re.compile(r'(response to reviewer|review comments|point by point response)', re.I)
    for parent in root.iter():
        for child in list(parent):
            tag = child.tag.rsplit('}', 1)[-1]
            text = ' '.join(''.join(child.itertext()).split())
            if tag == 'sub-article' or (tag == 'supplementary-material' and blocked.search(text)):
                parent.remove(child)
    tree.write(target, encoding='utf-8', xml_declaration=True)


def figure_pages(pdf, numbers):
    pages = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True).split('\f')
    chosen = []
    for number in numbers:
        pattern = re.compile(r'^\s*(?:Fig|Figure)\s+' + str(number) + r'\.', re.M)
        page = next((i for i, text in enumerate(pages, 1) if pattern.search(text)), None)
        if page is not None and page not in chosen:
            chosen.append(page)
    return chosen


def prepare(key):
    item = PAPERS[key]
    root = ROOT / key
    source = root / 'sources'
    pdf = source / 'main.pdf'
    xml = source / 'main.xml'
    imported = source / 'import.xml'
    sanitize_xml(xml, imported)
    workspace = root / 'workspace'
    if not (workspace / 'paper.json').exists():
        supplements = source / 'supplements'
        import_paper(pdf, workspace, xml=imported,
                     source_url='https://journals.plos.org/plosone/article?id=' + item['doi'],
                     supplements=supplements if supplements.exists() else None)
    paper = read(workspace / 'paper.json')
    if paper['statistics']['total_words'] >= 18000:
        raise ValueError(key + ' exceeds the held-out word limit')
    images = []
    for page in figure_pages(pdf, item['figures']):
        ident = 'figure-page-' + str(page)
        prefix = root / 'images' / ident
        prefix.parent.mkdir(exist_ok=True)
        target = prefix.with_suffix('.png')
        if not target.exists():
            subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-singlefile',
                            '-scale-to', '1900', '-png', str(pdf), str(prefix)],
                           check=True, capture_output=True)
        images.append({'id': ident, 'path': str(target.resolve()),
                       'label': 'Main PDF page ' + str(page) + ' with representative figures',
                       'sha256': digest(target.read_bytes())})
    write(root / 'images.json', images)
    source_urls = {
        'article': 'https://journals.plos.org/plosone/article?id=' + item['doi'],
        'xml': 'https://journals.plos.org/plosone/article/file?id=' + item['doi'] + '&type=manuscript',
        'pdf': 'https://journals.plos.org/plosone/article/file?id=' + item['doi'] + '&type=printable'
    }
    if key == 'ecology':
        source_urls['supplement'] = 'https://doi.org/10.1371/journal.pone.0309939.s011'
    selection = {
        'key': key,
        'doi': item['doi'],
        'title': paper['title'],
        'source_urls': source_urls,
        'selection_basis': item['basis'] + ' Selected before workspace generation.',
        'scope': item['included'],
        'omitted_assets': item['omitted'],
        'candidate_records': item['records'],
        'human_review_histories_read': False,
        'word_counts': paper['statistics'],
        'images': images,
        'source_files': {str(path.relative_to(source)): digest(path.read_bytes())
                         for path in sorted(source.rglob('*')) if path.is_file()}
    }
    write(root / 'selection.json', selection)
    return selection


if __name__ == '__main__':
    selections = [prepare(key) for key in ('chemistry', 'health', 'ecology')]
    write(ROOT / 'selection.json', {'papers': selections,
          'selection_frozen_before_generation': True,
          'human_review_histories_read': False})
    print(json.dumps([{'key': row['key'], 'title': row['title'],
                       'words': row['word_counts']['total_words'],
                       'images': len(row['images'])} for row in selections], ensure_ascii=False))
