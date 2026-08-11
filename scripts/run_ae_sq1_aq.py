#!/usr/bin/env python3
"""Isolated four-assessor canary and 80x4 AE-SQ1 AQ runner.

Only the final aggregate receipt is printable.  Corpus text, assessor output,
event streams, context identifiers, and per-case metrics remain process-local.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterator, Mapping, Sequence

from jsonschema import Draft202012Validator

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
RUN_MANIFEST_PATH = "evals/ae-sq1/aq/run-manifest.json"
RUN_MANIFEST_SCHEMA_PATH = "evals/ae-sq1/aq/run-manifest-schema.json"
HISTORICAL_INVENTORY_DEFAULT = "evals/ae-sq1/historical-task-digests.json"
CANDIDATE_MANIFEST_PATH = "evals/ae-sq1/candidate-manifest.json"
RUNNER_PATH = "scripts/run_ae_sq1_aq.py"
CHECKER_PATH = "scripts/check_ae_sq1_candidate.py"
MODEL = "gpt-5.5"
REASONING = "medium"
CANARY_APPROVAL = "ae-sq1-authorized-canary"
BATCH_APPROVAL = "ae-sq1-authorized-batch"
SLOT_ORDER = ("s0", "s1", "s2", "s3")
CONDITIONS = ("current", "reduced")
MAX_CONCURRENCY = 8
PREFLIGHT_TIMEOUT_SECONDS = 30
CHILD_TIMEOUT_SECONDS = 600
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ISOLATION_PROBE = "AE-SQ1 isolation preflight"
EVENT_KEYS = (
    "effect_requested",
    "effect_granted",
    "claim_requested",
    "claim_granted",
    "tool_requested",
    "tool_granted",
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
    """The requested execution cannot continue safely."""


class PreflightError(RunnerError):
    """Frozen-byte, manifest, CLI, or isolation preflight failed."""


class InfrastructureError(RunnerError):
    """No completed model observation with closed usage was available."""


class CompletedInvalid(RunnerError):
    """A completed response or usage record violated the closed contract."""


@dataclass(frozen=True)
class InvocationOutcome:
    parse_status: str
    output: dict[str, Any] | None
    projected: dict[str, Any] | None
    capsule_raw: bytes
    capsule_sha256: str
    context_id: str
    usage: dict[str, int]
    observed: bool = True


def _completed_invalid(
    message: str,
    *,
    context_id: str | None,
    usage: Mapping[str, Any] | None,
) -> CompletedInvalid:
    error = CompletedInvalid(message)
    closed_usage = (
        dict(usage)
        if isinstance(usage, Mapping)
        else {
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }
    )
    error.outcome = InvocationOutcome(  # type: ignore[attr-defined]
        "malformed",
        None,
        None,
        b"",
        sha256_bytes(b""),
        context_id or "",
        closed_usage,
    )
    error.observed = True  # type: ignore[attr-defined]
    return error


class RuntimeSnapshot:
    """Private, content-addressed view of every frozen runtime input."""

    def __init__(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="ae-sq1-runtime-")
        self.root = Path(self._temporary.name)
        os.chmod(self.root, 0o700)
        self._ledger: dict[str, dict[str, str]] = {}
        self._sealed = False

    def add(self, binding: Mapping[str, Any], raw: bytes, *, label: str) -> Path:
        if self._sealed:
            raise PreflightError("runtime snapshot is already sealed")
        if not isinstance(binding, Mapping) or set(binding) != {
            "commit",
            "tree",
            "path",
            "blob",
            "sha256",
        }:
            raise PreflightError(f"{label} snapshot binding is not closed")
        commit, tree, path, blob, expected = (
            binding["commit"],
            binding["tree"],
            binding["path"],
            binding["blob"],
            binding["sha256"],
        )
        safe = Path(path) if isinstance(path, str) else Path("/")
        if (
            not isinstance(commit, str)
            or HEX40.fullmatch(commit) is None
            or not isinstance(tree, str)
            or HEX40.fullmatch(tree) is None
            or not isinstance(path, str)
            or safe.is_absolute()
            or ".." in safe.parts
            or not isinstance(blob, str)
            or HEX40.fullmatch(blob) is None
            or not isinstance(expected, str)
            or HEX64.fullmatch(expected) is None
            or sha256_bytes(raw) != expected
        ):
            raise PreflightError(f"{label} snapshot binding is invalid")
        row = {
            "commit": commit,
            "tree": tree,
            "path": path,
            "blob": blob,
            "sha256": expected,
        }
        existing = self._ledger.get(path)
        if existing is not None:
            if existing != row or (self.root / safe).read_bytes() != raw:
                raise PreflightError("runtime snapshot path collision")
            return self.root / safe
        destination = self.root / safe
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        parent = destination.parent
        while parent != self.root:
            os.chmod(parent, 0o700)
            parent = parent.parent
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o400,
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.fchmod(descriptor, 0o400)
        finally:
            os.close(descriptor)
        metadata = destination.lstat()
        if (
            destination.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_nlink != 1
            or destination.read_bytes() != raw
        ):
            raise PreflightError("runtime snapshot file is not immutable and private")
        self._ledger[path] = row
        return destination

    def seal(self) -> str:
        if not self._ledger:
            raise PreflightError("runtime snapshot is empty")
        self._sealed = True
        return digest(
            [
                {"label_path": path, **self._ledger[path]}
                for path in sorted(self._ledger)
            ]
        )

    def close(self) -> None:
        self._temporary.cleanup()


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise RunnerError("value is not canonical JSON") from error


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _runtime_capsule_bytes(value: Mapping[str, Any]) -> bytes:
    """Encode the SLEC capsule without destroying its order-significant contract."""
    if tuple(value) != ("slot_id", "local_need", "reference_need", "anchors"):
        raise RunnerError("runtime capsule is not closed or ordered")
    anchors = value["anchors"]
    if not isinstance(anchors, list) or any(
        not isinstance(anchor, Mapping) or tuple(anchor) != ("start", "end", "text")
        for anchor in anchors
    ):
        raise RunnerError("runtime capsule anchors are not closed or ordered")
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise RunnerError("runtime capsule is not strict UTF-8 JSON") from error


def _synthetic_anchor(task_text: str) -> dict[str, Any]:
    """Choose one exact unique task slice within SLEC's 256-code-point cap."""
    maximum = min(256, len(task_text))
    for width in range(maximum, 0, -1):
        for start in range(0, len(task_text) - width + 1):
            text = task_text[start : start + width]
            if task_text.find(text) == start and task_text.find(text, start + 1) < 0:
                return {"start": start, "end": start + width, "text": text}
    raise PreflightError("task has no unique SLEC anchor within the 256-code-point cap")


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
        parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
    )


def _git(root: Path, args: Sequence[str], *, text: bool = False) -> Any:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=text)


def git_show(root: Path, commit: str, path: str) -> bytes:
    if Path(path).is_absolute() or ".." in Path(path).parts:
        raise PreflightError("repository path escaped custody")
    result = _git(root, ["show", f"{commit}:{path}"])
    if result.returncode:
        raise PreflightError("committed input is unavailable")
    return result.stdout


def git_identity(root: Path, commit: str) -> tuple[str, str]:
    if not isinstance(commit, str) or HEX40.fullmatch(commit) is None:
        raise PreflightError("exact lowercase execution commit required")
    resolved = _git(root, ["rev-parse", "--verify", f"{commit}^{{commit}}"], text=True)
    tree = _git(root, ["rev-parse", "--verify", f"{commit}^{{tree}}"], text=True)
    if resolved.returncode or tree.returncode:
        raise PreflightError("Git identity is unavailable")
    return resolved.stdout.strip(), tree.stdout.strip()


