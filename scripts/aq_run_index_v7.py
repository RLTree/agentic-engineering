#!/usr/bin/env python3
"""Private, zero-content custody index for the AQ7 evaluator.

This module deliberately has no corpus, model, or subprocess-runner integration.
Its only durable data is a closed binding and a small state machine stored below
the resolved Git common directory.  A later evaluator-owned runner must call
``begin_batch`` immediately before it launches its first corpus subprocess.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import subprocess
import tempfile
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping


class RunIndexError(RuntimeError):
    """A custody, schema, or state-machine violation (always fail closed)."""


INDEX_NAME = ".aq-run-index-v7"
SCHEMA_VERSION = "aq-run-index-v7"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ATOM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_IDENTITY_NAMES = ("protocol", "reference_policy", "corpus", "candidate", "runner", "evaluator", "validator")
_FORBIDDEN = ("prompt", "fact", "observation", "context", "transcript", "stderr", "provider", "output", "content", "path", "private")
_RETRY_REASONS = frozenset({"launch_failed", "transport_failed", "precompletion_infrastructure"})
_CANARY_FAILURE_REASONS = frozenset({"retry_exhausted", "malformed_or_content_failure"})
_BATCH_INTERRUPTION_REASONS = frozenset({"crash_ambiguous", "infrastructure_interrupted"})
_AUTHORITY = re.compile(r"^AQ7-RUN-AUTHORITY corpus=([0-9a-f]{40}) status=(unconsumed|consumed-pass|consumed-fail|consumed-interrupted|execution-ineligible)$")
_STATE_KEYS = frozenset({
    "schema_version", "run_key", "binding", "canary_status", "canary_retries", "retry_reason", "canary_failure_reason",
    "canary_lease_digest",
    "canary_parsed", "canary_context_received", "runner_local_raw_trajectories_persisted",
    "provider_raw_trajectory_retention_status", "corpus_status", "batch_status", "batch_terminal",
    "batch_interruption_reason", "first_child_launch_attempted", "first_response_observed",
    "batch_lease_digest",
    "presentations_started", "presentations_completed", "aggregate_digest", "state_sha256",
})


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _require_hex40(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _HEX40.fullmatch(value):
        raise RunIndexError("invalid sealed identity")
    return value


def _require_hex64(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise RunIndexError("invalid digest")
    return value


def _require_atom(value: Any) -> str:
    if not isinstance(value, str) or not _ATOM.fullmatch(value):
        raise RunIndexError("unsafe binding value")
    return value


def _closed_mapping(value: Any, keys: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise RunIndexError("binding schema is not closed")
    return value


def normalize_binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and copy the sole binding grammar used to derive a run key.

    The intentionally narrow grammar makes raw text and private paths impossible
    to smuggle into the durable index.  All identities are commit/tree/digest
    triplets; the remaining execution dimensions are either safe atoms or
    digests.
    """
    required = set(_IDENTITY_NAMES) | {"cli", "model", "reasoning", "tools", "host", "schedule"}
    source = _closed_mapping(binding, required)
    result: dict[str, Any] = {}
    for name in _IDENTITY_NAMES:
        item = _closed_mapping(source[name], {"commit", "tree", "digest"})
        result[name] = {
            "commit": _require_hex40(item["commit"], name),
            "tree": _require_hex40(item["tree"], name),
            "digest": _require_hex64(item["digest"], name),
        }
    for name in ("cli", "model", "reasoning"):
        item = _closed_mapping(source[name], {"id", "digest"})
        result[name] = {"id": _require_atom(item["id"]), "digest": _require_hex64(item["digest"], name)}
    for name in ("tools", "host"):
        item = _closed_mapping(source[name], {"digest"})
        result[name] = {"digest": _require_hex64(item["digest"], name)}
    schedule = _closed_mapping(source["schedule"], {"seed", "digest"})
    result["schedule"] = {"seed": _require_atom(schedule["seed"]), "digest": _require_hex64(schedule["digest"], "schedule")}
    # Redundant with the closed grammar, but makes future changes reject these
    # classes before a state file is ever written.
    encoded = _canonical_json(result).decode("ascii").lower()
    if any(word in encoded for word in _FORBIDDEN):
        raise RunIndexError("sensitive durable value rejected")
    return result


