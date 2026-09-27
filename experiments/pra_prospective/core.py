"""Prospective comparison freezing, blinding, rating, and reporting."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import random
import shutil

VERSION = "pra-prospective-v2"
RATINGS = {"supported", "partly_supported", "unsupported", "cannot_assess"}
PRIVATE_KEYS = {"condition", "workflow", "model", "prompt", "debate", "investigator", "generation"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canon(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value, mode=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != data:
        raise ValueError("Immutable artifact changed: " + str(path))
    if not path.exists():
        path.write_text(data, encoding="utf-8")
        if mode is not None:
            os.chmod(path, mode)


def _files(path):
    path = Path(path)
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(item for item in path.rglob("*") if item.is_file() and "__pycache__" not in item.parts and item.suffix != ".pyc")
    raise ValueError("Missing path: " + str(path))


def _paper_ids(value):
    papers = value.get("papers", []) if isinstance(value, dict) else value
    if not isinstance(papers, list):
        raise ValueError("Paper manifest must contain a papers array")
    found = set()
    for row in papers:
        if not isinstance(row, dict):
            continue
        for key in ("paper_id", "doi"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                continue
            item = row[key].strip().lower()
            if key == "doi":
                for prefix in ("https://doi.org/", "http://doi.org/", "http://dx.doi.org/", "https://dx.doi.org/", "doi:"):
                    if item.startswith(prefix):
                        item = item[len(prefix):].strip()
                        break
            found.add(item)
    return found


def _contract(config):
    conditions = config.get("conditions", {})
    if set(conditions) != {"single", "pra"}:
        raise ValueError("Conditions must be exactly single and pra")
    strings = ("manuscript", "source_packet", "domain_guidance", "model", "review_path")
    budgets = ("tool_call_budget", "source_request_budget", "model_calls")
    for name, row in conditions.items():
        if any(not isinstance(row.get(key), str) or not row[key].strip() for key in strings):
            raise ValueError(name + " has a missing resource, model, or output path")
        if not isinstance(row.get("tools"), list) or not row["tools"] or not all(isinstance(x, str) and x for x in row["tools"]):
            raise ValueError(name + " must record nonempty tools")
        if not isinstance(row.get("images"), list) or not isinstance(row.get("settings"), dict) or not row["settings"]:
            raise ValueError(name + " has invalid images or settings")
        if any(not isinstance(row.get(key), int) or row[key] < 0 for key in budgets) or row["tool_call_budget"] < 1 or row["model_calls"] < 1:
            raise ValueError(name + " has an invalid budget")
        if not isinstance(row.get("usage_receipts", []), list):
            raise ValueError(name + " usage_receipts must be a list")
    parity = ("manuscript", "source_packet", "domain_guidance", "model", "settings", "images", "tools", "tool_call_budget", "source_request_budget")
    if any(conditions["single"][key] != conditions["pra"][key] for key in parity):
        raise ValueError("Conditions must have equal models, settings, resources, and tool budgets")


def _resolve(base, value):
    return (Path(base) / value).resolve()


def _snapshot(files, extra, directories=()):
    files = list(dict.fromkeys(Path(x).resolve() for x in files))
    common = Path(os.path.commonpath([str(x) for x in files]))
    if common.is_file():
        common = common.parent
    records = [{"path": str(x.relative_to(common)), "sha256": sha(x), "bytes": x.stat().st_size} for x in sorted(files)]
    directory_manifests = {str(Path(root).resolve()): [str(path.relative_to(Path(root).resolve())) for path in _files(root)]
                           for root in directories if Path(root).is_dir()}
    value = {**extra, "file_base": str(common), "files": records, "directory_manifests": directory_manifests,
             "snapshot_sha256": hashlib.sha256(canon(records)).hexdigest()}
    value["integrity_sha256"] = hashlib.sha256(canon(value)).hexdigest()
    return value


def seal(protocol_path, study):
    protocol_path, study = Path(protocol_path).resolve(), Path(study)
    config, base = read(protocol_path), protocol_path.parent
    if config.get("schema_version") != VERSION:
        raise ValueError("Unsupported protocol schema")
    _contract(config)
    required = ("prompt_paths", "settings_paths", "implementation_paths", "domain_paths")
    if any(not isinstance(config.get(key), list) or not config[key] for key in required):
        raise ValueError("Prompt, settings, implementation, and domain paths are required")
    candidates = read(_resolve(base, config["candidate_manifest"]))
    prior = read(_resolve(base, config["prior_corpus_manifest"]))
    overlap = sorted(_paper_ids(candidates) & _paper_ids(prior))
    if overlap:
        raise ValueError("Held-out papers overlap the prior corpus: " + ", ".join(overlap))
    outputs = [_resolve(base, config["conditions"][name]["review_path"]) for name in ("single", "pra")]
    if any(path.exists() for path in outputs):
        raise ValueError("Seal must occur before review outputs exist")
    paths = [protocol_path, _resolve(base, config["candidate_manifest"]), _resolve(base, config["prior_corpus_manifest"])]
    directories = []
    for key in required + ("frozen_paths",):
        for value in config.get(key, []):
            resolved = _resolve(base, value)
            paths += _files(resolved)
            if resolved.is_dir():
                directories.append(resolved)
    shared = config["conditions"]["single"]
    for key in ("manuscript", "source_packet", "domain_guidance"):
        resolved = _resolve(base, shared[key])
        paths += _files(resolved)
        if resolved.is_dir():
            directories.append(resolved)
    for image in shared["images"]:
        paths += _files(_resolve(base, image.get("path") if isinstance(image, dict) else image))
    repo = Path(__file__).resolve().parents[2]
    for root in (repo / "paper_workspace", Path(__file__).resolve().parent):
        content = _files(root)
        paths += content if root.name == "paper_workspace" else [path for path in content if path.suffix == ".py"]
        if root.name == "paper_workspace":
            directories.append(root)
    value = _snapshot(paths, {"schema_version": VERSION, "stage": "pretrial_sealed", "protocol": config,
        "config_base": str(base), "candidate_paper_identifiers": sorted(_paper_ids(candidates)),
        "prior_paper_identifiers": sorted(_paper_ids(prior)), "prior_paper_overlap": [],
        "module_python_files": [str(path.relative_to(Path(__file__).resolve().parent))
                                for path in _files(Path(__file__).resolve().parent) if path.suffix == ".py"]}, directories)
    write_new(study / "pretrial-snapshot.json", value)
    (study / "status.json").write_text('{"stage":"pretrial_sealed"}\n', encoding="utf-8")
    return value


def _verify_snapshot(path):
    value = read(path)
    integrity = value.pop("integrity_sha256", None)
    if integrity != hashlib.sha256(canon(value)).hexdigest():
        raise ValueError("Snapshot metadata failed verification")
    value["integrity_sha256"] = integrity
    base, failures = Path(value["file_base"]), []
    for row in value["files"]:
        path = base / row["path"]
        if not path.is_file() or sha(path) != row["sha256"] or path.stat().st_size != row["bytes"]:
            failures.append(row["path"])
    for root, expected in value.get("directory_manifests", {}).items():
        current = [str(path.relative_to(Path(root))) for path in _files(root)]
        if current != expected:
            failures.append("directory:" + root)
    if "module_python_files" in value:
        module = Path(__file__).resolve().parent
        current = [str(path.relative_to(module)) for path in _files(module) if path.suffix == ".py"]
        if current != value["module_python_files"]:
            failures.append("prospective module Python files")
    if failures:
        raise ValueError("Frozen files failed verification: " + ", ".join(failures))
    return value


def verify(study):
    study = Path(study)
    pre = _verify_snapshot(study / "pretrial-snapshot.json")
    gen = _verify_snapshot(study / "generation-snapshot.json") if (study / "generation-snapshot.json").exists() else None
    manifest = study / "exports/manifest.json"
    if manifest.exists():
        item = read(manifest)
        if sha(item["packet_path"]) != item["packet_sha256"] or sha(study / "private/condition-map.json") != item["mapping_sha256"]:
            raise ValueError("Anonymous export failed verification")
        evidence = Path(item["evidence_path"])
        current = {str(x.relative_to(evidence)): sha(x) for x in _files(evidence)}
        if current != item["evidence_files"]:
            raise ValueError("Portable evidence failed verification")
    return {"verified": True, "stage": "reviews_attached" if gen else "pretrial_sealed",
            "pretrial_sha256": pre["snapshot_sha256"], "generation_sha256": gen["snapshot_sha256"] if gen else None}


def attach_reviews(study):
    study = Path(study)
    state = verify(study)
    if state["stage"] == "reviews_attached":
        return read(study / "generation-snapshot.json")
    pre, files = read(study / "pretrial-snapshot.json"), []
    base = Path(pre["config_base"])
    receipts = {}
    for name in ("single", "pra"):
        row = pre["protocol"]["conditions"][name]
        files += _files(_resolve(base, row["review_path"]))
        receipts[name] = row.get("usage_receipts", [])
        for path in receipts[name]:
            files += _files(_resolve(base, path))
    value = _snapshot(files, {"schema_version": VERSION, "stage": "reviews_attached",
                              "pretrial_sha256": pre["snapshot_sha256"], "usage_receipts": receipts})
    write_new(study / "generation-snapshot.json", value)
    (study / "status.json").write_text('{"stage":"reviews_attached"}\n', encoding="utf-8")
    return value


def _clean(value):
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items() if str(k).lower() not in PRIVATE_KEYS}
    if isinstance(value, list):
        return [_clean(x) for x in value]
    return value


def _evidence_ids(value):
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"evidence_id", "source_id"} and isinstance(item, str):
                found.add(item)
            found.update(_evidence_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_evidence_ids(item))
    return found


def _cards(review):
    cards = review.get("source_cards")
    if cards is None and isinstance(review.get("raw_response"), dict):
        cards = review["raw_response"].get("source_cards")
    return cards or []


def export_anonymous(study, output, seed):
    study, output = Path(study), Path(output)
    state = verify(study)
    if state["stage"] != "reviews_attached":
        raise ValueError("Attach reviews before export")
    pre, names = read(study / "pretrial-snapshot.json"), ["single", "pra"]
    base, config = Path(pre["config_base"]), pre["protocol"]
    random.Random(seed).shuffle(names)
    candidates, mapping, card_map = [], {"seed": seed, "labels": {}}, {}
    packet_hashes = {sha(path) for path in _files(_resolve(base, config["conditions"]["single"]["source_packet"]))}
    allowed = ("title", "block_id", "quote", "kind", "severity", "comment", "replacement", "evidence_blocks", "counterevidence", "source_evidence")
    for label, name in zip(("Review A", "Review B"), names):
        path = _resolve(base, config["conditions"][name]["review_path"])
        review = read(path)
        findings = [{"item_id": label[-1] + str(i), **_clean({k: row.get(k) for k in allowed if k in row})}
                    for i, row in enumerate(review.get("findings", []), 1)]
        referenced = {citation.get("evidence_id") for finding in findings
                      for citation in (finding.get("source_evidence", []) or [])}
        for card in _cards(review):
            evidence_id = card.get("evidence_id")
            if evidence_id not in referenced:
                continue
            if not isinstance(evidence_id, str) or not evidence_id:
                raise ValueError("Review source card lacks an evidence ID")
            if card.get("raw_sha256") not in packet_hashes:
                raise ValueError("Review source card is not backed by the frozen raw packet: " + evidence_id)
            card_fields = ("status", "source_url", "raw_sha256", "provider", "identifier", "manuscript_block_id",
                           "evidence_mode", "cutoff", "record_version", "source_publication_date", "fields",
                           "evidence_text", "limitation", "eligible", "evidence_id", "captured_at", "effective_date",
                           "version_locator", "curator_attestation")
            cleaned = {key: card.get(key) for key in card_fields if key in card}
            if evidence_id in card_map and canon(card_map[evidence_id]) != canon(cleaned):
                raise ValueError("Conflicting source cards: " + evidence_id)
            card_map[evidence_id] = cleaned
        candidates.append({"label": label, "findings": findings})
        mapping["labels"][label] = {"condition": name, "review_sha256": sha(path)}
    for candidate in candidates:
        for finding in candidate["findings"]:
            for citation in finding.get("source_evidence", []) or []:
                evidence_id, quote = citation.get("evidence_id"), citation.get("quote", "")
                if evidence_id not in card_map:
                    raise ValueError("Dangling source evidence ID: " + str(evidence_id))
                if not quote or quote not in card_map[evidence_id].get("evidence_text", ""):
                    raise ValueError("Invalid source evidence quote: " + str(evidence_id))
    shared = config["conditions"]["single"]
    manuscript = _resolve(base, shared["manuscript"])
    paper = read(manuscript / "paper.json" if manuscript.is_dir() else manuscript)
    evidence_dir = output / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    for i, evidence_id in enumerate(sorted(card_map), 1):
        target = evidence_dir / ("source-%03d.json" % i)
        target.write_text(json.dumps(card_map[evidence_id], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        cards.append({"evidence_id": evidence_id, "path": "evidence/" + target.name,
                      "sha256": sha(target), "content": card_map[evidence_id]})
    images = []
    for i, item in enumerate(shared["images"], 1):
        source = _resolve(base, item.get("path") if isinstance(item, dict) else item)
        target = evidence_dir / ("image-%03d%s" % (i, source.suffix.lower()))
        shutil.copyfile(source, target)
        images.append({"image_id": "image-%03d" % i, "path": "evidence/" + target.name, "sha256": sha(target),
                       "label": item.get("label", "Evidence image") if isinstance(item, dict) else "Evidence image"})
    packet = {"schema_version": VERSION, "pretrial_sha256": state["pretrial_sha256"],
        "generation_sha256": state["generation_sha256"], "candidates": candidates,
        "manuscript": _clean({k: paper[k] for k in ("id", "title", "blocks", "references") if k in paper}),
        "source_cards": cards, "images": images, "limitations": config.get("evidence_limitations", [])}
    write_new(output / "assessment-packet.json", packet)
    write_new(study / "private/condition-map.json", mapping, 0o600)
    write_new(study / "exports/manifest.json", {"packet_path": str((output / "assessment-packet.json").resolve()),
        "packet_sha256": sha(output / "assessment-packet.json"), "mapping_sha256": sha(study / "private/condition-map.json"),
        "evidence_path": str(evidence_dir.resolve()), "evidence_files": {str(x.relative_to(evidence_dir)): sha(x) for x in _files(evidence_dir)}})
    return packet


def import_ratings(study, packet_path, ratings_path):
    study, packet_path = Path(study), Path(packet_path)
    verify(study)
    exported = read(study / "exports/manifest.json")
    if packet_path.resolve() != Path(exported["packet_path"]).resolve() or sha(packet_path) != exported["packet_sha256"]:
        raise ValueError("Ratings must use the recorded anonymous packet")
    packet, value = read(packet_path), read(ratings_path)
    required = ("assessor_id", "expertise", "independence_attestation", "rated_at", "source_sha256")
    provenance = value.get("provenance", {})
    if any(not isinstance(provenance.get(k), str) or not provenance[k].strip() for k in required):
        raise ValueError("Rating provenance is incomplete")
    try:
        dt.date.fromisoformat(provenance["rated_at"])
    except ValueError as exc:
        raise ValueError("rated_at must be an ISO date") from exc
    if provenance["source_sha256"] != exported["packet_sha256"]:
        raise ValueError("Ratings reference the wrong packet")
    items = {x["item_id"] for c in packet["candidates"] for x in c["findings"]}
    blocks = {str(x["id"]): str(x["text"]) for x in packet["manuscript"].get("blocks", [])}
    seen, rows = set(), []
    for row in value.get("ratings", []):
        item = row.get("item_id")
        if item not in items or item in seen:
            raise ValueError("Unknown or duplicated rating item")
        seen.add(item)
        if row.get("assessment") not in RATINGS:
            raise ValueError("Invalid assessment")
        applicable = row["assessment"] != "cannot_assess"
        if applicable and (row.get("evidence_block_id") not in blocks or not row.get("evidence_quote") or row["evidence_quote"] not in blocks[row["evidence_block_id"]]):
            raise ValueError("Evidence quote failed validation")
        rows.append({**row, "quote_validated": applicable, "quote_validation": "exact_match" if applicable else "not_applicable"})
    assessor = provenance["assessor_id"]
    if "/" in assessor or "\\" in assessor:
        raise ValueError("Unsafe assessor ID")
    result = {"schema_version": VERSION, "provenance": provenance, "identity_verified": False, "ratings": rows,
              "completion": {"rated": len(rows), "expected": len(items), "missing": sorted(items - seen)}}
    result["integrity_sha256"] = hashlib.sha256(canon(result)).hexdigest()
    write_new(study / "ratings" / (assessor + ".json"), result)
    return result


def _usage(pre, attached):
    base, result = Path(pre["config_base"]), {}
    for name in ("single", "pra"):
        rows = []
        if not attached:
            result[name] = {"status": "unknown", "receipt_count": 0, "observed": {}}
            continue
        for item in pre["protocol"]["conditions"][name].get("usage_receipts", []):
            path = _resolve(base, item)
            try:
                value = read(path)
                rows += value if isinstance(value, list) else [value]
            except json.JSONDecodeError:
                rows += [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        observed = {}
        for key in ("observed_tokens", "input_tokens", "output_tokens", "cost_usd"):
            values = [x[key] for x in rows if isinstance(x, dict) and isinstance(x.get(key), (int, float))]
            if values:
                observed[key] = sum(values)
        unknown = any(not isinstance(row, dict) or row.get("usage_unknown") or not isinstance(row.get("observed_tokens"), (int, float)) for row in rows)
        status = "known" if rows and not unknown else ("partial" if rows and observed else "unknown")
        result[name] = {"status": status, "receipt_count": len(rows), "observed": observed}
    return result


def report(study, output):
    study = Path(study)
    state, pre = verify(study), read(study / "pretrial-snapshot.json")
    values = []
    for path in sorted((study / "ratings").glob("*.json")) if (study / "ratings").exists() else []:
        value = read(path)
        integrity = value.pop("integrity_sha256", None)
        if integrity != hashlib.sha256(canon(value)).hexdigest():
            raise ValueError("Rating failed verification")
        values.append(value)
    rows = [row for value in values for row in value["ratings"]]
    packet_items = set()
    if (study / "exports/manifest.json").exists():
        packet = read(read(study / "exports/manifest.json")["packet_path"])
        packet_items = {x["item_id"] for c in packet["candidates"] for x in c["findings"]}
    missing = sorted({x for v in values for x in v["completion"]["missing"]} if values else packet_items)
    mapping_path = study / "private/condition-map.json"
    mapping = read(mapping_path)["labels"] if mapping_path.exists() else {}
    by_condition = {}
    for label, details in mapping.items():
        selected = [row for row in rows if row["item_id"].startswith(label[-1])]
        by_condition[details["condition"]] = {x: sum(row["assessment"] == x for row in selected) for x in sorted(RATINGS)}
    summary = {"schema_version": VERSION, "study_stage": state["stage"],
        "rating_status": "unscored" if not values else ("incomplete" if missing else "complete"),
        "attested_independent_assessors": len(values), "assessor_identity_verification": "not_performed",
        "rated_items": len(rows), "missing_item_ids": missing,
        "expert_correctness": {x: sum(r["assessment"] == x for r in rows) for x in sorted(RATINGS)},
        "expert_correctness_by_condition": by_condition,
        "model_preference": {"status": "separate_not_imported"}, "human_review_overlap": {"status": "separate_not_imported"},
        "cost": {"observed_by_condition": _usage(pre, state["stage"] == "reviews_attached"), "planned_budgets": {name: {key: pre["protocol"]["conditions"][name][key]
                 for key in ("model_calls", "tool_call_budget", "source_request_budget")} for name in ("single", "pra")}},
        "limitations": ["Independence is attested and identity is not verified.", "Missing ratings and usage receipts remain explicit."]}
    write_new(output, summary)
    return summary


freeze = seal
