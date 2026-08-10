from __future__ import annotations

import json
import re
import unittest
import unicodedata
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "evals/foundation-v4/decision-certificate-protocol-v6.json"
SCHEMA_PATH = ROOT / "evals/foundation-v4/decision-certificate-selector-output-schema-v6.json"

PREDICATES = (
    "multi_domain_coordination", "cross_component_or_agent_boundary",
    "scope_acceptance_or_authority_contract", "execution_dependencies_or_stop_conditions",
    "claim_or_behavior_requires_verification_strategy", "oracle_or_evidence_adequacy_is_a_decision",
    "failure_attribution_or_adaptation_is_a_decision", "evaluation_or_knowledge_lifecycle_is_a_decision",
    "single_domain_native_execution_is_sufficient", "contract_is_already_complete_and_no_contract_decision_remains",
    "verification_method_is_already_fixed_and_no_verification_decision_remains", "no_learning_or_adaptation_decision_remains",
)
RULES = (
    ("topology-control-boundary", PREDICATES[:2], PREDICATES[8]),
    ("task-contract", PREDICATES[2:4], PREDICATES[9]),
    ("verification-strategy", PREDICATES[4:6], PREDICATES[10]),
    ("engineering-learning", PREDICATES[6:8], PREDICATES[11]),
)
PROTOCOL = json.loads(PROTOCOL_PATH.read_text())
CONSTRAINT = PROTOCOL["explicit_constraint"]
EXACT_TOKENS = {row["token"]: row["logical_atom"] for row in CONSTRAINT["ordered_token_to_logical_atom"]}
EXACT_PATTERN = re.compile(CONSTRAINT["qualified_invocation_grammar"]["exact_pattern"])
INVOCATION_LIKE_PATTERN = re.compile(CONSTRAINT["qualified_invocation_grammar"]["invocation_like_pattern"])


def facts(**states: str) -> dict:
    return {"predicate_facts": [{"predicate_id": predicate, "state": states.get(predicate, "absent")} for predicate in PREDICATES]}


def validate_selector_output(payload: object) -> None:
    if not isinstance(payload, dict) or set(payload) != {"predicate_facts"}:
        raise ValueError("closed top-level output required")
    rows = payload["predicate_facts"]
    if not isinstance(rows, list) or len(rows) != len(PREDICATES):
        raise ValueError("exactly twelve ordered facts required")
    for expected, row in zip(PREDICATES, rows):
        if not isinstance(row, dict) or set(row) != {"predicate_id", "state"}:
            raise ValueError("closed fact required")
        if row["predicate_id"] != expected or row["state"] not in {"present", "absent", "uncertain"}:
            raise ValueError("invalid ordered fact")


