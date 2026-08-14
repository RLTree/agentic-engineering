#!/usr/bin/env python3
"""One-shot AE-SQ9 F3 verifier and same-process F4 -> conditional F5 runner.

The only live mode claims the fixed Git-common-dir state before the first
canary model child.  It has no standalone canary, resume, retry, replacement,
or top-up path.  Raw task, capsule, event, context, and scorer material exists
only in private process memory and private temporary directories; the sole
terminal projection is the four-field aggregate result schema.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import platform
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterator, Mapping, Sequence

from jsonschema import Draft202012Validator

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "AE-SQ9"
CANDIDATE_ID = "AE-SQ9-SLEC-9"
MODEL = "gpt-5.5"
REASONING = "medium"
CLI_VERSION = "codex-cli 0.147.0"
CLI_SHA256 = "19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37"
RUN_MANIFEST_PATH = "evals/ae-sq9/f2/run-manifest.json"
F1B_FREEZE_PATH = "evals/ae-sq9/f1/repaired-freeze.json"
F1G_RECEIPT_PATH = "evals/ae-sq9/f1/author-template-gate.json"
F3_RECORD_PATH = "evals/ae-sq9/f3/preflight.json"
F6_RESULT_PATH = "evals/ae-sq9/f6/aggregate-result.json"
CHECKER_PATH = "scripts/check_ae_sq9_candidate.py"
RUNNER_PATH = "scripts/run_ae_sq9_aq.py"
USAGE_APPROVAL = "ae-sq9-authorized-canary-and-conditional-batch"
SLOT_ORDER = ("s0", "s1", "s2", "s3")
CONDITIONS = ("current", "reduced")
CANARY_CALLS = 4
BATCH_PRESENTATIONS = 80
BATCH_CALLS = 320
HARD_CALL_CEILING = 324
PREFLIGHT_TIMEOUT_SECONDS = 30
CHILD_TIMEOUT_SECONDS = 600
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
LIFECYCLES = frozenset({"none", "confirmed", "indeterminate"})
EVENT_KEYS = (
    "effect_requested",
    "effect_granted",
    "claim_requested",
    "claim_granted",
    "tool_requested",
    "tool_granted",
)
AUTHOR_PROVENANCE_KEYS = (
    "provenance_version",
    "split_id",
    "author_id",
    "commit",
    "tree",
    "parent_f1g_commit",
    "path",
    "blob",
    "raw_sha256",
    "content_sha256",
    "case_count",
    "other_split_route_permitted",
    "predecessor_material_route_permitted",
    "diagnostic_or_live_result_route_permitted",
    "outcome_route_permitted",
    "claim_ceiling",
)
AUTHOR_CLAIM_CEILING = (
    "git-object-and-orchestrator-attested-route-custody-only-"
    "not-human-identity-or-off-git-observation"
)
VALIDATOR_CLAIM_CEILING = (
    "git-object-and-orchestrator-attested-validator-route-only-"
    "not-human-identity-or-off-git-observation"
)
DISABLED_FEATURES = (
    "apps",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "chronicle",
    "code_mode",
    "computer_use",
    "enable_mcp_apps",
    "goals",
    "hooks",
    "image_generation",
    "in_app_browser",
    "memories",
    "multi_agent",
    "multi_agent_v2",
    "plugins",
    "recommended_plugins",
    "remote_plugin",
    "request_permissions_tool",
    "shell_tool",
    "skill_mcp_dependency_install",
    "skill_search",
    "standalone_web_search",
    "tool_suggest",
    "unified_exec",
    "view_image",
    "workspace_dependencies",
)
CONFIG_OVERRIDES = (
    f'model="{MODEL}"',
    f'model_reasoning_effort="{REASONING}"',
    'web_search="disabled"',
    "skills.bundled.enabled=false",
    "skills.include_instructions=false",
    "include_permissions_instructions=false",
    "include_apps_instructions=false",
    "include_collaboration_mode_instructions=false",
    "include_environment_context=false",
    "mcp_servers={}",
)


class RunnerError(RuntimeError):
    """The qualification runner cannot continue inside frozen authority."""


class PreflightError(RunnerError):
    """A zero-model or immutable-custody prerequisite failed."""


class CallFailure(RunnerError):
    """One counted child call did not produce a confirmed valid capsule."""

    def __init__(self, message: str, lifecycle: str):
        super().__init__(message)
        if lifecycle not in LIFECYCLES or lifecycle == "confirmed":
            raise ValueError("call failure lifecycle must be none or indeterminate")
        self.lifecycle = lifecycle


@dataclass(frozen=True)
class InvocationOutcome:
    lifecycle: str
    capsule_raw: bytes
    capsule_sha256: str
    projected: dict[str, Any]
    context_id: str
    usage: dict[str, int]

    def __post_init__(self) -> None:
        if self.lifecycle != "confirmed":
            raise ValueError("successful invocation must have confirmed lifecycle")


@dataclass(frozen=True)
class F3Reservation:
    descriptor: int
    directory_descriptor: int
    path: Path
    parent_identity: tuple[int, ...]


@dataclass
class AttemptLedger:
    """Process-local counters; durable state intentionally has no extensions."""

    canary_attempted: int = 0
    canary_completed: int = 0
    batch_attempted: int = 0
    batch_completed: int = 0
    canary_passed: bool = False
    batch_started: bool = False

    def before_call(self, phase: str) -> None:
        """Count before invocation, including launch, rejection, and timeout."""
        if phase == "canary":
            if self.batch_started or self.canary_attempted >= CANARY_CALLS:
                raise RunnerError("canary attempt ceiling or phase order violated")
            self.canary_attempted += 1
        elif phase == "batch":
            if not self.canary_passed or not self.batch_started:
                raise RunnerError(
                    "batch call attempted before same-process canary pass"
                )
            if self.batch_attempted >= BATCH_CALLS:
                raise RunnerError("batch attempt ceiling violated")
            self.batch_attempted += 1
        else:
            raise RunnerError("unknown attempt phase")
        if self.total_attempted > HARD_CALL_CEILING:
            raise RunnerError("qualification hard call ceiling violated")

    def complete_call(self, phase: str, outcome: InvocationOutcome) -> None:
        if outcome.lifecycle != "confirmed":
            raise RunnerError("only a confirmed lifecycle can complete a call")
        if phase == "canary":
            if self.canary_completed >= self.canary_attempted:
                raise RunnerError("canary completion preceded its attempt")
            self.canary_completed += 1
        elif phase == "batch":
            if self.batch_completed >= self.batch_attempted:
                raise RunnerError("batch completion preceded its attempt")
            self.batch_completed += 1
        else:
            raise RunnerError("unknown completion phase")

    def pass_canary(self) -> None:
        if (
            self.canary_passed
            or self.canary_attempted != CANARY_CALLS
            or self.canary_completed != CANARY_CALLS
            or self.batch_started
        ):
            raise RunnerError("canary cannot pass without exact four-call closure")
        self.canary_passed = True

    def begin_batch(self) -> None:
        if not self.canary_passed or self.batch_started:
            raise RunnerError("batch cannot begin outside one same-process edge")
        self.batch_started = True

    @property
    def total_attempted(self) -> int:
        return self.canary_attempted + self.batch_attempted

    @property
    def total_completed(self) -> int:
        return self.canary_completed + self.batch_completed


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise RunnerError("value is not canonical finite UTF-8 JSON") from error


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _closed_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def strict_json(value: str | bytes) -> Any:
    return json.loads(
        value,
        object_pairs_hook=_closed_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )


def _strict_document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = strict_json(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise PreflightError(f"{label} is not strict JSON") from error
    if not isinstance(value, dict):
        raise PreflightError(f"{label} is not an object")
    return value


def _git(root: Path, args: Sequence[str], *, text: bool = False) -> Any:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=text, timeout=30
    )


def git_identity(root: Path, commit: str) -> tuple[str, str]:
    if not isinstance(commit, str) or HEX40.fullmatch(commit) is None:
        raise PreflightError("exact lowercase commit required")
    resolved = _git(root, ["rev-parse", "--verify", f"{commit}^{{commit}}"], text=True)
    tree = _git(root, ["rev-parse", "--verify", f"{commit}^{{tree}}"], text=True)
    if resolved.returncode or tree.returncode:
        raise PreflightError("Git identity is unavailable")
    result = resolved.stdout.strip(), tree.stdout.strip()
    if result[0] != commit or HEX40.fullmatch(result[1]) is None:
        raise PreflightError("Git identity is not exact")
    return result


def git_show(root: Path, commit: str, path: str) -> bytes:
    safe = Path(path)
    if safe.is_absolute() or ".." in safe.parts or not path:
        raise PreflightError("repository path escaped custody")
    result = _git(root, ["show", f"{commit}:{path}"])
    if result.returncode:
        raise PreflightError("committed input is unavailable")
    return result.stdout


def git_blob(root: Path, commit: str, path: str) -> str:
    result = _git(root, ["rev-parse", f"{commit}:{path}"], text=True)
    value = result.stdout.strip() if not result.returncode else ""
    if HEX40.fullmatch(value) is None:
        raise PreflightError("committed blob identity is unavailable")
    return value


def require_clean_exact_head(
    root: Path,
    commit: str,
    *,
    allowed_untracked: Sequence[str] = (),
) -> tuple[str, str]:
    resolved, tree = git_identity(root, commit)
    head = _git(root, ["rev-parse", "HEAD"], text=True)
    status = _git(root, ["status", "--porcelain", "--untracked-files=all"], text=True)
    status_rows = status.stdout.splitlines()
    permitted = {f"?? {path}" for path in allowed_untracked}
    if (
        head.returncode
        or status.returncode
        or head.stdout.strip() != resolved
        or set(status_rows) != permitted
    ):
        raise PreflightError("live execution requires a clean exact committed HEAD")
    return resolved, tree


def _verify_sealed(
    root: Path,
    value: Any,
    *,
    label: str,
    default_commit: str | None = None,
    default_tree: str | None = None,
) -> tuple[bytes, dict[str, str]]:
    if not isinstance(value, Mapping):
        raise PreflightError(f"{label} binding is absent")
    expected = {"commit", "tree", "path", "blob", "sha256"}
    if set(value) == {"path", "blob", "sha256"} and default_commit and default_tree:
        value = {"commit": default_commit, "tree": default_tree, **dict(value)}
    if set(value) != expected:
        raise PreflightError(f"{label} binding is not closed")
    commit, tree = git_identity(root, value["commit"])
    if tree != value["tree"]:
        raise PreflightError(f"{label} tree drift")
    raw = git_show(root, commit, value["path"])
    if (
        git_blob(root, commit, value["path"]) != value["blob"]
        or sha256_bytes(raw) != value["sha256"]
    ):
        raise PreflightError(f"{label} byte drift")
    return raw, dict(value)


class RuntimeSnapshot:
    """Private content-addressed snapshot of every runtime-readable byte."""

    def __init__(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="ae-sq9-runtime-")
        self.root = Path(self._temporary.name)
        os.chmod(self.root, 0o700)
        self._ledger: dict[str, dict[str, str]] = {}
        self._module_names: set[str] = set()
        self._sealed = False

    def add(self, binding: Mapping[str, str], raw: bytes, *, label: str) -> Path:
        if self._sealed or set(binding) != {"commit", "tree", "path", "blob", "sha256"}:
            raise PreflightError(f"{label} snapshot binding is invalid")
        path = binding["path"]
        safe = Path(path)
        if (
            safe.is_absolute()
            or ".." in safe.parts
            or sha256_bytes(raw) != binding["sha256"]
        ):
            raise PreflightError(f"{label} snapshot byte identity is invalid")
        row = dict(binding)
        existing = self._ledger.get(path)
        destination = self.root / safe
        if existing is not None:
            if existing != row or destination.read_bytes() != raw:
                raise PreflightError("runtime snapshot path collision")
            return destination
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        parent = destination.parent
        while parent != self.root:
            os.chmod(parent, 0o700)
            parent = parent.parent
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(destination, flags, 0o400)
        try:
            view = memoryview(raw)
            while view:
                count = os.write(descriptor, view)
                if count <= 0:
                    raise PreflightError("snapshot write did not progress")
                view = view[count:]
            os.fchmod(descriptor, 0o400)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        metadata = destination.lstat()
        if (
            destination.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or destination.read_bytes() != raw
        ):
            raise PreflightError("snapshot file is not exact private immutable input")
        self._ledger[path] = row
        return destination

    def seal(self) -> str:
        if not self._ledger or self._sealed:
            raise PreflightError("runtime snapshot cannot be sealed")
        self._sealed = True
        return digest(
            [{"path": path, **self._ledger[path]} for path in sorted(self._ledger)]
        )

    def close(self) -> None:
        for module_name in self._module_names:
            module = sys.modules.get(module_name)
            location = getattr(module, "__file__", None)
            if location is not None:
                try:
                    Path(location).resolve().relative_to(self.root.resolve())
                except ValueError:
                    continue
                sys.modules.pop(module_name, None)
        self._module_names.clear()
        self._temporary.cleanup()
        if self.root.exists():
            raise RunnerError("runtime snapshot cleanup failed")


def _import_snapshot_module(
    snapshot: RuntimeSnapshot, module_name: str, path: str
) -> ModuleType:
    location = snapshot.root / path
    existing = sys.modules.get(module_name)
    if existing is not None:
        existing_path = getattr(existing, "__file__", None)
        if existing_path is None or Path(existing_path).resolve() != location.resolve():
            raise PreflightError(f"ambient module poisoning detected: {module_name}")
        snapshot._module_names.add(module_name)
        return existing
    specification = importlib.util.spec_from_file_location(module_name, location)
    if specification is None or specification.loader is None:
        raise PreflightError("snapshot runtime module cannot be loaded")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    try:
        specification.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    snapshot._module_names.add(module_name)
    return module


def _load_checker(root: Path, implementation_commit: str) -> ModuleType:
    """Bootstrap the checker only from the target F1A Git object."""
    raw = git_show(root, implementation_commit, CHECKER_PATH)
    entry = _git(
        root,
        ["ls-tree", implementation_commit, "--", CHECKER_PATH],
        text=True,
    )
    fields = entry.stdout.strip().split()
    if (
        entry.returncode
        or len(fields) < 3
        or fields[0] != "100644"
        or fields[1] != "blob"
    ):
        raise PreflightError("target-frozen checker is not a regular 100644 blob")
    temporary = tempfile.TemporaryDirectory(prefix="ae-sq9-checker-")
    directory = Path(temporary.name)
    os.chmod(directory, 0o700)
    location = directory / "check_ae_sq9_candidate.py"
    descriptor = os.open(
        location,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        os.write(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    specification = importlib.util.spec_from_file_location(
        "_ae_sq9_checker_bootstrap", location
    )
    if specification is None or specification.loader is None:
        raise PreflightError("candidate checker cannot be bootstrapped")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    module._bootstrap_temporary_directory = temporary
    module._bootstrap_raw_sha256 = sha256_bytes(raw)
    return module


def _host_digest() -> str:
    return digest(
        {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        }
    )


def _scorer_binding(
    profile: Mapping[str, Any],
    corpus_sha: str,
    *,
    corpus_manifest_sha256: str,
    run_manifest_sha256: str,
    preflight_record_sha256: str,
    program_authority_sha256: str,
) -> dict[str, str]:
    bindings = profile["bindings"]
    return {
        "program_id": PROGRAM_ID,
        "candidate_id": CANDIDATE_ID,
        "candidate_commit": profile["implementation_commit"],
        "candidate_tree": profile["implementation_tree"],
        "f1_freeze_sha256": profile["freeze_sha256"],
        "corpus_manifest_sha256": corpus_manifest_sha256,
        "run_manifest_sha256": run_manifest_sha256,
        "preflight_record_sha256": preflight_record_sha256,
        "program_authority_sha256": program_authority_sha256,
        "runner_sha256": bindings["runner"]["sha256"],
        "evaluator_schema_sha256": bindings["evaluator_schema"]["sha256"],
        "scorer_sha256": bindings["scorer"]["sha256"],
        "corpus_validator_sha256": bindings[
            "corpus_validator_and_expected_authority_helper"
        ]["sha256"],
        "corpus_sha256": corpus_sha,
        "model_id": MODEL,
        "reasoning": REASONING,
        "tools_sha256": digest(
            {
                role: bindings[role]["sha256"]
                for role in (
                    "resolver_and_local_semantic_validator",
                    "runner",
                    "run_index",
                    "scorer",
                )
            }
        ),
        "host_sha256": _host_digest(),
    }


def _trusted_json_profile(profile: Mapping[str, Any]) -> dict[str, tuple[bytes, str]]:
    """Rebuild exact raw-plus-digest ingress required by SLEC-9."""
    return {
        role: (profile["raw_roles"][role], profile["bindings"][role]["sha256"])
        for role in (
            "candidate_authority",
            "capsule_schema",
            "semantic_capsule_schema",
            "resolution_schema",
            "reference_policy",
        )
    }


def _add_reference_catalog(
    root: Path, snapshot: RuntimeSnapshot, profile: Mapping[str, Any]
) -> None:
    policy = profile["documents"]["reference_policy"]
    custody = policy.get("catalog_custody")
    if not isinstance(custody, Mapping):
        raise PreflightError("reference catalog custody is absent")
    commit, tree = git_identity(root, custody.get("commit"))
    if tree != custody.get("tree"):
        raise PreflightError("reference catalog tree drift")
    rows = policy.get("capability_catalog")
    if not isinstance(rows, list) or len(rows) != 8:
        raise PreflightError("reference capability catalog is incomplete")
    seen: set[str] = set()
    for row in rows:
        file_row = row.get("file") if isinstance(row, Mapping) else None
        if not isinstance(file_row, Mapping):
            raise PreflightError("reference file binding is absent")
        path = file_row.get("path")
        if not isinstance(path, str):
            raise PreflightError("reference path is invalid")
        raw = git_show(root, commit, path)
        binding = {
            "commit": commit,
            "tree": tree,
            "path": path,
            "blob": file_row.get("git_blob_sha1"),
            "sha256": file_row.get("sha256"),
        }
        if (
            path in seen
            or git_blob(root, commit, path) != binding["blob"]
            or sha256_bytes(raw) != binding["sha256"]
            or len(raw) != file_row.get("size_bytes")
        ):
            raise PreflightError("reference catalog byte drift")
        snapshot.add(binding, raw, label="reference catalog")
        seen.add(path)


def _validate_corpus_manifest_document(
    *,
    raw: bytes,
    run_manifest: Mapping[str, Any],
    run_schema: Mapping[str, Any],
    profile: Mapping[str, Any],
    split_raws: Sequence[bytes],
    split_documents: Sequence[Mapping[str, Any]],
    inventory_raw: bytes,
    schedule_raw: bytes,
    schedule_digest: str,
    validation: Any,
    validator: ModuleType,
    f1g_commit: str,
) -> dict[str, Any]:
    """Authenticate the self-reference-free F2 corpus manifest.

    The corpus manifest cannot bind the Git commit containing itself.  F2B
    therefore binds the exact F2A commit/tree and Git blobs, while this
    document binds every semantic/raw digest inside that tree.
    """
    document = _strict_document(raw, "corpus manifest")
    if canonical_json(document) != raw:
        raise PreflightError("corpus manifest is not exact canonical UTF-8 JSON")
    definitions = run_schema.get("$defs")
    if (
        not isinstance(definitions, Mapping)
        or "corpusManifestDocument" not in definitions
    ):
        raise PreflightError("frozen corpus-manifest schema is unavailable")
    wrapper = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": "#/$defs/corpusManifestDocument",
        "$defs": dict(definitions),
    }
    if list(Draft202012Validator(wrapper).iter_errors(document)):
        raise PreflightError("corpus manifest violates its frozen closed schema")
    if (
        document["f1_freeze"] != run_manifest["f1_freeze"]
        or document["implementation_freeze"] != run_manifest["implementation_freeze"]
        or document["corpus_contract_sha256"]
        != profile["bindings"]["corpus_schema"]["sha256"]
    ):
        raise PreflightError("corpus manifest F1 custody drift")
    inventory = _strict_document(inventory_raw, "historical inventory")
    historical = document["historical_inventory"]
    if (
        historical
        != {
            "path": profile["external_bindings"]["historical_task_digests"]["path"],
            "raw_sha256": sha256_bytes(inventory_raw),
            "inventory_sha256": inventory.get("inventory_sha256"),
            "inventory_count": inventory.get("inventory_count"),
            "source_count": len(inventory.get("sources", [])),
        }
        or inventory.get("role") != "historical_digest_inventory"
    ):
        raise PreflightError("corpus manifest historical-inventory drift")
    expected_splits = []
    for split_id, path, split_raw, split_document in zip(
        ("A", "B"),
        ("evals/ae-sq9/f2/split-a.json", "evals/ae-sq9/f2/split-b.json"),
        split_raws,
        split_documents,
        strict=True,
    ):
        expected_splits.append(
            {
                "split_id": split_id,
                "path": path,
                "raw_sha256": sha256_bytes(split_raw),
                "content_sha256": validator.digest(dict(split_document)),
                "case_count": len(split_document.get("cases", [])),
            }
        )
    if document["splits"] != expected_splits:
        raise PreflightError("corpus manifest split byte/content custody drift")
    provenance = document["authoring_provenance"]
    if (
        any(not isinstance(row, dict) for row in provenance)
        or any(set(row) != set(AUTHOR_PROVENANCE_KEYS) for row in provenance)
        or [row["split_id"] for row in provenance] != ["A", "B"]
        or len({row["author_id"] for row in provenance}) != 2
        or len({row["commit"] for row in provenance}) != 2
    ):
        raise PreflightError("corpus manifest author provenance is absent or coupled")
    for expected, row, split_document in zip(
        expected_splits, provenance, split_documents, strict=True
    ):
        if (
            row["provenance_version"] != "ae-sq9-author-provenance-v1"
            or row["author_id"] != split_document.get("author_id")
            or row["parent_f1g_commit"] != f1g_commit
            or row["path"] != expected["path"]
            or row["raw_sha256"] != expected["raw_sha256"]
            or row["content_sha256"] != expected["content_sha256"]
            or row["case_count"] != expected["case_count"]
            or row["other_split_route_permitted"] is not False
            or row["predecessor_material_route_permitted"] is not False
            or row["diagnostic_or_live_result_route_permitted"] is not False
            or row["outcome_route_permitted"] is not False
            or row["claim_ceiling"] != AUTHOR_CLAIM_CEILING
        ):
            raise PreflightError("corpus manifest author provenance custody drift")
    authority = split_documents[0].get("authority")
    if authority != split_documents[1].get("authority") or not isinstance(
        authority, Mapping
    ):
        raise PreflightError("corpus split F1 authority differs")
    expected_contracts = validator.contract_digests()
    if (
        authority.get("program_id") != PROGRAM_ID
        or authority.get("candidate_id") != CANDIDATE_ID
        or authority.get("candidate_commit") != profile["implementation_commit"]
        or authority.get("candidate_tree") != profile["implementation_tree"]
        or authority.get("f1_freeze_sha256") != profile["freeze_sha256"]
        or any(authority.get(key) != value for key, value in expected_contracts.items())
    ):
        raise PreflightError("corpus split authority is not the frozen F1 candidate")
    if document["combined_corpus_sha256"] != validation.corpus_digest:
        raise PreflightError("corpus manifest combined corpus digest drift")
    schedule = _strict_document(schedule_raw, "schedule")
    if set(schedule) != {"presentations"}:
        raise PreflightError(
            "schedule document is not the exact closed presentation set"
        )
    if document["schedule"] != {
        "path": "evals/ae-sq9/f2/schedule.json",
        "raw_sha256": sha256_bytes(schedule_raw),
        "schedule_sha256": schedule_digest,
        "presentations": len(schedule.get("presentations", [])),
        "calls_per_presentation": 4,
    }:
        raise PreflightError("corpus manifest schedule custody drift")
    return document


def _verify_author_template_gate(
    *, root: Path, manifest: Mapping[str, Any], profile: Mapping[str, Any]
) -> dict[str, Any]:
    raw, binding = _verify_sealed(
        root, manifest["author_template_gate"], label="F1G author-template gate"
    )
    receipt = _strict_document(raw, "F1G author-template gate")
    if canonical_json(receipt) != raw:
        raise PreflightError("F1G receipt is not exact canonical UTF-8 JSON")
    schema = profile["documents"]["author_template_gate_schema"]
    if list(Draft202012Validator(schema).iter_errors(receipt)):
        raise PreflightError("F1G receipt violates its frozen schema")
    unsigned = dict(receipt)
    aggregate = unsigned.pop("aggregate_sha256")
    if aggregate != sha256_bytes(canonical_json(unsigned)):
        raise PreflightError("F1G receipt aggregate digest mismatch")
    parents = _git(
        root, ["rev-list", "--parents", "-n", "1", binding["commit"]], text=True
    )
    if parents.returncode or parents.stdout.split() != [
        binding["commit"],
        profile["freeze_commit"],
    ]:
        raise PreflightError("F1G is not the exact direct child of F1B")
    changed = _git(
        root,
        [
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            profile["freeze_commit"],
            binding["commit"],
        ],
        text=True,
    )
    if changed.returncode or changed.stdout.splitlines() != [F1G_RECEIPT_PATH]:
        raise PreflightError("F1G is not a receipt-only commit")
    freeze_raw = git_show(root, profile["freeze_commit"], profile["freeze_path"])
    expected_freeze = {
        "blob": git_blob(root, profile["freeze_commit"], profile["freeze_path"]),
        "commit": profile["freeze_commit"],
        "path": profile["freeze_path"],
        "sha256": sha256_bytes(freeze_raw),
        "tree": profile["freeze_tree"],
    }
    selected_reference_gate = _run_selected_reference_anchor_gate(profile)
    full_f3_boundary_gate = _run_full_f3_boundary_gate(profile)
    clean_process_f2b_gate = _run_clean_process_f2b_gate(profile)
    if (
        receipt["f1a_implementation"]
        != {
            "commit": profile["implementation_commit"],
            "tree": profile["implementation_tree"],
        }
        or receipt["f1b_freeze"] != expected_freeze
        or receipt["builder"] != profile["bindings"]["author_template_builder"]
        or receipt["validator"]
        != profile["bindings"]["corpus_validator_and_expected_authority_helper"]
        or receipt["selected_reference_anchor_gate"] != selected_reference_gate
        or receipt["full_f3_boundary_gate"] != full_f3_boundary_gate
        or receipt["clean_process_f2b_gate"] != clean_process_f2b_gate
    ):
        raise PreflightError("F1G receipt custody binding drift")
    return {"binding": binding, "raw": raw, "receipt": receipt}


def _run_clean_process_f2b_gate(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Load the target-frozen verifier and freeze its closed process contract."""
    snapshot = RuntimeSnapshot()
    module_name = "_ae_sq9_target_f2b_verifier"
    try:
        binding = profile["bindings"]["f2b_clean_child_verifier"]
        snapshot.add(
            binding,
            profile["raw_roles"]["f2b_clean_child_verifier"],
            label="target-frozen F2B verifier",
        )
        snapshot.seal()
        verifier = _import_snapshot_module(snapshot, module_name, binding["path"])
        expected = {
            "child_isolation": "new-python-process",
            "durable_state": ".ae-sq9-f2g/state.json",
            "fixture_status": "PASS",
            "fixture_test": (
                "test_ae_sq9_author_template.AuthorTemplateTests."
                "test_real_ephemeral_f1g_to_f2b_graph_passes_production_loader"
            ),
            "fixture_test_sha256": profile["bindings"]["author_template_test"][
                "sha256"
            ],
            "model_calls": 0,
            "positive_parent_resolver_preimported": "PASS",
            "production_loader": "run_ae_sq9_aq:_load_base_state",
            "red_child_resolver_preloaded": "REJECTED",
            "red_same_process_validation_then_loader": "REJECTED",
            "terminal_states": ["claimed", "completed", "invalid"],
            "verifier_path": "scripts/verify_ae_sq9_f2b.py",
        }
        actual = verifier.fixture_contract()
        actual.update(
            verifier.execute_fixture_test(
                ROOT,
                profile["bindings"]["author_template_test"]["sha256"],
            )
        )
        if actual != expected:
            raise PreflightError("clean-process F2B verifier contract drift")
        return expected
    except PreflightError:
        raise
    except Exception as error:
        raise PreflightError("clean-process F2B verifier contract drift") from error
    finally:
        snapshot.close()
        sys.modules.pop(module_name, None)


