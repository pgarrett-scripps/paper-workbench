"""Subscription-only model transport with bounded calls and durable receipts."""
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
from .models import CODEX_MODELS

class StudyBlocked(RuntimeError):
    pass

APPROVED_MANUSCRIPT_TOOLS = (
    "read_blocks", "search", "calculate", "save_note", "view_page",
    "view_supplement", "check_citation", "search_literature",
)

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

def claim_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())

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
        from .billing import verify_billing
        if not billing_path.exists():
            raise StudyBlocked("Record current Codex subscription usage before execution.")
        try:
            verify_billing(read_json(billing_path))
        except ValueError as error:
            raise StudyBlocked(str(error)) from error
        return status
    if not billing_path.exists() or not read_json(billing_path).get("extra_usage_disabled"):
        raise StudyBlocked("Confirm paid extra usage is disabled in Claude settings, then record it with confirm-billing.")
    return status

def validate_protocol(protocol):
    pinned = {"claude-code": (MODEL,), "codex": CODEX_MODELS}
    if protocol.get("provider") not in pinned or protocol.get("model") not in pinned[protocol["provider"]]:
        raise StudyBlocked("Unapproved provider or model. No automatic fallback is permitted.")
    if protocol.get("held_out_runs_authorized"):
        raise StudyBlocked("This runner is limited to one development paper.")
    if protocol.get("effort") != "medium":
        raise StudyBlocked("Unapproved reasoning effort. This runner is pinned to medium.")
    for key in ("max_calls_per_condition", "observed_token_stop", "call_timeout_seconds"):
        value = protocol.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise StudyBlocked(f"Protocol field {key} must be a positive integer.")

