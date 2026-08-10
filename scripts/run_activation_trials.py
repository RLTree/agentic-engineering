#!/usr/bin/env python3
"""AQ's evaluator-owned, prompt-only runner.

The command has a zero-call default.  ``--canary`` and ``--execute`` are
deliberately opt-in and require an approval reference; production execution is
not attempted by this module's tests.  Raw child events and prompt contents
are held in memory only and are never written to disk.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
FROZEN_COMMIT = "407a2ac124856f0ce1fa33af8a61d0607e413820"
FROZEN_TREE = "8314ca6ad82fa4687720692d8c5762c7aabf6261"
CORPUS_COMMIT = "25de0cb1fe86a802768de9bf64659206d69650d0"
CORPUS_TREE = "e5faff4b1a5ba678a7df1727b5bda3b3d0afe00a"
CORPUS_ROOT = "evals/foundation-v4/future-activation-v2"
SCHEMA_PATH = ROOT / "evals/foundation-v4/selector-output-schema.json"
CHECKER_PATH = ROOT / "scripts/check_reduced_four_skill_candidate.py"
ADVISERS = (
    "agentic-engineering", "codex-task-contract",
    "verification-strategy-engineering", "engineering-learning-loop",
)
MODEL = "gpt-5.5"
REASONING = "medium"
DISABLED_FEATURES = (
    "apply_patch_streaming_events", "apps", "artifact", "auth_elicitation",
    "browser_use", "browser_use_external",
    "browser_use_full_cdp_access", "chronicle", "code_mode",
    "code_mode_buffered_exec", "code_mode_host", "code_mode_only",
    "computer_use", "default_mode_request_user_input", "enable_mcp_apps", "goals",
    "guardian_approval", "hooks", "image_generation", "in_app_browser", "memories", "multi_agent",
    "multi_agent_v2", "plugin_sharing", "plugins", "recommended_plugins",
    "remote_plugin", "request_permissions_tool", "shell_tool",
    "skill_mcp_dependency_install", "skill_search", "standalone_web_search",
    "tool_call_mcp_elicitation", "tool_suggest", "unified_exec", "view_image",
    "workspace_dependencies",
)
CONFIG_OVERRIDES = (
    f'model_reasoning_effort="{REASONING}"',
    'web_search="disabled"',
    "skills.bundled.enabled=false",
    "skills.include_instructions=false",
    "include_permissions_instructions=false",
    "include_apps_instructions=false",
    "include_collaboration_mode_instructions=false",
    "include_environment_context=false",
)
SELECTOR_DECISION_CONTRACT = (
    "Select the minimum necessary decision owner or owners for this task: zero, one, or two. "
    "Shared topical relevance is insufficient; do not select every adviser whose description seems related. "
    "Identify the controlling decision or decisions. For one controlling decision, select exactly one best owner using the catalog description with the most discriminative responsibility; when descriptions overlap, prefer the more specific decision owner over a broad or downstream lens. "
    "Select exactly two only when the task has two independent controlling decisions and one owner is necessary for each; do not stack advisers for a single decision. "
    "Select none when native work is sufficient without an adviser. "
    "An explicit evaluator-vocabulary invocation is decisive: select that named logical adviser and do not add others merely for shared relevance. "
    "Evaluator vocabulary maps $agentic-engineering to agentic-engineering, $codex-task-contract to codex-task-contract, $verification-strategy-engineering to verification-strategy-engineering, and $engineering-learning-loop to engineering-learning-loop. "
    "These bare aliases do not invoke, install, discover, or grant authority. "
    "Return only the schema object. Do not request tools, effects, approvals, claims, or additional context."
)


class RunnerError(ValueError):
    """A custody, preflight, or completed-output failure."""


class InfrastructureError(RunnerError):
    """A child failed before it supplied any completion event."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_show(root: Path, commit: str, path: str) -> bytes:
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=root, capture_output=True)
    if result.returncode:
        raise RunnerError("immutable input unavailable")
    return result.stdout


