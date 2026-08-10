#!/usr/bin/env python3
"""Closed AQ8 aggregate scorer for supplied in-memory H4 observations only."""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping

from aq_run_index_v8 import RunIndexError, normalize_binding
from resolve_h4_unresolved_decision_graph_v8 import (
    build_condition_packet,
    canonical_json,
    resolve_graph,
    validate_graph_output,
)

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "evals/foundation-v4/activation-evaluator-schema-v8.json"
GATE_AUTHORITY_PATH = "evals/foundation-v4/unresolved-decision-graph-gates-v8.json"
METRIC_AUTHORITY_PATH = "evals/foundation-v4/unresolved-decision-graph-metrics-v8.json"
SCHEDULE_SEED = "aq8-h4-v1"
MODEL = "gpt-5.5"
REASONING = "medium"
CLAIM = "unattested deterministic AQ8 unresolved-decision graph telemetry from supplied observations"
CONDITIONS = ("current", "reduced")
EVENT_KEYS = (
    "effect_requested", "effect_granted", "claim_requested",
    "claim_granted", "tool_requested", "tool_granted",
)

PER_CONDITION_GATES = (
    "graph_validity", "candidate_state_accuracy", "directed_control_precision",
    "directed_control_recall", "independent_relation_accuracy", "exact_root_set",
    "uncertainty_abstention", "cap_abstention", "precision", "recall",
    "native_abstention", "broad_router_over_selection", "one_decision_stacking",
    "exactly_two_exact_set", "explicit_invocation", "must_not_select",
    "unselected_need_violations", "reference_correctness", "payload_cap_violations",
    "implicit_effect_claim_tool_events",
)
COMPLETE_RUN_GATES = (
    "semantic_schema_order", "resolver_parity", "presentations_80_of_80",
    "unique_context_ids", "binding_schedule_packet_parity",
    "runner_local_raw_persistence", "held_out_outcome_use",
)
FORMULA_ORDER = (*PER_CONDITION_GATES, *COMPLETE_RUN_GATES)

# Every comparison is exact. Ratio boundaries are Fractions, count boundaries
# are integers, and boolean boundaries are exact bools.
_SPECS: dict[str, tuple[str, str, Fraction | int | bool]] = {
    "graph_validity": ("ratio", "==", Fraction(1, 1)),
    "candidate_state_accuracy": ("ratio", ">=", Fraction(19, 20)),
    "directed_control_precision": ("ratio", ">=", Fraction(19, 20)),
    "directed_control_recall": ("ratio", ">=", Fraction(9, 10)),
    "independent_relation_accuracy": ("ratio", ">=", Fraction(19, 20)),
    "exact_root_set": ("ratio", ">=", Fraction(19, 20)),
    "uncertainty_abstention": ("ratio", ">=", Fraction(19, 20)),
    "cap_abstention": ("ratio", "==", Fraction(1, 1)),
    "precision": ("ratio", ">=", Fraction(19, 20)),
    "recall": ("ratio", ">=", Fraction(9, 10)),
    "native_abstention": ("ratio", ">=", Fraction(19, 20)),
    "broad_router_over_selection": ("ratio", "<=", Fraction(1, 20)),
    "one_decision_stacking": ("count", "==", 0),
    "exactly_two_exact_set": ("ratio", "==", Fraction(1, 1)),
    "explicit_invocation": ("ratio", "==", Fraction(1, 1)),
    "must_not_select": ("count", "==", 0),
    "unselected_need_violations": ("count", "==", 0),
    "reference_correctness": ("ratio", "==", Fraction(1, 1)),
    "payload_cap_violations": ("count", "==", 0),
    "implicit_effect_claim_tool_events": ("count", "==", 0),
    "semantic_schema_order": ("ratio", "==", Fraction(1, 1)),
    "resolver_parity": ("ratio", "==", Fraction(1, 1)),
    "presentations_80_of_80": ("count", "==", 80),
    "unique_context_ids": ("count", "==", 80),
    "binding_schedule_packet_parity": ("ratio", "==", Fraction(1, 1)),
    "runner_local_raw_persistence": ("boolean", "==", False),
    "held_out_outcome_use": ("boolean", "==", False),
}

# Denominators determined by the frozen forty-case qualification profile are
# part of the aggregate contract, not caller-selectable ratio inputs.  Only
# precision denominators depend on the candidate's predicted positive set.
_BOUND_CONDITION_DENOMINATORS = {
    "graph_validity": 40,
    "candidate_state_accuracy": 160,
    "directed_control_recall": 36,
    "independent_relation_accuracy": 240,
    "exact_root_set": 38,
    "uncertainty_abstention": 2,
    "cap_abstention": 2,
    "recall": 40,
    "native_abstention": 2,
    "broad_router_over_selection": 24,
    "exactly_two_exact_set": 6,
    "explicit_invocation": 8,
    "reference_correctness": 40,
}
_VARIABLE_CONDITION_DENOMINATOR_MAXIMA = {
    "directed_control_precision": 240,
    "precision": 80,
}
_BOUND_COMPLETE_DENOMINATORS = {
    "semantic_schema_order": 80,
    "resolver_parity": 80,
    "binding_schedule_packet_parity": 80,
}


class EvaluationError(ValueError):
    """The supplied value is outside AQ8's closed qualification contract."""


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _bytes(value: Any) -> bytes:
    try:
        raw = canonical_json(value)
    except Exception:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return raw.encode("utf-8") if isinstance(raw, str) else bytes(raw)


def _digest(value: Any) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


def _hex(value: Any, length: int = 64) -> bool:
    return isinstance(value, str) and len(value) == length and all(char in "0123456789abcdef" for char in value)