def _run_full_f3_boundary_gate(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Execute the exact target-frozen production F3 boundary without corpus data."""
    snapshot = RuntimeSnapshot()
    module_name = "_ae_sq9_target_f3_boundary"
    quarantined = sys.modules.pop(module_name, None)
    try:
        runner_binding = profile["bindings"]["runner"]
        snapshot.add(
            runner_binding,
            profile["raw_roles"]["runner"],
            label="target-frozen runner",
        )
        snapshot.seal()
        target = _import_snapshot_module(
            snapshot,
            module_name,
            runner_binding["path"],
        )
        result = target.full_f3_boundary_fixture(
            profile["documents"]["preflight_schema"]
        )
        expected = {
            "fixture": "synthetic-zero-corpus-zero-model-closed-receipt",
            "production_boundary": "_execute_f3_boundary",
            "production_checks": "_f3_checks",
            "production_one_shot_builder": "build_f3_record",
            "positive": {
                "all_checks_true": True,
                "model_calls": 0,
                "status": "PASS",
            },
            "red_top_level_only": {
                "error": "validation_receipt_validator_identity",
                "status": "REJECTED",
            },
            "red_missing_nested": {
                "error": "validation_receipt_validator_identity",
                "status": "REJECTED",
            },
            "red_wrong_nested_placement": {
                "error": "validation_receipt_validator_identity",
                "status": "REJECTED",
            },
        }
        if result != expected:
            raise PreflightError("full target-frozen F3 boundary gate failed")
        return expected
    except PreflightError:
        raise
    except Exception as error:
        raise PreflightError("full target-frozen F3 boundary gate failed") from error
    finally:
        snapshot.close()
        if quarantined is not None and module_name not in sys.modules:
            sys.modules[module_name] = quarantined


def _run_selected_reference_anchor_gate(
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    """Run the synthetic anchor gate from exact target-frozen F1A bytes."""
    snapshot = RuntimeSnapshot()
    quarantined = {
        name: sys.modules.pop(name)
        for name in ("resolve_ae_sq9_slec", "validate_ae_sq9_corpus")
        if name in sys.modules
    }
    try:
        for role, binding in profile["bindings"].items():
            snapshot.add(binding, profile["raw_roles"][role], label=role)
        snapshot.seal()
        _import_snapshot_module(
            snapshot,
            "resolve_ae_sq9_slec",
            profile["bindings"]["resolver_and_local_semantic_validator"]["path"],
        )
        validator = _import_snapshot_module(
            snapshot,
            "validate_ae_sq9_corpus",
            profile["bindings"]["corpus_validator_and_expected_authority_helper"][
                "path"
            ],
        )
        result = validator.selected_reference_anchor_fixture()
        expected = {
            "production_validator": (
                "validate_corpora:selected_reference_anchors_valid"
            ),
            "production_resolver": "resolve_expected_capsules",
            "positive": {"status": "PASS"},
            "red_missing": {
                "error": "selected_reference_anchor",
                "status": "REJECTED",
            },
            "red_wrong": {
                "error": "selected_reference_anchor",
                "status": "REJECTED",
            },
        }
        if result != expected:
            raise PreflightError("selected-reference-anchor production gate failed")
        return expected
    except PreflightError:
        raise
    except Exception as error:
        raise PreflightError(
            "selected-reference-anchor production gate failed"
        ) from error
    finally:
        snapshot.close()
        for name, module in quarantined.items():
            if name not in sys.modules:
                sys.modules[name] = module


def _verify_author_provenance(
    *,
    root: Path,
    profile: Mapping[str, Any],
    corpus_commit: str,
    corpus_tree: str,
    corpus_manifest: Mapping[str, Any],
    split_bindings: Sequence[Mapping[str, str]],
    split_raws: Sequence[bytes],
    f1g_commit: str,
) -> bool:
    """Prove the approved F1G -> two isolated authors -> F2A merge topology."""
    rows = corpus_manifest["authoring_provenance"]
    if not isinstance(rows, list) or len(rows) != 2:
        raise PreflightError("author provenance rows are unavailable")
    f2a_parents = _git(
        root, ["rev-list", "--parents", "-n", "1", corpus_commit], text=True
    )
    expected_f2a = [
        corpus_commit,
        f1g_commit,
        rows[0]["commit"],
        rows[1]["commit"],
    ]
    if f2a_parents.returncode or f2a_parents.stdout.split() != expected_f2a:
        raise PreflightError("F2A is not the exact ordered three-parent author merge")
    if git_identity(root, corpus_commit)[1] != corpus_tree:
        raise PreflightError("F2A author merge tree drift")

    for row, binding, raw in zip(rows, split_bindings, split_raws, strict=True):
        commit, tree = git_identity(root, row["commit"])
        if commit != row["commit"] or tree != row["tree"]:
            raise PreflightError("author provenance commit/tree drift")
        parents = _git(root, ["rev-list", "--parents", "-n", "1", commit], text=True)
        if parents.returncode or parents.stdout.split() != [
            commit,
            f1g_commit,
        ]:
            raise PreflightError("author commit is not a direct F1G child")
        changed = _git(
            root,
            [
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                f1g_commit,
                commit,
            ],
            text=True,
        )
        if changed.returncode or changed.stdout.splitlines() != [row["path"]]:
            raise PreflightError("author commit delta is not one isolated split")
        author_raw = git_show(root, commit, row["path"])
        if (
            row["parent_f1g_commit"] != f1g_commit
            or row["blob"] != git_blob(root, commit, row["path"])
            or row["blob"] != git_blob(root, corpus_commit, row["path"])
            or row["blob"] != binding["blob"]
            or row["raw_sha256"] != sha256_bytes(author_raw)
            or row["raw_sha256"] != binding["sha256"]
            or author_raw != raw
            or git_show(root, corpus_commit, row["path"]) != raw
        ):
            raise PreflightError("author split bytes are not preserved in F2A")
    return True


def _verify_validation_receipt(
    *,
    manifest: Mapping[str, Any],
    profile: Mapping[str, Any],
    corpus_commit: str,
    corpus_tree: str,
    corpus_manifest: Mapping[str, Any],
    split_bindings: Sequence[Mapping[str, str]],
    split_documents: Sequence[Mapping[str, Any]],
    validator: ModuleType,
    f1g: Mapping[str, Any],
    corpus_manifest_binding: Mapping[str, str],
    schedule_binding: Mapping[str, str],
) -> bool:
    """Bind the validator-only F2B receipt to exact F2A and F1 validator bytes."""
    receipt = manifest["validation_receipt"]
    provenance = corpus_manifest["authoring_provenance"]
    expected_authors = []
    for row, binding, document in zip(
        provenance, split_bindings, split_documents, strict=True
    ):
        expected_authors.append(
            {
                "author_id": row["author_id"],
                "blob": binding["blob"],
                "commit": row["commit"],
                "content_sha256": validator.digest(dict(document)),
                "path": binding["path"],
                "raw_sha256": binding["sha256"],
                "tree": row["tree"],
            }
        )
    expected_artifacts = [
        {
            "blob": corpus_manifest_binding["blob"],
            "content_or_semantic_sha256": corpus_manifest["combined_corpus_sha256"],
            "path": corpus_manifest_binding["path"],
            "raw_sha256": corpus_manifest_binding["sha256"],
        },
        {
            "blob": split_bindings[0]["blob"],
            "content_or_semantic_sha256": validator.digest(dict(split_documents[0])),
            "path": split_bindings[0]["path"],
            "raw_sha256": split_bindings[0]["sha256"],
        },
        {
            "blob": split_bindings[1]["blob"],
            "content_or_semantic_sha256": validator.digest(dict(split_documents[1])),
            "path": split_bindings[1]["path"],
            "raw_sha256": split_bindings[1]["sha256"],
        },
        {
            "blob": schedule_binding["blob"],
            "content_or_semantic_sha256": corpus_manifest["schedule"][
                "schedule_sha256"
            ],
            "path": schedule_binding["path"],
            "raw_sha256": schedule_binding["sha256"],
        },
    ]
    expected_f1b = {
        "blob": manifest["f1_freeze"]["blob"],
        "commit": profile["freeze_commit"],
        "path": profile["freeze_path"],
        "sha256": profile["freeze_sha256"],
        "tree": profile["freeze_tree"],
    }
    unsigned = dict(receipt)
    aggregate = unsigned.pop("aggregate_sha256", None)
    if (
        receipt["receipt_version"] != "ae-sq9-independent-validation-v1"
        or receipt["status"] != "PASS"
        or receipt["errors"] != []
        or receipt["holds"] != []
        or receipt["f1a_implementation"]
        != {
            "commit": profile["implementation_commit"],
            "role_ledger_sha256": profile["role_ledger_sha256"],
            "tree": profile["implementation_tree"],
        }
        or receipt["f1b_freeze"] != expected_f1b
        or receipt["f1g_gate"] != f1g["binding"]
        or receipt["f2a_corpus"]
        != {
            "commit": corpus_commit,
            "ordered_parents": [
                f1g["binding"]["commit"],
                provenance[0]["commit"],
                provenance[1]["commit"],
            ],
            "tree": corpus_tree,
        }
        or receipt["author_commits"] != expected_authors
        or len({row["author_id"] for row in expected_authors}) != 2
        or receipt["artifacts"] != expected_artifacts
        or receipt["validator"]
        != {
            "blob": profile["bindings"][
                "corpus_validator_and_expected_authority_helper"
            ]["blob"],
            "commit": profile["implementation_commit"],
            "path": profile["bindings"][
                "corpus_validator_and_expected_authority_helper"
            ]["path"],
            "raw_sha256": profile["bindings"][
                "corpus_validator_and_expected_authority_helper"
            ]["sha256"],
            "tree": profile["implementation_tree"],
            "validator_id": "independent-nonauthor-validator",
        }
        or receipt["authorship_performed"] is not False
        or receipt["claim_ceiling"] != VALIDATOR_CLAIM_CEILING
        or aggregate != sha256_bytes(canonical_json(unsigned))
    ):
        raise PreflightError("independent validation receipt custody drift")
    return True


def _load_base_state(
    root: Path,
    run_commit: str,
    *,
    live_commit: str | None = None,
    reserved_f3: bool = False,
    preauthor: bool = False,
) -> dict[str, Any]:
    """Load the exact F1G preauthor gate or the frozen F2 qualification run."""
    commit, tree = git_identity(root, run_commit)
    current = live_commit if live_commit is not None else run_commit
    require_clean_exact_head(
        root,
        current,
        allowed_untracked=(F3_RECORD_PATH,) if reserved_f3 else (),
    )
    if preauthor:
        parents = _git(root, ["rev-list", "--parents", "-n", "1", commit], text=True)
        fields = parents.stdout.split() if not parents.returncode else []
        if len(fields) != 2 or fields[0] != commit:
            raise PreflightError("F1G is not an exact direct child")
        f1b = fields[1]
        freeze_raw = git_show(root, f1b, F1B_FREEZE_PATH)
        freeze_document = _strict_document(freeze_raw, "F1B freeze")
        implementation = freeze_document.get("implementation_freeze")
        if not isinstance(implementation, Mapping) or not isinstance(
            implementation.get("commit"), str
        ):
            raise PreflightError("F1B lacks the F1A bootstrap identity")
        checker = _load_checker(root, implementation["commit"])
        try:
            profile = checker.load_verified_candidate(
                root, f1b, require_live=True, live_commit=commit
            )
        except Exception as error:
            raise PreflightError("F1B candidate custody failed") from error
        binding = {
            "blob": git_blob(root, commit, F1G_RECEIPT_PATH),
            "commit": commit,
            "path": F1G_RECEIPT_PATH,
            "sha256": sha256_bytes(git_show(root, commit, F1G_RECEIPT_PATH)),
            "tree": tree,
        }
        f1g = _verify_author_template_gate(
            root=root,
            manifest={"author_template_gate": binding},
            profile=profile,
        )
        return {
            "root": root,
            "commit": commit,
            "tree": tree,
            "profile": profile,
            "f1g": f1g,
            "preauthor_verified": True,
        }
    manifest_raw = git_show(root, commit, RUN_MANIFEST_PATH)
    manifest = _strict_document(manifest_raw, "run manifest")
    if canonical_json(manifest) != manifest_raw:
        raise PreflightError("run manifest is not exact canonical UTF-8 JSON")
    freeze = manifest.get("f1_freeze")
    if not isinstance(freeze, Mapping) or not isinstance(freeze.get("commit"), str):
        raise PreflightError("run manifest lacks F1B bootstrap identity")
    implementation = manifest.get("implementation_freeze")
    if not isinstance(implementation, Mapping) or not isinstance(
        implementation.get("commit"), str
    ):
        raise PreflightError("run manifest lacks F1A bootstrap identity")
    checker = _load_checker(root, implementation["commit"])
    try:
        profile = checker.load_verified_candidate(
            root,
            freeze["commit"],
            require_live=True,
            live_commit=current,
        )
    except Exception as error:
        raise PreflightError("F1B candidate custody failed") from error
    if (
        checker._bootstrap_raw_sha256
        != profile["bindings"]["candidate_checker"]["sha256"]
    ):
        raise PreflightError("target-frozen checker byte binding drift")
    schema = profile["documents"]["run_manifest_schema"]
    if list(Draft202012Validator(schema).iter_errors(manifest)):
        raise PreflightError("run manifest violates the frozen schema")
    if manifest["f1_freeze"]["path"] != profile["freeze_path"]:
        raise PreflightError("run manifest F1B path drift")
    f1g = _verify_author_template_gate(root=root, manifest=manifest, profile=profile)
    f1g_binding = f1g["binding"]
    run_parents = _git(root, ["rev-list", "--parents", "-n", "1", commit], text=True)
    if run_parents.returncode:
        raise PreflightError("F2B ancestry is unavailable")
    run_fields = run_parents.stdout.split()
    if len(run_fields) != 2:
        raise PreflightError("F2B is not a single-parent run-manifest commit")
    f2a = run_fields[1]
    run_changed = _git(
        root,
        ["diff-tree", "--no-commit-id", "--name-only", "-r", f2a, commit],
        text=True,
    )
    if run_changed.returncode or run_changed.stdout.splitlines() != [RUN_MANIFEST_PATH]:
        raise PreflightError("F2B is not the exact manifest-only child of F2A")
    freeze_raw, freeze_binding = _verify_sealed(
        root, manifest["f1_freeze"], label="F1B freeze"
    )
    if (
        freeze_binding["commit"] != profile["freeze_commit"]
        or freeze_binding["sha256"] != profile["freeze_sha256"]
        or freeze_raw
        != git_show(root, profile["freeze_commit"], profile["freeze_path"])
        or manifest["implementation_freeze"]
        != {
            "commit": profile["implementation_commit"],
            "tree": profile["implementation_tree"],
        }
    ):
        raise PreflightError("run manifest F1 custody drift")
    corpus_commit, corpus_tree = git_identity(root, manifest["corpus_freeze"]["commit"])
    if corpus_commit != f2a or corpus_tree != manifest["corpus_freeze"]["tree"]:
        raise PreflightError("corpus freeze tree drift")
    f2a_parents = _git(
        root, ["rev-list", "--parents", "-n", "1", corpus_commit], text=True
    )
    f2a_fields = f2a_parents.stdout.split()
    if (
        f2a_parents.returncode
        or len(f2a_fields) != 4
        or f2a_fields[:2] != [corpus_commit, f1g_binding["commit"]]
    ):
        raise PreflightError("F2A is not a three-parent merge rooted at passing F1G")
    f2_delta = _git(
        root,
        ["diff", "--name-only", f1g_binding["commit"], corpus_commit],
        text=True,
    )
    authorized_f2a_paths = {
        "evals/ae-sq9/f2/corpus-manifest.json",
        "evals/ae-sq9/f2/schedule.json",
        "evals/ae-sq9/f2/split-a.json",
        "evals/ae-sq9/f2/split-b.json",
    }
    if f2_delta.returncode or set(f2_delta.stdout.splitlines()) != authorized_f2a_paths:
        raise PreflightError("F1B-to-F2A cumulative artifact closure drift")
    corpus = manifest["corpus"]
    exact_f2_paths = {
        "manifest": "evals/ae-sq9/f2/corpus-manifest.json",
        "split_a": "evals/ae-sq9/f2/split-a.json",
        "split_b": "evals/ae-sq9/f2/split-b.json",
    }
    for field, expected_path in exact_f2_paths.items():
        if corpus[field].get("path") != expected_path:
            raise PreflightError("run manifest F2 corpus path drift")
    if (
        corpus["schema"] != profile["bindings"]["corpus_schema"]
        or corpus["historical_inventory"]
        != profile["external_bindings"]["historical_task_digests"]
    ):
        raise PreflightError("run manifest F1A schema/history binding drift")
    if manifest["schedule"]["document"].get("path") != "evals/ae-sq9/f2/schedule.json":
        raise PreflightError("run manifest schedule path drift")
    manifest_document_raw, corpus_manifest_binding = _verify_sealed(
        root,
        corpus["manifest"],
        label="corpus manifest",
        default_commit=corpus_commit,
        default_tree=corpus_tree,
    )
    split_a, split_a_binding = _verify_sealed(
        root,
        corpus["split_a"],
        label="split A",
        default_commit=corpus_commit,
        default_tree=corpus_tree,
    )
    split_b, split_b_binding = _verify_sealed(
        root,
        corpus["split_b"],
        label="split B",
        default_commit=corpus_commit,
        default_tree=corpus_tree,
    )
    inventory_raw, inventory_binding = _verify_sealed(
        root, corpus["historical_inventory"], label="historical inventory"
    )
    schema_raw, schema_binding = _verify_sealed(
        root, corpus["schema"], label="corpus schema"
    )
    if schema_binding != profile["bindings"]["corpus_schema"]:
        raise PreflightError("run manifest corpus schema is outside F1A")
    schedule_raw, schedule_binding = _verify_sealed(
        root,
        manifest["schedule"]["document"],
        label="schedule",
        default_commit=corpus_commit,
        default_tree=corpus_tree,
    )
    schedule_document = _strict_document(schedule_raw, "schedule")
    if set(schedule_document) != {"presentations"}:
        raise PreflightError(
            "schedule document is not the exact closed presentation set"
        )
    snapshot = RuntimeSnapshot()
    try:
        for role, binding in profile["bindings"].items():
            snapshot.add(binding, profile["raw_roles"][role], label=role)
        for label, binding, raw in (
            ("corpus manifest", corpus_manifest_binding, manifest_document_raw),
            ("split A", split_a_binding, split_a),
            ("split B", split_b_binding, split_b),
            ("schedule", schedule_binding, schedule_raw),
        ):
            snapshot.add(binding, raw, label=label)
        _add_reference_catalog(root, snapshot, profile)
        snapshot_sha = snapshot.seal()
        resolver = _import_snapshot_module(
            snapshot,
            "resolve_ae_sq9_slec",
            profile["bindings"]["resolver_and_local_semantic_validator"]["path"],
        )
        validator = _import_snapshot_module(
            snapshot,
            "validate_ae_sq9_corpus",
            profile["bindings"]["corpus_validator_and_expected_authority_helper"][
                "path"
            ],
        )
        scorer = _import_snapshot_module(
            snapshot, "_ae_sq9_scorer", profile["bindings"]["scorer"]["path"]
        )
        run_index = _import_snapshot_module(
            snapshot, "_ae_sq9_run_index", profile["bindings"]["run_index"]["path"]
        )
        documents = (split_a, split_b)
        expected_authority = validator.expected_split_authority(profile)
        validation = validator.validate_corpora(
            documents,
            historical_digest_inventory=inventory_raw,
            expected_authority=expected_authority,
        )
        if not validation.passed or validation.corpus_digest is None:
            if tuple(validation.errors) == ("expected_authority_mismatch",):
                raise PreflightError(
                    "corpus split authority is not the frozen F1 candidate"
                )
            raise PreflightError(
                "fresh corpus is not qualification-ready: "
                f"errors={tuple(validation.errors)!r}, holds={tuple(validation.holds)!r}"
            )
        parsed = [validator._as_document(raw) for raw in documents]
        cases = {
            case["case_id"]: case for document in parsed for case in document["cases"]
        }
        schedule = list(validator.build_schedule(tuple(sorted(cases))))
        schedule_sha = validator.schedule_digest(schedule)
        frozen_schedule = _strict_document(schedule_raw, "schedule")
        if (
            frozen_schedule.get("presentations") != schedule
            or manifest["schedule"]["seed"] != validator.SCHEDULE_SEED
            or manifest["schedule"]["sha256"] != schedule_sha
            or manifest["schedule"]["presentations"] != BATCH_PRESENTATIONS
            or manifest["schedule"]["calls_per_presentation"] != 4
        ):
            raise PreflightError("frozen schedule drift")
        corpus_manifest_document = _validate_corpus_manifest_document(
            raw=manifest_document_raw,
            run_manifest=manifest,
            run_schema=schema,
            profile=profile,
            split_raws=(split_a, split_b),
            split_documents=parsed,
            inventory_raw=inventory_raw,
            schedule_raw=schedule_raw,
            schedule_digest=schedule_sha,
            validation=validation,
            validator=validator,
            f1g_commit=f1g_binding["commit"],
        )
        provenance_verified = _verify_author_provenance(
            root=root,
            profile=profile,
            corpus_commit=corpus_commit,
            corpus_tree=corpus_tree,
            corpus_manifest=corpus_manifest_document,
            split_bindings=(split_a_binding, split_b_binding),
            split_raws=(split_a, split_b),
            f1g_commit=f1g_binding["commit"],
        )
        validation_receipt_verified = _verify_validation_receipt(
            manifest=manifest,
            profile=profile,
            corpus_commit=corpus_commit,
            corpus_tree=corpus_tree,
            corpus_manifest=corpus_manifest_document,
            split_bindings=(split_a_binding, split_b_binding),
            split_documents=parsed,
            validator=validator,
            f1g=f1g,
            corpus_manifest_binding=corpus_manifest_binding,
            schedule_binding=schedule_binding,
        )
        state = {
            "root": root,
            "commit": commit,
            "tree": tree,
            "run_manifest": manifest,
            "run_manifest_raw": manifest_raw,
            "run_manifest_sha256": sha256_bytes(manifest_raw),
            "corpus_manifest_raw": manifest_document_raw,
            "corpus_manifest": corpus_manifest_document,
            "corpus_manifest_sha256": sha256_bytes(manifest_document_raw),
            "profile": profile,
            "snapshot": snapshot,
            "snapshot_root": snapshot.root,
            "snapshot_sha256": snapshot_sha,
            "validator": validator,
            "scorer": scorer,
            "resolver": resolver,
            "run_index_module": run_index,
            "corpus_documents": documents,
            "expected_authority": expected_authority,
            "corpus_split_documents": tuple(parsed),
            "corpus_validation": validation,
            "inventory_raw": inventory_raw,
            "inventory_binding": inventory_binding,
            "corpus_digest": validation.corpus_digest,
            "cases": cases,
            "schedule": schedule,
            "schedule_digest": schedule_sha,
            "author_provenance_verified": provenance_verified,
            "validation_receipt_verified": validation_receipt_verified,
            "f1g": f1g,
        }
        state["profile"]["trusted_json"] = _trusted_json_profile(profile)
        return state
    except Exception:
        snapshot.close()
        raise


def _synthetic_observations(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    validator = state["validator"]
    binding_sha = validator.digest(state["scorer_binding"])
    result: list[dict[str, Any]] = []
    for row in state["schedule"]:
        case = state["cases"][row["case_id"]]
        capsules = []
        for slot_id, expected in zip(
            SLOT_ORDER, case["expected_capsules"], strict=True
        ):
            capsule_raw, capsule_sha256 = validator._capsule_ingress(expected)
            capsules.append(
                {
                    "slot_id": slot_id,
                    "context_id": f"preflight-{row['presentation_index']:02d}-{slot_id}",
                    "invocation_count": 1,
                    "terminal_completed": True,
                    "capsule_raw": capsule_raw,
                    "capsule_sha256": capsule_sha256,
                    "binding_sha256": binding_sha,
                    "schedule_sha256": state["schedule_digest"],
                    "packet_sha256": validator.capsule_packet_digest(
                        binding_digest=binding_sha,
                        schedule_sha256=state["schedule_digest"],
                        condition=row["condition"],
                        case_id=row["case_id"],
                        task_sha256=case["task_text_nfc_sha256"],
                        slot_id=slot_id,
                    ),
                    "task_sha256": case["task_text_nfc_sha256"],
                }
            )
        result.append(
            {
                "presentation_index": row["presentation_index"],
                "presentation_id": row["presentation_id"],
                "condition": row["condition"],
                "case_id": row["case_id"],
                "terminal_completed": True,
                "capsules": capsules,
                "resolution": validator.resolve_expected_capsules(
                    case["task_text"], row["condition"], case["expected_capsules"]
                ),
                "events": {key: False for key in EVENT_KEYS},
            }
        )
    return result


def _event_stream(capsule_raw: bytes, *, context_id: str) -> bytes:
    message = capsule_raw.decode("utf-8", "strict")
    events = (
        {"type": "thread.started", "thread_id": context_id},
        {"type": "turn.started"},
        {
            "type": "item.completed",
            "item": {
                "id": f"{context_id}-message",
                "type": "agent_message",
                "text": message,
            },
        },
        {
            "type": "turn.completed",
            "usage": {
                "input_tokens": 1,
                "cached_input_tokens": 0,
                "output_tokens": 1,
                "total_tokens": 2,
            },
        },
    )
    return b"\n".join(canonical_json(event) for event in events) + b"\n"


def _probe_handshake(state: Mapping[str, Any]) -> bool:
    """Exercise event parsing, local semantics, fold, and reference parity."""
    explicit = next(
        case for case in state["cases"].values() if case["profile"] == "explicit"
    )
    automatic = next(
        case
        for case in state["cases"].values()
        if case["profile"] in {"single", "two"}
        and case["expected_resolution"]["reference_bundle"]
    )
    for case in (explicit, automatic):
        outcomes: list[InvocationOutcome] = []
        for slot_id, capsule in zip(SLOT_ORDER, case["expected_capsules"], strict=True):
            capsule_raw, _ = state["validator"]._capsule_ingress(capsule)
            outcome = parse_events(
                _event_stream(
                    capsule_raw, context_id=f"f3-{case['case_id']}-{slot_id}"
                ),
                resolver=state["resolver"],
                task_text=case["task_text"],
                condition="current",
                slot_id=slot_id,
                profile=state["profile"],
            )
            outcomes.append(outcome)
        actual = _parent_resolution(
            state,
            task_text=case["task_text"],
            condition="current",
            outcomes=outcomes,
        )
        expected = state["validator"].resolve_expected_capsules(
            case["task_text"], "current", case["expected_capsules"]
        )
        if actual != expected:
            return False
        if case is explicit and actual["reference_bundle"] != []:
            return False
        if (
            case is automatic
            and actual["reference_bundle"]
            != case["expected_resolution"]["reference_bundle"]
        ):
            return False
    valid_raw, _ = state["validator"]._capsule_ingress(explicit["expected_capsules"][0])
    valid_stream = _event_stream(valid_raw, context_id="f3-negative")
    valid_lines = valid_stream.splitlines()
    unknown = (
        b"\n".join(
            [
                *valid_lines[:-1],
                canonical_json({"type": "tool.completed"}),
                valid_lines[-1],
            ]
        )
        + b"\n"
    )
    try:
        parse_events(
            unknown,
            resolver=state["resolver"],
            task_text=explicit["task_text"],
            condition="current",
            slot_id="s0",
            profile=state["profile"],
        )
    except CallFailure as error:
        return error.lifecycle == "indeterminate"
    return False


def _validation_receipt_validator_id(receipt: Any) -> str:
    """Read the sole closed validator identity interface used by production F3."""
    if not isinstance(receipt, Mapping) or "validator_id" in receipt:
        raise PreflightError("validation_receipt_validator_identity")
    validator = receipt.get("validator")
    if not isinstance(validator, Mapping):
        raise PreflightError("validation_receipt_validator_identity")
    validator_id = validator.get("validator_id")
    if validator_id != "independent-nonauthor-validator":
        raise PreflightError("validation_receipt_validator_identity")
    return validator_id


def _synthetic_f3_boundary_checks(state: Mapping[str, Any]) -> dict[str, bool]:
    """Exercise every F3 check output on a closed, taskless, zero-model topology."""
    allowed = {
        "f3_gate_fixture",
        "f3_gate_bindings",
        "f3_gate_topology",
        "profile",
        "run_manifest",
    }
    if set(state) != allowed or state.get("f3_gate_fixture") is not True:
        raise PreflightError("F3 gate fixture topology is open")
    topology = state.get("f3_gate_topology")
    expected_topology = {
        "author_ids": ["synthetic-author-a", "synthetic-author-b"],
        "corpus_material_present": False,
        "model_calls": 0,
        "schedule_shape": [80, 4],
        "synthetic_case_shape": [2, 20],
        "synthetic_formula_positive": True,
        "synthetic_formula_red": True,
        "synthetic_lifecycle_closed": True,
        "synthetic_provider_closed": True,
        "synthetic_raw_persistence": False,
        "synthetic_retry_calls": 0,
        "synthetic_schema_closed": True,
        "synthetic_one_shot_unclaimed": True,
    }
    if topology != expected_topology:
        raise PreflightError("F3 gate fixture topology is open")
    receipt = state["run_manifest"].get("validation_receipt")
    validator_id = _validation_receipt_validator_id(receipt)
    checks = {
        "exact_custody": topology["corpus_material_present"] is False,
        "provider_subset_and_local_semantics": topology["synthetic_provider_closed"],
        "recursive_schema_closure": topology["synthetic_schema_closed"],
        "independent_two_by_twenty": (
            topology["synthetic_case_shape"] == [2, 20]
            and len(set(topology["author_ids"])) == 2
            and validator_id not in set(topology["author_ids"])
        ),
        "forty_unique_cases": topology["synthetic_case_shape"] == [2, 20],
        "eighty_by_four_schedule": topology["schedule_shape"] == [80, 4],
        "formula_totality_and_global_and": (
            topology["synthetic_formula_positive"] is True
            and topology["synthetic_formula_red"] is True
        ),
        "lifecycle_event_and_counter_closure": topology["synthetic_lifecycle_closed"],
        "zero_retry_and_aggregate_only": (
            topology["synthetic_retry_calls"] == 0 and topology["model_calls"] == 0
        ),
        "zero_raw_persistence": topology["synthetic_raw_persistence"] is False,
        "one_shot_state_unclaimed": topology["synthetic_one_shot_unclaimed"],
    }
    if not all(checks.values()):
        raise PreflightError("F3 check conjunction failed")
    return checks


def _f3_checks(state: Mapping[str, Any]) -> dict[str, bool]:
    if state.get("f3_gate_fixture") is True:
        return _synthetic_f3_boundary_checks(state)
    run_index = state["run_index_module"]
    run_index.assert_unclaimed(state["root"])
    one_shot_unclaimed = not run_index.state_path(state["root"]).exists()
    if "scorer_binding" not in state:
        # The F3 record cannot contain its own byte digest.  Its zero-model
        # scorer proof therefore uses a fixed domain-separated pending value;
        # live execution rebuilds the binding from the committed F3 bytes.
        state["scorer_binding"] = _scorer_binding(
            state["profile"],
            state["corpus_digest"],
            corpus_manifest_sha256=state["corpus_manifest_sha256"],
            run_manifest_sha256=state["run_manifest_sha256"],
            preflight_record_sha256=sha256_bytes(b"AE-SQ9-F3-PENDING"),
            program_authority_sha256=sha256_bytes(
                git_show(
                    state["root"],
                    "88c1b04dc049ab7656e811df9bc3f9e33276f778",
                    "evals/ae-sq9/program-authority.json",
                )
            ),
        )
    observations = _synthetic_observations(state)
    synthetic = state["scorer"].score_synthetic(
        documents=state["corpus_documents"],
        historical_digest_inventory=state["inventory_raw"],
        expected_authority=state["expected_authority"],
        observations=observations,
        binding=state["scorer_binding"],
        complete_run_assertions={
            "runner_local_raw_persistence": False,
            "heldout_outcome_use": False,
        },
    )
    state["scorer"].validate_result(
        synthetic, expected_aggregate_digest=synthetic["aggregate_digest"]
    )
    if synthetic.get("status") != "pass":
        raise PreflightError("formula-totality synthetic global AND did not pass")
    negative = copy.deepcopy(observations)
    negative[0]["capsules"][0]["capsule_sha256"] = "0" * 64
    failed = state["scorer"].score_synthetic(
        documents=state["corpus_documents"],
        historical_digest_inventory=state["inventory_raw"],
        expected_authority=state["expected_authority"],
        observations=negative,
        binding=state["scorer_binding"],
        complete_run_assertions={
            "runner_local_raw_persistence": False,
            "heldout_outcome_use": False,
        },
    )
    state["scorer"].validate_result(
        failed, expected_aggregate_digest=failed["aggregate_digest"]
    )
    if failed.get("status") != "fail":
        raise PreflightError("single-gate synthetic red did not fail global AND")
    provider = state["resolver"].validate_provider_schema(
        state["profile"]["trusted_json"]["capsule_schema"],
        state["profile"]["trusted_json"]["candidate_authority"],
    )
    explicit_case = next(
        case for case in state["cases"].values() if case["profile"] == "explicit"
    )
    capsule_raw, capsule_sha = state["validator"]._capsule_ingress(
        explicit_case["expected_capsules"][0]
    )
    normalized = state["resolver"].normalize_runtime_capsule(
        explicit_case["task_text"],
        "s0",
        (capsule_raw, capsule_sha),
        state["profile"]["trusted_json"]["candidate_authority"],
        state["profile"]["trusted_json"]["semantic_capsule_schema"],
    )
    invalid_capsule = copy.deepcopy(explicit_case["expected_capsules"][0])
    wrong_text = "X" if explicit_case["task_text"][0] != "X" else "Y"
    invalid_capsule["anchors"] = [{"start": 0, "end": 1, "text": wrong_text}]
    invalid_raw, invalid_sha = state["validator"]._capsule_ingress(invalid_capsule)
    local_semantics_closed = False
    try:
        state["resolver"].normalize_runtime_capsule(
            explicit_case["task_text"],
            "s0",
            (invalid_raw, invalid_sha),
            state["profile"]["trusted_json"]["candidate_authority"],
            state["profile"]["trusted_json"]["semantic_capsule_schema"],
        )
    except Exception:
        local_semantics_closed = True
    malformed_provider = copy.deepcopy(provider)
    malformed_provider["minimum"] = 0
    recursive_closed = False
    try:
        state["resolver"]._lint_provider_node(
            malformed_provider, root=malformed_provider
        )
    except Exception:
        recursive_closed = True
    ledger = AttemptLedger()
    for _ in SLOT_ORDER:
        ledger.before_call("canary")
        ledger.complete_call(
            "canary",
            InvocationOutcome(
                "confirmed",
                capsule_raw,
                capsule_sha,
                normalized,
                "f3-ledger",
                {
                    "input_tokens": 0,
                    "cached_input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                },
            ),
        )
    ledger.pass_canary()
    ledger.begin_batch()
    counter_closed = False
    ledger.batch_attempted = BATCH_CALLS
    try:
        ledger.before_call("batch")
    except RunnerError:
        counter_closed = ledger.total_attempted == HARD_CALL_CEILING
    public = state["scorer"].project_result(synthetic)
    state["scorer"].validate_result_public(
        public,
        expected_aggregate_digest=synthetic["aggregate_digest"],
        expected_status="PASS" if synthetic["status"] == "pass" else "FAIL",
    )
    private_probe = RuntimeSnapshot()
    probe_binding = state["profile"]["bindings"]["result_schema"]
    private_probe.add(
        probe_binding,
        state["profile"]["raw_roles"]["result_schema"],
        label="F3 cleanup probe",
    )
    probe_root = private_probe.root
    private_probe.seal()
    private_probe.close()
    split_documents = state["corpus_split_documents"]
    checks = {
        "exact_custody": (
            state["corpus_manifest_sha256"]
            == sha256_bytes(state["corpus_manifest_raw"])
            and state["snapshot"]._sealed is True
            and isinstance(state["corpus_manifest"], dict)
            and state["author_provenance_verified"] is True
            and state["validation_receipt_verified"] is True
        ),
        "provider_subset_and_local_semantics": (
            tuple(normalized) == ("slot_id", "local_need", "reference_need")
            and normalized["slot_id"] == "s0"
            and local_semantics_closed
        ),
        "recursive_schema_closure": recursive_closed,
        "independent_two_by_twenty": (
            len(split_documents) == 2
            and all(len(document["cases"]) == 20 for document in split_documents)
            and len(
                {
                    row["author_id"]
                    for row in state["corpus_manifest"]["authoring_provenance"]
                }
            )
            == 2
            and _validation_receipt_validator_id(
                state["run_manifest"]["validation_receipt"]
            )
            not in {
                row["author_id"]
                for row in state["corpus_manifest"]["authoring_provenance"]
            }
        ),
        "forty_unique_cases": len(state["cases"]) == 40,
        "eighty_by_four_schedule": (
            len(state["schedule"]) == 80
            and state["run_manifest"]["schedule"]["calls_per_presentation"] == 4
        ),
        "formula_totality_and_global_and": synthetic["status"] == "pass"
        and failed["status"] == "fail",
        "lifecycle_event_and_counter_closure": _probe_handshake(state)
        and counter_closed,
        "zero_retry_and_aggregate_only": (
            state["run_manifest"]["execution"]["retry_calls"] == 0
            and tuple(public)
            == ("program_id", "candidate_id", "status", "aggregate_digest")
        ),
        "zero_raw_persistence": not probe_root.exists(),
        "one_shot_state_unclaimed": one_shot_unclaimed,
    }
    if not all(checks.values()):
        raise PreflightError("F3 check conjunction failed")
    return checks


def validate_f3_record(
    record: Any,
    schema: Mapping[str, Any],
    *,
    expected_bindings: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Enforce the status/check logical biconditional beyond JSON Schema."""
    if not isinstance(record, dict) or list(
        Draft202012Validator(schema).iter_errors(record)
    ):
        raise PreflightError("F3 record violates its frozen schema")
    checks = record.get("checks")
    if (
        not isinstance(checks, dict)
        or not checks
        or any(type(value) is not bool for value in checks.values())
    ):
        raise PreflightError("F3 checks are not a closed boolean conjunction")
    all_pass = all(checks.values())
    if (record.get("status") == "PASS") is not all_pass:
        raise PreflightError("F3 status is not iff the complete check conjunction")
    if expected_bindings is not None and record.get("bindings") != dict(
        expected_bindings
    ):
        raise PreflightError("F3 binding drift")
    unsigned = {
        key: value for key, value in record.items() if key != "aggregate_sha256"
    }
    if record.get("aggregate_sha256") != digest(unsigned):
        raise PreflightError("F3 aggregate digest drift")
    return record


def _stat_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_uid,
        value.st_gid,
        value.st_mode,
        value.st_nlink,
    )


