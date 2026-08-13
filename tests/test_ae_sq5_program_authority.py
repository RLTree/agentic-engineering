"""Strict F0 authority checks for the distinct AE-SQ5 successor."""

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
AUTHORITY_PATH = ROOT / "evals/ae-sq5/program-authority.json"
PLAN_PATH = ROOT / "docs/exec-plans/active/ae-sq5.md"
TERMINAL_PATH = ROOT / "evals/ae-sq4/ar/terminal-decision.json"
TERMINAL_PLAN_PATH = ROOT / "docs/exec-plans/active/ae-sq4.md"
FOUNDATION_PATH = ROOT / "docs/foundations/current-2026-08-08.md"
LOG_PATH = ROOT / "docs/foundations/decision-log.csv"
BASE_COMMIT = "6357b87cfae9e488bbb1489541ec03d577803463"
F2A = "8b1a26dc6951d7052429197af5d8dffe3636bbb3"
AUTHORITY_SEMANTIC_SHA256 = (
    "7f801ca97604f0736bbcea204e1e6f72cb2ded7b8b25368fe766520387c2ff12"
)

EXPECTED_F1_LEDGER = (
    ("candidate_authority", "evals/ae-sq5/f1/slec5-authority.json"),
    ("resolver_and_local_semantic_validator", "scripts/resolve_ae_sq5_slec.py"),
    ("capsule_schema", "evals/ae-sq5/f1/slec5-capsule-schema.json"),
    (
        "semantic_capsule_schema",
        "evals/ae-sq5/f1/slec5-semantic-capsule-schema.json",
    ),
    ("resolution_schema", "evals/ae-sq5/f1/slec5-resolution-schema.json"),
    ("reference_policy", "evals/ae-sq5/f1/slec5-reference-policy.json"),
    ("corpus_schema", "evals/ae-sq5/f1/corpus-schema.json"),
    ("gates", "evals/ae-sq5/f1/gates.json"),
    ("metrics", "evals/ae-sq5/f1/metrics.json"),
    ("evaluator_schema", "evals/ae-sq5/f1/evaluator-schema.json"),
    (
        "corpus_validator_and_expected_authority_helper",
        "scripts/validate_ae_sq5_corpus.py",
    ),
    ("scorer", "scripts/score_ae_sq5_aq.py"),
    ("runner", "scripts/run_ae_sq5_aq.py"),
    ("run_index", "scripts/ae_sq5_run_index.py"),
    ("candidate_checker", "scripts/check_ae_sq5_candidate.py"),
    ("run_manifest_schema", "evals/ae-sq5/f1/run-manifest-schema.json"),
    ("preflight_schema", "evals/ae-sq5/f1/preflight-schema.json"),
    ("result_schema", "evals/ae-sq5/f1/result-schema.json"),
    (
        "historical_digest_test",
        "tests/test_ae_sq5_historical_task_digests.py",
    ),
    ("slec_test", "tests/test_ae_sq5_slec.py"),
    ("provider_schema_test", "tests/test_ae_sq5_provider_schema.py"),
    ("corpus_contract_test", "tests/test_ae_sq5_corpus_contract.py"),
    ("evaluator_test", "tests/test_ae_sq5_evaluator.py"),
    ("run_index_test", "tests/test_ae_sq5_run_index.py"),
    ("candidate_checker_test", "tests/test_check_ae_sq5_candidate.py"),
    ("runner_test", "tests/test_run_ae_sq5_aq.py"),
    (
        "author_template_gate_schema",
        "evals/ae-sq5/f1/author-template-gate-schema.json",
    ),
    ("author_template_builder", "scripts/build_ae_sq5_author_template.py"),
    ("author_template_test", "tests/test_ae_sq5_author_template.py"),
    ("handoff_schema", "evals/ae-sq5/f1/handoff-schema.json"),
    (
        "terminal_decision_schema",
        "evals/ae-sq5/f1/terminal-decision-schema.json",
    ),
)


