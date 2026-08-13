"""Strict terminal closeout checks for AE-SQ3."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = ROOT / "evals/ae-sq3/ar/terminal-decision.json"
PLAN_PATH = ROOT / "docs/exec-plans/active/ae-sq3.md"
D0_COMMIT = "e2562ca4da5f3dc14fb07c1522f911e2dfe4334d"
D0_PATH = "evals/ae-sq2/d0/diagnostic-record.json"
F0_COMMIT = "230354f09045c0f20b03c5080a6d70fcee38acbb"
F1A_COMMIT = "c06c433cdc2581e1747c10e520eb2fdd857cdccd"
SIBLING_COMMIT = "b31e8b619ae1ef75aef179bbba7212235258178f"
HEX64 = set("0123456789abcdef")


KEYS = {
    "/": (
        "schema_version",
        "program_id",
        "stage",
        "status",
        "decision",
        "stop",
        "claim_ceiling",
        "terminal_reason",
        "f0_custody",
        "f1a_attempts",
        "checker_mismatch",
        "sq2_d0_custody",
        "phase_status",
        "live_call_accounting",
        "retention",
        "successor_route",
        "terminal_edges",
    ),
    "/f0_custody": (
        "commit",
        "program_authority_path",
        "program_authority_blob",
        "program_authority_raw_sha256",
        "active_plan_path",
        "preterminal_active_plan_blob",
        "preterminal_active_plan_raw_sha256",
    ),
    "/f1a_attempts": (
        "canonical_attempt",
        "published_sibling",
        "same_program_repair_permitted",
        "uncommitted_repair_is_authority",
    ),
    "/f1a_attempts/canonical_attempt": (
        "commit",
        "tree",
        "parent",
        "status",
        "checker_path",
        "checker_blob",
        "checker_raw_sha256",
        "failure",
        "f1b_created",
    ),
    "/f1a_attempts/published_sibling": (
        "commit",
        "tree",
        "parent",
        "status",
        "same_checker_blob",
        "f1b_created",
    ),
    "/checker_mismatch": (
        "checker_expected_identity",
        "exact_record_identity",
        "exact_record_top_level_keys",
        "D0_rewrite_permitted",
        "route",
    ),
    "/checker_mismatch/checker_expected_identity": ("program_id", "mode"),
    "/checker_mismatch/exact_record_identity": (
        "program_id_field",
        "diagnostic_id",
        "mode",
        "status",
    ),
    "/sq2_d0_custody": ("commit", "record", "authority", "schema"),
    "/sq2_d0_custody/record": (
        "path",
        "blob",
        "raw_sha256",
        "record_sha256",
        "aggregate_sha256",
    ),
    "/sq2_d0_custody/authority": ("path", "blob", "raw_sha256"),
    "/sq2_d0_custody/schema": ("path", "blob", "raw_sha256"),
    "/phase_status": (
        "SQ3_F0",
        "SQ3_F1A",
        "SQ3_F1B",
        "SQ3_F2",
        "SQ3_F3",
        "SQ3_F4",
        "SQ3_F5",
        "SQ3_F6",
        "SQ3_AS_HANDOFF",
    ),
    "/live_call_accounting": (
        "diagnostic_calls",
        "canary_calls",
        "batch_calls",
        "total_model_calls",
    ),
}


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
    if not isinstance(value, dict):
        raise ValueError("root must be object")
    return value


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def is_hex(value: object, length: int) -> bool:
    return isinstance(value, str) and len(value) == length and not (set(value) - HEX64)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(document: dict[str, Any]) -> None:
    for pointer, keys in KEYS.items():
        value: Any = document
        for component in pointer.strip("/").split("/") if pointer != "/" else ():
            value = value[component]
        require(type(value) is dict and tuple(value) == keys, f"closed keys: {pointer}")
    require(document["schema_version"] == "ae-sq3-ar-terminal-decision-v2", "schema")
    require(document["program_id"] == "AE-SQ3", "program")
    require(document["stage"] == "SQ3-AR", "stage")
    require(document["status"] == "terminal", "status")
    require(document["decision"] == "DO_NOT_RELEASE_OR_PROMOTE", "decision")
    require(document["stop"] is True, "stop")
    require(document["f0_custody"]["commit"] == F0_COMMIT, "F0")
    attempts = document["f1a_attempts"]
    canonical_attempt = attempts["canonical_attempt"]
    sibling = attempts["published_sibling"]
    require(canonical_attempt["commit"] == F1A_COMMIT, "F1A commit")
    require(canonical_attempt["status"] == "NOT_PASS", "F1A status")
    require(canonical_attempt["f1b_created"] is False, "F1B absent")
    require(sibling["commit"] == SIBLING_COMMIT, "sibling")
    require(sibling["status"] == "superseded-NOT_PASS", "sibling status")
    require(sibling["f1b_created"] is False, "sibling F1B absent")
    require(attempts["same_program_repair_permitted"] is False, "repair")
    require(attempts["uncommitted_repair_is_authority"] is False, "uncommitted")
    mismatch = document["checker_mismatch"]
    require(
        mismatch["checker_expected_identity"]
        == {"program_id": "AE-SQ2", "mode": "diagnostic"},
        "checker expectation",
    )
    require(
        mismatch["exact_record_identity"]
        == {
            "program_id_field": "absent",
            "diagnostic_id": "AE-SQ2-D0-2026-08-12-01",
            "mode": "live",
            "status": "completed",
        },
        "actual D0 identity",
    )
    require(mismatch["D0_rewrite_permitted"] is False, "D0 rewrite")
    require(mismatch["route"] == "SQ3-AR", "route")
    require(
        document["successor_route"] == "distinct-owner-authorized-new-program-id-only",
        "successor route",
    )
    phases = document["phase_status"]
    require(phases["SQ3_F1A"] == "NOT_PASS", "F1A phase")
    require(phases["SQ3_F1B"] == "not_started-no-freeze-manifest", "F1B phase")
    require(phases["SQ3_F2"] == "not_started-no-corpus-authored", "corpus")
    require(phases["SQ3_F3"] == "not_started-no-preflight", "preflight")
    require(phases["SQ3_F6"] == "not_started-no-AQ-result", "AQ")
    require(phases["SQ3_AS_HANDOFF"] == "blocked", "downstream")
    require(
        all(
            type(value) is int and value == 0
            for value in document["live_call_accounting"].values()
        ),
        "SQ3 call accounting",
    )
    edges = document["terminal_edges"]
    require(type(edges) is list and len(edges) == 18, "terminal edges")
    for edge in (
        "no_SQ3_retry",
        "no_SQ3_refreeze",
        "no_reopen",
        "no_H6",
        "no_downstream",
    ):
        require(edge in edges, edge)
    for block in (document["f0_custody"], canonical_attempt, sibling):
        for key, value in block.items():
            if key.endswith(("commit", "tree", "parent", "blob")):
                require(is_hex(value, 40), f"object id: {key}")
            if key.endswith("sha256"):
                require(is_hex(value, 64), f"sha256: {key}")


def git_show(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def frozen_checker_identity_expectation(raw: bytes) -> dict[str, str]:
    """Extract the exact D0 identity comparison from the frozen checker AST."""
    tree = ast.parse(raw.decode("utf-8"))
    matches: list[dict[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.BoolOp):
            continue
        extracted: dict[str, str] = {}
        for clause in node.test.values:
            if (
                not isinstance(clause, ast.Compare)
                or len(clause.ops) != 1
                or not isinstance(clause.ops[0], ast.NotEq)
                or len(clause.comparators) != 1
                or not isinstance(clause.comparators[0], ast.Constant)
                or not isinstance(clause.comparators[0].value, str)
                or not isinstance(clause.left, ast.Call)
                or not isinstance(clause.left.func, ast.Attribute)
                or clause.left.func.attr != "get"
                or not isinstance(clause.left.func.value, ast.Name)
                or clause.left.func.value.id != "diagnosis"
                or len(clause.left.args) != 1
                or not isinstance(clause.left.args[0], ast.Constant)
                or not isinstance(clause.left.args[0].value, str)
            ):
                continue
            extracted[clause.left.args[0].value] = clause.comparators[0].value
        if set(extracted) == {"program_id", "mode"}:
            matches.append(extracted)
    if matches != [{"program_id": "AE-SQ2", "mode": "diagnostic"}]:
        raise ValueError(
            "frozen checker D0 identity comparison is not exact and unique"
        )
    return matches[0]


class AeSq3TerminalV2Tests(unittest.TestCase):
    def test_terminal_contract_and_exact_git_custody(self) -> None:
        document = strict(DECISION_PATH.read_bytes())
        validate(document)
        f0 = document["f0_custody"]
        authority = git_show(F0_COMMIT, f0["program_authority_path"])
        plan = git_show(F0_COMMIT, f0["active_plan_path"])
        self.assertEqual(
            hashlib.sha256(authority).hexdigest(), f0["program_authority_raw_sha256"]
        )
        self.assertEqual(
            hashlib.sha256(plan).hexdigest(), f0["preterminal_active_plan_raw_sha256"]
        )
        self.assertEqual(
            subprocess.run(
                ["git", "rev-parse", f"{F1A_COMMIT}^{{tree}}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            document["f1a_attempts"]["canonical_attempt"]["tree"],
        )
        self.assertEqual(
            (checker := git_show(F1A_COMMIT, "scripts/check_ae_sq3_candidate.py")),
            git_show(SIBLING_COMMIT, "scripts/check_ae_sq3_candidate.py"),
        )
        self.assertEqual(
            frozen_checker_identity_expectation(checker),
            document["checker_mismatch"]["checker_expected_identity"],
        )

    def test_exact_d0_record_proves_the_checker_mismatch_and_digests(self) -> None:
        document = strict(DECISION_PATH.read_bytes())
        record_raw = git_show(D0_COMMIT, D0_PATH)
        record = strict(record_raw)
        custody = document["sq2_d0_custody"]["record"]
        mismatch = document["checker_mismatch"]
        self.assertEqual(list(record), mismatch["exact_record_top_level_keys"])
        self.assertNotIn("program_id", record)
        self.assertEqual(record["mode"], "live")
        self.assertEqual(record["diagnostic_id"], "AE-SQ2-D0-2026-08-12-01")
        self.assertEqual(hashlib.sha256(record_raw).hexdigest(), custody["raw_sha256"])
        aggregate = hashlib.sha256(canonical(record["calls"])).hexdigest()
        self.assertEqual(aggregate, custody["aggregate_sha256"])
        unsealed = dict(record)
        unsealed.pop("record_sha256")
        self.assertEqual(
            hashlib.sha256(canonical(unsealed)).hexdigest(), custody["record_sha256"]
        )
        self.assertEqual(record["record_sha256"], custody["record_sha256"])
        self.assertEqual(record["aggregate_sha256"], custody["aggregate_sha256"])
        self.assertEqual(record["classification_counts"]["schema_unsupported"], 4)
        self.assertEqual(sum(record["classification_counts"].values()), 4)
        self.assertTrue(all(value == 0 for value in record["usage"].values()))

    def test_plan_terminal_checkpoint_and_absent_later_surfaces(self) -> None:
        plan = PLAN_PATH.read_text(encoding="utf-8")
        self.assertIn("Status: **TERMINAL — SQ3-AR AFTER SQ3-F1A NOT_PASS", plan)
        self.assertIn("## 11. Terminal checkpoint after SQ3-F1A", plan)
        self.assertIn("`program_id` field and correctly records `mode` as `live`", plan)
        self.assertFalse((ROOT / "evals/ae-sq3/f1/repaired-freeze.json").exists())
        for phase in ("f2", "f3", "f4", "f5", "f6"):
            self.assertFalse((ROOT / f"evals/ae-sq3/{phase}").exists(), phase)

    def test_recursive_and_semantic_mutation_reds(self) -> None:
        document = strict(DECISION_PATH.read_bytes())
        mutations: list[dict[str, Any]] = []
        for path, value in (
            (("stop",), False),
            (("status",), "open"),
            (("decision",), "RELEASE"),
            (("f1a_attempts", "canonical_attempt", "status"), "PASS"),
            (("f1a_attempts", "canonical_attempt", "f1b_created"), True),
            (("f1a_attempts", "same_program_repair_permitted"), True),
            (("checker_mismatch", "D0_rewrite_permitted"), True),
            (("checker_mismatch", "exact_record_identity", "mode"), "diagnostic"),
            (("phase_status", "SQ3_F2"), "started"),
            (("live_call_accounting", "canary_calls"), 1),
            (("successor_route",), "retry"),
        ):
            mutation = copy.deepcopy(document)
            target: Any = mutation
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            mutations.append(mutation)
        extension = copy.deepcopy(document)
        extension["f1a_attempts"]["canonical_attempt"]["extra"] = True
        mutations.append(extension)
        missing = copy.deepcopy(document)
        missing["terminal_edges"].remove("no_reopen")
        mutations.append(missing)
        for mutation in mutations:
            with self.assertRaises(ValueError):
                validate(mutation)


if __name__ == "__main__":
    unittest.main()