def source_manifest(path):
    return {str(p.relative_to(path)): digest(p.read_bytes()) for p in sorted(Path(path).rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}

def usage_tokens(envelope):
    usage = envelope.get("usage") or {}
    keys = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    if not any(key in usage for key in keys):
        return None
    return sum(int(usage.get(k) or 0) for k in keys)

def usage_row(record):
    return {k: v for k, v in record.items()
            if k not in {"value", "envelope", "stdout", "stderr", "events", "command"}}

def account_once(path, record):
    identity = record.get("request_sha256")
    if identity and any(row.get("request_sha256") == identity for row in jsonl(path)):
        return
    append_json(path, usage_row(record))

def reconcile_receipts(out):
    calls = Path(out) / "calls"
    if not calls.exists():
        return
    for receipt in calls.glob("*.json"):
        if not re.fullmatch(r"[0-9a-f]{64}\.json", receipt.name):
            continue
        account_once(Path(out) / "usage.jsonl", read_json(receipt))

def tool_identity(work, tools):
    if not tools:
        return None
    config_path = Path(work) / "tool-config.json"
    if not config_path.exists():
        raise StudyBlocked("Bounded manuscript tools require tool-config.json before inference.")
    config = read_json(config_path)
    source = Path(config.get("paper", "")) / "manifest.json"
    return {
        "approved_tools": tool_profile(config)[1],
        "config": config,
        "source_manifest_sha256": digest(source.read_bytes()) if source.is_file() else None,
    }

def tool_profile(config):
    profile = config.get('tool_profile', 'legacy')
    if profile == 'legacy':
        return 'manuscript_tools.py', APPROVED_MANUSCRIPT_TOOLS
    if profile == 'domains-v1':
        return 'manuscript_tools.py', (*APPROVED_MANUSCRIPT_TOOLS, 'lookup_source', 'inspect_results', 'record_comparison', 'resolve_identifier', 'historical_registration')
    if profile == 'debate-v2':
        from .debate_evidence import TOOLS
        return 'debate_tools.py', TOOLS
    raise StudyBlocked('Unknown manuscript tool profile')

def request_identity(protocol, prompt, schema, tools, images, work):
    return digest({
        "prompt": prompt,
        "schema": schema,
        "tools": tool_identity(work, tools),
        "protocol": protocol,
        "images": [{"path": str(path), "sha256": digest(path.read_bytes())} for path in images],
    })

def observed_codex_tokens(events):
    completed = [event for event in events if event.get("type") == "turn.completed"]
    keys = ("input_tokens", "output_tokens")
    if not completed or not any(key in event.get("usage", {}) for event in completed for key in keys):
        return None
    return sum(int(event.get("usage", {}).get(key) or 0)
               for event in completed for key in keys)

def recover_codex_call(out, identity, started):
    calls = Path(out) / "calls"
    events_path = calls / f"{identity}.events.jsonl"
    answer_path = calls / f"{identity}.answer.json"
    if not events_path.exists() or not answer_path.exists():
        return None
    events = []
    for line in events_path.read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    completed = [event for event in events if event.get("type") == "turn.completed"]
    failures = [event for event in events if event.get("type") in {"error", "turn.failed"}]
    tool_calls = [event.get("item", {}) for event in events
                  if event.get("type") == "item.completed"
                  and event.get("item", {}).get("type") == "mcp_tool_call"]
    if not completed or failures or any(item.get("status") != "completed" for item in tool_calls):
        return None
    try:
        value = read_json(answer_path)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(value, dict):
        return None
    record = dict(started)
    record.update(ok=True, value=value, recovered_after_interruption=True,
                  recovered_at=time.time(), events=events)
    tokens = observed_codex_tokens(events)
    record["usage_unknown"] = tokens is None
    if tokens is not None:
        record["observed_tokens"] = tokens
    return record

def unresolved_attempts(out):
    calls = Path(out) / "calls"
    if not calls.exists():
        return []
    unresolved = []
    for started in calls.glob("*.started.json"):
        identity = started.name.removesuffix(".started.json")
        if not (calls / f"{identity}.json").exists():
            unresolved.append(started)
    return unresolved

def verify_model(envelope):
    models = list((envelope.get("modelUsage") or {}).keys())
    if not models and envelope.get("model"):
        models = [envelope["model"]]
    if not models:
        raise StudyBlocked("Claude did not report a resolved model. Save output and inspect before continuing.")
    if any(model != MODEL and not model.startswith(MODEL + "-") for model in models):
        raise StudyBlocked(f"Unexpected model returned: {models}. No fallback is permitted.")
    return models

def model_call(protocol, out, prompt, schema, *, tools=False, label="call", images=None, recover_only=False):
    """A single fresh session, with a durable content-addressed response cache."""
    validate_protocol(protocol)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    images = [Path(p).resolve() for p in (images or [])]
    image_limit=protocol.get('max_source_images',3)
    image_ceiling=10 if protocol.get('image_budget_version')=='evidence-v1' else 4
    if type(image_limit) is not int or not 1<=image_limit<=image_ceiling or len(images)>image_limit:
        raise StudyBlocked("Attached source images exceed the bounded protocol allowance")
    work = out / "workspace"
    work.mkdir(exist_ok=True)
    identity = request_identity(protocol, prompt, schema, tools, images, work)
    cache = out / "calls" / f"{identity}.json"
    if cache.exists():
        saved = read_json(cache)
        account_once(out / "usage.jsonl", saved)
        if saved.get("usage_unknown") or saved.get("observed_tokens") is None:
            raise StudyBlocked("Cached output has unknown usage. Inspect its receipt before continuing.")
        if saved.get("ok"):
            return saved["value"]
        raise StudyBlocked("A prior attempt failed. Inspect it and use a new attempt directory to retry.")
    started_path = out / "calls" / f"{identity}.started.json"
    if started_path.exists():
        started = read_json(started_path)
        recovered = recover_codex_call(out, identity, started) if protocol["provider"] == "codex" else None
        if recovered:
            write_json(cache, recovered)
            account_once(out / "usage.jsonl", recovered)
            if recovered.get("usage_unknown"):
                raise StudyBlocked("Recovered output has unknown usage. Inspect its receipt before continuing.")
            return recovered["value"]
        raise StudyBlocked("An interrupted attempt has no complete recoverable receipt. Inspect it before any new model call.")
    if recover_only:
        raise StudyBlocked("No matching completed request is recoverable. Recovery never launches a model call.")
    reconcile_receipts(out)
    if unresolved_attempts(out):
        raise StudyBlocked("An earlier interrupted attempt is unresolved. Inspect it before any new model call.")
    prior = jsonl(out / "usage.jsonl")
    if any(row.get("usage_unknown") or row.get("observed_tokens") is None for row in prior):
        raise StudyBlocked("Prior model usage is unknown. No further model calls are permitted in this attempt directory.")
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
    record = {"label": label, "request_sha256": identity, "started_at": time.time(),
              "model_requested": protocol["model"], "tools": tools, "ok": False,
              "usage_unknown": True}
    write_json(out / "calls" / f"{identity}.request.json",
               {"prompt": prompt, "schema": schema, "identity": identity})
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
            entry_point, approved_tools = tool_profile(read_json(work / "tool-config.json"))
            command.extend(["-c", f"mcp_servers.manuscript.command={json.dumps(sys.executable)}",
                            "-c", "mcp_servers.manuscript.args=" + json.dumps([
                                str(HERE / entry_point), str(work / "tool-config.json")]),
                            "-c", "mcp_servers.manuscript.required=true"])
            for tool_name in approved_tools:
                command.extend(["-c", f'mcp_servers.manuscript.tools.{tool_name}.approval_mode="approve"'])
        for path in images:
            command.extend(["--image", str(path)])
        command.append("-")
    record["command"] = command
    record["provider"] = protocol["provider"]
    try:
        claim_json(started_path, record)
    except FileExistsError as exc:
        raise StudyBlocked("This request was started by another launcher. Inspect it before continuing.") from exc
    try:
        stdout_path = out / "calls" / f"{identity}.events.jsonl"
        stderr_path = out / "calls" / f"{identity}.stderr.txt"
        with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
            result = subprocess.run(command, input=prompt, stdout=stdout, stderr=stderr, text=True,
                                    cwd=work, env=clean_env(), timeout=protocol["call_timeout_seconds"])
        result.stdout = stdout_path.read_text()
        result.stderr = stderr_path.read_text()
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
            tokens = observed_codex_tokens(events)
            if tokens is not None:
                record["observed_tokens"] = tokens
                record["usage_unknown"] = False
            failures = [e for e in events if e.get("type") in {"error", "turn.failed"}]
            if result.returncode or not completed or failures:
                raise StudyBlocked(f"Codex failed. No automatic retry. {failures[-1:]}")
            tool_calls = [e.get("item", {}) for e in events if e.get("type") == "item.completed"
                          and e.get("item", {}).get("type") == "mcp_tool_call"]
            if any(item.get("status") != "completed" for item in tool_calls):
                raise StudyBlocked("A manuscript tool call failed. Do not score this incomplete run.")
            # Complete manuscript text is in every generation prompt. Tools are
            # optional targeted rereads, PDF page inspection, and calculations.
            # This CLI does not expose the resolved model in JSON events.
            record["models_observed"] = []
            record["model_verification"] = "Explicit CLI model selection. Resolved model unavailable in event stream."
            value = read_json(answer_path)
            if not isinstance(value, dict):
                raise StudyBlocked("Codex returned no structured object")
            if record["usage_unknown"]:
                raise StudyBlocked("Codex completed but did not report usage. Do not continue this run.")
            record.update(ok=True, value=value)
            return value
        try:
            envelope = json.loads(result.stdout)
        except json.JSONDecodeError:
            record["stdout"] = result.stdout
            raise StudyBlocked("Claude returned no parseable JSON. Check the saved attempt.")
        record["envelope"] = envelope
        tokens = usage_tokens(envelope)
        if tokens is not None:
            record["observed_tokens"] = tokens
            record["usage_unknown"] = False
        if result.returncode or envelope.get("is_error"):
            raise StudyBlocked(str(envelope.get("result") or "Claude failed. No automatic retry."))
        record["models_observed"] = verify_model(envelope)
        value = envelope.get("structured_output")
        if value is None:
            value = json.loads(envelope.get("result") or "null")
        if not isinstance(value, dict):
            raise StudyBlocked("Claude returned no structured object.")
        if record["usage_unknown"]:
            raise StudyBlocked("Claude completed but did not report usage. Do not continue this run.")
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
        account_once(out / "usage.jsonl", record)
    return record["value"]

HERE = Path(__file__).resolve().parent
MODEL = "claude-opus-5"
CODEX_MODEL = "gpt-5.6-sol"
