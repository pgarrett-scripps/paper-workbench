"""Import a Paper Scaffold source tree as a manuscript workspace the engine reviews.

The tree is copied under ``scaffold/`` and cut into pieces: the title, each heading, each
plain prose paragraph and each locked stretch of Typst. The engine's ``write_manuscript``
writes those pieces as the same base a PDF import writes (``paper.md``, ``map.json`` and
``manifest.json``), so a finding cites a scaffold manuscript by document and line like
any other.

Where each piece sits in the source is kept in ``scaffold-spans.json``: one entry per map
row, in map order, written before the manifest so the manifest digests it with the rest.
A changed source is a new workspace, never a patched one.
"""
from __future__ import annotations

import collections
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from peerreviewagents import MAIN_DOCUMENT, verify_workspace, write_manuscript
from peerreviewagents.workspace import digest, read_json, write_json

from .source_edits import NATIVE_CITATION


BODY_START = re.compile(r"(?m)^// >>> BODY START[^\n]*\n")
BODY_END = re.compile(r"(?m)^// <<< BODY END[^\n]*(?:\n|$)")
INCLUDE = re.compile(r'(?m)^[ \t]*#include[ \t]+"([^"\n]+)"[ \t]*$')
HEADING = re.compile(r"(?m)^\s*(=+)\s+(.+?)(?:\s+<[^>]+>)?\s*$")
CITATION = re.compile(r"(?<![\w\\:./-])@([A-Za-z0-9_-]+(?::[A-Za-z0-9_-]+)*)")
PLAIN_MARKUP = re.compile(r"[#*$@_<>\[\]{}\\`]")
BLOCK_PREFIX = re.compile(r"^\s*(?:=|#|//|/\*|```|~~~|[-+]\s|\d+[.)]\s)")
EXCLUDED_DIRECTORIES = {
    ".agents", ".codex", ".git", ".venv", "node_modules", "build", "dist",
    "out", "output", "target", ".build-state", ".edit-guard", "submission",
    "__pycache__",
}
EXCLUDED_FILES = {"AGENTS.md"}
ASSET_SUFFIXES = {
    ".csv", ".docx", ".eps", ".gif", ".jpeg", ".jpg", ".json", ".pdf",
    ".png", ".svg", ".tif", ".tiff", ".tsv", ".webp", ".xlsx",
}
PREVIEW_SUFFIXES = {".gif", ".jpeg", ".jpg", ".pdf", ".png", ".svg", ".webp"}
MAX_SOURCE_BYTES = 250 * 1024 * 1024

#: The file beside the base that says where each piece is in the scaffold source.
SPANS = "scaffold-spans.json"
SPANS_SCHEMA = "paper-workbench-scaffold-spans-v1"
PARSER = "paper_workspace.scaffold_import"
SOURCE_FILE = "scaffold/paper.typ"
#: Where a ported manuscript keeps the PDF it was read from, in the scaffold tree and in the workspace.
PORTED_PDF = Path("source") / "original" / "original.pdf"
ORIGINAL_PDF = Path("original") / "original.pdf"
WARNING = ("Scaffold source was imported without compilation. Plain BODY prose and verified ported "
           "string literals are editable. Citation markers are protected and other Typst syntax "
           "remains locked.")


