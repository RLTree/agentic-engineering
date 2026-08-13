"""Strict F0 authority checks for the distinct AE-SQ7 successor."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "evals/ae-sq7/program-authority.json"
PLAN = ROOT / "docs/exec-plans/active/ae-sq7.md"
EXPECTED_RAW_SHA256 = "10ec7a6f2a2bf4c303ee98dbf6208caaa1d74dd95e8d5322411a28265f387295"
EXPECTED_SEMANTIC_SHA256 = (
    "4f956cebd797084838c1b20aaf06a628587f4907d9498f15d8c78a553e014609"
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
    require(document["program_id"] == "AE-SQ7", "program")
    require(document["candidate_id"] == "AE-SQ7-SLEC-7", "candidate")
    require(document["authority_status"] == "F0_INITIAL_AUTHORITY_CLOSED", "state")

    owner = document["owner_authorization"]
    require(owner["authorized"] is True, "owner")
    require(owner["additional_diagnostic_calls_authorized"] is False, "diagnostic")
    require(
        owner[
            "corpus_authoring_authorized_only_after_exact_F1G_dual_production_gate_pass"
        ]
        is True,
        "author gate",
    )
    require(
        owner["downstream_execution_authorized_by_this_artifact"] is False, "downstream"
    )

    predecessor = document["predecessor_terminal_history"]
    require(predecessor["terminal_edge"] == "SQ6-F2:NOT_PASS->SQ6-AR", "edge")
    require(
        predecessor["sealed_f1"]
        == {
            "f1a_commit": "bc097d0d690578e68a5e667897381cdfb123c725",
            "f1a_tree": "716b9cd881f30825efb996b1261832403475f1dc",
            "f1b_commit": "278816cf9161e72822fe89197ea4570ec6c1ced6",
            "f1b_tree": "eda37945d5d390118f9edd5ae498b43ec6eede56",
            "f1b_freeze_blob": "9469089409267ca6866b54f6eef6ce75d24b3d50",
            "f1b_freeze_raw_sha256": "201c61fc6e12938ec666ae1346e212f69a068aae1b05afb8e8749c532b64f7d9",
            "f1g_commit": "421ba8911139d48630f411d2af50541590f0dc93",
            "f1g_tree": "685a3784001e07b67c21719019a8c6c6c5e01527",
            "f1g_receipt_blob": "f4328f68d639127b99a9ba15064d458b83d8f3cf",
            "f1g_receipt_raw_sha256": "85ebe24435750ff9809ad3307af347688fa2a661af3dfe7c6012558c66c230ce",
            "f1g_receipt_aggregate_sha256": "c5bb062bad9ee3ae468b8a6c389980bea713555921a6cd183cde1a8a95bda8db",
        },
        "sealed F1",
    )
    authors = predecessor["consumed_author_objects"]
    require(len(authors) == 2, "authors")
    require(
        [row["raw_and_content_sha256"] for row in authors]
        == [
            "ae18a859f0200db63aa4472121a211987c091e5f4a63eeb2ce58e1c60b49cb32",
            "ca93e97f8502b45bdf87f8dd52e20bb3b1ecad40645e705102868d4f926d6ca8",
        ],
        "author digests",
    )
    validation = predecessor["sole_frozen_validation"]
    require(validation["attempts"] == 1, "attempt")
    require(validation["errors"] == ["selected_reference_anchor"], "error")
    require(validation["holds"] == [], "holds")
    require(validation["qualified_case_ids"] == 40, "qualified")
    require(
        validation["profile"]
        == {"none": 6, "single": 16, "two": 8, "cap": 4, "explicit": 4, "uncertain": 2},
        "profile",
    )
    require(validation["all_six_two_slot_pairs_present"] is True, "pairs")
    require(validation["cross_split_comparisons"] == 400, "comparisons")
    require(
        validation["maximum_cross_split_similarity"] == 0.2638888888888889, "similarity"
    )
    require(validation["frozen_similarity_threshold"] == 0.8, "threshold")
    require(validation["historical_digest_count"] == 768, "history")
    require(validation["qualification_effect"] == "none", "qualification")
    require(validation["reuse_permitted"] is False, "reuse")
    later = predecessor["later_stage_facts"]
    require(later["f2a_created"] is False and later["f2b_created"] is False, "F2")
    require(later["f3_attempted"] is False, "F3")
    require(later["one_shot_state_present"] is False, "one shot")
    require(
        (later["model_calls"], later["canary_calls"], later["batch_calls"])
        == (0, 0, 0),
        "calls",
    )

    imported = document["imported_failure_contract"]
    require(
        imported["kind"] == "aggregate-selected-reference-anchor-validation-seam-only",
        "import",
    )
    require(
        imported["exact_production_validator_and_resolver_route_required"] is True,
        "route",
    )
    require(
        imported["source_mock_dictionary_or-alternate-resolver-proof_permitted"]
        is False,
        "mock",
    )
    require(
        imported["sq6_candidate_or_active-role-bytes-imported"] is False,
        "candidate reuse",
    )
    require(
        imported[
            "sq6_task_case_split_corpus_label_schedule_author-or-result-material-imported"
        ]
        is False,
        "material reuse",
    )

    graph = document["phase_graph"]
    require(len(graph["success_edges"]) == 10, "success graph")
    require(len(graph["terminal_edges"]) == 9, "terminal graph")
    require(graph["later_phase_compensation_permitted"] is False, "compensation")
    require(
        graph["retry_reopen_resume_repair_refreeze_or_H7_permitted"] is False, "retry"
    )
    budget = document["call_budgets"]
    require(
        (budget["diagnostic_calls"], budget["canary_calls"]) == (0, 4), "front calls"
    )
    require(
        budget["conditional_batch_presentations"] * budget["calls_per_presentation"]
        == budget["conditional_batch_calls"]
        == 320,
        "batch",
    )
    require(budget["qualification_hard_ceiling"] == 324, "ceiling")
    require(budget["retry_calls_hard_ceiling"] == 0, "retry calls")

    f1 = document["f1_contract"]
    canonical = f1["canonical_receipt_gate"]
    require(canonical["trailing_line_feed_permitted"] is False, "LF")
    require(
        canonical["verify_exact_committed_blob_not-in-memory-object"] is True, "blob"
    )
    anchor = f1["selected_reference_anchor_gate"]
    require(
        anchor["route"] == "exact-target-frozen-production-validator-and-resolver",
        "anchor route",
    )
    require(
        "correct-selected-reference-anchor-PASS" == anchor["positive"],
        "anchor positive",
    )
    require("missing-selected-reference-anchor" in anchor["red_missing"], "missing red")
    require("wrong-selected-reference-anchor" in anchor["red_wrong"], "wrong red")
    require(
        f1["authoring_before_exact_committed_F1G_dual_gate_pass_permitted"] is False,
        "preauthor",
    )

    f2 = document["f2_contract"]
    require(
        f2["fresh_holdout"]
        == "two-independent-authors-times-twenty-cases-after-F1G-PASS-only",
        "fresh",
    )
    require(
        f2["f2a"]["ordered_parents"] == ["exact-SQ7-F1G", "author-A", "author-B"],
        "parents",
    )
    require(len(f2["f2a"]["exact_delta_paths"]) == 4, "F2A closure")
    require(
        f2["f2b"]["exact_delta_paths"] == ["evals/ae-sq7/f2/run-manifest.json"],
        "F2B closure",
    )
    require("global-logical-AND" in document["execution_contract"]["f6"], "AND")
    outcome = document["outcome_contract"]
    require(
        outcome["durable_result_path"] == "evals/ae-sq7/f6/aggregate-result.json",
        "result",
    )
    require(outcome["handoff_and_terminal_may_coexist"] is False, "exclusive")
    require(
        outcome["handoff_confers_downstream_execution_authority"] is False, "handoff"
    )
    namespace = document["namespace"]
    require(
        namespace["active_plan"]
        == {
            "path": "docs/exec-plans/active/ae-sq7.md",
            "raw_sha256": "498a4d0a8a2495b6d58d213514d0884bee910d9618987208fb44caa841498797",
        },
        "plan",
    )


class AeSq7ProgramAuthorityTests(unittest.TestCase):
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

    def test_plan_exposes_closed_repair_and_execution_contract(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        for value in (
            "selected_reference_anchor",
            "exact target-frozen production validator and resolver",
            "reference-requiring selected anchors",
            "omit the selected reference anchor",
            "wrong selected reference\nanchor",
            "real target-frozen `_load_base_state`",
            "plus one line feed",
            "refuses to emit or accept task/case material",
            "two independently routed authors each create 20 fresh",
            "exactly four synthetic non-corpus calls",
            "deterministic global logical AND",
            "evals/ae-sq7/f6/aggregate-result.json",
        ):
            self.assertIn(value, plan)

    def test_mutation_reds_fail_whole_document_closure(self) -> None:
        base = strict(AUTHORITY.read_bytes())
        mutations: list[tuple[tuple[str, ...], object]] = [
            (("candidate_id",), "AE-SQ6-SLEC-6"),
            (("predecessor_terminal_history", "terminal_edge"), "SQ6-F2:PASS"),
            (("predecessor_terminal_history", "sole_frozen_validation", "errors"), []),
            (("predecessor_terminal_history", "later_stage_facts", "model_calls"), 1),
            (
                (
                    "imported_failure_contract",
                    "exact_production_validator_and_resolver_route_required",
                ),
                False,
            ),
            (("f1_contract", "selected_reference_anchor_gate", "positive"), "mock"),
            (
                ("f1_contract", "selected_reference_anchor_gate", "red_missing"),
                "accept",
            ),
            (("f1_contract", "selected_reference_anchor_gate", "red_wrong"), "accept"),
            (
                (
                    "f1_contract",
                    "authoring_before_exact_committed_F1G_dual_gate_pass_permitted",
                ),
                True,
            ),
            (("f2_contract", "fresh_holdout"), "reuse-SQ6"),
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
            strict(b'{"program_id":"AE-SQ7","program_id":"AE-SQ6"}')
        with self.assertRaisesRegex(ValueError, "non-finite"):
            strict(b'{"value":NaN}')


if __name__ == "__main__":
    unittest.main()