def _directory_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_uid,
        value.st_gid,
        value.st_mode,
    )


def _open_pinned_directory(
    parent_descriptor: int, parent_path: Path, name: str, label: str
) -> int:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(name, flags, dir_fd=parent_descriptor)
        opened = os.fstat(descriptor)
        relative_live = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        absolute_live = (parent_path / name).lstat()
    except OSError as error:
        if descriptor != -1:
            os.close(descriptor)
        raise PreflightError(
            f"{label} cannot be pinned without following links"
        ) from error
    if (
        not stat.S_ISDIR(opened.st_mode)
        or _directory_identity(opened) != _directory_identity(relative_live)
        or _directory_identity(opened) != _directory_identity(absolute_live)
        or opened.st_uid != os.getuid()
        or stat.S_IMODE(opened.st_mode) & 0o022
    ):
        os.close(descriptor)
        raise PreflightError(f"{label} identity is unsafe")
    return descriptor


def _reserve_f3_record(root: Path) -> F3Reservation:
    try:
        repository = root.resolve(strict=True)
    except OSError as error:
        raise PreflightError("F3 repository root is unavailable") from error
    path = repository / F3_RECORD_PATH
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    root_descriptor = os.open(repository, flags)
    evals_descriptor = -1
    authority_descriptor = -1
    try:
        root_metadata = os.fstat(root_descriptor)
        if (
            _directory_identity(root_metadata)
            != _directory_identity(repository.lstat())
            or root_metadata.st_uid != os.getuid()
            or stat.S_IMODE(root_metadata.st_mode) & 0o022
        ):
            raise PreflightError("F3 repository root identity drifted")
        evals_descriptor = _open_pinned_directory(
            root_descriptor, repository, "evals", "F3 evals directory"
        )
        authority_descriptor = _open_pinned_directory(
            evals_descriptor,
            repository / "evals",
            "ae-sq9",
            "F3 authority directory",
        )
        try:
            os.mkdir("f3", 0o700, dir_fd=authority_descriptor)
        except FileExistsError:
            pass
        directory_descriptor = _open_pinned_directory(
            authority_descriptor,
            repository / "evals/ae-sq9",
            "f3",
            "F3 result directory",
        )
    finally:
        if authority_descriptor != -1:
            os.close(authority_descriptor)
        if evals_descriptor != -1:
            os.close(evals_descriptor)
        os.close(root_descriptor)
    parent_metadata = os.fstat(directory_descriptor)
    try:
        parent_live = path.parent.lstat()
    except OSError as error:
        os.close(directory_descriptor)
        raise PreflightError("F3 result directory is unavailable") from error
    if (
        path.parent.is_symlink()
        or not stat.S_ISDIR(parent_metadata.st_mode)
        or _directory_identity(parent_metadata) != _directory_identity(parent_live)
        or parent_metadata.st_uid != os.getuid()
        or stat.S_IMODE(parent_metadata.st_mode) != 0o700
    ):
        os.close(directory_descriptor)
        raise PreflightError("F3 result directory is not exact owner-only custody")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path.name, flags, 0o600, dir_fd=directory_descriptor)
    except FileExistsError as error:
        os.close(directory_descriptor)
        raise PreflightError("F3 attempt is already consumed") from error
    except OSError as error:
        os.close(directory_descriptor)
        raise PreflightError("F3 attempt reservation failed") from error
    os.fchmod(descriptor, 0o600)
    opened = os.fstat(descriptor)
    if (
        not stat.S_ISREG(opened.st_mode)
        or opened.st_uid != os.getuid()
        or opened.st_nlink != 1
        or stat.S_IMODE(opened.st_mode) != 0o600
    ):
        os.close(descriptor)
        os.close(directory_descriptor)
        raise PreflightError("F3 attempt reservation identity is unsafe")
    os.fsync(descriptor)
    os.fsync(directory_descriptor)
    return F3Reservation(
        descriptor,
        directory_descriptor,
        path,
        _directory_identity(parent_metadata),
    )


