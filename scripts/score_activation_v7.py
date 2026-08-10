#!/usr/bin/env python3
"""Closed AQ7 aggregate scorer for supplied, in-memory observations only."""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

from aq_run_index_v7 import RunIndexError, normalize_binding
from resolve_h3_decision_certificate_v7 import (
    canonical_json,
    resolve_decision_certificate,
    validate_fact_output,
)

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "evals/foundation-v4/activation-evaluator-schema-v7.json"
SCHEDULE_SEED = "aq7-h3-ci1-v1"
MODEL = "gpt-5.5"
REASONING = "medium"
CLAIM = "unattested deterministic AQ7 decision-certificate telemetry from supplied observations"
CONDITIONS = ("current", "reduced")


class EvaluationError(ValueError):
    """The supplied envelope is outside AQ7's closed qualification contract."""


def _bytes(value: Any) -> bytes:
    raw = canonical_json(value)
    return raw.encode("utf-8") if isinstance(raw, str) else bytes(raw)


def _digest(value: Any) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


def _hex(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _decimal(value: Any, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise EvaluationError(f"AQ7 invalid {name}") from error
    if not result.is_finite():
        raise EvaluationError(f"AQ7 invalid {name}")
    return result


def build_schedule(qualified_case_ids: Any, seed: str) -> tuple[dict[str, Any], ...]:
    """Build the sole 80-presentation alternating AQ7 schedule."""
    if not isinstance(seed, str) or not seed:
        raise EvaluationError("AQ7 schedule seed unavailable")
    if not isinstance(qualified_case_ids, (tuple, list)) or len(qualified_case_ids) != 40:
        raise EvaluationError("AQ7 requires exactly forty qualified cases")
    identifiers = tuple(qualified_case_ids)
    if any(not isinstance(case_id, str) or not case_id for case_id in identifiers) or len(set(identifiers)) != 40:
        raise EvaluationError("AQ7 qualified case IDs invalid")
    rng = random.Random(int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16))
    current, reduced = list(sorted(identifiers)), list(sorted(identifiers))
    rng.shuffle(current); rng.shuffle(reduced)
    first = "current" if rng.randrange(2) == 0 else "reduced"
    second = "reduced" if first == "current" else "current"
    rows: list[dict[str, Any]] = []
    for current_id, reduced_id in zip(current, reduced, strict=True):
        rows.append({"presentation_index": len(rows), "condition": first, "case_id": current_id if first == "current" else reduced_id})
        rows.append({"presentation_index": len(rows), "condition": second, "case_id": reduced_id if second == "reduced" else current_id})
    return tuple(rows)


def schedule_digest(schedule: Any) -> str:
    if not isinstance(schedule, (tuple, list)):
        raise EvaluationError("AQ7 schedule unavailable")
    return _digest(list(schedule))


def _schema_validate(value: Any) -> None:
    try:
        import jsonschema
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(value))
    except (OSError, json.JSONDecodeError, ImportError) as error:
        raise EvaluationError("AQ7 evaluator schema unavailable") from error
    if errors:
        raise EvaluationError("AQ7 evaluator schema rejected envelope")


def _insufficient(reason: str) -> dict[str, Any]:
    return validate_result({
        "schema_version": "7.0", "evaluation_mode": "qualification", "status": "insufficient_data",
        "promotion_eligible": False, "runtime_provenance_proven": False, "provider_identity_proven": False,
        "telemetry_attested": False, "product_behavior_proven": False,
        "runner_local_raw_trajectories_persisted": False,
        "provider_raw_trajectory_retention_status": "unknown", "maximum_claim": None,
        "insufficiency_reason": reason,
    })


