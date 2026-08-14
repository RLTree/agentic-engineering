#!/usr/bin/env python3
"""Strict two-commit byte-custody checker for AE-SQ8-SLEC-8.

SQ8-F1A is exactly one implementation commit after the frozen F0 authority.
SQ8-F1B is exactly one manifest-only child commit.  This module treats Git
objects, rather than the mutable worktree, as the source of truth and can also
require the live checkout to match every frozen byte before execution.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "AE-SQ8"
CANDIDATE_ID = "AE-SQ8-SLEC-8"
MECHANISM_ID = "SLEC-8"
AUTHORITY_COMMIT = "342f923607bd45ecff7a670b1b939decea4676cf"
AUTHORITY_PATH = "evals/ae-sq8/program-authority.json"
DIAGNOSTIC_COMMIT = "e2562ca4da5f3dc14fb07c1522f911e2dfe4334d"
DIAGNOSTIC_PATH = "evals/ae-sq2/d0/diagnostic-record.json"
DIAGNOSTIC_SCHEMA_PATH = "evals/ae-sq2/d0/diagnostic-schema.json"
DIAGNOSTIC_AUTHORITY_PATH = "evals/ae-sq2/d0/diagnostic-authority.json"
FREEZE_PATH = "evals/ae-sq8/f1/repaired-freeze.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
PLACEHOLDER = re.compile(
    r"(?:UNBOUND|PLACEHOLDER|TBD|TO[-_ ]?BE[-_ ]?SET)", re.IGNORECASE
)

ROLE_PATHS = (
    ("candidate_authority", "evals/ae-sq8/f1/slec8-authority.json"),
    ("resolver_and_local_semantic_validator", "scripts/resolve_ae_sq8_slec.py"),
    ("capsule_schema", "evals/ae-sq8/f1/slec8-capsule-schema.json"),
    (
        "semantic_capsule_schema",
        "evals/ae-sq8/f1/slec8-semantic-capsule-schema.json",
    ),
    ("resolution_schema", "evals/ae-sq8/f1/slec8-resolution-schema.json"),
    ("reference_policy", "evals/ae-sq8/f1/slec8-reference-policy.json"),
    ("corpus_schema", "evals/ae-sq8/f1/corpus-schema.json"),
    ("gates", "evals/ae-sq8/f1/gates.json"),
    ("metrics", "evals/ae-sq8/f1/metrics.json"),
    ("evaluator_schema", "evals/ae-sq8/f1/evaluator-schema.json"),
    (
        "corpus_validator_and_expected_authority_helper",
        "scripts/validate_ae_sq8_corpus.py",
    ),
    ("scorer", "scripts/score_ae_sq8_aq.py"),
    ("runner", "scripts/run_ae_sq8_aq.py"),
    ("run_index", "scripts/ae_sq8_run_index.py"),
    ("candidate_checker", "scripts/check_ae_sq8_candidate.py"),
    ("run_manifest_schema", "evals/ae-sq8/f1/run-manifest-schema.json"),
    ("preflight_schema", "evals/ae-sq8/f1/preflight-schema.json"),
    ("result_schema", "evals/ae-sq8/f1/result-schema.json"),
    (
        "historical_digest_test",
        "tests/test_ae_sq8_historical_task_digests.py",
    ),
    ("slec_test", "tests/test_ae_sq8_slec.py"),
    ("provider_schema_test", "tests/test_ae_sq8_provider_schema.py"),
    ("corpus_contract_test", "tests/test_ae_sq8_corpus_contract.py"),
    ("evaluator_test", "tests/test_ae_sq8_evaluator.py"),
    ("run_index_test", "tests/test_ae_sq8_run_index.py"),
    ("candidate_checker_test", "tests/test_check_ae_sq8_candidate.py"),
    ("runner_test", "tests/test_run_ae_sq8_aq.py"),
    (
        "author_template_gate_schema",
        "evals/ae-sq8/f1/author-template-gate-schema.json",
    ),
    ("author_template_builder", "scripts/build_ae_sq8_author_template.py"),
    ("author_template_test", "tests/test_ae_sq8_author_template.py"),
    ("handoff_schema", "evals/ae-sq8/f1/handoff-schema.json"),
    (
        "terminal_decision_schema",
        "evals/ae-sq8/f1/terminal-decision-schema.json",
    ),
)
ROLE_ORDER = tuple(role for role, _path in ROLE_PATHS)
JSON_ROLES = frozenset(role for role, path in ROLE_PATHS if path.endswith(".json"))
EXPECTED_FORMULA_ORDER = (
    "capsule_local_need_accuracy",
    "capsule_reference_need_accuracy",
    "selected_precision",
    "selected_recall",
    "exact_selected_set",
    "abstention_specificity",
    "broad_over_selection",
    "one_decision_stacking",
    "exactly_two_exact_set",
    "cap_abstention",
    "explicit_invocation",
    "must_not_select",
    "anchor_grounding",
    "reference_bundle_correctness",
    "payload_cap_violations",
    "implicit_effect_claim_tool_events",
    "semantic_schema_order",
    "resolver_parity",
    "presentations_80_of_80",
    "unique_capsule_contexts_320",
    "binding_schedule_packet_parity",
    "invocation_count_320",
    "runner_local_raw_persistence",
    "heldout_outcome_use",
)
DIAGNOSTIC_PROBE_ORDER = ("p0", "p1", "p2", "p3")
DIAGNOSTIC_TOP_LEVEL_KEYS = (
    "diagnostic_id",
    "mode",
    "status",
    "claim_ceiling",
    "authority_sha256",
    "diagnostic_schema_sha256",
    "input_schema",
    "cli",
    "model",
    "reasoning_effort",
    "calls_started",
    "calls_completed",
    "classification_counts",
    "usage",
    "calls",
    "aggregate_sha256",
    "record_sha256",
)
F1A_FORBIDDEN_PATHS = frozenset(
    {
        FREEZE_PATH,
        "evals/ae-sq8/f1/author-template-gate.json",
        "evals/ae-sq8/f2/run-manifest.json",
        "evals/ae-sq8/f3/preflight.json",
        "evals/ae-sq8/f6/aggregate-result.json",
        "evals/ae-sq8/as/handoff.json",
        "evals/ae-sq8/ar/terminal-decision.json",
    }
)

SQ7_F1A_COMMIT = "1613d46d8fae71259979371717dd567de17ffded"
SQ7_ROLE_PATHS = tuple(
    path.replace("ae-sq8", "ae-sq7")
    .replace("ae_sq8", "ae_sq7")
    .replace("slec8", "slec7")
    for _role, path in ROLE_PATHS
)
HISTORICAL_BINDING = {
    "commit": "3762efae80ead1461d973b4737c5dcab6bae026a",
    "tree": "6a071b4ee33246cc2ef448cf4d574f51abc89348",
    "path": "evals/ae-sq4/f1/historical-task-digests.json",
    "blob": "6af74b660a9cf8fb04cde70abd527a88307f8cc3",
    "raw_sha256": "0e49a967d9a59021c0f1aa5fc8d80fd53fdf3ab1885925b0d86f1e8c4f9dc157",
    "content_kind": "digest-only-no-task-text",
}


class CandidateError(ValueError):
    """Frozen candidate custody is missing, open, or byte-drifted."""


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise CandidateError("value is not canonical finite JSON") from error


def _closed_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def closed_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_closed_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise CandidateError(f"{label} is not closed finite JSON") from error
    if not isinstance(value, dict):
        raise CandidateError(f"{label} is not a JSON object")
    return value


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git(root: Path, args: Sequence[str]) -> bytes:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
        ).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise CandidateError("required Git custody object is unavailable") from error


def _exact_commit(root: Path, value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX40.fullmatch(value) is None:
        raise CandidateError(f"{label} is not an exact commit SHA")
    resolved = (
        _git(root, ["rev-parse", "--verify", f"{value}^{{commit}}"]).decode().strip()
    )
    if resolved != value:
        raise CandidateError(f"{label} is not exact")
    return resolved


def _tree(root: Path, commit: str) -> str:
    value = _git(root, ["rev-parse", "--verify", f"{commit}^{{tree}}"]).decode().strip()
    if HEX40.fullmatch(value) is None:
        raise CandidateError("commit tree is unavailable")
    return value


def _show(root: Path, commit: str, path: str) -> bytes:
    safe = Path(path)
    if safe.is_absolute() or ".." in safe.parts or not path:
        raise CandidateError("custody path escaped repository")
    return _git(root, ["show", f"{commit}:{path}"])


def _blob(root: Path, commit: str, path: str) -> str:
    value = _git(root, ["rev-parse", f"{commit}:{path}"]).decode().strip()
    if HEX40.fullmatch(value) is None:
        raise CandidateError("role blob is unavailable")
    return value


def _require_regular_blob(root: Path, commit: str, path: str, blob: str) -> None:
    row = _git(root, ["ls-tree", commit, "--", path]).decode("utf-8", "strict")
    fields = row.rstrip("\n").split(None, 3)
    if (
        len(fields) != 4
        or fields[0] != "100644"
        or fields[1] != "blob"
        or fields[2] != blob
        or fields[3] != path
    ):
        raise CandidateError(f"role is not an exact 100644 regular blob: {path}")


def _parents(root: Path, commit: str) -> tuple[str, ...]:
    fields = _git(root, ["rev-list", "--parents", "-n", "1", commit]).decode().split()
    return tuple(fields[1:])


def _changed_paths(root: Path, parent: str, child: str) -> tuple[str, ...]:
    raw = _git(
        root, ["diff-tree", "--no-commit-id", "--name-only", "-r", parent, child]
    )
    return tuple(item for item in raw.decode().splitlines() if item)


def _reachable_f1b_children(root: Path, f1a: str) -> tuple[str, ...]:
    """Find every ref-reachable manifest-only child of this exact F1A."""
    commits = _git(root, ["rev-list", "--all"]).decode().splitlines()
    result = []
    for commit in commits:
        if _parents(root, commit) == (f1a,) and _changed_paths(root, f1a, commit) == (
            FREEZE_PATH,
        ):
            result.append(commit)
    return tuple(sorted(result))


def _has_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return PLACEHOLDER.search(value) is not None
    if isinstance(value, list):
        return any(_has_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(
            _has_placeholder(key) or _has_placeholder(item)
            for key, item in value.items()
        )
    return False


def _sealed_path(value: Any, *, expected_path: str, label: str) -> dict[str, str]:
    keys = {"commit", "tree", "path", "blob", "sha256"}
    if (
        not isinstance(value, dict)
        or set(value) != keys
        or value.get("path") != expected_path
    ):
        raise CandidateError(f"{label} binding is not exactly closed")
    for key in ("commit", "tree", "blob"):
        if not isinstance(value.get(key), str) or HEX40.fullmatch(value[key]) is None:
            raise CandidateError(f"{label} Git identity is invalid")
    if (
        not isinstance(value.get("sha256"), str)
        or HEX64.fullmatch(value["sha256"]) is None
    ):
        raise CandidateError(f"{label} SHA-256 is invalid")
    return dict(value)


def _validate_freeze(value: Any) -> dict[str, Any]:
    top = {
        "schema_version",
        "program_id",
        "candidate_id",
        "mechanism_id",
        "authority_bindings",
        "implementation_freeze",
        "role_order",
        "files",
        "runtime",
        "qualification",
        "durable_state",
        "privacy",
    }
    if not isinstance(value, dict) or set(value) != top or _has_placeholder(value):
        raise CandidateError("F1B freeze is open or unresolved")
    if (
        value["schema_version"] != "ae-sq8-repaired-freeze-v1"
        or value["program_id"] != PROGRAM_ID
        or value["candidate_id"] != CANDIDATE_ID
        or value["mechanism_id"] != MECHANISM_ID
    ):
        raise CandidateError("F1B freeze identity drift")
    authorities = value["authority_bindings"]
    if not isinstance(authorities, dict) or set(authorities) != {
        "program_authority",
        "bounded_sq2_diagnosis",
    }:
        raise CandidateError("F1B authority bindings are not closed")
    program = _sealed_path(
        authorities["program_authority"],
        expected_path=AUTHORITY_PATH,
        label="program authority",
    )
    diagnosis = _sealed_path(
        authorities["bounded_sq2_diagnosis"],
        expected_path=DIAGNOSTIC_PATH,
        label="bounded SQ2 diagnosis",
    )
    if (
        program["commit"] != AUTHORITY_COMMIT
        or diagnosis["commit"] != DIAGNOSTIC_COMMIT
    ):
        raise CandidateError("F1B earlier authority commit drift")
    freeze = value["implementation_freeze"]
    if (
        not isinstance(freeze, dict)
        or set(freeze) != {"commit", "tree"}
        or not isinstance(freeze.get("commit"), str)
        or HEX40.fullmatch(freeze["commit"]) is None
        or not isinstance(freeze.get("tree"), str)
        or HEX40.fullmatch(freeze["tree"]) is None
    ):
        raise CandidateError("F1A implementation freeze is unresolved")
    if value["role_order"] != list(ROLE_ORDER):
        raise CandidateError("F1A role order drift")
    files = value["files"]
    if not isinstance(files, list) or len(files) != len(ROLE_PATHS):
        raise CandidateError("F1A role ledger is incomplete")
    for row, (role, path) in zip(files, ROLE_PATHS, strict=True):
        if (
            not isinstance(row, dict)
            or set(row) != {"role", "path", "blob", "sha256"}
            or row.get("role") != role
            or row.get("path") != path
            or not isinstance(row.get("blob"), str)
            or HEX40.fullmatch(row["blob"]) is None
            or not isinstance(row.get("sha256"), str)
            or HEX64.fullmatch(row["sha256"]) is None
        ):
            raise CandidateError("F1A role binding is incomplete or reordered")
    if value["runtime"] != {
        "cli": {
            "id": "codex-cli",
            "version": "codex-cli 0.147.0",
            "sha256": "19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37",
        },
        "model": "gpt-5.5",
        "reasoning": "medium",
        "fallback": False,
        "sandbox": "read-only",
        "approval_policy": "never",
        "ephemeral": True,
        "strict_isolation": True,
    }:
        raise CandidateError("F1B runtime contract drift")
    if value["qualification"] != {
        "f3_preflight_attempts": 1,
        "f3_model_calls": 0,
        "canary_calls": 4,
        "conditional_batch_presentations": 80,
        "calls_per_presentation": 4,
        "conditional_batch_calls": 320,
        "hard_call_ceiling": 324,
        "retry_calls": 0,
        "same_process_canary_then_batch": True,
        "standalone_canary_or_resume": False,
        "global_and": True,
    }:
        raise CandidateError("F1B qualification contract drift")
    if value["durable_state"] != {
        "directory": ".git-common-dir/.ae-sq8-one-shot",
        "path": ".git-common-dir/.ae-sq8-one-shot/state.json",
        "schema_version": "ae-sq8-one-shot-run-index-v1",
        "top_level_keys": [
            "binding",
            "custody_key",
            "program_id",
            "record_sha256",
            "schema_version",
            "state_sha256",
            "status",
        ],
        "binding_keys": [
            "corpus_manifest_sha256",
            "f1_freeze_sha256",
            "preflight_record_sha256",
            "program_authority_sha256",
            "run_manifest_sha256",
        ],
        "statuses": ["claimed", "completed", "invalid"],
        "claim_before_first_canary_child": True,
        "crash_is_terminal": True,
        "reset_delete_retry_reopen_or_replacement": False,
    }:
        raise CandidateError("F1B durable-state contract drift")
    if value["privacy"] != {
        "raw_persistence": False,
        "subaggregate_persistence": False,
        "aggregate_only_projection": True,
        "private_runtime_snapshot": True,
        "private_child_tmp_cleanup_required": True,
    }:
        raise CandidateError("F1B privacy contract drift")
    return value


def _walk_provider_schema(value: Any) -> None:
    allowed = {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "description",
        "minItems",
        "maxItems",
        "$defs",
        "$ref",
    }
    if not isinstance(value, dict) or any(key not in allowed for key in value):
        raise CandidateError("provider schema uses a keyword outside the frozen subset")
    if value.get("type") == "object":
        properties = value.get("properties")
        if (
            not isinstance(properties, dict)
            or value.get("additionalProperties") is not False
            or value.get("required") != list(properties)
        ):
            raise CandidateError("provider object schema is not recursively closed")
        for child in properties.values():
            _walk_provider_schema(child)
    items = value.get("items")
    if isinstance(items, dict):
        _walk_provider_schema(items)
    defs = value.get("$defs")
    if isinstance(defs, dict):
        for child in defs.values():
            _walk_provider_schema(child)


def _validate_role_semantics(
    documents: Mapping[str, Any], raw_roles: Mapping[str, bytes]
) -> None:
    authority = documents["candidate_authority"]
    expected_authority_keys = {
        "schema_version",
        "authority_id",
        "candidate_id",
        "mechanism_id",
        "status",
        "claim_ceiling",
        "purpose",
        "f0_custody",
        "model_binding",
        "predecessor_terminal_provenance",
        "repair_provenance",
        "condition_contract",
        "slots",
        "assessor_packet_contract",
        "provider_schema_contract",
        "local_semantic_contract",
        "invocation_contract",
        "fold_contract",
        "reference_contract",
        "resolution_contract",
        "resolver_contract",
        "non_isomorphism_witness",
        "security_partition",
        "falsifiers",
        "qualification_boundary",
    }
    if (
        set(authority) != expected_authority_keys
        or any(
            token in key.casefold()
            for key in authority
            for token in ("heldout", "result", "event", "corpus", "schedule")
        )
        or authority.get("authority_id") != CANDIDATE_ID
        or authority.get("candidate_id") != CANDIDATE_ID
        or authority.get("mechanism_id") != MECHANISM_ID
        or authority.get("status") != "f1a-implementation"
        or authority.get("model_binding")
        != {
            "model_id": "gpt-5.5",
            "reasoning_effort": "medium",
            "fallback_permitted": False,
            "live_phases_only": ["SQ8-F4", "SQ8-F5"],
        }
        or authority.get("predecessor_terminal_provenance")
        != {
            "program_id": "AE-SQ7",
            "commit": "00d4e245244827cb4d12246725d95fc6287b00a2",
            "terminal_decision_path": "evals/ae-sq7/ar/terminal-decision.json",
            "terminal_decision_blob": "ca65696a8008b1412bdfbcfe185f26b26ee5b0b9",
            "terminal_decision_raw_sha256": "f401f7cda3fd9279d7fec49b2f02e6d4156f1268947aa1474c9fcc266ebc3454",
            "stage": "SQ7-AR",
            "status": "terminal",
            "terminal_reason": "frozen-runner-reads-top-level-validator_id-while-closed-receipt-schema-requires-nested-validator-validator_id",
            "later_stage_model_calls": 0,
            "candidate_qualification_imported": False,
            "candidate_identity_continued": False,
            "corpus_task_label_or_result_material_imported": False,
            "permitted_use": "terminal-custody-and-F3-receipt-interface-repair-provenance-only",
        }
    ):
        raise CandidateError("candidate authority identity or model binding drift")
    condition = authority.get("condition_contract")
    if (
        not isinstance(condition, dict)
        or condition.get("condition_order") != ["current", "reduced"]
        or condition.get("same_mechanism_for_both") is not True
        or len(authority.get("slots", [])) != 4
        or any(
            set(slot.get("cards", {})) != {"current", "reduced"}
            for slot in authority.get("slots", [])
        )
    ):
        raise CandidateError("candidate condition adapter/card binding drift")
    provider = authority.get("provider_schema_contract")
    semantic = authority.get("local_semantic_contract")
    resolution = authority.get("resolution_contract")
    reference = authority.get("reference_contract")
    if (
        not isinstance(provider, dict)
        or provider.get("capsule_schema_path") != dict(ROLE_PATHS)["capsule_schema"]
        or provider.get("capsule_schema_sha256")
        != sha256_bytes(raw_roles["capsule_schema"])
        or not isinstance(semantic, dict)
        or semantic.get("schema_path") != dict(ROLE_PATHS)["semantic_capsule_schema"]
        or semantic.get("schema_sha256")
        != sha256_bytes(raw_roles["semantic_capsule_schema"])
        or not isinstance(resolution, dict)
        or resolution.get("schema_path") != dict(ROLE_PATHS)["resolution_schema"]
        or resolution.get("schema_sha256")
        != sha256_bytes(raw_roles["resolution_schema"])
        or not isinstance(reference, dict)
        or reference.get("policy_path") != dict(ROLE_PATHS)["reference_policy"]
        or reference.get("policy_sha256") != sha256_bytes(raw_roles["reference_policy"])
    ):
        raise CandidateError("candidate schema/policy cross-binding drift")
    _walk_provider_schema(documents["capsule_schema"])
    semantic_schema = documents["semantic_capsule_schema"]
    if (
        semantic_schema.get("$id")
        != "https://example.local/agentic-engineering/evals/ae-sq8/slec8-semantic-capsule-schema.json"
        or semantic_schema.get("additionalProperties") is not False
    ):
        raise CandidateError("local semantic schema identity drift")
    resolver_text = raw_roles["resolver_and_local_semantic_validator"].decode(
        "utf-8", "strict"
    )
    resolver_contract = authority.get("resolver_contract")
    if (
        not isinstance(resolver_contract, dict)
        or resolver_contract.get("path")
        != dict(ROLE_PATHS)["resolver_and_local_semantic_validator"]
        or not isinstance(resolver_contract.get("required_api"), list)
    ):
        raise CandidateError("resolver contract identity drift")
    for api_name in resolver_contract["required_api"]:
        required_api = f"def {api_name}("
        if required_api not in resolver_text:
            raise CandidateError("resolver/local validator API closure is incomplete")
    for role, expected_id in (
        (
            "run_manifest_schema",
            "https://local.invalid/ae-sq8/f1/run-manifest-schema.json",
        ),
        ("preflight_schema", "https://local.invalid/ae-sq8/f1/preflight-schema.json"),
        ("result_schema", "https://local.invalid/ae-sq8/f1/result-schema.json"),
        (
            "author_template_gate_schema",
            "https://local.invalid/ae-sq8/f1/author-template-gate-schema.json",
        ),
        ("handoff_schema", "https://local.invalid/ae-sq8/f1/handoff-schema.json"),
        (
            "terminal_decision_schema",
            "https://local.invalid/ae-sq8/f1/terminal-decision-schema.json",
        ),
    ):
        if documents[role].get("$id") != expected_id:
            raise CandidateError(f"{role} identity drift")
    author_gate = documents["author_template_gate_schema"]
    selected_gate = author_gate.get("properties", {}).get(
        "selected_reference_anchor_gate"
    )
    full_f3_gate = author_gate.get("properties", {}).get("full_f3_boundary_gate")
    if (
        "selected_reference_anchor_gate" not in author_gate.get("required", [])
        or not isinstance(selected_gate, dict)
        or selected_gate.get("additionalProperties") is not False
        or selected_gate.get("required")
        != [
            "production_validator",
            "production_resolver",
            "positive",
            "red_missing",
            "red_wrong",
        ]
        or selected_gate.get("properties", {})
        .get("production_validator", {})
        .get("const")
        != "validate_corpora:selected_reference_anchors_valid"
        or selected_gate.get("properties", {})
        .get("production_resolver", {})
        .get("const")
        != "resolve_expected_capsules"
        or "full_f3_boundary_gate" not in author_gate.get("required", [])
        or not isinstance(full_f3_gate, dict)
        or full_f3_gate.get("additionalProperties") is not False
        or full_f3_gate.get("required")
        != [
            "fixture",
            "production_boundary",
            "production_checks",
            "production_one_shot_builder",
            "positive",
            "red_top_level_only",
            "red_missing_nested",
            "red_wrong_nested_placement",
        ]
        or full_f3_gate.get("properties", {})
        .get("production_boundary", {})
        .get("const")
        != "_execute_f3_boundary"
        or full_f3_gate.get("properties", {}).get("production_checks", {}).get("const")
        != "_f3_checks"
        or full_f3_gate.get("properties", {})
        .get("production_one_shot_builder", {})
        .get("const")
        != "build_f3_record"
    ):
        raise CandidateError("preauthor production gate schema is open")
    result = documents["result_schema"]
    if result.get("required") != [
        "aggregate_digest",
        "candidate_id",
        "program_id",
        "schema_version",
        "status",
    ] or set(result.get("properties", {})) != set(result["required"]):
        raise CandidateError("public result schema is not exact aggregate-only")
    preflight = documents["preflight_schema"]
    checks = preflight.get("properties", {}).get("checks", {})
    if not isinstance(checks, dict) or checks.get("additionalProperties") is not False:
        raise CandidateError("F3 check conjunction schema is open")
    check_names = checks.get("required")
    if not isinstance(check_names, list) or set(check_names) != set(
        checks.get("properties", {})
    ):
        raise CandidateError("F3 check conjunction keys are incomplete")
    f3_probe = {
        "schema_version": "ae-sq8-preflight-v1",
        "program_id": PROGRAM_ID,
        "candidate_id": CANDIDATE_ID,
        "phase": "SQ8-F3",
        "attempt": 1,
        "model_calls": 0,
        "status": "PASS",
        "bindings": {
            key: "0" * 64
            for key in preflight.get("properties", {})
            .get("bindings", {})
            .get("required", [])
        },
        "checks": {key: True for key in check_names},
        "aggregate_sha256": "0" * 64,
    }
    f3_validator = Draft202012Validator(preflight)
    if list(f3_validator.iter_errors(f3_probe)):
        raise CandidateError("F3 schema rejects its complete PASS conjunction")
    f3_probe["checks"][check_names[0]] = False
    if not list(f3_validator.iter_errors(f3_probe)):
        raise CandidateError("F3 schema permits PASS with a false check")
    f3_probe["status"] = "FAIL"
    if list(f3_validator.iter_errors(f3_probe)):
        raise CandidateError("F3 schema rejects FAIL with a false check")
    f3_probe["checks"][check_names[0]] = True
    if not list(f3_validator.iter_errors(f3_probe)):
        raise CandidateError("F3 schema permits FAIL with every check true")
    run_defs = documents["run_manifest_schema"].get("$defs", {})
    corpus_manifest = run_defs.get("corpusManifestDocument")
    authoring_provenance = run_defs.get("authoringProvenance")
    provenance_list = (
        corpus_manifest.get("properties", {}).get("authoring_provenance", {})
        if isinstance(corpus_manifest, dict)
        else {}
    )
    validation_receipt = run_defs.get("validationReceipt")
    if (
        not isinstance(corpus_manifest, dict)
        or corpus_manifest.get("additionalProperties") is not False
        or set(corpus_manifest.get("required", []))
        != set(corpus_manifest.get("properties", {}))
        or "combined_corpus_sha256" not in corpus_manifest.get("properties", {})
        or "freshness" not in corpus_manifest.get("properties", {})
        or not isinstance(authoring_provenance, dict)
        or authoring_provenance.get("additionalProperties") is not False
        or set(authoring_provenance.get("required", []))
        != set(authoring_provenance.get("properties", {}))
        or provenance_list.get("items") is not False
        or provenance_list.get("minItems") != 2
        or provenance_list.get("maxItems") != 2
        or len(provenance_list.get("prefixItems", [])) != 2
        or not isinstance(validation_receipt, dict)
        or validation_receipt.get("additionalProperties") is not False
        or set(validation_receipt.get("required", []))
        != set(validation_receipt.get("properties", {}))
    ):
        raise CandidateError("F2 corpus-manifest semantic schema is open")
    gates = documents["gates"]
    metrics = documents["metrics"]
    evaluator = documents["evaluator_schema"]
    if (
        gates.get("program_id") != PROGRAM_ID
        or gates.get("root_pass_iff")
        != "both conditions pass every per-condition gate and the complete run passes every complete-run gate"
        or gates.get("compensation") is not False
        or metrics.get("program_id") != PROGRAM_ID
        or tuple(metrics.get("formula_order", ())) != EXPECTED_FORMULA_ORDER
        or evaluator.get("properties", {}).get("program_id", {}).get("const")
        != PROGRAM_ID
        or evaluator.get("properties", {}).get("status", {}).get("enum")
        != ["pass", "fail"]
    ):
        raise CandidateError("evaluator/global-AND authority drift")
    validator_text = raw_roles["corpus_validator_and_expected_authority_helper"].decode(
        "utf-8", "strict"
    )
    builder_text = raw_roles["author_template_builder"].decode("utf-8", "strict")
    runner_text = raw_roles["runner"].decode("utf-8", "strict")
    if (
        "def expected_split_authority(" not in validator_text
        or "expected_authority: Mapping[str, Any] | None" not in validator_text
        or "def selected_reference_anchors_valid(" not in validator_text
        or "def selected_reference_anchor_fixture(" not in validator_text
        or "def render_author_template(" not in builder_text
        or 'profile["implementation_commit"]' not in builder_text
        or 'profile["freeze_commit"]' not in builder_text
        or "def _run_selected_reference_anchor_gate(" not in runner_text
        or 'receipt["selected_reference_anchor_gate"]' not in runner_text
        or "def _run_full_f3_boundary_gate(" not in runner_text
        or 'receipt["full_f3_boundary_gate"]' not in runner_text
        or "def _validation_receipt_validator_id(" not in runner_text
        or 'receipt.get("validator")' not in runner_text
        or "def _execute_f3_boundary(" not in runner_text
        or "def full_f3_boundary_fixture(" not in runner_text
        or "record = _execute_f3_boundary(state, root)" not in runner_text
    ):
        raise CandidateError("author-template identity repair APIs are incomplete")


def _verify_binding(root: Path, binding: Mapping[str, str], label: str) -> bytes:
    commit = _exact_commit(root, binding["commit"], f"{label} commit")
    if _tree(root, commit) != binding["tree"]:
        raise CandidateError(f"{label} tree mismatch")
    raw = _show(root, commit, binding["path"])
    if (
        _blob(root, commit, binding["path"]) != binding["blob"]
        or sha256_bytes(raw) != binding["sha256"]
    ):
        raise CandidateError(f"{label} byte identity mismatch")
    return raw


def _validate_diagnostic_record(
    root: Path,
    diagnosis: Mapping[str, Any],
    diagnosis_raw: bytes,
) -> dict[str, Any]:
    """Validate the immutable, bounded D0 projection without opening raw call data."""
    if tuple(diagnosis) != DIAGNOSTIC_TOP_LEVEL_KEYS:
        raise CandidateError("bounded diagnosis top-level field closure or order drift")

    schema_raw = _show(root, DIAGNOSTIC_COMMIT, DIAGNOSTIC_SCHEMA_PATH)
    schema = closed_json(schema_raw, "bounded SQ2 diagnostic schema")
    if diagnosis.get("diagnostic_schema_sha256") != sha256_bytes(schema_raw):
        raise CandidateError("bounded diagnosis schema digest mismatch")
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(diagnosis)
    except (SchemaError, ValidationError) as error:
        raise CandidateError("bounded diagnosis violates its closed schema") from error

    authority_raw = _show(root, DIAGNOSTIC_COMMIT, DIAGNOSTIC_AUTHORITY_PATH)
    diagnostic_authority = closed_json(
        authority_raw, "bounded SQ2 diagnostic authority"
    )
    if (
        diagnosis.get("authority_sha256") != sha256_bytes(authority_raw)
        or diagnostic_authority.get("program_id") != "AE-SQ2"
        or diagnostic_authority.get("authority_status")
        != "bounded-live-diagnostic-authority"
        or diagnostic_authority.get("claim_ceiling")
        != "four-call-synthetic-handshake-diagnostic-only"
    ):
        raise CandidateError("bounded diagnosis authority digest or identity mismatch")

    if (
        "program_id" in diagnosis
        or diagnosis.get("diagnostic_id") != "AE-SQ2-D0-2026-08-12-01"
        or diagnosis.get("mode") != "live"
        or diagnosis.get("status") != "completed"
        or diagnosis.get("claim_ceiling")
        != "four-call-synthetic-handshake-diagnostic-only"
    ):
        raise CandidateError("bounded diagnosis completion identity drift")

    input_schema = diagnosis.get("input_schema")
    if not isinstance(input_schema, dict) or set(input_schema) != {
        "path",
        "size_bytes",
        "sha256",
    }:
        raise CandidateError("bounded diagnosis input-schema custody is missing")
    input_raw = _show(root, DIAGNOSTIC_COMMIT, input_schema["path"])
    if input_schema["size_bytes"] != len(input_raw) or input_schema[
        "sha256"
    ] != sha256_bytes(input_raw):
        raise CandidateError("bounded diagnosis input-schema byte identity mismatch")

    unsigned_record = dict(diagnosis)
    record_digest = unsigned_record.pop("record_sha256", None)
    if record_digest != sha256_bytes(canonical_json(unsigned_record)):
        raise CandidateError("bounded diagnosis internal record digest mismatch")
    if sha256_bytes(diagnosis_raw) == record_digest:
        raise CandidateError("bounded diagnosis raw and internal digests are conflated")

    calls = diagnosis["calls"]
    if tuple(call["probe_id"] for call in calls) != DIAGNOSTIC_PROBE_ORDER:
        raise CandidateError("bounded diagnosis probe identity or order drift")
    if diagnosis["calls_started"] != len(calls):
        raise CandidateError("bounded diagnosis started-call count does not reconcile")
    completed = sum(
        1
        for call in calls
        if call["exit_code"] is not None or call["signal"] is not None
    )
    if diagnosis["calls_completed"] != completed:
        raise CandidateError(
            "bounded diagnosis completed-call count does not reconcile"
        )

    observed_classifications = Counter(call["classification"] for call in calls)
    expected_counts = {
        key: observed_classifications.get(key, 0)
        for key in diagnosis["classification_counts"]
    }
    if diagnosis["classification_counts"] != expected_counts:
        raise CandidateError("bounded diagnosis classification counts do not reconcile")
    if sum(diagnosis["classification_counts"].values()) != len(calls):
        raise CandidateError("bounded diagnosis classification count total drift")

    observed_usage = {
        key: sum(call["usage"][key] for call in calls) for key in diagnosis["usage"]
    }
    if diagnosis["usage"] != observed_usage:
        raise CandidateError("bounded diagnosis usage counters do not reconcile")
    if diagnosis["aggregate_sha256"] != sha256_bytes(canonical_json(calls)):
        raise CandidateError("bounded diagnosis call aggregate digest mismatch")
    return {
        "schema_raw": schema_raw,
        "authority_raw": authority_raw,
        "input_raw": input_raw,
    }


def _validate_bounded_diagnosis(
    root: Path,
    manifest: Mapping[str, Any],
    diagnosis: Mapping[str, Any],
    diagnosis_raw: bytes,
) -> None:
    """Bind the exact immutable D0 receipt and its frozen inputs to F1B."""
    source_raw = _validate_diagnostic_record(root, diagnosis, diagnosis_raw)
    f1_record = manifest["authority_bindings"]["bounded_sq2_diagnosis"]
    if (
        f1_record
        != {
            "commit": DIAGNOSTIC_COMMIT,
            "tree": "7a5f272b8e8d3750e2df5da108d9f7b9946958a5",
            "path": DIAGNOSTIC_PATH,
            "blob": "f5dc5b67435c78d0b214ac21fc69531c9bae7d3e",
            "sha256": "1e2352fe42453b03cafac06e9c2e98638af17ad6a3e5dfaf389baf9da39d6502",
        }
        or sha256_bytes(diagnosis_raw) != f1_record["sha256"]
        or sha256_bytes(source_raw["authority_raw"])
        != "2452348832f5a4d8a3ba566adfcf1893c6740dc0b66902fae8cf537324c5f379"
        or sha256_bytes(source_raw["schema_raw"])
        != "9b1f037cecf3071ce8d8ddea88e208c55c6f72674375db064eaeb46920fd0c01"
        or diagnosis["calls_started"] != 4
        or diagnosis["calls_completed"] != 4
        or diagnosis["classification_counts"].get("schema_unsupported") != 4
        or any(
            count
            for classification, count in diagnosis["classification_counts"].items()
            if classification != "schema_unsupported"
        )
        or any(diagnosis["usage"].values())
    ):
        raise CandidateError(
            "bounded diagnosis is not exact four-call zero-usage result"
        )

    runtime = manifest["runtime"]
    if (
        diagnosis.get("model") != runtime["model"]
        or diagnosis.get("reasoning_effort") != runtime["reasoning"]
        or diagnosis.get("cli", {}).get("version") != runtime["cli"]["version"]
        or diagnosis.get("cli", {}).get("sha256") != runtime["cli"]["sha256"]
    ):
        raise CandidateError("bounded diagnosis/F1 runtime identity drift")


def load_verified_candidate(
    root: Path | str,
    freeze_commit: str,
    *,
    require_live: bool = True,
    live_commit: str | None = None,
) -> dict[str, Any]:
    """Verify the complete F0 -> F1A -> manifest-only F1B custody chain."""
    repository = Path(root).resolve(strict=True)
    f1b = _exact_commit(repository, freeze_commit, "F1B commit")
    verified_live_commit: str | None = None
    canonical_ref: str | None = None
    if require_live:
        head = _git(repository, ["rev-parse", "HEAD"]).decode().strip()
        expected_live = _exact_commit(
            repository, live_commit if live_commit is not None else head, "live commit"
        )
        if head != expected_live:
            raise CandidateError("live execution commit is not canonical HEAD")
        verified_live_commit = expected_live
        ref_result = subprocess.run(
            ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
            cwd=repository,
            capture_output=True,
            text=True,
            timeout=30,
        )
        canonical_ref = (
            ref_result.stdout.strip() if ref_result.returncode == 0 else "DETACHED"
        )
        ancestry = (
            _git(
                repository,
                ["rev-list", "--first-parent", expected_live],
            )
            .decode()
            .splitlines()
        )
        if f1b not in ancestry:
            raise CandidateError("F1B is not on the canonical live first-parent chain")
        # No later freeze or same-program refreeze may appear on the active
        # lineage.  Git cannot prove absence of unreachable objects; the claim
        # ceiling is explicitly the canonical reachable first-parent lineage.
        freeze_occurrences = 0
        for lineage_commit in ancestry:
            present = (
                _git(
                    repository,
                    ["ls-tree", "--name-only", lineage_commit, "--", FREEZE_PATH],
                )
                .decode()
                .strip()
            )
            if present == FREEZE_PATH:
                parents = _parents(repository, lineage_commit)
                if not parents or _changed_paths(
                    repository, parents[0], lineage_commit
                ) == (FREEZE_PATH,):
                    freeze_occurrences += 1
        if freeze_occurrences != 1:
            raise CandidateError(
                "canonical live lineage has a missing or second F1B freeze"
            )
    freeze_raw = _show(repository, f1b, FREEZE_PATH)
    manifest = _validate_freeze(closed_json(freeze_raw, "F1B freeze"))
    f1a = _exact_commit(
        repository, manifest["implementation_freeze"]["commit"], "F1A commit"
    )
    if _tree(repository, f1a) != manifest["implementation_freeze"]["tree"]:
        raise CandidateError("F1A tree mismatch")
    if _parents(repository, f1a) != (AUTHORITY_COMMIT,):
        raise CandidateError("F1A is not the sole direct child of frozen F0")
    if _parents(repository, f1b) != (f1a,):
        raise CandidateError("F1B is not the sole direct child of F1A")
    reachable_freezes = _reachable_f1b_children(repository, f1a)
    if reachable_freezes != (f1b,):
        raise CandidateError("F1A has a reachable sibling or refreeze F1B")
    if set(_changed_paths(repository, AUTHORITY_COMMIT, f1a)) != {
        path for _role, path in ROLE_PATHS
    }:
        raise CandidateError("F1A changed paths are not the exhaustive role closure")
    if _changed_paths(repository, f1a, f1b) != (FREEZE_PATH,):
        raise CandidateError("F1B is not manifest-only")
    f1a_names = set(
        _git(repository, ["ls-tree", "-r", "--name-only", f1a, "--", "evals/ae-sq8"])
        .decode()
        .splitlines()
    )
    if f1a_names & F1A_FORBIDDEN_PATHS or any(
        name.startswith(
            (
                "evals/ae-sq8/f2/",
                "evals/ae-sq8/f3/",
                "evals/ae-sq8/f4/",
                "evals/ae-sq8/f5/",
                "evals/ae-sq8/f6/",
            )
        )
        for name in f1a_names
    ):
        raise CandidateError(
            "F1A contains a freeze, corpus, preflight, or result artifact"
        )

    authorities = manifest["authority_bindings"]
    program_raw = _verify_binding(
        repository, authorities["program_authority"], "program authority"
    )
    diagnosis_raw = _verify_binding(
        repository, authorities["bounded_sq2_diagnosis"], "bounded SQ2 diagnosis"
    )
    authority = closed_json(program_raw, "program authority")
    diagnosis = closed_json(diagnosis_raw, "bounded SQ2 diagnosis")
    if (
        authority.get("program_id") != PROGRAM_ID
        or authority.get("authority_status") != "F0_INITIAL_AUTHORITY_CLOSED"
    ):
        raise CandidateError("program authority identity drift")
    f1_contract = authority.get("f1_contract")
    if not isinstance(f1_contract, dict) or f1_contract.get(
        "candidate_requirements"
    ) != [
        "new-SLEC-8-identity",
        "fresh-SQ8-namespace",
        "complete-candidate-evaluator-runner-schema-and-test-closure",
        "no-SQ7-active-role-blob-or-raw-byte-reuse",
        "zero-corpus-and-zero-model-calls",
    ]:
        raise CandidateError("program authority F1 requirements drift")
    historical = HISTORICAL_BINDING
    historical_raw = _show(
        repository, historical.get("commit", ""), historical.get("path", "")
    )
    if (
        _tree(repository, historical["commit"]) != historical["tree"]
        or _blob(repository, historical["commit"], historical["path"])
        != historical["blob"]
        or sha256_bytes(historical_raw) != historical["raw_sha256"]
    ):
        raise CandidateError("external historical inventory custody drift")
    _validate_bounded_diagnosis(
        repository,
        manifest,
        diagnosis,
        diagnosis_raw,
    )

    documents: dict[str, Any] = {}
    raw_roles: dict[str, bytes] = {}
    bindings: dict[str, dict[str, str]] = {}
    sq7_blobs = {_blob(repository, SQ7_F1A_COMMIT, path) for path in SQ7_ROLE_PATHS}
    sq7_raw_sha256 = {
        sha256_bytes(_show(repository, SQ7_F1A_COMMIT, path)) for path in SQ7_ROLE_PATHS
    }
    for row, (role, path) in zip(manifest["files"], ROLE_PATHS, strict=True):
        raw = _show(repository, f1a, path)
        actual_blob = _blob(repository, f1a, path)
        if actual_blob != row["blob"] or sha256_bytes(raw) != row["sha256"]:
            raise CandidateError(f"F1A role byte mismatch: {role}")
        _require_regular_blob(repository, f1a, path, actual_blob)
        if actual_blob in sq7_blobs or sha256_bytes(raw) in sq7_raw_sha256:
            raise CandidateError(f"SQ8 active role aliases an SQ7 F1A byte: {role}")
        if require_live:
            destination = repository / path
            try:
                live = destination.read_bytes()
                metadata = destination.lstat()
            except OSError as error:
                raise CandidateError(f"live role is unavailable: {role}") from error
            if (
                destination.is_symlink()
                or not destination.is_file()
                or metadata.st_nlink != 1
                or live != raw
            ):
                raise CandidateError(f"live role byte drift: {role}")
            if stat.S_IMODE(metadata.st_mode) & 0o022:
                raise CandidateError(f"live role is group/world writable: {role}")
        if role in JSON_ROLES:
            documents[role] = closed_json(raw, role)
        raw_roles[role] = raw
        bindings[role] = {
            "commit": f1a,
            "tree": manifest["implementation_freeze"]["tree"],
            "path": path,
            "blob": row["blob"],
            "sha256": row["sha256"],
        }
    _validate_role_semantics(documents, raw_roles)
    if require_live:
        destination = repository / FREEZE_PATH
        try:
            live_freeze = destination.read_bytes()
        except OSError as error:
            raise CandidateError("live F1B freeze is unavailable") from error
        if destination.is_symlink() or live_freeze != freeze_raw:
            raise CandidateError("live F1B freeze byte drift")
        metadata = destination.lstat()
        if not destination.is_file() or metadata.st_nlink != 1:
            raise CandidateError("live F1B freeze is not a single-link regular file")
        if stat.S_IMODE(metadata.st_mode) & 0o022:
            raise CandidateError("live F1B freeze is group/world writable")
    return {
        "program_id": PROGRAM_ID,
        "candidate_id": CANDIDATE_ID,
        "mechanism_id": MECHANISM_ID,
        "freeze_commit": f1b,
        "freeze_tree": _tree(repository, f1b),
        "freeze_path": FREEZE_PATH,
        "freeze_sha256": sha256_bytes(freeze_raw),
        "implementation_commit": f1a,
        "implementation_tree": manifest["implementation_freeze"]["tree"],
        "role_ledger_sha256": sha256_bytes(canonical_json(manifest["files"])),
        "verified_live_commit": verified_live_commit,
        "canonical_ref": canonical_ref,
        "verification_claim_ceiling": (
            "all-ref-reachable-manifest-only-f1b-children-and-active-"
            "first-parent-live-lineage;unreachable-git-objects-excluded"
        ),
        "manifest": manifest,
        "documents": documents,
        "raw_roles": raw_roles,
        "bindings": bindings,
        "external_bindings": {
            "historical_task_digests": {
                "commit": historical["commit"],
                "tree": historical["tree"],
                "path": historical["path"],
                "blob": historical["blob"],
                "sha256": historical["raw_sha256"],
            }
        },
    }


def provisional_hashes(root: Path | str) -> dict[str, str]:
    """Return unqualified current hashes for preparing the F1B ledger."""
    repository = Path(root).resolve(strict=True)
    result: dict[str, str] = {}
    for role, path in ROLE_PATHS:
        destination = repository / path
        try:
            metadata = destination.lstat()
            raw = destination.read_bytes()
        except OSError:
            result[role] = "UNAVAILABLE"
            continue
        result[role] = (
            sha256_bytes(raw)
            if destination.is_file()
            and not destination.is_symlink()
            and metadata.st_nlink == 1
            and stat.S_IMODE(metadata.st_mode) & 0o022 == 0
            else "UNAVAILABLE"
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--freeze-commit")
    parser.add_argument("--require-live", action="store_true")
    parser.add_argument("--provisional-hashes", action="store_true")
    args = parser.parse_args(argv)
    if args.provisional_hashes:
        print(
            json.dumps(
                {"status": "unqualified", "role_sha256": provisional_hashes(args.root)},
                sort_keys=True,
            )
        )
        return 0
    if args.freeze_commit is None:
        parser.error("--freeze-commit is required unless --provisional-hashes is used")
    profile = load_verified_candidate(
        args.root, args.freeze_commit, require_live=args.require_live
    )
    print(
        json.dumps(
            {
                "status": (
                    "verified_live_execution_ready"
                    if args.require_live
                    else "verified_commit_only"
                ),
                "verification_mode": "live" if args.require_live else "commit-only",
                "program_id": profile["program_id"],
                "candidate_id": profile["candidate_id"],
                "implementation_commit": profile["implementation_commit"],
                "implementation_tree": profile["implementation_tree"],
                "freeze_sha256": profile["freeze_sha256"],
                "verified_live_commit": profile["verified_live_commit"],
                "canonical_ref": profile["canonical_ref"],
                "verification_claim_ceiling": profile["verification_claim_ceiling"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
