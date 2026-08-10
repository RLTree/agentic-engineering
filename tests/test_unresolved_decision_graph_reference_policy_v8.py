from __future__ import annotations

import hashlib
import itertools
import json
import subprocess
import unittest
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "evals/foundation-v4/unresolved-decision-graph-reference-policy-v8.json"
BASE_PATH = ROOT / "evals/foundation-v4/reduced-four-skills/candidate.json"
H3_POLICY_PATH = ROOT / "evals/foundation-v4/decision-certificate-reference-policy-v6.json"

POLICY = json.loads(POLICY_PATH.read_text())
BASE = json.loads(BASE_PATH.read_text())
H3_POLICY = json.loads(H3_POLICY_PATH.read_text())

EXPECTED_AUTHORITY = {
    "base_candidate": {
        "commit": "f09a0544acf4b7a95fff796434273511a0683ca9",
        "tree": "38c8c8adf3bb633d33200df1ec65f33e985ae244",
        "path": "evals/foundation-v4/reduced-four-skills/candidate.json",
        "sha256": "854f67bdd03e7121bd20e5513ef61ac806d016b3a5f1d6e5891bf4d9e546eb1f",
    },
    "h3_cover_authority": {
        "commit": "c4e661a926e0ace78d9da83f71d9c52d311abb72",
        "tree": "f2abb05d32a888c9054ef2e7ab3ad0f08547de88",
        "path": "evals/foundation-v4/decision-certificate-reference-policy-v6.json",
        "sha256": "92982c278e33ff52edce1ba2a16082afb3ecc1989d8333a77eee9ca0911fee19",
    },
}
EXPECTED_SLOT_ROWS = (
    (
        "s0",
        "topology-control-boundary",
        "agentic-engineering",
        "decomposition-boundary",
        "architecture-boundary",
    ),
    (
        "s1",
        "task-contract",
        "codex-task-contract",
        "decision-contract",
        "reference-isolation",
    ),
    (
        "s2",
        "verification-strategy",
        "verification-strategy-engineering",
        "verification-evidence",
        "reference-isolation",
    ),
    (
        "s3",
        "engineering-learning",
        "engineering-learning-loop",
        "reference-isolation",
        "learning-adoption",
    ),
)
EXPECTED_PAYLOADS = {
    ("s0", "primary"): "aq-agentic-seven-layer",
    ("s0", "secondary"): "aq-agentic-architecture",
    ("s1", "primary"): "aq-contract-vocabulary",
    ("s1", "secondary"): "aq-contract-assumption-approval",
    ("s2", "primary"): "aq-verify-mode-selection",
    ("s2", "secondary"): "aq-verify-boundary",
    ("s3", "primary"): "aq-learning-attribution",
    ("s3", "secondary"): "aq-learning-freshness",
}

SLOT_ORDER = tuple(POLICY["reference_need_contract"]["slot_order"])
NEEDS = tuple(POLICY["reference_need_contract"]["reference_need_enum"])
SELECTION_STATUSES = tuple(
    POLICY["reference_need_contract"]["selection_gate"]["closed_selection_statuses"]
)
EMITTING_STATUSES = tuple(
    POLICY["reference_need_contract"]["selection_gate"]["emitting_selection_statuses"]
)
NON_EMITTING_STATUSES = tuple(
    POLICY["reference_need_contract"]["selection_gate"]["non_emitting_selection_statuses"]
)


class CertificateInvalid(ValueError):
    """A schema-valid need vector violates the selected-slot reference contract."""


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout


