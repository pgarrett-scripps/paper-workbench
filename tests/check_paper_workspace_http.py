"""Serve a one-sentence workspace from a subprocess and check decisions and the export over HTTP.

    python tests/check_paper_workspace_http.py

It is a manual check, and no test runs it. The manuscript is written by the
engine's own writer, as the tests write theirs.
"""
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peerreviewagents.workspace import save_review

import manuscripts
from manuscripts import line_of

PORT = 38745

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    base = manuscripts.build(root, ['A claim with 12 samples.'])
    line = line_of(base, '12 samples')
    save_review(root, {'findings': [{'kind': 'edit', 'line': line, 'quote': '12 samples', 'replacement': '12 donors',
                                     'evidence_lines': [line]}]}, 'qa')
    original = base.documents
    edited = {'paper.md': original['paper.md'].replace('12 samples', '12 donors')}
    process = subprocess.Popen([sys.executable, '-m', 'paper_workspace', 'serve', tmp, '--port', str(PORT)],
                               cwd=Path(__file__).resolve().parents[1],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def req(path, data=None, origin=None):
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        request = urllib.request.Request(f'http://127.0.0.1:{PORT}{path}',
                                         data=json.dumps(data).encode() if data else None, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as failure:
            return failure.code, json.load(failure)

    try:
        for attempt in range(40):
            try:
                code, value = req('/api/reviews')
                break
            except urllib.error.URLError:
                time.sleep(.1)
        assert value == ['qa']
        decision = {'review_id': 'qa', 'annotation_id': 'qa-1', 'status': 'accepted', 'revision': 0}
        assert req('/api/decisions', decision, 'http://bad.example')[0] == 403
        assert req('/api/decisions', decision)[0] == 200
        assert req('/api/decisions', decision)[0] == 409
        code, value = req('/api/export?review=qa')
        assert value['proposed_documents'] == edited
        assert value['original_documents'] == original
        assert value['findings'][0]['issue_status'] == 'open'
        assert json.loads((root / 'decisions/qa.json').read_text())['revision'] == 1
        decision.update(status='proposed', revision=1)
        assert req('/api/decisions', decision)[0] == 200
        assert req('/api/export?review=qa')[1]['proposed_documents'] == original
        print('HTTP QA passed: durable save, undo, stale revision, cross-origin rejection, '
              'immutable original, open scientific issue')
    finally:
        process.terminate()
        process.wait(timeout=10)
