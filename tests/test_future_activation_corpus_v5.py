from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_future_activation_corpus_v5 as validator


class FutureActivationCorpusV5ValidatorTests(unittest.TestCase):
    """Tests use only synthetic hashes and custody fixtures, never corpus prompts."""

    def _root_with_staged_paths(self) -> Path:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for path in validator.CORPUS_FILES:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"{}\n" if target.suffix == ".json" else b"draft\n")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", *(path.as_posix() for path in validator.CORPUS_FILES)], cwd=root, check=True)
        return root

    def test_candidate_metadata_is_compact_reference_only_and_covers_all_atoms(self) -> None:
        payloads = validator.payload_catalog(ROOT)
        self.assertEqual({item.owner_atom for item in payloads}, set(validator.ATOMS))
        self.assertTrue(all(item.payload_id.startswith("aq-") and item.triggers for item in payloads))

    def test_canonical_bare_adviser_and_string_trigger_representation(self) -> None:
        atom = validator.ATOMS[0]
        adviser = validator.ATOM_TO_CANDIDATE_ADVISER[atom]
        trigger = validator.TRIGGER_ORDER[0]
        payloads = (validator.Payload("synthetic-payload", atom, frozenset({trigger})),)
        case = {
            "expected_decision_atoms": [atom],
            "expected_advisers": [adviser],
            "must_not_select": sorted(set(validator.ATOM_TO_CANDIDATE_ADVISER.values()) - {adviser}),
            "reference_triggers": [trigger],
            "deterministic_reference_expectations": [{"owner_atom": atom, "trigger_id": trigger, "payload_id": "synthetic-payload"}],
            "full_schema_or_template_expected": False,
        }
        self.assertTrue(validator._valid_labels(case, payloads))

    def test_rejects_prefixed_advisers_and_trigger_pair_objects(self) -> None:
        atom = validator.ATOMS[0]
        adviser = validator.ATOM_TO_CANDIDATE_ADVISER[atom]
        trigger = validator.TRIGGER_ORDER[0]
        payloads = (validator.Payload("synthetic-payload", atom, frozenset({trigger})),)
        case = {
            "expected_decision_atoms": [atom],
            "expected_advisers": [f"${adviser}"],
            "must_not_select": sorted(set(validator.ATOM_TO_CANDIDATE_ADVISER.values()) - {adviser}),
            "reference_triggers": [{"owner_atom": atom, "trigger_id": trigger}],
            "deterministic_reference_expectations": [{"owner_atom": atom, "trigger_id": trigger, "payload_id": "synthetic-payload"}],
            "full_schema_or_template_expected": False,
        }
        self.assertFalse(validator._valid_labels(case, payloads))

    def test_explicit_requires_dollar_prefixed_bare_declared_token_only(self) -> None:
        atom = validator.ATOMS[0]
        adviser = validator.ATOM_TO_CANDIDATE_ADVISER[atom]
        declared = f"${adviser}"
        aliases = validator._alias_pattern(frozenset())
        case = {
            "expected_decision_atoms": [atom],
            "expected_advisers": [adviser],
            "declared_invocation": declared,
        }
        self.assertTrue(validator._explicit_invocation_valid(case, declared, aliases))
        self.assertFalse(validator._explicit_invocation_valid({**case, "declared_invocation": adviser}, adviser, aliases))
        self.assertFalse(validator._explicit_invocation_valid({**case, "expected_advisers": [declared]}, declared, aliases))

    def test_split_ids_are_uppercase_three_digit_and_exact(self) -> None:
        authoring = [f"AQ5-A-{number:03d}" for number in range(1, 37)]
        heldout = [f"AQ5-H-{number:03d}" for number in range(1, 37)]
        self.assertTrue(validator._split_ids_valid(authoring, "authoring"))
        self.assertTrue(validator._split_ids_valid(heldout, "heldout"))
        self.assertFalse(validator._split_ids_valid([*authoring[:-1], "aq5-a-036"], "authoring"))
        self.assertFalse(validator._split_ids_valid([*heldout[:-1], "AQ5-H-36"], "heldout"))

    def test_plural_immutable_comparators_include_aq1_through_aq4(self) -> None:
        self.assertEqual(validator.COMPARATOR_BINDINGS, (validator.AQ1_BINDING, validator.AQ2_BINDING, validator.AQ3_BINDING, validator.AQ4_BINDING))
        bad = validator.ComparatorBinding("0" * 40, validator.AQ1_BINDING.tree, validator.AQ1_BINDING.paths)
        with patch.object(validator, "COMPARATOR_BINDINGS", (bad,)):
            with self.assertRaises(ValueError):
                validator.frozen_comparator_fixture(ROOT)

    def test_staging_requires_exact_four_paths_and_rejects_extra(self) -> None:
        root = self._root_with_staged_paths()
        self.assertTrue(validator.check_staged_corpus_only(root))
        (root / "extra.txt").write_bytes(b"extra\n")
        subprocess.run(["git", "add", "extra.txt"], cwd=root, check=True)
        self.assertFalse(validator.check_staged_corpus_only(root))

    def test_staging_rejects_live_drift(self) -> None:
        root = self._root_with_staged_paths()
        (root / validator.CORPUS_FILES[-1]).write_bytes(b"changed\n")
        self.assertFalse(validator.check_staged_corpus_only(root))

    def test_frozen_none_binding_fails_before_git_or_corpus_read(self) -> None:
        with patch.object(validator, "FROZEN_CORPUS_COMMIT", None), patch.object(validator, "FROZEN_CORPUS_TREE", None), patch.object(validator, "_git", side_effect=AssertionError("must not read")):
            result = validator.validate_frozen(ROOT)
        self.assertEqual(result.errors, ("AQ5 frozen corpus binding unavailable",))
        self.assertEqual(result.metrics, {})
        self.assertEqual(result.qualified_ids, ())

    def test_frozen_wrong_commit_and_tree_fail_closed(self) -> None:
        result = validator.validate_frozen(ROOT, "0" * 40, "1" * 40)
        self.assertEqual(result.errors, ("AQ5 frozen corpus binding unavailable",))

    def test_frozen_missing_path_returns_generic_byte_mismatch(self) -> None:
        commit, tree = "a" * 40, "b" * 40
        def fake_git(_root: Path, args: list[str], *, capture: bool = False) -> bytes | None:
            if args[:2] == ["cat-file", "-e"]:
                return b""
            if args[:1] == ["rev-parse"]:
                return (tree + "\n").encode()
            return None
        with patch.object(validator, "FROZEN_CORPUS_COMMIT", commit), patch.object(validator, "FROZEN_CORPUS_TREE", tree), patch.object(validator, "_git", side_effect=fake_git):
            result = validator.validate_frozen(ROOT, commit, tree)
        self.assertEqual(result.errors, ("AQ5 frozen corpus byte mismatch",))

    def test_frozen_observed_wrong_tree_returns_generic_tree_mismatch(self) -> None:
        commit, tree = "a" * 40, "b" * 40
        def fake_git(_root: Path, args: list[str], *, capture: bool = False) -> bytes | None:
            if args[:2] == ["cat-file", "-e"]:
                return b""
            if args[:1] == ["rev-parse"]:
                return b"c" * 40 + b"\n"
            raise AssertionError("corpus must not be read after tree mismatch")
        with patch.object(validator, "FROZEN_CORPUS_COMMIT", commit), patch.object(validator, "FROZEN_CORPUS_TREE", tree), patch.object(validator, "_git", side_effect=fake_git):
            result = validator.validate_frozen(ROOT, commit, tree)
        self.assertEqual(result.errors, ("AQ5 frozen corpus tree mismatch",))

    def test_frozen_live_byte_drift_returns_generic_byte_mismatch(self) -> None:
        root = self._root_with_staged_paths()
        commit, tree = "a" * 40, "b" * 40
        source = b"frozen\n"
        digests = {path: validator.hashlib.sha256(source).hexdigest() for path in validator.CORPUS_FILES}
        def fake_git(_root: Path, args: list[str], *, capture: bool = False) -> bytes | None:
            if args[:2] == ["cat-file", "-e"]:
                return b""
            if args[:1] == ["rev-parse"]:
                return (tree + "\n").encode()
            if args[:1] == ["show"]:
                return source
            raise AssertionError("unexpected git operation")
        with patch.object(validator, "FROZEN_CORPUS_COMMIT", commit), patch.object(validator, "FROZEN_CORPUS_TREE", tree), patch.object(validator, "FROZEN_CORPUS_SHA256", digests), patch.object(validator, "_git", side_effect=fake_git):
            result = validator.validate_frozen(root, commit, tree)
        self.assertEqual(result.errors, ("AQ5 frozen corpus byte mismatch",))

    def test_historical_reuse_is_hash_only(self) -> None:
        digest = "a" * 64
        fixture = validator.ComparatorFixture(frozenset({digest}), frozenset())
        with patch.object(validator, "prompt_digest", return_value=digest):
            self.assertTrue(validator._historical_reuse_detected([{ "prompt": "" }], fixture))

    def test_default_authoritative_validation_is_zero_write_and_exact(self) -> None:
        with patch.object(Path, "write_bytes", side_effect=AssertionError("validator must not write")):
            result = validator.validate_frozen(ROOT)
        self.assertTrue(result.passed, result.errors)
        self.assertEqual(result.metrics, {
            "automatic_cases": 64,
            "explicit_cases": 8,
            "total_cases": 72,
            "qualified_cases": 40,
        })
        self.assertEqual(len(result.qualified_ids), 40)
        self.assertEqual(len(set(result.qualified_ids)), 40)

    def test_frozen_receipt_binds_exact_commit_tree_and_file_digests(self) -> None:
        self.assertEqual(validator.FROZEN_CORPUS_COMMIT, "39fd55df96e99e38d51d5fee13faa6b6294f9c43")
        self.assertEqual(validator.FROZEN_CORPUS_TREE, "b7b9eb94ffe14a59e924ac2c40926e1a2dc513dd")
        self.assertEqual(validator.FROZEN_CORPUS_SHA256, {
            validator.CORPUS_FILES[0]: "0afb63ea9c89f48d1455dcead39453ebf05a8ed438517249b21f8c7ca90d63ea",
            validator.CORPUS_FILES[1]: "69e5e796f191165a2556054caf3aa961e4a03a48025ac18bccc6b2e7b1bca4b3",
            validator.CORPUS_FILES[2]: "c884713124f12271cd7bdd4cbed43f47312f2d15c0f16339ab954b9db65b971f",
            validator.CORPUS_FILES[3]: "4a0d9a621173e816cad0c44bd9717b40ff8739fd724d2dca9be3916224ee4027",
        })


if __name__ == "__main__":
    unittest.main()
