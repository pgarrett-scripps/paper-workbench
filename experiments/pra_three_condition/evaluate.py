"""Blinded four-condition assessment for the fresh paper panel."""
import copy
import itertools
import json
import shutil
from pathlib import Path

from experiments.pra_debate_revision.evaluation import EVALUATION, INSTRUCTIONS, audit
from experiments.pra_prospective.core import _cards, _clean
from paper_workspace.annotations import verify_workspace
from paper_workspace.evidence_handles import build_registry, model_catalog
from paper_workspace.judge_evidence import judge_schema, hydrate_judgment
from paper_workspace.model_runtime import model_call
from paper_workspace.reviewer import inspected_images
from paper_workspace.storage import digest, read, write


LABELS = ("A", "B", "C", "D")
CONDITIONS = ("basic_one", "basic_two", "workspace", "pra")
REVIEW_PATHS = {
    "basic_one": "basic/responses/first-guarded.json",
    "basic_two": "basic/responses/second-guarded.json",
    "workspace": "workspace/editor-package.json",
    "pra": "pra/editor-package.json",
}
STATE_ROOTS = {"basic_one": "basic", "basic_two": "basic", "workspace": "workspace", "pra": "pra"}
ALLOWED = ("title", "block_id", "quote", "kind", "severity", "comment",
           "replacement", "evidence_blocks", "counterevidence", "source_evidence")


def _pairs():
    return {frozenset(pair) for pair in itertools.combinations(LABELS, 2)}


def _pair_schema():
    return {"type": "array", "minItems": 6, "maxItems": 6, "items": {
        "type": "object", "additionalProperties": False,
        "properties": {
            "label_a": {"type": "string", "enum": list(LABELS)},
            "label_b": {"type": "string", "enum": list(LABELS)},
            "preferred_label": {"type": "string", "enum": [*LABELS, "tie", "uncertain"]},
            "reason": {"type": "string", "minLength": 1},
        }, "required": ["label_a", "label_b", "preferred_label", "reason"]}}


def schema():
    """Return the four-label judge schema before source-handle specialization."""
    value = copy.deepcopy(EVALUATION)
    value["properties"]["conditions"]["items"]["properties"]["label"]["enum"] = list(LABELS)
    value["properties"]["conditions"].update(minItems=4, maxItems=4)
    value["properties"]["preferred_label"]["enum"] = [*LABELS, "tie", "uncertain"]
    value["properties"]["pairwise"] = _pair_schema()
    value["required"] = [*value["required"], "pairwise"]
    return value


def audit_four(value, anonymous, paper, images):
    """Account for four reviews and reuse the established per-rating auditor."""
    rows = value.get("conditions", [])
    if {row.get("label") for row in rows} != set(LABELS) or len(rows) != 4:
        raise ValueError("Invalid four-condition accounting")
    by_label = {row["label"]: row for row in rows}
    valid, invalid = [], []
    for label in LABELS:
        row = by_label[label]
        remapped = {**row, "label": "A"}
        checked = audit({"conditions": [remapped,
                                         {"label": "B", "ratings": [], "matches": []},
                                         {"label": "C", "ratings": [], "matches": []}]},
                        {"A": anonymous[label], "B": [], "C": []}, paper, images)
        valid.extend((label, finding_id) for finding_id in checked["valid_rating_ids"])
        invalid.extend({"label": label, **item} for item in checked["invalid_ratings"])
    _validate_pairwise(value)
    return {"valid_rating_ids": valid, "invalid_ratings": invalid,
            "limitation": "Validated references and accounting do not establish scientific correctness. Invalid ratings make preference results provisional."}