def _remark_f3_canonical(repository: Path) -> None:
    """Best-effort terminal marker after detected parent substitution.

    Same-owner deletion cannot be made impossible by a userspace file, but a
    detected race is never allowed to silently recreate a retry lane.
    """
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptors: list[int] = []
    marker = -1
    try:
        root_descriptor = os.open(repository, flags)
        descriptors.append(root_descriptor)
        root_metadata = os.fstat(root_descriptor)
        if (
            root_metadata.st_uid != os.getuid()
            or stat.S_IMODE(root_metadata.st_mode) & 0o022
            or _directory_identity(root_metadata)
            != _directory_identity(repository.lstat())
        ):
            return
        evals_descriptor = _open_pinned_directory(
            root_descriptor, repository, "evals", "F3 remark evals directory"
        )
        descriptors.append(evals_descriptor)
        authority_descriptor = _open_pinned_directory(
            evals_descriptor,
            repository / "evals",
            "ae-sq9",
            "F3 remark authority directory",
        )
        descriptors.append(authority_descriptor)
        try:
            os.mkdir("f3", 0o700, dir_fd=authority_descriptor)
        except FileExistsError:
            pass
        f3_descriptor = _open_pinned_directory(
            authority_descriptor,
            repository / "evals/ae-sq9",
            "f3",
            "F3 remark result directory",
        )
        descriptors.append(f3_descriptor)
        f3_metadata = os.fstat(f3_descriptor)
        if (
            f3_metadata.st_uid != os.getuid()
            or stat.S_IMODE(f3_metadata.st_mode) != 0o700
        ):
            return
        marker_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        marker_flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            marker = os.open(
                Path(F3_RECORD_PATH).name,
                marker_flags,
                0o600,
                dir_fd=f3_descriptor,
            )
        except FileExistsError:
            return
        os.fchmod(marker, 0o600)
        os.fsync(marker)
        os.fsync(f3_descriptor)
    except (OSError, PreflightError):
        return
    finally:
        if marker != -1:
            os.close(marker)
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _validate_f3_reservation(reservation: F3Reservation) -> None:
    try:
        parent_opened = os.fstat(reservation.directory_descriptor)
        parent_live = reservation.path.parent.lstat()
        opened = os.fstat(reservation.descriptor)
        live = os.stat(
            reservation.path.name,
            dir_fd=reservation.directory_descriptor,
            follow_symlinks=False,
        )
    except OSError as error:
        _remark_f3_canonical(reservation.path.parents[3])
        raise PreflightError("F3 attempt reservation is unavailable") from error
    parent_drift = (
        reservation.path.parent.is_symlink()
        or _directory_identity(parent_opened) != reservation.parent_identity
        or _directory_identity(parent_live) != reservation.parent_identity
        or stat.S_IMODE(parent_opened.st_mode) != 0o700
    )
    if parent_drift:
        _remark_f3_canonical(reservation.path.parents[3])
        raise PreflightError("F3 attempt reservation parent identity drifted")
    if (
        not stat.S_ISREG(live.st_mode)
        or _stat_identity(opened) != _stat_identity(live)
        or live.st_uid != os.getuid()
        or live.st_nlink != 1
        or stat.S_IMODE(live.st_mode) != 0o600
        or live.st_size != 0
    ):
        raise PreflightError("F3 attempt reservation identity drifted")


