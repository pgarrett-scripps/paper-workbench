#!/usr/bin/env python3
"""Prepare, run, and audit the subscription-backed development pilot."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

from common import (
    DEFAULT_ROOT, HERE, StudyBlocked, append_json, auth_status, model_call,
    clean_env, digest, jsonl, quote_present, quote_match_mode, read_json, require_subscription,
    source_manifest, validate_concerns, validate_protocol, verify_study, write_json,
)
from prompts import (
    CONCERNS_SCHEMA, EXTRACT, JUDGE, JUDGE_SCHEMA, PLAIN_SCHEMA, REFERENCE,
    REFERENCE_CHECK_SCHEMA, REFERENCE_SCHEMA, RUBRIC,
)


def prepare(root):
    protocol = read_json(HERE / "protocol.json")
    validate_protocol(protocol)
    if (root / "manifest.json").exists():
        try:
            verify_study(root)
            print("Existing frozen pilot verified. No data were replaced.")
            return
        except StudyBlocked:
            if any(root.glob("**/*.request.json")):
                raise StudyBlocked("This pilot already has model attempts. Use a new root for changed code or protocol.")
            print("Refreshing preparation before the first model attempt.")
    root.mkdir(parents=True, exist_ok=True)
    corpus = Path(protocol["prior_corpus"])
    rows = jsonl(corpus / "corpus.jsonl")
    reviews = {r["paper_id"]: r for r in jsonl(corpus / "human_reviews.jsonl")}
    old_manifest = read_json(corpus / "corpus_manifest.json")
    if digest((corpus / "corpus.jsonl").read_bytes()) != old_manifest["corpus_sha256"]:
        raise StudyBlocked("Legacy corpus manifest does not match its current file")
    if digest((corpus / "human_reviews.jsonl").read_bytes()) != old_manifest["human_reviews_file"]["sha256"]:
        raise StudyBlocked("Legacy human reviews have changed")
    random.Random(protocol["seed"]).shuffle(rows)
    selected = rows[:protocol["pilot_size"]]
    papers = []
    for row in selected:
        paper_id = row["id"]
        original = corpus / row["pdf_path"]
        body = original.read_bytes()
        if digest(body) != old_manifest["papers"][paper_id]["sha256"]:
            raise StudyBlocked(f"Legacy manuscript hash mismatch: {paper_id}")
        packet = root / "inputs" / paper_id / "manuscript.txt"
        packet.parent.mkdir(parents=True, exist_ok=True)
        packet.write_bytes(body)
        ref = root / "references" / paper_id / "human_reviews.json"
        write_json(ref, reviews[paper_id])
        papers.append({
            "paper_id": paper_id, "title": row["title"], "source_url": row["source_url"],
            "manuscript": str(packet.relative_to(root)), "manuscript_sha256": digest(body),
            "reviews": str(ref.relative_to(root)), "reviews_sha256": digest(ref.read_bytes()),
            "version_verified": False, "figure_access_verified": False,
            "eligibility": "development_candidate_only", "prior_development_exposure": True,
            "pairing_evidence": "Legacy mirrored corpus. Original submission and review revisions unverified.",
        })
    source = Path(protocol["pra_source"])
    target = root / "source" / "peerreviewagents"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source / "peerreviewagents", target,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    version = subprocess.run(["git", "rev-parse", "HEAD"], cwd=source,
                             capture_output=True, text=True, check=True).stdout.strip()
    write_json(root / "protocol.json", protocol)
    write_json(root / "manifest.json", {
        "created_at": time.time(), "protocol_sha256": digest(protocol),
        "pra_git_revision": version, "pra_files": source_manifest(target),
        "runner_files": source_manifest(HERE), "papers": papers,
        "sampling": "Seeded shuffle of 20 historical development records, no performance-based selection",
        "held_out": False,
    })
    write_json(root / "status.json", {"stage": "prepared", "generation_runs": 0,
               "blockers": ["Subscription login and billing confirmation required",
                            "Exact manuscript-review pairing remains unverified"]})
    print(f"Prepared {len(papers)} development candidates at {root}")


def preflight(root):
    protocol, manifest = verify_study(root)
    status = auth_status(protocol["provider"])
    blockers = []
    try:
        require_subscription(root)
    except StudyBlocked as exc:
        blockers.append(str(exc))
    if not Path(protocol["pra_python"]).exists():
        blockers.append("PeerReviewAgents Python runtime is missing")
    if any(not p["version_verified"] for p in manifest["papers"]):
        blockers.append("Pilot candidates are unverified. Only explicitly labeled development smoke runs are allowed.")
    result = {"model": protocol["model"], "auth": status, "blockers": blockers,
              "candidates": len(manifest["papers"]), "api_inference_calls_made": 0}
    write_json(root / "preflight.json", result)
    print(json.dumps(result, indent=2))
    return 2 if blockers else 0


def baseline(root, item, condition, protocol):
    paper_id = item["paper_id"]
    out = root / "generation" / paper_id / condition
    body = (root / item["manuscript"]).read_text()
    if condition == "single_agent":
        work = out / "workspace"
        work.mkdir(parents=True, exist_ok=True)
        (work / "manuscript.txt").write_text(body)
        prompt = RUBRIC + """
