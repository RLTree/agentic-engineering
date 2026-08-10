from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_module(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load_module("scripts/check_reduced_four_skill_candidate_v4.py", "aq4_checker_score_test")
scorer = load_module("scripts/score_activation_v4.py", "aq4_scorer_test")


def bound_synthetic_candidate():
    candidate = checker.load_candidate(ROOT)
    base, _ = checker.load_base_candidate(ROOT)
    for name in ("current", "reduced"):
        candidate["conditions"][name]["atom_catalog_sha256"] = checker.canonical_sha256(candidate["conditions"][name]["atom_catalog"])
        candidate["conditions"][name]["condition_input_sha256"] = checker.canonical_sha256(checker.condition_descriptor(candidate, base, name))
    return candidate, base


def synthetic_cases():
    cases = {}
    automatic_patterns = [
        ([], [], []),
        (["topology-control-boundary"], ["task-contract"], ["architecture-boundary"]),
        (["task-contract", "verification-strategy"], [], ["decision-contract", "verification-evidence"]),
        (["task-contract"], [], ["decision-contract"]),
        (["verification-strategy"], [], ["verification-evidence"]),
        (["engineering-learning"], [], ["learning-adoption"]),
    ]
    for index in range(32):
        atoms, must_not, triggers = automatic_patterns[index % len(automatic_patterns)]
        case_id = f"S-H-{index + 1:03d}"
        cases[case_id] = {"id": case_id, "prompt": f"Synthetic direct decision instance {index + 1}.", "mode": "automatic", "hidden_labels": {"expected_decision_atoms": atoms, "must_not_select_atoms": must_not, "reference_triggers": triggers}}
    for index in range(8):
        atom = checker.ATOMS[index % 4]
        adviser = checker.ATOM_TO_ADVISER[atom]
        trigger = {"topology-control-boundary": "architecture-boundary", "task-contract": "decision-contract", "verification-strategy": "verification-evidence", "engineering-learning": "learning-adoption"}[atom]
        case_id = f"S-X-{index + 1:03d}"
        cases[case_id] = {"id": case_id, "prompt": f"Use ${adviser} for synthetic direct instance {index + 1}.", "mode": "explicit", "hidden_labels": {"expected_decision_atoms": [atom], "must_not_select_atoms": [], "reference_triggers": [trigger]}}
    return cases


def synthetic_corpus_bytes(*, heldout_automatic: int = 32, explicit: int = 8):
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "required": ["cases"], "properties": {"cases": {"type": "array", "items": {"type": "object", "required": ["id", "mode"], "properties": {"id": {"type": "string"}, "mode": {"enum": ["automatic", "explicit"]}}}}}, "additionalProperties": False}
    authoring_explicit = explicit // 2
    authoring = {"cases": [{"id": f"E-A-{index}", "mode": "explicit"} for index in range(authoring_explicit)]}
    heldout = {"cases": [{"id": f"A-H-{index}", "mode": "automatic"} for index in range(heldout_automatic)] + [{"id": f"E-H-{index}", "mode": "explicit"} for index in range(explicit - authoring_explicit)]}
    return tuple(json.dumps(value).encode() for value in (schema, authoring, heldout))


