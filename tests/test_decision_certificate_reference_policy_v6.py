from __future__ import annotations

import itertools
import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "evals/foundation-v4/decision-certificate-reference-policy-v6.json"
PROTOCOL_PATH = ROOT / "evals/foundation-v4/decision-certificate-protocol-v6.json"
BASE_PATH = ROOT / "evals/foundation-v4/reduced-four-skills/candidate.json"

POLICY = json.loads(POLICY_PATH.read_text())
PROTOCOL = json.loads(PROTOCOL_PATH.read_text())
BASE = json.loads(BASE_PATH.read_text())

ATOMS = tuple(PROTOCOL["deterministic_selection"]["derived_atom_order"])
PREDICATES = tuple(PROTOCOL["predicate_order"])
STATES = ("present", "absent", "uncertain")
ATOM_TO_ADVISER = {
    row["logical_atom"]: row["token"].removeprefix("$")
    for row in PROTOCOL["explicit_constraint"]["ordered_token_to_logical_atom"]
}
EXPECTED_ROWS = (
    ("topology-control-boundary", "agentic-engineering", "multi_domain_coordination", "decomposition-boundary"),
    ("topology-control-boundary", "agentic-engineering", "cross_component_or_agent_boundary", "architecture-boundary"),
    ("task-contract", "codex-task-contract", "scope_acceptance_or_authority_contract", "decision-contract"),
    ("task-contract", "codex-task-contract", "execution_dependencies_or_stop_conditions", "decision-contract"),
    ("verification-strategy", "verification-strategy-engineering", "claim_or_behavior_requires_verification_strategy", "verification-evidence"),
    ("verification-strategy", "verification-strategy-engineering", "oracle_or_evidence_adequacy_is_a_decision", "verification-evidence"),
    ("engineering-learning", "engineering-learning-loop", "failure_attribution_or_adaptation_is_a_decision", "reference-isolation"),
    ("engineering-learning", "engineering-learning-loop", "evaluation_or_knowledge_lifecycle_is_a_decision", "learning-adoption"),
)
EXCLUSION_PREDICATES = tuple(
    row["exclusion_predicate"] for row in PROTOCOL["deterministic_selection"]["eligibility_rules"]
)


def fact_map(**states: str) -> dict[str, str]:
    unknown = set(states) - set(PREDICATES)
    if unknown:
        raise ValueError(f"unknown predicates: {sorted(unknown)}")
    return {predicate: states.get(predicate, "absent") for predicate in PREDICATES}


def mapping_rows() -> list[dict[str, str]]:
    return POLICY["request_derivation"]["ordered_mapping_rows"]


def derive_requests(
    facts: dict[str, str], selection_status: str, selected_atoms: Iterable[str]
) -> list[dict[str, str]]:
    if set(facts) != set(PREDICATES) or any(facts[predicate] not in STATES for predicate in PREDICATES):
        raise ValueError("closed predicate facts required")
    selected = list(selected_atoms)
    if len(selected) != len(set(selected)) or any(atom not in ATOMS for atom in selected):
        raise ValueError("closed selected atoms required")
    canonical = [atom for atom in ATOMS if atom in selected]
    if selected != canonical:
        raise ValueError("selected atoms must use H3 order")
    if selection_status not in POLICY["request_derivation"]["emitting_selection_statuses"]:
        if selection_status not in POLICY["request_derivation"]["non_emitting_selection_statuses"]:
            raise ValueError("closed selection status required")
        return []
    if not selected:
        return []
    requests: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for atom in selected:
        rule = next(
            row for row in PROTOCOL["deterministic_selection"]["eligibility_rules"]
            if row["derived_atom"] == atom
        )
        if facts[rule["exclusion_predicate"]] == "present":
            continue
        for row in mapping_rows():
            if row["atom_id"] != atom or facts[row["predicate_id"]] != "present":
                continue
            identity = (row["adviser_id"], row["trigger_id"])
            if identity not in seen:
                seen.add(identity)
                requests.append({"owner_adviser_id": identity[0], "trigger_id": identity[1]})
            break
    return requests


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


