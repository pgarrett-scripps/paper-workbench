"""Import an immutable Paper Scaffold source tree for conservative editing."""
from __future__ import annotations

import collections
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from .ingest import words
from .storage import digest, write
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


def _copy_project(source: Path, destination: Path) -> None:
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


def _reference_inventory(root: Path, cited: list[str]) -> list[dict]:
    known = set()
    for path in root.rglob("*.bib"):
        source = path.read_text(encoding="utf-8", errors="replace")
        known.update(re.findall(r"(?m)^\s*@[A-Za-z]+\s*[({]\s*([^,\s]+)\s*,", source))
    return [
        {"id": key, "label": key, "raw": "@" + key, "doi": "", "title": "", "year": ""}
        for key in sorted(known)
    ]


def _extract_blocks(root: Path, hashes: dict[str, str]) -> list[dict]:
    blocks = []
    visited = set()
    active = set()
    section = "Body"

    def add_block(relative: str, source: str, start: int, end: int, *, editable: bool) -> None:
        nonlocal section
        raw = source[start:end]
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        start += left
        end = start + max(0, right - left)
        text = source[start:end]
        if not text:
            return
        heading = HEADING.fullmatch(text)
        if heading:
            section = heading.group(2).strip()
        identifier = f"b{len(blocks) + 1:04d}"
        block = {
            "id": identifier,
            "text": text,
            "sha256": digest(text),
            "section": section,
            "kind": "heading" if heading else "paragraph" if editable else "source",
            "source_id": relative,
            "page": None,
            "page_mapping": "unavailable",
            "bbox": None,
            "citations": _citation_ids(text),
            "document": "main",
            "table": None,
            "editable": editable,
            "locked": not editable,
            "source_span": {
                "file": relative,
                "start": start,
                "end": end,
                "file_sha256": hashes[relative],
            } if editable else None,
            "source_location": {
                "file": relative,
                "start": start,
                "end": end,
                "file_sha256": hashes[relative],
            },
        }
        if not editable:
            block["lock_reason"] = "Typst syntax or structural source is preserved verbatim"
        blocks.append(block)

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
        for start, _ in includes:
            match = INCLUDE.match(visible, start, body_end)
            if match:
                cuts.update((match.start(), match.end()))
        points = sorted(cuts)
        segments = list(zip(points, points[1:]))
        include_index = 0
        for start, end in segments:
            raw = source[start:end]
            left = len(raw) - len(raw.lstrip())
            right = len(raw.rstrip())
            trimmed_start = start + left
            trimmed_end = start + right
            candidate = source[trimmed_start:trimmed_end]
            editable = (_plain_paragraph(candidate, depths[trimmed_start], depths[trimmed_end],
                                         visible[trimmed_start:trimmed_end])
                        if candidate else False)
            add_block(relative, source, start, end, editable=editable)
            while include_index < len(includes) and includes[include_index][0] < end:
                visit(includes[include_index][1])
                include_index += 1
        while include_index < len(includes):
            visit(includes[include_index][1])
            include_index += 1
        active.remove(resolved)

    visit(root / "paper.typ", main=True)
    return blocks


def _paper(root: Path, title: str | None) -> dict:
    hashes = {
        path.relative_to(root).as_posix(): digest(path.read_bytes())
        for path in sorted(root.rglob("*")) if path.is_file()
    }
    blocks = _extract_blocks(root, hashes)
    from .scaffold_port import port_context
    port = port_context(root, blocks)
    cited = list(dict.fromkeys(key for block in blocks for key in block["citations"]))
    references = _reference_inventory(root, cited)
    if port:
        references = port.get('references', references)
    assets = _inventory_assets(root)
    sections = collections.defaultdict(list)
    for block in blocks:
        sections[block["section"]].append(block["id"])
    statistics = {
        "total_words": sum(len(words(block["text"])) for block in blocks if block["kind"] != "heading"),
        "main_words": sum(len(words(block["text"])) for block in blocks
                          if block["kind"] not in ("heading", "reference") and block['document'] == 'main'),
        "reference_words": sum(len(words(block["text"])) for block in blocks if block["kind"] == "reference"),
        "reference_entries": len(references),
        "blocks": len(blocks),
        "pdf_pages": port.get('pdf_pages',0) if port else 0,
        "sections": {
            name: {
                "blocks": len(identifiers),
                "words": sum(len(words(block["text"])) for block in blocks
                             if block["id"] in identifiers and block["kind"] != "heading"),
            }
            for name, identifiers in sections.items()
        },
        "convention": "Unicode words in imported Scaffold BODY sources. No PDF build or model inference was run.",
    }
    source_sha256 = digest(json.dumps(hashes, sort_keys=True, separators=(",", ":")))
    paper = {
        "schema_version": 1,
        "id": source_sha256[:16],
        "title": _title(root, title),
        "source_url": "",
        "source_sha256": source_sha256,
        "source_format": "scaffold-typst",
        "parser": "paper_workspace.scaffold_import",
        "xml_sha256": None,
        "blocks": blocks,
        "references": references,
        "assets": assets,
        "sections": dict(sections),
        "statistics": statistics,
        "warnings": [
            "Scaffold source was imported without compilation. Plain BODY prose and verified ported string literals are editable. Citation markers are protected and other Typst syntax remains locked."
        ],
    }
    if port:
        paper['source_url'] = port.get('source_url','')
        paper['port_provenance'] = {k:port[k] for k in ('source_paper_id','source_sha256','limitations')}
        paper['warnings'] += port['limitations']
        from .table_structure import enrich_tables
        paper = enrich_tables(root, paper)
    return paper


def import_scaffold(source, output, title=None):
    """Copy a Scaffold project and create a verified immutable review workspace."""
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
        _copy_project(source, copied)
        paper = _paper(copied, title)
        if paper.get('port_provenance') and (copied/'source/original.pdf').is_file():
            shutil.copyfile(copied/'source/original.pdf', temporary/'original.pdf')
        write(temporary / "paper.json", paper)
        files = {
            path.relative_to(temporary).as_posix(): digest(path.read_bytes())
            for path in sorted(temporary.rglob("*"))
            if path.is_file() and path != temporary / "manifest.json"
        }
        write(temporary / "manifest.json", {"paper_id": paper["id"], "files": files})
        if output.exists():
            output.rmdir()
        os.replace(temporary, output)
        return paper
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
