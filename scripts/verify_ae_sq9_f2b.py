#!/usr/bin/env python3
"""One-shot clean-interpreter verifier for the AE-SQ9 F2B production loader.

The launcher claims durable state before spawning the child.  The child loads
the exact checkout's runner by path, invokes its real ``_load_base_state``, and
returns an aggregate-only verdict.  It never serializes corpus or task data.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

sys.dont_write_bytecode = True

PROGRAM_ID = "AE-SQ9"
CANDIDATE_ID = "AE-SQ9-SLEC-9"
SCHEMA_VERSION = "ae-sq9-f2b-loader-gate-v1"
STATE_VERSION = "ae-sq9-f2g-state-v1"
VERIFIER_PATH = "scripts/verify_ae_sq9_f2b.py"
RUNNER_PATH = "scripts/run_ae_sq9_aq.py"
F2G_RECEIPT_PATH = "evals/ae-sq9/f2/f2b-loader-gate.json"
F2G_SCHEMA_PATH = "evals/ae-sq9/f1/f2b-loader-gate-schema.json"
STATE_RELATIVE = ".ae-sq9-f2g/state.json"
FIXTURE_TEST = (
    "test_ae_sq9_author_template.AuthorTemplateTests."
    "test_real_ephemeral_f1g_to_f2b_graph_passes_production_loader"
)
NESTED_FIXTURE_ENV = "AE_SQ9_CLEAN_GATE_NESTED_SHA256"
HEX40 = frozenset("0123456789abcdef")


class GateError(RuntimeError):
    """The clean-child gate is already consumed or failed closed."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fixture_contract() -> dict[str, Any]:
    """Closed contract frozen into F1G before any production corpus exists."""
    return {
        "child_isolation": "new-python-process",
        "durable_state": STATE_RELATIVE,
        "fixture_test": FIXTURE_TEST,
        "model_calls": 0,
        "positive_parent_resolver_preimported": "PASS",
        "production_loader": "run_ae_sq9_aq:_load_base_state",
        "red_child_resolver_preloaded": "REJECTED",
        "red_same_process_validation_then_loader": "REJECTED",
        "terminal_states": ["claimed", "completed", "invalid"],
        "verifier_path": VERIFIER_PATH,
    }


def execute_fixture_test(root: Path, fixture_test_sha256: str) -> dict[str, Any]:
    """Run the production-real synthetic Git fixture in a clean interpreter."""
    expected_sha = _sha256_value(fixture_test_sha256)
    if os.environ.get(NESTED_FIXTURE_ENV) == expected_sha:
        return {"fixture_status": "PASS", "fixture_test_sha256": expected_sha}
    environment = os.environ.copy()
    environment[NESTED_FIXTURE_ENV] = expected_sha
    result = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", FIXTURE_TEST],
        cwd=root / "tests",
        env=environment,
        check=False,
        capture_output=True,
        timeout=180,
    )
    if result.returncode:
        raise GateError("production-real clean-process F2B fixture failed")
    return {"fixture_status": "PASS", "fixture_test_sha256": expected_sha}


def _commit(value: str) -> str:
    if len(value) != 40 or any(character not in HEX40 for character in value):
        raise GateError("run commit is not a full lowercase Git object id")
    return value


def _sha256_value(value: str) -> str:
    if len(value) != 64 or any(character not in HEX40 for character in value):
        raise GateError("SHA-256 custody value is invalid")
    return value


def _strict_document(raw: bytes) -> dict[str, Any]:
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GateError("child emitted invalid JSON") from error
    if not isinstance(document, dict) or canonical_json(document) != raw:
        raise GateError("child emitted noncanonical JSON")
    return document


def _json_object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GateError(f"{label} is invalid JSON") from error
    if not isinstance(document, dict):
        raise GateError(f"{label} is not a JSON object")
    return document


def _git_common_dir(root: Path) -> Path:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise GateError("Git common directory is unavailable")
    path = Path(result.stdout.strip())
    if not path.is_absolute() or path.is_symlink():
        raise GateError("Git common directory is unsafe")
    return path


