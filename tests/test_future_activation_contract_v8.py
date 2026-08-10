from __future__ import annotations

import copy
import hashlib
import itertools
import json
import subprocess
import unicodedata
import unittest
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT / "evals" / "foundation-v4" / "future-activation-v8" / "activation-schema.json"
)
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
SCHEMA_VALIDATOR = Draft202012Validator(SCHEMA)


def _frozen_json(commit: str, path: str) -> dict[str, Any]:
    raw = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    return json.loads(raw)


def _canonical_sha256(value: Any) -> str:
    canonical = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _projection(value: dict[str, Any], dotted_path: str) -> Any:
    projected: Any = value
    for key in dotted_path.split("."):
        projected = projected[key]
    return projected


AUTHORITY_BINDING = SCHEMA["properties"]["authority"]["const"]
H4_BINDING = AUTHORITY_BINDING["h4"]
H4_COMPONENTS = {component["role"]: component for component in H4_BINDING["components"]}
FROZEN_PROTOCOL = _frozen_json(H4_BINDING["commit"], H4_COMPONENTS["protocol"]["path"])
FROZEN_REFERENCE_POLICY = _frozen_json(
    H4_BINDING["commit"], H4_COMPONENTS["reference_policy"]["path"]
)
BASE_BINDING = AUTHORITY_BINDING["base_candidate"]
FROZEN_BASE_CANDIDATE = _frozen_json(BASE_BINDING["commit"], BASE_BINDING["path"])

MODEL_OUTPUT_CONTRACT = FROZEN_PROTOCOL["model_output_contract"]
GRAPH_CONTRACT = FROZEN_PROTOCOL["deterministic_graph_resolution"]
PARSER_CONTRACT = FROZEN_PROTOCOL["explicit_constraint"]["h4_parent_parser_contract"]
REFERENCE_CONTRACT = FROZEN_REFERENCE_POLICY["reference_need_contract"]
COVER_CONTRACT = FROZEN_REFERENCE_POLICY["canonical_cover"]
REFERENCE_SELECTION_GATE = REFERENCE_CONTRACT["selection_gate"]

SLOTS = tuple(MODEL_OUTPUT_CONTRACT["candidate_states"]["slot_order"])
PAIRS = tuple(
    tuple(pair) for pair in MODEL_OUTPUT_CONTRACT["pairwise_relations"]["pair_order"]
)
STATE_VALUES = tuple(MODEL_OUTPUT_CONTRACT["candidate_states"]["allowed_states"])
RELATION_VALUES = tuple(
    MODEL_OUTPUT_CONTRACT["pairwise_relations"]["allowed_relations"]
)
REFERENCE_NEED_VALUES = tuple(MODEL_OUTPUT_CONTRACT["reference_needs"]["allowed_needs"])
GRAPH_STATUS_VALUES = tuple(GRAPH_CONTRACT["graph_status_values"])
AUTOMATIC_STATUS_VALUES = tuple(GRAPH_CONTRACT["automatic_selection_status_values"])
SELECTION_STATUS_VALUES = tuple(
    FROZEN_PROTOCOL["explicit_constraint"]["selection_status_values"]
)
STATUS_PRECEDENCE = tuple(GRAPH_CONTRACT["status_precedence"])
SELECTION_CAP = GRAPH_CONTRACT["selection_cap"]
IMPLEMENTED_STATUS_PRECEDENCE = (
    "schema_invalid_fail",
    "relation_state_mismatch_graph_invalid",
    "cycle_graph_cycle",
    "transitive_closure_failure_graph_invalid",
    "uncertainty_graph_uncertain",
    "root_selection",
)

SLOT_TO_ADVISER = {
    row["slot_id"]: row["adviser_id"]
    for row in FROZEN_PROTOCOL["slot_contract"]["slots"]
}
TOKEN_TO_SLOT = {
    row["token"]: row["slot_id"]
    for row in FROZEN_PROTOCOL["explicit_constraint"]["ordered_token_to_slot"]
}
REFERENCE_ROWS = FROZEN_REFERENCE_POLICY["reference_need_contract"][
    "ordered_slot_table"
]
REFERENCE_RULES = {
    row["slot_id"]: {
        "primary": row["primary_trigger_id"],
        "secondary": row["secondary_trigger_id"],
    }
    for row in REFERENCE_ROWS
}
REFERENCE_PAYLOADS = tuple(
    {
        "payload_id": reference["payload_id"],
        "owner_adviser_id": skill["id"],
        "path": reference["path"],
        "sha256": reference["sha256"],
        "trigger_ids": tuple(reference["trigger_ids"]),
    }
    for skill in FROZEN_BASE_CANDIDATE["skills"]
    for reference in skill["references"]
)
MAXIMUM_REFERENCE_PAYLOADS = COVER_CONTRACT["maximum_payloads"]
REFERENCE_EMITTING_STATUSES = frozenset(
    REFERENCE_SELECTION_GATE["emitting_selection_statuses"]
)
REFERENCE_NON_EMITTING_STATUSES = frozenset(
    REFERENCE_SELECTION_GATE["non_emitting_selection_statuses"]
)

INVOCATION_PREFIX = PARSER_CONTRACT["invocation_like_body"]["prefix"]
FIRST_CODEPOINT_RANGES = tuple(
    PARSER_CONTRACT["invocation_like_body"]["first_codepoint"]["allowed_ranges"]
)
REMAINING_CODEPOINT_RANGES = tuple(
    PARSER_CONTRACT["invocation_like_body"]["remaining_codepoints"]["allowed_ranges"]
)
REMAINING_CODEPOINT_LITERALS = frozenset(
    PARSER_CONTRACT["invocation_like_body"]["remaining_codepoints"]["allowed_literals"]
)
BOUNDARY_CATEGORY_PREFIXES = frozenset(
    PARSER_CONTRACT["boundary"]["disallowed_unicode_general_category_prefixes"]
)
BOUNDARY_CATEGORIES = frozenset(
    PARSER_CONTRACT["boundary"]["disallowed_unicode_general_categories"]
)
BOUNDARY_LITERALS = frozenset(PARSER_CONTRACT["boundary"]["disallowed_literals"])
RETAINED_BOUNDARY_CODEPOINTS = tuple(
    chr(int(fixture["codepoint"][2:], 16))
    for fixture in PARSER_CONTRACT["boundary"]["retained_rejection_fixtures"]
)

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
EXPECTED_PROFILE_COUNTS = Counter(
    {
        "no_unresolved": 2,
        "single_root": 4,
        "independent_pair": 6,
        "controller_pair": 6,
        "chain": 4,
        "fork": 4,
        "diamond": 2,
        "uncertainty": 2,
        "cap_exceeded": 2,
        "explicit_exact": 4,
    }
)
EXPECTED_SELECTED_NEEDS_BY_SLOT = {
    "s0": Counter({"primary": 4, "secondary": 3, "uncertain": 1, "none": 1}),
    "s1": Counter({"secondary": 4, "primary": 3, "uncertain": 1, "none": 1}),
    "s2": Counter({"primary": 4, "secondary": 3, "uncertain": 1, "none": 1}),
    "s3": Counter({"secondary": 4, "primary": 3, "uncertain": 1, "none": 1}),
}
NEED_SEQUENCE_BY_SLOT = {
    "s0": (
        "primary",
        "secondary",
        "uncertain",
        "none",
        "primary",
        "secondary",
        "primary",
        "secondary",
        "primary",
    ),
    "s1": (
        "primary",
        "secondary",
        "uncertain",
        "none",
        "primary",
        "secondary",
        "primary",
        "secondary",
        "secondary",
    ),
    "s2": (
        "primary",
        "secondary",
        "none",
        "primary",
        "secondary",
        "primary",
        "secondary",
        "primary",
        "uncertain",
    ),
    "s3": (
        "primary",
        "secondary",
        "uncertain",
        "primary",
        "secondary",
        "primary",
        "secondary",
        "secondary",
        "none",
    ),
}