def _write_f3_temporary(reservation: F3Reservation, raw: bytes, *, label: str) -> str:
    name = f".ae-sq9-f3-{label}-{secrets.token_hex(16)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(name, flags, 0o600, dir_fd=reservation.directory_descriptor)
    try:
        os.fchmod(descriptor, 0o600)
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise PreflightError("F3 terminal record write did not progress")
            view = view[written:]
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_size != len(raw)
        ):
            raise PreflightError("F3 terminal temporary identity is unsafe")
    finally:
        os.close(descriptor)
    return name


def _verify_f3_terminal(
    reservation: F3Reservation,
    raw: bytes,
    record: Mapping[str, Any],
    *,
    rollback: bool,
) -> None:
    read_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    read_flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(
            reservation.path.name,
            read_flags,
            dir_fd=reservation.directory_descriptor,
        )
    except OSError as error:
        _remark_f3_canonical(reservation.path.parents[3])
        raise PreflightError("F3 terminal record became unavailable") from error
    try:
        metadata = os.fstat(descriptor)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 65_536)
            if not chunk:
                break
            chunks.append(chunk)
        terminal_raw = b"".join(chunks)
    finally:
        os.close(descriptor)
    try:
        parent_live = reservation.path.parent.lstat()
        terminal_live = os.stat(
            reservation.path.name,
            dir_fd=reservation.directory_descriptor,
            follow_symlinks=False,
        )
    except OSError as error:
        _remark_f3_canonical(reservation.path.parents[3])
        raise PreflightError("F3 terminal custody became unavailable") from error
    parent_drift = (
        _directory_identity(os.fstat(reservation.directory_descriptor))
        != reservation.parent_identity
        or _directory_identity(parent_live) != reservation.parent_identity
    )
    if parent_drift:
        _remark_f3_canonical(reservation.path.parents[3])
        raise PreflightError("F3 terminal parent identity drifted")
    if rollback:
        try:
            decoded = json.loads(
                terminal_raw.decode("utf-8", "strict"),
                object_pairs_hook=_closed_pairs,
                parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise PreflightError("F3 rollback is not strict JSON") from error
    else:
        decoded = strict_json(terminal_raw)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or _stat_identity(metadata) != _stat_identity(terminal_live)
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or terminal_raw != raw
        or decoded != dict(record)
        or canonical_json(decoded) != terminal_raw
    ):
        raise PreflightError("F3 terminal record failed post-replace custody")


