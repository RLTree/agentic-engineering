"""Closed F0 authority checks for the distinct AE-SQ2 successor program."""

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
AUTHORITY_PATH = ROOT / "evals" / "ae-sq2" / "program-authority.json"
PLAN_PATH = ROOT / "docs" / "exec-plans" / "active" / "ae-sq2.md"
FOUNDATION_PATH = ROOT / "docs" / "foundations" / "current-2026-08-08.md"
DECISION_LOG_PATH = ROOT / "docs" / "foundations" / "decision-log.csv"

BASE_COMMIT = "9861df7c7894b35f5ce758ee1b005f80ceb0426e"
BASE_TREE = "573f53baa839a3b088548a7e7ba2050003911a7a"
SQ1_TAG = "ae-sq1-terminal-2026-08-11"
SQ1_PLAN_BLOB = "ff649a88cdf8ffa1f1a4b6a8b6a71b2c01cc43b4"
SQ1_PLAN_SHA256 = "ebc53ca6305837ecd089dd201542dcbb35c5478b6bbf31e1003a227440868418"
SQ1_NAMESPACE_TREE = "47e799543415c8834d9753f5252dd73e33eb3639"
DECISION_ROW_ID = "AE-SQ2-F0-2026-08-12"
AUTHORITY_SEMANTIC_SHA256 = "52ff479e81cd143bd682f0dcf875a12d055d403695e569e0534925b762550b24"