def _validate_pairwise(value):
    pairwise = value.get("pairwise")
    if not isinstance(pairwise, list) or len(pairwise) != 6:
        raise ValueError("Six pairwise preferences are required")
    seen = set()
    for row in pairwise:
        first, second, preferred = row.get("label_a"), row.get("label_b"), row.get("preferred_label")
        pair = frozenset((first, second))
        if first == second or pair not in _pairs() or pair in seen:
            raise ValueError("Pairwise preferences must cover each label pair exactly once")
        if preferred not in pair | {"tie", "uncertain"}:
            raise ValueError("Pairwise preference must name a pair member, tie, or uncertain")
        if not isinstance(row.get("reason"), str) or not row["reason"].strip():
            raise ValueError("Pairwise preference requires a reason")
        seen.add(pair)
    if seen != _pairs():
        raise ValueError("Pairwise preferences must cover each label pair exactly once")
    if value.get("preferred_label") not in {*LABELS, "tie", "uncertain"}:
        raise ValueError("Invalid overall preference")


def _cache_hashes(root, condition):
    hashes = set()
    state_root = STATE_ROOTS[condition]
    for cache in (root / state_root / "source-cache",
                  root / state_root / "initial-checkpoint" / "source-cache"):
        if cache.is_dir():
            hashes.update(digest(path.read_bytes()) for path in cache.rglob("*") if path.is_file())
    return hashes


def _anonymous_reviews(root, order):
    if sorted(order) != sorted(CONDITIONS) or len(order) != 4:
        raise ValueError("Order must be a four-condition permutation")
    reviews = {condition: read(root / REVIEW_PATHS[condition]) for condition in CONDITIONS}
    cards, anonymous, mapping = {}, {}, {}
    for label, condition in zip(LABELS, order):
        mapping[label] = condition
        cache_hashes = _cache_hashes(root, condition)
        findings = [{"finding_id": label + str(index),
                     **_clean({key: finding[key] for key in ALLOWED if key in finding})}
                    for index, finding in enumerate(reviews[condition].get("findings", []), 1)]
        anonymous[label] = findings
        cited = {source.get("evidence_id") for finding in findings
                 for source in finding.get("source_evidence", []) or []}
        for card in _cards(reviews[condition]):
            evidence_id = card.get("evidence_id")
            if evidence_id not in cited:
                continue
            if card.get("raw_sha256") not in cache_hashes:
                raise ValueError("Source card is not backed by this run's source cache")
            if evidence_id in cards and cards[evidence_id] != card:
                raise ValueError("Conflicting source cards")
            cards[evidence_id] = card
        for finding in findings:
            for source in finding.get("source_evidence", []) or []:
                card = cards.get(source.get("evidence_id"), {})
                if not source.get("quote") or source["quote"] not in card.get("evidence_text", ""):
                    raise ValueError("Invalid cited source")
    return anonymous, mapping, cards


def _images(root, base, paper, target):
    available = [(Path(item["path"]), "Shared manuscript image") for item in read(base / "images.json")]
    for condition, stages in (("workspace", ("self-revision",)),
                              ("pra", ("workspace", "debate"))):
        for stage in stages:
            investigation = root / condition / "investigations" / stage
            if investigation.is_dir():
                available += [(path, "Inspected manuscript image") for path, _ in
                              inspected_images(paper, base / "workspace", investigation, 10)]
    images, paths, hashes = [], [], set()
    for path, label in available:
        sha = digest(path.read_bytes())
        if sha in hashes:
            continue
        destination = target / "evidence" / ("image-" + str(len(images) + 1) + path.suffix.lower())
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        paths.append(destination)
        images.append({"id": "image-" + str(len(images) + 1), "label": label, "sha256": sha})
        hashes.add(sha)
    if len(images) > 10:
        raise ValueError("Image union exceeds the shared ceiling")
    return images, paths


def _decoded_pairs(pairwise, mapping):
    return [{"conditions": [mapping[row["label_a"]], mapping[row["label_b"]]],
             "preferred": mapping.get(row["preferred_label"], row["preferred_label"]),
             "reason": row["reason"]} for row in pairwise]


