"""Strict F0 authority checks for the distinct AE-SQ3 successor."""

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
AUTHORITY_PATH = ROOT / "evals/ae-sq3/program-authority.json"
PLAN_PATH = ROOT / "docs/exec-plans/active/ae-sq3.md"
TERMINAL_PATH = ROOT / "evals/ae-sq2/ar/terminal-decision.json"
FOUNDATION_PATH = ROOT / "docs/foundations/current-2026-08-08.md"
LOG_PATH = ROOT / "docs/foundations/decision-log.csv"
RECORD_COMMIT = "e2562ca4da5f3dc14fb07c1522f911e2dfe4334d"
SQ3_F0_COMMIT = "230354f09045c0f20b03c5080a6d70fcee38acbb"
RECORD_RAW_SHA = "1e2352fe42453b03cafac06e9c2e98638af17ad6a3e5dfaf389baf9da39d6502"
HEX64 = set("0123456789abcdef")


CLOSED_KEYS = {
    "/": (
        "schema_version",
        "program_id",
        "authority_status",
        "claim_ceiling",
        "owner_authorization",
        "predecessor_terminal_history",
        "imported_diagnosis",
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
        "terminal_decision",
        "terminal_plan",
        "frozen_program_authority",
        "diagnostic_record",
        "persistence_violation",
        "predecessor_bytes_write_permitted",
        "predecessor_state_delete_or_migrate_permitted",
        "EXECPLAN_write_permitted",
    ),
    "/predecessor_terminal_history/terminal_decision": ("path", "raw_sha256"),
    "/predecessor_terminal_history/terminal_plan": ("path", "raw_sha256"),
    "/predecessor_terminal_history/frozen_program_authority": ("path", "raw_sha256"),
    "/predecessor_terminal_history/diagnostic_record": (
        "path",
        "commit",
        "blob",
        "raw_sha256",
        "record_sha256",
        "aggregate_sha256",
    ),
    "/predecessor_terminal_history/persistence_violation": (
        "kind",
        "state_raw_sha256",
        "state_sha256",
        "custody_key",
        "route",
        "AE_SQ2_repair_permitted",
    ),
    "/imported_diagnosis": (
        "kind",
        "calls_started",
        "calls_completed",
        "classification_counts",
        "usage",
        "permitted_use",
        "qualification_effect",
        "behavioral_tuning_permitted",
        "evaluator_tuning_permitted",
        "corpus_or_label_use_permitted",
        "raw_or_event_material_imported",
    ),
    "/imported_diagnosis/classification_counts": (
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
    "/imported_diagnosis/usage": (
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "total_tokens",
    ),
    "/phase_graph": (
        "ordered_phases",
        "success_edges",
        "terminal_edges",
        "later_phase_compensation_permitted",
        "additional_active_phases_permitted",
        "additional_active_edges_permitted",
        "reopen_or_resume_permitted",
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
        "commit_sequence",
        "candidate_id",
        "F1A_forbidden_artifacts",
        "F1B_only_new_program_artifact",
        "required_exact_bindings",
        "independent_strict_review_required",
        "corpus_authoring_before_F1B_pass_permitted",
        "post_F1B_semantic_change_permitted",
        "same_program_refreeze_permitted",
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
        "SQ3_AS_HANDOFF_is_execution_authority",
        "SQ3_AR_is_terminal",
        "maximum_AQ_claim",
        "isolated_advice_composition_host_field_or_production_claim",
        "release_publish_or_promotion_claim",
    ),
    "/namespace": (
        "artifact_root",
        "active_plan",
        "program_base_commit",
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
        raw.decode(),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )
    if not isinstance(value, dict):
        raise ValueError("root must be object")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_exact(actual: object, expected: object, message: str) -> None:
    require(type(actual) is type(expected), f"{message} type")
    require(actual == expected, message)


def assert_closed(value: object, path: str = "/") -> None:
    if isinstance(value, dict):
        require(path in CLOSED_KEYS, f"unowned object path {path}")
        require(tuple(value) == CLOSED_KEYS[path], f"key/order drift at {path}")
        for key, child in value.items():
            child_path = f"/{key}" if path == "/" else f"{path}/{key}"
            assert_closed(child, child_path)
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                assert_closed(child, f"{path}/*")


def validate(document: dict[str, Any]) -> None:
    assert_closed(document)
    require_exact(document["schema_version"], "AE-SQ3-program-authority-v1", "schema")
    require_exact(document["program_id"], "AE-SQ3", "program")
    owner = document["owner_authorization"]
    require(owner["authorized"] is True, "authorization")
    require_exact(owner["candidate_id"], "AE-SQ3-SLEC-3", "candidate")
    require(owner["additional_diagnostic_calls_authorized"] is False, "diagnostic")
    require(
        all(
            owner[key] is False
            for key in (
                "downstream_execution_authorized_by_this_artifact",
                "release_publish_promotion_authorized",
                "deletion_or_migration_authorized",
            )
        ),
        "consequential authority",
    )
    predecessor = document["predecessor_terminal_history"]
    require_exact(predecessor["program_id"], "AE-SQ2", "predecessor program")
    require_exact(predecessor["status"], "terminal", "predecessor status")
    require_exact(predecessor["terminal_stage"], "SQ2-AR", "predecessor stage")
    require(
        predecessor["predecessor_bytes_write_permitted"] is False,
        "predecessor bytes immutable",
    )
    require(
        predecessor["predecessor_state_delete_or_migrate_permitted"] is False,
        "predecessor state retained",
    )
    require(predecessor["EXECPLAN_write_permitted"] is False, "EXECPLAN immutable")
    imported = document["imported_diagnosis"]
    require_exact(imported["calls_started"], 4, "D0 calls started")
    require_exact(imported["calls_completed"], 4, "D0 calls completed")
    require(
        type(imported["classification_counts"]["schema_unsupported"]) is int
        and imported["classification_counts"]["schema_unsupported"] == 4,
        "classification",
    )
    require(
        all(type(value) is int for value in imported["classification_counts"].values())
        and sum(imported["classification_counts"].values()) == 4,
        "classification sum",
    )
    require(
        all(type(value) is int and value == 0 for value in imported["usage"].values()),
        "usage",
    )
    require_exact(imported["qualification_effect"], "none", "diagnosis qualification")
    graph = document["phase_graph"]
    require(
        graph["ordered_phases"]
        == [
            "SQ3-F0",
            "SQ3-F1A",
            "SQ3-F1B",
            "SQ3-F2",
            "SQ3-F3",
            "SQ3-F4",
            "SQ3-F5",
            "SQ3-F6",
            "SQ3-AS-HANDOFF",
            "SQ3-AR",
        ],
        "phase order",
    )
    require(graph["success_edges"][-1] == "SQ3-F6:PASS->SQ3-AS-HANDOFF", "pass edge")
    require(
        "SQ3-F5:NOT_COMPLETE_VALID->SQ3-AR" in graph["terminal_edges"], "batch stop"
    )
    require(graph["later_phase_compensation_permitted"] is False, "compensation")
    require(graph["additional_active_phases_permitted"] is False, "extra phases")
    require(graph["additional_active_edges_permitted"] is False, "extra edges")
    require(graph["reopen_or_resume_permitted"] is False, "reopen or resume")
    repair = document["diagnosed_repair"]
    require_exact(repair["additional_diagnostic_calls"], 0, "diagnostic budget")
    require(
        "allOf" not in repair["provider_schema_permitted_keywords"], "provider subset"
    )
    require("allOf" in repair["provider_schema_forbidden_keywords"], "allOf ban")
    require("uniqueItems" in repair["provider_schema_forbidden_keywords"], "unique ban")
    provider_contract = repair["provider_object_contract"]
    require(
        provider_contract["all_properties_required"] is True,
        "all properties required",
    )
    require(
        provider_contract["additionalProperties_must_be_false"] is True,
        "closed provider objects",
    )
    require(
        provider_contract["undeclared_keywords_permitted"] is False,
        "undeclared provider keywords",
    )
    require(
        provider_contract["recursive_closure_required"] is True,
        "recursive provider closure",
    )
    require(repair["local_semantic_validation"]["required"] is True, "local semantics")
    require(
        repair["local_semantic_validation"]["provider_validation_substitute"] is False,
        "provider validation substitute",
    )
    require(
        repair["local_semantic_validation"]["fail_closed"] is True, "semantic close"
    )
    require(repair["raw_persistence_permitted"] is False, "raw persistence")
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
    require(
        freeze["commit_sequence"]
        == ["F1A-implementation-commit", "F1B-manifest-only-freeze-commit"],
        "two-commit freeze",
    )
    require(
        freeze["corpus_authoring_before_F1B_pass_permitted"] is False, "early corpus"
    )
    require(
        freeze["post_F1B_semantic_change_permitted"] is False,
        "post-freeze semantic change",
    )
    require(freeze["same_program_refreeze_permitted"] is False, "same-program refreeze")
    state = document["durable_state_contract"]
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
    require(state["status_enum"] == ["claimed", "completed", "invalid"], "state status")
    require(
        state["additional_top_level_or_nested_keys_permitted"] is False,
        "state extension",
    )
    require_exact(
        state["atomic_claim"],
        "owner-only-no-follow-O_CREAT-O_EXCL-before-first-canary-child",
        "atomic claim",
    )
    corpus = document["corpus_contract"]
    require(corpus["authoring_gate"] == "SQ3-F1B:PASS", "corpus gate")
    require(
        (
            corpus["independent_author_count"],
            corpus["cases_per_author"],
            corpus["total_unique_cases"],
        )
        == (2, 20, 40),
        "corpus counts",
    )
    require(
        corpus["total_presentations"] == 80 and corpus["total_batch_calls"] == 320,
        "schedule",
    )
    require(
        corpus["authors_may_access_each_other_split"] is False,
        "split author isolation",
    )
    require(
        corpus["result_informed_change_permitted"] is False,
        "result-informed corpus change",
    )
    preflight = document["zero_model_preflight"]
    require((preflight["attempts"], preflight["model_calls"]) == (1, 0), "preflight")
    require(
        preflight["repair_or_second_preflight_permitted"] is False, "preflight retry"
    )
    execution = document["qualification_execution"]
    require(execution["canary"]["calls"] == 4, "canary")
    require(execution["canary"]["not_pass_route"] == "SQ3-AR", "canary route")
    require(
        execution["canary"][
            "retry_top_up_replacement_second_canary_or_byte_change_permitted"
        ]
        is False,
        "canary retry or change",
    )
    require(execution["batch"]["hard_call_ceiling"] == 320, "batch")
    require(
        execution["batch"]["incomplete_failed_or_invalid_route"] == "SQ3-AR",
        "batch route",
    )
    global_and = document["global_and"]
    require(global_and["operator"] == "logical-AND", "global AND")
    require(
        global_and["compensation_threshold_repair_override_or_later_cure_permitted"]
        is False,
        "global compensation",
    )
    require(
        global_and["subaggregate_or_raw_result_disclosure_permitted"] is False,
        "global disclosure",
    )
    routing = document["routing_and_claims"]
    require(routing["pass_edge"] == "SQ3-F6:PASS->SQ3-AS-HANDOFF", "downstream pass")
    require(routing["nonpass_edge"] == "SQ3-F6:NOT_PASS->SQ3-AR", "nonpass")
    require(
        routing["SQ3_AS_HANDOFF_is_execution_authority"] is False, "handoff authority"
    )


class AeSq3ProgramAuthorityTests(unittest.TestCase):
    def test_strict_recursive_contract_and_exact_custody(self) -> None:
        raw = AUTHORITY_PATH.read_bytes()
        document = strict(raw)
        validate(document)
        predecessor = document["predecessor_terminal_history"]
        self.assertEqual(
            hashlib.sha256(TERMINAL_PATH.read_bytes()).hexdigest(),
            predecessor["terminal_decision"]["raw_sha256"],
        )
        preterminal_plan = subprocess.run(
            ["git", "show", f"{SQ3_F0_COMMIT}:docs/exec-plans/active/ae-sq3.md"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(
            hashlib.sha256(preterminal_plan).hexdigest(),
            document["namespace"]["active_plan"]["raw_sha256"],
        )
        record = subprocess.run(
            ["git", "show", f"{RECORD_COMMIT}:evals/ae-sq2/d0/diagnostic-record.json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(hashlib.sha256(record).hexdigest(), RECORD_RAW_SHA)
        self.assertEqual(
            subprocess.run(
                ["git", "hash-object", "--stdin"],
                cwd=ROOT,
                input=record,
                check=True,
                capture_output=True,
            )
            .stdout.decode()
            .strip(),
            predecessor["diagnostic_record"]["blob"],
        )
        self.assertNotIn("c4b18", raw.decode())

    def test_foundation_pointer_and_decision_rows(self) -> None:
        pointer = (
            "**Active successor plan:** `docs/exec-plans/active/ae-sq9.md` for AE-SQ9 only; "
            "AE-SQ8, AE-SQ7, AE-SQ6, AE-SQ5, AE-SQ4, AE-SQ3, AE-SQ2, AE-SQ1, and `EXECPLAN.md` remain immutable terminal history"
        )
        self.assertEqual(FOUNDATION_PATH.read_text().splitlines()[6], pointer)
        rows = list(csv.DictReader(io.StringIO(LOG_PATH.read_text())))
        identifiers = [row["decision_id"] for row in rows]
        self.assertEqual(identifiers.count("AE-SQ2-AR-2026-08-12"), 1)
        self.assertEqual(identifiers.count("AE-SQ3-F0-2026-08-12"), 1)
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
        self.assertEqual(identifiers.count("AE-SQ8-AR-2026-08-13"), 1)
        self.assertEqual(identifiers.count("AE-SQ9-F0-2026-08-13"), 1)

    def test_mutation_reds(self) -> None:
        document = strict(AUTHORITY_PATH.read_bytes())
        mutations: list[tuple[str, dict[str, Any]]] = []
        mutation = copy.deepcopy(document)
        mutation["extra"] = True
        mutations.append(("top-level extension", mutation))
        mutation = copy.deepcopy(document)
        mutation["durable_state_contract"]["extra"] = True
        mutations.append(("nested extension", mutation))
        mutation = copy.deepcopy(document)
        mutation["diagnosed_repair"]["additional_diagnostic_calls"] = 1
        mutations.append(("diagnostic call", mutation))
        mutation = copy.deepcopy(document)
        mutation["diagnosed_repair"]["provider_schema_permitted_keywords"].append(
            "allOf"
        )
        mutations.append(("unsupported provider keyword", mutation))
        mutation = copy.deepcopy(document)
        mutation["model_configuration"]["model_fallback_permitted"] = True
        mutations.append(("model fallback", mutation))
        mutation = copy.deepcopy(document)
        mutation["call_budgets"]["retry_calls_hard_ceiling"] = 1
        mutations.append(("retry budget", mutation))
        mutation = copy.deepcopy(document)
        mutation["f1_freeze"]["corpus_authoring_before_F1B_pass_permitted"] = True
        mutations.append(("early corpus", mutation))
        mutation = copy.deepcopy(document)
        mutation["zero_model_preflight"]["attempts"] = 2
        mutations.append(("second preflight", mutation))
        mutation = copy.deepcopy(document)
        mutation["qualification_execution"]["canary"]["calls"] = 5
        mutations.append(("canary overrun", mutation))
        mutation = copy.deepcopy(document)
        mutation["global_and"]["operator"] = "average"
        mutations.append(("compensatory aggregate", mutation))

        mutation = copy.deepcopy(document)
        mutation["phase_graph"]["reopen_or_resume_permitted"] = True
        mutations.append(("reopen or resume", mutation))
        mutation = copy.deepcopy(document)
        mutation["predecessor_terminal_history"][
            "predecessor_bytes_write_permitted"
        ] = True
        mutations.append(("predecessor write", mutation))
        mutation = copy.deepcopy(document)
        mutation["corpus_contract"]["result_informed_change_permitted"] = True
        mutations.append(("result-informed corpus change", mutation))
        mutation = copy.deepcopy(document)
        mutation["corpus_contract"]["authors_may_access_each_other_split"] = True
        mutations.append(("split author access", mutation))
        mutation = copy.deepcopy(document)
        mutation["qualification_execution"]["canary"][
            "retry_top_up_replacement_second_canary_or_byte_change_permitted"
        ] = True
        mutations.append(("canary retry top-up or change", mutation))
        mutation = copy.deepcopy(document)
        mutation["global_and"]["subaggregate_or_raw_result_disclosure_permitted"] = True
        mutations.append(("subaggregate or raw disclosure", mutation))
        mutation = copy.deepcopy(document)
        mutation["f1_freeze"]["post_F1B_semantic_change_permitted"] = True
        mutations.append(("post-freeze semantic change", mutation))
        mutation = copy.deepcopy(document)
        mutation["durable_state_contract"]["atomic_claim"] = "none"
        mutations.append(("missing atomic claim", mutation))
        mutation = copy.deepcopy(document)
        mutation["diagnosed_repair"]["provider_object_contract"][
            "undeclared_keywords_permitted"
        ] = True
        mutations.append(("undeclared provider keyword", mutation))
        mutation = copy.deepcopy(document)
        mutation["diagnosed_repair"]["local_semantic_validation"][
            "provider_validation_substitute"
        ] = True
        mutations.append(("provider validation substitute", mutation))

        for name, mutation in mutations:
            with self.subTest(mutation=name):
                with self.assertRaises(ValueError):
                    validate(mutation)


if __name__ == "__main__":
    unittest.main()
