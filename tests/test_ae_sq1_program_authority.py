"""Closed F0 authority checks for the distinct AE-SQ1 successor program."""

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
MANIFEST_PATH = ROOT / "evals" / "ae-sq1" / "program-authority.json"
PLAN_PATH = ROOT / "docs" / "exec-plans" / "active" / "ae-sq1.md"
FOUNDATION_PATH = ROOT / "docs" / "foundations" / "current-2026-08-08.md"
DECISION_LOG_PATH = ROOT / "docs" / "foundations" / "decision-log.csv"

BASE_COMMIT = "340b79399a987e6aad0d5435fa540a1db511489d"
BASE_TREE = "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933"
SQ1_TERMINAL_COMMIT = "9861df7c7894b35f5ce758ee1b005f80ceb0426e"
PLAN_RAW_SHA256 = "ebc53ca6305837ecd089dd201542dcbb35c5478b6bbf31e1003a227440868418"
F0_PLAN_RAW_SHA256 = "a7080db226bf499dd3037afe683361e4ccba0c1093ce3bc4e456520e2176a382"

TOP_LEVEL_KEYS = (
    "schema_version",
    "program_id",
    "authority_status",
    "claim_ceiling",
    "owner_authorization",
    "predecessor_terminal_history",
    "active_plan",
    "imported_prerequisites",
    "stage_graph",
    "freeze_points",
    "ownership_lanes",
    "namespace",
    "aq_contract",
    "downstream_design",
    "model_budget",
    "stage_claims",
    "forbidden_actions",
    "acceptance",
    "low_risk_substitutions",
)

NOT_SEMANTICS = (
    "AQ10",
    "H6",
    "retry",
    "resume",
    "reopen",
    "cure",
    "reinterpretation",
)
PERMITTED_TERMINAL_BITS = (
    "terminal-and-stopped",
    "successful-program-conditions-unmet",
    "public-release-and-promotion-negative",
    "artifacts-remain-immutable-history",
)
FORBIDDEN_IMPORT_CLASSES = (
    "task-text",
    "case",
    "corpus",
    "prompt",
    "candidate-mechanism-as-design-or-tuning-input",
    "diagnostic",
    "score",
    "raw-observation",
    "aggregate-result",
    "inferred-failure-cause",
    "outcome",
)

PREDECESSOR_FILES = (
    (
        "predecessor_terminal_plan",
        "EXECPLAN.md",
        "68883e5f7af6fe71c49bc191c1c7fad2a08bcbbc",
        "b7e57933a36e6442d61a7e920a5f98fd370620f93cffdb5342cf268b1139ebeb",
    ),
    (
        "current_foundation_at_terminal_base",
        "docs/foundations/current-2026-08-08.md",
        "f264a69485bed2882a84d36d375f249603db5900",
        "1cc550b2539cd638bd046dcc40c7d0f7251948e575bbdb060f3d2add5ed4ca34",
    ),
    (
        "decision_log_at_terminal_base",
        "docs/foundations/decision-log.csv",
        "f6800cfc92eec12a91b6ed3bc2e15d4a84bbb353",
        "96f43b51d23a9d16024c159bbd2bf328df1b70814eafae1e7c7cec2bf776db47",
    ),
    (
        "foundation_register_at_terminal_base",
        "docs/foundations/register.csv",
        "eade50e09f117bb7c40e394f5c7b8b2686fb48ad",
        "3043ad8ff93cbf35779638be9e8a7c8e7082d14166297fdddab9b9d1ddadeaf3",
    ),
    (
        "release_checker_at_terminal_base",
        "scripts/release_check.py",
        "3e8bee25d8c3a13b8224a9393ceb20374ffa5d70",
        "8038b19990ad800047e20088ddfcb5eb5f51b91a9dbb05b28a3762bf14e7e8a9",
    ),
    (
        "aq9_e0_packet_history",
        "evals/foundation-v4/aq9-h5-independent-evidence-v1.json",
        "34bb5efc8411961227b374d7ae3b610cda628de7",
        "1ec15fa32f3ad262eb95d913c964854799546a0397874cfa803322b4bb761fcd",
    ),
    (
        "aq9_e0_verdict_history",
        "evals/foundation-v4/aq9-h5-independent-evidence-verdict-v1.json",
        "b6b142e935381baada66e4d148364d4f22d55e88",
        "374825c130d076e4d298c0a8d004fc5d6f33c201715ffefb190f98c2c87815da",
    ),
    (
        "ar_terminal_decision",
        "evals/foundation-v4/ar-terminal-decision-v1.json",
        "841bab37a125a986da8b41d8591e6fc09da6ed26",
        "62f4f2f222962c58fdd5cca09231edb533ad5a4339e2f09a0e0084decb3dbc3b",
    ),
    (
        "ar_terminal_decision_test",
        "tests/test_ar_terminal_decision_v1.py",
        "ab8da0e5bc38c2d8eb1ec9b4518abcb3f0c2b41e",
        "20ca2404034dc21e0aba1cfa2411f5255e664b49cec6a8a4d755f3ca9a7d767c",
    ),
    (
        "ar_terminal_integration_test",
        "tests/test_ar_terminal_integration_v1.py",
        "0d133103e391eafb7ebc0ea5b6e8b9ecefdbaf62",
        "e4767bfd61187c713144e68a35fc0bff8b8088a813814fdb5d8559ebf164b926",
    ),
)