TOP_LEVEL_KEYS = (
    "schema_version",
    "program_id",
    "authority_status",
    "claim_ceiling",
    "owner_authorization",
    "predecessor_terminal_history",
    "active_plan",
    "phase_graph",
    "call_budgets",
    "model_configuration",
    "diagnostic_contract",
    "repaired_freeze",
    "corpus_contract",
    "zero_model_preflight",
    "qualification_execution",
    "global_and",
    "routing_and_claims",
    "custody_lanes",
    "namespace",
    "forbidden_actions",
    "acceptance",
)
PHASES = (
    "SQ2-F0",
    "SQ2-D0",
    "SQ2-F1",
    "SQ2-F2",
    "SQ2-F3",
    "SQ2-F4",
    "SQ2-F5",
    "SQ2-F6",
    "SQ2-AS-HANDOFF",
    "SQ2-AR",
)
SUCCESS_EDGES = (
    "SQ2-F0->SQ2-D0",
    "SQ2-D0:CLOSED->SQ2-F1",
    "SQ2-F1:PASS->SQ2-F2",
    "SQ2-F2:PASS->SQ2-F3",
    "SQ2-F3:PASS->SQ2-F4",
    "SQ2-F4:PASS->SQ2-F5",
    "SQ2-F5:CLOSED->SQ2-F6",
    "SQ2-F6:PASS->SQ2-AS-HANDOFF",
)
FAILURE_EDGES = (
    "SQ2-D0:BLOCKED->SQ2-AR",
    "SQ2-F1:NOT_PASS->SQ2-AR",
    "SQ2-F2:NOT_PASS->SQ2-AR",
    "SQ2-F3:NOT_PASS->SQ2-AR",
    "SQ2-F4:NOT_PASS->SQ2-AR",
    "SQ2-F6:NOT_PASS->SQ2-AR",
)
CLASSIFICATIONS = (
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
)
CLASSIFICATION_PRECEDENCE = (
    "transport_spawn",
    "timeout",
    "schema_unsupported",
    "provider_request_rejected",
    "signal_exit",
    "process_exit",
    "empty_stdout",
    "invalid_jsonl",
    "unknown_event",
    "missing_completed_message",
    "schema_invalid",
    "semantic_invalid",
    "valid_completed",
    "other_fail_closed",
)
REDACTED_ERROR_CLASSES = (
    "none",
    "invalid_json_schema",
    "invalid_request",
    "authentication",
    "authorization",
    "rate_limit",
    "network",
    "server",
    "other",
)
PROBE_IDS = ("p0", "p1", "p2", "p3")
PERMITTED_D0_FIELDS = (
    "diagnostic_id",
    "mode",
    "status",
    "claim_ceiling",
    "probe_id",
    "model",
    "reasoning_effort",
    "authority_sha256",
    "diagnostic_schema_sha256",
    "input_schema",
    "cli",
    "calls",
    "usage",
    "classification_counts",
    "event_type_counts",
    "input_schema_path",
    "input_schema_size_bytes",
    "input_schema_sha256",
    "cli_path",
    "cli_version",
    "cli_sha256",
    "classification",
    "exit_code_or_null",
    "signal_or_null",
    "request_bytes",
    "request_sha256",
    "stdout_bytes",
    "stdout_sha256",
    "stderr_bytes",
    "stderr_sha256",
    "completed_message_bytes",
    "completed_message_sha256",
    "closed_event_type_counts",
    "usage_observed",
    "closed_usage_counters",
    "redacted_error_class",
    "calls_started",
    "calls_completed",
    "classification_counters",
    "aggregate_sha256",
    "record_sha256",
)
FORBIDDEN_D0_MATERIAL = (
    "raw-prompt",
    "raw-output",
    "excerpt",
    "summary",
    "arbitrary-error-string",
    "transcript",
    "thread-id",
    "event-body",
    "event-payload",
    "provider-payload",
    "provider-error-message",
    "stack-trace",
    "token-log",
)
F0_FILES = (
    "docs/exec-plans/active/ae-sq2.md",
    "evals/ae-sq2/program-authority.json",
    "tests/test_ae_sq2_program_authority.py",
    "docs/foundations/current-2026-08-08.md",
    "docs/foundations/decision-log.csv",
)
RESERVED_D0_ARTIFACTS = (
    "evals/ae-sq2/d0/diagnostic-authority.json",
    "evals/ae-sq2/d0/diagnostic-schema.json",
    "evals/ae-sq2/d0/diagnostic-record.json",
)
RESERVED_D0_SUPPORT = (
    "scripts/diagnose_ae_sq2_handshake.py",
    "tests/test_diagnose_ae_sq2_handshake.py",
)
FAIL_VALUES = (
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
)
FORBIDDEN_ACTIONS = (
    "write-AE-SQ1",
    "mutate-EXECPLAN",
    "retry-reopen-resume-or-H6",
    "import-AE-SQ1-task-corpus-raw-result-or-outcome",
    "persist-D0-raw-prompt-or-output",
    "adaptive-or-repeated-D0-probe",
    "use-D0-as-AQ-evidence",
    "author-corpus-before-F1-pass",
    "same-program-refreeze-after-F1",
    "model-call-during-F2-F3-or-F6",
    "canary-before-F3-pass",
    "batch-before-F4-pass",
    "retry-replay-replace-duplicate-or-extra-presentation",
    "model-provider-reasoning-or-mode-fallback",
    "later-phase-compensation",
    "subaggregate-or-raw-result-disclosure",
    "route-nonpass-downstream",
    "public-release-publish-or-promotion",
    "deletion-or-migration",
)


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_strict_json(path: Path) -> dict[str, Any]:
    document = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON value: {value}")
        ),
    )
    if type(document) is not dict:
        raise AssertionError("authority must be a JSON object")
    return document


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def require_exact_keys(document: dict[str, Any]) -> None:
    require(tuple(document) == TOP_LEVEL_KEYS, "top-level keys or order drifted")


