"""Strict F0 authority checks for the distinct AE-SQ4 successor."""

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
AUTHORITY_PATH = ROOT / "evals/ae-sq4/program-authority.json"
PLAN_PATH = ROOT / "docs/exec-plans/active/ae-sq4.md"
TERMINAL_PATH = ROOT / "evals/ae-sq3/ar/terminal-decision.json"
FOUNDATION_PATH = ROOT / "docs/foundations/current-2026-08-08.md"
LOG_PATH = ROOT / "docs/foundations/decision-log.csv"
D0_COMMIT = "e2562ca4da5f3dc14fb07c1522f911e2dfe4334d"
F0_BASE = "c06c433cdc2581e1747c10e520eb2fdd857cdccd"
HEX64 = set("0123456789abcdef")


KEYS = {
    "/": (
        "schema_version",
        "program_id",
        "authority_status",
        "claim_ceiling",
        "owner_authorization",
        "predecessor_terminal_history",
        "imported_source_contract",
        "sq2_d0_source_custody",
        "corrected_d0_checker_contract",
        "phase_graph",
        "diagnosed_repair",
        "model_configuration",
        "call_budgets",
        "f1_freeze",
        "durable_state_contract",
        "corpus_contract",
        "zero_model_preflight",
        "qualification_execution",
        "global_and",
        "routing_and_claims",
        "namespace",
        "forbidden_actions",
        "acceptance",
    ),
    "/owner_authorization": (
        "authorized",
        "scope",
        "successor_kind",
        "candidate_id",
        "not_semantics",
        "authorized_phases",
        "live_model_phases",
        "additional_diagnostic_calls_authorized",
        "live_calls_authorized_within_gate_and_budget",
        "additional_owner_approval_required_for_authorized_phases",
        "corpus_authoring_authorized_only_after_F1B",
        "downstream_execution_authorized_by_this_artifact",
        "release_publish_promotion_authorized",
        "deletion_or_migration_authorized",
    ),
    "/predecessor_terminal_history": (
        "program_id",
        "status",
        "terminal_stage",
        "terminal_reason",
        "terminal_decision",
        "terminal_plan",
        "frozen_program_authority",
        "preterminal_plan",
        "canonical_f1a",
        "published_sibling",
        "later_stage_facts",
        "predecessor_bytes_write_permitted",
        "predecessor_state_delete_or_migrate_permitted",
        "EXECPLAN_write_permitted",
    ),
    "/predecessor_terminal_history/terminal_decision": ("path", "raw_sha256"),
    "/predecessor_terminal_history/terminal_plan": ("path", "raw_sha256"),
    "/predecessor_terminal_history/frozen_program_authority": (
        "commit",
        "path",
        "blob",
        "raw_sha256",
    ),
    "/predecessor_terminal_history/preterminal_plan": (
        "commit",
        "path",
        "blob",
        "raw_sha256",
    ),
    "/predecessor_terminal_history/canonical_f1a": (
        "commit",
        "tree",
        "parent",
        "status",
        "checker_path",
        "checker_blob",
        "checker_raw_sha256",
        "f1b_created",
    ),
    "/predecessor_terminal_history/published_sibling": (
        "commit",
        "tree",
        "parent",
        "status",
        "same_checker_blob",
        "f1b_created",
    ),
    "/predecessor_terminal_history/later_stage_facts": (
        "f1b_freeze_created",
        "corpus_authored",
        "preflight_executed",
        "diagnostic_calls",
        "canary_calls",
        "batch_calls",
        "AQ_result_created",
        "downstream_opened",
    ),
    "/imported_source_contract": (
        "kind",
        "sq3_candidate_qualification_imported",
        "sq3_candidate_identity_continued",
        "sq3_corpus_task_label_or_result_material_imported",
        "sq3_source_may_be_used_as_implementation_evidence",
        "new_SQ4_custody_required_for_every_candidate_byte",
        "permitted_use",
        "behavioral_tuning_permitted",
        "evaluator_threshold_tuning_permitted",
        "result_informed_change_permitted",
    ),
    "/sq2_d0_source_custody": (
        "commit",
        "diagnostic_record",
        "diagnostic_authority",
        "diagnostic_schema",
        "exact_record_identity",
        "exact_top_level_keys_in_order",
        "classification_counts",
        "usage",
        "qualification_effect",
    ),
    "/sq2_d0_source_custody/diagnostic_record": (
        "path",
        "blob",
        "raw_sha256",
        "record_sha256",
        "aggregate_sha256",
    ),
    "/sq2_d0_source_custody/diagnostic_authority": ("path", "blob", "raw_sha256"),
    "/sq2_d0_source_custody/diagnostic_schema": ("path", "blob", "raw_sha256"),
    "/sq2_d0_source_custody/exact_record_identity": (
        "program_id_field",
        "diagnostic_id",
        "mode",
        "status",
    ),
    "/sq2_d0_source_custody/classification_counts": (
        "transport_spawn",
        "process_exit",
        "signal_exit",
        "timeout",
        "empty_stdout",
        "invalid_jsonl",
        "unknown_event",
        "missing_completed_message",
        "provider_request_rejected",
        "schema_unsupported",
        "schema_invalid",
        "semantic_invalid",
        "valid_completed",
        "other_fail_closed",
    ),
    "/sq2_d0_source_custody/usage": (
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "total_tokens",
    ),
    "/corrected_d0_checker_contract": (
        "must_validate_exact_frozen_record",
        "must_validate_commit_path_blob_and_raw_sha256",
        "must_validate_authority_and_schema_raw_sha256",
        "must_recompute_record_and_aggregate_sha256",
        "must_validate_exact_closed_field_set_and_types",
        "must_validate_four_schema_unsupported_and_zero_usage",
        "invented_program_id_required",
        "mode_diagnostic_required",
        "mode_live_required",
        "D0_rewrite_or_surrogate_permitted",
        "fail_closed",
    ),
    "/phase_graph": (
        "ordered_phases",
        "success_edges",
        "terminal_edges",
        "later_phase_compensation_permitted",
        "additional_active_phases_permitted",
        "additional_active_edges_permitted",
        "reopen_resume_retry_or_refreeze_permitted",
    ),
    "/diagnosed_repair": (
        "repair_id",
        "additional_diagnostic_calls",
        "provider_schema_permitted_keywords",
        "provider_schema_forbidden_keywords",
        "provider_object_contract",
        "local_semantic_validation",
        "lifecycle_contract",
        "raw_persistence_permitted",
        "aggregate_only_projection_required",
        "result_informed_repair_permitted",
    ),
    "/diagnosed_repair/provider_object_contract": (
        "all_properties_required",
        "additionalProperties_must_be_false",
        "undeclared_keywords_permitted",
        "recursive_closure_required",
    ),
    "/diagnosed_repair/local_semantic_validation": (
        "required",
        "position",
        "enforces",
        "provider_validation_substitute",
        "fail_closed",
    ),
    "/diagnosed_repair/lifecycle_contract": (
        "observation_requires",
        "stdout_presence_is_observation",
        "process_exit_alone_is_observation",
        "stderr_text_is_observation",
        "timeout_is_observation",
        "unknown_tool_effect_malformed_duplicate_or_extra_event_route",
    ),
    "/model_configuration": (
        "model_id",
        "reasoning_effort",
        "applies_to_phases",
        "model_fallback_permitted",
        "provider_fallback_permitted",
        "reasoning_fallback_permitted",
        "mode_fallback_permitted",
    ),
    "/call_budgets": (
        "counting_unit",
        "diagnostic_calls",
        "canary_calls",
        "conditional_batch_calls",
        "qualification_hard_ceiling",
        "retry_calls_hard_ceiling",
        "failed_malformed_rejected_empty_or_timed_out_attempts_count",
        "unused_calls_transfer_permitted",
        "top_up_replacement_or_replay_calls_permitted",
        "downstream_call_budget_in_this_authority",
    ),
    "/f1_freeze": (
        "implementation_phase",
        "freeze_phase",
        "required_sequence",
        "candidate_id",
        "accepted_F1A_count",
        "alternate_sibling_or_second_F1A_permitted",
        "same_program_repair_or_refreeze_permitted",
        "F1A_forbidden_artifacts",
        "F1B_only_new_program_artifact",
        "required_exact_bindings",
        "independent_strict_review_required",
        "corpus_authoring_before_F1B_pass_permitted",
        "post_F1B_semantic_change_permitted",
        "not_pass_route",
    ),
    "/durable_state_contract": (
        "schema_version",
        "purpose",
        "exact_top_level_keys_in_canonical_order",
        "program_id",
        "exact_binding_keys_in_canonical_order",
        "binding_value_type",
        "custody_key_derivation",
        "status_enum",
        "record_sha256_contract",
        "state_sha256_derivation",
        "additional_top_level_or_nested_keys_permitted",
        "atomic_claim",
        "existing_or_unsafe_state_route",
        "interruption_after_claim_route",
        "terminal_replacement",
        "dry_run_or_preflight_claim_permitted",
        "strict_recursive_and_mutation_red_tests_required",
    ),
    "/corpus_contract": (
        "phase",
        "authoring_gate",
        "fresh_relative_to_all_predecessors",
        "predecessor_candidate_or_corpus_continuation_permitted",
        "independent_author_count",
        "cases_per_author",
        "total_unique_cases",
        "authors_may_access_each_other_split",
        "authors_may_access_predecessor_task_case_corpus_or_label_material",
        "authors_may_access_diagnostic_model_material_or_live_results",
        "independent_validation_required",
        "conditions",
        "total_presentations",
        "calls_per_presentation",
        "total_batch_calls",
        "historical_no_replay_digest_check_required",
        "result_informed_change_permitted",
        "consumption_trigger",
        "post_consumption_status",
        "retry_replay_duplicate_replacement_extra_or_top_up_permitted",
    ),
    "/zero_model_preflight": (
        "phase",
        "attempts",
        "model_calls",
        "requires",
        "required_checks",
        "pass_required_for_canary",
        "repair_or_second_preflight_permitted",
        "not_pass_route",
    ),
    "/qualification_execution": ("canary", "batch"),
    "/qualification_execution/canary": (
        "phase",
        "requires",
        "units",
        "calls",
        "corpus_content_permitted",
        "calls_per_isolated_child_context",
        "pass_requirements",
        "retry_top_up_replacement_second_canary_or_byte_change_permitted",
        "qualification_effect",
        "not_pass_route",
    ),
    "/qualification_execution/batch": (
        "phase",
        "requires",
        "conditional",
        "total_presentations",
        "calls_per_presentation",
        "hard_call_ceiling",
        "each_case_condition_presented_once",
        "first_call_consumes_both_splits",
        "failed_or_malformed_attempts_count",
        "retry_replay_duplicate_replacement_extra_or_top_up_permitted",
        "complete_valid_route",
        "incomplete_failed_or_invalid_route",
    ),
    "/global_and": (
        "phase",
        "model_calls",
        "operator",
        "scope",
        "required_conditions",
        "false_values",
        "compensation_threshold_repair_override_or_later_cure_permitted",
        "pass_literal",
        "fail_literal",
        "result_count",
        "result_projection",
        "subaggregate_or_raw_result_disclosure_permitted",
    ),
    "/routing_and_claims": (
        "diagnosis_can_qualify_AQ",
        "canary_alone_can_qualify_AQ",
        "incomplete_or_invalid_batch_can_reach_F6",
        "pass_edge",
        "nonpass_edge",
        "SQ4_AS_HANDOFF_is_execution_authority",
        "SQ4_AR_is_terminal",
        "maximum_AQ_claim",
        "isolated_advice_composition_host_field_or_production_claim",
        "release_publish_or_promotion_claim",
    ),
    "/namespace": (
        "artifact_root",
        "active_plan",
        "program_base_commit",
        "program_base_tree",
        "F0_commit",
        "F1A_must_be_direct_child_of_committed_F0",
        "foundation_pointer",
        "decision_log_row_ids",
        "F0_files",
        "predecessor_root_write_permitted",
        "predecessor_durable_state_write_delete_or_migrate_permitted",
        "EXECPLAN_write_permitted",
        "reserved_future_artifacts_confer_state",
    ),
    "/namespace/active_plan": ("path", "raw_sha256"),
    "/acceptance": (
        "F0_status",
        "F0_execution_claim",
        "required_checks",
        "next_authorized_transition",
        "semantic_change_requires_new_program_id",
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def is_hex(value: object, length: int) -> bool:
    return isinstance(value, str) and len(value) == length and not (set(value) - HEX64)


def mapping_at(document: dict[str, Any], pointer: str) -> dict[str, Any]:
    value: Any = document
    for component in pointer.strip("/").split("/") if pointer != "/" else ():
        value = value[component]
    if type(value) is not dict:
        raise ValueError(f"not object: {pointer}")
    return value


def validate(document: dict[str, Any]) -> None:
    for pointer, keys in KEYS.items():
        require(tuple(mapping_at(document, pointer)) == keys, f"closed keys: {pointer}")
    require(document["schema_version"] == "AE-SQ4-program-authority-v1", "schema")
    require(document["program_id"] == "AE-SQ4", "program")
    require(document["authority_status"] == "F0_INITIAL_AUTHORITY_CLOSED", "status")
    owner = document["owner_authorization"]
    require(owner["authorized"] is True, "owner")
    require(owner["candidate_id"] == "AE-SQ4-SLEC-4", "candidate")
    require(
        owner["authorized_phases"]
        == [f"SQ4-F{phase}" for phase in ("1A", "1B", 2, 3, 4, 5, 6)],
        "phases",
    )
    require(owner["live_model_phases"] == ["SQ4-F4", "SQ4-F5"], "live phases")
    for key in (
        "additional_diagnostic_calls_authorized",
        "downstream_execution_authorized_by_this_artifact",
        "release_publish_promotion_authorized",
        "deletion_or_migration_authorized",
    ):
        require(owner[key] is False, key)
    predecessor = document["predecessor_terminal_history"]
    require(
        (
            predecessor["program_id"],
            predecessor["status"],
            predecessor["terminal_stage"],
        )
        == ("AE-SQ3", "terminal", "SQ3-AR"),
        "predecessor",
    )
    require(predecessor["canonical_f1a"]["status"] == "NOT_PASS", "F1A")
    require(
        predecessor["published_sibling"]["status"] == "superseded-NOT_PASS", "sibling"
    )
    require(predecessor["canonical_f1a"]["f1b_created"] is False, "canonical F1B")
    require(predecessor["published_sibling"]["f1b_created"] is False, "sibling F1B")
    facts = predecessor["later_stage_facts"]
    require(
        all(
            value is False or (type(value) is int and value == 0)
            for value in facts.values()
        ),
        "later stages",
    )
    imported = document["imported_source_contract"]
    require(
        imported["kind"]
        == "source-backed-provider-repair-and-exact-SQ2-D0-aggregate-only",
        "import",
    )
    require(
        imported["sq3_candidate_qualification_imported"] is False, "SQ3 qualification"
    )
    require(
        imported["sq3_candidate_identity_continued"] is False, "candidate continuation"
    )
    require(
        imported["new_SQ4_custody_required_for_every_candidate_byte"] is True,
        "new custody",
    )
    d0 = document["sq2_d0_source_custody"]
    require(d0["commit"] == D0_COMMIT, "D0 commit")
    require(
        d0["exact_record_identity"]
        == {
            "program_id_field": "absent",
            "diagnostic_id": "AE-SQ2-D0-2026-08-12-01",
            "mode": "live",
            "status": "completed",
        },
        "D0 identity",
    )
    require(
        all(type(value) is int for value in d0["classification_counts"].values()),
        "classification types",
    )
    require(d0["classification_counts"]["schema_unsupported"] == 4, "classification")
    require(sum(d0["classification_counts"].values()) == 4, "classification sum")
    require(
        all(type(value) is int and value == 0 for value in d0["usage"].values()),
        "usage",
    )
    checker = document["corrected_d0_checker_contract"]
    for key in (
        "must_validate_exact_frozen_record",
        "must_validate_commit_path_blob_and_raw_sha256",
        "must_validate_authority_and_schema_raw_sha256",
        "must_recompute_record_and_aggregate_sha256",
        "must_validate_exact_closed_field_set_and_types",
        "must_validate_four_schema_unsupported_and_zero_usage",
        "mode_live_required",
        "fail_closed",
    ):
        require(checker[key] is True, key)
    for key in (
        "invented_program_id_required",
        "mode_diagnostic_required",
        "D0_rewrite_or_surrogate_permitted",
    ):
        require(checker[key] is False, key)
    graph = document["phase_graph"]
    require(
        graph["ordered_phases"]
        == [
            "SQ4-F0",
            "SQ4-F1A",
            "SQ4-F1B",
            "SQ4-F2",
            "SQ4-F3",
            "SQ4-F4",
            "SQ4-F5",
            "SQ4-F6",
            "SQ4-AS-HANDOFF",
            "SQ4-AR",
        ],
        "phase order",
    )
    require(
        graph["success_edges"]
        == [
            "SQ4-F0->SQ4-F1A",
            "SQ4-F1A:PASS->SQ4-F1B",
            "SQ4-F1B:PASS->SQ4-F2",
            "SQ4-F2:PASS->SQ4-F3",
            "SQ4-F3:PASS->SQ4-F4",
            "SQ4-F4:PASS->SQ4-F5",
            "SQ4-F5:COMPLETE_VALID->SQ4-F6",
            "SQ4-F6:PASS->SQ4-AS-HANDOFF",
        ],
        "success edges",
    )
    require(
        graph["terminal_edges"]
        == [
            "SQ4-F1A:NOT_PASS->SQ4-AR",
            "SQ4-F1B:NOT_PASS->SQ4-AR",
            "SQ4-F2:NOT_PASS->SQ4-AR",
            "SQ4-F3:NOT_PASS->SQ4-AR",
            "SQ4-F4:NOT_PASS->SQ4-AR",
            "SQ4-F5:NOT_COMPLETE_VALID->SQ4-AR",
            "SQ4-F6:NOT_PASS->SQ4-AR",
        ],
        "terminal edges",
    )
    for key in (
        "later_phase_compensation_permitted",
        "additional_active_phases_permitted",
        "additional_active_edges_permitted",
        "reopen_resume_retry_or_refreeze_permitted",
    ):
        require(graph[key] is False, key)
    repair = document["diagnosed_repair"]
    require(repair["additional_diagnostic_calls"] == 0, "diagnostics")
    require(
        "allOf" not in repair["provider_schema_permitted_keywords"], "provider subset"
    )
    require("allOf" in repair["provider_schema_forbidden_keywords"], "allOf")
    require(
        repair["provider_object_contract"]
        == {
            "all_properties_required": True,
            "additionalProperties_must_be_false": True,
            "undeclared_keywords_permitted": False,
            "recursive_closure_required": True,
        },
        "provider closure",
    )
    require(repair["local_semantic_validation"]["required"] is True, "local semantics")
    require(
        repair["local_semantic_validation"]["provider_validation_substitute"] is False,
        "substitute",
    )
    require(repair["raw_persistence_permitted"] is False, "raw")
    model = document["model_configuration"]
    require(
        (model["model_id"], model["reasoning_effort"]) == ("gpt-5.5", "medium"), "model"
    )
    require(
        all(
            model[key] is False
            for key in (
                "model_fallback_permitted",
                "provider_fallback_permitted",
                "reasoning_fallback_permitted",
                "mode_fallback_permitted",
            )
        ),
        "fallback",
    )
    budget = document["call_budgets"]
    require(
        all(
            type(budget[key]) is int
            for key in (
                "diagnostic_calls",
                "canary_calls",
                "conditional_batch_calls",
                "qualification_hard_ceiling",
                "retry_calls_hard_ceiling",
                "downstream_call_budget_in_this_authority",
            )
        ),
        "budget types",
    )
    require(
        (
            budget["diagnostic_calls"],
            budget["canary_calls"],
            budget["conditional_batch_calls"],
            budget["qualification_hard_ceiling"],
            budget["retry_calls_hard_ceiling"],
        )
        == (0, 4, 320, 324, 0),
        "budgets",
    )
    freeze = document["f1_freeze"]
    require(freeze["accepted_F1A_count"] == 1, "F1A count")
    require(
        freeze["required_sequence"]
        == [
            "one-correct-F1A-direct-child-of-SQ4-F0",
            "one-F1B-manifest-only-direct-child-of-passing-F1A",
        ],
        "F1 sequence",
    )
    require(
        freeze["alternate_sibling_or_second_F1A_permitted"] is False, "alternate F1A"
    )
    require(freeze["same_program_repair_or_refreeze_permitted"] is False, "refreeze")
    require(
        freeze["corpus_authoring_before_F1B_pass_permitted"] is False, "early corpus"
    )
    state = document["durable_state_contract"]
    require(state["schema_version"] == "ae-sq4-one-shot-run-index-v1", "state schema")
    require(state["program_id"] == "AE-SQ4", "state program")
    require(
        state["exact_top_level_keys_in_canonical_order"]
        == [
            "binding",
            "custody_key",
            "program_id",
            "record_sha256",
            "schema_version",
            "state_sha256",
            "status",
        ],
        "state keys",
    )
    require(
        state["exact_binding_keys_in_canonical_order"]
        == [
            "corpus_manifest_sha256",
            "f1_freeze_sha256",
            "preflight_record_sha256",
            "program_authority_sha256",
            "run_manifest_sha256",
        ],
        "binding keys",
    )
    require(
        state["additional_top_level_or_nested_keys_permitted"] is False,
        "state extension",
    )
    corpus = document["corpus_contract"]
    require(
        all(
            type(corpus[key]) is int
            for key in (
                "independent_author_count",
                "cases_per_author",
                "total_unique_cases",
                "total_presentations",
                "calls_per_presentation",
                "total_batch_calls",
            )
        ),
        "corpus count types",
    )
    require(
        (
            corpus["independent_author_count"],
            corpus["cases_per_author"],
            corpus["total_unique_cases"],
        )
        == (2, 20, 40),
        "corpus",
    )
    require(
        (
            corpus["total_presentations"],
            corpus["calls_per_presentation"],
            corpus["total_batch_calls"],
        )
        == (80, 4, 320),
        "schedule",
    )
    require(corpus["authors_may_access_each_other_split"] is False, "author isolation")
    preflight = document["zero_model_preflight"]
    require(
        type(preflight["attempts"]) is int and type(preflight["model_calls"]) is int,
        "preflight types",
    )
    require((preflight["attempts"], preflight["model_calls"]) == (1, 0), "preflight")
    require(
        preflight["repair_or_second_preflight_permitted"] is False, "second preflight"
    )
    execution = document["qualification_execution"]
    require(type(execution["canary"]["calls"]) is int, "canary call type")
    require(type(execution["batch"]["hard_call_ceiling"]) is int, "batch call type")
    require(execution["canary"]["calls"] == 4, "canary")
    require(execution["batch"]["hard_call_ceiling"] == 320, "batch")
    require(execution["canary"]["not_pass_route"] == "SQ4-AR", "canary route")
    require(
        execution["batch"]["incomplete_failed_or_invalid_route"] == "SQ4-AR",
        "batch route",
    )
    global_and = document["global_and"]
    require(global_and["operator"] == "logical-AND", "AND")
    require(global_and["phase"] == "SQ4-F6", "AND phase")
    require(
        type(global_and["model_calls"]) is int and global_and["model_calls"] == 0,
        "AND model calls",
    )
    require(
        global_and["required_conditions"] == ["current", "reduced"], "AND conditions"
    )
    require(
        global_and["false_values"]
        == [
            "missing",
            "skipped",
            "undefined",
            "nonfinite",
            "malformed",
            "duplicate",
            "extra",
            "unevaluable",
            "rejected",
            "failed",
        ],
        "AND false-value closure",
    )
    require(
        global_and["compensation_threshold_repair_override_or_later_cure_permitted"]
        is False,
        "compensation",
    )
    require(
        (
            global_and["pass_literal"],
            global_and["fail_literal"],
            global_and["result_count"],
            global_and["result_projection"],
        )
        == (
            "PASS",
            "FAIL",
            1,
            "candidate-bound-aggregate-status-and-digest-only",
        )
        and type(global_and["result_count"]) is int,
        "AND result projection",
    )
    require(
        global_and["subaggregate_or_raw_result_disclosure_permitted"] is False,
        "AND disclosure",
    )
    routing = document["routing_and_claims"]
    require(routing["pass_edge"] == "SQ4-F6:PASS->SQ4-AS-HANDOFF", "pass routing")
    require(routing["nonpass_edge"] == "SQ4-F6:NOT_PASS->SQ4-AR", "nonpass routing")
    require(routing["diagnosis_can_qualify_AQ"] is False, "diagnosis routing")
    require(routing["canary_alone_can_qualify_AQ"] is False, "canary routing")
    require(
        routing["incomplete_or_invalid_batch_can_reach_F6"] is False, "batch routing"
    )
    require(routing["SQ4_AS_HANDOFF_is_execution_authority"] is False, "handoff")
    require(routing["SQ4_AR_is_terminal"] is True, "AR terminal")
    namespace = document["namespace"]
    require(namespace["program_base_commit"] == F0_BASE, "base commit")
    require(namespace["F0_commit"] == "ABSENT_NOT_SELF_BOUND", "self binding")
    require(namespace["F1A_must_be_direct_child_of_committed_F0"] is True, "F1A parent")


def git_show(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=ROOT, check=True, capture_output=True
    ).stdout


class AeSq4ProgramAuthorityTests(unittest.TestCase):
    def test_strict_recursive_contract_and_exact_custody(self) -> None:
        document = strict(AUTHORITY_PATH.read_bytes())
        validate(document)
        self.assertEqual(
            hashlib.sha256(
                git_show(
                    "e8163ebfd74799cef546da176e73589f4a50d31a",
                    "docs/exec-plans/active/ae-sq4.md",
                )
            ).hexdigest(),
            document["namespace"]["active_plan"]["raw_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(TERMINAL_PATH.read_bytes()).hexdigest(),
            document["predecessor_terminal_history"]["terminal_decision"]["raw_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(
                (ROOT / "docs/exec-plans/active/ae-sq3.md").read_bytes()
            ).hexdigest(),
            document["predecessor_terminal_history"]["terminal_plan"]["raw_sha256"],
        )
        self.assertEqual(
            subprocess.run(
                ["git", "rev-parse", f"{F0_BASE}^{{tree}}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            document["namespace"]["program_base_tree"],
        )
        for role in ("diagnostic_record", "diagnostic_authority", "diagnostic_schema"):
            binding = document["sq2_d0_source_custody"][role]
            raw = git_show(D0_COMMIT, binding["path"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), binding["raw_sha256"])
            self.assertEqual(
                subprocess.run(
                    ["git", "rev-parse", f"{D0_COMMIT}:{binding['path']}"],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip(),
                binding["blob"],
            )

    def test_actual_d0_identity_is_closed_and_no_synthetic_surrogate_is_allowed(
        self,
    ) -> None:
        document = strict(AUTHORITY_PATH.read_bytes())
        d0 = document["sq2_d0_source_custody"]
        record = strict(git_show(D0_COMMIT, d0["diagnostic_record"]["path"]))
        self.assertEqual(list(record), d0["exact_top_level_keys_in_order"])
        self.assertNotIn("program_id", record)
        self.assertEqual(
            (record["diagnostic_id"], record["mode"], record["status"]),
            ("AE-SQ2-D0-2026-08-12-01", "live", "completed"),
        )
        self.assertEqual(
            record["record_sha256"], d0["diagnostic_record"]["record_sha256"]
        )
        self.assertEqual(
            record["aggregate_sha256"], d0["diagnostic_record"]["aggregate_sha256"]
        )

    def test_foundation_pointer_and_terminal_successor_rows(self) -> None:
        pointer = "**Active successor plan:** `docs/exec-plans/active/ae-sq8.md` for AE-SQ8 only; AE-SQ7, AE-SQ6, AE-SQ5, AE-SQ4, AE-SQ3, AE-SQ2, AE-SQ1, and `EXECPLAN.md` remain immutable terminal history"
        self.assertEqual(
            FOUNDATION_PATH.read_text(encoding="utf-8").splitlines()[6], pointer
        )
        rows = list(csv.DictReader(io.StringIO(LOG_PATH.read_text(encoding="utf-8"))))
        identifiers = [row["decision_id"] for row in rows]
        self.assertEqual(identifiers.count("AE-SQ3-AR-2026-08-12"), 1)
        self.assertEqual(identifiers.count("AE-SQ4-F0-2026-08-12"), 1)
        self.assertEqual(identifiers.count("AE-SQ4-AR-2026-08-13"), 1)
        self.assertEqual(identifiers.count("AE-SQ5-F0-2026-08-13"), 1)
        self.assertEqual(identifiers.count("AE-SQ5-AR-2026-08-13"), 1)
        self.assertEqual(identifiers.count("AE-SQ6-F0-2026-08-13"), 1)
        self.assertEqual(identifiers.count("AE-SQ6-AR-2026-08-13"), 1)
        self.assertEqual(identifiers.count("AE-SQ7-F0-2026-08-13"), 1)
        self.assertEqual(identifiers.count("AE-SQ7-AR-2026-08-13"), 1)
        self.assertEqual(identifiers.count("AE-SQ8-F0-2026-08-13"), 1)
        self.assertTrue((ROOT / "evals/ae-sq4/f1/repaired-freeze.json").is_file())
        self.assertTrue((ROOT / "evals/ae-sq4/ar/terminal-decision.json").is_file())

    def test_recursive_and_semantic_mutation_reds(self) -> None:
        document = strict(AUTHORITY_PATH.read_bytes())
        changes: list[tuple[tuple[str, ...], object]] = [
            (("owner_authorization", "candidate_id"), "AE-SQ3-SLEC-3"),
            (("owner_authorization", "additional_diagnostic_calls_authorized"), True),
            (("corrected_d0_checker_contract", "invented_program_id_required"), True),
            (("corrected_d0_checker_contract", "mode_live_required"), False),
            (
                ("corrected_d0_checker_contract", "D0_rewrite_or_surrogate_permitted"),
                True,
            ),
            (("phase_graph", "reopen_resume_retry_or_refreeze_permitted"), True),
            (
                ("phase_graph", "success_edges"),
                document["phase_graph"]["success_edges"][1:],
            ),
            (
                ("phase_graph", "terminal_edges"),
                document["phase_graph"]["terminal_edges"][:-1],
            ),
            (("call_budgets", "retry_calls_hard_ceiling"), 1),
            (("call_budgets", "diagnostic_calls"), False),
            (("f1_freeze", "accepted_F1A_count"), 2),
            (("f1_freeze", "alternate_sibling_or_second_F1A_permitted"), True),
            (("f1_freeze", "corpus_authoring_before_F1B_pass_permitted"), True),
            (("zero_model_preflight", "attempts"), 2),
            (("qualification_execution", "canary", "calls"), 5),
            (("global_and", "operator"), "average"),
            (("global_and", "required_conditions"), ["current"]),
            (
                ("global_and", "false_values"),
                document["global_and"]["false_values"][:-1],
            ),
            (("routing_and_claims", "nonpass_edge"), "SQ4-F6:NOT_PASS->SQ4-AS-HANDOFF"),
            (("routing_and_claims", "SQ4_AS_HANDOFF_is_execution_authority"), True),
        ]
        for path, replacement in changes:
            mutation = copy.deepcopy(document)
            target: Any = mutation
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = replacement
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    validate(mutation)
        extension = copy.deepcopy(document)
        extension["corrected_d0_checker_contract"]["extra"] = True
        with self.assertRaises(ValueError):
            validate(extension)

    def test_strict_parser_rejects_duplicate_and_nonfinite_json(self) -> None:
        with self.assertRaises(ValueError):
            strict(b'{"program_id":"AE-SQ4","program_id":"AE-SQ3"}')
        with self.assertRaises(ValueError):
            strict(b'{"value":NaN}')


if __name__ == "__main__":
    unittest.main()