STAGES = ("SQ1-AQ", "SQ1-AS", "SQ1-AC", "SQ1-AH", "SQ1-AF", "SQ1-AR")
SUCCESS_EDGES = (
    "SQ1-AQ->SQ1-AS",
    "SQ1-AS->SQ1-AC",
    "SQ1-AC->SQ1-AH",
    "SQ1-AH->SQ1-AF",
    "SQ1-AF->SQ1-AR",
)
FAILURE_EDGES = (
    "SQ1-AQ->SQ1-AR",
    "SQ1-AS->SQ1-AR",
    "SQ1-AC->SQ1-AR",
    "SQ1-AH->SQ1-AR",
    "SQ1-AF->SQ1-AR",
)
FREEZE_IDS = tuple(f"F{index}" for index in range(12))
LANE_IDS = (
    "program-owner",
    "root-conductor",
    "external-evidence-steward",
    "candidate-steward",
    "evaluator-steward",
    "split-A-author",
    "split-B-author",
    "corpus-custodian",
    "run-custodian",
    "aggregate-scorer",
    "AS-owner",
    "AC-owner",
    "AH-operator",
    "AF-authority-custodian",
    "AR-integrator",
)
FREEZE_ROWS = (
    (
        "F0",
        "program-owner-and-root-conductor",
        "program-plan-authority-pointer-log-predecessor-bindings",
        "all-canonical-candidate-evaluator-authority-heldout-and-model-corpus-observation",
    ),
    (
        "F1",
        "external-evidence-steward",
        "post-F0-reviewed-or-regenerated-independent-evidence-provenance-and-admissibility",
        "canonical-candidate-authority",
    ),
    (
        "F2",
        "candidate-steward",
        "post-F0-reviewed-or-regenerated-one-materially-non-H4-SLEC-1-candidate-and-condition-bytes",
        "evaluator-completion-and-heldout-authoring",
    ),
    (
        "F3",
        "evaluator-steward",
        "evaluator-schemas-formulas-thresholds-join-global-AND-aggregate-budgets",
        "both-independent-heldout-splits",
    ),
    (
        "F4",
        "split-A-author",
        "first-independent-20-case-heldout-split",
        "combined-corpus-freeze",
    ),
    (
        "F5",
        "split-B-author",
        "second-independent-20-case-heldout-split",
        "combined-corpus-freeze",
    ),
    (
        "F6",
        "corpus-custodian",
        "40-case-corpus-validator-80-presentation-schedule-no-replay-run-index",
        "canary-and-heldout-execution",
    ),
    (
        "F7",
        "run-custodian",
        "exact-run-packet-four-call-canary-counter-retry-state-usage-authorization",
        "first-heldout-backed-model-call",
    ),
    (
        "F8",
        "aggregate-scorer",
        "sole-AQ-aggregate-consumption-bit-direct-route",
        "SQ1-AS-or-terminal-closeout",
    ),
    (
        "F9",
        "AS-owner",
        "AS-tasks-isolation-evaluator-156-call-ceiling-and-aggregate-route",
        "SQ1-AC-or-terminal-closeout",
    ),
    (
        "F10",
        "AC-owner",
        "AC-two-decision-tasks-evaluator-144-call-ceiling-and-aggregate-route",
        "SQ1-AH-or-terminal-closeout",
    ),
    (
        "F11",
        "AH-AF-AR-owners",
        "offline-AH-envelope-AF-authority-check-separated-AR-claim-vector",
        "AH-checks-and-final-closeout",
    ),
)
LANE_ROWS = (
    (
        "program-owner",
        "objective-F0-authorization-consequential-exceptions",
        "heldout-access-raw-output-access-outcome-driven-contract-change",
    ),
    (
        "root-conductor",
        "stage-order-custody-counters-PASS-HOLD-direct-failure-routing",
        "candidate-authorship-split-authorship-scoring-discretion-release-actions",
    ),
    (
        "external-evidence-steward",
        "F1-public-source-provenance-and-independence",
        "predecessor-task-corpus-mechanism-diagnostic-score-result-outcome-access",
    ),
    (
        "candidate-steward",
        "one-F2-SLEC-1-candidate-from-F1-only",
        "heldout-label-author-identity-model-observation-predecessor-nonterminal-access",
    ),
    (
        "evaluator-steward",
        "F3-schemas-formulas-thresholds-four-output-join-aggregate-projection",
        "heldout-access-and-pre-freeze-model-observation-access",
    ),
    (
        "split-A-author",
        "F4-split-A-only",
        "split-B-outcome-and-candidate-internal-access",
    ),
    (
        "split-B-author",
        "F5-split-B-only",
        "split-A-outcome-and-candidate-internal-access",
    ),
    (
        "corpus-custodian",
        "F6-validation-digests-schedule-blinding-no-replay",
        "case-candidate-evaluator-edit-and-result-interpretation",
    ),
    (
        "run-custodian",
        "F7-execution-envelope-bytes-counter-stop",
        "contract-change-content-retry-scoring-change-raw-publication",
    ),
    (
        "aggregate-scorer",
        "F8-deterministic-global-AND-and-aggregate-projection",
        "candidate-evaluator-corpus-change-and-subaggregate-disclosure",
    ),
    (
        "AS-owner",
        "F9-isolated-adviser-builder-stage",
        "AQ-reinterpretation-pre-pass-AC-work-field-host-claims",
    ),
    (
        "AC-owner",
        "F10-exact-two-decision-composition-stage",
        "AS-reinterpretation-pre-pass-AH-work-generalized-composition-claims",
    ),
    (
        "AH-operator",
        "F11-offline-unprivileged-disposable-home-checks",
        "network-credentials-production-installed-home-clean-host-claim-privilege",
    ),
    (
        "AF-authority-custodian",
        "F11-separate-privacy-consent-envelope-authority-check",
        "participant-contact-data-collection-inferred-field-authority",
    ),
    (
        "AR-integrator",
        "separated-claim-vector-retention-stop",
        "claim-averaging-reopen-release-publish-promote-delete-migrate",
    ),
)
BUDGET = {
    "SQ1-AQ_normal": 324,
    "SQ1-AQ_absolute": 328,
    "SQ1-AS_hard_ceiling": 156,
    "SQ1-AC_hard_ceiling": 144,
    "SQ1-AH_hard_ceiling": 0,
    "SQ1-AF_hard_ceiling": 0,
    "SQ1-AR_hard_ceiling": 0,
    "normal_all_pass_ceiling": 624,
    "absolute_all_program_ceiling": 628,
    "unused_transfer_permitted": False,
    "diagnostic_overrun_permitted": False,
}
FAIL_VALUES = (
    "missing",
    "skipped",
    "undefined",
    "nonfinite",
    "malformed",
    "duplicate",
    "extra",
    "unevaluable",
)
AR_COORDINATES = (
    "program_authority",
    "aq_activation_selection",
    "as_isolated_advice_value",
    "ac_two_decision_composition",
    "ah_offline_disposable_home",
    "af_field_usefulness",
    "production_clean_host_security",
    "public_release_publish_promotion",
    "deletion_migration",
)
FORBIDDEN_ACTIONS = (
    "public-release",
    "publish",
    "promotion",
    "deletion",
    "migration",
    "production-action",
    "credentialed-host-action",
    "networked-AH-action",
    "field-action-without-separate-authority",
    "predecessor-reopen",
    "corpus-replay",
    "post-observation-retry",
    "model-fallback",
    "later-stage-compensation",
    "subaggregate-disclosure",
    "raw-result-disclosure",
)
F0_FILES = (
    "docs/exec-plans/active/ae-sq1.md",
    "evals/ae-sq1/program-authority.json",
    "tests/test_ae_sq1_program_authority.py",
    "docs/foundations/current-2026-08-08.md",
    "docs/foundations/decision-log.csv",
)
RESERVED_ARTIFACTS = (
    "evals/ae-sq1/external-evidence.json",
    "evals/ae-sq1/historical-task-digests.json",
    "evals/ae-sq1/candidate-manifest.json",
    "evals/ae-sq1/slec1-authority.json",
    "evals/ae-sq1/slec1-capsule-schema.json",
    "evals/ae-sq1/slec1-resolution-schema.json",
    "evals/ae-sq1/slec1-reference-policy.json",
    "evals/ae-sq1/aq/corpus-schema.json",
    "evals/ae-sq1/aq/evaluator-schema.json",
    "evals/ae-sq1/aq/gates.json",
    "evals/ae-sq1/aq/metrics.json",
    "evals/ae-sq1/aq/split-a.json",
    "evals/ae-sq1/aq/split-b.json",
    "evals/ae-sq1/aq/corpus-manifest.json",
    "evals/ae-sq1/aq/run-manifest-schema.json",
    "evals/ae-sq1/aq/run-manifest.json",
    "evals/ae-sq1/aq/aggregate.json",
    "evals/ae-sq1/as/schema.json",
    "evals/ae-sq1/ac/schema.json",
    "evals/ae-sq1/ah/stage-authority.json",
    "evals/ae-sq1/ah/result.json",
    "evals/ae-sq1/af/omission.json",
    "evals/ae-sq1/ar/decision.json",
)
RESERVED_SCRIPTS = (
    "scripts/resolve_ae_sq1_slec.py",
    "scripts/check_ae_sq1_candidate.py",
    "scripts/validate_ae_sq1_corpus.py",
    "scripts/ae_sq1_run_index.py",
    "scripts/run_ae_sq1_aq.py",
    "scripts/score_ae_sq1_aq.py",
    "scripts/run_ae_sq1_as.py",
    "scripts/run_ae_sq1_ac.py",
    "scripts/check_ae_sq1_ah.py",
    "scripts/close_ae_sq1.py",
)
RESERVED_TESTS = (
    "tests/test_ae_sq1_external_evidence.py",
    "tests/test_ae_sq1_historical_task_digests.py",
    "tests/test_ae_sq1_slec.py",
    "tests/test_ae_sq1_corpus_contract.py",
    "tests/test_ae_sq1_evaluator.py",
    "tests/test_ae_sq1_run_index.py",
    "tests/test_run_ae_sq1_aq.py",
    "tests/test_check_ae_sq1_candidate.py",
    "tests/test_ae_sq1_as.py",
    "tests/test_ae_sq1_ac.py",
    "tests/test_ae_sq1_ah.py",
    "tests/test_ae_sq1_ar.py",
)

