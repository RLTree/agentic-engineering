"""Strict F0 authority checks for the distinct AE-SQ6 successor."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "evals/ae-sq6/program-authority.json"
PLAN = ROOT / "docs/exec-plans/active/ae-sq6.md"
EXPECTED_RAW_SHA256 = "e4323a98f23173592b40cf433b24ec68252352b68fecbb8abcd6dc9fbb26639e"
EXPECTED_SEMANTIC_SHA256 = (
    "81a66ee158a5f39d8387e9ada5b7087d4edc4f17a7836e9363745038ae47aa67"
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
    require(
        tuple(document)
        == (
            "schema_version",
            "program_id",
            "candidate_id",
            "authority_status",
            "claim_ceiling",
            "owner_authorization",
            "predecessor_terminal_history",
            "imported_failure_contract",
            "phase_graph",
            "model_configuration",
            "call_budgets",
            "f1_contract",
            "f2_contract",
            "execution_contract",
            "outcome_contract",
            "privacy_and_claims",
            "namespace",
            "forbidden_actions",
        ),
        "top-level key closure",
    )
    require(document["schema_version"] == "AE-SQ6-program-authority-v1", "schema")
    require(document["program_id"] == "AE-SQ6", "program")
    require(document["candidate_id"] == "AE-SQ6-SLEC-6", "candidate")
    require(document["authority_status"] == "F0_INITIAL_AUTHORITY_CLOSED", "state")

    owner = document["owner_authorization"]
    require(owner["authorized"] is True, "owner authority")
    require(owner["additional_diagnostic_calls_authorized"] is False, "diagnostics")
    require(
        owner["corpus_authoring_authorized_only_after_exact_F1G_production_loader_pass"]
        is True,
        "author gate",
    )
    require(
        owner["downstream_execution_authorized_by_this_artifact"] is False, "downstream"
    )
    require(owner["release_publish_promotion_authorized"] is False, "release")

    predecessor = document["predecessor_terminal_history"]
    require(predecessor["terminal_edge"] == "SQ5-F1G:NOT_PASS->SQ5-AR", "terminal edge")
    mismatch = predecessor["f1g_receipt_mismatch"]
    require(
        mismatch
        == {
            "path": "evals/ae-sq5/f1/author-template-gate.json",
            "blob": "4a307072266ac6e879ca06704e73b2af4b337418",
            "committed_raw_sha256": "ffe6dca737c8e2a9f93a5bcdf596bec2569d6998efcc79d6583dd39ffb2a216d",
            "committed_size_bytes": 1623,
            "committed_ends_with_lf": True,
            "production_canonical_sha256": "52b7b29bfbe85b8260e659a17273793ebbfa90c3e7c5afb3e0b9d56588a9203d",
            "production_canonical_size_bytes": 1622,
            "production_canonical_ends_with_lf": False,
            "exception_class": "PreflightError",
            "exception_message": "F1G receipt is not exact canonical UTF-8 JSON",
        },
        "exact mismatch",
    )
    require(
        predecessor["later_stage_facts"]
        == {
            "f3_attempted": False,
            "model_calls": 0,
            "canary_calls": 0,
            "batch_calls": 0,
            "aggregate_result_created": False,
            "downstream_opened": False,
        },
        "zero later execution",
    )
    unqualified = predecessor["unqualified_unpublished_objects"]
    require(unqualified["qualification_effect"] == "none", "F2 qualification")
    require(unqualified["reuse_permitted"] is False, "F2 reuse")
    require(unqualified["publication_permitted"] is False, "F2 publication")

    imported = document["imported_failure_contract"]
    require(imported["actual_production_route_required"] is True, "production route")
    require(
        imported["dictionary_mock_source_only_or-reformatted-byte-proof_permitted"]
        is False,
        "mock proof",
    )
    require(
        imported["sq5_candidate_or_active-role-bytes-imported"] is False,
        "candidate import",
    )
    require(
        imported[
            "sq5_task_case_split_corpus_label_schedule_author-or-result-material-imported"
        ]
        is False,
        "corpus import",
    )

    graph = document["phase_graph"]
    require(
        graph["ordered_phases"]
        == [
            "SQ6-F0",
            "SQ6-F1A",
            "SQ6-F1B",
            "SQ6-F1G",
            "SQ6-F2A",
            "SQ6-F2B",
            "SQ6-F3",
            "SQ6-F4",
            "SQ6-F5",
            "SQ6-F6",
            "SQ6-AS-HANDOFF",
            "SQ6-AR",
        ],
        "phase order",
    )
    require(len(graph["success_edges"]) == 10, "success edges")
    require(len(graph["terminal_edges"]) == 9, "terminal edges")
    require(graph["later_phase_compensation_permitted"] is False, "compensation")
    require(
        graph["retry_reopen_resume_repair_refreeze_or_H6_permitted"] is False, "retry"
    )

    budget = document["call_budgets"]
    require(
        (budget["diagnostic_calls"], budget["canary_calls"]) == (0, 4), "front budget"
    )
    require(
        budget["conditional_batch_presentations"] * budget["calls_per_presentation"]
        == budget["conditional_batch_calls"]
        == 320,
        "batch budget",
    )
    require(budget["qualification_hard_ceiling"] == 324, "total budget")
    require(budget["retry_calls_hard_ceiling"] == 0, "retry budget")

    canonical = document["f1_contract"]["canonical_receipt_contract"]
    require(canonical["trailing_line_feed_permitted"] is False, "LF")
    require(
        canonical["writer_and_verifier_share_one_canonical_json_implementation"]
        is True,
        "shared canonicalizer",
    )
    require(
        canonical["verify_exact_committed_blob_not-in-memory-object"] is True,
        "committed bytes",
    )
    require(
        "real-target-frozen-_load_base_state-preauthor-mode"
        in canonical["positive_gate"],
        "positive loader",
    )
    require("no-trailing-line-feed" in canonical["positive_gate"], "positive no LF")
    require("plus-one-line-feed" in canonical["red_gate"], "LF red")
    requirements = document["f1_contract"]["f1g_requirements"]
    require(
        any("authoring-tool-refuses" in value for value in requirements),
        "author refusal",
    )
    require(
        document["f1_contract"][
            "authoring_before_exact_committed_F1G_loader_pass_permitted"
        ]
        is False,
        "preauthor block",
    )

    f2 = document["f2_contract"]
    require(
        f2["fresh_holdout"]
        == "two-independent-authors-times-twenty-cases-after-F1G-PASS-only",
        "fresh corpus",
    )
    require(
        f2["f2a"]["ordered_parents"] == ["exact-SQ6-F1G", "author-A", "author-B"],
        "F2A parents",
    )
    require(len(f2["f2a"]["exact_delta_paths"]) == 4, "F2A closure")
    require(f2["f2a"]["schedule_presentations"] == 80, "schedule")
    require(
        f2["f2b"]["exact_delta_paths"] == ["evals/ae-sq6/f2/run-manifest.json"],
        "F2B closure",
    )
    require(
        f2["retry_replacement_replay_duplicate_extra_or_top_up_permitted"] is False,
        "F2 retry",
    )

    execution = document["execution_contract"]
    require("global-logical-AND" in execution["f6"], "global AND")
    require(
        execution["later_stage_compensation_permitted"] is False,
        "execution compensation",
    )
    outcome = document["outcome_contract"]
    require(
        outcome["durable_result_path"] == "evals/ae-sq6/f6/aggregate-result.json",
        "result",
    )
    require(
        outcome["aggregate_result_fields_only"]
        == [
            "schema_version",
            "program_id",
            "candidate_id",
            "status",
            "aggregate_digest",
        ],
        "aggregate closure",
    )
    require(outcome["handoff_and_terminal_may_coexist"] is False, "exclusive outcome")
    require(
        outcome["handoff_confers_downstream_execution_authority"] is False, "handoff"
    )
    namespace = document["namespace"]
    require(
        namespace["active_plan"]
        == {
            "path": "docs/exec-plans/active/ae-sq6.md",
            "raw_sha256": "70b478470395a33d0468d9196848b058d1ea868a8fb9165bae750c9640908b89",
        },
        "active plan binding",
    )


class AeSq6ProgramAuthorityTests(unittest.TestCase):
    def test_strict_whole_document_closure_and_raw_lock(self) -> None:
        raw = AUTHORITY.read_bytes()
        self.assertEqual(EXPECTED_RAW_SHA256, hashlib.sha256(raw).hexdigest())
        self.assertTrue(raw.endswith(b"\n"))
        document = strict(raw)
        validate(document)
        active_plan = document["namespace"]["active_plan"]
        self.assertEqual("docs/exec-plans/active/ae-sq6.md", active_plan["path"])
        self.assertEqual(
            active_plan["raw_sha256"], hashlib.sha256(PLAN.read_bytes()).hexdigest()
        )

    def test_plan_exposes_the_same_fail_closed_contract(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        for value in (
            "real target-frozen `_load_base_state` preauthor mode",
            "exact\ncommitted no-line-feed bytes",
            "reject the exact receipt\nplus one line feed",
            "authoring tool must fail closed",
            "refuses to emit or accept any task or case material",
            "two independently routed authors each\ncreate 20 fresh cases",
            "80\npresentations with four isolated calls each",
            "deterministic global logical AND",
            "evals/ae-sq6/f6/aggregate-result.json",
        ):
            self.assertIn(value, plan)

    def test_mutation_reds_fail_semantic_closure(self) -> None:
        base = strict(AUTHORITY.read_bytes())
        mutations: list[tuple[tuple[str, ...], object]] = [
            (("candidate_id",), "AE-SQ5-SLEC-5"),
            (("owner_authorization", "additional_diagnostic_calls_authorized"), True),
            (
                (
                    "predecessor_terminal_history",
                    "f1g_receipt_mismatch",
                    "committed_size_bytes",
                ),
                1622,
            ),
            (("predecessor_terminal_history", "later_stage_facts", "model_calls"), 1),
            (("imported_failure_contract", "actual_production_route_required"), False),
            (("phase_graph", "success_edges"), []),
            (("call_budgets", "retry_calls_hard_ceiling"), 1),
            (
                (
                    "f1_contract",
                    "canonical_receipt_contract",
                    "trailing_line_feed_permitted",
                ),
                True,
            ),
            (("f1_contract", "canonical_receipt_contract", "positive_gate"), "mock"),
            (("f1_contract", "f1g_requirements"), []),
            (("f2_contract", "fresh_holdout"), "reuse-SQ5"),
            (("execution_contract", "later_stage_compensation_permitted"), True),
            (
                ("outcome_contract", "handoff_confers_downstream_execution_authority"),
                True,
            ),
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
            strict(b'{"program_id":"AE-SQ6","program_id":"AE-SQ5"}')
        with self.assertRaisesRegex(ValueError, "non-finite"):
            strict(b'{"value":NaN}')


if __name__ == "__main__":
    unittest.main()
