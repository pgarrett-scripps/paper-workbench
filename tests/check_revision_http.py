import json
from pathlib import Path
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peerreviewagents.engine.annotations import save_review
from peerreviewagents.engine.storage import write, digest

from paper_workspace.revisions import copyedit_proposals, create_revision as real_create_revision
from paper_workspace.scaffold_import import import_scaffold
from paper_workspace.server import make_server


FIXTURE = Path(__file__).parent / "fixtures/scaffold-revision"


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary) / "workspace"
    paper = import_scaffold(FIXTURE, root)
    response = copyedit_proposals(paper)
    scientific_block = next(block for block in paper["blocks"] if "protein activity" in block["text"])
    response["findings"].append({
        "category": "scientific", "kind": "question",
        "block_id": scientific_block["id"], "quote": "protein activity",
        "title": "Mechanistic support", "comment": "Clarify the evidence.",
        "evidence_blocks": [scientific_block["id"]]
    })
    review = save_review(root, response, "ui")
    server = make_server(root, 0)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(path, value=None, *, origin=None):
        headers = {"Content-Type": "application/json"}
        if origin:
            headers["Origin"] = origin
        body = json.dumps(value).encode() if value is not None else None
        call = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=body, headers=headers)
        try:
            with urllib.request.urlopen(call, timeout=5) as result:
                kind = result.headers.get_content_type()
                return result.status, json.load(result) if kind == "application/json" else result.read()
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)

    def source_only_revision(root, review, decisions, revision_id, expected_head, build=True):
        return real_create_revision(root, review, decisions, revision_id, expected_head, build=False)

    try:
        status, state = request("/api/revisions?draft=original")
        assert status == 200 and state["selected"] == "original"
        assert state["head"] == {"revision_id": "original", "version": 0}
        status, archive = request("/source.zip?draft=original")
        assert status == 200 and archive.startswith(b"PK")

        finding = review["findings"][0]
        decision = {"review_id": "ui", "annotation_id": finding["id"],
                    "status": "accepted", "revision": 0,
                    "author_comment": "The wording change is appropriate.",
                    "issue_status": "addressed", "rationale": ""}
        assert request("/api/decisions?draft=original", decision)[0] == 400
        decision["rationale"] = "The revised wording removes the unnecessary phrase."
        status, decisions = request("/api/decisions?draft=original", decision)
        assert status == 200 and decisions["revision"] == 1
        note = decisions["annotations"][finding["id"]]
        assert note["issue_status"] == "addressed" and len(note["history"]) == 1
        assert request("/api/decisions?draft=original", decision)[0] == 409
        assert request("/api/decisions?draft=original", decision,
                       origin="http://bad.example")[0] == 403

        create = {"revision_id": "ui-1", "review_id": "ui", "decision_revision": 1,
                  "expected_head": state["head"]}
        with patch("paper_workspace.server.create_revision", side_effect=source_only_revision):
            status, created = request("/api/revisions?draft=original", create)
        assert status == 201 and created["head"]["revision_id"] == "ui-1"
        status, revised = request("/api/paper")
        assert status == 200 and revised["id"] != paper["id"]
        assert request("/api/reviews?draft=ui-1")[1] == []
        ledger = request("/api/ledger?draft=ui-1")[1]
        assert ledger and ledger[0]["anchor_status"] == "historical"
        export_folder = root / 'exports' / 'verified'
        export_folder.mkdir(parents=True)
        (export_folder / 'paper.pdf').write_bytes(b'%PDF-fixture')
        (export_folder / 'review.docx').write_bytes(b'PK-review-fixture')
        write(export_folder / 'export.json', {'paper_id':revised['id'],
            'source_sha256':revised['source_sha256'],'files':{'paper.pdf':digest(b'%PDF-fixture'),'review.docx':digest(b'PK-review-fixture')}})
        assert request('/api/exports?draft=ui-1')[1][0]['id'] == 'verified'
        assert request('/api/exports?draft=original')[1] == []
        assert request('/exports/verified/paper.pdf?draft=ui-1')[1] == b'%PDF-fixture'
        assert request('/exports/verified/paper.pdf?draft=original')[0] == 400
        assert request('/exports/verified/review.docx?draft=ui-1')[1] == b'PK-review-fixture'
        assert request('/exports/verified/review.docx?draft=original')[0] == 400
        (export_folder / 'review.docx').write_bytes(b'changed')
        assert request('/exports/verified/review.docx?draft=ui-1')[0] == 400
        (export_folder / 'paper.pdf').write_bytes(b'changed')
        assert request('/exports/verified/paper.pdf?draft=ui-1')[0] == 400

        status, checked_out = request("/api/checkout?draft=ui-1", {
            "revision_id": "original", "expected_head": created["head"]})
        assert status == 200 and checked_out["revision_id"] == "original"
        assert request("/api/paper")[1]["id"] == paper["id"]
        print("Revision HTTP QA passed")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
