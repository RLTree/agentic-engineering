#!/usr/bin/env python3
"""Zero-write AQ8 corpus freeze validator.

The default path validates the exact one-way corpus freeze receipt bound below.
``--working-tree`` remains the narrow draft seam: the frozen contract must still
match its immutable Git object and the index must contain exactly the two new
split files, with no staged extras.

This module has no model, provider, result, replay, or persistence path. Public
errors are intentionally generic so malformed or historical corpus text is
never echoed.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, SchemaError


ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path("evals/foundation-v4/future-activation-v8")
SCHEMA = CORPUS / "activation-schema.json"
README = CORPUS / "README.md"
SPLITS = (
    CORPUS / "activation-authoring.json",
    CORPUS / "activation-heldout.json",
)
CONTRACT_COMMIT = "a31038253e6cb0900731c33ee3dc2f20985c2e47"
CONTRACT_TREE = "aabe520b88571f56d7ae65a34e3722ccbf08f01f"
CONTRACT_HASHES = {
    SCHEMA: "4fd0b52885cfa46364f7b3265484fc50d8b8af424c4b4dbf2205b0291385db51",
    README: "6c3a6f2019a99cc8b22333ed596bcf7b3306d2dde538e8fe7d68a831deded83f",
}

# One-way binding captured only after the exact two-path corpus freeze commit.
FROZEN_CORPUS_COMMIT: str | None = "46174c0c5eb3da9b6134305329ebc36cc5108847"
FROZEN_CORPUS_TREE: str | None = "163677779d0db59b586a91d4d3becf21803afb2e"
FROZEN_CORPUS_HASHES: dict[Path, str] = {
    SPLITS[0]: "08318e0f01b386bba2a0932915a87d07e637ed5b495e822308c42c8371d63a4d",
    SPLITS[1]: "db9c55fff89bdb636f977bb6bebd4b88830d09e6ffa3d0f09c8d4c120eb42227",
}

NEAR_REWRITE_THRESHOLD = 0.30
MIN_SIMILARITY_TEXT_LENGTH = 12
ROOT_KEYS = {
    "schema_version",
    "corpus_id",
    "split_nonce",
    "authority",
    "claim_boundary",
    "cases",
}
CASE_KEYS = {
    "case_id",
    "case_nonce",
    "task_text",
    "task_text_nfc_sha256",
    "expected_semantic_output",
    "expected_parent_derivation",
}
SPLIT_NONCES = {
    "AQ8-authoring": "fcedacb4116091fe69d412a085fd40e350b8f1c7e70348dd3dd950d1752da1c2",
    "AQ8-heldout": "20651a71f2e6739a41089b5fc0ea3474120f2e9e97f8f0f6274d926abc5b2671",
}
PROFILE_BY_ORDINAL = {
    **{ordinal: "no_unresolved" for ordinal in range(1, 3)},
    **{ordinal: "single_root" for ordinal in range(3, 7)},
    **{ordinal: "independent_pair" for ordinal in range(7, 13)},
    **{ordinal: "controller_pair" for ordinal in range(13, 19)},
    **{ordinal: "chain" for ordinal in range(19, 23)},
    **{ordinal: "fork" for ordinal in range(23, 27)},
    **{ordinal: "diamond" for ordinal in range(27, 29)},
    **{ordinal: "uncertainty" for ordinal in range(29, 31)},
    **{ordinal: "cap_exceeded" for ordinal in range(31, 33)},
    **{ordinal: "explicit_exact" for ordinal in range(33, 37)},
}
EXPECTED_PROFILE_COUNTS = Counter(PROFILE_BY_ORDINAL.values())
EXPECTED_SELECTED_NEEDS_BY_SLOT = {
    "s0": Counter({"primary": 4, "secondary": 3, "uncertain": 1, "none": 1}),
    "s1": Counter({"secondary": 4, "primary": 3, "uncertain": 1, "none": 1}),
    "s2": Counter({"primary": 4, "secondary": 3, "uncertain": 1, "none": 1}),
    "s3": Counter({"secondary": 4, "primary": 3, "uncertain": 1, "none": 1}),
}
IMPLEMENTED_STATUS_PRECEDENCE = (
    "schema_invalid_fail",
    "relation_state_mismatch_graph_invalid",
    "cycle_graph_cycle",
    "transitive_closure_failure_graph_invalid",
    "uncertainty_graph_uncertain",
    "root_selection",
)
_TOKEN_BODY = re.compile(r"\$[A-Za-z][A-Za-z0-9-]*")
_EXPECTED_INPUT_ERRORS = (
    OSError,
    UnicodeDecodeError,
    json.JSONDecodeError,
    SchemaError,
    TypeError,
    KeyError,
    ValueError,
    AttributeError,
    IndexError,
)


@dataclass(frozen=True)
class Comparator:
    commit: str
    tree: str
    directory: Path


# Every pre-AQ8 lineage is read only from its immutable commit/tree.  Only
# one-way digests and masked signatures leave _historical_fingerprints.
COMPARATORS = (
    Comparator(
        "407a2ac124856f0ce1fa33af8a61d0607e413820",
        "8314ca6ad82fa4687720692d8c5762c7aabf6261",
        Path("evals/foundation-v4"),
    ),
    Comparator(
        "25de0cb1fe86a802768de9bf64659206d69650d0",
        "e5faff4b1a5ba678a7df1727b5bda3b3d0afe00a",
        Path("evals/foundation-v4/future-activation-v2"),
    ),
    Comparator(
        "ee7be80441ce06e53615df74505a1b4549a4aa90",
        "e1c83c852b26a0c06753c591a689e1ecf00022b7",
        Path("evals/foundation-v4/future-activation-v3"),
    ),
    Comparator(
        "f110be6ccb3460719141fea74b2fdb4313924718",
        "ed3a0ee0afeb32f25033620519658b7b4774068c",
        Path("evals/foundation-v4/future-activation-v4"),
    ),
    Comparator(
        "39fd55df96e99e38d51d5fee13faa6b6294f9c43",
        "b7b9eb94ffe14a59e924ac2c40926e1a2dc513dd",
        Path("evals/foundation-v4/future-activation-v5"),
    ),
    Comparator(
        "4ba09a422b5485a885c7e12409dae84639bdb513",
        "937c6ed971a4c58049ed3a5f8ee891f5d6b5809a",
        Path("evals/foundation-v4/future-activation-v6"),
    ),
    Comparator(
        "4a8efb300a1cd26a72d8ac3bef1d1ba5250481ee",
        "753d15a7b7dceacca7e66d39ab42fe89d94b237b",
        Path("evals/foundation-v4/future-activation-v7"),
    ),
)


@dataclass(frozen=True)
class AuthorityContext:
    schema: dict[str, Any]
    protocol: dict[str, Any]
    reference_policy: dict[str, Any]
    base_candidate: dict[str, Any]
    slots: tuple[str, ...]
    pairs: tuple[tuple[str, str], ...]
    slot_to_adviser: dict[str, str]
    token_to_slot: dict[str, str]
    reference_rules: dict[str, dict[str, str]]
    reference_payloads: tuple[dict[str, Any], ...]
    selection_cap: int
    reference_cap: int
    emitting_statuses: frozenset[str]
    non_emitting_statuses: frozenset[str]
    parser: dict[str, Any]
    forbidden_task_identifiers: frozenset[str]


@dataclass(frozen=True)
class DocumentResult:
    cases: tuple[dict[str, Any], ...]
    derived: tuple[dict[str, Any], ...]
    profiles: tuple[str, ...]
    automatic_ids: tuple[str, ...]
    explicit_ids: tuple[str, ...]


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]
    metrics: dict[str, int]
    qualified_ids: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors


class ContractError(ValueError):
    """Internal non-sensitive structural failure."""


def _git(root: Path, args: list[str]) -> bytes | None:
    try:
        # Inherit no GIT_* variables: alternate indexes/object stores, replace
        # refs, config injection, namespaces, and trace files would redirect
        # custody or create writes outside this validator's declared surface.
        environment = {
            key: os.environ[key]
            for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR")
            if key in os.environ
        }
        environment["GIT_NO_REPLACE_OBJECTS"] = "1"
        environment["GIT_OPTIONAL_LOCKS"] = "0"
        run = subprocess.run(
            ["git", *args],
            cwd=root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return None
    return run.stdout if run.returncode == 0 else None


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_text(text: str) -> str:
    return _sha(text.encode("utf-8"))


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_json_constant(_: str) -> Any:
    raise ContractError("non-finite JSON constant")


def _json(raw: bytes) -> dict[str, Any]:
    result = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_closed_object,
        parse_constant=_reject_json_constant,
    )
    if not isinstance(result, dict):
        raise ContractError("JSON root is not an object")
    return result


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return _sha(raw)


def _projection(value: dict[str, Any], dotted_path: str) -> Any:
    projected: Any = value
    for key in dotted_path.split("."):
        projected = projected[key]
    return projected


def _collect_internal_identifiers(value: Any, key: str | None = None) -> set[str]:
    identifiers: set[str] = set()
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            identifiers.update(_collect_internal_identifiers(child_value, child_key))
    elif isinstance(value, list):
        for child in value:
            identifiers.update(_collect_internal_identifiers(child, key))
    elif isinstance(value, str):
        custody_key = key in {
            "$id",
            "adapter_id",
            "adviser_id",
            "authority_id",
            "commit",
            "discriminator_id",
            "gate_authority_id",
            "invariant_id",
            "logical_atom",
            "path",
            "payload_id",
            "policy_id",
            "protocol_id",
            "raw_sha256",
            "sha256",
            "tree",
            "trigger_id",
        } or bool(key and key.endswith(("_commit", "_path", "_sha256", "_tree")))
        if (
            custody_key
            or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value)
            or ("/" in value and " " not in value)
        ):
            identifiers.add(value)
    return identifiers


def _commit_file(root: Path, commit: str, path: Path) -> bytes:
    raw = _git(root, ["show", f"{commit}:{path.as_posix()}"])
    if raw is None:
        raise ContractError("immutable source unavailable")
    return raw


def _assert_commit(root: Path, commit: str, tree: str) -> None:
    if _git(root, ["cat-file", "-e", f"{commit}^{{commit}}"]) is None:
        raise ContractError("immutable commit unavailable")
    observed = _git(root, ["rev-parse", f"{commit}^{{tree}}"])
    if observed is None or observed.decode("ascii", "strict").strip() != tree:
        raise ContractError("immutable tree mismatch")


def _contract_ok(root: Path) -> bool:
    try:
        _assert_commit(root, CONTRACT_COMMIT, CONTRACT_TREE)
        for path, digest in CONTRACT_HASHES.items():
            raw = _commit_file(root, CONTRACT_COMMIT, path)
            if _sha(raw) != digest or (root / path).read_bytes() != raw:
                return False
        return True
    except _EXPECTED_INPUT_ERRORS:
        return False


def _load_authorities(root: Path, schema_raw: bytes) -> AuthorityContext:
    if _sha(schema_raw) != CONTRACT_HASHES[SCHEMA]:
        raise ContractError("contract schema digest mismatch")
    schema = _json(schema_raw)
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ContractError("corpus schema dialect mismatch")
    Draft202012Validator.check_schema(schema)
    authority = schema["properties"]["authority"]["const"]

    h4 = authority["h4"]
    _assert_commit(root, h4["commit"], h4["tree"])
    component_raw: dict[str, bytes] = {}
    component_json: dict[str, dict[str, Any]] = {}
    for component in h4["components"]:
        role = component["role"]
        path = Path(component["path"])
        raw = _commit_file(root, h4["commit"], path)
        if _sha(raw) != component["sha256"] or role in component_raw:
            raise ContractError("H4 component binding mismatch")
        component_raw[role] = raw
        component_json[role] = _json(raw)
    required_roles = {
        "authority",
        "protocol",
        "semantic_selector_schema",
        "runtime_selector_schema",
        "condition_adapter",
        "reference_policy",
    }
    if set(component_raw) != required_roles:
        raise ContractError("H4 component set mismatch")

    gate = authority["aq8_gate"]
    _assert_commit(root, gate["commit"], gate["tree"])
    gate_raw = _commit_file(root, gate["commit"], Path(gate["path"]))
    if _sha(gate_raw) != gate["sha256"]:
        raise ContractError("AQ8 gate binding mismatch")
    gate_doc = _json(gate_raw)

    base = authority["base_candidate"]
    _assert_commit(root, base["commit"], base["tree"])
    base_raw = _commit_file(root, base["commit"], Path(base["path"]))
    if _sha(base_raw) != base["sha256"]:
        raise ContractError("base candidate binding mismatch")
    base_doc = _json(base_raw)

    plan = authority["recorded_plan"]
    _assert_commit(root, plan["commit"], plan["tree"])

    protocol = component_json["protocol"]
    reference_policy = component_json["reference_policy"]
    h4_manifest = component_json["authority"]
    semantic_schema = component_json["semantic_selector_schema"]
    if (
        protocol.get("schema_version"),
        protocol.get("status"),
        reference_policy.get("schema_version"),
        reference_policy.get("status"),
        h4_manifest.get("schema_version"),
        h4_manifest.get("status"),
        gate_doc.get("schema_version"),
        gate_doc.get("status"),
    ) != (
        "8.0",
        "frozen-proposal-only",
        "8.0",
        "frozen-proposal-only",
        "8.0",
        "frozen-proposal-only",
        "8.0",
        "frozen-proposal-only",
    ):
        raise ContractError("authority status mismatch")
    if semantic_schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ContractError("semantic schema dialect mismatch")
    Draft202012Validator.check_schema(semantic_schema)

    parser_binding = h4["active_parent_parser_projection"]
    parser = _projection(protocol, parser_binding["path"])
    if _canonical_sha(parser) != parser_binding["canonical_sha256"]:
        raise ContractError("active parser projection mismatch")

    graph = protocol["deterministic_graph_resolution"]
    if tuple(graph["status_precedence"]) != IMPLEMENTED_STATUS_PRECEDENCE:
        raise ContractError("graph precedence mismatch")
    slots = tuple(protocol["model_output_contract"]["candidate_states"]["slot_order"])
    pairs = tuple(
        tuple(pair)
        for pair in protocol["model_output_contract"]["pairwise_relations"][
            "pair_order"
        ]
    )
    slot_rows = protocol["slot_contract"]["slots"]
    slot_to_adviser = {row["slot_id"]: row["adviser_id"] for row in slot_rows}
    token_to_slot = {
        row["token"]: row["slot_id"]
        for row in protocol["explicit_constraint"]["ordered_token_to_slot"]
    }
    reference_contract = reference_policy["reference_need_contract"]
    reference_rows = reference_contract["ordered_slot_table"]
    reference_rules = {
        row["slot_id"]: {
            "primary": row["primary_trigger_id"],
            "secondary": row["secondary_trigger_id"],
        }
        for row in reference_rows
    }
    payloads = tuple(
        {
            "payload_id": reference["payload_id"],
            "owner_adviser_id": skill["id"],
            "trigger_ids": tuple(reference["trigger_ids"]),
        }
        for skill in base_doc["skills"]
        for reference in skill["references"]
    )
    selection_gate = reference_contract["selection_gate"]
    forbidden_task_identifiers = {
        *(row["logical_atom"] for row in slot_rows),
        *(trigger for rules in reference_rules.values() for trigger in rules.values()),
        *(payload["payload_id"] for payload in payloads),
        *slots,
        *slot_to_adviser.values(),
        *SPLIT_NONCES,
        *SPLIT_NONCES.values(),
        *(
            f"{corpus_id}-{ordinal:02d}"
            for corpus_id in SPLIT_NONCES
            for ordinal in range(1, 37)
        ),
        *(
            _sha_text(f"{split_nonce}|{corpus_id}-{ordinal:02d}")
            for corpus_id, split_nonce in SPLIT_NONCES.items()
            for ordinal in range(1, 37)
        ),
        h4_manifest["authority_id"],
        protocol["protocol_id"],
        reference_policy["policy_id"],
        component_json["condition_adapter"]["adapter_id"],
        gate_doc["gate_authority_id"],
        "AQ8",
        "H4",
        "automatic_selection_status",
        "candidate_states",
        "canonical_payload_id_tuple",
        "cap_exceeded",
        "case_id",
        "case_nonce",
        "claim_boundary",
        "claim_ceiling",
        "complement_adviser_ids",
        "corpus_id",
        "expected_parent_derivation",
        "expected_semantic_output",
        "graph_cycle",
        "graph_invalid",
        "graph_status",
        "graph_uncertain",
        "left_controls_right_downstream",
        "left_slot",
        "owner_adviser_id",
        "observation_state",
        "pairwise_relations",
        "reference_needs",
        "reference_requests",
        "reference_resolution",
        "reference_uncertain_slots",
        "replay_policy",
        "resolved_count",
        "resolved_or_absent",
        "right_controls_left_downstream",
        "right_slot",
        "root_slots",
        "selected_adviser_ids",
        "selected_slots",
        "selection_status",
        "schema_version",
        "slot_id",
        "split_nonce",
        "task_text",
        "task_text_nfc_sha256",
        "tuning_policy",
        "trigger_id",
        "external_action",
        "failure_policy",
    }
    for frozen_surface in (
        authority,
        h4_manifest,
        protocol,
        reference_policy,
        component_json["condition_adapter"],
        component_json["semantic_selector_schema"],
        component_json["runtime_selector_schema"],
        gate_doc,
        base_doc,
    ):
        forbidden_task_identifiers.update(_collect_internal_identifiers(frozen_surface))
    forbidden_task_identifiers.update(
        {
            CONTRACT_COMMIT,
            CONTRACT_TREE,
            *(CONTRACT_HASHES.values()),
            *(path.as_posix() for path in (SCHEMA, README, *SPLITS)),
            *(binding.commit for binding in COMPARATORS),
            *(binding.tree for binding in COMPARATORS),
            *(binding.directory.as_posix() for binding in COMPARATORS),
        }
    )
    context = AuthorityContext(
        schema=schema,
        protocol=protocol,
        reference_policy=reference_policy,
        base_candidate=base_doc,
        slots=slots,
        pairs=pairs,
        slot_to_adviser=slot_to_adviser,
        token_to_slot=token_to_slot,
        reference_rules=reference_rules,
        reference_payloads=payloads,
        selection_cap=graph["selection_cap"],
        reference_cap=reference_policy["canonical_cover"]["maximum_payloads"],
        emitting_statuses=frozenset(selection_gate["emitting_selection_statuses"]),
        non_emitting_statuses=frozenset(
            selection_gate["non_emitting_selection_statuses"]
        ),
        parser=parser,
        forbidden_task_identifiers=frozenset(forbidden_task_identifiers),
    )
    if (
        context.slots != ("s0", "s1", "s2", "s3")
        or len(context.pairs) != 6
        or tuple(context.slot_to_adviser) != context.slots
        or tuple(context.reference_rules) != context.slots
        or tuple(context.token_to_slot.values()) != context.slots
        or context.selection_cap != 2
        or context.reference_cap != 3
        or context.emitting_statuses != frozenset({"automatic", "exact"})
        or context.emitting_statuses & context.non_emitting_statuses
    ):
        raise ContractError("closed authority projection mismatch")
    gate_h4 = gate_doc["h4_authority_binding"]
    if (
        gate_h4["commit"],
        gate_h4["tree"],
        gate_h4["raw_sha256"],
    ) != (
        h4["commit"],
        h4["tree"],
        next(row["sha256"] for row in h4["components"] if row["role"] == "authority"),
    ):
        raise ContractError("gate/H4 parity mismatch")
    return context


def _case_nonce(split_nonce: str, case_id: str) -> str:
    return _sha_text(f"{split_nonce}|{case_id}")


def _relation_edge(left: str, right: str, relation: str) -> tuple[str, str] | None:
    if relation == "left_controls_right_downstream":
        return left, right
    if relation == "right_controls_left_downstream":
        return right, left
    return None


def _graph_result(
    graph_status: str,
    automatic_status: str,
    roots: list[str] | None = None,
    selected: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "graph_status": graph_status,
        "automatic_selection_status": automatic_status,
        "root_slots": roots or [],
        "automatic_selected_slots": selected or [],
    }


def _resolve_graph(
    context: AuthorityContext, semantic: dict[str, Any]
) -> dict[str, Any]:
    states = {row["slot_id"]: row["state"] for row in semantic["candidate_states"]}
    edges: set[tuple[str, str]] = set()
    uncertain = any(state == "uncertain" for state in states.values())
    for row in semantic["pairwise_relations"]:
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
            return _graph_result("graph_invalid", "graph_invalid")
        edge = _relation_edge(left, right, relation)
        if edge is not None:
            edges.add(edge)

    unresolved = [slot for slot in context.slots if states[slot] == "unresolved"]
    outgoing = {slot: set() for slot in unresolved}
    for source, target in edges:
        if source not in outgoing or target not in outgoing:
            return _graph_result("graph_invalid", "graph_invalid")
        outgoing[source].add(target)

    visiting: set[str] = set()
    visited: set[str] = set()

    def cyclic(slot: str) -> bool:
        if slot in visiting:
            return True
        if slot in visited:
            return False
        visiting.add(slot)
        if any(cyclic(target) for target in outgoing[slot]):
            return True
        visiting.remove(slot)
        visited.add(slot)
        return False

    if any(cyclic(slot) for slot in unresolved):
        return _graph_result("graph_cycle", "graph_cycle")

    for source in unresolved:
        reachable: set[str] = set()
        pending = list(outgoing[source])
        while pending:
            target = pending.pop()
            if target in reachable:
                continue
            reachable.add(target)
            pending.extend(outgoing[target])
        if any((source, target) not in edges for target in reachable):
            return _graph_result("graph_invalid", "graph_invalid")

    if uncertain:
        return _graph_result("graph_uncertain", "graph_uncertain")
    indegree = Counter(target for _, target in edges)
    roots = [slot for slot in unresolved if indegree[slot] == 0]
    if len(roots) > context.selection_cap:
        return _graph_result("valid", "cap_exceeded", roots, [])
    return _graph_result("valid", "automatic", roots, roots)


def _in_ascii_ranges(value: str, ranges: tuple[str, ...]) -> bool:
    return any(
        lower <= value <= upper
        for encoded in ranges
        for lower, upper in (encoded.split("-", maxsplit=1),)
    )


def _allowed_boundary(context: AuthorityContext, value: str | None) -> bool:
    if value is None:
        return True
    boundary = context.parser["boundary"]
    category = unicodedata.category(value)
    return not (
        value in boundary["disallowed_literals"]
        or category[:1] in boundary["disallowed_unicode_general_category_prefixes"]
        or category in boundary["disallowed_unicode_general_categories"]
    )


def _scan_invocation_like(context: AuthorityContext, task_text: str) -> list[str]:
    body = context.parser["invocation_like_body"]
    first_ranges = tuple(body["first_codepoint"]["allowed_ranges"])
    remaining_ranges = tuple(body["remaining_codepoints"]["allowed_ranges"])
    remaining_literals = frozenset(body["remaining_codepoints"]["allowed_literals"])
    text = unicodedata.normalize("NFC", task_text)
    tokens: list[str] = []
    index = 0
    while index < len(text):
        if (
            text[index] == body["prefix"]
            and index + 1 < len(text)
            and _in_ascii_ranges(text[index + 1], first_ranges)
        ):
            end = index + 2
            while end < len(text) and (
                _in_ascii_ranges(text[end], remaining_ranges)
                or text[end] in remaining_literals
            ):
                end += 1
            before = text[index - 1] if index else None
            after = text[end] if end < len(text) else None
            if _allowed_boundary(context, before) and _allowed_boundary(context, after):
                tokens.append(text[index:end])
            index = end
            continue
        index += 1
    return tokens


def _resolve_selection(
    context: AuthorityContext,
    task_text: str,
    graph: dict[str, Any],
) -> tuple[str, list[str]]:
    tokens = _scan_invocation_like(context, task_text)
    recognized = [
        context.token_to_slot[token]
        for token in tokens
        if token in context.token_to_slot
    ]
    if any(token not in context.token_to_slot for token in tokens):
        return "unrecognized", []
    if len(recognized) == 1:
        return "exact", recognized
    if len(recognized) > 1:
        return "ambiguous", []
    return graph["automatic_selection_status"], list(graph["automatic_selected_slots"])


def _canonical_cover(
    context: AuthorityContext,
    requests: list[dict[str, str]],
) -> dict[str, Any]:
    required = {
        (request["owner_adviser_id"], request["trigger_id"]) for request in requests
    }
    payloads = sorted(context.reference_payloads, key=lambda row: row["payload_id"])
    for count in range(len(payloads) + 1):
        for combination in itertools.combinations(payloads, count):
            covered = {
                (payload["owner_adviser_id"], trigger)
                for payload in combination
                for trigger in payload["trigger_ids"]
            }
            if required <= covered:
                if count > context.reference_cap:
                    return {
                        "status": "cap_exceeded",
                        "resolved_count": count,
                        "canonical_payload_id_tuple": [],
                    }
                return {
                    "status": "resolved",
                    "resolved_count": count,
                    "canonical_payload_id_tuple": [
                        payload["payload_id"] for payload in combination
                    ],
                }
    return {
        "status": "unresolved",
        "resolved_count": 0,
        "canonical_payload_id_tuple": [],
    }


def _derive_parent(context: AuthorityContext, case: dict[str, Any]) -> dict[str, Any]:
    semantic = case["expected_semantic_output"]
    graph = _resolve_graph(context, semantic)
    selection_status, selected_slots = _resolve_selection(
        context, case["task_text"], graph
    )
    needs = {row["slot_id"]: row["need"] for row in semantic["reference_needs"]}
    closed_statuses = context.emitting_statuses | context.non_emitting_statuses
    if selection_status not in closed_statuses:
        raise ContractError("selection status outside frozen reference policy")
    emitting = selection_status in context.emitting_statuses
    if not emitting:
        if selected_slots or any(need != "none" for need in needs.values()):
            raise ContractError("non-emitting reference contract mismatch")
    elif selection_status == "automatic":
        if (
            selected_slots != graph["root_slots"]
            or len(selected_slots) > context.selection_cap
        ):
            raise ContractError("automatic selection/root mismatch")
    elif selection_status == "exact" and len(selected_slots) != 1:
        raise ContractError("exact selection cardinality mismatch")
    if emitting and any(
        slot not in selected_slots and needs[slot] != "none" for slot in context.slots
    ):
        raise ContractError("unselected reference need mismatch")

    requests: list[dict[str, str]] = []
    uncertain_slots: list[str] = []
    seen_requests: set[tuple[str, str]] = set()
    if emitting:
        for slot in selected_slots:
            need = needs[slot]
            if need == "uncertain":
                uncertain_slots.append(slot)
            elif need in {"primary", "secondary"}:
                request = {
                    "owner_adviser_id": context.slot_to_adviser[slot],
                    "trigger_id": context.reference_rules[slot][need],
                }
                identity = (request["owner_adviser_id"], request["trigger_id"])
                if identity not in seen_requests:
                    seen_requests.add(identity)
                    requests.append(request)
    selected_advisers = [context.slot_to_adviser[slot] for slot in selected_slots]
    complement = [
        context.slot_to_adviser[slot]
        for slot in context.slots
        if slot not in selected_slots
    ]
    return {
        "graph_status": graph["graph_status"],
        "automatic_selection_status": graph["automatic_selection_status"],
        "selection_status": selection_status,
        "root_slots": graph["root_slots"],
        "selected_slots": selected_slots,
        "selected_adviser_ids": selected_advisers,
        "complement_adviser_ids": complement,
        "reference_requests": requests,
        "reference_uncertain_slots": uncertain_slots,
        "reference_resolution": _canonical_cover(context, requests),
    }


def _edge_set(semantic: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        edge
        for row in semantic["pairwise_relations"]
        if (
            edge := _relation_edge(row["left_slot"], row["right_slot"], row["relation"])
        )
        is not None
    }


def _profile(
    context: AuthorityContext,
    case: dict[str, Any],
    derived: dict[str, Any],
) -> str:
    if derived["selection_status"] == "exact":
        return "explicit_exact"
    if derived["graph_status"] == "graph_uncertain":
        return "uncertainty"
    if derived["automatic_selection_status"] == "cap_exceeded":
        return "cap_exceeded"
    semantic = case["expected_semantic_output"]
    states = {row["slot_id"]: row["state"] for row in semantic["candidate_states"]}
    unresolved = [slot for slot in context.slots if states[slot] == "unresolved"]
    edges = _edge_set(semantic)
    indegree = Counter(target for _, target in edges)
    outdegree = Counter(source for source, _ in edges)
    if not unresolved:
        return "no_unresolved"
    if len(unresolved) == 1:
        return "single_root"
    if len(unresolved) == 2:
        if not edges:
            return "independent_pair"
        if len(edges) == 1:
            return "controller_pair"
    if len(unresolved) == 3:
        if sorted(outdegree[slot] for slot in unresolved) == [0, 1, 2] and sorted(
            indegree[slot] for slot in unresolved
        ) == [0, 1, 2]:
            return "chain"
        if sorted(outdegree[slot] for slot in unresolved) == [0, 0, 2] and sorted(
            indegree[slot] for slot in unresolved
        ) == [0, 1, 1]:
            return "fork"
    if (
        len(unresolved) == 4
        and sorted(outdegree[slot] for slot in unresolved) == [0, 1, 1, 3]
        and sorted(indegree[slot] for slot in unresolved) == [0, 1, 1, 3]
    ):
        return "diamond"
    raise ContractError("case profile mismatch")


def _pair_with_only_unresolved(
    context: AuthorityContext,
    semantic: dict[str, Any],
) -> tuple[str, str] | None:
    unresolved = {
        row["slot_id"]
        for row in semantic["candidate_states"]
        if row["state"] == "unresolved"
    }
    if len(unresolved) != 2:
        return None
    return next(pair for pair in context.pairs if set(pair) == unresolved)


def _validate_distribution(
    context: AuthorityContext,
    cases: tuple[dict[str, Any], ...],
    derived: tuple[dict[str, Any], ...],
    profiles: tuple[str, ...],
) -> None:
    if Counter(profiles) != EXPECTED_PROFILE_COUNTS:
        raise ContractError("profile count drift")
    if any(
        profile != PROFILE_BY_ORDINAL[ordinal]
        for ordinal, profile in enumerate(profiles, start=1)
    ):
        raise ContractError("ordinal profile drift")

    independent_pairs = {
        _pair_with_only_unresolved(
            context, cases[index - 1]["expected_semantic_output"]
        )
        for index in range(7, 13)
    }
    controller_pairs = {
        _pair_with_only_unresolved(
            context, cases[index - 1]["expected_semantic_output"]
        )
        for index in range(13, 19)
    }
    if independent_pairs != set(context.pairs) or controller_pairs != set(
        context.pairs
    ):
        raise ContractError("pair coverage drift")

    controller_roots = Counter(
        derived[index - 1]["root_slots"][0] for index in range(13, 19)
    )
    if controller_roots != Counter({"s0": 1, "s1": 2, "s2": 2, "s3": 1}):
        raise ContractError("controller root balance drift")
    controller_relations = Counter(
        row["relation"]
        for index in range(13, 19)
        for row in cases[index - 1]["expected_semantic_output"]["pairwise_relations"]
        if row["relation"]
        in {"left_controls_right_downstream", "right_controls_left_downstream"}
    )
    if controller_relations != Counter(
        {"left_controls_right_downstream": 3, "right_controls_left_downstream": 3}
    ):
        raise ContractError("controller direction balance drift")

    for start in (19, 23):
        roots = Counter(
            derived[index - 1]["root_slots"][0] for index in range(start, start + 4)
        )
        omitted = Counter(
            next(
                slot
                for slot in context.slots
                if slot
                not in {
                    row["slot_id"]
                    for row in cases[index - 1]["expected_semantic_output"][
                        "candidate_states"
                    ]
                    if row["state"] == "unresolved"
                }
            )
            for index in range(start, start + 4)
        )
        if roots != Counter(context.slots) or omitted != Counter(context.slots):
            raise ContractError("chain/fork balance drift")

    if [derived[index - 1]["root_slots"] for index in (27, 28)] != [["s0"], ["s3"]]:
        raise ContractError("diamond root balance drift")
    if [
        _edge_set(cases[index - 1]["expected_semantic_output"]) for index in (27, 28)
    ] != [
        {("s0", "s1"), ("s0", "s2"), ("s0", "s3"), ("s1", "s3"), ("s2", "s3")},
        {("s3", "s1"), ("s3", "s2"), ("s3", "s0"), ("s1", "s0"), ("s2", "s0")},
    ]:
        raise ContractError("diamond orientation drift")

    state_uncertainty = [
        sum(
            row["state"] == "uncertain"
            for row in cases[index - 1]["expected_semantic_output"]["candidate_states"]
        )
        for index in (29, 30)
    ]
    relation_uncertainty = [
        sum(
            row["relation"] == "uncertain"
            for row in cases[index - 1]["expected_semantic_output"][
                "pairwise_relations"
            ]
        )
        for index in (29, 30)
    ]
    if state_uncertainty != [1, 0] or relation_uncertainty != [3, 1]:
        raise ContractError("uncertainty profile drift")
    if [len(derived[index - 1]["root_slots"]) for index in (31, 32)] != [3, 4]:
        raise ContractError("cap profile drift")
    if any(
        _edge_set(cases[index - 1]["expected_semantic_output"]) for index in (31, 32)
    ):
        raise ContractError("cap independence drift")

    for index in range(33, 37):
        semantic = cases[index - 1]["expected_semantic_output"]
        row = derived[index - 1]
        if (
            row["graph_status"] != "valid"
            or row["automatic_selection_status"] != "automatic"
            or row["root_slots"]
            or any(
                item["state"] != "resolved_or_absent"
                for item in semantic["candidate_states"]
            )
        ):
            raise ContractError("explicit graph baseline drift")

    if Counter(row["selection_status"] for row in derived) != Counter(
        {"automatic": 28, "cap_exceeded": 2, "graph_uncertain": 2, "exact": 4}
    ):
        raise ContractError("selection status drift")
    total_selected = Counter(slot for row in derived for slot in row["selected_slots"])
    automatic_selected = Counter(
        slot
        for row in derived
        if row["selection_status"] == "automatic"
        for slot in row["selected_slots"]
    )
    exact_selected = Counter(
        slot
        for row in derived
        if row["selection_status"] == "exact"
        for slot in row["selected_slots"]
    )
    if total_selected != Counter({slot: 9 for slot in context.slots}):
        raise ContractError("selected slot balance drift")
    if automatic_selected != Counter({slot: 8 for slot in context.slots}):
        raise ContractError("automatic slot balance drift")
    if exact_selected != Counter({slot: 1 for slot in context.slots}):
        raise ContractError("exact slot balance drift")

    selected_needs = {slot: Counter() for slot in context.slots}
    all_needs: Counter[str] = Counter()
    for case, row in zip(cases, derived, strict=True):
        needs = {
            item["slot_id"]: item["need"]
            for item in case["expected_semantic_output"]["reference_needs"]
        }
        all_needs.update(needs.values())
        for slot in row["selected_slots"]:
            selected_needs[slot][needs[slot]] += 1
    if selected_needs != EXPECTED_SELECTED_NEEDS_BY_SLOT:
        raise ContractError("selected reference need balance drift")
    if all_needs != Counter(
        {"none": 112, "primary": 14, "secondary": 14, "uncertain": 4}
    ):
        raise ContractError("global reference need drift")
    request_identities = {
        (request["owner_adviser_id"], request["trigger_id"])
        for row in derived
        for request in row["reference_requests"]
    }
    expected_identities = {
        (context.slot_to_adviser[slot], trigger)
        for slot in context.slots
        for trigger in context.reference_rules[slot].values()
    }
    if request_identities != expected_identities:
        raise ContractError("request identity coverage drift")


def _automatic_surface_ok(context: AuthorityContext, task_text: str) -> bool:
    if _scan_invocation_like(context, task_text):
        return False
    normalized = re.sub(
        r"[-_\s]", "", unicodedata.normalize("NFC", task_text)
    ).casefold()
    return not any(
        adviser.replace("-", "").casefold() in normalized
        for adviser in context.slot_to_adviser.values()
    )


def _task_hygiene_ok(
    context: AuthorityContext,
    task_text: str,
    allowed_invocation_token: str | None = None,
) -> bool:
    text = unicodedata.normalize("NFC", task_text).casefold()
    exempt_token = (
        allowed_invocation_token.casefold()
        if allowed_invocation_token is not None
        and _scan_invocation_like(context, task_text) == [allowed_invocation_token]
        else None
    )
    adviser_ids = frozenset(context.slot_to_adviser.values())
    for identifier in context.forbidden_task_identifiers:
        needle = identifier.casefold()
        cursor = 0
        while (index := text.find(needle, cursor)) >= 0:
            end = index + len(needle)
            before = text[index - 1] if index else None
            after = text[end] if end < len(text) else None
            if _allowed_boundary(context, before) and _allowed_boundary(context, after):
                if (
                    exempt_token is not None
                    and identifier in adviser_ids
                    and index > 0
                    and text[index - 1 : end] == exempt_token
                ):
                    cursor = end
                    continue
                return False
            cursor = index + 1
    return True


def _validate_document(
    context: AuthorityContext,
    validator: Draft202012Validator,
    document: dict[str, Any],
) -> DocumentResult:
    if set(document) != ROOT_KEYS or list(validator.iter_errors(document)):
        raise ContractError("closed root/schema mismatch")
    corpus_id = document["corpus_id"]
    split_nonce = document["split_nonce"]
    if split_nonce != SPLIT_NONCES[corpus_id]:
        raise ContractError("split nonce mismatch")
    cases = tuple(document["cases"])
    derived_rows: list[dict[str, Any]] = []
    profiles: list[str] = []
    nonces: set[str] = set()
    digests: set[str] = set()
    texts: set[str] = set()
    tokens = tuple(context.token_to_slot)
    for ordinal, case in enumerate(cases, start=1):
        if set(case) != CASE_KEYS:
            raise ContractError("closed case mismatch")
        case_id = f"{corpus_id}-{ordinal:02d}"
        if case["case_id"] != case_id or case["case_nonce"] != _case_nonce(
            split_nonce, case_id
        ):
            raise ContractError("case custody mismatch")
        task_text = case["task_text"]
        if task_text != unicodedata.normalize("NFC", task_text):
            raise ContractError("task NFC mismatch")
        digest = _sha_text(task_text)
        if case["task_text_nfc_sha256"] != digest:
            raise ContractError("task digest mismatch")
        if case["case_nonce"] in nonces or digest in digests or task_text in texts:
            raise ContractError("within-split uniqueness mismatch")
        nonces.add(case["case_nonce"])
        digests.add(digest)
        texts.add(task_text)

        allowed_token = tokens[ordinal - 33] if ordinal > 32 else None
        if not _task_hygiene_ok(context, task_text, allowed_token):
            raise ContractError("task hygiene mismatch")
        if len(_similarity_compact(task_text)) < MIN_SIMILARITY_TEXT_LENGTH:
            raise ContractError("task similarity surface too short")

        parsed = _scan_invocation_like(context, task_text)
        if ordinal <= 32:
            if not _automatic_surface_ok(context, task_text):
                raise ContractError("automatic surface leakage")
        elif parsed != [tokens[ordinal - 33]]:
            raise ContractError("exact explicit grammar mismatch")

        derived = _derive_parent(context, case)
        if case["expected_parent_derivation"] != derived:
            raise ContractError("parent derivation mismatch")
        derived_rows.append(derived)
        profiles.append(_profile(context, case, derived))
    derived_tuple = tuple(derived_rows)
    profile_tuple = tuple(profiles)
    _validate_distribution(context, cases, derived_tuple, profile_tuple)
    return DocumentResult(
        cases=cases,
        derived=derived_tuple,
        profiles=profile_tuple,
        automatic_ids=tuple(case["case_id"] for case in cases[:32]),
        explicit_ids=tuple(case["case_id"] for case in cases[32:]),
    )


def _similarity_compact(text: str) -> str:
    masked = _TOKEN_BODY.sub("¤", unicodedata.normalize("NFC", text)).casefold()
    return re.sub(r"\s+", " ", masked).strip()


def _signature(text: str) -> set[str]:
    """Return one-way hashes of token-masked NFC character four-grams."""
    compact = _similarity_compact(text)
    grams = (
        [f"4:{compact[index : index + 4]}" for index in range(len(compact) - 3)]
        if len(compact) >= 4
        else [f"short:{compact}"]
    )
    return {_sha(gram.encode("utf-8")) for gram in grams}


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 0.0


def _historical_task(case: dict[str, Any]) -> str | None:
    packet = case.get("packet")
    if isinstance(packet, dict) and isinstance(packet.get("task_text"), str):
        return packet["task_text"]
    for key in ("normalized_prompt", "prompt"):
        if isinstance(case.get(key), str):
            return case[key]
    return None


def _historical_fingerprints(root: Path) -> list[tuple[str, set[str]]]:
    """Load prior immutable corpora and retain one-way fingerprints only."""
    out: list[tuple[str, set[str]]] = []
    for binding in COMPARATORS:
        _assert_commit(root, binding.commit, binding.tree)
        for leaf in ("activation-authoring.json", "activation-heldout.json"):
            document = _json(
                _commit_file(root, binding.commit, binding.directory / leaf)
            )
            cases = document.get("cases")
            if not isinstance(cases, list):
                raise ContractError("historical case shape mismatch")
            for case in cases:
                if not isinstance(case, dict):
                    raise ContractError("historical case row mismatch")
                text = _historical_task(case)
                if text is None:
                    raise ContractError("historical prompt unavailable")
                normalized = unicodedata.normalize("NFC", text)
                out.append((_sha_text(normalized), _signature(normalized)))
    return out


def _validate_documents(
    root: Path,
    schema_raw: bytes,
    split_raws: tuple[bytes, bytes],
    *,
    historical: list[tuple[str, set[str]]] | None = None,
) -> ValidationResult:
    try:
        context = _load_authorities(root, schema_raw)
        validator = Draft202012Validator(context.schema)
        documents = (_json(split_raws[0]), _json(split_raws[1]))
        authoring = _validate_document(context, validator, documents[0])
        heldout = _validate_document(context, validator, documents[1])
        if (
            documents[0]["corpus_id"] != "AQ8-authoring"
            or documents[1]["corpus_id"] != "AQ8-heldout"
        ):
            raise ContractError("split order mismatch")

        all_cases = (*authoring.cases, *heldout.cases)
        if len(all_cases) != 72:
            raise ContractError("combined count mismatch")
        if len({case["case_id"] for case in all_cases}) != 72:
            raise ContractError("combined ID uniqueness mismatch")
        if len({case["case_nonce"] for case in all_cases}) != 72:
            raise ContractError("combined nonce uniqueness mismatch")
        if len({case["task_text_nfc_sha256"] for case in all_cases}) != 72:
            raise ContractError("combined prompt uniqueness mismatch")

        max_similarity = 0.0
        for left, right in itertools.product(authoring.cases, heldout.cases):
            score = _jaccard(
                _signature(left["task_text"]), _signature(right["task_text"])
            )
            max_similarity = max(max_similarity, score)
            if score >= NEAR_REWRITE_THRESHOLD:
                raise ContractError("cross-split near rewrite")
        prior = historical if historical is not None else _historical_fingerprints(root)
        for case in all_cases:
            digest = case["task_text_nfc_sha256"]
            signature = _signature(case["task_text"])
            for old_digest, old_signature in prior:
                score = _jaccard(signature, old_signature)
                max_similarity = max(max_similarity, score)
                if digest == old_digest or score >= NEAR_REWRITE_THRESHOLD:
                    raise ContractError("historical reuse or near rewrite")

        automatic_ids = (*authoring.automatic_ids, *heldout.automatic_ids)
        explicit_ids = (*authoring.explicit_ids, *heldout.explicit_ids)
        qualified = (*heldout.automatic_ids, *explicit_ids)
        if (
            len(automatic_ids) != 64
            or len(explicit_ids) != 8
            or len(qualified) != 40
            or len(set(qualified)) != 40
        ):
            raise ContractError("qualification set mismatch")
        return ValidationResult(
            (),
            {
                "total_cases": 72,
                "automatic_cases": 64,
                "explicit_cases": 8,
                "qualified_cases": 40,
                "max_prompt_similarity_milli": round(max_similarity * 1000),
            },
            tuple(qualified),
        )
    except Exception:
        # Exception-closed by design: never emit task, label, historical text,
        # JSON-schema detail, path-local secrets, or mutation-specific content.
        return ValidationResult(("structural corpus validation failed",), {}, ())


def _staged_pairs(root: Path) -> list[tuple[str, str]] | None:
    raw = _git(root, ["diff", "--cached", "--name-status", "-z"])
    if raw is None:
        return None
    values = raw.decode("utf-8", "replace").split("\0")
    return [
        (values[index], values[index + 1])
        for index in range(0, len(values) - 1, 2)
        if values[index]
    ]


def check_staged_split_custody(
    root: Path,
    validated_split_raws: tuple[bytes, bytes] | None = None,
) -> bool:
    try:
        return _check_staged_split_custody(root, validated_split_raws)
    except Exception:
        return False


def _check_staged_split_custody(
    root: Path,
    validated_split_raws: tuple[bytes, bytes] | None = None,
) -> bool:
    pairs = _staged_pairs(root)
    if pairs is None or not _contract_ok(root):
        return False
    expected = {path.as_posix() for path in SPLITS}
    if len(pairs) != 2 or {path for _, path in pairs} != expected:
        return False
    if any(status != "A" for status, _ in pairs):
        return False

    # These two contract files are inherited, not restaged. Both the parent
    # tree and index must carry the exact immutable/live bytes.
    for path in (SCHEMA, README):
        expected_contract = _commit_file(root, CONTRACT_COMMIT, path)
        if (root / path).read_bytes() != expected_contract:
            return False
        for spec in (f"HEAD:{path.as_posix()}", f":{path.as_posix()}"):
            observed = _git(root, ["show", spec])
            if observed is None or observed != expected_contract:
                return False

    expected_raws = validated_split_raws or tuple(
        (root / path).read_bytes() for path in SPLITS
    )
    if len(expected_raws) != len(SPLITS):
        return False
    for path, expected_raw in zip(SPLITS, expected_raws, strict=True):
        staged = _git(root, ["show", f":{path.as_posix()}"])
        if (
            staged is None
            or staged != expected_raw
            or (root / path).read_bytes() != expected_raw
        ):
            return False
    return True


def _frozen_commit_custody(root: Path, commit: str) -> bool:
    raw = _git(
        root,
        ["diff-tree", "--no-commit-id", "--name-status", "-r", "-z", commit],
    )
    if raw is None:
        return False
    values = raw.decode("utf-8", "replace").split("\0")
    pairs = [
        (values[index], values[index + 1])
        for index in range(0, len(values) - 1, 2)
        if values[index]
    ]
    return (
        len(pairs) == 2
        and {path for _, path in pairs} == {item.as_posix() for item in SPLITS}
        and all(status == "A" for status, _ in pairs)
    )


def validate_frozen(
    root: Path = ROOT,
    commit: str | None = None,
    tree: str | None = None,
) -> ValidationResult:
    if (
        not isinstance(FROZEN_CORPUS_COMMIT, str)
        or not isinstance(FROZEN_CORPUS_TREE, str)
        or commit not in (None, FROZEN_CORPUS_COMMIT)
        or tree not in (None, FROZEN_CORPUS_TREE)
    ):
        return ValidationResult(("AQ8 frozen corpus binding unavailable",), {}, ())
    try:
        if not _contract_ok(root) or set(FROZEN_CORPUS_HASHES) != set(SPLITS):
            raise ContractError("frozen binding mismatch")
        _assert_commit(root, FROZEN_CORPUS_COMMIT, FROZEN_CORPUS_TREE)
        if not _frozen_commit_custody(root, FROZEN_CORPUS_COMMIT):
            raise ContractError("frozen commit custody mismatch")
        schema_raw = _commit_file(root, FROZEN_CORPUS_COMMIT, SCHEMA)
        readme_raw = _commit_file(root, FROZEN_CORPUS_COMMIT, README)
        split_raws = tuple(
            _commit_file(root, FROZEN_CORPUS_COMMIT, path) for path in SPLITS
        )
        if (
            _sha(schema_raw) != CONTRACT_HASHES[SCHEMA]
            or _sha(readme_raw) != CONTRACT_HASHES[README]
            or schema_raw != (root / SCHEMA).read_bytes()
            or readme_raw != (root / README).read_bytes()
        ):
            raise ContractError("frozen contract bytes mismatch")
        for path, raw in zip(SPLITS, split_raws, strict=True):
            if (
                _sha(raw) != FROZEN_CORPUS_HASHES[path]
                or raw != (root / path).read_bytes()
            ):
                raise ContractError("frozen split bytes mismatch")
        result = _validate_documents(
            root,
            schema_raw,
            (split_raws[0], split_raws[1]),
            historical=_historical_fingerprints(root),
        )
        final_live_bytes = {
            SCHEMA: schema_raw,
            README: readme_raw,
            SPLITS[0]: split_raws[0],
            SPLITS[1]: split_raws[1],
        }
        if any(
            (root / path).read_bytes() != expected
            for path, expected in final_live_bytes.items()
        ):
            raise ContractError("live corpus drift during validation")
        return result
    except Exception:
        return ValidationResult(("AQ8 frozen corpus authority unavailable",), {}, ())


def validate(
    root: Path = ROOT,
    *,
    working_tree: bool = False,
) -> tuple[bool, list[str], dict[str, int]]:
    if not working_tree:
        result = validate_frozen(root)
        return result.passed, list(result.errors), result.metrics
    try:
        if not _contract_ok(root):
            raise ContractError("contract binding unavailable")
        split_raws = (
            (root / SPLITS[0]).read_bytes(),
            (root / SPLITS[1]).read_bytes(),
        )
        result = _validate_documents(
            root,
            (root / SCHEMA).read_bytes(),
            split_raws,
            historical=_historical_fingerprints(root),
        )
        custody = check_staged_split_custody(root, split_raws)
    except Exception:
        result = ValidationResult(("structural corpus inputs unavailable",), {}, ())
        custody = False
    errors = list(result.errors)
    if not custody:
        errors.append("staged split custody failed")
    return not errors, errors, result.metrics


def main() -> int:
    args = sys.argv[1:]
    if args not in ([], ["--working-tree"]):
        print("future-activation-corpus-v8: FAIL")
        print("- error: structural rule failed")
        return 2
    passed, errors, metrics = validate(working_tree=args == ["--working-tree"])
    print("future-activation-corpus-v8:", "PASS" if passed else "FAIL")
    print(f"- total_cases: {metrics.get('total_cases', 0)}")
    print(f"- automatic_cases: {metrics.get('automatic_cases', 0)}")
    print(f"- explicit_cases: {metrics.get('explicit_cases', 0)}")
    print(f"- qualified_cases: {metrics.get('qualified_cases', 0)}")
    print("- claim_ceiling: structural corpus integrity only")
    for _ in errors:
        print("- error: structural rule failed")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
