"""Export verified revision differences and open questions into a Word review copy."""
from copy import deepcopy
from datetime import datetime, timezone
import difflib
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

from peerreviewagents.engine.storage import digest, read, write

from .revisions import snapshot

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/package/2006/relationships'
C = 'http://schemas.openxmlformats.org/package/2006/content-types'
NS = {'w': W}


def tag(name):
    return '{' + W + '}' + name


def visible(element, rejected=False):
    """Read a Word paragraph with tracked changes accepted or rejected."""
    if element.tag == tag('del') and not rejected:
        return ''
    if element.tag == tag('ins') and rejected:
        return ''
    if element.tag in (tag('t'), tag('delText')):
        return element.text or ''
    if element.tag == tag('tab'):
        return '\t'
    if element.tag in (tag('br'), tag('cr')):
        return '\n'
    return ''.join(visible(child, rejected) for child in element)


def patch_document(source, destination, parent, current, ledger):
    from lxml import etree as ET
    parser = ET.XMLParser(resolve_entities=False, no_network=True)
    with zipfile.ZipFile(source) as archive:
        entries = {i.filename: archive.read(i) for i in archive.infolist()}
    document = ET.fromstring(entries['word/document.xml'], parser)
    if document.xpath('.//w:ins|.//w:del|.//w:commentRangeStart', namespaces=NS) or ('word/comments.xml' in entries and len(ET.fromstring(entries['word/comments.xml'], parser))):
        raise ValueError('Review export requires a clean document without existing annotations')
    original_text = visible(document)
    paragraphs = document.findall('.//' + tag('p'))
    before = {b['id']: b for b in parent['blocks']}
    after = {b['id']: b for b in current['blocks']}
    if before.keys() != after.keys():
        raise ValueError('Review export does not yet support added or removed blocks')
    when = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    used_ids = [int(v) for v in document.xpath('//@w:id', namespaces=NS) if v.isdigit()]
    next_id = max(used_ids, default=0) + 1

    def run(text, properties=None, deleted=False):
        node = ET.Element(tag('r'))
        if properties is not None:
            node.append(deepcopy(properties))
        t = ET.SubElement(node, tag('delText' if deleted else 't'))
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        t.text = text
        return node

    def locate(text):
        matches = [p for p in paragraphs if visible(p) == text]
        if len(matches) != 1:
            raise ValueError('Expected one exact Word paragraph for the source block')
        return matches[0]

    changed = []
    for bid, block in after.items():
        old, new = before[bid]['text'], block['text']
        if old == new:
            continue
        paragraph = locate(new)
        # Only split plain text runs. Refuse fields, links, drawings, or bookmarks.
        if any(c.tag not in (tag('pPr'), tag('r')) for c in paragraph) or any(
                c.tag not in (tag('rPr'), tag('t')) for r in paragraph.findall(tag('r')) for c in r):
            raise ValueError('Changed paragraph contains unsupported Word markup')
        segments = []
        offset = 0
        for r in paragraph.findall(tag('r')):
            text = visible(r)
            segments.append((offset, offset + len(text), r.find(tag('rPr'))))
            offset += len(text)
        def slice_runs(start, end, deleted_text=None):
            if deleted_text is not None:
                properties = next((pr for a, b, pr in segments if a <= start < b), segments[-1][2] if segments else None)
                return [run(deleted_text, properties, True)]
            return [run(new[max(a, start):min(b, end)], pr) for a, b, pr in segments if max(a, start) < min(b, end)]
        for r in list(paragraph.findall(tag('r'))):
            paragraph.remove(r)
        old_tokens, new_tokens = re.findall(r'\s+|\w+|[^\w\s]', old), re.findall(r'\s+|\w+|[^\w\s]', new)
        new_offset = 0
        for operation, a, b, c, d in difflib.SequenceMatcher(None, old_tokens, new_tokens, autojunk=False).get_opcodes():
            left, right = ''.join(old_tokens[a:b]), ''.join(new_tokens[c:d])
            if operation == 'equal':
                paragraph.extend(slice_runs(new_offset, new_offset + len(right)))
            else:
                for name, text in (('del', left), ('ins', right)):
                    if not text:
                        continue
                    node = ET.SubElement(paragraph, tag(name), {tag('id'): str(next_id), tag('author'): 'In Silico', tag('date'): when})
                    next_id += 1
                    node.extend(slice_runs(new_offset, new_offset + len(right), text if name == 'del' else None))
            new_offset += len(right)
        if visible(paragraph) != new or visible(paragraph, True) != old:
            raise ValueError('Tracked change projections do not match the saved drafts')
        changed.append(bid)
    if visible(document) != original_text:
        raise ValueError('Review markup altered clean manuscript text')

    comments = ET.Element(tag('comments'), nsmap={'w': W})
    located, unlocated = [], []
    for index, entry in enumerate(ledger):
        if entry.get('scientific_status') != 'open':
            continue
        finding = entry['finding']
        block = after.get(finding.get('block_id'))
        reason = None
        if not block or digest(block['text'].encode()) != finding.get('block_sha256'):
            reason = 'The originating passage changed or is unavailable'
        quote = finding.get('quote', '')
        if not reason and (not quote or block['text'].count(quote) != 1):
            reason = 'The quoted passage is not unique in the current block'
        paragraph = None
        if not reason:
            try:
                paragraph = locate(block['text'])
            except ValueError:
                reason = 'No unique Word paragraph matches the current block'
        source_cards = {card.get('evidence_id') or card.get('source_url'): card
                        for card in finding.get('external_sources', [])}
        evidence = '\n\n'.join('Source: ' + str(card.get('source_url', '')) +
            '\nVersion: ' + str(card.get('record_version') or 'unknown') +
            '\nRetrieved or captured: ' + str(card.get('retrieved_at') or card.get('captured_at') or 'unavailable') +
            '\n' + str(card.get('limitation', '')) + '\n' +
            '\n'.join(ref.get('quote', '') for ref in finding.get('source_evidence', [])
                      if ref.get('evidence_id') == card.get('evidence_id'))
            for card in source_cards.values())
        text = '\n\n'.join(filter(None, [finding.get('title'), finding.get('comment'), evidence,
            'Open scientific question. Origin: ' + entry.get('origin_revision', 'unknown') + '. Finding: ' + finding['id'] + '.']))
        if reason:
            unlocated.append({'finding_id': finding['id'], 'reason': reason, 'text': text, 'quote': quote})
            continue
        # A full paragraph anchor retains inline formatting and makes the exact quote explicit.
        cid = str(index)
        start = ET.Element(tag('commentRangeStart'), {tag('id'): cid})
        paragraph.insert(1 if paragraph.find(tag('pPr')) is not None else 0, start)
        paragraph.append(ET.Element(tag('commentRangeEnd'), {tag('id'): cid}))
        reference = ET.SubElement(paragraph, tag('r'))
        ET.SubElement(reference, tag('commentReference'), {tag('id'): cid})
        comment = ET.SubElement(comments, tag('comment'), {tag('id'): cid, tag('author'): 'In Silico', tag('date'): when})
        for line in (text + '\n\nQuoted passage: ' + quote).split('\n'):
            ET.SubElement(comment, tag('p')).append(run(line))
        located.append({'finding_id': finding['id'], 'comment_id': cid, 'block_id': block['id'], 'anchor': 'exact paragraph', 'quote': quote})
    if unlocated:
        body = document.find(tag('body'))
        position = len(body) - (1 if body.find(tag('sectPr')) is not None else 0)
        for text in ['Unlocated review questions'] + [item['text'] + '\nLocation note: ' + item['reason'] + '\nQuoted passage: ' + item['quote'] for item in unlocated]:
            p = ET.Element(tag('p'))
            p.append(run(text))
            body.insert(position, p)
            position += 1
    def serialize(element):
        return ET.tostring(element, encoding='UTF-8', xml_declaration=True, standalone=True)
    if located:
        entries['word/comments.xml'] = serialize(comments)
        rels = ET.fromstring(entries['word/_rels/document.xml.rels'], parser)
        for node in list(rels):
            if node.get('Type', '').endswith('/comments'):
                rels.remove(node)
        rel_ids = {node.get('Id') for node in rels}
        rid = 'rIdReviewComments'
        while rid in rel_ids:
            rid += 'x'
        ET.SubElement(rels, '{' + R + '}Relationship', Id=rid,
                      Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments', Target='comments.xml')
        entries['word/_rels/document.xml.rels'] = serialize(rels)
        types = ET.fromstring(entries['[Content_Types].xml'], parser)
        for node in list(types):
            if node.get('PartName') == '/word/comments.xml':
                types.remove(node)
        ET.SubElement(types, '{' + C + '}Override', PartName='/word/comments.xml',
                      ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml')
        entries['[Content_Types].xml'] = serialize(types)
    settings = ET.fromstring(entries['word/settings.xml'], parser)
    if settings.find(tag('trackRevisions')) is None:
        ET.SubElement(settings, tag('trackRevisions'))
    entries['word/settings.xml'] = serialize(settings)
    entries['word/document.xml'] = serialize(document)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return {'changed_blocks': changed, 'comments': located, 'unlocated_questions': unlocated,
            'accepted_text_matches_clean': True, 'rejected_changed_blocks_match_parent': True,
            'scope': 'Changes from the immediate parent revision. Open questions from the inherited ledger.'}


def export_review(root, revision_id, clean_export, output):
    """Add a review copy to a verified export without altering saved sources."""
    source, paper = snapshot(root, revision_id)
    metadata = read(source / 'revision.json')
    _, parent = snapshot(root, metadata['parent'])
    clean_export, output = Path(clean_export).resolve(), Path(output).resolve()
    workspace = Path(root).resolve()
    if output.exists() or output == workspace or output.is_relative_to(clean_export):
        raise ValueError('Review export needs a new output directory')
    if output.is_relative_to(workspace) and output.relative_to(workspace).parts[0] != 'exports':
        raise ValueError('Exports inside a workspace must use its exports directory')
    record = read(clean_export / 'export.json')
    if record['paper_id'] != paper['id'] or record['source_sha256'] != paper['source_sha256']:
        raise ValueError('Clean export belongs to a different draft')
    for path in clean_export.rglob('*'):
        if path.is_symlink():
            raise ValueError('Export source contains a symbolic link')
    for name, sha in record['files'].items():
        path = clean_export / name
        if not path.resolve().is_relative_to(clean_export) or digest(path.read_bytes()) != sha:
            raise ValueError('Clean export integrity check failed')
    if 'paper.docx' not in record['files']:
        raise ValueError('Clean export has no verified Word document')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.review-export-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'artifacts'
        shutil.copytree(clean_export, stage)
        audit = patch_document(stage / 'paper.docx', stage / 'review.docx', parent, paper, read(source / 'issue-ledger.json'))
        audit.update({'revision_id': revision_id, 'parent_revision': metadata['parent'],
                      'clean_docx_sha256': record['files']['paper.docx'], 'new_review_model_calls': 0})
        write(stage / 'word-review.json', audit)
        record['word_review'] = audit
        record['limitations'] = [item for item in record.get('limitations', []) if item != 'Word tracked changes and embedded review comments are not exported.']
        record['limitations'].append('Review copy tracks the immediate revision only. Comment anchors cover exact matching paragraphs. Unlocated questions appear in an appendix.')
        record['files'].update({name: digest((stage / name).read_bytes()) for name in ('review.docx', 'word-review.json')})
        snapshot(root, revision_id)
        write(stage / 'export.json', record)
        stage.rename(output)
    return audit