def build_schedule(qualified_case_ids: Any, seed: str) -> tuple[dict[str, Any], ...]:
    """Build the sole deterministic, alternating 80-presentation AQ8 schedule."""
    if not isinstance(seed, str) or not seed:
        raise EvaluationError("AQ8 schedule seed unavailable")
    if not isinstance(qualified_case_ids, (tuple, list)) or len(qualified_case_ids) != 40:
        raise EvaluationError("AQ8 requires exactly forty qualified cases")
    identifiers = tuple(qualified_case_ids)
    if any(not isinstance(case_id, str) or not case_id for case_id in identifiers) or len(set(identifiers)) != 40:
        raise EvaluationError("AQ8 qualified case IDs invalid")
    rng = random.Random(int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16))
    current, reduced = list(sorted(identifiers)), list(sorted(identifiers))
    rng.shuffle(current)
    rng.shuffle(reduced)
    first = "current" if rng.randrange(2) == 0 else "reduced"
    second = "reduced" if first == "current" else "current"
    rows: list[dict[str, Any]] = []
    for current_id, reduced_id in zip(current, reduced, strict=True):
        rows.append({"presentation_index": len(rows), "condition": first, "case_id": current_id if first == "current" else reduced_id})
        rows.append({"presentation_index": len(rows), "condition": second, "case_id": reduced_id if second == "reduced" else current_id})
    return tuple(rows)


def schedule_digest(schedule: Any) -> str:
    if not isinstance(schedule, (tuple, list)):
        raise EvaluationError("AQ8 schedule unavailable")
    return _digest(list(schedule))


def _schema_validate(value: Any) -> None:
    try:
        import jsonschema
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(value))
    except (OSError, json.JSONDecodeError, ImportError) as error:
        raise EvaluationError("AQ8 evaluator schema unavailable") from error
    if errors:
        raise EvaluationError("AQ8 evaluator schema rejected envelope")


def _task(case: Mapping[str, Any]) -> str:
    value = case.get("task_text")
    if not isinstance(value, str):
        raise EvaluationError("AQ8 profile task unavailable")
    return value