def make_envelope():
    candidate, base = bound_synthetic_candidate()
    cases = synthetic_cases()
    corpus = {"source_commit": "1" * 40, "source_tree": "2" * 40, "activation_schema_sha256": "3" * 64, "authoring_sha256": "4" * 64, "heldout_sha256": "5" * 64, "validator_sha256": "6" * 64}
    reduced = {"commit": "a" * 40, "tree": "b" * 40, "input_sha256": candidate["conditions"]["reduced"]["condition_input_sha256"]}
    plan = scorer.qualification_schedule(cases, "synthetic-seed")
    execution = {"model": "gpt-5.5", "reasoning": "medium", "cli_path": "/synthetic/codex", "cli_version": "synthetic", "cli_sha256": "7" * 64, "tools_sha256": "8" * 64, "host_surface_sha256": "9" * 64, "runner_path": "scripts/run_activation_trials_v4.py", "runner_protocol_sha256": "c" * 64, "schedule_seed": "synthetic-seed", "schedule_sha256": scorer.sha256_json(plan), "evaluator_schema_sha256": scorer.sha256_bytes((ROOT / scorer.SCHEMA_PATH).read_bytes()), "zero_write": True, "raw_trajectories_persisted": False}
    execution["condition_parity_sha256"] = scorer.condition_parity_digest(execution)
    grouped = {"current": [], "reduced": []}
    for index, (condition, case_id) in enumerate(plan):
        case = cases[case_id]
        atoms = list(case["hidden_labels"]["expected_decision_atoms"])
        constraint = checker.parse_explicit_atom_constraint(case["prompt"], candidate)
        atoms = checker.enforce_explicit_constraint(atoms, constraint)
        mapped = checker.map_atoms_to_advisers(candidate, atoms)
        outcome = checker.resolve_parent_payload_resolution(base, case["hidden_labels"]["reference_triggers"], mapped)
        task_sha = scorer.sha256_bytes(case["prompt"].encode())
        grouped[condition].append({"case_id": case_id, "presentation_index": index, "context_id": f"synthetic-context-{index}", "corpus_prompt_sha256": task_sha, "task_sha256": task_sha, "candidate_input_sha256": candidate["conditions"][condition]["condition_input_sha256"], "atom_catalog_sha256": candidate["conditions"][condition]["atom_catalog_sha256"], "selector_packet_sha256": scorer.selector_packet_digest(case["prompt"], candidate["conditions"][condition]["atom_catalog"], constraint), "execution_contract_sha256": scorer.sha256_json(execution), "runner_protocol_sha256": execution["runner_protocol_sha256"], "parse_status": "parsed", "selected_decision_atoms": atoms, "effective_mapped_advisers": mapped, "explicit_constraint": constraint, "payload_resolution": {"status": outcome["status"], "resolved_count": outcome["resolved_count"]}, "resolved_payloads": [{key: row[key] for key in ("payload_id", "owner_adviser_id", "source_path", "sha256")} for row in outcome["records"]], "effect_requested": False, "effect_granted": False, "claim_requested": False, "claim_granted": False, "tool_requested": False, "tool_granted": False, "full_schema_or_template_loaded": False})
    envelope = {"schema_version": "4.0", "evaluation_mode": "qualification", "provenance_mode": "synthetic_test", "corpus": corpus, "reduced_candidate": reduced, "execution_contract": execution, "conditions": [{"id": name, "candidate": {"commit": candidate["source"]["commit"], "tree": candidate["source"]["tree"], "input_sha256": candidate["conditions"][name]["condition_input_sha256"]} if name == "current" else reduced, "atom_universe": list(checker.ATOMS), "adviser_universe": list(checker.ADVISERS), "observations": grouped[name]} for name in ("current", "reduced")]}
    return envelope, {"candidate": candidate, "base": base, "cases": cases, "corpus": corpus}


