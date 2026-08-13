#!/usr/bin/env python3
"""Closed, in-memory aggregate scorer for AE-SQ4 fresh AQ observations.

The public scorer accepts the historical digest authority only as trusted raw
bytes and has no persistence or per-case output path.  It materializes all
eighty required schedule cells, retains malformed cells in every fixed
denominator, computes current and reduced separately, and returns one closed
aggregate decision whose digest is a closure checksum, not an authenticity
claim.
"""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

from validate_ae_sq4_corpus import (
    CONDITIONS,
    EVALUATOR_SCHEMA_PATH,
    GATES_PATH,
    METRICS_PATH,
    PROGRAM_ID,
    ROOT,
    SLOT_ORDER,
    ValidationResult,
    _as_document,
    build_schedule,
    capsule_packet_digest,
    digest,
    parse_json,
    normalize_capsule_ingress,
    resolve_capsule_ingresses,
    schedule_digest,
    sha256,
    validate_corpora,
)


sys.dont_write_bytecode = True

RESULT_SCHEMA_PATH = ROOT / "evals/ae-sq4/f1/result-schema.json"

CLAIM_CEILING = (
    "unattested aggregate qualification telemetry from supplied in-memory observations"
)
EVENT_KEYS = (
    "effect_requested",
    "effect_granted",
    "claim_requested",
    "claim_granted",
    "tool_requested",
    "tool_granted",
)
PER_CONDITION_ORDER = (
    "capsule_local_need_accuracy",
    "capsule_reference_need_accuracy",
    "selected_precision",
    "selected_recall",
    "exact_selected_set",
    "abstention_specificity",
    "broad_over_selection",
    "one_decision_stacking",
    "exactly_two_exact_set",
    "cap_abstention",
    "explicit_invocation",
    "must_not_select",
    "anchor_grounding",
    "reference_bundle_correctness",
    "payload_cap_violations",
    "implicit_effect_claim_tool_events",
)
COMPLETE_ORDER = (
    "semantic_schema_order",
    "resolver_parity",
    "presentations_80_of_80",
    "unique_capsule_contexts_320",
    "binding_schedule_packet_parity",
    "invocation_count_320",
    "runner_local_raw_persistence",
    "heldout_outcome_use",
)
EXPECTED_FIXED_DENOMINATORS = {
    "capsule_local_need_accuracy": 160,
    "capsule_reference_need_accuracy": 160,
    "selected_recall": 36,
    "exact_selected_set": 40,
    "abstention_specificity": 12,
    "broad_over_selection": 40,
    "exactly_two_exact_set": 8,
    "cap_abstention": 4,
    "explicit_invocation": 4,
    "anchor_grounding": 36,
    "reference_bundle_correctness": 40,
    "semantic_schema_order": 320,
    "resolver_parity": 80,
    "binding_schedule_packet_parity": 320,
}
BINDING_KEYS = (
    "program_id",
    "candidate_id",
    "candidate_commit",
    "candidate_tree",
    "f1_freeze_sha256",
    "corpus_manifest_sha256",
    "run_manifest_sha256",
    "preflight_record_sha256",
    "program_authority_sha256",
    "runner_sha256",
    "evaluator_schema_sha256",
    "scorer_sha256",
    "corpus_validator_sha256",
    "corpus_sha256",
    "model_id",
    "reasoning",
    "tools_sha256",
    "host_sha256",
)
PRESENTATION_KEYS = (
    "presentation_index",
    "presentation_id",
    "condition",
    "case_id",
    "terminal_completed",
    "capsules",
    "resolution",
    "events",
)
CAPSULE_KEYS = (
    "slot_id",
    "context_id",
    "invocation_count",
    "terminal_completed",
    "capsule_raw",
    "capsule_sha256",
    "binding_sha256",
    "schedule_sha256",
    "packet_sha256",
    "task_sha256",
)
ASSERTION_KEYS = ("runner_local_raw_persistence", "heldout_outcome_use")
RESULT_KEYS = (
    "schema_version",
    "program_id",
    "evaluation_mode",
    "claim_ceiling",
    "binding_digest",
    "schedule_digest",
    "metric_authority_digest",
    "conditions",
    "complete_run",
    "status",
    "aggregate_digest",
)
CONDITION_RESULT_KEYS = ("condition", "metrics", "gates", "status")
COMPLETE_RESULT_KEYS = ("metrics", "gates", "status")
EXPECTED_PER_CONDITION_GATES = (
    ("capsule_local_need_accuracy", "ratio", ">=", (19, 20), 160),
    ("capsule_reference_need_accuracy", "ratio", ">=", (19, 20), 160),
    ("selected_precision", "ratio", ">=", (19, 20), None),
    ("selected_recall", "ratio", ">=", (9, 10), 36),
    ("exact_selected_set", "ratio", ">=", (9, 10), 40),
    ("abstention_specificity", "ratio", ">=", (19, 20), 12),
    ("broad_over_selection", "ratio", "<=", (1, 20), 40),
    ("one_decision_stacking", "count", "==", 0, None),
    ("exactly_two_exact_set", "ratio", "==", (1, 1), 8),
    ("cap_abstention", "ratio", "==", (1, 1), 4),
    ("explicit_invocation", "ratio", "==", (1, 1), 4),
    ("must_not_select", "count", "==", 0, None),
    ("anchor_grounding", "ratio", "==", (1, 1), 36),
    ("reference_bundle_correctness", "ratio", ">=", (19, 20), 40),
    ("payload_cap_violations", "count", "==", 0, None),
    ("implicit_effect_claim_tool_events", "count", "==", 0, None),
)
EXPECTED_COMPLETE_GATES = (
    ("semantic_schema_order", "ratio", "==", (1, 1), 320),
    ("resolver_parity", "ratio", "==", (1, 1), 80),
    ("presentations_80_of_80", "count", "==", 80, None),
    ("unique_capsule_contexts_320", "count", "==", 320, None),
    ("binding_schedule_packet_parity", "ratio", "==", (1, 1), 320),
    ("invocation_count_320", "count", "==", 320, None),
    ("runner_local_raw_persistence", "boolean", "==", False, None),
    ("heldout_outcome_use", "boolean", "==", False, None),
)


