"""Bounded blinded evaluation for the fresh ensemble comparison."""
import copy
import json
import shutil
from pathlib import Path

from experiments.pra_debate_revision.evaluation import EVALUATION, INSTRUCTIONS, audit
from experiments.pra_prospective.core import _clean
from paper_workspace.annotations import verify_workspace
from paper_workspace.ensemble import observed_usage
from paper_workspace.external_evidence import validate_references
from paper_workspace.evidence_handles import build_registry, model_catalog
from paper_workspace.judge_evidence import judge_schema, hydrate_judgment
from paper_workspace.model_runtime import model_call
from paper_workspace.reviewer import inspected_images
from paper_workspace.run_state import tracked_stage
from paper_workspace.storage import digest, read, write


PRIMARY_FIELDS = ("title", "block_id", "quote", "kind", "severity", "comment",
                  "replacement", "evidence_blocks", "counterevidence", "source_evidence")
ASSESSMENTS = ("justified_concern", "justified_clarification",
               "unsupported_allegation", "unverifiable")
STAGES = ("shared", "independent", "sequential-2", "sequential-3", "ensemble")


def exact_signature(finding):
    """Return an exact, stable signature of all scientific finding fields."""
    return json.dumps({key: finding.get(key) for key in PRIMARY_FIELDS if key in finding},
                      sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def deduplicate_with_memberships(records):
    """Deduplicate exact findings while retaining every private stage membership."""
    unique, positions = [], {}
    for record in records:
        signature = exact_signature(record["finding"])
        if signature not in positions:
            positions[signature] = len(unique)
            unique.append({"finding": copy.deepcopy(record["finding"]), "memberships": []})
        membership = {key: value for key, value in record.items() if key != "finding"}
        unique[positions[signature]]["memberships"].append(membership)
    return unique


def validate_issue_partition(groups, finding_ids):
    """Require every finding ID exactly once in a nonempty semantic issue group."""
    if not isinstance(groups, list) or not groups:
        raise ValueError("Issue groups are required")
    seen, issues = [], set()
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("issue_id"), str):
            raise ValueError("Issue group needs an ID")
        if group["issue_id"] in issues or not isinstance(group.get("reason"), str) or not group["reason"].strip():
            raise ValueError("Issue groups need unique IDs and reasons")
        members = group.get("members")
        if not isinstance(members, list) or not members or any(not isinstance(item, str) for item in members):
            raise ValueError("Issue group needs finding IDs")
        seen.extend(members)
        issues.add(group["issue_id"])
    if set(seen) != set(finding_ids) or len(seen) != len(set(seen)):
        raise ValueError("Issue groups must partition finding IDs exactly once")


def validate_criticized_excerpt(rating, finding):
    """Reject unsupported-allegation excerpts that misstate the reviewed comment."""
    excerpt = rating.get("criticized_excerpt", "")
    if not isinstance(excerpt, str):
        raise ValueError("Criticized excerpt must be text")
    if rating.get("assessment") != "unsupported_allegation":
        if excerpt:
            raise ValueError("Only unsupported allegations may include a criticized excerpt")
        return
    if not excerpt or excerpt not in finding.get("comment", ""):
        raise ValueError("Criticized excerpt must be an exact finding-comment substring")


def _schema():
    value = copy.deepcopy(EVALUATION)
    value["properties"]["conditions"]["items"]["properties"]["label"]["enum"] = ["A", "B", "C"]
    value["properties"]["conditions"].update(minItems=3, maxItems=3)
    rating = value["properties"]["conditions"]["items"]["properties"]["ratings"]["items"]
    rating["properties"]["criticized_excerpt"] = {"type": "string"}
    rating["required"] = list(dict.fromkeys(rating["required"] + ["criticized_excerpt"]))
    value["properties"]["issue_groups"] = {"type": "array", "minItems": 1, "items": {
        "type": "object", "additionalProperties": False,
        "properties": {"issue_id": {"type": "string"},
                       "members": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                       "reason": {"type": "string", "minLength": 1}},
        "required": ["issue_id", "members", "reason"]}}
    value["properties"]["preferred_label"] = {"type": "string", "enum": ["A", "B", "tie", "uncertain"]}
    value["required"] = list(dict.fromkeys(value["required"] + ["issue_groups", "preferred_label", "preference_reason"]))
    return value