def _write_exclusive(path: Path, document: Mapping[str, Any]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        os.write(descriptor, canonical_json(document))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _state_directory(root: Path) -> Path:
    directory = _git_common_dir(root) / ".ae-sq9-f2g"
    try:
        os.mkdir(directory, 0o700)
    except FileExistsError:
        pass
    info = directory.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise GateError("F2G state directory custody is unsafe")
    return directory


def _child_arguments(
    root: Path, run_commit: str, *, poison_resolver: bool = False
) -> list[str]:
    arguments = [
        sys.executable,
        "-B",
        str((root / VERIFIER_PATH).resolve()),
        "--child",
        "--root",
        str(root.resolve()),
        "--run-commit",
        _commit(run_commit),
    ]
    if poison_resolver:
        arguments.append("--poison-resolver")
    return arguments


def claim_state(root: Path, run_commit: str, verifier_sha256: str) -> Path:
    state_path = _state_directory(root) / "state.json"
    _write_exclusive(
        state_path,
        {
            "attempt": 1,
            "child_arguments": _child_arguments(root, run_commit),
            "child_executable_sha256": sha256(Path(sys.executable).read_bytes()),
            "run_commit": _commit(run_commit),
            "status": "claimed",
            "verifier_sha256": verifier_sha256,
            "version": STATE_VERSION,
        },
    )
    return state_path


def _replace_state(path: Path, document: Mapping[str, Any]) -> None:
    current = _strict_document(path.read_bytes())
    if current.get("status") != "claimed":
        raise GateError("F2G gate is not in the claimed state")
    info = path.stat(follow_symlinks=False)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise GateError("F2G state custody is unsafe")
    temporary = path.with_name("state.next")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, canonical_json(document))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)


def _mark_invalid(path: Path, error: str | None) -> None:
    """Terminalize a rejected child; a claimed state has no recovery route."""
    claimed = _strict_document(path.read_bytes())
    document: dict[str, Any] = {
        "attempt": 1,
        "child_arguments": claimed["child_arguments"],
        "child_executable_sha256": claimed["child_executable_sha256"],
        "run_commit": claimed["run_commit"],
        "status": "invalid",
        "verifier_sha256": claimed["verifier_sha256"],
        "version": STATE_VERSION,
    }
    document["error"] = error or "verification_rejected"
    _replace_state(path, document)
    if path.read_bytes() != canonical_json(document):
        raise GateError("F2G invalid state post-replace verification failed")


def _load_runner(root: Path):
    path = root / RUNNER_PATH
    specification = importlib.util.spec_from_file_location(
        "_ae_sq9_clean_child_runner", path
    )
    if specification is None or specification.loader is None:
        raise GateError("target-frozen runner is unavailable")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def child_verify(
    root: Path, run_commit: str, *, poison_resolver: bool = False
) -> dict[str, Any]:
    if poison_resolver:
        import types

        poison = types.ModuleType("resolve_ae_sq9_slec")
        poison.__file__ = str(root / "scripts/resolve_ae_sq9_slec.py")
        sys.modules["resolve_ae_sq9_slec"] = poison
    try:
        runner = _load_runner(root)
        state = runner._load_base_state(root, _commit(run_commit))
        snapshot = state.get("snapshot")
        if snapshot is not None:
            snapshot.close()
        return {"error": None, "status": "PASS"}
    except Exception as error:  # child boundary intentionally projects only class
        message = str(error)
        kind = (
            "ambient_module_poisoning"
            if "ambient module poisoning" in message
            else "loader_rejected"
        )
        return {"error": kind, "status": "REJECTED"}


def launch_child(
    root: Path, run_commit: str, *, poison_resolver: bool = False
) -> dict[str, Any]:
    command = _child_arguments(root, run_commit, poison_resolver=poison_resolver)
    result = subprocess.run(command, check=False, capture_output=True)
    if result.returncode not in {0, 1}:
        return {"error": "child_exit", "status": "REJECTED"}
    try:
        return _strict_document(result.stdout)
    except GateError:
        return {"error": "child_protocol", "status": "REJECTED"}