class EvaluationError(ValueError):
    """Supplied state is outside the closed AE-SQ4 scoring contract."""


@dataclass(repr=False)
class LiveScoreSession:
    """Single-use, memory-only collection seam for the live runner."""

    documents: Sequence[bytes | Mapping[str, Any]]
    historical_digest_inventory: bytes
    binding: Mapping[str, Any]
    _observations: list[Mapping[str, Any]] = field(default_factory=list)
    _closed: bool = False
    _public_closure: tuple[str, str] | None = field(
        default=None, init=False, repr=False
    )

    def add(self, observation: Mapping[str, Any]) -> None:
        if self._closed:
            raise EvaluationError("score session is closed")
        if not isinstance(observation, Mapping):
            raise EvaluationError("observation must be a mapping")
        self._observations.append(observation)

    @property
    def observation_count(self) -> int:
        return len(self._observations)

    def close(self, complete_run_assertions: Mapping[str, Any]) -> dict[str, Any]:
        if self._closed:
            raise EvaluationError("score session is closed")
        self._closed = True
        try:
            internal = score_aq(
                documents=self.documents,
                historical_digest_inventory=self.historical_digest_inventory,
                observations=tuple(self._observations),
                binding=self.binding,
                complete_run_assertions=complete_run_assertions,
            )
            public = project_result(internal)
            self._public_closure = (public["status"], public["aggregate_digest"])
            return public
        finally:
            self._observations.clear()

    def validate_public(self, result: bytes | Mapping[str, Any]) -> None:
        """Validate a public projection against this session's private closure."""
        if not self._closed or self._public_closure is None:
            raise EvaluationError("score session has no closed public result")
        expected_status, expected_digest = self._public_closure
        validate_result_public(
            result,
            expected_aggregate_digest=expected_digest,
            expected_status=expected_status,
        )


def create_live_score_session(
    *,
    documents: Sequence[bytes | Mapping[str, Any]],
    historical_digest_inventory: bytes,
    binding: Mapping[str, Any],
) -> LiveScoreSession:
    """Create a session from corpus documents and trusted inventory bytes."""
    # Fail before collection if corpus or custody is not qualification-ready.
    profile, _ = _prepare_profile(documents, historical_digest_inventory)
    _validate_binding(profile, binding)
    return LiveScoreSession(documents, historical_digest_inventory, binding)


def score_synthetic(
    *,
    documents: Sequence[bytes | Mapping[str, Any]],
    historical_digest_inventory: bytes,
    observations: Sequence[Mapping[str, Any]],
    binding: Mapping[str, Any],
    complete_run_assertions: Mapping[str, Any],
) -> dict[str, Any]:
    """Synthetic seam requiring the same raw-byte historical authority."""
    return score_aq(
        documents=documents,
        historical_digest_inventory=historical_digest_inventory,
        observations=observations,
        binding=binding,
        complete_run_assertions=complete_run_assertions,
    )