def parse_invocations(task: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFC", task)
    return tuple(match.group(0) for match in INVOCATION_LIKE_PATTERN.finditer(normalized))


def select(payload: object, task: str = "") -> dict:
    validate_selector_output(payload)
    invocation_tokens = parse_invocations(task)
    exact_tokens = tuple(match.group(0) for match in EXACT_PATTERN.finditer(unicodedata.normalize("NFC", task)))
    if any(token not in EXACT_TOKENS for token in invocation_tokens):
        return {"status": "selected", "selected_atoms": []}
    if len(exact_tokens) == 1:
        exact = [EXACT_TOKENS[exact_tokens[0]]]
        return {"status": "selected", "selected_atoms": exact}
    if len(exact_tokens) > 1:
        return {"status": "ambiguous", "selected_atoms": []}
    if invocation_tokens:
        return {"status": "selected", "selected_atoms": []}
    state = {row["predicate_id"]: row["state"] for row in payload["predicate_facts"]}
    selected = []
    for atom, positives, exclusion in RULES:
        relevant = (*positives, exclusion)
        if "uncertain" in {state[item] for item in relevant}:
            continue
        if any(state[item] == "present" for item in positives) and state[exclusion] == "absent":
            selected.append(atom)
    if len(selected) > 2:
        return {"status": "cap_exceeded", "selected_atoms": []}
    return {"status": "selected", "selected_atoms": selected}


class DecisionCertificateProtocolV6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = PROTOCOL
        cls.schema = json.loads(SCHEMA_PATH.read_text())

    def test_json_parse_and_schema_surface_are_closed(self):
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(set(self.schema["properties"]), {"predicate_facts"})
        facts_schema = self.schema["properties"]["predicate_facts"]
        self.assertEqual(len(facts_schema["prefixItems"]), 12)
        self.assertFalse(facts_schema["items"])
        self.assertEqual((facts_schema["minItems"], facts_schema["maxItems"]), (12, 12))
        valid = facts(multi_domain_coordination="present")
        self.assertEqual(list(Draft202012Validator(self.schema).iter_errors(valid)), [])
        validate_selector_output(valid)
        for invalid in (
            {"predicate_facts": valid["predicate_facts"], "extra": True},
            {"predicate_facts": valid["predicate_facts"][:-1]},
            {"predicate_facts": [{"predicate_id": PREDICATES[0], "state": "present", "extra": True}] + valid["predicate_facts"][1:]},
            {"predicate_facts": [{"predicate_id": "wrong", "state": "present"}] + valid["predicate_facts"][1:]},
        ):
            self.assertTrue(list(Draft202012Validator(self.schema).iter_errors(invalid)))
            with self.assertRaises(ValueError):
                validate_selector_output(invalid)

    def test_exact_predicate_order_and_uniqueness(self):
        self.assertEqual(tuple(self.protocol["predicate_order"]), PREDICATES)
        self.assertEqual(len(set(self.protocol["predicate_order"])), 12)
        self.assertEqual(tuple(item["derived_atom"] for item in self.protocol["deterministic_selection"]["eligibility_rules"]), tuple(rule[0] for rule in RULES))

    def test_automatic_exclusions_uncertainty_and_cap_are_deterministic(self):
        self.assertEqual(select(facts(multi_domain_coordination="present"))["selected_atoms"], ["topology-control-boundary"])
        self.assertEqual(select(facts(multi_domain_coordination="present", single_domain_native_execution_is_sufficient="present"))["selected_atoms"], [])
        self.assertEqual(select(facts(scope_acceptance_or_authority_contract="uncertain"))["selected_atoms"], [])
        capped = select(facts(multi_domain_coordination="present", scope_acceptance_or_authority_contract="present", claim_or_behavior_requires_verification_strategy="present"))
        self.assertEqual(capped, {"status": "cap_exceeded", "selected_atoms": []})

    def test_exact_and_ambiguous_constraints_override_or_withhold_selection(self):
        eligible = facts(multi_domain_coordination="present")
        self.assertEqual(select(eligible), {"status": "selected", "selected_atoms": ["topology-control-boundary"]})
        self.assertEqual(select(eligible, "Use $unknown."), {"status": "selected", "selected_atoms": []})
        excluded = facts(multi_domain_coordination="present", single_domain_native_execution_is_sufficient="present")
        self.assertEqual(select(excluded, "Use $codex-task-contract."), {"status": "selected", "selected_atoms": ["task-contract"]})
        self.assertEqual(select(excluded, "Use $codex-task-contract and $engineering-learning-loop."), {"status": "ambiguous", "selected_atoms": []})

    def test_frozen_grammar_and_mapping_cover_all_tokens_duplicates_and_mixed_tokens(self):
        self.assertEqual(EXACT_TOKENS, {
            "$agentic-engineering": "topology-control-boundary",
            "$codex-task-contract": "task-contract",
            "$verification-strategy-engineering": "verification-strategy",
            "$engineering-learning-loop": "engineering-learning",
        })
        self.assertEqual(tuple(EXACT_TOKENS), tuple(row["token"] for row in CONSTRAINT["ordered_token_to_logical_atom"]))
        for token, atom in EXACT_TOKENS.items():
            self.assertEqual(select(facts(), f"Use {token}."), {"status": "selected", "selected_atoms": [atom]})
        self.assertEqual(select(facts(), "Use $codex-task-contract twice: $codex-task-contract."), {"status": "ambiguous", "selected_atoms": []})
        self.assertEqual(select(facts(), "Use $codex-task-contract and $unknown."), {"status": "selected", "selected_atoms": []})
        self.assertEqual(select(facts(), "Use $codex-task-contract-extra."), {"status": "selected", "selected_atoms": []})

    def test_selector_schema_has_no_atom_adviser_or_route_fields(self):
        def property_names(value: object) -> set[str]:
            names = set()
            if isinstance(value, dict):
                for key, nested in value.items():
                    if key == "properties" and isinstance(nested, dict): names.update(nested)
                    names.update(property_names(nested))
            elif isinstance(value, list):
                for nested in value: names.update(property_names(nested))
            return names
        names = property_names(self.schema)
        self.assertFalse({"atom", "atoms", "adviser", "advisers", "route", "routes"} & names)
        self.assertEqual(self.protocol["model_output_contract"]["model_must_not_output"][:3], ["atoms", "advisers", "routes"])

    def test_protocol_records_non_replay_blinding_schedule_and_ceiling(self):
        controls = self.protocol["qualification_controls"]
        self.assertTrue(controls["aq5_g_no_replay"])
        self.assertFalse(controls["outcome_tuned"])
        self.assertTrue(controls["fresh_blinded_corpus_required"])
        self.assertEqual(controls["authorized_observation_schedule"], "one_canary_then_one_batch")
        self.assertEqual(self.protocol["claim_ceiling"], "structural-proposal-only")


if __name__ == "__main__":
    unittest.main()