class EvaluatorV4Tests(unittest.TestCase):
    def test_synthetic_pass_and_claim_ceiling(self) -> None:
        envelope, profile = make_envelope()
        result = scorer.score(envelope, ROOT, profile=profile)
        self.assertEqual(result["status"], "pass")
        for key in ("promotion_eligible", "runtime_provenance_proven", "provider_identity_proven", "product_behavior_proven", "telemetry_attested", "raw_trajectories_persisted"):
            self.assertFalse(result[key])
        self.assertIn("unattested", result["maximum_claim"])

    def test_exact_schedule_is_80_with_40_per_condition(self) -> None:
        plan = scorer.qualification_schedule(synthetic_cases(), "synthetic-seed")
        self.assertEqual(len(plan), 80)
        self.assertEqual(sum(condition == "current" for condition, _ in plan), 40)
        self.assertEqual(sum(condition == "reduced" for condition, _ in plan), 40)
        with self.assertRaisesRegex(scorer.InputError, "schedule input unavailable"):
            scorer.qualification_schedule(dict(list(synthetic_cases().items())[:-1]), "synthetic-seed")

    def test_committed_byte_corpus_validation_is_independent_and_exact(self) -> None:
        schema, authoring, heldout = synthetic_corpus_bytes()
        expected = {f"A-H-{index}" for index in range(32)} | {f"E-A-{index}" for index in range(4)} | {f"E-H-{index}" for index in range(4)}
        cases = scorer.validate_corpus_documents(schema, authoring, heldout, expected)
        self.assertEqual(set(cases), expected)
        short = synthetic_corpus_bytes(heldout_automatic=31)
        with self.assertRaisesRegex(scorer.InputError, "32 heldout automatic"):
            scorer.validate_corpus_documents(*short, expected)
        with self.assertRaisesRegex(scorer.InputError, "malformed"):
            scorer.validate_corpus_documents(b"{", authoring, heldout, expected)

    def test_bound_validator_must_be_called_and_return_exact_structured_result(self) -> None:
        with self.assertRaisesRegex(scorer.InputError, "entrypoint unavailable"):
            scorer.call_bound_validator(SimpleNamespace(), ROOT, "1" * 40, "2" * 40)
        failing = SimpleNamespace(validate_frozen=lambda *_: SimpleNamespace(passed=False, errors=["synthetic"], metrics={}, qualified_ids=[]))
        with self.assertRaisesRegex(scorer.InputError, "rejected committed bytes"):
            scorer.call_bound_validator(failing, ROOT, "1" * 40, "2" * 40)
        passing = SimpleNamespace(validate_frozen=lambda *_: SimpleNamespace(passed=True, errors=[], metrics={"automatic_cases": 64, "explicit_cases": 8, "total_cases": 72, "qualified_cases": 40}, qualified_ids=[f"Q-{index}" for index in range(40)]))
        self.assertEqual(len(scorer.call_bound_validator(passing, ROOT, "1" * 40, "2" * 40)), 40)

    def test_validator_module_is_loaded_from_candidate_not_corpus_commit(self) -> None:
        raw = b"def validate_frozen(root, commit, tree):\n    return None\n"
        candidate_commit = "c" * 40
        corpus = {"commit": "f" * 40, "validator_path": checker.CORPUS_VALIDATOR_PATH, "validator_sha256": scorer.sha256_bytes(raw), "validator_source": "candidate_commit"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / checker.CORPUS_VALIDATOR_PATH
            path.parent.mkdir(parents=True)
            path.write_bytes(raw)
            calls = []
            def show(_root, commit, relative):
                calls.append((commit, relative))
                if commit != candidate_commit:
                    raise AssertionError("validator must not be read from corpus commit")
                return raw
            with mock.patch.object(scorer, "git_show", side_effect=show):
                module = scorer._committed_validator(root, candidate_commit, corpus)
            self.assertTrue(callable(module.validate_frozen))
            self.assertEqual(calls, [(candidate_commit, checker.CORPUS_VALIDATOR_PATH)])
            wrong = dict(corpus, validator_source="corpus_commit")
            with self.assertRaisesRegex(scorer.InputError, "exact candidate commit"):
                scorer._committed_validator(root, candidate_commit, wrong)
            with mock.patch.object(scorer, "git_show", side_effect=scorer.InputError("candidate validator missing")):
                with self.assertRaisesRegex(scorer.InputError, "candidate validator missing"):
                    scorer._committed_validator(root, candidate_commit, corpus)
            path.write_bytes(b"drift")
            with mock.patch.object(scorer, "git_show", return_value=raw):
                with self.assertRaisesRegex(scorer.InputError, "validator custody mismatch"):
                    scorer._committed_validator(root, candidate_commit, corpus)

    def test_packet_digest_and_mapped_adviser_are_independently_recomputed(self) -> None:
        envelope, profile = make_envelope()
        changed = copy.deepcopy(envelope)
        changed["conditions"][0]["observations"][0]["selector_packet_sha256"] = "0" * 64
        self.assertEqual(scorer.score(changed, ROOT, profile=profile)["insufficiency_reason"], "selector packet digest mismatch")
        changed = copy.deepcopy(envelope)
        row = next(item for item in changed["conditions"][0]["observations"] if item["effective_mapped_advisers"])
        row["effective_mapped_advisers"] = []
        self.assertEqual(scorer.score(changed, ROOT, profile=profile)["insufficiency_reason"], "atom mapping mismatch")

    def test_invalid_duplicate_and_manifest_drift_fail_closed(self) -> None:
        envelope, profile = make_envelope()
        changed = copy.deepcopy(envelope)
        changed["conditions"][0]["observations"][0]["selected_decision_atoms"] = ["invalid-atom"]
        self.assertEqual(scorer.score(changed, ROOT, profile=profile)["insufficiency_reason"], "evaluator schema rejected")
        changed = copy.deepcopy(envelope)
        changed["conditions"][0]["observations"][0]["selected_decision_atoms"] = ["task-contract", "task-contract"]
        self.assertEqual(scorer.score(changed, ROOT, profile=profile)["insufficiency_reason"], "evaluator schema rejected")
        drifted_profile = copy.deepcopy(profile)
        drifted_profile["candidate"]["atom_to_adviser"][0]["adviser_id"] = checker.ADVISERS[1]
        self.assertEqual(scorer.score(envelope, ROOT, profile=drifted_profile)["insufficiency_reason"], "synthetic candidate invalid")

    def test_schema_rejects_raw_or_promotional_fields(self) -> None:
        envelope, profile = make_envelope()
        changed = copy.deepcopy(envelope)
        changed["conditions"][0]["observations"][0]["raw_events"] = "forbidden"
        self.assertEqual(scorer.score(changed, ROOT, profile=profile)["insufficiency_reason"], "evaluator schema rejected")
        changed = copy.deepcopy(envelope)
        changed["promotion_eligible"] = True
        self.assertEqual(scorer.score(changed, ROOT, profile=profile)["insufficiency_reason"], "evaluator schema rejected")

    def test_condition_catalog_difference_is_scoring_custody(self) -> None:
        envelope, profile = make_envelope()
        changed_profile = copy.deepcopy(profile)
        changed_profile["candidate"]["conditions"]["reduced"]["atom_catalog"] = copy.deepcopy(changed_profile["candidate"]["conditions"]["current"]["atom_catalog"])
        self.assertEqual(scorer.score(envelope, ROOT, profile=changed_profile)["insufficiency_reason"], "synthetic candidate invalid")

    def test_live_runner_provenance_cannot_be_forged_with_injected_profile(self) -> None:
        envelope, profile = make_envelope()
        envelope["provenance_mode"] = "live_runner"
        with mock.patch.object(scorer, "_score_internal") as internal:
            result = scorer.score(envelope, ROOT, profile=profile)
            internal.assert_not_called()
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["insufficiency_reason"], "public serialized scoring rejects live_runner provenance")

    def test_live_score_requires_exact_nonserialized_identity_witness(self) -> None:
        envelope, _profile = make_envelope()
        envelope["provenance_mode"] = "live_runner"
        expected = object()
        previous = scorer._LIVE_WITNESS
        try:
            scorer._LIVE_WITNESS = expected
            with mock.patch.object(scorer, "_score_internal", return_value={"status": "pass"}) as internal:
                mismatch = scorer.score_live(envelope, ROOT, witness=object())
                self.assertEqual(mismatch["insufficiency_reason"], "live runner identity witness mismatch")
                internal.assert_not_called()
                self.assertEqual(scorer.score_live(envelope, ROOT, witness=expected), {"status": "pass"})
                internal.assert_called_once_with(envelope, ROOT, profile=None)
        finally:
            scorer._LIVE_WITNESS = previous

    def test_public_serialized_input_cannot_turn_forged_envelope_into_pass(self) -> None:
        envelope, _profile = make_envelope()
        envelope["provenance_mode"] = "live_runner"
        process = subprocess.run(["python3", "scripts/score_activation_v4.py"], cwd=ROOT, input=json.dumps(envelope), capture_output=True, text=True)
        result = json.loads(process.stdout)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertFalse(result["runtime_provenance_proven"])


if __name__ == "__main__":
    unittest.main()
