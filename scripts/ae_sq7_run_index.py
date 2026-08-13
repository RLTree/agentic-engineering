#!/usr/bin/env python3
"""Atomic one-shot execution boundary for the AE-SQ7 qualification run.

The durable record intentionally contains no counters, leases, phase names, or
raw evaluation material.  A live runner creates exactly one global claim before
its first child process.  A crash leaves that claim in place and therefore
permanently closes the program to replay.
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
from pathlib import Path
from typing import Any, Mapping


class RunIndexError(RuntimeError):
    """The one-shot custody boundary could not be proved safe."""


INDEX_NAME = ".ae-sq7-one-shot"
STATE_NAME = "state.json"
SCHEMA_VERSION = "ae-sq7-one-shot-run-index-v1"
PROGRAM_ID = "AE-SQ7"
MAX_STATE_BYTES = 8_192
TOP_LEVEL_KEYS = (
    "binding",
    "custody_key",
    "program_id",
    "record_sha256",
    "schema_version",
    "state_sha256",
    "status",
)
BINDING_KEYS = (
    "corpus_manifest_sha256",
    "f1_freeze_sha256",
    "preflight_record_sha256",
    "program_authority_sha256",
    "run_manifest_sha256",
)
TERMINAL_STATUSES = frozenset({"completed", "invalid"})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical_json(value: Any) -> bytes:
    """Encode the sole ASCII canonical form admitted by the run index."""
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise RunIndexError("run-index value is not canonical JSON") from error


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value: Any) -> str:
    return _sha256_bytes(canonical_json(value))


def _hex64(value: Any, label: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise RunIndexError(f"{label} is not a lowercase SHA-256")
    return value


def normalize_binding(value: Mapping[str, Any]) -> dict[str, str]:
    """Return the exact five-digest binding in its canonical key order."""
    if not isinstance(value, Mapping) or set(value) != set(BINDING_KEYS):
        raise RunIndexError("one-shot binding is not exactly closed")
    return {key: _hex64(value[key], key) for key in BINDING_KEYS}


def custody_key(binding: Mapping[str, Any]) -> str:
    return _digest(normalize_binding(binding))


def _sealed_state(
    binding: Mapping[str, Any], *, status: str, record_sha256: str | None
) -> dict[str, Any]:
    normalized = normalize_binding(binding)
    if status == "claimed":
        if record_sha256 is not None:
            raise RunIndexError("claimed state cannot bind a terminal record")
    elif status in TERMINAL_STATUSES:
        _hex64(record_sha256, "terminal record")
    else:
        raise RunIndexError("one-shot status is outside the closed enum")
    state: dict[str, Any] = {
        "binding": normalized,
        "custody_key": custody_key(normalized),
        "program_id": PROGRAM_ID,
        "record_sha256": record_sha256,
        "schema_version": SCHEMA_VERSION,
    }
    state["state_sha256"] = _digest(state)
    state["status"] = status
    # state_sha256 covers the complete canonical record with only that field
    # omitted, including the terminal status which is appended above.
    state["state_sha256"] = _digest(
        {key: item for key, item in state.items() if key != "state_sha256"}
    )
    if tuple(state) != TOP_LEVEL_KEYS:
        raise RunIndexError("internal one-shot key order drift")
    return state


def _closed_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _strict_state(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("ascii", "strict"),
            object_pairs_hook=_closed_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise RunIndexError("one-shot state is not strict JSON") from error
    if (
        not isinstance(value, dict)
        or tuple(value) != TOP_LEVEL_KEYS
        or canonical_json(value) != raw
    ):
        raise RunIndexError("one-shot state is noncanonical, reordered, or open")
    return value


def validate_state(value: Any, expected_binding: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the complete recursive state and all derived digests."""
    if not isinstance(value, Mapping) or tuple(value) != TOP_LEVEL_KEYS:
        raise RunIndexError("one-shot state keys or order drifted")
    binding = value.get("binding")
    if not isinstance(binding, Mapping) or tuple(binding) != BINDING_KEYS:
        raise RunIndexError("one-shot binding keys or order drifted")
    normalized = normalize_binding(binding)
    expected = normalize_binding(expected_binding)
    if normalized != expected:
        raise RunIndexError("existing one-shot state has a different binding")
    if (
        value.get("custody_key") != custody_key(normalized)
        or value.get("program_id") != PROGRAM_ID
        or value.get("schema_version") != SCHEMA_VERSION
    ):
        raise RunIndexError("one-shot identity or custody digest drifted")
    status = value.get("status")
    record_sha256 = value.get("record_sha256")
    if status == "claimed":
        if record_sha256 is not None:
            raise RunIndexError("claimed state has a terminal record")
    elif status in TERMINAL_STATUSES:
        _hex64(record_sha256, "terminal record")
    else:
        raise RunIndexError("one-shot status is invalid")
    supplied_state_sha256 = _hex64(value.get("state_sha256"), "state digest")
    unsigned = {key: item for key, item in value.items() if key != "state_sha256"}
    if supplied_state_sha256 != _digest(unsigned):
        raise RunIndexError("one-shot state digest is invalid")
    return dict(value)


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


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def git_common_dir(root: Path | str) -> Path:
    """Resolve the repository's shared Git directory without writing."""
    try:
        repository = Path(root).resolve(strict=True)
        completed = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=repository,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=30,
        )
        candidate = Path(completed.stdout.strip())
        if not candidate.is_absolute():
            candidate = repository / candidate
        common = candidate.resolve(strict=True)
        metadata = common.lstat()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise RunIndexError("Git common directory is unavailable") from error
    if common.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise RunIndexError("Git common directory is unsafe")
    return common