def git_identity(root: Path, commit: str) -> tuple[str, str]:
    resolved = subprocess.run(["git", "rev-parse", "--verify", f"{commit}^{{commit}}"], cwd=root, capture_output=True, text=True)
    if resolved.returncode:
        raise RunnerError("candidate commit is unavailable")
    candidate = resolved.stdout.strip()
    tree = subprocess.run(["git", "rev-parse", "--verify", f"{candidate}^{{tree}}"], cwd=root, capture_output=True, text=True)
    if tree.returncode:
        raise RunnerError("candidate tree is unavailable")
    return candidate, tree.stdout.strip()


def committed_module(root: Path, commit: str, relative: str, name: str, dependencies: dict[str, Any] | None = None) -> Any:
    """Load evaluator code only after its live bytes match the candidate tree."""
    import types
    raw = git_show(root, commit, relative)
    if (root / relative).read_bytes() != raw:
        raise RunnerError("live evaluator code differs from candidate commit")
    module = types.ModuleType(name)
    module.__file__ = str(root / relative)
    previous = {key: sys.modules.get(key) for key in (dependencies or {})}
    try:
        for key, value in (dependencies or {}).items():
            sys.modules[key] = value
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
    finally:
        for key, value in previous.items():
            if value is None: sys.modules.pop(key, None)
            else: sys.modules[key] = value
    return module


def scorer_module(root: Path, commit: str, checker: Any) -> Any:
    return committed_module(root, commit, "scripts/score_activation.py", "aq_activation_scorer", {"check_reduced_four_skill_candidate": checker})


def validate_candidate(root: Path, candidate_commit: str) -> tuple[Any, dict[str, Any], str, str]:
    """Return the checker module, immutable manifest, commit, and tree."""
    commit, tree = git_identity(root, candidate_commit)
    checker = committed_module(root, commit, "scripts/check_reduced_four_skill_candidate.py", "aq_candidate_checker")
    errors = checker.validate_committed_candidate(root, commit)
    if errors:
        raise RunnerError("candidate custody failed: " + "; ".join(errors))
    return checker, checker.load_candidate_from_commit(root, commit), commit, tree