def _findings(package, key="findings", limit=10):
    value = package.get(key, [])
    if not isinstance(value, list) or len(value) > limit or any(not isinstance(item, dict) for item in value):
        raise ValueError("Invalid bounded finding inventory")
    return value


def _secondary_ensemble(package):
    inventory = package.get("candidate_inventory", {})
    secondary = inventory.get("secondary_candidates", []) if isinstance(inventory, dict) else []
    if not isinstance(secondary, list) or len(secondary) > 25:
        raise ValueError("Invalid ensemble secondary inventory")
    if 'adjudicated_secondary' in package:
        records = package['adjudicated_secondary']
        if not isinstance(records, list) or any(not isinstance(row, dict) or
                not isinstance(row.get('issue_id'), str) or not isinstance(row.get('finding'), dict) for row in records):
            raise ValueError('Invalid adjudicated secondary records')
        ids = [row['issue_id'] for row in records]
        if len(ids) != len(set(ids)) or set(ids) != {row['issue_id'] for row in secondary}:
            raise ValueError('Adjudicated secondary records differ from the retained inventory')
        # The original broad wording remains in the discovery bank, not the final secondary report.
        by_id = {row['issue_id']: row['finding'] for row in records}
        return [by_id[row['issue_id']] for row in secondary], []
    sources = package.get("source_findings", [])
    by_id = {}
    for source in sources if isinstance(sources, list) else []:
        if not isinstance(source, dict) or not isinstance(source.get("source_finding_id"), str):
            raise ValueError("Ensemble source finding lacks an ID")
        if source["source_finding_id"] in by_id:
            raise ValueError("Duplicate ensemble source finding ID")
        by_id[source["source_finding_id"]] = source.get("finding")
    result, skipped = [], []
    for item in secondary:
        if not isinstance(item, dict) or not isinstance(item.get("issue_id"), str):
            raise ValueError("Invalid ensemble secondary candidate")
        finding = by_id.get(item["issue_id"])
        if not isinstance(finding, dict):
            skipped.append({"issue_id": item["issue_id"], "reason": "No anchored source finding was available."})
            continue
        if not isinstance(finding.get("block_id"), str) or not isinstance(finding.get("quote"), str) or not finding["quote"]:
            skipped.append({"issue_id": item["issue_id"], "reason": "Source finding has no manuscript anchor."})
            continue
        result.append(finding)
    return result, skipped


def _validate_stage(package, raw_hashes):
    cards = package.get("source_cards", [])
    if not isinstance(cards, list):
        raise ValueError("Invalid source cards")
    validate_references({"findings": _findings(package)}, cards)
    if "secondary_findings" in package:
        validate_references({"findings": _findings(package, "secondary_findings")}, cards)
    if "source_findings" in package:
        originals = [item.get("finding", item) for item in package["source_findings"]
                     if isinstance(item, dict)]
        if len(originals) != len(package["source_findings"]):
            raise ValueError("Invalid source finding inventory")
        validate_references({"findings": originals}, cards)
    adjudicated = [row['finding'] for row in package.get('adjudicated_secondary', [])]
    validate_references({'findings': adjudicated}, cards)
    cited = {reference.get("evidence_id") for finding in _findings(package)
             for reference in finding.get("source_evidence", [])}
    cited.update(reference.get('evidence_id') for finding in adjudicated for reference in finding.get('source_evidence', []))
    for key in ("secondary_findings",):
        cited.update(reference.get("evidence_id") for finding in package.get(key, [])
                     if isinstance(finding, dict) for reference in finding.get("source_evidence", []))
    for source in package.get("source_findings", []):
        finding = source.get("finding", {}) if isinstance(source, dict) else {}
        cited.update(reference.get("evidence_id") for reference in finding.get("source_evidence", []))
    for card in cards:
        if card.get("evidence_id") in cited and card.get("raw_sha256") not in raw_hashes:
            raise ValueError("Cited source card is not backed by a raw cache file")
    return cards


