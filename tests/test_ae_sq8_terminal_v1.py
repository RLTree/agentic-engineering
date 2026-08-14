"""Aggregate-only terminal custody checks for AE-SQ8."""

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
DECISION = ROOT / "evals/ae-sq8/ar/terminal-decision.json"
SCHEMA = ROOT / "evals/ae-sq8/f1/terminal-decision-schema.json"
PLAN = ROOT / "docs/exec-plans/active/ae-sq8.md"
FOUNDATION = ROOT / "docs/foundations/current-2026-08-08.md"
LOG = ROOT / "docs/foundations/decision-log.csv"
EXPECTED_DECISION_RAW = (
    "0754a58ecb68dbfc5ac5b8b3d5aacbeca4e131a3724fadaea8d1e28d2f91ccd0"
)


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


def git_output(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


class AeSq8TerminalTests(unittest.TestCase):
    def test_terminal_record_is_exact_closed_and_schema_valid(self) -> None:
        raw = DECISION.read_bytes()
        self.assertEqual(EXPECTED_DECISION_RAW, hashlib.sha256(raw).hexdigest())
        document = strict(raw)
        self.assertEqual(
            document,
            {
                "aggregate_result": None,
                "candidate_id": "AE-SQ8-SLEC-8",
                "last_completed_phase": "SQ8-F2A",
                "program_id": "AE-SQ8",
                "schema_version": "ae-sq8-terminal-decision-v1",
                "status": "terminal",
                "terminal_edge": "SQ8-F2B:NOT_PASS->SQ8-AR",
            },
        )
        schema = strict(SCHEMA.read_bytes())
        self.assertEqual([], list(Draft202012Validator(schema).iter_errors(document)))

    def test_exact_graph_and_terminal_only_child(self) -> None:
        expected = {
            "7ea85f98762b79124e0323f5619e418ac0a55f09": (
                "6b40a897905874c28e626102fd9f15af981008d4",
                ["fb1c3dee8b9e3aaa77c12ad387af090ab26e410f"],
            ),
            "3040aa21bd95dfcfe54bf60bf5735a54159bbcf2": (
                "8c92ee65e074ebd8e2d161158182a87d303c5f6a",
                ["7ea85f98762b79124e0323f5619e418ac0a55f09"],
            ),
            "171635a5c5885fe975606c45c6eeeef158c60771": (
                "80bf1846d51fe8e0b4962d910363798dbb7fab04",
                ["7ea85f98762b79124e0323f5619e418ac0a55f09"],
            ),
            "6ad83a4340d71408bcf38f51ccab8a60c2e1bbcf": (
                "a8f2f3129712518e8924a48c222140c7ad96e1a4",
                [
                    "7ea85f98762b79124e0323f5619e418ac0a55f09",
                    "3040aa21bd95dfcfe54bf60bf5735a54159bbcf2",
                    "171635a5c5885fe975606c45c6eeeef158c60771",
                ],
            ),
            "96c4f8a33caf4b8d5d34a6bfc9d0d32db571e831": (
                "8918dceec8e324ce118dcf101fbed466de631709",
                ["6ad83a4340d71408bcf38f51ccab8a60c2e1bbcf"],
            ),
            "f455f582e8d94356fab142f4d51c8ef825c446ff": (
                "e6bbed7ababbf95b4809e21108c62ce344d61728",
                ["96c4f8a33caf4b8d5d34a6bfc9d0d32db571e831"],
            ),
        }
        for commit, (tree, parents) in expected.items():
            fields = git_output("show", "-s", "--format=%T %P", commit).split()
            self.assertEqual([tree, *parents], fields)
        self.assertEqual(
            ["A\tevals/ae-sq8/ar/terminal-decision.json"],
            git_output(
                "diff-tree",
                "--no-commit-id",
                "--name-status",
                "-r",
                "96c4f8a33caf4b8d5d34a6bfc9d0d32db571e831",
                "f455f582e8d94356fab142f4d51c8ef825c446ff",
            ).splitlines(),
        )

    def test_plan_records_failure_without_overclaiming_receipt(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        for fact in (
            "TERMINAL — SQ8-F2B NOT_PASS; SQ8-AR",
            "SQ8-F2B:NOT_PASS->SQ8-AR",
            "ambient module poisoning detected: resolve_ae_sq8_slec",
            "validation process had already imported that resolver",
            "pair-level PASS cannot compensate",
            "F3 never\nopened",
            "no one-shot state, F4-F6, result, handoff, canary, batch, or model call",
            EXPECTED_DECISION_RAW,
        ):
            self.assertIn(fact, plan)
        self.assertNotIn("durable loader failure receipt", plan)

    def test_frozen_guard_and_terminal_commit_message_support_cause(self) -> None:
        source = subprocess.run(
            [
                "git",
                "show",
                "8454c9c712eaeedb14381956ac6144fd42dfbe39:scripts/run_ae_sq8_aq.py",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertIn("ambient module poisoning detected: {module_name}", source)
        message = git_output(
            "show", "-s", "--format=%B", "f455f582e8d94356fab142f4d51c8ef825c446ff"
        )
        self.assertIn(
            "production F2B loader gate rejected ambient resolver contamination",
            message,
        )
        self.assertIn("zero model calls and no retry", message)

    def test_no_later_stage_or_one_shot_artifact(self) -> None:
        tree = git_output(
            "ls-tree", "-r", "--name-only", "f455f582e8d94356fab142f4d51c8ef825c446ff"
        ).splitlines()
        forbidden_prefixes = (
            "evals/ae-sq8/f3/",
            "evals/ae-sq8/f4/",
            "evals/ae-sq8/f5/",
            "evals/ae-sq8/f6/",
            "evals/ae-sq8/as/",
        )
        self.assertFalse(any(path.startswith(forbidden_prefixes) for path in tree))
        self.assertFalse((ROOT / ".git/.ae-sq8-one-shot/state.json").exists())

    def test_foundation_and_decision_log_advance_once(self) -> None:
        self.assertEqual(
            FOUNDATION.read_text(encoding="utf-8").splitlines()[6],
            "**Active successor plan:** `docs/exec-plans/active/ae-sq9.md` for AE-SQ9 only; AE-SQ8, AE-SQ7, AE-SQ6, AE-SQ5, AE-SQ4, AE-SQ3, AE-SQ2, AE-SQ1, and `EXECPLAN.md` remain immutable terminal history",
        )
        rows = list(csv.DictReader(io.StringIO(LOG.read_text(encoding="utf-8"))))
        ids = [row["decision_id"] for row in rows]
        self.assertEqual(1, ids.count("AE-SQ8-AR-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ9-F0-2026-08-13"))
        self.assertEqual(["AE-SQ8-AR-2026-08-13", "AE-SQ9-F0-2026-08-13"], ids[-2:])

    def test_duplicate_and_nonfinite_json_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate key"):
            strict(b'{"program_id":"AE-SQ8","program_id":"AE-SQ9"}')
        with self.assertRaises(ValueError):
            strict(b'{"value":NaN}')


if __name__ == "__main__":
    unittest.main()
