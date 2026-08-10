#!/usr/bin/env python3
"""Pure, parent-owned AQ8 unresolved-decision graph resolver.

This module intentionally has no filesystem, Git, subprocess, model, corpus,
or result surface.  It validates the model's anonymous fixed-slot graph,
computes H4 graph/root telemetry, applies the Unicode-safe invocation grammar,
and only then derives route-independent reference requests and their canonical
payload cover.
"""
from __future__ import annotations

import itertools
import json
import unicodedata
from copy import deepcopy
from typing import Any, Iterable


class ResolverError(ValueError):
    """A closed H4 input or deterministic-resolution contract was violated."""


_ROOT_KEYS = ("candidate_states", "pairwise_relations", "reference_needs")
_PACKET_KEYS = (
    "instruction",
    "task_text",
    "slot_order",
    "pair_order",
    "condition_guidance",
    "support_legend",
)


def canonical_json(value: Any) -> bytes:
    """Return the one ASCII canonical JSON encoding used for digest custody."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as error:
        raise ResolverError("value is not canonical JSON") from error


def _object(value: Any, keys: Iterable[str], message: str) -> dict[str, Any]:
    expected = set(keys)
    if not isinstance(value, dict) or set(value) != expected:
        raise ResolverError(message)
    return value


def _exact_value(value: Any, expected: Any) -> bool:
    """Compare JSON-like values without Python's bool/int equivalence."""
    if type(value) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(value) == set(expected) and all(
            _exact_value(value[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(value) == len(expected) and all(
            _exact_value(item, target)
            for item, target in zip(value, expected, strict=True)
        )
    return value == expected


def _contract(protocol: Any) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...], dict[str, Any]]:
    if not isinstance(protocol, dict):
        raise ResolverError("H4 protocol is unavailable")
    slots = protocol.get("slot_contract", {})
    output = protocol.get("model_output_contract", {})
    if not isinstance(slots, dict) or not isinstance(output, dict):
        raise ResolverError("H4 output contract is unavailable")
    slot_order = tuple(slots.get("stable_slot_order", ()))
    pair_order = tuple(tuple(pair) for pair in slots.get("stable_pair_order", ()))
    if (
        slot_order != ("s0", "s1", "s2", "s3")
        or pair_order
        != (
            ("s0", "s1"),
            ("s0", "s2"),
            ("s0", "s3"),
            ("s1", "s2"),
            ("s1", "s3"),
            ("s2", "s3"),
        )
    ):
        raise ResolverError("H4 slot or pair order is invalid")
    if output.get("only_top_level_keys") != list(_ROOT_KEYS):
        raise ResolverError("H4 root contract is invalid")
    expected = {
        "candidate_states": {
            "row_count": 4,
            "row_keys": ["slot_id", "state"],
            "slot_order": list(slot_order),
            "allowed_states": ["unresolved", "resolved_or_absent", "uncertain"],
        },
        "pairwise_relations": {
            "row_count": 6,
            "row_keys": ["left_slot", "right_slot", "relation"],
            "pair_order": [list(pair) for pair in pair_order],
            "allowed_relations": [
                "left_controls_right_downstream",
                "right_controls_left_downstream",
                "independent",
                "unrelated",
                "uncertain",
            ],
        },
        "reference_needs": {
            "row_count": 4,
            "row_keys": ["slot_id", "need"],
            "slot_order": list(slot_order),
            "allowed_needs": ["none", "primary", "secondary", "uncertain"],
        },
    }
    if any(output.get(key) != value for key, value in expected.items()):
        raise ResolverError("H4 ordered row contract is invalid")
    return slot_order, pair_order, output


def _canonical_graph_output(value: Any, protocol: Any) -> dict[str, list[dict[str, str]]]:
    slot_order, pair_order, output = _contract(protocol)
    _object(value, _ROOT_KEYS, "graph output root is not closed")
    states = value["candidate_states"]
    relations = value["pairwise_relations"]
    needs = value["reference_needs"]
    if not isinstance(states, list) or len(states) != 4:
        raise ResolverError("candidate state rows are invalid")
    if not isinstance(relations, list) or len(relations) != 6:
        raise ResolverError("pairwise relation rows are invalid")
    if not isinstance(needs, list) or len(needs) != 4:
        raise ResolverError("reference need rows are invalid")

    canonical_states: list[dict[str, str]] = []
    for slot_id, row in zip(slot_order, states, strict=True):
        _object(row, ("slot_id", "state"), "candidate state row is not closed")
        if row["slot_id"] != slot_id or row["state"] not in output["candidate_states"]["allowed_states"]:
            raise ResolverError("candidate state order or enum is invalid")
        canonical_states.append({"slot_id": slot_id, "state": row["state"]})

    canonical_relations: list[dict[str, str]] = []
    for (left, right), row in zip(pair_order, relations, strict=True):
        _object(row, ("left_slot", "right_slot", "relation"), "pairwise relation row is not closed")
        if (
            row["left_slot"] != left
            or row["right_slot"] != right
            or row["relation"] not in output["pairwise_relations"]["allowed_relations"]
        ):
            raise ResolverError("pairwise relation order or enum is invalid")
        canonical_relations.append(
            {"left_slot": left, "right_slot": right, "relation": row["relation"]}
        )

    canonical_needs: list[dict[str, str]] = []
    for slot_id, row in zip(slot_order, needs, strict=True):
        _object(row, ("slot_id", "need"), "reference need row is not closed")
        if row["slot_id"] != slot_id or row["need"] not in output["reference_needs"]["allowed_needs"]:
            raise ResolverError("reference need order or enum is invalid")
        canonical_needs.append({"slot_id": slot_id, "need": row["need"]})
    return {
        "candidate_states": canonical_states,
        "pairwise_relations": canonical_relations,
        "reference_needs": canonical_needs,
    }


def _semantic_schema_projection(protocol: Any) -> dict[str, Any]:
    slot_order, pair_order, output = _contract(protocol)

    def row(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

    def array(prefix_items: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "type": "array",
            "prefixItems": prefix_items,
            "items": False,
            "minItems": len(prefix_items),
            "maxItems": len(prefix_items),
        }

    properties = {
        "candidate_states": array(
            [
                row(
                    {
                        "slot_id": {"const": slot},
                        "state": {"type": "string", "enum": output["candidate_states"]["allowed_states"]},
                    },
                    ["slot_id", "state"],
                )
                for slot in slot_order
            ]
        ),
        "pairwise_relations": array(
            [
                row(
                    {
                        "left_slot": {"const": left},
                        "right_slot": {"const": right},
                        "relation": {"type": "string", "enum": output["pairwise_relations"]["allowed_relations"]},
                    },
                    ["left_slot", "right_slot", "relation"],
                )
                for left, right in pair_order
            ]
        ),
        "reference_needs": array(
            [
                row(
                    {
                        "slot_id": {"const": slot},
                        "need": {"type": "string", "enum": output["reference_needs"]["allowed_needs"]},
                    },
                    ["slot_id", "need"],
                )
                for slot in slot_order
            ]
        ),
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.local/agentic-engineering/evals/foundation-v4/unresolved-decision-graph-selector-output-schema-v8.json",
        "title": "AQ8 closed unresolved-decision graph output",
        "type": "object",
        "properties": properties,
        "required": list(_ROOT_KEYS),
        "additionalProperties": False,
    }


def validate_graph_output(value: Any, protocol: Any, semantic_schema: Any) -> dict[str, list[dict[str, str]]]:
    """Validate the exact semantic schema and return a detached canonical graph."""
    if not _exact_value(semantic_schema, _semantic_schema_projection(protocol)):
        raise ResolverError("semantic graph schema is not the exact H4 projection")
    return _canonical_graph_output(value, protocol)


def build_condition_packet(adapter: Any, condition_id: Any, task_text: Any) -> dict[str, Any]:
    """Build the exact six-key packet; condition guidance is its only variance."""
    if not isinstance(adapter, dict) or not isinstance(task_text, str):
        raise ResolverError("adapter or task text is invalid")
    contract = adapter.get("packet_contract")
    conditions = adapter.get("conditions")
    if not isinstance(contract, dict) or not isinstance(conditions, dict) or condition_id not in conditions:
        raise ResolverError("condition adapter is unavailable")
    if contract.get("packet_keys") != list(_PACKET_KEYS) or not isinstance(contract.get("instruction"), str):
        raise ResolverError("condition packet contract is invalid")
    slot_order = adapter.get("slot_order")
    pair_order = adapter.get("pair_order")
    support = adapter.get("support_legend")
    condition = conditions[condition_id]
    if (
        slot_order != ["s0", "s1", "s2", "s3"]
        or pair_order
        != [["s0", "s1"], ["s0", "s2"], ["s0", "s3"], ["s1", "s2"], ["s1", "s3"], ["s2", "s3"]]
        or not isinstance(support, list)
        or not isinstance(condition, dict)
    ):
        raise ResolverError("condition packet inputs are invalid")
    guidance = condition.get("condition_guidance")
    guidance_sha = condition.get("condition_guidance_canonical_sha256")
    support_sha = adapter.get("support_legend_canonical_sha256")
    import hashlib

    if (
        not isinstance(guidance, list)
        or hashlib.sha256(canonical_json(guidance)).hexdigest() != guidance_sha
        or hashlib.sha256(canonical_json(support)).hexdigest() != support_sha
    ):
        raise ResolverError("condition packet digest mismatch")
    return {
        "instruction": contract["instruction"],
        "task_text": task_text,
        "slot_order": deepcopy(slot_order),
        "pair_order": deepcopy(pair_order),
        "condition_guidance": deepcopy(guidance),
        "support_legend": deepcopy(support),
    }


def _allowed_boundary(parser: dict[str, Any], codepoint: str | None) -> bool:
    boundary = parser.get("boundary")
    if not isinstance(boundary, dict):
        raise ResolverError("H4 boundary parser is invalid")
    if codepoint is None:
        return boundary.get("allowed_when_absent") is True
    category = unicodedata.category(codepoint)
    prefixes = boundary.get("disallowed_unicode_general_category_prefixes")
    categories = boundary.get("disallowed_unicode_general_categories")
    literals = boundary.get("disallowed_literals")
    if not all(isinstance(value, list) for value in (prefixes, categories, literals)):
        raise ResolverError("H4 boundary parser is invalid")
    return codepoint not in literals and category not in categories and category[:1] not in prefixes


def _in_ranges(codepoint: str, ranges: Any) -> bool:
    if not isinstance(ranges, list):
        raise ResolverError("H4 parser range is invalid")
    try:
        return any(start <= codepoint <= end for item in ranges for start, end in (item.split("-", 1),))
    except (AttributeError, ValueError) as error:
        raise ResolverError("H4 parser range is invalid") from error


def _invocation_tokens(task_text: Any, protocol: Any) -> tuple[str, ...]:
    if not isinstance(task_text, str) or not isinstance(protocol, dict):
        raise ResolverError("task text or protocol is invalid")
    explicit = protocol.get("explicit_constraint")
    parser = explicit.get("h4_parent_parser_contract") if isinstance(explicit, dict) else None
    if not isinstance(parser, dict) or parser.get("normalization") != "Unicode NFC":
        raise ResolverError("H4 parser contract is invalid")
    body = parser.get("invocation_like_body")
    if not isinstance(body, dict) or body.get("prefix") != "$" or body.get("scan") != "maximal":
        raise ResolverError("H4 invocation scan contract is invalid")
    first = body.get("first_codepoint", {})
    remaining = body.get("remaining_codepoints", {})
    if first.get("alphabet") != "ASCII" or remaining.get("alphabet") != "ASCII" or remaining.get("minimum_count") != 0:
        raise ResolverError("H4 invocation alphabet contract is invalid")
    remaining_literals = remaining.get("allowed_literals")
    if not isinstance(remaining_literals, list):
        raise ResolverError("H4 invocation literal contract is invalid")
    text = unicodedata.normalize("NFC", task_text)
    tokens: list[str] = []
    for start, codepoint in enumerate(text):
        if codepoint != "$" or start + 1 >= len(text) or not _in_ranges(text[start + 1], first.get("allowed_ranges")):
            continue
        end = start + 2
        while end < len(text) and (
            _in_ranges(text[end], remaining.get("allowed_ranges")) or text[end] in remaining_literals
        ):
            end += 1
        before = text[start - 1] if start else None
        after = text[end] if end < len(text) else None
        if _allowed_boundary(parser, before) and _allowed_boundary(parser, after):
            tokens.append(text[start:end])
    return tuple(tokens)


def _graph_telemetry(graph: dict[str, list[dict[str, str]]], protocol: Any) -> dict[str, Any]:
    slot_order, _, _ = _contract(protocol)
    resolution = protocol.get("deterministic_graph_resolution", {})
    if resolution.get("selection_cap") != 2:
        raise ResolverError("H4 selection cap is invalid")
    states = {row["slot_id"]: row["state"] for row in graph["candidate_states"]}
    edges: set[tuple[str, str]] = set()
    uncertain = any(state == "uncertain" for state in states.values())
    for row in graph["pairwise_relations"]:
        left, right, relation = row["left_slot"], row["right_slot"], row["relation"]
        left_state, right_state = states[left], states[right]
        uncertain = uncertain or relation == "uncertain"
        if "uncertain" in (left_state, right_state):
            compatible = relation == "uncertain"
        elif "resolved_or_absent" in (left_state, right_state):
            compatible = relation == "unrelated"
        else:
            compatible = relation in {
                "left_controls_right_downstream",
                "right_controls_left_downstream",
                "independent",
                "uncertain",
            }
        if not compatible:
            return {"graph_status": "graph_invalid", "automatic_selection_status": "graph_invalid", "root_slots": [], "selected_slots": []}
        if relation == "left_controls_right_downstream":
            edges.add((left, right))
        elif relation == "right_controls_left_downstream":
            edges.add((right, left))

    unresolved = tuple(slot for slot in slot_order if states[slot] == "unresolved")
    adjacency = {slot: set() for slot in unresolved}
    for source, target in edges:
        if source not in adjacency or target not in adjacency:
            return {"graph_status": "graph_invalid", "automatic_selection_status": "graph_invalid", "root_slots": [], "selected_slots": []}
        adjacency[source].add(target)

    visiting: set[str] = set()
    visited: set[str] = set()

    def cyclic(slot: str) -> bool:
        if slot in visiting:
            return True
        if slot in visited:
            return False
        visiting.add(slot)
        if any(cyclic(target) for target in adjacency[slot]):
            return True
        visiting.remove(slot)
        visited.add(slot)
        return False

    if any(cyclic(slot) for slot in unresolved):
        return {"graph_status": "graph_cycle", "automatic_selection_status": "graph_cycle", "root_slots": [], "selected_slots": []}
    for source in unresolved:
        reachable: set[str] = set()
        pending = list(adjacency[source])
        while pending:
            target = pending.pop()
            if target in reachable:
                continue
            reachable.add(target)
            pending.extend(adjacency[target] - reachable)
        if any((source, target) not in edges for target in reachable):
            return {"graph_status": "graph_invalid", "automatic_selection_status": "graph_invalid", "root_slots": [], "selected_slots": []}
    if uncertain:
        return {"graph_status": "graph_uncertain", "automatic_selection_status": "graph_uncertain", "root_slots": [], "selected_slots": []}
    downstream = {target for _, target in edges}
    roots = [slot for slot in unresolved if slot not in downstream]
    if len(roots) > 2:
        return {"graph_status": "valid", "automatic_selection_status": "cap_exceeded", "root_slots": roots, "selected_slots": []}
    return {"graph_status": "valid", "automatic_selection_status": "automatic", "root_slots": roots, "selected_slots": roots}


def _slot_rows(policy: Any, slot_order: tuple[str, ...]) -> dict[str, dict[str, str]]:
    rows = policy.get("reference_need_contract", {}).get("ordered_slot_table") if isinstance(policy, dict) else None
    if not isinstance(rows, list) or [row.get("slot_id") if isinstance(row, dict) else None for row in rows] != list(slot_order):
        raise ResolverError("H4 reference slot table is invalid")
    expected = {"slot_id", "logical_atom", "adviser_id", "primary_trigger_id", "secondary_trigger_id"}
    for row in rows:
        _object(row, expected, "H4 reference slot row is not closed")
        if any(not isinstance(value, str) or not value for value in row.values()):
            raise ResolverError("H4 reference slot row is invalid")
    return {row["slot_id"]: row for row in rows}


def _payload_catalog(base_manifest: Any) -> list[dict[str, Any]]:
    skills = base_manifest.get("skills") if isinstance(base_manifest, dict) else None
    if not isinstance(skills, list):
        raise ResolverError("base manifest payload catalog is unavailable")
    catalog: list[dict[str, Any]] = []
    for skill in skills:
        if not isinstance(skill, dict) or not isinstance(skill.get("id"), str) or not isinstance(skill.get("references"), list):
            raise ResolverError("base manifest skill catalog is invalid")
        for reference in skill["references"]:
            if not isinstance(reference, dict):
                raise ResolverError("base manifest reference is invalid")
            required = {"payload_id", "sha256", "trigger_ids"}
            if not required.issubset(reference) or not isinstance(reference["payload_id"], str) or not isinstance(reference["trigger_ids"], list):
                raise ResolverError("base manifest reference is invalid")
            catalog.append(
                {
                    "payload_id": reference["payload_id"],
                    "owner_adviser_id": skill["id"],
                    "trigger_ids": tuple(reference["trigger_ids"]),
                }
            )
    identities = [row["payload_id"] for row in catalog]
    if len(identities) != len(set(identities)):
        raise ResolverError("base manifest payload identity is duplicated")
    return catalog


def _canonical_cover(requests: list[dict[str, str]], policy: Any, base_manifest: Any) -> dict[str, Any]:
    cover = policy.get("canonical_cover") if isinstance(policy, dict) else None
    if not isinstance(cover, dict) or cover.get("maximum_payloads") != 3:
        raise ResolverError("H4 canonical cover contract is invalid")
    required = {(row["owner_adviser_id"], row["trigger_id"]) for row in requests}
    catalog = sorted(
        (
            row
            for row in _payload_catalog(base_manifest)
            if any(row["owner_adviser_id"] == owner and trigger in row["trigger_ids"] for owner, trigger in required)
        ),
        key=lambda row: row["payload_id"],
    )

    def covers(rows: tuple[dict[str, Any], ...]) -> bool:
        return all(
            any(row["owner_adviser_id"] == owner and trigger in row["trigger_ids"] for row in rows)
            for owner, trigger in required
        )

    for count in range(len(catalog) + 1):
        choices = [choice for choice in itertools.combinations(catalog, count) if covers(choice)]
        if choices:
            chosen = min(choices, key=lambda choice: tuple(row["payload_id"] for row in choice))
            if count > 3:
                return {"status": "cap_exceeded", "resolved_count": count, "canonical_payload_id_tuple": []}
            return {
                "status": "resolved",
                "resolved_count": count,
                "canonical_payload_id_tuple": [row["payload_id"] for row in chosen],
            }
    return {"status": "unresolved", "resolved_count": 0, "canonical_payload_id_tuple": []}


def resolve_references(selection_status: Any, selected_slots: Any, reference_needs: Any,
                       policy: Any, base_manifest: Any) -> dict[str, Any]:
    """Derive references without permitting them to influence H4 routing."""
    if not isinstance(policy, dict):
        raise ResolverError("H4 reference policy is unavailable")
    contract = policy.get("reference_need_contract", {})
    gate = contract.get("selection_gate", {}) if isinstance(contract, dict) else {}
    slot_order = tuple(contract.get("slot_order", ())) if isinstance(contract, dict) else ()
    if slot_order != ("s0", "s1", "s2", "s3"):
        raise ResolverError("H4 reference slot order is invalid")
    emitting = tuple(gate.get("emitting_selection_statuses", ()))
    non_emitting = tuple(gate.get("non_emitting_selection_statuses", ()))
    if selection_status not in (*emitting, *non_emitting):
        raise ResolverError("selection status is outside H4 reference policy")
    if (
        not isinstance(selected_slots, list)
        or selected_slots != [slot for slot in slot_order if slot in selected_slots]
        or len(selected_slots) != len(set(selected_slots))
    ):
        raise ResolverError("selected slots are invalid or unordered")
    if not isinstance(reference_needs, list) or len(reference_needs) != 4:
        raise ResolverError("reference needs are invalid")
    needs: dict[str, str] = {}
    allowed_needs = tuple(contract.get("reference_need_enum", ()))
    for slot, row in zip(slot_order, reference_needs, strict=True):
        _object(row, ("slot_id", "need"), "reference need row is not closed")
        if row["slot_id"] != slot or row["need"] not in allowed_needs:
            raise ResolverError("reference need order or enum is invalid")
        needs[slot] = row["need"]
    if selection_status in non_emitting:
        if selected_slots or any(need != "none" for need in needs.values()):
            raise ResolverError("non-emitting selection cannot carry reference needs")
    else:
        if selection_status == "automatic" and len(selected_slots) > 2:
            raise ResolverError("automatic reference selection exceeds cap")
        if selection_status == "exact" and len(selected_slots) != 1:
            raise ResolverError("exact reference selection is not singular")
        if any(needs[slot] != "none" for slot in slot_order if slot not in selected_slots):
            raise ResolverError("unselected slot carries a reference need")

    rows = _slot_rows(policy, slot_order)
    requests: list[dict[str, str]] = []
    uncertain_slots: list[str] = []
    seen: set[tuple[str, str]] = set()
    if selection_status in emitting:
        for slot in selected_slots:
            need = needs[slot]
            if need == "uncertain":
                uncertain_slots.append(slot)
            elif need in {"primary", "secondary"}:
                request = {
                    "owner_adviser_id": rows[slot]["adviser_id"],
                    "trigger_id": rows[slot][f"{need}_trigger_id"],
                }
                identity = (request["owner_adviser_id"], request["trigger_id"])
                if identity not in seen:
                    seen.add(identity)
                    requests.append(request)
    advisers = [rows[slot]["adviser_id"] for slot in selected_slots]
    complement = [rows[slot]["adviser_id"] for slot in slot_order if slot not in selected_slots]
    return {
        "selected_adviser_ids": advisers,
        "complement_adviser_ids": complement,
        "reference_requests": requests,
        "reference_uncertain_slots": uncertain_slots,
        "reference_resolution": _canonical_cover(requests, policy, base_manifest),
    }


def resolve_graph(task_text: Any, graph_output: Any, protocol: Any,
                  reference_policy: Any, base_manifest: Any) -> dict[str, Any]:
    """Run frozen H4 graph, invocation, adviser, request, and cover resolution."""
    graph = _canonical_graph_output(graph_output, protocol)
    telemetry = _graph_telemetry(graph, protocol)
    explicit = protocol.get("explicit_constraint") if isinstance(protocol, dict) else None
    rows = explicit.get("ordered_token_to_slot") if isinstance(explicit, dict) else None
    if not isinstance(rows, list) or len(rows) != 4:
        raise ResolverError("H4 explicit token mapping is invalid")
    token_to_slot: dict[str, str] = {}
    for row in rows:
        _object(row, ("token", "slot_id"), "H4 explicit token row is not closed")
        if row["token"] in token_to_slot or row["slot_id"] in token_to_slot.values():
            raise ResolverError("H4 explicit token mapping is duplicated")
        token_to_slot[row["token"]] = row["slot_id"]
    tokens = _invocation_tokens(task_text, protocol)
    recognized = [token_to_slot[token] for token in tokens if token in token_to_slot]
    if any(token not in token_to_slot for token in tokens):
        selection_status, selected = "unrecognized", []
    elif len(recognized) == 1:
        selection_status, selected = "exact", recognized
    elif len(recognized) > 1:
        selection_status, selected = "ambiguous", []
    else:
        selection_status, selected = telemetry["automatic_selection_status"], list(telemetry["selected_slots"])
    references = resolve_references(
        selection_status,
        selected,
        graph["reference_needs"],
        reference_policy,
        base_manifest,
    )
    return {
        "graph_status": telemetry["graph_status"],
        "automatic_selection_status": telemetry["automatic_selection_status"],
        "selection_status": selection_status,
        "root_slots": telemetry["root_slots"],
        "selected_slots": selected,
        **references,
    }
