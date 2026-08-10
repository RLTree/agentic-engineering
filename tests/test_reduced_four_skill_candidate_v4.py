from __future__ import annotations

import copy
import importlib.util
import itertools
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load_module("scripts/check_reduced_four_skill_candidate_v4.py", "aq4_checker_test")


class CandidateV4Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate = checker.load_candidate(ROOT)
        self.base, _ = checker.load_base_candidate(ROOT)

    def test_bound_draft_is_structurally_valid_and_has_no_placeholders(self) -> None:
        self.assertEqual(checker.validate_candidate(self.candidate, ROOT, allow_unbound=True), [])
        self.assertEqual(checker.validate_candidate(self.candidate, ROOT, allow_unbound=False), [])
        self.assertEqual(checker.unresolved_bindings(self.candidate), [])
        self.assertIsNone(checker.require_bound(self.candidate))

    def test_mapping_is_total_injective_and_exhaustive_for_legal_subsets(self) -> None:
        self.assertEqual(checker.atom_mapping(self.candidate), checker.ATOM_TO_ADVISER)
        for size in range(3):
            for atoms in itertools.combinations(checker.ATOMS, size):
                mapped = checker.map_atoms_to_advisers(self.candidate, atoms)
                self.assertEqual(len(mapped), len(atoms))
                self.assertEqual(len(mapped), len(set(mapped)))

    def test_invalid_and_duplicate_atoms_are_rejected(self) -> None:
        for atoms in (["invalid-atom"], [checker.ATOMS[0], checker.ATOMS[0]], list(checker.ATOMS[:3])):
            with self.assertRaisesRegex(ValueError, "closed 0-2"):
                checker.map_atoms_to_advisers(self.candidate, atoms)

    def test_exact_token_bare_alias_and_ambiguity(self) -> None:
        exact = checker.parse_explicit_atom_constraint("Use $codex-task-contract for this decision.", self.candidate)
        self.assertEqual(exact, {"status": "exact", "atom_id": "task-contract"})
        self.assertEqual(checker.enforce_explicit_constraint(["task-contract"], exact), ["task-contract"])
        with self.assertRaisesRegex(ValueError, "explicit constraint"):
            checker.enforce_explicit_constraint(["verification-strategy"], exact)
        bare = checker.parse_explicit_atom_constraint("codex-task-contract is a bare filename label.", self.candidate)
        self.assertEqual(bare, {"status": "none", "atom_id": None})
        ambiguous = checker.parse_explicit_atom_constraint("Use $codex-task-contract and $verification-strategy-engineering.", self.candidate)
        self.assertEqual(ambiguous, {"status": "ambiguous", "atom_id": None})
        self.assertEqual(checker.enforce_explicit_constraint([], ambiguous), [])
        with self.assertRaisesRegex(ValueError, "explicit constraint"):
            checker.enforce_explicit_constraint(["task-contract"], ambiguous)

    def test_reference_resolution_accepts_mapped_advisers_not_atoms(self) -> None:
        mapped = checker.map_atoms_to_advisers(self.candidate, ["verification-strategy"])
        outcome = checker.resolve_parent_payload_resolution(self.base, ["verification-evidence"], mapped)
        self.assertEqual(outcome["status"], "resolved")
        self.assertLessEqual(len(outcome["records"]), 3)
        with self.assertRaisesRegex(ValueError, "mapped adviser IDs"):
            checker.resolve_parent_payload_resolution(self.base, ["verification-evidence"], ["verification-strategy"])

    def test_condition_catalogs_are_distinct_but_fixed_complete_boundaries_match(self) -> None:
        current = self.candidate["conditions"]["current"]["atom_catalog"]
        reduced = self.candidate["conditions"]["reduced"]["atom_catalog"]
        self.assertNotEqual(checker.canonical_sha256(current), checker.canonical_sha256(reduced))
        for left, right in zip(current, reduced, strict=True):
            self.assertNotEqual(left["declared_scope"], right["declared_scope"])
            self.assertEqual(left["positive_boundary"], right["positive_boundary"])
            self.assertEqual(left["admission_rule"], right["admission_rule"])
            self.assertEqual(left["pairwise_exclusions"], right["pairwise_exclusions"])
            self.assertEqual({item["atom_id"] for item in left["pairwise_exclusions"]}, set(checker.ATOMS) - {left["atom_id"]})

    def test_mapping_and_manifest_drift_are_detected(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["atom_to_adviser"][0]["adviser_id"] = checker.ADVISERS[1]
        errors = checker.validate_candidate(changed, ROOT, allow_unbound=True)
        self.assertTrue(any("mapping" in error for error in errors))
        changed = copy.deepcopy(self.candidate)
        changed["base_candidate"]["sha256"] = "0" * 64
        errors = checker.validate_candidate(changed, ROOT, allow_unbound=True)
        self.assertIn("base candidate digest mismatch", errors)

    def test_manifest_and_evaluator_surface_are_exact_closed_and_ordered(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["unexpected"] = True
        self.assertIn("candidate top-level surface is not exact and closed", checker.validate_candidate(changed, ROOT, allow_unbound=True))
        changed = copy.deepcopy(self.candidate)
        changed["evaluator_surface"]["unexpected"] = True
        self.assertIn("evaluator surface mismatch", checker.validate_candidate(changed, ROOT, allow_unbound=True))
        changed = copy.deepcopy(self.candidate)
        changed["evaluator_surface"]["files"].append(copy.deepcopy(changed["evaluator_surface"]["files"][0]))
        self.assertIn("evaluator file path set is not exact, unique, and ordered", checker.validate_candidate(changed, ROOT, allow_unbound=True))
        changed = copy.deepcopy(self.candidate)
        changed["evaluator_surface"]["files"][0], changed["evaluator_surface"]["files"][1] = changed["evaluator_surface"]["files"][1], changed["evaluator_surface"]["files"][0]
        self.assertIn("evaluator file path set is not exact, unique, and ordered", checker.validate_candidate(changed, ROOT, allow_unbound=True))
        changed = copy.deepcopy(self.candidate)
        changed["evaluator_surface"]["files"][-1]["path"] = "synthetic/validator.py"
        self.assertIn("evaluator file path set is not exact, unique, and ordered", checker.validate_candidate(changed, ROOT, allow_unbound=True))

    def test_corpus_and_validator_paths_are_canonical_not_candidate_chosen(self) -> None:
        for key in ("schema_path", "authoring_path", "heldout_path", "validator_path"):
            changed = copy.deepcopy(self.candidate)
            changed["corpus"][key] = f"synthetic/{key}"
            errors = checker.validate_candidate(changed, ROOT, allow_unbound=True)
            self.assertIn("corpus paths are not the canonical code-owned set", errors)

    def test_validator_source_role_is_closed_to_candidate_commit(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["corpus"]["validator_source"] = "corpus_commit"
        self.assertIn("validator source must be the exact candidate commit", checker.validate_candidate(changed, ROOT, allow_unbound=True))
        changed = copy.deepcopy(self.candidate)
        del changed["corpus"]["validator_source"]
        self.assertIn("corpus binding shape mismatch", checker.validate_candidate(changed, ROOT, allow_unbound=True))

    def test_aq3_protocol_files_remain_byte_identical_to_head(self) -> None:
        paths = [
            "scripts/check_reduced_four_skill_candidate.py",
            "scripts/score_activation.py",
            "scripts/run_activation_trials.py",
            "evals/foundation-v4/selector-output-schema.json",
            "evals/foundation-v4/activation-evaluator-schema.json",
            "evals/foundation-v4/reduced-four-skills/candidate.json",
        ]
        result = subprocess.run(["git", "diff", "--exit-code", "--", *paths], cwd=ROOT, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout.decode(errors="replace"))


if __name__ == "__main__":
    unittest.main()
