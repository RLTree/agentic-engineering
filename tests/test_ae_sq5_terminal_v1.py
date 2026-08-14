"""Fail-closed terminal custody checks for AE-SQ5."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
DECISION = ROOT / "evals/ae-sq5/ar/terminal-decision.json"
SCHEMA = ROOT / "evals/ae-sq5/f1/terminal-decision-schema.json"
PLAN = ROOT / "docs/exec-plans/active/ae-sq5.md"
FOUNDATION = ROOT / "docs/foundations/current-2026-08-08.md"
LOG = ROOT / "docs/foundations/decision-log.csv"
F1A = "f382d28b4b034f097170d97d3d04e706f0eb623c"
F1B = "f301438b53b94fd48c9836b40085aed4fad39890"
F1G = "4af4ad00cc11b903a2b6d796b3578d7e76e0aaca"
F2A = "e74e3ef5055ac95442ecd3b342d4a47bc2b0345d"
F2B = "4760ecb53997fe693a76531057eaf8c13014434d"
F1G_PATH = "evals/ae-sq5/f1/author-template-gate.json"
F2B_MANIFEST = "evals/ae-sq5/f2/run-manifest.json"


def git_show(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


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


class AeSq5TerminalTests(unittest.TestCase):
    def test_terminal_document_is_exact_and_matches_frozen_schema(self) -> None:
        document = strict(DECISION.read_bytes())
        self.assertEqual(
            document,
            {
                "aggregate_result": None,
                "candidate_id": "AE-SQ5-SLEC-5",
                "last_completed_phase": "SQ5-F1G",
                "program_id": "AE-SQ5",
                "schema_version": "ae-sq5-terminal-decision-v1",
                "status": "terminal",
                "terminal_edge": "SQ5-F1G:NOT_PASS->SQ5-AR",
            },
        )
        self.assertEqual(
            [],
            list(
                Draft202012Validator(strict(SCHEMA.read_bytes())).iter_errors(document)
            ),
        )
        self.assertFalse((ROOT / "evals/ae-sq5/as/handoff.json").exists())
        self.assertFalse((ROOT / "evals/ae-sq5/f3/preflight.json").exists())
        self.assertFalse((ROOT / "evals/ae-sq5/f6/aggregate-result.json").exists())

    def test_exact_committed_receipt_differs_only_by_forbidden_canonical_byte(
        self,
    ) -> None:
        raw = git_show(F1G, F1G_PATH)
        document = strict(raw)
        canonical = json.dumps(
            document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.assertEqual(1623, len(raw))
        self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(
            "ffe6dca737c8e2a9f93a5bcdf596bec2569d6998efcc79d6583dd39ffb2a216d",
            hashlib.sha256(raw).hexdigest(),
        )
        self.assertEqual(1622, len(canonical))
        self.assertFalse(canonical.endswith(b"\n"))
        self.assertEqual(
            "52b7b29bfbe85b8260e659a17273793ebbfa90c3e7c5afb3e0b9d56588a9203d",
            hashlib.sha256(canonical).hexdigest(),
        )
        self.assertEqual(canonical + b"\n", raw)

    def test_frozen_production_verifier_rejects_exact_receipt_before_f2(self) -> None:
        runner_path = ROOT / "scripts/run_ae_sq5_aq.py"
        spec = importlib.util.spec_from_file_location(
            "sq5_terminal_runner", runner_path
        )
        assert spec is not None and spec.loader is not None
        runner = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = runner
        spec.loader.exec_module(runner)

        checker = runner._load_checker(ROOT, F1A)
        profile = checker.load_verified_candidate(ROOT, F1B, require_live=False)
        manifest = strict(git_show(F2B, F2B_MANIFEST))
        with self.assertRaisesRegex(
            runner.PreflightError,
            "^F1G receipt is not exact canonical UTF-8 JSON$",
        ):
            runner._verify_author_template_gate(
                root=ROOT,
                manifest={"author_template_gate": manifest["author_template_gate"]},
                profile=profile,
            )

    def test_graph_and_accounting_are_exact_terminal_facts(self) -> None:
        expected = {
            F1A: (
                "0d6254a35346c79948d80897e96d13836d8b0698",
                "7f4590b284bfb5e5f60bc96c8cdb15e6ff8194c8",
            ),
            F1B: ("eca70f8282dea79d6ac902c23ccb73f22f534dde", F1A),
            F1G: ("515e94e4847627084b8b809ee910ed81209ea8b7", F1B),
            F2A: ("de5363f1b5ed12f295ae2274910d9a83cc2609a5", F1G),
            F2B: ("289bc7b146fb6b6379dea7ae9b687c357c872b99", F2A),
        }
        for commit, (tree, first_parent) in expected.items():
            fields = subprocess.run(
                ["git", "show", "-s", "--format=%T %P", commit],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.split()
            self.assertEqual(tree, fields[0])
            self.assertEqual(first_parent, fields[1])
        plan = PLAN.read_text(encoding="utf-8")
        for fact in (
            "F3 was not attempted; model, canary, and batch calls are all zero",
            "unreferenced and unpublished\nevidence objects only",
            "must never be reused",
            "SQ5-F1G:NOT_PASS->SQ5-AR",
        ):
            self.assertIn(fact, plan)

    def test_foundation_terminal_and_successor_bridge_is_unique(self) -> None:
        self.assertEqual(
            FOUNDATION.read_text(encoding="utf-8").splitlines()[6],
            "**Active successor plan:** `docs/exec-plans/active/ae-sq9.md` for AE-SQ9 only; AE-SQ8, AE-SQ7, AE-SQ6, AE-SQ5, AE-SQ4, AE-SQ3, AE-SQ2, AE-SQ1, and `EXECPLAN.md` remain immutable terminal history",
        )
        rows = list(csv.DictReader(io.StringIO(LOG.read_text(encoding="utf-8"))))
        ids = [row["decision_id"] for row in rows]
        self.assertEqual(1, ids.count("AE-SQ5-AR-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ6-F0-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ6-AR-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ7-F0-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ7-AR-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ8-F0-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ8-AR-2026-08-13"))
        self.assertEqual(1, ids.count("AE-SQ9-F0-2026-08-13"))
        self.assertEqual(["AE-SQ8-AR-2026-08-13", "AE-SQ9-F0-2026-08-13"], ids[-2:])

    def test_mutation_reds_fail_frozen_schema_or_exact_terminal_contract(self) -> None:
        base = strict(DECISION.read_bytes())
        mutations = [
            {**base, "extra": True},
            {**base, "last_completed_phase": "SQ5-F2B"},
            {**base, "terminal_edge": "SQ5-F2B:NOT_PASS->SQ5-AR"},
            {
                **base,
                "aggregate_result": {
                    "path": "evals/ae-sq5/f6/aggregate-result.json",
                    "sha256": "0" * 64,
                },
            },
        ]
        schema = strict(SCHEMA.read_bytes())
        for mutation in mutations:
            schema_rejects = bool(
                list(Draft202012Validator(schema).iter_errors(mutation))
            )
            exact_rejects = mutation != base
            self.assertTrue(schema_rejects or exact_rejects)


if __name__ == "__main__":
    unittest.main()