def authority_semantic_sha256(document: dict[str, Any]) -> str:
    """Hash every recursive key, value, JSON type, and sequence order."""
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_authority(document: dict[str, Any]) -> None:
    require_exact_keys(document)
    require(
        authority_semantic_sha256(document) == AUTHORITY_SEMANTIC_SHA256,
        "recursive keys, values, JSON types, or order drifted",
    )
    require(document["schema_version"] == "AE-SQ2-program-authority-v1", "schema")
    require(document["program_id"] == "AE-SQ2", "program id")
    require(
        document["authority_status"] == "F0_INITIAL_AUTHORITY_CLOSED",
        "authority status",
    )
    require(
        document["claim_ceiling"]
        == "structural-program-authority-and-unexecuted-owner-authorization-only",
        "claim ceiling",
    )

    owner = document["owner_authorization"]
    require(owner["authorized"] is True, "owner authorization")
    require(
        owner["authorized_phases"]
        == ["SQ2-D0", "SQ2-F1", "SQ2-F2", "SQ2-F3", "SQ2-F4", "SQ2-F5", "SQ2-F6"],
        "authorized phase order",
    )
    require(owner["live_model_phases"] == ["SQ2-D0", "SQ2-F4", "SQ2-F5"], "live phases")
    require(owner["corpus_authoring_authorized_only_after_F1"] is True, "corpus gate")
    require(owner["downstream_execution_authorized_by_this_artifact"] is False, "downstream authority")
    require(owner["release_publish_promotion_authorized"] is False, "release authority")

    predecessor = document["predecessor_terminal_history"]
    require(predecessor["program_id"] == "AE-SQ1", "predecessor id")
    require(predecessor["commit"] == BASE_COMMIT, "predecessor commit")
    require(predecessor["tree"] == BASE_TREE, "predecessor tree")
    require(predecessor["immutable_tag"] == SQ1_TAG, "predecessor tag")
    require(predecessor["tag_target"] == BASE_COMMIT, "tag target")
    require(predecessor["plan"]["blob"] == SQ1_PLAN_BLOB, "SQ1 plan blob")
    require(predecessor["plan"]["raw_sha256"] == SQ1_PLAN_SHA256, "SQ1 plan digest")
    require(predecessor["namespace"]["tree"] == SQ1_NAMESPACE_TREE, "SQ1 namespace")
    require(predecessor["predecessor_write_permitted"] is False, "SQ1 write rule")
    require(predecessor["EXECPLAN_write_permitted"] is False, "EXECPLAN rule")

    active = document["active_plan"]
    require(active["path"] == "docs/exec-plans/active/ae-sq2.md", "plan path")
    require(active["program_base_commit"] == BASE_COMMIT, "program base")
    require(active["successor_commit"] == "ABSENT_NOT_SELF_BOUND", "self binding")
    require(active["decision_log_row_id"] == DECISION_ROW_ID, "decision row")

    graph = document["phase_graph"]
    require(graph["ordered_phases"] == list(PHASES), "phase order")
    require(graph["success_edges"] == list(SUCCESS_EDGES), "success edges")
    require(graph["blocking_failure_edges"] == list(FAILURE_EDGES), "failure edges")
    require(graph["F5_outcomes_must_reach_F6"] is True, "F5 scoring route")
    require(graph["additional_active_phases_permitted"] is False, "extra phases")
    require(graph["additional_active_edges_permitted"] is False, "extra edges")
    require(graph["later_phase_compensation_permitted"] is False, "compensation")
    require(graph["reopen_or_resume_permitted"] is False, "reopen")

    budgets = document["call_budgets"]
    require(budgets["counting_unit"] == "attempted-model-invocation", "counting unit")
    require(budgets["diagnostic"]["normal_calls"] == 4, "D0 normal calls")
    require(budgets["diagnostic"]["hard_ceiling"] == 4, "D0 budget")
    require(budgets["qualification_canary"]["hard_ceiling"] == 4, "canary budget")
    require(budgets["qualification_batch"]["hard_ceiling"] == 320, "batch budget")
    require(budgets["qualification_hard_ceiling"] == 324, "qualification budget")
    require(budgets["program_through_F6_hard_ceiling"] == 328, "program budget")
    require(budgets["retry_calls_hard_ceiling"] == 0, "retry budget")
    require(budgets["failed_or_malformed_attempts_count"] is True, "failed calls")
    require(budgets["unused_calls_transfer_permitted"] is False, "transfer")
    require(budgets["top_up_or_replacement_calls_permitted"] is False, "top up")

    model = document["model_configuration"]
    require(model["model_id"] == "gpt-5.5", "model")
    require(model["reasoning_effort"] == "medium", "effort")
    require(model["applies_to_phases"] == ["SQ2-D0", "SQ2-F4", "SQ2-F5"], "model phases")
    for key in (
        "model_fallback_permitted",
        "provider_fallback_permitted",
        "reasoning_fallback_permitted",
        "mode_fallback_permitted",
    ):
        require(model[key] is False, key)

    diagnostic = document["diagnostic_contract"]
    require(diagnostic["must_precede_candidate_freeze"] is True, "D0 order")
    require(diagnostic["corpus_must_not_exist"] is True, "D0 corpus")
    require(diagnostic["qualification_effect"] == "none", "D0 qualification")
    require(diagnostic["predeclared_probe_slots"] == 4, "D0 slots")
    require(diagnostic["required_probe_ids"] == list(PROBE_IDS), "D0 probe identities")
    require(diagnostic["attempts_per_slot_max"] == 1, "D0 attempts")
    require(diagnostic["calls_started_required"] == 4, "D0 calls started")
    require(diagnostic["distinct_probe_ids_required"] == 4, "D0 distinct probes")
    require(diagnostic["all_slots_attempted_exactly_once"] is True, "D0 exact unit")
    require(diagnostic["early_close_permitted"] is False, "D0 early close")
    require(diagnostic["adaptive_probe_selection_permitted"] is False, "D0 adaptive")
    require(
        diagnostic["slot_repeat_replace_or_reorder_permitted"] is False,
        "D0 repeat or reorder",
    )
    require(diagnostic["retry_calls"] == 0, "D0 retry")
    require(diagnostic["classification_enum"] == list(CLASSIFICATIONS), "D0 classifications")
    require(
        diagnostic["classification_precedence"] == list(CLASSIFICATION_PRECEDENCE),
        "D0 classification precedence",
    )
    require(
        diagnostic["redacted_error_class_enum"] == list(REDACTED_ERROR_CLASSES),
        "D0 redacted error classes",
    )
    counters = diagnostic["classification_counter_contract"]
    require(counters["keys_in_exact_order"] == list(CLASSIFICATIONS), "D0 counter keys")
    require(counters["each_key_exactly_once"] is True, "D0 counter key cardinality")
    require(counters["value_type"] == "integer-not-boolean", "D0 counter type")
    require(type(counters["minimum"]) is int and counters["minimum"] == 0, "D0 counter min")
    require(type(counters["maximum"]) is int and counters["maximum"] == 4, "D0 counter max")
    require(type(counters["sum_required"]) is int and counters["sum_required"] == 4, "D0 counter sum")
    require(diagnostic["permitted_persisted_fields"] == list(PERMITTED_D0_FIELDS), "D0 fields")
    require("calls_started" in diagnostic["permitted_persisted_fields"], "D0 started name")
    require("calls_completed" in diagnostic["permitted_persisted_fields"], "D0 completed name")
    require("usage_observed_calls" not in diagnostic["permitted_persisted_fields"], "D0 usage aggregate")
    require(diagnostic["forbidden_persisted_material"] == list(FORBIDDEN_D0_MATERIAL), "D0 raw ban")
    require(diagnostic["transient_bytes_discarded_after_hash_and_classification"] is True, "D0 discard")
    require(diagnostic["budget_or_persistence_violation_route"] == "SQ2-AR", "D0 failure route")

    repaired = document["repaired_freeze"]
    require(repaired["requires"] == "SQ2-D0:CLOSED_DIAGNOSTIC_ONLY", "F1 gate")
    require(repaired["corpus_or_label_input_permitted"] is False, "F1 corpus input")
    require(repaired["qualification_result_input_permitted"] is False, "F1 result input")
    require(repaired["corpus_authoring_before_close_permitted"] is False, "F1 authoring")
    require(repaired["post_close_semantic_change_permitted"] is False, "F1 mutation")
    require(repaired["same_program_refreeze_permitted"] is False, "F1 refreeze")

    corpus = document["corpus_contract"]
    require(corpus["authoring_gate"] == "SQ2-F1:PASS", "F2 gate")
    require(corpus["authoring_before_gate_permitted"] is False, "early corpus")
    require(corpus["independent_author_count"] == 2, "author count")
    require(corpus["cases_per_author"] == 20, "cases per author")
    require(corpus["total_unique_cases"] == 40, "case total")
    require(corpus["conditions"] == ["current", "reduced"], "conditions")
    require(corpus["total_presentations"] == 80, "presentation total")
    require(corpus["calls_per_presentation"] == 4, "calls per presentation")
    require(corpus["total_batch_calls"] == 320, "batch derivation")
    require(corpus["post_consumption_status"] == "NO_REPLAY", "no replay")
    require(corpus["authors_may_access_each_other_split"] is False, "split sharing")
    require(corpus["authors_may_access_D0_model_material"] is False, "D0 split input")

    preflight = document["zero_model_preflight"]
    require(preflight["model_calls"] == 0, "F3 calls")
    require(preflight["requires"] == "SQ2-F2:PASS", "F3 gate")
    require(preflight["pass_required_for_canary"] is True, "F3 pass gate")
    require(preflight["second_preflight_permitted"] is False, "F3 replay")
    require(preflight["not_pass_route"] == "SQ2-AR", "F3 failure route")

    execution = document["qualification_execution"]
    canary = execution["canary"]
    require(canary["requires"] == "SQ2-F3:PASS", "F4 gate")
    require(canary["units"] == 1, "F4 unit")
    require(canary["calls"] == 4, "F4 calls")
    require(canary["calls_per_isolated_child_context"] == 1, "F4 isolation")
    require(canary["sibling_state_visible"] is False, "F4 sibling state")
    require(canary["corpus_content_permitted"] is False, "F4 corpus content")
    require(canary["retry_or_replacement_calls"] == 0, "F4 retry")
    require(canary["not_pass_route"] == "SQ2-AR", "F4 failure route")
    batch = execution["batch"]
    require(batch["requires"] == "SQ2-F4:PASS", "F5 gate")
    require(batch["total_presentations"] == 80, "F5 presentations")
    require(batch["calls_per_presentation"] == 4, "F5 calls per presentation")
    require(batch["hard_call_ceiling"] == 320, "F5 ceiling")
    require(batch["retry_replay_replacement_or_extra_permitted"] is False, "F5 replay")
    require(batch["all_outcomes_route"] == "SQ2-F6", "F5 scoring route")

    global_and = document["global_and"]
    require(global_and["model_calls"] == 0, "F6 calls")
    require(global_and["operator"] == "logical-AND", "F6 operator")
    require(global_and["required_conditions"] == ["current", "reduced"], "F6 conditions")
    require(global_and["fail_values"] == list(FAIL_VALUES), "F6 fail closure")
    require(global_and["compensation_or_override_permitted"] is False, "F6 override")
    require(global_and["result_count"] == 1, "aggregate count")
    require(
        global_and["result_projection"]
        == "candidate-bound-aggregate-status-and-digest-only",
        "projection",
    )
    require(global_and["subaggregate_disclosure_permitted"] is False, "subaggregate")
    require(global_and["raw_result_disclosure_permitted"] is False, "raw result")

    routes = document["routing_and_claims"]
    require(routes["pass_edge"] == "SQ2-F6:PASS->SQ2-AS-HANDOFF", "pass edge")
    require(routes["nonpass_edge"] == "SQ2-F6:NOT_PASS->SQ2-AR", "nonpass edge")
    require(routes["SQ2_AS_HANDOFF_is_execution_authority"] is False, "AS authority")
    require(routes["SQ2_AR_is_terminal"] is True, "AR terminal")
    require(routes["public_action_authorized"] is False, "public authority")

    require(document["forbidden_actions"] == list(FORBIDDEN_ACTIONS), "forbidden actions")

    namespace = document["namespace"]
    require(namespace["artifact_root"] == "evals/ae-sq2", "namespace")
    require(namespace["predecessor_root_write_permitted"] is False, "SQ1 namespace")
    require(namespace["F0_files"] == list(F0_FILES), "F0 file set")
    require(
        namespace["reserved_future_artifacts"][:3] == list(RESERVED_D0_ARTIFACTS),
        "D0 artifact identities",
    )
    require(
        namespace["reserved_future_support_paths"] == list(RESERVED_D0_SUPPORT),
        "D0 support identities",
    )
    require(namespace["reserved_future_paths_confer_state"] is False, "reserved state")

    acceptance = document["acceptance"]
    require(acceptance["F0_status"] == "structural-program-authority-closed", "F0 status")
    require(
        acceptance["F0_execution_claim"]
        == "zero-live-calls-zero-corpus-zero-candidate-freeze",
        "F0 execution claim",
    )
    require(acceptance["no_live_call_or_corpus_claim_from_F0"] is True, "F0 claim")
    require(acceptance["semantic_change_requires_new_program_id"] is True, "new id")


