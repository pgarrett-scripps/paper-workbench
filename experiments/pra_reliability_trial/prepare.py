"""Prepare two preselected fresh manuscripts for the bounded reliability trial."""
import argparse
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from paper_workspace.annotations import verify_workspace
from paper_workspace.external_evidence import SourceClient
from paper_workspace.ingest import import_paper
from paper_workspace.model_runtime import source_manifest
from paper_workspace.storage import digest, read, write


REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / 'runs/pra-reliability-trial-v1'
PAPERS = {
    'health': {
        'doi': '10.1371/journal.pone.0312992',
        'figures': [1, 2, 3],
        'basis': 'Online exercise randomized trial in older adults with a prespecified public registration.',
        'records': [('crossref', '10.1371/journal.pone.0312992'), ('clinicaltrials', 'NCT04627493')],
        'excluded_attachments': [
            {'id': 'pone.0312992.s003', 'description': 'Minimal dataset XLSX, omitted as raw participant-level trial data'},
            {'id': 'pone.0312992.s005', 'description': 'Author response PDF, omitted as human review history'},
        ],
        'derived_assets': [
            {'source': 'supplements/s2-consort-checklist.pdf', 'derived': 'supplements/s2-consort-checklist-text.docx',
             'method': 'pdftotext layout extraction followed by Pandoc DOCX conversion'},
            {'source': 'supplements/s4-protocol.pdf', 'derived': 'supplements/s4-protocol-text.docx',
             'method': 'pdftotext layout extraction followed by Pandoc DOCX conversion'},
        ],
    },
    'ecology': {
        'doi': '10.1371/journal.pone.0314791',
        'figures': [1, 2, 3],
        'basis': 'Field warming experiment involving honey bees, selected to exercise ecological design and result checks.',
        'records': [('crossref', '10.1371/journal.pone.0314791')],
        'excluded_attachments': [
            {'id': 'pone.0314791.s002', 'description': 'Reviewer comments PDF, omitted as human review history'},
            {'id': 'pone.0314791.s003', 'description': 'Author response DOCX, omitted as human review history'},
        ],
        'derived_assets': [],
    },
}


def normalize_doi(value):
    if not isinstance(value, str):
        return ''
    match = re.search(r'10\.\d{4,9}/[^\s?#"<>]+', value, re.I)
    return match.group(0).rstrip('.,/)').lower() if match else ''


