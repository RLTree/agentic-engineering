#!/usr/bin/env python3
"""Durable, content-free custody index for the AE-SQ1 AQ run.

The index is deliberately ignorant of corpus text and model output.  It stores
only exact byte identities, aggregate call/token counters, terminal status, and
a sealed no-replay marker below the repository's Git common directory.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping


class RunIndexError(RuntimeError):
    """A custody or state-machine invariant failed (always fail closed)."""


INDEX_NAME = ".ae-sq1-run-index"
SCHEMA_VERSION = "ae-sq1-run-index-v1"
PROGRAM_ID = "AE-SQ1"
CANARY_CALLS = 4
BATCH_PRESENTATIONS = 80
CALLS_PER_PRESENTATION = 4
BATCH_CALLS = BATCH_PRESENTATIONS * CALLS_PER_PRESENTATION
USAGE_KEYS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "total_tokens",
)

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ATOM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+-]{0,127}$")
_PATH_ROLES = (
    "candidate_manifest",
    "candidate_freeze",
    "run_manifest",
    "runner",
)
_CORPUS_KEYS = frozenset({"content_sha256", "split_a", "split_b"})
_BINDING_KEYS = frozenset(
    {
        "program_id",
        *_PATH_ROLES,
        "corpus",
        "cli",
        "model",
        "schedule",
        "host",
    }
)
_STATE_KEYS = frozenset(
    {
        "schema_version",
        "run_key",
        "binding",
        "owner_pid",
        "canary_status",
        "canary_attempt",
        "canary_calls_started",
        "canary_calls_completed",
        "canary_observation_seen",
        "canary_usage",
        "canary_lease_digest",
        "corpus_status",
        "batch_status",
        "batch_presentations_started",
        "batch_presentations_completed",
        "batch_calls_started",
        "batch_calls_completed",
        "batch_observation_seen",
        "batch_usage",
        "batch_lease_digest",
        "aggregate_digest",
        "terminal_marker",
        "state_sha256",
    }
)
_TERMINAL = frozenset({"consumed-pass", "consumed-fail", "consumed-invalid"})


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as error:
        raise RunIndexError("value is not canonical closed JSON") from error


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _closed(
    value: Any, keys: set[str] | frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(keys):
        raise RunIndexError(f"{label} is not closed")
    return value


def _hex(value: Any, length: int, label: str) -> str:
    pattern = _HEX40 if length == 40 else _HEX64
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise RunIndexError(f"{label} is not an exact lowercase digest")
    return value


def _safe_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise RunIndexError(f"{label} path is unavailable")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or "\x00" in value:
        raise RunIndexError(f"{label} path escaped repository")
    return value


def _sealed_path(value: Any, label: str) -> dict[str, str]:
    item = _closed(value, {"commit", "tree", "path", "blob", "sha256"}, label)
    return {
        "commit": _hex(item["commit"], 40, label),
        "tree": _hex(item["tree"], 40, label),
        "path": _safe_path(item["path"], label),
        "blob": _hex(item["blob"], 40, label),
        "sha256": _hex(item["sha256"], 64, label),
    }


def normalize_usage(value: Any) -> dict[str, int]:
    """Return exact closed usage; bools and inconsistent totals are rejected."""
    usage = _closed(value, set(USAGE_KEYS), "usage")
    result: dict[str, int] = {}
    for key in USAGE_KEYS:
        token_count = usage[key]
        if type(token_count) is not int or token_count < 0:
            raise RunIndexError("usage contains a non-exact token count")
        result[key] = token_count
    if result["cached_input_tokens"] > result["input_tokens"]:
        raise RunIndexError("cached input exceeds input usage")
    if result["total_tokens"] != result["input_tokens"] + result["output_tokens"]:
        raise RunIndexError("usage total is inconsistent")
    return result


def zero_usage() -> dict[str, int]:
    return {key: 0 for key in USAGE_KEYS}


def _add_usage(left: Mapping[str, int], right: Mapping[str, int]) -> dict[str, int]:
    one = normalize_usage(left)
    two = normalize_usage(right)
    return {key: one[key] + two[key] for key in USAGE_KEYS}


def normalize_binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    source = _closed(binding, _BINDING_KEYS, "run binding")
    if source["program_id"] != PROGRAM_ID:
        raise RunIndexError("cross-program binding rejected")
    result: dict[str, Any] = {"program_id": PROGRAM_ID}
    for role in _PATH_ROLES:
        result[role] = _sealed_path(source[role], role)

    corpus = _closed(source["corpus"], _CORPUS_KEYS, "corpus binding")
    content_sha256 = _hex(corpus["content_sha256"], 64, "corpus content")
    split_a = _sealed_path(corpus["split_a"], "corpus split A")
    split_b = _sealed_path(corpus["split_b"], "corpus split B")
    if split_a["path"] == split_b["path"]:
        raise RunIndexError("corpus split paths must be distinct")
    result["corpus"] = {
        "content_sha256": content_sha256,
        "split_a": split_a,
        "split_b": split_b,
    }

    cli = _closed(source["cli"], {"id", "version", "sha256"}, "CLI binding")
    if cli["id"] != "codex-cli" or not isinstance(cli["version"], str):
        raise RunIndexError("CLI identity is unavailable")
    if re.fullmatch(r"codex-cli 0\.147\.\d+", cli["version"]) is None:
        raise RunIndexError("Codex CLI is not in the frozen 0.147 lifecycle")
    result["cli"] = {
        "id": "codex-cli",
        "version": cli["version"],
        "sha256": _hex(cli["sha256"], 64, "CLI"),
    }

    model = _closed(source["model"], {"id", "reasoning", "fallback"}, "model binding")
    if model != {"id": "gpt-5.5", "reasoning": "medium", "fallback": False}:
        raise RunIndexError("model binding drift")
    result["model"] = dict(model)

    schedule = _closed(
        source["schedule"],
        {"seed", "sha256", "presentations", "calls_per_presentation"},
        "schedule binding",
    )
    if (
        not isinstance(schedule["seed"], str)
        or _SAFE_ATOM.fullmatch(schedule["seed"]) is None
        or schedule["presentations"] != BATCH_PRESENTATIONS
        or type(schedule["presentations"]) is not int
        or schedule["calls_per_presentation"] != CALLS_PER_PRESENTATION
        or type(schedule["calls_per_presentation"]) is not int
    ):
        raise RunIndexError("schedule binding drift")
    result["schedule"] = {
        "seed": schedule["seed"],
        "sha256": _hex(schedule["sha256"], 64, "schedule"),
        "presentations": BATCH_PRESENTATIONS,
        "calls_per_presentation": CALLS_PER_PRESENTATION,
    }

    host = _closed(source["host"], {"sha256"}, "host binding")
    result["host"] = {"sha256": _hex(host["sha256"], 64, "host")}
    return result


def run_key(binding: Mapping[str, Any]) -> str:
    return _sha256(normalize_binding(binding))


def _private(path: Path, *, directory: bool, mode: int) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise RunIndexError("custody path is unavailable") from error
    if directory:
        expected_type = stat.S_ISDIR(metadata.st_mode)
    else:
        expected_type = stat.S_ISREG(metadata.st_mode)
    if not expected_type or (not directory and metadata.st_nlink != 1):
        raise RunIndexError("custody path has an unsafe type")
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != mode:
        raise RunIndexError("custody path is not owner-only")


def git_common_dir(root: Path | str) -> Path:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--git-common-dir"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        raw = completed.stdout.strip()
        source = Path(root).resolve(strict=True)
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = source / candidate
        common = candidate.resolve(strict=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise RunIndexError("Git common directory is unavailable") from error
    if not common.is_dir():
        raise RunIndexError("Git common directory is unsafe")
    return common


def index_dir(root: Path | str) -> Path:
    common = git_common_dir(root)
    target = common / INDEX_NAME
    if target.parent != common or target.name != INDEX_NAME:
        raise RunIndexError("run index escaped Git common directory")
    try:
        os.mkdir(target, 0o700)
        os.chmod(target, 0o700)
        _fsync_dir(common)
    except FileExistsError:
        pass
    _private(target, directory=True, mode=0o700)
    return target


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _state_path(directory: Path, key: str) -> Path:
    _hex(key, 64, "run key")
    path = directory / f"{key}.json"
    if path.parent != directory:
        raise RunIndexError("state path escaped index")
    return path


@contextmanager
def _lock(directory: Path, name: str) -> Iterator[None]:
    if _SAFE_ATOM.fullmatch(name) is None:
        raise RunIndexError("lock identity is unsafe")
    path = directory / f"{name}.lock"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise RunIndexError("run index is locked or crash-ambiguous") from error
    try:
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.getuid()
            or opened.st_nlink != 1
            or stat.S_IMODE(opened.st_mode) != 0o600
        ):
            raise RunIndexError("lock file has an unsafe identity")
        yield
    finally:
        try:
            current = os.fstat(descriptor)
            path_metadata = path.lstat()
            if _file_identity(current) == _file_identity(path_metadata):
                path.unlink()
                _fsync_dir(directory)
        except (FileNotFoundError, OSError):
            pass
        finally:
            os.close(descriptor)


def _seal(state: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(state)
    result.pop("state_sha256", None)
    result["state_sha256"] = _sha256(result)
    return result


def _write(directory: Path, path: Path, state: Mapping[str, Any]) -> None:
    raw = _canonical_json(_seal(state))
    descriptor, name = tempfile.mkstemp(prefix=".ae-sq1-", suffix=".tmp", dir=directory)
    temporary = Path(name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        _fsync_dir(directory)
        _private(path, directory=False, mode=0o600)
    finally:
        if descriptor != -1:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _file_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _read_private_bytes(path: Path) -> bytes:
    """Read one owner-only state file without following replacement races."""
    _private(path, directory=False, mode=0o600)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise RunIndexError("run state is unavailable or replaced") from error
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.getuid()
            or opened.st_nlink != 1
            or stat.S_IMODE(opened.st_mode) != 0o600
        ):
            raise RunIndexError("run state has an unsafe file identity")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > 1 << 20:
                raise RunIndexError("run state is unreasonably large")
        closed = os.fstat(descriptor)
        if _file_identity(opened) != _file_identity(closed):
            raise RunIndexError("run state changed during read")
        return b"".join(chunks)
    except OSError as error:
        raise RunIndexError("run state read failed") from error
    finally:
        os.close(descriptor)


def _initial_state(key: str, binding: dict[str, Any], lease: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_key": key,
        "binding": binding,
        "owner_pid": os.getpid(),
        "canary_status": "started",
        "canary_attempt": 1,
        "canary_calls_started": 0,
        "canary_calls_completed": 0,
        "canary_observation_seen": False,
        "canary_usage": zero_usage(),
        "canary_lease_digest": lease,
        "corpus_status": "unconsumed",
        "batch_status": "not-started",
        "batch_presentations_started": 0,
        "batch_presentations_completed": 0,
        "batch_calls_started": 0,
        "batch_calls_completed": 0,
        "batch_observation_seen": False,
        "batch_usage": zero_usage(),
        "batch_lease_digest": None,
        "aggregate_digest": None,
        "terminal_marker": None,
    }


def _validate_state(value: Any, key: str, binding: dict[str, Any]) -> dict[str, Any]:
    state = _closed(value, _STATE_KEYS, "run state")
    if (
        state["schema_version"] != SCHEMA_VERSION
        or state["run_key"] != key
        or state["binding"] != binding
        or state["state_sha256"]
        != _sha256(
            {name: item for name, item in state.items() if name != "state_sha256"}
        )
    ):
        raise RunIndexError("run state integrity mismatch")
    if type(state["owner_pid"]) is not int or state["owner_pid"] <= 0:
        raise RunIndexError("run owner PID is invalid")
    if state["canary_status"] not in {
        "started",
        "retrying",
        "passed",
        "failed",
        "invalid",
    }:
        raise RunIndexError("canary status is invalid")
    if type(state["canary_attempt"]) is not int or state["canary_attempt"] not in {
        1,
        2,
    }:
        raise RunIndexError("canary attempt is invalid")
    canary_limit = CANARY_CALLS * state["canary_attempt"]
    for field in ("canary_calls_started", "canary_calls_completed"):
        if type(state[field]) is not int or not 0 <= state[field] <= canary_limit:
            raise RunIndexError("canary call count is invalid")
    if state["canary_calls_completed"] > state["canary_calls_started"]:
        raise RunIndexError("canary completion count is impossible")
    if type(state["canary_observation_seen"]) is not bool:
        raise RunIndexError("canary observation marker is invalid")
    normalize_usage(state["canary_usage"])
    if state["corpus_status"] not in {"unconsumed", "consumed"}:
        raise RunIndexError("corpus status is invalid")
    if state["batch_status"] not in {
        "not-started",
        "started",
        "passed",
        "failed",
        "invalid",
    }:
        raise RunIndexError("batch status is invalid")
    for field, limit in (
        ("batch_presentations_started", BATCH_PRESENTATIONS),
        ("batch_presentations_completed", BATCH_PRESENTATIONS),
        ("batch_calls_started", BATCH_CALLS),
        ("batch_calls_completed", BATCH_CALLS),
    ):
        if type(state[field]) is not int or not 0 <= state[field] <= limit:
            raise RunIndexError("batch count is invalid")
    if (
        state["batch_presentations_completed"] > state["batch_presentations_started"]
        or state["batch_calls_completed"] > state["batch_calls_started"]
        or state["batch_calls_started"]
        > state["batch_presentations_started"] * CALLS_PER_PRESENTATION
        or state["batch_presentations_completed"] * CALLS_PER_PRESENTATION
        > state["batch_calls_completed"]
    ):
        raise RunIndexError("batch counters are inconsistent")
    if type(state["batch_observation_seen"]) is not bool:
        raise RunIndexError("batch observation marker is invalid")
    normalize_usage(state["batch_usage"])
    for lease_name in ("canary_lease_digest", "batch_lease_digest"):
        lease = state[lease_name]
        if lease is not None:
            _hex(lease, 64, lease_name)
    digest = state["aggregate_digest"]
    if digest is not None:
        _hex(digest, 64, "aggregate")
    marker = state["terminal_marker"]
    if marker is not None and marker not in _TERMINAL:
        raise RunIndexError("terminal marker is invalid")
    if (state["canary_status"] in {"started", "retrying"}) != (
        state["canary_lease_digest"] is not None
    ):
        raise RunIndexError("canary lease lifecycle is invalid")
    if (state["batch_status"] == "started") != (
        state["batch_lease_digest"] is not None
    ):
        raise RunIndexError("batch lease lifecycle is invalid")
    if state["batch_status"] != "not-started" and (
        state["canary_status"] != "passed" or state["corpus_status"] != "consumed"
    ):
        raise RunIndexError("batch lacks canary or consumption custody")
    if state["batch_status"] in {"passed", "failed"} and (
        state["batch_presentations_completed"] != BATCH_PRESENTATIONS
        or state["batch_calls_completed"] != BATCH_CALLS
        or state["aggregate_digest"] is None
    ):
        raise RunIndexError("terminal completed batch lacks exact counts")
    expected_marker = {
        "passed": "consumed-pass",
        "failed": "consumed-fail",
        "invalid": "consumed-invalid",
    }.get(state["batch_status"])
    if expected_marker is not None and marker != expected_marker:
        raise RunIndexError("durable terminal marker is missing")
    if state["batch_status"] in {"not-started", "started"} and marker is not None:
        raise RunIndexError("nonterminal batch has a terminal marker")
    return dict(state)


def _strict_state(raw: bytes) -> dict[str, Any]:
    def closed_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for name, item in pairs:
            if name in value:
                raise ValueError("duplicate state key")
            value[name] = item
        return value

    value = json.loads(
        raw.decode("ascii", "strict"),
        object_pairs_hook=closed_pairs,
        parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
    )
    if not isinstance(value, dict) or raw != _canonical_json(value):
        raise ValueError("state bytes are not canonical")
    return value


def _read(path: Path, key: str, binding: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = _read_private_bytes(path)
        value = _strict_state(raw)
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        RunIndexError,
    ) as error:
        raise RunIndexError("run state is corrupt or unreadable") from error
    return _validate_state(value, key, binding)


class AESQ1RunIndex:
    """Single-process mutation capabilities around one durable no-replay state."""

    def __init__(self, root: Path | str):
        self.directory = index_dir(root)
        self._owner_pid = os.getpid()
        self._process_mac_key = secrets.token_bytes(32)
        self._canary_caps: dict[str, tuple[bytes, bytes]] = {}
        self._batch_caps: dict[str, tuple[bytes, bytes]] = {}
        self._completed_canaries: set[str] = set()

    def _identity(self, binding: Mapping[str, Any]) -> tuple[str, dict[str, Any], Path]:
        normalized = normalize_binding(binding)
        key = _sha256(normalized)
        return key, normalized, _state_path(self.directory, key)

    @staticmethod
    def _lease(capability: object) -> str:
        if not isinstance(capability, bytes) or len(capability) != 32:
            raise RunIndexError("mutation capability is invalid")
        return hashlib.sha256(capability).hexdigest()

    def _process_mac(self, capability: bytes) -> bytes:
        return hmac.new(self._process_mac_key, capability, hashlib.sha256).digest()

    def _remember_capability(
        self, table: dict[str, tuple[bytes, bytes]], key: str, capability: bytes
    ) -> None:
        table[key] = (capability, self._process_mac(capability))

    def _owner(self) -> None:
        if os.getpid() != self._owner_pid:
            raise RunIndexError("mutation capability cannot cross PID/fork/restart")

    def _state(
        self, binding: Mapping[str, Any]
    ) -> tuple[str, dict[str, Any], Path, dict[str, Any]]:
        key, normalized, path = self._identity(binding)
        return key, normalized, path, _read(path, key, normalized)

    def state(self, binding: Mapping[str, Any]) -> dict[str, Any]:
        return self._state(binding)[3]

    def _require_cap(
        self,
        key: str,
        state: Mapping[str, Any],
        capability: object,
        *,
        phase: str,
    ) -> None:
        self._owner()
        table = self._canary_caps if phase == "canary" else self._batch_caps
        lease = state[f"{phase}_lease_digest"]
        entry = table.get(key)
        if (
            not isinstance(entry, tuple)
            or len(entry) != 2
            or type(capability) is not bytes
            or len(capability) != 32
            or type(entry[0]) is not bytes
            or type(entry[1]) is not bytes
            or not hmac.compare_digest(entry[0], capability)
            or not hmac.compare_digest(entry[1], self._process_mac(capability))
            or lease != self._lease(capability)
        ):
            raise RunIndexError("mutation capability is absent or from another process")

    def _corpus_consumed(
        self,
        wanted_binding: Mapping[str, Any],
        *,
        for_canary: bool = False,
        current_key: str | None = None,
    ) -> None:
        wanted = wanted_binding["corpus"]
        for path in self.directory.glob("*.json"):
            try:
                raw = _strict_state(_read_private_bytes(path))
                sibling_binding = normalize_binding(raw.get("binding"))
                sibling_key = _sha256(sibling_binding)
                sibling = _validate_state(raw, sibling_key, sibling_binding)
            except (
                OSError,
                UnicodeDecodeError,
                json.JSONDecodeError,
                ValueError,
                RunIndexError,
            ) as error:
                raise RunIndexError("sibling run state is corrupt") from error
            other = sibling_binding["corpus"]
            if other["content_sha256"] == wanted["content_sha256"]:
                if other != wanted:
                    raise RunIndexError("same corpus content has inconsistent custody")
                if sibling["corpus_status"] == "consumed":
                    raise RunIndexError("corpus is already consumed or crash-ambiguous")
                if not for_canary or sibling_key == current_key:
                    continue
                started = sibling["canary_calls_started"] > 0
                observed = sibling["canary_observation_seen"]
                completed = sibling["canary_calls_completed"] > 0
                candidate_changed = (
                    sibling_binding["candidate_freeze"]
                    != wanted_binding["candidate_freeze"]
                )
                if started or observed or completed or not candidate_changed:
                    raise RunIndexError(
                        "same corpus already has invoked or unchanged-candidate canary custody"
                    )
                if sibling["canary_status"] in {"started", "retrying"}:
                    with _lock(self.directory, sibling_key):
                        sibling = _read(path, sibling_key, sibling_binding)
                        if (
                            sibling["canary_calls_started"] != 0
                            or sibling["canary_calls_completed"] != 0
                            or sibling["canary_observation_seen"]
                        ):
                            raise RunIndexError(
                                "candidate repair raced the first invocation"
                            )
                        sibling["canary_status"] = "invalid"
                        sibling["canary_lease_digest"] = None
                        _write(self.directory, path, sibling)

    def begin_canary(self, binding: Mapping[str, Any]) -> bytes:
        self._owner()
        key, normalized, path = self._identity(binding)
        capability = secrets.token_bytes(32)
        corpus_lock = f"corpus-{normalized['corpus']['content_sha256']}"
        with _lock(self.directory, corpus_lock), _lock(self.directory, key):
            self._corpus_consumed(normalized, for_canary=True, current_key=key)
            if path.exists() or path.is_symlink():
                if path.exists() and not path.is_symlink():
                    _read(path, key, normalized)
                raise RunIndexError("canary already started; replay rejected")
            state = _initial_state(key, normalized, self._lease(capability))
            _write(self.directory, path, state)
        self._remember_capability(self._canary_caps, key, capability)
        return capability

    def canary_call_started(
        self, binding: Mapping[str, Any], capability: bytes
    ) -> None:
        key, normalized, path, state = self._state(binding)
        corpus_lock = f"corpus-{normalized['corpus']['content_sha256']}"
        with _lock(self.directory, corpus_lock), _lock(self.directory, key):
            state = _read(path, key, normalized)
            self._require_cap(key, state, capability, phase="canary")
            limit = state["canary_attempt"] * CANARY_CALLS
            if (
                state["canary_status"] not in {"started", "retrying"}
                or state["canary_calls_started"] >= limit
            ):
                raise RunIndexError("canary call limit exceeded")
            state["canary_calls_started"] += 1
            _write(self.directory, path, state)

    def canary_observation(self, binding: Mapping[str, Any], capability: bytes) -> None:
        key, normalized, path, state = self._state(binding)
        with _lock(self.directory, key):
            state = _read(path, key, normalized)
            self._require_cap(key, state, capability, phase="canary")
            if state["canary_calls_started"] <= state["canary_calls_completed"]:
                raise RunIndexError("canary observation preceded a call")
            state["canary_observation_seen"] = True
            _write(self.directory, path, state)

    def canary_call_completed(
        self,
        binding: Mapping[str, Any],
        capability: bytes,
        usage: Mapping[str, Any],
    ) -> None:
        key, normalized, path, state = self._state(binding)
        with _lock(self.directory, key):
            state = _read(path, key, normalized)
            self._require_cap(key, state, capability, phase="canary")
            if state["canary_calls_completed"] >= state["canary_calls_started"]:
                raise RunIndexError("canary call completion is duplicate")
            state["canary_calls_completed"] += 1
            state["canary_usage"] = _add_usage(state["canary_usage"], usage)
            _write(self.directory, path, state)

    def retry_canary(self, binding: Mapping[str, Any], capability: bytes) -> None:
        key, normalized, path, state = self._state(binding)
        with _lock(self.directory, key):
            state = _read(path, key, normalized)
            self._require_cap(key, state, capability, phase="canary")
            if (
                state["canary_attempt"] != 1
                or state["canary_observation_seen"]
                or state["canary_calls_completed"] != 0
                or state["canary_calls_started"] != CANARY_CALLS
                or state["canary_status"] != "started"
            ):
                raise RunIndexError("canary retry is not pre-observation eligible")
            state["canary_attempt"] = 2
            state["canary_status"] = "retrying"
            _write(self.directory, path, state)

    def complete_canary(
        self,
        binding: Mapping[str, Any],
        capability: bytes,
        aggregate_digest: str,
    ) -> None:
        key, normalized, path, state = self._state(binding)
        _hex(aggregate_digest, 64, "canary aggregate")
        with _lock(self.directory, key):
            state = _read(path, key, normalized)
            self._require_cap(key, state, capability, phase="canary")
            expected = state["canary_attempt"] * CANARY_CALLS
            if (
                state["canary_calls_started"] != expected
                or state["canary_calls_completed"] != CANARY_CALLS
                or not state["canary_observation_seen"]
            ):
                raise RunIndexError("canary lacks four completed assessor calls")
            state["canary_status"] = "passed"
            state["canary_lease_digest"] = None
            state["aggregate_digest"] = aggregate_digest
            _write(self.directory, path, state)
        del self._canary_caps[key]
        self._completed_canaries.add(key)

    def fail_canary(
        self, binding: Mapping[str, Any], capability: bytes, *, invalid: bool
    ) -> None:
        key, normalized, path, state = self._state(binding)
        with _lock(self.directory, key):
            state = _read(path, key, normalized)
            self._require_cap(key, state, capability, phase="canary")
            state["canary_status"] = "invalid" if invalid else "failed"
            state["canary_lease_digest"] = None
            _write(self.directory, path, state)
        del self._canary_caps[key]

    def begin_batch(self, binding: Mapping[str, Any]) -> bytes:
        """Consume the corpus atomically immediately before the first child."""
        self._owner()
        key, normalized, path, state = self._state(binding)
        if key not in self._completed_canaries:
            raise RunIndexError("batch requires same-process completed canary custody")
        capability = secrets.token_bytes(32)
        corpus_lock = f"corpus-{normalized['corpus']['content_sha256']}"
        with _lock(self.directory, corpus_lock), _lock(self.directory, key):
            state = _read(path, key, normalized)
            if (
                state["canary_status"] != "passed"
                or state["batch_status"] != "not-started"
            ):
                raise RunIndexError("batch is not eligible")
            self._corpus_consumed(normalized)
            state["corpus_status"] = "consumed"
            state["batch_status"] = "started"
            state["batch_lease_digest"] = self._lease(capability)
            _write(self.directory, path, state)
        self._remember_capability(self._batch_caps, key, capability)
        return capability

    def presentation_started(
        self, binding: Mapping[str, Any], capability: bytes
    ) -> None:
        key, normalized, path, state = self._state(binding)
        with _lock(self.directory, key):
            state = _read(path, key, normalized)
            self._require_cap(key, state, capability, phase="batch")
            if state["batch_presentations_started"] >= BATCH_PRESENTATIONS:
                raise RunIndexError("81st presentation rejected")
            state["batch_presentations_started"] += 1
            _write(self.directory, path, state)

    def batch_call_started(self, binding: Mapping[str, Any], capability: bytes) -> None:
        key, normalized, path, state = self._state(binding)
        with _lock(self.directory, key):
            state = _read(path, key, normalized)
            self._require_cap(key, state, capability, phase="batch")
            if state["batch_calls_started"] >= BATCH_CALLS:
                raise RunIndexError("321st batch call rejected")
            if (
                state["batch_calls_started"]
                >= state["batch_presentations_started"] * CALLS_PER_PRESENTATION
            ):
                raise RunIndexError("batch call lacks a started presentation")
            state["batch_calls_started"] += 1
            _write(self.directory, path, state)

    def batch_observation(self, binding: Mapping[str, Any], capability: bytes) -> None:
        key, normalized, path, state = self._state(binding)
        with _lock(self.directory, key):
            state = _read(path, key, normalized)
            self._require_cap(key, state, capability, phase="batch")
            if state["batch_calls_started"] <= state["batch_calls_completed"]:
                raise RunIndexError("batch observation preceded a call")
            state["batch_observation_seen"] = True
            _write(self.directory, path, state)

    def batch_call_completed(
        self,
        binding: Mapping[str, Any],
        capability: bytes,
        usage: Mapping[str, Any],
    ) -> None:
        key, normalized, path, state = self._state(binding)
        with _lock(self.directory, key):
            state = _read(path, key, normalized)
            self._require_cap(key, state, capability, phase="batch")
            if state["batch_calls_completed"] >= state["batch_calls_started"]:
                raise RunIndexError("batch call completion is duplicate")
            state["batch_calls_completed"] += 1
            state["batch_usage"] = _add_usage(state["batch_usage"], usage)
            _write(self.directory, path, state)

    def presentation_completed(
        self, binding: Mapping[str, Any], capability: bytes
    ) -> None:
        key, normalized, path, state = self._state(binding)
        with _lock(self.directory, key):
            state = _read(path, key, normalized)
            self._require_cap(key, state, capability, phase="batch")
            next_count = state["batch_presentations_completed"] + 1
            if next_count > state["batch_presentations_started"]:
                raise RunIndexError("presentation completion preceded start")
            if state["batch_calls_completed"] < next_count * CALLS_PER_PRESENTATION:
                raise RunIndexError("presentation lacks four completed calls")
            state["batch_presentations_completed"] = next_count
            _write(self.directory, path, state)

    def complete_batch(
        self,
        binding: Mapping[str, Any],
        capability: bytes,
        *,
        status: str,
        aggregate_digest: str,
    ) -> None:
        if status not in {"passed", "failed"}:
            raise RunIndexError("completed batch status is invalid")
        _hex(aggregate_digest, 64, "aggregate")
        key, normalized, path, state = self._state(binding)
        with _lock(self.directory, key):
            state = _read(path, key, normalized)
            self._require_cap(key, state, capability, phase="batch")
            if (
                state["batch_presentations_completed"] != BATCH_PRESENTATIONS
                or state["batch_calls_started"] != BATCH_CALLS
                or state["batch_calls_completed"] != BATCH_CALLS
            ):
                raise RunIndexError("batch does not have exact 80x4 closure")
            state["batch_status"] = status
            state["aggregate_digest"] = aggregate_digest
            state["terminal_marker"] = (
                f"consumed-{status[:-2] if status.endswith('ed') else status}"
            )
            # passed -> pass, failed -> fail
            state["terminal_marker"] = (
                "consumed-pass" if status == "passed" else "consumed-fail"
            )
            state["batch_lease_digest"] = None
            _write(self.directory, path, state)
        del self._batch_caps[key]

    def mark_batch_invalid(
        self,
        binding: Mapping[str, Any],
        capability: bytes,
        aggregate_digest: str,
    ) -> None:
        """Durably close any consumed crash/integrity failure; never resumable."""
        _hex(aggregate_digest, 64, "invalid aggregate")
        key, normalized, path, state = self._state(binding)
        with _lock(self.directory, key):
            state = _read(path, key, normalized)
            self._require_cap(key, state, capability, phase="batch")
            state["batch_status"] = "invalid"
            state["aggregate_digest"] = aggregate_digest
            state["terminal_marker"] = "consumed-invalid"
            state["batch_lease_digest"] = None
            _write(self.directory, path, state)
        del self._batch_caps[key]


__all__ = [
    "AESQ1RunIndex",
    "BATCH_CALLS",
    "BATCH_PRESENTATIONS",
    "CALLS_PER_PRESENTATION",
    "CANARY_CALLS",
    "INDEX_NAME",
    "PROGRAM_ID",
    "RunIndexError",
    "normalize_binding",
    "normalize_usage",
    "run_key",
]
