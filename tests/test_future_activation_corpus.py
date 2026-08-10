from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_future_activation_corpus


ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path("evals/foundation-v4/future-activation-v2")


class FutureActivationCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.comparator_fixture = validate_future_activation_corpus.frozen_comparator_fixture(ROOT)

    def _draft_validate(self, root: Path):
        return validate_future_activation_corpus.validate(
            root, enforce_frozen_corpus=False, comparator_fixture=self.comparator_fixture,
        )

    def test_future_corpus_is_structurally_ready(self) -> None:
        passed, errors, metrics = validate_future_activation_corpus.validate(ROOT)
        self.assertTrue(passed, errors)
        self.assertEqual(metrics, {"automatic_cases": 64, "explicit_cases": 8, "total_cases": 72})

    def _copy_root(self) -> Path:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(ROOT / "evals", root / "evals")
        return root

    def _document(self, root: Path, name: str) -> tuple[Path, dict]:
        path = root / CORPUS / name
        return path, json.loads(path.read_text(encoding="utf-8"))

    def _stage_future_corpus(self, root: Path, paths: list[Path] | None = None) -> None:
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        staged = paths or list(validate_future_activation_corpus.STAGED_CORPUS_FILES)
        subprocess.run(["git", "add", *(str(path) for path in staged)], cwd=root, check=True)

    def _frozen_fixture(self) -> tuple[Path, str, str]:
        """A disposable repository for exercising the binding mechanism itself."""
        root = self._copy_root()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "evals"], cwd=root, check=True)
        subprocess.run(
            ["git", "-c", "user.name=unit", "-c", "user.email=unit@example.invalid", "commit", "-qm", "fixture"],
            cwd=root, check=True,
        )
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, stdout=subprocess.PIPE, check=True).stdout.decode().strip()
        tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=root, stdout=subprocess.PIPE, check=True).stdout.decode().strip()
        return root, commit, tree

    def test_rejects_leakage_authority_and_native_reference(self) -> None:
        root = self._copy_root()
        path, document = self._document(root, "activation-authoring.json")
        document["cases"][0]["prompt"] += " graph workflow engineering"
        document["cases"][0]["authority"] = {"effect_authority": False}
        native = next(case for case in document["cases"] if case["category"] == "native-sufficient")
        native["hidden_labels"]["reference_triggers"] = ["reference-isolation"]
        path.write_text(json.dumps(document), encoding="utf-8")
        passed, errors, _ = self._draft_validate(root)
        self.assertFalse(passed)
        self.assertTrue(any("automatic name leakage" in error for error in errors))
        self.assertTrue(any("authority" in error for error in errors))
        self.assertTrue(any("native-sufficient" in error for error in errors))

    def test_rejects_explicit_and_composition_mutations(self) -> None:
        root = self._copy_root()
        path, document = self._document(root, "activation-heldout.json")
        explicit = next(case for case in document["cases"] if case["mode"] == "explicit")
        explicit["prompt"] += " $agentic-engineering"
        neighbor = next(case for case in document["cases"] if case["near_neighbor_kind"] == "exactly_two")
        neighbor["hidden_labels"]["expected_advisers"] = ["engineering-learning-loop"]
        neighbor["hidden_labels"]["must_not_select"] = []
        path.write_text(json.dumps(document), encoding="utf-8")
        passed, errors, _ = self._draft_validate(root)
        self.assertFalse(passed)
        self.assertTrue(any("explicit invocation" in error for error in errors))
        self.assertTrue(any("exactly-two" in error for error in errors))

    def test_rejects_cross_split_case_whitespace_prompt_and_family_reuse(self) -> None:
        root = self._copy_root()
        author_path, authoring = self._document(root, "activation-authoring.json")
        held_path, heldout = self._document(root, "activation-heldout.json")
        heldout["cases"][0]["prompt"] = f"  {authoring['cases'][0]['prompt'].upper()}\n"
        heldout["cases"][0]["family_id"] = authoring["cases"][0]["family_id"]
        author_path.write_text(json.dumps(authoring), encoding="utf-8")
        held_path.write_text(json.dumps(heldout), encoding="utf-8")
        passed, errors, _ = self._draft_validate(root)
        self.assertFalse(passed)
        self.assertTrue(any("prompt uniqueness" in error for error in errors))
        self.assertTrue(any("family uniqueness" in error for error in errors))

    def test_rejects_injected_historical_case_and_space_normalized_digest(self) -> None:
        root = self._copy_root()
        _, document = self._document(root, "activation-authoring.json")
        prompt = document["cases"][0]["prompt"]
        real_exact = self.comparator_fixture.old_exact_digests
        real_normalized = self.comparator_fixture.old_normalized_digests
        self.assertTrue(real_exact)
        self.assertTrue(real_normalized)
        collisions = (
            ({validate_future_activation_corpus.exact_digest(prompt)}, set()),
            (set(), {validate_future_activation_corpus.digest(f"  {prompt.upper()}\n")}),
        )
        for old_digests in collisions:
            fixture = validate_future_activation_corpus.ComparatorFixture(
                self.comparator_fixture.adviser_names, frozenset(old_digests[0]), frozenset(old_digests[1]),
            )
            passed, errors, _ = validate_future_activation_corpus.validate(
                root, enforce_frozen_corpus=False, comparator_fixture=fixture,
            )
            self.assertFalse(passed)
            self.assertTrue(any("historical prompt reuse" in error for error in errors))

    def test_rejects_per_split_near_neighbor_mix(self) -> None:
        root = self._copy_root()
        path, document = self._document(root, "activation-heldout.json")
        neighbor = [case for case in document["cases"] if case["near_neighbor_kind"] == "exactly_two"][1]
        neighbor["near_neighbor_kind"] = "precedence"
        neighbor["hidden_labels"]["expected_advisers"] = ["agentic-engineering"]
        neighbor["hidden_labels"]["must_not_select"] = ["codex-task-contract"]
        path.write_text(json.dumps(document), encoding="utf-8")
        passed, errors, _ = self._draft_validate(root)
        self.assertFalse(passed)
        self.assertTrue(any("near-neighbor distribution" in error for error in errors))

    def test_rejects_blinding_overlap_and_malformed_precedence(self) -> None:
        root = self._copy_root()
        path, document = self._document(root, "activation-authoring.json")
        document["cases"][0]["condition_blind"] = False
        document["cases"][1]["hidden_labels"]["must_not_select"] = ["agentic-engineering"]
        precedence = next(case for case in document["cases"] if case["near_neighbor_kind"] == "precedence")
        precedence["hidden_labels"]["must_not_select"] = []
        path.write_text(json.dumps(document), encoding="utf-8")
        passed, errors, _ = self._draft_validate(root)
        self.assertFalse(passed)
        self.assertTrue(any("blinding" in error for error in errors))
        self.assertTrue(any("hidden labels" in error for error in errors))
        self.assertTrue(any("precedence" in error for error in errors))

    def test_rejects_readme_authority_and_commit_binding(self) -> None:
        root = self._copy_root()
        path = root / CORPUS / "README.md"
        readme = path.read_text(encoding="utf-8")
        path.write_text(readme.replace("No routing, outcome, or candidate authority is conferred by this corpus", "Candidate authority is unspecified"), encoding="utf-8")
        passed, errors, _ = self._draft_validate(root)
        self.assertFalse(passed)
        self.assertTrue(any("README authority" in error for error in errors))
        for identity in ("0123456789ab", "0123456789abcdef0123456789abcdef01234567"):
            path.write_text(readme + f"\nCandidate commit: {identity}\n", encoding="utf-8")
            passed, errors, _ = self._draft_validate(root)
            self.assertFalse(passed)
            self.assertTrue(any("README commit binding" in error for error in errors))

    def test_authoritative_binding_requires_the_exact_frozen_commit_and_tree(self) -> None:
        self.assertEqual(validate_future_activation_corpus.FROZEN_CORPUS_COMMIT, "25de0cb1fe86a802768de9bf64659206d69650d0")
        self.assertEqual(validate_future_activation_corpus.FROZEN_CORPUS_TREE, "e5faff4b1a5ba678a7df1727b5bda3b3d0afe00a")
        self.assertEqual(validate_future_activation_corpus.FROZEN_COMPARATOR_COMMIT, "407a2ac124856f0ce1fa33af8a61d0607e413820")
        self.assertEqual(validate_future_activation_corpus.FROZEN_COMPARATOR_TREE, "8314ca6ad82fa4687720692d8c5762c7aabf6261")
        root, commit, tree = self._frozen_fixture()
        with patch.multiple(
            validate_future_activation_corpus,
            FROZEN_CORPUS_COMMIT=commit, FROZEN_CORPUS_TREE=tree,
            FROZEN_COMPARATOR_COMMIT=commit, FROZEN_COMPARATOR_TREE=tree,
        ):
            passed, errors, _ = validate_future_activation_corpus.validate(root)
        self.assertTrue(passed, errors)
        with patch.object(validate_future_activation_corpus, "FROZEN_CORPUS_COMMIT", "0" * 40):
            errors = validate_future_activation_corpus.frozen_corpus_errors(root)
        self.assertEqual(errors, ["frozen corpus commit unavailable"])
        with patch.multiple(validate_future_activation_corpus, FROZEN_CORPUS_COMMIT=commit, FROZEN_CORPUS_TREE="0" * 40):
            errors = validate_future_activation_corpus.frozen_corpus_errors(root)
        self.assertEqual(errors, ["frozen corpus tree mismatch"])

    def test_authoritative_binding_rejects_live_byte_drift_and_missing_git_path(self) -> None:
        for name in ("README.md", "activation-schema.json", "activation-authoring.json", "activation-heldout.json"):
            root, commit, tree = self._frozen_fixture()
            path = root / CORPUS / name
            path.write_bytes(path.read_bytes() + b"\n")
            with patch.multiple(
                validate_future_activation_corpus,
                FROZEN_CORPUS_COMMIT=commit, FROZEN_CORPUS_TREE=tree,
                FROZEN_COMPARATOR_COMMIT=commit, FROZEN_COMPARATOR_TREE=tree,
            ):
                passed, errors, _ = validate_future_activation_corpus.validate(root)
            self.assertFalse(passed, name)
            self.assertIn("frozen corpus byte mismatch", errors, name)

        root, commit, tree = self._frozen_fixture()
        missing = CORPUS / "missing-fixture.json"
        with patch.multiple(
            validate_future_activation_corpus,
            FROZEN_CORPUS_COMMIT=commit,
            FROZEN_CORPUS_TREE=tree,
            STAGED_CORPUS_FILES=validate_future_activation_corpus.STAGED_CORPUS_FILES + (missing,),
        ):
            errors = validate_future_activation_corpus.frozen_corpus_errors(root)
        self.assertIn("frozen corpus byte mismatch", errors)

    def test_fixed_comparators_survive_live_legacy_and_routing_drift(self) -> None:
        root = self._copy_root()
        routing_path = root / "evals/routing-cases.json"
        routing = json.loads(routing_path.read_text(encoding="utf-8"))
        routing["cases"] = []
        routing_path.write_text(json.dumps(routing), encoding="utf-8")
        future_path, future = self._document(root, "activation-authoring.json")
        future["cases"][0]["prompt"] += " agent-first-software-engineering"
        future_path.write_text(json.dumps(future), encoding="utf-8")
        passed, errors, _ = self._draft_validate(root)
        self.assertFalse(passed)
        self.assertTrue(any("automatic name leakage" in error for error in errors))

        root = self._copy_root()
        legacy_path = root / "evals/foundation-v4/activation-authoring.json"
        legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
        legacy["cases"] = []
        legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
        source = subprocess.run(
            [
                "git", "show",
                f"{validate_future_activation_corpus.FROZEN_COMPARATOR_COMMIT}:evals/foundation-v4/activation-authoring.json",
            ],
            cwd=ROOT, stdout=subprocess.PIPE, check=True,
        )
        historic_prompt = json.loads(source.stdout)["cases"][0]["prompt"]
        future_path, future = self._document(root, "activation-authoring.json")
        future["cases"][0]["prompt"] = historic_prompt
        future_path.write_text(json.dumps(future), encoding="utf-8")
        passed, errors, _ = self._draft_validate(root)
        self.assertFalse(passed)
        self.assertTrue(any("historical prompt reuse" in error for error in errors))

    def test_authoritative_validation_fails_closed_for_comparator_identity_or_path(self) -> None:
        with patch.object(validate_future_activation_corpus, "FROZEN_COMPARATOR_COMMIT", "0" * 40):
            passed, errors, _ = validate_future_activation_corpus.validate(ROOT)
        self.assertFalse(passed)
        self.assertEqual(errors, ["corpus input unavailable or invalid"])
        with patch.object(validate_future_activation_corpus, "FROZEN_COMPARATOR_TREE", "0" * 40):
            passed, errors, _ = validate_future_activation_corpus.validate(ROOT)
        self.assertFalse(passed)
        self.assertEqual(errors, ["corpus input unavailable or invalid"])
        missing = validate_future_activation_corpus.COMPARATOR_FILES + (Path("evals/missing.json"),)
        with patch.object(validate_future_activation_corpus, "COMPARATOR_FILES", missing):
            passed, errors, _ = validate_future_activation_corpus.validate(ROOT)
        self.assertFalse(passed)
        self.assertEqual(errors, ["corpus input unavailable or invalid"])

    def test_cli_invalid_input_is_generic_and_zero_write(self) -> None:
        validator = ROOT / "scripts" / "validate_future_activation_corpus.py"
        before = validator.read_bytes()
        result = subprocess.run(
            [sys.executable, str(validator), "--not-an-option"],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, "future-activation-corpus: FAIL\n- error: structural rule failed\n")
        self.assertEqual(validator.read_bytes(), before)

    def test_staged_corpus_custody_rejects_extra_or_missing_paths(self) -> None:
        clean_root = self._copy_root()
        self._stage_future_corpus(clean_root)
        passed, errors, _ = validate_future_activation_corpus.validate(
            clean_root, require_staged_corpus_only=True, enforce_frozen_corpus=False,
            comparator_fixture=self.comparator_fixture,
        )
        self.assertTrue(passed, errors)

        extra_root = self._copy_root()
        self._stage_future_corpus(extra_root)
        extra = extra_root / "unrelated.txt"
        extra.write_text("extra", encoding="utf-8")
        subprocess.run(["git", "add", "unrelated.txt"], cwd=extra_root, check=True)
        passed, errors, _ = validate_future_activation_corpus.validate(
            extra_root, require_staged_corpus_only=True, enforce_frozen_corpus=False,
            comparator_fixture=self.comparator_fixture,
        )
        self.assertFalse(passed)
        self.assertTrue(any("staged corpus custody" in error for error in errors))

        missing_root = self._copy_root()
        self._stage_future_corpus(missing_root, list(validate_future_activation_corpus.STAGED_CORPUS_FILES[:-1]))
        passed, errors, _ = validate_future_activation_corpus.validate(
            missing_root, require_staged_corpus_only=True, enforce_frozen_corpus=False,
            comparator_fixture=self.comparator_fixture,
        )
        self.assertFalse(passed)
        self.assertTrue(any("staged corpus custody" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