def build_prior_corpus():
    """Inventory local manuscript identities without reading review prose."""
    records = []
    excluded_root = ROOT.resolve()
    for path in sorted((REPO / 'runs').glob('**/paper.json')):
        if excluded_root in path.resolve().parents:
            continue
        try:
            paper = read(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        doi = normalize_doi(paper.get('source_url', ''))
        if not doi:
            for parent in list(path.parents)[:4]:
                selection = parent / 'selection.json'
                if selection.is_file():
                    try:
                        doi = normalize_doi(read(selection).get('doi', ''))
                    except (OSError, ValueError, json.JSONDecodeError):
                        pass
                    if doi:
                        break
        records.append({'paper_id': paper.get('id', ''), 'doi': doi,
                        'title': paper.get('title', ''),
                        'source_kind': 'workspace',
                        'source_path': str(path.relative_to(REPO))})
    for path in sorted((REPO / 'docs/reviews').glob('**/provenance.json')):
        try:
            provenance = read(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        preprint = provenance.get('preprint') or {}
        title = preprint.get('title', '')
        doi = normalize_doi(preprint.get('doi', '') or preprint.get('identifier', '') or preprint.get('url', ''))
        paper_id = preprint.get('pdf_sha256', '') or (provenance.get('ingest') or {}).get('file_sha256', '')
        if title or doi or paper_id:
            records.append({'paper_id': paper_id, 'doi': doi, 'title': title,
                            'source_kind': 'review_metadata',
                            'source_path': str(path.relative_to(REPO))})
    for path in sorted((REPO / 'docs/reviews').glob('**/round.json')):
        try:
            round_metadata = read(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        title = round_metadata.get('manuscript_title', '')
        paper_id = round_metadata.get('manuscript_file_sha256', '')
        if title or paper_id:
            records.append({'paper_id': paper_id, 'doi': '', 'title': title,
                            'source_kind': 'review_round_metadata',
                            'source_path': str(path.relative_to(REPO))})
    groups = []
    for row in records:
        title_key = row['title'].strip().casefold()
        matching = [group for group in groups if
                    (row['doi'] and row['doi'] in group['dois']) or
                    (row['paper_id'] and row['paper_id'] in group['paper_ids']) or
                    (title_key and title_key in group['titles'])]
        if matching:
            current = matching[0]
            for duplicate in matching[1:]:
                for field in ('dois', 'paper_ids', 'titles', 'source_kinds', 'source_paths'):
                    current[field].update(duplicate[field])
                for display_title in duplicate['display_titles']:
                    if display_title not in current['display_titles']:
                        current['display_titles'].append(display_title)
                groups.remove(duplicate)
        else:
            current = {'dois': set(), 'paper_ids': set(), 'titles': set(),
                       'display_titles': [], 'source_kinds': set(), 'source_paths': set()}
            groups.append(current)
        if row['doi']:
            current['dois'].add(row['doi'])
        if row['paper_id']:
            current['paper_ids'].add(row['paper_id'])
        if title_key:
            current['titles'].add(title_key)
        if row['title'] and row['title'] not in current['display_titles']:
            current['display_titles'].append(row['title'])
        current['source_kinds'].add(row['source_kind'])
        current['source_paths'].add(row['source_path'])
    papers = []
    for group in groups:
        papers.append({'paper_id': sorted(group['paper_ids'])[0] if group['paper_ids'] else '',
                       'alternate_paper_ids': sorted(group['paper_ids'])[1:],
                       'doi': sorted(group['dois'])[0] if group['dois'] else '',
                       'alternate_dois': sorted(group['dois'])[1:],
                       'title': group['display_titles'][0] if group['display_titles'] else '',
                       'alternate_titles': group['display_titles'][1:],
                       'source_kinds': sorted(group['source_kinds']),
                       'source_paths': sorted(group['source_paths'])})
    papers.sort(key=lambda row: (row['doi'], row['title'].casefold(), row['paper_id']))
    value = {
        'papers': papers,
        'coverage': {
            'run_paper_json_files': sum(row['source_kind'] == 'workspace' for row in records),
            'review_provenance_files_with_identity': sum(row['source_kind'] == 'review_metadata' for row in records),
            'review_round_files_with_identity': sum(row['source_kind'] == 'review_round_metadata' for row in records),
            'deduplicated_papers': len(papers),
            'searched_paths': ['runs/**/paper.json', 'docs/reviews/**/provenance.json',
                               'docs/reviews/**/round.json'],
            'excluded_paths': ['runs/pra-reliability-trial-v1/**'],
            'limitations': [
                'Review prose was not read. Only workspace paper records and review provenance metadata were inspected.',
                'Records are deduplicated when any available DOI, paper ID, or normalized title matches.',
                'Local files can only establish absence from the locally available corpus.',
            ],
        },
    }
    write(ROOT / 'prior-corpus.json', value)
    return value


def sanitize_xml(source, target):
    tree = ET.parse(source)
    root = tree.getroot()
    blocked = re.compile(r'(response to reviewer|review comments|point by point response|peer review)', re.I)
    removed = []
    for parent in root.iter():
        for child in list(parent):
            tag = child.tag.rsplit('}', 1)[-1]
            text = ' '.join(''.join(child.itertext()).split())
            if tag == 'sub-article' or (tag == 'supplementary-material' and blocked.search(text)):
                removed.append({'tag': tag, 'id': child.get('id', ''), 'reason': 'review or sub-article exclusion'})
                parent.remove(child)
    tree.write(target, encoding='utf-8', xml_declaration=True)
    return removed


def figure_pages(pdf, numbers):
    pages = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True).split('\f')
    chosen = []
    for number in numbers:
        pattern = re.compile(r'^\s*(?:Fig|Figure)\s+' + str(number) + r'[.:]', re.M | re.I)
        page = next((i for i, text in enumerate(pages, 1) if pattern.search(text)), None)
        if page and page not in chosen:
            chosen.append(page)
    return chosen[:3]


def ensure_derived_assets(source, item):
    for asset in item['derived_assets']:
        original = source / asset['source']
        derived = source / asset['derived']
        text = derived.with_suffix('.txt')
        if not derived.exists():
            subprocess.run(['pdftotext', '-layout', str(original), str(text)], check=True,
                           capture_output=True)
            subprocess.run(['pandoc', str(text), '-o', str(derived)], check=True,
                           capture_output=True)


def prepare_paper(key):
    item = PAPERS[key]
    root = ROOT / 'inputs' / key
    source = root / 'sources'
    ensure_derived_assets(source, item)
    removed = sanitize_xml(source / 'main.xml', source / 'import.xml')
    workspace = root / 'workspace'
    if not (workspace / 'paper.json').exists():
        supplements = source / 'supplements'
        import_paper(source / 'main.pdf', workspace, xml=source / 'import.xml',
                     source_url='https://journals.plos.org/plosone/article?id=' + item['doi'],
                     supplements=supplements if supplements.exists() else None)
    paper = verify_workspace(workspace)
    images = []
    for page in figure_pages(source / 'main.pdf', item['figures']):
        ident = 'figure-page-' + str(page)
        prefix = root / 'images' / ident
        prefix.parent.mkdir(parents=True, exist_ok=True)
        target = prefix.with_suffix('.png')
        if not target.exists():
            subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-singlefile',
                            '-scale-to', '1900', '-png', str(source / 'main.pdf'), str(prefix)],
                           check=True, capture_output=True)
        images.append({'id': ident, 'path': str(target.resolve()),
                       'label': 'Main PDF page ' + str(page) + ' containing a selected figure',
                       'sha256': digest(target.read_bytes())})
    write(root / 'images.json', images)
    files = {str(path.relative_to(source)): digest(path.read_bytes())
             for path in sorted(source.rglob('*')) if path.is_file()}
    included_supplements = [str(p.relative_to(source)) for p in sorted((source / 'supplements').glob('*'))]
    selection = {
        'key': key,
        'doi': item['doi'],
        'title': paper['title'],
        'paper_id': paper['id'],
        'selection_basis': item['basis'] + ' Selected by DOI before scientific quality inspection or generation.',
        'freshness_check': 'Absent from the locally searched prior corpus before download and preparation.',
        'source_urls': {
            'article': 'https://journals.plos.org/plosone/article?id=' + item['doi'],
            'xml': 'https://journals.plos.org/plosone/article/file?id=' + item['doi'] + '&type=manuscript',
            'pdf': 'https://journals.plos.org/plosone/article/file?id=' + item['doi'] + '&type=printable',
        },
        'scope': 'Published main XML and PDF' + (', plus bounded small supplements' if included_supplements else ''),
        'included_supplements': included_supplements,
        'omitted_assets': [
            'Publisher peer-review histories and author responses',
            'Raw or large research datasets',
            'Analysis environments and complete reruns',
            'Supplements that were large, duplicative, inaccessible, or not needed for bounded manuscript review',
        ],
        'explicitly_excluded_source_attachments': item['excluded_attachments'],
        'derived_assets': item['derived_assets'],
        'sanitization_removals': removed,
        'candidate_records': [{'provider': p, 'identifier': i} for p, i in item['records']],
        'human_review_histories_read': False,
        'word_counts': paper['statistics'],
        'images': images,
        'source_files': files,
    }
    write(root / 'selection.json', selection)
    return selection


