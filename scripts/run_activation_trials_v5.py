#!/usr/bin/env python3
"""AQ5 prompt-only H2 runner with pre-launch frozen-case shape custody."""
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
CHECKER_PATH, SCORER_PATH = "scripts/check_reduced_four_skill_candidate_v5.py", "scripts/score_activation_v5.py"
RUNNER_PATH = "scripts/run_activation_trials_v5.py"
SELECTOR_SCHEMA_PATH = "evals/foundation-v4/decision-atom-selector-output-schema.json"
EVALUATOR_SCHEMA_PATH = "evals/foundation-v4/activation-evaluator-schema-v5.json"
MODEL, REASONING = "gpt-5.5", "medium"
DISABLED_FEATURES = ("apply_patch_streaming_events", "apps", "artifact", "auth_elicitation", "browser_use", "browser_use_external", "browser_use_full_cdp_access", "chronicle", "code_mode", "code_mode_buffered_exec", "code_mode_host", "code_mode_only", "computer_use", "default_mode_request_user_input", "enable_mcp_apps", "goals", "guardian_approval", "hooks", "image_generation", "in_app_browser", "memories", "multi_agent", "multi_agent_v2", "plugin_sharing", "plugins", "recommended_plugins", "remote_plugin", "request_permissions_tool", "shell_tool", "skill_mcp_dependency_install", "skill_search", "standalone_web_search", "tool_call_mcp_elicitation", "tool_suggest", "unified_exec", "view_image", "workspace_dependencies")
CONFIG_OVERRIDES = (f'model_reasoning_effort="{REASONING}"', 'web_search="disabled"', "skills.bundled.enabled=false", "skills.include_instructions=false", "include_permissions_instructions=false", "include_apps_instructions=false", "include_collaboration_mode_instructions=false", "include_environment_context=false")


class RunnerError(ValueError): pass
class InfrastructureError(RunnerError): pass
class PreflightError(RunnerError): pass
class LaunchError(RunnerError): pass
class ChildExecutionError(RunnerError): pass
def sha256_bytes(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def sha256_json(value: Any) -> str: return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())
def sha256_file(path: Path) -> str: return sha256_bytes(path.read_bytes())


def git_show(root: Path, commit: str, path: str) -> bytes:
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=root, capture_output=True)
    if result.returncode: raise RunnerError("AQ5 immutable input unavailable")
    return result.stdout
def git_identity(root: Path, commit: str) -> tuple[str, str]:
    resolved = subprocess.run(["git", "rev-parse", "--verify", f"{commit}^{{commit}}"], cwd=root, capture_output=True, text=True)
    if resolved.returncode: raise RunnerError("AQ5 candidate commit unavailable")
    exact = resolved.stdout.strip(); tree = subprocess.run(["git", "rev-parse", "--verify", f"{exact}^{{tree}}"], cwd=root, capture_output=True, text=True)
    if tree.returncode: raise RunnerError("AQ5 candidate tree unavailable")
    return exact, tree.stdout.strip()
def require_live_head_and_clean(root: Path, commit: str, probe: Callable[..., Any] = subprocess.run) -> None:
    candidate = probe(["git", "rev-parse", "--verify", f"{commit}^{{commit}}"], cwd=root, capture_output=True, text=True); head = probe(["git", "rev-parse", "--verify", "HEAD^{commit}"], cwd=root, capture_output=True, text=True); status = probe(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=root, capture_output=True, text=True)
    if candidate.returncode or head.returncode or candidate.stdout.strip() != head.stdout.strip(): raise RunnerError("AQ5 candidate is not live HEAD")
    if status.returncode or status.stdout: raise RunnerError("AQ5 worktree is not clean")


