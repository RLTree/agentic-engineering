#!/usr/bin/env python3
"""Zero-write deterministic AQ5 H2 scorer with top-level frozen labels.

The live witness is deliberately process-local: it prevents accidental public
entry-point use from being treated as a runner-owned live score.  It is not a
security boundary against hostile same-process Python introspection; no result
from this module establishes runtime, provider, product, or promotion proof.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

try:
    import aq5_live_witness as _live_dependency
except ImportError:
    _LIVE_WITNESS = None
else:
    _LIVE_WITNESS = getattr(_live_dependency, "WITNESS", None)

LIVE_WITNESS_SCOPE = "process_local_accidental_bypass_guard_not_hostile_same_process_security"

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = "scripts/check_reduced_four_skill_candidate_v5.py"
SCHEMA_PATH = "evals/foundation-v4/activation-evaluator-schema-v5.json"
RUNNER_PATH = "scripts/run_activation_trials_v5.py"
MODEL, REASONING = "gpt-5.5", "medium"
SELECTOR_DECISION_CONTRACT = (
    "Select zero, one, or two minimum necessary decision atoms. Admit an atom only for a direct instance of its controlling decision; topical relevance, downstream usefulness, and possible future need are insufficient. "
    "Select two only for two independent direct controlling decisions. Use each positive boundary, admission rule, and complete pairwise exclusions. Ambiguity defaults to none. "
    "When explicit_constraint.status is exact, return exactly that atom; when ambiguous, return none. Bare adviser names do not invoke. Return only the closed schema object and request no tools, effects, approvals, claims, or context."
)


class InputError(ValueError): pass
def sha256_bytes(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def sha256_json(value: Any) -> str: return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())


def git_show(root: Path, commit: str, path: str) -> bytes:
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=root, capture_output=True)
    if result.returncode: raise InputError("immutable input unavailable")
    return result.stdout


def git_tree(root: Path, commit: str) -> str:
    result = subprocess.run(["git", "rev-parse", "--verify", f"{commit}^{{tree}}"], cwd=root, capture_output=True, text=True)
    if result.returncode: raise InputError("candidate tree unavailable")
    return result.stdout.strip()


def _module(root: Path, path: str, name: str, commit: str | None = None) -> Any:
    raw = git_show(root, commit, path) if commit else (root / path).read_bytes()
    if commit and (root / path).read_bytes() != raw: raise InputError("live evaluator module drift")
    module = types.ModuleType(name); module.__file__ = str(root / path)
    previous = sys.modules.get(name)
    try:
        sys.modules[name] = module; exec(compile(raw, module.__file__, "exec"), module.__dict__)
    finally:
        if previous is None: sys.modules.pop(name, None)
        else: sys.modules[name] = previous
    return module


def selector_packet_value(task: str, catalog: list[dict[str, Any]], constraint: dict[str, Any]) -> dict[str, Any]:
    return {"instruction": SELECTOR_DECISION_CONTRACT, "task": task, "decision_atom_catalog": catalog, "explicit_constraint": constraint}
def selector_packet_digest(task: str, catalog: list[dict[str, Any]], constraint: dict[str, Any]) -> str: return sha256_json(selector_packet_value(task, catalog, constraint))


def qualification_schedule(cases: dict[str, dict[str, Any]], seed: str) -> list[tuple[str, str]]:
    if len(cases) != 40 or not isinstance(seed, str) or not seed.strip(): raise InputError("AQ5 schedule input unavailable")
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16)); identifiers = sorted(cases); current, reduced = identifiers[:], identifiers[:]; rng.shuffle(current); rng.shuffle(reduced)
    first = rng.choice(("current", "reduced")); other = "reduced" if first == "current" else "current"
    plan = [item for pair in zip(current, reduced, strict=True) for item in ((first, pair[0]), (other, pair[1]))]
    if len(plan) != 80 or any(plan[index][0] == plan[index + 1][0] for index in range(79)) or sum(condition == "current" for condition, _ in plan) != 40: raise InputError("AQ5 schedule is not exact strict alternation")
    return plan


def condition_parity_digest(execution: dict[str, Any]) -> str: return sha256_json({key: value for key, value in execution.items() if key not in {"condition_parity_sha256", "schedule_seed", "schedule_sha256"}})


def validate_corpus_documents(checker: Any, schema_raw: bytes, authoring_raw: bytes, heldout_raw: bytes, validator_ids: set[str]) -> dict[str, dict[str, Any]]:
    try:
        import jsonschema
        schema, authoring, heldout = json.loads(schema_raw), json.loads(authoring_raw), json.loads(heldout_raw)
        validator = jsonschema.Draft202012Validator(schema)
        if list(validator.iter_errors(authoring)) or list(validator.iter_errors(heldout)): raise InputError("AQ5 frozen corpus schema invalid")
    except ImportError as exc: raise InputError("jsonschema unavailable") from exc
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        if isinstance(exc, InputError): raise
        raise InputError("AQ5 frozen corpus malformed") from exc
    authoring_cases, heldout_cases = checker.validate_document_shape(authoring), checker.validate_document_shape(heldout)
    if any(not case["id"].startswith("AQ5-A-") for case in authoring_cases) or any(not case["id"].startswith("AQ5-H-") for case in heldout_cases): raise InputError("AQ5 frozen corpus split identity mismatch")
    heldout_automatic = [case for case in heldout_cases if case["mode"] == "automatic"]
    explicit = [case for case in [*authoring_cases, *heldout_cases] if case["mode"] == "explicit"]
    if len(authoring_cases) != 36 or len(heldout_cases) != 36 or len(heldout_automatic) != 32 or len(explicit) != 8: raise InputError("AQ5 qualification distribution mismatch")
    selected = [*heldout_automatic, *explicit]; identifiers = [case["id"] for case in selected]
    if len(set(identifiers)) != 40 or set(identifiers) != validator_ids: raise InputError("AQ5 qualification identity mismatch")
    return dict(zip(identifiers, selected, strict=True))


def _validator_result(module: Any, root: Path, commit: str, tree: str) -> set[str]:
    entrypoint = getattr(module, "validate_frozen", None)
    if not callable(entrypoint): raise InputError("AQ5 validator entrypoint unavailable")
    result = entrypoint(root, commit, tree); metrics = getattr(result, "metrics", None); identifiers = getattr(result, "qualified_ids", None)
    if getattr(result, "passed", None) is not True or getattr(result, "errors", None) not in ([], ()) or not isinstance(metrics, dict): raise InputError("AQ5 validator rejected corpus")
    if any(metrics.get(key) != value for key, value in {"automatic_cases": 64, "explicit_cases": 8, "total_cases": 72, "qualified_cases": 40}.items()): raise InputError("AQ5 validator distribution mismatch")
    if not isinstance(identifiers, (list, tuple, set, frozenset)) or len(identifiers) != 40 or len(set(identifiers)) != 40: raise InputError("AQ5 validator IDs invalid")
    return set(identifiers)


def _committed_validator(root: Path, candidate_commit: str, corpus: dict[str, Any]) -> Any:
    if corpus.get("validator_source") != "candidate_commit": raise InputError("AQ5 validator source mismatch")
    raw = git_show(root, candidate_commit, corpus["validator_path"])
    try: live = (root / corpus["validator_path"]).read_bytes()
    except OSError as exc: raise InputError("AQ5 live validator unavailable") from exc
    if live != raw or sha256_bytes(raw) != corpus["validator_sha256"]: raise InputError("AQ5 validator custody mismatch")
    module = types.ModuleType("aq5_bound_corpus_validator"); module.__file__ = str(root / corpus["validator_path"]); previous = sys.modules.get(module.__name__)
    try:
        sys.modules[module.__name__] = module; exec(compile(raw, module.__file__, "exec"), module.__dict__)
    finally:
        if previous is None: sys.modules.pop(module.__name__, None)
        else: sys.modules[module.__name__] = previous
    return module


def frozen_profile(root: Path, candidate_commit: str, checker: Any) -> dict[str, Any]:
    candidate = checker.load_candidate(root, candidate_commit); checker.require_bound(candidate)
    if checker.validate_candidate(candidate, root, candidate_commit): raise InputError("AQ5 candidate invalid")
    base, _ = checker.load_base(root, candidate_commit); corpus = candidate["corpus"]
    validator_ids = _validator_result(_committed_validator(root, candidate_commit, corpus), root, corpus["commit"], corpus["tree"])
    raw: dict[str, bytes] = {}; hashes: dict[str, str] = {}
    for key in ("schema_path", "authoring_path", "heldout_path"):
        value = git_show(root, corpus["commit"], corpus[key])
        if (root / corpus[key]).read_bytes() != value or sha256_bytes(value) != corpus[key.replace("_path", "_sha256")]: raise InputError("AQ5 live frozen corpus drift")
        raw[key] = value; hashes[key.replace("_path", "_sha256")] = sha256_bytes(value)
    cases = validate_corpus_documents(checker, raw["schema_path"], raw["authoring_path"], raw["heldout_path"], validator_ids)
    for case in cases.values(): checker.validate_case_references(case, base)
    return {"candidate": candidate, "base": base, "cases": cases, "corpus": {"source_commit": corpus["commit"], "source_tree": corpus["tree"], "activation_schema_sha256": hashes["schema_sha256"], "authoring_sha256": hashes["authoring_sha256"], "heldout_sha256": hashes["heldout_sha256"], "validator_sha256": corpus["validator_sha256"]}}


def _schema(payload: Any, root: Path, commit: str | None) -> bytes:
    try:
        import jsonschema
        raw = git_show(root, commit, SCHEMA_PATH) if commit else (root / SCHEMA_PATH).read_bytes()
        if commit and (root / SCHEMA_PATH).read_bytes() != raw: raise InputError("AQ5 evaluator schema drift")
        if list(jsonschema.Draft202012Validator(json.loads(raw)).iter_errors(payload)): raise InputError("AQ5 evaluator schema rejected")
        return raw
    except ImportError as exc: raise InputError("jsonschema unavailable") from exc


def _projection(rows: list[dict[str, Any]]) -> list[dict[str, Any]]: return [{key: row[key] for key in ("payload_id", "owner_adviser_id", "source_path", "sha256")} for row in rows]


def validate_payload_resolution(outcome: Any, triggers: list[str]) -> None:
    """Enforce the checker resolver's three closed, non-ambiguous branches."""
    if not isinstance(outcome, dict) or set(outcome) != {"status", "resolved_count", "records"}:
        raise InputError("AQ5 reference resolution shape mismatch")
    status, count, records = outcome["status"], outcome["resolved_count"], outcome["records"]
    if status not in {"resolved", "cap_exceeded", "unresolved"} or not isinstance(count, int) or count < 0 or not isinstance(records, list):
        raise InputError("AQ5 reference resolution branch mismatch")
    if status == "resolved" and not (count == len(records) <= 3): raise InputError("AQ5 resolved payload branch mismatch")
    if status == "cap_exceeded" and not (count > 3 and not records): raise InputError("AQ5 payload cap branch mismatch")
    if status == "unresolved" and not (count == len(records) <= 3): raise InputError("AQ5 unresolved payload branch mismatch")
    if len({row.get("payload_id") for row in records if isinstance(row, dict)}) != len(records): raise InputError("AQ5 resolved payload identity mismatch")
    covered = set().union(*(set(row.get("trigger_ids", [])) for row in records if isinstance(row, dict))) if records else set()
    required = set(triggers)
    if status == "resolved" and covered & required != required: raise InputError("AQ5 resolved payload coverage mismatch")
    if status == "unresolved" and covered & required == required: raise InputError("AQ5 unresolved payload coverage mismatch")


