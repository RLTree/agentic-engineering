from __future__ import annotations

import json
import multiprocessing
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import ae_sq7_run_index as run_index  # noqa: E402


def binding(offset: int = 0) -> dict[str, str]:
    return {
        key: f"{offset + index + 1:064x}"
        for index, key in enumerate(run_index.BINDING_KEYS)
    }


def _claim_worker(repository: str, value: dict[str, str], gate, queue) -> None:
    gate.wait()
    try:
        run_index.AESQ7RunIndex(repository).claim(value)
    except run_index.RunIndexError:
        queue.put("rejected")
    else:
        queue.put("claimed")


def _crash_after_claim(repository: str, value: dict[str, str]) -> None:
    run_index.AESQ7RunIndex(repository).claim(value)
    os._exit(0)


def _fork_finalize(owner, value: dict[str, str], capability: bytes, queue) -> None:
    try:
        owner.complete(value, capability, "a" * 64)
    except run_index.RunIndexError:
        queue.put("rejected")
    else:
        queue.put("completed")


class AESQ7RunIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repository = Path(self.temporary.name) / "repo"
        self.repository.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repository)], check=True)
        self.binding = binding()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_read_only_unclaimed_check_does_not_create_namespace(self) -> None:
        path = run_index.state_path(self.repository)
        self.assertFalse(path.parent.exists())
        run_index.assert_unclaimed(self.repository)
        self.assertFalse(path.parent.exists())

    def test_atomic_claim_is_exact_private_and_globally_one_shot(self) -> None:
        owner = run_index.AESQ7RunIndex(self.repository)
        capability = owner.claim(self.binding)
        path = owner.path
        self.assertEqual(path.name, "state.json")
        self.assertEqual(path.parent.name, ".ae-sq7-one-shot")
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.stat().st_nlink, 1)
        raw = path.read_bytes()
        value = json.loads(raw)
        self.assertEqual(tuple(value), run_index.TOP_LEVEL_KEYS)
        self.assertEqual(tuple(value["binding"]), run_index.BINDING_KEYS)
        self.assertEqual(raw, run_index.canonical_json(value))
        self.assertEqual(value["status"], "claimed")
        self.assertIsNone(value["record_sha256"])
        self.assertEqual(len(capability), 32)

        with self.assertRaises(run_index.RunIndexError):
            run_index.AESQ7RunIndex(self.repository).claim(binding(20))
        with self.assertRaises(run_index.RunIndexError):
            owner.claim(self.binding)

    def test_terminal_replacement_is_closed_and_restart_cannot_reuse(self) -> None:
        owner = run_index.AESQ7RunIndex(self.repository)
        capability = owner.claim(self.binding)
        terminal = owner.complete(self.binding, capability, "a" * 64)
        self.assertEqual(terminal["status"], "completed")
        self.assertEqual(terminal["record_sha256"], "a" * 64)
        self.assertEqual(owner.state(self.binding), terminal)
        with self.assertRaises(run_index.RunIndexError):
            run_index.AESQ7RunIndex(self.repository).claim(self.binding)
        with self.assertRaises(run_index.RunIndexError):
            owner.invalidate(self.binding, capability, "b" * 64)

    def test_concurrent_claim_has_exactly_one_winner(self) -> None:
        context = multiprocessing.get_context("fork")
        gate = context.Event()
        queue = context.Queue()
        workers = [
            context.Process(
                target=_claim_worker,
                args=(str(self.repository), self.binding, gate, queue),
            )
            for _ in range(2)
        ]
        for worker in workers:
            worker.start()
        gate.set()
        for worker in workers:
            worker.join(10)
            self.assertEqual(worker.exitcode, 0)
        self.assertEqual(
            sorted(queue.get(timeout=2) for _ in workers), ["claimed", "rejected"]
        )
        state = run_index.AESQ7RunIndex(self.repository).state(self.binding)
        self.assertEqual(state["status"], "claimed")

    def test_crash_after_claim_is_durable_terminal_no_reuse(self) -> None:
        context = multiprocessing.get_context("fork")
        worker = context.Process(
            target=_crash_after_claim,
            args=(str(self.repository), self.binding),
        )
        worker.start()
        worker.join(10)
        self.assertEqual(worker.exitcode, 0)
        owner = run_index.AESQ7RunIndex(self.repository)
        self.assertEqual(owner.state(self.binding)["status"], "claimed")
        with self.assertRaises(run_index.RunIndexError):
            owner.claim(self.binding)

    def test_fork_cannot_use_parent_capability(self) -> None:
        context = multiprocessing.get_context("fork")
        owner = run_index.AESQ7RunIndex(self.repository)
        capability = owner.claim(self.binding)
        queue = context.Queue()
        worker = context.Process(
            target=_fork_finalize,
            args=(owner, self.binding, capability, queue),
        )
        worker.start()
        worker.join(10)
        self.assertEqual(worker.exitcode, 0)
        self.assertEqual(queue.get(timeout=2), "rejected")
        self.assertEqual(owner.state(self.binding)["status"], "claimed")

    def test_capability_is_process_instance_bound(self) -> None:
        owner = run_index.AESQ7RunIndex(self.repository)
        capability = owner.claim(self.binding)
        restarted = run_index.AESQ7RunIndex(self.repository)
        with self.assertRaises(run_index.RunIndexError):
            restarted.complete(self.binding, capability, "a" * 64)
        with self.assertRaises(run_index.RunIndexError):
            owner.complete(self.binding, b"wrong".ljust(32, b"0"), "a" * 64)
        self.assertEqual(owner.state(self.binding)["status"], "claimed")

    def test_recursive_state_mutations_fail_closed(self) -> None:
        owner = run_index.AESQ7RunIndex(self.repository)
        owner.claim(self.binding)
        valid = owner.state(self.binding)
        mutations: list[dict] = []

        for key in run_index.TOP_LEVEL_KEYS:
            changed = deepcopy(valid)
            del changed[key]
            mutations.append(changed)
        for key in run_index.BINDING_KEYS:
            changed = deepcopy(valid)
            del changed["binding"][key]
            mutations.append(changed)
        for path, value in (
            (("extra",), True),
            (("binding", "extra"), "0" * 64),
            (("program_id",), "AE-SQ2"),
            (("schema_version",), "other"),
            (("status",), "passed"),
            (("record_sha256",), "0" * 64),
            (("custody_key",), "0" * 64),
            (("state_sha256",), "0" * 64),
            (("binding", run_index.BINDING_KEYS[0]), "A" * 64),
        ):
            changed = deepcopy(valid)
            if len(path) == 1:
                changed[path[0]] = value
            else:
                changed[path[0]][path[1]] = value
            mutations.append(changed)

        reordered = {key: valid[key] for key in reversed(run_index.TOP_LEVEL_KEYS)}
        mutations.append(reordered)
        nested_reordered = deepcopy(valid)
        nested_reordered["binding"] = {
            key: valid["binding"][key] for key in reversed(run_index.BINDING_KEYS)
        }
        mutations.append(nested_reordered)

        for index, changed in enumerate(mutations):
            with (
                self.subTest(index=index),
                self.assertRaises(run_index.RunIndexError),
            ):
                run_index.validate_state(changed, self.binding)

    def test_noncanonical_duplicate_symlink_hardlink_and_mode_fail_closed(self) -> None:
        cases = ("newline", "duplicate", "hardlink", "mode", "symlink")
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as directory:
                    repository = Path(directory) / "repo"
                    repository.mkdir()
                    subprocess.run(["git", "init", "-q", str(repository)], check=True)
                    owner = run_index.AESQ7RunIndex(repository)
                    owner.claim(self.binding)
                    path = owner.path
                    if case == "newline":
                        path.write_bytes(path.read_bytes() + b"\n")
                    elif case == "duplicate":
                        raw = path.read_bytes()
                        path.write_bytes(raw[:-1] + b',"status":"claimed"}')
                    elif case == "hardlink":
                        os.link(path, path.with_name("alias"))
                    elif case == "mode":
                        os.chmod(path, 0o644)
                    else:
                        target = path.with_name("target")
                        path.replace(target)
                        path.symlink_to(target.name)
                    with self.assertRaises(run_index.RunIndexError):
                        owner.state(self.binding)

    def test_unsafe_namespace_entry_rejects_claim(self) -> None:
        path = run_index.state_path(self.repository)
        path.parent.mkdir(mode=0o700)
        (path.parent / "rogue").write_text("unsafe", encoding="utf-8")
        with self.assertRaises(run_index.RunIndexError):
            run_index.AESQ7RunIndex(self.repository).claim(self.binding)

    def test_terminal_replacement_failure_consumes_capability(self) -> None:
        owner = run_index.AESQ7RunIndex(self.repository)
        capability = owner.claim(self.binding)
        with (
            patch.object(run_index.os, "replace", side_effect=OSError("injected")),
            self.assertRaises(OSError),
        ):
            owner.complete(self.binding, capability, "a" * 64)
        self.assertEqual(owner.state(self.binding)["status"], "claimed")
        with self.assertRaises(run_index.RunIndexError):
            owner.complete(self.binding, capability, "a" * 64)

    def test_noncanonical_terminal_state_fails_closed(self) -> None:
        owner = run_index.AESQ7RunIndex(self.repository)
        capability = owner.claim(self.binding)
        owner.complete(self.binding, capability, "a" * 64)
        owner.path.write_bytes(owner.path.read_bytes() + b"\n")
        with self.assertRaises(run_index.RunIndexError):
            owner.state(self.binding)


if __name__ == "__main__":
    unittest.main()
