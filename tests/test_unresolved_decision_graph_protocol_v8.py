"""Corpus-blind structural checks for the frozen H4 graph proposal."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
import unicodedata
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "evals/foundation-v4/unresolved-decision-graph-protocol-v8.json"
SEMANTIC_SCHEMA_PATH = ROOT / "evals/foundation-v4/unresolved-decision-graph-selector-output-schema-v8.json"
RUNTIME_SCHEMA_PATH = ROOT / "evals/foundation-v4/unresolved-decision-graph-runtime-output-schema-v8.json"

SLOTS = ("s0", "s1", "s2", "s3")
PAIRS = (
    ("s0", "s1"),
    ("s0", "s2"),
    ("s0", "s3"),
    ("s1", "s2"),
    ("s1", "s3"),
    ("s2", "s3"),
)
STATES = {"unresolved", "resolved_or_absent", "uncertain"}
RELATIONS = {
    "left_controls_right_downstream",
    "right_controls_left_downstream",
    "independent",
    "unrelated",
    "uncertain",
}
NEEDS = {"none", "primary", "secondary", "uncertain"}

EXPECTED_SLOT_ROWS = (
    ("s0", "topology-control-boundary", "agentic-engineering", "$agentic-engineering"),
    ("s1", "task-contract", "codex-task-contract", "$codex-task-contract"),
    ("s2", "verification-strategy", "verification-strategy-engineering", "$verification-strategy-engineering"),
    ("s3", "engineering-learning", "engineering-learning-loop", "$engineering-learning-loop"),
)

EXPECTED_AUTHORITY = {
    "h3": {
        "commit": "ccbe06be9a2ef5feca4104b6918985ee9c4527c0",
        "tree": "dd20449fdc45a73c55adb349d8c828687728ef4d",
        "protocol": {
            "path": "evals/foundation-v4/decision-certificate-protocol-v6.json",
            "sha256": "9ad483a26fe339f81c947507de9c1c66d54b2823a38f68b1c5ee7fdf5c426f84",
            "predicate_order_sha256": "cd890bb08444940bf1483dc48c0ca563476f7b4c2b25bbe65edfe861d839e4ae",
            "eligibility_rules_sha256": "3475626c995dfe801faeeded444ed249e72c0f50d8f19b01ee515ad12eba4ad2",
        },
        "selector_output_schema": {
            "path": "evals/foundation-v4/decision-certificate-selector-output-schema-v6.json",
            "sha256": "9742f2255fed5452df52f9da789a6f2fd72e89aa94c3c6847fad6944445f5b25",
        },
    },
    "h2_catalog": {
        "commit": "8ddf39198cb0e21f321a01a9755e009bb1c1860f",
        "tree": "1fbf9964b10831da051d2e5cafe29b6086d4d599",
        "path": "evals/foundation-v4/decision-atom-candidate-v4.json",
        "sha256": "50fffcf10170cd022d78428909d0679527439a002a7e07dac30e321bbaff61d9",
        "git_blob_sha1": "c3e1f89ded468592e3ada8f23f7336c89f0d580d",
    },
    "reference_policy": {
        "commit": "c4e661a926e0ace78d9da83f71d9c52d311abb72",
        "tree": "f2abb05d32a888c9054ef2e7ab3ad0f08547de88",
        "path": "evals/foundation-v4/decision-certificate-reference-policy-v6.json",
        "sha256": "92982c278e33ff52edce1ba2a16082afb3ecc1989d8333a77eee9ca0911fee19",
    },
    "base_manifest_provenance_only": {
        "commit": "f09a0544acf4b7a95fff796434273511a0683ca9",
        "tree": "38c8c8adf3bb633d33200df1ec65f33e985ae244",
        "path": "evals/foundation-v4/reduced-four-skills/candidate.json",
        "sha256": "854f67bdd03e7121bd20e5513ef61ac806d016b3a5f1d6e5891bf4d9e546eb1f",
        "conditions": {
            "current": {
                "selector_catalog_sha256": "7947721cd7ce8a3321b89a5b17891cbc79f373acadb0351793aa481b8dac362a",
                "condition_input_sha256": "0f7d1ef19a63fceeacf86779042bb9269a098a4e1a88b3eb176f11e44b44f0a0",
            },
            "reduced": {
                "selector_catalog_sha256": "e6b62fd582f724f33d0ce63acb22fa3209f6936213aeba74113a4c0eac67eb4d",
                "condition_input_sha256": "a2bb7830b3dfccdd5decf1a63d4bcf5cd2bb2605ea35db0efad6ac4d892c78d1",
            },
        },
    },
}

PROTOCOL = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
SEMANTIC_SCHEMA = json.loads(SEMANTIC_SCHEMA_PATH.read_text(encoding="utf-8"))
RUNTIME_SCHEMA = json.loads(RUNTIME_SCHEMA_PATH.read_text(encoding="utf-8"))
CONSTRAINT = PROTOCOL["explicit_constraint"]
PARSER_CONTRACT = CONSTRAINT["h4_parent_parser_contract"]
TOKEN_TO_SLOT = {
    row["token"]: row["slot_id"] for row in CONSTRAINT["ordered_token_to_slot"]
}

EXPECTED_GRAPH_CONTRACT = {
    "parent_owned": True,
    "status_precedence": [
        "schema_invalid_fail",
        "relation_state_mismatch_graph_invalid",
        "cycle_graph_cycle",
        "transitive_closure_failure_graph_invalid",
        "uncertainty_graph_uncertain",
        "root_selection",
    ],
    "schema_invalid": "Fail before invocation parsing or graph selection. A schema-invalid model output never produces a selection or recoverable routing status.",
    "pair_compatibility": [
        {
            "endpoint_states": "at_least_one_uncertain",
            "required_relation": "uncertain",
        },
        {
            "endpoint_states": "neither_uncertain_and_at_least_one_resolved_or_absent",
            "required_relation": "unrelated",
        },
        {
            "endpoint_states": "both_unresolved",
            "allowed_relations": [
                "left_controls_right_downstream",
                "right_controls_left_downstream",
                "independent",
                "uncertain",
            ],
            "forbidden_relation": "unrelated",
        },
    ],
    "invalid_pair_result": {
        "graph_status": "graph_invalid",
        "automatic_selection_status": "graph_invalid",
        "root_slots": [],
        "selected_slots": [],
    },
    "edge_construction": {
        "left_controls_right_downstream": "left_slot_to_right_slot",
        "right_controls_left_downstream": "right_slot_to_left_slot",
        "independent": "no_edge",
        "unrelated": "no_edge",
        "uncertain": "no_edge",
        "endpoint_scope": "Edges exist only between unresolved endpoints.",
    },
    "order_law": "The directed unresolved graph must be a strict partial order: irreflexive, acyclic, asymmetric, and transitively closed.",
    "cycle_result": {
        "graph_status": "graph_cycle",
        "automatic_selection_status": "graph_cycle",
        "root_slots": [],
        "selected_slots": [],
    },
    "transitive_closure_rule": "For every directed path from controller A to downstream B, the canonical pair for A and B must encode the direct A-to-B direction. A missing, independent, reverse, unrelated, or uncertain closure relation is graph_invalid.",
    "uncertainty_rule": "After schema, pair compatibility, cycle, and closure checks pass, any uncertain candidate state or any uncertain pairwise relation yields graph_uncertain automatic abstention.",
    "uncertainty_result": {
        "graph_status": "graph_uncertain",
        "automatic_selection_status": "graph_uncertain",
        "root_slots": [],
        "selected_slots": [],
    },
    "root_definition": "Roots are exactly unresolved slots with directed indegree zero.",
    "root_selection": {
        "zero_roots": {
            "graph_status": "valid",
            "automatic_selection_status": "automatic",
            "selected_slots": [],
        },
        "one_or_two_roots": {
            "graph_status": "valid",
            "automatic_selection_status": "automatic",
            "selection": "all roots in stable_slot_order",
        },
        "more_than_two_roots": {
            "graph_status": "valid",
            "automatic_selection_status": "cap_exceeded",
            "selected_slots": [],
        },
    },
    "selection_cap": 2,
    "graph_status_values": ["valid", "graph_uncertain", "graph_invalid", "graph_cycle"],
    "automatic_selection_status_values": [
        "automatic",
        "cap_exceeded",
        "graph_uncertain",
        "graph_invalid",
        "graph_cycle",
    ],
}

EXPECTED_EXPLICIT_CONSTRAINT = {
    "parse_boundary": "The parent, not the model output, parses task text after semantic-schema validation and computes graph telemetry before applying explicit selection precedence.",
    "superseded_h3_grammar_lineage": {
        "authority_path": "evals/foundation-v4/decision-certificate-protocol-v6.json",
        "authority_sha256": "9ad483a26fe339f81c947507de9c1c66d54b2823a38f68b1c5ee7fdf5c426f84",
        "superseded_surface": "explicit_constraint.qualified_invocation_grammar",
        "status": "superseded-for-h4",
        "reason": "H3 ASCII lookaround boundaries can recognize a qualified token adjacent to a non-ASCII Unicode letter, number, or combining mark. H4 owns a codepoint-category boundary parser instead.",
        "change_classification": "pre-corpus correctness hardening",
        "outcome_tuned": False,
        "corpus_or_evaluator_evidence_used": False,
    },
    "h4_parent_parser_contract": {
        "owner": "H4 parent",
        "normalization": "Unicode NFC",
        "qualified_token_bodies": [
            "agentic-engineering",
            "codex-task-contract",
            "verification-strategy-engineering",
            "engineering-learning-loop",
        ],
        "invocation_like_body": {
            "prefix": "$",
            "first_codepoint": {
                "alphabet": "ASCII",
                "allowed_ranges": ["A-Z", "a-z"],
            },
            "remaining_codepoints": {
                "alphabet": "ASCII",
                "allowed_ranges": ["A-Z", "a-z", "0-9"],
                "allowed_literals": ["-"],
                "minimum_count": 0,
            },
            "scan": "maximal",
        },
        "boundary": {
            "adjacent_codepoints": "The codepoint immediately before $ and the codepoint immediately after the maximal invocation-like body, when present.",
            "allowed_when_absent": True,
            "disallowed_unicode_general_category_prefixes": ["L", "N", "M"],
            "disallowed_unicode_general_categories": ["Cf", "Pc"],
            "disallowed_literals": ["_", "-"],
            "same_rule_on_both_sides": True,
            "retained_rejection_fixtures": [
                {"codepoint": "U+200C", "category": "Cf"},
                {"codepoint": "U+200D", "category": "Cf"},
                {"codepoint": "U+2060", "category": "Cf"},
                {"codepoint": "U+FEFF", "category": "Cf"},
                {"codepoint": "U+202E", "category": "Cf"},
                {"codepoint": "U+203F", "category": "Pc"},
            ],
        },
        "rewrites": "No trimming, case folding, substring expansion, or token rewriting.",
    },
    "ordered_token_to_slot": [
        {"token": "$agentic-engineering", "slot_id": "s0"},
        {"token": "$codex-task-contract", "slot_id": "s1"},
        {"token": "$verification-strategy-engineering", "slot_id": "s2"},
        {"token": "$engineering-learning-loop", "slot_id": "s3"},
    ],
    "schema_invalid": "Always fail before explicit invocation can be considered.",
    "exact": "When there is exactly one bounded invocation-like token whose exact ASCII body is qualified and no unrecognized invocation-like token, select exactly its mapped slot even when automatic graph selection would abstain or select a different root set.",
    "ambiguous": "More than one qualified invocation is ambiguous and selects no slot.",
    "absence": "When task text contains no invocation-like token, use automatic graph selection.",
    "unrecognized": "Any unrecognized invocation-like token, including one mixed with a qualified token, is unrecognized and selects no slot.",
    "precedence": "After schema validation, unrecognized takes precedence over exact or ambiguous; otherwise one qualified token is exact, more than one is ambiguous, and none leaves automatic selection in force.",
    "telemetry": "graph_status, automatic_selection_status, and root_slots remain parent-computed telemetry on exact, ambiguous, and unrecognized paths; explicit syntax changes selected_slots only.",
    "selection_status_values": [
        "automatic",
        "exact",
        "ambiguous",
        "unrecognized",
        "cap_exceeded",
        "graph_uncertain",
        "graph_invalid",
        "graph_cycle",
    ],
}

EXPECTED_PARENT_RESOLUTION_CONTRACT = {
    "result_fields": [
        "graph_status",
        "automatic_selection_status",
        "selection_status",
        "root_slots",
        "selected_slots",
    ],
    "slot_output_order": "stable_slot_order",
    "automatic_status": "Without invocation-like syntax, selection_status equals automatic_selection_status.",
    "explicit_status": "With recognized explicit syntax, selection_status is exact or ambiguous; with any unrecognized invocation-like token, selection_status is unrecognized.",
    "mapping": "Only the parent maps selected slots through slot_contract to logical atoms and advisers.",
    "prohibitions": [
        "no_model_owned_selection",
        "no_authority_assignment",
        "no_policy_adoption",
        "no_effect_execution",
        "no_external_action",
        "no_completion_claim",
        "no_efficacy_claim",
        "no_runtime_claim",
        "no_provider_claim",
        "no_product_claim",
        "no_promotion_claim",
    ],
}

EXPECTED_REFERENCE_BOUNDARY = {
    "routing_influence": "none",
    "reference_needs_are_annotations_only": True,
    "uncertain_need_does_not_change_graph_status": True,
    "must_not_control": [
        "pair_compatibility",
        "edge_construction",
        "cycle_detection",
        "transitive_closure",
        "root_slots",
        "automatic_selection_status",
        "selection_status",
        "selected_slots",
    ],
    "resolution_time": "Only after parent-owned slot selection may a separate frozen reference policy inspect reference needs.",
}

EXPECTED_QUALIFICATION_CONTROLS = {
    "aq8_failure_policy": {
        "terminal_stop": True,
        "rule": "An AQ8 failure is terminal. Stop unless independent new evidence supports a separately authorized protocol revision.",
        "outcome_tuning_after_failure_permitted": False,
    },
    "outcome_tuned": False,
    "corpus_inputs_permitted": False,
    "case_label_result_inputs_permitted": False,
    "evaluator_output_inputs_permitted": False,
    "fresh_blinded_corpus_required_for_any_later_qualification": True,
    "authorized_observation_schedule": "one_canary_then_one_batch",
    "claim_ceiling": "Protocol freezing, schema validation, synthetic resolver tests, and any later authorized qualification observations do not establish runtime behavior, provider behavior, product behavior, efficacy, promotion, authority, effects, or external claims.",
}


def raw_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_bytes(revision: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def git_revision(expression: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", expression], cwd=ROOT, text=True
    ).strip()


def model_output(
    *,
    states: dict[str, str] | None = None,
    relations: dict[tuple[str, str], str] | None = None,
    needs: dict[str, str] | None = None,
) -> dict[str, Any]:
    state_map = {slot: "resolved_or_absent" for slot in SLOTS}
    state_map.update(states or {})
    relation_map: dict[tuple[str, str], str] = {}
    for pair in PAIRS:
        left_state, right_state = (state_map[slot] for slot in pair)
        if "uncertain" in {left_state, right_state}:
            relation_map[pair] = "uncertain"
        elif "resolved_or_absent" in {left_state, right_state}:
            relation_map[pair] = "unrelated"
        else:
            relation_map[pair] = "independent"
    relation_map.update(relations or {})
    need_map = {slot: "none" for slot in SLOTS}
    need_map.update(needs or {})
    return {
        "candidate_states": [
            {"slot_id": slot, "state": state_map[slot]} for slot in SLOTS
        ],
        "pairwise_relations": [
            {
                "left_slot": left,
                "right_slot": right,
                "relation": relation_map[(left, right)],
            }
            for left, right in PAIRS
        ],
        "reference_needs": [
            {"slot_id": slot, "need": need_map[slot]} for slot in SLOTS
        ],
    }


def validate_model_output(payload: object) -> None:
    """Independent closed-row/order validator for the semantic contract."""
    if not isinstance(payload, dict) or set(payload) != {
        "candidate_states",
        "pairwise_relations",
        "reference_needs",
    }:
        raise ValueError("closed model output required")

    candidate_rows = payload["candidate_states"]
    if not isinstance(candidate_rows, list) or len(candidate_rows) != len(SLOTS):
        raise ValueError("exactly four candidate rows required")
    for slot, row in zip(SLOTS, candidate_rows, strict=True):
        if (
            not isinstance(row, dict)
            or set(row) != {"slot_id", "state"}
            or row["slot_id"] != slot
            or row["state"] not in STATES
        ):
            raise ValueError("invalid ordered candidate row")

    relation_rows = payload["pairwise_relations"]
    if not isinstance(relation_rows, list) or len(relation_rows) != len(PAIRS):
        raise ValueError("exactly six relation rows required")
    for pair, row in zip(PAIRS, relation_rows, strict=True):
        if (
            not isinstance(row, dict)
            or set(row) != {"left_slot", "right_slot", "relation"}
            or (row["left_slot"], row["right_slot"]) != pair
            or row["relation"] not in RELATIONS
        ):
            raise ValueError("invalid ordered relation row")

    reference_rows = payload["reference_needs"]
    if not isinstance(reference_rows, list) or len(reference_rows) != len(SLOTS):
        raise ValueError("exactly four reference rows required")
    for slot, row in zip(SLOTS, reference_rows, strict=True):
        if (
            not isinstance(row, dict)
            or set(row) != {"slot_id", "need"}
            or row["slot_id"] != slot
            or row["need"] not in NEEDS
        ):
            raise ValueError("invalid ordered reference row")


def codepoints_from_ranges(ranges: list[str], literals: list[str] | None = None) -> set[str]:
    allowed = set(literals or [])
    for codepoint_range in ranges:
        start, end = codepoint_range.split("-", maxsplit=1)
        if len(start) != 1 or len(end) != 1 or ord(start) > ord(end):
            raise ValueError("invalid parser codepoint range")
        allowed.update(chr(value) for value in range(ord(start), ord(end) + 1))
    return allowed


def parse_invocation_like_tokens(task_text: str) -> tuple[str, ...]:
    """Execute only the H4-owned Unicode-category parser contract."""
    parser = PARSER_CONTRACT
    normalized = unicodedata.normalize(parser["normalization"].split()[-1], task_text)
    body = parser["invocation_like_body"]
    prefix = body["prefix"]
    if prefix != "$" or len(prefix) != 1:
        raise ValueError("H4 parser requires one dollar prefix")
    first = body["first_codepoint"]
    remaining = body["remaining_codepoints"]
    if first["alphabet"] != "ASCII" or remaining["alphabet"] != "ASCII":
        raise ValueError("H4 invocation body must be ASCII")
    first_allowed = codepoints_from_ranges(first["allowed_ranges"])
    remaining_allowed = codepoints_from_ranges(
        remaining["allowed_ranges"], remaining["allowed_literals"]
    )
    if remaining["minimum_count"] != 0 or body["scan"] != "maximal":
        raise ValueError("unsupported H4 invocation scan contract")

    boundary = parser["boundary"]
    category_prefixes = set(boundary["disallowed_unicode_general_category_prefixes"])
    categories = set(boundary["disallowed_unicode_general_categories"])
    disallowed_literals = set(boundary["disallowed_literals"])
    if not boundary["allowed_when_absent"] or not boundary["same_rule_on_both_sides"]:
        raise ValueError("unsupported H4 boundary contract")

    def is_bounded(index: int) -> bool:
        if index < 0 or index >= len(normalized):
            return boundary["allowed_when_absent"]
        adjacent = normalized[index]
        category = unicodedata.category(adjacent)
        return (
            adjacent not in disallowed_literals
            and category not in categories
            and category[0] not in category_prefixes
        )

    tokens: list[str] = []
    for start, codepoint in enumerate(normalized):
        if codepoint != prefix:
            continue
        cursor = start + 1
        if cursor >= len(normalized) or normalized[cursor] not in first_allowed:
            continue
        cursor += 1
        while cursor < len(normalized) and normalized[cursor] in remaining_allowed:
            cursor += 1
        if is_bounded(start - 1) and is_bounded(cursor):
            tokens.append(normalized[start:cursor])
    return tuple(tokens)


def has_cycle(nodes: set[str], edges: set[tuple[str, str]]) -> bool:
    adjacency = {node: set() for node in nodes}
    for source, target in edges:
        adjacency[source].add(target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(target) for target in adjacency[node]):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in nodes)


def transitive_closure_is_explicit(
    nodes: set[str], edges: set[tuple[str, str]]
) -> bool:
    adjacency = {node: set() for node in nodes}
    for source, target in edges:
        adjacency[source].add(target)
    for source in nodes:
        reachable: set[str] = set()
        frontier = list(adjacency[source])
        while frontier:
            target = frontier.pop()
            if target in reachable:
                continue
            reachable.add(target)
            frontier.extend(adjacency[target] - reachable)
        if any((source, target) not in edges for target in reachable):
            return False
    return True


def automatic_graph(payload: object) -> dict[str, Any]:
    """Independent executable form of the frozen parent resolver algebra."""
    validate_model_output(payload)
    assert isinstance(payload, dict)
    states = {
        row["slot_id"]: row["state"] for row in payload["candidate_states"]
    }
    edges: set[tuple[str, str]] = set()
    any_uncertainty = "uncertain" in states.values()

    for row in payload["pairwise_relations"]:
        left, right, relation = (
            row["left_slot"],
            row["right_slot"],
            row["relation"],
        )
        endpoint_states = {states[left], states[right]}
        any_uncertainty = any_uncertainty or relation == "uncertain"
        if "uncertain" in endpoint_states:
            compatible = relation == "uncertain"
        elif "resolved_or_absent" in endpoint_states:
            compatible = relation == "unrelated"
        else:
            compatible = relation in {
                "left_controls_right_downstream",
                "right_controls_left_downstream",
                "independent",
                "uncertain",
            }
        if not compatible:
            return {
                "graph_status": "graph_invalid",
                "automatic_selection_status": "graph_invalid",
                "root_slots": [],
                "selected_slots": [],
            }
        if relation == "left_controls_right_downstream":
            edges.add((left, right))
        elif relation == "right_controls_left_downstream":
            edges.add((right, left))

    unresolved = {slot for slot, state in states.items() if state == "unresolved"}
    if has_cycle(unresolved, edges):
        return {
            "graph_status": "graph_cycle",
            "automatic_selection_status": "graph_cycle",
            "root_slots": [],
            "selected_slots": [],
        }
    if not transitive_closure_is_explicit(unresolved, edges):
        return {
            "graph_status": "graph_invalid",
            "automatic_selection_status": "graph_invalid",
            "root_slots": [],
            "selected_slots": [],
        }
    if any_uncertainty:
        return {
            "graph_status": "graph_uncertain",
            "automatic_selection_status": "graph_uncertain",
            "root_slots": [],
            "selected_slots": [],
        }

    downstream = {target for _, target in edges}
    roots = [slot for slot in SLOTS if slot in unresolved and slot not in downstream]
    automatic_status = "cap_exceeded" if len(roots) > 2 else "automatic"
    return {
        "graph_status": "valid",
        "automatic_selection_status": automatic_status,
        "root_slots": roots,
        "selected_slots": [] if automatic_status == "cap_exceeded" else roots,
    }


def resolve(payload: object, task_text: str = "") -> dict[str, Any]:
    graph = automatic_graph(payload)
    invocation_tokens = parse_invocation_like_tokens(task_text)
    exact_tokens = tuple(token for token in invocation_tokens if token in TOKEN_TO_SLOT)
    result = deepcopy(graph)
    if any(token not in TOKEN_TO_SLOT for token in invocation_tokens):
        result.update(selection_status="unrecognized", selected_slots=[])
    elif len(exact_tokens) == 1:
        result.update(
            selection_status="exact",
            selected_slots=[TOKEN_TO_SLOT[exact_tokens[0]]],
        )
    elif len(exact_tokens) > 1:
        result.update(selection_status="ambiguous", selected_slots=[])
    else:
        result["selection_status"] = result["automatic_selection_status"]
    return result


def schema_keywords(value: Any) -> set[str]:
    keywords: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, nested in node.items():
                keywords.add(key)
                if key == "properties":
                    for subschema in nested.values():
                        walk(subschema)
                else:
                    walk(nested)
        elif isinstance(node, list):
            for nested in node:
                walk(nested)

    walk(value)
    return keywords


def property_names(value: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            if key == "properties" and isinstance(nested, dict):
                names.update(nested)
            names.update(property_names(nested))
    elif isinstance(value, list):
        for nested in value:
            names.update(property_names(nested))
    return names


def values_at_key(
    value: Any, target_key: str, path: tuple[str, ...] = ()
) -> list[tuple[tuple[str, ...], Any]]:
    found: list[tuple[tuple[str, ...], Any]] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            nested_path = (*path, key)
            if key == target_key:
                found.append((nested_path, nested))
            found.extend(values_at_key(nested, target_key, nested_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(values_at_key(nested, target_key, (*path, str(index))))
    return found


def provider_safe_projection(semantic_schema: dict[str, Any]) -> dict[str, Any]:
    """Collapse exact tuple rows into the provider-safe homogeneous projection."""
    projected_properties: dict[str, Any] = {}
    for array_name, array_schema in semantic_schema["properties"].items():
        rows = array_schema["prefixItems"]
        row_properties = tuple(rows[0]["properties"])
        if any(tuple(row["properties"]) != row_properties for row in rows):
            raise ValueError("semantic rows do not share one property order")
        if any(row["required"] != rows[0]["required"] for row in rows):
            raise ValueError("semantic rows do not share one required set")
        if any(row["additionalProperties"] for row in rows):
            raise ValueError("semantic row is not closed")

        projected_row_properties: dict[str, Any] = {}
        for property_name in row_properties:
            values: list[str] = []
            for row in rows:
                property_schema = row["properties"][property_name]
                candidates = (
                    [property_schema["const"]]
                    if "const" in property_schema
                    else property_schema["enum"]
                )
                for candidate in candidates:
                    if candidate not in values:
                        values.append(candidate)
            projected_row_properties[property_name] = {
                "type": "string",
                "enum": values,
            }

        projected_properties[array_name] = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": projected_row_properties,
                "required": rows[0]["required"],
                "additionalProperties": False,
            },
            "minItems": array_schema["minItems"],
            "maxItems": array_schema["maxItems"],
        }
    return {
        "type": "object",
        "properties": projected_properties,
        "required": semantic_schema["required"],
        "additionalProperties": False,
    }


class UnresolvedDecisionGraphProtocolV8Tests(unittest.TestCase):
    def test_protocol_identity_authority_and_exact_slot_mapping(self) -> None:
        self.assertEqual(PROTOCOL["schema_version"], "8.0")
        self.assertEqual(PROTOCOL["protocol_id"], "H4-unresolved-decision-graph")
        self.assertEqual(PROTOCOL["status"], "frozen-proposal-only")
        self.assertEqual(PROTOCOL["claim_ceiling"], "structural-proposal-only")
        self.assertFalse(PROTOCOL["outcome_tuned"])
        self.assertEqual(PROTOCOL["authority_basis"], EXPECTED_AUTHORITY)
        self.assertEqual(tuple(PROTOCOL["slot_contract"]["stable_slot_order"]), SLOTS)
        self.assertEqual(
            tuple(tuple(pair) for pair in PROTOCOL["slot_contract"]["stable_pair_order"]),
            PAIRS,
        )
        actual_rows = tuple(
            (
                row["slot_id"],
                row["logical_atom"],
                row["adviser_id"],
                row["qualified_invocation"],
            )
            for row in PROTOCOL["slot_contract"]["slots"]
        )
        self.assertEqual(actual_rows, EXPECTED_SLOT_ROWS)

    def test_all_claim_bearing_nested_contracts_are_exact_and_closed(self) -> None:
        self.assertEqual(
            set(PROTOCOL),
            {
                "schema_version",
                "protocol_id",
                "status",
                "claim_ceiling",
                "outcome_tuned",
                "purpose",
                "novelty_statement",
                "authority_basis",
                "source_custody",
                "slot_contract",
                "model_output_contract",
                "deterministic_graph_resolution",
                "explicit_constraint",
                "parent_resolution_contract",
                "reference_boundary",
                "structural_discriminators",
                "structural_invariants",
                "qualification_controls",
            },
        )
        self.assertEqual(
            PROTOCOL["deterministic_graph_resolution"], EXPECTED_GRAPH_CONTRACT
        )
        self.assertEqual(PROTOCOL["explicit_constraint"], EXPECTED_EXPLICIT_CONSTRAINT)
        self.assertEqual(
            PROTOCOL["parent_resolution_contract"],
            EXPECTED_PARENT_RESOLUTION_CONTRACT,
        )
        self.assertEqual(PROTOCOL["reference_boundary"], EXPECTED_REFERENCE_BOUNDARY)
        self.assertEqual(
            PROTOCOL["qualification_controls"], EXPECTED_QUALIFICATION_CONTROLS
        )
        self.assertEqual(
            values_at_key(PROTOCOL, "claim_ceiling"),
            [
                (("claim_ceiling",), "structural-proposal-only"),
                (
                    ("qualification_controls", "claim_ceiling"),
                    EXPECTED_QUALIFICATION_CONTROLS["claim_ceiling"],
                ),
            ],
        )
        self.assertEqual(
            values_at_key(PROTOCOL, "prohibitions"),
            [
                (
                    ("parent_resolution_contract", "prohibitions"),
                    EXPECTED_PARENT_RESOLUTION_CONTRACT["prohibitions"],
                )
            ],
        )
        self.assertEqual(values_at_key(PROTOCOL, "completion_claim"), [])
        self.assertEqual(values_at_key(SEMANTIC_SCHEMA, "completion_claim"), [])
        self.assertEqual(values_at_key(RUNTIME_SCHEMA, "completion_claim"), [])
        self.assertIn(
            "no_completion_claim",
            PROTOCOL["parent_resolution_contract"]["prohibitions"],
        )

    def test_upstream_authority_git_objects_are_exact(self) -> None:
        for block_name, item_name in (
            ("h2_catalog", None),
            ("reference_policy", None),
            ("base_manifest_provenance_only", None),
            ("h3", "protocol"),
            ("h3", "selector_output_schema"),
        ):
            block = EXPECTED_AUTHORITY[block_name]
            authority = block[item_name] if item_name else block
            revision = block["commit"]
            tree = block["tree"]
            self.assertEqual(git_revision(f"{revision}^{{commit}}"), revision)
            self.assertEqual(git_revision(f"{revision}^{{tree}}"), tree)
            self.assertEqual(
                raw_sha256(git_bytes(revision, authority["path"])),
                authority["sha256"],
            )

    def test_semantic_schema_is_closed_and_enforces_exact_order(self) -> None:
        expected_states = ["unresolved", "resolved_or_absent", "uncertain"]
        self.assertEqual(
            SEMANTIC_SCHEMA["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertEqual(
            set(SEMANTIC_SCHEMA),
            {"$schema", "$id", "title", "type", "properties", "required", "additionalProperties"},
        )
        self.assertEqual(
            set(SEMANTIC_SCHEMA["properties"]),
            {"candidate_states", "pairwise_relations", "reference_needs"},
        )
        expected_lengths = {
            "candidate_states": 4,
            "pairwise_relations": 6,
            "reference_needs": 4,
        }
        for key, count in expected_lengths.items():
            array_schema = SEMANTIC_SCHEMA["properties"][key]
            self.assertEqual(len(array_schema["prefixItems"]), count)
            self.assertFalse(array_schema["items"])
            self.assertEqual((array_schema["minItems"], array_schema["maxItems"]), (count, count))
            for row_schema in array_schema["prefixItems"]:
                self.assertFalse(row_schema["additionalProperties"])
        for row_schema in SEMANTIC_SCHEMA["properties"]["candidate_states"]["prefixItems"]:
            self.assertEqual(row_schema["properties"]["state"]["enum"], expected_states)
        self.assertEqual(
            RUNTIME_SCHEMA["properties"]["candidate_states"]["items"]["properties"]["state"]["enum"],
            expected_states,
        )
        self.assertEqual(
            PROTOCOL["model_output_contract"]["candidate_states"]["allowed_states"],
            expected_states,
        )

        valid = model_output(states={"s0": "unresolved"})
        self.assertEqual(list(Draft202012Validator(SEMANTIC_SCHEMA).iter_errors(valid)), [])
        validate_model_output(valid)
        invalid_outputs = []
        extra_root = deepcopy(valid)
        extra_root["selected_slots"] = []
        invalid_outputs.append(extra_root)
        missing = deepcopy(valid)
        missing["candidate_states"] = missing["candidate_states"][:-1]
        invalid_outputs.append(missing)
        extra_row_key = deepcopy(valid)
        extra_row_key["reference_needs"][0]["reason"] = "forbidden"
        invalid_outputs.append(extra_row_key)
        for key in ("candidate_states", "pairwise_relations", "reference_needs"):
            reordered = deepcopy(valid)
            reordered[key][0], reordered[key][1] = reordered[key][1], reordered[key][0]
            invalid_outputs.append(reordered)
        wrong_id = deepcopy(valid)
        wrong_id["pairwise_relations"][0]["right_slot"] = "s3"
        invalid_outputs.append(wrong_id)
        widened_state_probe = deepcopy(valid)
        widened_state_probe["candidate_states"][0]["state"] = "complete"
        invalid_outputs.append(widened_state_probe)
        for invalid in invalid_outputs:
            self.assertTrue(list(Draft202012Validator(SEMANTIC_SCHEMA).iter_errors(invalid)))
            with self.assertRaises(ValueError):
                validate_model_output(invalid)

    def test_runtime_schema_is_a_deliberate_provider_safe_projection(self) -> None:
        allowed = {
            "type",
            "properties",
            "items",
            "required",
            "additionalProperties",
            "minItems",
            "maxItems",
            "enum",
        }
        self.assertEqual(schema_keywords(RUNTIME_SCHEMA), allowed)
        self.assertEqual(RUNTIME_SCHEMA, provider_safe_projection(SEMANTIC_SCHEMA))
        serialized = json.dumps(RUNTIME_SCHEMA, sort_keys=True)
        for forbidden in ("allOf", "prefixItems", "$ref"):
            self.assertNotIn(f'"{forbidden}"', serialized)
        valid = model_output(states={"s0": "unresolved"})
        self.assertEqual(list(Draft202012Validator(RUNTIME_SCHEMA).iter_errors(valid)), [])
        reordered = deepcopy(valid)
        reordered["candidate_states"][0], reordered["candidate_states"][1] = (
            reordered["candidate_states"][1],
            reordered["candidate_states"][0],
        )
        self.assertEqual(list(Draft202012Validator(RUNTIME_SCHEMA).iter_errors(reordered)), [])
        self.assertTrue(list(Draft202012Validator(SEMANTIC_SCHEMA).iter_errors(reordered)))
        self.assertIn("deliberate provider-safe", PROTOCOL["model_output_contract"]["runtime_projection"])

    def test_model_output_contract_forbids_parent_owned_fields(self) -> None:
        forbidden = {
            "selected_slots",
            "root_slots",
            "graph_status",
            "automatic_selection_status",
            "selection_status",
            "logical_atoms",
            "atoms",
            "advisers",
            "routes",
            "authority",
            "effects",
            "claims",
        }
        self.assertEqual(set(PROTOCOL["model_output_contract"]["model_must_not_output"]), forbidden)
        self.assertTrue(property_names(SEMANTIC_SCHEMA).isdisjoint(forbidden))
        self.assertTrue(property_names(RUNTIME_SCHEMA).isdisjoint(forbidden))

    def test_closed_chain_selects_only_the_controller_root(self) -> None:
        chain = model_output(
            states={"s0": "unresolved", "s1": "unresolved", "s2": "unresolved"},
            relations={
                ("s0", "s1"): "left_controls_right_downstream",
                ("s0", "s2"): "left_controls_right_downstream",
                ("s1", "s2"): "left_controls_right_downstream",
            },
        )
        self.assertEqual(
            resolve(chain),
            {
                "graph_status": "valid",
                "automatic_selection_status": "automatic",
                "selection_status": "automatic",
                "root_slots": ["s0"],
                "selected_slots": ["s0"],
            },
        )

    def test_fork_and_transitively_closed_diamond_each_select_one_root(self) -> None:
        fork = model_output(
            states={"s0": "unresolved", "s1": "unresolved", "s2": "unresolved"},
            relations={
                ("s0", "s1"): "left_controls_right_downstream",
                ("s0", "s2"): "left_controls_right_downstream",
            },
        )
        diamond = model_output(
            states={slot: "unresolved" for slot in SLOTS},
            relations={
                ("s0", "s1"): "left_controls_right_downstream",
                ("s0", "s2"): "left_controls_right_downstream",
                ("s0", "s3"): "left_controls_right_downstream",
                ("s1", "s3"): "left_controls_right_downstream",
                ("s2", "s3"): "left_controls_right_downstream",
            },
        )
        self.assertEqual(resolve(fork)["selected_slots"], ["s0"])
        self.assertEqual(resolve(diamond)["selected_slots"], ["s0"])
        self.assertEqual(resolve(diamond)["graph_status"], "valid")

    def test_transitivity_failure_is_graph_invalid(self) -> None:
        not_closed = model_output(
            states={"s0": "unresolved", "s1": "unresolved", "s2": "unresolved"},
            relations={
                ("s0", "s1"): "left_controls_right_downstream",
                ("s1", "s2"): "left_controls_right_downstream",
            },
        )
        self.assertEqual(
            resolve(not_closed),
            {
                "graph_status": "graph_invalid",
                "automatic_selection_status": "graph_invalid",
                "selection_status": "graph_invalid",
                "root_slots": [],
                "selected_slots": [],
            },
        )

    def test_cycle_has_cycle_status_before_transitivity(self) -> None:
        cycle = model_output(
            states={"s0": "unresolved", "s1": "unresolved", "s2": "unresolved"},
            relations={
                ("s0", "s1"): "left_controls_right_downstream",
                ("s0", "s2"): "right_controls_left_downstream",
                ("s1", "s2"): "left_controls_right_downstream",
            },
        )
        self.assertEqual(resolve(cycle)["graph_status"], "graph_cycle")
        self.assertEqual(resolve(cycle)["selection_status"], "graph_cycle")
        self.assertEqual(resolve(cycle)["selected_slots"], [])

    def test_uncertainty_abstains_and_invalid_pair_combinations_are_rejected(self) -> None:
        uncertain_state = model_output(states={"s0": "uncertain"})
        uncertain_relation = model_output(
            states={"s0": "unresolved", "s1": "unresolved"},
            relations={("s0", "s1"): "uncertain"},
        )
        for payload in (uncertain_state, uncertain_relation):
            self.assertEqual(resolve(payload)["graph_status"], "graph_uncertain")
            self.assertEqual(resolve(payload)["selected_slots"], [])

        invalid_resolved_edge = model_output(
            states={"s0": "unresolved"},
            relations={("s0", "s1"): "left_controls_right_downstream"},
        )
        invalid_unresolved_unrelated = model_output(
            states={"s0": "unresolved", "s1": "unresolved"},
            relations={("s0", "s1"): "unrelated"},
        )
        invalid_uncertain_incident = model_output(
            states={"s0": "uncertain"},
            relations={("s0", "s1"): "unrelated"},
        )
        for payload in (
            invalid_resolved_edge,
            invalid_unresolved_unrelated,
            invalid_uncertain_incident,
        ):
            self.assertEqual(resolve(payload)["graph_status"], "graph_invalid")

    def test_more_than_two_roots_is_cap_exceeded(self) -> None:
        three_roots = model_output(
            states={"s0": "unresolved", "s1": "unresolved", "s2": "unresolved"}
        )
        self.assertEqual(
            resolve(three_roots),
            {
                "graph_status": "valid",
                "automatic_selection_status": "cap_exceeded",
                "selection_status": "cap_exceeded",
                "root_slots": ["s0", "s1", "s2"],
                "selected_slots": [],
            },
        )

    def test_exact_ambiguous_and_unrecognized_h4_parser_semantics(self) -> None:
        controller = model_output(
            states={"s0": "unresolved", "s1": "unresolved"},
            relations={("s0", "s1"): "left_controls_right_downstream"},
        )
        exact = resolve(controller, "Use $codex-task-contract.")
        self.assertEqual(exact["selection_status"], "exact")
        self.assertEqual(exact["root_slots"], ["s0"])
        self.assertEqual(exact["selected_slots"], ["s1"])

        invalid_graph = model_output(
            states={"s0": "unresolved", "s1": "unresolved"},
            relations={("s0", "s1"): "unrelated"},
        )
        exact_invalid = resolve(invalid_graph, "Use $verification-strategy-engineering.")
        self.assertEqual(exact_invalid["graph_status"], "graph_invalid")
        self.assertEqual(exact_invalid["automatic_selection_status"], "graph_invalid")
        self.assertEqual(exact_invalid["selection_status"], "exact")
        self.assertEqual(exact_invalid["selected_slots"], ["s2"])

        for text in (
            "Use $codex-task-contract and $engineering-learning-loop.",
            "Use $codex-task-contract twice: $codex-task-contract.",
        ):
            result = resolve(controller, text)
            self.assertEqual(result["selection_status"], "ambiguous")
            self.assertEqual(result["selected_slots"], [])

        for text in (
            "Use $unknown.",
            "Use $codex-task-contract and $unknown.",
            "Use $codex-task-contract-extra.",
        ):
            result = resolve(controller, text)
            self.assertEqual(result["selection_status"], "unrecognized")
            self.assertEqual(result["selected_slots"], [])

        schema_invalid = deepcopy(controller)
        schema_invalid["candidate_states"].pop()
        with self.assertRaises(ValueError):
            resolve(schema_invalid, "Use $agentic-engineering.")

    def test_h4_unicode_safe_parent_parser_and_token_order_are_exact(self) -> None:
        self.assertNotIn("qualified_invocation_grammar", CONSTRAINT)
        self.assertEqual(CONSTRAINT, EXPECTED_EXPLICIT_CONSTRAINT)
        self.assertEqual(
            tuple(TOKEN_TO_SLOT.items()),
            tuple((row[3], row[0]) for row in EXPECTED_SLOT_ROWS),
        )
        self.assertEqual(
            tuple(PARSER_CONTRACT["qualified_token_bodies"]),
            tuple(token.removeprefix("$") for token in TOKEN_TO_SLOT),
        )
        self.assertTrue(all(body.isascii() for body in PARSER_CONTRACT["qualified_token_bodies"]))

        for token in TOKEN_TO_SLOT:
            self.assertEqual(parse_invocation_like_tokens(f" ({token}) "), (token,))
            self.assertEqual(parse_invocation_like_tokens(f" {token}! "), (token,))
            self.assertEqual(resolve(model_output(), f"Use ({token}).")["selection_status"], "exact")

        for adjacent in ("é", "β", "\u0301"):
            self.assertEqual(
                parse_invocation_like_tokens(f"{adjacent}$agentic-engineering"), ()
            )
            self.assertEqual(
                parse_invocation_like_tokens(f"$agentic-engineering{adjacent}"), ()
            )

        retained = PARSER_CONTRACT["boundary"]["retained_rejection_fixtures"]
        self.assertEqual(
            [fixture["codepoint"] for fixture in retained],
            ["U+200C", "U+200D", "U+2060", "U+FEFF", "U+202E", "U+203F"],
        )
        for fixture in retained:
            adjacent = chr(int(fixture["codepoint"].removeprefix("U+"), 16))
            self.assertEqual(unicodedata.category(adjacent), fixture["category"])
            for task_text in (
                f"{adjacent}$agentic-engineering",
                f"$agentic-engineering{adjacent}",
            ):
                self.assertEqual(parse_invocation_like_tokens(task_text), ())
                self.assertEqual(
                    resolve(model_output(), task_text)["selection_status"], "automatic"
                )

        self.assertEqual(
            parse_invocation_like_tokens("$codex-task-contract-extra"),
            ("$codex-task-contract-extra",),
        )
        self.assertEqual(
            parse_invocation_like_tokens("$Agentic-engineering"),
            ("$Agentic-engineering",),
        )
        self.assertEqual(parse_invocation_like_tokens("$unknown"), ("$unknown",))
        self.assertEqual(
            resolve(model_output(), "Use $Agentic-engineering.")["selection_status"],
            "unrecognized",
        )

    def test_reference_needs_cannot_influence_routing(self) -> None:
        graph = model_output(
            states={"s0": "unresolved", "s1": "unresolved"},
            relations={("s0", "s1"): "independent"},
        )
        changed = deepcopy(graph)
        changed["reference_needs"] = [
            {"slot_id": slot, "need": need}
            for slot, need in zip(
                SLOTS, ("primary", "secondary", "uncertain", "primary"), strict=True
            )
        ]
        self.assertEqual(resolve(graph), resolve(changed))
        boundary = PROTOCOL["reference_boundary"]
        self.assertEqual(boundary["routing_influence"], "none")
        self.assertTrue(boundary["uncertain_need_does_not_change_graph_status"])

    def test_discriminators_and_invariants_are_executable(self) -> None:
        discriminator_ids = [
            row["discriminator_id"] for row in PROTOCOL["structural_discriminators"]
        ]
        self.assertEqual(
            discriminator_ids,
            [
                "controller-and-downstream-select-root-only",
                "independent-pair-selects-both",
            ],
        )
        controller = model_output(
            states={"s0": "unresolved", "s1": "unresolved"},
            relations={("s0", "s1"): "left_controls_right_downstream"},
        )
        independent = model_output(
            states={"s0": "unresolved", "s1": "unresolved"},
            relations={("s0", "s1"): "independent"},
        )
        self.assertEqual(resolve(controller)["selected_slots"], ["s0"])
        self.assertEqual(resolve(independent)["selected_slots"], ["s0", "s1"])

        invariant_ids = [
            row["invariant_id"] for row in PROTOCOL["structural_invariants"]
        ]
        self.assertEqual(
            invariant_ids, ["single-direct-root", "no-unresolved-selects-none"]
        )
        single = resolve(model_output(states={"s2": "unresolved"}))
        none = resolve(model_output())
        self.assertEqual((single["root_slots"], single["selected_slots"]), (["s2"], ["s2"]))
        self.assertEqual((none["root_slots"], none["selected_slots"]), ([], []))

    def test_terminal_failure_no_tuning_and_structural_ceiling(self) -> None:
        controls = PROTOCOL["qualification_controls"]
        self.assertTrue(controls["aq8_failure_policy"]["terminal_stop"])
        self.assertIn("independent new evidence", controls["aq8_failure_policy"]["rule"])
        self.assertFalse(
            controls["aq8_failure_policy"]["outcome_tuning_after_failure_permitted"]
        )
        self.assertFalse(controls["outcome_tuned"])
        self.assertFalse(controls["corpus_inputs_permitted"])
        self.assertFalse(controls["evaluator_output_inputs_permitted"])
        self.assertEqual(PROTOCOL["claim_ceiling"], "structural-proposal-only")
        self.assertIn("structural resolver layer", PROTOCOL["novelty_statement"])


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    raise SystemExit(0 if result.wasSuccessful() else 1)
