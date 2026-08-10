from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative); assert spec and spec.loader; module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


checker = load("scripts/check_reduced_four_skill_candidate_v5.py", "aq5_checker_score_test")
scorer = load("scripts/score_activation_v5.py", "aq5_scorer_test")


def case(case_id: str, mode: str = "automatic"):
    atom, adviser = "task-contract", "codex-task-contract"; token = f"${adviser}"; prompt = f"Use {token} for this direct task contract." if mode == "explicit" else f"Define a direct task contract for {case_id}."; normalized = " ".join(prompt.casefold().split())
    return {"id": case_id, "nonce": f"nonce-{case_id}", "family": f"family-{case_id}", "prompt": prompt, "normalized_prompt": normalized, "prompt_sha256": hashlib.sha256(normalized.encode()).hexdigest(), "mode": mode, "expected_decision_atoms": [atom], "expected_advisers": [adviser], "must_not_select": [item for item in checker.ADVISERS if item != adviser], "reference_triggers": [], "deterministic_reference_expectations": [], "authority_prohibitions": ["no_authority_assignment", "no_policy_adoption"], "effect_prohibitions": ["no_effect_execution", "no_external_action"], "claim_prohibitions": ["no_completion_claim", "no_efficacy_claim", "no_product_claim"], "exactly_two": False, "precedence": {"applies": False, "candidate_atoms": [], "winner": None, "rule": None}, "declared_invocation": token if mode == "explicit" else None, "condition_blind": True, "blinding_flags": ["author_blind_to_candidate_selector", "author_blind_to_prior_outcomes"], "full_schema_or_template_expected": False}


def cases():
    rows = {f"AQ5-H-{index:03d}": case(f"AQ5-H-{index:03d}") for index in range(1, 33)}
    for split in ("A", "H"):
        for index in range(33, 37): rows[f"AQ5-{split}-{index:03d}"] = case(f"AQ5-{split}-{index:03d}", "explicit")
    return rows