def git_revision(expression: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", "--verify", expression],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def slot_rows() -> list[dict[str, str]]:
    return POLICY["reference_need_contract"]["ordered_slot_table"]


def slot_row(slot_id: str) -> dict[str, str]:
    return next(row for row in slot_rows() if row["slot_id"] == slot_id)


def need_vector(**by_slot: str) -> list[str]:
    unknown = set(by_slot) - set(SLOT_ORDER)
    if unknown:
        raise ValueError(f"unknown slots: {sorted(unknown)}")
    return [by_slot.get(slot_id, "none") for slot_id in SLOT_ORDER]


def stable_deduplicate(requests: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for request in requests:
        identity = (request["owner_adviser_id"], request["trigger_id"])
        if identity not in seen:
            seen.add(identity)
            result.append(request)
    return result


def derive_reference_requests(
    selection_status: str,
    selected_slots: Sequence[str],
    reference_needs: Sequence[str],
) -> dict[str, Any]:
    if selection_status not in SELECTION_STATUSES:
        raise ValueError("closed selection status required")
    if not isinstance(selected_slots, (list, tuple)):
        raise ValueError("closed selected slots required")
    if len(selected_slots) != len(set(selected_slots)) or any(
        slot_id not in SLOT_ORDER for slot_id in selected_slots
    ):
        raise ValueError("closed selected slots required")
    canonical_selected = [slot_id for slot_id in SLOT_ORDER if slot_id in selected_slots]
    if list(selected_slots) != canonical_selected:
        raise ValueError("selected slots must use frozen order")
    if not isinstance(reference_needs, (list, tuple)) or len(reference_needs) != len(SLOT_ORDER):
        raise ValueError("closed fixed-order reference needs required")
    if any(need not in NEEDS for need in reference_needs):
        raise ValueError("closed reference need enum required")

    if selection_status in NON_EMITTING_STATUSES:
        if selected_slots:
            raise ValueError("non-emitting selection status must select no slots")
        if any(need != "none" for need in reference_needs):
            raise CertificateInvalid("unselected slot reference need must be none")
        return {
            "selected_adviser_ids": [],
            "requests": [],
            "reference_uncertain_slots": [],
        }

    if selection_status == "automatic" and len(selected_slots) > 2:
        raise ValueError("automatic root cap exceeded")
    if selection_status == "exact" and len(selected_slots) != 1:
        raise ValueError("exact selection requires one selected slot")

    selected = set(selected_slots)
    for slot_id, need in zip(SLOT_ORDER, reference_needs, strict=True):
        if slot_id not in selected and need != "none":
            raise CertificateInvalid("unselected slot reference need must be none")

    selected_advisers = [slot_row(slot_id)["adviser_id"] for slot_id in selected_slots]
    requests: list[dict[str, str]] = []
    uncertain_slots: list[str] = []
    for slot_id in selected_slots:
        row = slot_row(slot_id)
        need = reference_needs[SLOT_ORDER.index(slot_id)]
        if need == "uncertain":
            uncertain_slots.append(slot_id)
        elif need in ("primary", "secondary"):
            requests.append(
                {
                    "owner_adviser_id": row["adviser_id"],
                    "trigger_id": row[f"{need}_trigger_id"],
                }
            )
    return {
        "selected_adviser_ids": selected_advisers,
        "requests": stable_deduplicate(requests),
        "reference_uncertain_slots": uncertain_slots,
    }


def payload_catalog() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for skill in BASE["skills"]:
        for reference in skill["references"]:
            rows.append(
                {
                    "payload_id": reference["payload_id"],
                    "owner_adviser_id": skill["id"],
                    "trigger_ids": tuple(reference["trigger_ids"]),
                }
            )
    return rows


def validate_catalog(catalog: Any) -> list[dict[str, Any]]:
    if not isinstance(catalog, list):
        raise ValueError("closed payload catalog required")
    payload_ids: list[str] = []
    for row in catalog:
        if not isinstance(row, dict) or set(row) != {
            "payload_id",
            "owner_adviser_id",
            "trigger_ids",
        }:
            raise ValueError("closed payload row required")
        if not isinstance(row["payload_id"], str) or not row["payload_id"]:
            raise ValueError("closed payload identity required")
        if not isinstance(row["owner_adviser_id"], str) or not row["owner_adviser_id"]:
            raise ValueError("closed payload owner required")
        if not isinstance(row["trigger_ids"], (list, tuple)) or any(
            not isinstance(trigger, str) or not trigger for trigger in row["trigger_ids"]
        ):
            raise ValueError("closed payload triggers required")
        payload_ids.append(row["payload_id"])
    if len(payload_ids) != len(set(payload_ids)):
        raise ValueError("payload identities must be unique")
    return catalog


def canonical_cover(
    requests: list[dict[str, str]], catalog: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    if any(
        not isinstance(request, dict)
        or set(request) != {"owner_adviser_id", "trigger_id"}
        or any(not isinstance(value, str) or not value for value in request.values())
        for request in requests
    ):
        raise ValueError("closed owner-qualified requests required")
    required = {(row["owner_adviser_id"], row["trigger_id"]) for row in requests}
    if len(required) != len(requests):
        raise ValueError("request identities must be unique")
    available = validate_catalog(payload_catalog() if catalog is None else catalog)
    eligible = sorted(
        (
            row
            for row in available
            if any(
                row["owner_adviser_id"] == owner and trigger in row["trigger_ids"]
                for owner, trigger in required
            )
        ),
        key=lambda row: row["payload_id"],
    )

    def covered(rows: tuple[dict[str, Any], ...]) -> set[tuple[str, str]]:
        return {
            (owner, trigger)
            for owner, trigger in required
            if any(
                row["owner_adviser_id"] == owner and trigger in row["trigger_ids"]
                for row in rows
            )
        }

    for size in range(len(eligible) + 1):
        covers = [
            rows
            for rows in itertools.combinations(eligible, size)
            if covered(rows) == required
        ]
        if covers:
            choice = min(covers, key=lambda rows: tuple(row["payload_id"] for row in rows))
            if size > POLICY["canonical_cover"]["maximum_payloads"]:
                return validate_cover_result(
                    {"status": "cap_exceeded", "resolved_count": size, "payload_ids": []}
                )
            return validate_cover_result(
                {
                    "status": "resolved",
                    "resolved_count": size,
                    "payload_ids": [row["payload_id"] for row in choice],
                }
            )
    return validate_cover_result(
        {"status": "unresolved", "resolved_count": 0, "payload_ids": []}
    )


def validate_cover_result(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict) or set(result) != {
        "status",
        "resolved_count",
        "payload_ids",
    }:
        raise ValueError("closed cover result required")
    status = result["status"]
    count = result["resolved_count"]
    payloads = result["payload_ids"]
    maximum = POLICY["canonical_cover"]["maximum_payloads"]
    if status not in POLICY["canonical_cover"]["statuses"]:
        raise ValueError("closed cover status required")
    if type(count) is not int or count < 0:
        raise ValueError("closed cover count required")
    if not isinstance(payloads, list) or any(
        not isinstance(payload_id, str) or not payload_id for payload_id in payloads
    ):
        raise ValueError("closed cover payload identities required")
    if payloads != sorted(set(payloads)):
        raise ValueError("cover payload identity and order mismatch")
    if status == "resolved" and not (count == len(payloads) <= maximum):
        raise ValueError("resolved branch mismatch")
    if status == "unresolved" and not (count == 0 and payloads == []):
        raise ValueError("unresolved branch mismatch")
    if status == "cap_exceeded" and not (count > maximum and payloads == []):
        raise ValueError("cap-exceeded branch mismatch")
    return result


class UnresolvedDecisionGraphReferencePolicyV8Tests(unittest.TestCase):
    def test_policy_surface_is_closed_parent_owned_and_structural_only(self):
        self.assertEqual(
            set(POLICY),
            {
                "schema_version",
                "policy_id",
                "status",
                "claim_ceiling",
                "authority_basis",
                "model_boundary",
                "reference_need_contract",
                "canonical_cover",
                "qualification_controls",
            },
        )
        self.assertEqual(POLICY["schema_version"], "8.0")
        self.assertEqual(
            POLICY["policy_id"],
            "H4-unresolved-decision-graph-parent-reference-policy",
        )
        self.assertEqual(POLICY["status"], "frozen-proposal-only")
        self.assertEqual(POLICY["claim_ceiling"], "structural-proposal-only")
        self.assertEqual(
            set(POLICY["model_boundary"]),
            {
                "model_visible",
                "model_visible_projection",
                "model_output_used",
                "parent_owned_inputs",
                "route_independence",
            },
        )
        self.assertEqual(
            POLICY["model_boundary"],
            {
                "model_visible": False,
                "model_visible_projection": "An anonymous fixed-slot reference-need legend only; no logical atom, adviser, trigger, payload, authority, route, effect, or claim values.",
                "model_output_used": "Schema-valid fixed-order reference_needs only after routing is independently resolved.",
                "parent_owned_inputs": [
                    "selection_status",
                    "selected_slots",
                    "ordered_slot_table",
                    "reference_payload_catalog",
                ],
                "route_independence": "reference_needs MUST NOT influence graph validation, root selection, exact-invocation selection, selection status, selected slots, or adviser selection.",
            },
        )
        self.assertEqual(
            set(POLICY["reference_need_contract"]),
            {
                "slot_order",
                "reference_need_enum",
                "ordered_slot_table",
                "routing_precondition",
                "selection_gate",
                "unselected_slot_rule",
                "selected_slot_rules",
                "request_shape",
                "deduplication",
            },
        )
        self.assertEqual(
            set(POLICY["canonical_cover"]),
            {
                "source_authority",
                "requirement_identity",
                "payload_eligibility",
                "objective_order",
                "payload_output_order",
                "maximum_payloads",
                "statuses",
                "branch_contracts",
            },
        )
        self.assertEqual(
            set(POLICY["reference_need_contract"]["selection_gate"]),
            {
                "closed_selection_statuses",
                "emitting_selection_statuses",
                "automatic",
                "exact",
                "non_emitting_selection_statuses",
                "non_emitting_rule",
            },
        )
        self.assertEqual(
            set(POLICY["reference_need_contract"]["unselected_slot_rule"]),
            {"required_need", "classes", "violation"},
        )
        self.assertEqual(
            set(POLICY["reference_need_contract"]["selected_slot_rules"]),
            set(NEEDS),
        )
        self.assertEqual(
            POLICY["reference_need_contract"]["routing_precondition"],
            "Graph and exact-invocation routing are resolved before this policy runs; this policy only validates reference needs and derives owner-qualified requests for already-selected slots.",
        )
        self.assertEqual(
            POLICY["reference_need_contract"]["selection_gate"],
            {
                "closed_selection_statuses": [
                    "automatic",
                    "exact",
                    "ambiguous",
                    "unrecognized",
                    "cap_exceeded",
                    "graph_uncertain",
                    "graph_invalid",
                    "graph_cycle",
                ],
                "emitting_selection_statuses": ["automatic", "exact"],
                "automatic": "Only zero through two root_slots copied to selected_slots in frozen slot order are selected and may emit.",
                "exact": "Only the one exact-invocation selected slot may emit; graph telemetry does not redirect or suppress that exact selection after schema validation.",
                "non_emitting_selection_statuses": [
                    "ambiguous",
                    "unrecognized",
                    "cap_exceeded",
                    "graph_uncertain",
                    "graph_invalid",
                    "graph_cycle",
                ],
                "non_emitting_rule": "selected_slots MUST be empty and every reference need MUST be none.",
            },
        )
        self.assertEqual(
            POLICY["reference_need_contract"]["unselected_slot_rule"],
            {
                "required_need": "none",
                "classes": [
                    "resolved_or_absent",
                    "downstream_unresolved",
                    "state_or_graph_uncertain",
                    "graph_invalid",
                    "graph_cycle",
                    "cap_exceeded",
                    "ambiguous",
                    "unrecognized",
                    "otherwise_unselected",
                ],
                "violation": "certificate_invalid_before_request_or_cover",
            },
        )
        self.assertEqual(
            POLICY["reference_need_contract"]["selected_slot_rules"],
            {
                "none": "emit_no_request",
                "primary": "emit_exactly_one_owner_qualified_request_for_that_slot_owner_and_primary_trigger",
                "secondary": "emit_exactly_one_owner_qualified_request_for_that_slot_owner_and_secondary_trigger",
                "uncertain": "emit_no_request_and_record_reference_uncertain_without_changing_selected_slots_or_advisers",
            },
        )
        self.assertEqual(
            POLICY["reference_need_contract"]["request_shape"],
            ["owner_adviser_id", "trigger_id"],
        )
        self.assertEqual(
            POLICY["reference_need_contract"]["deduplication"],
            "Stable first occurrence by owner_adviser_id then trigger_id.",
        )
        self.assertEqual(
            set(POLICY["qualification_controls"]),
            {
                "outcome_tuned",
                "corpus_inputs_permitted",
                "hidden_label_inputs_permitted",
                "binding_scope",
                "aq8_failure_rule",
                "prohibitions",
                "maximum_claim",
            },
        )

    def test_authority_basis_is_exact_closed_and_matches_immutable_and_live_bytes(self):
        self.assertEqual(POLICY["authority_basis"], EXPECTED_AUTHORITY)
        for binding in EXPECTED_AUTHORITY.values():
            self.assertEqual(set(binding), {"commit", "tree", "path", "sha256"})
            self.assertEqual(git_revision(f"{binding['commit']}^{{commit}}"), binding["commit"])
            self.assertEqual(git_revision(f"{binding['commit']}^{{tree}}"), binding["tree"])
            immutable = git_bytes(binding["commit"], binding["path"])
            self.assertEqual(hashlib.sha256(immutable).hexdigest(), binding["sha256"])
            self.assertEqual((ROOT / binding["path"]).read_bytes(), immutable)

    def test_h3_cover_contract_is_reused_exactly(self):
        cover = POLICY["canonical_cover"]
        for field in (
            "requirement_identity",
            "payload_eligibility",
            "objective_order",
            "payload_output_order",
            "maximum_payloads",
            "statuses",
            "branch_contracts",
        ):
            self.assertEqual(cover[field], H3_POLICY["canonical_cover"][field], field)
        self.assertEqual(cover["source_authority"], "h3_cover_authority")

    def test_slot_state_need_status_and_mapping_tables_are_exact(self):
        contract = POLICY["reference_need_contract"]
        self.assertEqual(SLOT_ORDER, ("s0", "s1", "s2", "s3"))
        self.assertEqual(NEEDS, ("none", "primary", "secondary", "uncertain"))
        self.assertEqual(
            SELECTION_STATUSES,
            (
                "automatic",
                "exact",
                "ambiguous",
                "unrecognized",
                "cap_exceeded",
                "graph_uncertain",
                "graph_invalid",
                "graph_cycle",
            ),
        )
        self.assertEqual(EMITTING_STATUSES, ("automatic", "exact"))
        self.assertEqual(
            NON_EMITTING_STATUSES,
            (
                "ambiguous",
                "unrecognized",
                "cap_exceeded",
                "graph_uncertain",
                "graph_invalid",
                "graph_cycle",
            ),
        )
        rows = slot_rows()
        self.assertTrue(
            all(
                set(row)
                == {
                    "slot_id",
                    "logical_atom",
                    "adviser_id",
                    "primary_trigger_id",
                    "secondary_trigger_id",
                }
                for row in rows
            )
        )
        self.assertEqual(
            tuple(
                (
                    row["slot_id"],
                    row["logical_atom"],
                    row["adviser_id"],
                    row["primary_trigger_id"],
                    row["secondary_trigger_id"],
                )
                for row in rows
            ),
            EXPECTED_SLOT_ROWS,
        )

    def test_every_table_trigger_has_an_owner_matching_base_payload(self):
        catalog = payload_catalog()
        base_owners = {skill["id"] for skill in BASE["skills"]}
        for row in slot_rows():
            self.assertIn(row["adviser_id"], base_owners)
            for need in ("primary", "secondary"):
                trigger = row[f"{need}_trigger_id"]
                self.assertTrue(
                    any(
                        payload["owner_adviser_id"] == row["adviser_id"]
                        and trigger in payload["trigger_ids"]
                        for payload in catalog
                    ),
                    (row["slot_id"], row["adviser_id"], trigger),
                )
                derived = derive_reference_requests(
                    "exact", [row["slot_id"]], need_vector(**{row["slot_id"]: need})
                )
                self.assertEqual(
                    canonical_cover(derived["requests"])["payload_ids"],
                    [EXPECTED_PAYLOADS[(row["slot_id"], need)]],
                )

    def test_all_zero_to_two_root_sets_and_needs_resolve_to_at_most_two_payloads(self):
        catalog = payload_catalog()
        catalog_orders = (
            catalog,
            list(reversed(catalog)),
            catalog[3:] + catalog[:3],
        )
        for size in range(3):
            for roots in itertools.combinations(SLOT_ORDER, size):
                for selected_needs in itertools.product(NEEDS, repeat=size):
                    needs = need_vector(**dict(zip(roots, selected_needs, strict=True)))
                    derived = derive_reference_requests("automatic", list(roots), needs)
                    self.assertEqual(
                        derived["selected_adviser_ids"],
                        [slot_row(slot_id)["adviser_id"] for slot_id in roots],
                    )
                    self.assertLessEqual(len(derived["requests"]), size)
                    results = [
                        canonical_cover(derived["requests"], order) for order in catalog_orders
                    ]
                    self.assertTrue(all(result == results[0] for result in results[1:]))
                    self.assertEqual(results[0]["status"], "resolved")
                    self.assertLessEqual(results[0]["resolved_count"], 2)
                    self.assertEqual(
                        results[0]["resolved_count"], len(results[0]["payload_ids"])
                    )

    def test_automatic_selection_rejects_more_than_two_or_noncanonical_roots(self):
        with self.assertRaisesRegex(ValueError, "automatic root cap exceeded"):
            derive_reference_requests("automatic", ["s0", "s1", "s2"], need_vector())
        with self.assertRaisesRegex(ValueError, "frozen order"):
            derive_reference_requests("automatic", ["s1", "s0"], need_vector())

    def test_payload_eligibility_never_crosses_owner_boundary(self):
        for row in slot_rows():
            for need in ("primary", "secondary"):
                trigger = row[f"{need}_trigger_id"]
                request = [
                    {"owner_adviser_id": row["adviser_id"], "trigger_id": trigger}
                ]
                wrong_owner = [
                    {
                        "payload_id": f"wrong-owner-{row['slot_id']}-{need}",
                        "owner_adviser_id": "different-owner",
                        "trigger_ids": (trigger,),
                    }
                ]
                self.assertEqual(
                    canonical_cover(request, wrong_owner),
                    {"status": "unresolved", "resolved_count": 0, "payload_ids": []},
                )
        request = [
            {
                "owner_adviser_id": "codex-task-contract",
                "trigger_id": "reference-isolation",
            }
        ]
        other_base_owners = [
            payload
            for payload in payload_catalog()
            if payload["owner_adviser_id"] != "codex-task-contract"
        ]
        self.assertTrue(
            any("reference-isolation" in payload["trigger_ids"] for payload in other_base_owners)
        )
        self.assertEqual(canonical_cover(request, other_base_owners)["status"], "unresolved")

    def test_catalog_order_and_lexical_ties_are_deterministic(self):
        request = [{"owner_adviser_id": "owner-a", "trigger_id": "trigger-a"}]
        tied = [
            {
                "payload_id": "payload-z",
                "owner_adviser_id": "owner-a",
                "trigger_ids": ("trigger-a",),
            },
            {
                "payload_id": "payload-a",
                "owner_adviser_id": "owner-a",
                "trigger_ids": ("trigger-a",),
            },
            {
                "payload_id": "payload-m",
                "owner_adviser_id": "owner-a",
                "trigger_ids": ("trigger-a",),
            },
        ]
        expected = {
            "status": "resolved",
            "resolved_count": 1,
            "payload_ids": ["payload-a"],
        }
        for order in itertools.permutations(tied):
            self.assertEqual(canonical_cover(request, list(order)), expected)

    def test_every_unselected_slot_requires_none_or_certificate_is_invalid(self):
        required_classes = {
            "resolved_or_absent",
            "downstream_unresolved",
            "state_or_graph_uncertain",
            "graph_invalid",
            "graph_cycle",
            "cap_exceeded",
            "ambiguous",
            "unrecognized",
            "otherwise_unselected",
        }
        rule = POLICY["reference_need_contract"]["unselected_slot_rule"]
        self.assertEqual(rule["required_need"], "none")
        self.assertEqual(set(rule["classes"]), required_classes)
        self.assertEqual(rule["violation"], "certificate_invalid_before_request_or_cover")
        for size in range(3):
            for selected in itertools.combinations(SLOT_ORDER, size):
                for unselected in set(SLOT_ORDER) - set(selected):
                    for leaked_need in ("primary", "secondary", "uncertain"):
                        with self.assertRaises(CertificateInvalid):
                            derive_reference_requests(
                                "automatic",
                                list(selected),
                                need_vector(**{unselected: leaked_need}),
                            )

    def test_non_emitting_statuses_require_empty_selection_and_all_none(self):
        empty = need_vector()
        for status in NON_EMITTING_STATUSES:
            self.assertEqual(
                derive_reference_requests(status, [], empty),
                {
                    "selected_adviser_ids": [],
                    "requests": [],
                    "reference_uncertain_slots": [],
                },
            )
            for slot_id in SLOT_ORDER:
                for leaked_need in ("primary", "secondary", "uncertain"):
                    with self.assertRaises(CertificateInvalid):
                        derive_reference_requests(
                            status, [], need_vector(**{slot_id: leaked_need})
                        )
            with self.assertRaisesRegex(ValueError, "select no slots"):
                derive_reference_requests(status, ["s0"], empty)

    def test_selected_uncertain_is_local_and_does_not_change_adviser_selection(self):
        selected = ["s0", "s2"]
        result = derive_reference_requests(
            "automatic",
            selected,
            need_vector(s0="uncertain", s2="primary"),
        )
        self.assertEqual(
            result["selected_adviser_ids"],
            ["agentic-engineering", "verification-strategy-engineering"],
        )
        self.assertEqual(result["reference_uncertain_slots"], ["s0"])
        self.assertEqual(
            result["requests"],
            [
                {
                    "owner_adviser_id": "verification-strategy-engineering",
                    "trigger_id": "verification-evidence",
                }
            ],
        )

    def test_exact_invocation_allows_only_one_selected_slot_and_follows_its_need(self):
        for slot_id in SLOT_ORDER:
            row = slot_row(slot_id)
            for need in NEEDS:
                result = derive_reference_requests(
                    "exact", [slot_id], need_vector(**{slot_id: need})
                )
                self.assertEqual(result["selected_adviser_ids"], [row["adviser_id"]])
                if need in ("primary", "secondary"):
                    self.assertEqual(
                        result["requests"],
                        [
                            {
                                "owner_adviser_id": row["adviser_id"],
                                "trigger_id": row[f"{need}_trigger_id"],
                            }
                        ],
                    )
                    self.assertEqual(result["reference_uncertain_slots"], [])
                elif need == "uncertain":
                    self.assertEqual(result["requests"], [])
                    self.assertEqual(result["reference_uncertain_slots"], [slot_id])
                else:
                    self.assertEqual(result["requests"], [])
                    self.assertEqual(result["reference_uncertain_slots"], [])
        for invalid_selection in ([], ["s0", "s1"]):
            with self.assertRaisesRegex(ValueError, "exact selection requires one"):
                derive_reference_requests("exact", invalid_selection, need_vector())
        for leaked_need in ("primary", "secondary", "uncertain"):
            with self.assertRaises(CertificateInvalid):
                derive_reference_requests(
                    "exact", ["s1"], need_vector(s0=leaked_need)
                )
        self.assertIn(
            "graph telemetry does not redirect or suppress",
            POLICY["reference_need_contract"]["selection_gate"]["exact"],
        )

    def test_request_deduplication_is_stable_owner_plus_trigger(self):
        requests = [
            {"owner_adviser_id": "owner-b", "trigger_id": "trigger-z"},
            {"owner_adviser_id": "owner-a", "trigger_id": "trigger-a"},
            {"owner_adviser_id": "owner-b", "trigger_id": "trigger-z"},
            {"owner_adviser_id": "owner-a", "trigger_id": "trigger-b"},
        ]
        self.assertEqual(
            stable_deduplicate(requests),
            [requests[0], requests[1], requests[3]],
        )

    def test_cover_statuses_and_exact_branch_shapes_are_closed(self):
        four_requests = [
            {
                "owner_adviser_id": row["adviser_id"],
                "trigger_id": row["primary_trigger_id"],
            }
            for row in slot_rows()
        ]
        self.assertEqual(
            canonical_cover(four_requests),
            {"status": "cap_exceeded", "resolved_count": 4, "payload_ids": []},
        )
        self.assertEqual(
            canonical_cover(
                [{"owner_adviser_id": "agentic-engineering", "trigger_id": "missing"}]
            ),
            {"status": "unresolved", "resolved_count": 0, "payload_ids": []},
        )
        valid = (
            {"status": "resolved", "resolved_count": 0, "payload_ids": []},
            {"status": "resolved", "resolved_count": 1, "payload_ids": ["payload-a"]},
            {"status": "unresolved", "resolved_count": 0, "payload_ids": []},
            {"status": "cap_exceeded", "resolved_count": 4, "payload_ids": []},
        )
        for result in valid:
            self.assertIs(validate_cover_result(result), result)
        invalid = (
            {"status": "unresolved", "resolved_count": 1, "payload_ids": ["partial"]},
            {"status": "unresolved", "resolved_count": 1, "payload_ids": []},
            {"status": "cap_exceeded", "resolved_count": 4, "payload_ids": ["partial"]},
            {"status": "cap_exceeded", "resolved_count": 3, "payload_ids": []},
            {"status": "resolved", "resolved_count": 0, "payload_ids": ["payload-a"]},
            {"status": "resolved", "resolved_count": 2, "payload_ids": ["payload-b", "payload-a"]},
            {"status": "resolved", "resolved_count": True, "payload_ids": ["payload-a"]},
        )
        for result in invalid:
            with self.assertRaises(ValueError):
                validate_cover_result(result)

    def test_no_corpus_case_result_or_route_authority_is_bound(self):
        self.assertEqual(set(POLICY["authority_basis"]), {"base_candidate", "h3_cover_authority"})
        forbidden_keys = {
            "case",
            "case_id",
            "prompt",
            "corpus",
            "corpus_path",
            "corpus_sha256",
            "labels",
            "hidden_labels",
            "expected_roots",
            "expected_advisers",
            "results",
            "evaluator_outputs",
            "route_authority",
            "effects",
            "claims",
        }

        def nested_keys(value: Any) -> set[str]:
            found: set[str] = set()
            if isinstance(value, dict):
                for key, nested in value.items():
                    found.add(key)
                    found.update(nested_keys(nested))
            elif isinstance(value, list):
                for nested in value:
                    found.update(nested_keys(nested))
            return found

        self.assertFalse(forbidden_keys & nested_keys(POLICY))

    def test_no_outcome_tuning_and_aq8_failure_is_terminal(self):
        controls = POLICY["qualification_controls"]
        self.assertEqual(
            controls,
            {
                "outcome_tuned": False,
                "corpus_inputs_permitted": False,
                "hidden_label_inputs_permitted": False,
                "binding_scope": "frozen_base_candidate_and_h3_cover_authority_only",
                "aq8_failure_rule": "Any AQ8 failure is terminal: stop without outcome tuning, replay, policy revision, or successor-hypothesis promotion.",
                "prohibitions": [
                    "no_corpus_binding",
                    "no_hidden_label_or_result_input",
                    "no_reference_need_route_influence",
                    "no_model_visible_owner_trigger_or_payload_table",
                    "no_authority_assignment",
                    "no_policy_adoption",
                    "no_effect_execution",
                    "no_external_action",
                    "no_completion_claim",
                    "no_efficacy_claim",
                    "no_product_claim",
                    "no_runtime_claim",
                    "no_provider_claim",
                    "no_promotion_claim",
                ],
                "maximum_claim": "A frozen parent-owned H4 reference policy can establish route-independent request derivation and reproducible owner-qualified catalog resolution only.",
            },
        )
        self.assertIn("no_corpus_binding", controls["prohibitions"])
        self.assertIn("no_reference_need_route_influence", controls["prohibitions"])
        self.assertNotIn("future-activation", POLICY_PATH.read_text())


if __name__ == "__main__":
    unittest.main()
