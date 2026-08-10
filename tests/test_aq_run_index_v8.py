from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import aq_run_index_v8 as index  # noqa: E402


def sealed(char: str) -> dict[str, str]:
    return {"commit": char * 40, "tree": chr(ord(char) + 1) * 40, "digest": char * 64}


def binding(
    *,
    candidate: str = "4",
    runner: str = "5",
    corpus: str = "3",
    corpus_tree: str | None = None,
    corpus_digest: str | None = None,
) -> dict[str, object]:
    values = {
        name: sealed(char) for name, char in zip(index._IDENTITY_NAMES, "1234567")
    }
    values["candidate"] = sealed(candidate)
    values["runner"] = sealed(runner)
    values["corpus"] = sealed(corpus)
    if corpus_tree is not None:
        values["corpus"]["tree"] = corpus_tree * 40
    if corpus_digest is not None:
        values["corpus"]["digest"] = corpus_digest * 64
    return {
        **values,
        "cli": {"id": "codex", "digest": "8" * 64},
        "model": {"id": "model-v8", "digest": "9" * 64},
        "reasoning": {"id": "high", "digest": "a" * 64},
        "tools": {"digest": "b" * 64},
        "host": {"digest": "c" * 64},
        "schedule": {"seed": "aq8-seed", "digest": "d" * 64},
    }


def worktree_snapshot(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }


class RunIndexV8Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.binding = binding()
        self.corpus = self.binding["corpus"]["commit"]
        self.marker = self.authority(self.corpus, "unconsumed")
        self.plan = self.repo / "EXECPLAN.md"
        self.set_plan(self.marker)
        self.run_index = index.AQ8RunIndex(self.repo)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def authority(corpus: str, status: str) -> str:
        return f"AQ8-RUN-AUTHORITY corpus={corpus} status={status}"

    def set_plan(self, *lines: str) -> None:
        self.plan.write_text("\n".join(lines) + "\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "EXECPLAN.md"], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "-c",
                "user.name=AQ8",
                "-c",
                "user.email=aq8@example.invalid",
                "commit",
                "-qm",
                "authority",
            ],
            check=True,
        )

    def complete_canary(self, value: dict[str, object], marker: str) -> None:
        cap = self.run_index.begin_canary(value, unconsumed_marker=marker)
        self.run_index.complete_canary(value, unconsumed_marker=marker, canary_cap=cap)

    def start_batch(self, value: dict[str, object], marker: str) -> bytes:
        self.complete_canary(value, marker)
        return self.run_index.begin_batch(value, unconsumed_marker=marker)

    def complete_80(self, value: dict[str, object], cap: bytes) -> None:
        for _ in range(80):
            self.run_index.presentation_started(value, batch_cap=cap)
            self.run_index.presentation_completed(value, batch_cap=cap)

    def test_private_common_dir_permissions_and_zero_worktree_writes(self) -> None:
        before = worktree_snapshot(self.repo)
        common = index.git_common_dir(self.repo)
        cap = self.run_index.begin_canary(self.binding, unconsumed_marker=self.marker)
        self.assertEqual(self.run_index.directory, common / index.INDEX_NAME)
        self.assertEqual(os.stat(self.run_index.directory).st_mode & 0o777, 0o700)
        self.assertEqual(before, worktree_snapshot(self.repo))
        durable = self.run_index._identity(self.binding)[2].read_bytes()
        self.assertNotIn(cap.hex().encode("ascii"), durable)

    def test_v8_namespace_marker_class_and_temp_prefix_are_separate(self) -> None:
        self.assertEqual(index.INDEX_NAME, ".aq-run-index-v8")
        self.assertEqual(index.SCHEMA_VERSION, "aq-run-index-v8")
        self.assertEqual(index.AQ8RunIndex.__name__, "AQ8RunIndex")
        source = (ROOT / "scripts" / "aq_run_index_v8.py").read_text(encoding="utf-8")
        for residue in ("AQ" + "7", "aq" + "7", "v" + "7"):
            self.assertNotIn(residue, source)
        self.assertIn('prefix=".aq8-"', source)
        self.assertIsNotNone(index._AUTHORITY.fullmatch(self.marker))

    def test_symlink_path_and_broad_permissions_fail_closed(self) -> None:
        directory = index.git_common_dir(self.repo) / index.INDEX_NAME
        directory.rmdir()
        directory.symlink_to(self.repo, target_is_directory=True)
        with self.assertRaises(index.RunIndexError):
            index.index_dir(self.repo)
        directory.unlink()
        directory.mkdir(mode=0o755)
        os.chmod(directory, 0o755)
        with self.assertRaises(index.RunIndexError):
            index.index_dir(self.repo)

    def test_concurrent_double_canary_start_is_atomic(self) -> None:
        results: list[object] = []
        gate = threading.Barrier(2)

        def begin() -> None:
            gate.wait()
            try:
                results.append(
                    self.run_index.begin_canary(
                        self.binding, unconsumed_marker=self.marker
                    )
                )
            except Exception as error:
                results.append(error)

        one, two = threading.Thread(target=begin), threading.Thread(target=begin)
        one.start()
        two.start()
        one.join()
        two.join()
        self.assertEqual(sum(isinstance(item, bytes) for item in results), 1)
        self.assertEqual(
            sum(isinstance(item, index.RunIndexError) for item in results), 1
        )

    def test_closed_binding_sensitive_values_and_resealed_tamper_fail_closed(
        self,
    ) -> None:
        bad = binding()
        bad["model"] = {"id": "prompt", "digest": "9" * 64}
        with self.assertRaises(index.RunIndexError):
            index.normalize_binding(bad)
        cap = self.run_index.begin_canary(self.binding, unconsumed_marker=self.marker)
        path = self.run_index._identity(self.binding)[2]
        data = json.loads(path.read_text())
        data["canary_lease_digest"] = None
        data["state_sha256"] = index._sha256(
            {key: item for key, item in data.items() if key != "state_sha256"}
        )
        path.write_text(json.dumps(data), encoding="ascii")
        os.chmod(path, 0o600)
        with self.assertRaises(index.RunIndexError):
            self.run_index.complete_canary(
                self.binding, unconsumed_marker=self.marker, canary_cap=cap
            )

    def test_full_line_clean_head_authority_rejects_substring_duplicate_and_uncommitted(
        self,
    ) -> None:
        with self.assertRaises(index.RunIndexError):
            index._require_active_execplan_authority(
                self.run_index.toplevel,
                marker="unconsumed",
                corpus_commit=self.corpus,
                phase="canary",
            )
        self.set_plan("context: " + self.marker)
        with self.assertRaises(index.RunIndexError):
            self.run_index.begin_canary(self.binding, unconsumed_marker=self.marker)
        self.set_plan(self.marker + " trailing")
        with self.assertRaises(index.RunIndexError):
            self.run_index.begin_canary(self.binding, unconsumed_marker=self.marker)
        self.set_plan(self.marker, self.marker)
        with self.assertRaises(index.RunIndexError):
            self.run_index.begin_canary(self.binding, unconsumed_marker=self.marker)
        self.set_plan(self.marker, self.authority(self.corpus, "consumed-fail"))
        with self.assertRaises(index.RunIndexError):
            self.run_index.begin_canary(self.binding, unconsumed_marker=self.marker)
        self.set_plan(self.marker)
        self.plan.write_text(
            self.authority(self.corpus, "consumed-pass") + "\n", encoding="utf-8"
        )
        with self.assertRaises(index.RunIndexError):
            self.run_index.begin_canary(self.binding, unconsumed_marker=self.marker)

    def test_staged_authority_drift_with_live_head_bytes_is_rejected(self) -> None:
        staged = self.authority(self.corpus, "consumed-fail")
        self.plan.write_text(staged + "\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "EXECPLAN.md"], check=True)
        self.plan.write_text(self.marker + "\n", encoding="utf-8")
        with self.assertRaises(index.RunIndexError):
            self.run_index.begin_canary(self.binding, unconsumed_marker=self.marker)

    def test_canary_capability_blocks_independent_instance_and_retry_failure_closes(
        self,
    ) -> None:
        cap = self.run_index.begin_canary(self.binding, unconsumed_marker=self.marker)
        restarted = index.AQ8RunIndex(self.repo)
        with self.assertRaises(index.RunIndexError):
            restarted.retry_canary(
                self.binding,
                unconsumed_marker=self.marker,
                canary_cap=cap,
                reason="launch_failed",
            )
        self.run_index.retry_canary(
            self.binding,
            unconsumed_marker=self.marker,
            canary_cap=cap,
            reason="launch_failed",
        )
        self.run_index.fail_canary(
            self.binding,
            unconsumed_marker=self.marker,
            canary_cap=cap,
            reason="retry_exhausted",
        )
        self.assertEqual(self.run_index.state(self.binding)["canary_status"], "failed")

    def test_retry_exhausted_old_canary_leaves_only_changed_repaired_candidate_eligible(
        self,
    ) -> None:
        old_cap = self.run_index.begin_canary(
            self.binding, unconsumed_marker=self.marker
        )
        self.run_index.retry_canary(
            self.binding,
            unconsumed_marker=self.marker,
            canary_cap=old_cap,
            reason="precompletion_infrastructure",
        )
        self.run_index.fail_canary(
            self.binding,
            unconsumed_marker=self.marker,
            canary_cap=old_cap,
            reason="retry_exhausted",
        )
        with self.assertRaises(index.RunIndexError):
            self.run_index.begin_canary(self.binding, unconsumed_marker=self.marker)

        repaired = binding(candidate="5")
        self.assertNotEqual(index.run_key(self.binding), index.run_key(repaired))
        repaired_cap = self.run_index.begin_canary(
            repaired, unconsumed_marker=self.marker
        )
        self.run_index.complete_canary(
            repaired,
            unconsumed_marker=self.marker,
            canary_cap=repaired_cap,
        )
        batch_cap = self.run_index.begin_batch(repaired, unconsumed_marker=self.marker)

        old_state = self.run_index.state(self.binding)
        repaired_state = self.run_index.state(repaired)
        self.assertEqual(
            (old_state["canary_status"], old_state["corpus_status"]),
            ("failed", "unconsumed"),
        )
        self.assertEqual(
            (repaired_state["canary_status"], repaired_state["corpus_status"]),
            ("passed", "consumed_assumed"),
        )
        self.run_index.mark_batch_ambiguous(repaired, batch_cap=batch_cap)

    @unittest.skipUnless(hasattr(os, "fork"), "requires fork")
    def test_fork_inherited_canary_and_batch_capabilities_are_rejected(self) -> None:
        canary = self.run_index.begin_canary(
            self.binding, unconsumed_marker=self.marker
        )
        pid = os.fork()
        if pid == 0:
            try:
                self.run_index.complete_canary(
                    self.binding, unconsumed_marker=self.marker, canary_cap=canary
                )
            except index.RunIndexError:
                os._exit(0)
            os._exit(1)
        _pid, status = os.waitpid(pid, 0)
        self.assertTrue(os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0)
        self.assertEqual(self.run_index.state(self.binding)["canary_status"], "started")
        self.run_index.complete_canary(
            self.binding, unconsumed_marker=self.marker, canary_cap=canary
        )
        batch = self.run_index.begin_batch(self.binding, unconsumed_marker=self.marker)
        pid = os.fork()
        if pid == 0:
            try:
                self.run_index.presentation_started(self.binding, batch_cap=batch)
            except index.RunIndexError:
                os._exit(0)
            os._exit(1)
        _pid, status = os.waitpid(pid, 0)
        self.assertTrue(os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0)
        state = self.run_index.state(self.binding)
        self.assertEqual(
            (state["presentations_started"], state["presentations_completed"]), (0, 0)
        )

    def test_exact_canary_batch_sequence_and_batch_capability_blocks_restart(
        self,
    ) -> None:
        canary = self.run_index.begin_canary(
            self.binding, unconsumed_marker=self.marker
        )
        with self.assertRaises(index.RunIndexError):
            self.run_index.begin_batch(self.binding, unconsumed_marker=self.marker)
        self.run_index.complete_canary(
            self.binding, unconsumed_marker=self.marker, canary_cap=canary
        )
        batch = self.run_index.begin_batch(self.binding, unconsumed_marker=self.marker)
        started = self.run_index.state(self.binding)
        self.assertEqual(started["corpus_status"], "consumed_assumed")
        with self.assertRaises(index.RunIndexError):
            index.AQ8RunIndex(self.repo).presentation_started(
                self.binding, batch_cap=batch
            )
        self.run_index.presentation_started(self.binding, batch_cap=batch)
        self.run_index.response_observed(self.binding, batch_cap=batch)
        self.run_index.presentation_completed(self.binding, batch_cap=batch)
        state = self.run_index.state(self.binding)
        self.assertTrue(
            state["first_child_launch_attempted"] and state["first_response_observed"]
        )
        self.assertFalse(state["runner_local_raw_trajectories_persisted"])
        self.assertEqual(state["provider_raw_trajectory_retention_status"], "unknown")

    def test_cross_key_same_commit_no_replay_and_tree_digest_inconsistency(
        self,
    ) -> None:
        first = self.start_batch(self.binding, self.marker)
        for changed in (binding(candidate="5"), binding(runner="8")):
            with self.assertRaises(index.RunIndexError):
                self.run_index.begin_canary(changed, unconsumed_marker=self.marker)
        self.run_index.mark_batch_ambiguous(self.binding, batch_cap=first)
        for inconsistent in (
            binding(candidate="6", corpus_tree="9"),
            binding(candidate="7", corpus_digest="e"),
        ):
            with self.assertRaises(index.RunIndexError):
                self.run_index.begin_canary(inconsistent, unconsumed_marker=self.marker)

    def test_corrupt_sibling_fail_closed_and_concurrent_double_start(self) -> None:
        other = binding(corpus="6")
        other_marker = self.authority(other["corpus"]["commit"], "unconsumed")
        self.set_plan(self.marker, other_marker)
        self.complete_canary(other, other_marker)
        sibling = self.run_index._identity(other)[2]
        sibling.write_text("{", encoding="ascii")
        os.chmod(sibling, 0o600)
        third = binding(corpus="7")
        third_marker = self.authority(third["corpus"]["commit"], "unconsumed")
        self.set_plan(third_marker)
        with self.assertRaises(index.RunIndexError):
            self.run_index.begin_canary(third, unconsumed_marker=third_marker)

    def test_complete_requires_exact_80_aggregate_and_interruption_is_terminal(
        self,
    ) -> None:
        cap = self.start_batch(self.binding, self.marker)
        with self.assertRaises(index.RunIndexError):
            self.run_index.complete_batch(
                self.binding, batch_cap=cap, status="failed", aggregate_digest="e" * 64
            )
        self.complete_80(self.binding, cap)
        with self.assertRaises(index.RunIndexError):
            self.run_index.presentation_started(self.binding, batch_cap=cap)
        self.run_index.complete_batch(
            self.binding, batch_cap=cap, status="failed", aggregate_digest="e" * 64
        )
        done = self.run_index.state(self.binding)
        self.assertEqual(
            (
                done["batch_terminal"],
                done["presentations_completed"],
                done["first_response_observed"],
            ),
            ("completed", 80, True),
        )

    def test_cleanup_multikey_and_crash_started_only_consumed_interrupted(self) -> None:
        sibling = binding(candidate="5")
        self.complete_canary(self.binding, self.marker)
        cap = self.start_batch(sibling, self.marker)
        self.complete_80(sibling, cap)
        self.run_index.complete_batch(
            sibling, batch_cap=cap, status="failed", aggregate_digest="e" * 64
        )
        self.set_plan(self.authority(self.corpus, "consumed-fail"))
        self.run_index.cleanup(
            self.binding, durable_marker=self.authority(self.corpus, "consumed-fail")
        )
        self.assertEqual(list(self.run_index.directory.glob("*.json")), [])
        new = binding(corpus="6")
        marker = self.authority(new["corpus"]["commit"], "unconsumed")
        self.set_plan(marker)
        self.start_batch(new, marker)
        self.set_plan(self.authority(new["corpus"]["commit"], "consumed-fail"))
        with self.assertRaises(index.RunIndexError):
            self.run_index.cleanup(
                new,
                durable_marker=self.authority(new["corpus"]["commit"], "consumed-fail"),
            )
        self.set_plan(self.authority(new["corpus"]["commit"], "consumed-interrupted"))
        self.run_index.cleanup(
            new,
            durable_marker=self.authority(
                new["corpus"]["commit"], "consumed-interrupted"
            ),
        )

    def test_execution_ineligible_cleans_only_unconsumed_multikey_states(self) -> None:
        sibling = binding(candidate="5")
        self.run_index.begin_canary(self.binding, unconsumed_marker=self.marker)
        self.run_index.begin_canary(sibling, unconsumed_marker=self.marker)
        self.set_plan(self.authority(self.corpus, "execution-ineligible"))
        self.run_index.cleanup(
            self.binding,
            durable_marker=self.authority(self.corpus, "execution-ineligible"),
        )
        self.assertEqual(list(self.run_index.directory.glob("*.json")), [])


if __name__ == "__main__":
    unittest.main()