def validate_runner_provenance(root: Path, reduced_commit: str, candidate: dict[str, Any], execution: dict[str, Any]) -> None:
    if execution["runner_path"] != RUNNER_PATH: raise InputError("AQ5 runner path mismatch")
    runner_raw = git_show(root, reduced_commit, RUNNER_PATH)
    try: runner_live = (root / RUNNER_PATH).read_bytes()
    except OSError as exc: raise InputError("AQ5 live runner unavailable") from exc
    manifest_runner = next((row["sha256"] for row in candidate["evaluator_surface"]["files"] if row.get("path") == RUNNER_PATH), None)
    if runner_live != runner_raw or sha256_bytes(runner_raw) != execution["runner_protocol_sha256"] or execution["runner_protocol_sha256"] != manifest_runner: raise InputError("AQ5 runner byte provenance mismatch")


def require_exact_commit(checker: Any, root: Path, commit: str) -> None:
    """Reject tree IDs and movable tree-ish names before any immutable lookup."""
    if checker.resolve_commit(root, commit) != commit: raise InputError("AQ5 reduced candidate must be an exact commit")


def validate(payload: Any, root: Path = ROOT, *, profile: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any], Any, str]:
    if not isinstance(payload, dict): raise InputError("AQ5 evaluator schema rejected")
    if profile is not None and payload.get("provenance_mode") != "synthetic_test": raise InputError("AQ5 injected profile requires synthetic provenance")
    if profile is None and payload.get("provenance_mode") != "live_runner": raise InputError("AQ5 live provenance required")
    reduced_commit, reduced_tree = payload["reduced_candidate"]["commit"], payload["reduced_candidate"]["tree"]
    checker = _module(root, CHECKER_PATH, "aq5_checker", None if profile is not None else reduced_commit)
    if profile is None:
        require_exact_commit(checker, root, reduced_commit)
        if git_tree(root, reduced_commit) != reduced_tree: raise InputError("AQ5 candidate tree mismatch")
        state = frozen_profile(root, reduced_commit, checker)
    else:
        state = profile
        if checker.validate_candidate(state["candidate"], root, allow_unbound=True): raise InputError("AQ5 synthetic candidate invalid")
        if len(state["cases"]) != 40: raise InputError("AQ5 synthetic case count mismatch")
        for case in state["cases"].values():
            checker.validate_case_shape(case)
            checker.validate_case_references(case, state["base"])
    candidate, base, cases = state["candidate"], state["base"], state["cases"]
    schema_raw = _schema(payload, root, None if profile is not None else reduced_commit)
    if payload["corpus"] != state["corpus"]: raise InputError("AQ5 corpus custody mismatch")
    execution = payload["execution_contract"]
    if execution["evaluator_schema_sha256"] != sha256_bytes(schema_raw) or execution["condition_parity_sha256"] != condition_parity_digest(execution): raise InputError("AQ5 execution digest mismatch")
    if profile is None: validate_runner_provenance(root, reduced_commit, candidate, execution)
    elif execution["runner_path"] != RUNNER_PATH: raise InputError("AQ5 runner path mismatch")
    h2_conditions = checker.conditions(candidate, root, None if profile is not None else reduced_commit)
    expected_reduced = {"commit": reduced_commit, "tree": reduced_tree, "input_sha256": h2_conditions["reduced"]["condition_input_sha256"]}
    if payload["reduced_candidate"] != expected_reduced: raise InputError("AQ5 reduced candidate mismatch")
    plan = qualification_schedule(cases, execution["schedule_seed"])
    if execution["schedule_sha256"] != sha256_json(plan): raise InputError("AQ5 schedule digest mismatch")
    execution_digest = sha256_json(execution); contexts: set[str] = set(); indices: set[int] = set()
    if [row["id"] for row in payload["conditions"]] != ["current", "reduced"]: raise InputError("AQ5 condition order mismatch")
    for condition in payload["conditions"]:
        name = condition["id"]; expected = {"commit": candidate["source"]["commit"], "tree": candidate["source"]["tree"], "input_sha256": h2_conditions[name]["condition_input_sha256"]} if name == "current" else expected_reduced
        if condition["candidate"] != expected or len(condition["observations"]) != 40 or {row["case_id"] for row in condition["observations"]} != set(cases): raise InputError("AQ5 condition coverage mismatch")
        catalog = h2_conditions[name]["atom_catalog"]; catalog_digest = sha256_json(catalog)
        for observation in condition["observations"]:
            case = cases[observation["case_id"]]; checker.validate_case_shape(case); checker.validate_case_references(case, base); index = observation["presentation_index"]
            if index in indices or not 0 <= index < 80 or plan[index] != (name, case["id"]): raise InputError("AQ5 presentation mismatch")
            indices.add(index)
            if observation["context_id"] in contexts or not observation["context_id"]: raise InputError("AQ5 context not fresh")
            contexts.add(observation["context_id"]); prompt_digest = sha256_bytes(case["prompt"].encode())
            if observation["task_sha256"] != prompt_digest or observation["corpus_prompt_sha256"] != case["prompt_sha256"]: raise InputError("AQ5 prompt digest mismatch")
            if observation["candidate_input_sha256"] != expected["input_sha256"] or observation["atom_catalog_sha256"] != catalog_digest or observation["execution_contract_sha256"] != execution_digest or observation["runner_protocol_sha256"] != execution["runner_protocol_sha256"]: raise InputError("AQ5 mounted custody mismatch")
            constraint = checker.parse_constraint(case["prompt"])
            if observation["explicit_constraint"] != constraint: raise InputError("AQ5 explicit constraint mismatch")
            atoms = checker.enforce_constraint(observation["selected_decision_atoms"], constraint); mapped = checker.map_atoms(candidate, atoms, root, None if profile is not None else reduced_commit)
            if observation["effective_mapped_advisers"] != mapped: raise InputError("AQ5 atom mapping mismatch")
            outcome = checker.resolve_payloads(base, case["reference_triggers"], mapped)
            validate_payload_resolution(outcome, case["reference_triggers"])
            if observation["payload_resolution"] != {"status": outcome["status"], "resolved_count": outcome["resolved_count"]} or observation["resolved_payloads"] != _projection(outcome["records"]): raise InputError("AQ5 reference resolution mismatch")
            if observation["selector_packet_sha256"] != selector_packet_digest(case["prompt"], catalog, constraint): raise InputError("AQ5 packet digest mismatch")
    if indices != set(range(80)): raise InputError("AQ5 presentation coverage mismatch")
    return payload, {"candidate": candidate, "base": base, "cases": cases}, checker, execution_digest