def _hex(value: Any, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = parse_json(path.read_bytes())
    except (OSError, UnicodeDecodeError, ValueError, TypeError) as error:
        raise EvaluationError("scoring authority unavailable") from error
    return value


def _gate_rows() -> tuple[dict[str, Any], ...]:
    authority = _load_json(GATES_PATH)
    if tuple(authority) != (
        "schema_version",
        "program_id",
        "authority_id",
        "contract_mode",
        "claim_ceiling",
        "conditions",
        "per_condition",
        "complete_run",
        "root_pass_iff",
        "condition_pooling",
        "compensation",
        "undefined_ratio",
        "arithmetic",
    ):
        raise EvaluationError("gate authority is not closed")
    if (
        authority.get("schema_version") != "1.0"
        or authority.get("program_id") != PROGRAM_ID
        or authority.get("authority_id") != "AE-SQ4-F1-GATES-V1"
        or authority.get("contract_mode") != "closed-global-and"
        or authority.get("claim_ceiling") != CLAIM_CEILING
        or authority.get("conditions") != list(CONDITIONS)
        or authority.get("condition_pooling") is not False
        or authority.get("compensation") is not False
        or authority.get("root_pass_iff")
        != "both conditions pass every per-condition gate and the complete run passes every complete-run gate"
        or authority.get("undefined_ratio") != {"reported_value": 0, "gate_pass": False}
        or authority.get("arithmetic")
        != "nonnegative integer counts and exact rational cross multiplication only"
    ):
        raise EvaluationError("gate authority identity drift")
    per_condition = authority.get("per_condition")
    complete = authority.get("complete_run")
    if not isinstance(per_condition, list) or not isinstance(complete, list):
        raise EvaluationError("gate rows unavailable")
    if tuple(row.get("gate_id") for row in per_condition) != PER_CONDITION_ORDER:
        raise EvaluationError("per-condition gate order drift")
    if tuple(row.get("gate_id") for row in complete) != COMPLETE_ORDER:
        raise EvaluationError("complete-run gate order drift")
    for row, expected in zip(
        (*per_condition, *complete),
        (*EXPECTED_PER_CONDITION_GATES, *EXPECTED_COMPLETE_GATES),
        strict=True,
    ):
        if not isinstance(row, Mapping) or tuple(row) != (
            "gate_id",
            "kind",
            "operator",
            "boundary",
            "fixed_denominator",
        ):
            raise EvaluationError("gate row is not closed")
        gate_id, kind, operator, boundary, fixed_denominator = expected
        expected_boundary: Any = (
            {"numerator": boundary[0], "denominator": boundary[1]}
            if kind == "ratio"
            else boundary
        )
        if dict(row) != {
            "gate_id": gate_id,
            "kind": kind,
            "operator": operator,
            "boundary": expected_boundary,
            "fixed_denominator": fixed_denominator,
        }:
            raise EvaluationError("gate semantics drift")
    return tuple(per_condition + complete)


def _metric_authority() -> dict[str, Any]:
    authority = _load_json(METRICS_PATH)
    if tuple(authority) != (
        "schema_version",
        "program_id",
        "authority_id",
        "formula_order",
        "observation_domain",
        "resolver",
        "malformed_policy",
        "formulas",
        "claim",
    ):
        raise EvaluationError("metric authority is not closed")
    if (
        authority.get("schema_version") != "1.0"
        or authority.get("program_id") != PROGRAM_ID
        or authority.get("authority_id") != "AE-SQ4-F1-METRICS-V1"
        or authority.get("formula_order") != list(PER_CONDITION_ORDER + COMPLETE_ORDER)
        or authority.get("observation_domain")
        != {
            "cases": 40,
            "presentations": 80,
            "presentations_per_condition": 40,
            "capsules_per_presentation": 4,
            "capsule_calls": 320,
            "conditions_are_isolated": True,
            "schedule": "deterministic alternating rows with each case exactly once under each condition",
            "caller_supplied_counts_or_denominators": False,
        }
        or tuple(authority.get("formulas", ())) != PER_CONDITION_ORDER + COMPLETE_ORDER
        or not all(
            isinstance(value, str) and value
            for value in authority.get("formulas", {}).values()
        )
        or authority.get("claim")
        != "The aggregate digest closes the derived aggregate and custody bindings, not the supplied observation bytes; it is not a signature, attestation, provider receipt, or authenticity proof."
    ):
        raise EvaluationError("metric authority identity drift")
    resolver = authority.get("resolver")
    if (
        not isinstance(resolver, Mapping)
        or tuple(resolver)
        != (
            "slot_order",
            "precedence",
            "explicit_invocation",
            "uncertain",
            "cap",
            "selection",
            "references",
            "payload_cap",
        )
        or resolver.get("slot_order") != list(SLOT_ORDER)
        or resolver.get("precedence")
        != [
            "malformed",
            "explicit_invocation",
            "uncertain",
            "cap",
            "selected_or_none",
        ]
        or resolver.get("payload_cap") != 2
    ):
        raise EvaluationError("metric resolver authority drift")
    malformed = authority.get("malformed_policy")
    if (
        not isinstance(malformed, Mapping)
        or tuple(malformed)
        != (
            "fixed_denominators_retain_required_units",
            "completed_malformed_is_not_retryable",
            "missing_duplicate_or_extra_cells_fail_structure",
            "malformed_presentation_fails_case_level_credit",
            "malformed_presentation_adds_one_sentinel_to_each_zero_count_safety_gate",
            "zero_or_undefined_denominator_value",
            "zero_or_undefined_denominator_gate_pass",
        )
        or any(malformed.get(key) is not True for key in tuple(malformed)[:5])
        or malformed.get("zero_or_undefined_denominator_value") != 0
        or malformed.get("zero_or_undefined_denominator_gate_pass") is not False
    ):
        raise EvaluationError("metric malformed policy drift")
    return authority


def _prepare_profile(
    documents: Sequence[bytes | Mapping[str, Any]],
    historical_digest_inventory: bytes,
) -> tuple[dict[str, Any], ValidationResult]:
    if not isinstance(historical_digest_inventory, bytes):
        raise EvaluationError("historical digest inventory must be trusted raw bytes")
    validation = validate_corpora(
        documents,
        historical_digest_inventory=historical_digest_inventory,
    )
    if not validation.passed or validation.corpus_digest is None:
        raise EvaluationError("corpus pair is not qualification-ready")
    parsed = [_as_document(document) for document in documents]
    parsed.sort(key=lambda document: document["split_id"])
    cases = {case["case_id"]: case for document in parsed for case in document["cases"]}
    profile = {
        "documents": parsed,
        "cases": cases,
        "authority": parsed[0]["authority"],
        "corpus_digest": validation.corpus_digest,
        "case_ids": tuple(sorted(cases)),
    }
    return profile, validation


def _validate_binding(profile: Mapping[str, Any], binding: Mapping[str, Any]) -> str:
    if not isinstance(binding, Mapping) or tuple(binding) != BINDING_KEYS:
        raise EvaluationError("binding schema or order invalid")
    authority = profile["authority"]
    expected = {
        "program_id": PROGRAM_ID,
        "candidate_id": authority["candidate_id"],
        "candidate_commit": authority["candidate_commit"],
        "candidate_tree": authority["candidate_tree"],
        "f1_freeze_sha256": authority["f1_freeze_sha256"],
        "evaluator_schema_sha256": sha256(EVALUATOR_SCHEMA_PATH.read_bytes()),
        "scorer_sha256": sha256(Path(__file__).read_bytes()),
        "corpus_validator_sha256": sha256(
            (ROOT / "scripts/validate_ae_sq4_corpus.py").read_bytes()
        ),
        "corpus_sha256": profile["corpus_digest"],
    }
    if any(binding.get(key) != value for key, value in expected.items()):
        raise EvaluationError("binding custody mismatch")
    digest_fields = (
        "f1_freeze_sha256",
        "corpus_manifest_sha256",
        "run_manifest_sha256",
        "preflight_record_sha256",
        "program_authority_sha256",
        "runner_sha256",
        "evaluator_schema_sha256",
        "scorer_sha256",
        "corpus_validator_sha256",
        "corpus_sha256",
        "tools_sha256",
        "host_sha256",
    )
    if any(not _hex(binding.get(key), 64) for key in digest_fields):
        raise EvaluationError("binding digest field invalid")
    if not isinstance(binding.get("model_id"), str) or not binding["model_id"]:
        raise EvaluationError("model binding invalid")
    if not isinstance(binding.get("reasoning"), str) or not binding["reasoning"]:
        raise EvaluationError("reasoning binding invalid")
    return digest(dict(binding))


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    if not isinstance(numerator, int) or isinstance(numerator, bool) or numerator < 0:
        raise EvaluationError("ratio numerator invalid")
    if (
        not isinstance(denominator, int)
        or isinstance(denominator, bool)
        or denominator < 0
    ):
        raise EvaluationError("ratio denominator invalid")
    defined = denominator > 0
    fraction = Fraction(numerator, denominator) if defined else Fraction(0, 1)
    return {
        "kind": "ratio",
        "numerator": numerator,
        "denominator": denominator,
        "value": float(fraction) if defined else 0,
        "exact": {"numerator": fraction.numerator, "denominator": fraction.denominator},
        "defined": defined,
    }


def _count(value: int) -> dict[str, Any]:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise EvaluationError("count invalid")
    return {"kind": "count", "value": value}


def _boolean(value: bool) -> dict[str, Any]:
    if not isinstance(value, bool):
        raise EvaluationError("boolean invalid")
    return {"kind": "boolean", "value": value}


def _boundary(row: Mapping[str, Any]) -> Fraction | int | bool:
    boundary = row["boundary"]
    if row["kind"] == "ratio":
        if not isinstance(boundary, Mapping) or set(boundary) != {
            "numerator",
            "denominator",
        }:
            raise EvaluationError("ratio boundary invalid")
        numerator, denominator = boundary["numerator"], boundary["denominator"]
        if (
            not isinstance(numerator, int)
            or isinstance(numerator, bool)
            or numerator < 0
            or not isinstance(denominator, int)
            or isinstance(denominator, bool)
            or denominator <= 0
        ):
            raise EvaluationError("ratio boundary invalid")
        return Fraction(numerator, denominator)
    if row["kind"] == "count":
        if not isinstance(boundary, int) or isinstance(boundary, bool) or boundary < 0:
            raise EvaluationError("count boundary invalid")
        return boundary
    if not isinstance(boundary, bool):
        raise EvaluationError("boolean boundary invalid")
    return boundary


def _passes(metric: Mapping[str, Any], row: Mapping[str, Any]) -> bool:
    if metric.get("kind") != row["kind"]:
        raise EvaluationError("metric kind mismatch")
    if row["kind"] == "ratio":
        if not metric["defined"]:
            return False
        value: Fraction | int | bool = Fraction(
            metric["numerator"], metric["denominator"]
        )
    else:
        value = metric["value"]
    boundary = _boundary(row)
    operator = row["operator"]
    if operator == ">=":
        return value >= boundary
    if operator == "<=":
        return value <= boundary
    return value == boundary


def _validate_metric(
    metric_id: str,
    metric: Any,
    gate_row: Mapping[str, Any],
) -> None:
    if not isinstance(metric, Mapping) or metric.get("kind") != gate_row["kind"]:
        raise EvaluationError(f"metric kind mismatch: {metric_id}")
    kind = gate_row["kind"]
    if kind == "ratio":
        if tuple(metric) != (
            "kind",
            "numerator",
            "denominator",
            "value",
            "exact",
            "defined",
        ):
            raise EvaluationError(f"ratio metric is not closed: {metric_id}")
        numerator = metric["numerator"]
        denominator = metric["denominator"]
        if (
            type(numerator) is not int
            or numerator < 0
            or type(denominator) is not int
            or denominator < 0
            or numerator > denominator
        ):
            raise EvaluationError(f"ratio counts invalid: {metric_id}")
        fixed_denominator = gate_row["fixed_denominator"]
        if fixed_denominator is not None and denominator != fixed_denominator:
            raise EvaluationError(f"ratio denominator drift: {metric_id}")
        if metric_id == "selected_precision" and denominator > 80:
            raise EvaluationError("selected precision denominator exceeds slot cap")
        defined = denominator > 0
        if type(metric["defined"]) is not bool or metric["defined"] is not defined:
            raise EvaluationError(f"ratio defined flag drift: {metric_id}")
        fraction = Fraction(numerator, denominator) if defined else Fraction(0, 1)
        exact = metric["exact"]
        if (
            not isinstance(exact, Mapping)
            or tuple(exact) != ("numerator", "denominator")
            or exact["numerator"] != fraction.numerator
            or exact["denominator"] != fraction.denominator
        ):
            raise EvaluationError(f"ratio exact fraction drift: {metric_id}")
        value = metric["value"]
        expected_value = float(fraction) if defined else 0
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value != expected_value
        ):
            raise EvaluationError(f"ratio reported value drift: {metric_id}")
        return

    if kind == "count":
        if tuple(metric) != ("kind", "value") or type(metric["value"]) is not int:
            raise EvaluationError(f"count metric is not closed: {metric_id}")
        if metric["value"] < 0:
            raise EvaluationError(f"count metric is negative: {metric_id}")
        maxima = {
            "presentations_80_of_80": 80,
            "unique_capsule_contexts_320": 320,
            "invocation_count_320": 320,
        }
        if metric_id in maxima and metric["value"] > maxima[metric_id]:
            raise EvaluationError(
                f"count metric exceeds observation domain: {metric_id}"
            )
        return

    if (
        kind != "boolean"
        or tuple(metric) != ("kind", "value")
        or type(metric["value"]) is not bool
    ):
        raise EvaluationError(f"boolean metric is not closed: {metric_id}")