def prepare_packet(key):
    packet = ROOT / 'packets' / key
    client = SourceClient(ROOT / 'packet-preparation' / key, packet, limit=6,
                          cutoff='2026-09-25')
    statuses = []
    for provider, identifier in PAPERS[key]['records']:
        card = client.lookup(provider, identifier, 'public-source-preparation')
        statuses.append({'provider': provider, 'identifier': identifier,
                         'status': card['status'], 'eligible': card.get('eligible', False),
                         'evidence_id': card.get('evidence_id')})
    index = {
        'records': statuses,
        'limitation': 'Finite current public-source packet frozen before review generation. It does not establish historical registry state or exhaustive literature coverage.',
    }
    write(packet / 'index.json', index)
    return index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('inputs', 'packets', 'all'))
    args = parser.parse_args()
    build_prior_corpus()
    results = {}
    for key in PAPERS:
        if args.stage in ('inputs', 'all'):
            results[key] = prepare_paper(key)
        if args.stage in ('packets', 'all'):
            results.setdefault(key, {})['packet'] = prepare_packet(key)
    write(ROOT / 'inputs' / 'selection.json', {
        'papers': [read(ROOT / 'inputs' / key / 'selection.json') for key in PAPERS],
        'selection_frozen_before_generation': True,
        'human_review_histories_read': False,
    })
    print(json.dumps({key: {'title': value.get('title'),
                            'words': value.get('word_counts', {}).get('total_words'),
                            'images': len(value.get('images', [])),
                            'packet': value.get('packet', {}).get('records')}
                      for key, value in results.items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
