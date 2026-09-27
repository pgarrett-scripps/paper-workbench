"""Frozen data, budget controls, and exact evidence validation."""

import json
import shutil
import threading
import time
from pathlib import Path

import runtime

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1] / "runs/pra-claim-investigation-v1"
read, write, Blocked = runtime.read_json, runtime.write_json, runtime.StudyBlocked
LOCK = threading.Lock()
INFLIGHT = 0


def source_text(source):
    return "\n\n".join(f"[{key}]\n{row['text']}" for key, row in source.items())


def usage():
    return [row for path in (ROOT / "work").rglob("usage.jsonl") for row in runtime.jsonl(path)]


def prepare():
    if (ROOT / "manifest.json").exists():
        verify()
        return
    protocol = read(HERE / "protocol.json")
    parent = Path(protocol["parent_root"])
    old_manifest = read(parent / "manifest.json")
    if runtime.source_manifest(parent / "inputs") != old_manifest["input_files"]:
        raise Blocked("Parent input manifest mismatch")
    for pid in protocol["paper_ids"]:
        dest = ROOT / "inputs" / pid
        dest.mkdir(parents=True, exist_ok=True)
        for name in ["manuscript.txt", "source_chunks.json", "reference.json", "reviewer_1.md", "reviewer_1_response.json"]:
            shutil.copy2(parent / "inputs" / pid / name, dest / name)
        generation = read(parent / "work" / pid / "generation.json")
        baseline = {key: row for key, row in generation["records"].items() if row["reviewer"] == "reviewer_1"}
        write(dest / "saved_single_candidates.json", baseline)
        write(dest / "saved_single_top.json", generation["stage_ids"]["reviewer_1_top"])
    shutil.copy2(parent / "public_data_provenance.json", ROOT / "public_data_provenance.json")
    write(ROOT / "protocol.json", protocol)
    write(ROOT / "manifest.json", {"created_at": time.time(), "runner_files": runtime.source_manifest(HERE),
          "input_files": runtime.source_manifest(ROOT / "inputs"), "protocol_sha256": runtime.digest(protocol),
          "parent_manifest_sha256": runtime.digest((parent / "manifest.json").read_bytes())})
    write(ROOT / "status.json", {"stage": "prepared"})


def verify():
    protocol, manifest = read(ROOT / "protocol.json"), read(ROOT / "manifest.json")
    runtime.validate_protocol(protocol)
    if runtime.digest(protocol) != manifest["protocol_sha256"]:
        raise Blocked("Frozen protocol changed")
    for path, key in [(HERE, "runner_files"), (ROOT / "inputs", "input_files")]:
        if runtime.source_manifest(path) != manifest[key]:
            raise Blocked(f"Frozen {key} changed")
    return protocol


def call(protocol, node, text, schema, source=None, arm=None):
    global INFLIGHT
    identity = runtime.digest({"prompt": text, "schema": schema, "tools": source is not None, "protocol": protocol})
    for attempt in (1, 2):
        out = node / f"attempt_{attempt}"
        cache = out / "calls" / f"{identity}.json"
        if cache.exists():
            record = read(cache)
            if record.get("ok"):
                return record["value"]
            if attempt == 1 and "stream disconnected before completion" in record.get("error", ""):
                continue
            raise Blocked("Saved failed attempt is not retryable")
        with LOCK:
            used = usage()
            if len(used) + INFLIGHT >= protocol["max_total_calls"] or sum(row.get("observed_tokens", 0) for row in used) >= protocol["max_total_tokens"]:
                raise Blocked("Global experiment budget reached")
            if arm is not None:
                arm_used = [row for path in arm.rglob("usage.jsonl") for row in runtime.jsonl(path)]
                if sum(row.get("observed_tokens", 0) for row in arm_used) >= protocol["max_arm_tokens"]:
                    raise Blocked("Arm observed-token stop reached")
            if attempt == 2:
                marker = node / "network_retry.json"
                if not marker.exists():
                    if len(list((ROOT / "work").rglob("network_retry.json"))) >= protocol["max_network_retries"]:
                        raise Blocked("Network retry allowance exhausted")
                    write(marker, {"policy": protocol["network_retry_policy"], "reserved_at": time.time()})
            INFLIGHT += 1
        try:
            if attempt == 2:
                time.sleep(10)
            if source is not None:
                work = out / "workspace"
                work.mkdir(parents=True, exist_ok=True)
                (work / "manuscript.txt").write_text(source_text(source))
            value = runtime.model_call(protocol, out, text, schema, tools=source is not None, label=node.name)
            import jsonschema
            jsonschema.validate(value, schema)
            return value
        except Exception:
            if attempt == 1 and cache.exists() and "stream disconnected before completion" in read(cache).get("error", ""):
                continue
            raise
        finally:
            with LOCK:
                INFLIGHT -= 1
    raise Blocked("Both network attempts failed")


