"""Loopback-only review viewer with durable decisions and native revisions."""
from datetime import datetime, timezone
import io
import json
import mimetypes
import re
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import zipfile

from peerreviewagents.engine.annotations import export_draft, verify_workspace
from peerreviewagents.engine.storage import digest, read, write

from .revisions import checkout, create_revision, head, snapshot, valid_id


LOCK = threading.Lock()
ASSETS = Path(__file__).parent / "web"
REVIEW_ID = re.compile(r"[a-z0-9_-]{1,50}")


def make_server(root, port=38744):
    root = Path(root).resolve()
    original = verify_workspace(root)

    def selected(query):
        requested = query.get("draft", [None])[0]
        if requested is None:
            requested = head(root)["revision_id"] if original.get("source_format") == "scaffold-typst" else "original"
        valid_id(requested)
        path, paper = snapshot(root, requested)
        return requested, path, paper

    def reviews(path):
        folder = path / "reviews"
        return [item.stem for item in sorted(folder.glob("*.json"))] if folder.is_dir() else []

    def exports(paper):
        records = []
        folder = root / 'exports'
        for path in folder.glob('*/export.json'):
            if path.is_symlink() or path.parent.is_symlink() or not path.resolve().is_relative_to(folder.resolve()):
                continue
            try:
                record = read(path)
                valid_id(path.parent.name)
            except (ValueError, OSError):
                continue
            if record.get('paper_id') == paper['id'] and record.get('source_sha256') == paper['source_sha256']:
                records.append({'id':path.parent.name, 'modified':path.stat().st_mtime,
                    'files':[name for name in ('paper.pdf','paper.docx','review.docx') if name in record.get('files',{})]})
        return sorted(records, key=lambda record: record['modified'], reverse=True)

    def review_for(path, rid):
        if not isinstance(rid, str) or not REVIEW_ID.fullmatch(rid):
            raise ValueError("Invalid review ID")
        return read(path / "reviews" / f"{rid}.json")

    def decisions_for(path, paper, rid):
        review_for(path, rid)
        target = path / "decisions" / f"{rid}.json"
        return read(target) if target.exists() else {
            "paper_id": paper["id"], "review_id": rid, "revision": 0,
            "items": {}, "annotations": {},
        }

    def revision_state(draft):
        revisions = [{"id": "original", "parent": None, "paper_id": original["id"]}]
        folder = root / "revisions"
        if folder.is_dir():
            for path in sorted(folder.iterdir()):
                if not path.is_dir() or not REVIEW_ID.fullmatch(path.name):
                    continue
                snapshot(root, path.name)
                metadata = read(path / "revision.json") if (path / "revision.json").exists() else {"id": path.name}
                revisions.append(metadata)
        current = head(root)
        path, paper = snapshot(root, draft)
        return {
            "selected": draft, "head": current,
            "native": paper.get("source_format") == "scaffold-typst",
            "revisions": revisions,
            "has_original_pdf": (root / "original.pdf").is_file(),
            "has_revision_pdf": (path / "artifacts" / "paper.pdf").is_file(),
            "has_source": (path / "scaffold").is_dir(),
        }

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, kind="application/json", *, disposition=None):
            data = json.dumps(body, ensure_ascii=False).encode() if kind == "application/json" else body
            self.send_response(status)
            self.send_header("Content-Type", kind + "; charset=utf-8" if kind.startswith(("text/", "application/json")) else kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'")
            if disposition:
                self.send_header("Content-Disposition", disposition)
            self.end_headers()
            self.wfile.write(data)

        def allowed_hosts(self):
            port = self.server.server_port
            return {f"127.0.0.1:{port}", f"localhost:{port}"}

        def parse_request(self):
            """Check Host before any method runs, so a DNS rebinding page cannot read the workspace."""
            if not super().parse_request():
                return False
            if self.headers.get("Host") not in self.allowed_hosts():
                self.send(403, {"error": "Local host required"})
                return False
            return True

        def post_value(self):
            origin = self.headers.get("Origin")
            allowed_origins = {f"http://{value}" for value in self.allowed_hosts()}
            if origin and origin not in allowed_origins:
                self.send(403, {"error": "Same-origin request required"})
                return None
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self.send(400, {"error": "Expected a JSON request"})
                return None
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length < 20000:
                raise ValueError("Invalid request size")
            value = json.loads(self.rfile.read(length))
            if not isinstance(value, dict):
                raise ValueError("Expected a JSON object")
            return value

        def do_GET(self):
            try:
                url = urlparse(self.path)
                name = "index.html" if url.path == "/" else url.path.lstrip("/")
                if name in ("index.html", "app.js", "style.css"):
                    # The viewer shell holds no manuscript data, so it skips workspace verification.
                    kind = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}[Path(name).suffix]
                    return self.send(200, (ASSETS / name).read_bytes(), kind)
                query = parse_qs(url.query)
                draft, workspace, paper = selected(query)
                rid = query.get("review", ["workspace"])[0]
                if url.path == "/api/paper":
                    if paper.get('port_provenance'):
                        from .table_structure import enrich_tables
                        paper = enrich_tables(workspace / 'scaffold', paper)
                    return self.send(200, paper)
                if url.path == "/api/revisions":
                    return self.send(200, revision_state(draft))
                if url.path == '/api/exports':
                    return self.send(200, exports(paper))
                export_match = re.fullmatch(r'/exports/([a-z0-9_-]{1,50})/(paper\.pdf|paper\.docx|review\.docx)', url.path)
                if export_match:
                    export_id, name = export_match.groups()
                    if not any(record['id'] == export_id and name in record['files'] for record in exports(paper)):
                        raise ValueError('Export does not belong to the selected manuscript draft')
                    directory = root / 'exports' / export_id
                    path = directory / name
                    if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
                        raise ValueError('Export file escapes its package')
                    data = path.read_bytes()
                    if digest(data) != read(directory / 'export.json')['files'][name]:
                        raise ValueError('Export file changed after verification')
                    mime = 'application/pdf' if name.endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    return self.send(200, data, mime,
                        disposition=('inline' if name.endswith('.pdf') else 'attachment') + f'; filename="{name}"')
                if url.path == "/api/reviews":
                    return self.send(200, reviews(workspace))
                if url.path == "/api/review":
                    return self.send(200, review_for(workspace, rid))
                if url.path == "/api/decisions":
                    return self.send(200, decisions_for(workspace, paper, rid))
                if url.path == "/api/ledger":
                    ledger = workspace / "issue-ledger.json"
                    return self.send(200, read(ledger) if ledger.exists() else [])
                if url.path == "/api/export":
                    verify_workspace(workspace)
                    return self.send(200, export_draft(paper, review_for(workspace, rid),
                                                       decisions_for(workspace, paper, rid)))
                if url.path == "/original.pdf":
                    target = root / "original.pdf"
                    if not target.is_file():
                        return self.send(404, {"error": "Original PDF is unavailable"})
                    return self.send(200, target.read_bytes(), "application/pdf")
                if url.path == "/draft.pdf":
                    target = workspace / "artifacts" / "paper.pdf"
                    if not target.is_file():
                        return self.send(404, {"error": "Compiled revision PDF is unavailable"})
                    return self.send(200, target.read_bytes(), "application/pdf")
                if url.path == "/source.zip":
                    source = workspace / "scaffold"
                    if not source.is_dir():
                        return self.send(404, {"error": "Native source is unavailable"})
                    verify_workspace(workspace)
                    archive = io.BytesIO()
                    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                        for path in sorted(source.rglob("*")):
                            if path.is_file():
                                bundle.write(path, Path("scaffold") / path.relative_to(source))
                    return self.send(200, archive.getvalue(), "application/zip",
                                     disposition=f'attachment; filename="{draft}-source.zip"')
                match = re.fullmatch(r"/pages/(\d+)\.png", url.path)
                if match:
                    page = int(match.group(1))
                    if not 1 <= page <= paper["statistics"]["pdf_pages"]:
                        raise ValueError("Unknown PDF page")
                    target = root / "page_images" / f"{page:03d}.png"
                    if not target.exists():
                        with LOCK:
                            # Render into a private folder and rename, so no request reads a partial image.
                            if not target.exists():
                                target.parent.mkdir(exist_ok=True)
                                with tempfile.TemporaryDirectory(dir=target.parent, prefix=".render-") as scratch:
                                    output = Path(scratch) / "page"
                                    subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page),
                                        "-scale-to", "1800", "-singlefile", "-png", str(root / "original.pdf"),
                                        str(output)], check=True, capture_output=True, timeout=30)
                                    output.with_suffix(".png").replace(target)
                    return self.send(200, target.read_bytes(), "image/png")
                if url.path.startswith("/supplements/"):
                    path = (workspace / url.path.lstrip("/")).resolve()
                    if path.parent != workspace / "supplements" or path.suffix not in (".png", ".jpg", ".pdf", ".docx"):
                        raise ValueError("Unavailable supplement format")
                    mime = {".png": "image/png", ".jpg": "image/jpeg", ".pdf": "application/pdf",
                            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}[path.suffix]
                    return self.send(200, path.read_bytes(), mime)
                if url.path.startswith("/scaffold/"):
                    path = (workspace / url.path.lstrip("/")).resolve()
                    source = (workspace / "scaffold").resolve()
                    if not path.is_relative_to(source) or not path.is_file():
                        raise ValueError("Unavailable source asset")
                    if path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf'):
                        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                        return self.send(200, path.read_bytes(), mime)
                    return self.send(200, path.read_bytes(), "application/octet-stream",
                                     disposition='attachment')
                return self.send(404, {"error": "Not found"})
            except (ValueError, FileNotFoundError, KeyError, UnicodeDecodeError, subprocess.SubprocessError) as exc:
                self.send(400, {"error": str(exc)})

        def do_POST(self):
            try:
                url = urlparse(self.path)
                if url.path not in ("/api/decisions", "/api/revisions", "/api/checkout"):
                    return self.send(404, {"error": "Not found"})
                value = self.post_value()
                if value is None:
                    return
                draft, workspace, paper = selected(parse_qs(url.query))
                with LOCK:
                    if url.path == "/api/decisions":
                        verify_workspace(workspace)
                        rid = value["review_id"]
                        review = review_for(workspace, rid)
                        decisions = decisions_for(workspace, paper, rid)
                        if value["revision"] != decisions["revision"]:
                            return self.send(409, {"error": "Another tab changed the decisions. Reload before saving."})
                        finding = next((item for item in review["findings"]
                                        if item["id"] == value["annotation_id"]), None)
                        if finding is None:
                            raise ValueError("Unknown annotation")
                        status = value["status"]
                        allowed = ("accepted", "rejected", "proposed") if finding["kind"] == "edit" else ("noted", "proposed")
                        if status not in allowed:
                            raise ValueError("Invalid decision for this finding")
                        annotations = decisions.setdefault("annotations", {})
                        previous = annotations.get(finding["id"], {})
                        comment = value.get("author_comment", previous.get("author_comment", ""))
                        issue_status = value.get("issue_status", previous.get("issue_status", "open"))
                        rationale = value.get("rationale", previous.get("rationale", ""))
                        if not isinstance(comment, str) or len(comment) > 4000:
                            raise ValueError("Author comment is too long")
                        if issue_status not in ("open", "addressed"):
                            raise ValueError("Issue status must be open or addressed")
                        if not isinstance(rationale, str) or len(rationale) > 2000:
                            raise ValueError("Issue rationale is too long")
                        if issue_status == "addressed" and not rationale.strip():
                            raise ValueError("Addressed issues require a rationale")
                        decisions["items"][finding["id"]] = status
                        export_draft(paper, review, decisions)
                        next_revision = decisions["revision"] + 1
                        history = list(previous.get("history", []))
                        history.append({"revision": next_revision,
                            "at": datetime.now(timezone.utc).isoformat(), "wording_decision": status,
                            "author_comment": comment, "issue_status": issue_status,
                            "rationale": rationale})
                        annotations[finding["id"]] = {"author_comment": comment,
                            "issue_status": issue_status, "rationale": rationale, "history": history}
                        decisions["revision"] = next_revision
                        write(workspace / "decisions" / f"{rid}.json", decisions)
                        return self.send(200, decisions)
                    if url.path == "/api/revisions":
                        revision_id = valid_id(value["revision_id"])
                        expected = value["expected_head"]
                        if not isinstance(expected, dict):
                            raise ValueError('Expected head must be a revision record')
                        if draft != expected.get("revision_id"):
                            raise ValueError("Create the revision from the active draft")
                        rid = value["review_id"]
                        review = review_for(workspace, rid)
                        decisions = decisions_for(workspace, paper, rid)
                        if value.get("decision_revision") != decisions["revision"]:
                            return self.send(409, {"error": "Decisions changed before the revision build. Reload and retry."})
                        metadata = create_revision(root, review, decisions, revision_id, expected, build=True)
                        return self.send(201, {"revision": metadata, "head": head(root)})
                    target = valid_id(value["revision_id"])
                    updated = checkout(root, target, value["expected_head"])
                    return self.send(200, updated)
            except (ValueError, KeyError, OSError, json.JSONDecodeError, TypeError, subprocess.SubprocessError) as exc:
                self.send(400, {"error": str(exc)})

        def log_message(self, format, *args):
            return

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(root, port=38744):
    server = make_server(root, port)
    print(f"Review workspace: http://127.0.0.1:{server.server_port}", flush=True)
    server.serve_forever()
