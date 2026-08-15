"""Strict F0 checks for the distinct AE-SQ9 clean-process successor."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "evals/ae-sq9/program-authority.json"
EXPECTED_RAW_SHA256 = "529c2a03d5c94c4505ed67c1c129a68fab1c73df4f6106098ec073512eafea3c"
EXPECTED_SEMANTIC_SHA256 = (
    "0f134184062b8aca0915b7e70f5c37ca0cc5e0b8c3f15574387cd5134c5ec2ec"
)
F0 = "88c1b04dc049ab7656e811df9bc3f9e33276f778"


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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(document: dict[str, Any]) -> None:
    require(
        hashlib.sha256(semantic_bytes(document)).hexdigest()
        == EXPECTED_SEMANTIC_SHA256,
        "whole-document semantic closure",
    )
    require(document["program_id"] == "AE-SQ9", "program")
    require(document["candidate_id"] == "AE-SQ9-SLEC-9", "candidate")
    require(document["authority_status"] == "F0_INITIAL_AUTHORITY_CLOSED", "status")
    owner = document["owner_authorization"]
    require(owner["authorized"] is True, "owner")
    require(owner["additional_diagnostic_calls_authorized"] is False, "diagnostic")
    require(
        owner["downstream_execution_authorized_by_this_artifact"] is False, "downstream"
    )

    predecessor = document["predecessor_terminal_history"]
    require(predecessor["terminal_edge"] == "SQ8-F2B:NOT_PASS->SQ8-AR", "edge")
    require(
        predecessor["terminal_decision"]
        == {
            "commit": "f455f582e8d94356fab142f4d51c8ef825c446ff",
            "tree": "e6bbed7ababbf95b4809e21108c62ce344d61728",
            "path": "evals/ae-sq8/ar/terminal-decision.json",
            "blob": "53e68cc9557214d842548c9dff19eb4168d7df63",
            "raw_sha256": "0754a58ecb68dbfc5ac5b8b3d5aacbeca4e131a3724fadaea8d1e28d2f91ccd0",
        },
        "terminal custody",
    )
    failure = predecessor["process_boundary_failure"]
    require(failure["root_cause_count"] == 1, "root count")
    require(failure["durable_command_receipt_present"] is False, "receipt honesty")
    require(
        failure["rejection"]
        == "ambient module poisoning detected: resolve_ae_sq8_slec",
        "rejection",
    )
    require(
        failure["orchestration_shape"]
        == "validate-corpora-and-load-base-state-in-one-interpreter",
        "shape",
    )
    later = predecessor["later_stage_facts"]
    require(
        (later["model_calls"], later["canary_calls"], later["batch_calls"])
        == (0, 0, 0),
        "calls",
    )
    require(
        all(
            later[key] is False
            for key in (
                "f3_created",
                "one_shot_state_present",
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
        imported["same_process_validation_then_loader_permitted"] is False,
        "same process",
    )
    require(imported["fresh_child_interpreter_required"] is True, "child")
    require(imported["durable_receipt_required"] is True, "durable")
    require(imported["sq8_candidate_qualification_imported"] is False, "qualification")

    graph = document["phase_graph"]
    require(graph["ordered_phases"][6] == "SQ9-F2G", "F2G phase")
    require("SQ9-F2B:PASS->SQ9-F2G" in graph["success_edges"], "F2B edge")
    require("SQ9-F2G:PASS->SQ9-F3" in graph["success_edges"], "F2G edge")
    require("SQ9-F2G:NOT_PASS->SQ9-AR" in graph["terminal_edges"], "F2G terminal")
    require(graph["later_phase_compensation_permitted"] is False, "compensation")
    require(
        graph["retry_reopen_resume_repair_refreeze_or_H9_permitted"] is False, "retry"
    )

    budget = document["call_budgets"]
    require(budget["diagnostic_calls"] == 0, "diagnostic calls")
    require(budget["canary_calls"] == 4, "canary")
    require(
        budget["conditional_batch_presentations"] * budget["calls_per_presentation"]
        == budget["conditional_batch_calls"]
        == 320,
        "batch",
    )
    require(budget["qualification_hard_ceiling"] == 324, "ceiling")
    require(budget["retry_calls_hard_ceiling"] == 0, "retry calls")

    f1 = document["f1_contract"]
    gate = f1["f1g_clean_process_gate"]
    require(gate["production_command"] == "scripts/verify_ae_sq9_f2b.py", "command")
    require(
        gate["positive_parent_preimports_resolver_clean_child_passes"] is True,
        "positive",
    )
    require(gate["red_child_poisoned"] == "REJECTED", "child red")
    require(gate["red_same_process_validation_then_loader"] == "REJECTED", "same red")
    require(gate["model_calls"] == 0, "gate calls")
    require(
        f1["authoring_before_exact_committed_F1G_clean_process_gate_pass_permitted"]
        is False,
        "authoring gate",
    )

    f2 = document["f2_contract"]
    require(
        f2["f2a"]["ordered_parents"] == ["exact-SQ9-F1G", "author-A", "author-B"],
        "parents",
    )
    require(len(f2["f2a"]["exact_delta_paths"]) == 4, "F2A")
    require(f2["f2b"]["transient_loader_output_establishes_pass"] is False, "transient")
    require(
        f2["f2g"]["exact_delta_paths"] == ["evals/ae-sq9/f2/f2b-loader-gate.json"],
        "F2G path",
    )
    require(f2["f2g"]["clean_child_attempts"] == 1, "attempt")
    attempt = f2["f2g"]["durable_attempt_state"]
    require(
        attempt["path"] == ".git-common-dir/.ae-sq9-f2g/state.json",
        "attempt state path",
    )
    require(attempt["claim_before_child_launch"] is True, "claim timing")
    require(attempt["exclusive_create"] is True, "exclusive claim")
    require(attempt["statuses"] == ["claimed", "completed", "invalid"], "states")
    require(
        attempt["reset_delete_replace_or_relaunch_permitted"] is False,
        "state retry",
    )
    require(
        attempt["completed_state_binds_receipt_raw_sha256_and_F2G_commit"] is True,
        "completion binding",
    )
    require(f2["f2g"]["only_exact_committed_PASS_opens_F3"] is True, "open F3")
    require(
        f2["retry_replacement_replay_duplicate_extra_or_top_up_permitted"] is False,
        "F2 retry",
    )

    require("global-logical-AND" in document["execution_contract"]["f6"], "AND")
    outcome = document["outcome_contract"]
    require(
        outcome["durable_result_path"] == "evals/ae-sq9/f6/aggregate-result.json",
        "result",
    )
    require(outcome["handoff_and_terminal_may_coexist"] is False, "exclusive")
    require(
        outcome["handoff_confers_downstream_execution_authority"] is False, "handoff"
    )
    require(
        document["namespace"]["active_plan"]
        == {
            "path": "docs/exec-plans/active/ae-sq9.md",
            "raw_sha256": "7d01de0811e2eea877d21206b42626ec3d447702c63d573ac3b8c33570b728f1",
        },
        "plan",
    )


def mutate_leaf(value: object, path: tuple[object, ...]) -> object:
    result = copy.deepcopy(value)
    cursor: Any = result
    for key in path[:-1]:
        cursor = cursor[key]
    key = path[-1]
    old = cursor[key]
    if type(old) is bool:
        cursor[key] = not old
    elif type(old) is int:
        cursor[key] = old + 1
    elif type(old) is str:
        cursor[key] = old + "-drift"
    else:
        raise AssertionError(f"unsupported mutation leaf: {path}")
    return result


class AeSq9AuthorityTests(unittest.TestCase):
    def test_exact_bytes_semantics_and_plan_binding(self) -> None:
        raw = AUTHORITY.read_bytes()
        self.assertEqual(EXPECTED_RAW_SHA256, hashlib.sha256(raw).hexdigest())
        document = strict(raw)
        self.assertEqual(
            EXPECTED_SEMANTIC_SHA256,
            hashlib.sha256(semantic_bytes(document)).hexdigest(),
        )
        self.assertEqual(
            document["namespace"]["active_plan"]["raw_sha256"],
            hashlib.sha256(
                subprocess.run(
                    ["git", "show", f"{F0}:docs/exec-plans/active/ae-sq9.md"],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                ).stdout
            ).hexdigest(),
        )
        validate(document)

    def test_exact_predecessor_git_custody_without_corpus_content(self) -> None:
        document = strict(AUTHORITY.read_bytes())
        predecessor = document["predecessor_terminal_history"]
        commits = [
            predecessor["terminal_decision"],
            predecessor["frozen_f1g"],
            *predecessor["sealed_authors"],
            predecessor["frozen_f2a"],
            predecessor["frozen_f2b"],
        ]
        for entry in commits:
            fields = subprocess.run(
                ["git", "show", "-s", "--format=%T", entry["commit"]],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(entry["tree"], fields)
        terminal = predecessor["terminal_decision"]
        raw = subprocess.run(
            ["git", "show", f'{terminal["commit"]}:{terminal["path"]}'],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(terminal["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(
            terminal["blob"],
            subprocess.run(
                ["git", "rev-parse", f'{terminal["commit"]}:{terminal["path"]}'],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
        )

    def test_contract_has_no_sq9_candidate_or_later_artifacts(self) -> None:
        introduction = subprocess.run(
            [
                "git",
                "log",
                "--all",
                "--format=%H",
                "--diff-filter=A",
                "--",
                "evals/ae-sq9/program-authority.json",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        if introduction:
            paths = subprocess.run(
                ["git", "ls-tree", "-r", "--name-only", introduction[0]],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            self.assertFalse(
                any(
                    path.startswith(
                        (
                            "evals/ae-sq9/f1/",
                            "evals/ae-sq9/f2/",
                            "evals/ae-sq9/f3/",
                            "evals/ae-sq9/f4/",
                            "evals/ae-sq9/f5/",
                            "evals/ae-sq9/f6/",
                            "evals/ae-sq9/as/",
                            "evals/ae-sq9/ar/",
                        )
                    )
                    for path in paths
                )
            )
        else:
            self.assertFalse((ROOT / "evals/ae-sq9/f1").exists())
            self.assertFalse((ROOT / "evals/ae-sq9/f2").exists())

    def test_material_semantic_mutations_all_fail(self) -> None:
        document = strict(AUTHORITY.read_bytes())
        paths = [
            ("program_id",),
            ("candidate_id",),
            ("owner_authorization", "authorized"),
            ("predecessor_terminal_history", "terminal_edge"),
            (
                "predecessor_terminal_history",
                "process_boundary_failure",
                "root_cause_count",
            ),
            (
                "predecessor_terminal_history",
                "process_boundary_failure",
                "durable_command_receipt_present",
            ),
            ("imported_failure_contract", "fresh_child_interpreter_required"),
            (
                "imported_failure_contract",
                "same_process_validation_then_loader_permitted",
            ),
            ("phase_graph", "later_phase_compensation_permitted"),
            ("call_budgets", "qualification_hard_ceiling"),
            ("f1_contract", "f1g_clean_process_gate", "production_command"),
            ("f1_contract", "f1g_clean_process_gate", "red_child_poisoned"),
            ("f2_contract", "f2b", "transient_loader_output_establishes_pass"),
            ("f2_contract", "f2g", "clean_child_attempts"),
            (
                "f2_contract",
                "f2g",
                "durable_attempt_state",
                "claim_before_child_launch",
            ),
            (
                "f2_contract",
                "f2g",
                "durable_attempt_state",
                "reset_delete_replace_or_relaunch_permitted",
            ),
            ("f2_contract", "f2g", "only_exact_committed_PASS_opens_F3"),
            ("outcome_contract", "handoff_confers_downstream_execution_authority"),
            ("namespace", "active_plan", "raw_sha256"),
        ]
        for path in paths:
            with self.subTest(path=path), self.assertRaisesRegex(
                ValueError, "whole-document semantic closure"
            ):
                validate(mutate_leaf(document, path))

    def test_frozen_f0_plan_has_required_clean_process_and_receipt_contract(
        self,
    ) -> None:
        plan = subprocess.run(
            ["git", "show", f"{F0}:docs/exec-plans/active/ae-sq9.md"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        for fact in (
            "F2B -> F2G -> F3",
            "verify_ae_sq9_f2b.py",
            "fresh child interpreter",
            "imports `resolve_ae_sq9_slec` in the parent",
            "same-process validation followed by loader invocation",
            "f2b-loader-gate.json",
            ".git-common-dir/.ae-sq9-f2g/state.json",
            "Only an\nexact committed `SQ9-F2G:PASS` opens F3",
            "retry ceiling is zero",
            "at most 320 calls",
            "global logical AND",
        ):
            self.assertIn(fact, plan)

    def test_duplicate_and_nonfinite_json_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate key"):
            strict(b'{"program_id":"AE-SQ9","program_id":"AE-SQ8"}')
        with self.assertRaises(ValueError):
            strict(b'{"value":Infinity}')


if __name__ == "__main__":
    unittest.main()