def load_qualification_cases(root: Path = ROOT) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Load the frozen corpus from Git, never working-tree corpus bytes."""
    documents = {}
    for split in ("authoring", "heldout"):
        path = f"{CORPUS_ROOT}/activation-{split}.json"
        raw = git_show(root, CORPUS_COMMIT, path)
        documents[split] = json.loads(raw)
    cases = []
    for document in documents.values():
        for case in document.get("cases", []):
            if case.get("mode") == "explicit" or (case.get("id", "").startswith("AQ2-H-") and case.get("mode") == "automatic"):
                cases.append(case)
    # The frozen corpus has four explicit cases in each split and 32 heldout automatic cases.
    wanted = {f"AQ2-H-{index:03d}" for index in range(1, 33)} | {f"AQ2-A-{index:03d}" for index in range(33, 37)} | {f"AQ2-H-{index:03d}" for index in range(33, 37)}
    selected = [case for case in cases if case.get("id") in wanted]
    if len(selected) != 40 or {case["id"] for case in selected} != wanted:
        raise RunnerError("frozen qualification distribution is unavailable")
    return selected, {
        "source_commit": CORPUS_COMMIT, "source_tree": CORPUS_TREE,
        "activation_schema_sha256": sha256_bytes(git_show(root, CORPUS_COMMIT, f"{CORPUS_ROOT}/activation-schema.json")),
        "authoring_sha256": sha256_bytes(git_show(root, CORPUS_COMMIT, f"{CORPUS_ROOT}/activation-authoring.json")),
        "heldout_sha256": sha256_bytes(git_show(root, CORPUS_COMMIT, f"{CORPUS_ROOT}/activation-heldout.json")),
    }


def validate_selector_schema(path: Path = SCHEMA_PATH, raw: bytes | None = None) -> dict[str, Any]:
    try:
        value = json.loads(raw if raw is not None else path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise RunnerError("selector output schema unavailable") from error
    expected = {"$schema", "$id", "title", "type", "properties", "required", "additionalProperties"}
    if not isinstance(value, dict) or set(value) != expected or value.get("type") != "object" or value.get("required") != ["selected_advisers"] or value.get("additionalProperties") is not False:
        raise RunnerError("selector output schema is not closed")
    selected = value["properties"].get("selected_advisers") if isinstance(value.get("properties"), dict) else None
    items = selected.get("items") if isinstance(selected, dict) else None
    if not isinstance(selected, dict) or set(selected) != {"type", "items", "maxItems"} or selected.get("type") != "array" or selected.get("maxItems") != 2 or not isinstance(items, dict) or set(items) != {"type", "enum"} or items.get("type") != "string" or items.get("enum") != list(ADVISERS):
        raise RunnerError("selector output schema has the wrong adviser universe")
    return value


def validate_selection(value: Any) -> list[str]:
    if not isinstance(value, dict) or set(value) != {"selected_advisers"}:
        raise RunnerError("completed selector output is not closed")
    chosen = value["selected_advisers"]
    if not isinstance(chosen, list) or len(chosen) > 2 or len(chosen) != len(set(chosen)) or any(item not in ADVISERS for item in chosen):
        raise RunnerError("completed selector output is outside the fixed-four contract")
    return chosen


def selector_packet(case: dict[str, Any], catalog: list[dict[str, str]]) -> str:
    """Build the sole model-visible packet; it intentionally contains no labels."""
    if set(case) - {"id", "family_id", "category", "mode", "prompt", "authority", "condition_blind", "labels_visible_to_runner", "outcomes_visible_to_authoring", "hidden_labels", "near_neighbor_kind", "declared_invocation"}:
        raise RunnerError("unexpected frozen case shape")
    logical = [{"id": record["adviser_id"], "description": record["description"]} for record in catalog]
    packet = {
        "instruction": SELECTOR_DECISION_CONTRACT,
        "task": case["prompt"],
        "logical_advisers": logical,
    }
    # Prevent accidental additions to a packet that is deliberately condition blind.
    return json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def immutable_preflight(root: Path, candidate_commit: str, checker: Any, reduced_commit: str) -> None:
    """Prove all evaluator inputs equal their committed candidate/source bytes."""
    for relative in ("scripts/run_activation_trials.py", "scripts/check_reduced_four_skill_candidate.py", "scripts/score_activation.py", "scripts/validate_future_activation_corpus.py", "evals/foundation-v4/selector-output-schema.json", "evals/foundation-v4/activation-evaluator-schema.json"):
        committed = git_show(root, reduced_commit, relative)
        try:
            live = (root / relative).read_bytes()
        except OSError as error:
            raise RunnerError("required evaluator input unavailable") from error
        if live != committed:
            raise RunnerError("live evaluator input differs from candidate commit")
    selector = git_show(root, reduced_commit, "evals/foundation-v4/selector-output-schema.json")
    validate_selector_schema(raw=selector)
    corpus_paths = tuple(f"{CORPUS_ROOT}/activation-{name}.json" for name in ("schema", "authoring", "heldout"))
    corpus = {}
    for relative in corpus_paths:
        committed = git_show(root, CORPUS_COMMIT, relative)
        if (root / relative).read_bytes() != committed:
            raise RunnerError("live frozen corpus differs from source commit")
        corpus[relative] = json.loads(committed)
    try:
        import jsonschema
        validator = jsonschema.Draft202012Validator(corpus[f"{CORPUS_ROOT}/activation-schema.json"])
        if any(validator.iter_errors(corpus[f"{CORPUS_ROOT}/activation-authoring.json"])) or any(validator.iter_errors(corpus[f"{CORPUS_ROOT}/activation-heldout.json"])):
            raise RunnerError("frozen corpus schema validation failed")
    except ImportError as error:
        raise RunnerError("jsonschema unavailable for immutable corpus preflight") from error


def schedule(cases: list[dict[str, Any]], seed: str) -> list[tuple[str, dict[str, Any]]]:
    """Strictly alternate randomized current/reduced presentations for all 80 trials."""
    if not isinstance(seed, str) or not seed.strip():
        raise RunnerError("seed must be nonblank")
    rng = random.Random(int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16))
    by_id = {case["id"]: case for case in cases}
    identifiers = sorted(by_id)
    current, reduced = identifiers[:], identifiers[:]
    rng.shuffle(current); rng.shuffle(reduced)
    first = rng.choice(("current", "reduced"))
    other = "reduced" if first == "current" else "current"
    result: list[tuple[str, dict[str, Any]]] = []
    for left, right in zip(current, reduced, strict=True):
        result.append((first, by_id[left])); result.append((other, by_id[right]))
    if len(result) != 80 or any(result[index][0] == result[index + 1][0] for index in range(79)):
        raise RunnerError("invalid strict-alternating schedule")
    return result


def codex_preflight(codex: str, probe: Callable[..., Any] = subprocess.run) -> dict[str, str]:
    resolved = shutil.which(codex) if not Path(codex).is_absolute() else codex
    if not resolved:
        raise RunnerError("codex executable unavailable")
    executable = Path(resolved).resolve()
    if not executable.is_file():
        raise RunnerError("codex executable unavailable")
    version = probe([str(executable), "--version"], capture_output=True, text=True)
    if version.returncode or not version.stdout.strip():
        raise RunnerError("codex version preflight failed")
    help_result = probe([str(executable), "exec", "--help"], capture_output=True, text=True)
    help_text = (help_result.stdout or "") + (help_result.stderr or "")
    required = ("--ephemeral", "--ignore-user-config", "--strict-config", "--output-schema", "--json", "--sandbox", "--disable")
    if help_result.returncode or any(flag not in help_text for flag in required):
        raise RunnerError("codex exec capability preflight failed")
    prompt_argv = [str(executable), "-c", f'model="{MODEL}"']
    for override in CONFIG_OVERRIDES:
        prompt_argv.extend(["-c", override])
    for feature in DISABLED_FEATURES:
        prompt_argv.extend(["--disable", feature])
    prompt_argv.extend(["debug", "prompt-input", "AQ local isolation preflight"])
    with tempfile.TemporaryDirectory(prefix="aq-local-preflight-") as temporary:
        rendered = probe(prompt_argv, cwd=temporary, capture_output=True, text=True)
    try:
        prompt_input = json.loads(rendered.stdout)
    except (json.JSONDecodeError, TypeError) as error:
        raise RunnerError("codex prompt isolation preflight failed") from error
    prompt_text = json.dumps(prompt_input, sort_keys=True)
    prohibited = ("<skills_instructions>", "SKILL.md", "<apps_instructions>", "<permissions instructions>", "<collaboration_mode>", "<environment_context>")
    if rendered.returncode or (rendered.stderr or "").strip() or any(marker in prompt_text for marker in prohibited):
        raise RunnerError("codex prompt isolation preflight failed")
    return {"path": str(executable), "version": version.stdout.strip(), "sha256": sha256_file(executable)}


def child_argv(codex_path: str, temporary_cwd: str, schema_path: Path) -> list[str]:
    # ``--ask-for-approval`` is a global Codex option and must precede ``exec``.
    argv = [codex_path, "--ask-for-approval", "never", "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config", "--skip-git-repo-check", "--cd", temporary_cwd, "--sandbox", "read-only", "--model", MODEL]
    for override in CONFIG_OVERRIDES:
        argv.extend(["-c", override])
    for feature in DISABLED_FEATURES:
        argv.extend(["--disable", feature])
    return argv + ["--output-schema", str(schema_path.resolve()), "--color", "never", "--json", "-"]


def error_message(value: Any) -> str:
    """Return a bounded diagnostic for a terminal child error event."""
    if isinstance(value, dict):
        value = value.get("message")
    if not isinstance(value, str) or not value.strip():
        return "unspecified child error"
    return " ".join(value.split())[:240]


def parse_events(raw: bytes) -> tuple[list[str], bytes, str]:
    """Parse Codex JSONL and retain the actual ephemeral thread identity only."""
    completed: list[str] = []
    thread_id: str | None = None
    turn_completed = False
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise InfrastructureError("child JSONL is malformed before completion") from error
        if not isinstance(event, dict):
            raise InfrastructureError("child JSONL event is not an object")
        event_type = event.get("type")
        if event_type == "thread.started":
            value = event.get("thread_id")
            if not isinstance(value, str) or not value:
                raise InfrastructureError("thread.started lacks thread_id")
            thread_id = value
            continue
        if event_type == "turn.started":
            continue
        if event_type == "turn.completed":
            turn_completed = True
            continue
        if event_type == "turn.failed":
            raise RunnerError(f"child turn failed: {error_message(event.get('error'))}")
        if event_type == "error":
            raise RunnerError(f"child stream error: {error_message(event.get('message'))}")
        item = event.get("item")
        if event_type not in {"item.started", "item.updated", "item.completed"} or not isinstance(item, dict):
            raise RunnerError(f"unrecognized Codex JSONL event type: {error_message(event_type)}")
        item_type = item.get("type")
        if item_type == "error":
            raise RunnerError(f"child error item: {error_message(item.get('message'))}")
        forbidden = {"tool_call", "mcp_tool_call", "command_execution", "file_change", "mcp_call", "function_call", "web_search_call", "effect", "approval", "approval_request"}
        if item_type in forbidden:
            raise RunnerError("child emitted an authority or tool event")
        if item_type not in {"agent_message", "reasoning"}:
            raise RunnerError(f"unrecognized Codex JSONL item type: {error_message(item_type)}")
        if event_type == "item.completed":
            if item_type == "reasoning":
                continue
            text = item.get("text")
            if not isinstance(text, str):
                raise RunnerError("completed agent message lacks text")
            completed.append(text)
    if not thread_id or not completed or not turn_completed:
        raise InfrastructureError("child supplied no completed output")
    if len(completed) != 1:
        raise RunnerError("child supplied multiple completed outputs")
    try:
        output = json.loads(completed[0])
    except json.JSONDecodeError as error:
        raise RunnerError("completed agent output is malformed") from error
    return validate_selection(output), raw, thread_id


def resolve_payloads(checker: Any, candidate: dict[str, Any], case: dict[str, Any], selected: list[str], root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    labels = case.get("hidden_labels")
    if not isinstance(labels, dict):
        raise RunnerError("frozen hidden trigger labels unavailable")
    outcome = checker.resolve_parent_payload_resolution(candidate, labels.get("reference_triggers", []), selected)
    if outcome["status"] == "cap_exceeded":
        return {"status": "cap_exceeded", "resolved_count": outcome["resolved_count"]}, []
    records = outcome["records"]
    output = []
    for record in records:
        if record.get("full_schema_or_template") is not False or record.get("content_class") != "compact-reference":
            raise RunnerError("schema/template payload prohibited")
        raw = git_show(root, FROZEN_COMMIT, record["source_path"])
        if hashlib.sha256(raw).hexdigest() != record["sha256"]:
            raise RunnerError("resolved payload digest drift")
        output.append({"payload_id": record["payload_id"], "owner_adviser_id": record["owner_adviser_id"], "source_path": record["source_path"], "sha256": record["sha256"]})
    return {"status": "resolved", "resolved_count": len(output)}, output


def execution_contract(codex_info: dict[str, str], schedule_seed: str, schedule_digest: str, catalog_digest: str, reduced_commit: str) -> dict[str, Any]:
    contract = {
        "model": MODEL, "reasoning": REASONING, "cli_path": codex_info["path"], "cli_version": codex_info["version"], "cli_sha256": codex_info["sha256"],
        "tools_sha256": sha256_json({"permitted": [], "disabled": DISABLED_FEATURES, "sandbox": "read-only", "approval": "never"}),
        "host_surface_sha256": sha256_json({"cli": codex_info, "argv": child_argv("<codex>", "<fresh-empty>", SCHEMA_PATH), "empty_temp_cwd": True, "selector_catalog_sha256": catalog_digest}),
        "runner_path": "scripts/run_activation_trials.py", "runner_protocol_sha256": sha256_file(ROOT / "scripts/run_activation_trials.py"),
        "schedule_seed": schedule_seed, "schedule_sha256": schedule_digest, "evaluator_schema_sha256": sha256_bytes(git_show(ROOT, reduced_commit, "evals/foundation-v4/activation-evaluator-schema.json")),
        "zero_write": True, "raw_trajectories_persisted": False,
    }
    contract["condition_parity_sha256"] = sha256_json({key: value for key, value in contract.items() if key not in {"condition_parity_sha256", "schedule_seed", "schedule_sha256"}})
    return contract


def run_one(*, argv: list[str] | None = None, argv_factory: Callable[[], list[str]] | None = None, packet: str, invoke: Callable[..., Any], allow_retry: bool = False) -> tuple[list[str], bytes, str]:
    """Launch once, except for an explicitly designated transport canary."""
    if (argv is None) == (argv_factory is None):
        raise RunnerError("provide exactly one child argv source")
    if not isinstance(allow_retry, bool):
        raise RunnerError("allow_retry must be boolean")
    for attempt in range(2 if allow_retry else 1):
        try:
            child_argv_value = argv_factory() if argv_factory else argv
            process = invoke(child_argv_value, input=packet.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            raw = process.stdout if isinstance(process.stdout, bytes) else str(process.stdout).encode()
            parsed = parse_events(raw)
            if process.returncode:
                raise RunnerError("child exited nonzero after completion")
            return parsed
        except InfrastructureError:
            if allow_retry and attempt == 0:
                continue
            raise
    raise RunnerError("unreachable child retry state")


def invoke_packet(*, codex_path: str, packet: str, invoke: Callable[..., Any], allow_retry: bool = False) -> tuple[list[str], bytes, str]:
    """Invoke a packet once; only a non-corpus transport canary may opt in to retry."""
    temporary: list[tempfile.TemporaryDirectory[str]] = []
    def fresh_argv() -> list[str]:
        directory = tempfile.TemporaryDirectory(prefix="aq-prompt-only-")
        temporary.append(directory)
        return child_argv(codex_path, directory.name, SCHEMA_PATH)
    try:
        return run_one(argv_factory=fresh_argv, packet=packet, invoke=invoke, allow_retry=allow_retry)
    finally:
        for directory in temporary:
            directory.cleanup()


def trial_observation(*, scorer: Any, checker: Any, candidate: dict[str, Any], condition: str, candidate_commit: str, candidate_tree: str, case: dict[str, Any], catalog: list[dict[str, str]], contract: dict[str, Any], codex_path: str, invoke: Callable[..., Any], root: Path, presentation_index: int = 0, allow_retry: bool = False) -> dict[str, Any]:
    if not isinstance(presentation_index, int) or not 0 <= presentation_index < 80:
        raise RunnerError("presentation index is outside the qualification schedule")
    if not isinstance(allow_retry, bool) or allow_retry:
        raise RunnerError("qualification trials never retry")
    packet = selector_packet(case, catalog)
    selected, _raw_event, context_id = invoke_packet(codex_path=codex_path, packet=packet, invoke=invoke, allow_retry=False)
    payload_resolution, payloads = resolve_payloads(checker, candidate, case, selected, root)
    prompt_digest = sha256_bytes(case["prompt"].encode())
    observation = {
        "case_id": case["id"], "presentation_index": presentation_index, "context_id": context_id,
        "corpus_prompt_sha256": prompt_digest, "task_sha256": prompt_digest,
        "selector_packet_sha256": scorer.selector_packet_digest(case["prompt"], catalog),
        "candidate_input_sha256": candidate["conditions"][condition]["condition_input_sha256"],
        "selector_catalog_sha256": candidate["conditions"][condition]["selector_catalog_sha256"],
        "parse_status": "parsed", "selected_advisers": selected,
        "payload_resolution": payload_resolution, "resolved_payloads": payloads, "execution_contract_sha256": sha256_json(contract),
        "runner_protocol_sha256": contract["runner_protocol_sha256"],
        "effect_requested": False, "effect_granted": False, "claim_requested": False, "claim_granted": False,
        "tool_requested": False, "tool_granted": False, "full_schema_or_template_loaded": False,
    }
    # Exact child bytes are discarded after parsing; the runner has no claim
    # authority and serializes neither raw evidence nor a promotion receipt.
    return observation


def execute_trials(*, root: Path, candidate_commit: str, seed: str, codex: str, invoke: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Run the mandatory canary then the one 80-presentation AQ schedule.

    This function intentionally has no filesystem output.  Its caller owns any
    authorization decision and receives a single compact evaluator envelope.
    """
    checker, candidate, reduced_commit, reduced_tree = validate_candidate(root, candidate_commit)
    immutable_preflight(root, candidate_commit, checker, reduced_commit)
    cases, corpus = load_qualification_cases(root)
    plan = schedule(cases, seed)
    codex_info = codex_preflight(codex)
    catalogs = {condition: checker.selector_catalog(candidate, condition, root, reduced_commit) for condition in ("current", "reduced")}
    if any([record["adviser_id"] for record in catalog] != list(ADVISERS) for catalog in catalogs.values()):
        raise RunnerError("selector catalog order drift")
    schedule_digest = sha256_json([(condition, case["id"]) for condition, case in plan])
    catalog_digest = sha256_json(catalogs)
    contract = execution_contract(codex_info, seed, schedule_digest, catalog_digest, reduced_commit)
    scorer = scorer_module(root, reduced_commit, checker)
    if not hasattr(scorer, "score") or not hasattr(scorer, "selector_packet_digest"):
        raise RunnerError("evaluator-owned live scorer unavailable")
    # Canary is intentionally outside the corpus and not included in scoring.
    canary_packet = json.dumps({"instruction": "Return only the schema object with an empty selected_advisers array.", "task": "AQ evaluator transport canary. Do not use tools or request authority.", "logical_advisers": [{"id": item, "description": "logical evaluator entry"} for item in ADVISERS]}, sort_keys=True, separators=(",", ":"))
    invoke_packet(codex_path=codex_info["path"], packet=canary_packet, invoke=invoke, allow_retry=True)
    grouped: dict[str, list[dict[str, Any]]] = {"current": [], "reduced": []}
    indexed_plan = list(enumerate(plan))
    if [presentation_index for presentation_index, _ in indexed_plan] != list(range(80)):
        raise RunnerError("qualification schedule indices are incomplete")
    for presentation_index, (condition, case) in indexed_plan:
        candidate_id, candidate_tree = (FROZEN_COMMIT, FROZEN_TREE) if condition == "current" else (reduced_commit, reduced_tree)
        observation = trial_observation(scorer=scorer, checker=checker, candidate=candidate, condition=condition, candidate_commit=candidate_id, candidate_tree=candidate_tree, case=case, catalog=catalogs[condition], contract=contract, codex_path=codex_info["path"], invoke=invoke, root=root, presentation_index=presentation_index)
        grouped[condition].append(observation)
    if any(len(grouped[condition]) != 40 for condition in grouped):
        raise RunnerError("partial scorer payload prohibited")
    envelope = {
        "schema_version": "2.0", "evaluation_mode": "qualification", "provenance_mode": "live_runner", "corpus": corpus,
        "reduced_candidate": {"commit": reduced_commit, "tree": reduced_tree, "input_sha256": candidate["conditions"]["reduced"]["condition_input_sha256"]}, "execution_contract": contract,
        "conditions": [{"id": condition, "candidate": {"commit": FROZEN_COMMIT, "tree": FROZEN_TREE, "input_sha256": candidate["conditions"][condition]["condition_input_sha256"]} if condition == "current" else {"commit": reduced_commit, "tree": reduced_tree, "input_sha256": candidate["conditions"][condition]["condition_input_sha256"]}, "adviser_universe": list(ADVISERS), "observations": grouped[condition]} for condition in ("current", "reduced")],
    }
    result = scorer.score(envelope, root)
    if result.get("promotion_eligible") is not False:
        raise RunnerError("runner scoring result attempted promotion")
    if result.get("runtime_provenance_proven") is not False:
        raise RunnerError("runner scoring result attempted runtime provenance claim")
    if "provenance_mode" in result or any(result.get(field) is True for field in ("provider_identity_proven", "product_behavior_proven")):
        raise RunnerError("runner scoring result attempted an attested runtime claim")
    return result


