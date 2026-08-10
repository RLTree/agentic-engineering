#!/usr/bin/env python3
"""AQ4 evaluator-owned prompt-only decision-atom runner.

Default operation makes zero calls.  Live canary/batch paths are opt-in and
fail before Codex preflight while any AQ4 corpus/evaluator binding is unbound.
Raw child JSONL and task text remain in memory and are never serialized.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = "scripts/check_reduced_four_skill_candidate_v4.py"
SCORER_PATH = "scripts/score_activation_v4.py"
RUNNER_PATH = "scripts/run_activation_trials_v4.py"
SELECTOR_SCHEMA_PATH = "evals/foundation-v4/decision-atom-selector-output-schema.json"
EVALUATOR_SCHEMA_PATH = "evals/foundation-v4/activation-evaluator-schema-v4.json"
MODEL = "gpt-5.5"
REASONING = "medium"
DISABLED_FEATURES = (
    "apply_patch_streaming_events", "apps", "artifact", "auth_elicitation",
    "browser_use", "browser_use_external", "browser_use_full_cdp_access",
    "chronicle", "code_mode", "code_mode_buffered_exec", "code_mode_host",
    "code_mode_only", "computer_use", "default_mode_request_user_input",
    "enable_mcp_apps", "goals", "guardian_approval", "hooks",
    "image_generation", "in_app_browser", "memories", "multi_agent",
    "multi_agent_v2", "plugin_sharing", "plugins", "recommended_plugins",
    "remote_plugin", "request_permissions_tool", "shell_tool",
    "skill_mcp_dependency_install", "skill_search", "standalone_web_search",
    "tool_call_mcp_elicitation", "tool_suggest", "unified_exec", "view_image",
    "workspace_dependencies",
)
CONFIG_OVERRIDES = (
    f'model_reasoning_effort="{REASONING}"', 'web_search="disabled"',
    "skills.bundled.enabled=false", "skills.include_instructions=false",
    "include_permissions_instructions=false", "include_apps_instructions=false",
    "include_collaboration_mode_instructions=false", "include_environment_context=false",
)


class RunnerError(ValueError):
    pass


class InfrastructureError(RunnerError):
    pass


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


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
        raise RunnerError("candidate commit unavailable")
    exact = resolved.stdout.strip()
    tree = subprocess.run(["git", "rev-parse", "--verify", f"{exact}^{{tree}}"], cwd=root, capture_output=True, text=True)
    if tree.returncode:
        raise RunnerError("candidate tree unavailable")
    return exact, tree.stdout.strip()


def require_live_head_and_clean(root: Path, candidate_commit: str, probe: Callable[..., Any] = subprocess.run) -> None:
    candidate = probe(["git", "rev-parse", "--verify", f"{candidate_commit}^{{commit}}"], cwd=root, capture_output=True, text=True)
    head = probe(["git", "rev-parse", "--verify", "HEAD^{commit}"], cwd=root, capture_output=True, text=True)
    status = probe(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=root, capture_output=True, text=True)
    if candidate.returncode or head.returncode or candidate.stdout.strip() != head.stdout.strip():
        raise RunnerError("candidate commit is not live HEAD")
    if status.returncode or status.stdout:
        raise RunnerError("repository worktree is not clean")


def committed_module(root: Path, commit: str, relative: str, name: str, dependencies: dict[str, Any] | None = None) -> Any:
    require_live_head_and_clean(root, commit)
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
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value
    return module


def validate_candidate(root: Path, candidate_commit: str) -> tuple[Any, dict[str, Any], str, str]:
    require_live_head_and_clean(root, candidate_commit)
    commit, tree = git_identity(root, candidate_commit)
    checker = committed_module(root, commit, CHECKER_PATH, "aq4_candidate_checker")
    candidate = checker.load_candidate(root, commit)
    checker.require_bound(candidate)
    errors = checker.validate_candidate(candidate, root, commit, allow_unbound=False)
    if errors:
        raise RunnerError("candidate custody failed: " + "; ".join(errors))
    return checker, candidate, commit, tree


def immutable_preflight(root: Path, commit: str, candidate: dict[str, Any]) -> None:
    """Recheck every bound byte; safe to call immediately before a child."""
    require_live_head_and_clean(root, commit)
    corpus = candidate["corpus"]
    corpus_commit, corpus_tree = git_identity(root, corpus["commit"])
    if corpus_commit != corpus["commit"] or corpus_tree != corpus["tree"]:
        raise RunnerError("corpus commit or tree drift")
    if corpus.get("validator_source") != "candidate_commit":
        raise RunnerError("validator source must be the exact candidate commit")
    for row in candidate["evaluator_surface"]["files"]:
        relative = row["path"]
        raw = git_show(root, commit, relative)
        if (root / relative).read_bytes() != raw:
            raise RunnerError("live evaluator input differs from candidate commit")
        if sha256_bytes(raw) != row["sha256"]:
            raise RunnerError("bound evaluator digest mismatch")
    digest_by_path = {corpus["schema_path"]: corpus["schema_sha256"], corpus["authoring_path"]: corpus["authoring_sha256"], corpus["heldout_path"]: corpus["heldout_sha256"]}
    for relative in (corpus["schema_path"], corpus["authoring_path"], corpus["heldout_path"]):
        raw = git_show(root, corpus["commit"], relative)
        if (root / relative).read_bytes() != raw:
            raise RunnerError("live frozen corpus input differs from corpus commit")
        if sha256_bytes(raw) != digest_by_path[relative]:
            raise RunnerError("frozen corpus or validator digest mismatch")


def validate_selector_schema(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RunnerError("selector schema unavailable") from exc
    selected = value.get("properties", {}).get("selected_decision_atoms", {}) if isinstance(value, dict) else {}
    items = selected.get("items", {}) if isinstance(selected, dict) else {}
    if set(value) != {"$schema", "$id", "title", "type", "properties", "required", "additionalProperties"} or value.get("type") != "object" or value.get("required") != ["selected_decision_atoms"] or value.get("additionalProperties") is not False:
        raise RunnerError("selector schema is not closed")
    if selected.get("type") != "array" or selected.get("uniqueItems") is not True or selected.get("maxItems") != 2 or items.get("enum") != ["topology-control-boundary", "task-contract", "verification-strategy", "engineering-learning"]:
        raise RunnerError("selector schema atom universe mismatch")
    return value


def validate_selection(value: Any, atoms: tuple[str, ...]) -> list[str]:
    if not isinstance(value, dict) or set(value) != {"selected_decision_atoms"}:
        raise RunnerError("completed selector output is not closed")
    selected = value["selected_decision_atoms"]
    if not isinstance(selected, list) or len(selected) > 2 or len(selected) != len(set(selected)) or any(item not in atoms for item in selected):
        raise RunnerError("completed selector output is outside the fixed atom contract")
    return selected


def selector_packet(*, scorer: Any, task: str, catalog: list[dict[str, Any]], constraint: dict[str, Any]) -> str:
    value = scorer.selector_packet_value(task, catalog, constraint)
    if set(value) != {"instruction", "task", "decision_atom_catalog", "explicit_constraint"}:
        raise RunnerError("selector packet label boundary escaped")
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if sha256_bytes(serialized.encode()) != scorer.selector_packet_digest(task, catalog, constraint):
        raise RunnerError("selector packet digest mismatch")
    return serialized


def schedule(cases: dict[str, dict[str, Any]], seed: str, scorer: Any) -> list[tuple[str, dict[str, Any]]]:
    plan = scorer.qualification_schedule(cases, seed)
    return [(condition, cases[case_id]) for condition, case_id in plan]


def codex_preflight(codex: str, probe: Callable[..., Any] = subprocess.run) -> dict[str, str]:
    resolved = shutil.which(codex) if not Path(codex).is_absolute() else codex
    if not resolved or not Path(resolved).resolve().is_file():
        raise RunnerError("codex executable unavailable")
    executable = Path(resolved).resolve()
    version = probe([str(executable), "--version"], capture_output=True, text=True)
    help_result = probe([str(executable), "exec", "--help"], capture_output=True, text=True)
    help_text = (help_result.stdout or "") + (help_result.stderr or "")
    required = ("--ephemeral", "--ignore-user-config", "--strict-config", "--output-schema", "--json", "--sandbox", "--disable")
    if version.returncode or not version.stdout.strip() or help_result.returncode or any(flag not in help_text for flag in required):
        raise RunnerError("codex capability preflight failed")
    argv = [str(executable), "-c", f'model="{MODEL}"']
    for override in CONFIG_OVERRIDES:
        argv.extend(["-c", override])
    for feature in DISABLED_FEATURES:
        argv.extend(["--disable", feature])
    argv.extend(["debug", "prompt-input", "AQ4 local isolation preflight"])
    with tempfile.TemporaryDirectory(prefix="aq4-local-preflight-") as temporary:
        rendered = probe(argv, cwd=temporary, capture_output=True, text=True)
    try:
        prompt = json.loads(rendered.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise RunnerError("codex prompt isolation preflight failed") from exc
    prohibited = ("<skills_instructions>", "SKILL.md", "<apps_instructions>", "<permissions instructions>", "<collaboration_mode>", "<environment_context>")
    if rendered.returncode or (rendered.stderr or "").strip() or any(marker in json.dumps(prompt, sort_keys=True) for marker in prohibited):
        raise RunnerError("codex prompt isolation preflight failed")
    return {"path": str(executable), "version": version.stdout.strip(), "sha256": sha256_file(executable)}


def child_argv(codex_path: str, temporary_cwd: str, schema_path: Path) -> list[str]:
    argv = [codex_path, "--ask-for-approval", "never", "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config", "--skip-git-repo-check", "--cd", temporary_cwd, "--sandbox", "read-only", "--model", MODEL]
    for override in CONFIG_OVERRIDES:
        argv.extend(["-c", override])
    for feature in DISABLED_FEATURES:
        argv.extend(["--disable", feature])
    return argv + ["--output-schema", str(schema_path.resolve()), "--color", "never", "--json", "-"]


def parse_events(raw: bytes, atoms: tuple[str, ...]) -> tuple[list[str], str]:
    completed: list[str] = []
    thread_id: str | None = None
    turn_completed = False
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise InfrastructureError("child JSONL malformed before completion") from exc
        if not isinstance(event, dict):
            raise InfrastructureError("child JSONL event is not an object")
        event_type = event.get("type")
        if event_type == "thread.started":
            if not isinstance(event.get("thread_id"), str) or not event["thread_id"]:
                raise InfrastructureError("thread identity unavailable")
            thread_id = event["thread_id"]
            continue
        if event_type in {"turn.started"}:
            continue
        if event_type == "turn.completed":
            turn_completed = True
            continue
        if event_type in {"turn.failed", "error"}:
            raise RunnerError("child failed")
        item = event.get("item")
        if event_type not in {"item.started", "item.updated", "item.completed"} or not isinstance(item, dict):
            raise RunnerError("unrecognized child event")
        item_type = item.get("type")
        if item_type in {"tool_call", "mcp_tool_call", "command_execution", "file_change", "mcp_call", "function_call", "web_search_call", "effect", "approval", "approval_request", "error"}:
            raise RunnerError("child emitted prohibited event")
        if item_type not in {"agent_message", "reasoning"}:
            raise RunnerError("unrecognized child item")
        if event_type == "item.completed" and item_type == "agent_message":
            if not isinstance(item.get("text"), str):
                raise RunnerError("completed output unavailable")
            completed.append(item["text"])
    if not thread_id or not turn_completed or len(completed) != 1:
        raise InfrastructureError("child supplied no single completed output")
    try:
        selected = validate_selection(json.loads(completed[0]), atoms)
    except json.JSONDecodeError as exc:
        raise RunnerError("completed output malformed") from exc
    return selected, thread_id


def run_one(*, argv_factory: Callable[[], list[str]], packet: str, invoke: Callable[..., Any], before_invoke: Callable[[], None], allow_retry: bool = False) -> tuple[list[str], str]:
    if not isinstance(allow_retry, bool):
        raise RunnerError("allow_retry must be boolean")
    for attempt in range(2 if allow_retry else 1):
        try:
            before_invoke()
            process = invoke(argv_factory(), input=packet.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            raw = process.stdout if isinstance(process.stdout, bytes) else str(process.stdout).encode()
            selected, context = parse_events(raw, ("topology-control-boundary", "task-contract", "verification-strategy", "engineering-learning"))
            if process.returncode:
                raise RunnerError("child exited nonzero after completion")
            return selected, context
        except InfrastructureError:
            if allow_retry and attempt == 0:
                continue
            raise
    raise RunnerError("unreachable retry state")


def invoke_packet(*, codex_info: dict[str, str], packet: str, invoke: Callable[..., Any], allow_retry: bool, custody_recheck: Callable[[], None]) -> tuple[list[str], str]:
    temporary: list[tempfile.TemporaryDirectory[str]] = []
    schema_path = ROOT / SELECTOR_SCHEMA_PATH
    def argv_factory() -> list[str]:
        directory = tempfile.TemporaryDirectory(prefix="aq4-prompt-only-")
        temporary.append(directory)
        return child_argv(codex_info["path"], directory.name, schema_path)
    def before_invoke() -> None:
        custody_recheck()
        if sha256_file(Path(codex_info["path"])) != codex_info["sha256"]:
            raise RunnerError("Codex executable drift detected")
    try:
        return run_one(argv_factory=argv_factory, packet=packet, invoke=invoke, before_invoke=before_invoke, allow_retry=allow_retry)
    finally:
        for directory in temporary:
            directory.cleanup()


def _project_payloads(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: row[key] for key in ("payload_id", "owner_adviser_id", "source_path", "sha256")} for row in rows]


def execution_contract(codex: dict[str, str], seed: str, schedule_digest: str, catalog_digest: str, commit: str) -> dict[str, Any]:
    contract = {
        "model": MODEL, "reasoning": REASONING, "cli_path": codex["path"], "cli_version": codex["version"], "cli_sha256": codex["sha256"],
        "tools_sha256": sha256_json({"permitted": [], "disabled": DISABLED_FEATURES, "sandbox": "read-only", "approval": "never"}),
        "host_surface_sha256": sha256_json({"cli": codex, "empty_temp_cwd": True, "catalogs_sha256": catalog_digest}),
        "runner_path": RUNNER_PATH, "runner_protocol_sha256": sha256_bytes(git_show(ROOT, commit, RUNNER_PATH)),
        "schedule_seed": seed, "schedule_sha256": schedule_digest,
        "evaluator_schema_sha256": sha256_bytes(git_show(ROOT, commit, EVALUATOR_SCHEMA_PATH)),
        "zero_write": True, "raw_trajectories_persisted": False,
    }
    contract["condition_parity_sha256"] = sha256_json({key: value for key, value in contract.items() if key not in {"condition_parity_sha256", "schedule_seed", "schedule_sha256"}})
    return contract


def trial_observation(*, checker: Any, scorer: Any, candidate: dict[str, Any], base: dict[str, Any], case: dict[str, Any], condition: str, presentation_index: int, contract: dict[str, Any], codex_info: dict[str, str], invoke: Callable[..., Any], custody_recheck: Callable[[], None]) -> dict[str, Any]:
    constraint = checker.parse_explicit_atom_constraint(case["prompt"], candidate)
    catalog = candidate["conditions"][condition]["atom_catalog"]
    packet = selector_packet(scorer=scorer, task=case["prompt"], catalog=catalog, constraint=constraint)
    selected, context = invoke_packet(codex_info=codex_info, packet=packet, invoke=invoke, allow_retry=False, custody_recheck=custody_recheck)
    checker.enforce_explicit_constraint(selected, constraint)
    mapped = checker.map_atoms_to_advisers(candidate, selected)
    outcome = checker.resolve_parent_payload_resolution(base, case["hidden_labels"]["reference_triggers"], mapped)
    # Verify every compact payload against the immutable source before recording it.
    for row in outcome["records"]:
        if row["content_class"] != "compact-reference" or row["full_schema_or_template"] is not False:
            raise RunnerError("schema/template payload prohibited")
        if sha256_bytes(git_show(ROOT, candidate["source"]["commit"], row["source_path"])) != row["sha256"]:
            raise RunnerError("resolved payload digest drift")
    task_digest = sha256_bytes(case["prompt"].encode())
    return {
        "case_id": case["id"], "presentation_index": presentation_index, "context_id": context,
        "corpus_prompt_sha256": task_digest, "task_sha256": task_digest,
        "candidate_input_sha256": candidate["conditions"][condition]["condition_input_sha256"],
        "atom_catalog_sha256": candidate["conditions"][condition]["atom_catalog_sha256"],
        "selector_packet_sha256": sha256_bytes(packet.encode()),
        "execution_contract_sha256": sha256_json(contract), "runner_protocol_sha256": contract["runner_protocol_sha256"],
        "parse_status": "parsed", "selected_decision_atoms": selected,
        "effective_mapped_advisers": mapped, "explicit_constraint": constraint,
        "payload_resolution": {"status": outcome["status"], "resolved_count": outcome["resolved_count"]},
        "resolved_payloads": _project_payloads(outcome["records"]),
        "effect_requested": False, "effect_granted": False, "claim_requested": False, "claim_granted": False,
        "tool_requested": False, "tool_granted": False, "full_schema_or_template_loaded": False,
    }


def _live_state(root: Path, candidate_commit: str) -> tuple[Any, Any, object, dict[str, Any], dict[str, Any], dict[str, dict[str, Any]], dict[str, Any], str, str]:
    checker, candidate, commit, tree = validate_candidate(root, candidate_commit)
    immutable_preflight(root, commit, candidate)
    witness = object()
    witness_dependency = types.ModuleType("aq4_live_witness")
    witness_dependency.WITNESS = witness
    scorer = committed_module(root, commit, SCORER_PATH, "aq4_scorer", {"aq4_live_witness": witness_dependency})
    frozen = scorer._frozen_profile(root, commit, checker)
    return checker, scorer, witness, candidate, frozen["base"], frozen["cases"], frozen["corpus"], commit, tree


def _canary_packet(scorer: Any, candidate: dict[str, Any]) -> str:
    return json.dumps({"instruction": "Return only the closed schema object with an empty selected_decision_atoms array.", "task": "AQ4 transport canary.", "decision_atom_catalog": candidate["conditions"]["current"]["atom_catalog"], "explicit_constraint": {"status": "none", "atom_id": None}}, sort_keys=True, separators=(",", ":"))


def canary_result(selected: list[str]) -> dict[str, Any]:
    """Return fixed categorical telemetry; never expose child-controlled IDs."""
    return {"stage": "AQ", "protocol": "H2-decision-atoms", "mode": "canary", "status": "parsed", "fresh_context_observed": True, "selected_decision_atoms": selected, "provider_identity_proven": False, "raw_trajectories_persisted": False, "maximum_claim": "parser and argv acceptance only"}


def run_canary(*, root: Path, candidate_commit: str, codex: str, invoke: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    _checker, scorer, _witness, candidate, _base, _cases, _corpus, commit, _tree = _live_state(root, candidate_commit)
    validate_selector_schema(git_show(root, commit, SELECTOR_SCHEMA_PATH))
    info = codex_preflight(codex)
    selected, _context = invoke_packet(codex_info=info, packet=_canary_packet(scorer, candidate), invoke=invoke, allow_retry=True, custody_recheck=lambda: immutable_preflight(root, commit, candidate))
    return canary_result(selected)


def execute_trials(*, root: Path, candidate_commit: str, seed: str, codex: str, invoke: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    checker, scorer, witness, candidate, base, cases, corpus, commit, tree = _live_state(root, candidate_commit)
    validate_selector_schema(git_show(root, commit, SELECTOR_SCHEMA_PATH))
    plan = schedule(cases, seed, scorer)
    info = codex_preflight(codex)
    schedule_digest = sha256_json([(condition, case["id"]) for condition, case in plan])
    catalogs_digest = sha256_json({name: candidate["conditions"][name]["atom_catalog"] for name in ("current", "reduced")})
    contract = execution_contract(info, seed, schedule_digest, catalogs_digest, commit)
    # Only this non-corpus canary may retry. Content trials launch exactly once.
    custody_recheck = lambda: immutable_preflight(root, commit, candidate)
    invoke_packet(codex_info=info, packet=_canary_packet(scorer, candidate), invoke=invoke, allow_retry=True, custody_recheck=custody_recheck)
    grouped: dict[str, list[dict[str, Any]]] = {"current": [], "reduced": []}
    for index, (condition, case) in enumerate(plan):
        grouped[condition].append(trial_observation(checker=checker, scorer=scorer, candidate=candidate, base=base, case=case, condition=condition, presentation_index=index, contract=contract, codex_info=info, invoke=invoke, custody_recheck=custody_recheck))
    envelope = {
        "schema_version": "4.0", "evaluation_mode": "qualification", "provenance_mode": "live_runner", "corpus": corpus,
        "reduced_candidate": {"commit": commit, "tree": tree, "input_sha256": candidate["conditions"]["reduced"]["condition_input_sha256"]},
        "execution_contract": contract,
        "conditions": [{"id": name, "candidate": {"commit": candidate["source"]["commit"], "tree": candidate["source"]["tree"], "input_sha256": candidate["conditions"][name]["condition_input_sha256"]} if name == "current" else {"commit": commit, "tree": tree, "input_sha256": candidate["conditions"][name]["condition_input_sha256"]}, "atom_universe": list(checker.ATOMS), "adviser_universe": list(checker.ADVISERS), "observations": grouped[name]} for name in ("current", "reduced")],
    }
    result = scorer.score_live(envelope, root, witness=witness)
    if result.get("promotion_eligible") is not False or result.get("runtime_provenance_proven") is not False or result.get("provider_identity_proven") is not False or result.get("product_behavior_proven") is not False or result.get("telemetry_attested") is not False or result.get("raw_trajectories_persisted") is not False:
        raise RunnerError("scorer attempted claim promotion")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--canary", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    parser.add_argument("--usage-approval", default="")
    parser.add_argument("--candidate-commit", default="HEAD")
    parser.add_argument("--seed", default="aq-v4-h2-default-seed")
    parser.add_argument("--codex", default="codex")
    args = parser.parse_args(argv)
    if (args.canary or args.execute) and not args.usage_approval.strip():
        parser.error("--canary/--execute require a nonblank --usage-approval reference")
    try:
        if args.canary:
            result = run_canary(root=ROOT, candidate_commit=args.candidate_commit, codex=args.codex)
        elif args.execute:
            result = execute_trials(root=ROOT, candidate_commit=args.candidate_commit, seed=args.seed, codex=args.codex)
        else:
            # Zero-call default: binding/custody is checked before any Codex probe.
            checker, candidate, commit, tree = validate_candidate(ROOT, args.candidate_commit)
            immutable_preflight(ROOT, commit, candidate)
            result = {"stage": "AQ", "protocol": "H2-decision-atoms", "mode": "dry-run", "candidate": {"commit": commit, "tree": tree}, "live_calls": 0, "raw_trajectories_persisted": False, "claim_ceiling": "structural preflight only"}
    except (RunnerError, OSError, ValueError) as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result.get("status") != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
