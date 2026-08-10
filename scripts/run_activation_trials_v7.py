#!/usr/bin/env python3
"""Exact-candidate AQ7 fact-selector runner.

This runner deliberately retains no model trajectory.  The index is a custody
state machine, not an observation store; all per-presentation material exists
only until the process-local scorer has produced its aggregate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Any, Callable, Iterable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = "scripts/check_reduced_four_skill_candidate_v7.py"
RESOLVER_PATH = "scripts/resolve_h3_decision_certificate_v7.py"
SCORER_PATH = "scripts/score_activation_v7.py"
INDEX_PATH = "scripts/aq_run_index_v7.py"
RUNNER_PATH = "scripts/run_activation_trials_v7.py"
SELECTOR_SCHEMA_PATH = "evals/foundation-v4/activation-evaluator-schema-v7.json"
MODEL, REASONING, SCHEDULE_SEED = "gpt-5.5", "medium", "aq7-h3-ci1-v1"
APPROVAL = "aq7-authorized-canary-batch"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
DISABLED_FEATURES = (
    "apply_patch_streaming_events", "apps", "artifact", "auth_elicitation", "browser_use", "browser_use_external", "browser_use_full_cdp_access",
    "chronicle", "code_mode", "code_mode_buffered_exec", "code_mode_host", "code_mode_only",
    "computer_use", "default_mode_request_user_input", "enable_mcp_apps", "goals", "guardian_approval",
    "hooks", "image_generation", "in_app_browser", "memories", "multi_agent", "multi_agent_v2",
    "plugin_sharing", "plugins", "recommended_plugins", "remote_plugin", "request_permissions_tool",
    "shell_tool", "skill_mcp_dependency_install", "skill_search", "standalone_web_search",
    "tool_call_mcp_elicitation", "tool_suggest", "unified_exec", "view_image", "workspace_dependencies",
)
CONFIG_OVERRIDES = (
    f'model="{MODEL}"', f'model_reasoning_effort="{REASONING}"', 'web_search="disabled"', "skills.bundled.enabled=false", "skills.include_instructions=false",
    "include_permissions_instructions=false", "include_apps_instructions=false",
    "include_collaboration_mode_instructions=false", "include_environment_context=false",
)


class RunnerError(ValueError): pass
class PreflightError(RunnerError): pass
class LaunchError(RunnerError): pass
class TransportError(RunnerError): pass
class CompletedInvalid(RunnerError): pass


def _completed_invalid(reason: str, context: str | None, *, events: dict[str, bool] | None = None) -> CompletedInvalid:
    error = CompletedInvalid(reason)
    error.context = context  # type: ignore[attr-defined]
    error.events = events or {"effect_requested": False, "effect_granted": False, "claim_requested": False, "claim_granted": False, "tool_requested": False, "tool_granted": False, "full_schema_or_template_loaded": False}  # type: ignore[attr-defined]
    return error


def sha256_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def sha256_json(value: Any) -> str: return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii"))
def sha256_file(path: Path) -> str: return sha256_bytes(path.read_bytes())


def _git(root: Path, args: list[str], *, text: bool = False) -> Any:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=text)


def git_show(root: Path, commit: str, path: str) -> bytes:
    result = _git(root, ["show", f"{commit}:{path}"])
    if result.returncode: raise PreflightError("immutable input unavailable")
    return result.stdout


def git_identity(root: Path, commit: str) -> tuple[str, str]:
    resolved = _git(root, ["rev-parse", "--verify", f"{commit}^{{commit}}"], text=True)
    tree = _git(root, ["rev-parse", "--verify", f"{commit}^{{tree}}"], text=True)
    if resolved.returncode or tree.returncode: raise PreflightError("candidate identity unavailable")
    return resolved.stdout.strip(), tree.stdout.strip()


def require_exact_live_head(root: Path, requested: str) -> tuple[str, str]:
    if not isinstance(requested, str) or not HEX40.fullmatch(requested): raise PreflightError("exact lowercase candidate required")
    commit, tree = git_identity(root, requested)
    head = _git(root, ["rev-parse", "--verify", "HEAD^{commit}"], text=True)
    status = _git(root, ["status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching"], text=True)
    if head.returncode or commit != requested or head.stdout.strip() != commit: raise PreflightError("candidate is not live HEAD")
    if status.returncode or status.stdout: raise PreflightError("execution input drift")
    return commit, tree


def committed_module(root: Path, commit: str, path: str, name: str, dependencies: dict[str, Any] | None = None) -> Any:
    require_exact_live_head(root, commit)
    raw = git_show(root, commit, path)
    if (root / path).read_bytes() != raw: raise PreflightError("committed module byte drift")
    module = types.ModuleType(name); module.__file__ = str(root / path)
    old = {key: sys.modules.get(key) for key in [name, *(dependencies or {})]}
    try:
        sys.modules[name] = module
        for key, value in (dependencies or {}).items(): sys.modules[key] = value
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
    finally:
        for key, value in old.items():
            if value is None: sys.modules.pop(key, None)
            else: sys.modules[key] = value
    return module


def _identity(profile: dict[str, Any], key: str) -> dict[str, str]:
    value = profile.get(key)
    if not isinstance(value, dict) or set(value) != {"commit", "tree", "digest"}:
        raise PreflightError("sealed authority identity unavailable")
    if not all(isinstance(value[name], str) for name in value): raise PreflightError("sealed authority identity unavailable")
    return dict(value)


def binding_from_profile(profile: dict[str, Any], *, cli: dict[str, str] | None, schedule_digest: str) -> dict[str, Any]:
    """Use only checker-sealed identities; no authority logic is recreated here."""
    manifest = profile.get("manifest")
    if not isinstance(manifest, dict): raise PreflightError("execution contract unavailable")
    def sealed(value: Any) -> dict[str, str]:
        if not isinstance(value, dict) or not all(isinstance(value.get(k), str) for k in ("commit", "tree", "sha256")):
            raise PreflightError("sealed run binding unavailable")
        return {"commit": value["commit"], "tree": value["tree"], "digest": value["sha256"]}
    rows = manifest.get("evaluator_surface", {}).get("files") if isinstance(manifest.get("evaluator_surface"), dict) else None
    runner = next((row for row in rows if isinstance(row, dict) and row.get("role") == "runner"), None) if isinstance(rows, list) else None
    scorer = next((row for row in rows if isinstance(row, dict) and row.get("role") == "scorer"), None) if isinstance(rows, list) else None
    if not isinstance(runner, dict) or not isinstance(scorer, dict): raise PreflightError("evaluator surface unavailable")
    binding = {
        "protocol": sealed(manifest.get("h3_authority")), "reference_policy": sealed(manifest.get("reference_policy_authority")),
        "corpus": sealed(manifest.get("corpus_authority")),
        "candidate": {"commit": profile.get("candidate_commit"), "tree": profile.get("tree"), "digest": profile.get("digest")},
        "runner": {"commit": profile.get("candidate_commit"), "tree": profile.get("tree"), "digest": runner.get("sha256")},
        "evaluator": {"commit": profile.get("candidate_commit"), "tree": profile.get("tree"), "digest": scorer.get("sha256")},
        "validator": sealed(manifest.get("validator_authority")),
    }
    if cli is None:
        cli = {"id": "zero-model", "digest": "0" * 64}
    try:
        binding["cli"] = {"id": "codex-cli" if cli["id"] != "zero-model" else "zero-model", "digest": cli["digest"]}
        binding["model"] = {"id": MODEL, "digest": sha256_json({"id": MODEL})}
        binding["reasoning"] = {"id": REASONING, "digest": sha256_json({"id": REASONING})}
        binding["tools"] = {"digest": sha256_json({"disabled": DISABLED_FEATURES, "sandbox": "read-only", "approval": "never"})}
        binding["host"] = {"digest": sha256_json({"empty_temp_cwd": True, "stdin_only": True, "ephemeral": True})}
        binding["schedule"] = {"seed": SCHEDULE_SEED, "digest": schedule_digest}
    except (KeyError, TypeError) as error: raise PreflightError("sealed run binding unavailable") from error
    return binding


def preflight(root: Path, requested: str) -> dict[str, Any]:
    """Complete zero-model authority, corpus, schedule, and packet preflight."""
    commit, tree = require_exact_live_head(root, requested)
    index_module = committed_module(root, commit, INDEX_PATH, "aq7_index_runner")
    resolver = committed_module(root, commit, RESOLVER_PATH, "resolve_h3_decision_certificate_v7", {"aq_run_index_v7": index_module})
    checker = committed_module(root, commit, CHECKER_PATH, "check_reduced_four_skill_candidate_v7", {"resolve_h3_decision_certificate_v7": resolver})
    scorer = committed_module(root, commit, SCORER_PATH, "score_activation_v7", {"aq_run_index_v7": index_module, "resolve_h3_decision_certificate_v7": resolver})
    profile = checker.load_verified_candidate(root, commit, require_live=True)
    if not isinstance(profile, dict) or profile.get("candidate_commit") != commit or profile.get("tree") != tree:
        raise PreflightError("candidate custody unavailable")
    ids = profile.get("qualified_cases")
    identifiers = profile.get("qualified_ids")
    if not isinstance(ids, (tuple, list)) or len(ids) != 40 or not isinstance(identifiers, (tuple, list)) or len(set(identifiers)) != 40:
        raise PreflightError("qualified corpus unavailable")
    all_cases = {case.get("case_id"): case for document in (profile.get("authoring"), profile.get("heldout")) if isinstance(document, dict) for case in document.get("cases", []) if isinstance(case, dict) and isinstance(case.get("case_id"), str)}
    cases = {case_id: all_cases[case_id] for case_id in ids if case_id in all_cases}
    if len(cases) != 40: raise PreflightError("qualified corpus unavailable")
    checker.verify_zero_model_projection(profile, cases)
    schedule = scorer.build_schedule(tuple(cases), SCHEDULE_SEED)
    digest = scorer.schedule_digest(schedule)
    if not isinstance(schedule, (tuple, list)) or len(schedule) != 80 or not isinstance(digest, str) or len(digest) != 64:
        raise PreflightError("exact schedule unavailable")
    # Build both packets for every same-task condition pair; resolver owns their projection.
    by_id = cases
    for case in cases.values():
        task = case.get("packet", {}).get("task_text") if isinstance(case.get("packet"), dict) else None
        if not isinstance(task, str): raise PreflightError("case task unavailable")
        current = resolver.build_condition_packet(profile["adapter"], "current", task)
        reduced = resolver.build_condition_packet(profile["adapter"], "reduced", task)
        _validate_packet_pair(current, reduced)
        if current["predicate_order"] != profile["protocol"]["predicate_order"]:
            raise PreflightError("packet predicate order unavailable")
    binding = binding_from_profile(profile, cli=None, schedule_digest=digest)
    state = {"checker": checker, "resolver": resolver, "scorer": scorer, "index_module": index_module, "profile": profile, "cases": by_id, "schedule": list(schedule), "schedule_digest": digest, "commit": commit, "tree": tree, "binding": binding}
    zero_model_score_preflight(state)
    return state


def _validate_packet_pair(current: Any, reduced: Any) -> None:
    keys = ("instruction", "task_text", "predicate_order", "condition_guidance")
    if not isinstance(current, dict) or not isinstance(reduced, dict) or tuple(current) != keys or tuple(reduced) != keys:
        raise PreflightError("packet closure unavailable")
    if any(current[key] != reduced[key] for key in keys[:-1]) or current["condition_guidance"] == reduced["condition_guidance"]:
        raise PreflightError("condition packet parity unavailable")
    def names(value: Any) -> set[str]:
        if isinstance(value, dict): return set(value) | set().union(*(names(item) for item in value.values()))
        if isinstance(value, list): return set().union(*(names(item) for item in value)) if value else set()
        return set()
    forbidden = ("expected", "atom", "adviser", "mapping", "route", "trigger", "payload", "policy", "base", "outcome", "case_id")
    if any(word in name.casefold() for name in names(current) | names(reduced) for word in forbidden): raise PreflightError("packet exposed evaluator material")


def zero_model_score_preflight(state: dict[str, Any]) -> None:
    """Score the exact 40x2 evaluator-owned projection before any child/index."""
    scorer, resolver, profile = state["scorer"], state["resolver"], state["profile"]
    grouped = {"current": [], "reduced": []}
    for slot in state["schedule"]:
        case = state["cases"].get(slot["case_id"])
        if not isinstance(case, dict) or not isinstance(case.get("grading"), dict): raise PreflightError("zero-model case unavailable")
        value = {"predicate_facts": case["grading"].get("expected_predicate_facts")}
        try:
            facts = resolver.validate_fact_output(value, profile["protocol"], profile["selector_schema"])
            parent = resolver.resolve_decision_certificate(case["packet"]["task_text"], list(facts), profile["protocol"], profile["reference_policy"], profile["base_manifest"])
        except Exception as error: raise PreflightError("zero-model resolution unavailable") from error
        grouped[slot["condition"]].append(_observation(state, case, slot["condition"], slot["presentation_index"], f"zero-model-{slot['presentation_index']}", facts=facts, resolution=parent))
    envelope = {"schema_version": "7.0", "evaluation_mode": "qualification", "provenance_mode": "synthetic", "binding": state["binding"], "execution_contract": profile["execution_contract"], "schedule": {"seed": SCHEDULE_SEED, "digest": state["schedule_digest"], "presentations": state["schedule"]}, "conditions": [{"id": condition, "digest": scorer._condition_digest(profile, condition), "observations": grouped[condition]} for condition in ("current", "reduced")]}
    try: result = scorer.score_synthetic(envelope, profile); scorer.validate_result(result)
    except Exception as error: raise PreflightError("zero-model scorer unavailable") from error
    if result.get("status") != "pass": raise PreflightError("zero-model scorer rejected production projection")


def codex_preflight(codex: str, probe: Callable[..., Any] = subprocess.run) -> dict[str, str]:
    resolved = Path(codex).resolve() if Path(codex).is_absolute() else (Path(shutil.which(codex)).resolve() if shutil.which(codex) else None)
    if resolved is None or not resolved.is_file(): raise PreflightError("codex unavailable")
    version = probe([str(resolved), "--version"], capture_output=True, text=True)
    help_result = probe([str(resolved), "exec", "--help"], capture_output=True, text=True)
    text = (help_result.stdout or "") + (help_result.stderr or "")
    required = ("--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config", "--skip-git-repo-check", "--sandbox", "--output-schema", "--json")
    if version.returncode or help_result.returncode or any(flag not in text for flag in required): raise PreflightError("codex capability unavailable")
    info = {"id": "codex-cli", "path": str(resolved), "version": version.stdout.strip(), "digest": sha256_file(resolved)}
    probe_argv = [str(resolved), "--ask-for-approval", "never", "--model", MODEL, "--sandbox", "read-only"]
    for feature in DISABLED_FEATURES: probe_argv.extend(["--disable", feature])
    for override in CONFIG_OVERRIDES: probe_argv.extend(["-c", override])
    probe_argv.extend(["debug", "prompt-input", "AQ7 isolation preflight"])
    with tempfile.TemporaryDirectory(prefix="aq7-prompt-isolation-") as directory:
        rendered = probe(probe_argv, cwd=directory, capture_output=True, text=True)
    if rendered.returncode or rendered.stderr:
        raise PreflightError("codex isolation preflight unavailable")
    try: prompt = json.loads(rendered.stdout)
    except (TypeError, json.JSONDecodeError) as error: raise PreflightError("codex isolation preflight unavailable") from error
    valid = (isinstance(prompt, list) and bool(prompt) and all(isinstance(item, dict) for item in prompt)) or isinstance(prompt, dict)
    forbidden = ("<skills_instructions>", "<apps_instructions>", "<permissions instructions>", "<collaboration_mode>", "<environment_context>", "skill.md")
    if not valid or any(marker in json.dumps(prompt, sort_keys=True).casefold() for marker in forbidden):
        raise PreflightError("codex isolation preflight unavailable")
    return info


def _selector_schema_path(root: Path, commit: str, profile: dict[str, Any] | None = None) -> Path:
    authority = profile.get("manifest", {}).get("selector_schema_authority") if isinstance(profile, dict) and isinstance(profile.get("manifest"), dict) else None
    path = authority.get("path") if isinstance(authority, dict) else SELECTOR_SCHEMA_PATH
    if not isinstance(path, str): raise PreflightError("selector schema authority unavailable")
    raw = git_show(root, commit, path)
    destination = root / path
    if destination.read_bytes() != raw: raise PreflightError("selector schema byte drift")
    return destination


def child_argv(info: dict[str, str], schema: Path) -> list[str]:
    argv = [info["path"], "--ask-for-approval", "never", "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config", "--skip-git-repo-check", "--sandbox", "read-only", "--model", MODEL, "--output-schema", str(schema), "--color", "never", "--json"]
    for feature in DISABLED_FEATURES: argv.extend(["--disable", feature])
    for override in CONFIG_OVERRIDES: argv.extend(["-c", override])
    return [*argv, "-"]


def parse_events(raw: bytes, resolver: Any, profile: dict[str, Any]) -> tuple[tuple[dict[str, str], ...], str]:
    """Fail closed: lifecycle and exactly one completed agent message only."""
    context: str | None = None; completed: list[str] = []; turn_done = False
    for line in raw.splitlines():
        try: event = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as error: raise TransportError("malformed event stream") from error
        if not isinstance(event, dict): raise TransportError("event stream unavailable")
        kind = event.get("type")
        if kind == "thread.started":
            if set(event) != {"type", "thread_id"} or not isinstance(event["thread_id"], str) or not event["thread_id"]: raise TransportError("context unavailable")
            if context is not None: raise TransportError("duplicate context")
            context = event["thread_id"]; continue
        if kind in {"turn.started", "turn.completed"}:
            if set(event) - {"type", "usage"}: raise _completed_invalid("lifecycle extension", context)
            turn_done = turn_done or kind == "turn.completed"; continue
        if kind in {"turn.failed", "error"}:
            # Provider/turn failures have no usable completed selector result;
            # after batch consumption this is an ambiguity, never a score row.
            raise TransportError("provider turn unavailable")
        item = event.get("item")
        if kind in {"item.started", "item.updated", "item.completed"} and isinstance(item, dict) and item.get("type") == "reasoning":
            # Reasoning lifecycle is transport metadata only: it is discarded
            # and cannot contribute to the selector result or observation.
            continue
        if kind in {"item.started", "item.updated"} and isinstance(item, dict) and item.get("type") == "agent_message":
            # A message lifecycle may precede its single completed payload.
            continue
        if kind != "item.completed" or not isinstance(item, dict) or set(item) != {"type", "text"} or item.get("type") != "agent_message" or not isinstance(item.get("text"), str):
            item_type = item.get("type") if isinstance(item, dict) else ""
            attempted_effect = item_type in {"effect", "approval"}; attempted_tool = item_type in {"tool_call", "mcp_tool_call", "command_execution", "file_change"}
            flags = {"effect_requested": attempted_effect, "effect_granted": attempted_effect, "claim_requested": item_type == "approval", "claim_granted": item_type == "approval", "tool_requested": attempted_tool, "tool_granted": attempted_tool, "full_schema_or_template_loaded": False}
            raise _completed_invalid("prohibited or unknown event", context, events=flags)
        completed.append(item["text"])
    if not context or not turn_done or len(completed) != 1: raise TransportError("incomplete event stream")
    try: value = json.loads(completed[0])
    except json.JSONDecodeError as error: raise _completed_invalid("completed selector output malformed", context) from error
    try: return resolver.validate_fact_output(value, profile["protocol"], profile["selector_schema"]), context
    except Exception as error: raise _completed_invalid("completed selector output invalid", context) from error


def _invoke(info: dict[str, str], schema: Path, packet: dict[str, Any], *, root: Path, commit: str, state: dict[str, Any], invoke: Callable[..., Any], on_raw: Callable[[], None] | None = None) -> tuple[tuple[dict[str, str], ...], str]:
    # Hash/authority rechecks immediately precede every child launch.
    require_exact_live_head(root, commit)
    if sha256_file(Path(info["path"])) != info["digest"]: raise PreflightError("resolved executable drift")
    _selector_schema_path(root, commit, state["profile"])
    encoded = json.dumps(packet, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    with tempfile.TemporaryDirectory(prefix="aq7-isolated-") as directory:
        try: result = invoke(child_argv(info, schema), cwd=directory, input=encoded, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except OSError as error: raise LaunchError("child launch unavailable") from error
    if result.returncode and not result.stdout: raise TransportError("child transport unavailable")
    if result.stdout and on_raw is not None: on_raw()
    if result.returncode < 0: raise TransportError("child terminated by signal")
    facts, context = parse_events(result.stdout or b"", state["resolver"], state["profile"])
    if result.returncode: raise _completed_invalid("completed selector exited nonzero", context)
    return facts, context


def _canary_packet(profile: dict[str, Any]) -> dict[str, Any]:
    order = profile.get("protocol", {}).get("predicate_order")
    if not isinstance(order, list) or len(order) != 12: raise PreflightError("predicate order unavailable")
    return {"instruction": "Return only the closed predicate_facts selector object in the supplied order.", "task_text": "Return each supplied predicate as absent.", "predicate_order": order, "condition_guidance": []}


def _unconsumed_marker(root: Path) -> str:
    path = root / "EXECPLAN.md"
    try: lines = [line.strip() for line in path.read_text().splitlines() if line.startswith("AQ7-RUN-AUTHORITY ")]
    except OSError as error: raise PreflightError("authority marker unavailable") from error
    if len(lines) != 1: raise PreflightError("authority marker unavailable")
    return lines[0]


def run_canary(*, root: Path, candidate_commit: str, codex: str, invoke: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    state = preflight(root, candidate_commit); info = codex_preflight(codex); state["binding"] = binding_from_profile(state["profile"], cli=info, schedule_digest=state["schedule_digest"])
    index = state["index_module"].AQ7RunIndex(root); marker = _unconsumed_marker(root); cap = index.begin_canary(state["binding"], unconsumed_marker=marker)
    schema = _selector_schema_path(root, state["commit"], state["profile"])
    for attempt in range(2):
        try:
            facts, _context = _invoke(info, schema, _canary_packet(state["profile"]), root=root, commit=state["commit"], state=state, invoke=invoke)
            expected = tuple({"predicate_id": name, "state": "absent"} for name in state["profile"]["protocol"]["predicate_order"])
            if facts != expected: raise CompletedInvalid("canary selector mismatch")
            index.complete_canary(state["binding"], unconsumed_marker=marker, canary_cap=cap)
            return receipt("canary", "passed", state, live_calls=attempt + 1)
        except (LaunchError, TransportError):
            if attempt == 0:
                index.retry_canary(state["binding"], unconsumed_marker=marker, canary_cap=cap, reason="precompletion_infrastructure")
                continue
            index.fail_canary(state["binding"], unconsumed_marker=marker, canary_cap=cap, reason="retry_exhausted")
        except Exception:
            index.fail_canary(state["binding"], unconsumed_marker=marker, canary_cap=cap)
        raise
    raise AssertionError("unreachable")


def _observation(state: dict[str, Any], case: dict[str, Any], condition: str, index: int, context: str,
                 *, facts: tuple[dict[str, str], ...] | None, resolution: dict[str, Any] | None) -> dict[str, Any]:
    scorer, resolver, profile = state["scorer"], state["resolver"], state["profile"]
    task = case["packet"]["task_text"]
    if facts is None:
        facts = None
        resolution = None
    if facts is not None and not isinstance(resolution, dict): raise PreflightError("resolver observation unavailable")
    return {
        "case_id": case["case_id"], "presentation_index": index, "context_id": context,
        "case_sha256": scorer._expected_case_digest(case, "case"), "task_sha256": scorer._expected_case_digest(case, "task"),
        "packet_sha256": scorer._packet_digest(profile, condition, case), "condition_sha256": scorer._condition_digest(profile, condition),
        "execution_sha256": scorer._profile_execution_digest(profile), "runner_sha256": state["binding"]["runner"]["digest"],
        "parse_status": "parsed" if facts is not None and resolution is not None else "malformed",
        "fact_output": {"predicate_facts": list(facts)} if facts is not None else None, "parent_resolution": resolution,
        "events": {"effect_requested": False, "effect_granted": False, "claim_requested": False, "claim_granted": False, "tool_requested": False, "tool_granted": False, "full_schema_or_template_loaded": False},
    }


def execute_trials(*, root: Path, candidate_commit: str, codex: str, invoke: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    state = preflight(root, candidate_commit); info = codex_preflight(codex); state["binding"] = binding_from_profile(state["profile"], cli=info, schedule_digest=state["schedule_digest"])
    index = state["index_module"].AQ7RunIndex(root); marker = _unconsumed_marker(root); schema = _selector_schema_path(root, state["commit"], state["profile"])
    # This only accepts a durable passed canary.  It never invokes one.
    cap = index.begin_batch(state["binding"], unconsumed_marker=marker); session = state["scorer"].create_live_score_session(state["profile"], state["binding"]); contexts: set[str] = set(); grouped = {"current": [], "reduced": []}
    try:
        for presentation_index, slot in enumerate(state["schedule"]):
            condition, case_id = slot.get("condition"), slot.get("case_id")
            case = state["cases"].get(case_id)
            if condition not in {"current", "reduced"} or not isinstance(case, dict): raise PreflightError("schedule case unavailable")
            index.presentation_started(state["binding"], batch_cap=cap)
            task = case.get("packet", {}).get("task_text") if isinstance(case.get("packet"), dict) else None
            if not isinstance(task, str): raise PreflightError("schedule task unavailable")
            packet = state["resolver"].build_condition_packet(state["profile"]["adapter"], condition, task)
            _validate_packet_pair(packet, state["resolver"].build_condition_packet(state["profile"]["adapter"], "reduced" if condition == "current" else "current", task))
            try:
                facts, context = _invoke(info, schema, packet, root=root, commit=state["commit"], state=state, invoke=invoke, on_raw=(lambda: index.response_observed(state["binding"], batch_cap=cap)) if presentation_index == 0 else None)
                if context in contexts: raise CompletedInvalid("duplicate context")
                contexts.add(context)
                resolution = state["resolver"].resolve_decision_certificate(task, list(facts), state["profile"]["protocol"], state["profile"]["reference_policy"], state["profile"]["base_manifest"])
                observation = _observation(state, case, condition, presentation_index, context, facts=facts, resolution=resolution)
            except CompletedInvalid as error:
                # The process completed; retain only a schema-valid malformed sentinel.
                context = getattr(error, "context", None)
                if not isinstance(context, str) or not context: raise TransportError("completed content lacked context")
                if context in contexts: raise PreflightError("context uniqueness unavailable")
                contexts.add(context)
                observation = _observation(state, case, condition, presentation_index, context, facts=None, resolution=None)
                observation["parse_status"] = "malformed"
                observation["events"] = getattr(error, "events")
            grouped[condition].append(observation); index.presentation_completed(state["binding"], batch_cap=cap)
        if len(contexts) != 80: raise CompletedInvalid("context coverage unavailable")
        envelope = {"schema_version": "7.0", "evaluation_mode": "qualification", "provenance_mode": "live_runner", "binding": state["binding"], "execution_contract": state["profile"]["execution_contract"], "schedule": {"seed": SCHEDULE_SEED, "digest": state["schedule_digest"], "presentations": state["schedule"]}, "conditions": [{"id": condition, "digest": state["scorer"]._condition_digest(state["profile"], condition), "observations": grouped[condition]} for condition in ("current", "reduced")]}
        result = session.score(envelope); state["scorer"].validate_result(result)
        if result.get("status") == "insufficient_data": raise PreflightError("live score custody unavailable")
        aggregate = result.get("aggregate_digest")
        if not isinstance(aggregate, str) or len(aggregate) != 64: raise PreflightError("aggregate digest unavailable")
        status = "passed" if result.get("status") == "pass" else "failed"
        index.complete_batch(state["binding"], batch_cap=cap, status=status, aggregate_digest=aggregate)
        return receipt("execute", status, state, live_calls=80, aggregate_digest=aggregate)
    except Exception:
        try: index.mark_batch_ambiguous(state["binding"], batch_cap=cap, reason="infrastructure_interrupted")
        except Exception: pass
        raise


def receipt(mode: str, status: str, state: dict[str, Any], *, live_calls: int, aggregate_digest: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"mode": mode, "status": status, "candidate": {"commit": state["commit"], "tree": state["tree"]}, "presentations": 80 if mode == "execute" else 0, "live_calls": live_calls, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown", "runtime_provenance_proven": False, "provider_identity_proven": False, "model_behavior_proven": False, "sandbox_proven": False, "product_behavior_proven": False, "promotion_eligible": False}
    if aggregate_digest is not None: value["aggregate_digest"] = aggregate_digest
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true"); modes.add_argument("--canary", action="store_true"); modes.add_argument("--execute", action="store_true")
    parser.add_argument("--candidate-commit", required=True); parser.add_argument("--usage-approval", default=""); parser.add_argument("--codex", default="codex")
    args = parser.parse_args(argv)
    if (args.canary or args.execute) and args.usage_approval != APPROVAL: parser.error("live AQ7 requires exact usage approval")
    if not HEX40.fullmatch(args.candidate_commit): parser.error("candidate commit must be lowercase forty-hex")
    try:
        if args.dry_run:
            state = preflight(ROOT, args.candidate_commit); result = receipt("dry-run", "passed", state, live_calls=0)
        elif args.canary: result = run_canary(root=ROOT, candidate_commit=args.candidate_commit, codex=args.codex)
        else: result = execute_trials(root=ROOT, candidate_commit=args.candidate_commit, codex=args.codex)
    except Exception:
        print(json.dumps({"mode": "hold", "status": "hold", "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown", "runtime_provenance_proven": False, "provider_identity_proven": False, "model_behavior_proven": False, "sandbox_proven": False, "product_behavior_proven": False, "promotion_eligible": False}, sort_keys=True, separators=(",", ":")))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__": raise SystemExit(main())
