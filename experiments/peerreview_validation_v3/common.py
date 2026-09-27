"""Shared persistence, subscription checks, and isolated model invocation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[1] / "runs" / "peerreview-validation-codex-v3"
MODEL = "claude-opus-5"
CODEX_MODEL = "gpt-5.6-sol"


class StudyBlocked(RuntimeError):
    pass


def digest(value):
    data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(f".tmp-{os.getpid()}")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def jsonl(path):
    path = Path(path)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def append_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def clean_env():
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(("ANTHROPIC_", "PEERREVIEW_", "OPENAI_")) or key in {
            "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
            "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT",
            "CODEX_API_KEY", "CODEX_ACCESS_TOKEN",
        }:
            del env[key]
    env["CLAUDE_CODE_DISABLE_FAST_MODE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def auth_status(provider="claude-code"):
    if provider == "codex":
        result = subprocess.run([shutil.which("codex") or "codex", "login", "status"],
                                capture_output=True, text=True, env=clean_env(), timeout=30)
        logged_in = result.returncode == 0 and "Logged in using ChatGPT" in result.stdout + result.stderr
        return {"loggedIn": logged_in, "authMethod": "chatgpt" if logged_in else "unverified"}
    executable = shutil.which("claude")
    if not executable:
        return {"loggedIn": False, "error": "Claude Code CLI is missing"}
    result = subprocess.run([executable, "auth", "status"], capture_output=True,
                            text=True, env=clean_env(), timeout=30)
    try:
        status = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"loggedIn": False, "error": "Cannot read Claude authentication status"}
    return {key: status.get(key) for key in ("loggedIn", "authMethod", "apiProvider", "subscriptionType")}


def require_subscription(root):
    protocol_path = Path(root) / "protocol.json"
    provider = read_json(protocol_path)["provider"] if protocol_path.exists() else "claude-code"
    status = auth_status(provider)
    if not status.get("loggedIn"):
        raise StudyBlocked(f"This process cannot access a {provider} subscription login.")
    accepted = {"chatgpt"} if provider == "codex" else {"claude.ai", "oauth"}
    if status.get("authMethod") not in accepted:
        raise StudyBlocked("Subscription authentication was not verified. Refusing API-backed execution.")
    billing_path = Path(root) / "billing_confirmation.json"
    if provider == "codex":
        if not billing_path.exists() or not read_json(billing_path).get("no_paid_credits_verified"):
            raise StudyBlocked("Record the verified Codex account credit status before execution.")
        return status
    if not billing_path.exists() or not read_json(billing_path).get("extra_usage_disabled"):
        raise StudyBlocked("Confirm paid extra usage is disabled in Claude settings, then record it with confirm-billing.")
    return status


def validate_protocol(protocol):
    pinned = {"claude-code": MODEL, "codex": CODEX_MODEL}
    if protocol.get("provider") not in pinned or protocol.get("model") != pinned[protocol["provider"]]:
        raise StudyBlocked("Unapproved provider or model. No automatic fallback is permitted.")
    if protocol.get("live_retrieval") or protocol.get("held_out_runs_authorized"):
        raise StudyBlocked("This runner is limited to the offline development pilot.")


def source_manifest(path):
    return {str(p.relative_to(path)): digest(p.read_bytes()) for p in sorted(Path(path).rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def verify_study(root):
    root = Path(root)
    manifest = read_json(root / "manifest.json")
    protocol = read_json(root / "protocol.json")
    validate_protocol(protocol)
    if digest(protocol) != manifest["protocol_sha256"]:
        raise StudyBlocked("Frozen protocol changed. Prepare a new study directory.")
    if source_manifest(root / "source" / "peerreviewagents") != manifest["pra_files"]:
        raise StudyBlocked("Frozen PeerReviewAgents source changed.")
    if source_manifest(HERE) != manifest["runner_files"]:
        raise StudyBlocked("Runner or prompts changed. Prepare a new study directory before model execution.")
    for item in manifest["papers"]:
        for key, hash_key in [("manuscript", "manuscript_sha256"), ("reviews", "reviews_sha256")]:
            if digest((root / item[key]).read_bytes()) != item[hash_key]:
                raise StudyBlocked(f"Frozen {key} changed for {item['paper_id']}")
    return protocol, manifest


def usage_tokens(envelope):
    usage = envelope.get("usage") or {}
    return sum(int(usage.get(k) or 0) for k in (
        "input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))


def verify_model(envelope):
    models = list((envelope.get("modelUsage") or {}).keys())
    if not models and envelope.get("model"):
        models = [envelope["model"]]
    if not models:
        raise StudyBlocked("Claude did not report a resolved model. Save output and inspect before continuing.")
    if any(model != MODEL and not model.startswith(MODEL + "-") for model in models):
        raise StudyBlocked(f"Unexpected model returned: {models}. No fallback is permitted.")
    return models


def model_call(protocol, out, prompt, schema, *, tools=False, label="call"):
    """A single fresh session, with a durable content-addressed response cache."""
    validate_protocol(protocol)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    identity = digest({"prompt": prompt, "schema": schema, "tools": tools,
                       "protocol": protocol})
    cache = out / "calls" / f"{identity}.json"
    if cache.exists():
        saved = read_json(cache)
        if saved.get("ok"):
            return saved["value"]
        raise StudyBlocked("A prior attempt failed. Inspect it and use a new attempt directory to retry.")
    prior = jsonl(out / "usage.jsonl")
    if len(prior) >= protocol["max_calls_per_condition"]:
        raise StudyBlocked("Pilot call limit reached. Outputs have been saved.")
    if sum(row.get("observed_tokens", 0) for row in prior) >= protocol["observed_token_stop"]:
        raise StudyBlocked("Pilot observed-token stop reached. Outputs have been saved.")
    command = [shutil.which("claude") or "claude", "-p", "--model", protocol["model"],
               "--effort", protocol["effort"], "--output-format", "json",
               "--json-schema", json.dumps(schema), "--no-session-persistence",
               "--safe-mode", "--restricted", "--strict-mcp-config",
               "--disable-slash-commands", "--permission-mode", "dontAsk",
               "--tools", "Read,Grep,Glob" if tools else ""]
    if tools:
        command.extend(["--allowedTools", "Read,Grep,Glob"])
    work = out / "workspace"
    work.mkdir(exist_ok=True)
    record = {"label": label, "request_sha256": identity, "started_at": time.time(),
              "model_requested": protocol["model"], "tools": tools, "ok": False}
    write_json(out / "calls" / f"{identity}.request.json", {"prompt": prompt, "schema": schema})
    if protocol["provider"] == "codex":
        schema_path = out / "calls" / f"{identity}.schema.json"
        answer_path = out / "calls" / f"{identity}.answer.json"
        write_json(schema_path, schema)
        command = [shutil.which("codex") or "codex", "exec", "--ephemeral",
                   "--sandbox", "read-only", "--ignore-user-config", "--ignore-rules",
                   "--skip-git-repo-check", "--color", "never", "--json",
                   "--output-schema", str(schema_path), "--output-last-message", str(answer_path),
                   "--cd", str(work), "--model", protocol["model"],
                   "-c", f'model_reasoning_effort="{protocol["effort"]}"',
                   "-c", 'forced_login_method="chatgpt"', "-c", 'web_search="disabled"']
        for feature in ("shell_tool", "apps", "plugins", "browser_use", "computer_use", "multi_agent"):
            command.extend(["-c", f"features.{feature}=false"])
        if tools:
            command.extend(["-c", f"mcp_servers.manuscript.command={json.dumps(sys.executable)}",
                            "-c", "mcp_servers.manuscript.args=" + json.dumps([
                                str(HERE / "manuscript_tools.py"), str(work / "manuscript.txt")]),
                            "-c", "mcp_servers.manuscript.required=true"])
        command.append("-")
    record["command"] = command
    record["provider"] = protocol["provider"]
    try:
        result = subprocess.run(command, input=prompt, capture_output=True, text=True,
                                cwd=work, env=clean_env(), timeout=protocol["call_timeout_seconds"])
        record["returncode"] = result.returncode
        record["stderr"] = result.stderr
        if protocol["provider"] == "codex":
            events = []
            record["stdout"] = result.stdout
            for line in result.stdout.splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            record["events"] = events
            completed = [event for event in events if event.get("type") == "turn.completed"]
            if completed:
                record["observed_tokens"] = sum(
                    int(event.get("usage", {}).get(k) or 0)
                    for event in completed for k in ("input_tokens", "output_tokens"))
            failures = [e for e in events if e.get("type") in {"error", "turn.failed"}]
            if result.returncode or not completed or failures:
                raise StudyBlocked(f"Codex failed. No automatic retry. {failures[-1:]}")
            tool_calls = [e.get("item", {}) for e in events if e.get("type") == "item.completed"
                          and e.get("item", {}).get("type") == "mcp_tool_call"]
            if any(item.get("status") != "completed" for item in tool_calls):
                raise StudyBlocked("A manuscript tool call failed. Do not score this incomplete run.")
            if tools and not any(item.get("tool") == "read_manuscript" for item in tool_calls):
                raise StudyBlocked("The single agent did not read the manuscript through its tool.")
            # This CLI does not expose the resolved model in JSON events.
            record["models_observed"] = []
            record["model_verification"] = "Explicit CLI model selection. Resolved model unavailable in event stream."
            value = read_json(answer_path)
            if not isinstance(value, dict):
                raise StudyBlocked("Codex returned no structured object")
            record.update(ok=True, value=value)
            return value
        try:
            envelope = json.loads(result.stdout)
        except json.JSONDecodeError:
            record["stdout"] = result.stdout
            raise StudyBlocked("Claude returned no parseable JSON. Check the saved attempt.")
        record["envelope"] = envelope
        record["observed_tokens"] = usage_tokens(envelope)
        if result.returncode or envelope.get("is_error"):
            raise StudyBlocked(str(envelope.get("result") or "Claude failed. No automatic retry."))
        record["models_observed"] = verify_model(envelope)
        value = envelope.get("structured_output")
        if value is None:
            value = json.loads(envelope.get("result") or "null")
        if not isinstance(value, dict):
            raise StudyBlocked("Claude returned no structured object.")
        record.update(ok=True, value=value)
    except subprocess.TimeoutExpired as exc:
        record["error"] = "Call timed out. Incurred usage is unknown."
        raise StudyBlocked(record["error"]) from exc
    except Exception as exc:
        record["error"] = str(exc)
        raise
    finally:
        record["elapsed_seconds"] = time.time() - record["started_at"]
        write_json(cache, record)
        append_json(out / "usage.jsonl", {k: v for k, v in record.items()
                                          if k not in {"value", "envelope", "stdout", "stderr", "events", "command"}})
    return record["value"]


def quote_match_mode(quote, text):
    if not quote.strip():
        return None
    if " ".join(quote.split()) in " ".join(text.split()):
        return "whitespace"
    # Match only source layout changes, never lexical substitutions.
    # A quoted hyphen may be followed by a PDF newline in the source.
    # A joined quoted word may contain a line-end hyphen in the source.
    parts = []
    for index, char in enumerate(quote.strip()):
        if char.isspace():
            if not parts or parts[-1] != r"\s+":
                parts.append(r"\s+")
            continue
        if char == "-":
            parts.append(r"-[ \t]*(?:\r?\n[ \t]*)?")
        else:
            parts.append(re.escape(char))
        if index + 1 < len(quote.strip()) and char.isalpha() and quote.strip()[index+1].isalpha():
            parts.append(r"(?:-[ \t]*\r?\n[ \t]*)?")
    if re.search("".join(parts), text):
        return "pdf_line_wrapping"
    return None


def quote_present(quote, text):
    return quote_match_mode(quote, text) is not None


def validate_concerns(value, source, *, maximum=None):
    concerns = value.get("concerns")
    if not isinstance(concerns, list) or (maximum is not None and len(concerns) > maximum):
        raise StudyBlocked("Invalid concern array")
    ids = [c.get("id") for c in concerns]
    if any(not x for x in ids) or len(set(ids)) != len(ids):
        raise StudyBlocked("Concern IDs are missing or duplicated")
    for concern in concerns:
        if not concern.get("claim") or not quote_present(concern.get("source_quote", ""), source):
            raise StudyBlocked("Concern extraction contains an unsupported source quote")
    return concerns