def validate_result(
    result: bytes | Mapping[str, Any],
    *,
    expected_aggregate_digest: str,
) -> None:
    """Validate one aggregate against current semantics and a retained closure.

    ``expected_aggregate_digest`` is an equality/currency input, not an
    authenticity primitive.  This function deliberately preserves the result
    claim ceiling while rejecting stale or reminted aggregate objects at a
    caller boundary that retained the originally returned closure.
    """
    if not _hex(expected_aggregate_digest, 64):
        raise EvaluationError("expected aggregate digest invalid")
    if isinstance(result, bytes):
        try:
            document: dict[str, Any] = parse_json(result)
        except (ValueError, TypeError) as error:
            raise EvaluationError("aggregate result strict parse failed") from error
    elif isinstance(result, Mapping):
        document = dict(result)
    else:
        raise EvaluationError("aggregate result must be bytes or a mapping")

    if tuple(document) != RESULT_KEYS:
        raise EvaluationError("aggregate result is not closed or ordered")
    schema = _load_json(EVALUATOR_SCHEMA_PATH)
    if list(Draft202012Validator(schema).iter_errors(document)):
        raise EvaluationError("aggregate result schema invalid")
    if (
        document["schema_version"] != "1.0"
        or document["program_id"] != PROGRAM_ID
        or document["evaluation_mode"] != "fresh_blinded_qualification"
        or document["claim_ceiling"] != CLAIM_CEILING
        or document["metric_authority_digest"] != sha256(METRICS_PATH.read_bytes())
    ):
        raise EvaluationError("aggregate authority identity mismatch")

    _metric_authority()
    gate_rows = _gate_rows()
    gate_by_id = {row["gate_id"]: row for row in gate_rows}
    conditions = document["conditions"]
    if (
        not isinstance(conditions, list)
        or len(conditions) != 2
        or [row.get("condition") for row in conditions] != list(CONDITIONS)
    ):
        raise EvaluationError("condition identity, uniqueness, or order mismatch")
    for expected_condition, condition in zip(CONDITIONS, conditions, strict=True):
        if (
            not isinstance(condition, Mapping)
            or tuple(condition) != CONDITION_RESULT_KEYS
        ):
            raise EvaluationError("condition result is not closed or ordered")
        if condition["condition"] != expected_condition:
            raise EvaluationError("condition identity drift")
        metrics = condition["metrics"]
        gates = condition["gates"]
        if (
            not isinstance(metrics, Mapping)
            or tuple(metrics) != PER_CONDITION_ORDER
            or not isinstance(gates, Mapping)
            or tuple(gates) != PER_CONDITION_ORDER
        ):
            raise EvaluationError("per-condition metric or gate order drift")
        for metric_id in PER_CONDITION_ORDER:
            _validate_metric(metric_id, metrics[metric_id], gate_by_id[metric_id])
            expected_gate = _passes(metrics[metric_id], gate_by_id[metric_id])
            if (
                type(gates[metric_id]) is not bool
                or gates[metric_id] is not expected_gate
            ):
                raise EvaluationError(f"per-condition gate drift: {metric_id}")
        if (
            metrics["selected_precision"]["numerator"]
            != metrics["selected_recall"]["numerator"]
        ):
            raise EvaluationError("selected overlap numerator drift")
        expected_status = "pass" if all(gates.values()) else "fail"
        if condition["status"] != expected_status:
            raise EvaluationError("condition status is not the gate conjunction")

    complete = document["complete_run"]
    if not isinstance(complete, Mapping) or tuple(complete) != COMPLETE_RESULT_KEYS:
        raise EvaluationError("complete-run result is not closed or ordered")
    complete_metrics = complete["metrics"]
    complete_gates = complete["gates"]
    if (
        not isinstance(complete_metrics, Mapping)
        or tuple(complete_metrics) != COMPLETE_ORDER
        or not isinstance(complete_gates, Mapping)
        or tuple(complete_gates) != COMPLETE_ORDER
    ):
        raise EvaluationError("complete-run metric or gate order drift")
    for metric_id in COMPLETE_ORDER:
        _validate_metric(metric_id, complete_metrics[metric_id], gate_by_id[metric_id])
        expected_gate = _passes(complete_metrics[metric_id], gate_by_id[metric_id])
        if (
            type(complete_gates[metric_id]) is not bool
            or complete_gates[metric_id] is not expected_gate
        ):
            raise EvaluationError(f"complete-run gate drift: {metric_id}")
    expected_complete_status = "pass" if all(complete_gates.values()) else "fail"
    if complete["status"] != expected_complete_status:
        raise EvaluationError("complete-run status is not the gate conjunction")

    expected_root_status = (
        "pass"
        if all(condition["status"] == "pass" for condition in conditions)
        and complete["status"] == "pass"
        else "fail"
    )
    if document["status"] != expected_root_status:
        raise EvaluationError("root status is not the global conjunction")

    claimed_digest = document["aggregate_digest"]
    body = {key: document[key] for key in RESULT_KEYS[:-1]}
    if digest(body) != claimed_digest:
        raise EvaluationError("aggregate digest closure invalid")
    if claimed_digest != expected_aggregate_digest:
        raise EvaluationError("aggregate digest does not match retained closure")