def _ratio(a: int, b: int) -> float: return a / b if b else 1.0
def score_condition(condition: dict[str, Any], state: dict[str, Any], checker: Any) -> dict[str, Any]:
    rows = {row["case_id"]: row for row in condition["observations"]}; cases, base = state["cases"], state["base"]; tp = fp = fn = native = native_ok = stacking = must_not = explicit = explicit_ok = exactly_two = exactly_two_ok = refs = authority = payload_caps = topology_control = topology_overselect = 0
    for case_id, case in cases.items():
        row = rows[case_id]; want, got = set(case["expected_decision_atoms"]), set(row["selected_decision_atoms"]); tp += len(want & got); fp += len(got - want); fn += len(want - got); must_not += len(set(row["effective_mapped_advisers"]) & set(case["must_not_select"]))
        if not want: native += 1; native_ok += int(not got)
        if len(want) == 1: stacking += int(len(got) > 1)
        if case["mode"] == "explicit": explicit += 1; explicit_ok += int(got == want)
        if case["exactly_two"]: exactly_two += 1; exactly_two_ok += int(got == want)
        if "topology-control-boundary" not in want: topology_control += 1; topology_overselect += int("topology-control-boundary" in got)
        outcome = checker.resolve_payloads(base, case["reference_triggers"], row["effective_mapped_advisers"]); validate_payload_resolution(outcome, case["reference_triggers"]); covered = (set().union(*(set(item["trigger_ids"]) for item in outcome["records"])) if outcome["records"] else set()) & set(case["reference_triggers"]); expected_refs = {(item["payload_id"], checker.ATOM_TO_ADVISER[item["owner_atom"]]) for item in case["deterministic_reference_expectations"]}; actual_refs = {(item["payload_id"], item["owner_adviser_id"]) for item in outcome["records"]}; refs += int(outcome["status"] == "resolved" and covered == set(case["reference_triggers"]) and actual_refs == expected_refs and not row["full_schema_or_template_loaded"]); payload_caps += int(outcome["status"] == "cap_exceeded")
        authority += sum(int(row[key]) for key in ("effect_requested", "effect_granted", "claim_requested", "claim_granted", "tool_requested", "tool_granted"))
    metrics = {"precision": _ratio(tp, tp + fp), "recall": _ratio(tp, tp + fn), "native_abstention_specificity": _ratio(native_ok, native), "topology_control_boundary_overselection_rate": _ratio(topology_overselect, topology_control), "exactly_two_exact_set_compliance": _ratio(exactly_two_ok, exactly_two), "explicit_exact_set_compliance": _ratio(explicit_ok, explicit), "reference_load_correctness": _ratio(refs, len(cases))}
    gates = {"precision": metrics["precision"] >= .95, "recall": metrics["recall"] >= .90, "native_abstention_specificity": metrics["native_abstention_specificity"] >= .95, "topology_control_boundary_overselection_rate": metrics["topology_control_boundary_overselection_rate"] <= .05, "one_decision_stacking": stacking == 0, "exactly_two_exact_set_compliance": metrics["exactly_two_exact_set_compliance"] == 1, "must_not_select": must_not == 0, "explicit_exact_set_compliance": metrics["explicit_exact_set_compliance"] == 1, "payload_cap": payload_caps == 0, "reference_load_correctness": metrics["reference_load_correctness"] == 1, "implicit_authority_or_tool_events": authority == 0}
    return {"id": condition["id"], "candidate": condition["candidate"], "counts": {"true_positive_edges": tp, "false_positive_edges": fp, "false_negative_edges": fn, "native_abstention_total": native, "topology_control_boundary_nonexpected_total": topology_control, "topology_control_boundary_overselections": topology_overselect, "one_decision_stacking_raw_count": stacking, "exactly_two_total": exactly_two, "exactly_two_exact_sets": exactly_two_ok, "must_not_select_violations": must_not, "payload_cap_exceeded": payload_caps, "reference_load_correct": refs, "implicit_authority_or_tool_events": authority}, "metrics": metrics, "gates": gates, "status": "pass" if all(gates.values()) else "fail"}