def _records(root):
    packages = {stage: read(root / stage / "editor-package.json") for stage in STAGES}
    for stage in ("shared", "independent", "sequential-2"):
        _findings(packages[stage], limit=10)
    _findings(packages["sequential-3"], limit=5)
    _findings(packages["sequential-3"], "secondary_findings", limit=10)
    _findings(packages["ensemble"], limit=5)
    raw_hashes = {digest(path.read_bytes()) for path in root.rglob("*.raw")}
    cards = {}
    for stage, package in packages.items():
        for card in _validate_stage(package, raw_hashes):
            key = card.get("evidence_id")
            if key:
                if key in cards and cards[key] != card:
                    raise ValueError("Conflicting source cards")
                cards[key] = card
    records = []
    for stage in ("shared", "independent", "sequential-2"):
        records.extend({"finding": finding, "stage": stage, "role": "discovery"}
                       for finding in _findings(packages[stage]))
    records.extend({"finding": finding, "stage": "sequential-3", "role": "secondary"}
                   for finding in _findings(packages["sequential-3"], "secondary_findings"))
    ensemble_secondary, skipped = _secondary_ensemble(packages["ensemble"])
    records.extend({"finding": finding, "stage": "ensemble", "role": "secondary"}
                   for finding in ensemble_secondary)
    return packages, deduplicate_with_memberships(records), cards, skipped


def _anonymous(packages, pool, mapping):
    if set(mapping) != {"A", "B"} or set(mapping.values()) != {"ensemble", "sequential"}:
        raise ValueError("Mapping must assign ensemble and sequential to A and B")
    primary = {"ensemble": _findings(packages["ensemble"], limit=5),
               "sequential": _findings(packages["sequential-3"], limit=5)}
    anonymous, primary_sigs = {}, set()
    for label in ("A", "B"):
        rows = primary[mapping[label]]
        anonymous[label] = [{"finding_id": label + str(index), **_clean({key: item[key] for key in PRIMARY_FIELDS if key in item})}
                            for index, item in enumerate(rows, 1)]
        primary_sigs.update(exact_signature(item) for item in rows)
    candidates = [row for row in pool if exact_signature(row["finding"]) not in primary_sigs]
    anonymous["C"] = [{"finding_id": "C" + str(index), **_clean({key: item["finding"][key] for key in PRIMARY_FIELDS if key in item["finding"]})}
                      for index, item in enumerate(candidates, 1)]
    return anonymous


def _images(root, base, paper, target):
    available = [(Path(item["path"]), item.get("label", "Shared manuscript image")) for item in read(base / "images.json")]
    for stage in STAGES:
        investigation = root / stage / "investigations"
        if investigation.is_dir():
            for child in sorted(item for item in investigation.iterdir() if item.is_dir()):
                available.extend(inspected_images(paper, base / "workspace", child, 10))
    images, paths, hashes = [], [], set()
    for path, label in available:
        if not path.is_file():
            raise ValueError("Missing source image")
        sha = digest(path.read_bytes())
        if sha in hashes:
            continue
        if len(images) == 10:
            raise ValueError("Image union exceeds ten images")
        destination = target / "evidence" / ("image-" + str(len(images) + 1) + path.suffix.lower())
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        images.append({"id": "image-" + str(len(images) + 1), "label": label, "sha256": sha})
        paths.append(destination)
        hashes.add(sha)
    return images, paths


def _audit(value, anonymous, paper, images):
    if {row.get("label") for row in value.get("conditions", [])} != {"A", "B", "C"} or len(value["conditions"]) != 3:
        raise ValueError("Invalid condition accounting")
    valid, invalid = [], []
    for row in value["conditions"]:
        label = row["label"]
        if row.get("matches"):
            raise ValueError("Candidate comparison cannot include matches")
        findings = {item["finding_id"]: item for item in anonymous[label]}
        ratings = row.get("ratings", [])
        if len(ratings) != len(findings) or {item.get("finding_id") for item in ratings} != set(findings):
            raise ValueError("Invalid finding accounting")
        for rating in ratings:
            try:
                one = {key: ([findings[rating["finding_id"]]] if key == label else [])
                       for key in ("A", "B", "C")}
                checked = audit({"conditions": [{"label": key, "ratings": [rating] if key == label else [], "matches": []}
                                                 for key in ("A", "B", "C")]}, one, paper, images)
                validate_criticized_excerpt(rating, findings[rating["finding_id"]])
                if checked["invalid_ratings"]:
                    raise ValueError(checked["invalid_ratings"][0]["error"])
                valid.append((label, rating["finding_id"]))
            except ValueError as error:
                invalid.append({"label": label, "finding_id": rating.get("finding_id"), "error": str(error)})
    validate_issue_partition(value["issue_groups"], [item["finding_id"] for rows in anonymous.values() for item in rows])
    if value.get("preferred_label") not in ("A", "B", "tie", "uncertain"):
        raise ValueError("Invalid primary preference")
    return {"valid_rating_ids": valid, "invalid_ratings": invalid}