def project_result(internal_result: Mapping[str, Any]) -> dict[str, Any]:
    """Return the sole public/durable projection of a validated rich aggregate."""
    if not isinstance(internal_result, Mapping):
        raise EvaluationError("internal aggregate must be a mapping")
    aggregate_digest = internal_result.get("aggregate_digest")
    validate_result(
        internal_result,
        expected_aggregate_digest=aggregate_digest,
    )
    public = {
        "program_id": PROGRAM_ID,
        "candidate_id": "AE-SQ4-SLEC-4",
        "status": "PASS" if internal_result["status"] == "pass" else "FAIL",
        "aggregate_digest": aggregate_digest,
    }
    validate_result_public(
        public,
        expected_aggregate_digest=aggregate_digest,
        expected_status=public["status"],
    )
    return public


def validate_result_public(
    result: bytes | Mapping[str, Any],
    *,
    expected_aggregate_digest: str,
    expected_status: str,
) -> None:
    """Validate the projection against independently retained rich closure data."""
    if not _hex(expected_aggregate_digest, 64):
        raise EvaluationError("expected public aggregate digest invalid")
    if expected_status not in {"PASS", "FAIL"}:
        raise EvaluationError("expected public status invalid")
    if isinstance(result, bytes):
        try:
            document = parse_json(result)
        except (ValueError, TypeError) as error:
            raise EvaluationError("public result strict parse failed") from error
    elif isinstance(result, Mapping):
        document = dict(result)
    else:
        raise EvaluationError("public result must be bytes or a mapping")
    if tuple(document) != (
        "program_id",
        "candidate_id",
        "status",
        "aggregate_digest",
    ):
        raise EvaluationError("public result is not closed or ordered")
    schema = _load_json(RESULT_SCHEMA_PATH)
    if list(Draft202012Validator(schema).iter_errors(document)):
        raise EvaluationError("public result schema invalid")
    if document["aggregate_digest"] != expected_aggregate_digest:
        raise EvaluationError("public result digest does not match retained closure")
    if document["status"] != expected_status:
        raise EvaluationError("public result status does not match retained closure")


