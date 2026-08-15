"""Aggregate-only terminal custody and successor-capability checks for AE-SQ9."""

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
DECISION = ROOT / "evals/ae-sq9/ar/terminal-decision.json"
SCHEMA = ROOT / "evals/ae-sq9/f1/terminal-decision-schema.json"
PLAN = ROOT / "docs/exec-plans/active/ae-sq9.md"
FOUNDATION = ROOT / "docs/foundations/current-2026-08-08.md"
LOG = ROOT / "docs/foundations/decision-log.csv"
F0 = "88c1b04dc049ab7656e811df9bc3f9e33276f778"
F1G = "cab71239ab9ed85a61e182782e6c00d5bcaac4bc"
TERMINAL = "f0c8f4436a68657ead041bcd216971f0c93593b5"
TERMINAL_TREE = "b3d6cd7618816a7fd7d4bfb0cc4b37a83f824826"
TERMINAL_BLOB = "90f0ff74b6e836849fa1f9fa975985473cc90a36"
TERMINAL_RAW = "350836e316378e41e067915f4d13be3e5c7fa1f766c45edb55a1f1404aef85ac"
F0_PLAN_RAW = "7d01de0811e2eea877d21206b42626ec3d447702c63d573ac3b8c33570b728f1"
POINTER = (
    "**Active successor plan:** none; AE-SQ9, AE-SQ8, AE-SQ7, AE-SQ6, "
    "AE-SQ5, AE-SQ4, AE-SQ3, AE-SQ2, AE-SQ1, and `EXECPLAN.md` remain "
    "immutable terminal history; a successor requires owner authorization "
    "after isolation capability PASS"
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


class AeSq9TerminalTests(unittest.TestCase):
    def test_terminal_record_is_exact_closed_and_schema_valid(self) -> None:
        raw = DECISION.read_bytes()
        self.assertEqual(TERMINAL_RAW, hashlib.sha256(raw).hexdigest())
        document = strict(raw)
        self.assertEqual(
            document,
            {
                "aggregate_result": None,
                "candidate_id": "AE-SQ9-SLEC-9",
                "last_completed_phase": "SQ9-F1G",
                "program_id": "AE-SQ9",
                "schema_version": "ae-sq9-terminal-decision-v1",
                "status": "terminal",
                "terminal_edge": "SQ9-F2A:NOT_PASS->SQ9-AR",
            },
        )
        schema = strict(SCHEMA.read_bytes())
        self.assertEqual([], list(Draft202012Validator(schema).iter_errors(document)))

    def test_terminal_commit_is_exact_direct_receipt_only_child(self) -> None:
        fields = git_output("show", "-s", "--format=%H %T %P", TERMINAL).split()
        self.assertEqual([TERMINAL, TERMINAL_TREE, F1G], fields)
        self.assertEqual(
            ["A\tevals/ae-sq9/ar/terminal-decision.json"],
            git_output(
                "diff-tree", "--no-commit-id", "--name-status", "-r", F1G, TERMINAL
            ).splitlines(),
        )
        self.assertEqual(
            f"100644 blob {TERMINAL_BLOB}\tevals/ae-sq9/ar/terminal-decision.json",
            git_output("ls-tree", TERMINAL, "evals/ae-sq9/ar/terminal-decision.json"),
        )

    def test_plan_is_truthful_terminal_and_preserves_f0_authority(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        for fact in (
            "TERMINAL — SQ9-F2A NOT_PASS; SQ9-AR",
            "SQ9-F2A:NOT_PASS->SQ9-AR",
            "failed custody before pair validation",
            "No\npair validation, F2A, F2B, F2G, F3-F6",
            "no retry,\nreplacement, replay, repair, refreeze, resume, or reuse",
            "capability gate is `NOT_PASS`",
            "No AE-SQ10 plan, authority, candidate, branch, corpus, or runtime\nartifact is created",
            TERMINAL_RAW,
            F0_PLAN_RAW,
        ):
            self.assertIn(fact, plan)
        original = subprocess.run(
            ["git", "show", f"{F0}:docs/exec-plans/active/ae-sq9.md"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(F0_PLAN_RAW, hashlib.sha256(original).hexdigest())

    def test_capability_hold_does_not_misclassify_aborts_as_red_passes(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        for fact in (
            "aborted before child\nexecution",
            "allowed sentinel read failed",
            "sole\nauthorized output write failed",
            "apparent red denials are non-evidence",
            "Docker socket access and unprivileged chroot were unavailable",
        ):
            self.assertIn(fact, plan)
        self.assertNotIn("isolation capability PASS", plan)
        self.assertFalse((ROOT / "docs/exec-plans/active/ae-sq10.md").exists())
        self.assertFalse((ROOT / "evals/ae-sq10").exists())

    def test_no_later_sq9_artifact_or_durable_state(self) -> None:
        tree = git_output("ls-tree", "-r", "--name-only", TERMINAL).splitlines()
        forbidden = tuple(
            f"evals/ae-sq9/{phase}/" for phase in ("f2", "f3", "f4", "f5", "f6", "as")
        )
        self.assertFalse(any(path.startswith(forbidden) for path in tree))
        common_dir = Path(git_output("rev-parse", "--git-common-dir"))
        if not common_dir.is_absolute():
            common_dir = ROOT / common_dir
        self.assertFalse((common_dir / ".ae-sq9-f2g").exists())
        self.assertFalse((common_dir / ".ae-sq9-one-shot").exists())

    def test_foundation_and_decision_log_close_without_successor(self) -> None:
        self.assertEqual(
            POINTER, FOUNDATION.read_text(encoding="utf-8").splitlines()[6]
        )
        rows = list(csv.DictReader(io.StringIO(LOG.read_text(encoding="utf-8"))))
        ids = [row["decision_id"] for row in rows]
        self.assertEqual(1, ids.count("AE-SQ9-AR-2026-08-15"))
        self.assertEqual(1, ids.count("AE-SQ10-P0-HOLD-2026-08-15"))
        self.assertEqual(
            ["AE-SQ9-AR-2026-08-15", "AE-SQ10-P0-HOLD-2026-08-15"],
            ids[-2:],
        )
        self.assertEqual(
            "retire", rows[-2]["disposition_no_change_update_replace_retire"]
        )
        self.assertEqual(
            "no_change", rows[-1]["disposition_no_change_update_replace_retire"]
        )

    def test_duplicate_and_nonfinite_json_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate key"):
            strict(b'{"program_id":"AE-SQ9","program_id":"AE-SQ10"}')
        with self.assertRaises(ValueError):
            strict(b'{"value":NaN}')


if __name__ == "__main__":
    unittest.main()