KEYS = {
    "/": (
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
        "author_template_gate",
        "frozen_target_loading",
        "corpus_contract",
        "f2b_run_manifest_contract",
        "durable_state_contract",
        "zero_model_preflight",
        "qualification_execution",
        "global_and",
        "outcome_artifact_contract",
        "routing_and_claims",
        "privacy",
        "namespace",
        "forbidden_actions",
        "acceptance",
    ),
    "/owner_authorization": (
        "authorized",
        "scope",
        "successor_kind",
        "authorized_phases",
        "live_model_phases",
        "additional_diagnostic_calls_authorized",
        "live_calls_authorized_within_gate_and_budget",
        "additional_owner_approval_required_for_authorized_phases",
        "corpus_authoring_authorized_only_after_exact_F1B_and_F1G_pass",
        "downstream_execution_authorized_by_this_artifact",
        "release_publish_promotion_authorized",
        "deletion_or_migration_authorized",
    ),
    "/predecessor_terminal_history": (
        "program_id",
        "candidate_id",
        "status",
        "terminal_stage",
        "terminal_edge",
        "terminal_reason",
        "terminal_decision",
        "terminal_plan",
        "sealed_f1a",
        "sealed_f1b",
        "failed_f2a",
        "later_stage_facts",
        "predecessor_bytes_write_permitted",
        "predecessor_state_delete_or_migrate_permitted",
        "predecessor_split_author_or_f2a_reuse_permitted",
        "EXECPLAN_write_permitted",
    ),
    "/predecessor_terminal_history/terminal_decision": ("path", "raw_sha256"),
    "/predecessor_terminal_history/terminal_plan": ("path", "raw_sha256"),
    "/predecessor_terminal_history/sealed_f1a": ("commit", "tree"),
    "/predecessor_terminal_history/sealed_f1b": (
        "commit",
        "tree",
        "freeze_raw_sha256",
    ),
    "/predecessor_terminal_history/failed_f2a": (
        "commit",
        "tree",
        "combined_corpus_sha256",
        "status",
    ),
    "/predecessor_terminal_history/later_stage_facts": (
        "f2b_created",
        "preflight_executed",
        "one_shot_state_claimed",
        "diagnostic_calls",
        "canary_calls",
        "batch_calls",
        "AQ_result_created",
        "downstream_opened",
    ),
    "/imported_failure_contract": (
        "kind",
        "exception_class",
        "exception_message",
        "actual_split_candidate_identity",
        "required_candidate_identity",
        "sq4_candidate_qualification_imported",
        "sq4_candidate_identity_or_bytes_continued",
        "sq4_task_case_split_corpus_label_schedule_or_result_material_imported",
        "sq4_standalone_validator_pass_has_qualification_effect",
        "behavioral_tuning_permitted",
        "evaluator_threshold_tuning_permitted",
        "result_informed_change_permitted",
        "permitted_use",
    ),
    "/imported_failure_contract/actual_split_candidate_identity": (
        "commit",
        "tree",
        "role",
    ),
    "/imported_failure_contract/required_candidate_identity": (
        "commit",
        "tree",
        "role",
    ),
    "/phase_graph": (
        "ordered_phases",
        "success_edges",
        "terminal_edges",
        "later_phase_compensation_permitted",
        "additional_active_phases_or_edges_permitted",
        "retry_reopen_resume_repair_refreeze_or_H6_permitted",
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
    "/f1_contract": (
        "implementation_phase",
        "freeze_phase",
        "required_sequence",
        "accepted_F1A_count",
        "alternate_sibling_or_second_F1A_permitted",
        "same_program_repair_or_refreeze_permitted",
        "sq4_candidate_freeze_or-byte-reuse-permitted",
        "F1A_required_components",
        "F1A_forbidden_artifacts",
        "fresh_candidate_closure",
        "external_provenance",
        "F1B_only_new_program_artifact",
        "F1B_must_bind_F1A_implementation_commit_and_tree",
        "independent_strict_review_required",
        "post_F1B_semantic_change_permitted",
        "not_pass_route",
    ),
    "/f1_contract/fresh_candidate_closure": (
        "source_of_truth",
        "sq4_baseline",
        "exact_active_role_count",
        "exact_role_path_ledger",
        "F0_to_F1A_changed_paths_must_equal_ledger_paths",
        "role_alias_path_alias_omission_or_extra_permitted",
        "sq5_path_may_equal_sq4_role_path",
        "any_sq4_F1A_role_blob_or_raw_sha256_reuse_permitted",
        "every_sq5_role_must_differ_from_every_sq4_role_by_blob_and_raw_sha256",
        "all_role_tree_entries_must_be_100644_regular_blobs",
        "stale_AE_SQ4_or_SLEC_4_identity_in_active_role_permitted",
        "closed_provenance_SQ4_identity_exempted_from_owned_identity_check",
        "immutable_predecessor_evidence_permitted_only_as_nonactive_provenance",
        "predecessor_evidence_may_occupy_active_role",
    ),
    "/f1_contract/fresh_candidate_closure/sq4_baseline": (
        "implementation_commit",
        "implementation_tree",
        "freeze_commit",
        "freeze_tree",
        "freeze_path",
        "freeze_blob",
        "freeze_raw_sha256",
        "active_role_count",
    ),
    "/f1_contract/external_provenance": (
        "permitted_roles",
        "historical_digest_inventory",
        "copied_into_SQ5_namespace_or_counted_as_active_F1A_role_permitted",
        "task_case_label_split_schedule_or_result_material_permitted",
    ),
    "/f1_contract/external_provenance/historical_digest_inventory": (
        "commit",
        "tree",
        "path",
        "blob",
        "raw_sha256",
        "content_kind",
    ),
    "/author_template_gate": (
        "phase",
        "requires",
        "attempts",
        "model_calls",
        "task_case_label_or_corpus_content_permitted",
        "real_canonical_byte_round_trip_required",
        "same_frozen_runtime_validation_path_as_F2B_required",
        "receipt_only_commit",
        "receipt_required_bindings",
        "author_commits_must_be_direct_children_of_F1G",
        "F2A_ordered_parent_roles",
        "F2B_and_F3_must_bind_F1G_commit_tree_receipt_blob_and_raw_sha256",
        "synthetic_authority_required_values",
        "red_fixture",
        "validated_taskless_author_template_required",
        "dictionary_only_mock_only_or-source-only-proof_permitted",
        "author_lane_open_before_pass_permitted",
        "repair_or_second_gate_permitted",
        "not_pass_route",
    ),
    "/author_template_gate/synthetic_authority_required_values": (
        "program_id",
        "candidate_id",
        "candidate_commit_role",
        "candidate_tree_role",
        "f1_freeze_sha256_role",
        "all_contract_digests_role",
    ),
    "/author_template_gate/red_fixture": (
        "mutation",
        "required_result",
        "required_exception_class",
        "required_exception_message",
    ),
    "/author_template_gate/receipt_only_commit": (
        "path",
        "schema_path",
        "schema_frozen_in",
        "direct_parent",
        "only_new_program_artifact",
        "exact_receipt_fields",
        "aggregate_sha256_derivation",
    ),
    "/frozen_target_loading": (
        "expected_authority_helper_role",
        "validate_corpora_expected_authority_argument_required",
        "validate_corpora_standalone_qualification_PASS_permitted",
        "production_loader_entrypoint",
        "F1G_and_F2B_must_call_exact_production_loader",
        "production_loader_environment",
        "partial-loader-mock-or-live-worktree-substitution-permitted",
        "checker_source",
        "authority_source",
        "ambient_root_checker_permitted",
        "ambient_root_authority_permitted",
        "ambient_and_target_byte_mismatch_route",
        "checker_or_authority_target_failure_route",
    ),
    "/corpus_contract": (
        "phase",
        "authoring_gate",
        "fresh_relative_to_all_predecessors",
        "sq4_split_author_commit_corpus_manifest_schedule_digest_or_f2a_reuse_permitted",
        "predecessor_candidate_or_corpus_continuation_permitted",
        "independent_author_count",
        "cases_per_author",
        "total_unique_cases",
        "authors_receive_only_validated_taskless_SQ5_template",
        "authors_may_access_each_other_split",
        "authors_may_access_predecessor_task_case_corpus_or_label_material",
        "authors_may_access_diagnostic_model_material_or_live_results",
        "split_authority_must_bind_SQ5_F1A_implementation_identity",
        "split_authority_must_bind_SQ5_F1B_separately",
        "independent_nonauthor_validation_required",
        "F2A_commit_contract",
        "F2_JSON_git_object_mode",
        "strict_canonical_UTF8_JSON_required_for",
        "duplicate_nonfinite_alternate_encoding_trailing_or_noncanonical_bytes_permitted",
        "conditions",
        "total_presentations",
        "calls_per_presentation",
        "total_batch_calls",
        "historical_exact_digest_no_replay_required",
        "result_informed_change_permitted",
        "consumption_trigger",
        "post_consumption_status",
        "retry_replay_duplicate_replacement_extra_or_top_up_permitted",
    ),
    "/corpus_contract/F2A_commit_contract": (
        "commit_kind",
        "exact_ordered_parent_roles",
        "author_A_direct_parent",
        "author_B_direct_parent",
        "exact_artifact_paths_relative_to_F1G",
        "omitted_extra_or_nonregular_artifact_permitted",
        "PASS_requires_exact_topology_artifact_closure_and_content_validation",
        "retry_replacement_or_second_F2A_permitted",
        "not_pass_route",
    ),
    "/f2b_run_manifest_contract": (
        "phase",
        "requires",
        "commit_kind",
        "direct_parent",
        "exact_delta_paths",
        "artifact",
        "embedded_independent_validator_receipt",
        "separate_validation_receipt_artifact_permitted",
        "F2B_PASS_requires_exact_parent_delta_bytes_schema_bindings_and_receipt",
        "only_F2B_PASS_opens_F3",
        "retry_replacement_or_second_F2B_permitted",
        "not_pass_route",
    ),
    "/f2b_run_manifest_contract/artifact": (
        "path",
        "schema_path",
        "schema_frozen_in",
        "git_object_mode",
        "encoding",
        "serialization",
        "exact_top_level_keys_in_canonical_order",
    ),
    "/f2b_run_manifest_contract/embedded_independent_validator_receipt": (
        "location",
        "exact_keys_in_canonical_order",
        "required_bindings",
        "exact_nested_binding_keys",
        "validator_identity_required",
        "status_required",
        "authorship_performed_required",
        "errors_required",
        "holds_required",
        "standalone_validator_PASS_has_qualification_effect",
    ),
    "/f2b_run_manifest_contract/embedded_independent_validator_receipt/exact_nested_binding_keys": (
        "f1a_implementation",
        "f1b_freeze",
        "f1g_gate",
        "f2a_corpus",
        "author_commit_row",
        "artifact_row",
        "validator",
    ),
    "/durable_state_contract": (
        "schema_version",
        "program_id",
        "purpose",
        "exact_top_level_keys_in_canonical_order",
        "exact_binding_keys_in_canonical_order",
        "atomic_claim",
        "existing_unsafe_or_interrupted_state_route",
        "preflight_or_dry_run_claim_permitted",
    ),
    "/zero_model_preflight": (
        "phase",
        "requires",
        "attempts",
        "model_calls",
        "required_checks",
        "pass_required_for_canary",
        "repair_or_second_preflight_permitted",
        "not_pass_route",
    ),
    "/qualification_execution": ("canary", "batch"),
    "/qualification_execution/canary": (
        "phase",
        "requires",
        "calls",
        "corpus_content_permitted",
        "calls_per_isolated_child_context",
        "all_four_valid_completed_capsules_required",
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
        "durable_result_path",
        "durable_result_format",
        "durable_result_raw_sha256_must_equal_run_index_record_sha256",
        "subaggregate_or_raw_result_disclosure_permitted",
    ),
    "/outcome_artifact_contract": (
        "schemas_frozen_in",
        "aggregate_result",
        "handoff",
        "terminal_decision",
        "aggregate_handoff_and_terminal_paths_pairwise_distinct",
        "schema_or_topology_fallback_permitted",
    ),
    "/outcome_artifact_contract/aggregate_result": (
        "path",
        "schema_path",
        "created_only_in",
        "exact_keys_in_canonical_order",
        "exact_constants",
        "aggregate_digest_is_exact_global_AND_digest",
        "raw_sha256_must_equal_run_index_record_sha256",
        "strict_canonical_UTF8_JSON_and_100644_regular_blob_required",
    ),
    "/outcome_artifact_contract/aggregate_result/exact_constants": (
        "schema_version",
        "program_id",
        "candidate_id",
        "status_values",
    ),
    "/outcome_artifact_contract/handoff": (
        "path",
        "schema_path",
        "created_only_on",
        "exact_keys_in_canonical_order",
        "must_bind_aggregate_result_path_and_raw_sha256",
        "source_phase",
        "source_status",
        "authority_effect",
        "terminal_decision_may_coexist",
    ),
    "/outcome_artifact_contract/terminal_decision": (
        "path",
        "schema_path",
        "created_only_on",
        "exact_keys_in_canonical_order",
        "must_bind_exact_terminal_edge_and_last_completed_phase",
        "aggregate_result_binding_required_only_if_F6_was_entered",
        "status",
        "handoff_may_coexist",
    ),
    "/routing_and_claims": (
        "diagnosis_can_qualify_AQ",
        "author_template_gate_can_qualify_AQ",
        "canary_alone_can_qualify_AQ",
        "incomplete_or_invalid_batch_can_reach_F6",
        "pass_edge",
        "nonpass_edge",
        "handoff_artifact_path",
        "terminal_artifact_path",
        "result_handoff_and_terminal_paths_must_be_pairwise_distinct",
        "SQ5_AS_HANDOFF_is_execution_authority",
        "SQ5_AR_is_terminal",
        "maximum_AQ_claim",
        "release_publish_or_promotion_claim",
    ),
    "/privacy": ("forbidden_durable_material", "permitted_external_projection"),
    "/namespace": (
        "artifact_root",
        "active_plan",
        "program_base_commit",
        "program_base_tree",
        "F0_commit",
        "F1A_must_be_direct_child_of_committed_F0",
        "foundation_pointer",
        "decision_log_row_ids",
        "predecessor_root_write_permitted",
        "predecessor_durable_state_write_delete_or_migrate_permitted",
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


def validate(document: dict[str, Any]) -> None:
    semantic_bytes = json.dumps(
        document,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    require(
        hashlib.sha256(semantic_bytes).hexdigest() == AUTHORITY_SEMANTIC_SHA256,
        "authority semantic digest",
    )
    for pointer, keys in KEYS.items():
        value: Any = document
        for component in pointer.strip("/").split("/") if pointer != "/" else ():
            value = value[component]
        require(type(value) is dict and tuple(value) == keys, f"closed keys: {pointer}")
    require(document["schema_version"] == "AE-SQ5-program-authority-v1", "schema")
    require(document["program_id"] == "AE-SQ5", "program")
    require(document["candidate_id"] == "AE-SQ5-SLEC-5", "candidate")
    require(document["authority_status"] == "F0_INITIAL_AUTHORITY_CLOSED", "status")
    owner = document["owner_authorization"]
    require(owner["authorized"] is True, "owner")
    require(owner["additional_diagnostic_calls_authorized"] is False, "diagnostics")
    require(
        owner["authorized_phases"]
        == [
            "SQ5-F1A",
            "SQ5-F1B",
            "SQ5-F1G",
            "SQ5-F2A",
            "SQ5-F2B",
            "SQ5-F3",
            "SQ5-F4",
            "SQ5-F5",
            "SQ5-F6",
        ],
        "authorized phases",
    )
    require(owner["live_model_phases"] == ["SQ5-F4", "SQ5-F5"], "live phases")
    require(
        owner["corpus_authoring_authorized_only_after_exact_F1B_and_F1G_pass"] is True,
        "author gate",
    )
    require(
        owner["downstream_execution_authorized_by_this_artifact"] is False, "downstream"
    )
    for key in (
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
        == ("AE-SQ4", "terminal", "SQ4-AR"),
        "predecessor",
    )
    require(predecessor["terminal_edge"] == "SQ4-F2:NOT_PASS->SQ4-AR", "terminal edge")
    require(
        predecessor["failed_f2a"]
        == {
            "commit": F2A,
            "tree": "fd76825a250466fbfabff8b75d307cb8cb017814",
            "combined_corpus_sha256": "feaa03f2afd815bbc661d6c9de99c2cf53410f472206b2a2cd4b964f5bb1f122",
            "status": "NOT_PASS",
        },
        "F2A",
    )
    require(
        predecessor["later_stage_facts"]
        == {
            "f2b_created": False,
            "preflight_executed": False,
            "one_shot_state_claimed": False,
            "diagnostic_calls": 0,
            "canary_calls": 0,
            "batch_calls": 0,
            "AQ_result_created": False,
            "downstream_opened": False,
        },
        "later stages",
    )
    for key in (
        "predecessor_bytes_write_permitted",
        "predecessor_state_delete_or_migrate_permitted",
        "predecessor_split_author_or_f2a_reuse_permitted",
        "EXECPLAN_write_permitted",
    ):
        require(predecessor[key] is False, key)
    imported = document["imported_failure_contract"]
    require(imported["exception_class"] == "PreflightError", "failure class")
    require(
        imported["exception_message"]
        == "corpus split authority is not the frozen F1 candidate",
        "failure message",
    )
    require(
        imported["actual_split_candidate_identity"]["role"] == "F1B-freeze",
        "actual role",
    )
    require(
        imported["required_candidate_identity"]["role"] == "F1A-implementation",
        "required role",
    )
    for key in (
        "sq4_candidate_qualification_imported",
        "sq4_candidate_identity_or_bytes_continued",
        "sq4_task_case_split_corpus_label_schedule_or_result_material_imported",
        "sq4_standalone_validator_pass_has_qualification_effect",
        "behavioral_tuning_permitted",
        "evaluator_threshold_tuning_permitted",
        "result_informed_change_permitted",
    ):
        require(imported[key] is False, key)
    graph = document["phase_graph"]
    require(
        graph["ordered_phases"]
        == [
            "SQ5-F0",
            "SQ5-F1A",
            "SQ5-F1B",
            "SQ5-F1G",
            "SQ5-F2A",
            "SQ5-F2B",
            "SQ5-F3",
            "SQ5-F4",
            "SQ5-F5",
            "SQ5-F6",
            "SQ5-AS-HANDOFF",
            "SQ5-AR",
        ],
        "ordered phases",
    )
    require(
        graph["success_edges"]
        == [
            "SQ5-F0->SQ5-F1A",
            "SQ5-F1A:PASS->SQ5-F1B",
            "SQ5-F1B:PASS->SQ5-F1G",
            "SQ5-F1G:PASS->SQ5-F2A",
            "SQ5-F2A:PASS->SQ5-F2B",
            "SQ5-F2B:PASS->SQ5-F3",
            "SQ5-F3:PASS->SQ5-F4",
            "SQ5-F4:PASS->SQ5-F5",
            "SQ5-F5:COMPLETE_VALID->SQ5-F6",
            "SQ5-F6:PASS->SQ5-AS-HANDOFF",
        ],
        "success edges",
    )
    require(
        graph["terminal_edges"]
        == [
            "SQ5-F1A:NOT_PASS->SQ5-AR",
            "SQ5-F1B:NOT_PASS->SQ5-AR",
            "SQ5-F1G:NOT_PASS->SQ5-AR",
            "SQ5-F2A:NOT_PASS->SQ5-AR",
            "SQ5-F2B:NOT_PASS->SQ5-AR",
            "SQ5-F3:NOT_PASS->SQ5-AR",
            "SQ5-F4:NOT_PASS->SQ5-AR",
            "SQ5-F5:NOT_COMPLETE_VALID->SQ5-AR",
            "SQ5-F6:NOT_PASS->SQ5-AR",
        ],
        "terminal edges",
    )
    require(
        graph["success_edges"][2:6]
        == [
            "SQ5-F1B:PASS->SQ5-F1G",
            "SQ5-F1G:PASS->SQ5-F2A",
            "SQ5-F2A:PASS->SQ5-F2B",
            "SQ5-F2B:PASS->SQ5-F3",
        ],
        "F1G sequence",
    )
    require("SQ5-F1G:NOT_PASS->SQ5-AR" in graph["terminal_edges"], "F1G terminal")
    require(
        graph["retry_reopen_resume_repair_refreeze_or_H6_permitted"] is False,
        "no retry",
    )
    require(graph["later_phase_compensation_permitted"] is False, "graph compensation")
    require(
        graph["additional_active_phases_or_edges_permitted"] is False,
        "additional graph edges",
    )
    require(document["model_configuration"]["model_id"] == "gpt-5.5", "model")
    require(document["model_configuration"]["reasoning_effort"] == "medium", "effort")
    model = document["model_configuration"]
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
        "fallbacks",
    )
    budgets = document["call_budgets"]
    require(
        (
            budgets["diagnostic_calls"],
            budgets["canary_calls"],
            budgets["conditional_batch_calls"],
            budgets["qualification_hard_ceiling"],
            budgets["retry_calls_hard_ceiling"],
        )
        == (0, 4, 320, 324, 0),
        "budgets",
    )
    require(
        budgets["failed_malformed_rejected_empty_or_timed_out_attempts_count"] is True,
        "attempt count",
    )
    require(budgets["unused_calls_transfer_permitted"] is False, "budget transfer")
    require(budgets["top_up_replacement_or_replay_calls_permitted"] is False, "top up")
    require(
        budgets["downstream_call_budget_in_this_authority"] == 0, "downstream budget"
    )
    f1 = document["f1_contract"]
    require(
        f1["F1A_required_components"]
        == [
            "authority-embedded-exact-role-path-ledger",
            "new-SQ5-candidate-authority-and-exact-external-historical-inventory-binding",
            "provider-local-semantic-resolution-and-corpus-schemas",
            "condition-adapter-resolver-gates-metrics-evaluator-and-global-AND-scorer",
            "runner-durable-one-shot-index-and-target-frozen-candidate-checker",
            "expected-authority-helper-as-sole-construction-source",
            "author-template-builder-corpus-validator-and-receipt-schema",
            "aggregate-result-handoff-and-terminal-decision-schemas",
            "zero-corpus-real-byte-and-byte-non-alias-contract-tests",
        ],
        "F1A components",
    )
    require(
        f1["F1A_forbidden_artifacts"]
        == [
            "evals/ae-sq5/f1/repaired-freeze.json",
            "evals/ae-sq5/f1/author-template-gate.json",
            "evals/ae-sq5/f2/split-a.json",
            "evals/ae-sq5/f2/split-b.json",
            "evals/ae-sq5/f2/schedule.json",
            "evals/ae-sq5/f2/corpus-manifest.json",
            "evals/ae-sq5/f2/run-manifest.json",
            "evals/ae-sq5/f3/preflight.json",
            "evals/ae-sq5/f6/aggregate-result.json",
            "evals/ae-sq5/as/handoff.json",
            "evals/ae-sq5/ar/terminal-decision.json",
        ],
        "F1A forbidden paths",
    )
    require(f1["accepted_F1A_count"] == 1, "one F1A")
    require(f1["alternate_sibling_or_second_F1A_permitted"] is False, "one child")
    require(f1["same_program_repair_or_refreeze_permitted"] is False, "no refreeze")
    require(
        f1["sq4_candidate_freeze_or-byte-reuse-permitted"] is False, "fresh candidate"
    )
    require(
        f1["F1B_must_bind_F1A_implementation_commit_and_tree"] is True, "F1B binding"
    )
    require(
        f1["F1B_only_new_program_artifact"] == "evals/ae-sq5/f1/repaired-freeze.json",
        "F1B sole artifact",
    )
    require(f1["independent_strict_review_required"] is True, "F1 review")
    require(f1["post_F1B_semantic_change_permitted"] is False, "post F1B change")
    fresh = f1["fresh_candidate_closure"]
    baseline = fresh["sq4_baseline"]
    require(
        baseline
        == {
            "implementation_commit": "3762efae80ead1461d973b4737c5dcab6bae026a",
            "implementation_tree": "6a071b4ee33246cc2ef448cf4d574f51abc89348",
            "freeze_commit": BASE_COMMIT,
            "freeze_tree": "6a04e5aa846cbe196425c58671bf390c499b4d59",
            "freeze_path": "evals/ae-sq4/f1/repaired-freeze.json",
            "freeze_blob": "30dd13fc674fdb45e3934bb5429cf8d20a8d1d0c",
            "freeze_raw_sha256": "580b08484a5ae9f35a942d1063ba7ce82ca83521533b0f8e0e6f763187f83893",
            "active_role_count": 27,
        },
        "SQ4 byte baseline",
    )
    ledger = fresh["exact_role_path_ledger"]
    require(
        fresh["exact_active_role_count"] == len(EXPECTED_F1_LEDGER) == 31, "role count"
    )
    require(
        type(ledger) is list
        and all(
            type(row) is dict and tuple(row) == ("role", "sq5_path") for row in ledger
        )
        and [(row["role"], row["sq5_path"]) for row in ledger]
        == list(EXPECTED_F1_LEDGER),
        "exact F1 role/path ledger",
    )
    require(len({row["role"] for row in ledger}) == len(ledger), "role aliases")
    require(len({row["sq5_path"] for row in ledger}) == len(ledger), "path aliases")
    require(
        all(
            path.startswith("evals/ae-sq5/f1/")
            or (path.startswith("scripts/") and "ae_sq5" in path)
            or (path.startswith("tests/") and "ae_sq5" in path)
            for _role, path in EXPECTED_F1_LEDGER
        ),
        "SQ5 namespace",
    )
    for key, expected_value in (
        ("F0_to_F1A_changed_paths_must_equal_ledger_paths", True),
        ("role_alias_path_alias_omission_or_extra_permitted", False),
        ("sq5_path_may_equal_sq4_role_path", False),
        ("any_sq4_F1A_role_blob_or_raw_sha256_reuse_permitted", False),
        ("every_sq5_role_must_differ_from_every_sq4_role_by_blob_and_raw_sha256", True),
        ("all_role_tree_entries_must_be_100644_regular_blobs", True),
        ("stale_AE_SQ4_or_SLEC_4_identity_in_active_role_permitted", False),
        ("closed_provenance_SQ4_identity_exempted_from_owned_identity_check", True),
        ("immutable_predecessor_evidence_permitted_only_as_nonactive_provenance", True),
        ("predecessor_evidence_may_occupy_active_role", False),
    ):
        require(fresh[key] is expected_value, key)
    provenance = f1["external_provenance"]
    require(
        provenance["copied_into_SQ5_namespace_or_counted_as_active_F1A_role_permitted"]
        is False,
        "provenance copy",
    )
    require(
        provenance["task_case_label_split_schedule_or_result_material_permitted"]
        is False,
        "provenance material",
    )
    require(
        provenance["historical_digest_inventory"]
        == {
            "commit": "3762efae80ead1461d973b4737c5dcab6bae026a",
            "tree": "6a071b4ee33246cc2ef448cf4d574f51abc89348",
            "path": "evals/ae-sq4/f1/historical-task-digests.json",
            "blob": "6af74b660a9cf8fb04cde70abd527a88307f8cc3",
            "raw_sha256": "0e49a967d9a59021c0f1aa5fc8d80fd53fdf3ab1885925b0d86f1e8c4f9dc157",
            "content_kind": "digest-only-no-task-text",
        },
        "historical provenance",
    )
    gate = document["author_template_gate"]
    require((gate["attempts"], gate["model_calls"]) == (1, 0), "gate budget")
    require(gate["task_case_label_or_corpus_content_permitted"] is False, "zero corpus")
    require(gate["real_canonical_byte_round_trip_required"] is True, "real bytes")
    require(
        gate["same_frozen_runtime_validation_path_as_F2B_required"] is True,
        "runtime parity",
    )
    expected = gate["synthetic_authority_required_values"]
    require(
        expected["candidate_commit_role"] == "F1A-implementation-commit", "commit role"
    )
    require(expected["candidate_tree_role"] == "F1A-implementation-tree", "tree role")
    require(
        expected["f1_freeze_sha256_role"] == "separate-F1B-manifest-digest",
        "freeze role",
    )
    red = gate["red_fixture"]
    require(
        red["mutation"] == "replace-candidate-commit-and-tree-with-F1B-freeze-identity",
        "red",
    )
    require(red["required_result"] == "rejected", "red result")
    require(red["required_exception_class"] == "PreflightError", "red class")
    require(
        red["required_exception_message"] == imported["exception_message"],
        "red message",
    )
    require(gate["author_lane_open_before_pass_permitted"] is False, "author lane")
    require(
        gate["validated_taskless_author_template_required"] is True, "taskless template"
    )
    require(
        gate["dictionary_only_mock_only_or-source-only-proof_permitted"] is False,
        "mock-only proof",
    )
    receipt = gate["receipt_only_commit"]
    require(
        receipt
        == {
            "path": "evals/ae-sq5/f1/author-template-gate.json",
            "schema_path": "evals/ae-sq5/f1/author-template-gate-schema.json",
            "schema_frozen_in": "SQ5-F1A",
            "direct_parent": "SQ5-F1B",
            "only_new_program_artifact": "evals/ae-sq5/f1/author-template-gate.json",
            "exact_receipt_fields": [
                "schema_version",
                "program_id",
                "candidate_id",
                "attempt",
                "status",
                "model_calls",
                "f1a_implementation",
                "f1b_freeze",
                "builder",
                "validator",
                "template_sha256",
                "positive_round_trip",
                "red_fixture",
                "aggregate_sha256",
            ],
            "aggregate_sha256_derivation": "SHA256-canonical-receipt-with-aggregate_sha256-omitted",
        },
        "F1G receipt",
    )
    require(
        gate["receipt_required_bindings"]
        == [
            "SQ5-F1A-commit-tree-builder-and-validator-bytes",
            "SQ5-F1B-commit-tree-and-freeze-raw-SHA256",
            "exact-taskless-author-template-raw-SHA256",
            "positive-real-byte-round-trip-PASS",
            "F1B-as-candidate-red-fixture-exact-PreflightError",
            "attempt-one-and-model-calls-zero",
        ],
        "F1G receipt bindings",
    )
    require(
        gate["author_commits_must_be_direct_children_of_F1G"] is True, "author topology"
    )
    require(
        gate["F2A_ordered_parent_roles"] == ["SQ5-F1G", "author-A", "author-B"],
        "F2A topology",
    )
    require(
        gate["F2B_and_F3_must_bind_F1G_commit_tree_receipt_blob_and_raw_sha256"]
        is True,
        "F2B/F3 F1G binding",
    )
    require(gate["repair_or_second_gate_permitted"] is False, "second F1G")
    target = document["frozen_target_loading"]
    require(
        target["expected_authority_helper_role"]
        == "sole-source-for-author-template-and-corpus-authority-construction",
        "expected authority helper",
    )
    require(
        target["validate_corpora_expected_authority_argument_required"] is True,
        "validator expected authority",
    )
    require(
        target["validate_corpora_standalone_qualification_PASS_permitted"] is False,
        "standalone qualification",
    )
    require(target["production_loader_entrypoint"] == "_load_base_state", "loader")
    require(
        target["F1G_and_F2B_must_call_exact_production_loader"] is True,
        "production loader",
    )
    require(
        target["production_loader_environment"]
        == "ephemeral-private-Git-snapshot-of-exact-F1A-bytes",
        "loader environment",
    )
    require(
        target["partial-loader-mock-or-live-worktree-substitution-permitted"] is False,
        "loader substitution",
    )
    require(target["checker_source"] == "target-frozen-F1A-bytes", "checker source")
    require(target["ambient_root_checker_permitted"] is False, "ambient checker")
    require(target["ambient_root_authority_permitted"] is False, "ambient authority")
    require(
        target["ambient_and_target_byte_mismatch_route"] == "SQ5-AR",
        "ambient mismatch",
    )
    require(
        target["checker_or_authority_target_failure_route"] == "SQ5-AR",
        "target failure route",
    )
    corpus = document["corpus_contract"]
    require(corpus["phase"] == "SQ5-F2A", "F2A phase")
    require(
        corpus["authoring_gate"]
        == "exact-committed-SQ5-F1G-receipt-PASS-direct-child-of-SQ5-F1B",
        "corpus gate",
    )
    require(corpus["fresh_relative_to_all_predecessors"] is True, "fresh corpus")
    require(
        corpus[
            "sq4_split_author_commit_corpus_manifest_schedule_digest_or_f2a_reuse_permitted"
        ]
        is False,
        "SQ4 reuse",
    )
    for key in (
        "predecessor_candidate_or_corpus_continuation_permitted",
        "authors_may_access_each_other_split",
        "authors_may_access_predecessor_task_case_corpus_or_label_material",
        "authors_may_access_diagnostic_model_material_or_live_results",
        "result_informed_change_permitted",
        "retry_replay_duplicate_replacement_extra_or_top_up_permitted",
    ):
        require(corpus[key] is False, key)
    require(
        corpus["authors_receive_only_validated_taskless_SQ5_template"] is True,
        "taskless author template",
    )
    require(
        (
            corpus["independent_author_count"],
            corpus["cases_per_author"],
            corpus["total_unique_cases"],
        )
        == (2, 20, 40),
        "corpus size",
    )
    require(
        corpus["split_authority_must_bind_SQ5_F1A_implementation_identity"] is True,
        "split implementation",
    )
    require(
        corpus["split_authority_must_bind_SQ5_F1B_separately"] is True, "split freeze"
    )
    require(
        corpus["independent_nonauthor_validation_required"] is True,
        "nonauthor validation",
    )
    require(
        corpus["historical_exact_digest_no_replay_required"] is True,
        "historical nonreplay",
    )
    require(corpus["F2_JSON_git_object_mode"] == "100644-regular-blob", "F2 modes")
    require(
        corpus["strict_canonical_UTF8_JSON_required_for"]
        == [
            "evals/ae-sq5/f2/split-a.json",
            "evals/ae-sq5/f2/split-b.json",
            "evals/ae-sq5/f2/schedule.json",
            "evals/ae-sq5/f2/corpus-manifest.json",
            "evals/ae-sq5/f2/run-manifest.json",
        ],
        "canonical F2 JSON",
    )
    require(
        corpus[
            "duplicate_nonfinite_alternate_encoding_trailing_or_noncanonical_bytes_permitted"
        ]
        is False,
        "invalid F2 bytes",
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
    require(
        corpus["consumption_trigger"] == "first-SQ5-F5-heldout-backed-call", "consume"
    )
    require(corpus["post_consumption_status"] == "NO_REPLAY", "no replay status")
    f2a_contract = corpus["F2A_commit_contract"]
    require(f2a_contract["commit_kind"] == "fresh-corpus-merge", "F2A kind")
    require(
        f2a_contract["exact_ordered_parent_roles"]
        == ["SQ5-F1G", "author-A", "author-B"],
        "F2A parent roles",
    )
    require(
        (f2a_contract["author_A_direct_parent"], f2a_contract["author_B_direct_parent"])
        == ("SQ5-F1G", "SQ5-F1G"),
        "author parents",
    )
    require(
        f2a_contract["exact_artifact_paths_relative_to_F1G"]
        == [
            "evals/ae-sq5/f2/split-a.json",
            "evals/ae-sq5/f2/split-b.json",
            "evals/ae-sq5/f2/schedule.json",
            "evals/ae-sq5/f2/corpus-manifest.json",
        ],
        "F2A artifacts",
    )
    require(
        f2a_contract["omitted_extra_or_nonregular_artifact_permitted"] is False,
        "F2A closure",
    )
    require(
        f2a_contract[
            "PASS_requires_exact_topology_artifact_closure_and_content_validation"
        ]
        is True,
        "F2A PASS",
    )
    require(
        f2a_contract["retry_replacement_or_second_F2A_permitted"] is False,
        "F2A retry",
    )
    require(f2a_contract["not_pass_route"] == "SQ5-AR", "F2A route")
    f2b = document["f2b_run_manifest_contract"]
    require(
        (f2b["phase"], f2b["requires"], f2b["commit_kind"], f2b["direct_parent"])
        == (
            "SQ5-F2B",
            "SQ5-F2A:PASS",
            "manifest-only-direct-child",
            "exact-SQ5-F2A-commit",
        ),
        "F2B topology",
    )
    require(
        f2b["exact_delta_paths"] == ["evals/ae-sq5/f2/run-manifest.json"],
        "F2B delta",
    )
    require(
        f2b["artifact"]
        == {
            "path": "evals/ae-sq5/f2/run-manifest.json",
            "schema_path": "evals/ae-sq5/f1/run-manifest-schema.json",
            "schema_frozen_in": "SQ5-F1A",
            "git_object_mode": "100644-regular-blob",
            "encoding": "strict-UTF-8",
            "serialization": "canonical-finite-duplicate-key-free-JSON",
            "exact_top_level_keys_in_canonical_order": [
                "author_template_gate",
                "candidate_id",
                "corpus",
                "corpus_freeze",
                "execution",
                "f1_freeze",
                "implementation_freeze",
                "program_id",
                "run_id",
                "runtime",
                "schedule",
                "schema_version",
                "usage_authority",
                "validation_receipt",
            ],
        },
        "F2B artifact",
    )
    receipt_v = f2b["embedded_independent_validator_receipt"]
    require(
        receipt_v["location"] == "run-manifest.validation_receipt", "receipt location"
    )
    require(
        receipt_v["exact_keys_in_canonical_order"]
        == [
            "aggregate_sha256",
            "artifacts",
            "author_commits",
            "authorship_performed",
            "claim_ceiling",
            "errors",
            "f1a_implementation",
            "f1b_freeze",
            "f1g_gate",
            "f2a_corpus",
            "holds",
            "receipt_version",
            "status",
            "validator",
        ],
        "receipt keys",
    )
    require(
        receipt_v["required_bindings"]
        == [
            "SQ5-F1A-commit-tree-and-all-active-role-blobs-and-raw-SHA256",
            "SQ5-F1B-commit-tree-freeze-blob-and-raw-SHA256",
            "SQ5-F1G-commit-tree-receipt-blob-and-raw-SHA256",
            "SQ5-F2A-commit-tree-and-exact-ordered-parents",
            "author-A-and-author-B-commit-tree-split-path-blob-raw-SHA256-content-SHA256-and-distinct-author-id",
            "split-a-split-b-schedule-and-corpus-manifest-path-blob-raw-SHA256-and-semantic-or-content-SHA256",
            "validator-id-path-blob-and-raw-SHA256-from-exact-F1A",
            "forty-case-independent-validation-PASS-with-empty-errors-and-holds",
            "authorship-performed-false-and-aggregate-receipt-SHA256",
        ],
        "receipt bindings",
    )
    require(
        receipt_v["validator_identity_required"] == "independent-nonauthor-validator",
        "validator identity",
    )
    require(
        receipt_v["exact_nested_binding_keys"]
        == {
            "f1a_implementation": ["commit", "role_ledger_sha256", "tree"],
            "f1b_freeze": ["blob", "commit", "path", "raw_sha256", "tree"],
            "f1g_gate": ["blob", "commit", "path", "raw_sha256", "tree"],
            "f2a_corpus": ["commit", "ordered_parents", "tree"],
            "author_commit_row": [
                "author_id",
                "blob",
                "commit",
                "content_sha256",
                "path",
                "raw_sha256",
                "tree",
            ],
            "artifact_row": [
                "blob",
                "content_or_semantic_sha256",
                "path",
                "raw_sha256",
            ],
            "validator": [
                "blob",
                "commit",
                "path",
                "raw_sha256",
                "tree",
                "validator_id",
            ],
        },
        "receipt nested bindings",
    )
    require(receipt_v["status_required"] == "PASS", "receipt PASS")
    require(receipt_v["authorship_performed_required"] is False, "receipt authorship")
    require(receipt_v["errors_required"] == [], "receipt errors")
    require(receipt_v["holds_required"] == [], "receipt holds")
    require(
        receipt_v["standalone_validator_PASS_has_qualification_effect"] is False,
        "receipt claim ceiling",
    )
    require(
        f2b["separate_validation_receipt_artifact_permitted"] is False,
        "separate receipt",
    )
    require(
        f2b["F2B_PASS_requires_exact_parent_delta_bytes_schema_bindings_and_receipt"]
        is True,
        "F2B PASS",
    )
    require(f2b["only_F2B_PASS_opens_F3"] is True, "F2B opens F3")
    require(
        f2b["retry_replacement_or_second_F2B_permitted"] is False,
        "F2B retry",
    )
    require(f2b["not_pass_route"] == "SQ5-AR", "F2B route")
    state = document["durable_state_contract"]
    require(state["schema_version"] == "ae-sq5-one-shot-run-index-v1", "state schema")
    require(state["program_id"] == "AE-SQ5", "state program")
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
        "state binding keys",
    )
    require(state["preflight_or_dry_run_claim_permitted"] is False, "preflight claim")
    preflight = document["zero_model_preflight"]
    require((preflight["attempts"], preflight["model_calls"]) == (1, 0), "preflight")
    require(preflight["requires"] == "SQ5-F2B:PASS", "preflight prerequisite")
    require(
        "real-byte-F1A-candidate-vs-F1B-freeze-authority-contract"
        in preflight["required_checks"],
        "preflight authority",
    )
    require(preflight["pass_required_for_canary"] is True, "preflight pass")
    require(
        preflight["repair_or_second_preflight_permitted"] is False,
        "second preflight",
    )
    canary = document["qualification_execution"]["canary"]
    require(canary["requires"] == "SQ5-F3:PASS", "canary prerequisite")
    require(canary["calls"] == 4, "canary")
    require(canary["corpus_content_permitted"] is False, "canary corpus")
    require(canary["calls_per_isolated_child_context"] == 1, "canary context")
    require(
        canary["all_four_valid_completed_capsules_required"] is True, "canary capsules"
    )
    require(
        canary["retry_top_up_replacement_second_canary_or_byte_change_permitted"]
        is False,
        "canary retry",
    )
    require(canary["not_pass_route"] == "SQ5-AR", "canary route")
    batch = document["qualification_execution"]["batch"]
    require(batch["requires"] == "SQ5-F4:PASS", "batch prerequisite")
    require(batch["conditional"] is True, "conditional batch")
    require(
        batch["hard_call_ceiling"] == 320,
        "batch",
    )
    require(
        (batch["total_presentations"], batch["calls_per_presentation"]) == (80, 4),
        "batch shape",
    )
    require(batch["first_call_consumes_both_splits"] is True, "consumption")
    require(batch["failed_or_malformed_attempts_count"] is True, "batch count")
    require(
        batch["retry_replay_duplicate_replacement_extra_or_top_up_permitted"] is False,
        "batch retry",
    )
    require(batch["complete_valid_route"] == "SQ5-F6", "batch success")
    require(batch["incomplete_failed_or_invalid_route"] == "SQ5-AR", "batch failure")
    global_and = document["global_and"]
    require(global_and["operator"] == "logical-AND", "AND")
    require(
        global_and["scope"]
        == "all-required-run-integrity-capsule-evaluator-gate-metric-condition-and-presentation-values",
        "AND scope",
    )
    require(global_and["phase"] == "SQ5-F6" and global_and["model_calls"] == 0, "F6")
    require(global_and["required_conditions"] == ["current", "reduced"], "conditions")
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
        "false values",
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
        )
        == ("PASS", "FAIL", 1),
        "F6 result",
    )
    require(
        global_and["result_projection"]
        == "candidate-bound-aggregate-status-and-digest-only",
        "projection",
    )
    require(
        global_and["subaggregate_or_raw_result_disclosure_permitted"] is False,
        "F6 disclosure",
    )
    require(
        global_and["durable_result_path"] == "evals/ae-sq5/f6/aggregate-result.json",
        "F6 path",
    )
    require(
        global_and["durable_result_format"]
        == "strict-canonical-UTF8-aggregate-only-JSON",
        "F6 format",
    )
    require(
        global_and["durable_result_raw_sha256_must_equal_run_index_record_sha256"]
        is True,
        "F6 run-index binding",
    )
    outcome = document["outcome_artifact_contract"]
    require(outcome["schemas_frozen_in"] == "SQ5-F1A", "outcome schemas")
    aggregate = outcome["aggregate_result"]
    require(
        aggregate["path"] == global_and["durable_result_path"]
        and aggregate["schema_path"] == "evals/ae-sq5/f1/result-schema.json",
        "aggregate paths",
    )
    require(
        aggregate["created_only_in"] == "SQ5-F6-after-SQ5-F5-COMPLETE_VALID",
        "aggregate topology",
    )
    require(
        aggregate["exact_keys_in_canonical_order"]
        == [
            "aggregate_digest",
            "candidate_id",
            "program_id",
            "schema_version",
            "status",
        ],
        "aggregate keys",
    )
    require(
        aggregate["exact_constants"]
        == {
            "schema_version": "ae-sq5-aggregate-result-v1",
            "program_id": "AE-SQ5",
            "candidate_id": "AE-SQ5-SLEC-5",
            "status_values": ["PASS", "FAIL"],
        },
        "aggregate constants",
    )
    require(aggregate["aggregate_digest_is_exact_global_AND_digest"] is True, "digest")
    require(
        aggregate["raw_sha256_must_equal_run_index_record_sha256"] is True,
        "aggregate record",
    )
    require(
        aggregate["strict_canonical_UTF8_JSON_and_100644_regular_blob_required"]
        is True,
        "aggregate bytes",
    )
    handoff = outcome["handoff"]
    require(
        handoff["path"] == "evals/ae-sq5/as/handoff.json"
        and handoff["schema_path"] == "evals/ae-sq5/f1/handoff-schema.json"
        and handoff["created_only_on"] == "SQ5-F6:PASS->SQ5-AS-HANDOFF",
        "handoff topology",
    )
    require(
        handoff["exact_keys_in_canonical_order"]
        == [
            "aggregate_result",
            "authority_effect",
            "candidate_id",
            "program_id",
            "schema_version",
            "source_phase",
            "source_status",
        ],
        "handoff keys",
    )
    require(
        handoff["must_bind_aggregate_result_path_and_raw_sha256"] is True,
        "handoff binding",
    )
    require(
        (handoff["source_phase"], handoff["source_status"], handoff["authority_effect"])
        == ("SQ5-F6", "PASS", "none"),
        "handoff content",
    )
    require(handoff["terminal_decision_may_coexist"] is False, "handoff exclusivity")
    terminal = outcome["terminal_decision"]
    require(
        terminal["path"] == "evals/ae-sq5/ar/terminal-decision.json"
        and terminal["schema_path"] == "evals/ae-sq5/f1/terminal-decision-schema.json"
        and terminal["created_only_on"] == "one-exact-terminal-edge-into-SQ5-AR",
        "terminal topology",
    )
    require(
        terminal["exact_keys_in_canonical_order"]
        == [
            "aggregate_result",
            "candidate_id",
            "last_completed_phase",
            "program_id",
            "schema_version",
            "status",
            "terminal_edge",
        ],
        "terminal keys",
    )
    require(
        terminal["must_bind_exact_terminal_edge_and_last_completed_phase"] is True,
        "terminal binding",
    )
    require(
        terminal["aggregate_result_binding_required_only_if_F6_was_entered"] is True,
        "terminal aggregate",
    )
    require(terminal["status"] == "terminal", "terminal status")
    require(terminal["handoff_may_coexist"] is False, "terminal exclusivity")
    require(
        outcome["aggregate_handoff_and_terminal_paths_pairwise_distinct"] is True,
        "outcome paths",
    )
    require(
        outcome["schema_or_topology_fallback_permitted"] is False, "outcome fallback"
    )
    require(
        document["routing_and_claims"]["pass_edge"] == "SQ5-F6:PASS->SQ5-AS-HANDOFF",
        "pass route",
    )
    require(
        document["routing_and_claims"]["nonpass_edge"] == "SQ5-F6:NOT_PASS->SQ5-AR",
        "fail route",
    )
    routing = document["routing_and_claims"]
    for key in (
        "diagnosis_can_qualify_AQ",
        "author_template_gate_can_qualify_AQ",
        "canary_alone_can_qualify_AQ",
        "incomplete_or_invalid_batch_can_reach_F6",
        "SQ5_AS_HANDOFF_is_execution_authority",
        "release_publish_or_promotion_claim",
    ):
        require(routing[key] is False, key)
    require(routing["SQ5_AR_is_terminal"] is True, "AR terminal")
    require(
        {
            global_and["durable_result_path"],
            routing["handoff_artifact_path"],
            routing["terminal_artifact_path"],
        }
        == {
            "evals/ae-sq5/f6/aggregate-result.json",
            "evals/ae-sq5/as/handoff.json",
            "evals/ae-sq5/ar/terminal-decision.json",
        },
        "routing paths",
    )
    require(
        routing["result_handoff_and_terminal_paths_must_be_pairwise_distinct"] is True,
        "distinct routes",
    )
    privacy = document["privacy"]
    require(
        privacy["forbidden_durable_material"]
        == [
            "raw-prompt",
            "task-text",
            "raw-output",
            "event-payload",
            "transcript",
            "message",
            "case-level-result",
            "split-level-result",
            "condition-level-result",
            "presentation-level-result",
            "assessor-level-result",
            "gate-level-result",
            "score-level-result",
        ],
        "privacy",
    )
    require(
        privacy["permitted_external_projection"]
        == "final-aggregate-status-and-digest-only",
        "privacy projection",
    )
    namespace = document["namespace"]
    require(namespace["program_base_commit"] == BASE_COMMIT, "base")
    require(
        namespace["program_base_tree"] == "6a04e5aa846cbe196425c58671bf390c499b4d59",
        "base tree",
    )
    require(namespace["F0_commit"] == "ABSENT_NOT_SELF_BOUND", "self bind")
    require(
        namespace["F1A_must_be_direct_child_of_committed_F0"] is True,
        "F1A parent",
    )
    require(
        namespace["predecessor_root_write_permitted"] is False,
        "predecessor write",
    )
    require(
        namespace["predecessor_durable_state_write_delete_or_migrate_permitted"]
        is False,
        "predecessor state",
    )
    require(
        namespace["reserved_future_artifacts_confer_state"] is False,
        "future state",
    )
    require(
        document["forbidden_actions"]
        == [
            "retry-reopen-resume-repair-refreeze-continue-cure-or-reinterpret-AE-SQ4",
            "H6",
            "write-delete-or-migrate-AE-SQ4-bytes-or-state",
            "reuse-AE-SQ4-split-author-object-corpus-manifest-schedule-digest-or-F2A",
            "continue-or-refreeze-AE-SQ4-candidate-bytes",
            "copy-or-alias-any-SQ4-F1A-role-blob-or-raw-bytes-into-an-active-SQ5-F1A-role",
            "omit-add-reorder-or-alias-an-SQ5-F1A-role-or-path",
            "treat-imported-predecessor-provenance-as-an-active-SQ5-candidate-role",
            "make-a-diagnostic-call",
            "author-corpus-before-exact-F1B-and-F1G-pass",
            "bind-authored-split-candidate-identity-to-F1B",
            "use-dictionary-only-mock-only-or-source-only-authority-proof",
            "bypass-F2A-or-F2B-or-open-F3-without-exact-F2B-PASS",
            "model-call-during-F1-F2A-F2B-F3-or-F6",
            "canary-before-F3-pass",
            "batch-before-F4-pass",
            "retry-replay-replace-duplicate-extra-or-top-up-call-or-presentation",
            "model-provider-reasoning-or-mode-fallback",
            "persist-forbidden-raw-or-subaggregate-material",
            "later-stage-compensation",
            "route-nonpass-downstream",
            "release-publish-promote-delete-or-migrate",
        ],
        "forbidden actions",
    )


class AeSq5ProgramAuthorityTests(unittest.TestCase):
    def test_strict_recursive_contract_and_exact_custody(self) -> None:
        document = strict(AUTHORITY_PATH.read_bytes())
        validate(document)
        self.assertEqual(
            document["namespace"]["active_plan"]["raw_sha256"],
            hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest(),
        )
        predecessor = document["predecessor_terminal_history"]
        self.assertEqual(
            predecessor["terminal_decision"]["raw_sha256"],
            hashlib.sha256(TERMINAL_PATH.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            predecessor["terminal_plan"]["raw_sha256"],
            hashlib.sha256(TERMINAL_PLAN_PATH.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            document["namespace"]["program_base_tree"],
            subprocess.run(
                ["git", "rev-parse", f"{BASE_COMMIT}^{{tree}}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
        )
        fresh = document["f1_contract"]["fresh_candidate_closure"]
        baseline = fresh["sq4_baseline"]
        freeze_raw = subprocess.run(
            ["git", "show", f"{baseline['freeze_commit']}:{baseline['freeze_path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(
            baseline["freeze_raw_sha256"], hashlib.sha256(freeze_raw).hexdigest()
        )
        self.assertEqual(
            baseline["freeze_blob"],
            subprocess.run(
                [
                    "git",
                    "rev-parse",
                    f"{baseline['freeze_commit']}:{baseline['freeze_path']}",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
        )
        sq4_freeze = strict(freeze_raw)
        self.assertEqual(baseline["active_role_count"], len(sq4_freeze["files"]))
        self.assertTrue(
            {row["sq5_path"] for row in fresh["exact_role_path_ledger"]}.isdisjoint(
                {row["path"] for row in sq4_freeze["files"]}
            )
        )
        inventory = document["f1_contract"]["external_provenance"][
            "historical_digest_inventory"
        ]
        inventory_raw = subprocess.run(
            ["git", "show", f"{inventory['commit']}:{inventory['path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(
            inventory["raw_sha256"], hashlib.sha256(inventory_raw).hexdigest()
        )
        self.assertEqual(
            inventory["blob"],
            subprocess.run(
                ["git", "rev-parse", f"{inventory['commit']}:{inventory['path']}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
        )

    def test_foundation_pointer_and_decision_rows(self) -> None:
        pointer = "**Active successor plan:** `docs/exec-plans/active/ae-sq5.md` for AE-SQ5 only; AE-SQ4, AE-SQ3, AE-SQ2, AE-SQ1, and `EXECPLAN.md` remain immutable terminal history"
        self.assertEqual(
            FOUNDATION_PATH.read_text(encoding="utf-8").splitlines()[6], pointer
        )
        rows = list(csv.DictReader(io.StringIO(LOG_PATH.read_text(encoding="utf-8"))))
        ids = [row["decision_id"] for row in rows]
        self.assertEqual(ids.count("AE-SQ4-AR-2026-08-13"), 1)
        self.assertEqual(ids.count("AE-SQ5-F0-2026-08-13"), 1)
        self.assertEqual(
            [row["decision_id"] for row in rows[-2:]],
            ["AE-SQ4-AR-2026-08-13", "AE-SQ5-F0-2026-08-13"],
        )

    def test_f0_has_no_premature_sq5_surfaces(self) -> None:
        for phase in ("f1", "f2", "f3", "f4", "f5", "f6", "ar"):
            self.assertFalse((ROOT / f"evals/ae-sq5/{phase}").exists(), phase)
        self.assertFalse((ROOT / "scripts/run_ae_sq5_aq.py").exists())

    def test_plan_exposes_real_byte_gate_and_freshness(self) -> None:
        plan = PLAN_PATH.read_text(encoding="utf-8")
        for text in (
            "zero-corpus real-byte author-template gate",
            "candidate_commit` and `candidate_tree` equal the F1A implementation identity",
            "red fixture that substitutes the F1B commit/tree as candidate identity",
            "F1G is a receipt-only commit directly after F1B",
            "Both author commits must be\ndirect children of exact F1G",
            "One frozen `expected_authority` helper is the sole source",
            "reject an ambient `--root` checker",
            "Neither\nSQ4 split, author commit, corpus manifest, schedule, combined corpus digest, nor\nF2A object may be copied",
            "exact Git `100644` regular blob",
            "strict canonical UTF-8 JSON",
            "evals/ae-sq5/f6/aggregate-result.json",
            "exactly `gpt-5.5` with reasoning effort `medium`",
            "total qualification\nceiling is 324; retry ceiling is zero",
        ):
            self.assertIn(text, plan)

    def test_mutations_fail_closed(self) -> None:
        document = strict(AUTHORITY_PATH.read_bytes())
        changes: list[tuple[tuple[str, ...], object]] = [
            (("candidate_id",), "AE-SQ4-SLEC-4"),
            (("owner_authorization", "additional_diagnostic_calls_authorized"), True),
            (
                ("phase_graph", "retry_reopen_resume_repair_refreeze_or_H6_permitted"),
                True,
            ),
            (("phase_graph", "later_phase_compensation_permitted"), True),
            (("phase_graph", "additional_active_phases_or_edges_permitted"), True),
            (("phase_graph", "success_edges"), []),
            (("phase_graph", "terminal_edges"), []),
            (("call_budgets", "retry_calls_hard_ceiling"), 1),
            (("f1_contract", "F1A_required_components"), []),
            (("f1_contract", "F1A_forbidden_artifacts"), []),
            (("f1_contract", "alternate_sibling_or_second_F1A_permitted"), True),
            (("f1_contract", "same_program_repair_or_refreeze_permitted"), True),
            (("f1_contract", "independent_strict_review_required"), False),
            (("f1_contract", "post_F1B_semantic_change_permitted"), True),
            (("f1_contract", "sq4_candidate_freeze_or-byte-reuse-permitted"), True),
            (("f1_contract", "F1B_only_new_program_artifact"), "other.json"),
            (("f1_contract", "fresh_candidate_closure", "exact_active_role_count"), 30),
            (("f1_contract", "fresh_candidate_closure", "exact_role_path_ledger"), []),
            (
                (
                    "f1_contract",
                    "fresh_candidate_closure",
                    "F0_to_F1A_changed_paths_must_equal_ledger_paths",
                ),
                False,
            ),
            (
                (
                    "f1_contract",
                    "fresh_candidate_closure",
                    "role_alias_path_alias_omission_or_extra_permitted",
                ),
                True,
            ),
            (
                (
                    "f1_contract",
                    "fresh_candidate_closure",
                    "any_sq4_F1A_role_blob_or_raw_sha256_reuse_permitted",
                ),
                True,
            ),
            (
                (
                    "f1_contract",
                    "fresh_candidate_closure",
                    "every_sq5_role_must_differ_from_every_sq4_role_by_blob_and_raw_sha256",
                ),
                False,
            ),
            (
                (
                    "f1_contract",
                    "fresh_candidate_closure",
                    "predecessor_evidence_may_occupy_active_role",
                ),
                True,
            ),
            (
                ("author_template_gate", "task_case_label_or_corpus_content_permitted"),
                True,
            ),
            (
                ("author_template_gate", "real_canonical_byte_round_trip_required"),
                False,
            ),
            (("author_template_gate", "red_fixture", "required_result"), "accepted"),
            (("author_template_gate", "author_lane_open_before_pass_permitted"), True),
            (
                ("author_template_gate", "validated_taskless_author_template_required"),
                False,
            ),
            (
                (
                    "author_template_gate",
                    "dictionary_only_mock_only_or-source-only-proof_permitted",
                ),
                True,
            ),
            (("author_template_gate", "receipt_required_bindings"), []),
            (
                ("author_template_gate", "receipt_only_commit", "direct_parent"),
                "SQ5-F1A",
            ),
            (
                (
                    "author_template_gate",
                    "author_commits_must_be_direct_children_of_F1G",
                ),
                False,
            ),
            (
                (
                    "frozen_target_loading",
                    "validate_corpora_expected_authority_argument_required",
                ),
                False,
            ),
            (
                (
                    "frozen_target_loading",
                    "validate_corpora_standalone_qualification_PASS_permitted",
                ),
                True,
            ),
            (("frozen_target_loading", "ambient_root_checker_permitted"), True),
            (
                (
                    "frozen_target_loading",
                    "F1G_and_F2B_must_call_exact_production_loader",
                ),
                False,
            ),
            (
                ("frozen_target_loading", "checker_or_authority_target_failure_route"),
                "SQ5-F3",
            ),
            (
                (
                    "corpus_contract",
                    "sq4_split_author_commit_corpus_manifest_schedule_digest_or_f2a_reuse_permitted",
                ),
                True,
            ),
            (
                (
                    "corpus_contract",
                    "split_authority_must_bind_SQ5_F1A_implementation_identity",
                ),
                False,
            ),
            (
                (
                    "corpus_contract",
                    "authors_may_access_predecessor_task_case_corpus_or_label_material",
                ),
                True,
            ),
            (("corpus_contract", "F2_JSON_git_object_mode"), "any"),
            (("corpus_contract", "independent_nonauthor_validation_required"), False),
            (("corpus_contract", "historical_exact_digest_no_replay_required"), False),
            (
                (
                    "corpus_contract",
                    "authors_receive_only_validated_taskless_SQ5_template",
                ),
                False,
            ),
            (("corpus_contract", "consumption_trigger"), "never"),
            (("corpus_contract", "post_consumption_status"), "REPLAY"),
            (
                (
                    "corpus_contract",
                    "F2A_commit_contract",
                    "exact_ordered_parent_roles",
                ),
                [],
            ),
            (
                (
                    "corpus_contract",
                    "F2A_commit_contract",
                    "exact_artifact_paths_relative_to_F1G",
                ),
                [],
            ),
            (("f2b_run_manifest_contract", "direct_parent"), "SQ5-F1G"),
            (("f2b_run_manifest_contract", "exact_delta_paths"), []),
            (
                (
                    "f2b_run_manifest_contract",
                    "embedded_independent_validator_receipt",
                    "required_bindings",
                ),
                ["wrong"] * 9,
            ),
            (
                (
                    "f2b_run_manifest_contract",
                    "embedded_independent_validator_receipt",
                    "validator_identity_required",
                ),
                "author-A",
            ),
            (
                (
                    "f2b_run_manifest_contract",
                    "embedded_independent_validator_receipt",
                    "status_required",
                ),
                "NOT_PASS",
            ),
            (
                (
                    "f2b_run_manifest_contract",
                    "embedded_independent_validator_receipt",
                    "authorship_performed_required",
                ),
                True,
            ),
            (("f2b_run_manifest_contract", "only_F2B_PASS_opens_F3"), False),
            (
                ("durable_state_contract", "preflight_or_dry_run_claim_permitted"),
                True,
            ),
            (("zero_model_preflight", "attempts"), 2),
            (("zero_model_preflight", "pass_required_for_canary"), False),
            (("zero_model_preflight", "repair_or_second_preflight_permitted"), True),
            (("zero_model_preflight", "requires"), "SQ5-F2A:PASS"),
            (("qualification_execution", "canary", "calls"), 5),
            (("qualification_execution", "canary", "requires"), "SQ5-F0"),
            (
                (
                    "qualification_execution",
                    "canary",
                    "retry_top_up_replacement_second_canary_or_byte_change_permitted",
                ),
                True,
            ),
            (
                (
                    "qualification_execution",
                    "batch",
                    "incomplete_failed_or_invalid_route",
                ),
                "SQ5-F6",
            ),
            (("qualification_execution", "batch", "requires"), "SQ5-F0"),
            (("qualification_execution", "batch", "conditional"), False),
            (("global_and", "operator"), "average"),
            (("global_and", "scope"), "one-value"),
            (("global_and", "durable_result_format"), "anything"),
            (
                (
                    "global_and",
                    "compensation_threshold_repair_override_or_later_cure_permitted",
                ),
                True,
            ),
            (
                (
                    "global_and",
                    "durable_result_raw_sha256_must_equal_run_index_record_sha256",
                ),
                False,
            ),
            (
                ("routing_and_claims", "incomplete_or_invalid_batch_can_reach_F6"),
                True,
            ),
            (("routing_and_claims", "release_publish_or_promotion_claim"), True),
            (("routing_and_claims", "nonpass_edge"), "SQ5-F6:NOT_PASS->SQ5-AS-HANDOFF"),
            (
                ("outcome_artifact_contract", "schema_or_topology_fallback_permitted"),
                True,
            ),
            (("outcome_artifact_contract", "aggregate_result", "schema_path"), "none"),
            (
                ("outcome_artifact_contract", "aggregate_result", "created_only_in"),
                "SQ5-F0",
            ),
            (("outcome_artifact_contract", "handoff", "created_only_on"), "SQ5-F0"),
            (
                (
                    "outcome_artifact_contract",
                    "handoff",
                    "exact_keys_in_canonical_order",
                ),
                ["program_id"],
            ),
            (
                (
                    "outcome_artifact_contract",
                    "terminal_decision",
                    "exact_keys_in_canonical_order",
                ),
                ["program_id"],
            ),
            (
                (
                    "outcome_artifact_contract",
                    "terminal_decision",
                    "handoff_may_coexist",
                ),
                True,
            ),
            (("namespace", "F1A_must_be_direct_child_of_committed_F0"), False),
            (("namespace", "predecessor_root_write_permitted"), True),
            (("forbidden_actions",), []),
        ]
        for path, replacement in changes:
            mutation = copy.deepcopy(document)
            target: Any = mutation
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = replacement
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate(mutation)
        extension = copy.deepcopy(document)
        extension["author_template_gate"]["extra"] = True
        with self.assertRaises(ValueError):
            validate(extension)
        extension = copy.deepcopy(document)
        extension["qualification_execution"]["canary"]["extra"] = True
        with self.assertRaises(ValueError):
            validate(extension)
        with self.assertRaises(ValueError):
            strict(b'{"program_id":"AE-SQ5","program_id":"AE-SQ4"}')
        with self.assertRaises(ValueError):
            strict(b'{"value":Infinity}')

    def test_every_semantic_leaf_mutation_fails_closed(self) -> None:
        document = strict(AUTHORITY_PATH.read_bytes())

        def leaves(value: Any, path: tuple[str | int, ...] = ()) -> Any:
            if isinstance(value, dict):
                if not value:
                    yield path, {"mutated": True}
                for key, child in value.items():
                    yield from leaves(child, (*path, key))
            elif isinstance(value, list):
                if not value:
                    yield path, ["mutated"]
                for index, child in enumerate(value):
                    yield from leaves(child, (*path, index))
            elif isinstance(value, bool):
                yield path, not value
            elif isinstance(value, str):
                yield path, f"{value}-MUTATED"
            elif isinstance(value, int):
                yield path, value + 1
            elif isinstance(value, float):
                yield path, value + 0.125
            elif value is None:
                yield path, "MUTATED"
            else:
                raise TypeError(f"unsupported leaf: {type(value).__name__}")

        for path, replacement in leaves(document):
            mutation = copy.deepcopy(document)
            target: Any = mutation
            for component in path[:-1]:
                target = target[component]
            target[path[-1]] = replacement
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate(mutation)


if __name__ == "__main__":
    unittest.main()
