#!/usr/bin/env python3
"""Freeze two version-matched manuscripts and their first-round eLife reviews."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path

import pymupdf as fitz


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs" / "pra-workspace-two-paper-v1" / "sources"

PAPERS = (
    {
        "id": "rice-microbiome",
        "elife_id": "97015",
        "api": "https://api.elifesciences.org/reviewed-preprints/97015v1",
        "pdf": "https://elifesciences.org/reviewed-preprints/97015v1.pdf",
        "drop_pages": [49, 50],
        "redactions": [
            {"page": 2, "start": "eLife assessment", "end": "Introduction"},
            {"page": 48, "start": "Editors", "end": None},
        ],
    },
    {
        "id": "synaptic-vesicle",
        "elife_id": "90497",
        "api": "https://api.elifesciences.org/reviewed-preprints/90497v1",
        "pdf": "https://elifesciences.org/reviewed-preprints/90497v1.pdf",
        "drop_pages": [20, 21, 22],
        "redactions": [
            {"page": 1, "start": "eLife assessment:", "end": None},
            {"page": 19, "start": "Editors", "end": None},
        ],
    },
)


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "insilico-source-freezer/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def text_from_html(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"</(?:p|h[1-6]|li|blockquote)>", "\n\n", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    import html

    text = html.unescape(fragment)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def review_fragment(index_content: str) -> str:
    starts = [
        match.start()
        for match in re.finditer(r"<p><strong>(?:eLife assessment|eLife assessment:)</strong>", index_content)
    ]
    if not starts:
        raise ValueError("review section start not found")
    start = starts[0]
    ends = [
        marker
        for marker in (
            index_content.find('<h1 id="abstract">', start),
            index_content.find('<section id="abstract">', start),
            index_content.find('<h1 id="s1">', start),
        )
        if marker >= 0
    ]
    if not ends:
        raise ValueError("review section end not found")
    return index_content[start : min(ends)]


def clean_pdf(source: bytes, destination: Path, paper: dict) -> dict:
    document = fitz.open(stream=source, filetype="pdf")
    operations = []
    for item in paper["redactions"]:
        page = document[item["page"] - 1]
        start_hits = page.search_for(item["start"])
        if not start_hits:
            raise ValueError(f"redaction start not found: {paper['id']} {item}")
        y0 = min(hit.y0 for hit in start_hits) - 2
        if item["end"]:
            end_hits = page.search_for(item["end"])
            if not end_hits:
                raise ValueError(f"redaction end not found: {paper['id']} {item}")
            y1 = min(hit.y0 for hit in end_hits) - 4
        else:
            y1 = page.rect.height - 26
        rectangle = fitz.Rect(0, y0, page.rect.width, y1)
        page.add_redact_annot(rectangle, fill=(1, 1, 1))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
        operations.append(
            {
                "source_page": item["page"],
                "rectangle_points": [round(value, 2) for value in rectangle],
                "start_anchor": item["start"],
                "end_anchor": item["end"],
            }
        )

    drop_zero_based = sorted((page - 1 for page in paper["drop_pages"]), reverse=True)
    for page_number in drop_zero_based:
        document.delete_page(page_number)
    document.set_metadata({**document.metadata, "title": f"{paper['id']} manuscript-only reviewed-preprint v1"})
    document.save(destination, garbage=4, deflate=True)
    document.close()
    return {"redactions": operations, "excluded_source_pages": paper["drop_pages"]}


def main() -> None:
    manuscripts = OUT / "manuscripts"
    evaluation = OUT / "evaluation-only"
    manuscripts.mkdir(parents=True, exist_ok=True)
    evaluation.mkdir(parents=True, exist_ok=True)

    manifest = []
    for paper in PAPERS:
        record_bytes = download(paper["api"])
        record = json.loads(record_bytes)
        pdf_bytes = download(paper["pdf"])
        if not pdf_bytes.startswith(b"%PDF"):
            raise ValueError(f"non-PDF response for {paper['id']}")

        pdf_path = manuscripts / f"{paper['id']}-manuscript-only-v1.pdf"
        full_pdf_path = evaluation / f"{paper['id']}-elife-v1-full.pdf"
        record_path = evaluation / f"{paper['id']}-elife-v1.json"
        html_path = evaluation / f"{paper['id']}-human-reviews.html"
        text_path = evaluation / f"{paper['id']}-human-reviews.txt"
        full_pdf_path.write_bytes(pdf_bytes)
        sanitization = clean_pdf(pdf_bytes, pdf_path, paper)
        record_path.write_bytes(record_bytes)

        fragment = review_fragment(record["indexContent"])
        html_path.write_text(fragment + "\n", encoding="utf-8")
        text_path.write_text(text_from_html(fragment), encoding="utf-8")

        manifest.append(
            {
                "id": paper["id"],
                "elife_id": paper["elife_id"],
                "title": record["title"],
                "preprint_doi": record["doi"],
                "elife_reviewed_preprint_doi": record["elifeAssessment"]["doi"].rsplit(".sa", 1)[0],
                "reviewed_preprint_version": record["version"],
                "reviewed_preprint_date": record["reviewedDate"],
                "pdf_source_url": paper["pdf"],
                "review_source_url": paper["api"],
                "pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest(),
                "manuscript_only_pdf_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
                "sanitization": sanitization,
                "review_record_sha256": hashlib.sha256(record_bytes).hexdigest(),
            }
        )

    (OUT / "download-manifest.json").write_text(
        json.dumps({"papers": manifest}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
