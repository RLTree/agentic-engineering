from __future__ import annotations

import importlib.util
import json
import py_compile
import stat
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/evaluate_hc1_isolation_probe.py"
SCHEMA_PATH = ROOT / "evals/host-isolation/hc1-evaluator-summary-schema.json"
GOLDEN_PATH = ROOT / "tests/fixtures/hc1-evaluator-pass-summary.json"

SPEC = importlib.util.spec_from_file_location("hc1_evaluator", SCRIPT)
assert SPEC and SPEC.loader
evaluator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = evaluator
SPEC.loader.exec_module(evaluator)


def passing_events() -> list[dict[str, object]]:
    return [
        {"case": name, "child_started": True, "outcome": expected, "rc": 0}
        for name, expected in evaluator.EXPECTED_CASES
    ]


def passing_postchecks() -> dict[str, bool]:
    return {name: True for name in evaluator.POSTCHECK_NAMES}


class Hc1IsolationEvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = evaluator.load_schema(ROOT)

    def test_schema_is_closed_draft_2020_12(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text())
        Draft202012Validator.check_schema(schema)
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["properties"]["postchecks"]["additionalProperties"])
        self.assertFalse(schema["properties"]["cases"]["items"]["additionalProperties"])

    def test_source_compiles_and_golden_pass_bytes_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            py_compile.compile(
                str(SCRIPT),
                cfile=str(Path(directory) / "evaluator.pyc"),
                doraise=True,
            )
        document = evaluator.evaluate(
            passing_events(), passing_postchecks(), "HC1-E1-GOLDEN"
        )
        expected = evaluator.summary_bytes(document, self.schema)
        self.assertEqual(expected, GOLDEN_PATH.read_bytes())
        self.assertEqual("PASS", document["status"])

    def test_execute_writes_then_rereads_exact_pass_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "summary.json"
            code, document = evaluator.execute(
                passing_events(),
                passing_postchecks(),
                "HC1-E1-PASS",
                output,
                self.schema,
            )
            self.assertEqual(0, code)
            self.assertIsNotNone(document)
            self.assertEqual("PASS", document["status"])
            self.assertEqual(
                document,
                evaluator.verify_summary_bytes(output.read_bytes(), self.schema),
            )
            self.assertEqual(
                document, evaluator.verify_accepted_summary(output, code, self.schema)
            )
            self.assertEqual(0o600, stat.S_IMODE(output.stat().st_mode))
            self.assertEqual([], list(output.parent.glob(f".{output.name}.*")))

    def test_every_material_event_mutation_fails_closed_with_durable_summary(
        self,
    ) -> None:
        mutations: dict[str, object] = {}
        missing = passing_events()
        missing.pop()
        mutations["missing"] = missing
        duplicate = passing_events()
        duplicate.append(deepcopy(duplicate[0]))
        mutations["duplicate"] = duplicate
        malformed = passing_events()
        malformed[1] = "not-an-object"
        mutations["malformed"] = malformed
        unexpected = passing_events()
        unexpected[1] = {
            "case": "unknown",
            "child_started": True,
            "outcome": "DENIED",
            "rc": 0,
        }
        mutations["unexpected"] = unexpected
        leak = passing_events()
        leak[10]["outcome"] = "LEAK"
        mutations["broad-search-fixture-leak"] = leak
        wrong = passing_events()
        wrong[2]["outcome"] = "PASS"
        mutations["wrong-outcome"] = wrong
        nonzero = passing_events()
        nonzero[3]["rc"] = 41
        mutations["nonzero-rc"] = nonzero
        not_started = passing_events()
        not_started[4]["child_started"] = False
        mutations["child-not-started"] = not_started

        with tempfile.TemporaryDirectory() as directory:
            for name, events in mutations.items():
                with self.subTest(name=name):
                    output = Path(directory) / f"{name}.json"
                    code, document = evaluator.execute(
                        events,
                        passing_postchecks(),
                        f"HC1-E1-{name}",
                        output,
                        self.schema,
                    )
                    self.assertEqual(1, code)
                    self.assertEqual("HOLD", document["status"])
                    self.assertEqual(
                        document,
                        evaluator.verify_summary_bytes(
                            output.read_bytes(), self.schema
                        ),
                    )

    def test_every_postcheck_is_required_and_unknown_postcheck_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for name in evaluator.POSTCHECK_NAMES:
                with self.subTest(name=name):
                    postchecks = passing_postchecks()
                    postchecks[name] = False
                    output = Path(directory) / f"{name}.json"
                    code, document = evaluator.execute(
                        passing_events(),
                        postchecks,
                        f"HC1-E1-{name}",
                        output,
                        self.schema,
                    )
                    self.assertEqual(1, code)
                    self.assertEqual("HOLD", document["status"])
                    self.assertIn(
                        f"postcheck:{name}:failed-or-missing", document["failures"]
                    )
            postchecks = passing_postchecks()
            postchecks["invented"] = True
            output = Path(directory) / "unknown.json"
            code, document = evaluator.execute(
                passing_events(), postchecks, "HC1-E1-unknown", output, self.schema
            )
            self.assertEqual(1, code)
            self.assertIn("postcheck:invented:unexpected", document["failures"])

    def test_evaluation_exception_creates_valid_hold_and_never_exits_zero(self) -> None:
        def explode(
            _events: object, _postchecks: object, _attempt: str
        ) -> dict[str, object]:
            raise RuntimeError("synthetic evaluator failure")

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "summary.json"
            code, document = evaluator.execute(
                passing_events(),
                passing_postchecks(),
                "HC1-E1-EXCEPTION",
                output,
                self.schema,
                evaluator=explode,
            )
            self.assertEqual(1, code)
            self.assertEqual("HOLD", document["status"])
            self.assertIn("evaluation-exception:RuntimeError", document["failures"])
            self.assertEqual(
                document,
                evaluator.verify_summary_bytes(output.read_bytes(), self.schema),
            )

    def test_write_failure_cannot_return_zero_or_claim_a_summary(self) -> None:
        missing_parent = ROOT / "does-not-exist-hc1-e1" / "summary.json"
        self.assertFalse(missing_parent.parent.exists())
        code, document = evaluator.execute(
            passing_events(),
            passing_postchecks(),
            "HC1-E1-WRITE-FAIL",
            missing_parent,
            self.schema,
        )
        self.assertEqual(70, code)
        self.assertIsNone(document)
        self.assertFalse(missing_parent.exists())

    def test_postwrite_drift_is_detected(self) -> None:
        original = evaluator.verify_summary_bytes
        calls = 0

        def fail_after_write(raw: bytes, schema: object) -> dict[str, object]:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise evaluator.EvaluationError("synthetic postwrite drift")
            return original(raw, schema)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "summary.json"
            with mock.patch.object(
                evaluator, "verify_summary_bytes", side_effect=fail_after_write
            ):
                code, document = evaluator.execute(
                    passing_events(),
                    passing_postchecks(),
                    "HC1-E1-POSTWRITE",
                    output,
                    self.schema,
                )
            self.assertEqual(1, code)
            self.assertEqual("HOLD", document["status"])
            self.assertIn("evaluation-exception:EvaluationError", document["failures"])
            self.assertEqual(
                document,
                evaluator.verify_summary_bytes(output.read_bytes(), self.schema),
            )

    def test_double_fsync_failure_never_leaves_accepted_pass(self) -> None:
        real_fsync = evaluator.os.fsync
        calls = 0

        def fail_directory_fsyncs(descriptor: int) -> None:
            nonlocal calls
            calls += 1
            if calls >= 3:
                raise OSError("synthetic directory fsync failure")
            real_fsync(descriptor)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "summary.json"
            with mock.patch.object(
                evaluator.os, "fsync", side_effect=fail_directory_fsyncs
            ):
                code, document = evaluator.execute(
                    passing_events(),
                    passing_postchecks(),
                    "HC1-E1-DOUBLE-FSYNC",
                    output,
                    self.schema,
                )
            self.assertEqual(70, code)
            self.assertIsNone(document)
            self.assertEqual(4, calls)
            residual = evaluator.verify_summary_bytes(output.read_bytes(), self.schema)
            self.assertEqual("HOLD", residual["status"])
            self.assertEqual("HOLD", residual["capability_gate"])

    def test_residual_pass_after_storage_failures_is_never_accepted(self) -> None:
        real_fsync = evaluator.os.fsync
        real_replace = evaluator.os.replace
        real_unlink = Path.unlink
        fsync_calls = 0
        replace_calls = 0

        def fail_directory_fsync(descriptor: int) -> None:
            nonlocal fsync_calls
            fsync_calls += 1
            if fsync_calls >= 3:
                raise OSError("synthetic directory fsync failure")
            real_fsync(descriptor)

        def fail_rollback_replace(source: object, destination: object) -> None:
            nonlocal replace_calls
            replace_calls += 1
            if replace_calls == 2:
                raise OSError("synthetic rollback replace failure")
            real_replace(source, destination)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "summary.json"

            def fail_output_unlink(path: Path, *, missing_ok: bool = False) -> None:
                if path == output:
                    raise OSError("synthetic invalidation failure")
                real_unlink(path, missing_ok=missing_ok)

            with (
                mock.patch.object(
                    evaluator.os, "fsync", side_effect=fail_directory_fsync
                ),
                mock.patch.object(
                    evaluator.os, "replace", side_effect=fail_rollback_replace
                ),
                mock.patch.object(Path, "unlink", new=fail_output_unlink),
            ):
                code, document = evaluator.execute(
                    passing_events(),
                    passing_postchecks(),
                    "HC1-E1-RESIDUAL-PASS",
                    output,
                    self.schema,
                )
            self.assertEqual(70, code)
            self.assertIsNone(document)
            self.assertEqual(
                "PASS",
                evaluator.verify_summary_bytes(output.read_bytes(), self.schema)[
                    "status"
                ],
            )
            with self.assertRaisesRegex(
                evaluator.EvaluationError, "nonzero process exit"
            ):
                evaluator.verify_accepted_summary(output, code, self.schema)

    def test_exit_zero_without_exact_pass_summary_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            with self.assertRaises(OSError):
                evaluator.verify_accepted_summary(missing, 0, self.schema)
            hold = evaluator.evaluate([], {}, "HC1-E1-HOLD-ACCEPTANCE")
            hold_path = Path(directory) / "hold.json"
            hold_path.write_bytes(evaluator.summary_bytes(hold, self.schema))
            with self.assertRaisesRegex(evaluator.EvaluationError, "exact PASS"):
                evaluator.verify_accepted_summary(hold_path, 0, self.schema)

    def test_strict_json_rejects_duplicate_nonfinite_and_noncanonical_summary(
        self,
    ) -> None:
        with self.assertRaisesRegex(evaluator.EvaluationError, "duplicate"):
            evaluator.strict_json(b'{"a":1,"a":2}')
        with self.assertRaisesRegex(evaluator.EvaluationError, "non-finite"):
            evaluator.strict_json(b'{"a":NaN}')
        document = evaluator.evaluate(
            passing_events(), passing_postchecks(), "HC1-E1-CANONICAL"
        )
        raw = evaluator.summary_bytes(document, self.schema)
        for changed in (b" " + raw, raw[:-1], raw + b"\n"):
            with self.subTest(changed=changed[:8]):
                with self.assertRaises(evaluator.EvaluationError):
                    evaluator.verify_summary_bytes(changed, self.schema)

    def test_semantic_mutations_cannot_claim_pass(self) -> None:
        document = evaluator.evaluate(
            passing_events(), passing_postchecks(), "HC1-E1-MUTATION"
        )
        mutations = []
        extra = deepcopy(document)
        extra["invented"] = True
        mutations.append(extra)
        wrong_status = deepcopy(document)
        wrong_status["status"] = "HOLD"
        mutations.append(wrong_status)
        wrong_order = deepcopy(document)
        wrong_order["cases"][0], wrong_order["cases"][1] = (
            wrong_order["cases"][1],
            wrong_order["cases"][0],
        )
        mutations.append(wrong_order)
        wrong_hash = deepcopy(document)
        wrong_hash["aggregate_sha256"] = "0" * 64
        mutations.append(wrong_hash)
        wrong_expected = deepcopy(document)
        wrong_expected["cases"][0]["expected"] = "DENIED"
        wrong_expected["cases"][0]["observed"] = "DENIED"
        wrong_expected["aggregate_sha256"] = self._recompute(wrong_expected)
        mutations.append(wrong_expected)
        wrong_count = deepcopy(document)
        wrong_count["case_count_observed"] = 16
        wrong_count["aggregate_sha256"] = self._recompute(wrong_count)
        mutations.append(wrong_count)
        wrong_row_status = deepcopy(document)
        wrong_row_status["cases"][0]["status"] = "HOLD"
        wrong_row_status["aggregate_sha256"] = self._recompute(wrong_row_status)
        mutations.append(wrong_row_status)
        for mutation in mutations:
            with self.subTest(keys=sorted(mutation)):
                with self.assertRaises(evaluator.EvaluationError):
                    evaluator.validate_summary_document(mutation, self.schema)

    @staticmethod
    def _recompute(document: dict[str, object]) -> str:
        unsigned = deepcopy(document)
        unsigned.pop("aggregate_sha256")
        return evaluator.sha256_bytes(evaluator.canonical_json(unsigned))

    def test_cli_exit_zero_requires_exact_durable_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            events = base / "events.json"
            postchecks = base / "postchecks.json"
            summary = base / "summary.json"
            events.write_bytes(evaluator.canonical_json(passing_events()) + b"\n")
            postchecks.write_bytes(
                evaluator.canonical_json(passing_postchecks()) + b"\n"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--events",
                    str(events),
                    "--postchecks",
                    str(postchecks),
                    "--attempt-id",
                    "HC1-E1-CLI",
                    "--summary",
                    str(summary),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
            )
            self.assertEqual(0, result.returncode, result.stderr.decode())
            self.assertEqual(summary.read_bytes(), result.stdout)
            self.assertEqual(
                "PASS",
                evaluator.verify_summary_bytes(summary.read_bytes(), self.schema)[
                    "status"
                ],
            )


if __name__ == "__main__":
    unittest.main()