class ContractError(ValueError):
    pass


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _case_nonce(split_nonce: str, case_id: str) -> str:
    return _sha256_text(f"{split_nonce}|{case_id}")


def _model_input(case: dict[str, Any]) -> dict[str, str]:
    return {"task_text": case["task_text"]}


def _schema_validate(document: dict[str, Any]) -> None:
    errors = sorted(
        SCHEMA_VALIDATOR.iter_errors(document), key=lambda error: list(error.path)
    )
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise ContractError(f"schema violation at {path}: {first.message}")


def _relation_edge(left: str, right: str, relation: str) -> tuple[str, str] | None:
    if relation == "left_controls_right_downstream":
        return left, right
    if relation == "right_controls_left_downstream":
        return right, left
    return None


def _graph_result(
    graph_status: str,
    automatic_selection_status: str,
    root_slots: list[str] | None = None,
    automatic_selected_slots: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "graph_status": graph_status,
        "automatic_selection_status": automatic_selection_status,
        "root_slots": root_slots or [],
        "automatic_selected_slots": automatic_selected_slots or [],
    }


def _resolve_graph(semantic: dict[str, Any]) -> dict[str, Any]:
    states = {row["slot_id"]: row["state"] for row in semantic["candidate_states"]}
    edges: set[tuple[str, str]] = set()
    uncertainty = any(state == "uncertain" for state in states.values())

    for row in semantic["pairwise_relations"]:
        left = row["left_slot"]
        right = row["right_slot"]
        relation = row["relation"]
        left_state = states[left]
        right_state = states[right]
        uncertainty = uncertainty or relation == "uncertain"

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

    unresolved = [slot for slot in SLOTS if states[slot] == "unresolved"]
    outgoing = {slot: set() for slot in unresolved}
    for source, target in edges:
        outgoing[source].add(target)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(slot: str) -> bool:
        if slot in visiting:
            return True
        if slot in visited:
            return False
        visiting.add(slot)
        for target in outgoing[slot]:
            if visit(target):
                return True
        visiting.remove(slot)
        visited.add(slot)
        return False

    if any(visit(slot) for slot in unresolved):
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

    if uncertainty:
        return _graph_result("graph_uncertain", "graph_uncertain")

    indegree = Counter(target for _, target in edges)
    roots = [slot for slot in unresolved if indegree[slot] == 0]
    if len(roots) > SELECTION_CAP:
        return _graph_result("valid", "cap_exceeded", roots, [])
    return _graph_result("valid", "automatic", roots, roots)


def _in_ascii_ranges(value: str, ranges: tuple[str, ...]) -> bool:
    for encoded_range in ranges:
        lower, upper = encoded_range.split("-", maxsplit=1)
        if lower <= value <= upper:
            return True
    return False


def _first_invocation_codepoint(value: str) -> bool:
    return _in_ascii_ranges(value, FIRST_CODEPOINT_RANGES)


def _remaining_invocation_codepoint(value: str) -> bool:
    return _in_ascii_ranges(value, REMAINING_CODEPOINT_RANGES) or (
        value in REMAINING_CODEPOINT_LITERALS
    )


def _allowed_boundary(value: str | None) -> bool:
    if value is None:
        return True
    category = unicodedata.category(value)
    return not (
        value in BOUNDARY_LITERALS
        or category[:1] in BOUNDARY_CATEGORY_PREFIXES
        or category in BOUNDARY_CATEGORIES
    )


def _scan_invocation_like(task_text: str) -> list[str]:
    text = unicodedata.normalize("NFC", task_text)
    tokens: list[str] = []
    index = 0
    while index < len(text):
        if (
            text[index] == INVOCATION_PREFIX
            and index + 1 < len(text)
            and _first_invocation_codepoint(text[index + 1])
        ):
            end = index + 2
            while end < len(text) and _remaining_invocation_codepoint(text[end]):
                end += 1
            before = text[index - 1] if index else None
            after = text[end] if end < len(text) else None
            if _allowed_boundary(before) and _allowed_boundary(after):
                tokens.append(text[index:end])
            index = end
            continue
        index += 1
    return tokens


def _resolve_selection(task_text: str, graph: dict[str, Any]) -> tuple[str, list[str]]:
    tokens = _scan_invocation_like(task_text)
    recognized = [TOKEN_TO_SLOT[token] for token in tokens if token in TOKEN_TO_SLOT]
    if any(token not in TOKEN_TO_SLOT for token in tokens):
        return "unrecognized", []
    if len(recognized) == 1:
        return "exact", recognized
    if len(recognized) > 1:
        return "ambiguous", []
    return graph["automatic_selection_status"], list(graph["automatic_selected_slots"])


def _canonical_cover(requests: list[dict[str, str]]) -> dict[str, Any]:
    required = {
        (request["owner_adviser_id"], request["trigger_id"]) for request in requests
    }
    payloads = sorted(REFERENCE_PAYLOADS, key=lambda payload: payload["payload_id"])

    for count in range(len(payloads) + 1):
        for combination in itertools.combinations(payloads, count):
            covered = {
                (payload["owner_adviser_id"], trigger)
                for payload in combination
                for trigger in payload["trigger_ids"]
            }
            if required <= covered:
                payload_ids = [payload["payload_id"] for payload in combination]
                if count > MAXIMUM_REFERENCE_PAYLOADS:
                    return {
                        "status": "cap_exceeded",
                        "resolved_count": count,
                        "canonical_payload_id_tuple": [],
                    }
                return {
                    "status": "resolved",
                    "resolved_count": count,
                    "canonical_payload_id_tuple": payload_ids,
                }
    return {
        "status": "unresolved",
        "resolved_count": 0,
        "canonical_payload_id_tuple": [],
    }


