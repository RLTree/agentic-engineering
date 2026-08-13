#!/usr/bin/env python3
"""Bounded, non-corpus four-call handshake diagnostic for AE-SQ2.

The only durable output is a closed aggregate record containing hashes,
lengths, counters, and classifications. Prompt, event, provider-error, and
completed-message bytes exist only in memory or owner-only temporary
directories and are discarded before this process exits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

from jsonschema import Draft202012Validator

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = ROOT / "evals/ae-sq2/d0/diagnostic-authority.json"
RECORD_SCHEMA_PATH = ROOT / "evals/ae-sq2/d0/diagnostic-schema.json"
PROGRAM_AUTHORITY_PATH = ROOT / "evals/ae-sq2/program-authority.json"
MODEL = "gpt-5.5"
REASONING = "medium"
APPROVAL = "ae-sq2-authorized-diagnostic-four-call"
CLI_VERSION = "codex-cli 0.147.0"
CLI_SHA256 = "19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37"
SQ1_SCHEMA_PATH = "evals/ae-sq1/slec1-capsule-schema.json"
SQ1_SCHEMA_SHA256 = "7124be192fa7d047ae7d9e54f1cfd84c32129164caddf6474277ae5fb3e65f4f"
CALLS = 4
TIMEOUT_SECONDS = 600
MAX_REQUEST_BYTES = 16_384
MAX_STDOUT_BYTES = 1_048_576
MAX_STDERR_BYTES = 65_536
READ_CHUNK_BYTES = 8_192
CUSTODY_DIRECTORY = ".ae-sq2-d0"
CUSTODY_SCHEMA_VERSION = "ae-sq2-d0-custody-v1"
MAX_CUSTODY_BYTES = 8_192
HEX64 = re.compile(r"^[0-9a-f]{64}$")

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
KNOWN_EVENTS = (
    "thread.started",
    "turn.started",
    "item.completed",
    "turn.completed",
    "turn.failed",
    "error",
)
EVENT_COUNT_KEYS = (
    "thread_started",
    "turn_started",
    "item_completed",
    "turn_completed",
    "turn_failed",
    "error",
    "unknown",
)
USAGE_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens", "total_tokens")

# These are protocol probes, not evaluation cases. They are fixed before D0 and
# differ only by the required slot identifier so the original four-slot schema
# path is reproduced without opening any corpus.
_PROBE_TEMPLATE = (
    "AE-SQ2 D0 synthetic handshake probe {probe_id}. No tools or external data. "
    "Return exactly one JSON object satisfying the supplied output schema. "
    "Use slot_id {slot_id}. Treat the unique phrase 'reversible quartz marker "
    "{probe_id}' as the entire synthetic task evidence. Set local_need to yes, "
    "reference_need to none, and anchors to one exact occurrence of that phrase "
    "with correct zero-based start and end offsets in this prompt."
)
PROBE_IDS = ("p0", "p1", "p2", "p3")
SLOT_IDS = ("s0", "s1", "s2", "s3")

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


class DiagnosticError(RuntimeError):
    """The diagnostic cannot safely produce a record."""


@dataclass(frozen=True)
class Probe:
    probe_id: str
    slot_id: str
    request: bytes


@dataclass(frozen=True)
class RawProcessResult:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    stdout_bytes: int
    stderr_bytes: int
    stdout_sha256: str
    stderr_sha256: str
    timed_out: bool = False
    spawn_failed: bool = False
    overflowed: bool = False


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _closed_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def strict_json(value: bytes | str) -> Any:
    text = value.decode("utf-8") if isinstance(value, bytes) else value
    return json.loads(
        text, object_pairs_hook=_closed_pairs, parse_constant=_reject_constant
    )


def probes() -> tuple[Probe, ...]:
    result = tuple(
        Probe(
            probe_id=probe_id,
            slot_id=slot_id,
            request=_PROBE_TEMPLATE.format(probe_id=probe_id, slot_id=slot_id).encode(
                "utf-8"
            ),
        )
        for probe_id, slot_id in zip(PROBE_IDS, SLOT_IDS, strict=True)
    )
    if len(result) != CALLS or any(
        not probe.request or len(probe.request) > MAX_REQUEST_BYTES for probe in result
    ):
        raise DiagnosticError("fixed probe set is not closed and bounded")
    return result


def _regular_owned_file(path: Path, *, private: bool = False) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise DiagnosticError("required file is unavailable") from error
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or (private and stat.S_IMODE(metadata.st_mode) != 0o600)
        or metadata.st_size <= 0
    ):
        raise DiagnosticError("required file fails owner-only custody")
    return metadata


def _auth_source() -> tuple[Path, tuple[int, ...]]:
    configured = os.environ.get("CODEX_HOME")
    base = Path(configured) if configured else Path.home() / ".codex"
    if not base.is_absolute():
        raise DiagnosticError("CODEX_HOME must be absolute")
    source = base / "auth.json"
    metadata = _regular_owned_file(source, private=True)
    return source, _fingerprint(metadata)


def _fingerprint(metadata: os.stat_result) -> tuple[int, ...]:
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


def _child_env(home: Path, private_tmp: Path) -> dict[str, str]:
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
    environment["HOME"] = str(home)
    environment["CODEX_HOME"] = str(home)
    environment["TMPDIR"] = str(private_tmp)
    return environment


@contextmanager
def isolated_child() -> Iterator[tuple[Path, Mapping[str, str]]]:
    source, fingerprint = _auth_source()
    home_temp = tempfile.TemporaryDirectory(prefix="ae-sq2-d0-home-")
    cwd_temp = tempfile.TemporaryDirectory(prefix="ae-sq2-d0-cwd-")
    home = Path(home_temp.name)
    cwd = Path(cwd_temp.name)
    try:
        os.chmod(home, 0o700)
        os.chmod(cwd, 0o700)
        if any(home.iterdir()) or any(cwd.iterdir()):
            raise DiagnosticError("isolation directories are not empty")
        current, current_fingerprint = _auth_source()
        if current != source or current_fingerprint != fingerprint:
            raise DiagnosticError("auth source changed before isolation")
        destination = home / "auth.json"
        shutil.copyfile(source, destination, follow_symlinks=False)
        os.chmod(destination, 0o600)
        _regular_owned_file(destination, private=True)
        private_tmp = home / "tmp"
        private_tmp.mkdir(mode=0o700)
        os.chmod(private_tmp, 0o700)
        private_tmp_metadata = private_tmp.lstat()
        if (
            private_tmp.is_symlink()
            or not stat.S_ISDIR(private_tmp_metadata.st_mode)
            or private_tmp_metadata.st_uid != os.getuid()
            or stat.S_IMODE(private_tmp_metadata.st_mode) != 0o700
            or any(private_tmp.iterdir())
        ):
            raise DiagnosticError("private child TMPDIR is not fresh and owner-only")
        if {entry.name for entry in home.iterdir()} != {"auth.json", "tmp"}:
            raise DiagnosticError("isolated CODEX_HOME contains unexpected material")
        yield cwd, _child_env(home, private_tmp)
        if _fingerprint(source.lstat()) != fingerprint:
            raise DiagnosticError("auth source changed during diagnostic call")
    finally:
        cwd_temp.cleanup()
        home_temp.cleanup()
        if cwd.exists() or home.exists():
            raise DiagnosticError("temporary diagnostic isolation cleanup failed")


def resolve_cli(value: str) -> dict[str, str]:
    candidate = Path(value)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        found = shutil.which(value)
        if found is None:
            raise DiagnosticError("Codex CLI is unavailable")
        resolved = Path(found).resolve()
    _regular_owned_file(resolved)
    digest = sha256_bytes(resolved.read_bytes())
    if digest != CLI_SHA256:
        raise DiagnosticError("Codex CLI bytes do not match the exact D0 pin")
    return {
        "path": str(resolved),
        "version": CLI_VERSION,
        "sha256": digest,
    }


def resolve_schema(
    path_value: str, expected_sha256: str
) -> tuple[Path, dict[str, Any], Any]:
    if len(expected_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in expected_sha256
    ):
        raise DiagnosticError("--schema-sha256 must be lowercase SHA-256")
    given = Path(path_value)
    path = (ROOT / given).resolve() if not given.is_absolute() else given.resolve()
    try:
        relative = path.relative_to(ROOT).as_posix()
    except ValueError as error:
        raise DiagnosticError(
            "diagnostic schema must remain inside the repository"
        ) from error
    _regular_owned_file(path)
    raw = path.read_bytes()
    if sha256_bytes(raw) != expected_sha256:
        raise DiagnosticError("explicit diagnostic input schema digest mismatch")
    try:
        document = strict_json(raw)
        Draft202012Validator.check_schema(document)
    except Exception as error:
        raise DiagnosticError("explicit diagnostic input schema is invalid") from error
    return (
        path,
        {"path": relative, "size_bytes": len(raw), "sha256": expected_sha256},
        document,
    )


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
        argv.extend(("--disable", feature))
    for override in CONFIG_OVERRIDES:
        argv.extend(("-c", override))
    return [*argv, "-"]


def _empty_digest() -> str:
    return sha256_bytes(b"")


def _spawn_failure() -> RawProcessResult:
    return RawProcessResult(
        returncode=None,
        stdout=b"",
        stderr=b"",
        stdout_bytes=0,
        stderr_bytes=0,
        stdout_sha256=_empty_digest(),
        stderr_sha256=_empty_digest(),
        spawn_failed=True,
    )


def _other_closed_failure() -> RawProcessResult:
    return RawProcessResult(
        returncode=None,
        stdout=b"",
        stderr=b"",
        stdout_bytes=0,
        stderr_bytes=0,
        stdout_sha256=_empty_digest(),
        stderr_sha256=_empty_digest(),
        overflowed=True,
    )


def _run_bounded(
    argv: Sequence[str],
    request: bytes,
    *,
    cwd: Path,
    env: Mapping[str, str],
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
    timeout_seconds: int = TIMEOUT_SECONDS,
) -> RawProcessResult:
    try:
        process = popen(
            list(argv),
            cwd=cwd,
            env=dict(env),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError:
        return _spawn_failure()
    if process.stdin is None or process.stdout is None or process.stderr is None:
        try:
            process.kill()
        except OSError:
            pass
        return _spawn_failure()
    stdout_hash = hashlib.sha256()
    stderr_hash = hashlib.sha256()
    stdout = bytearray()
    stderr = bytearray()
    stdout_count = 0
    stderr_count = 0
    overflowed = False
    timed_out = False
    selector = selectors.DefaultSelector()
    started = time.monotonic()
    try:
        try:
            process.stdin.write(request)
            process.stdin.close()
        except BrokenPipeError:
            # A local/provider rejection may close stdin before consuming the
            # synthetic probe. Continue draining its bounded diagnostic output.
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass
        for stream, name in ((process.stdout, "stdout"), (process.stderr, "stderr")):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map():
            remaining = timeout_seconds - (time.monotonic() - started)
            if remaining <= 0:
                timed_out = True
                break
            ready = selector.select(min(remaining, 0.25))
            if not ready and process.poll() is not None:
                ready = [
                    (key, selectors.EVENT_READ) for key in selector.get_map().values()
                ]
            for key, _ in ready:
                try:
                    chunk = os.read(key.fileobj.fileno(), READ_CHUNK_BYTES)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "stdout":
                    stdout_count += len(chunk)
                    stdout_hash.update(chunk)
                    if stdout_count <= MAX_STDOUT_BYTES:
                        stdout.extend(chunk)
                    else:
                        overflowed = True
                else:
                    stderr_count += len(chunk)
                    stderr_hash.update(chunk)
                    if stderr_count <= MAX_STDERR_BYTES:
                        stderr.extend(chunk)
                    else:
                        overflowed = True
            if overflowed:
                break
        if timed_out or overflowed:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                process.kill()
        returncode = process.wait(timeout=5)
    except (OSError, subprocess.SubprocessError):
        try:
            process.kill()
            process.wait(timeout=5)
        except (OSError, subprocess.SubprocessError):
            pass
        returncode = process.returncode
        overflowed = True
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()
    return RawProcessResult(
        returncode=returncode,
        stdout=bytes(stdout),
        stderr=bytes(stderr),
        stdout_bytes=stdout_count,
        stderr_bytes=stderr_count,
        stdout_sha256=stdout_hash.hexdigest(),
        stderr_sha256=stderr_hash.hexdigest(),
        timed_out=timed_out,
        overflowed=overflowed,
    )


def _invoke_probe(
    probe: Probe, cli: Mapping[str, str], schema_path: Path
) -> RawProcessResult:
    try:
        with isolated_child() as (cwd, environment):
            return _run_bounded(
                child_argv(cli, schema_path),
                probe.request,
                cwd=cwd,
                env=environment,
            )
    except DiagnosticError:
        return _other_closed_failure()


def _zero_usage() -> dict[str, int]:
    return {key: 0 for key in USAGE_KEYS}


def _event_counts() -> dict[str, int]:
    return {key: 0 for key in EVENT_COUNT_KEYS}


def _classification_counts() -> dict[str, int]:
    return {key: 0 for key in CLASSIFICATIONS}


@dataclass(frozen=True)
class CustodyClaim:
    directory: Path
    path: Path
    key: str
    binding: Mapping[str, str]


def _git_common_dir(root: Path) -> Path:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--git-common-dir"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=30,
        )
        raw = completed.stdout.strip()
        repository = root.resolve(strict=True)
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = repository / candidate
        common = candidate.resolve(strict=True)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise DiagnosticError("Git common directory is unavailable") from error
    metadata = common.lstat()
    if common.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise DiagnosticError("Git common directory is unsafe")
    return common


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _custody_directory(root: Path) -> Path:
    common = _git_common_dir(root)
    directory = common / CUSTODY_DIRECTORY
    if directory.parent != common or directory.name != CUSTODY_DIRECTORY:
        raise DiagnosticError("D0 custody directory escaped Git common dir")
    try:
        os.mkdir(directory, 0o700)
        os.chmod(directory, 0o700)
        _fsync_directory(common)
    except FileExistsError:
        pass
    try:
        metadata = directory.lstat()
    except OSError as error:
        raise DiagnosticError("D0 custody directory is unavailable") from error
    if (
        directory.is_symlink()
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise DiagnosticError("D0 custody directory is not owner-only")
    return directory


def _custody_binding(
    *,
    authority_raw: bytes,
    record_schema_raw: bytes,
    input_schema_info: Mapping[str, Any],
    cli: Mapping[str, str],
) -> dict[str, str]:
    authority = strict_json(authority_raw)
    parent = authority.get("parent_program_authority")
    if not isinstance(parent, dict):
        raise DiagnosticError("parent program authority binding is unavailable")
    binding = {
        "parent_program_authority_sha256": parent.get("sha256"),
        "diagnostic_authority_sha256": sha256_bytes(authority_raw),
        "diagnostic_schema_sha256": sha256_bytes(record_schema_raw),
        "input_schema_sha256": input_schema_info.get("sha256"),
        "cli_sha256": cli.get("sha256"),
    }
    if any(
        not isinstance(value, str) or HEX64.fullmatch(value) is None
        for value in binding.values()
    ):
        raise DiagnosticError("D0 custody binding contains an invalid digest")
    return binding  # type: ignore[return-value]


def _custody_key(binding: Mapping[str, str]) -> str:
    return sha256_bytes(canonical_json(dict(binding)))


def _sealed_custody_state(
    *,
    key: str,
    binding: Mapping[str, str],
    status: str,
    record_sha256: str | None,
) -> dict[str, Any]:
    if status not in {"claimed", "completed", "invalid"}:
        raise DiagnosticError("D0 custody status is not closed")
    if record_sha256 is not None and HEX64.fullmatch(record_sha256) is None:
        raise DiagnosticError("D0 record digest is invalid")
    state: dict[str, Any] = {
        "schema_version": CUSTODY_SCHEMA_VERSION,
        "custody_key": key,
        "binding": dict(binding),
        "status": status,
        "record_sha256": record_sha256,
    }
    state["state_sha256"] = sha256_bytes(canonical_json(state))
    return state


def _write_all(descriptor: int, raw: bytes) -> None:
    view = memoryview(raw)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise DiagnosticError("D0 custody write did not progress")
        view = view[written:]


def _state_path(directory: Path, key: str) -> Path:
    if HEX64.fullmatch(key) is None:
        raise DiagnosticError("D0 custody key is invalid")
    # The path is intentionally global for AE-SQ2 D0. The exact binding key is
    # sealed inside it; changing any pinned bytes cannot create a second lane.
    path = directory / "state.json"
    if path.parent != directory:
        raise DiagnosticError("D0 custody state escaped its directory")
    return path


def _read_custody_state(path: Path, expected_key: str) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise DiagnosticError("existing D0 custody state is unavailable") from error
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or not 0 < metadata.st_size <= MAX_CUSTODY_BYTES
    ):
        raise DiagnosticError("existing D0 custody state has unsafe identity")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise DiagnosticError(
            "existing D0 custody state cannot be opened safely"
        ) from error
    try:
        opened = os.fstat(descriptor)
        if (
            (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino)
            or opened.st_nlink != 1
            or stat.S_IMODE(opened.st_mode) != 0o600
        ):
            raise DiagnosticError("existing D0 custody state identity changed")
        raw = os.read(descriptor, MAX_CUSTODY_BYTES + 1)
    finally:
        os.close(descriptor)
    try:
        state = strict_json(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise DiagnosticError("existing D0 custody state is invalid JSON") from error
    if not isinstance(state, dict) or canonical_json(state) != raw:
        raise DiagnosticError("existing D0 custody state is noncanonical")
    expected_keys = {
        "schema_version",
        "custody_key",
        "binding",
        "status",
        "record_sha256",
        "state_sha256",
    }
    if (
        set(state) != expected_keys
        or state.get("schema_version") != CUSTODY_SCHEMA_VERSION
    ):
        raise DiagnosticError("existing D0 custody state is not closed")
    supplied_sha = state.pop("state_sha256")
    expected_sha = sha256_bytes(canonical_json(state))
    state["state_sha256"] = supplied_sha
    if supplied_sha != expected_sha or state.get("custody_key") != expected_key:
        raise DiagnosticError("existing D0 custody state digest is invalid")
    if state.get("status") not in {"claimed", "completed", "invalid"}:
        raise DiagnosticError("existing D0 custody state status is invalid")
    record_sha256 = state.get("record_sha256")
    if record_sha256 is not None and (
        not isinstance(record_sha256, str) or HEX64.fullmatch(record_sha256) is None
    ):
        raise DiagnosticError("existing D0 custody record digest is invalid")
    return state


def _claim_d0(root: Path, binding: Mapping[str, str]) -> CustodyClaim:
    directory = _custody_directory(root)
    key = _custody_key(binding)
    path = _state_path(directory, key)
    existing_names = {entry.name for entry in directory.iterdir()}
    if existing_names:
        if existing_names == {path.name}:
            _read_custody_state(path, key)
            raise DiagnosticError("D0 custody is already claimed or terminal")
        raise DiagnosticError("D0 custody directory contains unexpected material")
    state = _sealed_custody_state(
        key=key, binding=binding, status="claimed", record_sha256=None
    )
    raw = canonical_json(state)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as error:
        _read_custody_state(path, key)
        raise DiagnosticError("D0 custody is already claimed or terminal") from error
    except OSError as error:
        raise DiagnosticError("D0 custody claim could not be created") from error
    try:
        os.fchmod(descriptor, 0o600)
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.getuid()
            or opened.st_nlink != 1
            or stat.S_IMODE(opened.st_mode) != 0o600
        ):
            raise DiagnosticError("D0 custody claim has unsafe identity")
        _write_all(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(directory)
    if {entry.name for entry in directory.iterdir()} != {path.name}:
        raise DiagnosticError("D0 custody directory changed during claim")
    stored = _read_custody_state(path, key)
    if stored != state:
        raise DiagnosticError("D0 custody claim did not persist exactly")
    return CustodyClaim(directory=directory, path=path, key=key, binding=dict(binding))


def _finalize_d0_claim(
    claim: CustodyClaim, *, status: str, record_sha256: str | None
) -> None:
    existing = _read_custody_state(claim.path, claim.key)
    expected_claimed = _sealed_custody_state(
        key=claim.key, binding=claim.binding, status="claimed", record_sha256=None
    )
    if existing != expected_claimed:
        raise DiagnosticError("D0 custody claim is not the exact active claim")
    terminal = _sealed_custody_state(
        key=claim.key,
        binding=claim.binding,
        status=status,
        record_sha256=record_sha256,
    )
    raw = canonical_json(terminal)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{claim.key}.", suffix=".tmp", dir=claim.directory
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        _write_all(descriptor, raw)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, claim.path)
        _fsync_directory(claim.directory)
        if _read_custody_state(claim.path, claim.key) != terminal:
            raise DiagnosticError("terminal D0 custody state did not persist exactly")
    finally:
        if descriptor != -1:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _closed_provider_material(event: Any) -> tuple[str, ...] | None:
    if not isinstance(event, dict) or event.get("type") not in {"error", "turn.failed"}:
        return None
    if event["type"] == "error" and set(event) == {"type", "message"}:
        return (event["message"],) if isinstance(event["message"], str) else None
    if set(event) != {"type", "error"} or not isinstance(event["error"], dict):
        return None
    detail = event["error"]
    allowed = {"type", "code", "message", "status", "status_code"}
    if not detail or not set(detail).issubset(allowed):
        return None
    material: list[str] = []
    for key in ("type", "code", "message", "status", "status_code"):
        value = detail.get(key)
        if isinstance(value, str):
            material.append(value)
        elif type(value) is int:
            material.append(str(value))
        elif value is not None:
            return None
    return tuple(material) if material else None


def _provider_error_class(events: Sequence[Any]) -> tuple[str, bool]:
    relevant = [
        material
        for event in events
        if (material := _closed_provider_material(event)) is not None
    ]
    if not relevant:
        return "none", False
    folded = " ".join(item for material in relevant for item in material).casefold()
    if "invalid_json_schema" in folded:
        return "invalid_json_schema", True
    if "invalid_request" in folded or "invalid request" in folded:
        return "invalid_request", True
    if (
        "unauthenticated" in folded
        or "authentication" in folded
        or "login" in folded
        or "401" in folded
        or "unauthorized" in folded
    ):
        return "authentication", True
    if "permission" in folded or "authorization" in folded or "forbidden" in folded:
        return "authorization", True
    if "rate limit" in folded or "rate_limit" in folded or "429" in folded:
        return "rate_limit", True
    if "network" in folded or "connection" in folded or "dns" in folded:
        return "network", True
    if "server" in folded or "internal" in folded:
        return "server", True
    # An explicit error/turn.failed event is a provider rejection even when its
    # closed redaction is merely `other`. Arbitrary stderr alone is retained
    # only as a digest/count and must not erase an otherwise valid completion.
    return "other", bool(relevant)


def _closed_usage(value: Any) -> dict[str, int] | None:
    required = {"input_tokens", "cached_input_tokens", "output_tokens"}
    if not isinstance(value, dict) or set(value) not in (
        required,
        required | {"total_tokens"},
    ):
        return None
    if any(type(value[key]) is not int or value[key] < 0 for key in value):
        return None
    total = value.get("total_tokens", value["input_tokens"] + value["output_tokens"])
    if total != value["input_tokens"] + value["output_tokens"]:
        return None
    if value["cached_input_tokens"] > value["input_tokens"]:
        return None
    return {
        "input_tokens": value["input_tokens"],
        "cached_input_tokens": value["cached_input_tokens"],
        "output_tokens": value["output_tokens"],
        "total_tokens": total,
    }


def _semantic_capsule(value: Any, probe: Probe) -> bool:
    if not isinstance(value, dict):
        return False
    required = {"slot_id", "local_need", "reference_need", "anchors"}
    if set(value) != required or value["slot_id"] != probe.slot_id:
        return False
    local = value["local_need"]
    reference = value["reference_need"]
    anchors = value["anchors"]
    if local == "no" and reference != "none":
        return False
    if local == "uncertain" and reference != "uncertain":
        return False
    uncertain = local == "uncertain" or reference == "uncertain"
    if (
        not isinstance(anchors, list)
        or (uncertain and anchors)
        or (not uncertain and not 1 <= len(anchors) <= 2)
    ):
        return False
    previous_end = -1
    seen: set[tuple[int, int, str]] = set()
    text = probe.request.decode("utf-8")
    for anchor in anchors:
        if not isinstance(anchor, dict) or set(anchor) != {"start", "end", "text"}:
            return False
        start, end, anchor_text = anchor["start"], anchor["end"], anchor["text"]
        if (
            type(start) is not int
            or type(end) is not int
            or not isinstance(anchor_text, str)
            or not anchor_text
            or not 0 <= start < end <= len(text)
            or start < previous_end
            or text[start:end] != anchor_text
            or text.count(anchor_text) != 1
            or (start, end, anchor_text) in seen
        ):
            return False
        previous_end = end
        seen.add((start, end, anchor_text))
    return True


def classify_result(
    probe: Probe, raw: RawProcessResult, input_schema: Any
) -> dict[str, Any]:
    counts = _event_counts()
    usage = _zero_usage()
    usage_observed = False
    message = b""
    error_class = "none"
    classification = "other_fail_closed"
    events: list[Any] = []

    if raw.spawn_failed:
        classification = "transport_spawn"
    elif raw.timed_out:
        classification = "timeout"
    elif raw.overflowed:
        classification = "other_fail_closed"
    else:
        parse_failed = False
        for line in raw.stdout.splitlines():
            if not line:
                continue
            try:
                events.append(strict_json(line))
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                parse_failed = True
                break
        if not parse_failed:
            for event in events:
                if not isinstance(event, dict) or not isinstance(
                    event.get("type"), str
                ):
                    counts["unknown"] += 1
                    continue
                key = event["type"].replace(".", "_")
                if event["type"] in KNOWN_EVENTS:
                    counts[key] += 1
                else:
                    counts["unknown"] += 1
        error_class, provider_rejected = _provider_error_class(events)
        if error_class == "invalid_json_schema":
            classification = "schema_unsupported"
        elif provider_rejected:
            classification = "provider_request_rejected"
        elif raw.returncode is not None and raw.returncode < 0:
            classification = "signal_exit"
        elif raw.returncode not in (None, 0):
            classification = "process_exit"
        elif not raw.stdout:
            classification = "empty_stdout"
        elif parse_failed:
            classification = "invalid_jsonl"
        elif counts["unknown"]:
            classification = "unknown_event"
        else:
            messages: list[str] = []
            lifecycle_ok = (
                counts["thread_started"] == 1
                and counts["turn_started"] == 1
                and counts["turn_completed"] == 1
                and counts["turn_failed"] == 0
                and counts["error"] == 0
            )
            for event in events:
                if not isinstance(event, dict) or event.get("type") != "item.completed":
                    continue
                item = event.get("item")
                if (
                    isinstance(item, dict)
                    and item.get("type") == "agent_message"
                    and isinstance(item.get("text"), str)
                ):
                    messages.append(item["text"])
            for event in events:
                if isinstance(event, dict) and event.get("type") == "turn.completed":
                    candidate = _closed_usage(event.get("usage"))
                    if candidate is not None:
                        usage = candidate
                        usage_observed = True
            if not lifecycle_ok or len(messages) != 1:
                classification = "missing_completed_message"
            else:
                message = messages[0].encode("utf-8")
                try:
                    value = strict_json(message)
                    errors = list(Draft202012Validator(input_schema).iter_errors(value))
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                    errors = [object()]
                    value = None
                if errors:
                    classification = "schema_invalid"
                elif not _semantic_capsule(value, probe):
                    classification = "semantic_invalid"
                else:
                    classification = "valid_completed"

    exit_code = (
        raw.returncode if raw.returncode is not None and raw.returncode >= 0 else None
    )
    child_signal = (
        -raw.returncode if raw.returncode is not None and raw.returncode < 0 else None
    )
    return {
        "probe_id": probe.probe_id,
        "classification": classification,
        "exit_code": exit_code,
        "signal": child_signal,
        "request_bytes": len(probe.request),
        "request_sha256": sha256_bytes(probe.request),
        "stdout_bytes": raw.stdout_bytes,
        "stdout_sha256": raw.stdout_sha256,
        "stderr_bytes": raw.stderr_bytes,
        "stderr_sha256": raw.stderr_sha256,
        "completed_message_bytes": len(message),
        "completed_message_sha256": sha256_bytes(message),
        "event_type_counts": counts,
        "usage_observed": usage_observed,
        "usage": usage,
        "error_class": error_class,
    }


def _load_closed_authority() -> tuple[dict[str, Any], bytes, bytes]:
    authority_raw = AUTHORITY_PATH.read_bytes()
    record_schema_raw = RECORD_SCHEMA_PATH.read_bytes()
    program_authority_raw = PROGRAM_AUTHORITY_PATH.read_bytes()
    authority = strict_json(authority_raw)
    record_schema = strict_json(record_schema_raw)
    Draft202012Validator.check_schema(record_schema)
    expected = authority.get("record_schema")
    if expected != {
        "path": "evals/ae-sq2/d0/diagnostic-schema.json",
        "sha256": sha256_bytes(record_schema_raw),
    }:
        raise DiagnosticError("diagnostic record schema authority is not exact")
    if authority.get("execution", {}).get("live_usage_approval") != APPROVAL:
        raise DiagnosticError("diagnostic approval authority drifted")
    if authority.get("parent_program_authority") != {
        "path": "evals/ae-sq2/program-authority.json",
        "sha256": sha256_bytes(program_authority_raw),
    }:
        raise DiagnosticError("parent program authority binding drifted")
    fixed = probes()
    expected_probes = [
        {
            "probe_id": probe.probe_id,
            "slot_id": probe.slot_id,
            "request_bytes": len(probe.request),
            "request_sha256": sha256_bytes(probe.request),
        }
        for probe in fixed
    ]
    execution = authority.get("execution", {})
    if (
        authority.get("scope")
        != {
            "live_call_count": CALLS,
            "synthetic_task_only": True,
            "corpus_access_permitted": False,
            "candidate_change_permitted": False,
            "persistent_raw_material_permitted": False,
        }
        or execution.get("model") != MODEL
        or execution.get("reasoning_effort") != REASONING
        or execution.get("timeout_seconds_per_call") != TIMEOUT_SECONDS
        or execution.get("private_tmpdir")
        != "fresh-empty-owner-only-0700-under-isolated-home-per-call"
        or execution.get("shared_tmpdir_forwarded") is not False
        or execution.get("max_request_bytes") != MAX_REQUEST_BYTES
        or execution.get("max_stdout_bytes") != MAX_STDOUT_BYTES
        or execution.get("max_stderr_bytes") != MAX_STDERR_BYTES
        or execution.get("cli") != {"version": CLI_VERSION, "sha256": CLI_SHA256}
        or authority.get("fixed_probes") != expected_probes
        or tuple(authority.get("classification_precedence", ()))
        != (
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
        or tuple(authority.get("known_event_types", ())) != KNOWN_EVENTS
        or tuple(authority.get("redacted_error_classes", ()))
        != (
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
        or authority.get("input_schema_profiles", {}).get("ae_sq1_reproduction")
        != {"path": SQ1_SCHEMA_PATH, "sha256": SQ1_SCHEMA_SHA256}
        or authority.get("one_shot_custody")
        != {
            "directory": CUSTODY_DIRECTORY,
            "location": "git-common-dir",
            "directory_mode": "0700",
            "state_file": "state.json",
            "state_file_mode": "0600",
            "atomic_claim": "O_CREAT|O_EXCL-before-any-child-spawn",
            "binding_roles": [
                "parent_program_authority_sha256",
                "diagnostic_authority_sha256",
                "diagnostic_schema_sha256",
                "input_schema_sha256",
                "cli_sha256",
            ],
            "existing_state_route": "fail-closed-no-child-spawn",
            "interruption_after_claim_route": "terminal-invalid-or-durable-claimed-no-reuse",
            "dry_run_claims_state": False,
        }
    ):
        raise DiagnosticError("diagnostic execution authority drifted")
    return authority, authority_raw, record_schema_raw


def _validate_record_semantics(record: Mapping[str, Any], mode: str) -> None:
    calls = record["calls"]
    counters = record["classification_counts"]
    if tuple(counters) != CLASSIFICATIONS:
        raise DiagnosticError("classification counter order drifted")
    if any(
        type(value) is not int or not 0 <= value <= CALLS for value in counters.values()
    ):
        raise DiagnosticError("classification counter is not closed")
    if mode == "dry_run":
        if calls or record["calls_started"] != 0 or record["calls_completed"] != 0:
            raise DiagnosticError("dry run attempted a diagnostic call")
        if sum(counters.values()) != 0:
            raise DiagnosticError("dry run has nonzero classification counters")
        return
    if (
        len(calls) != CALLS
        or record["calls_started"] != CALLS
        or not 0 <= record["calls_completed"] <= CALLS
        or tuple(call["probe_id"] for call in calls) != PROBE_IDS
        or sum(counters.values()) != CALLS
    ):
        raise DiagnosticError("live D0 is not one exact four-probe unit")
    observed_counts = _classification_counts()
    for call in calls:
        observed_counts[call["classification"]] += 1
    if observed_counts != counters:
        raise DiagnosticError("aggregate classification counters disagree with calls")


def _record(
    *,
    mode: str,
    authority_raw: bytes,
    record_schema_raw: bytes,
    input_schema_info: Mapping[str, Any],
    cli: Mapping[str, str],
    calls: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    classification_counts = _classification_counts()
    usage = _zero_usage()
    for call in calls:
        classification_counts[call["classification"]] += 1
        for key in USAGE_KEYS:
            usage[key] += call["usage"][key]
    # A completed D0 call means the child process returned an exit status or
    # signal after bounded collection. It does not mean a valid model output.
    live_completed = sum(
        1
        for call in calls
        if call["exit_code"] is not None or call["signal"] is not None
    )
    record: dict[str, Any] = {
        "diagnostic_id": "AE-SQ2-D0-2026-08-12-01",
        "mode": mode,
        "status": "ready" if mode == "dry_run" else "completed",
        "claim_ceiling": "four-call-synthetic-handshake-diagnostic-only",
        "authority_sha256": sha256_bytes(authority_raw),
        "diagnostic_schema_sha256": sha256_bytes(record_schema_raw),
        "input_schema": dict(input_schema_info),
        "cli": dict(cli),
        "model": MODEL,
        "reasoning_effort": REASONING,
        "calls_started": len(calls),
        "calls_completed": live_completed,
        "classification_counts": classification_counts,
        "usage": usage,
        "calls": list(calls),
        "aggregate_sha256": sha256_bytes(canonical_json(list(calls))),
    }
    record["record_sha256"] = sha256_bytes(canonical_json(record))
    return record


def run_diagnostic(
    *,
    mode: str,
    usage_approval: str | None = None,
    schema_path: Path,
    schema_document: Any,
    schema_info: Mapping[str, Any],
    cli: Mapping[str, str],
    invoke: Callable[
        [Probe, Mapping[str, str], Path], RawProcessResult
    ] = _invoke_probe,
    custody_root: Path = ROOT,
    claim: Callable[[Path, Mapping[str, str]], CustodyClaim] = _claim_d0,
    finalize: Callable[..., None] = _finalize_d0_claim,
    after_claim: Callable[[CustodyClaim], None] | None = None,
) -> dict[str, Any]:
    if mode not in {"dry_run", "live"}:
        raise DiagnosticError("diagnostic mode is not closed")
    if (mode == "live" and usage_approval != APPROVAL) or (
        mode == "dry_run" and usage_approval is not None
    ):
        raise DiagnosticError("diagnostic usage approval is not exact")
    _, authority_raw, record_schema_raw = _load_closed_authority()
    fixed = probes()
    calls: list[Mapping[str, Any]] = []
    custody_claim: CustodyClaim | None = None
    if mode == "live":
        binding = _custody_binding(
            authority_raw=authority_raw,
            record_schema_raw=record_schema_raw,
            input_schema_info=schema_info,
            cli=cli,
        )
        custody_claim = claim(custody_root, binding)
    try:
        if custody_claim is not None and after_claim is not None:
            after_claim(custody_claim)
        if mode == "live":
            pending: list[Mapping[str, Any] | None] = [None] * CALLS
            with ThreadPoolExecutor(
                max_workers=CALLS, thread_name_prefix="ae-sq2-d0"
            ) as pool:
                futures = {
                    pool.submit(invoke, probe, cli, schema_path): index
                    for index, probe in enumerate(fixed)
                }
                for future in as_completed(futures):
                    index = futures[future]
                    probe = fixed[index]
                    try:
                        raw = future.result()
                    except Exception:
                        raw = _spawn_failure()
                    pending[index] = classify_result(probe, raw, schema_document)
            if any(call is None for call in pending):
                raise DiagnosticError("four-call diagnostic lost a fixed probe")
            calls = [call for call in pending if call is not None]
        record = _record(
            mode=mode,
            authority_raw=authority_raw,
            record_schema_raw=record_schema_raw,
            input_schema_info=schema_info,
            cli=cli,
            calls=calls,
        )
        _validate_record_semantics(record, mode)
        schema = strict_json(record_schema_raw)
        errors = sorted(
            Draft202012Validator(schema).iter_errors(record),
            key=lambda error: list(error.path),
        )
        if errors:
            raise DiagnosticError("diagnostic record violates its closed schema")
        if custody_claim is not None:
            finalize(
                custody_claim,
                status="completed",
                record_sha256=record["record_sha256"],
            )
        return record
    except BaseException:
        if custody_claim is not None:
            try:
                finalize(custody_claim, status="invalid", record_sha256=None)
            except Exception:
                pass
        raise


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--execute", action="store_true")
    parser.add_argument("--schema", required=True)
    parser.add_argument("--schema-sha256", required=True)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--usage-approval")
    arguments = parser.parse_args(argv)
    if arguments.execute and arguments.usage_approval != APPROVAL:
        parser.error(f"--execute requires exact --usage-approval {APPROVAL}")
    if arguments.dry_run and arguments.usage_approval is not None:
        parser.error("--dry-run forbids --usage-approval")
    return arguments


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_args(argv)
    try:
        schema_path, schema_info, schema_document = resolve_schema(
            arguments.schema, arguments.schema_sha256
        )
        cli = resolve_cli(arguments.codex)
        record = run_diagnostic(
            mode="live" if arguments.execute else "dry_run",
            usage_approval=arguments.usage_approval,
            schema_path=schema_path,
            schema_document=schema_document,
            schema_info=schema_info,
            cli=cli,
        )
    except DiagnosticError as error:
        print(f"AE-SQ2 D0 fail-closed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(record, ensure_ascii=False, allow_nan=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
