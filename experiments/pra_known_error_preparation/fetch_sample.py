"""Fetch a fixed tiny FLAWS sample through verified public ZIP byte ranges."""

import hashlib
import json
import struct
import zlib
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2] / "runs/pra-known-error-preparation-v1"
REVISION = "a20a57860ed4afc8a046a73abab6bd1222068762"
URL = f"https://huggingface.co/datasets/xasayi/FLAWS/resolve/{REVISION}/OPENAI_NON_ML.zip"


def fetch_range(start, end):
    response = requests.get(URL, headers={"Range": f"bytes={start}-{end}"}, timeout=60, stream=True)
    if response.status_code != 206 or response.headers.get("Content-Range") != f"bytes {start}-{end}/224811852":
        response.close()
        raise RuntimeError("The server did not return the requested archive byte range")
    body = response.content
    if len(body) != end - start + 1:
        raise RuntimeError("Truncated archive range")
    return body


def extract(row):
    path = ROOT / "source" / row["name"]
    if path.exists():
        content = path.read_bytes()
    else:
        offset = row["offset"]
        header = fetch_range(offset, offset + 29)
        if header[:4] != b"PK\x03\x04":
            raise RuntimeError("Invalid local ZIP header")
        name_length, extra_length = struct.unpack_from("<HH", header, 26)
        start = offset + 30
        data = fetch_range(start, start + name_length + extra_length + row["compressed_size"] - 1)
        if data[:name_length].decode("utf-8") != row["name"]:
            raise RuntimeError("ZIP entry identity mismatch")
        compressed = data[name_length + extra_length:]
        if row["compress_type"] == 8:
            content = zlib.decompress(compressed, -15)
        elif row["compress_type"] == 0:
            content = compressed
        else:
            raise RuntimeError("Unsupported ZIP compression")
        if len(content) != row["size"] or zlib.crc32(content) != row["crc"]:
            raise RuntimeError("ZIP checksum mismatch")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    if len(content) != row["size"] or zlib.crc32(content) != row["crc"]:
        raise RuntimeError("Cached file checksum mismatch")
    return path


def main():
    inventory = json.loads((ROOT / "openai_non_ml_zip_inventory.json").read_text())
    by_name = {row["name"]: row for row in inventory}
    metadata = extract(by_name["OPENAI_NON_ML/openai_all.json"])
    errors = json.loads(metadata.read_text())
    ranked = sorted(errors, key=lambda pid: hashlib.sha256(("20260920:" + pid).encode()).hexdigest())
    selected = ranked[:3]
    plan = {"dataset": "xasayi/FLAWS", "revision": REVISION, "archive": "OPENAI_NON_ML.zip",
            "selection": "First three paper IDs sorted by sha256 of 20260920: plus ID, selected before system outputs or error annotations.",
            "population": len(errors), "paper_ids": selected,
            "claim_indices": {pid: errors[pid] for pid in selected},
            "purpose": "Input feasibility and separately labeled known-error development test. Not a substitution for human-review coverage.",
            "generation_started": False}
    selection = ROOT / "sample_selection.json"
    if selection.exists() and json.loads(selection.read_text()) != plan:
        raise RuntimeError("Sample selection changed")
    selection.write_text(json.dumps(plan, indent=2) + "\n")
    artifacts = []
    for pid in selected:
        index = str(errors[pid])
        prefix = f"OPENAI_NON_ML/altered_papers/{pid}/"
        names = [prefix + f"altered_{index}.pdf", prefix + f"altered_{index}.tex", prefix + "combined.tex"]
        names += [name for name in by_name if any(name.startswith(f"OPENAI_NON_ML/{folder}/{pid}_{index}_") for folder in ("inserted_error", "location_error"))]
        for name in names:
            if name not in by_name:
                artifacts.append({"paper_id": pid, "name": name, "available": False})
                continue
            path = extract(by_name[name])
            artifacts.append({"paper_id": pid, "name": name, "available": True,
                              "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size,
                              "role": "evaluation_only" if "/inserted_error/" in name or "/location_error/" in name else "source_artifact"})
        print(f"Downloaded selected artifacts for {pid}", flush=True)
    (ROOT / "download_manifest.json").write_text(json.dumps({"selection": plan, "artifacts": artifacts}, indent=2) + "\n")


if __name__ == "__main__":
    main()
