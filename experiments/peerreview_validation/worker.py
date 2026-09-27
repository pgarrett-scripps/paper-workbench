"""Execute a frozen PRA graph through the same subscription adapter as the plugin."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from common import StudyBlocked, model_call, digest, jsonl, read_json, require_subscription, verify_study, write_json
from prompts import CONCERNS_SCHEMA, EXTRACT


def main():
    root, paper_id, condition = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    protocol, manifest = verify_study(root)
    require_subscription(root)
    sys.path.insert(0, str(root / "source"))
    from peerreviewagents.agents.editor import editor_in_chief
    from peerreviewagents.default_config import DEFAULT_CONFIG
    from peerreviewagents.graph.review_graph import PeerReviewGraph, _merge_partial
    from peerreviewagents.observability import current_node
    from peerreviewagents.runtime import subscriptions

    item = next(p for p in manifest["papers"] if p["paper_id"] == paper_id)
    out = root / "generation" / paper_id / condition
    out.mkdir(parents=True, exist_ok=True)

    def subscription_runner(provider, prompt, schema, model, effort, timeout):
        if provider != protocol["provider"] or model != protocol["model"]:
            raise StudyBlocked("PRA attempted an unapproved provider or model")
        value = model_call(protocol, out, prompt, schema, label=current_node() or "PRA")
        # The complete CLI envelopes and usage are recorded by model_call.
        # Avoid counting cached response replay as new inference in PRA events.
        return subscriptions.CLIResponse(value=value)

    subscriptions.run_subscription_cli = subscription_runner
    config = copy.deepcopy(DEFAULT_CONFIG)
    config.update({
        "provider": protocol["provider"], "reasoning_model": protocol["model"],
        "fast_model": protocol["model"], "single_model": True,
        "models": {tag: {"provider": protocol["provider"], "model": protocol["model"],
                         "effort": protocol["effort"]}
                   for tag in ("reviewer", "audit", "debate", "synthesis")},
        "agent_models": {}, "research_enabled": False,
        "enable_journal_recommender": False, "desk_screen_mode": "off",
        "desk_screen": False, "max_debate_rounds": protocol["debate_rounds"],
        "enable_debate": condition == "pra_full", "markdown_attempts": 1,
        "target_journal": protocol["journal"], "article_type": protocol["article_type"],
        "output_dir": str(out), "checkpoint_dir": str(out / "checkpoints"),
        "request_timeout_s": protocol["call_timeout_seconds"],
        "panel_quorum_fraction": 1.0, "revision_of": None,
    })
    graph = PeerReviewGraph(config)
    if condition == "pra_full":
        state = dict(graph.initial_state(str(root / item["manuscript"])))
        write_json(out / "initial_state.json", state)
        for chunk in graph.graph.stream(state, {"recursion_limit": 100, "max_concurrency": 1}):
            for name, partial in chunk.items():
                _merge_partial(state, partial)
                write_json(out / "state.json", state)
                if name == "panel_gate":
                    if not state.get("panel_complete") or state.get("panel_degraded"):
                        raise StudyBlocked("PRA did not produce a complete panel")
                    write_json(out / "panel_state.json", state)
                    write_json(out / "panel_usage.json", jsonl(out / "usage.jsonl"))
                print(json.dumps({"paper_id": paper_id, "condition": condition, "stage": name}), flush=True)
        if not state.get("panel_complete") or state.get("errors"):
            raise StudyBlocked("PRA reported errors. Saved output is not a successful run.")
    elif condition == "pra_no_debate":
        panel_path = root / "generation" / paper_id / "pra_full" / "panel_state.json"
        if not panel_path.exists():
            raise StudyBlocked("Run the full condition through its panel stage first")
        state = read_json(panel_path)
        if state.get("debate") or state.get("decision_letter") or state.get("debate_synthesis"):
            raise StudyBlocked("Panel snapshot contains downstream information")
        write_json(out / "shared_panel.json", {"sha256": digest(panel_path.read_bytes()),
                   "source": str(panel_path), "reused_reports": True,
                   "accounting": "Include original panel inference when estimating standalone cost"})
        state["config"] = graph.config
        partial = editor_in_chief.node(state)
        _merge_partial(state, partial)
        write_json(out / "state.json", state)
        if state.get("errors"):
            raise StudyBlocked("No-debate editor reported an error")
    else:
        raise StudyBlocked("Unsupported PRA condition")
    raw = state.get("decision_letter") or ""
    if len(raw.strip()) < 100:
        raise StudyBlocked("PRA did not produce a substantive decision letter")
    (out / "review.md").write_text(raw)
    value = model_call(protocol, out, EXTRACT + "\nREVIEW\n" + raw,
                        CONCERNS_SCHEMA, label="extract_final_concerns")
    from common import validate_concerns
    concerns = validate_concerns(value, raw, maximum=protocol["max_concerns"])
    if sum(len(c["source_quote"].split()) for c in concerns) > protocol["final_word_limit"]:
        raise StudyBlocked("Extracted review exceeds the common word allowance")
    write_json(out / "result.json", {"ok": True, "condition": condition,
               "paper_id": paper_id, "concerns": concerns, "model": protocol["model"],
               "phase": "development", "scientific_version_verified": item["version_verified"]})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        sys.exit(2)
