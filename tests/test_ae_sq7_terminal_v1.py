"""Aggregate-only terminal custody checks for AE-SQ7."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
import unittest
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
DECISION = ROOT / "evals/ae-sq7/ar/terminal-decision.json"
PLAN = ROOT / "docs/exec-plans/active/ae-sq7.md"
FOUNDATION = ROOT / "docs/foundations/current-2026-08-08.md"
LOG = ROOT / "docs/foundations/decision-log.csv"
EXPECTED_DECISION_RAW = (
    "f401f7cda3fd9279d7fec49b2f02e6d4156f1268947aa1474c9fcc266ebc3454"
)
F1A = "1613d46d8fae71259979371717dd567de17ffded"
F3 = "39384f86f4680866cb2cee945c3eb7b2f3ea10fe"
F3_PATH = "evals/ae-sq7/f3/preflight.json"
PREFLIGHT_SCHEMA_PATH = "evals/ae-sq7/f1/preflight-schema.json"


def strict(raw: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )
    if type(value) is not dict:
        raise ValueError("root must be object")
    return value


def git_show(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


class AeSq7TerminalTests(unittest.TestCase):
    def test_existing_terminal_decision_is_exact_and_untouched(self) -> None:
        raw = DECISION.read_bytes()
        self.assertEqual(EXPECTED_DECISION_RAW, hashlib.sha256(raw).hexdigest())
        self.assertEqual(
            strict(raw),
            {
                "aggregate_result": None,
                "candidate_id": "AE-SQ7-SLEC-7",
                "last_completed_phase": "SQ7-F2B",
                "program_id": "AE-SQ7",
                "schema_version": "ae-sq7-terminal-decision-v1",
                "status": "terminal",
                "terminal_edge": "SQ7-F3:NOT_PASS->SQ7-AR",
            },
        )

    def test_exact_commit_tree_and_blob_metadata_without_opening_frozen_bytes(
        self,
    ) -> None:
        commits = {
            "323d5b44f2453ce3343648a0ac1519db5a878511": "70871d6031d24a76cf636054af4a872b216df69a",
            "39384f86f4680866cb2cee945c3eb7b2f3ea10fe": "72e35516785f9c934c94b24b5cb0a59328d8225e",
            "00d4e245244827cb4d12246725d95fc6287b00a2": "ae9f30c1135dee8407f1366918bd085962024783",
            "1613d46d8fae71259979371717dd567de17ffded": "58a490dfc641ab11a2176c15801bb25b3df428a1",
        }
        for commit, expected_tree in commits.items():
            tree = subprocess.run(
                ["git", "show", "-s", "--format=%T", commit],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(expected_tree, tree)
        for blob in (
            "c443f8f5eb6ce950ce3b049fa6f7ed48ddaf5647",
            "fedf77d632af3cfe393762bf761591d792bd6b9f",
        ):
            kind = subprocess.run(
                ["git", "cat-file", "-t", blob],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual("blob", kind)
        f3_delta = subprocess.run(
            [
                "git",
                "diff-tree",
                "--no-commit-id",
                "--name-status",
                "-r",
                "323d5b44f2453ce3343648a0ac1519db5a878511",
                "39384f86f4680866cb2cee945c3eb7b2f3ea10fe",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertEqual(["A\tevals/ae-sq7/f3/preflight.json"], f3_delta)

    def test_plan_records_exact_failure_and_zero_later_execution(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        for fact in (
            "SQ7-F3:NOT_PASS->SQ7-AR",
            "receipt['validator_id']",
            "receipt.validator.validator_id",
            "fail-record fallback marks all 11\nchecks false",
            "single\nroot cause remains the field-location mismatch",
            "status is `FAIL`, attempt is 1, and model calls are 0",
            "One-shot state is absent",
            "No F4-F6, result, handoff, canary, batch, or model\ncall exists",
            "f401f7cda3fd9279d7fec49b2f02e6d4156f1268947aa1474c9fcc266ebc3454",
        ):
            self.assertIn(fact, plan)
        self.assertFalse((ROOT / ".git/.ae-sq7-one-shot/state.json").exists())
        self.assertFalse((ROOT / "evals/ae-sq7/f6/aggregate-result.json").exists())
        self.assertFalse((ROOT / "evals/ae-sq7/as/handoff.json").exists())

    def test_exact_git_f3_record_derives_raw_aggregate_schema_and_all_false(
        self,
    ) -> None:
        raw = git_show(F3, F3_PATH)
        self.assertEqual(
            "20024841e72a40b426203ca039b5ef70fb4cdfd20d47ddecfed9eac786fd41b8",
            hashlib.sha256(raw).hexdigest(),
        )
        record = strict(raw)
        unsigned = dict(record)
        aggregate = unsigned.pop("aggregate_sha256")
        canonical = json.dumps(
            unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.assertEqual(
            "e59cd5db8d9fc3331b593860d15531c0eeb1dffba0f7719b89f795a02f7e3ea8",
            aggregate,
        )
        self.assertEqual(aggregate, hashlib.sha256(canonical).hexdigest())
        schema = strict(git_show(F1A, PREFLIGHT_SCHEMA_PATH))
        self.assertEqual([], list(Draft202012Validator(schema).iter_errors(record)))
        checks = record["checks"]
        self.assertEqual(11, len(checks))
        self.assertEqual(11, sum(value is False for value in checks.values()))
        self.assertEqual("FAIL", record["status"])
        self.assertEqual(0, record["model_calls"])

    def test_foundation_bridge_and_decision_rows_are_unique(self) -> None:
        self.assertEqual(
            FOUNDATION.read_text(encoding="utf-8").splitlines()[6],
            "**Active successor plan:** none; AE-SQ9, AE-SQ8, AE-SQ7, AE-SQ6, AE-SQ5, AE-SQ4, AE-SQ3, AE-SQ2, AE-SQ1, and `EXECPLAN.md` remain immutable terminal history; a successor requires owner authorization after isolation capability PASS",
        )
        rows = list(csv.DictReader(io.StringIO(LOG.read_text(encoding="utf-8"))))
        ids = [row["decision_id"] for row in rows]
        self.assertEqual(1, ids.count("AE-SQ7-AR-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ8-F0-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ8-AR-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ9-F0-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ9-AR-2026-08-15"))
        self.assertEqual(1, ids.count("AE-SQ10-P0-HOLD-2026-08-15"))
        self.assertEqual(
            ["AE-SQ9-AR-2026-08-15", "AE-SQ10-P0-HOLD-2026-08-15"], ids[-2:]
        )

    def test_duplicate_and_nonfinite_json_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate key"):
            strict(b'{"program_id":"AE-SQ7","program_id":"AE-SQ8"}')
        with self.assertRaises(ValueError):
            strict(b'{"value":NaN}')


if __name__ == "__main__":
    unittest.main()