def committed_module(root: Path, commit: str, path: str, name: str, dependencies: dict[str, Any] | None = None) -> Any:
    require_live_head_and_clean(root, commit); raw = git_show(root, commit, path)
    if (root / path).read_bytes() != raw: raise RunnerError("AQ5 live evaluator module drift")
    module = types.ModuleType(name); module.__file__ = str(root / path); previous = {key: sys.modules.get(key) for key in (dependencies or {})}; name_previous = sys.modules.get(name)
    try:
        sys.modules[name] = module
        for key, value in (dependencies or {}).items(): sys.modules[key] = value
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
    finally:
        if name_previous is None: sys.modules.pop(name, None)
        else: sys.modules[name] = name_previous
        for key, value in previous.items():
            if value is None: sys.modules.pop(key, None)
            else: sys.modules[key] = value
    return module


def validate_candidate(root: Path, requested: str) -> tuple[Any, dict[str, Any], str, str]:
    require_live_head_and_clean(root, requested); commit, tree = git_identity(root, requested); checker = committed_module(root, commit, CHECKER_PATH, "aq5_checker_runner"); candidate = checker.load_candidate(root, commit); checker.require_bound(candidate); errors = checker.validate_candidate(candidate, root, commit)
    if errors: raise RunnerError("AQ5 candidate custody failed: " + "; ".join(errors))
    return checker, candidate, commit, tree


def immutable_preflight(root: Path, commit: str, candidate: dict[str, Any]) -> None:
    require_live_head_and_clean(root, commit); corpus = candidate["corpus"]
    corpus_commit, corpus_tree = git_identity(root, corpus["commit"])
    if (corpus_commit, corpus_tree) != (corpus["commit"], corpus["tree"]): raise RunnerError("AQ5 corpus commit/tree drift")
    if corpus["validator_source"] != "candidate_commit": raise RunnerError("AQ5 validator source mismatch")
    for row in candidate["evaluator_surface"]["files"]:
        raw = git_show(root, commit, row["path"])
        if (root / row["path"]).read_bytes() != raw or sha256_bytes(raw) != row["sha256"]: raise RunnerError("AQ5 evaluator byte drift")
    for key in ("schema_path", "authoring_path", "heldout_path"):
        raw = git_show(root, corpus["commit"], corpus[key])
        if (root / corpus[key]).read_bytes() != raw or sha256_bytes(raw) != corpus[key.replace("_path", "_sha256")]: raise RunnerError("AQ5 frozen corpus byte drift")


def validate_selection(value: Any, atoms: tuple[str, ...]) -> list[str]:
    if not isinstance(value, dict) or set(value) != {"selected_decision_atoms"}: raise RunnerError("AQ5 selector output is not closed")
    selected = value["selected_decision_atoms"]
    if not isinstance(selected, list) or len(selected) > 2 or len(selected) != len(set(selected)) or any(item not in atoms for item in selected): raise RunnerError("AQ5 selector output outside atom contract")
    return selected


def parse_events(raw: bytes, atoms: tuple[str, ...]) -> tuple[list[str], str]:
    completed: list[str] = []; thread_id: str | None = None; turn_complete = False
    for line in raw.splitlines():
        try: event = json.loads(line)
        except json.JSONDecodeError as exc: raise InfrastructureError("AQ5 child malformed before completion") from exc
        if not isinstance(event, dict): raise InfrastructureError("AQ5 child event not object")
        event_type = event.get("type")
        if event_type == "thread.started":
            if not isinstance(event.get("thread_id"), str) or not event["thread_id"]: raise InfrastructureError("AQ5 child context unavailable")
            thread_id = event["thread_id"]; continue
        if event_type == "turn.started": continue
        if event_type == "turn.completed": turn_complete = True; continue
        if event_type in {"turn.failed", "error"}: raise RunnerError("AQ5 child failed")
        item = event.get("item")
        if event_type not in {"item.started", "item.updated", "item.completed"} or not isinstance(item, dict): raise RunnerError("AQ5 unrecognized child event")
        item_type = item.get("type")
        if item_type in {"tool_call", "mcp_tool_call", "command_execution", "file_change", "mcp_call", "function_call", "web_search_call", "effect", "approval", "approval_request", "error"}: raise RunnerError("AQ5 prohibited child event")
        if item_type not in {"agent_message", "reasoning"}: raise RunnerError("AQ5 unrecognized child item")
        if event_type == "item.completed" and item_type == "agent_message":
            if not isinstance(item.get("text"), str): raise RunnerError("AQ5 completed output unavailable")
            completed.append(item["text"])
    if not thread_id or not turn_complete or len(completed) != 1: raise InfrastructureError("AQ5 child supplied no single completion")
    try: return validate_selection(json.loads(completed[0]), atoms), thread_id
    except json.JSONDecodeError as exc: raise RunnerError("AQ5 completed output malformed") from exc


