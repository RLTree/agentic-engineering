"""Synthetic and frozen-custody tests for the AQ7 freeze validator.

Tests never emit corpus task, fact, label, or result text.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


V = load(ROOT / "scripts/validate_future_activation_corpus_v7.py", "aq7_validator")
C = load(ROOT / "tests/test_future_activation_contract_v7.py", "aq7_contract_fixture")


def synthetic_pair() -> tuple[dict, dict]:
    h3, _, policy, base, _ = C.authority_inputs()
    authoring = C.synthetic_root(h3, policy, base)
    heldout = copy.deepcopy(authoring)
    heldout["corpus_id"] = "AQ7-heldout"; heldout["split"] = "heldout"; heldout["nonce_source_contract"]["split_scope"] = "AQ7-heldout"
    for number, case in enumerate(heldout["cases"], 1):
        case["case_id"] = f"AQ7-H-{number:03d}"
        task = case["packet"]["task_text"].replace("Synthetic packet", "Independent fixture")
        case["packet"]["task_text"] = task
        case["prompt_sha256"] = hashlib.sha256(task.encode()).hexdigest()
        case["nonce_sha256"] = f"{1000 + number:064x}"
    return authoring, heldout


class TestFutureActivationCorpusV7(unittest.TestCase):
    def test_synthetic_closed_pair_passes_and_qualifies_40_ids(self) -> None:
        authoring, heldout = synthetic_pair()
        result = V._validate_documents(ROOT, (ROOT / V.SCHEMA).read_bytes(), (json.dumps(authoring).encode(), json.dumps(heldout).encode()), historical=[])
        self.assertTrue(result.passed, result.errors)
        self.assertEqual(40, len(result.qualified_ids))
        self.assertTrue(all(item.startswith("AQ7-H-") for item in result.qualified_ids[:32]))

    def test_derivation_and_surface_mutations_fail(self) -> None:
        authoring, heldout = synthetic_pair()
        mutations = (
            lambda c: c["grading"].update(expected_selected_atoms=[]),
            lambda c: c["grading"].update(expected_selection_status="cap_exceeded"),
            lambda c: c["grading"].update(expected_advisers=[]),
            lambda c: c["grading"].update(expected_must_not_select_advisers=[]),
            lambda c: c["grading"].update(expected_reference_requests=[]),
            lambda c: c["grading"]["expected_selection_constraint"].update(parse_status="ambiguous"),
            lambda c: c["grading"]["deterministic_reference_expectations"].update(payloads=[]),
            lambda c: c["grading"]["deterministic_reference_expectations"].update(resolved_payload_count=0),
            lambda c: c["grading"]["deterministic_reference_expectations"].update(derivation="other"),
            lambda c: c["grading"]["expected_predicate_facts"][0].update(state="absent"),
            lambda c: c.update(family_atom="task-contract"),
            lambda c: c["packet"].update(task_text="Agentic Engineering"),
        )
        for mutate in mutations:
            bad = copy.deepcopy(authoring); mutate(bad["cases"][0])
            result = V._validate_documents(ROOT, (ROOT / V.SCHEMA).read_bytes(), (json.dumps(bad).encode(), json.dumps(heldout).encode()), historical=[])
            self.assertFalse(result.passed)

    def test_token_hash_duplicate_distribution_and_historical_reds(self) -> None:
        authoring, heldout = synthetic_pair()
        reds = []
        bad = copy.deepcopy(authoring); bad["cases"][32]["packet"]["task_text"] += " $unknown-skill"; reds.append(bad)
        bad = copy.deepcopy(authoring); bad["cases"][1]["nonce_sha256"] = bad["cases"][0]["nonce_sha256"]; reds.append(bad)
        bad = copy.deepcopy(authoring); bad["cases"][0]["prompt_sha256"] = "0" * 64; reds.append(bad)
        bad = copy.deepcopy(authoring); bad["cases"].pop(); reds.append(bad)
        bad = copy.deepcopy(authoring); bad["cases"][0]["case_id"] = "AQ7-A-036"; reds.append(bad)
        for bad in reds:
            self.assertFalse(V._validate_documents(ROOT, (ROOT / V.SCHEMA).read_bytes(), (json.dumps(bad).encode(), json.dumps(heldout).encode()), historical=[]).passed)
        prompt = authoring["cases"][0]["packet"]["task_text"]
        prior = [(V._prompt_hash(prompt), V._signature(prompt), "AQ6-X-001")]
        self.assertFalse(V._validate_documents(ROOT, (ROOT / V.SCHEMA).read_bytes(), (json.dumps(authoring).encode(), json.dumps(heldout).encode()), historical=prior).passed)
        near = [("different", V._signature(prompt), "AQ6-X-002")]
        self.assertFalse(V._validate_documents(ROOT, (ROOT / V.SCHEMA).read_bytes(), (json.dumps(authoring).encode(), json.dumps(heldout).encode()), historical=near).passed)
        self.assertEqual(V._signature("Use $agentic-engineering shared text."), V._signature("Use $codex-task-contract shared text."))
        self.assertGreaterEqual(V._jaccard({"a", "b", "c"}, {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"}), V.NEAR_REWRITE_THRESHOLD)
        self.assertLess(V._jaccard({"a", "b"}, {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"}), V.NEAR_REWRITE_THRESHOLD)
        non_nfc = copy.deepcopy(authoring); task = non_nfc["cases"][0]["packet"]["task_text"] + "e\u0301"; non_nfc["cases"][0]["packet"]["task_text"] = task; non_nfc["cases"][0]["prompt_sha256"] = hashlib.sha256(__import__("unicodedata").normalize("NFC", task).encode()).hexdigest()
        self.assertFalse(V._validate_documents(ROOT, (ROOT / V.SCHEMA).read_bytes(), (json.dumps(non_nfc).encode(), json.dumps(heldout).encode()), historical=[]).passed)

    def test_surface_token_guard_and_exact_threshold_mutation_killers(self) -> None:
        authoring, heldout = synthetic_pair()
        for forbidden in ("AGENTIC ENGINEERING", "CODEX_TASK_CONTRACT", "VERIFICATION STRATEGY ENGINEERING", "ENGINEERING_LEARNING_LOOP"):
            bad = copy.deepcopy(authoring); bad["cases"][0]["packet"]["task_text"] = forbidden; bad["cases"][0]["prompt_sha256"] = hashlib.sha256(unicodedata.normalize("NFC", forbidden).encode()).hexdigest()
            self.assertFalse(V._validate_documents(ROOT, (ROOT / V.SCHEMA).read_bytes(), (json.dumps(bad).encode(), json.dumps(heldout).encode()), historical=[]).passed)
        bypass = copy.deepcopy(authoring); task = "AGENTIC ENGINEERING"; bypass["cases"][0]["packet"]["task_text"] = task; bypass["cases"][0]["prompt_sha256"] = hashlib.sha256(task.encode()).hexdigest()
        with patch.object(V, "_automatic_surface_ok", return_value=True):
            self.assertTrue(V._validate_documents(ROOT, (ROOT / V.SCHEMA).read_bytes(), (json.dumps(bypass).encode(), json.dumps(heldout).encode()), historical=[]).passed)
        h3, _, _, _, _ = C.authority_inputs()
        status, atoms, qualified, invocation_like = V._parse(h3, "Synthetic $agentic-engineering $unknown-skill")
        self.assertEqual(("unrecognized", [], ["$agentic-engineering"], ["$agentic-engineering", "$unknown-skill"]), (status, atoms, qualified, invocation_like))
        self.assertEqual(0.30, V.NEAR_REWRITE_THRESHOLD)
        at_boundary = V._jaccard({"a", "b", "c"}, {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"})
        below_boundary = V._jaccard({"a", "b"}, {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"})
        self.assertEqual(V.NEAR_REWRITE_THRESHOLD, at_boundary)
        self.assertGreaterEqual(at_boundary, V.NEAR_REWRITE_THRESHOLD)
        self.assertLess(below_boundary, V.NEAR_REWRITE_THRESHOLD)
        boundary_task = authoring["cases"][0]["packet"]["task_text"]
        history_signature = {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"}
        with patch.object(V, "_signature", side_effect=lambda text: {"a", "b", "c"} if text == boundary_task else set()):
            at_result = V._validate_documents(ROOT, (ROOT / V.SCHEMA).read_bytes(), (json.dumps(authoring).encode(), json.dumps(heldout).encode()), historical=[("different", history_signature, "AQ6-X-003")])
        self.assertFalse(at_result.passed)
        with patch.object(V, "_signature", side_effect=lambda text: {"a", "b"} if text == boundary_task else set()):
            below_result = V._validate_documents(ROOT, (ROOT / V.SCHEMA).read_bytes(), (json.dumps(authoring).encode(), json.dumps(heldout).encode()), historical=[("different", history_signature, "AQ6-X-004")])
        self.assertTrue(below_result.passed, below_result.errors)

    def test_staged_custody_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for path, payload in ((V.SPLITS[0], b"A"), (V.SPLITS[1], b"B")):
                target = root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(payload)
            staged = b"A\0evals/foundation-v4/future-activation-v7/activation-authoring.json\0A\0evals/foundation-v4/future-activation-v7/activation-heldout.json\0"
            def git_ok(_, args):
                if args[:3] == ["diff", "--cached", "--name-status"]: return staged
                return b"A" if args[-1].endswith("authoring.json") else b"B"
            with patch.object(V, "_contract_ok", return_value=True), patch.object(V, "_git", side_effect=git_ok):
                self.assertTrue(V.check_staged_split_custody(root))
                extra = b"A\0evals/foundation-v4/future-activation-v7/activation-authoring.json\0A\0evals/foundation-v4/future-activation-v7/activation-heldout.json\0A\0extra\0"
                with patch.object(V, "_git", side_effect=lambda _, args: extra if args[:3] == ["diff", "--cached", "--name-status"] else b"A"):
                    self.assertFalse(V.check_staged_split_custody(root))
                missing = b"A\0evals/foundation-v4/future-activation-v7/activation-authoring.json\0"
                with patch.object(V, "_git", side_effect=lambda _, args: missing if args[:3] == ["diff", "--cached", "--name-status"] else b"A"):
                    self.assertFalse(V.check_staged_split_custody(root))
                with patch.object(V, "_git", side_effect=lambda _, args: staged if args[:3] == ["diff", "--cached", "--name-status"] else b"drift"):
                    self.assertFalse(V.check_staged_split_custody(root))

    def test_contract_live_drift_fails_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            schema, readme = b"schema", b"readme"
            for path, payload in ((V.SCHEMA, schema), (V.README, readme)):
                target = root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(payload)
            with patch.object(V, "_assert_commit"), patch.object(V, "_commit_file", side_effect=lambda _, __, p: schema if p == V.SCHEMA else readme), patch.dict(V.CONTRACT_HASHES, {V.SCHEMA: hashlib.sha256(schema).hexdigest(), V.README: hashlib.sha256(readme).hexdigest()}, clear=True):
                self.assertTrue(V._contract_ok(root))
                (root / V.README).write_bytes(b"drift")
                self.assertFalse(V._contract_ok(root))

    def test_authoritative_default_cli_passes_without_writes(self) -> None:
        watched = (ROOT / V.SCHEMA, ROOT / V.README, *(ROOT / path for path in V.SPLITS))
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in watched}
        run = subprocess.run([sys.executable, str(ROOT / "scripts/validate_future_activation_corpus_v7.py")], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertIn("future-activation-corpus-v7: PASS", run.stdout)
        self.assertIn("- total_cases: 72", run.stdout)
        self.assertIn("- qualified_cases: 40", run.stdout)
        self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in watched})

    def test_frozen_binding_and_live_drift_fail_closed(self) -> None:
        self.assertTrue(V.validate_frozen(ROOT).passed)
        with patch.object(V, "FROZEN_CORPUS_COMMIT", "0" * 40):
            self.assertFalse(V.validate_frozen(ROOT).passed)
        with patch.object(V, "FROZEN_CORPUS_TREE", "0" * 40):
            self.assertFalse(V.validate_frozen(ROOT).passed)
        wrong_path = {V.SPLITS[0]: V.FROZEN_CORPUS_HASHES[V.SPLITS[0]], Path("wrong-path.json"): V.FROZEN_CORPUS_HASHES[V.SPLITS[1]]}
        with patch.object(V, "FROZEN_CORPUS_HASHES", wrong_path):
            self.assertFalse(V.validate_frozen(ROOT).passed)
        wrong_hash = dict(V.FROZEN_CORPUS_HASHES); wrong_hash[V.SPLITS[0]] = "0" * 64
        with patch.object(V, "FROZEN_CORPUS_HASHES", wrong_hash):
            self.assertFalse(V.validate_frozen(ROOT).passed)
        original_read = Path.read_bytes
        for drift_path in (ROOT / V.SPLITS[0], ROOT / V.SCHEMA, ROOT / V.README):
            def read_bytes(path: Path, *, target: Path = drift_path) -> bytes:
                return b"drift" if path == target else original_read(path)
            with patch.object(Path, "read_bytes", read_bytes):
                self.assertFalse(V.validate_frozen(ROOT).passed)

    def test_working_tree_uses_history_and_performs_no_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for path in (V.SCHEMA, *V.SPLITS):
                target = root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(b"fixture")
            before = {path: (root / path).stat().st_mtime_ns for path in (V.SCHEMA, *V.SPLITS)}
            empty = V.ValidationResult((), {"total_cases": 72, "qualified_cases": 40}, tuple(f"AQ7-H-{i:03d}" for i in range(1, 33)) + tuple(f"AQ7-A-{i:03d}" for i in range(33, 37)) + tuple(f"AQ7-H-{i:03d}" for i in range(33, 37)))
            with patch.object(V, "_historical", return_value=[]) as history, patch.object(V, "_validate_documents", return_value=empty) as validate_docs, patch.object(V, "check_staged_split_custody", return_value=True):
                passed, _, _ = V.validate(root, working_tree=True)
            self.assertTrue(passed); history.assert_called_once_with(root)
            self.assertIsNotNone(validate_docs.call_args.kwargs["historical"])
            self.assertEqual(before, {path: (root / path).stat().st_mtime_ns for path in (V.SCHEMA, *V.SPLITS)})

    def test_public_working_tree_malformed_input_is_generic_and_zero_write(self) -> None:
        authoring, heldout = synthetic_pair()
        marker = "private-fixture-sentinel"
        authoring["cases"][0]["grading"]["expected_predicate_facts"][0] = marker
        malformed = json.dumps(authoring).encode()
        watched = (ROOT / V.SCHEMA, ROOT / V.README, *(ROOT / path for path in V.SPLITS))
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in watched}
        original_read = Path.read_bytes
        def read_bytes(path: Path) -> bytes:
            return malformed if path == ROOT / V.SPLITS[0] else original_read(path)
        with patch.object(Path, "read_bytes", read_bytes):
            passed, errors, _ = V.validate(ROOT, working_tree=True)
        self.assertFalse(passed)
        self.assertEqual(["structural corpus inputs unavailable", "staged split custody failed"], errors)
        self.assertNotIn(marker, " ".join(errors))
        self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in watched})

    def test_public_working_tree_invalid_draft_schema_is_generic_and_zero_write(self) -> None:
        invalid_schema = json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "not-a-json-schema-type"}).encode()
        watched = (ROOT / V.SCHEMA, ROOT / V.README, *(ROOT / path for path in V.SPLITS))
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in watched}
        original_read = Path.read_bytes
        def read_bytes(path: Path) -> bytes:
            return invalid_schema if path == ROOT / V.SCHEMA else original_read(path)
        with patch.object(Path, "read_bytes", read_bytes):
            passed, errors, _ = V.validate(ROOT, working_tree=True)
        self.assertFalse(passed)
        self.assertEqual(["structural authority unavailable", "staged split custody failed"], errors)
        self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in watched})


if __name__ == "__main__":
    unittest.main()