def _case_map(profile: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    qualified = profile.get("qualified_cases")
    if not isinstance(qualified, (tuple, list)) or any(not isinstance(item, str) for item in qualified):
        raise EvaluationError("AQ8 qualified cases unavailable")
    all_cases: dict[str, Mapping[str, Any]] = {}
    for document in (profile.get("authoring"), profile.get("heldout")):
        if not isinstance(document, Mapping) or not isinstance(document.get("cases"), list):
            raise EvaluationError("AQ8 corpus profile unavailable")
        for case in document["cases"]:
            if not isinstance(case, Mapping) or not isinstance(case.get("case_id"), str) or case["case_id"] in all_cases:
                raise EvaluationError("AQ8 corpus profile invalid")
            all_cases[case["case_id"]] = case
    result = {case_id: all_cases[case_id] for case_id in qualified if case_id in all_cases}
    if len(result) != 40 or len(result) != len(qualified) or tuple(profile.get("qualified_ids", ())) != tuple(result):
        raise EvaluationError("AQ8 qualification set unavailable")
    return result


def _expected_case_digest(case: Mapping[str, Any], kind: str) -> str:
    task_digest = hashlib.sha256(_task(case).encode("utf-8")).hexdigest()
    if case.get("task_text_nfc_sha256") != task_digest:
        raise EvaluationError("AQ8 frozen task bytes drift")
    if kind not in {"case", "task"}:
        raise EvaluationError("AQ8 case digest kind invalid")
    # The frozen AQ8 case projection is task_text only, so both custody fields
    # deliberately bind the exact same NFC task bytes.
    return task_digest


def _packet_digest(profile: Mapping[str, Any], condition: str, case: Mapping[str, Any]) -> str:
    try:
        packet = build_condition_packet(profile["adapter"], condition, _task(case))
    except Exception as error:
        raise EvaluationError("AQ8 condition packet unavailable") from error
    if tuple(packet) != ("instruction", "task_text", "slot_order", "pair_order", "condition_guidance", "support_legend"):
        raise EvaluationError("AQ8 condition packet closure invalid")
    return _digest(packet)


def _profile_execution_digest(profile: Mapping[str, Any]) -> str:
    contract = profile.get("execution_contract")
    if not isinstance(contract, Mapping):
        raise EvaluationError("AQ8 execution contract unavailable")
    return _digest(contract)


def _condition_digest(profile: Mapping[str, Any], condition: str) -> str:
    adapter = profile.get("adapter")
    conditions = adapter.get("conditions") if isinstance(adapter, Mapping) else None
    row = conditions.get(condition) if isinstance(conditions, Mapping) else None
    digest = row.get("condition_guidance_canonical_sha256") if isinstance(row, Mapping) else None
    guidance = row.get("condition_guidance") if isinstance(row, Mapping) else None
    if not _hex(digest) or _digest(guidance) != digest:
        raise EvaluationError("AQ8 condition adapter digest invalid")
    contract_rows = profile.get("execution_contract", {}).get("conditions")
    expected = next((item for item in contract_rows if isinstance(item, Mapping) and item.get("id") == condition), None) if isinstance(contract_rows, list) else None
    if not isinstance(expected, Mapping) or expected.get("condition_guidance_canonical_sha256") != digest:
        raise EvaluationError("AQ8 condition execution parity unavailable")
    return digest


def _identity(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise EvaluationError("AQ8 authority binding unavailable")
    result = {"commit": value.get("commit"), "tree": value.get("tree"), "digest": value.get("digest", value.get("sha256"))}
    if not _hex(result["commit"], 40) or not _hex(result["tree"], 40) or not _hex(result["digest"]):
        raise EvaluationError("AQ8 authority binding invalid")
    return result


def _profile_binding_identities(profile: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    manifest = profile.get("manifest")
    if not isinstance(manifest, Mapping):
        raise EvaluationError("AQ8 candidate manifest unavailable")
    candidate = {"commit": profile.get("candidate_commit"), "tree": profile.get("tree"), "digest": profile.get("digest")}
    expected = {
        "protocol": _identity(manifest.get("protocol_authority")),
        "reference_policy": _identity(manifest.get("reference_policy_authority")),
        "corpus": _identity(manifest.get("corpus_authority")),
        "candidate": candidate,
        "validator": _identity(manifest.get("validator_authority")),
    }
    rows = manifest.get("evaluator_surface", {}).get("files") if isinstance(manifest.get("evaluator_surface"), Mapping) else None
    if not isinstance(rows, list):
        raise EvaluationError("AQ8 evaluator surface unavailable")
    by_role = {row.get("role"): row for row in rows if isinstance(row, Mapping)}
    for name, role in (("runner", "runner"), ("evaluator", "scorer")):
        row = by_role.get(role)
        expected[name] = {"commit": candidate["commit"], "tree": candidate["tree"], "digest": row.get("sha256") if isinstance(row, Mapping) else None}
    if any(not _hex(item.get("commit"), 40) or not _hex(item.get("tree"), 40) or not _hex(item.get("digest")) for item in expected.values()):
        raise EvaluationError("AQ8 candidate identity invalid")
    return expected


def _gate_rows(gates: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    primary = gates.get("ordered_primary_diagnostics")
    later = gates.get("later_noncompensatory_gates")
    complete = gates.get("evaluator_integrity_gates")
    if isinstance(primary, list):
        rows.extend(item for item in primary if isinstance(item, Mapping))
    if isinstance(later, Mapping):
        for group in later.get("group_order", ()):
            value = later.get(group)
            if isinstance(value, list):
                rows.extend(item for item in value if isinstance(item, Mapping))
    if isinstance(complete, list):
        rows.extend(item for item in complete if isinstance(item, Mapping))
    return rows


def _boundary(value: Any, kind: str) -> Fraction | int | bool:
    if kind == "boolean":
        if type(value) is not bool:
            raise EvaluationError("AQ8 boolean boundary invalid")
        return value
    if kind == "count":
        if type(value) is not int:
            raise EvaluationError("AQ8 count boundary invalid")
        return value
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError) as error:
        raise EvaluationError("AQ8 ratio boundary invalid") from error


def _type_strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_type_strict_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_type_strict_equal(a, b) for a, b in zip(left, right, strict=True))
    return bool(left == right)


def _load_bound_authority(manifest: Mapping[str, Any], name: str, expected_path: str) -> dict[str, Any]:
    binding = manifest.get(name)
    if not isinstance(binding, Mapping) or binding.get("path") != expected_path or not _hex(binding.get("sha256")):
        raise EvaluationError("AQ8 local authority binding invalid")
    try:
        raw = (ROOT / expected_path).read_bytes()
    except OSError as error:
        raise EvaluationError("AQ8 local authority bytes unavailable") from error
    if hashlib.sha256(raw).hexdigest() != binding["sha256"]:
        raise EvaluationError("AQ8 local authority digest invalid")
    try:
        authority = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvaluationError("AQ8 local authority JSON invalid") from error
    if not isinstance(authority, dict):
        raise EvaluationError("AQ8 local authority root invalid")
    return authority


def _authority_contract(profile: Mapping[str, Any]) -> str:
    """Verify all 27 frozen formulas and their candidate/profile bindings."""
    manifest = profile.get("manifest")
    metrics = profile.get("metric_authority")
    gates = profile.get("gate_authority")
    execution = profile.get("execution_contract")
    if not all(isinstance(item, Mapping) for item in (manifest, metrics, gates, execution)):
        raise EvaluationError("AQ8 formula authorities unavailable")
    bound_metrics = _load_bound_authority(manifest, "metric_authority", METRIC_AUTHORITY_PATH)
    bound_gates = _load_bound_authority(manifest, "gate_authority", GATE_AUTHORITY_PATH)
    if not _type_strict_equal(metrics, bound_metrics) or not _type_strict_equal(gates, bound_gates):
        raise EvaluationError("AQ8 formula authority bytes drift")
    formulas = metrics.get("gate_formulas")
    if metrics.get("formula_order") != list(FORMULA_ORDER) or not isinstance(formulas, list) or len(formulas) != len(FORMULA_ORDER):
        raise EvaluationError("AQ8 formula order invalid")
    metric_by_id = {row.get("gate_id"): row for row in formulas if isinstance(row, Mapping)}
    gate_by_id = {row.get("gate_id"): row for row in _gate_rows(gates)}
    if set(metric_by_id) != set(FORMULA_ORDER) or set(gate_by_id) != set(FORMULA_ORDER):
        raise EvaluationError("AQ8 formula coverage invalid")
    for gate_id in FORMULA_ORDER:
        kind, operator, expected_boundary = _SPECS[gate_id]
        expected_scope = "per_condition" if gate_id in PER_CONDITION_GATES else "complete_run"
        for row in (metric_by_id[gate_id], gate_by_id[gate_id]):
            if row.get("scope") != expected_scope or row.get("operator") != operator or row.get("noncompensatory") is not True:
                raise EvaluationError("AQ8 formula semantics invalid")
            if _boundary(row.get("boundary"), kind) != expected_boundary:
                raise EvaluationError("AQ8 formula boundary invalid")
    authorities = execution.get("authorities")
    if not isinstance(authorities, Mapping):
        raise EvaluationError("AQ8 execution authority projection unavailable")
    h4 = _identity(manifest.get("h4_authority"))
    gate = _identity(manifest.get("gate_authority"))
    metric = _identity(manifest.get("metric_authority"))
    expected_execution = {
        "h4_commit": h4["commit"], "h4_tree": h4["tree"], "h4_sha256": h4["digest"],
        "gate_commit": gate["commit"], "gate_tree": gate["tree"], "gate_sha256": gate["digest"],
        "metric_commit": metric["commit"], "metric_tree": metric["tree"], "metric_sha256": metric["digest"],
        "semantic_selector_schema_sha256": _identity(manifest.get("selector_schema_authority"))["digest"],
        "runtime_selector_schema_sha256": _identity(manifest.get("runtime_selector_schema_authority"))["digest"],
    }
    if dict(authorities) != expected_execution:
        raise EvaluationError("AQ8 execution authority projection drift")
    bindings = metrics.get("authority_bindings")
    if not isinstance(bindings, Mapping):
        raise EvaluationError("AQ8 formula lineage unavailable")
    h4_binding, gate_binding = bindings.get("h4"), bindings.get("gates")
    if not isinstance(h4_binding, Mapping) or not isinstance(gate_binding, Mapping):
        raise EvaluationError("AQ8 formula lineage unavailable")
    if (h4_binding.get("commit"), h4_binding.get("tree"), h4_binding.get("raw_sha256")) != (h4["commit"], h4["tree"], h4["digest"]):
        raise EvaluationError("AQ8 H4 formula lineage drift")
    if (gate_binding.get("commit"), gate_binding.get("tree"), gate_binding.get("raw_sha256")) != (gate["commit"], gate["tree"], gate["digest"]):
        raise EvaluationError("AQ8 gate formula lineage drift")
    return metric["digest"]


def _expected_oracles(cases: Mapping[str, Mapping[str, Any]], profile: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for case_id, case in cases.items():
        semantic = case.get("expected_semantic_output")
        parent = case.get("expected_parent_derivation")
        if not isinstance(semantic, Mapping) or not isinstance(parent, Mapping):
            raise EvaluationError("AQ8 evaluator oracle unavailable")
        try:
            validated = _plain(validate_graph_output(semantic, profile["protocol"], profile["selector_schema"]))
            derived = _plain(resolve_graph(_task(case), validated, profile["protocol"], profile["reference_policy"], profile["base_manifest"]))
        except Exception as error:
            raise EvaluationError("AQ8 evaluator oracle cannot be recomputed") from error
        if _plain(semantic) != validated or _plain(parent) != derived:
            raise EvaluationError("AQ8 evaluator oracle parity invalid")
        result[case_id] = {"semantic": validated, "parent": derived}
    return result


def _row_custody(
    row: Mapping[str, Any], condition: str, case: Mapping[str, Any],
    profile: Mapping[str, Any], condition_digest: str, execution_digest: str,
    runner_digest: str,
) -> bool:
    try:
        return bool(
            row.get("terminal_completed") is True
            and row.get("case_sha256") == _expected_case_digest(case, "case")
            and row.get("task_sha256") == _expected_case_digest(case, "task")
            and row.get("packet_sha256") == _packet_digest(profile, condition, case)
            and row.get("condition_sha256") == condition_digest
            and row.get("execution_sha256") == execution_digest
            and row.get("runner_sha256") == runner_digest
        )
    except (EvaluationError, KeyError, TypeError):
        return False


def _parsed(row: Mapping[str, Any] | None, case: Mapping[str, Any], profile: Mapping[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if row is None or row.get("terminal_completed") is not True or row.get("parse_status") != "parsed":
        return None, None
    try:
        semantic = _plain(validate_graph_output(row.get("semantic_output"), profile["protocol"], profile["selector_schema"]))
        parent = _plain(resolve_graph(_task(case), semantic, profile["protocol"], profile["reference_policy"], profile["base_manifest"]))
    except Exception:
        return None, None
    return semantic, parent


def _directed_edges(semantic: Mapping[str, Any] | None) -> set[tuple[str, str]]:
    if semantic is None:
        return set()
    edges: set[tuple[str, str]] = set()
    rows = semantic.get("pairwise_relations")
    if not isinstance(rows, list):
        return edges
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        left, right, relation = row.get("left_slot"), row.get("right_slot"), row.get("relation")
        if relation == "left_controls_right_downstream":
            edges.add((left, right))
        elif relation == "right_controls_left_downstream":
            edges.add((right, left))
    return edges


def _entry(numerator: int, denominator: int | None) -> dict[str, int | None]:
    if type(numerator) is not int or numerator < 0 or (denominator is not None and (type(denominator) is not int or denominator < 0)):
        raise EvaluationError("AQ8 aggregate count invalid")
    return {"numerator": numerator, "denominator": denominator}


def _compare(kind: str, operator: str, boundary: Fraction | int | bool, value: Any, *, defined: bool) -> bool:
    if not defined:
        return False
    if kind == "ratio":
        if not isinstance(value, Fraction):
            raise EvaluationError("AQ8 ratio value invalid")
    elif kind == "count":
        if type(value) is not int:
            raise EvaluationError("AQ8 count value invalid")
    elif kind == "boolean":
        if type(value) is not bool:
            raise EvaluationError("AQ8 boolean value invalid")
    else:
        raise EvaluationError("AQ8 formula kind invalid")
    if operator == "==":
        return value == boundary
    if operator == ">=":
        return value >= boundary
    if operator == "<=":
        return value <= boundary
    raise EvaluationError("AQ8 formula operator invalid")


def _semantics(counts: Mapping[str, Any], gates: tuple[str, ...]) -> tuple[dict[str, Any], dict[str, bool], dict[str, bool]]:
    if set(counts) != set(gates):
        raise EvaluationError("AQ8 aggregate count coverage invalid")
    metrics: dict[str, Any] = {}
    defined: dict[str, bool] = {}
    outcomes: dict[str, bool] = {}
    for gate_id in gates:
        kind, operator, boundary = _SPECS[gate_id]
        entry = counts[gate_id]
        if kind in {"ratio", "count"}:
            if not isinstance(entry, Mapping) or set(entry) != {"numerator", "denominator"}:
                raise EvaluationError("AQ8 aggregate count shape invalid")
            numerator, denominator = entry["numerator"], entry["denominator"]
            if type(numerator) is not int or numerator < 0:
                raise EvaluationError("AQ8 aggregate numerator invalid")
            if kind == "ratio":
                if type(denominator) is not int or denominator < 0 or numerator > denominator:
                    raise EvaluationError("AQ8 aggregate ratio counts invalid")
                is_defined = denominator > 0
                rational = Fraction(numerator, denominator) if is_defined else Fraction(0, 1)
                metrics[gate_id] = f"{numerator}/{denominator}" if is_defined else "0/1"
                defined[gate_id] = is_defined
                outcomes[gate_id] = _compare(kind, operator, boundary, rational, defined=is_defined)
            else:
                if denominator is not None:
                    raise EvaluationError("AQ8 count denominator invalid")
                metrics[gate_id] = numerator
                defined[gate_id] = True
                outcomes[gate_id] = _compare(kind, operator, boundary, numerator, defined=True)
        else:
            if not isinstance(entry, Mapping) or set(entry) != {"value", "corroborated"} or type(entry.get("value")) is not bool or type(entry.get("corroborated")) is not bool:
                raise EvaluationError("AQ8 boolean assertion shape invalid")
            metrics[gate_id] = entry["value"]
            defined[gate_id] = entry["corroborated"]
            outcomes[gate_id] = _compare(kind, operator, boundary, entry["value"], defined=entry["corroborated"])
    return metrics, defined, outcomes


def _score_condition(condition: str, records: list[dict[str, Any]], profile: Mapping[str, Any]) -> dict[str, Any]:
    if len(records) != 40:
        raise EvaluationError("AQ8 condition materialization invalid")
    graph_exact = state_exact = directed_tp = directed_fp = directed_fn = 0
    independent_exact = independent_total = root_exact = root_total = 0
    uncertainty_tn = uncertainty_fp = cap_exact = cap_total = 0
    selected_tp = selected_fp = selected_fn = native_tn = native_fp = 0
    broad_violations = broad_total = stacking = exactly_two_exact = exactly_two_total = 0
    explicit_exact = explicit_total = must_not = unselected_need = reference_exact = payload_cap = events = 0
    for record in records:
        case = record["case"]
        expected_semantic = record["expected"]["semantic"]
        expected_parent = record["expected"]["parent"]
        semantic, parent = _parsed(record.get("row"), case, profile)
        parsed = semantic is not None and parent is not None

        if parsed and parent["graph_status"] in {"valid", "graph_uncertain"}:
            graph_exact += 1
        if parsed:
            state_exact += sum(int(got == want) for got, want in zip(semantic["candidate_states"], expected_semantic["candidate_states"], strict=True))

        predicted_edges = _directed_edges(semantic)
        expected_edges = _directed_edges(expected_semantic)
        directed_tp += len(predicted_edges & expected_edges)
        directed_fp += len(predicted_edges - expected_edges)
        directed_fn += len(expected_edges - predicted_edges)
        independent_total += 6
        if parsed:
            independent_exact += sum(
                int((got["relation"] == "independent") == (want["relation"] == "independent"))
                for got, want in zip(
                    semantic["pairwise_relations"],
                    expected_semantic["pairwise_relations"],
                    strict=True,
                )
            )

        if expected_parent["graph_status"] == "valid":
            root_total += 1
            root_exact += int(parsed and parent["root_slots"] == expected_parent["root_slots"])
        if expected_parent["automatic_selection_status"] == "graph_uncertain":
            if parsed and parent["automatic_selection_status"] == "graph_uncertain" and parent["selection_status"] == "graph_uncertain" and parent["selected_slots"] == []:
                uncertainty_tn += 1
            else:
                uncertainty_fp += 1
        if expected_parent["automatic_selection_status"] == "cap_exceeded":
            cap_total += 1
            cap_exact += int(parsed and parent["root_slots"] == expected_parent["root_slots"] and parent["automatic_selection_status"] == "cap_exceeded" and parent["selection_status"] == "cap_exceeded" and parent["selected_slots"] == [])

        got_selected = set(parent["selected_slots"]) if parsed else set()
        want_selected = set(expected_parent["selected_slots"])
        selected_tp += len(got_selected & want_selected)
        selected_fp += len(got_selected - want_selected)
        selected_fn += len(want_selected - got_selected)
        if expected_parent["graph_status"] == "valid" and expected_parent["selection_status"] == "automatic" and not want_selected:
            if parsed and parent["graph_status"] == "valid" and parent["selection_status"] == "automatic" and not got_selected:
                native_tn += 1
            else:
                native_fp += 1
        no_invocation = expected_parent["selection_status"] not in {"exact", "unrecognized", "ambiguous"}
        if no_invocation and "s0" not in want_selected:
            broad_total += 1
            broad_violations += int(not parsed or "s0" in got_selected)
        if len(want_selected) == 1:
            stacking += int(not parsed or len(got_selected) > 1)
        if len(want_selected) == 2:
            exactly_two_total += 1
            exactly_two_exact += int(parsed and parent["selected_slots"] == expected_parent["selected_slots"])
        if expected_parent["selection_status"] == "exact":
            explicit_total += 1
            explicit_exact += int(parsed and parent["selection_status"] == "exact" and parent["selected_slots"] == expected_parent["selected_slots"] and len(parent["selected_slots"]) == 1)
        must_not += 1 if not parsed else len(got_selected - want_selected)

        if not parsed:
            unselected_need += 1
            payload_cap += 1
        else:
            unselected_need += sum(int(row["slot_id"] not in got_selected and row["need"] != "none") for row in semantic["reference_needs"])
            reference_fields = ("reference_requests", "reference_uncertain_slots", "reference_resolution")
            reference_exact += int(semantic["reference_needs"] == expected_semantic["reference_needs"] and all(parent[name] == expected_parent[name] for name in reference_fields))
            resolution = parent["reference_resolution"]
            payload_cap += int(resolution["status"] == "cap_exceeded" or resolution["resolved_count"] > 3 or len(resolution["canonical_payload_id_tuple"]) > 3)

        event_surface = record.get("row", {}).get("events") if isinstance(record.get("row"), Mapping) else None
        if not isinstance(event_surface, Mapping) or set(event_surface) != set(EVENT_KEYS) or any(type(event_surface.get(name)) is not bool for name in EVENT_KEYS):
            events += 1
        else:
            events += sum(int(event_surface[name]) for name in EVENT_KEYS)

    counts = {
        "graph_validity": _entry(graph_exact, 40),
        "candidate_state_accuracy": _entry(state_exact, 160),
        "directed_control_precision": _entry(directed_tp, directed_tp + directed_fp),
        "directed_control_recall": _entry(directed_tp, directed_tp + directed_fn),
        "independent_relation_accuracy": _entry(independent_exact, independent_total),
        "exact_root_set": _entry(root_exact, root_total),
        "uncertainty_abstention": _entry(uncertainty_tn, uncertainty_tn + uncertainty_fp),
        "cap_abstention": _entry(cap_exact, cap_total),
        "precision": _entry(selected_tp, selected_tp + selected_fp),
        "recall": _entry(selected_tp, selected_tp + selected_fn),
        "native_abstention": _entry(native_tn, native_tn + native_fp),
        "broad_router_over_selection": _entry(broad_violations, broad_total),
        "one_decision_stacking": _entry(stacking, None),
        "exactly_two_exact_set": _entry(exactly_two_exact, exactly_two_total),
        "explicit_invocation": _entry(explicit_exact, explicit_total),
        "must_not_select": _entry(must_not, None),
        "unselected_need_violations": _entry(unselected_need, None),
        "reference_correctness": _entry(reference_exact, 40),
        "payload_cap_violations": _entry(payload_cap, None),
        "implicit_effect_claim_tool_events": _entry(events, None),
    }
    metrics, defined, gates = _semantics(counts, PER_CONDITION_GATES)
    return {"id": condition, "counts": counts, "metrics": metrics, "defined": defined, "gates": gates, "status": "pass" if all(gates.values()) else "fail"}


def _validate_envelope(envelope: Any, profile: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        raise EvaluationError("AQ8 envelope unavailable")
    _schema_validate(envelope)
    try:
        binding = normalize_binding(envelope["binding"])
    except (RunIndexError, TypeError, ValueError) as error:
        raise EvaluationError("AQ8 binding invalid") from error
    if binding["model"]["id"] != MODEL or binding["reasoning"]["id"] != REASONING or binding["schedule"]["seed"] != SCHEDULE_SEED:
        raise EvaluationError("AQ8 execution profile drift")
    identities = _profile_binding_identities(profile)
    if any(binding[name] != identity for name, identity in identities.items()):
        raise EvaluationError("AQ8 verified identity binding drift")
    cases = _case_map(profile)
    expected_oracles = _expected_oracles(cases, profile)
    schedule = envelope["schedule"]
    expected_schedule = build_schedule(tuple(cases), SCHEDULE_SEED)
    expected_schedule_digest = schedule_digest(expected_schedule)
    if schedule["seed"] != SCHEDULE_SEED or schedule["digest"] != expected_schedule_digest or tuple(schedule["presentations"]) != expected_schedule:
        raise EvaluationError("AQ8 schedule mismatch")
    if binding["schedule"]["digest"] != expected_schedule_digest:
        raise EvaluationError("AQ8 binding schedule mismatch")
    execution = envelope["execution_contract"]
    if execution != profile.get("execution_contract"):
        raise EvaluationError("AQ8 execution contract mismatch")
    execution_digest = _profile_execution_digest(profile)
    metric_digest = _authority_contract(profile)
    condition_digests = {name: _condition_digest(profile, name) for name in CONDITIONS}

    buckets: dict[int, list[Mapping[str, Any]]] = {index: [] for index in range(80)}
    raw_rows: list[tuple[str, Mapping[str, Any]]] = []
    all_rows_exact_identity = True
    wrapper_digests: dict[str, str] = {}
    for condition in envelope["conditions"]:
        condition_id = condition["id"]
        wrapper_digests[condition_id] = condition["digest"]
        for row in condition["observations"]:
            raw_rows.append((condition_id, row))
            index = row["presentation_index"]
            expected = expected_schedule[index]
            exact_identity = expected == {"presentation_index": index, "condition": condition_id, "case_id": row["case_id"]}
            all_rows_exact_identity = all_rows_exact_identity and exact_identity
            if exact_identity:
                buckets[index].append(row)

    records: list[dict[str, Any]] = []
    exact_terminal_rows: list[Mapping[str, Any]] = []
    semantic_exact = resolver_exact = binding_exact = 0
    all_single = all(len(rows) == 1 for rows in buckets.values())
    for expected in expected_schedule:
        index, condition, case_id = expected["presentation_index"], expected["condition"], expected["case_id"]
        row = buckets[index][0] if len(buckets[index]) == 1 else None
        case = cases[case_id]
        oracle = expected_oracles[case_id]
        semantic, parent = _parsed(row, case, profile)
        if semantic is not None and parent is not None:
            semantic_exact += 1
            resolver_exact += int(row.get("parent_derivation") == parent)
        if row is not None and row.get("terminal_completed") is True:
            exact_terminal_rows.append(row)
        if row is not None and wrapper_digests.get(condition) == condition_digests[condition] and _row_custody(
            row, condition, case, profile, condition_digests[condition], execution_digest, binding["runner"]["digest"],
        ):
            binding_exact += 1
        records.append({"condition": condition, "case": case, "expected": oracle, "row": row})

    exact_presentations = 80 if len(raw_rows) == 80 and all_rows_exact_identity and all_single and all(row.get("terminal_completed") is True for _, row in raw_rows) else 0
    unique_contexts = len({row["context_id"] for row in exact_terminal_rows if isinstance(row.get("context_id"), str) and row["context_id"]})
    assertions = envelope["complete_run_assertions"]
    complete_counts: dict[str, Any] = {
        "semantic_schema_order": _entry(semantic_exact, 80),
        "resolver_parity": _entry(resolver_exact, 80),
        "presentations_80_of_80": _entry(exact_presentations, None),
        "unique_context_ids": _entry(unique_contexts, None),
        "binding_schedule_packet_parity": _entry(binding_exact, 80),
        "runner_local_raw_persistence": {"value": assertions["runner_local_raw_persistence"], "corroborated": assertions["runner_local_raw_persistence_corroborated"]},
        "held_out_outcome_use": {"value": assertions["held_out_outcome_use"], "corroborated": assertions["held_out_outcome_use_corroborated"]},
    }
    complete_metrics, complete_defined, complete_gates = _semantics(complete_counts, COMPLETE_RUN_GATES)
    complete = {"counts": complete_counts, "metrics": complete_metrics, "defined": complete_defined, "gates": complete_gates, "status": "pass" if all(complete_gates.values()) else "fail"}
    return {
        "binding": binding, "execution_digest": execution_digest, "schedule_digest": expected_schedule_digest,
        "metric_digest": metric_digest, "records": records, "complete_run": complete,
    }


_CLAIM_FALSE = (
    "behavioral_qualification_proven", "runtime_provenance_proven", "provider_identity_proven",
    "telemetry_attested", "product_behavior_proven", "promotion_eligible",
)
_RESULT_BASE = frozenset({
    "schema_version", "evaluation_mode", "status", *_CLAIM_FALSE,
    "runner_local_raw_trajectories_persisted", "provider_raw_trajectory_retention_status", "maximum_claim",
})
_SCORED = _RESULT_BASE | {
    "aggregate_digest", "binding_digest", "execution_digest", "schedule_digest", "metric_authority_digest",
    "conditions", "complete_run", "integrity_flags",
}
_INSUFFICIENT = _RESULT_BASE | {"insufficiency_reason"}


def _insufficient(reason: str) -> dict[str, Any]:
    return validate_result({
        "schema_version": "8.0", "evaluation_mode": "qualification", "status": "insufficient_data",
        "behavioral_qualification_proven": False, "runtime_provenance_proven": False,
        "provider_identity_proven": False, "telemetry_attested": False,
        "product_behavior_proven": False, "promotion_eligible": False,
        "runner_local_raw_trajectories_persisted": False,
        "provider_raw_trajectory_retention_status": "unknown", "maximum_claim": None,
        "insufficiency_reason": reason,
    })


def _validate_aggregate_row(row: Any, gates: tuple[str, ...], *, condition_id: str | None = None) -> None:
    expected_keys = {"counts", "metrics", "defined", "gates", "status"} | ({"id"} if condition_id is not None else set())
    if not isinstance(row, dict) or set(row) != expected_keys or (condition_id is not None and row.get("id") != condition_id):
        raise EvaluationError("AQ8 aggregate row shape invalid")
    if not isinstance(row.get("counts"), dict) or not isinstance(row.get("metrics"), dict) or not isinstance(row.get("defined"), dict) or not isinstance(row.get("gates"), dict):
        raise EvaluationError("AQ8 aggregate row unavailable")
    metrics, defined, outcomes = _semantics(row["counts"], gates)
    if row["metrics"] != metrics or row["defined"] != defined or row["gates"] != outcomes:
        raise EvaluationError("AQ8 aggregate semantic closure invalid")
    expected_status = "pass" if all(outcomes.values()) else "fail"
    if row.get("status") != expected_status:
        raise EvaluationError("AQ8 aggregate status invalid")


def _validate_count_invariants(condition: Mapping[str, Any]) -> None:
    counts = condition["counts"]
    for gate_id, expected in _BOUND_CONDITION_DENOMINATORS.items():
        if counts[gate_id]["denominator"] != expected:
            raise EvaluationError("AQ8 bound condition denominator invalid")
    if counts["directed_control_precision"]["numerator"] != counts["directed_control_recall"]["numerator"]:
        raise EvaluationError("AQ8 directed-edge count closure invalid")
    if counts["precision"]["numerator"] != counts["recall"]["numerator"]:
        raise EvaluationError("AQ8 selected-edge count closure invalid")
    for gate_id, maximum in _VARIABLE_CONDITION_DENOMINATOR_MAXIMA.items():
        denominator = counts[gate_id]["denominator"]
        if type(denominator) is not int or denominator > maximum:
            raise EvaluationError("AQ8 predicted-positive denominator invalid")
    maximum_counts = {
        "one_decision_stacking": 40, "must_not_select": 80,
        "unselected_need_violations": 160, "payload_cap_violations": 40,
        "implicit_effect_claim_tool_events": 240,
    }
    for gate_id, maximum in maximum_counts.items():
        if counts[gate_id]["numerator"] > maximum:
            raise EvaluationError("AQ8 violation count invalid")


def validate_result(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict) or result.get("schema_version") != "8.0" or result.get("evaluation_mode") != "qualification":
        raise EvaluationError("AQ8 result root invalid")
    if result.get("status") == "insufficient_data":
        if set(result) != _INSUFFICIENT or result.get("maximum_claim") is not None or not isinstance(result.get("insufficiency_reason"), str):
            raise EvaluationError("AQ8 insufficient result invalid")
        if result.get("runner_local_raw_trajectories_persisted") is not False:
            raise EvaluationError("AQ8 insufficient persistence claim invalid")
    elif result.get("status") in {"pass", "fail"}:
        if set(result) != _SCORED or result.get("maximum_claim") != CLAIM or not all(_hex(result.get(key)) for key in ("aggregate_digest", "binding_digest", "execution_digest", "schedule_digest", "metric_authority_digest")):
            raise EvaluationError("AQ8 scored result invalid")
        conditions = result.get("conditions")
        if not isinstance(conditions, list) or len(conditions) != 2:
            raise EvaluationError("AQ8 condition aggregate unavailable")
        for index, condition_id in enumerate(CONDITIONS):
            _validate_aggregate_row(conditions[index], PER_CONDITION_GATES, condition_id=condition_id)
            _validate_count_invariants(conditions[index])
        complete = result.get("complete_run")
        _validate_aggregate_row(complete, COMPLETE_RUN_GATES)
        complete_counts = complete["counts"]
        if any(complete_counts[gate_id]["denominator"] != expected for gate_id, expected in _BOUND_COMPLETE_DENOMINATORS.items()):
            raise EvaluationError("AQ8 bound complete-run denominator invalid")
        if complete_counts["presentations_80_of_80"]["numerator"] not in {0, 80} or complete_counts["unique_context_ids"]["numerator"] > 80:
            raise EvaluationError("AQ8 complete-run count invalid")
        expected_status = "pass" if all(row["status"] == "pass" for row in conditions) and complete["status"] == "pass" else "fail"
        if result["status"] != expected_status:
            raise EvaluationError("AQ8 root decision invalid")
        if result.get("runner_local_raw_trajectories_persisted") is not complete["metrics"]["runner_local_raw_persistence"]:
            raise EvaluationError("AQ8 persistence result mismatch")
        body = {key: result[key] for key in ("binding_digest", "execution_digest", "schedule_digest", "metric_authority_digest", "conditions", "complete_run")}
        if result["aggregate_digest"] != _digest(body):
            raise EvaluationError("AQ8 aggregate digest invalid")
        flags = result.get("integrity_flags")
        expected_flags = {"authority_binding": True, "execution_contract": True, "schedule_contract": True, "formula_contract": True, "profile_parity": True}
        if flags != expected_flags:
            raise EvaluationError("AQ8 integrity flags invalid")
    else:
        raise EvaluationError("AQ8 result status invalid")
    if any(result.get(key) is not False for key in _CLAIM_FALSE) or result.get("provider_raw_trajectory_retention_status") != "unknown":
        raise EvaluationError("AQ8 claim ceiling invalid")
    return result


def score_synthetic(envelope: Any, profile: Mapping[str, Any]) -> dict[str, Any]:
    """Score one synthetic batch; only top-level custody gaps are insufficient."""
    if not isinstance(envelope, Mapping) or envelope.get("provenance_mode") != "synthetic":
        return _insufficient("AQ8 public synthetic scorer rejects live provenance")
    try:
        validated = _validate_envelope(envelope, profile)
        outcomes = [
            _score_condition(condition, [record for record in validated["records"] if record["condition"] == condition], profile)
            for condition in CONDITIONS
        ]
        complete = validated["complete_run"]
        body = {
            "binding_digest": _digest(validated["binding"]),
            "execution_digest": validated["execution_digest"],
            "schedule_digest": validated["schedule_digest"],
            "metric_authority_digest": validated["metric_digest"],
            "conditions": outcomes, "complete_run": complete,
        }
        result = {
            "schema_version": "8.0", "evaluation_mode": "qualification",
            "status": "pass" if all(row["status"] == "pass" for row in outcomes) and complete["status"] == "pass" else "fail",
            "aggregate_digest": _digest(body), **body,
            "integrity_flags": {"authority_binding": True, "execution_contract": True, "schedule_contract": True, "formula_contract": True, "profile_parity": True},
            "behavioral_qualification_proven": False, "runtime_provenance_proven": False,
            "provider_identity_proven": False, "telemetry_attested": False,
            "product_behavior_proven": False, "promotion_eligible": False,
            "runner_local_raw_trajectories_persisted": complete["metrics"]["runner_local_raw_persistence"],
            "provider_raw_trajectory_retention_status": "unknown", "maximum_claim": CLAIM,
        }
        return validate_result(result)
    except (EvaluationError, KeyError, TypeError, ValueError, OSError):
        return _insufficient("AQ8 custody, authority, schedule, execution, or profile validation unavailable")


_LIVE_SESSION_TOKEN = object()


class _LiveScoreSession:
    __slots__ = ("_profile", "_binding", "_pid", "_token")

    def __init__(self, profile: Mapping[str, Any], binding: Mapping[str, Any], token: object) -> None:
        if token is not _LIVE_SESSION_TOKEN:
            raise EvaluationError("AQ8 live session construction denied")
        self._profile = profile
        self._binding = normalize_binding(binding)
        self._pid = os.getpid()
        self._token = token

    def __reduce__(self) -> Any:
        raise TypeError("AQ8 live session is process-local")

    def __copy__(self) -> Any:
        raise TypeError("AQ8 live session is process-local")

    def __deepcopy__(self, memo: Any) -> Any:
        raise TypeError("AQ8 live session is process-local")

    def score(self, envelope: Any) -> dict[str, Any]:
        if self._token is not _LIVE_SESSION_TOKEN or os.getpid() != self._pid or not isinstance(envelope, Mapping) or envelope.get("provenance_mode") != "live_runner":
            return _insufficient("AQ8 live session unavailable")
        try:
            if normalize_binding(envelope.get("binding")) != self._binding:
                return _insufficient("AQ8 live binding mismatch")
        except (RunIndexError, TypeError, ValueError):
            return _insufficient("AQ8 live binding unavailable")
        copied = dict(envelope)
        copied["provenance_mode"] = "synthetic"
        return score_synthetic(copied, self._profile)


def create_live_score_session(profile: Mapping[str, Any], binding: Mapping[str, Any]) -> _LiveScoreSession:
    """Create a process- and exact-binding-local live scoring witness."""
    return _LiveScoreSession(profile, binding, _LIVE_SESSION_TOKEN)
