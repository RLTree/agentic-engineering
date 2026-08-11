from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_ae_sq1_candidate as checker  # noqa: E402

STRUCTURAL_TEST_BINDINGS = (
    ("historical_digest_test", "tests/test_ae_sq1_historical_task_digests.py"),
    ("slec_test", "tests/test_ae_sq1_slec.py"),
    ("corpus_contract_test", "tests/test_ae_sq1_corpus_contract.py"),
    ("evaluator_test", "tests/test_ae_sq1_evaluator.py"),
    ("run_index_test", "tests/test_ae_sq1_run_index.py"),
    ("candidate_checker_test", "tests/test_check_ae_sq1_candidate.py"),
    ("runner_test", "tests/test_run_ae_sq1_aq.py"),
)


class CandidateCheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.value = json.loads(
            (ROOT / "evals/ae-sq1/candidate-manifest.json").read_text(encoding="utf-8")
        )

    def bound(self) -> dict:
        value = copy.deepcopy(self.value)
        value["candidate_freeze"] = {"commit": "a" * 40, "tree": "b" * 40}
        for index, row in enumerate(value["files"]):
            row["commit"] = "a" * 40
            row["tree"] = "b" * 40
            row["blob"] = f"{index + 1:040x}"
            row["sha256"] = f"{index + 1:064x}"
        return value

    def test_bound_fixture_rejects_an_injected_placeholder(self) -> None:
        value = self.bound()
        value["files"][0]["sha256"] = "UNBOUND"
        with self.assertRaisesRegex(checker.CandidateError, "placeholder"):
            checker._validate_manifest(value)

    def test_only_earlier_authority_roles_may_split_from_component_freeze(self) -> None:
        value = self.bound()
        for index, role in enumerate(("program_authority", "external_evidence")):
            row = value["files"][index]
            self.assertEqual(row["role"], role)
            row["commit"] = f"{index + 12:040x}"
            row["tree"] = f"{index + 14:040x}"
        self.assertEqual(checker._validate_manifest(value)["candidate_id"], "SLEC-1")

        for index, row in enumerate(value["files"][2:], start=2):
            for field, replacement in (("commit", "c" * 40), ("tree", "d" * 40)):
                changed = copy.deepcopy(value)
                changed["files"][index][field] = replacement
                with (
                    self.subTest(role=row["role"], field=field),
                    self.assertRaises(checker.CandidateError),
                ):
                    checker._validate_manifest(changed)

    def test_structural_test_roles_are_exact_and_ordered(self) -> None:
        width = len(STRUCTURAL_TEST_BINDINGS)
        self.assertEqual(checker.ROLE_PATHS[-width:], STRUCTURAL_TEST_BINDINGS)
        self.assertEqual(
            tuple((row["role"], row["path"]) for row in self.value["files"][-width:]),
            STRUCTURAL_TEST_BINDINGS,
        )

    def test_structural_test_rows_fail_closed_when_omitted_or_forged(self) -> None:
        value = self.bound()
        indices = {row["role"]: index for index, row in enumerate(value["files"])}
        for role, _path in STRUCTURAL_TEST_BINDINGS:
            index = indices[role]

            omitted = copy.deepcopy(value)
            del omitted["files"][index]
            with (
                self.subTest(role=role, mutation="omitted"),
                self.assertRaisesRegex(checker.CandidateError, "ledger is incomplete"),
            ):
                checker._validate_manifest(omitted)

            forged = copy.deepcopy(value)
            forged["files"][index] = copy.deepcopy(value["files"][0])
            forged["files"][index]["role"] = role
            with (
                self.subTest(role=role, mutation="forged"),
                self.assertRaisesRegex(
                    checker.CandidateError, "binding is incomplete or reordered"
                ),
            ):
                checker._validate_manifest(forged)

    def test_exact_roles_runtime_and_cross_program_are_closed(self) -> None:
        value = self.bound()
        self.assertEqual(checker._validate_manifest(value)["program_id"], "AE-SQ1")
        for mutation in ("program", "role", "path", "hash", "runtime"):
            changed = copy.deepcopy(value)
            if mutation == "program":
                changed["program_id"] = "AQ8"
            elif mutation == "role":
                changed["role_order"][0] = "other"
            elif mutation == "path":
                changed["files"][0]["path"] = "../escape"
            elif mutation == "hash":
                changed["files"][0]["sha256"] = "a" * 63
            else:
                changed["runtime"]["fallback"] = True
            with (
                self.subTest(mutation=mutation),
                self.assertRaises(checker.CandidateError),
            ):
                checker._validate_manifest(changed)

    def test_provisional_hashes_never_claim_qualification(self) -> None:
        values = checker.provisional_hashes(ROOT)
        self.assertEqual(tuple(values), checker.ROLE_ORDER)
        self.assertRegex(values["candidate_checker"], r"^[0-9a-f]{64}$")
        self.assertRegex(values["run_index"], r"^[0-9a-f]{64}$")
        for role, _path in STRUCTURAL_TEST_BINDINGS:
            with self.subTest(role=role):
                self.assertRegex(values[role], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
