"""Synthetic and adversarial tests for the closed AQ8 scorer/schema lane."""
from __future__ import annotations

import copy
import json
import os
import pickle
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import resolve_h4_unresolved_decision_graph_v8 as resolver  # noqa: E402
import score_activation_v8 as scorer  # noqa: E402


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def replace_placeholders(value: object) -> object:
    if isinstance(value, dict):
        return {key: replace_placeholders(item) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_placeholders(item) for item in value]
    if isinstance(value, str) and value.startswith("__AQ8_"):
        return ("8" * 40) if value.endswith("COMMIT__") else (("7" * 40) if value.endswith("TREE__") else ("9" * 64))
    return value


def reclose_public_result(result: dict) -> None:
    """Recompute every public field derived from aggregate counts."""
    for condition in result["conditions"]:
        metrics, defined, gates = scorer._semantics(condition["counts"], scorer.PER_CONDITION_GATES)
        condition["metrics"] = metrics
        condition["defined"] = defined
        condition["gates"] = gates
        condition["status"] = "pass" if all(gates.values()) else "fail"
    complete = result["complete_run"]
    metrics, defined, gates = scorer._semantics(complete["counts"], scorer.COMPLETE_RUN_GATES)
    complete["metrics"] = metrics
    complete["defined"] = defined
    complete["gates"] = gates
    complete["status"] = "pass" if all(gates.values()) else "fail"
    result["status"] = (
        "pass"
        if all(condition["status"] == "pass" for condition in result["conditions"])
        and complete["status"] == "pass"
        else "fail"
    )
    result["runner_local_raw_trajectories_persisted"] = complete["metrics"]["runner_local_raw_persistence"]
    body = {
        key: result[key]
        for key in (
            "binding_digest",
            "execution_digest",
            "schedule_digest",
            "metric_authority_digest",
            "conditions",
            "complete_run",
        )
    }
    result["aggregate_digest"] = scorer._digest(body)


