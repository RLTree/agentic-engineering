from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path("evals/foundation-v4/future-activation-v3")
sys.path.insert(0, str(ROOT / "scripts"))
import validate_future_activation_corpus_v3 as validator


class FutureActivationCorpusV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Read immutable comparators once from the real historical repository.
        cls.comparator = validator.frozen_comparator_fixture(ROOT)

    def _copy_root(self) -> Path:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(ROOT / "evals", root / "evals")
        return root

    def _document(self, root: Path, name: str) -> tuple[Path, dict]:
        path = root / CORPUS / name
        return path, json.loads(path.read_text(encoding="utf-8"))

    def _canonicalize_reference_expectations(self, root: Path) -> None:
        """Make a disposable structural fixture from the fixed catalog only."""
        for name in ("activation-authoring.json", "activation-heldout.json"):
            path, document = self._document(root, name)
            for case in document["cases"]:
                labels = case["hidden_labels"]
                labels["reference_expectations"] = list(
                    validator.minimum_reference_expectations(labels["expected_advisers"], labels["reference_triggers"]) or ()
                )
            path.write_text(json.dumps(document), encoding="utf-8")

    def _validate_draft(self, root: Path):
        return validator.validate(root, comparator_fixture=self.comparator, enforce_frozen_corpus=False)

    def _stage_corpus(self, root: Path, paths: tuple[Path, ...] | None = None) -> None:
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", *(str(path) for path in (paths or validator.CORPUS_FILES))], cwd=root, check=True)

    def _frozen_fixture(self) -> tuple[Path, str, str]:
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

    def test_working_tree_structural_contract_and_exact_staged_custody(self) -> None:
        root = self._copy_root()
        self._canonicalize_reference_expectations(root)
        self._stage_corpus(root)
        passed, errors, metrics = validator.validate(root, working_tree=True, comparator_fixture=self.comparator)
        self.assertTrue(passed, errors)
        self.assertEqual(metrics, {"automatic_cases": 64, "explicit_cases": 8, "total_cases": 72})

    def test_authoritative_default_requires_exact_frozen_live_inputs(self) -> None:
        self.assertEqual(validator.FROZEN_CORPUS_COMMIT, "ee7be80441ce06e53615df74505a1b4549a4aa90")
        self.assertEqual(validator.FROZEN_CORPUS_TREE, "e1c83c852b26a0c06753c591a689e1ecf00022b7")
        passed, errors, metrics = validator.validate(ROOT)
        self.assertTrue(passed, errors)
        self.assertEqual(metrics, {"automatic_cases": 64, "explicit_cases": 8, "total_cases": 72})

    def test_comparator_is_independent_of_live_legacy_drift(self) -> None:
        root = self._copy_root()
        path, document = self._document(root, "activation-authoring.json")
        document["cases"][0]["prompt"] += " agentic engineering"
        path.write_text(json.dumps(document), encoding="utf-8")
        legacy_path = root / "evals" / "routing-cases.json"
        legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
        legacy["cases"] = []
        legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
        passed, errors, _ = self._validate_draft(root)
        self.assertFalse(passed)
        self.assertIn("authoring: automatic adviser-name leakage", errors)
        with self.assertRaises(ValueError):
            validator.frozen_comparator_fixture(root)

    def test_rejects_wrong_missing_comparator_commit_tree_or_path(self) -> None:
        bad_commit = validator.ComparatorBinding("0" * 40, validator.AQ1_BINDING.tree, validator.AQ1_BINDING.paths)
        bad_tree = validator.ComparatorBinding(validator.AQ1_BINDING.commit, "0" * 40, validator.AQ1_BINDING.paths)
        missing_path = validator.ComparatorBinding(validator.AQ1_BINDING.commit, validator.AQ1_BINDING.tree, validator.AQ1_BINDING.paths + (Path("evals/missing.json"),))
        for binding in (bad_commit, bad_tree, missing_path):
            with patch.object(validator, "COMPARATOR_BINDINGS", (binding, validator.AQ2_BINDING)):
                passed, errors, _ = validator.validate(ROOT, enforce_frozen_corpus=False)
            self.assertFalse(passed)
            self.assertEqual(errors, ["corpus input unavailable or invalid"])

    def test_rejects_exact_and_normalized_historical_prompt_reuse(self) -> None:
        source = subprocess.run(
            ["git", "show", f"{validator.AQ1_BINDING.commit}:{validator.AQ1_BINDING.paths[1].as_posix()}"],
            cwd=ROOT, stdout=subprocess.PIPE, check=True,
        )
        historical = json.loads(source.stdout)["cases"][0]["prompt"]
        for prompt in (historical, f"  {historical.upper()}\n"):
            root = self._copy_root()
            path, document = self._document(root, "activation-authoring.json")
            document["cases"][0]["prompt"] = prompt
            path.write_text(json.dumps(document), encoding="utf-8")
            passed, errors, _ = self._validate_draft(root)
            self.assertFalse(passed)
            self.assertIn("historical prompt reuse detected", errors)

    def test_rejects_schema_shape_leakage_precedence_authority_and_reference_reds(self) -> None:
        root = self._copy_root()
        self._canonicalize_reference_expectations(root)
        path, document = self._document(root, "activation-authoring.json")
        document["cases"][0]["authority"] = {"effect_authority": False}
        document["cases"][1]["condition_blind"] = False
        document["cases"][2]["prompt"] += " verification strategy engineering"
        document["cases"][3]["hidden_labels"]["reference_expectations"] = [{"trigger": "not-a-trigger", "reference_title": "x", "required": True}]
        precedence = next(case for case in document["cases"] if case["near_neighbor_kind"] == "precedence")
        precedence["precedence"]["competing_owner"] = precedence["precedence"]["primary_owner"]
        explicit = next(case for case in document["cases"] if case["mode"] == "explicit")
        explicit["prompt"] += " `agentic-engineering`"
        document["cases"][4]["anti_reuse"]["case_nonce"] = 1
        path.write_text(json.dumps(document), encoding="utf-8")
        passed, errors, _ = self._validate_draft(root)
        self.assertFalse(passed)
        self.assertTrue(any("schema validation" in error for error in errors))
        self.assertIn("authoring: authority mismatch", errors)
        self.assertIn("authoring: blinding flags mismatch", errors)
        self.assertIn("authoring: automatic adviser-name leakage", errors)
        self.assertIn("authoring: hidden labels or prompt mismatch", errors)
        self.assertIn("authoring: precedence mismatch", errors)
        self.assertIn("authoring: explicit invocation mismatch", errors)

    def test_rejects_reference_coverage_catalog_and_explicit_token_reds(self) -> None:
        def mutate(case: dict, kind: str) -> None:
            labels = case["hidden_labels"]
            refs = labels["reference_expectations"]
            if kind == "missing":
                labels["reference_expectations"] = refs[:-1]
            elif kind == "empty":
                labels["reference_expectations"] = []
            elif kind == "extra":
                labels["reference_expectations"] = refs + [dict(refs[0])]
            elif kind == "wrong-owner-title":
                refs[0]["reference_title"] = "vocabulary-translator"
            elif kind == "wrong-trigger":
                refs[0]["trigger"] = "reference-isolation"
            elif kind == "unavailable-title":
                refs[0]["reference_title"] = "execution-contract-schema"

        for kind in ("missing", "empty", "extra", "wrong-owner-title", "wrong-trigger", "unavailable-title"):
            root = self._copy_root()
            self._canonicalize_reference_expectations(root)
            path, document = self._document(root, "activation-authoring.json")
            case = next(case for case in document["cases"] if case["hidden_labels"]["reference_expectations"])
            mutate(case, kind)
            path.write_text(json.dumps(document), encoding="utf-8")
            passed, errors, _ = self._validate_draft(root)
            self.assertFalse(passed, kind)
            self.assertIn("authoring: hidden labels or prompt mismatch", errors, kind)

        for kind in ("native-trigger", "bare-explicit", "multiple-dollar"):
            root = self._copy_root()
            self._canonicalize_reference_expectations(root)
            path, document = self._document(root, "activation-heldout.json")
            if kind == "native-trigger":
                native = next(case for case in document["cases"] if case["category"] == "native-sufficient")
                native["hidden_labels"]["reference_triggers"] = ["architecture-boundary"]
                native["hidden_labels"]["reference_expectations"] = []
            else:
                explicit = next(case for case in document["cases"] if case["mode"] == "explicit")
                declared = explicit["declared_invocation"]
                token = f"`${declared}`"
                if kind == "bare-explicit":
                    explicit["prompt"] = explicit["prompt"].replace(token, f"`{declared}`", 1)
                else:
                    explicit["prompt"] += f" `${declared}`"
            path.write_text(json.dumps(document), encoding="utf-8")
            passed, errors, _ = self._validate_draft(root)
            self.assertFalse(passed, kind)
            expected_error = "heldout: hidden labels or prompt mismatch" if kind == "native-trigger" else "heldout: explicit invocation mismatch"
            self.assertIn(expected_error, errors, kind)

    def test_selected_zero_reference_distribution_and_overlap_projection(self) -> None:
        root = self._copy_root()
        self._canonicalize_reference_expectations(root)
        passed, errors, _ = self._validate_draft(root)
        self.assertTrue(passed, errors)

        root = self._copy_root()
        self._canonicalize_reference_expectations(root)
        path, document = self._document(root, "activation-authoring.json")
        selected_zero = next(case for case in document["cases"] if case["mode"] == "automatic" and case["hidden_labels"]["expected_advisers"] and not case["hidden_labels"]["reference_triggers"])
        owner = selected_zero["hidden_labels"]["expected_advisers"][0]
        payload = next(payload for payload in validator.REFERENCE_PAYLOADS if payload[1] == owner)
        trigger = next(iter(payload[3]))
        selected_zero["hidden_labels"]["reference_triggers"] = [trigger]
        selected_zero["hidden_labels"]["reference_expectations"] = list(validator.minimum_reference_expectations([owner], [trigger]) or ())
        path.write_text(json.dumps(document), encoding="utf-8")
        passed, errors, _ = self._validate_draft(root)
        self.assertFalse(passed)
        self.assertIn("authoring: selected zero-reference distribution mismatch", errors)

        root = self._copy_root()
        self._canonicalize_reference_expectations(root)
        path, document = self._document(root, "activation-heldout.json")
        selected_zero = [case for case in document["cases"] if case["mode"] == "automatic" and case["hidden_labels"]["expected_advisers"] and not case["hidden_labels"]["reference_triggers"]]
        duplicate_owner = selected_zero[0]["hidden_labels"]["expected_advisers"][0]
        altered = selected_zero[1]
        altered["hidden_labels"]["expected_advisers"] = [duplicate_owner]
        altered["hidden_labels"]["must_not_select"] = [adviser for adviser in validator.ADVISERS if adviser != duplicate_owner]
        altered["precedence"]["primary_owner"] = duplicate_owner
        path.write_text(json.dumps(document), encoding="utf-8")
        passed, errors, _ = self._validate_draft(root)
        self.assertFalse(passed)
        self.assertIn("heldout: selected zero-reference distribution mismatch", errors)

        overlap = (
            ("a-payload", "agentic-engineering", "first-title", frozenset({"architecture-boundary", "decision-contract"})),
            ("z-payload", "agentic-engineering", "second-title", frozenset({"architecture-boundary", "verification-evidence"})),
        )
        with patch.object(validator, "REFERENCE_PAYLOADS", overlap):
            projected = validator.minimum_reference_expectations(["agentic-engineering"], ["architecture-boundary", "decision-contract", "verification-evidence"])
        self.assertEqual(projected, (
            {"trigger": "architecture-boundary", "reference_title": "first-title", "required": True},
            {"trigger": "decision-contract", "reference_title": "first-title", "required": True},
            {"trigger": "verification-evidence", "reference_title": "second-title", "required": True},
        ))

    def test_staged_extra_and_missing_path_rejected(self) -> None:
        for missing, extra in ((True, False), (False, True)):
            root = self._copy_root()
            self._canonicalize_reference_expectations(root)
            paths = validator.CORPUS_FILES[:-1] if missing else validator.CORPUS_FILES
            self._stage_corpus(root, paths)
            if extra:
                extra_path = root / "unrelated.txt"
                extra_path.write_text("extra", encoding="utf-8")
                subprocess.run(["git", "add", "unrelated.txt"], cwd=root, check=True)
            passed, errors, _ = validator.validate(root, working_tree=True, comparator_fixture=self.comparator)
            self.assertFalse(passed)
            self.assertIn("staged corpus custody check failed", errors)

    def test_staged_blob_live_byte_drift_rejected(self) -> None:
        root = self._copy_root()
        self._canonicalize_reference_expectations(root)
        self._stage_corpus(root)
        path = root / CORPUS / "README.md"
        path.write_bytes(path.read_bytes() + b"\n")
        passed, errors, _ = validator.validate(root, working_tree=True, comparator_fixture=self.comparator)
        self.assertFalse(passed)
        self.assertIn("staged corpus custody check failed", errors)

    def test_frozen_binding_rejects_wrong_commit_tree_and_path(self) -> None:
        root, commit, tree = self._frozen_fixture()
        with patch.object(validator, "FROZEN_CORPUS_COMMIT", None), patch.object(validator, "FROZEN_CORPUS_TREE", tree):
            self.assertEqual(validator.frozen_corpus_errors(root), ["AQ3 frozen corpus binding unavailable"])
        with patch.object(validator, "FROZEN_CORPUS_COMMIT", "0" * 40), patch.object(validator, "FROZEN_CORPUS_TREE", tree):
            self.assertEqual(validator.frozen_corpus_errors(root), ["AQ3 frozen corpus commit unavailable"])
        with patch.object(validator, "FROZEN_CORPUS_COMMIT", commit), patch.object(validator, "FROZEN_CORPUS_TREE", "0" * 40):
            self.assertEqual(validator.frozen_corpus_errors(root), ["AQ3 frozen corpus tree mismatch"])
        with patch.object(validator, "FROZEN_CORPUS_COMMIT", commit), patch.object(validator, "FROZEN_CORPUS_TREE", tree), patch.object(validator, "CORPUS_FILES", validator.CORPUS_FILES + (CORPUS / "missing.json",)):
            self.assertIn("AQ3 frozen corpus byte mismatch", validator.frozen_corpus_errors(root))
        drifted = root / CORPUS / "README.md"
        drifted.write_bytes(drifted.read_bytes() + b"\n")
        with patch.object(validator, "FROZEN_CORPUS_COMMIT", commit), patch.object(validator, "FROZEN_CORPUS_TREE", tree):
            passed, errors, _ = validator.validate(root, comparator_fixture=self.comparator)
        self.assertFalse(passed)
        self.assertIn("AQ3 frozen corpus byte mismatch", errors)

    def test_cli_is_zero_write_and_never_outputs_prompt_or_case_results(self) -> None:
        script = ROOT / "scripts" / "validate_future_activation_corpus_v3.py"
        before = script.read_bytes()
        result = subprocess.run([sys.executable, str(script), "--bad-option"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, "future-activation-corpus-v3: FAIL\n- error: structural rule failed\n")
        self.assertEqual(script.read_bytes(), before)
        self.assertNotIn("AQ3-A-", result.stdout)


if __name__ == "__main__":
    unittest.main()