def _derive_parent(case: dict[str, Any]) -> dict[str, Any]:
    semantic = case["expected_semantic_output"]
    graph = _resolve_graph(semantic)
    selection_status, selected_slots = _resolve_selection(case["task_text"], graph)
    needs = {row["slot_id"]: row["need"] for row in semantic["reference_needs"]}

    if selection_status not in (
        REFERENCE_EMITTING_STATUSES | REFERENCE_NON_EMITTING_STATUSES
    ):
        raise ContractError("selection status is outside the frozen reference policy")
    emitting = selection_status in REFERENCE_EMITTING_STATUSES
    if not emitting:
        if selected_slots or any(need != "none" for need in needs.values()):
            raise ContractError(
                "non-emitting selection must be empty with all reference needs none"
            )
    elif selection_status == "automatic":
        if selected_slots != graph["root_slots"] or len(selected_slots) > SELECTION_CAP:
            raise ContractError(
                "automatic selected slots must copy zero through two roots"
            )
    elif selection_status == "exact" and len(selected_slots) != 1:
        raise ContractError("exact selection must contain exactly one slot")

    if emitting:
        for slot in SLOTS:
            if slot not in selected_slots and needs[slot] != "none":
                raise ContractError("an unselected slot must have reference need none")

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
                    "owner_adviser_id": SLOT_TO_ADVISER[slot],
                    "trigger_id": REFERENCE_RULES[slot][need],
                }
                identity = (request["owner_adviser_id"], request["trigger_id"])
                if identity not in seen_requests:
                    seen_requests.add(identity)
                    requests.append(request)

    selected_advisers = [SLOT_TO_ADVISER[slot] for slot in selected_slots]
    complement_advisers = [
        SLOT_TO_ADVISER[slot] for slot in SLOTS if slot not in selected_slots
    ]
    return {
        "graph_status": graph["graph_status"],
        "automatic_selection_status": graph["automatic_selection_status"],
        "selection_status": selection_status,
        "root_slots": graph["root_slots"],
        "selected_slots": selected_slots,
        "selected_adviser_ids": selected_advisers,
        "complement_adviser_ids": complement_advisers,
        "reference_requests": requests,
        "reference_uncertain_slots": uncertain_slots,
        "reference_resolution": _canonical_cover(requests),
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


def _profile(case: dict[str, Any], derived: dict[str, Any]) -> str:
    if derived["selection_status"] == "exact":
        return "explicit_exact"
    if derived["graph_status"] == "graph_uncertain":
        return "uncertainty"
    if derived["automatic_selection_status"] == "cap_exceeded":
        return "cap_exceeded"

    semantic = case["expected_semantic_output"]
    states = {row["slot_id"]: row["state"] for row in semantic["candidate_states"]}
    unresolved = [slot for slot in SLOTS if states[slot] == "unresolved"]
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
    if len(unresolved) == 4:
        if sorted(outdegree[slot] for slot in unresolved) == [0, 1, 1, 3] and sorted(
            indegree[slot] for slot in unresolved
        ) == [0, 1, 1, 3]:
            return "diamond"
    raise ContractError("case does not match a frozen AQ8 distribution profile")


def _pair_with_only_unresolved(semantic: dict[str, Any]) -> tuple[str, str] | None:
    unresolved = {
        row["slot_id"]
        for row in semantic["candidate_states"]
        if row["state"] == "unresolved"
    }
    if len(unresolved) != 2:
        return None
    return next(pair for pair in PAIRS if set(pair) == unresolved)


def _validate_distribution(
    cases: list[dict[str, Any]],
    derived_by_case: list[dict[str, Any]],
    profiles: list[str],
) -> None:
    if Counter(profiles) != EXPECTED_PROFILE_COUNTS:
        raise ContractError("profile count distribution drift")
    for ordinal, profile in enumerate(profiles, start=1):
        if profile != PROFILE_BY_ORDINAL[ordinal]:
            raise ContractError(f"profile drift at ordinal {ordinal:02d}")

    independent_pairs = {
        _pair_with_only_unresolved(cases[index - 1]["expected_semantic_output"])
        for index in range(7, 13)
    }
    controller_pairs = {
        _pair_with_only_unresolved(cases[index - 1]["expected_semantic_output"])
        for index in range(13, 19)
    }
    if independent_pairs != set(PAIRS) or controller_pairs != set(PAIRS):
        raise ContractError(
            "pair profiles must cover every canonical pair exactly once"
        )

    controller_roots = Counter(
        derived_by_case[index - 1]["root_slots"][0] for index in range(13, 19)
    )
    if controller_roots != Counter({"s0": 1, "s1": 2, "s2": 2, "s3": 1}):
        raise ContractError("controller direction balance drift")
    controller_relations = Counter(
        row["relation"]
        for index in range(13, 19)
        for row in cases[index - 1]["expected_semantic_output"]["pairwise_relations"]
        if row["relation"]
        in {
            "left_controls_right_downstream",
            "right_controls_left_downstream",
        }
    )
    if controller_relations != Counter(
        {
            "left_controls_right_downstream": 3,
            "right_controls_left_downstream": 3,
        }
    ):
        raise ContractError("controller left/right relation balance drift")

    for start in (19, 23):
        roots = Counter(
            derived_by_case[index - 1]["root_slots"][0]
            for index in range(start, start + 4)
        )
        omitted = Counter(
            next(
                slot
                for slot in SLOTS
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
        if roots != Counter(SLOTS) or omitted != Counter(SLOTS):
            raise ContractError("chain/fork slot balance drift")

    if [derived_by_case[index - 1]["root_slots"] for index in (27, 28)] != [
        ["s0"],
        ["s3"],
    ]:
        raise ContractError("diamond orientation balance drift")
    diamond_edges = [
        _edge_set(cases[index - 1]["expected_semantic_output"]) for index in (27, 28)
    ]
    expected_diamond_edges = [
        {
            ("s0", "s1"),
            ("s0", "s2"),
            ("s0", "s3"),
            ("s1", "s3"),
            ("s2", "s3"),
        },
        {
            ("s3", "s1"),
            ("s3", "s2"),
            ("s3", "s0"),
            ("s1", "s0"),
            ("s2", "s0"),
        },
    ]
    if diamond_edges != expected_diamond_edges:
        raise ContractError("diamond root/middle/sink orientation drift")

    state_uncertainty_counts = [
        sum(
            row["state"] == "uncertain"
            for row in cases[index - 1]["expected_semantic_output"]["candidate_states"]
        )
        for index in (29, 30)
    ]
    relation_uncertainty_counts = [
        sum(
            row["relation"] == "uncertain"
            for row in cases[index - 1]["expected_semantic_output"][
                "pairwise_relations"
            ]
        )
        for index in (29, 30)
    ]
    if state_uncertainty_counts != [1, 0] or relation_uncertainty_counts != [3, 1]:
        raise ContractError("uncertain state/relation profile drift")

    if [len(derived_by_case[index - 1]["root_slots"]) for index in (31, 32)] != [3, 4]:
        raise ContractError("cap profiles must exercise exactly three and four roots")
    if any(
        _edge_set(cases[index - 1]["expected_semantic_output"]) for index in (31, 32)
    ):
        raise ContractError("cap profiles must use independent roots")

    for index in range(33, 37):
        derived = derived_by_case[index - 1]
        semantic = cases[index - 1]["expected_semantic_output"]
        if (
            derived["graph_status"] != "valid"
            or derived["automatic_selection_status"] != "automatic"
            or derived["root_slots"]
            or any(
                row["state"] != "resolved_or_absent"
                for row in semantic["candidate_states"]
            )
        ):
            raise ContractError(
                "explicit profiles must override a valid no-unresolved graph"
            )

    status_counts = Counter(derived["selection_status"] for derived in derived_by_case)
    if status_counts != Counter(
        {"automatic": 28, "cap_exceeded": 2, "graph_uncertain": 2, "exact": 4}
    ):
        raise ContractError("selection-status distribution drift")

    total_selected = Counter(
        slot for derived in derived_by_case for slot in derived["selected_slots"]
    )
    automatic_selected = Counter(
        slot
        for derived in derived_by_case
        if derived["selection_status"] == "automatic"
        for slot in derived["selected_slots"]
    )
    exact_selected = Counter(
        slot
        for derived in derived_by_case
        if derived["selection_status"] == "exact"
        for slot in derived["selected_slots"]
    )
    if total_selected != Counter({slot: 9 for slot in SLOTS}):
        raise ContractError("total selected-slot balance drift")
    if automatic_selected != Counter({slot: 8 for slot in SLOTS}):
        raise ContractError("automatic root balance drift")
    if exact_selected != Counter({slot: 1 for slot in SLOTS}):
        raise ContractError("explicit token-to-slot balance drift")

    selected_needs_by_slot = {slot: Counter() for slot in SLOTS}
    all_need_counts: Counter[str] = Counter()
    for case, derived in zip(cases, derived_by_case, strict=True):
        needs = {
            row["slot_id"]: row["need"]
            for row in case["expected_semantic_output"]["reference_needs"]
        }
        all_need_counts.update(needs.values())
        for slot in derived["selected_slots"]:
            selected_needs_by_slot[slot][needs[slot]] += 1
    if selected_needs_by_slot != EXPECTED_SELECTED_NEEDS_BY_SLOT:
        raise ContractError("selected reference-need balance drift")
    if all_need_counts != Counter(
        {"none": 112, "primary": 14, "secondary": 14, "uncertain": 4}
    ):
        raise ContractError("global reference-need distribution drift")

    request_identities = {
        (request["owner_adviser_id"], request["trigger_id"])
        for derived in derived_by_case
        for request in derived["reference_requests"]
    }
    expected_request_identities = {
        (SLOT_TO_ADVISER[slot], trigger)
        for slot in SLOTS
        for trigger in REFERENCE_RULES[slot].values()
    }
    if request_identities != expected_request_identities:
        raise ContractError("owner-qualified request coverage drift")


def validate_document(document: dict[str, Any]) -> None:
    _schema_validate(document)
    corpus_id = document["corpus_id"]
    split_nonce = document["split_nonce"]
    if split_nonce != SPLIT_NONCES[corpus_id]:
        raise ContractError("split nonce mismatch")

    seen_case_nonces: set[str] = set()
    seen_prompt_hashes: set[str] = set()
    seen_task_texts: set[str] = set()
    derived_by_case: list[dict[str, Any]] = []
    profiles: list[str] = []

    for ordinal, case in enumerate(document["cases"], start=1):
        expected_case_id = f"{corpus_id}-{ordinal:02d}"
        if case["case_id"] != expected_case_id:
            raise ContractError(f"case id/order mismatch at ordinal {ordinal:02d}")
        if case["case_nonce"] != _case_nonce(split_nonce, expected_case_id):
            raise ContractError(f"case nonce mismatch at ordinal {ordinal:02d}")
        if case["case_nonce"] in seen_case_nonces:
            raise ContractError("duplicate case nonce")
        seen_case_nonces.add(case["case_nonce"])

        task_text = case["task_text"]
        if task_text != unicodedata.normalize("NFC", task_text):
            raise ContractError(f"task text is not NFC at ordinal {ordinal:02d}")
        expected_prompt_hash = _sha256_text(task_text)
        if case["task_text_nfc_sha256"] != expected_prompt_hash:
            raise ContractError(f"task text digest mismatch at ordinal {ordinal:02d}")
        if expected_prompt_hash in seen_prompt_hashes or task_text in seen_task_texts:
            raise ContractError("duplicate prompt within split")
        seen_prompt_hashes.add(expected_prompt_hash)
        seen_task_texts.add(task_text)

        parsed_tokens = _scan_invocation_like(task_text)
        if ordinal <= 32:
            if parsed_tokens:
                raise ContractError(
                    "automatic task text contains invocation-like syntax"
                )
            if any(adviser in task_text for adviser in SLOT_TO_ADVISER.values()):
                raise ContractError(
                    "automatic task text contains a canonical adviser name"
                )
        else:
            expected_token = tuple(TOKEN_TO_SLOT)[ordinal - 33]
            if parsed_tokens != [expected_token]:
                raise ContractError(
                    "explicit task text must parse exactly one expected qualified token"
                )

        derived = _derive_parent(case)
        if case["expected_parent_derivation"] != derived:
            raise ContractError(
                f"downstream equality mismatch at ordinal {ordinal:02d}"
            )
        derived_by_case.append(derived)
        profiles.append(_profile(case, derived))

    _validate_distribution(document["cases"], derived_by_case, profiles)


def validate_split_pair(authoring: dict[str, Any], heldout: dict[str, Any]) -> None:
    validate_document(authoring)
    validate_document(heldout)
    if (
        authoring["corpus_id"] != "AQ8-authoring"
        or heldout["corpus_id"] != "AQ8-heldout"
    ):
        raise ContractError("split pair must be authoring then heldout")
    authoring_nonces = {case["case_nonce"] for case in authoring["cases"]}
    heldout_nonces = {case["case_nonce"] for case in heldout["cases"]}
    if authoring_nonces & heldout_nonces:
        raise ContractError("case nonce overlap across splits")
    authoring_prompts = {case["task_text_nfc_sha256"] for case in authoring["cases"]}
    heldout_prompts = {case["task_text_nfc_sha256"] for case in heldout["cases"]}
    if authoring_prompts & heldout_prompts:
        raise ContractError("prompt overlap across splits")


def _relation_for_edge(left: str, right: str, edges: set[tuple[str, str]]) -> str:
    if (left, right) in edges:
        return "left_controls_right_downstream"
    if (right, left) in edges:
        return "right_controls_left_downstream"
    return "independent"


def _semantic_output(
    unresolved: set[str] | None = None,
    *,
    uncertain_states: set[str] | None = None,
    edges: set[tuple[str, str]] | None = None,
    uncertain_pairs: set[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    unresolved = unresolved or set()
    uncertain_states = uncertain_states or set()
    edges = edges or set()
    uncertain_pairs = uncertain_pairs or set()
    states = {
        slot: (
            "uncertain"
            if slot in uncertain_states
            else "unresolved"
            if slot in unresolved
            else "resolved_or_absent"
        )
        for slot in SLOTS
    }
    relations = []
    for left, right in PAIRS:
        if "uncertain" in (states[left], states[right]):
            relation = "uncertain"
        elif "resolved_or_absent" in (states[left], states[right]):
            relation = "unrelated"
        elif (left, right) in uncertain_pairs:
            relation = "uncertain"
        else:
            relation = _relation_for_edge(left, right, edges)
        relations.append({"left_slot": left, "right_slot": right, "relation": relation})
    return {
        "candidate_states": [
            {"slot_id": slot, "state": states[slot]} for slot in SLOTS
        ],
        "pairwise_relations": relations,
        "reference_needs": [{"slot_id": slot, "need": "none"} for slot in SLOTS],
    }


def _base_case_semantic(ordinal: int) -> dict[str, Any]:
    if ordinal in (1, 2) or ordinal >= 33:
        return _semantic_output()
    if 3 <= ordinal <= 6:
        return _semantic_output({SLOTS[ordinal - 3]})
    if 7 <= ordinal <= 12:
        return _semantic_output(set(PAIRS[ordinal - 7]))
    if 13 <= ordinal <= 18:
        pair = PAIRS[ordinal - 13]
        controller_by_pair = {
            ("s0", "s1"): "s1",
            ("s0", "s2"): "s2",
            ("s0", "s3"): "s0",
            ("s1", "s2"): "s1",
            ("s1", "s3"): "s3",
            ("s2", "s3"): "s2",
        }
        controller = controller_by_pair[pair]
        downstream = pair[1] if pair[0] == controller else pair[0]
        return _semantic_output(set(pair), edges={(controller, downstream)})
    if 19 <= ordinal <= 22:
        chain_orders = (
            ("s0", "s1", "s2"),
            ("s1", "s0", "s3"),
            ("s2", "s0", "s3"),
            ("s3", "s1", "s2"),
        )
        root, middle, sink = chain_orders[ordinal - 19]
        return _semantic_output(
            {root, middle, sink},
            edges={(root, middle), (middle, sink), (root, sink)},
        )
    if 23 <= ordinal <= 26:
        fork_orders = (
            ("s0", "s1", "s2"),
            ("s1", "s0", "s3"),
            ("s2", "s0", "s3"),
            ("s3", "s1", "s2"),
        )
        root, child_one, child_two = fork_orders[ordinal - 23]
        return _semantic_output(
            {root, child_one, child_two}, edges={(root, child_one), (root, child_two)}
        )
    if ordinal == 27:
        return _semantic_output(
            set(SLOTS),
            edges={
                ("s0", "s1"),
                ("s0", "s2"),
                ("s0", "s3"),
                ("s1", "s3"),
                ("s2", "s3"),
            },
        )
    if ordinal == 28:
        return _semantic_output(
            set(SLOTS),
            edges={
                ("s3", "s1"),
                ("s3", "s2"),
                ("s3", "s0"),
                ("s1", "s0"),
                ("s2", "s0"),
            },
        )
    if ordinal == 29:
        return _semantic_output(uncertain_states={"s0"})
    if ordinal == 30:
        return _semantic_output({"s1", "s2"}, uncertain_pairs={("s1", "s2")})
    if ordinal == 31:
        return _semantic_output({"s0", "s1", "s2"})
    if ordinal == 32:
        return _semantic_output(set(SLOTS))
    raise AssertionError(f"unhandled synthetic ordinal {ordinal}")


def _synthetic_task_text(corpus_id: str, ordinal: int) -> str:
    if ordinal <= 32:
        return (
            f"Synthetic {corpus_id} neutral task {ordinal:02d}: assess a fresh frozen "
            "decision pattern without naming a route."
        )
    token = tuple(TOKEN_TO_SLOT)[ordinal - 33]
    return (
        f"Synthetic {corpus_id} exact task {ordinal:02d}: use ({token}) for this "
        "bounded decision."
    )


def build_synthetic_document(corpus_id: str) -> dict[str, Any]:
    split_nonce = SPLIT_NONCES[corpus_id]
    cases: list[dict[str, Any]] = []
    selected_occurrences = Counter()

    for ordinal in range(1, 37):
        task_text = _synthetic_task_text(corpus_id, ordinal)
        semantic = _base_case_semantic(ordinal)
        graph = _resolve_graph(semantic)
        _, selected_slots = _resolve_selection(task_text, graph)
        for slot in selected_slots:
            need_index = selected_occurrences[slot]
            semantic["reference_needs"][SLOTS.index(slot)]["need"] = (
                NEED_SEQUENCE_BY_SLOT[slot][need_index]
            )
            selected_occurrences[slot] += 1

        case_id = f"{corpus_id}-{ordinal:02d}"
        case = {
            "case_id": case_id,
            "case_nonce": _case_nonce(split_nonce, case_id),
            "task_text": task_text,
            "task_text_nfc_sha256": _sha256_text(task_text),
            "expected_semantic_output": semantic,
        }
        case["expected_parent_derivation"] = _derive_parent(case)
        cases.append(case)

    if selected_occurrences != Counter({slot: 9 for slot in SLOTS}):
        raise AssertionError(
            f"synthetic selection balance drift: {selected_occurrences}"
        )
    return {
        "schema_version": "8.0",
        "corpus_id": corpus_id,
        "split_nonce": split_nonce,
        "authority": copy.deepcopy(SCHEMA["properties"]["authority"]["const"]),
        "claim_boundary": copy.deepcopy(
            SCHEMA["properties"]["claim_boundary"]["const"]
        ),
        "cases": cases,
    }


def _recompute_case(document: dict[str, Any], ordinal: int) -> None:
    case = document["cases"][ordinal - 1]
    case["expected_parent_derivation"] = _derive_parent(case)


class FutureActivationContractV8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.authoring = build_synthetic_document("AQ8-authoring")
        cls.heldout = build_synthetic_document("AQ8-heldout")

    def assert_contract_rejects(self, document: dict[str, Any]) -> None:
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_schema_is_closed_draft_2020_12(self) -> None:
        Draft202012Validator.check_schema(SCHEMA)
        self.assertEqual(
            SCHEMA["$schema"], "https://json-schema.org/draft/2020-12/schema"
        )
        self.assertFalse(SCHEMA["additionalProperties"])
        self.assertFalse(SCHEMA["$defs"]["case"]["additionalProperties"])
        self.assertFalse(SCHEMA["$defs"]["semantic_output"]["additionalProperties"])
        self.assertFalse(SCHEMA["$defs"]["parent_derivation"]["additionalProperties"])

    def test_frozen_h4_projections_drive_local_contract(self) -> None:
        self.assertEqual(SLOTS, ("s0", "s1", "s2", "s3"))
        self.assertEqual(
            PAIRS,
            (
                ("s0", "s1"),
                ("s0", "s2"),
                ("s0", "s3"),
                ("s1", "s2"),
                ("s1", "s3"),
                ("s2", "s3"),
            ),
        )
        self.assertEqual(
            STATE_VALUES, ("unresolved", "resolved_or_absent", "uncertain")
        )
        self.assertEqual(
            RELATION_VALUES,
            (
                "left_controls_right_downstream",
                "right_controls_left_downstream",
                "independent",
                "unrelated",
                "uncertain",
            ),
        )
        self.assertEqual(
            REFERENCE_NEED_VALUES, ("none", "primary", "secondary", "uncertain")
        )

        semantic_schema = SCHEMA["$defs"]["semantic_output"]["properties"]
        self.assertEqual(tuple(SCHEMA["$defs"]["slot_id"]["enum"]), SLOTS)
        self.assertEqual(
            tuple(
                item["allOf"][1]["properties"]["slot_id"]["const"]
                for item in semantic_schema["candidate_states"]["prefixItems"]
            ),
            SLOTS,
        )
        self.assertEqual(
            tuple(
                (
                    item["allOf"][1]["properties"]["left_slot"]["const"],
                    item["allOf"][1]["properties"]["right_slot"]["const"],
                )
                for item in semantic_schema["pairwise_relations"]["prefixItems"]
            ),
            PAIRS,
        )
        self.assertEqual(
            tuple(
                SCHEMA["$defs"]["candidate_state_row"]["properties"]["state"]["enum"]
            ),
            STATE_VALUES,
        )
        self.assertEqual(
            tuple(
                SCHEMA["$defs"]["pairwise_relation_row"]["properties"]["relation"][
                    "enum"
                ]
            ),
            RELATION_VALUES,
        )
        self.assertEqual(
            tuple(SCHEMA["$defs"]["reference_need_row"]["properties"]["need"]["enum"]),
            REFERENCE_NEED_VALUES,
        )

        parser_binding = H4_BINDING["active_parent_parser_projection"]
        self.assertEqual(
            parser_binding["path"],
            "explicit_constraint.h4_parent_parser_contract",
        )
        parser_projection = _projection(FROZEN_PROTOCOL, parser_binding["path"])
        self.assertEqual(parser_projection, PARSER_CONTRACT)
        self.assertEqual(
            _canonical_sha256(parser_projection), parser_binding["canonical_sha256"]
        )
        self.assertEqual(PARSER_CONTRACT["normalization"], "Unicode NFC")
        self.assertEqual(INVOCATION_PREFIX, "$")
        self.assertEqual(FIRST_CODEPOINT_RANGES, ("A-Z", "a-z"))
        self.assertEqual(REMAINING_CODEPOINT_RANGES, ("A-Z", "a-z", "0-9"))
        self.assertEqual(REMAINING_CODEPOINT_LITERALS, frozenset({"-"}))
        self.assertEqual(
            PARSER_CONTRACT["invocation_like_body"]["remaining_codepoints"][
                "minimum_count"
            ],
            0,
        )
        self.assertEqual(PARSER_CONTRACT["invocation_like_body"]["scan"], "maximal")
        self.assertEqual(BOUNDARY_CATEGORY_PREFIXES, frozenset({"L", "N", "M"}))
        self.assertEqual(BOUNDARY_CATEGORIES, frozenset({"Cf", "Pc"}))
        self.assertEqual(BOUNDARY_LITERALS, frozenset({"_", "-"}))
        for codepoint, fixture in zip(
            RETAINED_BOUNDARY_CODEPOINTS,
            PARSER_CONTRACT["boundary"]["retained_rejection_fixtures"],
            strict=True,
        ):
            self.assertEqual(unicodedata.category(codepoint), fixture["category"])
        self.assertTrue(PARSER_CONTRACT["boundary"]["allowed_when_absent"])
        self.assertTrue(PARSER_CONTRACT["boundary"]["same_rule_on_both_sides"])
        self.assertEqual(
            PARSER_CONTRACT["rewrites"],
            "No trimming, case folding, substring expansion, or token rewriting.",
        )
        self.assertEqual(
            TOKEN_TO_SLOT,
            {
                row["qualified_invocation"]: row["slot_id"]
                for row in FROZEN_PROTOCOL["slot_contract"]["slots"]
            },
        )

        self.assertEqual(STATUS_PRECEDENCE, IMPLEMENTED_STATUS_PRECEDENCE)
        self.assertEqual(SELECTION_CAP, 2)
        self.assertEqual(
            GRAPH_CONTRACT["root_definition"],
            "Roots are exactly unresolved slots with directed indegree zero.",
        )
        self.assertEqual(
            GRAPH_CONTRACT["pair_compatibility"],
            [
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
        )
        self.assertEqual(
            GRAPH_CONTRACT["edge_construction"],
            {
                "left_controls_right_downstream": "left_slot_to_right_slot",
                "right_controls_left_downstream": "right_slot_to_left_slot",
                "independent": "no_edge",
                "unrelated": "no_edge",
                "uncertain": "no_edge",
                "endpoint_scope": "Edges exist only between unresolved endpoints.",
            },
        )
        self.assertEqual(
            GRAPH_CONTRACT["root_selection"]["more_than_two_roots"][
                "automatic_selection_status"
            ],
            "cap_exceeded",
        )
        no_roots = _resolve_graph(_semantic_output())
        one_root = _resolve_graph(_semantic_output({"s0"}))
        two_roots = _resolve_graph(_semantic_output({"s0", "s1"}))
        over_cap = _resolve_graph(_semantic_output({"s0", "s1", "s2"}))
        self.assertEqual(
            (no_roots["root_slots"], no_roots["automatic_selection_status"]),
            ([], "automatic"),
        )
        self.assertEqual(
            (one_root["root_slots"], one_root["automatic_selected_slots"]),
            (["s0"], ["s0"]),
        )
        self.assertEqual(
            (two_roots["root_slots"], two_roots["automatic_selected_slots"]),
            (["s0", "s1"], ["s0", "s1"]),
        )
        self.assertEqual(
            (over_cap["root_slots"], over_cap["automatic_selection_status"]),
            (["s0", "s1", "s2"], "cap_exceeded"),
        )

        cycle = _semantic_output(
            {"s0", "s1", "s2"},
            edges={("s0", "s1"), ("s1", "s2"), ("s2", "s0")},
        )
        self.assertEqual(_resolve_graph(cycle)["graph_status"], "graph_cycle")
        closure_before_uncertainty = _semantic_output(
            {"s0", "s1", "s2"},
            edges={("s0", "s1"), ("s1", "s2")},
            uncertain_pairs={("s0", "s2")},
        )
        self.assertEqual(
            _resolve_graph(closure_before_uncertainty)["graph_status"],
            "graph_invalid",
        )
        parent_schema = SCHEMA["$defs"]["parent_derivation"]["properties"]
        self.assertEqual(
            tuple(parent_schema["graph_status"]["enum"]), GRAPH_STATUS_VALUES
        )
        self.assertEqual(
            tuple(parent_schema["automatic_selection_status"]["enum"]),
            AUTOMATIC_STATUS_VALUES,
        )
        self.assertEqual(
            tuple(parent_schema["selection_status"]["enum"]),
            SELECTION_STATUS_VALUES,
        )

        self.assertEqual(tuple(REFERENCE_CONTRACT["slot_order"]), SLOTS)
        self.assertEqual(
            tuple(REFERENCE_CONTRACT["reference_need_enum"]), REFERENCE_NEED_VALUES
        )
        self.assertEqual(tuple(row["slot_id"] for row in REFERENCE_ROWS), SLOTS)
        self.assertEqual(
            {row["slot_id"]: row["adviser_id"] for row in REFERENCE_ROWS},
            SLOT_TO_ADVISER,
        )
        self.assertEqual(
            REFERENCE_CONTRACT["request_shape"],
            ["owner_adviser_id", "trigger_id"],
        )
        self.assertEqual(REFERENCE_EMITTING_STATUSES, frozenset({"automatic", "exact"}))
        self.assertEqual(
            REFERENCE_NON_EMITTING_STATUSES,
            frozenset(
                {
                    "ambiguous",
                    "unrecognized",
                    "cap_exceeded",
                    "graph_uncertain",
                    "graph_invalid",
                    "graph_cycle",
                }
            ),
        )
        self.assertEqual(
            COVER_CONTRACT["requirement_identity"],
            ["owner_adviser_id", "trigger_id"],
        )
        self.assertEqual(
            COVER_CONTRACT["objective_order"],
            ["minimum_payload_count", "lexicographically_smallest_payload_id_tuple"],
        )
        self.assertEqual(COVER_CONTRACT["payload_output_order"], "payload_id_ascending")
        self.assertEqual(MAXIMUM_REFERENCE_PAYLOADS, 3)
        self.assertEqual(
            tuple(COVER_CONTRACT["statuses"]),
            ("resolved", "unresolved", "cap_exceeded"),
        )

        adviser_order = tuple(SLOT_TO_ADVISER[slot] for slot in SLOTS)
        self.assertEqual(
            tuple(FROZEN_BASE_CANDIDATE["conditions"]["current"]["adviser_ids"]),
            adviser_order,
        )
        self.assertEqual(
            tuple(FROZEN_BASE_CANDIDATE["conditions"]["reduced"]["adviser_ids"]),
            adviser_order,
        )
        self.assertEqual(
            tuple(skill["id"] for skill in FROZEN_BASE_CANDIDATE["skills"]),
            adviser_order,
        )
        payload_ids = [payload["payload_id"] for payload in REFERENCE_PAYLOADS]
        self.assertEqual(len(payload_ids), len(set(payload_ids)))
        for payload in REFERENCE_PAYLOADS:
            self.assertRegex(payload["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(payload["path"])
            self.assertTrue(payload["trigger_ids"])

        canonical_payload_ids: set[str] = set()
        for slot in SLOTS:
            for need in ("primary", "secondary"):
                cover = _canonical_cover(
                    [
                        {
                            "owner_adviser_id": SLOT_TO_ADVISER[slot],
                            "trigger_id": REFERENCE_RULES[slot][need],
                        }
                    ]
                )
                self.assertEqual(cover["status"], "resolved")
                self.assertEqual(cover["resolved_count"], 1)
                canonical_payload_ids.update(cover["canonical_payload_id_tuple"])
        schema_payload_ids = tuple(
            SCHEMA["$defs"]["reference_resolution"]["properties"][
                "canonical_payload_id_tuple"
            ]["items"]["enum"]
        )
        self.assertEqual(schema_payload_ids, tuple(sorted(canonical_payload_ids)))

    def test_positive_synthetic_documents_and_split_pair(self) -> None:
        validate_split_pair(self.authoring, self.heldout)
        for document in (self.authoring, self.heldout):
            self.assertEqual(len(document["cases"]), 36)
            self.assertTrue(
                all(
                    set(_model_input(case)) == {"task_text"}
                    for case in document["cases"]
                )
            )
            self.assertEqual(
                Counter(
                    case["expected_parent_derivation"]["selection_status"]
                    for case in document["cases"]
                ),
                Counter(
                    {
                        "automatic": 28,
                        "cap_exceeded": 2,
                        "graph_uncertain": 2,
                        "exact": 4,
                    }
                ),
            )

    def test_authority_commit_tree_path_and_sha_bindings(self) -> None:
        authority = SCHEMA["properties"]["authority"]["const"]
        h4 = authority["h4"]
        observed_tree = subprocess.run(
            ["git", "rev-parse", f"{h4['commit']}^{{tree}}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(observed_tree, h4["tree"])
        for component in h4["components"]:
            raw = subprocess.run(
                ["git", "show", f"{h4['commit']}:{component['path']}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            ).stdout
            self.assertEqual(hashlib.sha256(raw).hexdigest(), component["sha256"])

        gate = authority["aq8_gate"]
        gate_tree = subprocess.run(
            ["git", "rev-parse", f"{gate['commit']}^{{tree}}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(gate_tree, gate["tree"])
        raw_gate = subprocess.run(
            ["git", "show", f"{gate['commit']}:{gate['path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(hashlib.sha256(raw_gate).hexdigest(), gate["sha256"])

        base = authority["base_candidate"]
        base_tree = subprocess.run(
            ["git", "rev-parse", f"{base['commit']}^{{tree}}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(base_tree, base["tree"])
        raw_base = subprocess.run(
            ["git", "show", f"{base['commit']}:{base['path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(hashlib.sha256(raw_base).hexdigest(), base["sha256"])

        plan = authority["recorded_plan"]
        plan_tree = subprocess.run(
            ["git", "rev-parse", f"{plan['commit']}^{{tree}}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(plan_tree, plan["tree"])

    def test_red_closure_mutation(self) -> None:
        document = copy.deepcopy(self.authoring)
        relation = document["cases"][18]["expected_semantic_output"][
            "pairwise_relations"
        ][1]
        self.assertEqual((relation["left_slot"], relation["right_slot"]), ("s0", "s2"))
        relation["relation"] = "independent"
        self.assert_contract_rejects(document)

    def test_red_semantic_order_mutation(self) -> None:
        document = copy.deepcopy(self.authoring)
        rows = document["cases"][2]["expected_semantic_output"]["candidate_states"]
        rows[0], rows[1] = rows[1], rows[0]
        self.assert_contract_rejects(document)

    def test_red_root_mutation(self) -> None:
        document = copy.deepcopy(self.authoring)
        document["cases"][2]["expected_parent_derivation"]["root_slots"] = ["s1"]
        self.assert_contract_rejects(document)

    def test_red_pair_coherence_mutation(self) -> None:
        document = copy.deepcopy(self.authoring)
        document["cases"][0]["expected_semantic_output"]["pairwise_relations"][0][
            "relation"
        ] = "independent"
        self.assert_contract_rejects(document)

    def test_unicode_boundaries_and_explicit_precedence(self) -> None:
        qualified = next(token for token, slot in TOKEN_TO_SLOT.items() if slot == "s0")
        for codepoint in RETAINED_BOUNDARY_CODEPOINTS:
            self.assertEqual(_scan_invocation_like(codepoint + qualified), [])
            self.assertEqual(_scan_invocation_like(qualified + codepoint), [])
        for codepoint in ("é", "β", "\u0301", "_"):
            self.assertEqual(_scan_invocation_like(codepoint + qualified), [])
            self.assertEqual(_scan_invocation_like(qualified + codepoint), [])
        self.assertEqual(_scan_invocation_like("-" + qualified), [])
        self.assertEqual(
            _scan_invocation_like(qualified + "-"), ["$agentic-engineering-"]
        )

        graph = _resolve_graph(_semantic_output({"s1"}))
        self.assertEqual(_resolve_selection(f"({qualified})", graph), ("exact", ["s0"]))
        self.assertEqual(
            _resolve_selection(f"{qualified} $not-qualified", graph),
            ("unrecognized", []),
        )
        self.assertEqual(
            _resolve_selection(f"{qualified} {qualified}", graph),
            ("ambiguous", []),
        )
        self.assertEqual(
            _resolve_selection("$codex-task-contract-extra", graph),
            ("unrecognized", []),
        )

    def test_red_unicode_token_boundary_mutation(self) -> None:
        document = copy.deepcopy(self.authoring)
        case = document["cases"][32]
        case["task_text"] = case["task_text"].replace(
            "$agentic-engineering", "\u200c$agentic-engineering"
        )
        case["task_text_nfc_sha256"] = _sha256_text(case["task_text"])
        self.assert_contract_rejects(document)

    def test_red_distribution_mutation_after_downstream_recompute(self) -> None:
        document = copy.deepcopy(self.authoring)
        case = document["cases"][6]
        case["expected_semantic_output"]["pairwise_relations"][0]["relation"] = (
            "left_controls_right_downstream"
        )
        for row in case["expected_semantic_output"]["reference_needs"]:
            row["need"] = "none"
        _recompute_case(document, 7)
        self.assert_contract_rejects(document)

    def test_red_reference_and_payload_mutations(self) -> None:
        bad_need = copy.deepcopy(self.authoring)
        bad_need["cases"][2]["expected_semantic_output"]["reference_needs"][1][
            "need"
        ] = "primary"
        self.assert_contract_rejects(bad_need)

        bad_payload = copy.deepcopy(self.authoring)
        derived = bad_payload["cases"][2]["expected_parent_derivation"]
        derived["reference_resolution"]["canonical_payload_id_tuple"] = []
        derived["reference_resolution"]["resolved_count"] = 0
        self.assert_contract_rejects(bad_payload)

        bad_payload_order = copy.deepcopy(self.authoring)
        payload_tuple = bad_payload_order["cases"][6]["expected_parent_derivation"][
            "reference_resolution"
        ]["canonical_payload_id_tuple"]
        self.assertEqual(len(payload_tuple), 2)
        payload_tuple.reverse()
        self.assert_contract_rejects(bad_payload_order)

    def test_red_claim_and_authority_mutations(self) -> None:
        bad_claim = copy.deepcopy(self.authoring)
        bad_claim["claim_boundary"]["replay_policy"] = "replay-permitted"
        self.assert_contract_rejects(bad_claim)

        bad_authority = copy.deepcopy(self.authoring)
        bad_authority["authority"]["h4"]["tree"] = "0" * 40
        self.assert_contract_rejects(bad_authority)

        bad_projection = copy.deepcopy(self.authoring)
        bad_projection["authority"]["h4"]["active_parent_parser_projection"][
            "canonical_sha256"
        ] = "0" * 64
        self.assert_contract_rejects(bad_projection)

    def test_red_prompt_hash_nfc_and_split_coupling_mutations(self) -> None:
        bad_case_id = copy.deepcopy(self.authoring)
        bad_case_id["cases"][0]["case_id"] = "AQ8-heldout-01"
        bad_case_id["cases"][0]["case_nonce"] = _case_nonce(
            bad_case_id["split_nonce"], "AQ8-heldout-01"
        )
        self.assert_contract_rejects(bad_case_id)

        bad_case_nonce = copy.deepcopy(self.authoring)
        bad_case_nonce["cases"][0]["case_nonce"] = "0" * 64
        self.assert_contract_rejects(bad_case_nonce)

        bad_hash = copy.deepcopy(self.authoring)
        bad_hash["cases"][0]["task_text_nfc_sha256"] = "0" * 64
        self.assert_contract_rejects(bad_hash)

        bad_nfc = copy.deepcopy(self.authoring)
        bad_nfc["cases"][0]["task_text"] += " e\u0301"
        bad_nfc["cases"][0]["task_text_nfc_sha256"] = _sha256_text(
            bad_nfc["cases"][0]["task_text"]
        )
        self.assert_contract_rejects(bad_nfc)

        coupled_heldout = copy.deepcopy(self.heldout)
        coupled_heldout["cases"][0]["task_text"] = self.authoring["cases"][0][
            "task_text"
        ]
        coupled_heldout["cases"][0]["task_text_nfc_sha256"] = self.authoring["cases"][
            0
        ]["task_text_nfc_sha256"]
        with self.assertRaises(ContractError):
            validate_split_pair(self.authoring, coupled_heldout)


if __name__ == "__main__":
    unittest.main()
