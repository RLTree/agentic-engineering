from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_ae_sq9_f2b", ROOT / "scripts/verify_ae_sq9_f2b.py"
)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class CleanChildGateTests(unittest.TestCase):
    def test_receipt_is_closed_and_aggregate_bound(self) -> None:
        verifier = {
            "blob": "a" * 40,
            "commit": "b" * 40,
            "path": gate.VERIFIER_PATH,
            "sha256": "c" * 64,
            "tree": "d" * 40,
        }
        receipt = gate.build_receipt(
            run_commit="e" * 40,
            verifier=verifier,
            parent_resolver_preimported=True,
            child_resolver_preloaded=False,
            outcome={"status": "PASS"},
        )
        schema = json.loads(
            (ROOT / "evals/ae-sq9/f1/f2b-loader-gate-schema.json").read_text()
        )
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(receipt)), [])
        unsigned = dict(receipt)
        aggregate = unsigned.pop("aggregate_sha256")
        self.assertEqual(aggregate, gate.sha256(gate.canonical_json(unsigned)))
        with self.assertRaises(gate.GateError):
            gate.build_receipt(
                run_commit="e" * 40,
                verifier=verifier,
                parent_resolver_preimported=False,
                child_resolver_preloaded=False,
                outcome={"status": "PASS"},
            )

    def test_parent_import_does_not_contaminate_spawned_child_contract(self) -> None:
        with patch.object(gate.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = gate.canonical_json(
                {"error": None, "status": "PASS"}
            )
            result = gate.launch_child(ROOT, "a" * 40)
        self.assertEqual(result["status"], "PASS")
        command = run.call_args.args[0]
        self.assertIn("-B", command)
        self.assertIn("--child", command)

    def test_poison_and_protocol_fail_closed(self) -> None:
        with patch.object(gate.subprocess, "run") as run:
            run.return_value.returncode = 1
            run.return_value.stdout = gate.canonical_json(
                {"error": "ambient_module_poisoning", "status": "REJECTED"}
            )
            self.assertEqual(
                gate.launch_child(ROOT, "a" * 40, poison_resolver=True)["error"],
                "ambient_module_poisoning",
            )
            run.return_value.returncode = 0
            run.return_value.stdout = b"not-json"
            self.assertEqual(
                gate.launch_child(ROOT, "a" * 40)["error"], "child_protocol"
            )

    def test_state_is_exclusive_and_rejection_is_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            common = Path(directory) / "git-common"
            common.mkdir()
            with patch.object(gate, "_git_common_dir", return_value=common):
                state = gate.claim_state(ROOT, "a" * 40, "b" * 64)
                self.assertEqual(state.stat().st_mode & 0o777, 0o600)
                with self.assertRaises(FileExistsError):
                    gate.claim_state(ROOT, "a" * 40, "b" * 64)
                gate._mark_invalid(state, "loader_rejected")
                document = json.loads(state.read_text())
                self.assertEqual(document["status"], "invalid")
                self.assertEqual(document["error"], "loader_rejected")
                self.assertIn("child_arguments", document)
                self.assertIn("child_executable_sha256", document)
                with self.assertRaises(gate.GateError):
                    gate._mark_invalid(state, "second_attempt")

    def test_claimed_state_survives_child_crash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            common = Path(directory) / "git-common"
            common.mkdir()
            with patch.object(gate, "_git_common_dir", return_value=common):
                state = gate.claim_state(ROOT, "a" * 40, "b" * 64)
                self.assertEqual(json.loads(state.read_text())["status"], "claimed")
                self.assertTrue(state.exists())

    def test_unsafe_state_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            common = Path(directory) / "git-common"
            state_directory = common / ".ae-sq9-f2g"
            state_directory.mkdir(parents=True, mode=0o755)
            with patch.object(gate, "_git_common_dir", return_value=common):
                with self.assertRaisesRegex(gate.GateError, "directory custody"):
                    gate.claim_state(ROOT, "a" * 40, "b" * 64)

    def test_rejected_child_atomically_terminalizes_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            common = Path(directory) / "git-common"
            common.mkdir()
            binding = {
                "blob": "a" * 40,
                "commit": "b" * 40,
                "path": gate.VERIFIER_PATH,
                "sha256": "c" * 64,
                "tree": "d" * 40,
            }
            with (
                patch.object(gate, "_git_common_dir", return_value=common),
                patch.object(gate, "verifier_binding", return_value=binding),
                patch.object(
                    gate,
                    "launch_child",
                    return_value={
                        "error": "ambient_module_poisoning",
                        "status": "REJECTED",
                    },
                ),
            ):
                state, receipt = gate.verify_once(
                    ROOT,
                    "e" * 40,
                    parent_resolver_preimported=True,
                )
            self.assertEqual(receipt["status"], "REJECTED")
            self.assertEqual(json.loads(state.read_text())["status"], "invalid")
            with self.assertRaises(FileExistsError):
                with patch.object(gate, "_git_common_dir", return_value=common):
                    gate.claim_state(ROOT, "e" * 40, "c" * 64)

    def test_completion_recomputes_committed_receipt_and_topology(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            common = Path(directory) / "git-common"
            common.mkdir()
            verifier = {
                "blob": "1" * 40,
                "commit": "2" * 40,
                "path": gate.VERIFIER_PATH,
                "sha256": "3" * 64,
                "tree": "4" * 40,
            }
            receipt = gate.build_receipt(
                run_commit="a" * 40,
                verifier=verifier,
                parent_resolver_preimported=True,
                child_resolver_preloaded=False,
                outcome={"status": "PASS"},
            )
            receipt_raw = gate.canonical_json(receipt)
            schema_raw = (
                ROOT / "evals/ae-sq9/f1/f2b-loader-gate-schema.json"
            ).read_bytes()
            manifest_raw = gate.canonical_json(
                {"implementation_freeze": {"commit": "2" * 40, "tree": "4" * 40}}
            )

            def git_result(_root, *arguments, text=False):
                if arguments[:3] == ("rev-list", "--parents", "-n"):
                    return f"{'b' * 40} {'a' * 40}\n"
                if arguments[0] == "diff-tree":
                    return gate.F2G_RECEIPT_PATH + "\n"
                if arguments[0] == "ls-tree":
                    return f"100644 blob {'5' * 40}\t{gate.F2G_RECEIPT_PATH}\n"
                if arguments[-1] == f"{'b' * 40}:{gate.F2G_RECEIPT_PATH}":
                    return receipt_raw
                if arguments[-1] == f"{'a' * 40}:evals/ae-sq9/f2/run-manifest.json":
                    return manifest_raw
                if arguments[-1] == f"{'2' * 40}:{gate.F2G_SCHEMA_PATH}":
                    return schema_raw
                self.fail(arguments)

            with patch.object(gate, "_git_common_dir", return_value=common):
                state = gate.claim_state(ROOT, "a" * 40, "3" * 64)
                with patch.object(gate, "_git", side_effect=git_result):
                    gate._verify_committed_gate(ROOT, state, "b" * 40, receipt_raw)
                self.assertEqual(json.loads(state.read_text())["status"], "claimed")

            with tempfile.TemporaryDirectory() as second:
                second_common = Path(second) / "git-common"
                second_common.mkdir()
                with patch.object(gate, "_git_common_dir", return_value=second_common):
                    state = gate.claim_state(ROOT, "a" * 40, "3" * 64)
                    with patch.object(
                        gate,
                        "_git",
                        return_value=f"{'b' * 40} {'c' * 40}\n",
                    ):
                        with self.assertRaisesRegex(gate.GateError, "direct child"):
                            gate._verify_committed_gate(
                                ROOT, state, "b" * 40, receipt_raw
                            )

    def test_success_commits_and_verifies_receipt_before_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            common = Path(directory) / "git-common"
            common.mkdir()
            binding = {
                "blob": "1" * 40,
                "commit": "2" * 40,
                "path": gate.VERIFIER_PATH,
                "sha256": "3" * 64,
                "tree": "4" * 40,
            }
            with (
                patch.object(gate, "_git_common_dir", return_value=common),
                patch.object(gate, "verifier_binding", return_value=binding),
                patch.object(
                    gate,
                    "launch_child",
                    return_value={"error": None, "status": "PASS"},
                ),
                patch.object(
                    gate,
                    "_create_receipt_commit",
                    return_value="5" * 40,
                ) as create,
                patch.object(gate, "_verify_committed_gate") as verify,
            ):
                state, receipt = gate.verify_once(
                    ROOT,
                    "a" * 40,
                    parent_resolver_preimported=True,
                )
            durable = json.loads(state.read_text())
            self.assertEqual(durable["status"], "completed")
            self.assertEqual(durable["f2g_commit"], "5" * 40)
            self.assertEqual(
                durable["receipt_sha256"],
                gate.sha256(gate.canonical_json(receipt)),
            )
            create.assert_called_once_with(ROOT, "a" * 40, gate.canonical_json(receipt))
            verify.assert_called_once_with(
                ROOT,
                state,
                "5" * 40,
                gate.canonical_json(receipt),
            )

    def test_crash_after_receipt_commit_is_terminal_claimed(self) -> None:
        with tempfile.TemporaryDirectory() as second:
            common = Path(second) / "git-common"
            common.mkdir()
            binding = {
                "blob": "1" * 40,
                "commit": "2" * 40,
                "path": gate.VERIFIER_PATH,
                "sha256": "3" * 64,
                "tree": "4" * 40,
            }
            with (
                patch.object(gate, "_git_common_dir", return_value=common),
                patch.object(gate, "verifier_binding", return_value=binding),
                patch.object(
                    gate,
                    "launch_child",
                    return_value={"error": None, "status": "PASS"},
                ),
                patch.object(gate, "_create_receipt_commit", return_value="5" * 40),
                patch.object(
                    gate,
                    "_verify_committed_gate",
                    side_effect=gate.GateError("post-commit crash"),
                ),
            ):
                with self.assertRaisesRegex(gate.GateError, "post-commit crash"):
                    gate.verify_once(
                        ROOT,
                        "a" * 40,
                        parent_resolver_preimported=True,
                    )
            durable = json.loads((common / gate.STATE_RELATIVE).read_text())
            self.assertEqual(durable["status"], "claimed")
            self.assertNotIn("receipt_sha256", durable)
            self.assertNotIn("f2g_commit", durable)

    def test_no_external_completion_or_recovery_cli_exists(self) -> None:
        with self.assertRaises(SystemExit):
            gate.main(
                [
                    "--root",
                    str(ROOT),
                    "--run-commit",
                    "a" * 40,
                    "--complete",
                ]
            )


if __name__ == "__main__":
    unittest.main()
