"""Strict F0 authority checks for the distinct AE-SQ8 successor."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "evals/ae-sq8/program-authority.json"
PLAN = ROOT / "docs/exec-plans/active/ae-sq8.md"
EXPECTED_RAW_SHA256 = "dc15fc8403f59cb59ae1491ce790c0dfa3439b0d2bb02c0bfaadcfd6f3fb7654"
EXPECTED_SEMANTIC_SHA256 = (
    "472ef4241dd06b0a9472c4da404b2534ed68f02cb53b2054486375b18730d70a"
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


def semantic_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def git_show(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(document: dict[str, Any]) -> None:
    require(
        hashlib.sha256(semantic_bytes(document)).hexdigest()
        == EXPECTED_SEMANTIC_SHA256,
        "whole-document semantic closure",
    )
    require(document["program_id"] == "AE-SQ8", "program")
    require(document["candidate_id"] == "AE-SQ8-SLEC-8", "candidate")
    require(document["authority_status"] == "F0_INITIAL_AUTHORITY_CLOSED", "state")

    owner = document["owner_authorization"]
    require(owner["authorized"] is True, "owner")
    require(owner["additional_diagnostic_calls_authorized"] is False, "diagnostic")
    require(
        owner[
            "corpus_authoring_authorized_only_after_exact_committed_F1G_full_F3_boundary_pass"
        ]
        is True,
        "author gate",
    )
    require(
        owner["downstream_execution_authorized_by_this_artifact"] is False,
        "downstream",
    )

    predecessor = document["predecessor_terminal_history"]
    require(predecessor["terminal_edge"] == "SQ7-F3:NOT_PASS->SQ7-AR", "edge")
    require(
        predecessor["terminal_decision"]
        == {
            "commit": "00d4e245244827cb4d12246725d95fc6287b00a2",
            "tree": "ae9f30c1135dee8407f1366918bd085962024783",
            "path": "evals/ae-sq7/ar/terminal-decision.json",
            "raw_sha256": "f401f7cda3fd9279d7fec49b2f02e6d4156f1268947aa1474c9fcc266ebc3454",
        },
        "terminal",
    )
    f3 = predecessor["sole_f3"]
    require(f3["commit"] == "39384f86f4680866cb2cee945c3eb7b2f3ea10fe", "F3")
    require(f3["parent"] == "323d5b44f2453ce3343648a0ac1519db5a878511", "F2B")
    require(f3["record_blob"] == "c443f8f5eb6ce950ce3b049fa6f7ed48ddaf5647", "record")
    require(
        f3["record_raw_sha256"]
        == "20024841e72a40b426203ca039b5ef70fb4cdfd20d47ddecfed9eac786fd41b8",
        "record raw",
    )
    require(
        f3["aggregate_sha256"]
        == "e59cd5db8d9fc3331b593860d15531c0eeb1dffba0f7719b89f795a02f7e3ea8",
        "aggregate",
    )
    require(
        (f3["status"], f3["attempt"], f3["model_calls"]) == ("FAIL", 1, 0),
        "status",
    )
    require((f3["check_count"], f3["false_check_count"]) == (11, 11), "checks")
    require(
        f3["fail_record_behavior"]
        == "single-interface-exception-produces-fallback-record-with-all-eleven-checks-false",
        "fallback",
    )
    mismatch = predecessor["frozen_interface_mismatch"]
    require(
        mismatch
        == {
            "runner_commit": "1613d46d8fae71259979371717dd567de17ffded",
            "runner_tree": "58a490dfc641ab11a2176c15801bb25b3df428a1",
            "runner_blob": "fedf77d632af3cfe393762bf761591d792bd6b9f",
            "runner_raw_sha256": "a483680c2ee688ae708a63390b2db313d920f2cc5896e0fe28833efe400c775c",
            "frozen_read": "receipt['validator_id']",
            "closed_required_interface": "receipt.validator.validator_id",
            "nested_valid_receipt_satisfies_frozen_runner": False,
            "root_cause_count": 1,
        },
        "mismatch",
    )
    later = predecessor["later_stage_facts"]
    require(later["one_shot_state_present"] is False, "one shot")
    require(
        (later["model_calls"], later["canary_calls"], later["batch_calls"])
        == (0, 0, 0),
        "calls",
    )
    require(
        all(
            later[key] is False
            for key in (
                "f4_created",
                "f5_created",
                "f6_created",
                "aggregate_result_created",
                "handoff_created",
                "downstream_opened",
            )
        ),
        "later stages",
    )

    imported = document["imported_failure_contract"]
    require(
        imported["kind"]
        == "aggregate-F3-receipt-validator-identity-interface-mismatch-only",
        "import",
    )
    require(
        imported["permitted_inputs"]
        == [
            "terminal-and-interface-provenance",
            "external-digest-only-historical-inventory",
        ],
        "inputs",
    )
    require(imported["actual_target_frozen_full_F3_boundary_required"] is True, "route")
    require(
        imported[
            "source_assertion_isolated_lookup_mock_dictionary_partial_checker_or_alternate_boundary_permitted"
        ]
        is False,
        "shortcuts",
    )
    require(
        imported[
            "sq7_candidate_active_role_task_case_split_corpus_label_schedule_author_result_F2_F3_or_execution_bytes_imported"
        ]
        is False,
        "reuse",
    )

    graph = document["phase_graph"]
    require(len(graph["success_edges"]) == 10, "success graph")
    require(len(graph["terminal_edges"]) == 9, "terminal graph")
    require(graph["later_phase_compensation_permitted"] is False, "compensation")
    require(
        graph["retry_reopen_resume_repair_refreeze_or_H8_permitted"] is False,
        "retry",
    )
    budget = document["call_budgets"]
    require((budget["diagnostic_calls"], budget["canary_calls"]) == (0, 4), "front")
    require(
        budget["conditional_batch_presentations"] * budget["calls_per_presentation"]
        == budget["conditional_batch_calls"]
        == 320,
        "batch",
    )
    require(budget["qualification_hard_ceiling"] == 324, "ceiling")
    require(budget["retry_calls_hard_ceiling"] == 0, "retry calls")

    f1 = document["f1_contract"]
    gate = f1["full_F3_boundary_gate"]
    require("_f3_checks-and-build_f3_record" in gate["route"], "production F3")
    require("nested-receipt-validator-validator_id" in gate["positive"], "positive")
    require("top-level-receipt-validator_id" in gate["red_top_level"], "top red")
    require("missing-nested-validator_id" in gate["red_missing"], "missing red")
    require(
        "wrong-nested-validator_id-placement" in gate["red_wrong_nesting"], "wrong red"
    )
    require(
        f1["authoring_before_exact_committed_F1G_full_F3_boundary_pass_permitted"]
        is False,
        "preauthor",
    )
    f2 = document["f2_contract"]
    require(
        f2["historical_replay_input"] == "external-digest-only-inventory", "history"
    )
    require(
        f2["f2a"]["ordered_parents"] == ["exact-SQ8-F1G", "author-A", "author-B"],
        "parents",
    )
    require(len(f2["f2a"]["exact_delta_paths"]) == 4, "F2A")
    require(
        f2["f2b"]["exact_delta_paths"] == ["evals/ae-sq8/f2/run-manifest.json"], "F2B"
    )
    require("global-logical-AND" in document["execution_contract"]["f6"], "AND")
    outcome = document["outcome_contract"]
    require(
        outcome["durable_result_path"] == "evals/ae-sq8/f6/aggregate-result.json",
        "result",
    )
    require(outcome["handoff_and_terminal_may_coexist"] is False, "exclusive")
    require(
        outcome["handoff_confers_downstream_execution_authority"] is False, "handoff"
    )
    require(
        document["namespace"]["active_plan"]
        == {
            "path": "docs/exec-plans/active/ae-sq8.md",
            "raw_sha256": "2740cc7ba62fb91ad3c59d3865b9db4e5b6ca62eae9aed1236eccb876976368f",
        },
        "plan",
    )


class AeSq8ProgramAuthorityTests(unittest.TestCase):
    def test_strict_whole_document_closure_and_plan_binding(self) -> None:
        raw = AUTHORITY.read_bytes()
        self.assertEqual(EXPECTED_RAW_SHA256, hashlib.sha256(raw).hexdigest())
        self.assertTrue(raw.endswith(b"\n"))
        document = strict(raw)
        validate(document)
        self.assertEqual(
            document["namespace"]["active_plan"]["raw_sha256"],
            hashlib.sha256(PLAN.read_bytes()).hexdigest(),
        )

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
        self.assertEqual(
            "e59cd5db8d9fc3331b593860d15531c0eeb1dffba0f7719b89f795a02f7e3ea8",
            aggregate,
        )
        self.assertEqual(
            aggregate, hashlib.sha256(semantic_bytes(unsigned)).hexdigest()
        )
        schema = strict(git_show(F1A, PREFLIGHT_SCHEMA_PATH))
        self.assertEqual([], list(Draft202012Validator(schema).iter_errors(record)))
        checks = record["checks"]
        self.assertEqual(11, len(checks))
        self.assertEqual(11, sum(value is False for value in checks.values()))
        self.assertEqual("FAIL", record["status"])
        self.assertEqual(0, record["model_calls"])

    def test_plan_exposes_full_boundary_repair_and_execution_contract(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        for value in (
            "actual target-frozen production\n`_f3_checks` and `build_f3_record`",
            "synthetic zero-corpus/no-model fixture",
            "receipt.validator.validator_id",
            "top-level `receipt.validator_id`",
            "missing nested `validator_id`",
            "wrong\nnested placement",
            "author CLI refuses to emit or accept any task/case material",
            "two independently routed authors each create 20 fresh",
            "exactly four synthetic non-corpus calls",
            "deterministic global logical AND",
            "evals/ae-sq8/f6/aggregate-result.json",
        ):
            self.assertIn(value, plan)

    def test_mutation_reds_fail_whole_document_closure(self) -> None:
        base = strict(AUTHORITY.read_bytes())
        mutations: list[tuple[tuple[str, ...], object]] = [
            (("candidate_id",), "AE-SQ7-SLEC-7"),
            (("predecessor_terminal_history", "terminal_edge"), "SQ7-F3:PASS"),
            (("predecessor_terminal_history", "sole_f3", "status"), "PASS"),
            (("predecessor_terminal_history", "sole_f3", "false_check_count"), 1),
            (
                (
                    "predecessor_terminal_history",
                    "frozen_interface_mismatch",
                    "root_cause_count",
                ),
                11,
            ),
            (("predecessor_terminal_history", "later_stage_facts", "model_calls"), 1),
            (
                (
                    "imported_failure_contract",
                    "actual_target_frozen_full_F3_boundary_required",
                ),
                False,
            ),
            (("f1_contract", "full_F3_boundary_gate", "route"), "isolated lookup"),
            (("f1_contract", "full_F3_boundary_gate", "positive"), "FAIL"),
            (("f1_contract", "full_F3_boundary_gate", "red_top_level"), "PASS"),
            (("f1_contract", "full_F3_boundary_gate", "red_missing"), "PASS"),
            (("f1_contract", "full_F3_boundary_gate", "red_wrong_nesting"), "PASS"),
            (
                (
                    "f1_contract",
                    "authoring_before_exact_committed_F1G_full_F3_boundary_pass_permitted",
                ),
                True,
            ),
            (("f2_contract", "historical_replay_input"), "SQ7 corpus"),
            (("call_budgets", "retry_calls_hard_ceiling"), 1),
            (("execution_contract", "later_stage_compensation_permitted"), True),
            (("namespace", "active_plan", "raw_sha256"), "0" * 64),
            (("forbidden_actions",), []),
        ]
        extension = copy.deepcopy(base)
        extension["extra"] = True
        with self.assertRaisesRegex(ValueError, "whole-document semantic closure"):
            validate(extension)
        for pointer, replacement in mutations:
            mutation = copy.deepcopy(base)
            target: Any = mutation
            for component in pointer[:-1]:
                target = target[component]
            target[pointer[-1]] = replacement
            with self.subTest(pointer=pointer):
                with self.assertRaisesRegex(
                    ValueError, "whole-document semantic closure"
                ):
                    validate(mutation)

    def test_duplicate_and_nonfinite_json_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate key"):
            strict(b'{"program_id":"AE-SQ8","program_id":"AE-SQ7"}')
        with self.assertRaises(ValueError):
            strict(b'{"value":NaN}')


if __name__ == "__main__":
    unittest.main()