You have access to manuscript.txt in this workspace. Read the complete paper.
Inspect specific passages and cross-check your claims using local read tools.
Develop and critically revise your assessment before returning the final review.
Spend the effort needed for a careful assessment, including reconsidering your
initial interpretation. Do not delegate, search online, or access other papers.
Return your final review in the content field.
"""
    else:
        prompt = RUBRIC + "\nReturn your final review in content.\nMANUSCRIPT\n" + body
    raw = model_call(protocol, out, prompt, PLAIN_SCHEMA,
                      tools=condition == "single_agent", label=condition)["content"]
    (out / "review.md").write_text(raw)
    if len(raw.split()) > protocol["final_word_limit"]:
        raise StudyBlocked("Baseline exceeded the shared final word allowance")
    value = model_call(protocol, out, EXTRACT + "\nREVIEW\n" + raw,
                        CONCERNS_SCHEMA, label="extract_final_concerns")
    concerns = validate_concerns(value, raw, maximum=protocol["max_concerns"])
    if sum(len(c["source_quote"].split()) for c in concerns) > protocol["final_word_limit"]:
        raise StudyBlocked("Extracted concerns exceed the common word allowance")
    write_json(out / "result.json", {"ok": True, "paper_id": paper_id,
               "condition": condition, "concerns": concerns, "model": protocol["model"],
               "phase": "development", "scientific_version_verified": item["version_verified"]})


def choose_papers(manifest, args):
    papers = manifest["papers"]
    if args.paper:
        papers = [p for p in papers if p["paper_id"] == args.paper]
        if not papers:
            raise StudyBlocked("Unknown paper ID")
    return papers[:args.limit] if args.limit else papers


def run(root, args):
    protocol, manifest = verify_study(root)
    require_subscription(root)
    papers = choose_papers(manifest, args)
    if any(not p["version_verified"] for p in papers) and not args.development_smoke:
        raise StudyBlocked("Unverified version pairs. Use development-smoke only for a non-scientific execution check.")
    for item in papers:
        conditions = list(protocol["conditions"])
        random.Random(f"{protocol['seed']}:{item['paper_id']}").shuffle(conditions)
        # Paired no-debate execution requires the shared panel checkpoint.
        if conditions.index("pra_no_debate") < conditions.index("pra_full"):
            a, b = conditions.index("pra_no_debate"), conditions.index("pra_full")
            conditions[a], conditions[b] = conditions[b], conditions[a]
        for condition in conditions:
            out = root / "generation" / item["paper_id"] / condition
            if (out / "result.json").exists() and read_json(out / "result.json").get("ok"):
                continue
            write_json(root / "status.json", {"stage": "generating", "paper_id": item["paper_id"],
                       "condition": condition, "development_smoke": args.development_smoke})
            if condition.startswith("pra_"):
                result = subprocess.run([protocol["pra_python"], str(HERE / "worker.py"),
                                         str(root), item["paper_id"], condition], env=clean_env())
                if result.returncode:
                    raise StudyBlocked(f"{condition} stopped. Inspect preserved artifacts before retrying.")
            else:
                baseline(root, item, condition, protocol)
    write_json(root / "status.json", {"stage": "generation_complete", "papers": len(papers),
               "development_smoke": args.development_smoke, "scientific_results": False})


def reference_inventory(root, item, protocol):
    out = root / "evaluation" / item["paper_id"] / "reference"
    final = out / "reference.json"
    if final.exists():
        return read_json(final)
    human = read_json(root / item["reviews"])
    # Exclude decisions and numerical ratings from the reference extraction task.
    reviews = [{k: r[k] for k in ("weaknesses", "questions") if k in r}
               for r in human["reviews"]]
    text = "\n\n".join(f"REVIEW {i+1}\n" + "\n".join(r.values()) for i, r in enumerate(reviews))
    extracted = model_call(protocol, out, REFERENCE + "\n" + text,
                            REFERENCE_SCHEMA, label="reference_extract")
    concerns = validate_concerns(extracted, text)
    check = model_call(protocol, out,
        "Check EVERY extracted concern for faithful source meaning, substantive criticism, and semantic uniqueness. "
        "Do not judge scientific correctness. Return each concern ID once.\nSOURCE\n" + text +
        "\nEXTRACTED\n" + json.dumps(concerns), REFERENCE_CHECK_SCHEMA, label="reference_check")
    expected = {c["id"] for c in concerns}
    checked = [c["id"] for c in check["checks"]]
    if len(checked) != len(set(checked)) or set(checked) != expected:
        raise StudyBlocked("Reference checker omitted or duplicated IDs")
    valid = {c["id"] for c in check["checks"] if c["faithful_substantive_unique"]}
    result = {"concerns": [c for c in concerns if c["id"] in valid],
              "excluded": [c for c in concerns if c["id"] not in valid],
              "checks": check["checks"], "source_sha256": item["reviews_sha256"]}
    write_json(final, result)
    return result


def validate_judgment(value, refs, candidates, manuscript):
    ref_ids = {r["id"] for r in refs}
    cand_ids = {c["id"] for c in candidates}
    matches = value["matches"]
    supports = value["support"]
    if len(matches) != len(ref_ids) or {r["reference_id"] for r in matches} != ref_ids:
        raise StudyBlocked("Judge omitted or duplicated reference IDs")
    if len(supports) != len(cand_ids) or {r["candidate_id"] for r in supports} != cand_ids:
        raise StudyBlocked("Judge omitted or duplicated candidate IDs")
    for row in matches:
        if not set(row["candidate_ids"]) <= cand_ids or bool(row["candidate_ids"]) != row["matched"]:
            raise StudyBlocked("Judge returned invalid match IDs")
    for row in supports:
        if row["label"] not in {"supported", "contradicted", "insufficient_evidence"}:
            raise StudyBlocked("Judge returned an unknown support label")
        row["evidence_match_mode"] = quote_match_mode(row["evidence_quote"], manuscript)
        row["evidence_valid"] = row["label"] == "insufficient_evidence" or row["evidence_match_mode"] is not None
        row["validation_status"] = "valid" if row["evidence_valid"] else "unmatched_quote_pending_audit"
    return value


def score(root, args):
    protocol, manifest = verify_study(root)
    require_subscription(root)
    papers = choose_papers(manifest, args)
    if any(not p["version_verified"] for p in papers) and not args.development_smoke:
        raise StudyBlocked("Unverified pairs cannot produce scientific scores")
    # Freeze every reference inventory before beginning any output comparisons.
    inventories = {p["paper_id"]: reference_inventory(root, p, protocol) for p in papers}
    mapping = []
    for item in papers:
        body = (root / item["manuscript"]).read_text()
        refs = inventories[item["paper_id"]]["concerns"]
        conditions = list(protocol["conditions"])
        random.Random(f"judge:{protocol['seed']}:{item['paper_id']}").shuffle(conditions)
        for i, condition in enumerate(conditions):
            result_path = root / "generation" / item["paper_id"] / condition / "result.json"
            if not result_path.exists():
                continue
            candidate = read_json(result_path)["concerns"]
            anonymous_id = f"review_{i+1}"
            mapping.append({"paper_id": item["paper_id"], "anonymous_id": anonymous_id, "condition": condition})
            for judge in ("A", "B"):
                out = root / "evaluation" / item["paper_id"] / anonymous_id / judge
                if (out / "judgment.json").exists():
                    saved = read_json(out / "judgment.json")
                    validate_judgment(saved, refs, candidate, body)
                    write_json(out / "judgment.json", saved)
                    continue
                ordered_refs = refs if judge == "A" else list(reversed(refs))
                ordered_candidates = candidate if judge == "A" else list(reversed(candidate))
                prompt = JUDGE
                if judge == "B":
                    prompt += "\nActively consider alternative interpretations before deciding each match.\n"
                prompt += "\nMANUSCRIPT\n" + body + "\nREFERENCES\n" + json.dumps(ordered_refs)
                prompt += "\nCANDIDATE CONCERNS\n" + json.dumps(ordered_candidates)
                value = model_call(protocol, out, prompt, JUDGE_SCHEMA, label="judge_" + judge)
                validate_judgment(value, refs, candidate, body)
                write_json(out / "judgment.json", value)
    key_path = root / "evaluation" / "condition_key.json"
    previous = read_json(key_path) if key_path.exists() else []
    combined = {(r["paper_id"], r["anonymous_id"]): r for r in previous + mapping}
    write_json(key_path, list(combined.values()))
    write_json(root / "status.json", {"stage": "automated_scoring_complete", "manual_audit": "pending",
               "scientific_results": False})


def summarize(root):
    protocol, manifest = verify_study(root)
    map_path = root / "evaluation" / "condition_key.json"
    mapping = read_json(map_path) if map_path.exists() else []
    rows = []
    for entry in mapping:
        base = root / "evaluation" / entry["paper_id"] / entry["anonymous_id"]
        if not all((base / j / "judgment.json").exists() for j in ("A", "B")):
            continue
        judgments = [read_json(base / j / "judgment.json") for j in ("A", "B")]
        sets = [{r["reference_id"] for r in j["matches"] if r["matched"]} for j in judgments]
        denominator = len(judgments[0]["matches"])
        invalid = [{r["candidate_id"] for r in j["support"] if not r.get("evidence_valid", False)}
                   for j in judgments]
        support_complete = not any(invalid)
        supported = [{r["candidate_id"] for r in j["support"] if r["label"] == "supported" and r.get("evidence_valid", False)}
                     for j in judgments]
        false_major = [{r["candidate_id"] for r in j["support"]
                        if r["label"] == "contradicted" and r["major"] and r.get("evidence_valid", False)} for j in judgments]
        usage = jsonl(root / "generation" / entry["paper_id"] / entry["condition"] / "usage.jsonl")
        if entry["condition"] == "pra_no_debate":
            panel_usage_path = root / "generation" / entry["paper_id"] / "pra_full" / "panel_usage.json"
            if not panel_usage_path.exists():
                raise StudyBlocked("Missing shared-panel usage prevents standalone no-debate accounting")
            usage = read_json(panel_usage_path) + usage
        rows.append({**entry, "n_reference": denominator,
                     "n_generated_concerns": len(judgments[0]["support"]),
                     "n_supported_both_evaluators": len(supported[0] & supported[1]) if support_complete else None,
                     "n_false_major_both_evaluators": len(false_major[0] & false_major[1]) if support_complete else None,
                     "support_statistics_complete": support_complete,
                     "n_invalid_evidence_A": len(invalid[0]), "n_invalid_evidence_B": len(invalid[1]),
                     "observed_tokens_including_shared_panel": sum(r.get("observed_tokens", 0) for r in usage),
                     "subscription_sessions_including_shared_panel": len(usage),
                     "active_seconds_including_shared_panel": sum(r.get("elapsed_seconds", 0) for r in usage),
                     "usage_unknown_calls": sum("observed_tokens" not in r for r in usage),
                     "coverage_A": len(sets[0]) / denominator if denominator else None,
                     "coverage_B": len(sets[1]) / denominator if denominator else None,
                     "coverage_agreement": len(sets[0] & sets[1]) / denominator if denominator else None,
                     "coverage_either": len(sets[0] | sets[1]) / denominator if denominator else None})
    report = {"phase": "development", "scientific_results": False, "paper_metrics": rows,
              "limitations": protocol["limitations"] + [
                  "Support statistics are withheld for any condition with unmatched evaluator evidence. Unmatched quotes require manual audit."],
              "human_audit": "pending",
              "n_completed_generation": len(list((root / "generation").glob("*/*/result.json"))),
              "n_candidates": len(manifest["papers"])}
    write_json(root / "report.json", report)
    print(json.dumps(report, indent=2))


def audit(root):
    _, manifest = verify_study(root)
    items = []
    evidence_failures = []
    key_path = root / "evaluation" / "condition_key.json"
    mapping = read_json(key_path) if key_path.exists() else []
    condition_key = {(r["paper_id"], r["anonymous_id"]): r["condition"] for r in mapping}
    package = root / "manual_audit"
    for paper in manifest["papers"]:
        evidence = package / "evidence" / paper["paper_id"]
        evidence.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / paper["manuscript"], evidence / "manuscript.txt")
        shutil.copyfile(root / paper["reviews"], evidence / "human_reviews.json")
        ref_path = root / "evaluation" / paper["paper_id"] / "reference" / "reference.json"
        references = []
        if ref_path.exists():
            refs = read_json(ref_path)
            references = refs["concerns"]
            for row in refs["concerns"] + refs["excluded"]:
                items.append({"paper_id": paper["paper_id"], "category": "reference_extraction",
                              "claim": row["claim"], "source_quote": row["source_quote"]})
        for path in (root / "evaluation" / paper["paper_id"]).glob("review_*/A/judgment.json"):
            value = read_json(path)
            anonymous_id = path.parent.parent.name
            condition = condition_key[(paper["paper_id"], anonymous_id)]
            candidates = read_json(root / "generation" / paper["paper_id"] / condition / "result.json")["concerns"]
            for category, rows in (("matching", value["matches"]), ("support", value["support"])):
                for row in rows:
                    items.append({"paper_id": paper["paper_id"], "category": category,
                                  "anonymous_review": anonymous_id,
                                  "references": references, "candidates": candidates,
                                  "target_id": row.get("reference_id") or row.get("candidate_id"),
                                  "automated_judgment": row})
    for entry in mapping:
        candidate = read_json(root / "generation" / entry["paper_id"] / entry["condition"] / "result.json")["concerns"]
        for judge in ("A", "B"):
            path = root / "evaluation" / entry["paper_id"] / entry["anonymous_id"] / judge / "judgment.json"
            if not path.exists():
                continue
            for row in read_json(path)["support"]:
                if not row.get("evidence_valid", False):
                    evidence_failures.append({"paper_id": entry["paper_id"], "anonymous_review": entry["anonymous_id"],
                                              "judge": judge, "candidate_id": row["candidate_id"],
                                              "candidate": next(c for c in candidate if c["id"] == row["candidate_id"]),
                                              "attempted_quote": row["evidence_quote"]})
    write_json(package / "unmatched_evidence.json", {"purpose": "Complete validation-failure queue, separate from the random audit sample",
               "items": evidence_failures, "human_ratings": "pending"})
    if not items:
        raise StudyBlocked("No model judgments exist to audit")
    # Pilot audit is a simple random sample. Later stratification needs weights.
    random.Random(20260916).shuffle(items)
    selected = items[:150]
    expected = []
    for i, row in enumerate(selected):
        if "automated_judgment" in row:
            expected.append({"audit_id": f"A{i+1:03d}", "judgment": row.pop("automated_judgment")})
    write_json(root / "evaluation" / "audit_scoring_key.json", expected)
    write_json(package / "items.json", {"sampling": "simple random sample without replacement",
               "population": len(items), "inclusion_probability": len(selected) / len(items),
               "items": [{"audit_id": f"A{i+1:03d}", **r} for i, r in enumerate(selected)]})
    with (package / "ratings.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["audit_id", "assessor", "correct", "reason", "evidence_location"])
        writer.writerows([[f"A{i+1:03d}", "", "", "", ""] for i in range(len(selected))])
    print(f"Prepared {len(selected)} audit items. Human ratings are empty.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "preflight", "summarize", "audit"):
        sub.add_parser(name)
    sub.add_parser("pilot", help="Run one execution check, then the remaining development candidates")
    billing = sub.add_parser("confirm-billing")
    billing.add_argument("--extra-usage-disabled", action="store_true", required=True)
    for name in ("run", "score"):
        p = sub.add_parser(name)
        p.add_argument("--paper")
        p.add_argument("--limit", type=int)
        p.add_argument("--development-smoke", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "prepare":
            prepare(root)
        elif args.command == "preflight":
            return preflight(root)
        elif args.command == "confirm-billing":
            write_json(root / "billing_confirmation.json", {"extra_usage_disabled": True,
                       "confirmed_at": time.time(), "source": "operator confirmation"})
        elif args.command == "run":
            run(root, args)
        elif args.command == "pilot":
            args.paper = None
            args.development_smoke = True
            args.limit = 1
            run(root, args)
            score(root, args)
            summarize(root)
            args.limit = None
            run(root, args)
            score(root, args)
            summarize(root)
            audit(root)
        elif args.command == "score":
            score(root, args)
        elif args.command == "audit":
            audit(root)
        else:
            summarize(root)
    except (StudyBlocked, OSError, ValueError, KeyError) as exc:
        write_json(root / "status.json", {"stage": "blocked", "reason": str(exc),
                   "updated_at": time.time()})
        print(f"STOPPED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