def _stage_groups(value, anonymous, pool, mapping, valid):
    """Compute stage retention metrics after judging, without exposing stages to the judge."""
    id_signature = {item["finding_id"]: exact_signature(item)
                    for rows in anonymous.values() for item in rows}
    memberships = {}
    for row in pool:
        memberships.setdefault(exact_signature(row["finding"]), []).extend(row["memberships"])
    for label, condition in mapping.items():
        stage = "ensemble" if condition == "ensemble" else "sequential-3"
        for item in anonymous[label]:
            memberships.setdefault(exact_signature(item), []).append({"stage": stage, "role": "primary"})
    rating_by_id = {rating["finding_id"]: rating for row in value["conditions"] for rating in row["ratings"]
                    if (row["label"], rating["finding_id"]) in valid}
    grouped, private_memberships = [], {}
    for group in value["issue_groups"]:
        ids = group["members"]
        by_stage = {}
        for finding_id in ids:
            rating = rating_by_id.get(finding_id, {})
            own_supported = rating.get("assessment") in ASSESSMENTS[:2]
            entries = memberships.get(id_signature[finding_id], [])
            private_memberships[finding_id] = entries
            for entry in entries:
                stage = entry.get("stage")
                state = by_stage.setdefault(stage, {"present": False, "supported": False,
                                                     "secondary_supported": False, "roles": set()})
                state["present"] = True
                state["supported"] = state["supported"] or own_supported
                if entry.get("role") == "secondary":
                    state["secondary_supported"] = state["secondary_supported"] or own_supported
                state["roles"].add(entry.get("role"))
        grouped.append({"issue_id": group["issue_id"], "by_stage": by_stage})
    per_stage = {stage: sorted(item["issue_id"] for item in grouped
                                if item["by_stage"].get(stage, {}).get("supported")) for stage in STAGES}
    independent_only = [item["issue_id"] for item in grouped
                        if item["by_stage"].get("independent", {}).get("supported")
                        and not item["by_stage"].get("shared", {}).get("present")]
    def losses(pool_stages, final_stage):
        return sorted(item["issue_id"] for item in grouped
                      if any(item["by_stage"].get(stage, {}).get("supported") for stage in pool_stages)
                      and not item["by_stage"].get(final_stage, {}).get("present"))
    secondary_groups = {"ensemble": sorted(item["issue_id"] for item in grouped
                                             if item["by_stage"].get("ensemble", {}).get("secondary_supported")),
                        "sequential": sorted(item["issue_id"] for item in grouped
                                              if item["by_stage"].get("sequential-3", {}).get("secondary_supported"))}
    return (per_stage, sorted(independent_only),
            {"ensemble": losses(("shared", "independent"), "ensemble"),
             "sequential": losses(("shared", "sequential-2"), "sequential-3")}, private_memberships,
            secondary_groups)


def evaluate(root, base, protocol, budget, mapping, *, resume=False):
    root = Path(root)
    if (root / 'evaluation').exists() and not resume:
        raise ValueError('Evaluation already prepared or attempted')
    with tracked_stage(root / 'evaluation-state.json', 'blind-assessment',
                       protocol.get('call_timeout_seconds', 900)+180):
        return _evaluate(root, base, protocol, budget, mapping, resume=resume)


