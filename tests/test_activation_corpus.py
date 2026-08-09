from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_activation_corpus


ROOT = Path(__file__).resolve().parents[1]


class ActivationCorpusTests(unittest.TestCase):
    def test_frozen_corpus_is_structurally_ready(self) -> None:
        passed, errors, metrics = validate_activation_corpus.validate(ROOT)
        self.assertTrue(passed, errors)
        self.assertEqual(metrics, {"automatic_cases": 64, "explicit_cases": 8, "total_cases": 72})

    def _copy_root(self) -> Path:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(ROOT / "evals", root / "evals")
        return root

    def _document(self, root: Path, name: str) -> tuple[Path, dict]:
        path = root / "evals" / "foundation-v4" / name
        return path, json.loads(path.read_text(encoding="utf-8"))

    def test_rejects_space_normalized_name_leak_and_no_advice_reference(self) -> None:
        root = self._copy_root()
        path, document = self._document(root, "activation-authoring.json")
        document["cases"][0]["prompt"] += " Agentic Engineering"
        no_advice = next(case for case in document["cases"] if case["category"] == "native-sufficient")
        no_advice["hidden_labels"]["reference_triggers"] = ["reference-isolation"]
        no_advice["authority"] = {"effect_authority": False}
        path.write_text(json.dumps(document), encoding="utf-8")
        passed, errors, _ = validate_activation_corpus.validate(root)
        self.assertFalse(passed)
        self.assertTrue(any("leaks legacy or fixed" in error for error in errors))
        self.assertTrue(any("no-advice" in error for error in errors))
        self.assertTrue(any("authority" in error for error in errors))

    def test_rejects_bad_explicit_prompt_and_cross_split_duplicate(self) -> None:
        root = self._copy_root()
        author_path, authoring = self._document(root, "activation-authoring.json")
        held_path, heldout = self._document(root, "activation-heldout.json")
        explicit = next(case for case in authoring["cases"] if case["mode"] == "explicit")
        explicit["prompt"] += f"; use ${explicit['declared_invocation']} again"
        heldout["cases"][0]["family_id"] = authoring["cases"][0]["family_id"]
        author_path.write_text(json.dumps(authoring), encoding="utf-8")
        held_path.write_text(json.dumps(heldout), encoding="utf-8")
        passed, errors, _ = validate_activation_corpus.validate(root)
        self.assertFalse(passed)
        self.assertTrue(any("declared dollar token" in error for error in errors))
        self.assertTrue(any("family IDs" in error for error in errors))

    def test_rejects_wrong_near_neighbor_distribution_and_legacy_reuse(self) -> None:
        root = self._copy_root()
        path, document = self._document(root, "activation-heldout.json")
        neighbors = [case for case in document["cases"] if case["category"] == "near-neighbor"]
        neighbors[0]["near_neighbor_kind"] = "precedence"
        neighbors[0]["hidden_labels"]["expected_advisers"] = ["verification-strategy-engineering"]
        legacy = json.loads((ROOT / "evals" / "routing-cases.json").read_text(encoding="utf-8"))
        document["cases"][0]["prompt"] = legacy["cases"][0]["prompt"]
        path.write_text(json.dumps(document), encoding="utf-8")
        passed, errors, _ = validate_activation_corpus.validate(root)
        self.assertFalse(passed)
        self.assertTrue(any("near-neighbor" in error for error in errors))
        self.assertTrue(any("legacy" in error for error in errors))

    def test_rejects_unknown_keys_invalid_family_and_legacy_space_name(self) -> None:
        root = self._copy_root()
        path, document = self._document(root, "activation-authoring.json")
        document["unknown_root"] = True
        document["cases"][0]["unknown_case"] = True
        document["cases"][0]["family_id"] = "Invalid_Family"
        document["cases"][1]["prompt"] += " graph workflow engineering"
        path.write_text(json.dumps(document), encoding="utf-8")
        passed, errors, _ = validate_activation_corpus.validate(root)
        self.assertFalse(passed)
        self.assertTrue(any("root keys" in error for error in errors))
        self.assertTrue(any("case keys" in error for error in errors))
        self.assertTrue(any("family_id" in error for error in errors))
        self.assertTrue(any("leaks legacy or fixed" in error for error in errors))