def envelope_and_profile():
    candidate = checker.load_candidate(ROOT)
    # Synthetic envelopes deliberately exercise the unbound test seam while the
    # live path separately demands manifest/current-byte equality.
    candidate = copy.deepcopy(candidate)
    for row in candidate["evaluator_surface"]["files"]: row["sha256"] = "UNBOUND_AQ5_SYNTHETIC"
    base, _ = checker.load_base(ROOT); all_cases = cases(); h2 = checker.conditions(candidate)
    corpus = {"source_commit": "1" * 40, "source_tree": "2" * 40, "activation_schema_sha256": "3" * 64, "authoring_sha256": "4" * 64, "heldout_sha256": "5" * 64, "validator_sha256": "6" * 64}; reduced = {"commit": "a" * 40, "tree": "b" * 40, "input_sha256": h2["reduced"]["condition_input_sha256"]}; plan = scorer.qualification_schedule(all_cases, "aq5-synthetic")
    execution = {"model": "gpt-5.5", "reasoning": "medium", "cli_path": "<synthetic>", "cli_version": "synthetic", "cli_sha256": "7" * 64, "tools_sha256": "8" * 64, "host_surface_sha256": "9" * 64, "runner_path": scorer.RUNNER_PATH, "runner_protocol_sha256": "c" * 64, "schedule_seed": "aq5-synthetic", "schedule_sha256": scorer.sha256_json(plan), "evaluator_schema_sha256": scorer.sha256_bytes((ROOT / scorer.SCHEMA_PATH).read_bytes()), "zero_write": True, "ephemeral_context_requested": False, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown"}; execution["condition_parity_sha256"] = scorer.condition_parity_digest(execution); grouped = {"current": [], "reduced": []}
    for index, (condition, case_id) in enumerate(plan):
        item = all_cases[case_id]; constraint = checker.parse_constraint(item["prompt"]); atoms = checker.enforce_constraint(list(item["expected_decision_atoms"]), constraint); mapped = checker.map_atoms(candidate, atoms); outcome = checker.resolve_payloads(base, item["reference_triggers"], mapped); catalog = h2[condition]["atom_catalog"]
        grouped[condition].append({"case_id": case_id, "presentation_index": index, "context_id": f"aq5-synthetic-{index}", "corpus_prompt_sha256": item["prompt_sha256"], "task_sha256": scorer.sha256_bytes(item["prompt"].encode()), "candidate_input_sha256": h2[condition]["condition_input_sha256"], "atom_catalog_sha256": scorer.sha256_json(catalog), "selector_packet_sha256": scorer.selector_packet_digest(item["prompt"], catalog, constraint), "execution_contract_sha256": scorer.sha256_json(execution), "runner_protocol_sha256": execution["runner_protocol_sha256"], "parse_status": "parsed", "selected_decision_atoms": atoms, "effective_mapped_advisers": mapped, "explicit_constraint": constraint, "payload_resolution": {"status": outcome["status"], "resolved_count": outcome["resolved_count"]}, "resolved_payloads": [], "effect_requested": False, "effect_granted": False, "claim_requested": False, "claim_granted": False, "tool_requested": False, "tool_granted": False, "full_schema_or_template_loaded": False})
    conditions = [{"id": name, "candidate": {"commit": candidate["source"]["commit"], "tree": candidate["source"]["tree"], "input_sha256": h2[name]["condition_input_sha256"]} if name == "current" else reduced, "atom_universe": list(checker.ATOMS), "adviser_universe": list(checker.ADVISERS), "observations": grouped[name]} for name in ("current", "reduced")]
    return {"schema_version": "5.0", "evaluation_mode": "qualification", "provenance_mode": "synthetic_test", "corpus": corpus, "reduced_candidate": reduced, "execution_contract": execution, "conditions": conditions}, {"candidate": candidate, "base": base, "cases": all_cases, "corpus": corpus}


class EvaluatorV5Tests(unittest.TestCase):
    def test_complete_top_level_shape_scores_with_unattested_ceiling(self):
        envelope, profile = envelope_and_profile(); result = scorer.score(envelope, ROOT, profile=profile)
        self.assertEqual(result["status"], "pass")
        for key in ("promotion_eligible", "runtime_provenance_proven", "provider_identity_proven", "product_behavior_proven", "telemetry_attested", "runner_local_raw_trajectories_persisted"): self.assertFalse(result[key])
        self.assertEqual(result["provider_raw_trajectory_retention_status"], "unknown")

    def test_corpus_and_raw_task_hashes_are_distinct_and_independently_checked(self):
        envelope, profile = envelope_and_profile(); row = envelope["conditions"][0]["observations"][0]; self.assertNotEqual(row["corpus_prompt_sha256"], row["task_sha256"])
        changed = copy.deepcopy(envelope); changed["conditions"][0]["observations"][0]["corpus_prompt_sha256"] = changed["conditions"][0]["observations"][0]["task_sha256"]
        self.assertEqual(scorer.score(changed, ROOT, profile=profile)["insufficiency_reason"], "AQ5 prompt digest mismatch")

    def test_missing_or_renested_top_level_triggers_fail_before_scoring(self):
        envelope, profile = envelope_and_profile(); missing = copy.deepcopy(profile); item = next(iter(missing["cases"].values())); del item["reference_triggers"]
        self.assertEqual(scorer.score(envelope, ROOT, profile=missing)["insufficiency_reason"], "AQ5 custody unavailable")
        nested = copy.deepcopy(profile); item = next(iter(nested["cases"].values())); item["hidden_labels"] = {"reference_triggers": item.pop("reference_triggers")}
        self.assertEqual(scorer.score(envelope, ROOT, profile=nested)["insufficiency_reason"], "AQ5 custody unavailable")

    def test_public_live_json_and_wrong_identity_witness_fail_closed(self):
        envelope, profile = envelope_and_profile(); envelope["provenance_mode"] = "live_runner"
        self.assertEqual(scorer.score(envelope, ROOT, profile=profile)["insufficiency_reason"], "AQ5 public scoring rejects live provenance")
        self.assertEqual(scorer.score_live(envelope, ROOT, witness=object())["insufficiency_reason"], "AQ5 live witness mismatch")

    def test_direct_core_live_scoring_bypass_without_process_local_witness_fails_closed(self):
        envelope, _profile = envelope_and_profile(); envelope["provenance_mode"] = "live_runner"
        self.assertEqual(scorer._score(envelope, ROOT, None)["insufficiency_reason"], "AQ5 live witness mismatch")

    def test_live_reduced_candidate_requires_the_exact_resolved_commit_not_tree_identity(self):
        class FakeChecker:
            @staticmethod
            def resolve_commit(_root, _commit): return "b" * 40
        with self.assertRaisesRegex(scorer.InputError, "exact commit"):
            scorer.require_exact_commit(FakeChecker(), ROOT, "a" * 40)

    def test_resolution_branches_are_closed_and_incomplete_is_scored_not_custody_abort(self):
        resolved = {"status": "resolved", "resolved_count": 1, "records": [{"payload_id": "one", "trigger_ids": ["decision-contract"]}]}
        scorer.validate_payload_resolution(resolved, ["decision-contract"])
        scorer.validate_payload_resolution({"status": "cap_exceeded", "resolved_count": 4, "records": []}, ["decision-contract"])
        scorer.validate_payload_resolution({"status": "unresolved", "resolved_count": 1, "records": [{"payload_id": "partial", "trigger_ids": ["decision-contract"]}]}, ["decision-contract", "verification-evidence"])
        for bad in ({"status": "cap_exceeded", "resolved_count": 4, "records": [{"payload_id": "leak", "trigger_ids": []}]}, {"status": "unresolved", "resolved_count": 1, "records": [{"payload_id": "complete", "trigger_ids": ["decision-contract", "verification-evidence"]}]}, {"status": "resolved", "resolved_count": 1, "records": [{"payload_id": "partial", "trigger_ids": ["decision-contract"]}]}):
            with self.assertRaises(scorer.InputError): scorer.validate_payload_resolution(bad, ["decision-contract", "verification-evidence"])

    def test_noncompensatory_gate_thresholds_are_inclusive_only_at_the_boundary(self):
        all_cases = {f"AQ5-H-{index:03d}": {"id": f"AQ5-H-{index:03d}", "expected_decision_atoms": ["task-contract"], "must_not_select": [], "reference_triggers": [], "deterministic_reference_expectations": [], "mode": "automatic", "exactly_two": False} for index in range(1, 41)}
        class FakeChecker:
            ATOM_TO_ADVISER = checker.ATOM_TO_ADVISER
            @staticmethod
            def resolve_payloads(*_args): return {"status": "resolved", "resolved_count": 0, "records": []}
        def condition(overselected: int):
            observations = []
            for index, case_id in enumerate(all_cases):
                atoms = ["task-contract"] + (["topology-control-boundary"] if index < overselected else [])
                observations.append({"case_id": case_id, "selected_decision_atoms": atoms, "effective_mapped_advisers": [checker.ATOM_TO_ADVISER[atom] for atom in atoms], "full_schema_or_template_loaded": False, "effect_requested": False, "effect_granted": False, "claim_requested": False, "claim_granted": False, "tool_requested": False, "tool_granted": False})
            return {"id": "current", "candidate": {}, "observations": observations}
        at = scorer.score_condition(condition(2), {"cases": all_cases, "base": {}}, FakeChecker())
        below = scorer.score_condition(condition(3), {"cases": all_cases, "base": {}}, FakeChecker())
        self.assertEqual(at["metrics"]["topology_control_boundary_overselection_rate"], .05); self.assertTrue(at["gates"]["topology_control_boundary_overselection_rate"])
        self.assertGreater(below["metrics"]["topology_control_boundary_overselection_rate"], .05); self.assertFalse(below["gates"]["topology_control_boundary_overselection_rate"])

    def test_precision_recall_and_native_threshold_reds_cover_boundary_and_one_step_below(self):
        class FakeChecker:
            ATOM_TO_ADVISER = checker.ATOM_TO_ADVISER
            @staticmethod
            def resolve_payloads(*_args): return {"status": "resolved", "resolved_count": 0, "records": []}
        cases = {}
        for index in range(20): cases[f"AQ5-H-{index:03d}"] = {"id": f"AQ5-H-{index:03d}", "expected_decision_atoms": ["task-contract"], "must_not_select": [], "reference_triggers": [], "deterministic_reference_expectations": [], "mode": "automatic", "exactly_two": False}
        for index in range(20, 40): cases[f"AQ5-H-{index:03d}"] = {"id": f"AQ5-H-{index:03d}", "expected_decision_atoms": [], "must_not_select": [], "reference_triggers": [], "deterministic_reference_expectations": [], "mode": "automatic", "exactly_two": False}
        def scored(correct_positive: int, false_positive_native: int):
            observations = []
            for index, case_id in enumerate(cases):
                atoms = ["task-contract"] if index < correct_positive or 20 <= index < 20 + false_positive_native else []
                observations.append({"case_id": case_id, "selected_decision_atoms": atoms, "effective_mapped_advisers": [checker.ATOM_TO_ADVISER[atom] for atom in atoms], "full_schema_or_template_loaded": False, "effect_requested": False, "effect_granted": False, "claim_requested": False, "claim_granted": False, "tool_requested": False, "tool_granted": False})
            return scorer.score_condition({"id": "current", "candidate": {}, "observations": observations}, {"cases": cases, "base": {}}, FakeChecker())
        precision_at, precision_below = scored(19, 1), scored(18, 1)
        recall_at, recall_below = scored(18, 0), scored(17, 0)
        native_at, native_below = scored(20, 1), scored(20, 2)
        self.assertEqual(precision_at["metrics"]["precision"], .95); self.assertTrue(precision_at["gates"]["precision"]); self.assertFalse(precision_below["gates"]["precision"])
        self.assertEqual(recall_at["metrics"]["recall"], .9); self.assertTrue(recall_at["gates"]["recall"]); self.assertFalse(recall_below["gates"]["recall"])
        self.assertEqual(native_at["metrics"]["native_abstention_specificity"], .95); self.assertTrue(native_at["gates"]["native_abstention_specificity"]); self.assertFalse(native_below["gates"]["native_abstention_specificity"])

    def test_each_noncompensatory_behavior_gate_has_a_targeted_red(self):
        """Each target is otherwise a passing 40-case condition; payload caps also make their reference unavailable by definition."""
        all_cases = {}
        for index in range(40):
            case_id = f"AQ5-H-{index:03d}"; all_cases[case_id] = {"id": case_id, "expected_decision_atoms": ["task-contract"], "must_not_select": [], "reference_triggers": [], "deterministic_reference_expectations": [], "mode": "automatic", "exactly_two": False}
        all_cases["AQ5-H-001"].update(expected_decision_atoms=["task-contract", "verification-strategy"], exactly_two=True)
        all_cases["AQ5-H-002"].update(mode="explicit")
        all_cases["AQ5-H-003"].update(reference_triggers=["special"], deterministic_reference_expectations=[{"payload_id": "special", "owner_atom": "task-contract"}])

        class FakeChecker:
            ATOM_TO_ADVISER = checker.ATOM_TO_ADVISER
            @staticmethod
            def resolve_payloads(base, triggers, _advisers):
                if triggers == ["special"] and base["failure"] == "payload_cap": return {"status": "cap_exceeded", "resolved_count": 4, "records": []}
                if triggers == ["special"] and base["failure"] == "reference_load_correctness": return {"status": "unresolved", "resolved_count": 0, "records": []}
                if triggers == ["special"]: return {"status": "resolved", "resolved_count": 1, "records": [{"payload_id": "special", "owner_adviser_id": "codex-task-contract", "trigger_ids": ["special"]}]}
                return {"status": "resolved", "resolved_count": 0, "records": []}

        def condition(target: str):
            observations = []
            for case_id, item in all_cases.items():
                atoms = list(item["expected_decision_atoms"]); mapped = [checker.ATOM_TO_ADVISER[atom] for atom in atoms]
                if target == "one_decision_stacking" and case_id == "AQ5-H-004": atoms.append("verification-strategy"); mapped.append("verification-strategy-engineering")
                elif target == "exactly_two_exact_set_compliance" and case_id == "AQ5-H-001": atoms.pop(); mapped.pop()
                elif target == "must_not_select" and case_id == "AQ5-H-004": all_cases[case_id]["must_not_select"] = ["agentic-engineering"]; mapped.append("agentic-engineering")
                elif target == "explicit_exact_set_compliance" and case_id == "AQ5-H-002": atoms = []; mapped = []
                observations.append({"case_id": case_id, "selected_decision_atoms": atoms, "effective_mapped_advisers": mapped, "full_schema_or_template_loaded": False, "effect_requested": False, "effect_granted": False, "claim_requested": False, "claim_granted": False, "tool_requested": target == "implicit_authority_or_tool_events" and case_id == "AQ5-H-004", "tool_granted": False})
            return {"id": "current", "candidate": {}, "observations": observations}

        for target in ("one_decision_stacking", "exactly_two_exact_set_compliance", "must_not_select", "explicit_exact_set_compliance", "payload_cap", "reference_load_correctness", "implicit_authority_or_tool_events"):
            result = scorer.score_condition(condition(target), {"cases": all_cases, "base": {"failure": target}}, FakeChecker())
            self.assertFalse(result["gates"][target], target)

    def test_result_contract_is_closed_for_scored_and_insufficient_outcomes(self):
        envelope, profile = envelope_and_profile(); result = scorer.score(envelope, ROOT, profile=profile); self.assertIs(scorer.validate_result(result), result)
        malformed = dict(result); malformed["unexpected"] = True
        with self.assertRaises(scorer.InputError): scorer.validate_result(malformed)
        self.assertEqual(set(scorer.insufficient("test")), scorer.INSUFFICIENT_KEYS)

    def test_live_runner_provenance_requires_committed_manifest_contract_and_live_byte_identity(self):
        raw = b"synthetic committed AQ5 runner bytes"; digest = scorer.sha256_bytes(raw); candidate = {"evaluator_surface": {"files": [{"path": scorer.RUNNER_PATH, "sha256": digest}]}}; execution = {"runner_path": scorer.RUNNER_PATH, "runner_protocol_sha256": digest}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); path = root / scorer.RUNNER_PATH; path.parent.mkdir(parents=True); path.write_bytes(raw)
            with mock.patch.object(scorer, "git_show", return_value=raw): scorer.validate_runner_provenance(root, "a" * 40, candidate, execution)
            changed = copy.deepcopy(execution); changed["runner_protocol_sha256"] = "0" * 64
            with mock.patch.object(scorer, "git_show", return_value=raw), self.assertRaisesRegex(scorer.InputError, "byte provenance"):
                scorer.validate_runner_provenance(root, "a" * 40, candidate, changed)
            path.write_bytes(b"live drift")
            with mock.patch.object(scorer, "git_show", return_value=raw), self.assertRaisesRegex(scorer.InputError, "byte provenance"):
                scorer.validate_runner_provenance(root, "a" * 40, candidate, execution)

    def test_v5_runner_and_scorer_have_no_nested_hidden_label_access(self):
        for relative in ("scripts/score_activation_v5.py", "scripts/run_activation_trials_v5.py"):
            source = (ROOT / relative).read_text()
            self.assertNotIn('["hidden_labels"]', source); self.assertNotIn("['hidden_labels']", source)


if __name__ == "__main__": unittest.main()
