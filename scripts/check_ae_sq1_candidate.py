#!/usr/bin/env python3
"""Fail-closed byte-custody checker for the AE-SQ1 SLEC-1 candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = "evals/ae-sq1/candidate-manifest.json"
PROGRAM_ID = "AE-SQ1"
CANDIDATE_ID = "SLEC-1"
ROLE_PATHS = (
    ("program_authority", "evals/ae-sq1/program-authority.json"),
    ("external_evidence", "evals/ae-sq1/external-evidence.json"),
    ("historical_task_digests", "evals/ae-sq1/historical-task-digests.json"),
    ("candidate_authority", "evals/ae-sq1/slec1-authority.json"),
    ("resolver", "scripts/resolve_ae_sq1_slec.py"),
    ("capsule_schema", "evals/ae-sq1/slec1-capsule-schema.json"),
    ("resolution_schema", "evals/ae-sq1/slec1-resolution-schema.json"),
    ("reference_policy", "evals/ae-sq1/slec1-reference-policy.json"),
    ("corpus_schema", "evals/ae-sq1/aq/corpus-schema.json"),
    ("gates", "evals/ae-sq1/aq/gates.json"),
    ("metrics", "evals/ae-sq1/aq/metrics.json"),
    ("evaluator_schema", "evals/ae-sq1/aq/evaluator-schema.json"),
    ("corpus_validator", "scripts/validate_ae_sq1_corpus.py"),
    ("scorer", "scripts/score_ae_sq1_aq.py"),
    ("runner", "scripts/run_ae_sq1_aq.py"),
    ("run_index", "scripts/ae_sq1_run_index.py"),
    ("candidate_checker", "scripts/check_ae_sq1_candidate.py"),
    ("run_manifest_schema", "evals/ae-sq1/aq/run-manifest-schema.json"),
    ("historical_digest_test", "tests/test_ae_sq1_historical_task_digests.py"),
    ("slec_test", "tests/test_ae_sq1_slec.py"),
    ("corpus_contract_test", "tests/test_ae_sq1_corpus_contract.py"),
    ("evaluator_test", "tests/test_ae_sq1_evaluator.py"),
    ("run_index_test", "tests/test_ae_sq1_run_index.py"),
    ("candidate_checker_test", "tests/test_check_ae_sq1_candidate.py"),
    ("runner_test", "tests/test_run_ae_sq1_aq.py"),
)
ROLE_ORDER = tuple(role for role, _path in ROLE_PATHS)
EARLIER_AUTHORITY_ROLES = frozenset({"program_authority", "external_evidence"})
JSON_ROLES = frozenset(role for role, path in ROLE_PATHS if path.endswith(".json"))
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
PLACEHOLDER = re.compile(
    r"(?:UNBOUND|PLACEHOLDER|TBD|TO[-_ ]?BE[-_ ]?SET)", re.IGNORECASE
)


class CandidateError(ValueError):
    """The manifest is unresolved, cross-program, or byte-drifted."""


def _closed_json(raw: bytes, label: str) -> dict[str, Any]:
    def closed_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw,
            object_pairs_hook=closed_pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise CandidateError(f"{label} is not closed finite JSON") from error
    if not isinstance(value, dict):
        raise CandidateError(f"{label} is not a JSON object")
    return value


def _git(root: Path, args: list[str]) -> bytes:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise CandidateError("required Git custody object is unavailable") from error


def _commit(root: Path, revision: str) -> str:
    if not isinstance(revision, str) or HEX40.fullmatch(revision) is None:
        raise CandidateError("manifest commit must be an exact lowercase SHA")
    return (
        _git(root, ["rev-parse", "--verify", f"{revision}^{{commit}}"]).decode().strip()
    )


def _tree(root: Path, revision: str) -> str:
    return (
        _git(root, ["rev-parse", "--verify", f"{revision}^{{tree}}"]).decode().strip()
    )


def _show(root: Path, revision: str, path: str) -> bytes:
    safe = Path(path)
    if not isinstance(path, str) or safe.is_absolute() or ".." in safe.parts:
        raise CandidateError("custody path escaped repository")
    return _git(root, ["show", f"{revision}:{path}"])


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


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


def _validate_manifest(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "program_id",
        "candidate_id",
        "candidate_freeze",
        "role_order",
        "files",
        "runtime",
        "aq",
    }:
        raise CandidateError("candidate manifest is not closed")
    if _has_placeholder(value):
        raise CandidateError("candidate manifest contains an unresolved placeholder")
    if (
        value["schema_version"] != "ae-sq1-candidate-manifest-v1"
        or value["program_id"] != PROGRAM_ID
        or value["candidate_id"] != CANDIDATE_ID
    ):
        raise CandidateError("candidate manifest belongs to another program or version")
    freeze = value["candidate_freeze"]
    if (
        not isinstance(freeze, dict)
        or set(freeze) != {"commit", "tree"}
        or not isinstance(freeze["commit"], str)
        or HEX40.fullmatch(freeze["commit"]) is None
        or not isinstance(freeze["tree"], str)
        or HEX40.fullmatch(freeze["tree"]) is None
    ):
        raise CandidateError("candidate freeze is unresolved")
    if value["role_order"] != list(ROLE_ORDER):
        raise CandidateError("candidate role order drift")
    files = value["files"]
    if not isinstance(files, list) or len(files) != len(ROLE_PATHS):
        raise CandidateError("candidate role ledger is incomplete")
    for row, (role, path) in zip(files, ROLE_PATHS, strict=True):
        if (
            not isinstance(row, dict)
            or set(row) != {"role", "commit", "tree", "path", "blob", "sha256"}
            or row.get("role") != role
            or not isinstance(row.get("commit"), str)
            or HEX40.fullmatch(row["commit"]) is None
            or not isinstance(row.get("tree"), str)
            or HEX40.fullmatch(row["tree"]) is None
            or row.get("path") != path
            or not isinstance(row.get("blob"), str)
            or HEX40.fullmatch(row["blob"]) is None
            or not isinstance(row.get("sha256"), str)
            or HEX64.fullmatch(row["sha256"]) is None
        ):
            raise CandidateError("candidate role binding is incomplete or reordered")
        if role not in EARLIER_AUTHORITY_ROLES and (
            row["commit"] != freeze["commit"] or row["tree"] != freeze["tree"]
        ):
            raise CandidateError(
                "candidate component role is outside the component freeze"
            )
    runtime = value["runtime"]
    if runtime != {
        "cli_lifecycle": "codex-cli 0.147.x",
        "model": "gpt-5.5",
        "reasoning": "medium",
        "fallback": False,
        "sandbox": "read-only",
        "approval_policy": "never",
        "ephemeral": True,
        "ignore_user_config": True,
        "ignore_rules": True,
        "strict_config": True,
        "assessor_calls_per_presentation": 4,
        "max_concurrency": 8,
    }:
        raise CandidateError("candidate runtime contract drift")
    aq = value["aq"]
    if aq != {
        "canary_presentations": 1,
        "canary_calls": 4,
        "batch_presentations": 80,
        "batch_calls": 320,
        "normal_max_calls": 324,
        "canary_retry_limit": 1,
        "retry_before_any_observation_only": True,
        "batch_retry_limit": 0,
        "completed_work_is_scored": True,
        "raw_trajectory_persistence": False,
        "aggregate_usage_required": True,
    }:
        raise CandidateError("candidate AQ contract drift")
    return value


def load_verified_candidate(
    root: Path | str,
    manifest_commit: str,
    *,
    require_live: bool = True,
) -> dict[str, Any]:
    """Load a later manifest while verifying all roles at its earlier freeze."""
    repository = Path(root).resolve(strict=True)
    commit = _commit(repository, manifest_commit)
    manifest_raw = _show(repository, commit, MANIFEST_PATH)
    manifest = _validate_manifest(_closed_json(manifest_raw, "candidate manifest"))
    if require_live:
        destination = repository / MANIFEST_PATH
        try:
            live_manifest = destination.read_bytes()
        except OSError as error:
            raise CandidateError(
                "candidate manifest is absent from live checkout"
            ) from error
        if destination.is_symlink() or live_manifest != manifest_raw:
            raise CandidateError("candidate manifest has live byte drift")
    freeze = manifest["candidate_freeze"]
    frozen_commit = _commit(repository, freeze["commit"])
    frozen_tree = _tree(repository, frozen_commit)
    if frozen_commit != freeze["commit"] or frozen_tree != freeze["tree"]:
        raise CandidateError("candidate freeze commit/tree mismatch")
    documents: dict[str, Any] = {}
    trusted_json: dict[str, tuple[bytes, str]] = {}
    bindings: dict[str, dict[str, str]] = {}
    for row in manifest["files"]:
        role_commit = _commit(repository, row["commit"])
        role_tree = _tree(repository, role_commit)
        if role_commit != row["commit"] or role_tree != row["tree"]:
            raise CandidateError("candidate role commit/tree mismatch")
        raw = _show(repository, role_commit, row["path"])
        blob = (
            _git(repository, ["rev-parse", f"{role_commit}:{row['path']}"])
            .decode()
            .strip()
        )
        if blob != row["blob"] or _sha(raw) != row["sha256"]:
            raise CandidateError("candidate role digest mismatch")
        if require_live:
            destination = repository / row["path"]
            try:
                live = destination.read_bytes()
            except OSError as error:
                raise CandidateError(
                    "candidate role is absent from live checkout"
                ) from error
            if destination.is_symlink() or live != raw:
                raise CandidateError("candidate role has live byte drift")
        if row["role"] in JSON_ROLES:
            documents[row["role"]] = _closed_json(raw, row["role"])
            trusted_json[row["role"]] = (raw, row["sha256"])
        else:
            documents[row["role"]] = raw
        bindings[row["role"]] = {
            "commit": role_commit,
            "tree": role_tree,
            "path": row["path"],
            "blob": row["blob"],
            "sha256": row["sha256"],
        }
    return {
        "program_id": PROGRAM_ID,
        "candidate_id": CANDIDATE_ID,
        "manifest_commit": commit,
        "manifest_tree": _tree(repository, commit),
        "manifest_path": MANIFEST_PATH,
        "manifest_sha256": _sha(manifest_raw),
        "candidate_commit": frozen_commit,
        "candidate_tree": frozen_tree,
        "manifest": manifest,
        "documents": documents,
        "trusted_json": trusted_json,
        "bindings": bindings,
    }


def provisional_hashes(root: Path | str) -> dict[str, str]:
    """Return current role hashes for freeze preparation; never qualifies them."""
    repository = Path(root).resolve(strict=True)
    result: dict[str, str] = {}
    for role, path in ROLE_PATHS:
        destination = repository / path
        if destination.is_symlink() or not destination.is_file():
            result[role] = "UNAVAILABLE"
        else:
            result[role] = _sha(destination.read_bytes())
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest-commit")
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
    if args.manifest_commit is None:
        parser.error(
            "--manifest-commit is required unless --provisional-hashes is used"
        )
    profile = load_verified_candidate(
        args.root,
        args.manifest_commit,
        require_live=args.require_live,
    )
    print(
        json.dumps(
            {
                "status": "pass",
                "program_id": profile["program_id"],
                "candidate_id": profile["candidate_id"],
                "candidate_commit": profile["candidate_commit"],
                "candidate_tree": profile["candidate_tree"],
                "manifest_sha256": profile["manifest_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