def _replace_f3_record(
    reservation: F3Reservation,
    record: Mapping[str, Any],
    *,
    rollback_record: Mapping[str, Any] | None = None,
) -> None:
    _validate_f3_reservation(reservation)
    raw = canonical_json(record)
    rollback_raw = (
        canonical_json(rollback_record) if rollback_record is not None else None
    )
    rollback_name = (
        _write_f3_temporary(reservation, rollback_raw, label="rollback")
        if rollback_raw is not None
        else None
    )
    temporary_name: str | None = None
    try:
        temporary_name = _write_f3_temporary(reservation, raw, label="terminal")
        _validate_f3_reservation(reservation)
        os.replace(
            temporary_name,
            reservation.path.name,
            src_dir_fd=reservation.directory_descriptor,
            dst_dir_fd=reservation.directory_descriptor,
        )
        os.fsync(reservation.directory_descriptor)
        _verify_f3_terminal(reservation, raw, record, rollback=False)
    except BaseException:
        if (
            rollback_name is not None
            and rollback_raw is not None
            and rollback_record is not None
        ):
            try:
                os.replace(
                    rollback_name,
                    reservation.path.name,
                    src_dir_fd=reservation.directory_descriptor,
                    dst_dir_fd=reservation.directory_descriptor,
                )
                rollback_name = None
                os.fsync(reservation.directory_descriptor)
                _verify_f3_terminal(
                    reservation,
                    rollback_raw,
                    rollback_record,
                    rollback=True,
                )
            except BaseException as rollback_error:
                raise PreflightError(
                    "F3 PASS failure could not install verified non-PASS rollback"
                ) from rollback_error
        raise
    finally:
        for name in (temporary_name, rollback_name):
            if name is not None:
                try:
                    os.unlink(name, dir_fd=reservation.directory_descriptor)
                except FileNotFoundError:
                    pass


def _f3_bindings(state: Mapping[str, Any], root: Path) -> dict[str, str]:
    fixture = state.get("f3_gate_bindings")
    if fixture is not None:
        expected = {
            "program_authority_sha256",
            "f1_freeze_sha256",
            "corpus_manifest_sha256",
            "run_manifest_sha256",
        }
        if (
            not isinstance(fixture, Mapping)
            or set(fixture) != expected
            or any(
                not isinstance(value, str) or HEX64.fullmatch(value) is None
                for value in fixture.values()
            )
        ):
            raise PreflightError("F3 gate binding fixture is open")
        return dict(fixture)
    return {
        "program_authority_sha256": sha256_bytes(
            git_show(
                root,
                "88c1b04dc049ab7656e811df9bc3f9e33276f778",
                "evals/ae-sq9/program-authority.json",
            )
        ),
        "f1_freeze_sha256": state["profile"]["freeze_sha256"],
        "corpus_manifest_sha256": state["corpus_manifest_sha256"],
        "run_manifest_sha256": state["run_manifest_sha256"],
    }


def _f3_record(
    state: Mapping[str, Any], root: Path, *, status: str, checks: Mapping[str, bool]
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": "ae-sq9-preflight-v1",
        "program_id": PROGRAM_ID,
        "candidate_id": CANDIDATE_ID,
        "phase": "SQ9-F3",
        "attempt": 1,
        "model_calls": 0,
        "status": status,
        "bindings": _f3_bindings(state, root),
        "checks": dict(checks),
    }
    record["aggregate_sha256"] = digest(record)
    return record


def _execute_f3_boundary(state: Mapping[str, Any], root: Path) -> dict[str, Any]:
    """Shared complete F3 checks -> record -> schema/AND validation boundary."""
    checks = _f3_checks(state)
    record = _f3_record(state, root, status="PASS", checks=checks)
    schema = state["profile"]["documents"]["preflight_schema"]
    result = validate_f3_record(record, schema)
    check_names = schema["properties"]["checks"]["required"]
    failed = _f3_record(
        state,
        root,
        status="FAIL",
        checks={key: False for key in check_names},
    )
    validate_f3_record(failed, schema)
    return result


def _f3_gate_state(
    schema: Mapping[str, Any], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "f3_gate_fixture": True,
        "f3_gate_bindings": {
            "program_authority_sha256": "1" * 64,
            "f1_freeze_sha256": "2" * 64,
            "corpus_manifest_sha256": "3" * 64,
            "run_manifest_sha256": "4" * 64,
        },
        "f3_gate_topology": {
            "author_ids": ["synthetic-author-a", "synthetic-author-b"],
            "corpus_material_present": False,
            "model_calls": 0,
            "schedule_shape": [80, 4],
            "synthetic_case_shape": [2, 20],
            "synthetic_formula_positive": True,
            "synthetic_formula_red": True,
            "synthetic_lifecycle_closed": True,
            "synthetic_provider_closed": True,
            "synthetic_raw_persistence": False,
            "synthetic_retry_calls": 0,
            "synthetic_schema_closed": True,
            "synthetic_one_shot_unclaimed": True,
        },
        "profile": {"documents": {"preflight_schema": schema}},
        "run_manifest": {"validation_receipt": dict(receipt)},
    }


