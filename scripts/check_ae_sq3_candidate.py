#!/usr/bin/env python3
"""Strict two-commit byte-custody checker for AE-SQ3-SLEC-3.

SQ3-F1A is exactly one implementation commit after the frozen F0 authority.
SQ3-F1B is exactly one manifest-only child commit.  This module treats Git
objects, rather than the mutable worktree, as the source of truth and can also
require the live checkout to match every frozen byte before execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "AE-SQ3"
CANDIDATE_ID = "AE-SQ3-SLEC-3"
MECHANISM_ID = "SLEC-3"
AUTHORITY_COMMIT = "230354f09045c0f20b03c5080a6d70fcee38acbb"
AUTHORITY_PATH = "evals/ae-sq3/program-authority.json"
DIAGNOSTIC_COMMIT = "e2562ca4da5f3dc14fb07c1522f911e2dfe4334d"
DIAGNOSTIC_PATH = "evals/ae-sq2/d0/diagnostic-record.json"
FREEZE_PATH = "evals/ae-sq3/f1/repaired-freeze.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
PLACEHOLDER = re.compile(
    r"(?:UNBOUND|PLACEHOLDER|TBD|TO[-_ ]?BE[-_ ]?SET)", re.IGNORECASE
)

ROLE_PATHS = (
    ("historical_task_digests", "evals/ae-sq3/f1/historical-task-digests.json"),
    ("candidate_authority", "evals/ae-sq3/f1/slec3-authority.json"),
    ("resolver_and_local_semantic_validator", "scripts/resolve_ae_sq3_slec.py"),
    ("capsule_schema", "evals/ae-sq3/f1/slec3-capsule-schema.json"),
    (
        "semantic_capsule_schema",
        "evals/ae-sq3/f1/slec3-semantic-capsule-schema.json",
    ),
    ("resolution_schema", "evals/ae-sq3/f1/slec3-resolution-schema.json"),
    ("reference_policy", "evals/ae-sq3/f1/slec3-reference-policy.json"),
    ("corpus_schema", "evals/ae-sq3/f1/corpus-schema.json"),
    ("gates", "evals/ae-sq3/f1/gates.json"),
    ("metrics", "evals/ae-sq3/f1/metrics.json"),
    ("evaluator_schema", "evals/ae-sq3/f1/evaluator-schema.json"),
    ("corpus_validator", "scripts/validate_ae_sq3_corpus.py"),
    ("scorer", "scripts/score_ae_sq3_aq.py"),
    ("runner", "scripts/run_ae_sq3_aq.py"),
    ("run_index", "scripts/ae_sq3_run_index.py"),
    ("candidate_checker", "scripts/check_ae_sq3_candidate.py"),
    ("run_manifest_schema", "evals/ae-sq3/f1/run-manifest-schema.json"),
    ("preflight_schema", "evals/ae-sq3/f1/preflight-schema.json"),
    ("result_schema", "evals/ae-sq3/f1/result-schema.json"),
    (
        "historical_digest_test",
        "tests/test_ae_sq3_historical_task_digests.py",
    ),
    ("slec_test", "tests/test_ae_sq3_slec.py"),
    ("provider_schema_test", "tests/test_ae_sq3_provider_schema.py"),
    ("corpus_contract_test", "tests/test_ae_sq3_corpus_contract.py"),
    ("evaluator_test", "tests/test_ae_sq3_evaluator.py"),
    ("run_index_test", "tests/test_ae_sq3_run_index.py"),
    ("candidate_checker_test", "tests/test_check_ae_sq3_candidate.py"),
    ("runner_test", "tests/test_run_ae_sq3_aq.py"),
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
F1A_FORBIDDEN_PATHS = frozenset(
    {
        FREEZE_PATH,
        "evals/ae-sq3/f2/run-manifest.json",
        "evals/ae-sq3/f3/preflight.json",
    }
)


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
    resolved = _git(root, ["rev-parse", "--verify", f"{value}^{{commit}}"]).decode().strip()
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


def _parents(root: Path, commit: str) -> tuple[str, ...]:
    fields = _git(root, ["rev-list", "--parents", "-n", "1", commit]).decode().split()
    return tuple(fields[1:])


def _changed_paths(root: Path, parent: str, child: str) -> tuple[str, ...]:
    raw = _git(root, ["diff-tree", "--no-commit-id", "--name-only", "-r", parent, child])
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
        return any(_has_placeholder(key) or _has_placeholder(item) for key, item in value.items())
    return False


def _sealed_path(value: Any, *, expected_path: str, label: str) -> dict[str, str]:
    keys = {"commit", "tree", "path", "blob", "sha256"}
    if not isinstance(value, dict) or set(value) != keys or value.get("path") != expected_path:
        raise CandidateError(f"{label} binding is not exactly closed")
    for key in ("commit", "tree", "blob"):
        if not isinstance(value.get(key), str) or HEX40.fullmatch(value[key]) is None:
            raise CandidateError(f"{label} Git identity is invalid")
    if not isinstance(value.get("sha256"), str) or HEX64.fullmatch(value["sha256"]) is None:
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
        value["schema_version"] != "ae-sq3-repaired-freeze-v1"
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
    if program["commit"] != AUTHORITY_COMMIT or diagnosis["commit"] != DIAGNOSTIC_COMMIT:
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
        "directory": ".git-common-dir/.ae-sq3-one-shot",
        "path": ".git-common-dir/.ae-sq3-one-shot/state.json",
        "schema_version": "ae-sq3-one-shot-run-index-v1",
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


def _validate_role_semantics(documents: Mapping[str, Any], raw_roles: Mapping[str, bytes]) -> None:
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
        or
        authority.get("authority_id") != CANDIDATE_ID
        or authority.get("candidate_id") != CANDIDATE_ID
        or authority.get("mechanism_id") != MECHANISM_ID
        or authority.get("status") != "f1a-implementation"
        or authority.get("model_binding")
        != {
            "model_id": "gpt-5.5",
            "reasoning_effort": "medium",
            "fallback_permitted": False,
            "live_phases_only": ["SQ3-F4", "SQ3-F5"],
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
        or provider.get("capsule_schema_path")
        != dict(ROLE_PATHS)["capsule_schema"]
        or provider.get("capsule_schema_sha256")
        != sha256_bytes(raw_roles["capsule_schema"])
        or not isinstance(semantic, dict)
        or semantic.get("schema_path")
        != dict(ROLE_PATHS)["semantic_capsule_schema"]
        or semantic.get("schema_sha256")
        != sha256_bytes(raw_roles["semantic_capsule_schema"])
        or not isinstance(resolution, dict)
        or resolution.get("schema_path") != dict(ROLE_PATHS)["resolution_schema"]
        or resolution.get("schema_sha256")
        != sha256_bytes(raw_roles["resolution_schema"])
        or not isinstance(reference, dict)
        or reference.get("policy_path") != dict(ROLE_PATHS)["reference_policy"]
        or reference.get("policy_sha256")
        != sha256_bytes(raw_roles["reference_policy"])
    ):
        raise CandidateError("candidate schema/policy cross-binding drift")
    _walk_provider_schema(documents["capsule_schema"])
    semantic_schema = documents["semantic_capsule_schema"]
    if (
        semantic_schema.get("$id")
        != "https://example.local/agentic-engineering/evals/ae-sq3/slec3-semantic-capsule-schema.json"
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
        ("run_manifest_schema", "https://local.invalid/ae-sq3/f1/run-manifest-schema.json"),
        ("preflight_schema", "https://local.invalid/ae-sq3/f1/preflight-schema.json"),
        ("result_schema", "https://local.invalid/ae-sq3/f1/result-schema.json"),
    ):
        if documents[role].get("$id") != expected_id:
            raise CandidateError(f"{role} identity drift")
    result = documents["result_schema"]
    if result.get("required") != [
        "program_id",
        "candidate_id",
        "status",
        "aggregate_digest",
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
        "schema_version": "ae-sq3-preflight-v1",
        "program_id": PROGRAM_ID,
        "candidate_id": CANDIDATE_ID,
        "phase": "SQ3-F3",
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
    if (
        not isinstance(corpus_manifest, dict)
        or corpus_manifest.get("additionalProperties") is not False
        or set(corpus_manifest.get("required", []))
        != set(corpus_manifest.get("properties", {}))
        or "combined_corpus_sha256" not in corpus_manifest.get("properties", {})
        or "freshness" not in corpus_manifest.get("properties", {})
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
    historical = documents["historical_task_digests"]
    if (
        historical.get("program_id") != PROGRAM_ID
        or historical.get("role") != "historical_digest_inventory"
        or historical.get("inventory_count") != 768
        or len(historical.get("sources", [])) != 20
    ):
        raise CandidateError("historical inventory role is incomplete")


def _verify_binding(root: Path, binding: Mapping[str, str], label: str) -> bytes:
    commit = _exact_commit(root, binding["commit"], f"{label} commit")
    if _tree(root, commit) != binding["tree"]:
        raise CandidateError(f"{label} tree mismatch")
    raw = _show(root, commit, binding["path"])
    if _blob(root, commit, binding["path"]) != binding["blob"] or sha256_bytes(raw) != binding["sha256"]:
        raise CandidateError(f"{label} byte identity mismatch")
    return raw


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
        ancestry = _git(
            repository,
            ["rev-list", "--first-parent", expected_live],
        ).decode().splitlines()
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
                if not parents or _changed_paths(repository, parents[0], lineage_commit) == (FREEZE_PATH,):
                    freeze_occurrences += 1
        if freeze_occurrences != 1:
            raise CandidateError("canonical live lineage has a missing or second F1B freeze")
    freeze_raw = _show(repository, f1b, FREEZE_PATH)
    manifest = _validate_freeze(closed_json(freeze_raw, "F1B freeze"))
    f1a = _exact_commit(repository, manifest["implementation_freeze"]["commit"], "F1A commit")
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
        _git(repository, ["ls-tree", "-r", "--name-only", f1a, "--", "evals/ae-sq3"]).decode().splitlines()
    )
    if f1a_names & F1A_FORBIDDEN_PATHS or any(
        name.startswith(("evals/ae-sq3/f2/", "evals/ae-sq3/f3/", "evals/ae-sq3/f4/", "evals/ae-sq3/f5/", "evals/ae-sq3/f6/"))
        for name in f1a_names
    ):
        raise CandidateError("F1A contains a freeze, corpus, preflight, or result artifact")

    authorities = manifest["authority_bindings"]
    program_raw = _verify_binding(repository, authorities["program_authority"], "program authority")
    diagnosis_raw = _verify_binding(repository, authorities["bounded_sq2_diagnosis"], "bounded SQ2 diagnosis")
    authority = closed_json(program_raw, "program authority")
    diagnosis = closed_json(diagnosis_raw, "bounded SQ2 diagnosis")
    if authority.get("program_id") != PROGRAM_ID or authority.get("authority_status") != "F0_INITIAL_AUTHORITY_CLOSED":
        raise CandidateError("program authority identity drift")
    imported = authority.get("imported_diagnosis")
    if not isinstance(imported, dict) or imported.get("classification_counts", {}).get("schema_unsupported") != 4:
        raise CandidateError("bounded diagnosis is not the authorized four-call result")
    if diagnosis.get("program_id") != "AE-SQ2" or diagnosis.get("mode") != "diagnostic":
        raise CandidateError("bounded diagnosis record identity drift")

    documents: dict[str, Any] = {}
    raw_roles: dict[str, bytes] = {}
    bindings: dict[str, dict[str, str]] = {}
    for row, (role, path) in zip(manifest["files"], ROLE_PATHS, strict=True):
        raw = _show(repository, f1a, path)
        if _blob(repository, f1a, path) != row["blob"] or sha256_bytes(raw) != row["sha256"]:
            raise CandidateError(f"F1A role byte mismatch: {role}")
        if require_live:
            destination = repository / path
            try:
                live = destination.read_bytes()
                metadata = destination.lstat()
            except OSError as error:
                raise CandidateError(f"live role is unavailable: {role}") from error
            if destination.is_symlink() or not destination.is_file() or metadata.st_nlink != 1 or live != raw:
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
        print(json.dumps({"status": "unqualified", "role_sha256": provisional_hashes(args.root)}, sort_keys=True))
        return 0
    if args.freeze_commit is None:
        parser.error("--freeze-commit is required unless --provisional-hashes is used")
    profile = load_verified_candidate(args.root, args.freeze_commit, require_live=args.require_live)
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
