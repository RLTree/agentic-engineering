"""Synthetic-only tests for the pure AQ7 resolver and checker surface."""
from __future__ import annotations

import copy
import importlib.util
import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


resolver = load("scripts/resolve_h3_decision_certificate_v7.py", "aq7_resolver")
checker = load("scripts/check_reduced_four_skill_candidate_v7.py", "aq7_checker")
PROTOCOL = json.loads((ROOT / "evals/foundation-v4/decision-certificate-protocol-v6.json").read_text())
SCHEMA = json.loads((ROOT / "evals/foundation-v4/decision-certificate-selector-output-schema-v6.json").read_text())
POLICY = json.loads((ROOT / "evals/foundation-v4/decision-certificate-reference-policy-v6.json").read_text())
ADAPTER = json.loads((ROOT / "evals/foundation-v4/decision-certificate-condition-adapter-v7.json").read_text())


def facts(**states: str) -> list[dict[str, str]]:
    return [{"predicate_id": predicate, "state": states.get(predicate, "absent")}
            for predicate in PROTOCOL["predicate_order"]]


def base() -> dict:
    return {"skills": [
        {"id": "agentic-engineering", "references": [
            {"payload_id": "a", "sha256": "a" * 64, "trigger_ids": ["decomposition-boundary", "architecture-boundary"]}]},
        {"id": "codex-task-contract", "references": [
            {"payload_id": "b", "sha256": "b" * 64, "trigger_ids": ["decision-contract"]}]},
        {"id": "verification-strategy-engineering", "references": [
            {"payload_id": "c", "sha256": "c" * 64, "trigger_ids": ["verification-evidence"]}]},
        {"id": "engineering-learning-loop", "references": [
            {"payload_id": "d", "sha256": "d" * 64, "trigger_ids": ["reference-isolation", "learning-adoption"]}]},
    ]}