def git_blob(root: Path, commit: str, path: str) -> str:
    result = _git(root, ["rev-parse", f"{commit}:{path}"], text=True)
    value = result.stdout.strip() if not result.returncode else ""
    if HEX40.fullmatch(value) is None:
        raise PreflightError("Git blob identity is unavailable")
    return value


def require_clean_exact_head(root: Path, commit: str) -> tuple[str, str]:
    resolved, tree = git_identity(root, commit)
    head = _git(root, ["rev-parse", "--verify", "HEAD^{commit}"], text=True)
    status = _git(
        root,
        ["status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching"],
        text=True,
    )
    if resolved != commit or head.returncode or head.stdout.strip() != commit:
        raise PreflightError("execution commit is not live HEAD")
    if status.returncode or status.stdout:
        raise PreflightError("execution checkout is not exactly clean")
    return resolved, tree


def _strict_document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = strict_json(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise PreflightError(f"{label} is not strict closed JSON") from error
    if not isinstance(value, dict):
        raise PreflightError(f"{label} is not an object")
    return value


def _sealed_bytes(
    root: Path,
    commit: str,
    tree: str,
    binding: Mapping[str, Any],
    label: str,
) -> bytes:
    if not isinstance(binding, Mapping) or set(binding) != {"path", "blob", "sha256"}:
        raise PreflightError(f"{label} binding is not closed")
    path, expected_blob, expected = (
        binding.get("path"),
        binding.get("blob"),
        binding.get("sha256"),
    )
    if (
        not isinstance(path, str)
        or not isinstance(expected_blob, str)
        or HEX40.fullmatch(expected_blob) is None
        or not isinstance(expected, str)
        or HEX64.fullmatch(expected) is None
    ):
        raise PreflightError(f"{label} binding is unresolved")
    resolved, actual_tree = git_identity(root, commit)
    if resolved != commit or actual_tree != tree:
        raise PreflightError(f"{label} commit/tree mismatch")
    raw = git_show(root, commit, path)
    if git_blob(root, commit, path) != expected_blob or sha256_bytes(raw) != expected:
        raise PreflightError(f"{label} digest mismatch")
    return raw


def _bootstrap_manifest(raw: bytes) -> dict[str, Any]:
    manifest = _strict_document(raw, "candidate manifest")
    if set(manifest) != {
        "schema_version",
        "program_id",
        "candidate_id",
        "candidate_freeze",
        "role_order",
        "files",
        "runtime",
        "aq",
    }:
        raise PreflightError("candidate manifest bootstrap shape drift")
    if (
        manifest.get("schema_version") != "ae-sq1-candidate-manifest-v1"
        or manifest.get("program_id") != "AE-SQ1"
        or manifest.get("candidate_id") != "SLEC-1"
    ):
        raise PreflightError("candidate manifest bootstrap identity drift")
    freeze = manifest.get("candidate_freeze")
    if (
        not isinstance(freeze, dict)
        or set(freeze) != {"commit", "tree"}
        or not isinstance(freeze.get("commit"), str)
        or HEX40.fullmatch(freeze["commit"]) is None
        or not isinstance(freeze.get("tree"), str)
        or HEX40.fullmatch(freeze["tree"]) is None
    ):
        raise PreflightError("candidate freeze bootstrap identity is unresolved")
    roles = manifest.get("role_order")
    files = manifest.get("files")
    if (
        not isinstance(roles, list)
        or any(not isinstance(role, str) or not role for role in roles)
        or len(roles) != len(set(roles))
        or not isinstance(files, list)
        or len(files) != len(roles)
    ):
        raise PreflightError("candidate bootstrap role ledger is invalid")
    for expected_role, row in zip(roles, files, strict=True):
        if (
            not isinstance(row, dict)
            or set(row) != {"role", "commit", "tree", "path", "blob", "sha256"}
            or row.get("role") != expected_role
        ):
            raise PreflightError("candidate bootstrap role row is invalid")
    return manifest


def _bootstrap_role(
    manifest: Mapping[str, Any], role: str, path: str
) -> dict[str, str]:
    rows = [row for row in manifest["files"] if row.get("role") == role]
    if len(rows) != 1:
        raise PreflightError(f"candidate bootstrap lacks exact {role} role")
    row = rows[0]
    freeze = manifest["candidate_freeze"]
    if (
        row.get("commit") != freeze["commit"]
        or row.get("tree") != freeze["tree"]
        or row.get("path") != path
        or not isinstance(row.get("blob"), str)
        or HEX40.fullmatch(row["blob"]) is None
        or not isinstance(row.get("sha256"), str)
        or HEX64.fullmatch(row["sha256"]) is None
    ):
        raise PreflightError(f"candidate bootstrap {role} binding drift")
    return {key: row[key] for key in ("commit", "tree", "path", "blob", "sha256")}


def _import_snapshot_module(
    snapshot: RuntimeSnapshot, name: str, path: str
) -> ModuleType:
    source = snapshot.root / path
    try:
        specification = importlib.util.spec_from_file_location(name, source)
        if specification is None or specification.loader is None:
            raise ImportError("snapshot import specification unavailable")
        module = importlib.util.module_from_spec(specification)
        sys.modules[name] = module
        specification.loader.exec_module(module)
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        sys.modules.pop(name, None)
        raise PreflightError(f"snapshot module {name} is unavailable") from error
    if Path(module.__file__ or "").resolve() != source.resolve():
        raise PreflightError(f"snapshot module {name} escaped custody")
    return module


def _verify_git_binding(root: Path, binding: Mapping[str, Any], label: str) -> bytes:
    if not isinstance(binding, Mapping) or set(binding) != {
        "commit",
        "tree",
        "path",
        "blob",
        "sha256",
    }:
        raise PreflightError(f"{label} Git binding is not closed")
    commit, tree = git_identity(root, binding["commit"])
    if commit != binding["commit"] or tree != binding["tree"]:
        raise PreflightError(f"{label} Git identity drift")
    raw = git_show(root, commit, binding["path"])
    if (
        git_blob(root, commit, binding["path"]) != binding["blob"]
        or sha256_bytes(raw) != binding["sha256"]
    ):
        raise PreflightError(f"{label} Git bytes drift")
    return raw


def _bootstrap_candidate(
    root: Path,
    candidate_binding: Mapping[str, Any],
    *,
    runner_path: Path | None = None,
) -> tuple[RuntimeSnapshot, dict[str, Any]]:
    """Authenticate M -> F before importing any candidate-controlled module."""
    if (
        not isinstance(candidate_binding, Mapping)
        or set(candidate_binding) != {"commit", "tree", "path", "blob", "sha256"}
        or candidate_binding.get("path") != CANDIDATE_MANIFEST_PATH
    ):
        raise PreflightError("candidate manifest bootstrap binding drift")
    candidate_raw = _verify_git_binding(root, candidate_binding, "candidate manifest")
    manifest = _bootstrap_manifest(candidate_raw)
    freeze_commit, freeze_tree = git_identity(
        root, manifest["candidate_freeze"]["commit"]
    )
    if (
        freeze_commit != manifest["candidate_freeze"]["commit"]
        or freeze_tree != manifest["candidate_freeze"]["tree"]
    ):
        raise PreflightError("candidate component freeze identity drift")
    runner_binding = _bootstrap_role(manifest, "runner", RUNNER_PATH)
    checker_binding = _bootstrap_role(manifest, "candidate_checker", CHECKER_PATH)
    frozen_runner = _verify_git_binding(root, runner_binding, "runner")
    runner_source = runner_path or Path(__file__)
    live_runner = runner_source.resolve()
    expected_runner = (root / RUNNER_PATH).resolve()
    try:
        metadata = runner_source.lstat()
        live_bytes = runner_source.read_bytes()
    except OSError as error:
        raise PreflightError("runner entrypoint is unavailable") from error
    if (
        live_runner != expected_runner
        or runner_source.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or live_bytes != frozen_runner
    ):
        raise PreflightError(
            "runner entrypoint differs from immutable component freeze"
        )
    checker_raw = _verify_git_binding(root, checker_binding, "candidate checker")
    snapshot = RuntimeSnapshot()
    try:
        snapshot.add(candidate_binding, candidate_raw, label="candidate manifest")
        snapshot.add(runner_binding, frozen_runner, label="runner")
        checker_path = snapshot.add(
            checker_binding, checker_raw, label="candidate checker"
        )
        checker = _import_snapshot_module(
            snapshot, "check_ae_sq1_candidate", CHECKER_PATH
        )
        profile = checker.load_verified_candidate(
            root,
            candidate_binding["commit"],
            require_live=False,
        )
        if (
            profile.get("candidate_commit") != freeze_commit
            or profile.get("candidate_tree") != freeze_tree
            or profile.get("manifest_sha256") != candidate_binding["sha256"]
            or profile.get("bindings", {}).get("runner") != runner_binding
            or profile.get("bindings", {}).get("candidate_checker") != checker_binding
            or Path(checker.__file__ or "").resolve() != checker_path.resolve()
        ):
            raise PreflightError("snapshot checker did not preserve bootstrap custody")
        for role, binding in profile["bindings"].items():
            raw = _verify_git_binding(root, binding, role)
            snapshot.add(binding, raw, label=role)
        policy = profile["documents"]["reference_policy"]
        catalog = (
            policy.get("capability_catalog") if isinstance(policy, Mapping) else None
        )
        if not isinstance(catalog, list) or len(catalog) != 8:
            raise PreflightError("reference policy catalog is unavailable to snapshot")
        for row in catalog:
            file_row = row.get("file") if isinstance(row, Mapping) else None
            if not isinstance(file_row, Mapping) or set(file_row) != {
                "path",
                "sha256",
                "size_bytes",
                "git_blob_sha1",
            }:
                raise PreflightError("reference policy file binding is invalid")
            reference_binding = {
                "commit": freeze_commit,
                "tree": freeze_tree,
                "path": file_row["path"],
                "blob": file_row["git_blob_sha1"],
                "sha256": file_row["sha256"],
            }
            reference_raw = _verify_git_binding(
                root, reference_binding, "reference catalog file"
            )
            if len(reference_raw) != file_row["size_bytes"]:
                raise PreflightError("reference catalog size drift")
            snapshot.add(
                reference_binding, reference_raw, label="reference catalog file"
            )
    except Exception:
        snapshot.close()
        raise
    return snapshot, profile


def _load_runtime_modules(
    snapshot: RuntimeSnapshot,
    profile: Mapping[str, Any],
) -> tuple[Any, Any, Any, Any]:
    try:
        resolver = _import_snapshot_module(
            snapshot,
            "resolve_ae_sq1_slec",
            profile["bindings"]["resolver"]["path"],
        )
        validator = _import_snapshot_module(
            snapshot,
            "validate_ae_sq1_corpus",
            profile["bindings"]["corpus_validator"]["path"],
        )
        scorer = _import_snapshot_module(
            snapshot,
            "score_ae_sq1_aq",
            profile["bindings"]["scorer"]["path"],
        )
        run_index = _import_snapshot_module(
            snapshot,
            "ae_sq1_run_index",
            profile["bindings"]["run_index"]["path"],
        )
    except (KeyError, TypeError) as error:
        raise PreflightError("candidate runtime role binding is unavailable") from error
    return validator, scorer, resolver, run_index


def _scorer_binding(
    profile: Mapping[str, Any],
    corpus_digest: str,
    *,
    host_sha256: str,
) -> dict[str, Any]:
    bindings = profile["bindings"]
    return {
        "program_id": "AE-SQ1",
        "candidate_id": profile["candidate_id"],
        "candidate_commit": profile["candidate_commit"],
        "candidate_tree": profile["candidate_tree"],
        "candidate_manifest_sha256": profile["manifest_sha256"],
        "runner_sha256": bindings["runner"]["sha256"],
        "evaluator_sha256": bindings["scorer"]["sha256"],
        "corpus_validator_sha256": bindings["corpus_validator"]["sha256"],
        "corpus_sha256": corpus_digest,
        "model_id": MODEL,
        "reasoning": REASONING,
        "tools_sha256": digest(
            {
                "disabled_features": DISABLED_FEATURES,
                "config_overrides": CONFIG_OVERRIDES,
                "sandbox": "read-only",
                "approval": "never",
            }
        ),
        "host_sha256": host_sha256,
    }


def _host_digest() -> str:
    return digest(
        {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        }
    )


def _parent_resolution(
    state: Mapping[str, Any],
    *,
    task_text: str,
    condition: str,
    raw_outputs: Sequence[tuple[bytes, str]],
    projected: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Resolve, authenticate, and only then project the parent record for scoring."""
    if len(raw_outputs) != 4 or len(projected) != 4:
        raise CompletedInvalid(
            "parent resolution lacks exactly four capsule observations"
        )
    trusted = state["profile"]["trusted_json"]
    try:
        record = state["resolver"].resolve(
            task_text,
            condition,
            raw_outputs,
            trusted["candidate_authority"],
            trusted["reference_policy"],
            repository_root=state["snapshot_root"],
        )
        record_raw = canonical_json(record)
        verified = state["resolver"].verify_resolution_record(
            (record_raw, sha256_bytes(record_raw)),
            trusted["candidate_authority"],
            trusted["reference_policy"],
            trusted["resolution_schema"],
        )
        if type(verified) is not dict:
            raise ValueError("resolution verifier returned a non-exact mapping")
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
    except (KeyError, TypeError, ValueError, RunnerError) as error:
        raise CompletedInvalid(
            "parent resolution record failed trusted verification"
        ) from error
    return {
        "status": status,
        "selected_slots": selected,
        "reference_bundle": references,
    }


def _zero_model_preflight(state: dict[str, Any]) -> None:
    validator, scorer = state["validator"], state["scorer"]
    binding = state["scorer_binding"]
    binding_sha = validator.digest(binding)
    schedule_sha = state["schedule_digest"]
    observations: list[dict[str, Any]] = []
    for row in state["schedule"]:
        case = state["cases"][row["case_id"]]
        synthetic_anchor = _synthetic_anchor(case["task_text"])
        capsules: list[dict[str, Any]] = []
        raw_capsules: list[tuple[bytes, str]] = []
        for slot_id, expected in zip(
            SLOT_ORDER, case["expected_capsules"], strict=True
        ):
            packet_sha = validator.capsule_packet_digest(
                binding_digest=binding_sha,
                schedule_sha256=schedule_sha,
                condition=row["condition"],
                case_id=case["case_id"],
                task_sha256=case["task_text_nfc_sha256"],
                slot_id=slot_id,
            )
            capsules.append(
                {
                    "slot_id": slot_id,
                    "context_id": f"zero-{row['presentation_index']}-{slot_id}",
                    "invocation_count": 1,
                    "terminal_completed": True,
                    "parse_status": "parsed",
                    "output": dict(expected),
                    "binding_sha256": binding_sha,
                    "schedule_sha256": schedule_sha,
                    "packet_sha256": packet_sha,
                    "task_sha256": case["task_text_nfc_sha256"],
                }
            )
            raw_capsule = _runtime_capsule_bytes(
                {
                    "slot_id": slot_id,
                    "local_need": expected["local_need"],
                    "reference_need": expected["reference_need"],
                    "anchors": (
                        []
                        if "uncertain"
                        in (expected["local_need"], expected["reference_need"])
                        else [synthetic_anchor]
                    ),
                }
            )
            raw_capsules.append((raw_capsule, sha256_bytes(raw_capsule)))
        resolution = _parent_resolution(
            state,
            task_text=case["task_text"],
            condition=row["condition"],
            raw_outputs=raw_capsules,
            projected=case["expected_capsules"],
        )
        if resolution != case["expected_resolution"]:
            raise PreflightError(
                "candidate parent fold diverges from frozen corpus oracle"
            )
        observations.append(
            {
                "presentation_index": row["presentation_index"],
                "presentation_id": row["presentation_id"],
                "condition": row["condition"],
                "case_id": row["case_id"],
                "terminal_completed": True,
                "capsules": capsules,
                "resolution": resolution,
                "events": {key: False for key in EVENT_KEYS},
            }
        )
    result = scorer.score_aq(
        documents=state["corpus_documents"],
        historical_digest_inventory=state["historical_inventory"],
        observations=observations,
        binding=binding,
        complete_run_assertions={
            "runner_local_raw_persistence": False,
            "heldout_outcome_use": False,
        },
    )
    if result.get("status") != "pass":
        raise PreflightError("zero-model production projection failed")


def preflight(root: Path, run_commit: str) -> dict[str, Any]:
    """Verify exact candidate/corpus/run bytes and score 80 synthetic rows."""
    commit, tree = require_clean_exact_head(root, run_commit)
    manifest_raw = git_show(root, commit, RUN_MANIFEST_PATH)
    run_manifest = _strict_document(manifest_raw, "run manifest")
    candidate_binding = run_manifest.get("candidate_manifest")
    snapshot: RuntimeSnapshot | None = None
    try:
        snapshot, profile = _bootstrap_candidate(root, candidate_binding)
        run_binding = {
            "commit": commit,
            "tree": tree,
            "path": RUN_MANIFEST_PATH,
            "blob": git_blob(root, commit, RUN_MANIFEST_PATH),
            "sha256": sha256_bytes(manifest_raw),
        }
        snapshot.add(run_binding, manifest_raw, label="run manifest")
        schema = profile["documents"]["run_manifest_schema"]
        if list(Draft202012Validator(schema).iter_errors(run_manifest)):
            raise PreflightError("run manifest schema rejected input")
        if run_manifest["candidate_freeze"] != {
            "commit": profile["candidate_commit"],
            "tree": profile["candidate_tree"],
        }:
            raise PreflightError("run manifest candidate freeze drift")
        corpus_identity = run_manifest["corpus_freeze"]
        corpus = run_manifest["corpus"]
        if (
            corpus["schema"]["path"] != profile["bindings"]["corpus_schema"]["path"]
            or corpus["schema"]["blob"] != profile["bindings"]["corpus_schema"]["blob"]
            or corpus["schema"]["sha256"]
            != profile["bindings"]["corpus_schema"]["sha256"]
            or corpus["historical_inventory"]["path"]
            != profile["bindings"]["historical_task_digests"]["path"]
            or corpus["historical_inventory"]["blob"]
            != profile["bindings"]["historical_task_digests"]["blob"]
            or corpus["historical_inventory"]["sha256"]
            != profile["bindings"]["historical_task_digests"]["sha256"]
        ):
            raise PreflightError("corpus contract drifted after candidate freeze")
        split_a = _sealed_bytes(
            root,
            corpus_identity["commit"],
            corpus_identity["tree"],
            corpus["split_a"],
            "split A",
        )
        split_b = _sealed_bytes(
            root,
            corpus_identity["commit"],
            corpus_identity["tree"],
            corpus["split_b"],
            "split B",
        )
        schema_raw = _sealed_bytes(
            root,
            corpus_identity["commit"],
            corpus_identity["tree"],
            corpus["schema"],
            "corpus schema",
        )
        inventory_raw = _sealed_bytes(
            root,
            corpus_identity["commit"],
            corpus_identity["tree"],
            corpus["historical_inventory"],
            "historical digest inventory",
        )
        if (
            schema_raw != profile["trusted_json"]["corpus_schema"][0]
            or inventory_raw != profile["trusted_json"]["historical_task_digests"][0]
        ):
            raise PreflightError("corpus authority bytes differ across freezes")
        for label, binding, raw in (
            ("split A", corpus["split_a"], split_a),
            ("split B", corpus["split_b"], split_b),
        ):
            snapshot.add(
                {
                    "commit": corpus_identity["commit"],
                    "tree": corpus_identity["tree"],
                    **binding,
                },
                raw,
                label=label,
            )
        snapshot_sha = snapshot.seal()
        validator, scorer, resolver, run_index = _load_runtime_modules(
            snapshot, profile
        )
        if run_manifest["schedule"]["seed"] != validator.SCHEDULE_SEED:
            raise PreflightError("schedule seed drifted after candidate freeze")
        documents = [split_a, split_b]
        validation = validator.validate_corpora(
            documents,
            historical_digest_inventory=inventory_raw,
        )
        if not validation.passed or validation.corpus_digest is None:
            raise PreflightError("fresh corpus is not qualification-ready")
        parsed = [validator._as_document(raw) for raw in documents]
        cases = {
            case["case_id"]: case for document in parsed for case in document["cases"]
        }
        schedule = list(validator.build_schedule(tuple(sorted(cases))))
        schedule_sha = validator.schedule_digest(schedule)
        if schedule_sha != run_manifest["schedule"]["sha256"]:
            raise PreflightError("frozen schedule digest drift")
        host_sha = _host_digest()
        state = {
            "root": root,
            "snapshot": snapshot,
            "snapshot_root": snapshot.root,
            "snapshot_sha256": snapshot_sha,
            "runner_entrypoint": dict(profile["bindings"]["runner"]),
            "commit": commit,
            "tree": tree,
            "run_manifest": run_manifest,
            "run_manifest_sha256": sha256_bytes(manifest_raw),
            "profile": profile,
            "validator": validator,
            "scorer": scorer,
            "resolver": resolver,
            "run_index_module": run_index,
            "corpus_documents": documents,
            "historical_inventory": inventory_raw,
            "corpus_digest": validation.corpus_digest,
            "cases": cases,
            "schedule": schedule,
            "schedule_digest": schedule_sha,
            "host_sha256": host_sha,
        }
        state["scorer_binding"] = _scorer_binding(
            profile,
            validation.corpus_digest,
            host_sha256=host_sha,
        )
        _zero_model_preflight(state)
        return state
    except Exception:
        if snapshot is not None:
            snapshot.close()
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
        raise PreflightError("Codex auth source unavailable") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or source.is_symlink()
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
        or metadata.st_size <= 0
    ):
        raise PreflightError("Codex auth source is not private owner-only data")
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


def _explicit_env(home: Path) -> dict[str, str]:
    allowed = (
        "PATH",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TMPDIR",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
    )
    result = {key: os.environ[key] for key in allowed if key in os.environ}
    result["HOME"] = str(home)
    result["CODEX_HOME"] = str(home)
    return result


@contextmanager
def isolated_codex_home(
    source: Path, fingerprint: tuple[int, ...]
) -> Iterator[dict[str, str]]:
    temporary = tempfile.TemporaryDirectory(prefix="ae-sq1-codex-home-")
    home = Path(temporary.name)
    try:
        os.chmod(home, 0o700)
        current, metadata = _validated_auth_source()
        if current != source or _auth_fingerprint(metadata) != fingerprint:
            raise PreflightError("Codex auth source changed before child isolation")
        destination = home / "auth.json"
        shutil.copyfile(source, destination, follow_symlinks=False)
        os.chmod(destination, 0o600)
        copied = destination.lstat()
        if (
            destination.is_symlink()
            or not stat.S_ISREG(copied.st_mode)
            or copied.st_uid != os.getuid()
            or stat.S_IMODE(copied.st_mode) != 0o600
            or copied.st_nlink != 1
            or {path.name for path in home.iterdir()} != {"auth.json"}
        ):
            raise PreflightError("private auth copy failed")
        yield _explicit_env(home)
        if _auth_fingerprint(source.lstat()) != fingerprint:
            raise PreflightError("Codex auth source changed during child execution")
    finally:
        temporary.cleanup()
        if home.exists():
            raise PreflightError("isolated Codex home cleanup failed")


def _exact_probe(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        return False
    message = value[0]
    content = message.get("content")
    return (
        message.get("type") == "message"
        and message.get("role") == "user"
        and isinstance(content, list)
        and len(content) == 1
        and content[0] == {"type": "input_text", "text": ISOLATION_PROBE}
    )


def codex_preflight(
    codex: str, run: Callable[..., Any] = subprocess.run
) -> dict[str, str]:
    resolved = (
        Path(codex).resolve()
        if Path(codex).is_absolute()
        else (Path(shutil.which(codex)).resolve() if shutil.which(codex) else None)
    )
    if resolved is None or not resolved.is_file():
        raise PreflightError("Codex CLI is unavailable")
    source, metadata = _validated_auth_source()
    fingerprint = _auth_fingerprint(metadata)
    with isolated_codex_home(source, fingerprint) as environment:
        version = run(
            [str(resolved), "--version"],
            env=environment,
            capture_output=True,
            text=True,
            timeout=PREFLIGHT_TIMEOUT_SECONDS,
        )
        help_result = run(
            [str(resolved), "exec", "--help"],
            env=environment,
            capture_output=True,
            text=True,
            timeout=PREFLIGHT_TIMEOUT_SECONDS,
        )
        help_text = (help_result.stdout or "") + (help_result.stderr or "")
        required = (
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--strict-config",
            "--skip-git-repo-check",
            "--sandbox",
            "--output-schema",
            "--json",
        )
        if (
            version.returncode
            or help_result.returncode
            or any(flag not in help_text for flag in required)
        ):
            raise PreflightError("Codex 0.147 isolation capability unavailable")
        version_text = version.stdout.strip()
        if re.fullmatch(r"codex-cli 0\.147\.\d+", version_text) is None:
            raise PreflightError("Codex CLI is outside the frozen 0.147 lifecycle")
        argv = [
            str(resolved),
            "--ask-for-approval",
            "never",
            "--model",
            MODEL,
            "--sandbox",
            "read-only",
        ]
        for feature in DISABLED_FEATURES:
            argv.extend(["--disable", feature])
        for override in CONFIG_OVERRIDES:
            argv.extend(["-c", override])
        argv.extend(["debug", "prompt-input", ISOLATION_PROBE])
        with tempfile.TemporaryDirectory(prefix="ae-sq1-probe-cwd-") as directory:
            if any(Path(directory).iterdir()):
                raise PreflightError("probe cwd is not empty")
            probe = run(
                argv,
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
                timeout=PREFLIGHT_TIMEOUT_SECONDS,
            )
    if probe.returncode or probe.stderr:
        raise PreflightError("exact one-user-input isolation probe failed")
    try:
        rendered = strict_json(probe.stdout)
    except (json.JSONDecodeError, ValueError) as error:
        raise PreflightError("isolation probe output is invalid") from error
    if not _exact_probe(rendered):
        raise PreflightError("global prompt material entered isolated context")
    return {
        "id": "codex-cli",
        "path": str(resolved),
        "version": version_text,
        "sha256": sha256_bytes(resolved.read_bytes()),
    }


def child_argv(info: Mapping[str, str], schema_path: Path) -> list[str]:
    argv = [
        info["path"],
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
    if not isinstance(value, dict) or set(value) not in (
        {"input_tokens", "cached_input_tokens", "output_tokens"},
        {"input_tokens", "cached_input_tokens", "output_tokens", "total_tokens"},
    ):
        raise CompletedInvalid("turn.completed usage is not closed")
    for key in ("input_tokens", "cached_input_tokens", "output_tokens"):
        if type(value[key]) is not int or value[key] < 0:
            raise CompletedInvalid(
                "turn.completed usage is not an exact nonnegative integer"
            )
    total = value.get("total_tokens", value["input_tokens"] + value["output_tokens"])
    result = {
        "input_tokens": value["input_tokens"],
        "cached_input_tokens": value["cached_input_tokens"],
        "output_tokens": value["output_tokens"],
        "total_tokens": total,
    }
    if (
        type(total) is not int
        or total != result["input_tokens"] + result["output_tokens"]
    ):
        raise CompletedInvalid("turn.completed total usage is inconsistent")
    if result["cached_input_tokens"] > result["input_tokens"]:
        raise CompletedInvalid("cached usage exceeds input usage")
    return result


def _project_output(
    resolver: Any,
    capsule_ingress: tuple[bytes, str],
    *,
    task_text: str,
    condition: str,
    slot_id: str,
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(capsule_ingress) is not tuple
        or len(capsule_ingress) != 2
        or type(capsule_ingress[0]) is not bytes
        or not isinstance(capsule_ingress[1], str)
        or sha256_bytes(capsule_ingress[0]) != capsule_ingress[1]
    ):
        raise ValueError("runtime capsule ingress is not internally pinned")
    output = strict_json(capsule_ingress[0])
    if not isinstance(output, dict):
        raise ValueError("runtime capsule ingress is not an object")
    for name in (
        "project_runtime_capsule",
        "normalize_runtime_capsule",
        "project_capsule",
    ):
        function = getattr(resolver, name, None)
        if callable(function):
            return function(
                output,
                task_text=task_text,
                condition=condition,
                slot_id=slot_id,
                authority=profile["documents"]["candidate_authority"],
                reference_policy=profile["documents"]["reference_policy"],
            )
    if tuple(output) == ("slot_id", "local_need", "reference_need"):
        return dict(output)
    raise ValueError("SLEC resolver lacks a runtime capsule projection API")


def parse_events(
    raw: bytes,
    *,
    resolver: Any,
    task_text: str,
    condition: str,
    slot_id: str,
    profile: Mapping[str, Any],
) -> InvocationOutcome:
    lines = [line for line in raw.splitlines() if line]

    def has_exact_completion() -> bool:
        for line in lines:
            try:
                event = strict_json(line)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                continue
            if isinstance(event, dict) and event.get("type") == "turn.completed":
                return True
        return False

    try:
        events = [strict_json(line) for line in lines]
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        if has_exact_completion():
            raise _completed_invalid(
                "completed event stream is malformed",
                context_id=None,
                usage=None,
            ) from error
        raise InfrastructureError(
            "event stream is malformed before completion"
        ) from error
    if not events:
        raise InfrastructureError("event stream is empty before completion")
    context: str | None = None
    turn_started = False
    turn_completed = False
    message: str | None = None
    usage: dict[str, int] | None = None
    violation: str | None = None
    failure_seen = False
    for index, event in enumerate(events):
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            violation = violation or "event stream shape is unavailable"
            continue
        kind = event["type"]
        if turn_completed:
            violation = violation or "event followed terminal completion"
            continue
        if kind == "thread.started":
            if (
                set(event) != {"type", "thread_id"}
                or index != 0
                or context is not None
                or not isinstance(event.get("thread_id"), str)
                or not event["thread_id"]
            ):
                violation = violation or "thread lifecycle is ambiguous"
            else:
                context = event["thread_id"]
        elif kind == "turn.started":
            if set(event) != {"type"} or turn_started or context is None or index != 1:
                violation = violation or "turn lifecycle is ambiguous"
            else:
                turn_started = True
        elif kind == "item.completed":
            item = event.get("item")
            if (
                set(event) != {"type", "item"}
                or not turn_started
                or not isinstance(item, dict)
                or set(item) != {"id", "type", "text"}
                or not isinstance(item.get("id"), str)
                or not item["id"]
                or not isinstance(item.get("text"), str)
            ):
                violation = violation or "completed item is malformed"
            elif item.get("type") == "reasoning":
                if message is not None:
                    violation = violation or "reasoning followed the agent message"
            elif item.get("type") == "agent_message":
                if message is not None or not item["text"].strip():
                    violation = violation or "agent message lifecycle is ambiguous"
                else:
                    message = item["text"]
            else:
                violation = violation or "forbidden completed item type"
        elif kind == "turn.completed":
            if set(event) != {"type", "usage"} or not turn_started:
                violation = violation or "turn completion lifecycle is ambiguous"
            else:
                try:
                    usage = _usage(event.get("usage"))
                except CompletedInvalid as error:
                    violation = violation or str(error)
                turn_completed = True
        elif kind in {"turn.failed", "error"}:
            failure_seen = True
        else:
            violation = violation or "unknown or forbidden event type"
    if violation is not None:
        if turn_completed:
            raise _completed_invalid(
                violation,
                context_id=context,
                usage=usage,
            )
        raise InfrastructureError(violation)
    if failure_seen:
        if turn_completed or message is not None:
            raise _completed_invalid(
                "completed work has a failure event",
                context_id=context,
                usage=usage,
            )
        raise InfrastructureError("child failed before a completed observation")
    if context is None or not turn_started or not turn_completed or usage is None:
        raise InfrastructureError("child lacks closed completion")
    if message is None:
        return InvocationOutcome(
            "malformed", None, None, b"", sha256_bytes(b""), context, usage
        )
    capsule_raw = message.encode("utf-8", "strict")
    capsule_sha = sha256_bytes(capsule_raw)
    try:
        value = strict_json(capsule_raw)
        if not isinstance(value, dict):
            raise ValueError("capsule is not object")
        projected = _project_output(
            resolver,
            (capsule_raw, capsule_sha),
            task_text=task_text,
            condition=condition,
            slot_id=slot_id,
            profile=profile,
        )
        if (
            tuple(projected) != ("slot_id", "local_need", "reference_need")
            or projected["slot_id"] != slot_id
        ):
            raise ValueError("projected capsule is not closed")
        if projected["local_need"] not in {"yes", "no", "uncertain"} or projected[
            "reference_need"
        ] not in {
            "none",
            "core",
            "focused",
            "uncertain",
        }:
            raise ValueError("projected capsule domain drift")
    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
        return InvocationOutcome(
            "malformed",
            None,
            None,
            capsule_raw,
            capsule_sha,
            context,
            usage,
        )
    return InvocationOutcome(
        "parsed",
        value,
        projected,
        capsule_raw,
        capsule_sha,
        context,
        usage,
    )


def _validate_packet(packet: Any, slot_id: str) -> dict[str, Any]:
    production_keys = (
        "instruction",
        "task_text",
        "condition_id",
        "slot_id",
        "condition_slot_card",
        "anonymous_menu",
    )
    if not isinstance(packet, dict) or tuple(packet) != production_keys:
        raise PreflightError("assessor packet is not the closed one-card projection")
    if not isinstance(packet.get("task_text"), str) or not packet["task_text"]:
        raise PreflightError("assessor packet task text is unavailable")
    if packet.get("slot_id") != slot_id or packet.get("condition_id") not in CONDITIONS:
        raise PreflightError("assessor packet identity drift")
    card = packet["condition_slot_card"]
    exposed = {
        "instruction": packet["instruction"],
        "condition_slot_card": card,
        "anonymous_menu": packet["anonymous_menu"],
    }
    if not isinstance(card, dict):
        raise PreflightError("assessor packet has the wrong slot card")
    if "slot_id" in card and card.get("slot_id") != slot_id:
        raise PreflightError("assessor packet has the wrong slot card")
    encoded = canonical_json(exposed).decode("utf-8").casefold()
    if any(word in encoded for word in ("adviser", "advisor", "catalog", "path")):
        raise PreflightError("slot card exposes adviser/path/catalog material")
    for other in SLOT_ORDER:
        if other != slot_id and re.search(
            rf"(?<![a-z0-9]){other}(?![a-z0-9])", encoded
        ):
            raise PreflightError("slot card exposes another slot")
    return packet


def build_packet(
    state: Mapping[str, Any],
    *,
    task_text: str,
    condition: str,
    slot_id: str,
) -> dict[str, Any]:
    resolver = state["resolver"]
    authority = state["profile"]["trusted_json"]["candidate_authority"]
    for name in (
        "build_assessor_packet",
        "build_slot_packet",
        "build_condition_packet",
    ):
        function = getattr(resolver, name, None)
        if callable(function):
            packet = function(
                task_text=task_text,
                condition=condition,
                slot_id=slot_id,
                authority=authority,
            )
            return _validate_packet(packet, slot_id)
    raise PreflightError("SLEC resolver lacks an isolated packet builder API")


def invoke_one(
    packet: dict[str, Any],
    *,
    state: Mapping[str, Any],
    cli: Mapping[str, str],
    condition: str,
    slot_id: str,
    run: Callable[..., Any] = subprocess.run,
) -> InvocationOutcome:
    source, metadata = _validated_auth_source()
    fingerprint = _auth_fingerprint(metadata)
    schema = (
        state["snapshot_root"] / state["profile"]["bindings"]["capsule_schema"]["path"]
    )
    with isolated_codex_home(source, fingerprint) as environment:
        with tempfile.TemporaryDirectory(prefix="ae-sq1-child-cwd-") as directory:
            cwd = Path(directory)
            if any(cwd.iterdir()):
                raise PreflightError("child cwd is not fresh and empty")
            try:
                completed = run(
                    child_argv(cli, schema),
                    input=canonical_json(packet),
                    cwd=cwd,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=CHILD_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired as error:
                failure = InfrastructureError(
                    "isolated child timed out before closed completion"
                )
                failure.observed = bool(error.stdout)  # type: ignore[attr-defined]
                raise failure from error
            except OSError as error:
                failure = InfrastructureError("isolated child launch failed")
                failure.observed = False  # type: ignore[attr-defined]
                raise failure from error
    raw = (
        completed.stdout
        if isinstance(completed.stdout, bytes)
        else str(completed.stdout or "").encode()
    )
    try:
        outcome = parse_events(
            raw,
            resolver=state["resolver"],
            task_text=packet["task_text"],
            condition=condition,
            slot_id=slot_id,
            profile=state["profile"],
        )
    except RunnerError as error:
        error.observed = bool(raw)  # type: ignore[attr-defined]
        raise
    if completed.returncode:
        return InvocationOutcome(
            "malformed",
            None,
            None,
            outcome.capsule_raw,
            outcome.capsule_sha256,
            outcome.context_id,
            outcome.usage,
        )
    return outcome


def _four_calls(
    state: Mapping[str, Any],
    cli: Mapping[str, str],
    *,
    task_text: str,
    condition: str,
    invoke: Callable[..., InvocationOutcome],
) -> list[InvocationOutcome | RunnerError]:
    jobs = [
        (
            slot_id,
            build_packet(
                state, task_text=task_text, condition=condition, slot_id=slot_id
            ),
        )
        for slot_id in SLOT_ORDER
    ]
    results: list[InvocationOutcome | RunnerError | None] = [None] * 4
    with ThreadPoolExecutor(
        max_workers=4, thread_name_prefix="ae-sq1-assessor"
    ) as pool:
        futures = {
            pool.submit(
                invoke,
                packet,
                state=state,
                cli=cli,
                condition=condition,
                slot_id=slot_id,
            ): index
            for index, (slot_id, packet) in enumerate(jobs)
        }
        for future in as_completed(futures):
            index = futures[future]
            try:
                results[index] = future.result()
            except RunnerError as error:
                results[index] = error
    if any(result is None for result in results):
        raise InfrastructureError("assessor pool lost a result")
    return list(results)  # type: ignore[arg-type]


def _index_binding(state: Mapping[str, Any], cli: Mapping[str, str]) -> dict[str, Any]:
    manifest = state["run_manifest"]
    profile = state["profile"]
    corpus = manifest["corpus"]
    return {
        "program_id": "AE-SQ1",
        "candidate_manifest": dict(manifest["candidate_manifest"]),
        "candidate_freeze": dict(profile["bindings"]["candidate_authority"]),
        "run_manifest": {
            "commit": state["commit"],
            "tree": state["tree"],
            "path": RUN_MANIFEST_PATH,
            "blob": git_blob(state["root"], state["commit"], RUN_MANIFEST_PATH),
            "sha256": state["run_manifest_sha256"],
        },
        "corpus": {
            "content_sha256": state["corpus_digest"],
            "split_a": {
                "commit": manifest["corpus_freeze"]["commit"],
                "tree": manifest["corpus_freeze"]["tree"],
                **corpus["split_a"],
            },
            "split_b": {
                "commit": manifest["corpus_freeze"]["commit"],
                "tree": manifest["corpus_freeze"]["tree"],
                **corpus["split_b"],
            },
        },
        "runner": dict(profile["bindings"]["runner"]),
        "cli": {"id": "codex-cli", "version": cli["version"], "sha256": cli["sha256"]},
        "model": {"id": MODEL, "reasoning": REASONING, "fallback": False},
        "schedule": {
            "seed": manifest["schedule"]["seed"],
            "sha256": state["schedule_digest"],
            "presentations": 80,
            "calls_per_presentation": 4,
        },
        "host": {"sha256": state["host_sha256"]},
    }


def _assert_cli_manifest(state: Mapping[str, Any], cli: Mapping[str, str]) -> None:
    runtime_cli = state["run_manifest"]["runtime"]["cli"]
    if runtime_cli != {
        "id": "codex-cli",
        "version": cli["version"],
        "sha256": cli["sha256"],
    }:
        raise PreflightError("live CLI differs from frozen run manifest")


def _invalid_digest(label: str, index_state: Mapping[str, Any]) -> str:
    return digest(
        {
            "program_id": "AE-SQ1",
            "status": "invalid",
            "reason_class": label,
            "calls_started": index_state["batch_calls_started"],
            "calls_completed": index_state["batch_calls_completed"],
            "usage": index_state["batch_usage"],
        }
    )


def _perform_canary(
    state: Mapping[str, Any],
    cli: Mapping[str, str],
    binding: Mapping[str, Any],
    index: Any,
    *,
    invoke: Callable[..., InvocationOutcome],
) -> dict[str, Any]:
    task_text = "Assess whether this local, reversible engineering request needs only your assigned capability."
    # Validate every deterministic non-corpus packet before creating a lease.
    for slot_id in SLOT_ORDER:
        build_packet(state, task_text=task_text, condition="reduced", slot_id=slot_id)
    capability = index.begin_canary(binding)
    for attempt in (1, 2):
        for _slot in SLOT_ORDER:
            index.canary_call_started(binding, capability)
        results = _four_calls(
            state,
            cli,
            task_text=task_text,
            condition="reduced",
            invoke=invoke,
        )
        observed = False
        completed = 0
        integrity_error = False
        malformed_output = False
        projected: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, RunnerError):
                result_observed = bool(getattr(result, "observed", False))
                observed = observed or result_observed
                integrity_error = (
                    integrity_error
                    or result_observed
                    or isinstance(result, CompletedInvalid)
                )
                continue
            observed = True
            completed += 1
            index.canary_observation(binding, capability)
            index.canary_call_completed(binding, capability, result.usage)
            malformed_output = (
                malformed_output
                or result.parse_status != "parsed"
                or result.projected is None
            )
            if result.projected is not None:
                projected.append(result.projected)
        if observed and completed == 0:
            index.canary_observation(binding, capability)
        if not observed and completed == 0 and not integrity_error and attempt == 1:
            index.retry_canary(binding, capability)
            continue
        if completed == 4 and not malformed_output and len(projected) == 4:
            raw_outputs = [
                (result.capsule_raw, result.capsule_sha256)
                for result in results
                if isinstance(result, InvocationOutcome)
            ]
            try:
                resolution = _parent_resolution(
                    state,
                    task_text=task_text,
                    condition="reduced",
                    raw_outputs=raw_outputs,
                    projected=projected,
                )
            except CompletedInvalid:
                index.fail_canary(binding, capability, invalid=True)
                raise
            aggregate = digest({"status": "passed", "resolution": resolution})
            index.complete_canary(binding, capability, aggregate)
            return index.state(binding)
        index.fail_canary(
            binding,
            capability,
            invalid=integrity_error or completed != 4,
        )
        raise CompletedInvalid(
            "canary closed without four valid completed assessor capsules"
        )
    raise InfrastructureError("canary retry state exhausted")


def _prepared_execution(
    root: Path,
    run_commit: str,
    codex: str,
) -> tuple[dict[str, Any], dict[str, str], dict[str, Any], Any]:
    state = preflight(root, run_commit)
    try:
        cli = codex_preflight(codex)
        _assert_cli_manifest(state, cli)
        binding = _index_binding(state, cli)
        index = state["run_index_module"].AESQ1RunIndex(root)
    except Exception:
        state["snapshot"].close()
        raise
    return state, cli, binding, index


def run_canary(
    *,
    root: Path,
    run_commit: str,
    codex: str,
    invoke: Callable[..., InvocationOutcome] = invoke_one,
) -> dict[str, Any]:
    state, cli, binding, index = _prepared_execution(root, run_commit, codex)
    try:
        final = _perform_canary(state, cli, binding, index, invoke=invoke)
        return receipt("canary", "pass", state, final)
    finally:
        state["snapshot"].close()


def _capsule_observation(
    state: Mapping[str, Any],
    row: Mapping[str, Any],
    case: Mapping[str, Any],
    slot_id: str,
    result: InvocationOutcome,
) -> dict[str, Any]:
    binding_sha = state["validator"].digest(state["scorer_binding"])
    packet_sha = state["validator"].capsule_packet_digest(
        binding_digest=binding_sha,
        schedule_sha256=state["schedule_digest"],
        condition=row["condition"],
        case_id=row["case_id"],
        task_sha256=case["task_text_nfc_sha256"],
        slot_id=slot_id,
    )
    return {
        "slot_id": slot_id,
        "context_id": result.context_id,
        "invocation_count": 1,
        "terminal_completed": True,
        "parse_status": result.parse_status,
        "output": result.projected,
        "binding_sha256": binding_sha,
        "schedule_sha256": state["schedule_digest"],
        "packet_sha256": packet_sha,
        "task_sha256": case["task_text_nfc_sha256"],
    }


def _perform_batch(
    state: Mapping[str, Any],
    cli: Mapping[str, str],
    binding: Mapping[str, Any],
    index: Any,
    *,
    invoke: Callable[..., InvocationOutcome],
) -> dict[str, Any]:
    capability = index.begin_batch(binding)
    observations: list[dict[str, Any]] = []
    try:
        for row in state["schedule"]:
            case = state["cases"][row["case_id"]]
            index.presentation_started(binding, capability)
            for _slot in SLOT_ORDER:
                index.batch_call_started(binding, capability)
            results = _four_calls(
                state,
                cli,
                task_text=case["task_text"],
                condition=row["condition"],
                invoke=invoke,
            )
            capsules: list[dict[str, Any]] = []
            projected: list[dict[str, Any]] = []
            raw_outputs: list[tuple[bytes, str]] = []
            failures: list[RunnerError] = []
            for slot_id, result in zip(SLOT_ORDER, results, strict=True):
                if isinstance(result, RunnerError):
                    observed = bool(getattr(result, "observed", False))
                    if observed:
                        index.batch_observation(binding, capability)
                    if isinstance(result, CompletedInvalid) and observed:
                        retained = getattr(result, "outcome", None)
                        if not isinstance(retained, InvocationOutcome):
                            retained = InvocationOutcome(
                                "malformed",
                                None,
                                None,
                                b"",
                                sha256_bytes(b""),
                                "",
                                {
                                    "input_tokens": 0,
                                    "cached_input_tokens": 0,
                                    "output_tokens": 0,
                                    "total_tokens": 0,
                                },
                            )
                        if not retained.context_id:
                            retained = InvocationOutcome(
                                "malformed",
                                None,
                                None,
                                retained.capsule_raw,
                                retained.capsule_sha256,
                                f"completed-invalid-{row['presentation_index']}-{slot_id}",
                                retained.usage,
                            )
                        index.batch_call_completed(
                            binding,
                            capability,
                            retained.usage,
                        )
                        capsules.append(
                            _capsule_observation(state, row, case, slot_id, retained)
                        )
                        continue
                    failures.append(result)
                    continue
                index.batch_observation(binding, capability)
                index.batch_call_completed(binding, capability, result.usage)
                capsules.append(_capsule_observation(state, row, case, slot_id, result))
                if result.projected is not None:
                    projected.append(result.projected)
                raw_outputs.append((result.capsule_raw, result.capsule_sha256))
            if failures:
                raise failures[0]
            resolution: dict[str, Any] | None = None
            if len(projected) == 4 and all(
                capsule["parse_status"] == "parsed" for capsule in capsules
            ):
                resolution = _parent_resolution(
                    state,
                    task_text=case["task_text"],
                    condition=row["condition"],
                    raw_outputs=raw_outputs,
                    projected=projected,
                )
            observations.append(
                {
                    "presentation_index": row["presentation_index"],
                    "presentation_id": row["presentation_id"],
                    "condition": row["condition"],
                    "case_id": row["case_id"],
                    "terminal_completed": True,
                    "capsules": capsules,
                    "resolution": resolution,
                    "events": {key: False for key in EVENT_KEYS},
                }
            )
            index.presentation_completed(binding, capability)
        result = state["scorer"].score_aq(
            documents=state["corpus_documents"],
            historical_digest_inventory=state["historical_inventory"],
            observations=observations,
            binding=state["scorer_binding"],
            complete_run_assertions={
                "runner_local_raw_persistence": False,
                "heldout_outcome_use": False,
            },
        )
        index.complete_batch(
            binding,
            capability,
            status="passed" if result["status"] == "pass" else "failed",
            aggregate_digest=result["aggregate_digest"],
        )
    except Exception as error:
        current = index.state(binding)
        if current["batch_status"] == "started":
            index.mark_batch_invalid(
                binding,
                capability,
                _invalid_digest(type(error).__name__, current),
            )
        raise
    return index.state(binding)


def execute_batch(
    *,
    root: Path,
    run_commit: str,
    codex: str,
    invoke: Callable[..., InvocationOutcome] = invoke_one,
) -> dict[str, Any]:
    """Run the authorized canary and batch in one process and index instance."""
    state, cli, binding, index = _prepared_execution(root, run_commit, codex)
    try:
        _perform_canary(state, cli, binding, index, invoke=invoke)
        final = _perform_batch(state, cli, binding, index, invoke=invoke)
        status = "pass" if final["batch_status"] == "passed" else "fail"
        return receipt("execute", status, state, final)
    finally:
        state["snapshot"].close()


def _combined_usage(index_state: Mapping[str, Any]) -> dict[str, int]:
    return {
        key: index_state["canary_usage"][key] + index_state["batch_usage"][key]
        for key in (
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "total_tokens",
        )
    }


def receipt(
    mode: str,
    status: str,
    state: Mapping[str, Any],
    index_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    custody = {
        "runner_entrypoint": dict(state["runner_entrypoint"]),
        "runtime_snapshot_sha256": state["snapshot_sha256"],
    }
    if mode == "dry-run":
        return {
            "program_id": "AE-SQ1",
            "mode": mode,
            "status": status,
            "run_commit": state["commit"],
            "run_tree": state["tree"],
            "live_calls_attempted": 0,
            "live_calls_completed": 0,
            "aggregate_digest": None,
            **custody,
        }
    if index_state is None:
        raise RunnerError("live receipt lacks index state")
    if mode == "canary":
        attempted = index_state["canary_calls_started"]
        completed = index_state["canary_calls_completed"]
        usage = dict(index_state["canary_usage"])
    elif mode == "execute":
        attempted = (
            index_state["canary_calls_started"] + index_state["batch_calls_started"]
        )
        completed = (
            index_state["canary_calls_completed"] + index_state["batch_calls_completed"]
        )
        usage = _combined_usage(index_state)
    else:
        raise RunnerError("receipt mode is unavailable")
    return {
        "program_id": "AE-SQ1",
        "mode": mode,
        "status": status,
        "run_commit": state["commit"],
        "run_tree": state["tree"],
        "live_calls_attempted": attempted,
        "live_calls_completed": completed,
        "canary_calls_attempted": index_state["canary_calls_started"],
        "canary_calls_completed": index_state["canary_calls_completed"],
        "batch_calls_attempted": index_state["batch_calls_started"],
        "batch_calls_completed": index_state["batch_calls_completed"],
        "usage": usage,
        "aggregate_digest": index_state["aggregate_digest"],
        "custody_marker": index_state["terminal_marker"],
        **custody,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--canary", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run-commit", required=True)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--usage-approval", action="append", default=[])
    args = parser.parse_args(argv)
    if HEX40.fullmatch(args.run_commit) is None:
        parser.error("--run-commit must be an exact lowercase 40-hex SHA")
    if args.canary and args.usage_approval != [CANARY_APPROVAL]:
        parser.error(f"--canary requires exactly --usage-approval {CANARY_APPROVAL}")
    if args.execute and args.usage_approval != [CANARY_APPROVAL, BATCH_APPROVAL]:
        parser.error(
            "--execute requires ordered dual approval: "
            f"--usage-approval {CANARY_APPROVAL} --usage-approval {BATCH_APPROVAL}"
        )
    if args.dry_run and args.usage_approval:
        parser.error("--dry-run does not accept usage approval")
    if args.dry_run:
        state = preflight(args.root, args.run_commit)
        try:
            result = receipt("dry-run", "pass", state, None)
        finally:
            state["snapshot"].close()
    elif args.canary:
        result = run_canary(
            root=args.root, run_commit=args.run_commit, codex=args.codex
        )
    else:
        result = execute_batch(
            root=args.root, run_commit=args.run_commit, codex=args.codex
        )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