def build_receipt(
    *,
    run_commit: str,
    verifier: Mapping[str, str],
    parent_resolver_preimported: bool,
    child_resolver_preloaded: bool,
    outcome: Mapping[str, Any],
) -> dict[str, Any]:
    if outcome["status"] == "PASS" and (
        not parent_resolver_preimported or child_resolver_preloaded
    ):
        raise GateError("PASS requires contaminated parent and clean child")
    receipt: dict[str, Any] = {
        "attempt": 1,
        "candidate_id": CANDIDATE_ID,
        "child_resolver_preloaded": child_resolver_preloaded,
        "model_calls": 0,
        "parent_resolver_preimported": parent_resolver_preimported,
        "production_loader": "run_ae_sq9_aq:_load_base_state",
        "program_id": PROGRAM_ID,
        "run_commit": _commit(run_commit),
        "schema_version": SCHEMA_VERSION,
        "status": outcome["status"],
        "verifier": dict(verifier),
    }
    if outcome["status"] != "PASS":
        receipt["error"] = outcome.get("error", "loader_rejected")
    receipt["aggregate_sha256"] = sha256(canonical_json(receipt))
    return receipt


def _git(root: Path, *arguments: str, text: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=text,
    )
    if result.returncode:
        raise GateError("required Git custody is unavailable")
    return result.stdout


def verifier_binding(root: Path, run_commit: str) -> dict[str, str]:
    raw_manifest = _git(
        root,
        "show",
        f"{_commit(run_commit)}:evals/ae-sq9/f2/run-manifest.json",
    )
    assert isinstance(raw_manifest, bytes)
    manifest = _strict_document(raw_manifest)
    implementation = manifest.get("implementation_freeze")
    if not isinstance(implementation, dict):
        raise GateError("run manifest implementation binding is unavailable")
    commit = _commit(implementation.get("commit", ""))
    tree = _git(root, "rev-parse", f"{commit}^{{tree}}", text=True).strip()
    if tree != implementation.get("tree"):
        raise GateError("verifier implementation tree drift")
    raw = _git(root, "show", f"{commit}:{VERIFIER_PATH}")
    assert isinstance(raw, bytes)
    blob = _git(root, "rev-parse", f"{commit}:{VERIFIER_PATH}", text=True).strip()
    return {
        "blob": blob,
        "commit": commit,
        "path": VERIFIER_PATH,
        "sha256": sha256(raw),
        "tree": tree,
    }


def verify_once(
    root: Path, run_commit: str, *, parent_resolver_preimported: bool
) -> tuple[Path, dict[str, Any]]:
    """Consume the sole attempt, create F2G, then durably complete before output."""
    binding = verifier_binding(root, run_commit)
    state_path = claim_state(root, run_commit, binding["sha256"])
    outcome = launch_child(root, run_commit)
    receipt = build_receipt(
        run_commit=run_commit,
        verifier=binding,
        parent_resolver_preimported=parent_resolver_preimported,
        child_resolver_preloaded=False,
        outcome=outcome,
    )
    if outcome["status"] != "PASS":
        _mark_invalid(state_path, outcome.get("error"))
        return state_path, receipt
    raw = canonical_json(receipt)
    commit = _create_receipt_commit(root, run_commit, raw)
    _verify_committed_gate(root, state_path, commit, raw)
    claimed = _strict_document(state_path.read_bytes())
    completed = {
        "attempt": 1,
        "child_arguments": claimed["child_arguments"],
        "child_executable_sha256": claimed["child_executable_sha256"],
        "f2g_commit": _commit(commit),
        "receipt_sha256": sha256(raw),
        "run_commit": claimed["run_commit"],
        "status": "completed",
        "verifier_sha256": claimed["verifier_sha256"],
        "version": STATE_VERSION,
    }
    _replace_state(state_path, completed)
    if state_path.read_bytes() != canonical_json(completed):
        raise GateError("F2G completed state post-replace verification failed")
    return state_path, receipt