SQ1_POINTER_LINE = (
    "**Active successor plan:** `docs/exec-plans/active/ae-sq1.md` for AE-SQ1 "
    "only; `EXECPLAN.md` remains immutable predecessor terminal history"
)
POINTER_LINE = (
    "**Active successor plan:** `docs/exec-plans/active/ae-sq2.md` for AE-SQ2 "
    "only; AE-SQ1 and `EXECPLAN.md` remain immutable terminal history"
)
DECISION_LOG_FIELDS = (
    "decision_id",
    "repository",
    "foundation_id",
    "observed_change",
    "affected_decision",
    "decision_owner",
    "disposition_no_change_update_replace_retire",
    "implementation_or_test_delta",
    "claim_ceiling",
    "review_trigger",
    "date",
    "candidate_commit",
    "notes",
)
EXPECTED_LOG_ROW = {
    "decision_id": "AE-SQ1-F0-2026-08-10",
    "repository": "RLTree/agentic-engineering",
    "foundation_id": "current-2026-08-08",
    "observed_change": (
        "Owner authorized AE-SQ1 as a distinct successor after immutable "
        "predecessor terminal closeout; only terminal bits cross the boundary"
    ),
    "affected_decision": "active successor program authority",
    "decision_owner": "root conductor",
    "disposition_no_change_update_replace_retire": "update",
    "implementation_or_test_delta": (
        "Freeze docs/exec-plans/active/ae-sq1.md and "
        "evals/ae-sq1/program-authority.json before candidate, heldout, or model "
        "work; preserve predecessor Git bytes"
    ),
    "claim_ceiling": (
        "structural-program-authority-frozen only; no candidate, evaluation, "
        "runtime, host, field, release, publication, promotion, deletion, or "
        "migration claim"
    ),
    "review_trigger": (
        "F1 independent external-evidence authority or any proposed F0 semantic change"
    ),
    "date": "2026-08-10",
    "candidate_commit": BASE_COMMIT,
    "notes": (
        f"Plan raw SHA256 {F0_PLAN_RAW_SHA256}; predecessor tree {BASE_TREE}; base "
        "commit is historical custody, not a future AE-SQ1 commit; AE-SQ1 is not "
        "AQ10, H6, retry, resume, reopen, cure, or reinterpretation; all stage "
        "work remains HOLD"
    ),
}

EXPECTED_TERMINAL_LOG_FIELDS = {
    "decision_id": "AE-SQ1-AQ-AR-2026-08-11",
    "repository": "RLTree/agentic-engineering",
    "foundation_id": "current-2026-08-08",
    "affected_decision": "AE-SQ1 successor qualification",
    "decision_owner": "root conductor",
    "disposition_no_change_update_replace_retire": "retire",
    "candidate_commit": "0417fdd1174508fc0591be9a3e89263f25592b25",
}

EXPECTED_SQ2_LOG_ROW = {
    "decision_id": "AE-SQ2-F0-2026-08-12",
    "repository": "RLTree/agentic-engineering",
    "foundation_id": "current-2026-08-08",
    "observed_change": (
        "Owner authorized distinct AE-SQ2 after immutable AE-SQ1 terminal "
        "closeout, including a bounded diagnostic before repaired freeze and "
        "gated live qualification"
    ),
    "affected_decision": "active successor program authority",
    "decision_owner": "root conductor",
    "disposition_no_change_update_replace_retire": "update",
    "implementation_or_test_delta": (
        "Freeze docs/exec-plans/active/ae-sq2.md and "
        "evals/ae-sq2/program-authority.json; authorize D0-F6 in order with "
        "diagnostic 4, canary 4, batch 320, fresh 2 x 20 corpus only after F1, "
        "zero-model preflight, global AND, and pass-only routing"
    ),
    "claim_ceiling": (
        "Structural program authority and unexecuted owner authorization only; "
        "no diagnostic, corpus, candidate freeze, qualification, downstream, "
        "host, field, production, release, publication, promotion, deletion, or "
        "migration claim"
    ),
    "review_trigger": (
        "Closed SQ2-D0 diagnostic record or any proposed F0 semantic change"
    ),
    "date": "2026-08-12",
    "candidate_commit": SQ1_TERMINAL_COMMIT,
    "notes": (
        "Plan raw SHA256 "
        "21cba55af6067d9af1f934d2a58d964f2d7c11df5791ee9e510cf8ebb2fdaf9b; "
        "base tree 573f53baa839a3b088548a7e7ba2050003911a7a; AE-SQ1 tag "
        "ae-sq1-terminal-2026-08-11 remains immutable; AE-SQ2 is not retry, "
        "reopen, resume, H6, AQ10, cure, reinterpretation, or AE-SQ1 "
        "continuation; gpt-5.5 medium with no fallback is controlled "
        "configuration, not behavioral evidence; this F0 lane made zero live "
        "calls and authored zero corpus cases"
    ),
}


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def parse_manifest(raw: bytes | str) -> dict[str, Any]:
    text = raw.decode("utf-8") if type(raw) is bytes else raw
    value = json.loads(
        text,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_nonfinite,
    )
    if type(value) is not dict:
        raise AssertionError("program authority root must be an object")
    return value


FILE_SHAPE = {"role": str, "path": str, "blob": str, "raw_sha256": str}
PREREQUISITE_SHAPE = {
    "stage": str,
    "disposition": str,
    "imported_bit": str,
    "claim_expansion": bool,
}
FREEZE_SHAPE = {"id": str, "owner": str, "surface": str, "precedes": str}
LANE_SHAPE = {"lane": str, "owns": str, "forbidden": str}