def run_key(binding: Mapping[str, Any]) -> str:
    """Return the deterministic key for one exact closed execution binding."""
    return _sha256(normalize_binding(binding))


def _check_private(path: Path, *, directory: bool, mode: int) -> None:
    try:
        stat = path.lstat()
    except FileNotFoundError:
        raise RunIndexError("required custody path is missing") from None
    if path.is_symlink() or (directory != path.is_dir()):
        raise RunIndexError("unsafe custody path")
    if stat.st_uid != os.getuid() or (stat.st_mode & 0o777) != mode:
        raise RunIndexError("custody permissions are not owner-only")


def git_common_dir(root: Path | str) -> Path:
    """Resolve the canonical common Git directory without accepting a path knob."""
    source = Path(root)
    if not source.is_dir():
        raise RunIndexError("repository root is not a directory")
    try:
        completed = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "--git-common-dir"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise RunIndexError("unable to resolve git common directory") from error
    raw = completed.stdout.strip()
    if not raw or "\x00" in raw:
        raise RunIndexError("invalid git common directory")
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = source / candidate
    try:
        common = candidate.resolve(strict=True)
    except OSError as error:
        raise RunIndexError("git common directory is unavailable") from error
    if not common.is_dir():
        raise RunIndexError("git common directory is not a directory")
    return common


