from __future__ import annotations

import copy
import concurrent.futures
import inspect
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from types import ModuleType
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_ae_sq3_aq as runner  # noqa: E402


USAGE = {"input_tokens": 3, "cached_input_tokens": 1, "output_tokens": 2}
TASK = "Alpha request"


def load_json(relative: str) -> tuple[dict, bytes]:
    raw = (ROOT / relative).read_bytes()
    return json.loads(raw), raw


PROVIDER_SCHEMA, PROVIDER_RAW = load_json(
    "evals/ae-sq3/f1/slec3-capsule-schema.json"
)
SEMANTIC_SCHEMA, SEMANTIC_RAW = load_json(
    "evals/ae-sq3/f1/slec3-semantic-capsule-schema.json"
)
RESULT_SCHEMA, _RESULT_RAW = load_json("evals/ae-sq3/f1/result-schema.json")
PREFLIGHT_SCHEMA, _PREFLIGHT_RAW = load_json(
    "evals/ae-sq3/f1/preflight-schema.json"
)


def capsule(slot_id: str = "s0") -> dict:
    return {
        "slot_id": slot_id,
        "local_need": "yes",
        "reference_need": "none",
        "anchors": [{"start": 0, "end": 5, "text": "Alpha"}],
    }


def capsule_raw(slot_id: str = "s0") -> bytes:
    return json.dumps(capsule(slot_id), separators=(",", ":")).encode()


def event_rows(message: bytes | None = None) -> list[dict]:
    if message is None:
        message = capsule_raw()
    return [
        {"type": "thread.started", "thread_id": "context-1"},
        {"type": "turn.started"},
        {
            "type": "item.completed",
            "item": {
                "id": "message-1",
                "type": "agent_message",
                "text": message.decode(),
            },
        },
        {"type": "turn.completed", "usage": USAGE},
    ]


def event_stream(rows: list[dict] | None = None) -> bytes:
    if rows is None:
        rows = event_rows()
    return b"\n".join(json.dumps(row, separators=(",", ":")).encode() for row in rows)


def prepare_f3_base(root: Path) -> None:
    (root / "evals/ae-sq3").mkdir(parents=True)


class CapturingResolver:
    calls: list[tuple] = []

    @classmethod
    def normalize_runtime_capsule(
        cls,
        task_text,
        expected_slot,
        ingress,
        authority_custody,
        semantic_schema_custody,
    ):
        cls.calls.append(
            (
                task_text,
                expected_slot,
                ingress,
                authority_custody,
                semantic_schema_custody,
            )
        )
        raw, digest = ingress
        if digest != runner.sha256_bytes(raw):
            raise ValueError("capsule digest mismatch")
        value = json.loads(raw)
        if task_text != TASK or value["slot_id"] != expected_slot:
            raise ValueError("capsule context mismatch")
        return {
            "slot_id": expected_slot,
            "local_need": value["local_need"],
            "reference_need": value["reference_need"],
        }

    @staticmethod
    def build_assessor_packet(task_text, condition, slot_id, authority):
        del authority
        return {
            "instruction": "assess",
            "task_text": task_text,
            "condition_id": condition,
            "slot_id": slot_id,
            "condition_slot_card": {"description": "d", "decision_scope": "s"},
            "anonymous_menu": [{"option_id": "core"}, {"option_id": "focused"}],
        }


AUTHORITY_CUSTODY = (b"authority", runner.sha256_bytes(b"authority"))
SEMANTIC_CUSTODY = (SEMANTIC_RAW, runner.sha256_bytes(SEMANTIC_RAW))
PROFILE = {
    "documents": {
        "capsule_schema": PROVIDER_SCHEMA,
        "semantic_capsule_schema": SEMANTIC_SCHEMA,
        "result_schema": RESULT_SCHEMA,
    },
    "trusted_json": {
        "candidate_authority": AUTHORITY_CUSTODY,
        "semantic_capsule_schema": SEMANTIC_CUSTODY,
    },
}


def parse(raw: bytes, *, slot_id: str = "s0") -> runner.InvocationOutcome:
    return runner.parse_events(
        raw,
        resolver=CapturingResolver,
        task_text=TASK,
        condition="reduced",
        slot_id=slot_id,
        profile=PROFILE,
    )


def outcome(slot_id: str = "s0", context: str | None = None) -> runner.InvocationOutcome:
    raw = capsule_raw(slot_id)
    return runner.InvocationOutcome(
        "confirmed",
        raw,
        runner.sha256_bytes(raw),
        {"slot_id": slot_id, "local_need": "yes", "reference_need": "none"},
        context or f"context-{slot_id}",
        {**USAGE, "total_tokens": 5},
    )