MANIFEST_SHAPE: dict[str, Any] = {
    "schema_version": str,
    "program_id": str,
    "authority_status": str,
    "claim_ceiling": str,
    "owner_authorization": {
        "authorized": bool,
        "scope": str,
        "successor_kind": str,
        "not_semantics": [str],
        "successor_commit_binding": str,
        "provisional_noncanonical_drafts_may_coexist": bool,
        "provisional_drafts_confer_authority": bool,
        "candidate_authority_authorized": bool,
        "heldout_authoring_authorized": bool,
        "model_work_authorized": bool,
        "model_or_corpus_observation_authorized": bool,
        "downstream_staging_or_commit_authorized": bool,
        "external_action_authorized": bool,
    },
    "predecessor_terminal_history": {
        "commit": str,
        "tree": str,
        "custody_purpose": str,
        "permitted_imported_bits": [str],
        "forbidden_import_classes": [str],
        "non_isomorphism_inspection": {
            "permission": str,
            "purpose": str,
            "commit": str,
            "tree": str,
            "path": str,
            "blob": str,
            "raw_sha256": str,
            "mechanics_as_design_input": bool,
            "outcomes_as_input": bool,
        },
        "files": [FILE_SHAPE],
    },
    "active_plan": {
        "path": str,
        "raw_sha256": str,
        "successor_commit": str,
    },
    "imported_prerequisites": [PREREQUISITE_SHAPE],
    "stage_graph": {
        "ordered_stages": [str],
        "success_edges": [str],
        "blocking_failure_edges": [str],
        "later_stage_compensation": bool,
        "additional_active_stages_permitted": bool,
        "additional_active_edges_permitted": bool,
    },
    "freeze_points": [FREEZE_SHAPE],
    "ownership_lanes": [LANE_SHAPE],
    "namespace": {
        "artifact_root": str,
        "predecessor_root_write_permitted": bool,
        "draft_workspace_presence_confers_authority": bool,
        "f0_commit_may_include_reserved_paths": bool,
        "f0_files": [str],
        "reserved_artifacts": [str],
        "reserved_scripts": [str],
        "reserved_tests": [str],
    },
    "aq_contract": {
        "candidate": {
            "count": int,
            "fresh": bool,
            "materially_non_H4": bool,
            "sole_design_input": str,
            "predecessor_outcome_tuning_permitted": bool,
        },
        "mechanism": {
            "id": str,
            "kind": str,
            "calls_per_unit": int,
            "unique_child_contexts_per_unit": int,
            "sibling_state_visible": bool,
        },
        "heldout": {
            "split_count": int,
            "cases_per_split": int,
            "total_unique_cases": int,
            "independent_authors_required": bool,
            "candidate_and_evaluator_frozen_first": bool,
        },
        "presentations": {
            "conditions": [str],
            "presentations_per_case": int,
            "total_presentations": int,
            "calls_per_presentation": int,
            "total_heldout_calls": int,
        },
        "canary": {
            "units": int,
            "normal_calls": int,
            "absolute_calls_with_retry": int,
            "corpus_content_permitted": bool,
            "heldout_consumed": bool,
        },
        "consumption": {
            "trigger": str,
            "scope": str,
            "irreversible": bool,
            "status_after_trigger": str,
        },
        "retry": {
            "post_observation_retries": int,
            "pre_model_infrastructure_retries_max": int,
            "scope": str,
            "zero_completed_child_outputs_required": bool,
            "zero_semantic_child_observations_required": bool,
            "unchanged_bytes_required": bool,
            "launched_retry_calls_count": bool,
            "second_infrastructure_failure_route": str,
        },
        "reporting": {
            "result_count": int,
            "visibility": str,
            "subaggregate_disclosure_permitted": bool,
            "raw_disclosure_permitted": bool,
        },
        "global_and": {
            "operator": str,
            "condition_scope": str,
            "fail_values": [str],
            "compensation_permitted": bool,
        },
        "model": {
            "id": str,
            "reasoning_effort": str,
            "fallback_permitted": bool,
        },
    },
    "downstream_design": {
        "SQ1-AS": {
            "fresh_tasks": int,
            "conditions": [str],
            "automatic_routing_reexecuted": bool,
            "automatic_routing_authority": str,
            "base_calls_per_task_max": int,
            "residual_review_calls_per_task_max": int,
            "design_calls_max": int,
            "hard_ceiling": int,
        },
        "SQ1-AC": {
            "fresh_tasks": int,
            "conditions": [str],
            "base_calls_per_task_max": int,
            "residual_review_calls_per_task_max": int,
            "design_calls_max": int,
            "hard_ceiling": int,
        },
        "nonduplicative_successor_design": bool,
        "unused_margin_transfer_or_retry_permitted": bool,
    },
    "model_budget": {
        "SQ1-AQ_normal": int,
        "SQ1-AQ_absolute": int,
        "SQ1-AS_hard_ceiling": int,
        "SQ1-AC_hard_ceiling": int,
        "SQ1-AH_hard_ceiling": int,
        "SQ1-AF_hard_ceiling": int,
        "SQ1-AR_hard_ceiling": int,
        "normal_all_pass_ceiling": int,
        "absolute_all_program_ceiling": int,
        "unused_transfer_permitted": bool,
        "diagnostic_overrun_permitted": bool,
    },
    "stage_claims": {
        "SQ1-AQ": {"maximum": str, "production": bool, "release": bool},
        "SQ1-AS": {"maximum": str, "composition": bool, "field": bool},
        "SQ1-AC": {"maximum": str, "general_composition": bool, "field": bool},
        "SQ1-AH": {
            "environment": str,
            "passing_literal": str,
            "production_or_clean_host_proof": bool,
        },
        "SQ1-AF": {
            "default_literal": str,
            "separate_privacy_consent_envelope_authority_required": bool,
            "field_claim": bool,
        },
        "SQ1-AR": {
            "aggregation": str,
            "coordinates": [str],
            "public_action_authorized": bool,
        },
    },
    "forbidden_actions": [str],
    "acceptance": {
        "f0_status": str,
        "f0_next_state": str,
        "required_checks": [str],
        "next_authorized_transition": str,
    },
    "low_risk_substitutions": {
        "permitted_before_owning_freeze": [str],
        "forbidden_without_new_program": [str],
    },
}


def assert_shape(value: Any, shape: Any, label: str = "manifest") -> None:
    if type(shape) is dict:
        if type(value) is not dict:
            raise AssertionError(f"{label} must be an object")
        if tuple(value) != tuple(shape):
            raise AssertionError(f"{label} keys/order differ: {tuple(value)!r}")
        for key, child_shape in shape.items():
            assert_shape(value[key], child_shape, f"{label}.{key}")
        return
    if type(shape) is list:
        if type(value) is not list:
            raise AssertionError(f"{label} must be an array")
        if len(shape) != 1:
            raise AssertionError("test schema array must have one item shape")
        for index, item in enumerate(value):
            assert_shape(item, shape[0], f"{label}[{index}]")
        return
    if type(value) is not shape:
        raise AssertionError(
            f"{label} must be exactly {shape.__name__}, got {type(value).__name__}"
        )


def git_output(*args: str, text: bool = False) -> bytes | str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=text)


def git_bytes(commit: str, path: str) -> bytes:
    value = git_output("show", f"{commit}:{path}")
    if type(value) is not bytes:
        raise AssertionError("git show unexpectedly returned text")
    return value


def git_text(commit: str, path: str) -> str:
    value = git_output("show", f"{commit}:{path}", text=True)
    if type(value) is not str:
        raise AssertionError("git show unexpectedly returned bytes")
    return value


def raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def validate_manifest(document: dict[str, Any]) -> None:
    assert_shape(document, MANIFEST_SHAPE)
    if tuple(document) != TOP_LEVEL_KEYS:
        raise AssertionError("top-level order differs")
    expected_header = (
        "AE-SQ1-program-authority-v1",
        "AE-SQ1",
        "F0_STATIC_AUTHORITY_FROZEN",
        "structural-program-authority-frozen-only",
    )
    actual_header = tuple(document[key] for key in TOP_LEVEL_KEYS[:4])
    if actual_header != expected_header:
        raise AssertionError("authority header differs")

    authorization = document["owner_authorization"]
    expected_authorization = {
        "authorized": True,
        "scope": "local-static-authority-surfaces-only",
        "successor_kind": "distinct-owner-authorized-successor-program",
        "not_semantics": list(NOT_SEMANTICS),
        "successor_commit_binding": "ABSENT_NOT_SELF_BOUND",
        "provisional_noncanonical_drafts_may_coexist": True,
        "provisional_drafts_confer_authority": False,
        "candidate_authority_authorized": False,
        "heldout_authoring_authorized": False,
        "model_work_authorized": False,
        "model_or_corpus_observation_authorized": False,
        "downstream_staging_or_commit_authorized": False,
        "external_action_authorized": False,
    }
    if authorization != expected_authorization:
        raise AssertionError("owner authorization differs")

    history = document["predecessor_terminal_history"]
    if (history["commit"], history["tree"]) != (BASE_COMMIT, BASE_TREE):
        raise AssertionError("predecessor base differs")
    if history["custody_purpose"] != "immutable-history-verification-only":
        raise AssertionError("predecessor custody purpose differs")
    if tuple(history["permitted_imported_bits"]) != PERMITTED_TERMINAL_BITS:
        raise AssertionError("permitted predecessor bits differ")
    if tuple(history["forbidden_import_classes"]) != FORBIDDEN_IMPORT_CLASSES:
        raise AssertionError("forbidden import classes differ")
    if history["non_isomorphism_inspection"] != {
        "permission": "read-only-pinned-H4-protocol-inspection-only",
        "purpose": "prove-SLEC-1-material-non-isomorphism",
        "commit": "d6f9e6089e6e11f158a2d3bf4af717fc026548d4",
        "tree": "6b65ea1e125836c9ae684e869f1156e5750c7a0b",
        "path": "evals/foundation-v4/unresolved-decision-graph-protocol-v8.json",
        "blob": "5fe35b98dce5373d974d05ba3a29819605f5bc4f",
        "raw_sha256": "a145766c475de5ed1411bc86467a1a82c3cdaa18782b772ef00901238f590fd5",
        "mechanics_as_design_input": False,
        "outcomes_as_input": False,
    }:
        raise AssertionError("H4 non-isomorphism inspection boundary differs")
    file_rows = tuple(
        (row["role"], row["path"], row["blob"], row["raw_sha256"])
        for row in history["files"]
    )
    if file_rows != PREDECESSOR_FILES:
        raise AssertionError("predecessor file custody differs")

    if document["active_plan"] != {
        "path": "docs/exec-plans/active/ae-sq1.md",
        "raw_sha256": PLAN_RAW_SHA256,
        "successor_commit": "ABSENT_NOT_SELF_BOUND",
    }:
        raise AssertionError("active plan binding differs")
    expected_prerequisites = [
        {
            "stage": "A0",
            "disposition": "revalidated-imported-prerequisite-only",
            "imported_bit": "current-foundation-authority",
            "claim_expansion": False,
        },
        {
            "stage": "A1",
            "disposition": "revalidated-imported-prerequisite-only",
            "imported_bit": "exact-structural-package-identity",
            "claim_expansion": False,
        },
    ]
    if document["imported_prerequisites"] != expected_prerequisites:
        raise AssertionError("imported prerequisites differ")

    graph = document["stage_graph"]
    if tuple(graph["ordered_stages"]) != STAGES:
        raise AssertionError("stage order differs")
    if tuple(graph["success_edges"]) != SUCCESS_EDGES:
        raise AssertionError("success edges differ")
    if tuple(graph["blocking_failure_edges"]) != FAILURE_EDGES:
        raise AssertionError("blocking failure edges differ")
    if any(
        graph[key]
        for key in (
            "later_stage_compensation",
            "additional_active_stages_permitted",
            "additional_active_edges_permitted",
        )
    ):
        raise AssertionError("stage graph must be closed and noncompensatory")
    freeze_rows = tuple(
        (point["id"], point["owner"], point["surface"], point["precedes"])
        for point in document["freeze_points"]
    )
    if freeze_rows != FREEZE_ROWS:
        raise AssertionError("freeze points differ")
    lane_rows = tuple(
        (lane["lane"], lane["owns"], lane["forbidden"])
        for lane in document["ownership_lanes"]
    )
    if lane_rows != LANE_ROWS:
        raise AssertionError("ownership lanes differ")

    namespace = document["namespace"]
    if namespace["artifact_root"] != "evals/ae-sq1":
        raise AssertionError("artifact namespace differs")
    if namespace["predecessor_root_write_permitted"]:
        raise AssertionError("predecessor root writes must be forbidden")
    if namespace["draft_workspace_presence_confers_authority"]:
        raise AssertionError("a noncanonical draft cannot confer authority")
    if namespace["f0_commit_may_include_reserved_paths"]:
        raise AssertionError("F0 cannot commit a reserved downstream path")
    if tuple(namespace["f0_files"]) != F0_FILES:
        raise AssertionError("F0 file namespace differs")
    if tuple(namespace["reserved_artifacts"]) != RESERVED_ARTIFACTS:
        raise AssertionError("reserved artifact namespace differs")
    if tuple(namespace["reserved_scripts"]) != RESERVED_SCRIPTS:
        raise AssertionError("reserved script namespace differs")
    if tuple(namespace["reserved_tests"]) != RESERVED_TESTS:
        raise AssertionError("reserved test namespace differs")

    aq = document["aq_contract"]
    if aq["candidate"] != {
        "count": 1,
        "fresh": True,
        "materially_non_H4": True,
        "sole_design_input": "independent-external-evidence-frozen-at-F1",
        "predecessor_outcome_tuning_permitted": False,
    }:
        raise AssertionError("candidate contract differs")
    if aq["mechanism"] != {
        "id": "SLEC-1",
        "kind": "four-isolated-assessor-capsules-with-deterministic-parent-join",
        "calls_per_unit": 4,
        "unique_child_contexts_per_unit": 4,
        "sibling_state_visible": False,
    }:
        raise AssertionError("SLEC-1 mechanism differs")
    if aq["heldout"] != {
        "split_count": 2,
        "cases_per_split": 20,
        "total_unique_cases": 40,
        "independent_authors_required": True,
        "candidate_and_evaluator_frozen_first": True,
    }:
        raise AssertionError("heldout contract differs")
    if aq["presentations"] != {
        "conditions": ["current", "reduced"],
        "presentations_per_case": 2,
        "total_presentations": 80,
        "calls_per_presentation": 4,
        "total_heldout_calls": 320,
    }:
        raise AssertionError("presentation contract differs")
    if aq["canary"] != {
        "units": 1,
        "normal_calls": 4,
        "absolute_calls_with_retry": 8,
        "corpus_content_permitted": False,
        "heldout_consumed": False,
    }:
        raise AssertionError("non-corpus canary differs")
    if aq["consumption"] != {
        "trigger": "first-heldout-backed-model-invocation",
        "scope": "both-frozen-splits",
        "irreversible": True,
        "status_after_trigger": "NO_REPLAY",
    }:
        raise AssertionError("consumption/no-replay contract differs")
    if aq["retry"] != {
        "post_observation_retries": 0,
        "pre_model_infrastructure_retries_max": 1,
        "scope": "entire-four-call-non-corpus-canary-attempt-only",
        "zero_completed_child_outputs_required": True,
        "zero_semantic_child_observations_required": True,
        "unchanged_bytes_required": True,
        "launched_retry_calls_count": True,
        "second_infrastructure_failure_route": "SQ1-AR",
    }:
        raise AssertionError("retry contract differs")
    if aq["reporting"] != {
        "result_count": 1,
        "visibility": "candidate-bound-aggregate-only",
        "subaggregate_disclosure_permitted": False,
        "raw_disclosure_permitted": False,
    }:
        raise AssertionError("aggregate-only reporting differs")
    if aq["global_and"] != {
        "operator": "logical-AND",
        "condition_scope": "all-required-values-both-conditions",
        "fail_values": list(FAIL_VALUES),
        "compensation_permitted": False,
    }:
        raise AssertionError("global AND differs")
    if aq["model"] != {
        "id": "gpt-5.5",
        "reasoning_effort": "medium",
        "fallback_permitted": False,
    }:
        raise AssertionError("model contract differs")

    downstream = document["downstream_design"]
    if downstream["SQ1-AS"] != {
        "fresh_tasks": 12,
        "conditions": [
            "native-one-shot",
            "equal-budget-neutral-analysis-plus-fresh-builder",
            "current-explicit-specialist-advice-plus-fresh-builder",
            "reduced-explicit-specialist-advice-plus-fresh-builder",
        ],
        "automatic_routing_reexecuted": False,
        "automatic_routing_authority": "SQ1-AQ-only",
        "base_calls_per_task_max": 7,
        "residual_review_calls_per_task_max": 2,
        "design_calls_max": 108,
        "hard_ceiling": 156,
    }:
        raise AssertionError("AS nonduplicative design differs")
    if downstream["SQ1-AC"] != {
        "fresh_tasks": 8,
        "conditions": [
            "neutral-decomposition",
            "current-explicit-two-specialist-composition",
            "reduced-explicit-two-specialist-composition",
            "wrong-neighbor-negative-control",
        ],
        "base_calls_per_task_max": 10,
        "residual_review_calls_per_task_max": 2,
        "design_calls_max": 96,
        "hard_ceiling": 144,
    }:
        raise AssertionError("AC nonduplicative design differs")
    if not downstream["nonduplicative_successor_design"]:
        raise AssertionError("downstream design must be explicitly nonduplicative")
    if downstream["unused_margin_transfer_or_retry_permitted"]:
        raise AssertionError("unused downstream margin is not spendable")
    if downstream["SQ1-AS"]["design_calls_max"] != 12 * (7 + 2):
        raise AssertionError("AS design budget formula differs")
    if downstream["SQ1-AC"]["design_calls_max"] != 8 * (10 + 2):
        raise AssertionError("AC design budget formula differs")

    if document["model_budget"] != BUDGET:
        raise AssertionError("model budget differs")
    if BUDGET["SQ1-AQ_normal"] != 4 + 80 * 4:
        raise AssertionError("normal AQ budget formula differs")
    if BUDGET["SQ1-AQ_absolute"] != 8 + 80 * 4:
        raise AssertionError("absolute AQ budget formula differs")
    if BUDGET["normal_all_pass_ceiling"] != 324 + 156 + 144:
        raise AssertionError("normal all-pass budget formula differs")
    if BUDGET["absolute_all_program_ceiling"] != 328 + 156 + 144:
        raise AssertionError("absolute program budget formula differs")

    claims = document["stage_claims"]
    if tuple(claims) != STAGES:
        raise AssertionError("claim coordinates are not stage-separated")
    if claims["SQ1-AQ"] != {
        "maximum": "exact-candidate-aggregate-for-frozen-SLEC-1-envelope-only",
        "production": False,
        "release": False,
    }:
        raise AssertionError("AQ claim ceiling differs")
    if claims["SQ1-AS"] != {
        "maximum": "isolated-advice-value-on-frozen-representative-tasks-only",
        "composition": False,
        "field": False,
    }:
        raise AssertionError("AS claim ceiling differs")
    if claims["SQ1-AC"] != {
        "maximum": "composition-on-frozen-exact-two-decision-tasks-only",
        "general_composition": False,
        "field": False,
    }:
        raise AssertionError("AC claim ceiling differs")
    if claims["SQ1-AH"] != {
        "environment": "offline-unprivileged-disposable-home",
        "passing_literal": "NARROW_PASS",
        "production_or_clean_host_proof": False,
    }:
        raise AssertionError("AH claim ceiling differs")
    if claims["SQ1-AF"] != {
        "default_literal": "OMITTED_NO_FIELD_CLAIM",
        "separate_privacy_consent_envelope_authority_required": True,
        "field_claim": False,
    }:
        raise AssertionError("AF omission differs")
    if tuple(claims["SQ1-AR"]["coordinates"]) != AR_COORDINATES:
        raise AssertionError("AR claim vector differs")
    if claims["SQ1-AR"]["aggregation"] != "forbidden-separated-vector-only":
        raise AssertionError("AR aggregation must be forbidden")
    if claims["SQ1-AR"]["public_action_authorized"]:
        raise AssertionError("AR cannot authorize a public action")
    if tuple(document["forbidden_actions"]) != FORBIDDEN_ACTIONS:
        raise AssertionError("forbidden actions differ")
    if document["acceptance"]["f0_status"] != ("structural-program-authority-frozen"):
        raise AssertionError("F0 status differs")
    if document["acceptance"]["f0_next_state"] != "HOLD_F1_AND_ALL_EXECUTION":
        raise AssertionError("F0 next state differs")
    if document["acceptance"]["required_checks"] != [
        "strict-duplicate-key-type-order-closure",
        "predecessor-bytes-at-base",
        "plan-raw-digest",
        "stage-order-budget-no-replay-claims",
        "pointer-and-single-log-row",
        "mutation-reds",
        "no-disallowed-imports",
        "focused-tests",
        "foundation-tests",
        "ruff-no-cache",
        "json-parse",
        "diff-and-status",
    ]:
        raise AssertionError("F0 required checks differ")
    if document["acceptance"]["next_authorized_transition"] != (
        "none-until-F1-independent-external-evidence-authority"
    ):
        raise AssertionError("next authorized transition differs")

    substitutions = document["low_risk_substitutions"]
    if substitutions["permitted_before_owning_freeze"] != [
        "temporary-directory-or-disposable-home-path",
        "deterministic-JSON-serialization-implementation",
        "local-process-runner-implementation",
        "semantically-identical-deterministic-schedule-seed",
        "task-wording-preserving-frozen-AS-or-AC-semantics",
        "test-helper-organization-or-internal-function-name",
        "equivalent-offline-AH-fixture",
    ]:
        raise AssertionError("low-risk substitutions differ")
    if substitutions["forbidden_without_new_program"] != [
        "predecessor-input",
        "candidate-mechanism",
        "evidence-independence-rule",
        "model-or-reasoning-or-fallback",
        "candidate-or-case-or-presentation-or-call-count",
        "budget",
        "evaluator-formula-or-threshold-or-aggregation",
        "stage-or-edge",
        "retry-or-no-replay-or-consumption-point",
        "isolation-or-permission-or-network",
        "AS-or-AC-task-count-condition-or-routing-authority",
        "claim-ceiling-or-AF-omission-or-forbidden-action",
    ]:
        raise AssertionError("non-substitutable rules differ")