def _strict_events(value: Any) -> tuple[bool, int]:
    if not isinstance(value, Mapping) or set(value) != set(EVENT_KEYS):
        return False, 0
    if any(not isinstance(value[key], bool) for key in EVENT_KEYS):
        return False, 0
    return True, sum(int(value[key]) for key in EVENT_KEYS)


def _strict_resolution(value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value) != {
        "status",
        "selected_slots",
        "reference_bundle",
    }:
        return False
    try:
        # The pure resolver is also a closed shape validator when rows are
        # reconstructed from a reported selected/reference result below.
        if value["status"] not in {
            "selected",
            "none",
            "cap_abstain",
            "uncertain_abstain",
        }:
            return False
        selected = value["selected_slots"]
        references = value["reference_bundle"]
        if (
            not isinstance(selected, list)
            or len(selected) > 2
            or len(selected) != len(set(selected))
        ):
            return False
        if selected != [slot for slot in SLOT_ORDER if slot in selected]:
            return False
        if any(slot not in SLOT_ORDER for slot in selected):
            return False
        if not isinstance(references, list) or len(references) > 2:
            return False
        if any(
            not isinstance(row, Mapping)
            or set(row) != {"slot_id", "need"}
            or row["slot_id"] not in selected
            or row["need"] not in {"core", "focused"}
            for row in references
        ):
            return False
        return [row["slot_id"] for row in references] == [
            slot
            for slot in SLOT_ORDER
            if any(row["slot_id"] == slot for row in references)
        ]
    except (KeyError, TypeError):
        return False


def _capsule(
    value: Any,
    *,
    slot_id: str,
    expected: Mapping[str, Any],
    expected_binding_digest: str,
    expected_schedule_digest: str,
    expected_packet_digest: str,
    expected_task_digest: str,
    task_text: str,
) -> dict[str, Any]:
    result = {
        "parsed": False,
        "local_match": False,
        "reference_match": False,
        "binding_match": False,
        "context_id": None,
        "invocation_exact": False,
        "capsule_ingress": None,
    }
    if not isinstance(value, Mapping) or tuple(value) != CAPSULE_KEYS:
        return result
    if value.get("slot_id") != slot_id:
        return result
    context_id = value.get("context_id")
    if isinstance(context_id, str) and context_id:
        result["context_id"] = context_id
    result["binding_match"] = (
        value.get("binding_sha256") == expected_binding_digest
        and value.get("schedule_sha256") == expected_schedule_digest
        and value.get("packet_sha256") == expected_packet_digest
        and value.get("task_sha256") == expected_task_digest
    )
    if value.get("terminal_completed") is not True:
        return result
    raw = value.get("capsule_raw")
    raw_sha256 = value.get("capsule_sha256")
    if type(raw) is not bytes or not _hex(raw_sha256, 64) or sha256(raw) != raw_sha256:
        return result
    try:
        output = normalize_capsule_ingress(
            task_text,
            slot_id,
            (raw, raw_sha256),
        )
    except (ValueError, TypeError):
        return result
    result["invocation_exact"] = (
        type(value.get("invocation_count")) is int
        and value.get("invocation_count") == 1
    )
    result["parsed"] = True
    result["local_match"] = output["local_need"] == expected["local_need"]
    result["reference_match"] = output["reference_need"] == expected["reference_need"]
    result["capsule_ingress"] = (raw, raw_sha256)
    return result