def validate_evidence(value, source, receipts):
    if isinstance(value, dict):
        for key, row in value.items():
            if key in ("evidence_ids", "counterevidence_ids", "support") and isinstance(row, list):
                if len(row) != len(set(row)) or not set(row) <= set(source):
                    raise Blocked("Invalid evidence ID")
            elif key == "test_receipts":
                if not set(row) <= receipts:
                    raise Blocked("A calculation receipt was not executed in this arm")
            else:
                validate_evidence(row, source, receipts)
    elif isinstance(value, list):
        for item in value:
            validate_evidence(item, source, receipts)


def receipts_in(path):
    return {row["receipt"] for file in path.rglob("calculation_receipts.jsonl") for row in runtime.jsonl(file)}


def validate_final(value, cases, replies, source):
    if set(value["dispositions"]) != set(cases):
        raise Blocked("Incomplete dispositions")
    retained = {key for key, row in value["dispositions"].items() if row["status"] in ("retain", "unresolved")}
    rank = value["ranking"]
    chosen = value["selected_ids"]
    if len(rank) != len(set(rank)) or set(rank) != retained:
        raise Blocked("Incomplete ranking")
    if len(chosen) > 5 or len(chosen) != len(set(chosen)) or not set(chosen) <= retained:
        raise Blocked("Invalid final selection")
    if chosen != [key for key in rank if key in chosen]:
        raise Blocked("Final selection reorders ranking")
    for key, row in value["dispositions"].items():
        if not row["reason"].strip():
            raise Blocked("Empty disposition reason")
        if row["status"] == "duplicate":
            if row["duplicate_of"] not in retained or row["duplicate_of"] == key:
                raise Blocked("Invalid duplicate target")
        elif row["duplicate_of"]:
            raise Blocked("Unexpected duplicate target")
        if row["status"] == "answered" and not row["evidence_ids"]:
            raise Blocked("Answered finding lacks evidence")
        if key in retained and replies[key]["position"] == "withdraw":
            raise Blocked("Withdrawn criticism cannot silently reenter final output")
    intro = value["summary"] + "\n" + value["strengths"]
    if len(intro.split()) > 80:
        raise Blocked("Summary and strengths exceed 80 words")
    body = intro + "\n\n" + "\n\n".join(cases[key]["text"] for key in chosen)
    if len(body.split()) > 900:
        raise Blocked("Final review exceeds 900 words")
    return body


def metrics_usage():
    totals = {"attempts": len(usage()), "observed_tokens": 0, "cached_input_tokens": 0,
              "uncached_input_tokens": 0, "output_tokens": 0, "unknown_usage_calls": 0,
              "failures": 0, "calculation_receipts": 0}
    for path in (ROOT / "work").glob("**/calls/*.json"):
        record = read(path)
        if "label" not in record or "request_sha256" not in record:
            continue
        totals["failures"] += not record.get("ok", False)
        if "observed_tokens" not in record:
            totals["unknown_usage_calls"] += 1
            continue
        totals["observed_tokens"] += record["observed_tokens"]
        for event in record.get("events", []):
            if event.get("type") == "turn.completed":
                usage_row = event["usage"]
                cached = usage_row.get("cached_input_tokens", 0)
                totals["cached_input_tokens"] += cached
                totals["uncached_input_tokens"] += max(0, usage_row.get("input_tokens", 0) - cached)
                totals["output_tokens"] += usage_row.get("output_tokens", 0)
    totals["calculation_receipts"] = sum(len(runtime.jsonl(p)) for p in (ROOT / "work").rglob("calculation_receipts.jsonl"))
    return totals
