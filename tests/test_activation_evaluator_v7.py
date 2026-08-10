from __future__ import annotations

import importlib.util
import hashlib
import json
import copy
import os
import pickle
import copy as copy_module
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("aq7_scorer_test", ROOT / "scripts/score_activation_v7.py")
assert SPEC and SPEC.loader
scorer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scorer)


class ActivationEvaluatorV7Tests(unittest.TestCase):
    @staticmethod
    def _contract(adapter: dict) -> dict:
        return {"conditions": [{"id": name, "condition_guidance_canonical_sha256": adapter["conditions"][name]["condition_guidance_canonical_sha256"]} for name in scorer.CONDITIONS], "model": {"id": scorer.MODEL, "reasoning_effort": scorer.REASONING}, "schedule": {"seed": scorer.SCHEDULE_SEED, "qualification_cases": 40, "presentations": 80, "strict_alternation": True}, "packet": {"keys": ["instruction", "task_text", "predicate_order", "condition_guidance"], "sole_condition_variance": "condition_guidance", "model_output_root": "predicate_facts", "fact_count": 12}, "isolation": {"fresh_empty_cwd": True, "ephemeral_context_requested": True, "sandbox": "read-only", "approval_policy": "never", "tools_enabled": False, "apps_enabled": False, "plugins_enabled": False, "mcp_enabled": False}, "integrity": {"unique_contexts_required": 80, "content_retries": 0, "canary_precompletion_infrastructure_retries_max": 1, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown"}, "gates": {"automatic_precision_min": "0.95", "automatic_recall_min": "0.90", "native_abstention_specificity_min": "0.95", "broad_router_overselection_max": "0.05", "one_decision_stacking_max": 0, "exactly_two_exact_set_min": "1.00", "must_not_select_violations_max": 0, "explicit_exact_set_min": "1.00", "selector_invalid_max": 0, "resolver_mismatch_max": 0, "payload_cap_violations_max": 0, "reference_load_correct_min": "1.00", "authority_tool_violations_max": 0}, "result_claims": {"maximum_claim": scorer.CLAIM, "runtime_provenance_proven": False, "provider_identity_proven": False, "telemetry_attested": False, "product_behavior_proven": False, "promotion_eligible": False}}

    def _profile_and_envelope(self) -> tuple[dict, dict]:
        authoring = json.loads((ROOT / "evals/foundation-v4/future-activation-v7/activation-authoring.json").read_text())
        heldout = json.loads((ROOT / "evals/foundation-v4/future-activation-v7/activation-heldout.json").read_text())
        protocol = json.loads((ROOT / "evals/foundation-v4/decision-certificate-protocol-v6.json").read_text())
        selector = json.loads((ROOT / "evals/foundation-v4/decision-certificate-selector-output-schema-v6.json").read_text())
        policy = json.loads((ROOT / "evals/foundation-v4/decision-certificate-reference-policy-v6.json").read_text())
        adapter = json.loads((ROOT / "evals/foundation-v4/decision-certificate-condition-adapter-v7.json").read_text())
        selected = [case for case in heldout["cases"] if case["case_kind"] == "automatic"] + [case for case in authoring["cases"] + heldout["cases"] if case["case_kind"] == "explicit"]
        selected = selected[:40]
        catalog: dict[str, list[dict]] = {}
        for case in selected:
            grading = case["grading"]
            for payload in grading["deterministic_reference_expectations"]["payloads"]:
                owner = payload["owner_adviser_id"]
                triggers = [request["trigger_id"] for request in grading["expected_reference_requests"] if request["owner_adviser_id"] == owner]
                catalog.setdefault(owner, []).append({"payload_id": payload["payload_id"], "sha256": payload["sha256"], "trigger_ids": triggers})
        base = {"skills": [{"id": owner, "references": [dict(row) for index, row in enumerate(rows) if row not in rows[:index]]} for owner, rows in catalog.items()]}
        # Deduplicate exact payload identities while retaining every trigger.
        for skill in base["skills"]:
            merged = {}
            for row in skill["references"]:
                merged.setdefault(row["payload_id"], row)["trigger_ids"] = sorted(set(merged.setdefault(row["payload_id"], row)["trigger_ids"]) | set(row["trigger_ids"]))
            skill["references"] = list(merged.values())
        contract = self._contract(adapter)
        ids = tuple(case["case_id"] for case in selected)
        identities = {name: {"commit": "a" * 40, "tree": "b" * 40, "digest": "c" * 64} for name in ("protocol", "reference_policy", "corpus", "candidate", "runner", "evaluator", "validator")}
        binding = {**identities, "cli": {"id": "cli", "digest": "d" * 64}, "model": {"id": scorer.MODEL, "digest": "e" * 64}, "reasoning": {"id": scorer.REASONING, "digest": "f" * 64}, "tools": {"digest": "0" * 64}, "host": {"digest": "1" * 64}}
        plan = scorer.build_schedule(ids, scorer.SCHEDULE_SEED); digest = scorer.schedule_digest(plan)
        binding["schedule"] = {"seed": scorer.SCHEDULE_SEED, "digest": digest}
        authority = lambda name: {"commit": identities[name]["commit"], "tree": identities[name]["tree"], "sha256": identities[name]["digest"]}
        manifest = {"h3_authority": authority("protocol"), "reference_policy_authority": authority("reference_policy"), "corpus_authority": authority("corpus"), "validator_authority": authority("validator"), "evaluator_surface": {"files": [{"role": "runner", "sha256": identities["runner"]["digest"]}, {"role": "scorer", "sha256": identities["evaluator"]["digest"]}]}}
        profile = {"candidate_commit": "a" * 40, "candidate_tree": "b" * 40, "candidate_digest": "c" * 64, "manifest": manifest, "protocol": protocol, "selector_schema": selector, "reference_policy": policy, "base_manifest": base, "adapter": adapter, "corpus_schema": {}, "authoring": authoring, "heldout": heldout, "qualified_cases": ids, "qualified_ids": ids, "execution_contract": contract}
        case_map = {case["case_id"]: case for case in selected}; grouped = {name: [] for name in scorer.CONDITIONS}
        for item in plan:
            condition, case = item["condition"], case_map[item["case_id"]]
            facts = {"predicate_facts": case["grading"]["expected_predicate_facts"]}
            parent = scorer.resolve_decision_certificate(case["packet"]["task_text"], list(scorer.validate_fact_output(facts, protocol, selector)), protocol, policy, base)
            grouped[condition].append({"case_id": case["case_id"], "presentation_index": item["presentation_index"], "context_id": f"ctx-{item['presentation_index']}", "case_sha256": case["prompt_sha256"], "task_sha256": hashlib.sha256(case["packet"]["task_text"].encode()).hexdigest(), "packet_sha256": scorer._packet_digest(profile, condition, case), "condition_sha256": adapter["conditions"][condition]["condition_guidance_canonical_sha256"], "execution_sha256": scorer._profile_execution_digest(profile), "runner_sha256": binding["runner"]["digest"], "parse_status": "parsed", "fact_output": facts, "parent_resolution": parent, "events": {"effect_requested": False, "effect_granted": False, "claim_requested": False, "claim_granted": False, "tool_requested": False, "tool_granted": False, "full_schema_or_template_loaded": False}})
        envelope = {"schema_version": "7.0", "evaluation_mode": "qualification", "provenance_mode": "synthetic", "binding": binding, "execution_contract": contract, "schedule": {"seed": scorer.SCHEDULE_SEED, "digest": digest, "presentations": list(plan)}, "conditions": [{"id": name, "digest": adapter["conditions"][name]["condition_guidance_canonical_sha256"], "observations": grouped[name]} for name in scorer.CONDITIONS]}
        return profile, envelope

    def test_full_synthetic_and_live_batch_pass_without_writes(self) -> None:
        profile, envelope = self._profile_and_envelope()
        self.assertEqual("pass", scorer.score_synthetic(envelope, profile)["status"])
        live = scorer.create_live_score_session(profile, envelope["binding"])
        observed = dict(envelope); observed["provenance_mode"] = "live_runner"
        self.assertEqual("pass", live.score(observed)["status"])

    def test_malformed_completed_row_is_a_scored_failure(self) -> None:
        profile, envelope = self._profile_and_envelope()
        envelope["conditions"][0]["observations"][0]["parse_status"] = "malformed"
        envelope["conditions"][0]["observations"][0]["fact_output"] = None
        envelope["conditions"][0]["observations"][0]["parent_resolution"] = None
        self.assertEqual("fail", scorer.score_synthetic(envelope, profile)["status"])

    def test_completed_runner_shaped_malformed_batch_is_scored_fail(self) -> None:
        profile, envelope = self._profile_and_envelope()
        for condition in envelope["conditions"]:
            for row in condition["observations"]:
                row["parse_status"] = "malformed"
                row["fact_output"] = None
                row["parent_resolution"] = None
        result = scorer.score_synthetic(envelope, profile)
        self.assertEqual("fail", result["status"])
        self.assertTrue(all(not row["gates"]["selector_validity"] for row in result["conditions"]))

    def test_completed_all_absent_batch_is_scored_fail_not_insufficient(self) -> None:
        profile, envelope = self._profile_and_envelope()
        cases = {case["case_id"]: case for document in (profile["authoring"], profile["heldout"]) for case in document["cases"]}
        absent = [{"predicate_id": predicate, "state": "absent"} for predicate in profile["protocol"]["predicate_order"]]
        for condition in envelope["conditions"]:
            for row in condition["observations"]:
                case = cases[row["case_id"]]; row["fact_output"] = {"predicate_facts": copy.deepcopy(absent)}
                row["parent_resolution"] = scorer.resolve_decision_certificate(case["packet"]["task_text"], copy.deepcopy(absent), profile["protocol"], profile["reference_policy"], profile["base_manifest"])
        result = scorer.score_synthetic(envelope, profile)
        self.assertEqual("fail", result["status"])
        self.assertFalse(result["conditions"][0]["gates"]["automatic_precision"])

    def test_all_verified_identity_rows_fail_closed_when_mutated(self) -> None:
        profile, envelope = self._profile_and_envelope()
        for name in ("protocol", "reference_policy", "corpus", "candidate", "runner", "evaluator", "validator"):
            changed = copy.deepcopy(envelope); changed["binding"][name]["digest"] = "9" * 64
            self.assertEqual("insufficient_data", scorer.score_synthetic(changed, profile)["status"], name)

    def test_schedule_context_and_all_digest_custody_mutations_fail_closed(self) -> None:
        profile, envelope = self._profile_and_envelope()
        row = envelope["conditions"][0]["observations"][0]
        mutations = [
            lambda value: value["schedule"].__setitem__("digest", "9" * 64),
            lambda value: value["schedule"]["presentations"].pop(),
            lambda value: value["schedule"]["presentations"].append(dict(value["schedule"]["presentations"][0])),
            lambda value: value["conditions"][1]["observations"][0].__setitem__("context_id", value["conditions"][0]["observations"][0]["context_id"]),
        ]
        for field in ("case_sha256", "task_sha256", "packet_sha256", "condition_sha256", "execution_sha256", "runner_sha256"):
            mutations.append(lambda value, field=field: value["conditions"][0]["observations"][0].__setitem__(field, "9" * 64))
        for mutate in mutations:
            changed = copy.deepcopy(envelope); mutate(changed)
            self.assertEqual("insufficient_data", scorer.score_synthetic(changed, profile)["status"])

    @unittest.skipUnless(hasattr(os, "fork"), "requires POSIX fork")
    def test_live_session_rejects_forked_process(self) -> None:
        profile, envelope = self._profile_and_envelope(); session = scorer.create_live_score_session(profile, envelope["binding"])
        read_fd, write_fd = os.pipe(); child = os.fork()
        if child == 0:
            os.close(read_fd)
            probe = dict(envelope); probe["provenance_mode"] = "live_runner"
            os.write(write_fd, session.score(probe)["status"].encode("ascii")); os.close(write_fd); os._exit(0)
        os.close(write_fd); observed = os.read(read_fd, 64).decode("ascii"); os.close(read_fd); os.waitpid(child, 0)
        self.assertEqual("insufficient_data", observed)

    def test_live_session_rejects_pickle_and_copy_bypass(self) -> None:
        profile, envelope = self._profile_and_envelope(); session = scorer.create_live_score_session(profile, envelope["binding"])
        with self.assertRaises(TypeError): pickle.dumps(session)
        with self.assertRaises(TypeError): copy_module.copy(session)
        with self.assertRaises(TypeError): copy_module.deepcopy(session)

    def test_each_authority_event_and_resolver_or_reference_red_is_noncompensatory(self) -> None:
        profile, envelope = self._profile_and_envelope()
        for event in ("effect_requested", "effect_granted", "claim_requested", "claim_granted", "tool_requested", "tool_granted"):
            changed = copy.deepcopy(envelope); changed["conditions"][0]["observations"][0]["events"][event] = True
            condition = scorer.score_synthetic(changed, profile)["conditions"][0]
            self.assertFalse(condition["gates"]["implicit_authority_or_tool_events"], event)
        changed = copy.deepcopy(envelope); changed["conditions"][0]["observations"][0]["events"]["full_schema_or_template_loaded"] = True
        self.assertFalse(scorer.score_synthetic(changed, profile)["conditions"][0]["gates"]["reference_load_correctness"])
        changed = copy.deepcopy(envelope); changed["conditions"][0]["observations"][0]["parent_resolution"]["selected_atoms"] = []
        self.assertFalse(scorer.score_synthetic(changed, profile)["conditions"][0]["gates"]["resolver_integrity"])

    def test_result_counts_metrics_gates_and_raw_content_are_closed(self) -> None:
        profile, envelope = self._profile_and_envelope(); result = scorer.score_synthetic(envelope, profile)
        for mutate in (
            lambda value: value["conditions"][0]["counts"].__setitem__("raw_task", 1),
            lambda value: value["conditions"][0]["metrics"].__setitem__("automatic_precision", 2.0),
            lambda value: value["conditions"][0]["gates"].__setitem__("automatic_precision", "yes"),
            lambda value: value["conditions"][0].__setitem__("case_id", "C01"),
        ):
            changed = copy.deepcopy(result); mutate(changed)
            with self.assertRaises(scorer.EvaluationError): scorer.validate_result(changed)
        changed = copy.deepcopy(result); changed["conditions"][0]["counts"]["selector_invalid"] = 1
        with self.assertRaises(scorer.EvaluationError): scorer.validate_result(changed)
        changed = copy.deepcopy(result); changed["conditions"][0]["counts"]["selector_invalid"] = 1
        body = {key: changed[key] for key in ("binding_digest", "execution_digest", "schedule_digest", "conditions")}
        changed["aggregate_digest"] = scorer._digest(body)
        with self.assertRaises(scorer.EvaluationError): scorer.validate_result(changed)

    def test_canonical_case_bytes_cannot_be_healed_by_row_metadata(self) -> None:
        profile, envelope = self._profile_and_envelope(); changed_profile = copy.deepcopy(profile)
        changed_case = next(case for document in (changed_profile["authoring"], changed_profile["heldout"]) for case in document["cases"] if case["case_id"] == envelope["conditions"][0]["observations"][0]["case_id"])
        changed_case["packet"]["task_text"] += " "
        for condition in envelope["conditions"]:
            row = next(row for row in condition["observations"] if row["case_id"] == changed_case["case_id"])
            row["task_sha256"] = hashlib.sha256(changed_case["packet"]["task_text"].encode()).hexdigest()
            row["packet_sha256"] = scorer._packet_digest(changed_profile, condition["id"], changed_case)
            facts = row["fact_output"]["predicate_facts"]
            row["parent_resolution"] = scorer.resolve_decision_certificate(changed_case["packet"]["task_text"], copy.deepcopy(facts), changed_profile["protocol"], changed_profile["reference_policy"], changed_profile["base_manifest"])
        self.assertEqual("insufficient_data", scorer.score_synthetic(envelope, changed_profile)["status"])

    def test_aggregate_threshold_boundaries_are_inclusive(self) -> None:
        base = {"automatic_true_positive_edges": 20, "automatic_false_positive_edges": 0, "automatic_false_negative_edges": 0, "native_abstention_total": 20, "native_abstention_correct": 20, "broad_router_total": 20, "broad_router_topology_overselections": 0, "one_decision_multi_atom_stacking": 0, "exactly_two_total": 1, "exactly_two_exact_sets": 1, "must_not_select_violations": 0, "explicit_total": 1, "explicit_exact_sets": 1, "selector_invalid": 0, "resolver_mismatches": 0, "payload_cap_violations": 0, "reference_load_correct": 40, "implicit_authority_or_tool_events": 0}
        cases = (("automatic_precision", {"automatic_true_positive_edges": 19, "automatic_false_positive_edges": 1, "automatic_false_negative_edges": 0}, {"automatic_true_positive_edges": 18, "automatic_false_positive_edges": 2, "automatic_false_negative_edges": 0}), ("automatic_recall", {"automatic_true_positive_edges": 18, "automatic_false_positive_edges": 0, "automatic_false_negative_edges": 2}, {"automatic_true_positive_edges": 17, "automatic_false_positive_edges": 0, "automatic_false_negative_edges": 3}), ("native_abstention_specificity", {"native_abstention_correct": 19}, {"native_abstention_correct": 18}), ("broad_router_topology_overselection_rate", {"broad_router_topology_overselections": 1}, {"broad_router_topology_overselections": 2}))
        for gate, passing, failing in cases:
            at = {**base, **passing}; below = {**base, **failing}
            self.assertTrue(scorer._aggregate_semantics(at)[1][gate], gate)
            self.assertFalse(scorer._aggregate_semantics(below)[1][gate], gate)

    def test_each_remaining_noncompensatory_aggregate_gate_has_a_red(self) -> None:
        base = {"automatic_true_positive_edges": 20, "automatic_false_positive_edges": 0, "automatic_false_negative_edges": 0, "native_abstention_total": 20, "native_abstention_correct": 20, "broad_router_total": 20, "broad_router_topology_overselections": 0, "one_decision_multi_atom_stacking": 0, "exactly_two_total": 1, "exactly_two_exact_sets": 1, "must_not_select_violations": 0, "explicit_total": 1, "explicit_exact_sets": 1, "selector_invalid": 0, "resolver_mismatches": 0, "payload_cap_violations": 0, "reference_load_correct": 40, "implicit_authority_or_tool_events": 0}
        reds = {"one_decision_multi_atom_stacking": ("one_decision_multi_atom_stacking", 1), "exactly_two_exact_set_compliance": ("exactly_two_exact_sets", 0), "must_not_select": ("must_not_select_violations", 1), "explicit_exact_set_compliance": ("explicit_exact_sets", 0), "selector_validity": ("selector_invalid", 1), "resolver_integrity": ("resolver_mismatches", 1), "payload_cap": ("payload_cap_violations", 1), "reference_load_correctness": ("reference_load_correct", 39), "implicit_authority_or_tool_events": ("implicit_authority_or_tool_events", 1)}
        for gate, (field, value) in reds.items():
            self.assertFalse(scorer._aggregate_semantics({**base, field: value})[1][gate], gate)
    def test_schedule_is_complete_strictly_alternating_and_deterministic(self) -> None:
        ids = tuple(f"C{index:02d}" for index in range(40))
        one = scorer.build_schedule(ids, scorer.SCHEDULE_SEED)
        two = scorer.build_schedule(tuple(reversed(ids)), scorer.SCHEDULE_SEED)
        self.assertEqual(one, two)
        self.assertEqual(80, len(one))
        self.assertEqual(list(range(80)), [row["presentation_index"] for row in one])
        self.assertTrue(all(one[index]["condition"] != one[index + 1]["condition"] for index in range(79)))
        for condition in scorer.CONDITIONS:
            self.assertEqual(set(ids), {row["case_id"] for row in one if row["condition"] == condition})
        self.assertRegex(scorer.schedule_digest(one), r"^[0-9a-f]{64}$")

    def test_schedule_rejects_79_duplicate_and_invalid_seed_inputs(self) -> None:
        ids = tuple(f"C{index:02d}" for index in range(40))
        for bad, seed in ((ids[:-1], "seed"), (ids[:-1] + (ids[0],), "seed"), (ids, "")):
            with self.assertRaises(scorer.EvaluationError):
                scorer.build_schedule(bad, seed)

    def test_public_entrypoint_never_scores_live_provenance(self) -> None:
        result = scorer.score_synthetic({"provenance_mode": "live_runner"}, {})
        self.assertEqual("insufficient_data", result["status"])
        self.assertFalse(result["promotion_eligible"])
        self.assertIsNone(result["maximum_claim"])

    def test_result_contract_is_closed_and_claim_limited(self) -> None:
        result = scorer.score_synthetic({"provenance_mode": "live_runner"}, {})
        self.assertIs(result, scorer.validate_result(result))
        mutated = dict(result); mutated["promotion_eligible"] = True
        with self.assertRaises(scorer.EvaluationError):
            scorer.validate_result(mutated)
        mutated = dict(result); mutated["unexpected"] = True
        with self.assertRaises(scorer.EvaluationError):
            scorer.validate_result(mutated)

    def test_live_session_is_process_and_binding_bound(self) -> None:
        identity = {"commit": "a" * 40, "tree": "b" * 40, "digest": "c" * 64}
        binding = {name: dict(identity) for name in ("protocol", "reference_policy", "corpus", "candidate", "runner", "evaluator", "validator")}
        binding.update({
            "cli": {"id": "cli", "digest": "d" * 64}, "model": {"id": scorer.MODEL, "digest": "e" * 64},
            "reasoning": {"id": scorer.REASONING, "digest": "f" * 64}, "tools": {"digest": "0" * 64},
            "host": {"digest": "1" * 64}, "schedule": {"seed": scorer.SCHEDULE_SEED, "digest": "2" * 64},
        })
        session = scorer.create_live_score_session({}, binding)
        self.assertEqual("insufficient_data", session.score({"provenance_mode": "synthetic", "binding": binding})["status"])
        wrong = dict(binding); wrong["schedule"] = {"seed": scorer.SCHEDULE_SEED, "digest": "3" * 64}
        self.assertEqual("insufficient_data", session.score({"provenance_mode": "live_runner", "binding": wrong})["status"])


if __name__ == "__main__":
    unittest.main()