def git_toplevel(root: Path | str) -> Path:
    """Resolve the one canonical worktree root that owns ``EXECPLAN.md``."""
    source = Path(root)
    try:
        completed = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "--show-toplevel"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        return Path(completed.stdout.strip()).resolve(strict=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise RunIndexError("unable to resolve git worktree root") from error


def index_dir(root: Path | str) -> Path:
    """Create/return only ``<git-common-dir>/.aq-run-index-v7`` at mode 0700."""
    common = git_common_dir(root)
    target = common / INDEX_NAME
    if target.parent != common or target.name != INDEX_NAME:
        raise RunIndexError("index path escaped common directory")
    try:
        if target.exists() or target.is_symlink():
            _check_private(target, directory=True, mode=0o700)
        else:
            os.mkdir(target, 0o700)
            os.chmod(target, 0o700)
            _fsync_directory(common)
            _check_private(target, directory=True, mode=0o700)
    except FileExistsError:
        _check_private(target, directory=True, mode=0o700)
    return target


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _state_path(directory: Path, key: str) -> Path:
    if not _HEX64.fullmatch(key):
        raise RunIndexError("invalid run key")
    path = directory / (key + ".json")
    if path.parent != directory:
        raise RunIndexError("state path escaped index")
    return path


@contextmanager
def _key_lock(directory: Path, key: str) -> Iterator[None]:
    with _named_lock(directory, key, "run key"):
        yield


@contextmanager
def _corpus_lock(directory: Path, corpus_key: str) -> Iterator[None]:
    with _named_lock(directory, "corpus-" + corpus_key, "corpus"):
        yield


@contextmanager
def _named_lock(directory: Path, key: str, label: str) -> Iterator[None]:
    lock = directory / (key + ".lock")
    if lock.parent != directory:
        raise RunIndexError("lock path escaped index")
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        # A stale lock is deliberately indistinguishable from a live mutation:
        # recovery is external and no uncertain state is replayed.
        raise RunIndexError(label + " is locked or crash-ambiguous") from error
    try:
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
        yield
    finally:
        os.close(descriptor)
        try:
            lock.unlink()
            _fsync_directory(directory)
        except FileNotFoundError:
            pass


def _seal(state: dict[str, Any]) -> dict[str, Any]:
    result = dict(state)
    result.pop("state_sha256", None)
    result["state_sha256"] = _sha256(result)
    return result


def _initial_state(key: str, binding: dict[str, Any], *, canary_lease_digest: str) -> dict[str, Any]:
    return _seal({
        "schema_version": SCHEMA_VERSION, "run_key": key, "binding": binding,
        "canary_status": "started", "canary_retries": 0, "retry_reason": None, "canary_failure_reason": "none", "canary_lease_digest": canary_lease_digest,
        "canary_parsed": False, "canary_context_received": False,
        "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown",
        "corpus_status": "unconsumed", "batch_status": "not_started", "batch_terminal": "not_terminal",
        "batch_interruption_reason": "none", "first_child_launch_attempted": False, "first_response_observed": False, "batch_lease_digest": None,
        "presentations_started": 0, "presentations_completed": 0, "aggregate_digest": None,
    })


def _validate_state(value: Any, *, key: str, binding: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _STATE_KEYS:
        raise RunIndexError("state schema is not closed")
    if value.get("schema_version") != SCHEMA_VERSION or value.get("run_key") != key:
        raise RunIndexError("state identity mismatch")
    if value.get("binding") != binding:
        raise RunIndexError("state binding mismatch")
    if value.get("state_sha256") != _sha256({name: item for name, item in value.items() if name != "state_sha256"}):
        raise RunIndexError("state integrity mismatch")
    if value["canary_status"] not in {"started", "retrying", "passed", "failed"}:
        raise RunIndexError("invalid canary state")
    if not isinstance(value["canary_retries"], int) or value["canary_retries"] not in {0, 1}:
        raise RunIndexError("invalid retry count")
    if value["retry_reason"] is not None and value["retry_reason"] not in _RETRY_REASONS:
        raise RunIndexError("invalid retry reason")
    if value["canary_failure_reason"] not in {"none", *_CANARY_FAILURE_REASONS}:
        raise RunIndexError("invalid canary failure reason")
    if value["canary_lease_digest"] is not None and (not isinstance(value["canary_lease_digest"], str) or not _HEX64.fullmatch(value["canary_lease_digest"])):
        raise RunIndexError("invalid canary lease")
    if not isinstance(value["canary_parsed"], bool) or not isinstance(value["canary_context_received"], bool):
        raise RunIndexError("invalid canary evidence state")
    if value["runner_local_raw_trajectories_persisted"] is not False or value["provider_raw_trajectory_retention_status"] != "unknown":
        raise RunIndexError("invalid raw-trajectory custody state")
    if value["corpus_status"] not in {"unconsumed", "consumed_assumed"}:
        raise RunIndexError("invalid corpus status")
    if value["batch_status"] not in {"not_started", "started", "passed", "failed", "ambiguous"}:
        raise RunIndexError("invalid batch state")
    if value["batch_terminal"] not in {"not_terminal", "completed", "interrupted"}:
        raise RunIndexError("invalid batch terminal state")
    if value["batch_interruption_reason"] not in {"none", *_BATCH_INTERRUPTION_REASONS}:
        raise RunIndexError("invalid batch interruption reason")
    if value["batch_lease_digest"] is not None and (not isinstance(value["batch_lease_digest"], str) or not _HEX64.fullmatch(value["batch_lease_digest"])):
        raise RunIndexError("invalid batch lease")
    if not isinstance(value["first_child_launch_attempted"], bool) or not isinstance(value["first_response_observed"], bool):
        raise RunIndexError("invalid first-child evidence state")
    if not all(isinstance(value[name], int) and 0 <= value[name] <= 80 for name in ("presentations_started", "presentations_completed")):
        raise RunIndexError("invalid presentation counts")
    if value["presentations_completed"] > value["presentations_started"]:
        raise RunIndexError("impossible presentation counts")
    digest = value["aggregate_digest"]
    if digest is not None and (not isinstance(digest, str) or not _HEX64.fullmatch(digest)):
        raise RunIndexError("invalid aggregate digest")
    if (value["canary_retries"] == 0) != (value["retry_reason"] is None):
        raise RunIndexError("impossible retry state")
    if value["canary_status"] == "started" and value["canary_retries"] != 0:
        raise RunIndexError("impossible canary state")
    if value["canary_status"] == "retrying" and value["canary_retries"] != 1:
        raise RunIndexError("impossible canary state")
    if value["canary_status"] == "failed" and value["canary_failure_reason"] == "none":
        raise RunIndexError("impossible canary failure state")
    if value["canary_failure_reason"] == "retry_exhausted" and value["canary_retries"] != 1:
        raise RunIndexError("retry-exhausted canary lacks retry custody")
    if value["canary_status"] != "failed" and value["canary_failure_reason"] != "none":
        raise RunIndexError("impossible canary failure state")
    if (value["canary_status"] in {"started", "retrying"}) != (value["canary_lease_digest"] is not None):
        raise RunIndexError("invalid canary lease lifecycle")
    if value["canary_parsed"] != value["canary_context_received"]:
        raise RunIndexError("partial canary evidence is not durable")
    if value["canary_status"] == "passed" and not value["canary_parsed"]:
        raise RunIndexError("passed canary lacks parsed context evidence")
    if value["canary_status"] != "passed" and value["canary_parsed"]:
        raise RunIndexError("non-passed canary has invalid evidence")
    if value["batch_status"] != "not_started" and value["corpus_status"] != "consumed_assumed":
        raise RunIndexError("batch state lacks consumption custody")
    if value["batch_status"] != "not_started" and value["canary_status"] != "passed":
        raise RunIndexError("batch state lacks canary custody")
    if (value["batch_status"] == "started") != (value["batch_lease_digest"] is not None):
        raise RunIndexError("invalid batch lease lifecycle")
    if value["batch_status"] == "not_started" and (value["corpus_status"] != "unconsumed" or value["presentations_started"] != 0 or value["first_child_launch_attempted"]):
        raise RunIndexError("impossible pre-batch state")
    if value["first_response_observed"] and not value["first_child_launch_attempted"]:
        raise RunIndexError("response observed before launch")
    if value["presentations_started"] and not value["first_child_launch_attempted"]:
        raise RunIndexError("presentation started before child launch")
    if value["batch_status"] in {"passed", "failed"}:
        if digest is None or value["batch_terminal"] != "completed" or value["batch_interruption_reason"] != "none" or (value["presentations_started"], value["presentations_completed"]) != (80, 80):
            raise RunIndexError("completed batch lacks full aggregate custody")
    elif value["batch_status"] == "ambiguous":
        if digest is not None or value["batch_terminal"] != "interrupted" or value["batch_interruption_reason"] == "none":
            raise RunIndexError("ambiguous batch lacks interruption custody")
    elif digest is not None or value["batch_terminal"] != "not_terminal" or value["batch_interruption_reason"] != "none":
        raise RunIndexError("nonterminal batch has terminal evidence")
    return value


def _read_state(path: Path, *, key: str, binding: dict[str, Any]) -> dict[str, Any]:
    _check_private(path, directory=False, mode=0o600)
    try:
        with path.open("rb") as handle:
            value = json.loads(handle.read().decode("ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RunIndexError("state is corrupt or unreadable") from error
    return _validate_state(value, key=key, binding=binding)


def _read_any_state(path: Path) -> dict[str, Any]:
    """Validate a sibling before it can influence corpus no-replay custody."""
    _check_private(path, directory=False, mode=0o600)
    try:
        with path.open("rb") as handle:
            value = json.loads(handle.read().decode("ascii"))
        if not isinstance(value, dict):
            raise RunIndexError("state is corrupt or unreadable")
        binding = normalize_binding(value.get("binding"))
        key = _sha256(binding)
    except (OSError, TypeError, UnicodeDecodeError, json.JSONDecodeError, RunIndexError) as error:
        raise RunIndexError("sibling state is corrupt or unreadable") from error
    return _validate_state(value, key=key, binding=binding)


def _corpus_identity(binding: Mapping[str, Any]) -> str:
    return binding["corpus"]["commit"]


def _assert_corpus_unconsumed(directory: Path, binding: dict[str, Any]) -> None:
    """Scan all durable state: one corrupt sibling is an index-wide hard stop."""
    wanted = binding["corpus"]
    for _path, sibling in _all_states(directory):
        sibling_corpus = sibling["binding"]["corpus"]
        if sibling_corpus["commit"] == wanted["commit"]:
            if sibling_corpus != wanted:
                raise RunIndexError("same corpus commit has inconsistent tree or digest")
            if sibling["corpus_status"] == "consumed_assumed":
                raise RunIndexError("corpus is already consumed or crash-ambiguous")


def _all_states(directory: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Return every validated state; no corrupt sibling is ignorable custody."""
    return [(path, _read_any_state(path)) for path in directory.glob("*.json")]


def _write_state(directory: Path, path: Path, state: dict[str, Any]) -> None:
    sealed = _seal(state)
    data = _canonical_json(sealed)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".aq7-", suffix=".tmp", dir=directory)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        _fsync_directory(directory)
        _check_private(path, directory=False, mode=0o600)
    finally:
        if descriptor != -1:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _canonical_execplan(toplevel: Path) -> bytes:
    """Return live bytes only when the tracked canonical plan equals clean HEAD."""
    plan = toplevel / "EXECPLAN.md"
    try:
        if plan.is_symlink() or not plan.is_file():
            raise RunIndexError("canonical execplan is unsafe")
        live = plan.read_bytes()
        # The worktree and index must independently match HEAD.  Checking only
        # live bytes would accept an MM split where a staged authority differs.
        for command in (
            ["git", "-C", str(toplevel), "diff", "--quiet", "--no-ext-diff", "--", "EXECPLAN.md"],
            ["git", "-C", str(toplevel), "diff", "--cached", "--quiet", "--no-ext-diff", "HEAD", "--", "EXECPLAN.md"],
        ):
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        committed = subprocess.run(
            ["git", "-C", str(toplevel), "show", "HEAD:EXECPLAN.md"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise RunIndexError("canonical clean HEAD execplan unavailable") from error
    if live != committed:
        raise RunIndexError("canonical execplan is not clean HEAD")
    return live


def _authority_lines(toplevel: Path, corpus_commit: str) -> list[str]:
    _require_hex40(corpus_commit, "corpus")
    try:
        lines = _canonical_execplan(toplevel).decode("utf-8").splitlines()
    except (UnicodeDecodeError, RunIndexError) as error:
        raise RunIndexError("active execplan unavailable") from error
    matches: list[str] = []
    for line in lines:
        if line.startswith("AQ7-RUN-AUTHORITY"):
            parsed = _AUTHORITY.fullmatch(line)
            if parsed is None:
                raise RunIndexError("malformed AQ7 authority line")
            if parsed.group(1) == corpus_commit:
                matches.append(line)
    return matches


def _require_marker(marker: str, *, corpus_commit: str, statuses: set[str]) -> None:
    if not isinstance(marker, str) or "\n" in marker or "\r" in marker:
        raise RunIndexError("invalid authority marker")
    parsed = _AUTHORITY.fullmatch(marker)
    if parsed is None or parsed.group(1) != corpus_commit or parsed.group(2) not in statuses:
        raise RunIndexError("authority marker has wrong corpus or status")


def _require_active_execplan_authority(toplevel: Path, *, marker: str, corpus_commit: str, phase: str) -> None:
    """Require one exact full-line unconsumed authority marker before a launch."""
    if phase not in {"canary", "batch"}:
        raise RunIndexError("invalid authority phase")
    _require_marker(marker, corpus_commit=corpus_commit, statuses={"unconsumed"})
    lines = _authority_lines(toplevel, corpus_commit)
    if lines != [marker]:
        raise RunIndexError("active authority marker is absent, duplicated, or superseded")


def _require_cleanup_authority(toplevel: Path, *, durable_marker: str, corpus_commit: str) -> str:
    """Require a sole exact durable authority line for the bound corpus."""
    durable_statuses = {"consumed-pass", "consumed-fail", "consumed-interrupted", "execution-ineligible"}
    _require_marker(durable_marker, corpus_commit=corpus_commit, statuses=durable_statuses)
    lines = _authority_lines(toplevel, corpus_commit)
    if lines != [durable_marker]:
        raise RunIndexError("durable cleanup marker is absent, duplicated, or superseded")
    return _AUTHORITY.fullmatch(durable_marker).group(2)  # type: ignore[union-attr]


class AQ7RunIndex:
    """State-machine facade with process-local mutation capabilities.

    Capabilities prevent an independently restarted evaluator process from
    resuming an uncertain phase.  They are accidental-bypass controls, not a
    hostile same-process security boundary.
    """

    def __init__(self, root: Path | str):
        self.toplevel = git_toplevel(root)
        self.directory = index_dir(self.toplevel)
        self._owner_pid = os.getpid()
        self._canary_capabilities: dict[str, bytes] = {}
        self._batch_capabilities: dict[str, bytes] = {}

    def _identity(self, binding: Mapping[str, Any]) -> tuple[str, dict[str, Any], Path]:
        normalized = normalize_binding(binding)
        key = _sha256(normalized)
        return key, normalized, _state_path(self.directory, key)

    def state(self, binding: Mapping[str, Any]) -> dict[str, Any]:
        key, normalized, path = self._identity(binding)
        return _read_state(path, key=key, binding=normalized)

    @staticmethod
    def _lease_digest(capability: object) -> str:
        if not isinstance(capability, bytes) or len(capability) != 32:
            raise RunIndexError("invalid mutation capability")
        return hashlib.sha256(capability).hexdigest()

    def _require_owner(self) -> None:
        if os.getpid() != self._owner_pid:
            raise RunIndexError("mutation capability belongs to a different process")

    def _require_canary_capability(self, key: str, canary_cap: object, state: Mapping[str, Any]) -> None:
        self._require_owner()
        if self._canary_capabilities.get(key) != canary_cap or state["canary_lease_digest"] != self._lease_digest(canary_cap):
            raise RunIndexError("canary mutation capability is absent or from another process")

    def _require_batch_capability(self, key: str, batch_cap: object, state: Mapping[str, Any]) -> None:
        self._require_owner()
        if self._batch_capabilities.get(key) != batch_cap or state["batch_lease_digest"] != self._lease_digest(batch_cap):
            raise RunIndexError("batch mutation capability is absent or from another process")

    def begin_canary(self, binding: Mapping[str, Any], *, unconsumed_marker: str) -> bytes:
        self._require_owner()
        key, normalized, path = self._identity(binding)
        capability = secrets.token_bytes(32)
        with _corpus_lock(self.directory, _corpus_identity(normalized)):
            with _key_lock(self.directory, key):
                _require_active_execplan_authority(self.toplevel, marker=unconsumed_marker, corpus_commit=normalized["corpus"]["commit"], phase="canary")
                _assert_corpus_unconsumed(self.directory, normalized)
                if path.exists() or path.is_symlink():
                    # Read it first: corruption and replay are both hard stops.
                    _read_state(path, key=key, binding=normalized)
                    raise RunIndexError("canary already started; no second canary")
                _write_state(self.directory, path, _initial_state(key, normalized, canary_lease_digest=self._lease_digest(capability)))
        self._canary_capabilities[key] = capability
        return capability

    def retry_canary(self, binding: Mapping[str, Any], *, unconsumed_marker: str, canary_cap: bytes, reason: str) -> None:
        key, normalized, path = self._identity(binding)
        if reason not in _RETRY_REASONS:
            raise RunIndexError("retry reason is not precompletion infrastructure")
        with _key_lock(self.directory, key):
            state = _read_state(path, key=key, binding=normalized)
            self._require_canary_capability(key, canary_cap, state)
            _require_active_execplan_authority(self.toplevel, marker=unconsumed_marker, corpus_commit=normalized["corpus"]["commit"], phase="canary")
            if state["canary_status"] not in {"started", "retrying"} or state["canary_retries"] != 0:
                raise RunIndexError("canary retry is exhausted or no longer eligible")
            state["canary_status"] = "retrying"
            state["canary_retries"] = 1
            state["retry_reason"] = reason
            _write_state(self.directory, path, state)

    def complete_canary(self, binding: Mapping[str, Any], *, unconsumed_marker: str, canary_cap: bytes) -> None:
        key, normalized, path = self._identity(binding)
        with _key_lock(self.directory, key):
            state = _read_state(path, key=key, binding=normalized)
            self._require_canary_capability(key, canary_cap, state)
            _require_active_execplan_authority(self.toplevel, marker=unconsumed_marker, corpus_commit=normalized["corpus"]["commit"], phase="canary")
            if state["canary_status"] not in {"started", "retrying"} or state["batch_status"] != "not_started":
                raise RunIndexError("canary completion is not eligible")
            state["canary_status"] = "passed"
            state["canary_parsed"] = True
            state["canary_context_received"] = True
            state["canary_lease_digest"] = None
            _write_state(self.directory, path, state)
        del self._canary_capabilities[key]

    def fail_canary(self, binding: Mapping[str, Any], *, unconsumed_marker: str, canary_cap: bytes, reason: str = "malformed_or_content_failure") -> None:
        """Close a completed/malformed canary; only precompletion failures retry."""
        key, normalized, path = self._identity(binding)
        if reason not in _CANARY_FAILURE_REASONS:
            raise RunIndexError("canary failure reason is not allowed")
        with _key_lock(self.directory, key):
            state = _read_state(path, key=key, binding=normalized)
            self._require_canary_capability(key, canary_cap, state)
            _require_active_execplan_authority(self.toplevel, marker=unconsumed_marker, corpus_commit=normalized["corpus"]["commit"], phase="canary")
            if state["canary_status"] not in {"started", "retrying"}:
                raise RunIndexError("canary failure is not eligible")
            if reason == "retry_exhausted" and state["canary_retries"] != 1:
                raise RunIndexError("retry-exhausted canary lacks retry custody")
            state["canary_status"] = "failed"
            state["canary_failure_reason"] = reason
            state["canary_lease_digest"] = None
            _write_state(self.directory, path, state)
        del self._canary_capabilities[key]

    def begin_batch(self, binding: Mapping[str, Any], *, unconsumed_marker: str) -> bytes:
        """Atomically consume custody immediately before the first corpus child."""
        self._require_owner()
        key, normalized, path = self._identity(binding)
        capability = secrets.token_bytes(32)
        with _corpus_lock(self.directory, _corpus_identity(normalized)):
            with _key_lock(self.directory, key):
                _require_active_execplan_authority(self.toplevel, marker=unconsumed_marker, corpus_commit=normalized["corpus"]["commit"], phase="batch")
                _assert_corpus_unconsumed(self.directory, normalized)
                state = _read_state(path, key=key, binding=normalized)
                if state["canary_status"] != "passed" or state["batch_status"] != "not_started" or state["corpus_status"] != "unconsumed":
                    raise RunIndexError("batch requires exactly one passed canary and unconsumed corpus")
                state["corpus_status"] = "consumed_assumed"
                state["batch_status"] = "started"
                state["batch_lease_digest"] = self._lease_digest(capability)
                _write_state(self.directory, path, state)
        self._batch_capabilities[key] = capability
        return capability

    def presentation_started(self, binding: Mapping[str, Any], *, batch_cap: bytes) -> None:
        key, normalized, path = self._identity(binding)
        with _key_lock(self.directory, key):
            state = _read_state(path, key=key, binding=normalized)
            self._require_batch_capability(key, batch_cap, state)
            if state["batch_status"] != "started" or state["presentations_started"] >= 80:
                raise RunIndexError("presentation start is not eligible")
            # This durable bit is written before the runner may launch its first
            # corpus child; a crash after it is therefore permanently consumed.
            state["first_child_launch_attempted"] = True
            state["presentations_started"] += 1
            _write_state(self.directory, path, state)

    def presentation_completed(self, binding: Mapping[str, Any], *, batch_cap: bytes) -> None:
        key, normalized, path = self._identity(binding)
        with _key_lock(self.directory, key):
            state = _read_state(path, key=key, binding=normalized)
            self._require_batch_capability(key, batch_cap, state)
            if state["batch_status"] != "started" or state["presentations_completed"] >= state["presentations_started"]:
                raise RunIndexError("presentation completion lacks a recorded start")
            state["presentations_completed"] += 1
            if state["presentations_completed"] == 1:
                state["first_response_observed"] = True
            _write_state(self.directory, path, state)

    def response_observed(self, binding: Mapping[str, Any], *, batch_cap: bytes) -> None:
        """Record only that the first corpus response was observed, never it."""
        key, normalized, path = self._identity(binding)
        with _key_lock(self.directory, key):
            state = _read_state(path, key=key, binding=normalized)
            self._require_batch_capability(key, batch_cap, state)
            if state["batch_status"] != "started" or not state["first_child_launch_attempted"] or state["first_response_observed"]:
                raise RunIndexError("first response observation is not eligible")
            state["first_response_observed"] = True
            _write_state(self.directory, path, state)

    def complete_batch(self, binding: Mapping[str, Any], *, batch_cap: bytes, status: str, aggregate_digest: str) -> None:
        if status not in {"passed", "failed"}:
            raise RunIndexError("batch terminal status is not allowed")
        _require_hex64(aggregate_digest, "aggregate")
        key, normalized, path = self._identity(binding)
        with _key_lock(self.directory, key):
            state = _read_state(path, key=key, binding=normalized)
            self._require_batch_capability(key, batch_cap, state)
            if state["batch_status"] != "started" or (state["presentations_started"], state["presentations_completed"]) != (80, 80):
                raise RunIndexError("batch completion is not eligible")
            state["batch_status"] = status
            state["batch_terminal"] = "completed"
            state["aggregate_digest"] = aggregate_digest
            state["batch_lease_digest"] = None
            _write_state(self.directory, path, state)
        del self._batch_capabilities[key]

    def mark_batch_ambiguous(self, binding: Mapping[str, Any], *, batch_cap: bytes, reason: str = "crash_ambiguous") -> None:
        """Permanently close an interrupted batch without attempting recovery."""
        if reason not in _BATCH_INTERRUPTION_REASONS:
            raise RunIndexError("batch interruption reason is not allowed")
        key, normalized, path = self._identity(binding)
        with _key_lock(self.directory, key):
            state = _read_state(path, key=key, binding=normalized)
            self._require_batch_capability(key, batch_cap, state)
            if state["batch_status"] != "started":
                raise RunIndexError("batch ambiguity is not eligible")
            state["batch_status"] = "ambiguous"
            state["batch_terminal"] = "interrupted"
            state["batch_interruption_reason"] = reason
            state["batch_lease_digest"] = None
            _write_state(self.directory, path, state)
        del self._batch_capabilities[key]

    def cleanup(self, binding: Mapping[str, Any], *, durable_marker: str) -> None:
        self._require_owner()
        _key, normalized, _path = self._identity(binding)
        durable_status = _require_cleanup_authority(self.toplevel, durable_marker=durable_marker, corpus_commit=normalized["corpus"]["commit"])
        with _corpus_lock(self.directory, _corpus_identity(normalized)):
            initial = [(path, state) for path, state in _all_states(self.directory) if state["binding"]["corpus"]["commit"] == normalized["corpus"]["commit"]]
            if not initial:
                raise RunIndexError("no same-corpus state is available for cleanup")
            if any(state["binding"]["corpus"] != normalized["corpus"] for _path, state in initial):
                raise RunIndexError("same corpus commit has inconsistent tree or digest")
            with ExitStack() as locks:
                for _path, state in sorted(initial, key=lambda item: item[1]["run_key"]):
                    locks.enter_context(_key_lock(self.directory, state["run_key"]))
                # Re-read under every sibling lock: cleanup never races a state
                # transition or deletes only a subset of a corpus disposition.
                siblings = [(path, state) for path, state in _all_states(self.directory) if state["binding"]["corpus"]["commit"] == normalized["corpus"]["commit"]]
                if {state["run_key"] for _path, state in siblings} != {state["run_key"] for _path, state in initial}:
                    raise RunIndexError("same-corpus state changed during cleanup")
                self._validate_cleanup_disposition(siblings, durable_status)
                for path, _state in siblings:
                    path.unlink()
                _fsync_directory(self.directory)

    @staticmethod
    def _validate_cleanup_disposition(siblings: list[tuple[Path, dict[str, Any]]], durable_status: str) -> None:
        """Match the durable active-plan disposition to every removable state."""
        states = [state for _path, state in siblings]
        consumed_statuses = {"consumed-pass", "consumed-fail", "consumed-interrupted"}
        if durable_status in consumed_statuses:
            expected = {"consumed-pass": "passed", "consumed-fail": "failed", "consumed-interrupted": "ambiguous"}[durable_status]
            consumed = [state for state in states if state["corpus_status"] == "consumed_assumed"]
            if len(consumed) != 1:
                raise RunIndexError("durable consumed marker mismatches same-corpus state")
            if consumed[0]["batch_status"] == "started":
                if durable_status != "consumed-interrupted":
                    raise RunIndexError("crash-stuck batch requires consumed-interrupted authority")
            elif consumed[0]["batch_status"] != expected:
                raise RunIndexError("durable consumed marker mismatches same-corpus state")
            if any(state["corpus_status"] != "unconsumed" for state in states if state["run_key"] != consumed[0]["run_key"]):
                raise RunIndexError("multiple consumed same-corpus states are unsafe")
        elif durable_status == "execution-ineligible":
            if any(state["corpus_status"] != "unconsumed" or state["batch_status"] != "not_started" for state in states):
                raise RunIndexError("execution-ineligible marker cannot erase consumed state")
        else:  # Defensive closure if the authority grammar changes.
            raise RunIndexError("unknown durable authority status")