def _create_receipt_commit(root: Path, run_commit: str, raw: bytes) -> str:
    """Create an unreachable receipt-only child without touching checkout or refs."""
    with tempfile.TemporaryDirectory(prefix="ae-sq9-f2g-index-") as directory:
        environment = os.environ.copy()
        environment["GIT_INDEX_FILE"] = str(Path(directory) / "index")

        def command(*arguments: str, input_bytes: bytes | None = None) -> bytes:
            result = subprocess.run(
                ["git", "-C", str(root), *arguments],
                env=environment,
                input=input_bytes,
                check=False,
                capture_output=True,
            )
            if result.returncode:
                raise GateError("F2G receipt commit construction failed")
            return result.stdout.strip()

        command("read-tree", _commit(run_commit))
        blob = command("hash-object", "-w", "--stdin", input_bytes=raw).decode()
        command(
            "update-index",
            "--add",
            "--cacheinfo",
            f"100644,{blob},{F2G_RECEIPT_PATH}",
        )
        tree = command("write-tree").decode()
        return command(
            "commit-tree",
            tree,
            "-p",
            _commit(run_commit),
            input_bytes=b"AE-SQ9 F2G clean-child loader receipt\n",
        ).decode()


def _verify_committed_gate(
    root: Path, state_path: Path, f2g_commit: str, expected_raw: bytes
) -> None:
    """Verify the internally-created receipt child before durable completion."""
    commit = _commit(f2g_commit)
    state = _strict_document(state_path.read_bytes())
    if state.get("status") != "claimed":
        raise GateError("F2G gate is not in the claimed state")
    run_commit = _commit(state.get("run_commit", ""))
    parents = _git(root, "rev-list", "--parents", "-n", "1", commit, text=True).split()
    if parents != [commit, run_commit]:
        raise GateError("F2G is not the exact direct child of F2B")
    changed = _git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        run_commit,
        commit,
        text=True,
    ).splitlines()
    if changed != [F2G_RECEIPT_PATH]:
        raise GateError("F2G is not receipt-only")
    entry = _git(root, "ls-tree", commit, "--", F2G_RECEIPT_PATH, text=True).split()
    if len(entry) < 3 or entry[:2] != ["100644", "blob"]:
        raise GateError("F2G receipt is not a regular 100644 blob")
    raw = _git(root, "show", f"{commit}:{F2G_RECEIPT_PATH}")
    assert isinstance(raw, bytes)
    if raw != expected_raw:
        raise GateError("F2G committed receipt differs from child result")
    receipt = _strict_document(raw)
    unsigned = dict(receipt)
    aggregate = unsigned.pop("aggregate_sha256", None)
    if aggregate != sha256(canonical_json(unsigned)):
        raise GateError("F2G receipt aggregate mismatch")
    manifest_raw = _git(root, "show", f"{run_commit}:evals/ae-sq9/f2/run-manifest.json")
    assert isinstance(manifest_raw, bytes)
    manifest = _strict_document(manifest_raw)
    implementation = manifest.get("implementation_freeze")
    if not isinstance(implementation, dict):
        raise GateError("F2G implementation custody is unavailable")
    f1a = _commit(implementation.get("commit", ""))
    schema_raw = _git(root, "show", f"{f1a}:{F2G_SCHEMA_PATH}")
    assert isinstance(schema_raw, bytes)
    schema = _json_object(schema_raw, "F2G receipt schema")
    if list(Draft202012Validator(schema).iter_errors(receipt)):
        raise GateError("F2G receipt violates its frozen schema")
    if (
        receipt.get("status") != "PASS"
        or receipt.get("run_commit") != run_commit
        or receipt.get("verifier", {}).get("sha256") != state.get("verifier_sha256")
    ):
        raise GateError("F2G receipt custody drift")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run-commit", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--child", action="store_true")
    mode.add_argument("--verify", action="store_true")
    parser.add_argument("--poison-resolver", action="store_true")
    parser.add_argument("--parent-resolver-preimported", action="store_true")
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    if arguments.child:
        outcome = child_verify(
            root,
            arguments.run_commit,
            poison_resolver=arguments.poison_resolver,
        )
        sys.stdout.buffer.write(canonical_json(outcome))
        return 0 if outcome["status"] == "PASS" else 1
    _state_path, receipt = verify_once(
        root,
        arguments.run_commit,
        parent_resolver_preimported=arguments.parent_resolver_preimported,
    )
    sys.stdout.buffer.write(canonical_json(receipt))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