def _index_path(root: Path | str) -> Path:
    common = git_common_dir(root)
    directory = common / INDEX_NAME
    if directory.parent != common or directory.name != INDEX_NAME:
        raise RunIndexError("one-shot directory escaped Git custody")
    return directory


def _validate_directory(directory: Path) -> None:
    try:
        metadata = directory.lstat()
    except OSError as error:
        raise RunIndexError("one-shot directory is unavailable") from error
    if (
        directory.is_symlink()
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise RunIndexError("one-shot directory is not owner-only")


def _ensure_directory(root: Path | str) -> Path:
    directory = _index_path(root)
    common = directory.parent
    try:
        os.mkdir(directory, 0o700)
        os.chmod(directory, 0o700)
        _fsync_directory(common)
    except FileExistsError:
        pass
    except OSError as error:
        raise RunIndexError("one-shot directory could not be created") from error
    _validate_directory(directory)
    return directory


def state_path(root: Path | str) -> Path:
    """Return the fixed global AE-SQ7 state path without creating it."""
    return _index_path(root) / STATE_NAME


def assert_unclaimed(root: Path | str) -> None:
    """Read-only F3/live preflight: prove that no one-shot state exists."""
    directory = _index_path(root)
    try:
        directory.lstat()
    except FileNotFoundError:
        return
    except OSError as error:
        raise RunIndexError("one-shot namespace cannot be inspected") from error
    _validate_directory(directory)
    try:
        entries = tuple(directory.iterdir())
    except OSError as error:
        raise RunIndexError("one-shot namespace cannot be enumerated") from error
    if entries:
        raise RunIndexError("AE-SQ7 execution is already claimed or unsafe")


def _read_private_state(
    path: Path, expected_binding: Mapping[str, Any]
) -> dict[str, Any]:
    try:
        before = path.lstat()
    except OSError as error:
        raise RunIndexError("one-shot state is unavailable") from error
    if (
        path.is_symlink()
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != os.getuid()
        or before.st_nlink != 1
        or stat.S_IMODE(before.st_mode) != 0o600
        or not 0 < before.st_size <= MAX_STATE_BYTES
    ):
        raise RunIndexError("one-shot state has an unsafe file identity")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise RunIndexError("one-shot state cannot be opened safely") from error
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.getuid()
            or opened.st_nlink != 1
            or stat.S_IMODE(opened.st_mode) != 0o600
            or _file_identity(before) != _file_identity(opened)
        ):
            raise RunIndexError("one-shot state identity changed before read")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, 65_536)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_STATE_BYTES:
                raise RunIndexError("one-shot state exceeds its size bound")
        closed = os.fstat(descriptor)
        if _file_identity(opened) != _file_identity(closed):
            raise RunIndexError("one-shot state changed during read")
    except OSError as error:
        raise RunIndexError("one-shot state read failed") from error
    finally:
        os.close(descriptor)
    return validate_state(_strict_state(b"".join(chunks)), expected_binding)


def _write_all(descriptor: int, raw: bytes) -> None:
    view = memoryview(raw)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise RunIndexError("one-shot state write did not progress")
        view = view[written:]