def _case_map(profile: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    qualified = profile.get("qualified_cases")
    documents = (profile.get("authoring"), profile.get("heldout"))
    if not isinstance(qualified, (tuple, list)) or any(not isinstance(item, str) for item in qualified):
        raise EvaluationError("AQ7 profile qualified cases unavailable")
    all_cases: dict[str, Mapping[str, Any]] = {}
    for document in documents:
        if not isinstance(document, Mapping) or not isinstance(document.get("cases"), list):
            raise EvaluationError("AQ7 corpus profile unavailable")
        for case in document["cases"]:
            if not isinstance(case, Mapping) or not isinstance(case.get("case_id"), str) or case["case_id"] in all_cases:
                raise EvaluationError("AQ7 profile case grammar invalid")
            all_cases[case["case_id"]] = case
    result = {case_id: all_cases[case_id] for case_id in qualified if case_id in all_cases}
    if len(result) != len(qualified):
        raise EvaluationError("AQ7 profile case coverage invalid")
    ids = profile.get("qualified_ids")
    if not isinstance(ids, (tuple, list)) or tuple(ids) != tuple(result):
        raise EvaluationError("AQ7 profile case order unavailable")
    if len(result) != 40:
        raise EvaluationError("AQ7 profile case coverage invalid")
    return result


def _field(source: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in source:
            return source[name]
    raise EvaluationError("AQ7 profile digest unavailable")


def _expected_case_digest(case: Mapping[str, Any], kind: str) -> str:
    if kind == "case":
        value = _field(case, "prompt_sha256")
        if value != hashlib.sha256(_task(case).encode("utf-8")).hexdigest():
            raise EvaluationError("AQ7 frozen case bytes drift")
    elif kind == "task":
        value = hashlib.sha256(_task(case).encode("utf-8")).hexdigest()
    else:
        raise EvaluationError("AQ7 packet digest requires a condition")
    if not _hex(value):
        raise EvaluationError("AQ7 profile digest invalid")
    return value


def _task(case: Mapping[str, Any]) -> str:
    packet = case.get("packet")
    value = packet.get("task_text") if isinstance(packet, Mapping) else None
    if not isinstance(value, str):
        raise EvaluationError("AQ7 profile task unavailable")
    return value


def _packet_digest(profile: Mapping[str, Any], condition: str, case: Mapping[str, Any]) -> str:
    adapter = profile.get("adapter")
    rows = adapter.get("conditions") if isinstance(adapter, Mapping) else None
    entry = rows.get(condition) if isinstance(rows, Mapping) else None
    contract = adapter.get("packet_contract") if isinstance(adapter, Mapping) else None
    if not isinstance(entry, Mapping) or not isinstance(contract, Mapping):
        raise EvaluationError("AQ7 condition packet unavailable")
    packet = {"instruction": contract.get("instruction"), "task_text": _task(case),
              "predicate_order": profile.get("protocol", {}).get("predicate_order"),
              "condition_guidance": entry.get("condition_guidance")}
    if not isinstance(packet["instruction"], str) or not isinstance(packet["predicate_order"], list):
        raise EvaluationError("AQ7 condition packet invalid")
    return _digest(packet)


def _profile_execution_digest(profile: Mapping[str, Any]) -> str:
    contract = profile.get("execution_contract")
    if not isinstance(contract, Mapping):
        raise EvaluationError("AQ7 execution contract unavailable")
    return _digest(contract)


def _identity_from_authority(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise EvaluationError("AQ7 authority binding unavailable")
    digest = value.get("digest", value.get("sha256"))
    identity = {"commit": value.get("commit"), "tree": value.get("tree"), "digest": digest}
    if not isinstance(identity["commit"], str) or not isinstance(identity["tree"], str) or not _hex(identity["digest"]):
        raise EvaluationError("AQ7 authority binding invalid")
    return identity


def _profile_binding_identities(profile: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    manifest = profile.get("manifest")
    if not isinstance(manifest, Mapping):
        raise EvaluationError("AQ7 manifest unavailable")
    expected = {
        "protocol": _identity_from_authority(manifest.get("h3_authority")),
        "reference_policy": _identity_from_authority(manifest.get("reference_policy_authority")),
        "corpus": _identity_from_authority(manifest.get("corpus_authority")),
        "validator": _identity_from_authority(manifest.get("validator_authority")),
        "candidate": {
            "commit": profile.get("candidate_commit"), "tree": profile.get("candidate_tree", profile.get("tree")),
            "digest": profile.get("candidate_digest", profile.get("digest")),
        },
    }
    surface = manifest.get("evaluator_surface")
    rows = surface.get("files") if isinstance(surface, Mapping) else None
    if not isinstance(rows, list):
        raise EvaluationError("AQ7 evaluator surface unavailable")
    by_role = {row.get("role"): row for row in rows if isinstance(row, Mapping)}
    for binding_name, role in (("runner", "runner"), ("evaluator", "scorer")):
        row = by_role.get(role)
        if not isinstance(row, Mapping):
            raise EvaluationError("AQ7 evaluator surface unavailable")
        expected[binding_name] = {
            "commit": expected["candidate"]["commit"], "tree": expected["candidate"]["tree"],
            "digest": row.get("sha256"),
        }
    if any(not isinstance(item["commit"], str) or not isinstance(item["tree"], str) or not _hex(item["digest"]) for item in expected.values()):
        raise EvaluationError("AQ7 profile identity invalid")
    return expected


def _condition_digest(profile: Mapping[str, Any], condition_id: str) -> str:
    adapter = profile.get("adapter")
    if not isinstance(adapter, Mapping) or not isinstance(adapter.get("conditions"), Mapping):
        raise EvaluationError("AQ7 condition adapter unavailable")
    row = adapter["conditions"].get(condition_id)
    if not isinstance(row, Mapping):
        raise EvaluationError("AQ7 condition adapter unavailable")
    claimed = row.get("condition_guidance_canonical_sha256")
    guidance = row.get("condition_guidance")
    if not _hex(claimed) or _digest(guidance) != claimed:
        raise EvaluationError("AQ7 condition adapter digest invalid")
    contract = profile.get("execution_contract")
    contract_rows = contract.get("conditions") if isinstance(contract, Mapping) else None
    if isinstance(contract_rows, Mapping):
        contract_row = contract_rows.get(condition_id)
    elif isinstance(contract_rows, list):
        contract_row = next((item for item in contract_rows if isinstance(item, Mapping) and item.get("id") == condition_id), None)
    else:
        contract_row = None
    if not isinstance(contract_row, Mapping) or contract_row.get("condition_guidance_canonical_sha256") != claimed:
        raise EvaluationError("AQ7 execution condition parity unavailable")
    return claimed


def _profile_gate(profile: Mapping[str, Any], *names: str) -> Decimal:
    sources = (profile.get("execution_contract"), profile.get("manifest"))
    for source in sources:
        if isinstance(source, Mapping):
            for name in names:
                if name in source:
                    return _decimal(source[name], name)
                gates = source.get("gates")
                if isinstance(gates, Mapping) and name in gates:
                    return _decimal(gates[name], name)
    raise EvaluationError("AQ7 execution gates unavailable")


def _event_count(events: Mapping[str, Any]) -> int:
    return sum(int(events[name] is True) for name in (
        "effect_requested", "effect_granted", "claim_requested", "claim_granted", "tool_requested", "tool_granted",
    ))


def _expected_reference(case: Mapping[str, Any], resolution: Mapping[str, Any]) -> bool:
    grading = case.get("grading")
    expected = (grading.get("deterministic_reference_expectations") if isinstance(grading, Mapping) else None)
    if expected is None:
        return resolution["payload_resolution"]["status"] == "resolved"
    if not isinstance(expected, Mapping):
        raise EvaluationError("AQ7 reference expectations invalid")
    observed = resolution["payload_resolution"]
    payloads = observed["payloads"]
    expected_payloads = expected.get("payloads")
    return (
        observed["status"] == expected.get("status")
        and observed["resolved_count"] == expected.get("resolved_payload_count")
        and (expected_payloads is None or payloads == expected_payloads)
    )


def _validate_envelope(envelope: Any, profile: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], list[dict[str, Any]], str]:
    if not isinstance(envelope, Mapping):
        raise EvaluationError("AQ7 envelope unavailable")
    _schema_validate(envelope)
    if envelope["provenance_mode"] not in {"synthetic", "live_runner"}:
        raise EvaluationError("AQ7 provenance invalid")
    try:
        binding = normalize_binding(envelope["binding"])
    except (RunIndexError, TypeError, ValueError) as error:
        raise EvaluationError("AQ7 binding invalid") from error
    if binding["model"]["id"] != MODEL or binding["reasoning"]["id"] != REASONING:
        raise EvaluationError("AQ7 execution profile drift")
    if binding["schedule"]["seed"] != SCHEDULE_SEED:
        raise EvaluationError("AQ7 schedule seed drift")
    expected_identities = _profile_binding_identities(profile)
    if any(binding[name] != identity for name, identity in expected_identities.items()):
        raise EvaluationError("AQ7 verified identity binding drift")
    cases = _case_map(profile)
    schedule = envelope["schedule"]
    expected = build_schedule(tuple(cases), schedule["seed"])
    if schedule["seed"] != SCHEDULE_SEED or schedule["digest"] != schedule_digest(expected) or tuple(schedule["presentations"]) != expected:
        raise EvaluationError("AQ7 schedule mismatch")
    if binding["schedule"]["digest"] != schedule["digest"]:
        raise EvaluationError("AQ7 binding schedule mismatch")
    execution_digest = _profile_execution_digest(profile)
    execution = envelope["execution_contract"]
    integrity = execution.get("integrity") if isinstance(execution, Mapping) else None
    if execution != profile.get("execution_contract") or not isinstance(integrity, Mapping) or integrity.get("runner_local_raw_trajectories_persisted") is not False or integrity.get("provider_raw_trajectory_retention_status") != "unknown":
        raise EvaluationError("AQ7 execution custody mismatch")
    if [condition["id"] for condition in envelope["conditions"]] != list(CONDITIONS):
        raise EvaluationError("AQ7 condition order mismatch")
    rows: list[dict[str, Any]] = []
    contexts: set[str] = set(); indexes: set[int] = set()
    for condition in envelope["conditions"]:
        if len(condition["observations"]) != 40:
            raise EvaluationError("AQ7 condition coverage mismatch")
        expected_condition_digest = _condition_digest(profile, condition["id"])
        if condition["digest"] != expected_condition_digest:
            raise EvaluationError("AQ7 condition digest invalid")
        seen: set[str] = set()
        for row in condition["observations"]:
            case_id, index = row["case_id"], row["presentation_index"]
            if case_id not in cases or case_id in seen or index in indexes or expected[index] != {"presentation_index": index, "condition": condition["id"], "case_id": case_id}:
                raise EvaluationError("AQ7 presentation mismatch")
            seen.add(case_id); indexes.add(index)
            if row["context_id"] in contexts:
                raise EvaluationError("AQ7 context reuse")
            contexts.add(row["context_id"])
            if (
                row["case_sha256"] != _expected_case_digest(cases[case_id], "case")
                or row["task_sha256"] != _expected_case_digest(cases[case_id], "task")
                or row["packet_sha256"] != _packet_digest(profile, condition["id"], cases[case_id])
                or row["condition_sha256"] != condition["digest"]
                or row["execution_sha256"] != execution_digest
                or row["runner_sha256"] != binding["runner"]["digest"]
            ):
                raise EvaluationError("AQ7 observation custody mismatch")
            rows.append({"condition": condition["id"], "case": cases[case_id], "row": row})
        if seen != set(cases):
            raise EvaluationError("AQ7 condition case coverage mismatch")
    if indexes != set(range(80)):
        raise EvaluationError("AQ7 presentation coverage mismatch")
    return cases, rows, execution_digest


def _score_condition(condition: str, records: list[dict[str, Any]], profile: Mapping[str, Any]) -> dict[str, Any]:
    automatic_tp = automatic_fp = automatic_fn = native_total = native_ok = topology_total = topology_over = 0
    stacking = exactly_two_total = exactly_two_ok = must_not = explicit_total = explicit_ok = 0
    selector_invalid = resolver_mismatch = payload_cap = reference_ok = authority = 0
    for record in records:
        case, row = record["case"], record["row"]
        grading = case.get("grading")
        if not isinstance(grading, Mapping):
            raise EvaluationError("AQ7 case grading unavailable")
        expected_atoms = set(grading.get("expected_selected_atoms", ()))
        valid = row["parse_status"] == "parsed"
        actual: Mapping[str, Any] | None = None
        if valid:
            try:
                facts = validate_fact_output(row["fact_output"], profile["protocol"], profile["selector_schema"])
                actual = resolve_decision_certificate(_task(case), list(facts), profile["protocol"], profile["reference_policy"], profile["base_manifest"])
                valid = isinstance(actual, Mapping)
            except (ValueError, TypeError, KeyError):
                valid = False
        if not valid:
            selector_invalid += 1
            got: set[str] = set()
        else:
            got = set(actual["selected_atoms"])
            resolver_mismatch += int(row["parent_resolution"] != actual)
            payload_cap += int(actual["payload_resolution"]["status"] == "cap_exceeded")
            reference_ok += int(_expected_reference(case, actual) and row["events"]["full_schema_or_template_loaded"] is False)
        if case.get("case_kind") == "automatic":
            automatic_tp += len(expected_atoms & got); automatic_fp += len(got - expected_atoms); automatic_fn += len(expected_atoms - got)
            if not expected_atoms:
                native_total += 1; native_ok += int(not got)
            if "topology-control-boundary" not in expected_atoms:
                topology_total += 1; topology_over += int("topology-control-boundary" in got)
        if len(expected_atoms) == 1:
            stacking += int(len(got) > 1)
        if case.get("exactly_two") is True:
            exactly_two_total += 1; exactly_two_ok += int(got == expected_atoms)
        if case.get("case_kind") == "explicit":
            explicit_total += 1; explicit_ok += int(got == expected_atoms)
        must_not += len(set(grading.get("expected_must_not_select_advisers", ())) & set(actual["mapped_advisers"] if actual else ()))
        authority += _event_count(row["events"])
    def ratio(n: int, d: int) -> Decimal:
        if d == 0:
            raise EvaluationError("AQ7 zero-denominator qualification gate")
        return Decimal(n) / Decimal(d)
    metrics = {
        # A completed all-abstain batch is poor content, not a custody gap.
        "automatic_precision": (Decimal(0) if automatic_tp + automatic_fp == 0 else ratio(automatic_tp, automatic_tp + automatic_fp)),
        "automatic_recall": ratio(automatic_tp, automatic_tp + automatic_fn),
        "native_abstention_specificity": ratio(native_ok, native_total),
        "broad_router_topology_overselection_rate": ratio(topology_over, topology_total),
        "exactly_two_exact_set_compliance": ratio(exactly_two_ok, exactly_two_total),
        "explicit_exact_set_compliance": ratio(explicit_ok, explicit_total),
        "reference_load_correctness": ratio(reference_ok, 40),
    }
    gates = {
        "automatic_precision": metrics["automatic_precision"] >= _profile_gate(profile, "automatic_precision_min"),
        "automatic_recall": metrics["automatic_recall"] >= _profile_gate(profile, "automatic_recall_min"),
        "native_abstention_specificity": metrics["native_abstention_specificity"] >= _profile_gate(profile, "native_abstention_specificity_min", "native_abstention_min"),
        "broad_router_topology_overselection_rate": metrics["broad_router_topology_overselection_rate"] <= _profile_gate(profile, "broad_router_overselection_max"),
        "one_decision_multi_atom_stacking": stacking <= _profile_gate(profile, "one_decision_stacking_max"),
        "exactly_two_exact_set_compliance": metrics["exactly_two_exact_set_compliance"] >= _profile_gate(profile, "exactly_two_exact_set_min", "exactly_two_min"),
        "must_not_select": must_not <= _profile_gate(profile, "must_not_select_violations_max"),
        "explicit_exact_set_compliance": metrics["explicit_exact_set_compliance"] >= _profile_gate(profile, "explicit_exact_set_min", "explicit_min"),
        "selector_validity": selector_invalid <= _profile_gate(profile, "selector_invalid_max"),
        "resolver_integrity": resolver_mismatch <= _profile_gate(profile, "resolver_mismatch_max"),
        "payload_cap": payload_cap <= _profile_gate(profile, "payload_cap_violations_max"),
        "reference_load_correctness": metrics["reference_load_correctness"] >= _profile_gate(profile, "reference_load_correct_min"),
        "implicit_authority_or_tool_events": authority <= _profile_gate(profile, "authority_tool_violations_max"),
    }
    counts = {
        "automatic_true_positive_edges": automatic_tp, "automatic_false_positive_edges": automatic_fp, "automatic_false_negative_edges": automatic_fn,
        "native_abstention_total": native_total, "native_abstention_correct": native_ok,
        "broad_router_total": topology_total, "broad_router_topology_overselections": topology_over,
        "one_decision_multi_atom_stacking": stacking, "exactly_two_total": exactly_two_total, "exactly_two_exact_sets": exactly_two_ok,
        "must_not_select_violations": must_not, "explicit_total": explicit_total, "explicit_exact_sets": explicit_ok,
        "selector_invalid": selector_invalid, "resolver_mismatches": resolver_mismatch, "payload_cap_violations": payload_cap,
        "reference_load_correct": reference_ok, "implicit_authority_or_tool_events": authority,
    }
    return {"id": condition, "counts": counts, "metrics": {key: float(value) for key, value in metrics.items()}, "gates": gates, "status": "pass" if all(gates.values()) else "fail"}


_CLAIM_FALSE = ("promotion_eligible", "runtime_provenance_proven", "provider_identity_proven", "telemetry_attested", "product_behavior_proven", "runner_local_raw_trajectories_persisted")
_RESULT_BASE = frozenset({"schema_version", "evaluation_mode", "status", *_CLAIM_FALSE, "provider_raw_trajectory_retention_status", "maximum_claim"})
_SCORED = _RESULT_BASE | {"aggregate_digest", "binding_digest", "execution_digest", "schedule_digest", "conditions", "integrity_flags"}
_INSUFFICIENT = _RESULT_BASE | {"insufficiency_reason"}
_COUNT_KEYS = frozenset({"automatic_true_positive_edges", "automatic_false_positive_edges", "automatic_false_negative_edges", "native_abstention_total", "native_abstention_correct", "broad_router_total", "broad_router_topology_overselections", "one_decision_multi_atom_stacking", "exactly_two_total", "exactly_two_exact_sets", "must_not_select_violations", "explicit_total", "explicit_exact_sets", "selector_invalid", "resolver_mismatches", "payload_cap_violations", "reference_load_correct", "implicit_authority_or_tool_events"})
_METRIC_KEYS = frozenset({"automatic_precision", "automatic_recall", "native_abstention_specificity", "broad_router_topology_overselection_rate", "exactly_two_exact_set_compliance", "explicit_exact_set_compliance", "reference_load_correctness"})
_GATE_KEYS = frozenset({"automatic_precision", "automatic_recall", "native_abstention_specificity", "broad_router_topology_overselection_rate", "one_decision_multi_atom_stacking", "exactly_two_exact_set_compliance", "must_not_select", "explicit_exact_set_compliance", "selector_validity", "resolver_integrity", "payload_cap", "reference_load_correctness", "implicit_authority_or_tool_events"})


def _aggregate_semantics(counts: Mapping[str, int]) -> tuple[dict[str, float], dict[str, bool]]:
    """Recompute the closed aggregate semantics without any observation data."""
    def ratio(numerator: int, denominator: int, *, zero_is_precision: bool = False) -> float:
        if denominator == 0:
            if zero_is_precision:
                return 0.0
            raise EvaluationError("AQ7 aggregate cohort denominator invalid")
        return numerator / denominator
    metrics = {
        "automatic_precision": ratio(counts["automatic_true_positive_edges"], counts["automatic_true_positive_edges"] + counts["automatic_false_positive_edges"], zero_is_precision=True),
        "automatic_recall": ratio(counts["automatic_true_positive_edges"], counts["automatic_true_positive_edges"] + counts["automatic_false_negative_edges"]),
        "native_abstention_specificity": ratio(counts["native_abstention_correct"], counts["native_abstention_total"]),
        "broad_router_topology_overselection_rate": ratio(counts["broad_router_topology_overselections"], counts["broad_router_total"]),
        "exactly_two_exact_set_compliance": ratio(counts["exactly_two_exact_sets"], counts["exactly_two_total"]),
        "explicit_exact_set_compliance": ratio(counts["explicit_exact_sets"], counts["explicit_total"]),
        "reference_load_correctness": ratio(counts["reference_load_correct"], 40),
    }
    gates = {
        "automatic_precision": metrics["automatic_precision"] >= .95,
        "automatic_recall": metrics["automatic_recall"] >= .90,
        "native_abstention_specificity": metrics["native_abstention_specificity"] >= .95,
        "broad_router_topology_overselection_rate": metrics["broad_router_topology_overselection_rate"] <= .05,
        "one_decision_multi_atom_stacking": counts["one_decision_multi_atom_stacking"] == 0,
        "exactly_two_exact_set_compliance": metrics["exactly_two_exact_set_compliance"] == 1.0,
        "must_not_select": counts["must_not_select_violations"] == 0,
        "explicit_exact_set_compliance": metrics["explicit_exact_set_compliance"] == 1.0,
        "selector_validity": counts["selector_invalid"] == 0,
        "resolver_integrity": counts["resolver_mismatches"] == 0,
        "payload_cap": counts["payload_cap_violations"] == 0,
        "reference_load_correctness": metrics["reference_load_correctness"] == 1.0,
        "implicit_authority_or_tool_events": counts["implicit_authority_or_tool_events"] == 0,
    }
    return metrics, gates


def validate_result(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict) or result.get("schema_version") != "7.0" or result.get("evaluation_mode") != "qualification":
        raise EvaluationError("AQ7 result root invalid")
    if result.get("status") == "insufficient_data":
        if set(result) != _INSUFFICIENT or result.get("maximum_claim") is not None or not isinstance(result.get("insufficiency_reason"), str):
            raise EvaluationError("AQ7 insufficient result invalid")
    elif result.get("status") in {"pass", "fail"}:
        if set(result) != _SCORED or result.get("maximum_claim") != CLAIM or not all(_hex(result.get(key)) for key in ("aggregate_digest", "binding_digest", "execution_digest", "schedule_digest")):
            raise EvaluationError("AQ7 aggregate result invalid")
        conditions = result.get("conditions")
        if not isinstance(conditions, list) or [row.get("id") for row in conditions] != list(CONDITIONS) or any(
            row.get("status") not in {"pass", "fail"} or set(row) != {"id", "counts", "metrics", "gates", "status"}
            or not isinstance(row.get("counts"), dict) or set(row["counts"]) != _COUNT_KEYS
            or not isinstance(row.get("metrics"), dict) or set(row["metrics"]) != _METRIC_KEYS
            or not isinstance(row.get("gates"), dict) or set(row["gates"]) != _GATE_KEYS
            or any(type(value) is not int or value < 0 for value in row["counts"].values())
            or any(type(value) not in {int, float} or not 0 <= value <= 1 for value in row["metrics"].values())
            or any(type(value) is not bool for value in row["gates"].values())
            or row["status"] != ("pass" if all(row["gates"].values()) else "fail")
            for row in conditions):
            raise EvaluationError("AQ7 condition aggregate invalid")
        for row in conditions:
            metrics, gates = _aggregate_semantics(row["counts"])
            if row["metrics"] != metrics or row["gates"] != gates or row["status"] != ("pass" if all(gates.values()) else "fail"):
                raise EvaluationError("AQ7 aggregate semantics invalid")
        aggregate_body = {key: result[key] for key in ("binding_digest", "execution_digest", "schedule_digest", "conditions")}
        if result["aggregate_digest"] != _digest(aggregate_body) or result["status"] != ("pass" if all(row["status"] == "pass" for row in conditions) else "fail"):
            raise EvaluationError("AQ7 aggregate digest or status invalid")
        flags = result.get("integrity_flags")
        if not isinstance(flags, dict) or set(flags) != {"binding", "execution", "schedule", "custody", "profile_parity"} or any(value is not True for value in flags.values()):
            raise EvaluationError("AQ7 integrity flags invalid")
    else:
        raise EvaluationError("AQ7 result status invalid")
    if any(result.get(key) is not False for key in _CLAIM_FALSE) or result.get("provider_raw_trajectory_retention_status") != "unknown":
        raise EvaluationError("AQ7 claim ceiling invalid")
    return result


def score_synthetic(envelope: Any, profile: Mapping[str, Any]) -> dict[str, Any]:
    """Score one synthetic-only batch; all custody gaps fail closed as insufficient."""
    if not isinstance(envelope, Mapping) or envelope.get("provenance_mode") != "synthetic":
        return _insufficient("AQ7 public synthetic scorer rejects live provenance")
    try:
        _, records, execution_digest = _validate_envelope(envelope, profile)
        outcomes = [_score_condition(condition, [row for row in records if row["condition"] == condition], profile) for condition in CONDITIONS]
    except (EvaluationError, KeyError, TypeError, ValueError, OSError):
        return _insufficient("AQ7 custody, schedule, binding, parity, or profile validation unavailable")
    body = {"binding_digest": _digest(normalize_binding(envelope["binding"])), "execution_digest": execution_digest, "schedule_digest": envelope["schedule"]["digest"], "conditions": outcomes}
    return validate_result({
        "schema_version": "7.0", "evaluation_mode": "qualification", "status": "pass" if all(row["status"] == "pass" for row in outcomes) else "fail",
        "aggregate_digest": _digest(body), **body,
        "integrity_flags": {"binding": True, "execution": True, "schedule": True, "custody": True, "profile_parity": True},
        "promotion_eligible": False, "runtime_provenance_proven": False, "provider_identity_proven": False,
        "telemetry_attested": False, "product_behavior_proven": False, "runner_local_raw_trajectories_persisted": False,
        "provider_raw_trajectory_retention_status": "unknown", "maximum_claim": CLAIM,
    })


_LIVE_SESSION_TOKEN = object()


class _LiveScoreSession:
    __slots__ = ("_profile", "_binding", "_pid", "_token")
    def __init__(self, profile: Mapping[str, Any], binding: Mapping[str, Any], token: object) -> None:
        if token is not _LIVE_SESSION_TOKEN:
            raise EvaluationError("AQ7 live session construction denied")
        self._profile, self._binding, self._pid, self._token = profile, normalize_binding(binding), os.getpid(), token
    def __reduce__(self) -> Any:
        raise TypeError("AQ7 live session is process-local")
    def __copy__(self) -> Any:
        raise TypeError("AQ7 live session is process-local")
    def __deepcopy__(self, memo: Any) -> Any:
        raise TypeError("AQ7 live session is process-local")
    def score(self, envelope: Any) -> dict[str, Any]:
        if self._token is not _LIVE_SESSION_TOKEN or os.getpid() != self._pid or not isinstance(envelope, Mapping) or envelope.get("provenance_mode") != "live_runner":
            return _insufficient("AQ7 live session unavailable")
        try:
            if normalize_binding(envelope.get("binding")) != self._binding:
                return _insufficient("AQ7 live binding mismatch")
        except (RunIndexError, TypeError, ValueError):
            return _insufficient("AQ7 live binding unavailable")
        # The aggregate implementation is deliberately shared, but the public
        # synthetic entrypoint must never accept this provenance.
        copied = dict(envelope); copied["provenance_mode"] = "synthetic"
        result = score_synthetic(copied, self._profile)
        return result if result["status"] != "insufficient_data" else result


def create_live_score_session(profile: Mapping[str, Any], binding: Mapping[str, Any]) -> _LiveScoreSession:
    """Create a process-local accidental-bypass guard, not a serializable witness."""
    return _LiveScoreSession(profile, binding, _LIVE_SESSION_TOKEN)