class AeSq1ProgramAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw_manifest = MANIFEST_PATH.read_bytes()
        cls.manifest = parse_manifest(cls.raw_manifest)
        cls.plan_raw = PLAN_PATH.read_bytes()

    def test_manifest_is_strict_closed_ordered_and_valid(self) -> None:
        validate_manifest(self.manifest)

    def test_parser_rejects_duplicate_keys_nonfinite_and_non_object_roots(self) -> None:
        for raw in (
            '{"program_id":"AE-SQ1","program_id":"other"}',
            '{"value":NaN}',
            '{"value":Infinity}',
            '{"value":-Infinity}',
            "[]",
        ):
            with self.subTest(raw=raw), self.assertRaises((ValueError, AssertionError)):
                parse_manifest(raw)

    def test_predecessor_commit_tree_blobs_and_raw_bytes_reproduce(self) -> None:
        commit = git_output(
            "rev-parse", "--verify", f"{BASE_COMMIT}^{{commit}}", text=True
        )
        tree = git_output("rev-parse", "--verify", f"{BASE_COMMIT}^{{tree}}", text=True)
        self.assertEqual(BASE_COMMIT, str(commit).strip())
        self.assertEqual(BASE_TREE, str(tree).strip())

        for _, path, expected_blob, expected_sha256 in PREDECESSOR_FILES:
            with self.subTest(path=path):
                raw = git_bytes(BASE_COMMIT, path)
                blob = git_output("rev-parse", f"{BASE_COMMIT}:{path}", text=True)
                self.assertEqual(expected_blob, str(blob).strip())
                self.assertEqual(expected_sha256, raw_sha256(raw))
                candidate = (ROOT / path).resolve()
                self.assertTrue(candidate.is_relative_to(ROOT.resolve()))

        inspection = self.manifest["predecessor_terminal_history"][
            "non_isomorphism_inspection"
        ]
        inspection_tree = git_output(
            "rev-parse", "--verify", f"{inspection['commit']}^{{tree}}", text=True
        )
        inspection_blob = git_output(
            "rev-parse",
            f"{inspection['commit']}:{inspection['path']}",
            text=True,
        )
        inspection_raw = git_bytes(inspection["commit"], inspection["path"])
        self.assertEqual(inspection["tree"], str(inspection_tree).strip())
        self.assertEqual(inspection["blob"], str(inspection_blob).strip())
        self.assertEqual(inspection["raw_sha256"], raw_sha256(inspection_raw))

        self.assertEqual(
            git_bytes(BASE_COMMIT, "EXECPLAN.md"),
            (ROOT / "EXECPLAN.md").read_bytes(),
            "predecessor terminal plan changed in the workspace",
        )

    def test_plan_raw_digest_and_required_contract_language(self) -> None:
        self.assertEqual(PLAN_RAW_SHA256, raw_sha256(self.plan_raw))
        text = self.plan_raw.decode("utf-8")
        for required in (
            "distinct successor program",
            "not AQ10, H6, a retry, a resume, a reopen, a cure, or a",
            "reinterpretation",
            "revalidated imported prerequisites only",
            "SQ1-AQ -> SQ1-AS -> SQ1-AC -> SQ1-AH -> SQ1-AF -> SQ1-AR",
            "one four-capsule unit",
            "four unique child contexts",
            "one non-corpus canary unit",
            "completed child outputs and zero semantic child observations",
            "328 AQ and 628 program absolute ceilings",
            "first heldout-backed model invocation consumes both frozen splits",
            "There is no post-observation retry",
            "aggregate result may leave evaluator custody",
            "Missing, skipped, undefined, non-finite",
            "`gpt-5.5`",
            "`medium`",
            "NARROW_PASS",
            "OMITTED_NO_FIELD_CLAIM",
            "Automatic routing is not rerun in AS",
            "12 x (7 + 2) = 108",
            "8 x (10 + 2) = 96",
            "wrong-neighbor negative control",
            "No AE-SQ1 artifact may be",
            "No closeout state authorizes release or external action",
        ):
            self.assertIn(required, text)
        for freeze_id in FREEZE_IDS:
            self.assertIn(f"| {freeze_id} |", text)
        self.assertNotIn(" 81 ", text)
        self.assertNotIn(" 381 ", text)

    def test_pointer_is_the_only_foundation_change(self) -> None:
        base = git_text(
            SQ1_TERMINAL_COMMIT,
            "docs/foundations/current-2026-08-08.md",
        )
        self.assertEqual(1, base.count(SQ1_POINTER_LINE))
        expected = base.replace(SQ1_POINTER_LINE, POINTER_LINE, 1)
        self.assertEqual(expected, FOUNDATION_PATH.read_text(encoding="utf-8"))

    def test_decision_log_has_exactly_one_appended_row(self) -> None:
        base = git_bytes(SQ1_TERMINAL_COMMIT, "docs/foundations/decision-log.csv")
        current = DECISION_LOG_PATH.read_bytes()
        self.assertTrue(current.startswith(base))
        suffix = current[len(base) :]
        self.assertTrue(suffix.endswith(b"\n"))
        self.assertEqual(1, len(suffix.splitlines()))

        base_reader = csv.DictReader(io.StringIO(base.decode("utf-8")))
        current_reader = csv.DictReader(io.StringIO(current.decode("utf-8")))
        self.assertEqual(DECISION_LOG_FIELDS, tuple(base_reader.fieldnames or ()))
        self.assertEqual(DECISION_LOG_FIELDS, tuple(current_reader.fieldnames or ()))
        base_rows = list(base_reader)
        current_rows = list(current_reader)
        self.assertEqual(base_rows, current_rows[:-1])
        self.assertEqual(EXPECTED_LOG_ROW, base_rows[-2])
        for key, expected in EXPECTED_TERMINAL_LOG_FIELDS.items():
            self.assertEqual(expected, base_rows[-1][key], key)
        self.assertIn(
            "DO_NOT_RELEASE_OR_PROMOTE",
            base_rows[-1]["implementation_or_test_delta"],
        )
        self.assertIn("heldout corpus unconsumed", base_rows[-1]["notes"])
        self.assertEqual(EXPECTED_SQ2_LOG_ROW, current_rows[-1])
        self.assertEqual(
            1,
            sum(row["decision_id"] == "AE-SQ1-F0-2026-08-10" for row in current_rows),
        )
        self.assertEqual(
            1,
            sum(row["decision_id"] == "AE-SQ2-F0-2026-08-12" for row in current_rows),
        )

    def test_f0_namespace_reserves_but_does_not_authorize_future_files(self) -> None:
        namespace = self.manifest["namespace"]
        self.assertFalse(namespace["draft_workspace_presence_confers_authority"])
        self.assertFalse(namespace["f0_commit_may_include_reserved_paths"])
        for relative in namespace["f0_files"]:
            self.assertTrue((ROOT / relative).is_file(), relative)

        reserved = {
            relative
            for group in ("reserved_artifacts", "reserved_scripts", "reserved_tests")
            for relative in namespace[group]
        }
        self.assertEqual(
            len(reserved),
            sum(
                len(namespace[group])
                for group in (
                    "reserved_artifacts",
                    "reserved_scripts",
                    "reserved_tests",
                )
            ),
            "reserved paths must be unique",
        )
        base_names = git_output("ls-tree", "-r", "--name-only", BASE_COMMIT, text=True)
        self.assertTrue(reserved.isdisjoint(str(base_names).splitlines()))
        staged_names = git_output("diff", "--cached", "--name-only", text=True)
        self.assertTrue(reserved.isdisjoint(str(staged_names).splitlines()))
        self.assertTrue(
            all(
                path.startswith("evals/ae-sq1/")
                for path in reserved
                if path.startswith("evals/")
            )
        )

    def test_no_disallowed_predecessor_imports(self) -> None:
        history = self.manifest["predecessor_terminal_history"]
        self.assertEqual(
            PERMITTED_TERMINAL_BITS, tuple(history["permitted_imported_bits"])
        )
        self.assertEqual(
            FORBIDDEN_IMPORT_CLASSES,
            tuple(history["forbidden_import_classes"]),
        )
        self.assertEqual(
            "independent-external-evidence-frozen-at-F1",
            self.manifest["aq_contract"]["candidate"]["sole_design_input"],
        )
        combined = self.raw_manifest + self.plan_raw
        for forbidden_prior_detail in (
            b"AQ7",
            b"AQ8",
            b"H1/",
            b"H2/",
            b"H3/",
            b"CI-1",
            b"946f63a9e9f8c3d461e92f019b1e96ff",
            b"TP 37",
            b"FP 1",
            b"FN 1",
            b"corpus J",
        ):
            self.assertNotIn(forbidden_prior_detail, combined)

    def test_contract_mutation_reds(self) -> None:
        mutations: list[tuple[str, Any]] = []

        missing = copy.deepcopy(self.manifest)
        del missing["claim_ceiling"]
        mutations.append(("missing top-level key", missing))

        extra = copy.deepcopy(self.manifest)
        extra["extra"] = False
        mutations.append(("extra top-level key", extra))

        reordered = copy.deepcopy(self.manifest)
        value = reordered.pop("schema_version")
        reordered["schema_version"] = value
        mutations.append(("reordered top-level key", reordered))

        wrong_type = copy.deepcopy(self.manifest)
        wrong_type["model_budget"]["SQ1-AQ"] = True
        mutations.append(("boolean budget", wrong_type))

        wrong_base = copy.deepcopy(self.manifest)
        wrong_base["predecessor_terminal_history"]["tree"] = "0" * 40
        mutations.append(("wrong predecessor tree", wrong_base))

        wrong_blob = copy.deepcopy(self.manifest)
        wrong_blob["predecessor_terminal_history"]["files"][0]["blob"] = "0" * 40
        mutations.append(("wrong predecessor blob", wrong_blob))

        wrong_plan = copy.deepcopy(self.manifest)
        wrong_plan["active_plan"]["raw_sha256"] = "0" * 64
        mutations.append(("wrong plan digest", wrong_plan))

        self_bound = copy.deepcopy(self.manifest)
        self_bound["active_plan"]["successor_commit"] = "1" * 40
        mutations.append(("future self-binding", self_bound))

        wrong_stages = copy.deepcopy(self.manifest)
        wrong_stages["stage_graph"]["ordered_stages"][0:2] = ["SQ1-AS", "SQ1-AQ"]
        mutations.append(("wrong stage order", wrong_stages))

        compensation = copy.deepcopy(self.manifest)
        compensation["stage_graph"]["later_stage_compensation"] = True
        mutations.append(("later-stage compensation", compensation))

        wrong_freeze = copy.deepcopy(self.manifest)
        wrong_freeze["freeze_points"][3]["id"] = "F4"
        mutations.append(("duplicate freeze", wrong_freeze))

        wrong_candidate = copy.deepcopy(self.manifest)
        wrong_candidate["aq_contract"]["candidate"]["count"] = 2
        mutations.append(("second candidate", wrong_candidate))

        wrong_contexts = copy.deepcopy(self.manifest)
        wrong_contexts["aq_contract"]["mechanism"]["unique_child_contexts_per_unit"] = 1
        mutations.append(("shared child context", wrong_contexts))

        wrong_canary = copy.deepcopy(self.manifest)
        wrong_canary["aq_contract"]["canary"]["normal_calls"] = 1
        mutations.append(("one-call canary", wrong_canary))

        replay = copy.deepcopy(self.manifest)
        replay["aq_contract"]["consumption"]["status_after_trigger"] = "REPLAY"
        mutations.append(("corpus replay", replay))

        post_retry = copy.deepcopy(self.manifest)
        post_retry["aq_contract"]["retry"]["post_observation_retries"] = 1
        mutations.append(("post-observation retry", post_retry))

        partial_reporting = copy.deepcopy(self.manifest)
        partial_reporting["aq_contract"]["reporting"][
            "subaggregate_disclosure_permitted"
        ] = True
        mutations.append(("subaggregate disclosure", partial_reporting))

        missing_fail_open = copy.deepcopy(self.manifest)
        missing_fail_open["aq_contract"]["global_and"]["fail_values"].remove("missing")
        mutations.append(("missing no longer fails", missing_fail_open))

        fallback = copy.deepcopy(self.manifest)
        fallback["aq_contract"]["model"]["fallback_permitted"] = True
        mutations.append(("model fallback", fallback))

        wrong_budget = copy.deepcopy(self.manifest)
        wrong_budget["model_budget"]["SQ1-AQ_normal"] = 81
        mutations.append(("obsolete AQ budget", wrong_budget))

        wrong_total = copy.deepcopy(self.manifest)
        wrong_total["model_budget"]["normal_all_pass_ceiling"] = 381
        mutations.append(("obsolete total budget", wrong_total))

        rerun_routing = copy.deepcopy(self.manifest)
        rerun_routing["downstream_design"]["SQ1-AS"]["automatic_routing_reexecuted"] = (
            True
        )
        mutations.append(("AS routing rerun", rerun_routing))

        wrong_as_condition = copy.deepcopy(self.manifest)
        wrong_as_condition["downstream_design"]["SQ1-AS"]["conditions"].pop()
        mutations.append(("missing AS condition", wrong_as_condition))

        wrong_ac_condition = copy.deepcopy(self.manifest)
        wrong_ac_condition["downstream_design"]["SQ1-AC"]["conditions"][-1] = (
            "no-negative-control"
        )
        mutations.append(("wrong AC negative control", wrong_ac_condition))

        clean_host_claim = copy.deepcopy(self.manifest)
        clean_host_claim["stage_claims"]["SQ1-AH"]["production_or_clean_host_proof"] = (
            True
        )
        mutations.append(("clean-host claim", clean_host_claim))

        field_claim = copy.deepcopy(self.manifest)
        field_claim["stage_claims"]["SQ1-AF"]["field_claim"] = True
        mutations.append(("field claim", field_claim))

        aggregate_claim = copy.deepcopy(self.manifest)
        aggregate_claim["stage_claims"]["SQ1-AR"]["aggregation"] = "allowed"
        mutations.append(("aggregate claim vector", aggregate_claim))

        public_action = copy.deepcopy(self.manifest)
        public_action["stage_claims"]["SQ1-AR"]["public_action_authorized"] = True
        mutations.append(("public action", public_action))

        for label, mutation in mutations:
            with self.subTest(label=label), self.assertRaises(AssertionError):
                validate_manifest(mutation)


if __name__ == "__main__":
    unittest.main()