class AESQ7RunIndex:
    """Single-process capability wrapper around one durable global record."""

    def __init__(self, root: Path | str):
        self.root = Path(root).resolve(strict=True)
        self._owner_pid = os.getpid()
        self._process_key = secrets.token_bytes(32)
        self._capability: tuple[bytes, bytes] | None = None
        self._binding: dict[str, str] | None = None

    @property
    def directory(self) -> Path:
        return _index_path(self.root)

    @property
    def path(self) -> Path:
        return self.directory / STATE_NAME

    def assert_unclaimed(self) -> None:
        assert_unclaimed(self.root)

    def _remember(self, capability: bytes) -> None:
        tag = hmac.new(self._process_key, capability, hashlib.sha256).digest()
        self._capability = (capability, tag)

    def _require_capability(
        self, capability: object, binding: Mapping[str, Any]
    ) -> dict[str, str]:
        if os.getpid() != self._owner_pid:
            raise RunIndexError("one-shot capability cannot cross a process boundary")
        normalized = normalize_binding(binding)
        entry = self._capability
        if (
            entry is None
            or type(capability) is not bytes
            or len(capability) != 32
            or not hmac.compare_digest(entry[0], capability)
            or not hmac.compare_digest(
                entry[1],
                hmac.new(self._process_key, capability, hashlib.sha256).digest(),
            )
            or self._binding != normalized
        ):
            raise RunIndexError("one-shot mutation capability is absent or invalid")
        return normalized

    def claim(self, binding: Mapping[str, Any]) -> bytes:
        """Atomically create the only live-execution claim."""
        if os.getpid() != self._owner_pid or self._capability is not None:
            raise RunIndexError("one-shot instance has already been used")
        normalized = normalize_binding(binding)
        directory = _ensure_directory(self.root)
        try:
            existing = tuple(entry.name for entry in directory.iterdir())
        except OSError as error:
            raise RunIndexError("one-shot namespace cannot be enumerated") from error
        if existing:
            if existing == (STATE_NAME,):
                _read_private_state(directory / STATE_NAME, normalized)
            raise RunIndexError("AE-SQ7 execution is already claimed or unsafe")
        path = directory / STATE_NAME
        state = _sealed_state(normalized, status="claimed", record_sha256=None)
        raw = canonical_json(state)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags, 0o600)
        except FileExistsError as error:
            _read_private_state(path, normalized)
            raise RunIndexError("AE-SQ7 execution is already claimed") from error
        except OSError as error:
            raise RunIndexError("one-shot claim could not be created") from error
        try:
            os.fchmod(descriptor, 0o600)
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_uid != os.getuid()
                or opened.st_nlink != 1
                or stat.S_IMODE(opened.st_mode) != 0o600
            ):
                raise RunIndexError("one-shot claim has an unsafe identity")
            _write_all(descriptor, raw)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        _fsync_directory(directory)
        if tuple(entry.name for entry in directory.iterdir()) != (STATE_NAME,):
            raise RunIndexError("one-shot namespace changed during claim")
        if _read_private_state(path, normalized) != state:
            raise RunIndexError("one-shot claim did not persist exactly")
        capability = secrets.token_bytes(32)
        self._binding = normalized
        self._remember(capability)
        return capability

    # Explicit name used by the live runner and kept as the only semantic alias.
    claim_execution = claim

    def state(self, binding: Mapping[str, Any]) -> dict[str, Any]:
        normalized = normalize_binding(binding)
        directory = _index_path(self.root)
        _validate_directory(directory)
        names = tuple(entry.name for entry in directory.iterdir())
        if names != (STATE_NAME,):
            raise RunIndexError("one-shot namespace contains unexpected material")
        return _read_private_state(directory / STATE_NAME, normalized)

    def _finalize(
        self,
        binding: Mapping[str, Any],
        capability: object,
        *,
        status: str,
        record_sha256: str,
    ) -> dict[str, Any]:
        normalized = self._require_capability(capability, binding)
        # Finalization is itself one-shot.  If any subsequent filesystem step
        # fails, the durable claim remains and this process cannot retry the
        # terminal replacement.
        self._capability = None
        if status not in TERMINAL_STATUSES:
            raise RunIndexError("terminal one-shot status is invalid")
        _hex64(record_sha256, "terminal record")
        directory = _index_path(self.root)
        _validate_directory(directory)
        path = directory / STATE_NAME
        existing = _read_private_state(path, normalized)
        expected = _sealed_state(normalized, status="claimed", record_sha256=None)
        if existing != expected:
            raise RunIndexError("one-shot claim is no longer the exact active claim")
        terminal = _sealed_state(normalized, status=status, record_sha256=record_sha256)
        raw = canonical_json(terminal)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".ae-sq7-terminal-", suffix=".tmp", dir=directory
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            _write_all(descriptor, raw)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = -1
            os.replace(temporary, path)
            _fsync_directory(directory)
            if _read_private_state(path, normalized) != terminal:
                raise RunIndexError("terminal one-shot state did not persist exactly")
        finally:
            if descriptor != -1:
                os.close(descriptor)
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        return terminal

    def complete(
        self,
        binding: Mapping[str, Any],
        capability: object,
        record_sha256: str,
    ) -> dict[str, Any]:
        return self._finalize(
            binding,
            capability,
            status="completed",
            record_sha256=record_sha256,
        )

    def invalidate(
        self,
        binding: Mapping[str, Any],
        capability: object,
        record_sha256: str,
    ) -> dict[str, Any]:
        return self._finalize(
            binding,
            capability,
            status="invalid",
            record_sha256=record_sha256,
        )


__all__ = [
    "AESQ7RunIndex",
    "BINDING_KEYS",
    "INDEX_NAME",
    "PROGRAM_ID",
    "RunIndexError",
    "SCHEMA_VERSION",
    "STATE_NAME",
    "TOP_LEVEL_KEYS",
    "assert_unclaimed",
    "canonical_json",
    "custody_key",
    "normalize_binding",
    "state_path",
    "validate_state",
]