class TestAeSq2ProgramAuthority(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.authority = read_strict_json(AUTHORITY_PATH)

    def test_strict_contract(self) -> None:
        validate_authority(self.authority)

    def test_plan_digest_and_required_semantics(self) -> None:
        raw = PLAN_PATH.read_bytes()
        expected = self.authority["active_plan"]["raw_sha256"]
        self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)
        text = raw.decode("utf-8")
        for literal in (
            "AE-SQ2 is not\nan AE-SQ1 retry, reopen, resume, continuation",
            "`SQ2-D0` diagnostic | 4 | 4",
            "`SQ2-F4` canary | 4 | 4",
            "`SQ2-F5` batch | 320 | 320",
            "Fresh corpus authoring is forbidden until the exact F1 freeze is closed.",
            "Only exact global `PASS` routes to `SQ2-AS-HANDOFF`.",
            "There is no infrastructure retry, content retry, post-observation",
        ):
            self.assertIn(literal, text)
        for classification in CLASSIFICATIONS:
            self.assertIn(f"`{classification}`", text)

    def test_predecessor_git_custody(self) -> None:
        self.assertEqual(git("rev-parse", f"{BASE_COMMIT}^{{tree}}"), (BASE_TREE + "\n").encode())
        self.assertEqual(git("rev-parse", f"{SQ1_TAG}^{{}}"), (BASE_COMMIT + "\n").encode())
        self.assertEqual(
            git("rev-parse", f"{BASE_COMMIT}:docs/exec-plans/active/ae-sq1.md"),
            (SQ1_PLAN_BLOB + "\n").encode(),
        )
        self.assertEqual(
            hashlib.sha256(git("show", f"{BASE_COMMIT}:docs/exec-plans/active/ae-sq1.md")).hexdigest(),
            SQ1_PLAN_SHA256,
        )
        self.assertEqual(
            git("rev-parse", f"{BASE_COMMIT}:evals/ae-sq1"),
            (SQ1_NAMESPACE_TREE + "\n").encode(),
        )
        changed = git(
            "diff",
            "--name-only",
            BASE_COMMIT,
            "--",
            "EXECPLAN.md",
            "docs/exec-plans/active/ae-sq1.md",
            "evals/ae-sq1",
        )
        self.assertEqual(changed, b"")

    def test_foundation_pointer_is_only_foundation_body_change(self) -> None:
        base = git("show", f"{BASE_COMMIT}:docs/foundations/current-2026-08-08.md").decode()
        old = (
            "**Active successor plan:** `docs/exec-plans/active/ae-sq1.md` for "
            "AE-SQ1 only; `EXECPLAN.md` remains immutable predecessor terminal history"
        )
        new = (
            "**Active successor plan:** `docs/exec-plans/active/ae-sq2.md` for "
            "AE-SQ2 only; AE-SQ1 and `EXECPLAN.md` remain immutable terminal history"
        )
        self.assertEqual(FOUNDATION_PATH.read_text(encoding="utf-8"), base.replace(old, new))

    def test_decision_log_appends_exactly_one_F0_row(self) -> None:
        base = git("show", f"{BASE_COMMIT}:docs/foundations/decision-log.csv")
        current = DECISION_LOG_PATH.read_bytes()
        self.assertTrue(current.startswith(base))
        suffix = current[len(base) :].decode("utf-8")
        rows = list(csv.reader(io.StringIO(suffix)))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], DECISION_ROW_ID)
        self.assertEqual(rows[0][11], BASE_COMMIT)
        self.assertIn(self.authority["active_plan"]["raw_sha256"], rows[0][12])
        self.assertIn("zero live calls", rows[0][12])
        self.assertIn("zero corpus cases", rows[0][12])

    def test_contract_mutation_reds(self) -> None:
        mutations: list[tuple[str, dict[str, Any]]] = []

        changed = copy.deepcopy(self.authority)
        changed["call_budgets"]["diagnostic"]["hard_ceiling"] = 5
        mutations.append(("D0 budget", changed))

        changed = copy.deepcopy(self.authority)
        changed["call_budgets"]["retry_calls_hard_ceiling"] = 1
        mutations.append(("retry budget", changed))

        changed = copy.deepcopy(self.authority)
        changed["phase_graph"]["ordered_phases"][1:3] = ["SQ2-F1", "SQ2-D0"]
        mutations.append(("phase order", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["classification_enum"].remove("schema_unsupported")
        mutations.append(("D0 enum", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["calls_started_required"] = 3
        mutations.append(("partial D0 close", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["early_close_permitted"] = True
        mutations.append(("early D0 close", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["adaptive_probe_selection_permitted"] = True
        mutations.append(("adaptive D0", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["required_probe_ids"][0:2] = ["p1", "p0"]
        mutations.append(("reordered D0 slots", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["required_probe_ids"][-1] = "p2"
        mutations.append(("repeated D0 slot", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["classification_precedence"][0:2] = [
            "timeout",
            "transport_spawn",
        ]
        mutations.append(("classification precedence", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["redacted_error_class_enum"].append("raw")
        mutations.append(("redacted error enum", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["classification_counter_contract"]["sum_required"] = 3
        mutations.append(("classification counter sum", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["permitted_persisted_fields"].append("raw_output")
        mutations.append(("D0 raw persistence", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["permitted_persisted_fields"].append(
            "usage_observed_calls"
        )
        mutations.append(("D0 forbidden usage aggregate", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["permitted_persisted_fields"].remove("calls")
        mutations.append(("missing D0 container", changed))

        changed = copy.deepcopy(self.authority)
        changed["repaired_freeze"]["corpus_authoring_before_close_permitted"] = True
        mutations.append(("early corpus", changed))

        changed = copy.deepcopy(self.authority)
        changed["corpus_contract"]["authors_may_access_each_other_split"] = True
        mutations.append(("split sharing", changed))

        changed = copy.deepcopy(self.authority)
        changed["model_configuration"]["model_fallback_permitted"] = True
        mutations.append(("model fallback", changed))

        changed = copy.deepcopy(self.authority)
        changed["qualification_execution"]["canary"]["calls"] = 3
        mutations.append(("partial canary", changed))

        changed = copy.deepcopy(self.authority)
        changed["qualification_execution"]["canary"]["sibling_state_visible"] = True
        mutations.append(("sibling-visible canary", changed))

        changed = copy.deepcopy(self.authority)
        changed["qualification_execution"]["canary"]["corpus_content_permitted"] = True
        mutations.append(("corpus-bearing canary", changed))

        changed = copy.deepcopy(self.authority)
        changed["qualification_execution"]["batch"]["hard_call_ceiling"] = 321
        mutations.append(("batch overrun", changed))

        changed = copy.deepcopy(self.authority)
        changed["global_and"]["fail_values"].remove("missing")
        mutations.append(("missing fail-open", changed))

        changed = copy.deepcopy(self.authority)
        changed["global_and"]["required_conditions"].clear()
        mutations.append(("empty global conditions", changed))

        changed = copy.deepcopy(self.authority)
        changed["forbidden_actions"].clear()
        mutations.append(("cleared forbidden actions", changed))

        changed = copy.deepcopy(self.authority)
        changed["routing_and_claims"]["nonpass_edge"] = "SQ2-F6:NOT_PASS->SQ2-AS-HANDOFF"
        mutations.append(("nonpass downstream", changed))

        changed = copy.deepcopy(self.authority)
        changed["routing_and_claims"]["SQ2_AS_HANDOFF_is_execution_authority"] = True
        mutations.append(("AS execution authority", changed))

        changed = copy.deepcopy(self.authority)
        changed["namespace"]["reserved_future_artifacts"].remove(
            "evals/ae-sq2/d0/diagnostic-schema.json"
        )
        mutations.append(("unreserved D0 schema", changed))

        changed = copy.deepcopy(self.authority)
        changed["namespace"]["reserved_future_support_paths"].pop()
        mutations.append(("unreserved D0 support", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["unexpected_nested_key"] = False
        mutations.append(("nested addition", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["attempts_per_slot_max"] = True
        mutations.append(("bool as integer", changed))

        changed = copy.deepcopy(self.authority)
        changed["diagnostic_contract"]["calls_started_required"] = None
        mutations.append(("null type", changed))

        changed = copy.deepcopy(self.authority)
        owner = changed["owner_authorization"]
        first, second, *remaining = owner.items()
        changed["owner_authorization"] = dict([second, first, *remaining])
        mutations.append(("nested key order", changed))

        for name, mutation in mutations:
            with self.subTest(mutation=name):
                with self.assertRaises(AssertionError):
                    validate_authority(mutation)

    def test_duplicate_key_rejected(self) -> None:
        with self.assertRaises(ValueError):
            json.loads('{"program_id":"AE-SQ2","program_id":"AE-SQ1"}', object_pairs_hook=reject_duplicate_keys)


if __name__ == "__main__":
    unittest.main()