def codex_preflight(codex: str, probe: Callable[..., Any] = subprocess.run) -> dict[str, str]:
    resolved = shutil.which(codex) if not Path(codex).is_absolute() else codex
    if not resolved or not Path(resolved).resolve().is_file(): raise RunnerError("AQ5 Codex unavailable")
    executable = Path(resolved).resolve(); version = probe([str(executable), "--version"], capture_output=True, text=True); help_result = probe([str(executable), "exec", "--help"], capture_output=True, text=True); help_text = (help_result.stdout or "") + (help_result.stderr or "")
    if version.returncode or not version.stdout.strip() or help_result.returncode or any(flag not in help_text for flag in ("--ephemeral", "--ignore-user-config", "--strict-config", "--output-schema", "--json", "--sandbox", "--disable")): raise RunnerError("AQ5 Codex capability preflight failed")
    argv = [str(executable), "-c", f'model="{MODEL}"']
    for override in CONFIG_OVERRIDES: argv.extend(["-c", override])
    for feature in DISABLED_FEATURES: argv.extend(["--disable", feature])
    argv.extend(["debug", "prompt-input", "AQ5 local isolation preflight"])
    with tempfile.TemporaryDirectory(prefix="aq5-local-preflight-") as temporary: rendered = probe(argv, cwd=temporary, capture_output=True, text=True)
    try: prompt = json.loads(rendered.stdout)
    except (json.JSONDecodeError, TypeError) as exc: raise RunnerError("AQ5 prompt isolation preflight failed") from exc
    if rendered.returncode or (rendered.stderr or "").strip() or any(marker in json.dumps(prompt, sort_keys=True) for marker in ("<skills_instructions>", "SKILL.md", "<apps_instructions>", "<permissions instructions>", "<collaboration_mode>", "<environment_context>")): raise RunnerError("AQ5 prompt isolation preflight failed")
    return {"path": str(executable), "version": version.stdout.strip(), "sha256": sha256_file(executable)}


def child_argv(codex: str, cwd: str, schema: Path) -> list[str]:
    argv = [codex, "--ask-for-approval", "never", "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config", "--skip-git-repo-check", "--cd", cwd, "--sandbox", "read-only", "--model", MODEL]
    for override in CONFIG_OVERRIDES: argv.extend(["-c", override])
    for feature in DISABLED_FEATURES: argv.extend(["--disable", feature])
    return argv + ["--output-schema", str(schema.resolve()), "--color", "never", "--json", "-"]