class FakeIndex:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def claim_execution(self, _binding):
        self.events.append("claim")
        return b"capability"

    def complete(self, _binding, _capability, _digest):
        self.events.append("complete")

    def invalidate(self, _binding, _capability, _digest):
        self.events.append("invalidate")


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        CapturingResolver.calls.clear()

    def test_parser_confirms_only_exact_completed_provider_and_local_capsule(self) -> None:
        parsed = parse(event_stream())
        self.assertEqual(parsed.lifecycle, "confirmed")
        self.assertEqual(parsed.context_id, "context-1")
        self.assertEqual(parsed.usage["total_tokens"], 5)
        self.assertEqual(parsed.capsule_raw, capsule_raw())
        self.assertEqual(len(CapturingResolver.calls), 1)
        task, slot, ingress, authority, semantic = CapturingResolver.calls[0]
        self.assertEqual((task, slot), (TASK, "s0"))
        self.assertEqual(ingress, (capsule_raw(), runner.sha256_bytes(capsule_raw())))
        self.assertEqual(authority, AUTHORITY_CUSTODY)
        self.assertEqual(semantic, SEMANTIC_CUSTODY)

    def test_lifecycle_none_confirmed_and_indeterminate_are_not_stdout_truthiness(self) -> None:
        cases: list[tuple[str, bytes, str]] = [
            ("empty", b"", "none"),
            ("nonempty-garbage", b"not-json", "none"),
            ("unknown-without-completion", b'{"type":"warning"}', "none"),
            (
                "malformed-with-completion",
                b"not-json\n" + json.dumps(event_rows()[-1]).encode(),
                "indeterminate",
            ),
        ]
        tool_rows = event_rows()
        tool_rows.insert(2, {"type": "tool.executed", "tool": "forbidden"})
        cases.append(("tool-with-completion", event_stream(tool_rows), "indeterminate"))
        extra_rows = event_rows()
        extra_rows.append({"type": "unexpected.after-completion"})
        cases.append(("extra-after-completion", event_stream(extra_rows), "indeterminate"))
        for label, raw, lifecycle in cases:
            with self.subTest(label=label), self.assertRaises(runner.CallFailure) as captured:
                parse(raw)
            self.assertEqual(captured.exception.lifecycle, lifecycle)

    def test_duplicate_malformed_and_semantically_invalid_capsules_fail_closed(self) -> None:
        duplicate = event_rows()
        duplicate.insert(3, copy.deepcopy(duplicate[2]))
        invalid_semantic = capsule()
        invalid_semantic["anchors"] = []
        invalid_raw = json.dumps(invalid_semantic, separators=(",", ":")).encode()
        for label, raw in (
            ("duplicate-message", event_stream(duplicate)),
            ("semantic-invalid", event_stream(event_rows(invalid_raw))),
        ):
            with self.subTest(label=label), self.assertRaises(runner.CallFailure) as captured:
                parse(raw)
            self.assertEqual(captured.exception.lifecycle, "indeterminate")

    def test_timeout_never_turns_arbitrary_stdout_into_observation(self) -> None:
        @contextmanager
        def isolated():
            with tempfile.TemporaryDirectory() as directory:
                yield {}, Path(directory)

        state = {
            "snapshot_root": ROOT,
            "profile": {
                **PROFILE,
                "bindings": {
                    "capsule_schema": {
                        "path": "evals/ae-sq3/f1/slec3-capsule-schema.json"
                    }
                },
            },
            "resolver": CapturingResolver,
        }
        error = subprocess.TimeoutExpired(
            cmd=["codex"], timeout=1, output=b"arbitrary-nonempty-stdout"
        )
        with (
            patch.object(runner, "isolated_child_environment", isolated),
            patch.object(runner, "child_argv", return_value=["codex"]),
            patch.object(runner.subprocess, "run", side_effect=error),
            self.assertRaises(runner.CallFailure) as captured,
        ):
            runner.invoke_one(
                {"task_text": TASK},
                state=state,
                cli={"path": "codex"},
                condition="reduced",
                slot_id="s0",
            )
        self.assertEqual(captured.exception.lifecycle, "none")

    def test_attempt_ledger_has_exact_phase_order_and_zero_retry(self) -> None:
        ledger = runner.AttemptLedger()
        with self.assertRaises(runner.RunnerError):
            ledger.before_call("batch")
        for slot in runner.SLOT_ORDER:
            ledger.before_call("canary")
            ledger.complete_call("canary", outcome(slot))
        with self.assertRaises(runner.RunnerError):
            ledger.before_call("canary")
        ledger.pass_canary()
        ledger.begin_batch()
        for index in range(runner.BATCH_CALLS):
            ledger.before_call("batch")
            ledger.complete_call("batch", outcome("s0", f"batch-{index}"))
        self.assertEqual(ledger.total_attempted, runner.HARD_CALL_CEILING)
        self.assertEqual(ledger.total_completed, runner.HARD_CALL_CEILING)
        with self.assertRaises(runner.RunnerError):
            ledger.before_call("batch")

    def test_four_calls_count_failures_once_and_never_retry(self) -> None:
        ledger = runner.AttemptLedger()
        invocations: list[str] = []

        def invoke(_packet, *, state, cli, condition, slot_id):
            del state, cli, condition
            invocations.append(slot_id)
            raise runner.CallFailure("rejected", "none")

        state = {"resolver": CapturingResolver, "profile": PROFILE}
        results = runner._four_calls(
            state,
            {"path": "codex"},
            ledger,
            phase="canary",
            task_text=TASK,
            condition="reduced",
            invoke=invoke,
        )
        self.assertEqual(invocations, list(runner.SLOT_ORDER))
        self.assertEqual(ledger.canary_attempted, 4)
        self.assertEqual(ledger.canary_completed, 0)
        self.assertTrue(all(isinstance(result, runner.CallFailure) for result in results))
        with self.assertRaises(runner.RunnerError):
            runner._four_calls(
                state,
                {"path": "codex"},
                ledger,
                phase="canary",
                task_text=TASK,
                condition="reduced",
                invoke=invoke,
            )
        self.assertEqual(invocations, list(runner.SLOT_ORDER))

    def test_claim_precedes_same_process_canary_and_conditional_batch(self) -> None:
        events: list[str] = []
        index = FakeIndex(events)
        snapshot = SimpleNamespace(close=lambda: events.append("close"))
        state = {"profile": {"documents": {"result_schema": RESULT_SCHEMA}}, "snapshot": snapshot}
        binding = {
            "corpus_manifest_sha256": "1" * 64,
            "f1_freeze_sha256": "2" * 64,
            "preflight_record_sha256": "3" * 64,
            "program_authority_sha256": "4" * 64,
            "run_manifest_sha256": "5" * 64,
        }
        public = {
            "program_id": runner.PROGRAM_ID,
            "candidate_id": runner.CANDIDATE_ID,
            "status": "PASS",
            "aggregate_digest": "a" * 64,
        }

        def canary(*_args, **_kwargs):
            events.append("canary")

        def batch(*_args, **_kwargs):
            events.append("batch")
            return public

        with (
            patch.object(runner, "prepare_execution", return_value=(state, {}, binding, index)),
            patch.object(
                runner, "_prepare_canary_packets", return_value=({}, {}, {}, {})
            ),
            patch.object(runner, "_perform_canary", side_effect=canary),
            patch.object(runner, "_perform_batch", side_effect=batch),
        ):
            self.assertEqual(
                runner.execute_batch(
                    root=ROOT,
                    run_commit="a" * 40,
                    preflight_commit="b" * 40,
                    codex="codex",
                ),
                public,
            )
        self.assertEqual(events, ["claim", "canary", "batch", "close", "complete"])

    def test_failed_canary_terminalizes_without_batch_or_second_attempt(self) -> None:
        events: list[str] = []
        index = FakeIndex(events)
        snapshot = SimpleNamespace(close=lambda: events.append("close"))
        state = {
            "profile": {"documents": {"result_schema": RESULT_SCHEMA}},
            "snapshot": snapshot,
        }
        binding = {key: f"{index_:064x}" for index_, key in enumerate((
            "corpus_manifest_sha256",
            "f1_freeze_sha256",
            "preflight_record_sha256",
            "program_authority_sha256",
            "run_manifest_sha256",
        ), start=1)}

        def canary(*_args, **_kwargs):
            events.append("canary")
            raise runner.CallFailure("invalid", "indeterminate")

        with (
            patch.object(runner, "prepare_execution", return_value=(state, {}, binding, index)),
            patch.object(
                runner, "_prepare_canary_packets", return_value=({}, {}, {}, {})
            ),
            patch.object(runner, "_perform_canary", side_effect=canary),
            patch.object(runner, "_perform_batch") as batch,
        ):
            result = runner.execute_batch(
                root=ROOT,
                run_commit="a" * 40,
                preflight_commit="b" * 40,
                codex="codex",
            )
        self.assertEqual(result["status"], "FAIL")
        batch.assert_not_called()
        self.assertEqual(events, ["claim", "canary", "close", "invalidate"])

    def test_canary_packet_failure_occurs_before_claim_or_child(self) -> None:
        events: list[str] = []
        index = FakeIndex(events)
        state = {
            "profile": {"documents": {"result_schema": RESULT_SCHEMA}},
            "snapshot": SimpleNamespace(close=lambda: events.append("close")),
        }
        binding = {
            key: f"{ordinal:064x}"
            for ordinal, key in enumerate(runner.BINDING_KEYS if hasattr(runner, "BINDING_KEYS") else (
                "corpus_manifest_sha256", "f1_freeze_sha256",
                "preflight_record_sha256", "program_authority_sha256",
                "run_manifest_sha256",
            ), start=1)
        }
        invoke = unittest.mock.Mock()
        with (
            patch.object(runner, "prepare_execution", return_value=(state, {}, binding, index)),
            patch.object(runner, "_prepare_canary_packets", side_effect=runner.PreflightError("packet prep")),
            self.assertRaises(runner.PreflightError),
        ):
            runner.execute_batch(
                root=ROOT, run_commit="a" * 40, preflight_commit="b" * 40,
                codex="codex", invoke=invoke,
            )
        self.assertEqual(events, ["close"])
        invoke.assert_not_called()

    def test_execution_cleanup_failure_never_terminalizes_claim(self) -> None:
        binding = {
            key: f"{ordinal:064x}"
            for ordinal, key in enumerate(
                (
                    "corpus_manifest_sha256", "f1_freeze_sha256",
                    "preflight_record_sha256", "program_authority_sha256",
                    "run_manifest_sha256",
                ), start=1
            )
        }
        public = {
            "program_id": runner.PROGRAM_ID,
            "candidate_id": runner.CANDIDATE_ID,
            "status": "PASS",
            "aggregate_digest": "a" * 64,
        }
        for label, canary_effect in (("success", None), ("failure", runner.CallFailure("bad", "none"))):
            events: list[str] = []
            index = FakeIndex(events)

            def cleanup() -> None:
                events.append("close")
                raise runner.RunnerError("cleanup failed")

            state = {
                "profile": {"documents": {"result_schema": RESULT_SCHEMA}},
                "snapshot": SimpleNamespace(close=cleanup),
            }
            with (
                self.subTest(label=label),
                patch.object(runner, "prepare_execution", return_value=(state, {}, binding, index)),
                patch.object(runner, "_prepare_canary_packets", return_value=({}, {}, {}, {})),
                patch.object(runner, "_perform_canary", side_effect=canary_effect),
                patch.object(runner, "_perform_batch", return_value=public),
                self.assertRaisesRegex(runner.RunnerError, "cleanup failed"),
            ):
                runner.execute_batch(
                    root=ROOT, run_commit="a" * 40,
                    preflight_commit="b" * 40, codex="codex",
                )
            self.assertEqual(events.count("claim"), 1)
            self.assertEqual(events.count("close"), 1)
            self.assertNotIn("complete", events)
            self.assertNotIn("invalidate", events)

    def test_public_projection_is_exact_ordered_and_custody_sensitive(self) -> None:
        state = {"profile": {"documents": {"result_schema": RESULT_SCHEMA}}}
        valid = {
            "program_id": runner.PROGRAM_ID,
            "candidate_id": runner.CANDIDATE_ID,
            "status": "PASS",
            "aggregate_digest": "a" * 64,
        }
        self.assertEqual(runner._validate_public_result(state, valid), valid)
        mutants = [
            {**valid, "raw": "forbidden"},
            {"candidate_id": valid["candidate_id"], "program_id": valid["program_id"], "status": "PASS", "aggregate_digest": "a" * 64},
            {**valid, "status": "pass"},
            {**valid, "aggregate_digest": "A" * 64},
        ]
        for mutant in mutants:
            with self.subTest(mutant=mutant), self.assertRaises(runner.RunnerError):
                runner._validate_public_result(state, mutant)

        profile = {
            "implementation_commit": "1" * 40,
            "implementation_tree": "2" * 40,
            "freeze_sha256": "3" * 64,
            "bindings": {
                role: {"sha256": f"{index:064x}"}
                for index, role in enumerate(
                    (
                        "runner",
                        "evaluator_schema",
                        "corpus_validator",
                        "resolver_and_local_semantic_validator",
                        "run_index",
                        "scorer",
                    ),
                    start=4,
                )
            },
        }
        kwargs = {
            "corpus_manifest_sha256": "a" * 64,
            "run_manifest_sha256": "b" * 64,
            "preflight_record_sha256": "c" * 64,
            "program_authority_sha256": "d" * 64,
        }
        with patch.object(runner, "_host_digest", return_value="e" * 64):
            first = runner._scorer_binding(profile, "f" * 64, **kwargs)
            second = runner._scorer_binding(
                profile,
                "f" * 64,
                **{**kwargs, "run_manifest_sha256": "0" * 64},
            )
        self.assertNotEqual(runner.digest(first), runner.digest(second))
        self.assertEqual(first["f1_freeze_sha256"], profile["freeze_sha256"])
        self.assertEqual(first["run_manifest_sha256"], "b" * 64)
        self.assertEqual(first["preflight_record_sha256"], "c" * 64)

    def test_f3_pass_constructor_requires_every_check_true(self) -> None:
        checks = {
            "exact_custody": True,
            "provider_subset_and_local_semantics": True,
            "recursive_schema_closure": True,
            "independent_two_by_twenty": True,
            "forty_unique_cases": True,
            "eighty_by_four_schedule": True,
            "formula_totality_and_global_and": True,
            "lifecycle_event_and_counter_closure": True,
            "zero_retry_and_aggregate_only": True,
            "zero_raw_persistence": True,
            "one_shot_state_unclaimed": True,
        }
        checks["lifecycle_event_and_counter_closure"] = False
        snapshot = SimpleNamespace(close=lambda: None)
        state = {
            "snapshot": snapshot,
            "profile": {
                "freeze_sha256": "1" * 64,
                "documents": {"preflight_schema": PREFLIGHT_SCHEMA},
            },
            "corpus_digest": "4" * 64,
            "corpus_manifest_sha256": "2" * 64,
            "run_manifest_sha256": "3" * 64,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_f3_base(root)
            with (
                patch.object(runner, "_load_base_state", return_value=state),
                patch.object(runner, "_f3_checks", return_value=checks),
                patch.object(runner, "git_show", return_value=b"authority"),
                self.assertRaises(runner.PreflightError),
            ):
                runner.build_f3_record(root=root, run_commit="a" * 40)

    def test_f3_success_is_persistent_and_nonreplayable(self) -> None:
        checks = {key: True for key in PREFLIGHT_SCHEMA["properties"]["checks"]["required"]}
        state = {
            "snapshot": SimpleNamespace(close=lambda: None),
            "profile": {"freeze_sha256": "1" * 64, "documents": {"preflight_schema": PREFLIGHT_SCHEMA}},
            "corpus_manifest_sha256": "2" * 64,
            "run_manifest_sha256": "3" * 64,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_f3_base(root)
            with (
                patch.object(runner, "_load_base_state", return_value=state) as load,
                patch.object(runner, "_f3_checks", return_value=checks),
                patch.object(runner, "git_show", return_value=b"authority"),
            ):
                record = runner.build_f3_record(root=root, run_commit="a" * 40)
                path = root / runner.F3_RECORD_PATH
                self.assertEqual(runner.canonical_json(record), path.read_bytes())
                self.assertEqual(0o600, path.stat().st_mode & 0o777)
                runner.validate_f3_record(record, PREFLIGHT_SCHEMA)
                with self.assertRaises(runner.PreflightError):
                    runner.build_f3_record(root=root, run_commit="a" * 40)
            load.assert_called_once_with(root, "a" * 40, reserved_f3=True)

    def test_f3_failure_and_crash_are_terminal(self) -> None:
        state = {
            "snapshot": SimpleNamespace(close=lambda: None),
            "profile": {"freeze_sha256": "1" * 64, "documents": {"preflight_schema": PREFLIGHT_SCHEMA}},
            "corpus_manifest_sha256": "2" * 64,
            "run_manifest_sha256": "3" * 64,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_f3_base(root)
            with (
                patch.object(runner, "_load_base_state", return_value=state),
                patch.object(runner, "_f3_checks", side_effect=runner.PreflightError("probe failed")),
                patch.object(runner, "git_show", return_value=b"authority"),
                self.assertRaises(runner.PreflightError),
            ):
                runner.build_f3_record(root=root, run_commit="a" * 40)
            failed = json.loads((root / runner.F3_RECORD_PATH).read_bytes())
            self.assertEqual("FAIL", failed["status"])
            self.assertFalse(any(failed["checks"].values()))
            runner.validate_f3_record(failed, PREFLIGHT_SCHEMA)
            with self.assertRaises(runner.PreflightError):
                runner.build_f3_record(root=root, run_commit="a" * 40)

    def test_f3_cleanup_failure_leaves_only_consumed_marker(self) -> None:
        checks = {key: True for key in PREFLIGHT_SCHEMA["properties"]["checks"]["required"]}
        close_calls = 0

        def cleanup() -> None:
            nonlocal close_calls
            close_calls += 1
            raise runner.RunnerError("snapshot cleanup failed")

        state = {
            "snapshot": SimpleNamespace(close=cleanup),
            "profile": {"freeze_sha256": "1" * 64, "documents": {"preflight_schema": PREFLIGHT_SCHEMA}},
            "corpus_manifest_sha256": "2" * 64,
            "run_manifest_sha256": "3" * 64,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_f3_base(root)
            with (
                patch.object(runner, "_load_base_state", return_value=state),
                patch.object(runner, "_f3_checks", return_value=checks),
                patch.object(runner, "git_show", return_value=b"authority"),
                self.assertRaisesRegex(runner.RunnerError, "snapshot cleanup failed"),
            ):
                runner.build_f3_record(root=root, run_commit="a" * 40)
            self.assertEqual(close_calls, 1)
            self.assertEqual(b"", (root / runner.F3_RECORD_PATH).read_bytes())
            with self.assertRaises(runner.PreflightError):
                runner.build_f3_record(root=root, run_commit="a" * 40)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_f3_base(root)
            with (
                patch.object(runner, "_load_base_state", side_effect=KeyboardInterrupt()),
                self.assertRaises(KeyboardInterrupt),
            ):
                runner.build_f3_record(root=root, run_commit="a" * 40)
            marker = root / runner.F3_RECORD_PATH
            self.assertEqual(b"", marker.read_bytes())
            with self.assertRaises(runner.PreflightError):
                runner.build_f3_record(root=root, run_commit="a" * 40)

    def test_f3_reservation_rejects_existing_unsafe_and_is_concurrent_one_shot(self) -> None:
        for kind in ("symlink", "hardlink", "wrong-mode", "noncanonical"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                prepare_f3_base(root)
                target = root / runner.F3_RECORD_PATH
                target.parent.mkdir(parents=True)
                os.chmod(target.parent, 0o700)
                source = root / "source"
                source.write_bytes(b"not-a-preflight")
                if kind == "symlink":
                    target.symlink_to(source)
                elif kind == "hardlink":
                    os.link(source, target)
                else:
                    target.write_bytes(b"{}" if kind == "noncanonical" else b"x")
                    if kind == "wrong-mode":
                        os.chmod(target, 0o666)
                with self.assertRaises(runner.PreflightError):
                    runner._reserve_f3_record(root)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_f3_base(root)

            def reserve() -> bool:
                try:
                    reservation = runner._reserve_f3_record(root)
                except runner.PreflightError:
                    return False
                os.close(reservation.descriptor)
                os.close(reservation.directory_descriptor)
                return True

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _value: reserve(), range(2)))
            self.assertEqual([False, True], sorted(results))

    def test_f3_directory_walk_rejects_unsafe_parent_and_ancestor_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_f3_base(root)
            f3 = root / "evals/ae-sq3/f3"
            f3.mkdir(mode=0o755)
            with self.assertRaises(runner.PreflightError):
                runner._reserve_f3_record(root)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_f3_base(root)
            os.chmod(root / "evals", 0o777)
            with self.assertRaises(runner.PreflightError):
                runner._reserve_f3_record(root)
            self.assertFalse((root / runner.F3_RECORD_PATH).exists())
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            external = Path(outside)
            (external / "ae-sq3").mkdir()
            (root / "evals").symlink_to(external, target_is_directory=True)
            with self.assertRaises(runner.PreflightError):
                runner._reserve_f3_record(root)
            self.assertFalse((external / "ae-sq3/f3/preflight.json").exists())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_f3_base(root)
            reservation = runner._reserve_f3_record(root)
            try:
                original = root / "evals/ae-sq3/f3"
                original.rename(root / "evals/ae-sq3/f3-moved")
                original.mkdir(mode=0o700)
                with self.assertRaises(runner.PreflightError):
                    runner._validate_f3_reservation(reservation)
                canonical_marker = original / Path(runner.F3_RECORD_PATH).name
                self.assertEqual(b"", canonical_marker.read_bytes())
                with self.assertRaises(runner.PreflightError):
                    runner._reserve_f3_record(root)
            finally:
                os.close(reservation.descriptor)
                os.close(reservation.directory_descriptor)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_f3_base(root)
            reservation = runner._reserve_f3_record(root)
            try:
                record = {"status": "FAIL"}
                raw = runner.canonical_json(record)
                temporary = runner._write_f3_temporary(
                    reservation, raw, label="test-terminal"
                )
                os.replace(
                    temporary,
                    Path(runner.F3_RECORD_PATH).name,
                    src_dir_fd=reservation.directory_descriptor,
                    dst_dir_fd=reservation.directory_descriptor,
                )
                original = root / "evals/ae-sq3/f3"
                original.rename(root / "evals/ae-sq3/f3-moved")
                original.mkdir(mode=0o700)
                with self.assertRaisesRegex(runner.PreflightError, "parent identity"):
                    runner._verify_f3_terminal(
                        reservation, raw, record, rollback=True
                    )
                self.assertEqual(
                    b"", (root / runner.F3_RECORD_PATH).read_bytes()
                )
                with self.assertRaises(runner.PreflightError):
                    runner._reserve_f3_record(root)
            finally:
                os.close(reservation.descriptor)
                os.close(reservation.directory_descriptor)

    def test_f3_terminal_replace_performs_post_write_canonical_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_f3_base(root)
            reservation = runner._reserve_f3_record(root)
            try:
                with (
                    patch.object(runner, "strict_json", return_value={"drift": True}),
                    self.assertRaisesRegex(runner.PreflightError, "post-replace custody"),
                ):
                    runner._replace_f3_record(
                        reservation,
                        {"status": "PASS"},
                        rollback_record={"status": "FAIL"},
                    )
                self.assertEqual(
                    runner.canonical_json({"status": "FAIL"}),
                    (root / runner.F3_RECORD_PATH).read_bytes(),
                )
            finally:
                os.close(reservation.descriptor)
                os.close(reservation.directory_descriptor)

    def test_f3_full_pass_postverify_failure_rolls_back_to_canonical_fail(self) -> None:
        checks = {key: True for key in PREFLIGHT_SCHEMA["properties"]["checks"]["required"]}
        state = {
            "snapshot": SimpleNamespace(close=lambda: None),
            "profile": {"freeze_sha256": "1" * 64, "documents": {"preflight_schema": PREFLIGHT_SCHEMA}},
            "corpus_manifest_sha256": "2" * 64,
            "run_manifest_sha256": "3" * 64,
        }
        original_verify = runner._verify_f3_terminal

        def verify(*args, rollback=False, **kwargs):
            if not rollback:
                raise runner.PreflightError("injected PASS postverify failure")
            return original_verify(*args, rollback=rollback, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_f3_base(root)
            with (
                patch.object(runner, "_load_base_state", return_value=state),
                patch.object(runner, "_f3_checks", return_value=checks),
                patch.object(runner, "git_show", return_value=b"authority"),
                patch.object(runner, "_verify_f3_terminal", side_effect=verify),
                self.assertRaisesRegex(runner.PreflightError, "injected PASS"),
            ):
                runner.build_f3_record(root=root, run_commit="a" * 40)
            record = json.loads((root / runner.F3_RECORD_PATH).read_bytes())
            self.assertEqual("FAIL", record["status"])
            runner.validate_f3_record(record, PREFLIGHT_SCHEMA)
            with self.assertRaises(runner.PreflightError):
                runner.build_f3_record(root=root, run_commit="a" * 40)

    def test_committed_f3_pass_is_exactly_cross_bound_and_conjunctive(self) -> None:
        checks = {
            "exact_custody": True,
            "provider_subset_and_local_semantics": True,
            "recursive_schema_closure": True,
            "independent_two_by_twenty": True,
            "forty_unique_cases": True,
            "eighty_by_four_schedule": True,
            "formula_totality_and_global_and": True,
            "lifecycle_event_and_counter_closure": True,
            "zero_retry_and_aggregate_only": True,
            "zero_raw_persistence": True,
            "one_shot_state_unclaimed": True,
        }
        authority_raw = b"authority"
        state = {
            "root": ROOT,
            "commit": "9" * 40,
            "profile": {
                "freeze_sha256": "1" * 64,
                "documents": {"preflight_schema": PREFLIGHT_SCHEMA},
            },
            "corpus_digest": "4" * 64,
            "corpus_manifest_sha256": "2" * 64,
            "run_manifest_sha256": "3" * 64,
        }
        bindings = {
            "program_authority_sha256": runner.sha256_bytes(authority_raw),
            "f1_freeze_sha256": "1" * 64,
            "corpus_manifest_sha256": "2" * 64,
            "run_manifest_sha256": "3" * 64,
        }

        def record_for(current_checks, current_bindings=bindings):
            value = {
                "schema_version": "ae-sq3-preflight-v1",
                "program_id": runner.PROGRAM_ID,
                "candidate_id": runner.CANDIDATE_ID,
                "phase": "SQ3-F3",
                "attempt": 1,
                "model_calls": 0,
                "status": "PASS",
                "bindings": copy.deepcopy(current_bindings),
                "checks": copy.deepcopy(current_checks),
            }
            value["aggregate_sha256"] = runner.digest(value)
            return value

        valid = record_for(checks)

        def git_result(_root, args, *, text=False):
            del _root, text
            if args[:2] == ["rev-list", "--parents"]:
                return SimpleNamespace(
                    returncode=0, stdout=f"{'a' * 40} {state['commit']}\n"
                )
            if args and args[0] == "diff-tree":
                return SimpleNamespace(returncode=0, stdout=f"{runner.F3_RECORD_PATH}\n")
            raise AssertionError(args)

        def show(_root, _commit, path):
            if path == runner.F3_RECORD_PATH:
                return runner.canonical_json(valid)
            return authority_raw

        with (
            patch.object(runner, "git_identity", return_value=("a" * 40, "b" * 40)),
            patch.object(runner, "git_show", side_effect=show),
            patch.object(runner, "_git", side_effect=git_result),
            patch.object(runner, "_scorer_binding", return_value={}),
        ):
            runner._load_preflight_record(state, "a" * 40)

        for label, mutant in (
            ("false-check", record_for({**checks, "exact_custody": False})),
            (
                "cross-binding",
                record_for(checks, {**bindings, "run_manifest_sha256": "4" * 64}),
            ),
        ):
            def mutant_show(_root, _commit, path, value=mutant):
                if path == runner.F3_RECORD_PATH:
                    return runner.canonical_json(value)
                return authority_raw

            with (
                self.subTest(label=label),
                patch.object(runner, "git_identity", return_value=("a" * 40, "b" * 40)),
                patch.object(runner, "git_show", side_effect=mutant_show),
                patch.object(runner, "_git", side_effect=git_result),
                patch.object(runner, "_scorer_binding", return_value={}),
                self.assertRaises(runner.PreflightError),
            ):
                runner._load_preflight_record(copy.deepcopy(state), "a" * 40)

        canonical = runner.canonical_json(valid)
        noncanonical_rows = (
            b" " + canonical,
            json.dumps(valid, separators=(",", ":")).encode(),
            canonical.replace(
                b'"program_id":"AE-SQ3"',
                b'"program_id":"AE-SQ3","program_id":"AE-SQ3"',
                1,
            ),
            canonical.replace(b'"attempt":1', b'"attempt":NaN', 1),
        )
        for label, raw in zip(
            ("whitespace", "reordered", "duplicate", "nonfinite"),
            noncanonical_rows,
            strict=True,
        ):
            def raw_show(_root, _commit, path, value=raw):
                return value if path == runner.F3_RECORD_PATH else authority_raw

            with (
                self.subTest(label=label),
                patch.object(runner, "git_identity", return_value=("a" * 40, "b" * 40)),
                patch.object(runner, "git_show", side_effect=raw_show),
                patch.object(runner, "_git", side_effect=git_result),
                patch.object(runner, "_scorer_binding", return_value={}),
                self.assertRaises(runner.PreflightError),
            ):
                runner._load_preflight_record(copy.deepcopy(state), "a" * 40)

    def test_child_environment_is_private_minimal_and_erased(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / "source"
            codex_home.mkdir()
            auth = codex_home / "auth.json"
            auth.write_text('{"token":"fixture-only"}', encoding="utf-8")
            os.chmod(auth, 0o600)
            with patch.dict(
                os.environ,
                {
                    "CODEX_HOME": str(codex_home),
                    "TMPDIR": str(Path(directory) / "parent-tmp"),
                    "AE_SQ3_SECRET_SENTINEL": "must-not-inherit",
                },
                clear=False,
            ):
                with runner.isolated_child_environment() as (environment, cwd):
                    call_root = cwd.parent
                    self.assertEqual(call_root.stat().st_mode & 0o777, 0o700)
                    self.assertEqual(cwd.stat().st_mode & 0o777, 0o700)
                    self.assertEqual(Path(environment["TMPDIR"]).stat().st_mode & 0o777, 0o700)
                    self.assertEqual(environment["HOME"], environment["CODEX_HOME"])
                    self.assertNotEqual(environment["TMPDIR"], os.environ["TMPDIR"])
                    self.assertNotIn("AE_SQ3_SECRET_SENTINEL", environment)
                    copied_auth = Path(environment["CODEX_HOME"]) / "auth.json"
                    self.assertEqual(copied_auth.stat().st_mode & 0o777, 0o600)
                    (Path(environment["TMPDIR"]) / "raw-output").write_text(
                        "forbidden", encoding="utf-8"
                    )
                self.assertFalse(call_root.exists())
            self.assertEqual(auth.read_text(encoding="utf-8"), '{"token":"fixture-only"}')

    def test_runtime_snapshot_is_private_single_link_read_only_and_erased(self) -> None:
        snapshot = runner.RuntimeSnapshot()
        raw = b"frozen"
        binding = {
            "commit": "a" * 40,
            "tree": "b" * 40,
            "path": "inputs/value.json",
            "blob": "c" * 40,
            "sha256": runner.sha256_bytes(raw),
        }
        path = snapshot.add(binding, raw, label="fixture")
        self.assertEqual(snapshot.root.stat().st_mode & 0o777, 0o700)
        self.assertEqual(path.stat().st_mode & 0o777, 0o400)
        self.assertEqual(path.stat().st_nlink, 1)
        self.assertRegex(snapshot.seal(), r"^[0-9a-f]{64}$")
        root = snapshot.root
        snapshot.close()
        self.assertFalse(root.exists())

    def test_snapshot_close_removes_snapshot_owned_modules(self) -> None:
        snapshot = runner.RuntimeSnapshot()
        raw = b"VALUE = 7\n"
        binding = {
            "commit": "1" * 40,
            "tree": "2" * 40,
            "path": "scripts/f3_cleanup_probe.py",
            "blob": "3" * 40,
            "sha256": runner.sha256_bytes(raw),
        }
        name = "_ae_sq3_f3_cleanup_probe"
        try:
            snapshot.add(binding, raw, label="cleanup probe")
            snapshot.seal()
            module = runner._import_snapshot_module(snapshot, name, binding["path"])
            self.assertEqual(module.VALUE, 7)
            self.assertIn(name, sys.modules)
        finally:
            snapshot.close()
        self.assertNotIn(name, sys.modules)

    def test_capsule_observation_preserves_raw_custody_not_projection(self) -> None:
        raw = capsule_raw()
        observed = runner._capsule_observation(
            {
                "validator": SimpleNamespace(
                    digest=lambda _value: "b" * 64,
                    capsule_packet_digest=lambda **_kwargs: "c" * 64,
                ),
                "scorer_binding": {"bound": True},
                "schedule_digest": "d" * 64,
            },
            {"condition": "current", "case_id": "AE-SQ3-A-01"},
            {"task_text_nfc_sha256": "e" * 64},
            "s0",
            runner.InvocationOutcome(
                "confirmed",
                raw,
                runner.sha256_bytes(raw),
                {"slot_id": "s0", "local_need": "yes", "reference_need": "none"},
                "context-raw",
                {**USAGE, "total_tokens": 5},
            ),
        )
        self.assertEqual(raw, observed["capsule_raw"])
        self.assertEqual(runner.sha256_bytes(raw), observed["capsule_sha256"])
        self.assertNotIn("output", observed)
        self.assertNotIn("parse_status", observed)

    def test_frozen_preflight_schema_enforces_status_check_biconditional(self) -> None:
        checks = {key: True for key in PREFLIGHT_SCHEMA["properties"]["checks"]["required"]}
        value = {
            "schema_version": "ae-sq3-preflight-v1",
            "program_id": runner.PROGRAM_ID,
            "candidate_id": runner.CANDIDATE_ID,
            "phase": "SQ3-F3",
            "attempt": 1,
            "model_calls": 0,
            "status": "PASS",
            "bindings": {
                key: "1" * 64
                for key in PREFLIGHT_SCHEMA["properties"]["bindings"]["required"]
            },
            "checks": checks,
            "aggregate_sha256": "2" * 64,
        }
        validate = runner.Draft202012Validator(PREFLIGHT_SCHEMA)
        self.assertFalse(list(validate.iter_errors(value)))
        value["checks"]["exact_custody"] = False
        self.assertTrue(list(validate.iter_errors(value)))
        value["status"] = "FAIL"
        self.assertFalse(list(validate.iter_errors(value)))
        value["checks"]["exact_custody"] = True
        self.assertTrue(list(validate.iter_errors(value)))

    def test_corpus_manifest_is_closed_and_cross_bound_to_all_f2_inputs(self) -> None:
        run_schema, _ = load_json("evals/ae-sq3/f1/run-manifest-schema.json")
        implementation = {"commit": "1" * 40, "tree": "2" * 40}
        freeze = {
            **implementation,
            "path": "evals/ae-sq3/f1/repaired-freeze.json",
            "blob": "3" * 40,
            "sha256": "4" * 64,
        }
        contracts = {
            "corpus_contract_sha256": "5" * 64,
            "gates_sha256": "6" * 64,
            "metrics_sha256": "7" * 64,
            "evaluator_schema_sha256": "8" * 64,
        }
        authority = {
            "program_id": runner.PROGRAM_ID,
            "candidate_id": runner.CANDIDATE_ID,
            "candidate_commit": implementation["commit"],
            "candidate_tree": implementation["tree"],
            "f1_freeze_sha256": freeze["sha256"],
            **contracts,
        }
        split_documents = (
            {"split_id": "A", "author_id": "author-a", "authority": authority, "cases": [None] * 20},
            {"split_id": "B", "author_id": "author-b", "authority": authority, "cases": [None] * 20},
        )
        split_raws = tuple(runner.canonical_json(value) for value in split_documents)
        inventory = {
            "role": "historical_digest_inventory",
            "inventory_sha256": "9" * 64,
            "inventory_count": 768,
            "sources": [{} for _ in range(20)],
        }
        inventory_raw = runner.canonical_json(inventory)
        schedule = {"presentations": [{} for _ in range(80)]}
        schedule_raw = runner.canonical_json(schedule)
        schedule_sha = "a" * 64
        corpus_sha = "b" * 64
        profile = {
            "freeze_sha256": freeze["sha256"],
            "implementation_commit": implementation["commit"],
            "implementation_tree": implementation["tree"],
            "bindings": {
                "corpus_schema": {"sha256": contracts["corpus_contract_sha256"]},
                "historical_task_digests": {
                    "path": "evals/ae-sq3/f1/historical-task-digests.json"
                },
            },
        }
        document = {
            "schema_version": "ae-sq3-corpus-manifest-v1",
            "program_id": runner.PROGRAM_ID,
            "candidate_id": runner.CANDIDATE_ID,
            "corpus_id": "AE-SQ3-AQ-FRESH-V1",
            "f1_freeze": freeze,
            "implementation_freeze": implementation,
            "corpus_contract_sha256": contracts["corpus_contract_sha256"],
            "historical_inventory": {
                "path": "evals/ae-sq3/f1/historical-task-digests.json",
                "raw_sha256": runner.sha256_bytes(inventory_raw),
                "inventory_sha256": inventory["inventory_sha256"],
                "inventory_count": 768,
                "source_count": 20,
            },
            "splits": [
                {
                    "split_id": split_id,
                    "path": f"evals/ae-sq3/f2/split-{split_id.casefold()}.json",
                    "raw_sha256": runner.sha256_bytes(raw),
                    "content_sha256": runner.digest(value),
                    "case_count": 20,
                    "author_id": value["author_id"],
                }
                for split_id, raw, value in zip(
                    ("A", "B"), split_raws, split_documents, strict=True
                )
            ],
            "combined_corpus_sha256": corpus_sha,
            "schedule": {
                "path": "evals/ae-sq3/f2/schedule.json",
                "raw_sha256": runner.sha256_bytes(schedule_raw),
                "schedule_sha256": schedule_sha,
                "presentations": 80,
                "calls_per_presentation": 4,
            },
            "freshness": {
                "split_authors_distinct": True,
                "other_split_access": False,
                "predecessor_material_access": False,
                "diagnostic_or_live_result_access": False,
                "outcome_blind_at_authoring": True,
                "corpus_freeze_self_reference": False,
            },
        }
        validator = SimpleNamespace(
            digest=runner.digest,
            contract_digests=lambda: contracts,
        )

        def validate(value: dict) -> None:
            runner._validate_corpus_manifest_document(
                raw=runner.canonical_json(value),
                run_manifest={
                    "f1_freeze": freeze,
                    "implementation_freeze": implementation,
                },
                run_schema=run_schema,
                profile=profile,
                split_raws=split_raws,
                split_documents=split_documents,
                inventory_raw=inventory_raw,
                schedule_raw=schedule_raw,
                schedule_digest=schedule_sha,
                validation=SimpleNamespace(corpus_digest=corpus_sha),
                validator=validator,
            )

        validate(document)
        for label, mutate in (
            ("split_raw", lambda value: value["splits"][0].update(raw_sha256="0" * 64)),
            ("combined", lambda value: value.update(combined_corpus_sha256="0" * 64)),
            ("history", lambda value: value["historical_inventory"].update(raw_sha256="0" * 64)),
            ("schedule", lambda value: value["schedule"].update(raw_sha256="0" * 64)),
            ("f1", lambda value: value["f1_freeze"].update(sha256="0" * 64)),
        ):
            changed = copy.deepcopy(document)
            mutate(changed)
            with self.subTest(label=label), self.assertRaises(runner.PreflightError):
                validate(changed)

    def test_snapshot_import_rejects_preloaded_ambient_canonical_resolver(self) -> None:
        snapshot = runner.RuntimeSnapshot()
        raw = b"VALUE = 'frozen'\n"
        binding = {
            "commit": "a" * 40,
            "tree": "b" * 40,
            "path": "scripts/resolve_ae_sq3_slec.py",
            "blob": "c" * 40,
            "sha256": runner.sha256_bytes(raw),
        }
        snapshot.add(binding, raw, label="resolver")
        ambient = ModuleType("resolve_ae_sq3_slec")
        ambient.__file__ = str(ROOT / "scripts/resolve_ae_sq3_slec.py")
        try:
            with patch.dict(sys.modules, {"resolve_ae_sq3_slec": ambient}):
                with self.assertRaisesRegex(
                    runner.PreflightError, "ambient module poisoning"
                ):
                    runner._import_snapshot_module(
                        snapshot,
                        "resolve_ae_sq3_slec",
                        binding["path"],
                    )
                self.assertIs(sys.modules.get("resolve_ae_sq3_slec"), ambient)
        finally:
            snapshot.close()

    def test_base_loader_imports_canonical_resolver_before_validator_and_scorer(
        self,
    ) -> None:
        # This ordering is security-significant: validator/scorer imports may
        # themselves import the canonical resolver name.
        source = inspect.getsource(runner._load_base_state)
        resolver_position = source.index('"resolve_ae_sq3_slec"')
        validator_position = source.index('"validate_ae_sq3_corpus"')
        scorer_position = source.index('"_ae_sq3_scorer"')
        self.assertLess(resolver_position, validator_position)
        self.assertLess(validator_position, scorer_position)

    def test_f2b_run_commit_requires_exact_f2a_parent_and_manifest_only_delta(self) -> None:
        run_commit = "1" * 40
        run_tree = "2" * 40
        corpus_commit = "3" * 40
        corpus_tree = "4" * 40
        f1_commit = "5" * 40
        f1_tree = "6" * 40
        freeze_raw = b"freeze"
        freeze_binding = {
            "commit": f1_commit,
            "tree": f1_tree,
            "path": "evals/ae-sq3/f1/repaired-freeze.json",
            "blob": "7" * 40,
            "sha256": runner.sha256_bytes(freeze_raw),
        }
        manifest = {
            "f1_freeze": freeze_binding,
            "implementation_freeze": {"commit": "8" * 40, "tree": "9" * 40},
            "corpus_freeze": {"commit": corpus_commit, "tree": corpus_tree},
        }
        manifest_raw = runner.canonical_json(manifest)
        profile = {
            "freeze_commit": f1_commit,
            "freeze_path": freeze_binding["path"],
            "freeze_sha256": freeze_binding["sha256"],
            "implementation_commit": "8" * 40,
            "implementation_tree": "9" * 40,
            "documents": {"run_manifest_schema": {}},
        }
        checker = SimpleNamespace(
            load_verified_candidate=lambda *_args, **_kwargs: profile
        )

        def show(_root, commit, path):
            if commit == run_commit and path == runner.RUN_MANIFEST_PATH:
                return manifest_raw
            if commit == f1_commit and path == freeze_binding["path"]:
                return freeze_raw
            raise AssertionError((commit, path))

        def identity(_root, commit):
            if commit == run_commit:
                return run_commit, run_tree
            if commit == corpus_commit:
                return corpus_commit, corpus_tree
            raise AssertionError(commit)

        cases = (
            (
                "merge-parent",
                f"{run_commit} {corpus_commit} {'a' * 40}\n",
                f"{runner.RUN_MANIFEST_PATH}\n",
            ),
            (
                "extra-path",
                f"{run_commit} {corpus_commit}\n",
                f"{runner.RUN_MANIFEST_PATH}\nevals/ae-sq3/f2/extra.json\n",
            ),
            (
                "unrelated-parent",
                f"{run_commit} {'b' * 40}\n",
                f"{runner.RUN_MANIFEST_PATH}\n",
            ),
        )
        for label, parent_output, changed_output in cases:
            def command(_root, args, *, text=False):
                del _root, text
                if args[:2] == ["rev-list", "--parents"]:
                    return SimpleNamespace(returncode=0, stdout=parent_output)
                if args and args[0] == "diff-tree":
                    return SimpleNamespace(returncode=0, stdout=changed_output)
                raise AssertionError(args)

            with (
                self.subTest(label=label),
                patch.object(runner, "git_identity", side_effect=identity),
                patch.object(runner, "require_clean_exact_head"),
                patch.object(runner, "git_show", side_effect=show),
                patch.object(runner, "_load_checker", return_value=checker),
                patch.object(runner, "_git", side_effect=command),
                patch.object(
                    runner,
                    "_verify_sealed",
                    return_value=(freeze_raw, freeze_binding),
                ),
                self.assertRaises(runner.PreflightError),
            ):
                runner._load_base_state(ROOT, run_commit)

    def test_cli_has_no_standalone_canary_resume_or_retry_surface(self) -> None:
        for argv in (
            ["--canary", "--run-commit", "a" * 40],
            ["--resume", "--run-commit", "a" * 40],
            ["--execute", "--run-commit", "a" * 40, "--preflight-commit", "b" * 40],
        ):
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                runner.main(argv)
        with (
            patch.object(runner, "execute_batch", return_value={
                "program_id": runner.PROGRAM_ID,
                "candidate_id": runner.CANDIDATE_ID,
                "status": "PASS",
                "aggregate_digest": "a" * 64,
            }),
            patch("builtins.print"),
        ):
            self.assertEqual(
                runner.main(
                    [
                        "--execute",
                        "--run-commit",
                        "a" * 40,
                        "--preflight-commit",
                        "b" * 40,
                        "--usage-approval",
                        runner.USAGE_APPROVAL,
                    ]
                ),
                0,
            )


if __name__ == "__main__":
    unittest.main()
