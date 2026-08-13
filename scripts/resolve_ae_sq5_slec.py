#!/usr/bin/env python3
"""AE-SQ5 SLEC-5 slot-local capsule resolver and reference broker.

Task text is untrusted quoted data.  The fold is deterministic and has no
filesystem, network, model, subprocess, or external-effect surface.  Reference
materialization is a separate capability-ID-only boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import struct
import unicodedata
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Sequence

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


class SLECError(ValueError):
    """A closed SLEC-5 contract was violated."""


SLOTS = ("s0", "s1", "s2", "s3")
CONDITIONS = ("current", "reduced")
LOCAL_NEEDS = ("yes", "no", "uncertain")
REFERENCE_NEEDS = ("none", "core", "focused", "uncertain")
CAPABILITIES = (
    ("cap.ae.architecture.core.v4", "cap.ae.architecture.focused.v4"),
    ("cap.ae.task-contract.core.v4", "cap.ae.task-contract.focused.v4"),
    ("cap.ae.verification.core.v4", "cap.ae.verification.focused.v4"),
    ("cap.ae.learning.core.v4", "cap.ae.learning.focused.v4"),
)
ALL_CAPABILITIES = tuple(capability for pair in CAPABILITIES for capability in pair)
CAPSULE_KEYS = ("slot_id", "local_need", "reference_need", "anchors")
ANCHOR_KEYS = ("start", "end", "text")
HEX64 = frozenset("0123456789abcdef")

AUTHORITY_KEYS = (
    "schema_version",
    "authority_id",
    "candidate_id",
    "mechanism_id",
    "status",
    "claim_ceiling",
    "purpose",
    "f0_custody",
    "predecessor_terminal_provenance",
    "model_binding",
    "repair_provenance",
    "condition_contract",
    "slots",
    "assessor_packet_contract",
    "provider_schema_contract",
    "local_semantic_contract",
    "invocation_contract",
    "fold_contract",
    "reference_contract",
    "resolution_contract",
    "resolver_contract",
    "non_isomorphism_witness",
    "security_partition",
    "falsifiers",
    "qualification_boundary",
)
POLICY_KEYS = (
    "schema_version",
    "policy_id",
    "candidate_id",
    "mechanism_id",
    "status",
    "claim_ceiling",
    "catalog_custody",
    "limits",
    "broker_boundary",
    "filesystem_contract",
    "capability_catalog",
    "prohibitions",
)
RESOLUTION_RECORD_KEYS = (
    "record_version",
    "candidate_id",
    "mechanism_id",
    "condition_id",
    "resolution_status",
    "selection_mode",
    "input_custody",
    "slot_outcomes",
    "invocation_evidence",
    "selected_slots",
    "reference_capability_ids",
    "references",
    "claim_ceiling",
)

PROVIDER_KEYWORDS = frozenset(
    {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "description",
        "minItems",
        "maxItems",
        "$defs",
        "$ref",
    }
)
JSON_TYPES = frozenset(
    {"object", "array", "string", "integer", "number", "boolean", "null"}
)
F0_CUSTODY = {
    "commit": "7f4590b284bfb5e5f60bc96c8cdb15e6ff8194c8",
    "tree": "2ffba244f6a4ed40f0743309cbafddf10038cad4",
    "program_authority_path": "evals/ae-sq5/program-authority.json",
    "program_authority_blob": "7d68e68dbaec55472b1c2587fe937638599d5f7b",
    "program_authority_sha256": (
        "be255bdd8e69f56b350b64c6fcec29bff65a59056c910e2e516eb8c4d770ec9d"
    ),
    "active_plan_path": "docs/exec-plans/active/ae-sq5.md",
    "active_plan_blob": "3577740185dbf1693a20362b7d62692ad701b441",
    "active_plan_sha256": (
        "b53759750fe7822265ebff3feeeb4f457b8973d84d735f8160bf6dec2cbe79b4"
    ),
}
PREDECESSOR_TERMINAL_PROVENANCE = {
    "program_id": "AE-SQ4",
    "commit": "7f4590b284bfb5e5f60bc96c8cdb15e6ff8194c8",
    "terminal_decision_path": "evals/ae-sq4/ar/terminal-decision.json",
    "terminal_decision_blob": "d6b31dae97aa324c522e375154152832e741d8a2",
    "terminal_decision_raw_sha256": (
        "d71572df72f6dbf90547388983489e4b87328c5806bcf08b395e6e27bf2b0a12"
    ),
    "stage": "SQ4-AR",
    "status": "terminal",
    "terminal_reason": (
        "sealed-split-authority-bound-F1B-instead-of-required-F1A-implementation"
    ),
    "later_stage_model_calls": 0,
    "candidate_qualification_imported": False,
    "candidate_identity_continued": False,
    "corpus_task_label_or_result_material_imported": False,
    "permitted_use": "terminal-custody-and-provider-repair-source-provenance-only",
}
DIAGNOSTIC_CLASSIFICATION_COUNTS = {
    "transport_spawn": 0,
    "process_exit": 0,
    "signal_exit": 0,
    "timeout": 0,
    "empty_stdout": 0,
    "invalid_jsonl": 0,
    "unknown_event": 0,
    "missing_completed_message": 0,
    "provider_request_rejected": 0,
    "schema_unsupported": 4,
    "schema_invalid": 0,
    "semantic_invalid": 0,
    "valid_completed": 0,
    "other_fail_closed": 0,
}
DIAGNOSTIC_USAGE = {
    "input_tokens": 0,
    "cached_input_tokens": 0,
    "output_tokens": 0,
    "total_tokens": 0,
}
DIAGNOSTIC_BINDING = {
    "path": "evals/ae-sq2/d0/diagnostic-record.json",
    "commit": "e2562ca4da5f3dc14fb07c1522f911e2dfe4334d",
    "blob": "f5dc5b67435c78d0b214ac21fc69531c9bae7d3e",
    "raw_sha256": "1e2352fe42453b03cafac06e9c2e98638af17ad6a3e5dfaf389baf9da39d6502",
    "record_sha256": "5bb323666e5fe54d39df3fb91a65e1dd44c96ac5a4f3c9e967d2481a5eda5e9c",
    "aggregate_sha256": "d333397b1bc0a633d80ac43bbf1ae6e9b5aafdfb6af5b01ad5493f9fb3292235",
}
AUTHORITY_SHA256 = "0dc5f36ae6004d077fbe0927970a3fcf4bf1ccc047eccec95550aad8c18935c8"
POLICY_SHA256 = "df0e05e3af1c84c3f90bb423b2f036261076a5da19fb2cf479f45d084a24acab"


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError) as error:
        raise SLECError("value is not canonical JSON") from error


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _closed(value: Any, keys: Iterable[str], message: str) -> dict[str, Any]:
    expected = tuple(keys)
    if type(value) is not dict or tuple(value) != expected:
        raise SLECError(message)
    return value


def _closed_unordered(value: Any, keys: Iterable[str], message: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != set(keys):
        raise SLECError(message)
    return value


def _valid_hex64(value: Any) -> bool:
    return type(value) is str and len(value) == 64 and set(value) <= HEX64


def _valid_hex40(value: Any) -> bool:
    return type(value) is str and len(value) == 40 and set(value) <= HEX64


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SLECError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise SLECError("non-finite JSON number")


def _decode_json(raw: bytes) -> Any:
    if type(raw) is not bytes:
        raise SLECError("runtime capsule must be exact bytes")
    try:
        text = raw.decode("utf-8", "strict")
        return json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SLECError("runtime capsule is not strict UTF-8 JSON") from error


def _trusted_json(value: Any, label: str) -> tuple[dict[str, Any], str]:
    if type(value) is not tuple or len(value) != 2:
        raise SLECError(f"{label} must be trusted raw bytes plus pinned SHA-256")
    raw, expected_sha256 = value
    if type(raw) is not bytes or not _valid_hex64(expected_sha256):
        raise SLECError(f"{label} custody tuple is invalid")
    if sha256_bytes(raw) != expected_sha256:
        raise SLECError(f"{label} digest mismatch")
    document = _decode_json(raw)
    if type(document) is not dict:
        raise SLECError(f"{label} must be a JSON object")
    return document, expected_sha256


def _resolve_local_ref(root: dict[str, Any], reference: Any) -> dict[str, Any]:
    if type(reference) is not str or not reference.startswith("#/"):
        raise SLECError("provider schema reference must be a local JSON pointer")
    current: Any = root
    for raw_component in reference[2:].split("/"):
        component = raw_component.replace("~1", "/").replace("~0", "~")
        if component in {"", ".", ".."}:
            raise SLECError("provider schema reference escapes its local namespace")
        if type(current) is not dict or component not in current:
            raise SLECError("provider schema reference is dangling")
        current = current[component]
    if type(current) is not dict:
        raise SLECError("provider schema reference target is not a schema")
    return current


def _enum_character_count(value: Any) -> int:
    if type(value) is str:
        return len(value)
    return len(canonical_json(value).decode("ascii"))


def _json_type_matches(value: Any, schema_type: str) -> bool:
    value_type = type(value)
    if schema_type == "string":
        return value_type is str
    if schema_type == "integer":
        return value_type is int
    if schema_type == "number":
        return value_type in {int, float}
    if schema_type == "boolean":
        return value_type is bool
    if schema_type == "null":
        return value is None
    if schema_type == "object":
        return value_type is dict
    if schema_type == "array":
        return value_type is list
    return False


def _provider_resource_state() -> dict[str, Any]:
    return {
        "counted_nodes": set(),
        "total_object_properties": 0,
        "total_enum_values": 0,
        "aggregate_characters": 0,
    }


def _account_provider_resources(node: dict[str, Any], state: dict[str, Any]) -> None:
    identity = id(node)
    if identity in state["counted_nodes"]:
        return
    state["counted_nodes"].add(identity)
    properties = node.get("properties")
    if type(properties) is dict:
        if any(type(name) is not str for name in properties):
            raise SLECError("provider property name is invalid")
        state["total_object_properties"] += len(properties)
        state["aggregate_characters"] += sum(len(name) for name in properties)
    definitions = node.get("$defs")
    if type(definitions) is dict:
        if any(type(name) is not str for name in definitions):
            raise SLECError("provider definition name is invalid")
        state["aggregate_characters"] += sum(len(name) for name in definitions)
    enum = node.get("enum")
    if type(enum) is list:
        state["total_enum_values"] += len(enum)
        state["aggregate_characters"] += sum(
            _enum_character_count(value) for value in enum
        )
        if (
            node.get("type") == "string"
            and len(enum) > 250
            and sum(len(value) for value in enum if type(value) is str) > 15000
        ):
            raise SLECError("provider large string enum character cap exceeded")
    if "const" in node:
        state["aggregate_characters"] += _enum_character_count(node["const"])
    if state["total_object_properties"] > 5000:
        raise SLECError("provider object property cap exceeded")
    if state["total_enum_values"] > 1000:
        raise SLECError("provider enum value cap exceeded")
    if state["aggregate_characters"] > 120000:
        raise SLECError("provider aggregate schema character cap exceeded")


def _lint_provider_node(
    node: Any,
    *,
    root: dict[str, Any],
    active_references: frozenset[str] = frozenset(),
    _state: dict[str, Any] | None = None,
    _depth: int = 1,
) -> None:
    if type(node) is not dict or not node:
        raise SLECError("provider schema node must be a nonempty object")
    state = _provider_resource_state() if _state is None else _state
    _account_provider_resources(node, state)
    unknown = set(node) - PROVIDER_KEYWORDS
    if unknown:
        raise SLECError("provider schema uses an undeclared keyword")
    if "$ref" in node:
        if set(node) != {"$ref"}:
            raise SLECError("provider schema reference siblings are forbidden")
        reference = node["$ref"]
        if reference in active_references:
            raise SLECError("provider schema reference cycle is forbidden")
        _lint_provider_node(
            _resolve_local_ref(root, reference),
            root=root,
            active_references=active_references | {reference},
            _state=state,
            _depth=_depth,
        )
        return
    schema_type = node.get("type")
    if type(schema_type) is not str or schema_type not in JSON_TYPES:
        raise SLECError("provider schema type is invalid")
    if _depth > 10:
        raise SLECError("provider schema nesting cap exceeded")
    if "description" in node and type(node["description"]) is not str:
        raise SLECError("provider schema description is invalid")
    if "enum" in node:
        enum = node["enum"]
        if (
            type(enum) is not list
            or not enum
            or len({canonical_json(value) for value in enum}) != len(enum)
            or any(not _json_type_matches(value, schema_type) for value in enum)
        ):
            raise SLECError("provider schema enum is invalid")
    if schema_type == "object":
        properties = node.get("properties")
        required = node.get("required")
        if (
            type(properties) is not dict
            or type(required) is not list
            or any(type(key) is not str for key in required)
            or len(required) != len(set(required))
            or required != list(properties)
            or node.get("additionalProperties") is not False
        ):
            raise SLECError("provider object schema is not recursively closed")
        if any(key in node for key in ("items", "minItems", "maxItems")):
            raise SLECError("provider object schema has array keywords")
        for child in properties.values():
            _lint_provider_node(child, root=root, _state=state, _depth=_depth + 1)
    elif schema_type == "array":
        if "items" not in node or any(
            key in node for key in ("properties", "required", "additionalProperties")
        ):
            raise SLECError("provider array schema is invalid")
        for key in ("minItems", "maxItems"):
            if key in node and (type(node[key]) is not int or node[key] < 0):
                raise SLECError("provider array bound is invalid")
        if node.get("minItems", 0) > node.get("maxItems", 2**63 - 1):
            raise SLECError("provider array bounds are inverted")
        _lint_provider_node(node["items"], root=root, _state=state, _depth=_depth + 1)
    elif any(
        key in node
        for key in (
            "properties",
            "required",
            "additionalProperties",
            "items",
            "minItems",
            "maxItems",
        )
    ):
        raise SLECError("provider scalar schema has structural keywords")
    if "$defs" in node:
        definitions = node["$defs"]
        if type(definitions) is not dict or not definitions:
            raise SLECError("provider schema definitions are invalid")
        for child in definitions.values():
            _lint_provider_node(child, root=root, _state=state, _depth=1)


def validate_provider_schema(
    schema_custody: Any, authority_custody: Any
) -> dict[str, Any]:
    """Authenticate and recursively lint a provider-facing schema."""
    authority, _ = _trusted_authority(authority_custody)
    schema, digest = _trusted_json(schema_custody, "SLEC-5 provider schema")
    contract = authority["provider_schema_contract"]
    if contract["capsule_schema_path"] != "evals/ae-sq5/f1/slec5-capsule-schema.json":
        raise SLECError("provider schema path binding is invalid")
    if digest != contract["capsule_schema_sha256"]:
        raise SLECError("provider schema is not authority-pinned")
    if tuple(contract["permitted_keywords"]) != (
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "description",
        "minItems",
        "maxItems",
        "$defs",
        "$ref",
    ):
        raise SLECError("provider keyword allowlist binding is invalid")
    _lint_provider_node(schema, root=schema)
    return deepcopy(schema)


def _task_text(value: Any) -> tuple[str, bytes]:
    if type(value) is bytes:
        try:
            return value.decode("utf-8", "strict"), value
        except UnicodeDecodeError as error:
            raise SLECError("task is not strict UTF-8") from error
    if type(value) is not str:
        raise SLECError("task text must be a string or UTF-8 bytes")
    try:
        return value, value.encode("utf-8", "strict")
    except UnicodeEncodeError as error:
        raise SLECError("task text contains an invalid Unicode scalar") from error


def _authority_slots(authority: Any) -> tuple[dict[str, Any], ...]:
    _closed(authority, AUTHORITY_KEYS, "SLEC-5 authority is not closed")
    if (
        authority["schema_version"] != "4.0"
        or authority["authority_id"] != "AE-SQ5-SLEC-5"
        or authority["candidate_id"] != "AE-SQ5-SLEC-5"
        or authority["mechanism_id"] != "SLEC-5"
        or authority["status"] != "f1a-implementation"
        or authority["claim_ceiling"] != "structural-candidate-implementation-only"
    ):
        raise SLECError("SLEC-5 authority identity is invalid")
    f0 = _closed(
        authority["f0_custody"],
        F0_CUSTODY,
        "F0 custody is not closed",
    )
    if f0 != F0_CUSTODY:
        raise SLECError("F0 custody is invalid")
    predecessor = _closed(
        authority["predecessor_terminal_provenance"],
        PREDECESSOR_TERMINAL_PROVENANCE,
        "predecessor terminal provenance is not closed",
    )
    if predecessor != PREDECESSOR_TERMINAL_PROVENANCE:
        raise SLECError("predecessor terminal provenance is invalid")
    model = _closed(
        authority["model_binding"],
        ("model_id", "reasoning_effort", "fallback_permitted", "live_phases_only"),
        "model binding is not closed",
    )
    if model != {
        "model_id": "gpt-5.5",
        "reasoning_effort": "medium",
        "fallback_permitted": False,
        "live_phases_only": ["SQ5-F4", "SQ5-F5"],
    }:
        raise SLECError("model binding is invalid")
    repair = _closed(
        authority["repair_provenance"],
        (
            "kind",
            "calls_started",
            "calls_completed",
            "classification_counts",
            "usage",
            "permitted_use",
            "qualification_effect",
            "behavioral_tuning_permitted",
            "evaluator_tuning_permitted",
            "corpus_or_label_use_permitted",
            "raw_or_event_material_imported",
            "diagnostic_binding",
        ),
        "repair provenance is not closed",
    )
    classification_counts = _closed(
        repair["classification_counts"],
        DIAGNOSTIC_CLASSIFICATION_COUNTS,
        "diagnostic classification counts are not closed",
    )
    usage = _closed(
        repair["usage"],
        DIAGNOSTIC_USAGE,
        "diagnostic usage is not closed",
    )
    diagnostic_binding = _closed(
        repair["diagnostic_binding"],
        DIAGNOSTIC_BINDING,
        "diagnostic binding is not closed",
    )
    if (
        repair["kind"] != "bounded-non-corpus-interface-diagnosis-only"
        or repair["calls_started"] != 4
        or repair["calls_completed"] != 4
        or classification_counts != DIAGNOSTIC_CLASSIFICATION_COUNTS
        or usage != DIAGNOSTIC_USAGE
        or repair["permitted_use"]
        != "select-provider-schema-compatibility-repair-and-no-other-purpose"
        or repair["qualification_effect"] != "none"
        or any(
            repair[key] is not False
            for key in (
                "behavioral_tuning_permitted",
                "evaluator_tuning_permitted",
                "corpus_or_label_use_permitted",
                "raw_or_event_material_imported",
            )
        )
        or diagnostic_binding != DIAGNOSTIC_BINDING
    ):
        raise SLECError("bounded diagnostic binding is invalid")
    condition = _closed(
        authority["condition_contract"],
        (
            "condition_order",
            "same_mechanism_for_both",
            "expected_labels_condition_invariant",
            "card_bytes_must_differ_between_conditions",
            "model_visible_card_projection",
            "condition_must_not_change",
        ),
        "condition contract is not closed",
    )
    if (
        condition["condition_order"] != list(CONDITIONS)
        or condition["same_mechanism_for_both"] is not True
        or condition["expected_labels_condition_invariant"] is not True
        or condition["card_bytes_must_differ_between_conditions"] is not True
        or condition["model_visible_card_projection"]
        != ["description", "decision_scope"]
    ):
        raise SLECError("condition contract is invalid")
    slots = authority["slots"]
    if type(slots) is not list or len(slots) != 4:
        raise SLECError("slot authority is invalid")
    for index, slot in enumerate(slots):
        _closed(
            slot,
            (
                "slot_id",
                "assessor_id",
                "capability_ids",
                "qualified_invocation",
                "cards",
            ),
            "slot authority is not closed",
        )
        if slot["slot_id"] != SLOTS[index]:
            raise SLECError("slot authority order is invalid")
        capabilities = _closed(
            slot["capability_ids"],
            ("core", "focused"),
            "slot capability mapping is not closed",
        )
        if tuple(capabilities.values()) != CAPABILITIES[index]:
            raise SLECError("slot capability mapping is invalid")
        cards = _closed(slot["cards"], CONDITIONS, "condition cards are not closed")
        for condition_id in CONDITIONS:
            card = _closed(
                cards[condition_id],
                ("condition_id", "slot_id", "body", "source_binding"),
                "condition card is not closed",
            )
            if card["condition_id"] != condition_id or card["slot_id"] != SLOTS[index]:
                raise SLECError("condition card identity is invalid")
            body = _closed(
                card["body"],
                ("description", "decision_scope"),
                "condition card body is not closed",
            )
            if any(type(value) is not str or not value for value in body.values()):
                raise SLECError("condition card body is invalid")
            source = _closed(
                card["source_binding"],
                (
                    "source_kind",
                    "commit",
                    "path",
                    "sha256",
                    "description_selector",
                    "decision_scope_heading",
                    "decision_scope_paragraph_index",
                ),
                "condition source binding is not closed",
            )
            if (
                source["source_kind"] != "newly-bound-structural-source"
                or source["commit"] != authority["f0_custody"]["commit"]
                or not _valid_hex64(source["sha256"])
                or type(source["path"]) is not str
                or type(source["decision_scope_paragraph_index"]) is not int
            ):
                raise SLECError("condition source binding is invalid")
        if canonical_json(cards["current"]["body"]) == canonical_json(
            cards["reduced"]["body"]
        ):
            raise SLECError("condition card bodies must differ")
    packet = _closed(
        authority["assessor_packet_contract"],
        ("packet_keys", "instruction", "condition_menus", "independence"),
        "assessor packet contract is not closed",
    )
    if packet["packet_keys"] != [
        "instruction",
        "task_text",
        "condition_id",
        "slot_id",
        "condition_slot_card",
        "anonymous_menu",
    ]:
        raise SLECError("assessor packet keys are invalid")
    menus = _closed(
        packet["condition_menus"], CONDITIONS, "condition menus are not closed"
    )
    for condition_id in CONDITIONS:
        if type(menus[condition_id]) is not list or len(menus[condition_id]) != 2:
            raise SLECError("condition menu is invalid")
        for option in menus[condition_id]:
            _closed(option, ("option_id", "question"), "menu option is not closed")
    provider = _closed(
        authority["provider_schema_contract"],
        (
            "capsule_schema_path",
            "capsule_schema_sha256",
            "permitted_keywords",
            "forbidden_keywords",
            "resource_limits",
            "all_properties_required",
            "additional_properties_false",
            "recursive_closure_required",
            "undeclared_keywords_permitted",
        ),
        "provider schema contract is not closed",
    )
    if (
        provider["capsule_schema_path"] != "evals/ae-sq5/f1/slec5-capsule-schema.json"
        or not _valid_hex64(provider["capsule_schema_sha256"])
        or set(provider["permitted_keywords"]) != PROVIDER_KEYWORDS
        or provider["resource_limits"]
        != {
            "maximum_total_object_properties": 5000,
            "maximum_nesting_levels": 10,
            "maximum_aggregate_name_and_enum_characters": 120000,
            "maximum_total_enum_values": 1000,
            "large_string_enum_threshold": 250,
            "maximum_large_string_enum_characters": 15000,
        }
        or provider["all_properties_required"] is not True
        or provider["additional_properties_false"] is not True
        or provider["recursive_closure_required"] is not True
        or provider["undeclared_keywords_permitted"] is not False
    ):
        raise SLECError("provider schema contract is invalid")
    local = _closed(
        authority["local_semantic_contract"],
        (
            "schema_path",
            "schema_sha256",
            "required",
            "position",
            "enforces",
            "provider_validation_substitute",
            "fail_closed",
            "capsule_input",
            "normalized_keys",
            "anchor_rule",
            "raw_runtime_ingress",
            "json_order",
        ),
        "local semantic contract is not closed",
    )
    if (
        local["schema_path"] != "evals/ae-sq5/f1/slec5-semantic-capsule-schema.json"
        or not _valid_hex64(local["schema_sha256"])
        or local["required"] is not True
        or local["provider_validation_substitute"] is not False
        or local["fail_closed"] is not True
        or local["normalized_keys"] != ["slot_id", "local_need", "reference_need"]
    ):
        raise SLECError("local semantic contract is invalid")
    _closed(
        authority["invocation_contract"],
        (
            "normalization",
            "maximum_recognized_occurrences",
            "duplicates_permitted",
            "unrecognized_or_malformed_result",
            "more_than_two_result",
            "one_or_two_result",
        ),
        "invocation contract is not closed",
    )
    _closed(
        authority["fold_contract"],
        (
            "slot_order",
            "precedence",
            "maximum_selected_slots",
            "invalid_or_uncertain_emits",
            "pure",
            "anchors_in_durable_record",
            "task_text_in_durable_record",
        ),
        "fold contract is not closed",
    )
    reference = _closed(
        authority["reference_contract"],
        (
            "policy_path",
            "policy_sha256",
            "broker_input",
            "reference_mapping",
            "task_text_to_broker",
            "atomic_failure",
            "new_structural_source_binding_permitted",
            "predecessor_corpus_result_event_or_raw_import_permitted",
        ),
        "reference contract is not closed",
    )
    if (
        reference["policy_path"] != "evals/ae-sq5/f1/slec5-reference-policy.json"
        or not _valid_hex64(reference["policy_sha256"])
        or reference["task_text_to_broker"] is not False
        or reference["atomic_failure"] is not True
        or reference["predecessor_corpus_result_event_or_raw_import_permitted"]
        is not False
    ):
        raise SLECError("reference contract is invalid")
    resolution = _closed(
        authority["resolution_contract"],
        (
            "schema_path",
            "schema_sha256",
            "closed",
            "durable_anchors",
            "durable_task_text",
            "local_cross_field_verification_required",
        ),
        "resolution contract is not closed",
    )
    if (
        resolution["schema_path"] != "evals/ae-sq5/f1/slec5-resolution-schema.json"
        or not _valid_hex64(resolution["schema_sha256"])
        or resolution["closed"] is not True
        or resolution["durable_anchors"] is not False
        or resolution["durable_task_text"] is not False
        or resolution["local_cross_field_verification_required"] is not True
    ):
        raise SLECError("resolution contract is invalid")
    resolver = _closed(
        authority["resolver_contract"],
        ("path", "required_api", "no_model_network_corpus_or_external_effect"),
        "resolver contract is not closed",
    )
    if (
        resolver["path"] != "scripts/resolve_ae_sq5_slec.py"
        or resolver["no_model_network_corpus_or_external_effect"] is not True
        or resolver["required_api"]
        != [
            "validate_provider_schema",
            "build_assessor_packet",
            "normalize_runtime_capsule",
            "fold",
            "resolve_capsules",
            "broker_references",
            "resolve",
            "verify_resolution_record",
        ]
    ):
        raise SLECError("resolver contract is invalid")
    witness = _closed(
        authority["non_isomorphism_witness"],
        (
            "comparison",
            "synthetic_input",
            "slec5_expected_selected_slots",
            "distinguishing_fact",
        ),
        "non-isomorphism witness is not closed",
    )
    if witness["slec5_expected_selected_slots"] != ["s0", "s1"]:
        raise SLECError("non-isomorphism witness is invalid")
    _closed(
        authority["security_partition"],
        (
            "untrusted",
            "parent_deterministic",
            "broker_visible",
            "broker_forbidden",
            "external_effects",
        ),
        "security partition is not closed",
    )
    qualification = _closed(
        authority["qualification_boundary"],
        (
            "prospective_only",
            "historical_evaluation_inputs_permitted",
            "bounded_diagnosis_is_not_effectiveness_evidence",
            "claims_proven",
        ),
        "qualification boundary is not closed",
    )
    if (
        qualification["prospective_only"] is not True
        or qualification["historical_evaluation_inputs_permitted"] is not False
        or qualification["bounded_diagnosis_is_not_effectiveness_evidence"] is not True
        or any(qualification["claims_proven"].values())
    ):
        raise SLECError("qualification boundary is invalid")
    return tuple(slots)


def _policy_catalog(reference_policy: Any) -> tuple[dict[str, Any], ...]:
    _closed(reference_policy, POLICY_KEYS, "reference policy is not closed")
    if (
        reference_policy.get("schema_version") != "4.0"
        or reference_policy.get("policy_id") != "AE-SQ5-SLEC-5-reference-policy"
        or reference_policy.get("candidate_id") != "AE-SQ5-SLEC-5"
        or reference_policy.get("mechanism_id") != "SLEC-5"
        or reference_policy.get("status") != "f1a-implementation"
        or reference_policy.get("claim_ceiling")
        != "structural-candidate-implementation-only"
    ):
        raise SLECError("reference policy identity is invalid")
    catalog_custody = _closed(
        reference_policy["catalog_custody"],
        ("commit", "tree", "repository_relative_root", "source_kind"),
        "catalog custody is not closed",
    )
    if catalog_custody != {
        "commit": F0_CUSTODY["commit"],
        "tree": F0_CUSTODY["tree"],
        "repository_relative_root": ".",
        "source_kind": "newly-bound-structural-reference-catalog",
    }:
        raise SLECError("catalog custody is invalid")
    limits = reference_policy.get("limits")
    expected_limits = {
        "maximum_selected_capabilities_per_request": 2,
        "maximum_files_per_slot": 1,
        "maximum_files_per_request": 2,
        "maximum_bytes_per_file": 4096,
        "maximum_total_bytes_per_request": 8192,
    }
    if limits != expected_limits:
        raise SLECError("reference limits are invalid")
    if tuple(limits) != tuple(expected_limits):
        raise SLECError("reference limits order is invalid")
    _closed(
        reference_policy["broker_boundary"],
        (
            "accepted_input",
            "forbidden_input",
            "selection_influence",
            "atomic_failure",
            "no_extra_references",
        ),
        "broker boundary is not closed",
    )
    _closed(
        reference_policy["filesystem_contract"],
        (
            "path_form",
            "forbidden_path_components",
            "regular_file_required",
            "symbolic_links_permitted",
            "hard_link_count_required",
            "path_containment_required",
            "open_rule",
            "race_rule",
            "digest_rule",
        ),
        "filesystem contract is not closed",
    )
    catalog = reference_policy.get("capability_catalog")
    if type(catalog) is not list or len(catalog) != 8:
        raise SLECError("capability catalog is invalid")
    for index, row in enumerate(catalog):
        _closed(
            row,
            ("slot_id", "reference_need", "capability_id", "file"),
            "catalog row is not closed",
        )
        slot_index, need_index = divmod(index, 2)
        expected_need = ("core", "focused")[need_index]
        if (
            row["slot_id"] != SLOTS[slot_index]
            or row["reference_need"] != expected_need
            or row["capability_id"] != CAPABILITIES[slot_index][need_index]
        ):
            raise SLECError("capability catalog order is invalid")
        file_row = _closed(
            row["file"],
            ("path", "sha256", "size_bytes", "git_blob_sha1"),
            "catalog file is not closed",
        )
        if (
            type(file_row["path"]) is not str
            or not _valid_hex64(file_row["sha256"])
            or type(file_row["size_bytes"]) is not int
            or not 0 <= file_row["size_bytes"] <= 4096
            or not _valid_hex40(file_row["git_blob_sha1"])
        ):
            raise SLECError("catalog file identity is invalid")
    return tuple(catalog)


def _trusted_authority(value: Any) -> tuple[dict[str, Any], str]:
    authority, digest = _trusted_json(value, "SLEC-5 authority")
    if digest != AUTHORITY_SHA256:
        raise SLECError("SLEC-5 authority is not the frozen byte object")
    _authority_slots(authority)
    return authority, digest


def _trusted_policy(value: Any) -> tuple[dict[str, Any], str]:
    policy, digest = _trusted_json(value, "SLEC-5 reference policy")
    if digest != POLICY_SHA256:
        raise SLECError("SLEC-5 reference policy is not the frozen byte object")
    _policy_catalog(policy)
    return policy, digest


def _trusted_authority_and_policy(
    authority_value: Any,
    policy_value: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    authority, _ = _trusted_authority(authority_value)
    policy, digest = _trusted_policy(policy_value)
    if digest != authority["reference_contract"]["policy_sha256"]:
        raise SLECError("reference policy is not authority-pinned")
    return authority, policy


def _trusted_resolution_schema(
    value: Any,
    authority: dict[str, Any],
) -> dict[str, Any]:
    schema, digest = _trusted_json(value, "SLEC-5 resolution schema")
    contract = authority["resolution_contract"]
    if (
        contract["schema_path"] != "evals/ae-sq5/f1/slec5-resolution-schema.json"
        or digest != contract["schema_sha256"]
        or schema.get("additionalProperties") is not False
    ):
        raise SLECError("resolution schema identity is invalid")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise SLECError("resolution schema is invalid") from error
    return schema


def build_assessor_packet(
    task_text: str,
    condition: str,
    slot_id: str,
    authority: Any,
) -> dict[str, Any]:
    """Build a one-card assessor packet; no other slot is projected."""
    text, _ = _task_text(task_text)
    authority, _ = _trusted_authority(authority)
    slots = _authority_slots(authority)
    if condition not in CONDITIONS or slot_id not in SLOTS:
        raise SLECError("condition or slot is invalid")
    contract = authority.get("assessor_packet_contract")
    if not isinstance(contract, dict) or contract.get("packet_keys") != [
        "instruction",
        "task_text",
        "condition_id",
        "slot_id",
        "condition_slot_card",
        "anonymous_menu",
    ]:
        raise SLECError("assessor packet contract is invalid")
    menus = contract.get("condition_menus")
    if not isinstance(menus, dict) or tuple(menus) != CONDITIONS:
        raise SLECError("condition-specific assessor menus are invalid")
    menu = menus.get(condition)
    if not isinstance(menu, list) or [
        row.get("option_id") for row in menu if isinstance(row, dict)
    ] != ["core", "focused"]:
        raise SLECError("condition-specific assessor menu is invalid")
    card = slots[SLOTS.index(slot_id)]["cards"][condition]
    return {
        "instruction": contract["instruction"],
        "task_text": text,
        "condition_id": condition,
        "slot_id": slot_id,
        "condition_slot_card": deepcopy(card["body"]),
        "anonymous_menu": deepcopy(menu),
    }


def _anchor_occurrences(task_text: str, anchor: str) -> list[int]:
    found: list[int] = []
    start = 0
    while True:
        index = task_text.find(anchor, start)
        if index < 0:
            return found
        found.append(index)
        start = index + 1


def _trusted_semantic_schema(
    value: Any,
    authority: dict[str, Any],
) -> dict[str, Any]:
    schema, digest = _trusted_json(value, "SLEC-5 semantic capsule schema")
    contract = authority["local_semantic_contract"]
    if (
        digest != contract["schema_sha256"]
        or contract["schema_path"]
        != "evals/ae-sq5/f1/slec5-semantic-capsule-schema.json"
    ):
        raise SLECError("semantic capsule schema is not authority-pinned")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise SLECError("semantic capsule schema is invalid") from error
    return schema


def _normalize_decoded_capsule(
    capsule: Any,
    text: str,
    expected_slot: str,
    semantic_schema: dict[str, Any],
) -> dict[str, str]:
    try:
        Draft202012Validator(semantic_schema).validate(capsule)
    except ValidationError as error:
        raise SLECError("capsule fails the local semantic schema") from error
    capsule = _closed(capsule, CAPSULE_KEYS, "runtime capsule is not closed")
    if capsule["slot_id"] != expected_slot:
        raise SLECError("runtime capsule slot is invalid")
    anchors = capsule["anchors"]
    previous_end = -1
    seen: set[tuple[int, int, str]] = set()
    for anchor in anchors:
        _closed(anchor, ANCHOR_KEYS, "anchor is not closed")
        start, end, anchor_text = anchor["start"], anchor["end"], anchor["text"]
        if (
            type(start) is not int
            or type(end) is not int
            or type(anchor_text) is not str
            or not anchor_text
            or len(anchor_text) > 256
            or not 0 <= start < end <= len(text)
            or start < previous_end
            or text[start:end] != anchor_text
            or _anchor_occurrences(text, anchor_text) != [start]
            or (start, end, anchor_text) in seen
        ):
            raise SLECError("anchor is not an exact unique ordered task slice")
        previous_end = end
        seen.add((start, end, anchor_text))
    return {
        "slot_id": expected_slot,
        "local_need": capsule["local_need"],
        "reference_need": capsule["reference_need"],
    }


def normalize_runtime_capsule(
    task: Any,
    expected_slot: str,
    capsule_ingress: Any,
    authority_custody: Any,
    semantic_schema_custody: Any,
) -> dict[str, str]:
    """Authenticate raw capsule bytes, apply local schema, and enforce task anchors."""
    text, _ = _task_text(task)
    authority, _ = _trusted_authority(authority_custody)
    if expected_slot not in SLOTS:
        raise SLECError("expected slot is invalid")
    capsule, _ = _trusted_json(capsule_ingress, "runtime capsule")
    semantic_schema = _trusted_semantic_schema(semantic_schema_custody, authority)
    return _normalize_decoded_capsule(capsule, text, expected_slot, semantic_schema)


def _boundary_allowed(codepoint: str | None) -> bool:
    if codepoint is None:
        return True
    category = unicodedata.category(codepoint)
    return not (
        category[:1] in {"L", "M", "N"}
        or category in {"Cf", "Pc"}
        or codepoint in {"_", "-", "$", ":"}
    )


def _scan_invocations(
    task_text: str, authority: dict[str, Any]
) -> tuple[list[str], bool]:
    slots = _authority_slots(authority)
    token_to_slot = {row["qualified_invocation"]: row["slot_id"] for row in slots}
    text = unicodedata.normalize("NFC", task_text)
    selected: list[str] = []
    malformed = False
    for start, character in enumerate(text):
        if character != "$":
            continue
        end = start + 1
        while end < len(text) and (
            text[end].isascii() and (text[end].isalnum() or text[end] in {"-", ":"})
        ):
            end += 1
        candidate = text[start:end]
        before = text[start - 1] if start else None
        after = text[end] if end < len(text) else None
        valid_shape = (
            len(candidate) > 1
            and candidate.count(":") == 1
            and all(
                part and part[0].isascii() and part[0].isalpha()
                for part in candidate[1:].split(":")
            )
        )
        if (
            not valid_shape
            or not _boundary_allowed(before)
            or not _boundary_allowed(after)
        ):
            malformed = True
            continue
        slot = token_to_slot.get(candidate)
        if slot is None or slot in selected:
            malformed = True
            continue
        selected.append(slot)
    return selected, malformed


def _typed_frame(tag: bytes, payload: bytes) -> bytes:
    return tag + len(payload).to_bytes(8, "big") + payload


def _typed_invalid_ingress(value: Any, active: set[int] | None = None) -> bytes:
    """Encode exact Python types and structure for rejected-ingress custody only."""
    if active is None:
        active = set()
    value_type = type(value)
    if value is None:
        return _typed_frame(b"N", b"")
    if value_type is bool:
        return _typed_frame(b"B", b"1" if value else b"0")
    if value_type is int:
        return _typed_frame(b"I", str(value).encode("ascii"))
    if value_type is float:
        return _typed_frame(b"F", struct.pack(">d", value))
    if value_type is str:
        try:
            return _typed_frame(b"S", value.encode("utf-8", "strict"))
        except UnicodeEncodeError as error:
            raise SLECError("invalid-ingress string custody is unavailable") from error
    if value_type is bytes:
        return _typed_frame(b"Y", value)
    if value_type is bytearray:
        return _typed_frame(b"A", bytes(value))
    if value_type in {tuple, list, dict, set, frozenset}:
        identity = id(value)
        if identity in active:
            raise SLECError("cyclic invalid-ingress custody is unavailable")
        active.add(identity)
        try:
            if value_type in {tuple, list}:
                tag = b"T" if value_type is tuple else b"L"
                children = b"".join(
                    _typed_frame(b"E", _typed_invalid_ingress(item, active))
                    for item in value
                )
                return _typed_frame(tag, len(value).to_bytes(8, "big") + children)
            if value_type is dict:
                children = b"".join(
                    _typed_frame(b"K", _typed_invalid_ingress(key, active))
                    + _typed_frame(b"V", _typed_invalid_ingress(item, active))
                    for key, item in value.items()
                )
                return _typed_frame(b"D", len(value).to_bytes(8, "big") + children)
            tag = b"Q" if value_type is set else b"R"
            children = sorted(_typed_invalid_ingress(item, active) for item in value)
            return _typed_frame(tag, len(value).to_bytes(8, "big") + b"".join(children))
        finally:
            active.remove(identity)
    raise SLECError("invalid-ingress value type has no deterministic custody encoding")


def _invalid_ingress_digest(item: Any) -> tuple[str, bool]:
    """Create typed custody, never semantic authority, for rejected ingress."""
    try:
        payload = _typed_invalid_ingress(item)
        return sha256_bytes(
            b"AE-SQ5-TYPED-INVALID-CAPSULE-INGRESS-V1\0" + payload
        ), True
    except SLECError:
        identity = f"{type(item).__module__}.{type(item).__qualname__}".encode(
            "utf-8", "strict"
        )
        return sha256_bytes(b"AE-SQ5-CUSTODY-UNAVAILABLE-V1\0" + identity), False


def _collect_capsule_ingress(
    capsule_outputs: Any,
) -> tuple[list[Any], list[str], bool, bool]:
    if not isinstance(capsule_outputs, Sequence) or isinstance(
        capsule_outputs, (str, bytes, bytearray)
    ):
        digest, complete = _invalid_ingress_digest(capsule_outputs)
        return [], [digest], True, complete
    values: list[Any] = []
    digests: list[str] = []
    invalid = False
    custody_complete = True
    for item in capsule_outputs:
        if type(item) is not tuple or len(item) != 2:
            digest, complete = _invalid_ingress_digest(item)
            digests.append(digest)
            custody_complete = custody_complete and complete
            values.append(None)
            invalid = True
            continue
        raw, expected = item
        if type(raw) is not bytes:
            digest, complete = _invalid_ingress_digest(item)
            digests.append(digest)
            custody_complete = custody_complete and complete
            values.append(None)
            invalid = True
            continue
        actual = sha256_bytes(raw)
        if not _valid_hex64(expected) or actual != expected:
            digest, complete = _invalid_ingress_digest(item)
            digests.append(digest)
            custody_complete = custody_complete and complete
            values.append(None)
            invalid = True
            continue
        digests.append(actual)
        try:
            values.append(_decode_json(raw))
        except SLECError:
            values.append(None)
            invalid = True
    return values, digests, invalid, custody_complete


def _empty_record(
    condition: str,
    task_digest: str,
    digests: Sequence[str],
    custody_complete: bool = True,
) -> dict[str, Any]:
    set_digest = sha256_bytes(canonical_json(sorted(digests)))
    return {
        "record_version": "4.0",
        "candidate_id": "AE-SQ5-SLEC-5",
        "mechanism_id": "SLEC-5",
        "condition_id": condition if condition in CONDITIONS else "current",
        "resolution_status": "abstain_invalid",
        "selection_mode": "none",
        "input_custody": {
            "task_utf8_sha256": task_digest,
            "capsule_set_sha256": set_digest,
            "capsule_count": len(digests),
            "capsule_custody_complete": custody_complete,
        },
        "slot_outcomes": [
            {"slot_id": slot, "local_need": "invalid", "reference_need": "invalid"}
            for slot in SLOTS
        ],
        "invocation_evidence": {
            "recognized_count": 0,
            "recognized_slots": [],
            "has_unrecognized_or_malformed": False,
        },
        "selected_slots": [],
        "reference_capability_ids": [],
        "references": {"status": "not_requested", "files": []},
        "claim_ceiling": "structural-candidate-implementation-only",
    }


def fold(
    task_text: Any,
    condition: str,
    capsule_outputs: Sequence[Any],
    authority: Any,
    reference_policy: Any,
    semantic_schema: Any,
) -> dict[str, Any]:
    """Pure fail-closed fold; completion order cannot affect its output."""
    values, digests, invalid_ingress, custody_complete = _collect_capsule_ingress(
        capsule_outputs
    )
    try:
        text, task_raw = _task_text(task_text)
    except SLECError:
        raw = task_text if type(task_text) is bytes else b""
        return _empty_record("current", sha256_bytes(raw), digests, custody_complete)
    task_digest = sha256_bytes(task_raw)
    record = _empty_record(condition, task_digest, digests, custody_complete)
    try:
        authority_map, reference_policy_map = _trusted_authority_and_policy(
            authority, reference_policy
        )
        semantic_schema_map = _trusted_semantic_schema(semantic_schema, authority_map)
        if condition not in CONDITIONS or invalid_ingress:
            raise SLECError("fold inputs are invalid")
        normalized: dict[str, dict[str, str]] = {}
        for value in values:
            claimed_slot = value.get("slot_id") if isinstance(value, dict) else None
            if claimed_slot not in SLOTS or claimed_slot in normalized:
                raise SLECError("capsule slots are missing or duplicated")
            normalized[claimed_slot] = _normalize_decoded_capsule(
                value, text, claimed_slot, semantic_schema_map
            )
        if tuple(sorted(normalized)) != SLOTS:
            raise SLECError("exactly four slot-local capsules are required")
    except SLECError:
        return _empty_record(condition, task_digest, digests, custody_complete)

    ordered = [normalized[slot] for slot in SLOTS]
    record = _empty_record(condition, task_digest, digests, custody_complete)
    record["slot_outcomes"] = deepcopy(ordered)
    invoked, malformed = _scan_invocations(text, authority_map)
    record["invocation_evidence"] = {
        "recognized_count": len(invoked),
        "recognized_slots": [slot for slot in SLOTS if slot in invoked],
        "has_unrecognized_or_malformed": malformed,
    }
    if any(
        "uncertain" in (row["local_need"], row["reference_need"]) for row in ordered
    ):
        record["resolution_status"] = "abstain_uncertain"
        return record
    if malformed:
        return record
    if len(invoked) > 2:
        record["resolution_status"] = "abstain_cap"
        return record
    if invoked:
        selected = [slot for slot in SLOTS if slot in invoked]
        record["resolution_status"] = "selected"
        record["selection_mode"] = "explicit_invocation"
        record["selected_slots"] = selected
        return record
    selected = [row["slot_id"] for row in ordered if row["local_need"] == "yes"]
    if len(selected) > 2:
        record["resolution_status"] = "abstain_cap"
        return record
    record["selection_mode"] = "capsule_fold"
    if not selected:
        record["resolution_status"] = "no_selection"
        return record
    references = []
    for row in ordered:
        if row["slot_id"] not in selected or row["reference_need"] == "none":
            continue
        need_index = ("core", "focused").index(row["reference_need"])
        references.append(CAPABILITIES[SLOTS.index(row["slot_id"])][need_index])
    record["resolution_status"] = "selected"
    record["selected_slots"] = selected
    record["reference_capability_ids"] = references
    return record


def resolve_capsules(
    *,
    task: Any,
    condition_id: str,
    capsule_ingresses: Sequence[Any],
    authority_custody: Any,
    policy_custody: Any,
    resolution_schema_custody: Any,
    semantic_schema_custody: Any,
) -> dict[str, Any]:
    """Canonical pure evaluator/runner path with no reference materialization."""
    authority_map, policy_map = _trusted_authority_and_policy(
        authority_custody, policy_custody
    )
    resolution_schema_map = _trusted_resolution_schema(
        resolution_schema_custody, authority_map
    )
    _trusted_semantic_schema(semantic_schema_custody, authority_map)
    record = fold(
        task,
        condition_id,
        capsule_ingresses,
        authority_custody,
        policy_custody,
        semantic_schema_custody,
    )
    try:
        Draft202012Validator(resolution_schema_map).validate(record)
    except ValidationError as error:
        raise SLECError(
            "generated record fails its frozen resolution schema"
        ) from error
    _verify_resolution_mapping(record, policy_map)
    return record


def _safe_relative_path(value: Any) -> PurePosixPath:
    if type(value) is not str or "\\" in value:
        raise SLECError("catalog path is invalid")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or str(path) != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise SLECError("catalog path is not contained")
    return path


def _stat_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _read_catalog_file(
    repository_root: Path,
    file_row: dict[str, Any],
    after_open_hook: Callable[[Path, int], None] | None,
) -> bytes:
    relative = _safe_relative_path(file_row["path"])
    if not repository_root.is_absolute():
        raise SLECError("repository root must be absolute")
    root_before = repository_root.lstat()
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_DIRECTORY", 0)
    )
    file_flags = (
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptors: list[int] = []
    directory_edges: list[tuple[int, str, int, os.stat_result]] = []
    descriptor = -1
    try:
        root_descriptor = os.open(repository_root, directory_flags)
        descriptors.append(root_descriptor)
        root_opened = os.fstat(root_descriptor)
        if not stat.S_ISDIR(root_before.st_mode) or _stat_identity(
            root_before
        ) != _stat_identity(root_opened):
            raise SLECError("repository root identity is invalid")
        parent_descriptor = root_descriptor
        for component in relative.parts[:-1]:
            child_descriptor = os.open(
                component, directory_flags, dir_fd=parent_descriptor
            )
            descriptors.append(child_descriptor)
            child_opened = os.fstat(child_descriptor)
            child_entry = os.stat(
                component, dir_fd=parent_descriptor, follow_symlinks=False
            )
            if not stat.S_ISDIR(child_opened.st_mode) or _stat_identity(
                child_opened
            ) != _stat_identity(child_entry):
                raise SLECError("catalog parent identity is invalid")
            directory_edges.append(
                (parent_descriptor, component, child_descriptor, child_opened)
            )
            parent_descriptor = child_descriptor
        final_name = relative.parts[-1]
        before = os.stat(final_name, dir_fd=parent_descriptor, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise SLECError("catalog target is not a single-link regular file")
        descriptor = os.open(final_name, file_flags, dir_fd=parent_descriptor)
        descriptors.append(descriptor)
        opened = os.fstat(descriptor)
        if _stat_identity(opened) != _stat_identity(before):
            raise SLECError("catalog target changed before open")
        path = repository_root.joinpath(*relative.parts)
        if after_open_hook is not None:
            after_open_hook(path, descriptor)
        chunks: list[bytes] = []
        remaining = 4097
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        after_fd = os.fstat(descriptor)
        after_entry = os.stat(
            final_name, dir_fd=parent_descriptor, follow_symlinks=False
        )
        after_text_path = path.lstat()
        for edge_parent, edge_name, edge_descriptor, edge_opened in directory_edges:
            edge_entry = os.stat(edge_name, dir_fd=edge_parent, follow_symlinks=False)
            if _stat_identity(os.fstat(edge_descriptor)) != _stat_identity(
                edge_opened
            ) or _stat_identity(edge_entry) != _stat_identity(edge_opened):
                raise SLECError("catalog parent changed during read")
        root_after = repository_root.lstat()
        if _stat_identity(os.fstat(root_descriptor)) != _stat_identity(
            root_opened
        ) or _stat_identity(root_after) != _stat_identity(root_opened):
            raise SLECError("repository root changed during read")
    finally:
        for open_descriptor in reversed(descriptors):
            try:
                os.close(open_descriptor)
            except OSError:
                pass
    if (
        _stat_identity(after_fd) != _stat_identity(opened)
        or _stat_identity(after_entry) != _stat_identity(opened)
        or _stat_identity(after_text_path) != _stat_identity(opened)
        or len(payload) != file_row["size_bytes"]
        or len(payload) > 4096
        or sha256_bytes(payload) != file_row["sha256"]
        or hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()
        != file_row["git_blob_sha1"]
    ):
        raise SLECError("catalog target custody failed")
    return payload


def broker_references(
    capability_ids: Sequence[str],
    reference_policy: Any,
    repository_root: str | Path,
    *,
    _after_open_hook: Callable[[Path, int], None] | None = None,
) -> dict[str, Any]:
    """Atomically resolve capability IDs; no task or capsule parameter exists."""
    try:
        reference_policy, _ = _trusted_policy(reference_policy)
        catalog = _policy_catalog(reference_policy)
        if (
            not isinstance(capability_ids, Sequence)
            or isinstance(capability_ids, (str, bytes))
            or len(capability_ids) > 2
            or any(type(capability) is not str for capability in capability_ids)
        ):
            raise SLECError("capability request is invalid")
        if len(set(capability_ids)) != len(capability_ids):
            raise SLECError("capability request is duplicated")
        by_id = {row["capability_id"]: row for row in catalog}
        rows = [by_id[capability] for capability in capability_ids]
        if len({row["slot_id"] for row in rows}) != len(rows):
            raise SLECError("only one reference capability per slot is permitted")
        if sum(row["file"]["size_bytes"] for row in rows) > 8192:
            raise SLECError("capability request byte cap exceeded")
        files: list[dict[str, Any]] = []
        for row in rows:
            _read_catalog_file(Path(repository_root), row["file"], _after_open_hook)
            files.append(
                {
                    "slot_id": row["slot_id"],
                    "reference_need": row["reference_need"],
                    "capability_id": row["capability_id"],
                    "path": row["file"]["path"],
                    "sha256": row["file"]["sha256"],
                    "git_blob_sha1": row["file"]["git_blob_sha1"],
                    "size_bytes": row["file"]["size_bytes"],
                }
            )
        return {"status": "resolved" if files else "not_requested", "files": files}
    except (KeyError, OSError, SLECError):
        return {"status": "custody_failure", "files": []}


def _ordered_unique_slots(value: Any, maximum: int) -> list[str]:
    if (
        type(value) is not list
        or len(value) > maximum
        or any(type(slot) is not str or slot not in SLOTS for slot in value)
        or len(set(value)) != len(value)
        or value != [slot for slot in SLOTS if slot in value]
    ):
        raise SLECError("resolution slot sequence is invalid")
    return value


def _expected_reference_file(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "slot_id": row["slot_id"],
        "reference_need": row["reference_need"],
        "capability_id": row["capability_id"],
        "path": row["file"]["path"],
        "sha256": row["file"]["sha256"],
        "git_blob_sha1": row["file"]["git_blob_sha1"],
        "size_bytes": row["file"]["size_bytes"],
    }


def _verify_resolution_mapping(
    record: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    _closed_unordered(record, RESOLUTION_RECORD_KEYS, "resolution record is not closed")
    if (
        record["record_version"] != "4.0"
        or record["candidate_id"] != "AE-SQ5-SLEC-5"
        or record["mechanism_id"] != "SLEC-5"
        or type(record["condition_id"]) is not str
        or record["condition_id"] not in CONDITIONS
        or type(record["resolution_status"]) is not str
        or type(record["selection_mode"]) is not str
        or record["claim_ceiling"] != "structural-candidate-implementation-only"
    ):
        raise SLECError("resolution record identity is invalid")

    custody = _closed_unordered(
        record["input_custody"],
        (
            "task_utf8_sha256",
            "capsule_set_sha256",
            "capsule_count",
            "capsule_custody_complete",
        ),
        "resolution input custody is not closed",
    )
    if (
        not _valid_hex64(custody["task_utf8_sha256"])
        or not _valid_hex64(custody["capsule_set_sha256"])
        or type(custody["capsule_count"]) is not int
        or not 0 <= custody["capsule_count"] <= 1024
        or type(custody["capsule_custody_complete"]) is not bool
    ):
        raise SLECError("resolution input custody is invalid")

    outcomes = record["slot_outcomes"]
    if type(outcomes) is not list or len(outcomes) != 4:
        raise SLECError("resolution slot outcomes are invalid")
    for index, outcome in enumerate(outcomes):
        _closed_unordered(
            outcome,
            ("slot_id", "local_need", "reference_need"),
            "resolution slot outcome is not closed",
        )
        if (
            outcome["slot_id"] != SLOTS[index]
            or type(outcome["local_need"]) is not str
            or outcome["local_need"] not in (*LOCAL_NEEDS, "invalid")
            or type(outcome["reference_need"]) is not str
            or outcome["reference_need"] not in (*REFERENCE_NEEDS, "invalid")
        ):
            raise SLECError("resolution slot outcome is invalid")
        if outcome["local_need"] == "no" and outcome["reference_need"] != "none":
            raise SLECError("unselected durable slot requested a reference")
        if (
            outcome["local_need"] == "uncertain"
            and outcome["reference_need"] != "uncertain"
        ):
            raise SLECError("uncertain durable slot has a definite reference state")
        if (outcome["local_need"] == "invalid") != (
            outcome["reference_need"] == "invalid"
        ):
            raise SLECError("durable invalid slot state is partial")

    invocation = _closed_unordered(
        record["invocation_evidence"],
        ("recognized_count", "recognized_slots", "has_unrecognized_or_malformed"),
        "resolution invocation evidence is not closed",
    )
    recognized = _ordered_unique_slots(invocation["recognized_slots"], 4)
    if (
        type(invocation["recognized_count"]) is not int
        or invocation["recognized_count"] != len(recognized)
        or type(invocation["has_unrecognized_or_malformed"]) is not bool
    ):
        raise SLECError("resolution invocation evidence is invalid")

    selected = _ordered_unique_slots(record["selected_slots"], 2)
    capabilities = record["reference_capability_ids"]
    if (
        type(capabilities) is not list
        or len(capabilities) > 2
        or any(
            type(value) is not str or value not in ALL_CAPABILITIES
            for value in capabilities
        )
        or len(set(capabilities)) != len(capabilities)
    ):
        raise SLECError("resolution capability sequence is invalid")

    references = _closed_unordered(
        record["references"],
        ("status", "files"),
        "resolution references are not closed",
    )
    files = references["files"]
    if type(references["status"]) is not str or references["status"] not in {
        "not_requested",
        "resolved",
        "custody_failure",
    }:
        raise SLECError("resolution reference status is invalid")
    if type(files) is not list or len(files) > 2:
        raise SLECError("resolution reference files are invalid")
    if references["status"] != "resolved" and files:
        raise SLECError("unresolved record contains reference files")

    catalog = _policy_catalog(policy)
    by_capability = {row["capability_id"]: row for row in catalog}
    expected_files = [
        _expected_reference_file(by_capability[value]) for value in capabilities
    ]
    if references["status"] == "resolved" and files != expected_files:
        raise SLECError("resolved reference files contradict the frozen catalog")
    for file_row in files:
        _closed_unordered(
            file_row,
            (
                "slot_id",
                "reference_need",
                "capability_id",
                "path",
                "sha256",
                "git_blob_sha1",
                "size_bytes",
            ),
            "resolved reference file is not closed",
        )
        if (
            not _valid_hex64(file_row["sha256"])
            or not _valid_hex40(file_row["git_blob_sha1"])
            or type(file_row["size_bytes"]) is not int
        ):
            raise SLECError("resolved reference file identity is invalid")

    invalid_rows = [row for row in outcomes if row["local_need"] == "invalid"]
    uncertain_rows = [
        row
        for row in outcomes
        if "uncertain" in (row["local_need"], row["reference_need"])
    ]
    yes_slots = [row["slot_id"] for row in outcomes if row["local_need"] == "yes"]
    expected_capabilities = [
        CAPABILITIES[SLOTS.index(row["slot_id"])][
            ("core", "focused").index(row["reference_need"])
        ]
        for row in outcomes
        if row["slot_id"] in yes_slots and row["reference_need"] in {"core", "focused"}
    ]
    status = record["resolution_status"]
    mode = record["selection_mode"]
    malformed = invocation["has_unrecognized_or_malformed"]
    empty_references = references == {"status": "not_requested", "files": []}
    definite = not invalid_rows and not uncertain_rows

    if status == "selected" and mode == "explicit_invocation":
        valid = (
            definite
            and not malformed
            and 1 <= len(recognized) <= 2
            and selected == recognized
            and not capabilities
            and empty_references
        )
    elif status == "selected" and mode == "capsule_fold":
        valid = (
            definite
            and not malformed
            and not recognized
            and 1 <= len(yes_slots) <= 2
            and selected == yes_slots
            and capabilities == expected_capabilities
            and (
                (not capabilities and empty_references)
                or (
                    capabilities
                    and references["status"] in {"not_requested", "resolved"}
                )
            )
        )
    elif status == "no_selection" and mode == "capsule_fold":
        valid = (
            definite
            and not malformed
            and not recognized
            and not yes_slots
            and not selected
            and not capabilities
            and empty_references
        )
    elif status == "abstain_uncertain" and mode == "none":
        valid = (
            not invalid_rows
            and bool(uncertain_rows)
            and not selected
            and not capabilities
            and empty_references
        )
    elif status == "abstain_cap" and mode == "none":
        valid = (
            definite
            and not malformed
            and not selected
            and not capabilities
            and empty_references
            and (len(recognized) > 2 or (not recognized and len(yes_slots) > 2))
        )
    elif status == "abstain_invalid" and mode == "none":
        all_invalid = (
            len(invalid_rows) == 4
            and not uncertain_rows
            and not recognized
            and not malformed
            and empty_references
        )
        scanner_invalid = (
            definite and malformed and references["status"] == "not_requested"
        )
        broker_invalid = (
            custody["capsule_custody_complete"] is True
            and custody["capsule_count"] == 4
            and definite
            and not malformed
            and not recognized
            and 1 <= len(yes_slots) <= 2
            and 1 <= len(expected_capabilities) <= len(yes_slots)
            and references["status"] == "custody_failure"
        )
        valid = (
            not selected
            and not capabilities
            and not files
            and (all_invalid or scanner_invalid or broker_invalid)
        )
    else:
        valid = False
    if not valid:
        raise SLECError("resolution record fields are semantically contradictory")
    if status != "abstain_invalid" and custody["capsule_custody_complete"] is not True:
        raise SLECError("authoritative resolution lacks complete capsule custody")


def verify_resolution_record(
    record: Any,
    authority: Any,
    reference_policy: Any,
    resolution_schema: Any,
) -> dict[str, Any]:
    """Authenticate and semantically verify one exact durable resolution record."""
    authority_map, policy_map = _trusted_authority_and_policy(
        authority, reference_policy
    )
    schema = _trusted_resolution_schema(resolution_schema, authority_map)
    record_map, _ = _trusted_json(record, "SLEC-5 resolution record")
    try:
        Draft202012Validator(schema).validate(record_map)
    except ValidationError as error:
        raise SLECError("resolution record fails its frozen schema") from error
    _verify_resolution_mapping(record_map, policy_map)
    return deepcopy(record_map)


def resolve(
    task_text: Any,
    condition: str,
    capsule_outputs: Sequence[Any],
    authority: Any,
    reference_policy: Any,
    semantic_schema: Any,
    repository_root: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve capsules and optionally materialize their fixed references."""
    record = fold(
        task_text,
        condition,
        capsule_outputs,
        authority,
        reference_policy,
        semantic_schema,
    )
    capabilities = record["reference_capability_ids"]
    if not capabilities:
        return record
    if repository_root is None:
        record["resolution_status"] = "abstain_invalid"
        record["selection_mode"] = "none"
        record["selected_slots"] = []
        record["reference_capability_ids"] = []
        record["references"] = {"status": "custody_failure", "files": []}
        return record
    reference_result = broker_references(
        capabilities, reference_policy, repository_root
    )
    if reference_result["status"] == "custody_failure":
        record["resolution_status"] = "abstain_invalid"
        record["selection_mode"] = "none"
        record["selected_slots"] = []
        record["reference_capability_ids"] = []
    record["references"] = reference_result
    return record


__all__ = [
    "SLECError",
    "broker_references",
    "build_assessor_packet",
    "canonical_json",
    "fold",
    "normalize_runtime_capsule",
    "resolve",
    "resolve_capsules",
    "sha256_bytes",
    "validate_provider_schema",
    "verify_resolution_record",
]
