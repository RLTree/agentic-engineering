#!/usr/bin/env python3
"""Pure, parent-owned AQ7 decision-certificate resolver.

This module intentionally has no filesystem, Git, subprocess, or model surface.
"""
from __future__ import annotations

import itertools
import json
import re
import unicodedata
from copy import deepcopy
from typing import Any


class ResolverError(ValueError):
    """A closed H3 input or deterministic-resolution contract was violated."""


_STATES = frozenset(("present", "absent", "uncertain"))
_FACT_KEYS = frozenset(("predicate_id", "state"))
_PACKET_KEYS = ("instruction", "task_text", "predicate_order", "condition_guidance")
_RESULT_KEYS = (
    "selection_status", "eligible_atoms", "selected_atoms", "selection_constraint",
    "mapped_advisers", "reference_requests", "payload_resolution",
)


def canonical_json(value: Any) -> bytes:
    """Return the one ASCII canonical JSON encoding used for digest custody."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                          allow_nan=False).encode("ascii")
    except (TypeError, ValueError) as error:
        raise ResolverError("value is not canonical JSON") from error


def _object(value: Any, keys: set[str], message: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ResolverError(message)
    return value


def _protocol_order(protocol: Any) -> tuple[str, ...]:
    if not isinstance(protocol, dict) or not isinstance(protocol.get("predicate_order"), list):
        raise ResolverError("protocol predicate order is unavailable")
    order = tuple(protocol["predicate_order"])
    if len(order) != 12 or len(set(order)) != 12 or any(not isinstance(item, str) or not item for item in order):
        raise ResolverError("protocol predicate order is invalid")
    return order


def validate_fact_output(value: Any, protocol: Any, selector_schema: Any) -> tuple[dict[str, str], ...]:
    """Validate only the frozen, ordered 12-fact model output contract."""
    order = _protocol_order(protocol)
    _object(value, {"predicate_facts"}, "fact output must contain only predicate_facts")
    if not isinstance(selector_schema, dict):
        raise ResolverError("selector schema is unavailable")
    props = selector_schema.get("properties")
    schema_facts = props.get("predicate_facts") if isinstance(props, dict) else None
    if (not isinstance(schema_facts, dict) or selector_schema.get("required") != ["predicate_facts"]
            or selector_schema.get("additionalProperties") is not False
            or schema_facts.get("minItems") != 12 or schema_facts.get("maxItems") != 12
            or schema_facts.get("items") is not False):
        raise ResolverError("selector schema lacks predicate_facts")
    rows = value["predicate_facts"]
    if not isinstance(rows, list) or len(rows) != len(order):
        raise ResolverError("fact output must contain exactly 12 ordered facts")
    result: list[dict[str, str]] = []
    for predicate_id, row in zip(order, rows, strict=True):
        _object(row, set(_FACT_KEYS), "fact row is not closed")
        if row["predicate_id"] != predicate_id or row["state"] not in _STATES:
            raise ResolverError("fact row violates frozen predicate order or state grammar")
        result.append({"predicate_id": predicate_id, "state": row["state"]})
    return tuple(result)


def build_condition_packet(adapter: Any, condition_id: Any, task_text: Any) -> dict[str, Any]:
    """Build the model-visible packet; condition guidance is its only variable part."""
    if not isinstance(adapter, dict) or not isinstance(task_text, str):
        raise ResolverError("adapter or task text is invalid")
    contract = adapter.get("packet_contract")
    conditions = adapter.get("conditions")
    if not isinstance(contract, dict) or not isinstance(conditions, dict) or condition_id not in conditions:
        raise ResolverError("condition adapter is unavailable")
    if contract.get("packet_keys") != list(_PACKET_KEYS) or not isinstance(contract.get("instruction"), str):
        raise ResolverError("adapter packet contract is invalid")
    guidance = conditions[condition_id].get("condition_guidance") if isinstance(conditions[condition_id], dict) else None
    if not isinstance(guidance, list) or len(guidance) != 4:
        raise ResolverError("condition guidance is invalid")
    banned = {"labels", "atoms", "advisers", "routes", "policy", "payload", "provenance"}
    encoded = canonical_json(guidance).decode("ascii").lower()
    if any(re.search(rf'"{word}"\s*:', encoded) for word in banned):
        raise ResolverError("condition guidance exposes a parent-only field")
    authority_path = adapter.get("authority_basis", {}).get("h3", {}).get("protocol", {}).get("path")
    if authority_path != "evals/foundation-v4/decision-certificate-protocol-v6.json":
        raise ResolverError("adapter does not bind frozen H3 predicate authority")
    # The frozen adapter mechanically mirrors H3's four eligibility rows: the
    # eight positives occur in row order, then the four exclusions in row order.
    try:
        protocol_order = [predicate for group in guidance for predicate in group["positive_predicate_ids"]]
        protocol_order.extend(group["exclusion_predicate_id"] for group in guidance)
    except (KeyError, TypeError) as error:
        raise ResolverError("condition guidance grammar is invalid") from error
    if len(protocol_order) != 12 or len(set(protocol_order)) != 12 or any(not isinstance(item, str) for item in protocol_order):
        raise ResolverError("adapter-derived predicate order is invalid")
    return {
        "instruction": contract["instruction"],
        "task_text": task_text,
        "predicate_order": list(protocol_order),
        "condition_guidance": deepcopy(guidance),
    }


def _constraint(task_text: Any, protocol: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(task_text, str):
        raise ResolverError("task text must be text")
    explicit = protocol.get("explicit_constraint", {})
    grammar = explicit.get("qualified_invocation_grammar", {}) if isinstance(explicit, dict) else {}
    mapping_rows = explicit.get("ordered_token_to_logical_atom") if isinstance(explicit, dict) else None
    if not isinstance(grammar, dict) or not isinstance(mapping_rows, list):
        raise ResolverError("explicit invocation protocol is unavailable")
    mapping: dict[str, str] = {}
    for row in mapping_rows:
        _object(row, {"token", "logical_atom"}, "explicit invocation mapping is invalid")
        mapping[row["token"]] = row["logical_atom"]
    try:
        exact_re = re.compile(grammar["exact_pattern"])
        like_re = re.compile(grammar["invocation_like_pattern"])
    except (KeyError, TypeError, re.error) as error:
        raise ResolverError("explicit invocation grammar is invalid") from error
    text = unicodedata.normalize("NFC", task_text)
    exact = exact_re.findall(text)
    like = like_re.findall(text)
    if any(token not in exact for token in like):
        return {"parse_status": "unrecognized", "selected_atom": None,
                "qualified_tokens": exact, "invocation_like_tokens": like}
    if len(exact) > 1:
        return {"parse_status": "ambiguous", "selected_atom": None,
                "qualified_tokens": exact, "invocation_like_tokens": like}
    if len(exact) == 1:
        return {"parse_status": "exact", "selected_atom": mapping[exact[0]],
                "qualified_tokens": exact, "invocation_like_tokens": like}
    return {"parse_status": "no_invocation_like", "selected_atom": None,
            "qualified_tokens": [], "invocation_like_tokens": []}


def _mapping(policy: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, str]]]:
    rows = policy.get("request_derivation", {}).get("ordered_mapping_rows") if isinstance(policy, dict) else None
    if not isinstance(rows, list) or len(rows) != 8:
        raise ResolverError("reference-policy mapping rows are invalid")
    mapping: dict[str, str] = {}
    normalized: list[dict[str, str]] = []
    for row in rows:
        _object(row, {"atom_id", "adviser_id", "predicate_id", "trigger_id"}, "reference-policy row is not closed")
        atom, adviser = row["atom_id"], row["adviser_id"]
        if not all(isinstance(item, str) and item for item in row.values()) or mapping.setdefault(atom, adviser) != adviser:
            raise ResolverError("reference-policy parent mapping is invalid")
        normalized.append({key: row[key] for key in ("atom_id", "adviser_id", "predicate_id", "trigger_id")})
    return mapping, normalized


def _payload_catalog(base_manifest: Any) -> list[dict[str, Any]]:
    skills = base_manifest.get("skills") if isinstance(base_manifest, dict) else None
    if not isinstance(skills, list):
        raise ResolverError("base manifest payload catalog is unavailable")
    catalog: list[dict[str, Any]] = []
    for skill in skills:
        if not isinstance(skill, dict) or not isinstance(skill.get("id"), str) or not isinstance(skill.get("references"), list):
            continue
        for reference in skill["references"]:
            if not isinstance(reference, dict):
                raise ResolverError("base manifest reference is invalid")
            required = {"payload_id", "sha256", "trigger_ids"}
            if not required.issubset(reference) or not isinstance(reference["payload_id"], str) or not isinstance(reference["sha256"], str) or not isinstance(reference["trigger_ids"], list):
                raise ResolverError("base manifest reference is invalid")
            catalog.append({"owner_adviser_id": skill["id"], "payload_id": reference["payload_id"],
                            "sha256": reference["sha256"], "trigger_ids": list(reference["trigger_ids"])})
    if len({(item["owner_adviser_id"], item["payload_id"]) for item in catalog}) != len(catalog):
        raise ResolverError("base manifest payload identity is duplicated")
    return sorted(catalog, key=lambda item: item["payload_id"])


def _resolve_payloads(base_manifest: Any, requests: list[dict[str, str]], policy: dict[str, Any]) -> dict[str, Any]:
    if not requests:
        return {"status": "resolved", "resolved_count": 0, "payloads": []}
    cover = policy.get("canonical_cover", {}) if isinstance(policy, dict) else {}
    if not isinstance(cover, dict) or cover.get("maximum_payloads") != 3:
        raise ResolverError("reference-policy cover contract is invalid")
    required = {(row["owner_adviser_id"], row["trigger_id"]) for row in requests}
    catalog = _payload_catalog(base_manifest)
    eligible = [row for row in catalog if any(row["owner_adviser_id"] == owner and trigger in row["trigger_ids"] for owner, trigger in required)]
    def covers(choice: tuple[dict[str, Any], ...]) -> bool:
        return all(any(row["owner_adviser_id"] == owner and trigger in row["trigger_ids"] for row in choice) for owner, trigger in required)
    for count in range(len(eligible) + 1):
        choices = [choice for choice in itertools.combinations(eligible, count) if covers(choice)]
        if choices:
            chosen = min(choices, key=lambda choice: tuple(sorted(row["payload_id"] for row in choice)))
            if count > 3:
                return {"status": "cap_exceeded", "resolved_count": count, "payloads": []}
            payloads = [{key: row[key] for key in ("owner_adviser_id", "payload_id", "sha256")}
                        for row in sorted(chosen, key=lambda row: row["payload_id"])]
            return {"status": "resolved", "resolved_count": count, "payloads": payloads}
    return {"status": "unresolved", "resolved_count": 0, "payloads": []}


def resolve_decision_certificate(task_text: Any, predicate_facts: Any, protocol: Any,
                                 reference_policy: Any, base_manifest: Any) -> dict[str, Any]:
    """Run frozen H3 selection, parent mapping, requests, and canonical cover."""
    if not isinstance(protocol, dict) or not isinstance(reference_policy, dict):
        raise ResolverError("H3 authority is unavailable")
    # ``validate_fact_output`` returns an immutable canonical tuple.  Accept it
    # at this public boundary, but normalize only its outer container before
    # applying the exact same closed row/order/state validation below.
    if isinstance(predicate_facts, tuple):
        predicate_facts = list(predicate_facts)
    facts = validate_fact_output({"predicate_facts": predicate_facts}, protocol,
                                 {"properties": {"predicate_facts": {"minItems": 12, "maxItems": 12, "items": False}},
                                  "required": ["predicate_facts"], "additionalProperties": False})
    states = {row["predicate_id"]: row["state"] for row in facts}
    selection = protocol.get("deterministic_selection", {})
    rules = selection.get("eligibility_rules") if isinstance(selection, dict) else None
    if not isinstance(rules, list) or selection.get("selection_cap") != 2:
        raise ResolverError("selection protocol is invalid")
    eligible: list[str] = []
    rule_by_atom: dict[str, dict[str, Any]] = {}
    for rule in rules:
        _object(rule, {"derived_atom", "positive_predicates", "exclusion_predicate"}, "eligibility rule is not closed")
        positives = rule["positive_predicates"]
        exclusion = rule["exclusion_predicate"]
        if not isinstance(positives, list) or not positives or any(item not in states for item in [*positives, exclusion]):
            raise ResolverError("eligibility rule refers outside predicate order")
        rule_by_atom[rule["derived_atom"]] = rule
        relevant = [*positives, exclusion]
        if all(states[item] != "uncertain" for item in relevant) and any(states[item] == "present" for item in positives) and states[exclusion] == "absent":
            eligible.append(rule["derived_atom"])
    constraint = _constraint(task_text, protocol)
    if constraint["parse_status"] == "exact":
        status, selected = "exact", [constraint["selected_atom"]]
    elif constraint["parse_status"] in {"ambiguous", "unrecognized"}:
        status, selected = constraint["parse_status"], []
    elif len(eligible) > 2:
        status, selected = "cap_exceeded", []
    else:
        status, selected = "automatic", eligible
    atom_to_adviser, rows = _mapping(reference_policy)
    if any(atom not in atom_to_adviser for atom in selected):
        raise ResolverError("selected atom has no parent adviser mapping")
    advisers = [atom_to_adviser[atom] for atom in selected]
    requests: list[dict[str, str]] = []
    if status in {"automatic", "exact"}:
        for atom, adviser in zip(selected, advisers, strict=True):
            if states[rule_by_atom[atom]["exclusion_predicate"]] == "present":
                continue
            for row in rows:
                if row["atom_id"] == atom and states[row["predicate_id"]] == "present":
                    request = {"owner_adviser_id": adviser, "trigger_id": row["trigger_id"]}
                    if request not in requests:
                        requests.append(request)
                    break
    result = {
        "selection_status": status,
        "eligible_atoms": eligible,
        "selected_atoms": selected,
        "selection_constraint": constraint,
        "mapped_advisers": advisers,
        "reference_requests": requests,
        "payload_resolution": _resolve_payloads(base_manifest, requests, reference_policy),
    }
    if tuple(result) != _RESULT_KEYS:
        raise ResolverError("internal resolution shape drift")
    return result