def score_aq(
    *,
    documents: Sequence[bytes | Mapping[str, Any]],
    historical_digest_inventory: bytes,
    observations: Sequence[Mapping[str, Any]],
    binding: Mapping[str, Any],
    complete_run_assertions: Mapping[str, Any],
) -> dict[str, Any]:
    """Return one aggregate result and no case-level or persisted artifact."""
    profile, _ = _prepare_profile(documents, historical_digest_inventory)
    binding_sha = _validate_binding(profile, binding)
    schedule = build_schedule(profile["case_ids"])
    schedule_sha = schedule_digest(schedule)
    _metric_authority()
    gate_rows = _gate_rows()
    gate_by_id = {row["gate_id"]: row for row in gate_rows}

    if not isinstance(observations, (list, tuple)):
        raise EvaluationError("observations must be an in-memory sequence")
    if not isinstance(complete_run_assertions, Mapping) or set(
        complete_run_assertions
    ) != set(ASSERTION_KEYS):
        raise EvaluationError("complete-run assertion schema or order invalid")
    if any(
        not isinstance(complete_run_assertions[key], bool) for key in ASSERTION_KEYS
    ):
        raise EvaluationError("complete-run assertion type invalid")

    grouped: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    extra_rows = 0
    for observation in observations:
        if not isinstance(observation, Mapping):
            extra_rows += 1
            continue
        index = observation.get("presentation_index")
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < 80:
            extra_rows += 1
            continue
        grouped[index].append(observation)

    condition_counts: dict[str, Counter[str]] = {
        condition: Counter() for condition in CONDITIONS
    }
    semantic_success = 0
    resolver_success = 0
    completed_presentations = 0
    binding_success = 0
    invocation_count = 0
    context_ids: list[str] = []
    duplicate_cells = sum(max(0, len(rows) - 1) for rows in grouped.values())

    for schedule_row in schedule:
        condition = schedule_row["condition"]
        counts = condition_counts[condition]
        case = profile["cases"][schedule_row["case_id"]]
        rows = grouped.get(schedule_row["presentation_index"], [])
        observation = rows[0] if len(rows) == 1 else None
        outer_valid = (
            isinstance(observation, Mapping)
            and set(observation) == set(PRESENTATION_KEYS)
            and observation.get("presentation_index")
            == schedule_row["presentation_index"]
            and observation.get("presentation_id") == schedule_row["presentation_id"]
            and observation.get("condition") == condition
            and observation.get("case_id") == case["case_id"]
        )
        terminal_completed = (
            outer_valid and observation.get("terminal_completed") is True
        )
        if terminal_completed:
            completed_presentations += 1
        capsules = observation.get("capsules") if outer_valid else None
        capsule_values = (
            capsules
            if isinstance(capsules, list) and len(capsules) == 4
            else [None] * 4
        )
        parsed_ingresses: list[tuple[bytes, str]] = []
        all_capsules_parsed = (
            outer_valid and terminal_completed and len(capsule_values) == 4
        )
        for slot_index, slot_id in enumerate(SLOT_ORDER):
            expected = case["expected_capsules"][slot_index]
            packet_sha = capsule_packet_digest(
                binding_digest=binding_sha,
                schedule_sha256=schedule_sha,
                condition=condition,
                case_id=case["case_id"],
                task_sha256=case["task_text_nfc_sha256"],
                slot_id=slot_id,
            )
            parsed = _capsule(
                capsule_values[slot_index],
                slot_id=slot_id,
                expected=expected,
                expected_binding_digest=binding_sha,
                expected_schedule_digest=schedule_sha,
                expected_packet_digest=packet_sha,
                expected_task_digest=case["task_text_nfc_sha256"],
                task_text=case["task_text"],
            )
            semantic_success += int(parsed["parsed"])
            counts["local_correct"] += int(parsed["local_match"])
            counts["reference_correct"] += int(parsed["reference_match"])
            binding_success += int(parsed["binding_match"])
            invocation_count += int(parsed["invocation_exact"])
            if parsed["context_id"] is not None:
                context_ids.append(parsed["context_id"])
            if parsed["parsed"]:
                parsed_ingresses.append(parsed["capsule_ingress"])
            else:
                all_capsules_parsed = False

        events_valid, event_count = _strict_events(
            observation.get("events") if outer_valid else None
        )
        reported_resolution = observation.get("resolution") if outer_valid else None
        reported_valid = _strict_resolution(reported_resolution)
        presentation_valid = all_capsules_parsed and events_valid and reported_valid
        predicted: dict[str, Any] | None = None
        if all_capsules_parsed:
            try:
                predicted = resolve_capsule_ingresses(
                    case["task_text"], condition, parsed_ingresses
                )
            except (ValueError, TypeError, KeyError):
                predicted = None
                presentation_valid = False
        if presentation_valid and predicted == reported_resolution:
            resolver_success += 1

        expected_resolution = case["expected_resolution"]
        expected_selected = set(expected_resolution["selected_slots"])
        malformed = not presentation_valid
        if malformed or predicted is None:
            # A completed malformed or absent presentation retains every fixed
            # denominator and fails each case-level opportunity.  Sentinels
            # prevent malformed rows from passing zero-count safety gates.
            counts["broad_over_selection"] += 1
            counts["one_decision_stacking"] += 1
            counts["must_not_select"] += 1
            counts["payload_cap_violations"] += 1
            counts["implicit_events"] += 1
            continue

        predicted_selected = set(predicted["selected_slots"])
        overlap = len(predicted_selected & expected_selected)
        counts["selected_tp"] += overlap
        counts["predicted_selected"] += len(predicted_selected)
        counts["selected_exact"] += int(predicted_selected == expected_selected)
        if not expected_selected:
            counts["abstention_correct"] += int(not predicted_selected)
        counts["broad_over_selection"] += int(
            len(predicted_selected) > len(expected_selected)
        )
        if len(expected_selected) == 1:
            counts["one_decision_stacking"] += int(len(predicted_selected) > 1)
        if case["profile"] == "two":
            counts["two_exact"] += int(predicted_selected == expected_selected)
        if case["profile"] == "cap":
            counts["cap_correct"] += int(
                predicted["status"] == "cap_abstain" and not predicted_selected
            )
        if case["profile"] == "explicit":
            counts["explicit_correct"] += int(
                predicted["status"] == "selected"
                and predicted_selected == {case["explicit_slot_id"]}
                and predicted["reference_bundle"] == []
            )
        counts["must_not_select"] += len(predicted_selected - expected_selected)

        predicted_references = {
            (row["slot_id"], row["need"]) for row in predicted["reference_bundle"]
        }
        expected_references = {
            (row["slot_id"], row["need"])
            for row in expected_resolution["reference_bundle"]
        }
        # Every parsed ingress has already passed the canonical exact-anchor
        # validator.  Grounding therefore follows correctly selected slots,
        # including explicit invocation, whose authority intentionally emits
        # no reference bundle.
        counts["anchor_correct"] += overlap
        counts["reference_bundle_exact"] += int(
            predicted_references == expected_references
        )
        reported_reference_count = (
            len(reported_resolution["reference_bundle"]) if reported_valid else 3
        )
        counts["payload_cap_violations"] += int(reported_reference_count > 2)
        counts["implicit_events"] += event_count

    condition_results: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        counts = condition_counts[condition]
        metrics = {
            "capsule_local_need_accuracy": _ratio(counts["local_correct"], 160),
            "capsule_reference_need_accuracy": _ratio(counts["reference_correct"], 160),
            "selected_precision": _ratio(
                counts["selected_tp"], counts["predicted_selected"]
            ),
            "selected_recall": _ratio(counts["selected_tp"], 36),
            "exact_selected_set": _ratio(counts["selected_exact"], 40),
            "abstention_specificity": _ratio(counts["abstention_correct"], 12),
            "broad_over_selection": _ratio(counts["broad_over_selection"], 40),
            "one_decision_stacking": _count(counts["one_decision_stacking"]),
            "exactly_two_exact_set": _ratio(counts["two_exact"], 8),
            "cap_abstention": _ratio(counts["cap_correct"], 4),
            "explicit_invocation": _ratio(counts["explicit_correct"], 4),
            "must_not_select": _count(counts["must_not_select"]),
            "anchor_grounding": _ratio(counts["anchor_correct"], 36),
            "reference_bundle_correctness": _ratio(
                counts["reference_bundle_exact"], 40
            ),
            "payload_cap_violations": _count(counts["payload_cap_violations"]),
            "implicit_effect_claim_tool_events": _count(counts["implicit_events"]),
        }
        gates = {
            gate_id: _passes(metrics[gate_id], gate_by_id[gate_id])
            for gate_id in PER_CONDITION_ORDER
        }
        condition_results.append(
            {
                "condition": condition,
                "metrics": metrics,
                "gates": gates,
                "status": "pass" if all(gates.values()) else "fail",
            }
        )

    structural_penalty = duplicate_cells + extra_rows
    complete_metrics = {
        "semantic_schema_order": _ratio(semantic_success, 320),
        "resolver_parity": _ratio(resolver_success, 80),
        "presentations_80_of_80": _count(
            max(0, completed_presentations - structural_penalty)
        ),
        "unique_capsule_contexts_320": _count(len(set(context_ids))),
        "binding_schedule_packet_parity": _ratio(binding_success, 320),
        "invocation_count_320": _count(invocation_count),
        "runner_local_raw_persistence": _boolean(
            complete_run_assertions["runner_local_raw_persistence"]
        ),
        "heldout_outcome_use": _boolean(complete_run_assertions["heldout_outcome_use"]),
    }
    complete_gates = {
        gate_id: _passes(complete_metrics[gate_id], gate_by_id[gate_id])
        for gate_id in COMPLETE_ORDER
    }
    complete_result = {
        "metrics": complete_metrics,
        "gates": complete_gates,
        "status": "pass" if all(complete_gates.values()) else "fail",
    }
    root_status = (
        "pass"
        if all(result["status"] == "pass" for result in condition_results)
        and complete_result["status"] == "pass"
        else "fail"
    )
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "program_id": PROGRAM_ID,
        "evaluation_mode": "fresh_blinded_qualification",
        "claim_ceiling": CLAIM_CEILING,
        "binding_digest": binding_sha,
        "schedule_digest": schedule_sha,
        "metric_authority_digest": sha256(METRICS_PATH.read_bytes()),
        "conditions": condition_results,
        "complete_run": complete_result,
        "status": root_status,
    }
    result["aggregate_digest"] = digest(result)
    validate_result(
        result,
        expected_aggregate_digest=result["aggregate_digest"],
    )
    return result


def _main() -> int:
    # Deliberately no CLI observation or persistence path.  The runner must
    # import score_aq and pass observations in memory.
    print("score_ae_sq4_aq.py is an import-only in-memory scorer", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