INSUFFICIENT_KEYS = frozenset(("schema_version", "evaluation_mode", "status", "promotion_eligible", "runtime_provenance_proven", "provider_identity_proven", "product_behavior_proven", "telemetry_attested", "deterministic_input_telemetry_scored", "runner_local_raw_trajectories_persisted", "provider_raw_trajectory_retention_status", "insufficiency_reason", "maximum_claim"))
SCORED_KEYS = frozenset(("schema_version", "evaluation_mode", "status", "promotion_eligible", "runtime_provenance_proven", "provider_identity_proven", "product_behavior_proven", "telemetry_attested", "deterministic_input_telemetry_scored", "score_basis", "corpus", "reduced_candidate", "execution_contract_sha256", "conditions", "runner_local_raw_trajectories_persisted", "provider_raw_trajectory_retention_status", "maximum_claim"))
CONDITION_KEYS = frozenset(("id", "candidate", "counts", "metrics", "gates", "status"))
FALSE_CLAIMS = ("promotion_eligible", "runtime_provenance_proven", "provider_identity_proven", "product_behavior_proven", "telemetry_attested", "runner_local_raw_trajectories_persisted")
COUNT_KEYS = frozenset(("true_positive_edges", "false_positive_edges", "false_negative_edges", "native_abstention_total", "topology_control_boundary_nonexpected_total", "topology_control_boundary_overselections", "one_decision_stacking_raw_count", "exactly_two_total", "exactly_two_exact_sets", "must_not_select_violations", "payload_cap_exceeded", "reference_load_correct", "implicit_authority_or_tool_events"))
METRIC_KEYS = frozenset(("precision", "recall", "native_abstention_specificity", "topology_control_boundary_overselection_rate", "exactly_two_exact_set_compliance", "explicit_exact_set_compliance", "reference_load_correctness"))
GATE_KEYS = frozenset(("precision", "recall", "native_abstention_specificity", "topology_control_boundary_overselection_rate", "one_decision_stacking", "exactly_two_exact_set_compliance", "must_not_select", "explicit_exact_set_compliance", "payload_cap", "reference_load_correctness", "implicit_authority_or_tool_events"))