def full_f3_boundary_fixture(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Run the target production F3 boundary on positive and interface-red receipts."""
    Draft202012Validator.check_schema(schema)
    nested = {"validator": {"validator_id": "independent-nonauthor-validator"}}
    positive = _execute_f3_boundary(_f3_gate_state(schema, nested), Path("."))
    reds = {
        "red_top_level_only": {"validator_id": "independent-nonauthor-validator"},
        "red_missing_nested": {"validator": {}},
        "red_wrong_nested_placement": {
            "validator": {
                "identity": {"validator_id": "independent-nonauthor-validator"}
            }
        },
    }
    results: dict[str, dict[str, str]] = {}
    for label, receipt in reds.items():
        try:
            _execute_f3_boundary(_f3_gate_state(schema, receipt), Path("."))
        except PreflightError as error:
            if str(error) != "validation_receipt_validator_identity":
                raise
            results[label] = {
                "error": "validation_receipt_validator_identity",
                "status": "REJECTED",
            }
        else:
            raise PreflightError(f"{label} passed the production F3 boundary")
    return {
        "fixture": "synthetic-zero-corpus-zero-model-closed-receipt",
        "production_boundary": "_execute_f3_boundary",
        "production_checks": "_f3_checks",
        "production_one_shot_builder": "build_f3_record",
        "positive": {
            "all_checks_true": all(positive["checks"].values()),
            "model_calls": positive["model_calls"],
            "status": positive["status"],
        },
        **results,
    }


def build_f3_record(*, root: Path, run_commit: str) -> dict[str, Any]:
    """Consume exactly one F3 attempt and persist its aggregate-only record."""
    reservation = _reserve_f3_record(root)
    state: dict[str, Any] | None = None
    cleanup_attempted = False
    cleanup_succeeded = False
    pass_install_attempted = False
    try:
        _validate_f3_reservation(reservation)
        state = _load_base_state(root, run_commit, reserved_f3=True)
        record = _execute_f3_boundary(state, root)
        schema = state["profile"]["documents"]["preflight_schema"]
        result = record
        check_names = schema["properties"]["checks"]["required"]
        failed = _f3_record(
            state,
            root,
            status="FAIL",
            checks={key: False for key in check_names},
        )
        validate_f3_record(failed, schema)
        cleanup_attempted = True
        state["snapshot"].close()
        cleanup_succeeded = True
        pass_install_attempted = True
        _replace_f3_record(reservation, result, rollback_record=failed)
        return result
    except Exception:
        # The O_EXCL reservation is the durable terminal proof of the failed
        # attempt.  It is intentionally not deleted or reopened, so even a
        # crash or failure before a schema-valid aggregate permanently routes
        # this successor away from F4.
        if state is not None and not cleanup_attempted:
            cleanup_attempted = True
            state["snapshot"].close()
            cleanup_succeeded = True
        if state is not None and cleanup_succeeded and not pass_install_attempted:
            try:
                schema = state["profile"]["documents"]["preflight_schema"]
                check_names = schema["properties"]["checks"]["required"]
                failed = _f3_record(
                    state,
                    root,
                    status="FAIL",
                    checks={key: False for key in check_names},
                )
                validate_f3_record(failed, schema)
                _replace_f3_record(reservation, failed)
            except Exception:
                # A partial/empty exclusive marker is itself terminal and
                # cannot be upgraded by a second F3 attempt.
                pass
        raise
    finally:
        try:
            if state is not None and not cleanup_attempted:
                cleanup_attempted = True
                state["snapshot"].close()
        finally:
            os.close(reservation.descriptor)
            os.close(reservation.directory_descriptor)


def _load_preflight_record(
    state: dict[str, Any], preflight_commit: str
) -> dict[str, Any]:
    commit, _tree = git_identity(state["root"], preflight_commit)
    parents = _git(
        state["root"], ["rev-list", "--parents", "-n", "1", commit], text=True
    )
    if parents.returncode:
        raise PreflightError("F3 commit ancestry is unavailable")
    fields = parents.stdout.split()
    if fields != [commit, state["commit"]]:
        raise PreflightError("F3 is not the sole direct child of the frozen F2 run")
    changed = _git(
        state["root"],
        [
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            state["commit"],
            commit,
        ],
        text=True,
    )
    if changed.returncode or changed.stdout.splitlines() != [F3_RECORD_PATH]:
        raise PreflightError("F3 commit is not the exact one-record transition")
    raw = git_show(state["root"], commit, F3_RECORD_PATH)
    record = _strict_document(raw, "F3 record")
    if canonical_json(record) != raw:
        raise PreflightError("committed F3 record is not exact canonical bytes")
    schema = state["profile"]["documents"]["preflight_schema"]
    expected_bindings = {
        "program_authority_sha256": sha256_bytes(
            git_show(
                state["root"],
                "88c1b04dc049ab7656e811df9bc3f9e33276f778",
                "evals/ae-sq9/program-authority.json",
            )
        ),
        "f1_freeze_sha256": state["profile"]["freeze_sha256"],
        "corpus_manifest_sha256": state["corpus_manifest_sha256"],
        "run_manifest_sha256": state["run_manifest_sha256"],
    }
    validate_f3_record(record, schema, expected_bindings=expected_bindings)
    if record.get("status") != "PASS":
        raise PreflightError("F3 PASS record is not exact or fully conjunctive")
    state["preflight_record"] = record
    state["preflight_record_raw"] = raw
    state["preflight_record_sha256"] = sha256_bytes(raw)
    state["scorer_binding"] = _scorer_binding(
        state["profile"],
        state["corpus_digest"],
        corpus_manifest_sha256=state["corpus_manifest_sha256"],
        run_manifest_sha256=state["run_manifest_sha256"],
        preflight_record_sha256=state["preflight_record_sha256"],
        program_authority_sha256=record["bindings"]["program_authority_sha256"],
    )
    return state


def prepare_execution(
    *, root: Path, run_commit: str, preflight_commit: str, codex: str
) -> tuple[dict[str, Any], dict[str, str], dict[str, str], Any]:
    state = _load_base_state(root, run_commit, live_commit=preflight_commit)
    try:
        _load_preflight_record(state, preflight_commit)
        state["run_index_module"].assert_unclaimed(root)
        cli = codex_preflight(codex)
        manifest_cli = state["run_manifest"]["runtime"]["cli"]
        if manifest_cli != {
            "id": "codex-cli",
            "version": cli["version"],
            "sha256": cli["sha256"],
        }:
            raise PreflightError("live CLI differs from the frozen run manifest")
        binding = {
            "corpus_manifest_sha256": state["corpus_manifest_sha256"],
            "f1_freeze_sha256": state["profile"]["freeze_sha256"],
            "preflight_record_sha256": state["preflight_record_sha256"],
            "program_authority_sha256": state["preflight_record"]["bindings"][
                "program_authority_sha256"
            ],
            "run_manifest_sha256": state["run_manifest_sha256"],
        }
        index = state["run_index_module"].AESQ9RunIndex(root)
        return state, cli, binding, index
    except Exception:
        state["snapshot"].close()
        raise


def _validated_auth_source() -> tuple[Path, os.stat_result]:
    configured = os.environ.get("CODEX_HOME")
    base = Path(configured) if configured is not None else Path.home() / ".codex"
    if not base.is_absolute():
        raise PreflightError("Codex auth source must be absolute")
    source = base / "auth.json"
    try:
        metadata = source.lstat()
    except OSError as error:
        raise PreflightError("Codex auth source is unavailable") from error
    if (
        source.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_size <= 0
    ):
        raise PreflightError("Codex auth source is not owner-only private data")
    return source, metadata


def _auth_fingerprint(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


@contextmanager
def isolated_child_environment() -> Iterator[tuple[dict[str, str], Path]]:
    """Give one call a unique 0700 HOME, CODEX_HOME, TMPDIR, and empty cwd."""
    source, metadata = _validated_auth_source()
    fingerprint = _auth_fingerprint(metadata)
    temporary = tempfile.TemporaryDirectory(prefix="ae-sq9-call-")
    call_root = Path(temporary.name)
    try:
        os.chmod(call_root, 0o700)
        home = call_root / "home"
        tmp = call_root / "tmp"
        cwd = call_root / "cwd"
        for directory in (home, tmp, cwd):
            directory.mkdir(mode=0o700)
        destination = home / "auth.json"
        shutil.copyfile(source, destination, follow_symlinks=False)
        os.chmod(destination, 0o600)
        copied = destination.lstat()
        if (
            destination.is_symlink()
            or not stat.S_ISREG(copied.st_mode)
            or copied.st_nlink != 1
            or copied.st_uid != os.getuid()
            or stat.S_IMODE(copied.st_mode) != 0o600
            or _auth_fingerprint(source.lstat()) != fingerprint
        ):
            raise PreflightError("isolated auth copy failed")
        allowed = (
            "PATH",
            "LANG",
            "LC_ALL",
            "LC_CTYPE",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
            "HTTPS_PROXY",
            "HTTP_PROXY",
            "ALL_PROXY",
            "NO_PROXY",
        )
        environment = {key: os.environ[key] for key in allowed if key in os.environ}
        environment.update(
            {"HOME": str(home), "CODEX_HOME": str(home), "TMPDIR": str(tmp)}
        )
        yield environment, cwd
        if _auth_fingerprint(source.lstat()) != fingerprint:
            raise PreflightError("Codex auth source changed during child execution")
    finally:
        temporary.cleanup()
        if call_root.exists():
            raise RunnerError("private child temporary directory cleanup failed")


def codex_preflight(codex: str) -> dict[str, str]:
    resolved = (
        Path(codex).resolve()
        if Path(codex).is_absolute()
        else (Path(shutil.which(codex)).resolve() if shutil.which(codex) else None)
    )
    if resolved is None or not resolved.is_file() or resolved.is_symlink():
        raise PreflightError("Codex CLI is unavailable")
    if sha256_bytes(resolved.read_bytes()) != CLI_SHA256:
        raise PreflightError("Codex CLI executable digest drift")
    with isolated_child_environment() as (environment, cwd):
        completed = subprocess.run(
            [str(resolved), "--version"],
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            timeout=PREFLIGHT_TIMEOUT_SECONDS,
        )
    if completed.returncode or completed.stdout.strip() != CLI_VERSION:
        raise PreflightError("Codex CLI version drift")
    return {
        "id": "codex-cli",
        "path": str(resolved),
        "version": CLI_VERSION,
        "sha256": CLI_SHA256,
    }


def child_argv(cli: Mapping[str, str], schema_path: Path) -> list[str]:
    argv = [
        cli["path"],
        "--ask-for-approval",
        "never",
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--strict-config",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--model",
        MODEL,
        "--output-schema",
        str(schema_path),
        "--color",
        "never",
        "--json",
    ]
    for feature in DISABLED_FEATURES:
        argv.extend(["--disable", feature])
    for override in CONFIG_OVERRIDES:
        argv.extend(["-c", override])
    return [*argv, "-"]


def _usage(value: Any) -> dict[str, int]:
    keys = {"input_tokens", "cached_input_tokens", "output_tokens"}
    if not isinstance(value, dict) or set(value) not in (keys, keys | {"total_tokens"}):
        raise ValueError("turn completion usage is not closed")
    if any(type(value[key]) is not int or value[key] < 0 for key in keys):
        raise ValueError("turn completion usage is not nonnegative integers")
    total = value.get("total_tokens", value["input_tokens"] + value["output_tokens"])
    if (
        type(total) is not int
        or total != value["input_tokens"] + value["output_tokens"]
        or value["cached_input_tokens"] > value["input_tokens"]
    ):
        raise ValueError("turn completion usage is inconsistent")
    return {
        "input_tokens": value["input_tokens"],
        "cached_input_tokens": value["cached_input_tokens"],
        "output_tokens": value["output_tokens"],
        "total_tokens": total,
    }


def parse_events(
    raw: bytes,
    *,
    resolver: Any,
    task_text: str,
    condition: str,
    slot_id: str,
    profile: Mapping[str, Any],
) -> InvocationOutcome:
    """Recognize only one exact lifecycle and validate provider then semantics."""
    lines = [line for line in raw.splitlines() if line]
    if not lines:
        raise CallFailure("event stream is empty", "none")
    parsed: list[Any] = []
    malformed = False
    for line in lines:
        try:
            parsed.append(strict_json(line))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            malformed = True
            parsed.append(None)
    completion_present = any(
        isinstance(event, dict) and event.get("type") == "turn.completed"
        for event in parsed
    )
    if malformed:
        raise CallFailure(
            "event stream contains malformed JSON",
            "indeterminate" if completion_present else "none",
        )
    events = parsed
    if len(events) < 4:
        raise CallFailure(
            "event stream lacks closed lifecycle",
            "indeterminate" if completion_present else "none",
        )
    thread = events[0]
    started = events[1]
    if (
        not isinstance(thread, dict)
        or set(thread) != {"type", "thread_id"}
        or thread.get("type") != "thread.started"
        or not isinstance(thread.get("thread_id"), str)
        or not thread["thread_id"]
        or started != {"type": "turn.started"}
    ):
        raise CallFailure(
            "event lifecycle prefix is invalid",
            "indeterminate" if completion_present else "none",
        )
    message: str | None = None
    for event in events[2:-1]:
        if (
            not isinstance(event, dict)
            or set(event) != {"type", "item"}
            or event.get("type") != "item.completed"
        ):
            raise CallFailure(
                "unknown, tool, effect, or extra event",
                "indeterminate" if completion_present else "none",
            )
        item = event["item"]
        if (
            not isinstance(item, dict)
            or set(item) != {"id", "type", "text"}
            or not isinstance(item.get("id"), str)
            or not item["id"]
            or not isinstance(item.get("text"), str)
        ):
            raise CallFailure(
                "completed item is malformed",
                "indeterminate" if completion_present else "none",
            )
        if item["type"] == "reasoning" and message is None:
            continue
        if item["type"] == "agent_message" and message is None and item["text"].strip():
            message = item["text"]
            continue
        raise CallFailure(
            "completed item type/order is forbidden",
            "indeterminate" if completion_present else "none",
        )
    terminal = events[-1]
    if (
        not isinstance(terminal, dict)
        or set(terminal) != {"type", "usage"}
        or terminal.get("type") != "turn.completed"
    ):
        raise CallFailure("event lifecycle has no exact terminal completion", "none")
    try:
        usage = _usage(terminal["usage"])
    except ValueError as error:
        raise CallFailure("terminal usage is invalid", "indeterminate") from error
    if message is None:
        raise CallFailure(
            "completed lifecycle lacks one agent message", "indeterminate"
        )
    capsule_raw = message.encode("utf-8", "strict")
    capsule_sha = sha256_bytes(capsule_raw)
    try:
        capsule = strict_json(capsule_raw)
        if not isinstance(capsule, dict):
            raise ValueError("capsule is not an object")
        provider_schema = profile["documents"]["capsule_schema"]
        if list(Draft202012Validator(provider_schema).iter_errors(capsule)):
            raise ValueError("provider-schema-invalid capsule")
        semantic_schema = profile["documents"]["semantic_capsule_schema"]
        if list(Draft202012Validator(semantic_schema).iter_errors(capsule)):
            raise ValueError("local-semantic-schema-invalid capsule")
        projected = resolver.normalize_runtime_capsule(
            task_text,
            slot_id,
            (capsule_raw, capsule_sha),
            profile["trusted_json"]["candidate_authority"],
            profile["trusted_json"]["semantic_capsule_schema"],
        )
        if (
            not isinstance(projected, dict)
            or tuple(projected) != ("slot_id", "local_need", "reference_need")
            or projected["slot_id"] != slot_id
        ):
            raise ValueError("local normalizer returned an open projection")
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        raise CallFailure(
            "completed capsule failed provider or local semantics", "indeterminate"
        ) from error
    return InvocationOutcome(
        "confirmed", capsule_raw, capsule_sha, projected, thread["thread_id"], usage
    )


def build_packet(
    state: Mapping[str, Any], *, task_text: str, condition: str, slot_id: str
) -> dict[str, Any]:
    try:
        packet = state["resolver"].build_assessor_packet(
            task_text,
            condition,
            slot_id,
            state["profile"]["trusted_json"]["candidate_authority"],
        )
    except Exception as error:
        raise PreflightError("assessor packet construction failed") from error
    if (
        not isinstance(packet, dict)
        or tuple(packet)
        != (
            "instruction",
            "task_text",
            "condition_id",
            "slot_id",
            "condition_slot_card",
            "anonymous_menu",
        )
        or packet["task_text"] != task_text
        or packet["condition_id"] != condition
        or packet["slot_id"] != slot_id
    ):
        raise PreflightError("assessor packet is not the closed one-card projection")
    return packet


def invoke_one(
    packet: Mapping[str, Any],
    *,
    state: Mapping[str, Any],
    cli: Mapping[str, str],
    condition: str,
    slot_id: str,
) -> InvocationOutcome:
    schema_path = (
        state["snapshot_root"] / state["profile"]["bindings"]["capsule_schema"]["path"]
    )
    argv = child_argv(cli, schema_path)
    with isolated_child_environment() as (environment, cwd):
        try:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                env=environment,
                input=canonical_json(packet),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=CHILD_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as error:
            # Timeout and arbitrary partial stdout are explicitly not an
            # observation.  No retry follows; the counted attempt terminates.
            raise CallFailure("isolated child timed out", "none") from error
        except OSError as error:
            raise CallFailure("isolated child launch failed", "none") from error
    raw = completed.stdout if isinstance(completed.stdout, bytes) else b""
    try:
        outcome = parse_events(
            raw,
            resolver=state["resolver"],
            task_text=packet["task_text"],
            condition=condition,
            slot_id=slot_id,
            profile=state["profile"],
        )
    except CallFailure:
        raise
    if completed.returncode:
        raise CallFailure("child exited nonzero after event output", "indeterminate")
    return outcome


def _four_calls(
    state: Mapping[str, Any],
    cli: Mapping[str, str],
    ledger: AttemptLedger,
    *,
    phase: str,
    task_text: str,
    condition: str,
    invoke: Callable[..., InvocationOutcome],
    packets: Sequence[Mapping[str, Any]] | None = None,
) -> list[InvocationOutcome | CallFailure]:
    if packets is not None and len(packets) != len(SLOT_ORDER):
        raise RunnerError("prebuilt four-call packet closure is incomplete")
    results: list[InvocationOutcome | CallFailure] = []
    for index, slot_id in enumerate(SLOT_ORDER):
        packet = (
            packets[index]
            if packets is not None
            else build_packet(
                state, task_text=task_text, condition=condition, slot_id=slot_id
            )
        )
        ledger.before_call(phase)
        try:
            outcome = invoke(
                packet,
                state=state,
                cli=cli,
                condition=condition,
                slot_id=slot_id,
            )
            if (
                not isinstance(outcome, InvocationOutcome)
                or outcome.lifecycle != "confirmed"
            ):
                raise CallFailure(
                    "invoker returned an unconfirmed outcome", "indeterminate"
                )
        except CallFailure as error:
            results.append(error)
        except Exception as error:
            results.append(CallFailure(type(error).__name__, "none"))
        else:
            ledger.complete_call(phase, outcome)
            results.append(outcome)
    return results


def _parent_resolution(
    state: Mapping[str, Any],
    *,
    task_text: str,
    condition: str,
    outcomes: Sequence[InvocationOutcome],
) -> dict[str, Any]:
    if len(outcomes) != 4 or any(
        outcome.lifecycle != "confirmed" for outcome in outcomes
    ):
        raise CallFailure(
            "parent resolution lacks four confirmed capsules", "indeterminate"
        )
    trusted = state["profile"]["trusted_json"]
    ingresses = [(outcome.capsule_raw, outcome.capsule_sha256) for outcome in outcomes]
    try:
        record = state["resolver"].resolve(
            task_text,
            condition,
            ingresses,
            trusted["candidate_authority"],
            trusted["reference_policy"],
            trusted["semantic_capsule_schema"],
            repository_root=state["snapshot_root"],
        )
        record_raw = canonical_json(record)
        verified = state["resolver"].verify_resolution_record(
            (record_raw, sha256_bytes(record_raw)),
            trusted["candidate_authority"],
            trusted["reference_policy"],
            trusted["resolution_schema"],
        )
        status = {
            "selected": "selected",
            "no_selection": "none",
            "abstain_cap": "cap_abstain",
            "abstain_uncertain": "uncertain_abstain",
            "abstain_invalid": "uncertain_abstain",
        }[verified["resolution_status"]]
        selected = list(verified["selected_slots"]) if status == "selected" else []
        references = [
            {"slot_id": row["slot_id"], "need": row["reference_need"]}
            for row in verified["references"]["files"]
        ]
    except Exception as error:
        raise CallFailure(
            "parent resolution failed trusted verification", "indeterminate"
        ) from error
    return {
        "status": status,
        "selected_slots": selected,
        "reference_bundle": references,
    }


def _perform_canary(
    state: Mapping[str, Any],
    cli: Mapping[str, str],
    ledger: AttemptLedger,
    *,
    invoke: Callable[..., InvocationOutcome],
    packets: Sequence[Mapping[str, Any]],
) -> None:
    task = "Assess whether this local reversible engineering request needs only your assigned capability."
    results = _four_calls(
        state,
        cli,
        ledger,
        phase="canary",
        task_text=task,
        condition="reduced",
        invoke=invoke,
        packets=packets,
    )
    if any(isinstance(result, CallFailure) for result in results):
        raise CallFailure("canary did not close four valid capsules", "indeterminate")
    outcomes = [result for result in results if isinstance(result, InvocationOutcome)]
    _parent_resolution(state, task_text=task, condition="reduced", outcomes=outcomes)
    ledger.pass_canary()


def _prepare_canary_packets(state: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    task = "Assess whether this local reversible engineering request needs only your assigned capability."
    return tuple(
        build_packet(
            state,
            task_text=task,
            condition="reduced",
            slot_id=slot_id,
        )
        for slot_id in SLOT_ORDER
    )


def _capsule_observation(
    state: Mapping[str, Any],
    schedule_row: Mapping[str, Any],
    case: Mapping[str, Any],
    slot_id: str,
    outcome: InvocationOutcome,
) -> dict[str, Any]:
    if outcome.lifecycle != "confirmed":
        raise RunnerError("unconfirmed capsule cannot enter evaluator custody")
    validator = state["validator"]
    binding_sha = validator.digest(state["scorer_binding"])
    return {
        "slot_id": slot_id,
        "context_id": outcome.context_id,
        "invocation_count": 1,
        "terminal_completed": True,
        # The evaluator independently authenticates and normalizes the exact
        # provider bytes.  The runner projection is used only by the parent
        # resolver and is never accepted as scorer evidence.
        "capsule_raw": outcome.capsule_raw,
        "capsule_sha256": outcome.capsule_sha256,
        "binding_sha256": binding_sha,
        "schedule_sha256": state["schedule_digest"],
        "packet_sha256": validator.capsule_packet_digest(
            binding_digest=binding_sha,
            schedule_sha256=state["schedule_digest"],
            condition=schedule_row["condition"],
            case_id=schedule_row["case_id"],
            task_sha256=case["task_text_nfc_sha256"],
            slot_id=slot_id,
        ),
        "task_sha256": case["task_text_nfc_sha256"],
    }


def _perform_batch(
    state: Mapping[str, Any],
    cli: Mapping[str, str],
    ledger: AttemptLedger,
    *,
    invoke: Callable[..., InvocationOutcome],
) -> dict[str, Any]:
    ledger.begin_batch()
    scorer = state["scorer"]
    session = scorer.create_live_score_session(
        documents=state["corpus_documents"],
        historical_digest_inventory=state["inventory_raw"],
        expected_authority=state["expected_authority"],
        binding=state["scorer_binding"],
    )
    for schedule_row in state["schedule"]:
        case = state["cases"][schedule_row["case_id"]]
        results = _four_calls(
            state,
            cli,
            ledger,
            phase="batch",
            task_text=case["task_text"],
            condition=schedule_row["condition"],
            invoke=invoke,
        )
        if any(isinstance(result, CallFailure) for result in results):
            raise CallFailure(
                "batch presentation lifecycle became invalid", "indeterminate"
            )
        outcomes = [
            result for result in results if isinstance(result, InvocationOutcome)
        ]
        resolution = _parent_resolution(
            state,
            task_text=case["task_text"],
            condition=schedule_row["condition"],
            outcomes=outcomes,
        )
        session.add(
            {
                "presentation_index": schedule_row["presentation_index"],
                "presentation_id": schedule_row["presentation_id"],
                "condition": schedule_row["condition"],
                "case_id": schedule_row["case_id"],
                "terminal_completed": True,
                "capsules": [
                    _capsule_observation(state, schedule_row, case, slot_id, outcome)
                    for slot_id, outcome in zip(SLOT_ORDER, outcomes, strict=True)
                ],
                "resolution": resolution,
                "events": {key: False for key in EVENT_KEYS},
            }
        )
    if (
        ledger.batch_attempted != BATCH_CALLS
        or ledger.batch_completed != BATCH_CALLS
        or session.observation_count != BATCH_PRESENTATIONS
        or ledger.total_attempted != HARD_CALL_CEILING
        or ledger.total_completed != HARD_CALL_CEILING
    ):
        raise RunnerError("batch lacks exact 80x4 and 324-call closure")
    public = session.close(
        {
            "runner_local_raw_persistence": False,
            "heldout_outcome_use": False,
        }
    )
    session.validate_public(public)
    _validate_public_result(state, public)
    return public


def _validate_public_result(state: Mapping[str, Any], value: Any) -> dict[str, Any]:
    schema = state["profile"]["documents"]["result_schema"]
    if (
        not isinstance(value, dict)
        or tuple(value)
        != (
            "aggregate_digest",
            "candidate_id",
            "program_id",
            "schema_version",
            "status",
        )
        or list(Draft202012Validator(schema).iter_errors(value))
    ):
        raise RunnerError("public result is not the exact aggregate-only projection")
    return value


def _failure_result(
    state: Mapping[str, Any],
    binding: Mapping[str, str],
    ledger: AttemptLedger,
    error: BaseException,
) -> dict[str, Any]:
    value = {
        "aggregate_digest": digest(
            {
                "program_id": PROGRAM_ID,
                "candidate_id": CANDIDATE_ID,
                "status": "FAIL",
                "reason_class": type(error).__name__,
                "custody_key": digest(binding),
                "attempted_calls": ledger.total_attempted,
                "completed_calls": ledger.total_completed,
            }
        ),
        "candidate_id": CANDIDATE_ID,
        "program_id": PROGRAM_ID,
        "schema_version": "ae-sq9-aggregate-result-v1",
        "status": "FAIL",
    }
    return _validate_public_result(state, value)


def _persist_f6_result(root: Path, public: Mapping[str, Any]) -> tuple[bytes, str]:
    """Atomically retain the sole canonical aggregate-only F6 result."""
    raw = canonical_json(dict(public))
    destination = root / F6_RESULT_PATH
    parent = destination.parent
    if parent.exists() and (parent.is_symlink() or not parent.is_dir()):
        raise RunnerError("F6 result parent is unsafe")
    parent.mkdir(mode=0o700, parents=False, exist_ok=True)
    if stat.S_IMODE(parent.stat().st_mode) & 0o022:
        raise RunnerError("F6 result parent is group/world writable")
    if destination.exists() or destination.is_symlink():
        raise RunnerError("F6 result already exists")
    temporary = parent / ".aggregate-result.pending"
    descriptor = -1
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        os.write(descriptor, raw)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, destination)
        directory = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except Exception:
        if descriptor != -1:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise
    metadata = destination.lstat()
    if (
        destination.is_symlink()
        or not destination.is_file()
        or metadata.st_nlink != 1
        or destination.read_bytes() != raw
    ):
        raise RunnerError("F6 result post-write custody failed")
    return raw, sha256_bytes(raw)


def execute_batch(
    *,
    root: Path,
    run_commit: str,
    preflight_commit: str,
    codex: str,
    invoke: Callable[..., InvocationOutcome] = invoke_one,
) -> dict[str, Any]:
    """Claim once, run one canary, conditionally run one batch, and terminalize."""
    state, cli, binding, index = prepare_execution(
        root=root,
        run_commit=run_commit,
        preflight_commit=preflight_commit,
        codex=codex,
    )
    ledger = AttemptLedger()
    capability: bytes | None = None
    cleanup_attempted = False
    try:
        # Deterministically construct and validate all four assessor packets
        # before F4 is durably entered.  The next mutation is the sole claim,
        # immediately followed by the first counted child attempt.
        canary_packets = _prepare_canary_packets(state)
        capability = index.claim_execution(binding)
        try:
            _perform_canary(state, cli, ledger, invoke=invoke, packets=canary_packets)
            public = _perform_batch(state, cli, ledger, invoke=invoke)
        except Exception as error:
            public = _failure_result(state, binding, ledger, error)
            cleanup_attempted = True
            state["snapshot"].close()
            index.invalidate(binding, capability, sha256_bytes(canonical_json(public)))
            capability = None
            return public
        cleanup_attempted = True
        state["snapshot"].close()
        _raw, result_sha256 = _persist_f6_result(state["root"], public)
        index.complete(binding, capability, result_sha256)
        capability = None
        return public
    finally:
        # A BaseException or crash after claim intentionally leaves `claimed`
        # durable and non-reusable; there is no cleanup/delete/reset route.
        if not cleanup_attempted:
            cleanup_attempted = True
            state["snapshot"].close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run-commit", required=True)
    parser.add_argument("--preflight-commit")
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--usage-approval")
    args = parser.parse_args(argv)
    if HEX40.fullmatch(args.run_commit) is None:
        parser.error("--run-commit must be an exact lowercase 40-hex SHA")
    if args.preflight:
        if args.preflight_commit is not None or args.usage_approval is not None:
            parser.error("--preflight accepts no prior record or live usage approval")
        print(
            json.dumps(
                build_f3_record(root=args.root, run_commit=args.run_commit),
                sort_keys=True,
            )
        )
        return 0
    if args.preflight_commit is None or HEX40.fullmatch(args.preflight_commit) is None:
        parser.error("--verify/--execute require exact --preflight-commit")
    if args.verify:
        if args.usage_approval is not None:
            parser.error("--verify accepts no live usage approval")
        state = _load_base_state(
            args.root,
            args.run_commit,
            live_commit=args.preflight_commit,
        )
        try:
            _load_preflight_record(state, args.preflight_commit)
            state["run_index_module"].assert_unclaimed(args.root)
            result = {
                "program_id": PROGRAM_ID,
                "candidate_id": CANDIDATE_ID,
                "verification_status": "PASS",
                "aggregate_digest": state["preflight_record"]["aggregate_sha256"],
                "model_calls": 0,
            }
        finally:
            state["snapshot"].close()
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.usage_approval != USAGE_APPROVAL:
        parser.error(f"--execute requires exact --usage-approval {USAGE_APPROVAL}")
    result = execute_batch(
        root=args.root,
        run_commit=args.run_commit,
        preflight_commit=args.preflight_commit,
        codex=args.codex,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