def _mask(source: str, *, strings: bool = False) -> str:
    """Blank comments and raw text while preserving character offsets."""
    out = list(source)
    i = 0
    while i < len(source):
        start = i
        if source.startswith("//", i):
            end = source.find("\n", i)
            i = len(source) if end < 0 else end
        elif source.startswith("/*", i):
            depth = 1
            i += 2
            while i < len(source) and depth:
                if source.startswith("/*", i):
                    depth += 1
                    i += 2
                elif source.startswith("*/", i):
                    depth -= 1
                    i += 2
                else:
                    i += 1
        elif source[i] == "`":
            fence = re.match(r"`+", source[i:]).group()
            end = source.find(fence, i + len(fence))
            i = len(source) if end < 0 else end + len(fence)
        elif source[i] == '"':
            i += 1
            while i < len(source):
                if source[i] == "\\":
                    i += 2
                elif source[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            if not strings:
                continue
        elif source[i] == "\\":
            i += 2
        else:
            i += 1
            continue
        out[start:i] = ["\n" if char == "\n" else " " for char in source[start:i]]
    return "".join(out)


def _depths(source: str) -> list[int]:
    """Return conservative bracket depth before each source character."""
    visible = _mask(source, strings=True)
    depths = [0] * (len(source) + 1)
    stack = []
    in_math = False
    pairs = {"(": ")", "[": "]", "{": "}"}
    for index, char in enumerate(visible):
        depths[index] = len(stack) + int(in_math)
        if char == "$" and (index == 0 or source[index - 1] != "\\"):
            in_math = not in_math
        elif not in_math and char in pairs:
            stack.append(pairs[char])
        elif not in_math and stack and char == stack[-1]:
            stack.pop()
    depths[len(source)] = len(stack) + int(in_math)
    return depths


def _body_span(source: str, name: str, *, required: bool) -> tuple[int, int]:
    starts = list(BODY_START.finditer(source))
    ends = list(BODY_END.finditer(source))
    if not starts and not ends and not required:
        return 0, len(source)
    if len(starts) != 1 or len(ends) != 1 or starts[0].end() > ends[0].start():
        raise ValueError(f"{name}: expected exactly one ordered BODY START and BODY END pair")
    return starts[0].end(), ends[0].start()


def copy_project(source: Path, destination: Path) -> None:
    """Copy a Scaffold project's source into ``destination``, a folder that does not exist yet.

    The copy leaves out the agent notes and the version control, environment,
    build and cache folders a project keeps, and refuses a symlink, a file that
    is not a regular file and a project over the import limit.
    """
    destination.mkdir(parents=True)
    copied_bytes = 0

    def copy_directory(current: Path, target: Path) -> None:
        nonlocal copied_bytes
        target.mkdir(exist_ok=True)
        for child in sorted(current.iterdir(), key=lambda path: path.name):
            if child.name in EXCLUDED_FILES:
                continue
            if child.is_symlink():
                raise ValueError(f"Scaffold source contains a symlink: {child.relative_to(source)}")
            if child.is_dir():
                if child.name not in EXCLUDED_DIRECTORIES:
                    copy_directory(child, target / child.name)
            elif child.is_file():
                copied_bytes += child.stat().st_size
                if copied_bytes > MAX_SOURCE_BYTES:
                    raise ValueError('Scaffold source exceeds the 250 MiB import limit. Supply manuscript sources and required assets without large analysis datasets.')
                shutil.copy2(child, target / child.name)
            else:
                raise ValueError(f"Scaffold source contains an unsupported file: {child.relative_to(source)}")

    copy_directory(source, destination)


def _resolve_include(root: Path, current: Path, value: str) -> Path:
    lexical = Path(value.lstrip("/"))
    if not value or lexical.is_absolute() or ".." in lexical.parts:
        raise ValueError(f"Unsafe Scaffold include in {current}: {value}")
    target = (root / value.lstrip("/")) if value.startswith("/") else current.parent / value
    if target.is_symlink():
        raise ValueError(f"Scaffold include is a symlink in {current}: {value}")
    resolved = target.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Scaffold include escapes the source tree in {current}: {value}")
    if not resolved.is_file():
        raise ValueError(f"Missing Scaffold include in {current}: {value}")
    return resolved


def _plain_paragraph(text: str, start_depth: int, end_depth: int, visible: str) -> bool:
    if start_depth or end_depth or not re.search(r"[^\W\d_]", text, re.UNICODE):
        return False
    if visible != text:
        return False
    if PLAIN_MARKUP.search(NATIVE_CITATION.sub('', text)):
        return False
    return not any(BLOCK_PREFIX.match(line) for line in text.splitlines())


def plain_prose(text: str) -> bool:
    """Whether this text, as a file of its own, is one editable plain paragraph.

    The port writes a paragraph as plain Typst only when this holds, so a ported
    paragraph imports back as the same editable piece and never as locked source.
    """
    if not text or text != text.strip() or re.search(r"\n[ \t]*\n", text) or HEADING.fullmatch(text):
        return False
    depths = _depths(text)
    return _plain_paragraph(text, depths[0], depths[len(text)], _mask(text))


def _citation_ids(text: str) -> list[str]:
    excluded = {"fig", "tbl", "tab", "sec", "eq", "chap", "preview"}
    return list(dict.fromkeys(
        match.group(1) for match in CITATION.finditer(_mask(text))
        if match.group(1).split(":", 1)[0] not in excluded
    ))


def _title(root: Path, supplied: str | None) -> str:
    if supplied is not None:
        if not isinstance(supplied, str) or not supplied.strip():
            raise ValueError("Title must be a nonempty string")
        return supplied.strip()
    config = root / "config.typ"
    if config.is_file():
        match = re.search(r'(?m)^\s*#let\s+paper-title\s*=\s*"((?:\\.|[^"\\])*)"',
                          _mask(config.read_text(encoding="utf-8")))
        if match:
            try:
                return json.loads('"' + match.group(1) + '"')
            except json.JSONDecodeError:
                pass
    return root.name


def _inventory_assets(root: Path) -> list[dict]:
    assets = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in ASSET_SUFFIXES:
            continue
        relative = path.relative_to(root).as_posix()
        item = {
            "id": "asset-" + digest(relative)[:12],
            "label": path.name,
            "kind": "source-asset",
            "path": "scaffold/" + relative,
            "available": "file",
        }
        if path.suffix.lower() in PREVIEW_SUFFIXES:
            item["preview"] = item["path"]
        assets.append(item)
    return assets


def _reference_inventory(root: Path) -> list[dict]:
    known = set()
    for path in root.rglob("*.bib"):
        source = path.read_text(encoding="utf-8", errors="replace")
        known.update(re.findall(r"(?m)^\s*@[A-Za-z]+\s*[({]\s*([^,\s]+)\s*,", source))
    return [
        {"id": key, "label": key, "raw": "@" + key, "doi": "", "title": "", "year": ""}
        for key in sorted(known)
    ]


def segments(root: Path, hashes: dict[str, str]) -> list[dict]:
    """The BODY of ``paper.typ`` and every file it includes, cut into source segments in reading order.

    A segment is a heading, a plain paragraph (the only kind a revision may edit) or a
    stretch of Typst kept verbatim. An ``#include`` line routes the document and is not
    part of what a reader reads, so it is followed and not kept.
    """
    found = []
    visited = set()
    active = set()

    def visit(path: Path, *, main: bool = False) -> None:
        resolved = path.resolve()
        relative = resolved.relative_to(root.resolve()).as_posix()
        if resolved in active:
            raise ValueError(f"Cyclic Scaffold include: {relative}")
        if resolved in visited:
            return
        active.add(resolved)
        visited.add(resolved)
        source = resolved.read_bytes().decode("utf-8")
        body_start, body_end = _body_span(source, relative, required=main)
        depths = _depths(source)
        visible = _mask(source)
        code = _mask(source, strings=True)
        includes = []
        for match in INCLUDE.finditer(visible, body_start, body_end):
            if code[match.start():match.start() + 1].strip() and depths[match.start()] == 0:
                includes.append((match.start(), _resolve_include(root, resolved, match.group(1))))
        cuts = {body_start, body_end}
        for separator in re.finditer(r"\r?\n[ \t]*(?:\r?\n)+", source[body_start:body_end]):
            cuts.update((body_start + separator.start(), body_start + separator.end()))
        for match in HEADING.finditer(source, body_start, body_end):
            if (depths[match.start()] == 0
                    and visible[match.start():match.end()] == source[match.start():match.end()]):
                cuts.update((match.start(), match.end()))
        routes = set()
        for start, _ in includes:
            match = INCLUDE.match(visible, start, body_end)
            if match:
                cuts.update((match.start(), match.end()))
                routes.add(match.start() + len(match.group()) - len(match.group().lstrip()))
        points = sorted(cuts)
        include_index = 0
        for start, end in zip(points, points[1:]):
            raw = source[start:end]
            left = len(raw) - len(raw.lstrip())
            right = len(raw.rstrip())
            trimmed_start = start + left
            trimmed_end = start + max(left, right)
            text = source[trimmed_start:trimmed_end]
            if text and trimmed_start not in routes:
                heading = HEADING.fullmatch(text)
                editable = not heading and _plain_paragraph(
                    text, depths[trimmed_start], depths[trimmed_end], visible[trimmed_start:trimmed_end])
                found.append({
                    "file": relative, "start": trimmed_start, "end": trimmed_end,
                    "file_sha256": hashes[relative], "text": text,
                    "kind": "heading" if heading else "paragraph" if editable else "source",
                    "level": len(heading.group(1)) if heading else None,
                    "heading": heading.group(2).strip() if heading else None,
                })
            while include_index < len(includes) and includes[include_index][0] < end:
                visit(includes[include_index][1])
                include_index += 1
        while include_index < len(includes):
            visit(includes[include_index][1])
            include_index += 1
        active.remove(resolved)

    visit(root / "paper.typ", main=True)
    return found


def span_entry(segment: dict, kind: str, *, editable: bool, **extra) -> dict:
    """Where one piece is in the source, as ``scaffold-spans.json`` records it."""
    return {"kind": kind, "file": segment["file"], "start": segment["start"], "end": segment["end"],
            "file_sha256": segment["file_sha256"], "editable": editable, **extra}


def _plain_items(found: list[dict]) -> list[tuple]:
    """``(document, piece, entry)`` for each segment of a scaffold written by hand."""
    items = []
    section = "Body"
    for segment in found:
        if segment["kind"] == "heading":
            section = segment["heading"]
            piece = {"kind": "heading", "level": segment["level"], "text": segment["heading"],
                     "section": section}
        else:
            piece = {"kind": segment["kind"], "text": segment["text"], "section": section,
                     "citations": _citation_ids(segment["text"])}
        items.append((MAIN_DOCUMENT, piece,
                      span_entry(segment, piece["kind"], editable=segment["kind"] == "paragraph")))
    return items


def _documents(root: Path, title: str):
    """The pieces of each document, the spans record beside them, and what the manifest says."""
    hashes = {
        path.relative_to(root).as_posix(): digest(path.read_bytes())
        for path in sorted(root.rglob("*")) if path.is_file()
    }
    found = segments(root, hashes)
    warnings = [WARNING]
    references = _reference_inventory(root)
    port = None
    pages = []
    if (root / "pra-port.json").is_file():
        from .scaffold_port import ported_items
        items, port = ported_items(root, found, hashes)
        references = port["references"]
        pages = port["pages"]
        warnings += port["limitations"]
    else:
        items = _plain_items(found)
        items.insert(0, (MAIN_DOCUMENT, {"kind": "title", "text": title, "section": "Title"},
                         {"kind": "title", "file": None, "editable": False}))
    from .table_structure import enrich_tables
    warnings += enrich_tables(root, items, port["supplements"] if port else {})
    documents = collections.OrderedDict([(MAIN_DOCUMENT, [])])
    entries = collections.OrderedDict([(MAIN_DOCUMENT, [])])
    for document, piece, entry in items:
        documents.setdefault(document, []).append(piece)
        entries.setdefault(document, []).append(entry)
    spans = {"schema": SPANS_SCHEMA, "documents": entries,
             "port": {key: port[key] for key in ("source_paper_id", "source_sha256", "source_url")}
             if port else None}
    tree = digest(json.dumps(hashes, sort_keys=True, separators=(",", ":")))
    # A port keeps the pieces a model wrote with their source, and the engine writes them only
    # with the name of that model. A Scaffold project of the authors' own has none.
    return documents, spans, {"references": references, "warnings": warnings, "pages": pages,
                              "tree": tree, "source_url": port.get("source_url") if port else "",
                              "ai_model": port["ai_model"] if port else ""}


def import_scaffold(source, output, title=None, prepare=None, check=None):
    """Copy a Scaffold project and write a verified, immutable review workspace from it.

    ``prepare(folder, paper_id)``, when given, writes the caller's own files into the
    workspace before the manifest is taken, so they are digested with it. It is told
    the id the manuscript will have. ``check(folder, base)``
    runs on the written workspace before it is moved into place, and refuses it by
    raising. Returns the manifest.
    """
    source = Path(source)
    output = Path(output)
    if source.is_symlink() or not source.is_dir():
        raise ValueError("Scaffold source must be a regular directory")
    source = source.resolve()
    output_resolved = output.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output directory must not exist or must be empty")
    if output_resolved == source or output_resolved.is_relative_to(source) or source.is_relative_to(output_resolved):
        raise ValueError("Source and output directories must not overlap")
    if not (source / "paper.typ").is_file() or (source / "paper.typ").is_symlink():
        raise ValueError("Scaffold source must contain a regular paper.typ")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".scaffold-import-", dir=output.parent))
    try:
        copied = temporary / "scaffold"
        copy_project(source, copied)
        name = _title(copied, title)
        documents, spans, about = _documents(copied, name)
        write_json(temporary / SPANS, spans)
        if spans["port"] and (copied / PORTED_PDF).is_file():
            (temporary / ORIGINAL_PDF).parent.mkdir()
            shutil.copyfile(copied / PORTED_PDF, temporary / ORIGINAL_PDF)
        if prepare:
            prepare(temporary, about["tree"][:16])
        manifest = write_manuscript(
            temporary, documents, title=name, paper_id=about["tree"][:16],
            source={"file": SOURCE_FILE, "sha256": about["tree"]}, parser=PARSER,
            source_url=about["source_url"], references=about["references"],
            assets=_inventory_assets(copied), warnings=about["warnings"], pages=about["pages"],
            ai_model=about["ai_model"])
        base = verify_workspace(temporary)
        scaffold_spans(temporary, base)
        if check:
            check(temporary, base)
        if output.exists():
            output.rmdir()
        os.replace(temporary, output)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def scaffold_spans(folder, base) -> dict:
    """Each map row of a scaffold workspace, with where its piece is in the source.

    Returns ``{document: [entry, ...]}`` in map order, each entry carrying its row's
    ``lines``. A spans record that does not pair one to one with the map, kind for kind,
    is refused rather than joined.
    """
    record = read_json(Path(folder) / SPANS)
    if not isinstance(record, dict) or record.get("schema") != SPANS_SCHEMA:
        raise ValueError(f"{SPANS} is not a scaffold spans record this version reads")
    stored = record.get("documents") or {}
    if set(stored) != set(base.document_names()):
        raise ValueError(f"{SPANS} names other documents than the manuscript holds")
    joined = {}
    for document in base.document_names():
        rows, entries = base.pieces(document), stored[document]
        if len(rows) != len(entries) or any(row["kind"] != entry["kind"] for row, entry in zip(rows, entries)):
            raise ValueError(f"{SPANS} does not pair with the map of {document}")
        joined[document] = [{**entry, "lines": row["lines"]} for row, entry in zip(rows, entries)]
    return joined


def span_at(spans: dict, document: str, line: int):
    """The spans entry of the piece that holds this line, or ``None``."""
    for entry in spans.get(document, []):
        if entry["lines"][0] <= line <= entry["lines"][1]:
            return entry
    return None


def port_record(folder) -> dict | None:
    """The source manuscript a ported workspace was read from, or ``None`` for a hand-written scaffold."""
    return read_json(Path(folder) / SPANS).get("port")