class ActivationEvaluatorV8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = load("evals/foundation-v4/unresolved-decision-graph-protocol-v8.json")
        cls.selector = load("evals/foundation-v4/unresolved-decision-graph-selector-output-schema-v8.json")
        cls.policy = load("evals/foundation-v4/unresolved-decision-graph-reference-policy-v8.json")
        cls.base = load("evals/foundation-v4/reduced-four-skills/candidate.json")
        cls.adapter = load("evals/foundation-v4/unresolved-decision-graph-condition-adapter-v8.json")
        cls.authoring = load("evals/foundation-v4/future-activation-v8/activation-authoring.json")
        cls.heldout = load("evals/foundation-v4/future-activation-v8/activation-heldout.json")
        cls.metrics = load("evals/foundation-v4/unresolved-decision-graph-metrics-v8.json")
        cls.gates = load("evals/foundation-v4/unresolved-decision-graph-gates-v8.json")

    def profile_and_envelope(self) -> tuple[dict, dict]:
        manifest = replace_placeholders(load("evals/foundation-v4/decision-certificate-candidate-v8.json"))
        assert isinstance(manifest, dict)
        qualified = tuple(
            [case["case_id"] for case in self.heldout["cases"][:32]]
            + [case["case_id"] for document in (self.authoring, self.heldout) for case in document["cases"][32:]]
        )
        profile = {
            "candidate_commit": "a" * 40,
            "tree": "b" * 40,
            "digest": "c" * 64,
            "manifest": manifest,
            "protocol": copy.deepcopy(self.protocol),
            "selector_schema": copy.deepcopy(self.selector),
            "runtime_selector_schema": load("evals/foundation-v4/unresolved-decision-graph-runtime-output-schema-v8.json"),
            "reference_policy": copy.deepcopy(self.policy),
            "base_manifest": copy.deepcopy(self.base),
            "adapter": copy.deepcopy(self.adapter),
            "gate_authority": copy.deepcopy(self.gates),
            "metric_authority": copy.deepcopy(self.metrics),
            "corpus_schema": load("evals/foundation-v4/future-activation-v8/activation-schema.json"),
            "authoring": copy.deepcopy(self.authoring),
            "heldout": copy.deepcopy(self.heldout),
            "qualified_cases": qualified,
            "qualified_ids": qualified,
            "execution_contract": copy.deepcopy(manifest["execution_contract"]),
        }
        plan = scorer.build_schedule(qualified, scorer.SCHEDULE_SEED)
        digest = scorer.schedule_digest(plan)
        by_id = {case["case_id"]: case for document in (profile["authoring"], profile["heldout"]) for case in document["cases"]}
        def identity(row: dict) -> dict:
            return {"commit": row["commit"], "tree": row["tree"], "digest": row["sha256"]}
        surface = {row["role"]: row for row in manifest["evaluator_surface"]["files"]}
        binding = {
            "protocol": identity(manifest["protocol_authority"]),
            "reference_policy": identity(manifest["reference_policy_authority"]),
            "corpus": identity(manifest["corpus_authority"]),
            "candidate": {"commit": profile["candidate_commit"], "tree": profile["tree"], "digest": profile["digest"]},
            "runner": {"commit": profile["candidate_commit"], "tree": profile["tree"], "digest": surface["runner"]["sha256"]},
            "evaluator": {"commit": profile["candidate_commit"], "tree": profile["tree"], "digest": surface["scorer"]["sha256"]},
            "validator": identity(manifest["validator_authority"]),
            "cli": {"id": "zero-model", "digest": "d" * 64},
            "model": {"id": scorer.MODEL, "digest": "e" * 64},
            "reasoning": {"id": scorer.REASONING, "digest": "f" * 64},
            "tools": {"digest": "0" * 64},
            "host": {"digest": "1" * 64},
            "schedule": {"seed": scorer.SCHEDULE_SEED, "digest": digest},
        }
        grouped = {name: [] for name in scorer.CONDITIONS}
        execution_digest = scorer._profile_execution_digest(profile)
        for item in plan:
            condition, case = item["condition"], by_id[item["case_id"]]
            semantic = copy.deepcopy(case["expected_semantic_output"])
            parent = resolver.resolve_graph(case["task_text"], semantic, profile["protocol"], profile["reference_policy"], profile["base_manifest"])
            grouped[condition].append({
                "case_id": case["case_id"], "presentation_index": item["presentation_index"],
                "context_id": f"ctx-{item['presentation_index']}", "terminal_completed": True,
                "case_sha256": case["task_text_nfc_sha256"], "task_sha256": case["task_text_nfc_sha256"],
                "packet_sha256": scorer._packet_digest(profile, condition, case),
                "condition_sha256": scorer._condition_digest(profile, condition),
                "execution_sha256": execution_digest, "runner_sha256": binding["runner"]["digest"],
                "parse_status": "parsed", "semantic_output": semantic, "parent_derivation": parent,
                "events": {name: False for name in scorer.EVENT_KEYS},
            })
        envelope = {
            "schema_version": "8.0", "evaluation_mode": "qualification", "provenance_mode": "synthetic",
            "binding": binding, "execution_contract": profile["execution_contract"],
            "schedule": {"seed": scorer.SCHEDULE_SEED, "digest": digest, "presentations": list(plan)},
            "complete_run_assertions": {
                "runner_local_raw_persistence": False, "runner_local_raw_persistence_corroborated": True,
                "held_out_outcome_use": False, "held_out_outcome_use_corroborated": True,
            },
            "conditions": [{"id": name, "digest": scorer._condition_digest(profile, name), "observations": grouped[name]} for name in scorer.CONDITIONS],
        }
        return profile, envelope

    def test_full_exact_projection_passes_synthetic_and_live(self) -> None:
        profile, envelope = self.profile_and_envelope()
        result = scorer.score_synthetic(envelope, profile)
        self.assertEqual("pass", result["status"], result)
        self.assertIs(result, scorer.validate_result(result))
        live = scorer.create_live_score_session(profile, envelope["binding"])
        observed = copy.deepcopy(envelope)
        observed["provenance_mode"] = "live_runner"
        self.assertEqual("pass", live.score(observed)["status"])

    def test_completed_fully_malformed_batch_is_fail_not_insufficient(self) -> None:
        profile, envelope = self.profile_and_envelope()
        for condition in envelope["conditions"]:
            for row in condition["observations"]:
                row["parse_status"] = "malformed"
                row["semantic_output"] = None
                row["parent_derivation"] = None
        result = scorer.score_synthetic(envelope, profile)
        self.assertEqual("fail", result["status"])
        self.assertTrue(all(not condition["gates"]["graph_validity"] for condition in result["conditions"]))
        self.assertTrue(result["complete_run"]["gates"]["presentations_80_of_80"])

    def test_missing_duplicate_and_nonterminal_completed_cells_are_scored_fail(self) -> None:
        for mutation in ("missing", "duplicate", "nonterminal"):
            profile, envelope = self.profile_and_envelope()
            if mutation == "missing":
                envelope["conditions"][0]["observations"].pop()
            elif mutation == "duplicate":
                envelope["conditions"][0]["observations"][-1] = copy.deepcopy(envelope["conditions"][0]["observations"][0])
            else:
                envelope["conditions"][0]["observations"][0]["terminal_completed"] = False
            result = scorer.score_synthetic(envelope, profile)
            self.assertEqual("fail", result["status"], mutation)
            self.assertFalse(result["complete_run"]["gates"]["presentations_80_of_80"], mutation)

    def test_duplicate_context_row_custody_and_parent_forgery_have_independent_reds(self) -> None:
        profile, envelope = self.profile_and_envelope()
        changed = copy.deepcopy(envelope)
        changed["conditions"][1]["observations"][0]["context_id"] = changed["conditions"][0]["observations"][0]["context_id"]
        result = scorer.score_synthetic(changed, profile)
        self.assertEqual("fail", result["status"])
        self.assertFalse(result["complete_run"]["gates"]["unique_context_ids"])
        changed = copy.deepcopy(envelope)
        changed["conditions"][0]["observations"][0]["packet_sha256"] = "9" * 64
        self.assertFalse(scorer.score_synthetic(changed, profile)["complete_run"]["gates"]["binding_schedule_packet_parity"])
        changed = copy.deepcopy(envelope)
        changed["conditions"][0]["observations"][0]["parent_derivation"]["selected_slots"] = []
        self.assertFalse(scorer.score_synthetic(changed, profile)["complete_run"]["gates"]["resolver_parity"])

    def test_complete_run_boolean_assertions_are_noncompensatory_and_corroborated(self) -> None:
        for field in ("runner_local_raw_persistence", "held_out_outcome_use"):
            profile, envelope = self.profile_and_envelope()
            envelope["complete_run_assertions"][field] = True
            result = scorer.score_synthetic(envelope, profile)
            self.assertEqual("fail", result["status"])
            self.assertFalse(result["complete_run"]["gates"][field])
        for field, gate in (("runner_local_raw_persistence_corroborated", "runner_local_raw_persistence"), ("held_out_outcome_use_corroborated", "held_out_outcome_use")):
            profile, envelope = self.profile_and_envelope()
            envelope["complete_run_assertions"][field] = False
            self.assertFalse(scorer.score_synthetic(envelope, profile)["complete_run"]["gates"][gate])

    def test_every_formula_has_a_direct_noncompensatory_red_and_zero_denominators_fail(self) -> None:
        profile, envelope = self.profile_and_envelope()
        result = scorer.score_synthetic(envelope, profile)
        for condition_gate in scorer.PER_CONDITION_GATES:
            counts = copy.deepcopy(result["conditions"][0]["counts"])
            kind, operator, _ = scorer._SPECS[condition_gate]
            if kind == "ratio":
                if operator == "<=":
                    counts[condition_gate] = {"numerator": 1, "denominator": 1}
                elif operator == "==":
                    counts[condition_gate] = {"numerator": 0, "denominator": max(1, counts[condition_gate]["denominator"])}
                else:
                    counts[condition_gate] = {"numerator": 0, "denominator": max(1, counts[condition_gate]["denominator"])}
            else:
                counts[condition_gate] = {"numerator": 1, "denominator": None}
            self.assertFalse(scorer._semantics(counts, scorer.PER_CONDITION_GATES)[2][condition_gate], condition_gate)
        for complete_gate in scorer.COMPLETE_RUN_GATES:
            counts = copy.deepcopy(result["complete_run"]["counts"])
            kind = scorer._SPECS[complete_gate][0]
            if kind == "ratio":
                counts[complete_gate] = {"numerator": 79, "denominator": 80}
            elif kind == "count":
                counts[complete_gate] = {"numerator": 79, "denominator": None}
            else:
                counts[complete_gate] = {"value": True, "corroborated": True}
            self.assertFalse(scorer._semantics(counts, scorer.COMPLETE_RUN_GATES)[2][complete_gate], complete_gate)
        counts = copy.deepcopy(result["conditions"][0]["counts"])
        for gate in ("directed_control_precision", "directed_control_recall", "independent_relation_accuracy", "precision", "recall"):
            changed = copy.deepcopy(counts)
            changed[gate] = {"numerator": 0, "denominator": 0}
            metrics, defined, gates = scorer._semantics(changed, scorer.PER_CONDITION_GATES)
            self.assertEqual("0/1", metrics[gate])
            self.assertFalse(defined[gate])
            self.assertFalse(gates[gate])

    def test_exact_boundary_comparisons_use_rational_arithmetic(self) -> None:
        profile, envelope = self.profile_and_envelope()
        base = scorer.score_synthetic(envelope, profile)["conditions"][0]["counts"]
        cases = {
            "candidate_state_accuracy": ({"numerator": 19, "denominator": 20}, {"numerator": 18, "denominator": 20}),
            "directed_control_recall": ({"numerator": 9, "denominator": 10}, {"numerator": 8, "denominator": 10}),
            "broad_router_over_selection": ({"numerator": 1, "denominator": 20}, {"numerator": 2, "denominator": 20}),
        }
        for gate, (passing, failing) in cases.items():
            at = copy.deepcopy(base)
            at[gate] = passing
            below = copy.deepcopy(base)
            below[gate] = failing
            self.assertTrue(scorer._semantics(at, scorer.PER_CONDITION_GATES)[2][gate], gate)
            self.assertFalse(scorer._semantics(below, scorer.PER_CONDITION_GATES)[2][gate], gate)

    def test_directed_reversal_is_simultaneously_false_positive_and_false_negative(self) -> None:
        profile, envelope = self.profile_and_envelope()
        target = None
        for condition in envelope["conditions"]:
            for row in condition["observations"]:
                relations = row["semantic_output"]["pairwise_relations"]
                index = next((i for i, item in enumerate(relations) if "controls" in item["relation"]), None)
                if index is not None:
                    target = row
                    relation = relations[index]["relation"]
                    relations[index]["relation"] = "right_controls_left_downstream" if relation == "left_controls_right_downstream" else "left_controls_right_downstream"
                    for need in row["semantic_output"]["reference_needs"]:
                        need["need"] = "none"
                    row["parent_derivation"] = resolver.resolve_graph(
                        next(case["task_text"] for document in (profile["authoring"], profile["heldout"]) for case in document["cases"] if case["case_id"] == row["case_id"]),
                        row["semantic_output"], profile["protocol"], profile["reference_policy"], profile["base_manifest"],
                    )
                    break
            if target is not None:
                break
        self.assertIsNotNone(target)
        result = scorer.score_synthetic(envelope, profile)
        condition = next(item for item in result["conditions"] if target in next(group["observations"] for group in envelope["conditions"] if group["id"] == item["id"]))
        self.assertGreater(condition["counts"]["directed_control_precision"]["denominator"] - condition["counts"]["directed_control_precision"]["numerator"], 0)
        self.assertGreater(condition["counts"]["directed_control_recall"]["denominator"] - condition["counts"]["directed_control_recall"]["numerator"], 0)

    def test_independent_accuracy_is_binary_over_all_240_pair_rows(self) -> None:
        profile, envelope = self.profile_and_envelope()
        target = None
        for condition in envelope["conditions"]:
            for row in condition["observations"]:
                relation = next(
                    (item for item in row["semantic_output"]["pairwise_relations"] if item["relation"] == "unrelated"),
                    None,
                )
                if relation is not None:
                    relation["relation"] = "independent"
                    for need in row["semantic_output"]["reference_needs"]:
                        need["need"] = "none"
                    target = condition["id"]
                    break
            if target is not None:
                break
        self.assertIsNotNone(target)
        result = scorer.score_synthetic(envelope, profile)
        condition = next(item for item in result["conditions"] if item["id"] == target)
        self.assertEqual(240, condition["counts"]["independent_relation_accuracy"]["denominator"])
        self.assertEqual(239, condition["counts"]["independent_relation_accuracy"]["numerator"])

    def test_binding_schedule_execution_and_formula_authority_drift_are_insufficient(self) -> None:
        profile, envelope = self.profile_and_envelope()
        mutations = []
        changed = copy.deepcopy(envelope)
        changed["binding"]["candidate"]["digest"] = "9" * 64
        mutations.append((profile, changed))
        changed = copy.deepcopy(envelope)
        changed["schedule"]["digest"] = "9" * 64
        mutations.append((profile, changed))
        changed = copy.deepcopy(envelope)
        changed["execution_contract"]["integrity"]["content_retries"] = 1
        mutations.append((profile, changed))
        changed_profile = copy.deepcopy(profile)
        changed_profile["metric_authority"]["gate_formulas"][0]["boundary"] = 0.5
        mutations.append((changed_profile, envelope))
        for candidate_profile, candidate_envelope in mutations:
            self.assertEqual("insufficient_data", scorer.score_synthetic(candidate_envelope, candidate_profile)["status"])

    def test_formula_authorities_require_exact_type_strict_bound_bytes(self) -> None:
        profile, envelope = self.profile_and_envelope()
        mutations = {}
        changed = copy.deepcopy(profile)
        changed["metric_authority"]["gate_formulas"][0]["calculation"]["value_kind"] = "count"
        mutations["value_kind"] = changed
        changed = copy.deepcopy(profile)
        changed["metric_authority"]["gate_formulas"][0]["denominator"]["fixed_value"] = 1
        mutations["fixed_denominator"] = changed
        changed = copy.deepcopy(profile)
        changed["metric_authority"]["gate_formulas"][0]["semantic_contract"]["denominator_algebra"] = "caller_selected"
        mutations["semantic_algebra"] = changed
        changed = copy.deepcopy(profile)
        changed["metric_authority"]["gate_formulas"][0]["denominator"]["must_be_positive"] = 1
        mutations["bool_as_int"] = changed
        changed = copy.deepcopy(profile)
        changed["metric_authority"]["status"] = "mutable"
        mutations["metric_top_level"] = changed
        changed = copy.deepcopy(profile)
        changed["gate_authority"]["status"] = "mutable"
        mutations["gate_top_level"] = changed
        for name, changed_profile in mutations.items():
            with self.subTest(name=name):
                self.assertEqual("insufficient_data", scorer.score_synthetic(envelope, changed_profile)["status"])

    def test_every_isolation_contract_field_is_exact_and_noncompensatory(self) -> None:
        profile, envelope = self.profile_and_envelope()
        replacements = {
            "fresh_empty_cwd": False,
            "ephemeral_context_requested": False,
            "sandbox": "workspace-write",
            "approval_policy": "on-request",
            "tools_enabled": True,
            "apps_enabled": True,
            "plugins_enabled": True,
            "mcp_enabled": True,
            "isolated_codex_home": False,
            "isolated_home_mode": "0755",
            "auth_source": "ambient",
            "auth_seed": "symlink",
            "explicit_subprocess_env": False,
            "exact_single_probe_input": False,
            "temp_cleanup_required": False,
            "global_agents_loaded": True,
        }
        self.assertEqual(list(replacements), list(envelope["execution_contract"]["isolation"]))
        for field, replacement in replacements.items():
            changed = copy.deepcopy(envelope)
            changed["execution_contract"]["isolation"][field] = replacement
            self.assertEqual(
                "insufficient_data",
                scorer.score_synthetic(changed, profile)["status"],
                field,
            )

    def test_result_metrics_gates_counts_digest_and_claims_are_closed(self) -> None:
        profile, envelope = self.profile_and_envelope()
        result = scorer.score_synthetic(envelope, profile)
        mutations = []
        changed = copy.deepcopy(result)
        changed["conditions"][0]["metrics"]["graph_validity"] = "0/1"
        mutations.append(changed)
        changed = copy.deepcopy(result)
        changed["conditions"][0]["gates"]["graph_validity"] = False
        mutations.append(changed)
        changed = copy.deepcopy(result)
        changed["conditions"][0]["counts"]["graph_validity"]["numerator"] = 39
        mutations.append(changed)
        changed = copy.deepcopy(result)
        changed["aggregate_digest"] = "0" * 64
        mutations.append(changed)
        changed = copy.deepcopy(result)
        changed["promotion_eligible"] = True
        mutations.append(changed)
        changed = copy.deepcopy(result)
        changed["conditions"][0]["raw_case"] = "forbidden"
        mutations.append(changed)
        for changed in mutations:
            with self.assertRaises(scorer.EvaluationError):
                scorer.validate_result(changed)

    def test_independent_fixed_denominator_rejects_self_consistent_forgery(self) -> None:
        profile, envelope = self.profile_and_envelope()
        result = scorer.score_synthetic(envelope, profile)
        forged = copy.deepcopy(result)
        forged["conditions"][0]["counts"]["independent_relation_accuracy"] = {
            "numerator": 1,
            "denominator": 1,
        }
        reclose_public_result(forged)
        self.assertEqual("pass", forged["status"])
        self.assertNotEqual(result["aggregate_digest"], forged["aggregate_digest"])
        with self.assertRaisesRegex(scorer.EvaluationError, "bound condition denominator"):
            scorer.validate_result(forged)

    def test_all_other_fixed_and_cohort_denominators_reject_self_consistent_forgery(self) -> None:
        profile, envelope = self.profile_and_envelope()
        result = scorer.score_synthetic(envelope, profile)
        expected_condition_denominators = {
            "graph_validity": 40,
            "candidate_state_accuracy": 160,
            "directed_control_recall": 36,
            "independent_relation_accuracy": 240,
            "exact_root_set": 38,
            "uncertainty_abstention": 2,
            "cap_abstention": 2,
            "recall": 40,
            "native_abstention": 2,
            "broad_router_over_selection": 24,
            "exactly_two_exact_set": 6,
            "explicit_invocation": 8,
            "reference_correctness": 40,
        }
        self.assertEqual(expected_condition_denominators, scorer._BOUND_CONDITION_DENOMINATORS)
        for gate_id in expected_condition_denominators:
            if gate_id == "independent_relation_accuracy":
                continue
            with self.subTest(scope="condition", gate=gate_id):
                forged = copy.deepcopy(result)
                counts = forged["conditions"][0]["counts"]
                numerator = 0 if gate_id == "broad_router_over_selection" else 1
                counts[gate_id] = {"numerator": numerator, "denominator": 1}
                if gate_id == "directed_control_recall":
                    counts["directed_control_precision"] = {"numerator": 1, "denominator": 1}
                elif gate_id == "recall":
                    counts["precision"] = {"numerator": 1, "denominator": 1}
                reclose_public_result(forged)
                self.assertEqual("pass", forged["status"])
                with self.assertRaisesRegex(scorer.EvaluationError, "bound condition denominator"):
                    scorer.validate_result(forged)

        expected_complete_denominators = {
            "semantic_schema_order": 80,
            "resolver_parity": 80,
            "binding_schedule_packet_parity": 80,
        }
        self.assertEqual(expected_complete_denominators, scorer._BOUND_COMPLETE_DENOMINATORS)
        for gate_id in expected_complete_denominators:
            with self.subTest(scope="complete", gate=gate_id):
                forged = copy.deepcopy(result)
                forged["complete_run"]["counts"][gate_id] = {"numerator": 1, "denominator": 1}
                reclose_public_result(forged)
                self.assertEqual("pass", forged["status"])
                with self.assertRaisesRegex(scorer.EvaluationError, "bound complete-run denominator"):
                    scorer.validate_result(forged)

    def test_must_not_select_rejects_impossible_self_consistent_count_above_eighty(self) -> None:
        profile, envelope = self.profile_and_envelope()
        forged = copy.deepcopy(scorer.score_synthetic(envelope, profile))
        forged["conditions"][0]["counts"]["must_not_select"]["numerator"] = 81
        reclose_public_result(forged)
        self.assertEqual("fail", forged["status"])
        with self.assertRaisesRegex(scorer.EvaluationError, "violation count"):
            scorer.validate_result(forged)

    @unittest.skipUnless(hasattr(os, "fork"), "requires POSIX fork")
    def test_live_witness_rejects_fork_copy_pickle_and_binding_drift(self) -> None:
        profile, envelope = self.profile_and_envelope()
        session = scorer.create_live_score_session(profile, envelope["binding"])
        with self.assertRaises(TypeError):
            pickle.dumps(session)
        with self.assertRaises(TypeError):
            copy.copy(session)
        with self.assertRaises(TypeError):
            copy.deepcopy(session)
        wrong = copy.deepcopy(envelope)
        wrong["provenance_mode"] = "live_runner"
        wrong["binding"]["host"]["digest"] = "9" * 64
        self.assertEqual("insufficient_data", session.score(wrong)["status"])
        read_fd, write_fd = os.pipe()
        child = os.fork()
        if child == 0:
            os.close(read_fd)
            observed = copy.deepcopy(envelope)
            observed["provenance_mode"] = "live_runner"
            os.write(write_fd, session.score(observed)["status"].encode("ascii"))
            os.close(write_fd)
            os._exit(0)
        os.close(write_fd)
        observed = os.read(read_fd, 64).decode("ascii")
        os.close(read_fd)
        os.waitpid(child, 0)
        self.assertEqual("insufficient_data", observed)

    def test_public_entrypoint_rejects_live_and_schema_is_closed(self) -> None:
        result = scorer.score_synthetic({"provenance_mode": "live_runner"}, {})
        self.assertEqual("insufficient_data", result["status"])
        profile, envelope = self.profile_and_envelope()
        envelope["extra"] = False
        self.assertEqual("insufficient_data", scorer.score_synthetic(envelope, profile)["status"])


if __name__ == "__main__":
    unittest.main()
