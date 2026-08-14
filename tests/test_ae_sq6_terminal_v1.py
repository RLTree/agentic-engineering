"""Aggregate-only terminal custody checks for AE-SQ6."""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import subprocess
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DECISION = ROOT / "evals/ae-sq6/ar/terminal-decision.json"
PLAN = ROOT / "docs/exec-plans/active/ae-sq6.md"
FOUNDATION = ROOT / "docs/foundations/current-2026-08-08.md"
LOG = ROOT / "docs/foundations/decision-log.csv"
EXPECTED_RAW_SHA256 = "a404b6a9230e87bdc4625ad336d768e682fcff6303a2cefd79d5c74648b69bcf"
EXPECTED_SEMANTIC_SHA256 = (
    "d0c4b0920a1b0292739c74c447b31e2cd945d539411984acc449db666b59f720"
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
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite: {token}")
        ),
    )
    if type(value) is not dict:
        raise ValueError("root must be object")
    return value


class AeSq6TerminalTests(unittest.TestCase):
    def test_terminal_document_is_exact(self) -> None:
        raw = DECISION.read_bytes()
        self.assertEqual(EXPECTED_RAW_SHA256, hashlib.sha256(raw).hexdigest())
        self.assertTrue(raw.endswith(b"\n"))
        document = strict(raw)
        semantic = json.dumps(
            document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.assertEqual(EXPECTED_SEMANTIC_SHA256, hashlib.sha256(semantic).hexdigest())
        self.assertEqual(
            document,
            {
                "aggregate_result": None,
                "candidate_id": "AE-SQ6-SLEC-6",
                "last_completed_phase": "SQ6-F1G",
                "program_id": "AE-SQ6",
                "schema_version": "ae-sq6-terminal-decision-v1",
                "status": "terminal",
                "terminal_edge": "SQ6-F2:NOT_PASS->SQ6-AR",
            },
        )
        self.assertFalse((ROOT / "evals/ae-sq6/as/handoff.json").exists())
        self.assertFalse((ROOT / "evals/ae-sq6/f3/preflight.json").exists())
        self.assertFalse((ROOT / "evals/ae-sq6/f6/aggregate-result.json").exists())
        self.assertFalse((ROOT / ".git/.ae-sq6-one-shot/state.json").exists())

    def test_aggregate_object_custody_without_opening_corpus_bytes(self) -> None:
        commits = {
            "bc097d0d690578e68a5e667897381cdfb123c725": "716b9cd881f30825efb996b1261832403475f1dc",
            "278816cf9161e72822fe89197ea4570ec6c1ced6": "eda37945d5d390118f9edd5ae498b43ec6eede56",
            "421ba8911139d48630f411d2af50541590f0dc93": "685a3784001e07b67c21719019a8c6c6c5e01527",
            "ba59d6da1e564d859e584dd0ebe3958d961dc9ef": "ec36e54c6e67d604d802778c62777b0b43200031",
            "d62711dcb70133561d51aa5aadd897ef4426573f": "214ae7ffd58006058a6dd546657195895b90382c",
        }
        for commit, tree in commits.items():
            actual = subprocess.run(
                ["git", "show", "-s", "--format=%T", commit],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(tree, actual)
        for blob in (
            "9469089409267ca6866b54f6eef6ce75d24b3d50",
            "f4328f68d639127b99a9ba15064d458b83d8f3cf",
            "2afa046966fdf9bfcb277cf672168c7cc5ee4e3c",
            "59ab7f94460ab14aaf8fb2f5026d591110ebc466",
        ):
            kind = subprocess.run(
                ["git", "cat-file", "-t", blob],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual("blob", kind)

    def test_plan_records_exact_terminal_aggregate_and_zero_execution(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        for fact in (
            "errors=[selected_reference_anchor]",
            "`holds=[]`",
            "40 qualified case IDs",
            "none 6, single 16, two 8, cap 4, explicit 4,\nuncertain 2",
            "all six two-slot pairs",
            "400\ncross-split comparisons",
            "`0.2638888888888889`",
            "768\nhistorical digests",
            "No F2A or F2B was created",
            "one-shot state is absent",
            "model, canary, and batch calls are all zero",
            "SQ6-F2:NOT_PASS->SQ6-AR",
        ):
            self.assertIn(fact, plan)

    def test_foundation_bridge_and_decision_rows_are_unique(self) -> None:
        self.assertEqual(
            FOUNDATION.read_text(encoding="utf-8").splitlines()[6],
            "**Active successor plan:** `docs/exec-plans/active/ae-sq8.md` for AE-SQ8 only; AE-SQ7, AE-SQ6, AE-SQ5, AE-SQ4, AE-SQ3, AE-SQ2, AE-SQ1, and `EXECPLAN.md` remain immutable terminal history",
        )
        rows = list(csv.DictReader(io.StringIO(LOG.read_text(encoding="utf-8"))))
        ids = [row["decision_id"] for row in rows]
        self.assertEqual(1, ids.count("AE-SQ6-AR-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ7-F0-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ7-AR-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ8-F0-2026-08-13"))
        self.assertEqual(["AE-SQ7-AR-2026-08-13", "AE-SQ8-F0-2026-08-13"], ids[-2:])

    def test_exact_terminal_contract_rejects_mutations(self) -> None:
        base = strict(DECISION.read_bytes())
        mutations = []
        for key, value in (
            ("terminal_edge", "SQ6-F2:PASS->SQ6-F2A"),
            ("last_completed_phase", "SQ6-F2B"),
            ("aggregate_result", {"status": "PASS"}),
        ):
            mutation = copy.deepcopy(base)
            mutation[key] = value
            mutations.append(mutation)
        extension = copy.deepcopy(base)
        extension["extra"] = True
        mutations.append(extension)
        for mutation in mutations:
            semantic = json.dumps(
                mutation, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            self.assertNotEqual(
                EXPECTED_SEMANTIC_SHA256, hashlib.sha256(semantic).hexdigest()
            )

    def test_duplicate_and_nonfinite_json_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate key"):
            strict(b'{"program_id":"AE-SQ6","program_id":"AE-SQ7"}')
        with self.assertRaisesRegex(ValueError, "non-finite"):
            strict(b'{"value":NaN}')


if __name__ == "__main__":
    unittest.main()