def run_one(*, argv_factory: Callable[[], list[str]], packet: str, invoke: Callable[..., Any], before_invoke: Callable[[], None], allow_retry: bool) -> tuple[list[str], str]:
    for attempt in range(2 if allow_retry else 1):
        try:
            before_invoke()
        except (RunnerError, OSError, ValueError) as exc:
            raise PreflightError("AQ5 pre-child custody failed") from exc
        try:
            process = invoke(argv_factory(), input=packet.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        except OSError as exc:
            raise LaunchError("AQ5 child launch failed") from exc
        try:
            raw = process.stdout if isinstance(process.stdout, bytes) else str(process.stdout).encode(); parsed = parse_events(raw, ("topology-control-boundary", "task-contract", "verification-strategy", "engineering-learning"))
            if process.returncode: raise RunnerError("AQ5 child nonzero after completion")
            return parsed
        except InfrastructureError as exc:
            if allow_retry and attempt == 0: continue
            raise ChildExecutionError("AQ5 child failed") from exc
        except (RunnerError, OSError, ValueError) as exc:
            raise ChildExecutionError("AQ5 child failed") from exc
    raise RunnerError("AQ5 unreachable retry")


def invoke_packet(*, info: dict[str, str], packet: str, invoke: Callable[..., Any], custody: Callable[[], None], allow_retry: bool) -> tuple[list[str], str]:
    temporary: list[tempfile.TemporaryDirectory[str]] = []
    def argv_factory() -> list[str]:
        directory = tempfile.TemporaryDirectory(prefix="aq5-prompt-only-"); temporary.append(directory); return child_argv(info["path"], directory.name, ROOT / SELECTOR_SCHEMA_PATH)
    def before() -> None:
        custody()
        if sha256_file(Path(info["path"])) != info["sha256"]: raise RunnerError("AQ5 Codex executable drift")
    try: return run_one(argv_factory=argv_factory, packet=packet, invoke=invoke, before_invoke=before, allow_retry=allow_retry)
    finally:
        for directory in temporary: directory.cleanup()


def packet(scorer: Any, case: dict[str, Any], catalog: list[dict[str, Any]], constraint: dict[str, Any]) -> str:
    value = scorer.selector_packet_value(case["prompt"], catalog, constraint)
    if set(value) != {"instruction", "task", "decision_atom_catalog", "explicit_constraint"}: raise RunnerError("AQ5 packet boundary escaped")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _payload_projection(rows: list[dict[str, Any]]) -> list[dict[str, Any]]: return [{key: row[key] for key in ("payload_id", "owner_adviser_id", "source_path", "sha256")} for row in rows]


def trial_observation(*, checker: Any, scorer: Any, candidate: dict[str, Any], base: dict[str, Any], case: dict[str, Any], condition: str, index: int, contract: dict[str, Any], info: dict[str, str], invoke: Callable[..., Any], custody: Callable[[], None], protocol_commit: str | None = None) -> dict[str, Any]:
    # This check precedes packet construction and therefore every child call.
    checker.validate_case_shape(case); checker.validate_case_references(case, base)
    constraint = checker.parse_constraint(case["prompt"]); h2_conditions = checker.conditions(candidate, ROOT, protocol_commit); catalog = h2_conditions[condition]["atom_catalog"]; serialized = packet(scorer, case, catalog, constraint)
    selected, context = invoke_packet(info=info, packet=serialized, invoke=invoke, custody=custody, allow_retry=False); checker.enforce_constraint(selected, constraint); mapped = checker.map_atoms(candidate, selected, ROOT, protocol_commit)
    outcome = checker.resolve_payloads(base, case["reference_triggers"], mapped)
    scorer.validate_payload_resolution(outcome, case["reference_triggers"])
    for row in outcome["records"]:
        if row["content_class"] != "compact-reference" or row["full_schema_or_template"] is not False or sha256_bytes(git_show(ROOT, candidate["source"]["commit"], row["source_path"])) != row["sha256"]: raise RunnerError("AQ5 resolved payload custody drift")
    prompt_digest = sha256_bytes(case["prompt"].encode())
    return {"case_id": case["id"], "presentation_index": index, "context_id": context, "corpus_prompt_sha256": case["prompt_sha256"], "task_sha256": prompt_digest, "candidate_input_sha256": h2_conditions[condition]["condition_input_sha256"], "atom_catalog_sha256": sha256_json(catalog), "selector_packet_sha256": sha256_bytes(serialized.encode()), "execution_contract_sha256": sha256_json(contract), "runner_protocol_sha256": contract["runner_protocol_sha256"], "parse_status": "parsed", "selected_decision_atoms": selected, "effective_mapped_advisers": mapped, "explicit_constraint": constraint, "payload_resolution": {"status": outcome["status"], "resolved_count": outcome["resolved_count"]}, "resolved_payloads": _payload_projection(outcome["records"]), "effect_requested": False, "effect_granted": False, "claim_requested": False, "claim_granted": False, "tool_requested": False, "tool_granted": False, "full_schema_or_template_loaded": False}


def execution_contract(info: dict[str, str], seed: str, schedule_digest: str, catalog_digest: str, commit: str) -> dict[str, Any]:
    result = {"model": MODEL, "reasoning": REASONING, "cli_path": info["path"], "cli_version": info["version"], "cli_sha256": info["sha256"], "tools_sha256": sha256_json({"permitted": [], "disabled": DISABLED_FEATURES, "sandbox": "read-only", "approval": "never"}), "host_surface_sha256": sha256_json({"cli": info, "empty_temp_cwd": True, "catalogs_sha256": catalog_digest}), "runner_path": RUNNER_PATH, "runner_protocol_sha256": sha256_bytes(git_show(ROOT, commit, RUNNER_PATH)), "schedule_seed": seed, "schedule_sha256": schedule_digest, "evaluator_schema_sha256": sha256_bytes(git_show(ROOT, commit, EVALUATOR_SCHEMA_PATH)), "zero_write": True, "ephemeral_context_requested": True, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown"}
    result["condition_parity_sha256"] = sha256_json({key: value for key, value in result.items() if key not in {"condition_parity_sha256", "schedule_seed", "schedule_sha256"}}); return result


def zero_model_label_preflight(*, root: Path, checker: Any, scorer: Any, candidate: dict[str, Any], base: dict[str, Any], cases: dict[str, dict[str, Any]], corpus: dict[str, Any], commit: str, tree: str, live_witness: object | None = None) -> dict[str, Any]:
    """Exercise the complete label-dependent 40x2 path without a child call."""
    if len(cases) != 40: raise RunnerError("AQ5 zero-model preflight case count mismatch")
    for case in cases.values(): checker.validate_case_shape(case); checker.validate_case_references(case, base)
    seed = "aq5-zero-model-label-preflight"; plan = scorer.qualification_schedule(cases, seed); h2 = checker.conditions(candidate, root, commit)
    contract = {"model": MODEL, "reasoning": REASONING, "cli_path": "<zero-model-preflight>", "cli_version": "zero-model", "cli_sha256": "0" * 64, "tools_sha256": sha256_json({"permitted": []}), "host_surface_sha256": sha256_json({"zero_model": True}), "runner_path": RUNNER_PATH, "runner_protocol_sha256": sha256_bytes((root / RUNNER_PATH).read_bytes()), "schedule_seed": seed, "schedule_sha256": sha256_json(plan), "evaluator_schema_sha256": sha256_bytes((root / EVALUATOR_SCHEMA_PATH).read_bytes()), "zero_write": True, "ephemeral_context_requested": False, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown"}
    contract["condition_parity_sha256"] = scorer.condition_parity_digest(contract); grouped: dict[str, list[dict[str, Any]]] = {"current": [], "reduced": []}
    for index, (condition, case_id) in enumerate(plan):
        case = cases[case_id]; checker.validate_case_shape(case); checker.validate_case_references(case, base); constraint = checker.parse_constraint(case["prompt"]); selected = checker.enforce_constraint(list(case["expected_decision_atoms"]), constraint); mapped = checker.map_atoms(candidate, selected, root, commit)
        if mapped != case["expected_advisers"]: raise RunnerError("AQ5 zero-model expected mapping mismatch")
        outcome = checker.resolve_payloads(base, case["reference_triggers"], mapped); scorer.validate_payload_resolution(outcome, case["reference_triggers"]); projected = _payload_projection(outcome["records"]); expected_payloads = {(row["payload_id"], checker.ATOM_TO_ADVISER[row["owner_atom"]]) for row in case["deterministic_reference_expectations"]}
        if {(row["payload_id"], row["owner_adviser_id"]) for row in projected} != expected_payloads: raise RunnerError("AQ5 zero-model reference expectation mismatch")
        catalog = h2[condition]["atom_catalog"]; packet_value = scorer.selector_packet_value(case["prompt"], catalog, constraint)
        if set(packet_value) != {"instruction", "task", "decision_atom_catalog", "explicit_constraint"}: raise RunnerError("AQ5 zero-model packet exposed labels")
        raw_prompt_sha = sha256_bytes(case["prompt"].encode()); grouped[condition].append({"case_id": case_id, "presentation_index": index, "context_id": f"aq5-zero-model-{index:02d}", "corpus_prompt_sha256": case["prompt_sha256"], "task_sha256": raw_prompt_sha, "candidate_input_sha256": h2[condition]["condition_input_sha256"], "atom_catalog_sha256": sha256_json(catalog), "selector_packet_sha256": scorer.selector_packet_digest(case["prompt"], catalog, constraint), "execution_contract_sha256": sha256_json(contract), "runner_protocol_sha256": contract["runner_protocol_sha256"], "parse_status": "parsed", "selected_decision_atoms": selected, "effective_mapped_advisers": mapped, "explicit_constraint": constraint, "payload_resolution": {"status": outcome["status"], "resolved_count": outcome["resolved_count"]}, "resolved_payloads": projected, "effect_requested": False, "effect_granted": False, "claim_requested": False, "claim_granted": False, "tool_requested": False, "tool_granted": False, "full_schema_or_template_loaded": False})
    reduced = {"commit": commit, "tree": tree, "input_sha256": h2["reduced"]["condition_input_sha256"]}; envelope = {"schema_version": "5.0", "evaluation_mode": "qualification", "provenance_mode": "live_runner" if live_witness is not None else "synthetic_test", "corpus": corpus, "reduced_candidate": reduced, "execution_contract": contract, "conditions": [{"id": name, "candidate": {"commit": candidate["source"]["commit"], "tree": candidate["source"]["tree"], "input_sha256": h2[name]["condition_input_sha256"]} if name == "current" else reduced, "atom_universe": list(checker.ATOMS), "adviser_universe": list(checker.ADVISERS), "observations": grouped[name]} for name in ("current", "reduced")]}; profile = {"candidate": candidate, "base": base, "cases": cases, "corpus": corpus}; result = scorer.score_live(envelope, root, witness=live_witness) if live_witness is not None else scorer.score(envelope, root, profile=profile)
    if result.get("status") != "pass" or any(result.get(key) is not False for key in ("promotion_eligible", "runtime_provenance_proven", "provider_identity_proven", "product_behavior_proven", "telemetry_attested", "runner_local_raw_trajectories_persisted")) or result.get("provider_raw_trajectory_retention_status") != "unknown": raise RunnerError("AQ5 zero-model scorer preflight failed")
    return {"status": "pass", "qualification_cases": 40, "presentations": 80, "live_calls": 0, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown"}


def live_state(root: Path, requested: str) -> tuple[Any, Any, object, dict[str, Any], dict[str, Any], dict[str, dict[str, Any]], dict[str, Any], str, str]:
    checker, candidate, commit, tree = validate_candidate(root, requested); immutable_preflight(root, commit, candidate); witness = object(); dependency = types.ModuleType("aq5_live_witness"); dependency.WITNESS = witness; scorer = committed_module(root, commit, SCORER_PATH, "aq5_scorer_runner", {"aq5_live_witness": dependency}); frozen = scorer.frozen_profile(root, commit, checker); zero_model_label_preflight(root=root, checker=checker, scorer=scorer, candidate=candidate, base=frozen["base"], cases=frozen["cases"], corpus=frozen["corpus"], commit=commit, tree=tree, live_witness=witness)
    return checker, scorer, witness, candidate, frozen["base"], frozen["cases"], frozen["corpus"], commit, tree


def canary_result(selected: list[str], *, context_id_received: bool) -> dict[str, Any]: return {"stage": "AQ", "protocol": "AQ5-H2", "mode": "canary", "status": "parsed", "ephemeral_context_requested": True, "context_id_received": context_id_received, "selected_decision_atoms": selected, "provider_identity_proven": False, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown", "maximum_claim": "parser and argv acceptance only"}
def _canary(scorer: Any, candidate: dict[str, Any], checker: Any, commit: str) -> str: return json.dumps({"instruction": "Return only the closed schema object with an empty selected_decision_atoms array.", "task": "AQ5 transport canary.", "decision_atom_catalog": checker.conditions(candidate, ROOT, commit)["current"]["atom_catalog"], "explicit_constraint": {"status": "none", "atom_id": None}}, sort_keys=True, separators=(",", ":"))


def require_live_score(result: Any) -> dict[str, Any]:
    required = {"schema_version", "evaluation_mode", "status", "promotion_eligible", "runtime_provenance_proven", "provider_identity_proven", "product_behavior_proven", "telemetry_attested", "deterministic_input_telemetry_scored", "score_basis", "corpus", "reduced_candidate", "execution_contract_sha256", "conditions", "runner_local_raw_trajectories_persisted", "provider_raw_trajectory_retention_status", "maximum_claim"}
    if not isinstance(result, dict) or set(result) != required or result.get("schema_version") != "5.0" or result.get("evaluation_mode") != "qualification" or result.get("status") not in {"pass", "fail"} or result.get("deterministic_input_telemetry_scored") is not True or result.get("score_basis") != "supplied_observations" or not isinstance(result.get("corpus"), dict) or not isinstance(result.get("reduced_candidate"), dict) or not isinstance(result.get("execution_contract_sha256"), str) or not isinstance(result.get("conditions"), list) or len(result["conditions"]) != 2 or not isinstance(result.get("maximum_claim"), str): raise ChildExecutionError("AQ5 live score unavailable")
    condition_keys = {"id", "candidate", "counts", "metrics", "gates", "status"}
    count_keys = {"true_positive_edges", "false_positive_edges", "false_negative_edges", "native_abstention_total", "topology_control_boundary_nonexpected_total", "topology_control_boundary_overselections", "one_decision_stacking_raw_count", "exactly_two_total", "exactly_two_exact_sets", "must_not_select_violations", "payload_cap_exceeded", "reference_load_correct", "implicit_authority_or_tool_events"}
    metric_keys = {"precision", "recall", "native_abstention_specificity", "topology_control_boundary_overselection_rate", "exactly_two_exact_set_compliance", "explicit_exact_set_compliance", "reference_load_correctness"}
    gate_keys = {"precision", "recall", "native_abstention_specificity", "topology_control_boundary_overselection_rate", "one_decision_stacking", "exactly_two_exact_set_compliance", "must_not_select", "explicit_exact_set_compliance", "payload_cap", "reference_load_correctness", "implicit_authority_or_tool_events"}
    if any(not isinstance(row, dict) or set(row) != condition_keys or row.get("id") not in {"current", "reduced"} or row.get("status") not in {"pass", "fail"} or not isinstance(row.get("candidate"), dict) or set(row["candidate"]) != {"commit", "tree", "input_sha256"} or set(row.get("counts", {})) != count_keys or set(row.get("metrics", {})) != metric_keys or set(row.get("gates", {})) != gate_keys or any(type(value) is not int or value < 0 for value in row["counts"].values()) or any(not isinstance(value, float) or not 0 <= value <= 1 for value in row["metrics"].values()) or any(type(value) is not bool for value in row["gates"].values()) for row in result["conditions"]): raise ChildExecutionError("AQ5 live score unavailable")
    if any(result.get(key) is not False for key in ("promotion_eligible", "runtime_provenance_proven", "provider_identity_proven", "product_behavior_proven", "telemetry_attested", "runner_local_raw_trajectories_persisted")) or result.get("provider_raw_trajectory_retention_status") != "unknown": raise ChildExecutionError("AQ5 scorer attempted claim promotion")
    return result


def run_canary(*, root: Path, candidate_commit: str, codex: str, invoke: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    checker, scorer, _witness, candidate, _base, _cases, _corpus, commit, _tree = live_state(root, candidate_commit); info = codex_preflight(codex); selected, context_id = invoke_packet(info=info, packet=_canary(scorer, candidate, checker, commit), invoke=invoke, custody=lambda: immutable_preflight(root, commit, candidate), allow_retry=True); return canary_result(selected, context_id_received=bool(context_id))


def execute_trials(*, root: Path, candidate_commit: str, seed: str, codex: str, invoke: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    checker, scorer, witness, candidate, base, cases, corpus, commit, tree = live_state(root, candidate_commit); plan = scorer.qualification_schedule(cases, seed); info = codex_preflight(codex); h2 = checker.conditions(candidate, root, commit); contract = execution_contract(info, seed, sha256_json([(condition, case_id) for condition, case_id in plan]), sha256_json(h2), commit); custody = lambda: immutable_preflight(root, commit, candidate); invoke_packet(info=info, packet=_canary(scorer, candidate, checker, commit), invoke=invoke, custody=custody, allow_retry=True); grouped = {"current": [], "reduced": []}
    for index, (condition, case_id) in enumerate(plan): grouped[condition].append(trial_observation(checker=checker, scorer=scorer, candidate=candidate, base=base, case=cases[case_id], condition=condition, index=index, contract=contract, info=info, invoke=invoke, custody=custody, protocol_commit=commit))
    reduced = {"commit": commit, "tree": tree, "input_sha256": h2["reduced"]["condition_input_sha256"]}; envelope = {"schema_version": "5.0", "evaluation_mode": "qualification", "provenance_mode": "live_runner", "corpus": corpus, "reduced_candidate": reduced, "execution_contract": contract, "conditions": [{"id": name, "candidate": {"commit": candidate["source"]["commit"], "tree": candidate["source"]["tree"], "input_sha256": h2[name]["condition_input_sha256"]} if name == "current" else reduced, "atom_universe": list(checker.ATOMS), "adviser_universe": list(checker.ADVISERS), "observations": grouped[name]} for name in ("current", "reduced")]}; return require_live_score(scorer.score_live(envelope, root, witness=witness))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); modes = parser.add_mutually_exclusive_group(); modes.add_argument("--canary", action="store_true"); modes.add_argument("--execute", action="store_true"); modes.add_argument("--dry-run", action="store_true"); parser.add_argument("--usage-approval", default=""); parser.add_argument("--candidate-commit", default="HEAD"); parser.add_argument("--seed", default="aq5-h2-default-seed"); parser.add_argument("--codex", default="codex"); args = parser.parse_args(argv)
    if (args.canary or args.execute) and not args.usage_approval.strip(): parser.error("live mode requires --usage-approval")
    try:
        if args.canary: result = run_canary(root=ROOT, candidate_commit=args.candidate_commit, codex=args.codex)
        elif args.execute: result = execute_trials(root=ROOT, candidate_commit=args.candidate_commit, seed=args.seed, codex=args.codex)
        else:
            _checker, candidate, commit, tree = validate_candidate(ROOT, args.candidate_commit); immutable_preflight(ROOT, commit, candidate); result = {"stage": "AQ", "protocol": "AQ5-H2", "mode": "dry-run", "candidate": {"commit": commit, "tree": tree}, "live_calls": 0, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown", "claim_ceiling": "structural preflight only"}
    except LaunchError:
        print(json.dumps({"stage": "AQ", "protocol": "AQ5-H2", "status": "launch_failed", "failed_child_started": False, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown", "maximum_claim": None}, sort_keys=True, separators=(",", ":"))); return 2
    except ChildExecutionError:
        print(json.dumps({"stage": "AQ", "protocol": "AQ5-H2", "status": "child_failed", "failed_child_started": True, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown", "maximum_claim": None}, sort_keys=True, separators=(",", ":"))); return 2
    except (RunnerError, OSError, ValueError):
        print(json.dumps({"stage": "AQ", "protocol": "AQ5-H2", "status": "runner_failed", "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown", "maximum_claim": None}, sort_keys=True, separators=(",", ":"))); return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":"))); return 1 if result.get("status") == "fail" else 0
if __name__ == "__main__": raise SystemExit(main())