def canonical_cover(
    requests: list[dict[str, str]], catalog: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    available = payload_catalog() if catalog is None else catalog
    required = {(row["owner_adviser_id"], row["trigger_id"]) for row in requests}
    if len(required) != len(requests):
        raise ValueError("request identities must be unique")
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
        covers = [rows for rows in itertools.combinations(eligible, size) if covered(rows) == required]
        if covers:
            choice = min(covers, key=lambda rows: tuple(row["payload_id"] for row in rows))
            if size > POLICY["canonical_cover"]["maximum_payloads"]:
                return validate_cover_result({"status": "cap_exceeded", "resolved_count": size, "payload_ids": []})
            return validate_cover_result({
                "status": "resolved",
                "resolved_count": size,
                "payload_ids": sorted(row["payload_id"] for row in choice),
            })
    return validate_cover_result({"status": "unresolved", "resolved_count": 0, "payload_ids": []})


def validate_cover_result(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict) or set(result) != {"status", "resolved_count", "payload_ids"}:
        raise ValueError("closed cover result required")
    status, count, payloads = result["status"], result["resolved_count"], result["payload_ids"]
    maximum = POLICY["canonical_cover"]["maximum_payloads"]
    if status not in POLICY["canonical_cover"]["statuses"] or type(count) is not int or count < 0:
        raise ValueError("closed cover status and count required")
    if not isinstance(payloads, list) or any(not isinstance(item, str) or not item for item in payloads):
        raise ValueError("closed cover payloads required")
    if payloads != sorted(set(payloads)):
        raise ValueError("cover payload identity and order mismatch")
    if status == "resolved" and not (count == len(payloads) <= maximum):
        raise ValueError("resolved branch mismatch")
    if status == "unresolved" and not (count == 0 and payloads == []):
        raise ValueError("unresolved branch mismatch")
    if status == "cap_exceeded" and not (count > maximum and payloads == []):
        raise ValueError("cap-exceeded branch mismatch")
    return result


class DecisionCertificateReferencePolicyV6Tests(unittest.TestCase):
    def test_policy_surface_is_closed_and_proposal_only(self):
        self.assertEqual(
            set(POLICY),
            {
                "schema_version", "policy_id", "status", "claim_ceiling", "authority_basis",
                "model_boundary", "request_derivation", "canonical_cover", "qualification_controls",
            },
        )
        self.assertEqual(POLICY["schema_version"], "6.0")
        self.assertEqual(POLICY["status"], "frozen-proposal-only")
        self.assertEqual(POLICY["claim_ceiling"], "structural-proposal-only")
        self.assertEqual(set(POLICY["authority_basis"]), {"h3_commit", "h3_tree", "h3_protocol", "base_candidate"})
        self.assertEqual(
            set(POLICY["model_boundary"]),
            {"model_visible", "model_output_used", "parent_owned_inputs"},
        )
        self.assertEqual(
            set(POLICY["request_derivation"]),
            {
                "selected_atom_order", "emitting_selection_statuses", "non_emitting_selection_statuses",
                "empty_selection", "state_rule", "per_selected_atom_rule", "ordered_mapping_rows",
                "request_shape", "deduplication",
            },
        )
        self.assertEqual(
            set(POLICY["canonical_cover"]),
            {
                "requirement_identity", "payload_eligibility", "objective_order",
                "payload_output_order", "maximum_payloads", "statuses", "branch_contracts",
            },
        )
        self.assertEqual(
            set(POLICY["qualification_controls"]),
            {
                "outcome_tuned", "corpus_inputs_permitted", "hidden_label_inputs_permitted",
                "prohibitions", "maximum_claim",
            },
        )
        self.assertFalse(POLICY["model_boundary"]["model_visible"])
        controls = POLICY["qualification_controls"]
        self.assertFalse(controls["outcome_tuned"])
        self.assertFalse(controls["corpus_inputs_permitted"])
        self.assertFalse(controls["hidden_label_inputs_permitted"])
        self.assertIn("no_model_visible_reference_policy", controls["prohibitions"])

    def test_authority_basis_binds_exact_commit_tree_and_live_bytes(self):
        authority = POLICY["authority_basis"]
        commit = authority["h3_commit"]
        resolved_commit = subprocess.run(
            ["git", "rev-parse", "--verify", f"{commit}^{{commit}}"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        resolved_tree = subprocess.run(
            ["git", "rev-parse", "--verify", f"{commit}^{{tree}}"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(resolved_commit, "ccbe06be9a2ef5feca4104b6918985ee9c4527c0")
        self.assertEqual(resolved_tree, "dd20449fdc45a73c55adb349d8c828687728ef4d")
        for key in ("h3_protocol", "base_candidate"):
            binding = authority[key]
            self.assertEqual(set(binding), {"path", "sha256"})
            immutable = subprocess.run(
                ["git", "show", f"{commit}:{binding['path']}"],
                cwd=ROOT, capture_output=True, check=True,
            ).stdout
            live = (ROOT / binding["path"]).read_bytes()
            self.assertEqual(live, immutable)
            self.assertEqual(hashlib.sha256(immutable).hexdigest(), binding["sha256"])

    def test_authority_order_mapping_and_states_are_exact(self):
        self.assertEqual(tuple(POLICY["request_derivation"]["selected_atom_order"]), ATOMS)
        self.assertEqual(
            tuple(POLICY["request_derivation"]["emitting_selection_statuses"]),
            ("automatic", "exact"),
        )
        self.assertEqual(
            tuple(POLICY["request_derivation"]["non_emitting_selection_statuses"]),
            ("ambiguous", "cap_exceeded", "unrecognized"),
        )
        self.assertEqual(POLICY["request_derivation"]["state_rule"], {
            "emitting_state": "present",
            "non_emitting_states": ["absent", "uncertain"],
            "exclusion_predicates": "A present exclusion suppresses every request for that atom; absent and uncertain exclusions emit no request themselves.",
            "explicit_override_without_present_positive": "emit_no_requests",
        })
        rows = mapping_rows()
        self.assertTrue(all(set(row) == {"atom_id", "adviser_id", "predicate_id", "trigger_id"} for row in rows))
        self.assertEqual(
            tuple((row["atom_id"], row["adviser_id"], row["predicate_id"], row["trigger_id"]) for row in rows),
            EXPECTED_ROWS,
        )
        self.assertEqual({row["atom_id"]: row["adviser_id"] for row in rows}, ATOM_TO_ADVISER)
        self.assertFalse(set(EXCLUSION_PREDICATES) & {row["predicate_id"] for row in rows})

    def test_each_mapping_is_covered_by_its_owner_in_base_catalog(self):
        catalog = payload_catalog()
        for _atom, owner, _predicate, trigger in EXPECTED_ROWS:
            self.assertTrue(
                any(row["owner_adviser_id"] == owner and trigger in row["trigger_ids"] for row in catalog),
                (owner, trigger),
            )

    def test_first_present_positive_and_non_emitting_inputs(self):
        for atom in ATOMS:
            rows = [row for row in mapping_rows() if row["atom_id"] == atom]
            first, second = rows
            expected_first = [{"owner_adviser_id": first["adviser_id"], "trigger_id": first["trigger_id"]}]
            expected_second = [{"owner_adviser_id": second["adviser_id"], "trigger_id": second["trigger_id"]}]
            for status in ("automatic", "exact"):
                self.assertEqual(derive_requests(fact_map(**{first["predicate_id"]: "present", second["predicate_id"]: "present"}), status, [atom]), expected_first)
                self.assertEqual(derive_requests(fact_map(**{second["predicate_id"]: "present"}), status, [atom]), expected_second)
            for state in ("absent", "uncertain"):
                self.assertEqual(derive_requests(fact_map(**{first["predicate_id"]: state}), "automatic", [atom]), [])
            exclusion = next(row["exclusion_predicate"] for row in PROTOCOL["deterministic_selection"]["eligibility_rules"] if row["derived_atom"] == atom)
            self.assertEqual(derive_requests(fact_map(**{exclusion: "present"}), "exact", [atom]), [])
            self.assertEqual(
                derive_requests(
                    fact_map(**{first["predicate_id"]: "present", exclusion: "present"}),
                    "exact",
                    [atom],
                ),
                [],
            )
        for status in ("ambiguous", "cap_exceeded", "unrecognized"):
            self.assertEqual(derive_requests(fact_map(multi_domain_coordination="present"), status, [ATOMS[0]]), [])
        self.assertEqual(derive_requests(fact_map(), "exact", [ATOMS[0]]), [])
        self.assertEqual(derive_requests(fact_map(multi_domain_coordination="present"), "automatic", []), [])

    def test_order_is_canonical_and_pair_deduplication_is_stable(self):
        facts = fact_map(
            multi_domain_coordination="present",
            cross_component_or_agent_boundary="present",
            scope_acceptance_or_authority_contract="present",
        )
        self.assertEqual(derive_requests(facts, "automatic", list(ATOMS[:2])), [
            {"owner_adviser_id": "agentic-engineering", "trigger_id": "decomposition-boundary"},
            {"owner_adviser_id": "codex-task-contract", "trigger_id": "decision-contract"},
        ])
        with self.assertRaisesRegex(ValueError, "H3 order"):
            derive_requests(facts, "automatic", list(reversed(ATOMS[:2])))
        duplicate_policy_rows = mapping_rows()
        duplicate_policy_rows.insert(1, dict(duplicate_policy_rows[0]))
        try:
            self.assertEqual(derive_requests(facts, "automatic", [ATOMS[0]]), [
                {"owner_adviser_id": "agentic-engineering", "trigger_id": "decomposition-boundary"}
            ])
        finally:
            duplicate_policy_rows.pop(1)

    def test_exhaustive_positive_states_and_selected_subsets_resolve_zero_to_two(self):
        positives = tuple(row[2] for row in EXPECTED_ROWS)
        selected_subsets = [
            list(subset)
            for size in range(3)
            for subset in itertools.combinations(ATOMS, size)
        ]
        for states in itertools.product(STATES, repeat=len(positives)):
            facts = fact_map(**dict(zip(positives, states, strict=True)))
            for selected in selected_subsets:
                requests = derive_requests(facts, "automatic", selected)
                self.assertLessEqual(len(requests), 2)
                result = canonical_cover(requests)
                self.assertEqual(result["status"], "resolved")
                self.assertLessEqual(result["resolved_count"], 2)
                self.assertEqual(result["resolved_count"], len(result["payload_ids"]))

    def test_owner_qualification_and_lexical_tie_are_deterministic(self):
        request = [{"owner_adviser_id": "verification-strategy-engineering", "trigger_id": "verification-evidence"}]
        expected = {"status": "resolved", "resolved_count": 1, "payload_ids": ["aq-verify-mode-selection"]}
        catalog = payload_catalog()
        self.assertEqual(canonical_cover(request, catalog), expected)
        self.assertEqual(canonical_cover(request, list(reversed(catalog))), expected)
        learning = [{"owner_adviser_id": "engineering-learning-loop", "trigger_id": "reference-isolation"}]
        self.assertEqual(canonical_cover(learning)["payload_ids"], ["aq-learning-attribution"])
        wrong_owner_catalog = [row for row in catalog if row["owner_adviser_id"] != "engineering-learning-loop"]
        self.assertEqual(canonical_cover(learning, wrong_owner_catalog)["status"], "unresolved")

    def test_cover_statuses_and_three_payload_ceiling_are_closed(self):
        four = [
            {"owner_adviser_id": "agentic-engineering", "trigger_id": "decomposition-boundary"},
            {"owner_adviser_id": "codex-task-contract", "trigger_id": "decision-contract"},
            {"owner_adviser_id": "verification-strategy-engineering", "trigger_id": "verification-evidence"},
            {"owner_adviser_id": "engineering-learning-loop", "trigger_id": "learning-adoption"},
        ]
        self.assertEqual(canonical_cover(four), {"status": "cap_exceeded", "resolved_count": 4, "payload_ids": []})
        missing = [{"owner_adviser_id": "agentic-engineering", "trigger_id": "not-in-catalog"}]
        self.assertEqual(canonical_cover(missing), {"status": "unresolved", "resolved_count": 0, "payload_ids": []})
        self.assertEqual(tuple(POLICY["canonical_cover"]["statuses"]), ("resolved", "unresolved", "cap_exceeded"))
        self.assertEqual(POLICY["canonical_cover"]["maximum_payloads"], 3)
        self.assertEqual(POLICY["canonical_cover"]["branch_contracts"], {
            "resolved": {
                "payloads": "exact_chosen_cover_in_payload_id_order",
                "resolved_count": "exact_chosen_payload_count_at_most_maximum",
            },
            "unresolved": {"payloads": "empty", "resolved_count": 0},
            "cap_exceeded": {
                "payloads": "empty",
                "resolved_count": "minimum_required_payload_count_greater_than_maximum",
            },
        })

    def test_cover_branch_contract_rejects_partial_or_miscounted_outputs(self):
        valid = (
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
        )
        for result in invalid:
            with self.assertRaises(ValueError):
                validate_cover_result(result)

    def test_forbidden_case_label_and_model_route_fields_are_absent(self):
        forbidden_keys = {
            "case", "case_id", "prompt", "corpus", "labels", "hidden_labels",
            "expected_decision_atoms", "expected_advisers", "expected_reference_triggers",
            "selected_decision_atoms", "routes", "authority", "effects", "claims",
        }

        def keys(value: Any) -> set[str]:
            found: set[str] = set()
            if isinstance(value, dict):
                for key, nested in value.items():
                    found.add(key)
                    found.update(keys(nested))
            elif isinstance(value, list):
                for nested in value:
                    found.update(keys(nested))
            return found

        self.assertFalse(forbidden_keys & keys(POLICY))
        self.assertNotIn("future-activation", POLICY_PATH.read_text())


if __name__ == "__main__":
    unittest.main()