def validate_result(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict) or result.get("schema_version") != "5.0" or result.get("evaluation_mode") != "qualification": raise InputError("AQ5 result shape mismatch")
    status = result.get("status")
    if status == "insufficient_data":
        if set(result) != INSUFFICIENT_KEYS or result["deterministic_input_telemetry_scored"] is not False or not isinstance(result["insufficiency_reason"], str) or result["maximum_claim"] is not None: raise InputError("AQ5 insufficient result shape mismatch")
    elif status in {"pass", "fail"}:
        if set(result) != SCORED_KEYS or result["deterministic_input_telemetry_scored"] is not True or result["score_basis"] != "supplied_observations" or not isinstance(result["conditions"], list) or len(result["conditions"]) != 2 or result["maximum_claim"] != "unattested deterministic AQ5 decision-atom telemetry from supplied observations": raise InputError("AQ5 scored result shape mismatch")
        for condition in result["conditions"]:
            if not isinstance(condition, dict) or set(condition) != CONDITION_KEYS or condition.get("id") not in {"current", "reduced"} or condition.get("status") not in {"pass", "fail"} or not isinstance(condition.get("candidate"), dict) or set(condition["candidate"]) != {"commit", "tree", "input_sha256"} or set(condition.get("counts", {})) != COUNT_KEYS or set(condition.get("metrics", {})) != METRIC_KEYS or set(condition.get("gates", {})) != GATE_KEYS or any(type(value) is not int or value < 0 for value in condition["counts"].values()) or any(not isinstance(value, float) or not 0 <= value <= 1 for value in condition["metrics"].values()) or any(type(value) is not bool for value in condition["gates"].values()): raise InputError("AQ5 condition result shape mismatch")
    else: raise InputError("AQ5 result status mismatch")
    if any(result.get(key) is not False for key in FALSE_CLAIMS) or result.get("provider_raw_trajectory_retention_status") != "unknown": raise InputError("AQ5 result claim ceiling mismatch")
    return result