def _evaluate(root, base, protocol, budget, mapping, *, resume=False):
    """Run one bounded Terra judge after all review states have been generated."""
    root, base = Path(root), Path(base)
    if protocol.get("provider") != "codex" or protocol.get("model") != "gpt-5.6-terra":
        raise ValueError("Evaluation is pinned to Codex Terra")
    target = root / "evaluation"
    if target.exists() and not resume:
        raise ValueError("Evaluation already prepared or attempted")
    packages, pool, cards, skipped_secondary = _records(root)
    anonymous = _anonymous(packages, pool, mapping)
    paper = verify_workspace(base / "workspace")
    if not resume:
        budget(1)
    images, paths = _images(root, base, paper, target)
    registry = build_registry(paper, list(cards.values()))
    schema = judge_schema(_schema(), registry, images)
    prompt = INSTRUCTIONS.replace("three anonymous scientific reviews", "two anonymous primary reviews and one candidate bank")
    prompt += "\nA and B are the only main reports. Choose preferred_label using only A and B. C is a separate candidate bank for assessing supported additions and losses, never a contender. Group every finding ID exactly once by the same scientific question and resolution. Do not group by topic alone. Do not infer stages or workflows."
    prompt += "\nFor unsupported_allegation, criticized_excerpt must be an exact substring of that finding's comment. Leave it empty for every other assessment."
    prompt += "\nREFERENCE FORMAT OVERRIDE: Return evidence_handle for text references. Return image_id and visual_observation for images."
    prompt += "\nANONYMOUS MATERIAL:\n" + json.dumps(anonymous, ensure_ascii=False)
    prompt += "\nSOURCE SPANS:\n" + json.dumps(model_catalog(registry), ensure_ascii=False)
    prompt += "\nSOURCE IMAGES:\n" + json.dumps(images, ensure_ascii=False)
    inputs = {"anonymous": anonymous, "images": images, "source_cards": list(cards.values()),
                                           "schema": schema, "prompt_sha256": digest(prompt),
                                           "registry_sha256": registry.manifest_sha256}
    if resume and (read(target / 'judge-inputs.json') != inputs or read(root / 'private/condition-map.json') != mapping):
        raise ValueError('Recovery inputs differ from the original assessment')
    write(root / "private" / "condition-map.json", mapping)
    write(target / "judge-inputs.json", inputs)
    raw = model_call(protocol, target / "execution", prompt, schema, tools=False,
                     label="ensemble-fresh-judge", images=paths, recover_only=resume)
    write(target / "raw-model.json", raw)
    hydrated = hydrate_judgment(raw, registry, images)
    write(target / "reference-audit.json", hydrated)
    value = hydrated["response"]
    write(target / "raw.json", value)
    judge_paper = {**paper, "blocks": paper["blocks"] + [{"id": card["evidence_id"], "text": card["evidence_text"]}
                   for card in cards.values() if card.get("eligible")]}
    checked = _audit(value, anonymous, judge_paper, images)
    write(target / "audit.json", checked)
    valid = set(checked["valid_rating_ids"])
    group_by_id = {member: group["issue_id"] for group in value["issue_groups"] for member in group["members"]}
    metrics = {}
    for label in ("A", "B", "C"):
        ratings = [item for row in value["conditions"] if row["label"] == label for item in row["ratings"]
                   if (label, item["finding_id"]) in valid]
        metrics[label] = {"total": len(anonymous[label]), "unscored": len(anonymous[label]) - len(ratings),
                          "assessments": {name: sum(item["assessment"] == name for item in ratings) for name in ASSESSMENTS},
                          "supported_issue_groups": sorted({group_by_id[item["finding_id"]] for item in ratings
                                                            if item["assessment"] in ASSESSMENTS[:2]})}
    supported = {label: set(data["supported_issue_groups"]) for label, data in metrics.items()}
    stage_supported, independent_only, absent, private_memberships, secondary_groups = _stage_groups(
        value, anonymous, pool, mapping, valid)
    sequential_secondary = _findings(packages["sequential-3"], "secondary_findings", limit=10)
    ensemble_secondary, ignored = _secondary_ensemble(packages["ensemble"])
    if ignored != skipped_secondary:
        raise ValueError("Ensemble secondary inventory changed during evaluation")
    result = {"preferred": value["preferred_label"], "preference_reason": value["preference_reason"],
              "preference_provisional": bool(checked["invalid_ratings"]), "metrics": metrics,
              "issue_groups": value["issue_groups"],
              "per_stage_distinct_supported_issue_groups": stage_supported,
              "groups_independent_not_shared": independent_only,
              "pool_supported_absent_final_secondary": absent,
              "secondary_metrics": {
                  "ensemble": {"total": len(ensemble_secondary) + len(skipped_secondary),
                               "unscored": len(skipped_secondary), "supported_issue_groups": secondary_groups["ensemble"],
                               "unscored_candidates": skipped_secondary},
                  "sequential": {"total": len(sequential_secondary), "unscored": 0,
                                 "supported_issue_groups": secondary_groups["sequential"],
                                 "unscored_candidates": []}},
              "usage": observed_usage(root),
              "limitations": ["One blinded Terra judge is an automated assessment, not independent expert validation."]}
    # C memberships remain private. These set differences are computed from blinded IDs only.
    result["unique_supported_additions"] = {"A": sorted(supported["A"] - supported["B"]),
                                             "B": sorted(supported["B"] - supported["A"])}
    write(root / "private" / "source-stage-memberships.json", private_memberships)
    write(target / "results.json", result)
    write(root / "results.json", result)
    return result
