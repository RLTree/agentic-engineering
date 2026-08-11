from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import ae_sq1_run_index as index  # noqa: E402


def sealed(char: str, path: str) -> dict[str, str]:
    return {
        "commit": char * 40,
        "tree": chr(ord(char) + 1) * 40,
        "path": path,
        "blob": chr(ord(char) + 2) * 40,
        "sha256": char * 64,
    }


def binding(*, candidate: str = "2", corpus: str = "5") -> dict[str, object]:
    return {
        "program_id": "AE-SQ1",
        "candidate_manifest": sealed("1", "evals/ae-sq1/candidate-manifest.json"),
        "candidate_freeze": sealed(candidate, "evals/ae-sq1/slec1-authority.json"),
        "run_manifest": sealed("4", "evals/ae-sq1/aq/run-manifest.json"),
        "corpus": {
            "content_sha256": corpus * 64,
            "split_a": sealed(corpus, "evals/ae-sq1/aq/split-a.json"),
            "split_b": sealed("2", "evals/ae-sq1/aq/split-b.json"),
        },
        "runner": sealed("7", "scripts/run_ae_sq1_aq.py"),
        "cli": {"id": "codex-cli", "version": "codex-cli 0.147.0", "sha256": "8" * 64},
        "model": {"id": "gpt-5.5", "reasoning": "medium", "fallback": False},
        "schedule": {
            "seed": "AE-SQ1-test",
            "sha256": "9" * 64,
            "presentations": 80,
            "calls_per_presentation": 4,
        },
        "host": {"sha256": "a" * 64},
    }


USAGE = {
    "input_tokens": 2,
    "cached_input_tokens": 1,
    "output_tokens": 3,
    "total_tokens": 5,
}


class RunIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.binding = binding()
        self.value = index.AESQ1RunIndex(self.repo)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def pass_canary(self) -> None:
        capability = self.value.begin_canary(self.binding)
        for _ in range(4):
            self.value.canary_call_started(self.binding, capability)
            self.value.canary_observation(self.binding, capability)
            self.value.canary_call_completed(self.binding, capability, USAGE)
        self.value.complete_canary(self.binding, capability, "b" * 64)

    def test_closed_binding_usage_and_private_namespace(self) -> None:
        self.assertEqual(index.normalize_binding(self.binding)["program_id"], "AE-SQ1")
        wrong = dict(self.binding)
        wrong["program_id"] = "AQ8"
        with self.assertRaises(index.RunIndexError):
            index.normalize_binding(wrong)
        legacy = dict(self.binding)
        legacy["corpus"] = sealed("5", "evals/ae-sq1/aq/split-a.json")
        with self.assertRaises(index.RunIndexError):
            index.normalize_binding(legacy)
        for invalid in (
            {**USAGE, "input_tokens": True},
            {key: value for key, value in USAGE.items() if key != "total_tokens"},
            {**USAGE, "total_tokens": 99},
        ):
            with self.assertRaises(index.RunIndexError):
                index.normalize_usage(invalid)
        self.assertEqual(self.value.directory.name, ".ae-sq1-run-index")
        self.assertEqual(self.value.directory.stat().st_mode & 0o777, 0o700)

    def test_one_preobservation_retry_and_completed_work_blocks_retry(self) -> None:
        capability = self.value.begin_canary(self.binding)
        for _ in range(4):
            self.value.canary_call_started(self.binding, capability)
        self.value.retry_canary(self.binding, capability)
        with self.assertRaises(index.RunIndexError):
            self.value.retry_canary(self.binding, capability)

        for _ in range(4):
            self.value.canary_call_started(self.binding, capability)
            self.value.canary_observation(self.binding, capability)
            self.value.canary_call_completed(self.binding, capability, USAGE)
        self.value.complete_canary(self.binding, capability, "b" * 64)

        other = binding(candidate="3", corpus="6")
        other_capability = self.value.begin_canary(other)
        self.value.canary_call_started(other, other_capability)
        self.value.canary_observation(other, other_capability)
        with self.assertRaises(index.RunIndexError):
            self.value.retry_canary(other, other_capability)
        changed_after_observation = binding(candidate="4", corpus="6")
        with self.assertRaises(index.RunIndexError):
            self.value.begin_canary(changed_after_observation)

    def test_repaired_candidate_can_replace_only_a_zero_invocation_canary(self) -> None:
        old_capability = self.value.begin_canary(self.binding)
        repaired = binding(candidate="3", corpus="5")
        repaired_capability = self.value.begin_canary(repaired)
        with self.assertRaises(index.RunIndexError):
            self.value.canary_call_started(self.binding, old_capability)
        self.value.canary_call_started(repaired, repaired_capability)

        unchanged_candidate = binding(candidate="3", corpus="5")
        unchanged_candidate["runner"] = sealed("6", "scripts/run_ae_sq1_aq.py")
        with self.assertRaises(index.RunIndexError):
            self.value.begin_canary(unchanged_candidate)

    def test_exact_four_plus_320_and_durable_no_replay(self) -> None:
        self.pass_canary()
        capability = self.value.begin_batch(self.binding)
        for _ in range(80):
            self.value.presentation_started(self.binding, capability)
            for _slot in range(4):
                self.value.batch_call_started(self.binding, capability)
                self.value.batch_observation(self.binding, capability)
                self.value.batch_call_completed(self.binding, capability, USAGE)
            self.value.presentation_completed(self.binding, capability)
        with self.assertRaises(index.RunIndexError):
            self.value.batch_call_started(self.binding, capability)
        with self.assertRaises(index.RunIndexError):
            self.value.presentation_started(self.binding, capability)
        self.value.complete_batch(
            self.binding,
            capability,
            status="passed",
            aggregate_digest="c" * 64,
        )
        state = self.value.state(self.binding)
        self.assertEqual(state["terminal_marker"], "consumed-pass")
        self.assertEqual(state["batch_calls_completed"], 320)
        self.assertEqual(state["batch_usage"]["total_tokens"], 1600)
        restarted = index.AESQ1RunIndex(self.repo)
        with self.assertRaises(index.RunIndexError):
            restarted.begin_canary(self.binding)

    def test_corrupt_sibling_and_broadened_permissions_fail_closed(self) -> None:
        capability = self.value.begin_canary(self.binding)
        path = self.value._identity(self.binding)[2]
        data = json.loads(path.read_text(encoding="ascii"))
        data["canary_status"] = "passed"
        path.write_text(json.dumps(data), encoding="ascii")
        os.chmod(path, 0o600)
        with self.assertRaises(index.RunIndexError):
            self.value.complete_canary(self.binding, capability, "b" * 64)
        os.chmod(self.value.directory, 0o755)
        with self.assertRaises(index.RunIndexError):
            index.AESQ1RunIndex(self.repo)

    def test_state_content_must_be_canonical(self) -> None:
        self.value.begin_canary(self.binding)
        path = self.value._identity(self.binding)[2]
        raw = path.read_bytes()
        path.write_bytes(raw + b"\n")
        with self.assertRaises(index.RunIndexError):
            self.value.state(self.binding)

    def test_state_hardlinks_are_rejected(self) -> None:
        self.value.begin_canary(self.binding)
        path = self.value._identity(self.binding)[2]
        alias = path.with_name("alias.json")
        os.link(path, alias)
        with self.assertRaises(index.RunIndexError):
            self.value.state(self.binding)

    def test_state_fifos_are_rejected_without_blocking(self) -> None:
        self.value.begin_canary(self.binding)
        path = self.value._identity(self.binding)[2]
        path.unlink()
        os.mkfifo(path, 0o600)
        with self.assertRaises(index.RunIndexError):
            self.value.state(self.binding)

    def test_process_instance_mac_and_restart_cannot_reuse_active_lease(self) -> None:
        capability = self.value.begin_canary(self.binding)
        restarted = index.AESQ1RunIndex(self.repo)
        with self.assertRaises(index.RunIndexError):
            restarted.canary_call_started(self.binding, capability)

        key = self.value._identity(self.binding)[0]
        self.value._canary_caps[key] = (capability, b"tampered")
        with self.assertRaises(index.RunIndexError):
            self.value.canary_call_started(self.binding, capability)

    def test_restart_cannot_reopen_a_persisted_canary_pass(self) -> None:
        self.pass_canary()
        restarted = index.AESQ1RunIndex(self.repo)
        with self.assertRaises(index.RunIndexError):
            restarted.begin_batch(self.binding)

    def test_same_corpus_content_binding_cannot_replay(self) -> None:
        self.value.begin_canary(self.binding)
        changed = binding(candidate="3", corpus="5")
        changed["corpus"]["split_a"]["sha256"] = "6" * 64
        with self.assertRaises(index.RunIndexError):
            self.value.begin_canary(changed)

    def test_same_content_repackage_cannot_replay_under_new_git_identity(self) -> None:
        self.value.begin_canary(self.binding)
        repackaged = binding(candidate="3", corpus="5")
        repackaged["corpus"]["split_a"]["commit"] = "a" * 40
        repackaged["corpus"]["split_a"]["tree"] = "b" * 40
        repackaged["corpus"]["split_a"]["blob"] = "c" * 40
        repackaged["corpus"]["split_b"]["commit"] = "d" * 40
        with self.assertRaises(index.RunIndexError):
            self.value.begin_canary(repackaged)


if __name__ == "__main__":
    unittest.main()