@contextmanager
def candidate_fixture():
    """A content-free Git fixture exercising committed/live custody seams."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        def git(*args: str) -> str:
            return subprocess.check_output(["git", *args], cwd=root, text=True).strip()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        git("config", "user.name", "AQ7 test")
        git("config", "user.email", "aq7@example.invalid")
        paths = {
            checker.H3_PROTOCOL, checker.SELECTOR_SCHEMA, checker.POLICY_PATH, checker.BASE_PATH,
            checker.CORPUS_SCHEMA, checker.AUTHORING, checker.HELDOUT, checker.VALIDATOR_PATH,
            checker.RUN_INDEX_PATH, checker.ADAPTER_PATH, f"{checker.CORPUS_ROOT}/README.md",
            "scripts/check_reduced_four_skill_candidate_v7.py", "scripts/resolve_h3_decision_certificate_v7.py",
            "scripts/score_activation_v7.py", "scripts/run_activation_trials_v7.py",
            "evals/foundation-v4/activation-evaluator-schema-v7.json",
        }
        for index, path in enumerate(sorted(paths)):
            target = root / path; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"{}" if path.endswith(".json") else f"fixture-{index}".encode())
        git("add", "."); git("commit", "-qm", "authority")
        authority_commit, authority_tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
        def digest(path: str) -> str: return hashlib.sha256((root / path).read_bytes()).hexdigest()
        def binding(path: str) -> dict: return {"commit": authority_commit, "tree": authority_tree, "path": path, "sha256": digest(path)}
        h3, schema, policy, base_binding = (binding(path) for path in (checker.H3_PROTOCOL, checker.SELECTOR_SCHEMA, checker.POLICY_PATH, checker.BASE_PATH))
        contract = {**binding(checker.CORPUS_SCHEMA), "readme_path": f"{checker.CORPUS_ROOT}/README.md", "readme_sha256": digest(f"{checker.CORPUS_ROOT}/README.md")}
        corpus = {**binding(checker.CORPUS_SCHEMA), "authoring_path": checker.AUTHORING, "authoring_sha256": digest(checker.AUTHORING), "heldout_path": checker.HELDOUT, "heldout_sha256": digest(checker.HELDOUT)}
        validator, run_index, adapter = (binding(path) for path in (checker.VALIDATOR_PATH, checker.RUN_INDEX_PATH, checker.ADAPTER_PATH))
        patched = {"H3": (authority_commit, authority_tree), "POLICY": (authority_commit, authority_tree), "BASE": (authority_commit, authority_tree), "CONTRACT": (authority_commit, authority_tree), "CORPUS": (authority_commit, authority_tree), "VALIDATOR": (authority_commit, authority_tree), "RUN_INDEX": (authority_commit, authority_tree), "ADAPTER": (authority_commit, authority_tree), "H3_BINDING": h3, "SCHEMA_BINDING": schema, "POLICY_BINDING": policy, "BASE_BINDING": base_binding, "CONTRACT_BINDING": contract, "CORPUS_BINDING": corpus, "VALIDATOR_BINDING": validator, "RUN_INDEX_BINDING": run_index, "ADAPTER_BINDING": adapter}
        with patch.multiple(checker, **patched):
            files = []
            for role, path in zip(checker.ROLES, ("scripts/check_reduced_four_skill_candidate_v7.py", "scripts/resolve_h3_decision_certificate_v7.py", "scripts/score_activation_v7.py", "scripts/run_activation_trials_v7.py", "evals/foundation-v4/activation-evaluator-schema-v7.json", checker.VALIDATOR_PATH, checker.RUN_INDEX_PATH, checker.ADAPTER_PATH), strict=True):
                files.append({"role": role, "path": path, "sha256": digest(path)})
            manifest = {"schema_version": "7.0", "claim_ceiling": "structural-only", "h3_authority": h3, "selector_schema_authority": schema, "reference_policy_authority": policy, "base_manifest_authority": base_binding, "aq7_contract_authority": contract, "corpus_authority": corpus, "validator_authority": validator, "run_index_authority": run_index, "condition_adapter_authority": adapter, "evaluator_surface": {"files": files}, "execution_contract": CheckerTests._contract()}
            (root / checker.MANIFEST_PATH).write_text(json.dumps(manifest))
            git("add", "."); git("commit", "-qm", "candidate")
            candidate_commit = git("rev-parse", "HEAD")
            yield root, candidate_commit, manifest


class ResolverTests(unittest.TestCase):
    def test_closed_facts_and_packet(self) -> None:
        canonical = resolver.validate_fact_output({"predicate_facts": facts()}, PROTOCOL, SCHEMA)
        self.assertEqual(len(canonical), 12)
        for vector in (list(canonical), canonical):
            resolved = resolver.resolve_decision_certificate("task", vector, PROTOCOL, POLICY, base())
            self.assertEqual(resolved["selected_atoms"], [])
        with self.assertRaises(resolver.ResolverError):
            resolver.validate_fact_output({"predicate_facts": facts(), "atoms": []}, PROTOCOL, SCHEMA)
        for malformed in (({"predicate_id": "wrong", "state": "absent"},), tuple(facts())[:-1]):
            with self.assertRaises(resolver.ResolverError):
                resolver.resolve_decision_certificate("task", malformed, PROTOCOL, POLICY, base())
        packet = resolver.build_condition_packet(ADAPTER, "current", "same task")
        reduced = resolver.build_condition_packet(ADAPTER, "reduced", "same task")
        self.assertEqual(list(packet), ["instruction", "task_text", "predicate_order", "condition_guidance"])
        self.assertEqual(packet["predicate_order"], PROTOCOL["predicate_order"])
        self.assertEqual({key: packet[key] for key in packet if key != "condition_guidance"},
                         {key: reduced[key] for key in reduced if key != "condition_guidance"})
        self.assertNotIn("labels", json.dumps(packet).lower())

    def test_automatic_uncertainty_cap_and_explicit_precedence(self) -> None:
        automatic = resolver.resolve_decision_certificate("task", facts(multi_domain_coordination="present"), PROTOCOL, POLICY, base())
        self.assertEqual((automatic["selection_status"], automatic["selected_atoms"]), ("automatic", ["topology-control-boundary"]))
        uncertain = resolver.resolve_decision_certificate("task", facts(multi_domain_coordination="present", cross_component_or_agent_boundary="uncertain"), PROTOCOL, POLICY, base())
        self.assertEqual(uncertain["selected_atoms"], [])
        capped = resolver.resolve_decision_certificate("task", facts(multi_domain_coordination="present", scope_acceptance_or_authority_contract="present", claim_or_behavior_requires_verification_strategy="present"), PROTOCOL, POLICY, base())
        self.assertEqual((capped["selection_status"], capped["selected_atoms"]), ("cap_exceeded", []))
        explicit = resolver.resolve_decision_certificate("$engineering-learning-loop", facts(multi_domain_coordination="present"), PROTOCOL, POLICY, base())
        self.assertEqual((explicit["selection_status"], explicit["selected_atoms"]), ("exact", ["engineering-learning"]))
        ambiguous = resolver.resolve_decision_certificate("$agentic-engineering $codex-task-contract", facts(), PROTOCOL, POLICY, base())
        self.assertEqual((ambiguous["selection_status"], ambiguous["selected_atoms"]), ("ambiguous", []))

    def test_owner_qualified_cover_and_lexical_tie(self) -> None:
        source = base()
        source["skills"][0]["references"] = [
            {"payload_id": "z", "sha256": "z" * 64, "trigger_ids": ["decomposition-boundary"]},
            {"payload_id": "a", "sha256": "a" * 64, "trigger_ids": ["decomposition-boundary"]},
        ]
        result = resolver.resolve_decision_certificate("task", facts(multi_domain_coordination="present"), PROTOCOL, POLICY, source)
        self.assertEqual(result["payload_resolution"]["payloads"], [{"owner_adviser_id": "agentic-engineering", "payload_id": "a", "sha256": "a" * 64}])
        self.assertEqual(set(result), {"selection_status", "eligible_atoms", "selected_atoms", "selection_constraint", "mapped_advisers", "reference_requests", "payload_resolution"})

    def test_explicit_grammar_and_each_eligibility_boundary(self) -> None:
        cases = (
            ("$not-a-frozen-adviser", "unrecognized"),
            ("$agentic-engineering $not-a-frozen-adviser", "unrecognized"),
            ("$agentic-engineering $agentic-engineering", "ambiguous"),
            ("$agentic-engineering-suffix", "unrecognized"),
            ("bare $", "automatic"),
        )
        for task, status in cases:
            with self.subTest(task=task):
                value = resolver.resolve_decision_certificate(task, facts(), PROTOCOL, POLICY, base())
                self.assertEqual(value["selection_status"], status)
        for rule in PROTOCOL["deterministic_selection"]["eligibility_rules"]:
            atom = rule["derived_atom"]
            positive, exclusion = rule["positive_predicates"][0], rule["exclusion_predicate"]
            for state in ("present", "uncertain"):
                with self.subTest(atom=atom, state=state):
                    value = resolver.resolve_decision_certificate("task", facts(**{positive: "present", exclusion: state}), PROTOCOL, POLICY, base())
                    self.assertNotIn(atom, value["selected_atoms"])

    def test_zero_one_two_and_over_cap_selection(self) -> None:
        positives = [row["positive_predicates"][0] for row in PROTOCOL["deterministic_selection"]["eligibility_rules"]]
        for count, expected_status, expected_count in ((0, "automatic", 0), (1, "automatic", 1), (2, "automatic", 2), (3, "cap_exceeded", 0)):
            with self.subTest(count=count):
                state = {name: "present" for name in positives[:count]}
                value = resolver.resolve_decision_certificate("task", facts(**state), PROTOCOL, POLICY, base())
                self.assertEqual((value["selection_status"], len(value["selected_atoms"])), (expected_status, expected_count))

    def test_reference_requests_and_cover_failure_branches(self) -> None:
        no_positive = resolver.resolve_decision_certificate("$agentic-engineering", facts(), PROTOCOL, POLICY, base())
        self.assertEqual(no_positive["reference_requests"], [])
        ordered = resolver.resolve_decision_certificate("task", facts(multi_domain_coordination="present", scope_acceptance_or_authority_contract="present"), PROTOCOL, POLICY, base())
        self.assertEqual(ordered["reference_requests"], [
            {"owner_adviser_id": "agentic-engineering", "trigger_id": "decomposition-boundary"},
            {"owner_adviser_id": "codex-task-contract", "trigger_id": "decision-contract"},
        ])
        missing = {"skills": [{"id": "agentic-engineering", "references": []}]}
        unresolved = resolver.resolve_decision_certificate("task", facts(multi_domain_coordination="present"), PROTOCOL, POLICY, missing)
        self.assertEqual(unresolved["payload_resolution"], {"status": "unresolved", "resolved_count": 0, "payloads": []})
        too_many = {"skills": [{"id": "agentic-engineering", "references": [
            {"payload_id": str(i), "sha256": str(i) * 64, "trigger_ids": [trigger]}
            for i, trigger in enumerate(("decomposition-boundary", "architecture-boundary", "x", "y"), 1)]}]}
        policy = copy.deepcopy(POLICY)
        policy["request_derivation"]["ordered_mapping_rows"][0]["trigger_id"] = "decomposition-boundary"
        # Four distinct owner-qualified requests demonstrate the hard cover cap
        # through the private resolver's deterministic path, not labels.
        self.assertEqual(resolver._resolve_payloads(too_many, [
            {"owner_adviser_id": "agentic-engineering", "trigger_id": trigger}
            for trigger in ("decomposition-boundary", "architecture-boundary", "x", "y")], policy)["status"], "cap_exceeded")


class CheckerTests(unittest.TestCase):
    def test_execution_contract_is_exact(self) -> None:
        contract = {
            "conditions": [{"id": ident, "condition_guidance_canonical_sha256": digest} for ident, digest in checker.CONDITIONS],
            "model": {"id": "gpt-5.5", "reasoning_effort": "medium"},
            "schedule": {"seed": "aq7-h3-ci1-v1", "qualification_cases": 40, "presentations": 80, "strict_alternation": True},
            "packet": {"keys": ["instruction", "task_text", "predicate_order", "condition_guidance"], "sole_condition_variance": "condition_guidance", "model_output_root": "predicate_facts", "fact_count": 12},
            "isolation": {"fresh_empty_cwd": True, "ephemeral_context_requested": True, "sandbox": "read-only", "approval_policy": "never", "tools_enabled": False, "apps_enabled": False, "plugins_enabled": False, "mcp_enabled": False},
            "integrity": {"unique_contexts_required": 80, "content_retries": 0, "canary_precompletion_infrastructure_retries_max": 1, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown"},
            "gates": {"automatic_precision_min": "0.95", "automatic_recall_min": "0.90", "native_abstention_specificity_min": "0.95", "broad_router_overselection_max": "0.05", "one_decision_stacking_max": 0, "exactly_two_exact_set_min": "1.00", "must_not_select_violations_max": 0, "explicit_exact_set_min": "1.00", "selector_invalid_max": 0, "resolver_mismatch_max": 0, "payload_cap_violations_max": 0, "reference_load_correct_min": "1.00", "authority_tool_violations_max": 0},
            "result_claims": {"maximum_claim": "unattested deterministic AQ7 decision-certificate telemetry from supplied observations", "runtime_provenance_proven": False, "provider_identity_proven": False, "telemetry_attested": False, "product_behavior_proven": False, "promotion_eligible": False},
        }
        checker._execution_contract(contract)
        bad = copy.deepcopy(contract); bad["schedule"]["presentations"] = 79
        with self.assertRaises(checker.CandidateError): checker._execution_contract(bad)

    def test_no_shadow_resolver_definition(self) -> None:
        for path in (ROOT / "scripts").glob("*_v7.py"):
            if path.name in {"resolve_h3_decision_certificate_v7.py", "check_reduced_four_skill_candidate_v7.py"}:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("def resolve_decision_certificate(", text, path.name)

    def test_temp_git_candidate_manifest_and_live_drift(self) -> None:
        with candidate_fixture() as (root, commit, manifest):
            self.assertEqual(checker.validate_manifest_document(manifest, root, commit, True), [])
            fake = type("Validator", (), {"validate_frozen": staticmethod(lambda *args, **kwargs: type("Result", (), {"errors": (), "qualified_ids": tuple(f"AQ7-H-{n:03d}" for n in range(1, 41))})())})
            with patch.object(checker, "_load_module", return_value=fake):
                profile = checker.load_verified_candidate(root, commit, True)
            self.assertEqual((profile["candidate_commit"], profile["tree"]), (commit, subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=root, text=True).strip()))
            for field in tuple(manifest):
                broken = copy.deepcopy(manifest); broken[field] = None
                with self.subTest(field=field), self.assertRaises(checker.CandidateError):
                    checker.validate_manifest_document(broken)
            for mutation in (
                lambda value: value["h3_authority"].__setitem__("tree", "0" * 40),
                lambda value: value["corpus_authority"].__setitem__("authoring_path", "../escape"),
                lambda value: value["evaluator_surface"]["files"].reverse(),
                lambda value: value["evaluator_surface"]["files"].pop(),
                lambda value: value["evaluator_surface"]["files"].append(copy.deepcopy(value["evaluator_surface"]["files"][0])),
                lambda value: value["execution_contract"]["model"].__setitem__("reasoning_effort", "high"),
                lambda value: value["execution_contract"]["conditions"][0].__setitem__("condition_guidance_canonical_sha256", "0" * 64),
                lambda value: value["execution_contract"]["gates"].__setitem__("automatic_recall_min", "0.89"),
                lambda value: value["execution_contract"]["result_claims"].__setitem__("promotion_eligible", True),
            ):
                broken = copy.deepcopy(manifest); mutation(broken)
                with self.assertRaises(checker.CandidateError): checker.validate_manifest_document(broken)
            with self.assertRaises(checker.CandidateError): checker.validate_manifest_document(manifest, root, "A" * 40, True)
            (root / "untracked.txt").write_text("drift")
            with self.assertRaises(checker.CandidateError): checker.validate_manifest_document(manifest, root, commit, True)
        with candidate_fixture() as (root, commit, manifest):
            target = root / "scripts/score_activation_v7.py"
            target.write_text(target.read_text() + "unstaged")
            with self.assertRaises(checker.CandidateError): checker.validate_manifest_document(manifest, root, commit, True)
            subprocess.run(["git", "add", str(target)], cwd=root, check=True)
            with self.assertRaises(checker.CandidateError): checker.validate_manifest_document(manifest, root, commit, True)

    def test_zero_model_projection_is_exact_40x2_and_content_free(self) -> None:
        contract = self._contract()
        ids = tuple(f"AQ7-H-{index:03d}" for index in range(1, 41))
        expected = resolver.resolve_decision_certificate("synthetic", facts(), PROTOCOL, POLICY, base())
        grading = {
            "expected_predicate_facts": facts(), "expected_selection_status": expected["selection_status"],
            "expected_selected_atoms": expected["selected_atoms"], "expected_selection_constraint": expected["selection_constraint"],
            "expected_advisers": expected["mapped_advisers"], "expected_reference_requests": expected["reference_requests"],
            "deterministic_reference_expectations": {"status": expected["payload_resolution"]["status"], "resolved_payload_count": expected["payload_resolution"]["resolved_count"], "payloads": expected["payload_resolution"]["payloads"]},
        }
        profile = {"protocol": PROTOCOL, "selector_schema": SCHEMA, "reference_policy": POLICY, "base_manifest": base(), "qualified_ids": ids, "execution_contract": contract}
        cases = {case_id: {"packet": {"task_text": "synthetic"}, "grading": copy.deepcopy(grading)} for case_id in ids}
        with patch.object(checker.subprocess, "run", side_effect=AssertionError("subprocess forbidden")):
            self.assertEqual(checker.verify_zero_model_projection(profile, cases), {"status": "pass", "qualification_cases": 40, "presentations": 80, "live_calls": 0})
        for mutate in (
            lambda value: value[ids[0]]["grading"].__setitem__("expected_selected_atoms", ["task-contract"]),
            lambda value: value.pop(ids[-1]),
            lambda value: value[ids[0]]["grading"]["expected_predicate_facts"].__setitem__(0, {"predicate_id": "wrong", "state": "absent"}),
        ):
            broken = copy.deepcopy(cases); mutate(broken)
            with self.assertRaises(checker.CandidateError): checker.verify_zero_model_projection(profile, broken)
        bad_profile = copy.deepcopy(profile); bad_profile["execution_contract"]["schedule"]["presentations"] = 79
        with self.assertRaises(checker.CandidateError): checker.verify_zero_model_projection(bad_profile, cases)

    @staticmethod
    def _contract() -> dict:
        return {
            "conditions": [{"id": ident, "condition_guidance_canonical_sha256": digest} for ident, digest in checker.CONDITIONS],
            "model": {"id": "gpt-5.5", "reasoning_effort": "medium"},
            "schedule": {"seed": "aq7-h3-ci1-v1", "qualification_cases": 40, "presentations": 80, "strict_alternation": True},
            "packet": {"keys": ["instruction", "task_text", "predicate_order", "condition_guidance"], "sole_condition_variance": "condition_guidance", "model_output_root": "predicate_facts", "fact_count": 12},
            "isolation": {"fresh_empty_cwd": True, "ephemeral_context_requested": True, "sandbox": "read-only", "approval_policy": "never", "tools_enabled": False, "apps_enabled": False, "plugins_enabled": False, "mcp_enabled": False},
            "integrity": {"unique_contexts_required": 80, "content_retries": 0, "canary_precompletion_infrastructure_retries_max": 1, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown"},
            "gates": {"automatic_precision_min": "0.95", "automatic_recall_min": "0.90", "native_abstention_specificity_min": "0.95", "broad_router_overselection_max": "0.05", "one_decision_stacking_max": 0, "exactly_two_exact_set_min": "1.00", "must_not_select_violations_max": 0, "explicit_exact_set_min": "1.00", "selector_invalid_max": 0, "resolver_mismatch_max": 0, "payload_cap_violations_max": 0, "reference_load_correct_min": "1.00", "authority_tool_violations_max": 0},
            "result_claims": {"maximum_claim": "unattested deterministic AQ7 decision-certificate telemetry from supplied observations", "runtime_provenance_proven": False, "provider_identity_proven": False, "telemetry_attested": False, "product_behavior_proven": False, "promotion_eligible": False},
        }


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