def insufficient(reason: str) -> dict[str, Any]: return validate_result({"schema_version": "5.0", "evaluation_mode": "qualification", "status": "insufficient_data", "promotion_eligible": False, "runtime_provenance_proven": False, "provider_identity_proven": False, "product_behavior_proven": False, "telemetry_attested": False, "deterministic_input_telemetry_scored": False, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown", "insufficiency_reason": reason, "maximum_claim": None})
def _score(payload: Any, root: Path, profile: dict[str, Any] | None, *, witness: object | None = None) -> dict[str, Any]:
    if profile is None and (_LIVE_WITNESS is None or witness is not _LIVE_WITNESS): return insufficient("AQ5 live witness mismatch")
    try: payload, state, checker, execution_digest = validate(payload, root, profile=profile); results = [score_condition(row, state, checker) for row in payload["conditions"]]
    except (InputError, ValueError, OSError, KeyError, TypeError) as exc: return insufficient(str(exc) if isinstance(exc, InputError) else "AQ5 custody unavailable")
    passed = all(row["status"] == "pass" for row in results)
    return validate_result({"schema_version": "5.0", "evaluation_mode": "qualification", "status": "pass" if passed else "fail", "promotion_eligible": False, "runtime_provenance_proven": False, "provider_identity_proven": False, "product_behavior_proven": False, "telemetry_attested": False, "deterministic_input_telemetry_scored": True, "score_basis": "supplied_observations", "corpus": payload["corpus"], "reduced_candidate": payload["reduced_candidate"], "execution_contract_sha256": execution_digest, "conditions": results, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown", "maximum_claim": "unattested deterministic AQ5 decision-atom telemetry from supplied observations"})
def score(payload: Any, root: Path = ROOT, *, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(payload, dict) and payload.get("provenance_mode") == "live_runner": return insufficient("AQ5 public scoring rejects live provenance")
    if profile is None: return insufficient("AQ5 public scoring requires synthetic profile")
    return _score(payload, root, profile)
def score_live(payload: Any, root: Path, *, witness: object) -> dict[str, Any]:
    if _LIVE_WITNESS is None or witness is not _LIVE_WITNESS: return insufficient("AQ5 live witness mismatch")
    if not isinstance(payload, dict) or payload.get("provenance_mode") != "live_runner": return insufficient("AQ5 live provenance required")
    return _score(payload, root, None, witness=witness)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--input", type=Path); args = parser.parse_args(argv)
    try: payload = json.loads(args.input.read_text() if args.input else sys.stdin.read()); result = score(payload)
    except (OSError, json.JSONDecodeError): result = insufficient("AQ5 input unavailable")
    print(json.dumps(result, sort_keys=True, separators=(",", ":"))); return {"pass": 0, "fail": 1, "insufficient_data": 2}[result["status"]]
if __name__ == "__main__": raise SystemExit(main())
