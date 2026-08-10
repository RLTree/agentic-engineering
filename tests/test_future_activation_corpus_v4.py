from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_future_activation_corpus_v4 as validator


class FutureActivationCorpusV4ValidatorTests(unittest.TestCase):
    """Unit tests deliberately use bindings/metadata, never v4 corpus content."""

    def _root_with_staged_paths(self) -> Path:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        corpus = root / validator.CORPUS_RELATIVE
        corpus.mkdir(parents=True)
        for path in validator.CORPUS_FILES:
            target = root / path
            target.write_text("{}\n" if target.suffix == ".json" else "draft\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", *(path.as_posix() for path in validator.CORPUS_FILES)], cwd=root, check=True)
        return root

    def test_candidate_metadata_is_compact_reference_only_and_covers_all_atoms(self) -> None:
        payloads = validator.payload_catalog(ROOT)
        self.assertEqual({payload.owner_atom for payload in payloads}, set(validator.ATOMS))
        self.assertTrue(all(payload.payload_id.startswith("aq-") and payload.triggers for payload in payloads))

    def test_historical_comparators_are_read_from_verified_immutable_trees(self) -> None:
        fixture = validator.frozen_comparator_fixture(ROOT)
        self.assertTrue(fixture.prompt_digests)
        bad = validator.ComparatorBinding("0" * 40, validator.AQ1_BINDING.tree, validator.AQ1_BINDING.paths)
        with patch.object(validator, "COMPARATOR_BINDINGS", (bad,)):
            with self.assertRaises(ValueError):
                validator.frozen_comparator_fixture(ROOT)

    def test_exact_staging_requires_only_the_four_corpus_paths_and_live_bytes(self) -> None:
        root = self._root_with_staged_paths()
        self.assertTrue(validator.check_staged_corpus_only(root))
        extra = root / "extra.txt"
        extra.write_text("extra\n", encoding="utf-8")
        subprocess.run(["git", "add", "extra.txt"], cwd=root, check=True)
        self.assertFalse(validator.check_staged_corpus_only(root))

    def test_staging_rejects_working_copy_drift(self) -> None:
        root = self._root_with_staged_paths()
        target = root / validator.CORPUS_FILES[-1]
        target.write_text("changed\n", encoding="utf-8")
        self.assertFalse(validator.check_staged_corpus_only(root))

    def test_frozen_api_fails_closed_before_any_corpus_read_when_binding_is_invalid(self) -> None:
        result = validator.validate_frozen(ROOT, "not-a-sha", "0" * 40)
        self.assertFalse(result.passed)
        self.assertEqual(result.errors, ("AQ4 frozen corpus binding unavailable",))
        self.assertEqual(result.qualified_ids, ())

    def test_default_binds_the_exact_frozen_corpus_and_wrong_tree_fails(self) -> None:
        self.assertEqual(validator.FROZEN_CORPUS_COMMIT, "f110be6ccb3460719141fea74b2fdb4313924718")
        self.assertEqual(validator.FROZEN_CORPUS_TREE, "ed3a0ee0afeb32f25033620519658b7b4774068c")
        self.assertEqual(validator.frozen_corpus_errors(ROOT), [])
        result = validator.validate_frozen(ROOT, validator.FROZEN_CORPUS_COMMIT, "0" * 40)
        self.assertFalse(result.passed)
        self.assertEqual(result.errors, ("AQ4 frozen corpus tree mismatch",))

    def test_programmatic_packet_entrypoint_is_generic_and_zero_result_for_invalid_bytes(self) -> None:
        result = validator._validate_documents(b"not-json", b"{}", b"{}", root=ROOT)
        self.assertFalse(result.passed)
        self.assertEqual(result.errors, ("corpus input unavailable or invalid",))
        self.assertEqual(result.metrics, {})
        self.assertEqual(result.qualified_ids, ())


if __name__ == "__main__":
    unittest.main()