def evaluate(ROOT, BASE, PROTOCOL, budget, verify, usage, order):
    """Run one no-tools Terra judge for a predeclared blinded four-arm order."""
    ROOT, BASE = Path(ROOT), Path(BASE)
    if PROTOCOL.get("provider") != "codex" or PROTOCOL.get("model") != "gpt-5.6-terra":
        raise ValueError("Four-condition judging is pinned to Codex Terra")
    target = ROOT / "evaluation"
    if target.exists():
        raise ValueError("Judge already prepared or attempted")
    for condition in CONDITIONS:
        if read(ROOT / STATE_ROOTS[condition] / "progress.json").get("status") != "complete":
            raise ValueError("Judge requires validated complete reviews")
    budget(1)
    anonymous, mapping, cards = _anonymous_reviews(ROOT, order)
    paper = verify_workspace(BASE / "workspace")
    images, paths = _images(ROOT, BASE, paper, target)
    registry = build_registry(paper, list(cards.values()))
    judge = judge_schema(schema(), registry, images)
    prompt = INSTRUCTIONS.replace("three anonymous scientific reviews", "four anonymous scientific reviews")
    prompt += "\nRate every finding. Then compare every unordered pair exactly once and choose one overall preference. Pairwise preferred_label must be a label in that pair, tie, or uncertain. Do not expose stage IDs or workflow names."
    prompt += "\nREFERENCE FORMAT OVERRIDE: For text references return only evidence_handle selected from SOURCE SPANS. For image references return image_id and visual_observation."
    prompt += "\nANONYMOUS REVIEWS:\n" + json.dumps(anonymous, ensure_ascii=False)
    prompt += "\nSOURCE SPANS, manuscript order followed by external cards:\n" + json.dumps(model_catalog(registry), ensure_ascii=False)
    prompt += "\nSOURCE IMAGES, attached in order:\n" + json.dumps(images, ensure_ascii=False)
    write(ROOT / "private/condition-map.json", mapping)
    write(target / "judge-inputs.json", {"anonymous": anonymous, "source_cards": list(cards.values()),
          "images": images, "schema": judge, "prompt_sha256": digest(prompt),
          "registry_sha256": registry.manifest_sha256, "order": list(order)})
    raw = model_call(PROTOCOL, target / "execution", prompt, judge, label="four-condition-judge", images=paths)
    write(target / "raw-model.json", raw)
    hydrated = hydrate_judgment(raw, registry, images)
    write(target / "reference-audit.json", hydrated)
    value = hydrated["response"]
    write(target / "raw.json", value)
    judge_paper = {**paper, "blocks": paper["blocks"] + [{"id": card["evidence_id"], "text": card["evidence_text"]}
                  for card in cards.values() if card.get("eligible")]}
    checked = audit_four(value, anonymous, judge_paper, images)
    write(target / "audit.json", checked)
    valid = set(checked["valid_rating_ids"])
    metrics = []
    for row in value["conditions"]:
        ratings = [rating for rating in row["ratings"] if (row["label"], rating["finding_id"]) in valid]
        metrics.append({"condition": mapping[row["label"]], "total": len(row["ratings"]),
                        "unscored": len(row["ratings"]) - len(ratings),
                        "assessments": {name: sum(rating["assessment"] == name for rating in ratings)
                                        for name in ("justified_concern", "justified_clarification", "unsupported_allegation", "unverifiable")},
                        "excessive_requests": sum(rating["resolution_proportionality"] == "excessive" for rating in ratings)})
    provisional = bool(checked["invalid_ratings"])
    result = {"preferred": mapping.get(value["preferred_label"], value["preferred_label"]),
              "preference_reason": value["preference_reason"], "pairwise": _decoded_pairs(value["pairwise"], mapping),
              "metrics": metrics, "preference_provisional": provisional, "usage": usage(),
              "limitations": ["One blinded fresh-context Terra model judge, not independent expert validation.",
                              "Four development papers cannot establish superiority or domain generalization.",
                              "Any invalid finding rating makes all preference results provisional."]}
    write(target / "results.json", result)
    verify()
    print(json.dumps(result), flush=True)