def run_canary(*, root: Path, candidate_commit: str, codex: str, invoke: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Run one non-corpus parser/argv canary; it establishes no provider identity."""
    checker, _candidate, reduced_commit, _tree = validate_candidate(root, candidate_commit)
    immutable_preflight(root, candidate_commit, checker, reduced_commit)
    info = codex_preflight(codex)
    packet = json.dumps({"instruction": "Return only the schema object with an empty selected_advisers array.", "task": "AQ evaluator transport canary. Do not use tools or request authority.", "logical_advisers": [{"id": item, "description": "logical evaluator entry"} for item in ADVISERS]}, sort_keys=True, separators=(",", ":"))
    selected, _raw_digest, context_id = invoke_packet(codex_path=info["path"], packet=packet, invoke=invoke, allow_retry=True)
    return {"stage": "AQ", "mode": "canary", "status": "parsed", "context_id": context_id, "selected_advisers": selected, "provider_identity_proven": False, "raw_trajectories_persisted": False, "maximum_claim": "parser and argv acceptance only"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--canary", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    parser.add_argument("--usage-approval", default="")
    parser.add_argument("--candidate-commit", default="HEAD")
    parser.add_argument("--seed", default="aq-v4-default-seed")
    parser.add_argument("--codex", default="codex")
    args = parser.parse_args(argv)
    if (args.canary or args.execute) and not args.usage_approval.strip():
        parser.error("--canary/--execute require a nonblank --usage-approval reference")
    if args.canary:
        try:
            result = run_canary(root=ROOT, candidate_commit=args.candidate_commit, codex=args.codex)
        except (RunnerError, OSError) as error:
            print(f"HOLD: {error}", file=sys.stderr); return 2
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    if args.execute:
        try:
            result = execute_trials(root=ROOT, candidate_commit=args.candidate_commit, seed=args.seed, codex=args.codex)
        except (RunnerError, OSError) as error:
            print(f"HOLD: {error}", file=sys.stderr); return 2
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    try:
        checker, candidate, commit, tree = validate_candidate(ROOT, args.candidate_commit)
        immutable_preflight(ROOT, args.candidate_commit, checker, commit)
        cases, corpus = load_qualification_cases(ROOT)
        plan = schedule(cases, args.seed)
        codex_info = codex_preflight(args.codex)
        # Construct a representative argv without invoking it; the execution
        # path always creates a fresh directory again for the actual child.
        with tempfile.TemporaryDirectory(prefix="aq-preflight-") as temporary:
            child_argv(codex_info["path"], temporary, SCHEMA_PATH)
    except (RunnerError, OSError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 2
    summary = {"stage": "AQ", "mode": "dry-run", "candidate": {"commit": commit, "tree": tree}, "corpus": corpus, "cli_sha256": codex_info["sha256"], "qualification_trials": len(plan), "schedule_seed": args.seed, "schedule_sha256": sha256_json([(condition, case["id"]) for condition, case in plan]), "live_calls": 0, "raw_trajectories_persisted": False, "claim_ceiling": "structural preflight only"}
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
