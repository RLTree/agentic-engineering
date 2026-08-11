from __future__ import annotations

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_ae_sq1_aq as runner  # noqa: E402
import resolve_ae_sq1_slec as slec  # noqa: E402
import ae_sq1_run_index as run_index  # noqa: E402


USAGE = {"input_tokens": 3, "cached_input_tokens": 1, "output_tokens": 2}


class Resolver:
    @staticmethod
    def project_runtime_capsule(
        value,
        *,
        task_text,
        condition,
        slot_id,
        authority,
        reference_policy,
    ):
        del task_text, condition, authority, reference_policy
        if value != {"answer": "yes"}:
            raise ValueError("bad output")
        return {"slot_id": slot_id, "local_need": "yes", "reference_need": "focused"}

    @staticmethod
    def build_assessor_packet(*, task_text, condition, slot_id, authority):
        del authority
        return {
            "instruction": "assess only this capability",
            "task_text": task_text,
            "condition_id": condition,
            "slot_id": slot_id,
            "condition_slot_card": {
                "description": "bounded capability",
                "decision_scope": "local only",
            },
            "anonymous_menu": [{"option_id": "core"}],
        }


def event_stream(message: str = '{"answer":"yes"}', usage: dict | None = None) -> bytes:
    rows = (
        {"type": "thread.started", "thread_id": "unique-context"},
        {"type": "turn.started"},
        {
            "type": "item.completed",
            "item": {"id": "m", "type": "agent_message", "text": message},
        },
        {"type": "turn.completed", "usage": USAGE if usage is None else usage},
    )
    return b"\n".join(json.dumps(row).encode() for row in rows)


PROFILE = {
    "documents": {"candidate_authority": {}, "reference_policy": {}},
    "trusted_json": {"candidate_authority": (b"{}", runner.sha256_bytes(b"{}"))},
    "bindings": {"capsule_schema": {"path": "evals/ae-sq1/slec1-capsule-schema.json"}},
}


def trusted(path: Path) -> tuple[bytes, str]:
    raw = path.read_bytes()
    return raw, runner.sha256_bytes(raw)


def actual_parent_fixture() -> tuple[dict, str, list[tuple[bytes, str]], list[dict]]:
    authority = trusted(ROOT / "evals/ae-sq1/slec1-authority.json")
    policy = trusted(ROOT / "evals/ae-sq1/slec1-reference-policy.json")
    resolution_schema = trusted(ROOT / "evals/ae-sq1/slec1-resolution-schema.json")
    task = "Choose a bounded architecture for this reversible local implementation."
    raw = []
    projected = []
    for index, slot_id in enumerate(runner.SLOT_ORDER):
        local_need = "yes" if index == 0 else "no"
        reference_need = "focused" if index == 0 else "none"
        capsule_raw = runner._runtime_capsule_bytes(
            {
                "slot_id": slot_id,
                "local_need": local_need,
                "reference_need": reference_need,
                "anchors": [{"start": 0, "end": len(task), "text": task}],
            }
        )
        raw.append((capsule_raw, runner.sha256_bytes(capsule_raw)))
        projected.append(
            {
                "slot_id": slot_id,
                "local_need": local_need,
                "reference_need": reference_need,
            }
        )
    state = {
        "root": ROOT,
        "snapshot_root": ROOT,
        "resolver": slec,
        "profile": {
            "documents": {
                "candidate_authority": json.loads(authority[0]),
                "reference_policy": json.loads(policy[0]),
                "resolution_schema": json.loads(resolution_schema[0]),
            },
            "trusted_json": {
                "candidate_authority": authority,
                "reference_policy": policy,
                "resolution_schema": resolution_schema,
            },
        },
    }
    return state, task, raw, projected


class RunnerTests(unittest.TestCase):
    def test_cli_requires_exact_mode_commit_and_usage_approval(self) -> None:
        with self.assertRaises(SystemExit):
            runner.main(["--dry-run", "--run-commit", "A" * 40])
        with self.assertRaises(SystemExit):
            runner.main(
                ["--canary", "--run-commit", "a" * 40, "--usage-approval", "wrong"]
            )
        with self.assertRaises(SystemExit):
            runner.main(["--execute", "--run-commit", "a" * 40])
        with (
            patch.object(runner, "execute_batch", return_value={"status": "pass"}),
            patch("builtins.print"),
        ):
            self.assertEqual(
                runner.main(
                    [
                        "--execute",
                        "--run-commit",
                        "a" * 40,
                        "--usage-approval",
                        runner.CANARY_APPROVAL,
                        "--usage-approval",
                        runner.BATCH_APPROVAL,
                    ]
                ),
                0,
            )

    def test_usage_is_closed_exact_and_consistent(self) -> None:
        self.assertEqual(runner._usage(USAGE)["total_tokens"], 5)
        for invalid in (
            {**USAGE, "input_tokens": True},
            {"input_tokens": 1, "output_tokens": 1},
            {**USAGE, "total_tokens": 99},
            {**USAGE, "cached_input_tokens": 4},
        ):
            with self.assertRaises(runner.CompletedInvalid):
                runner._usage(invalid)

    def test_event_parser_accepts_one_context_message_and_usage(self) -> None:
        outcome = runner.parse_events(
            event_stream(),
            resolver=Resolver,
            task_text="task",
            condition="current",
            slot_id="s0",
            profile=PROFILE,
        )
        self.assertEqual(outcome.parse_status, "parsed")
        self.assertEqual(outcome.projected["slot_id"], "s0")
        self.assertEqual(outcome.usage["total_tokens"], 5)
        malformed = runner.parse_events(
            event_stream("not-json"),
            resolver=Resolver,
            task_text="task",
            condition="current",
            slot_id="s0",
            profile=PROFILE,
        )
        self.assertEqual(malformed.parse_status, "malformed")
        with self.assertRaises(runner.CompletedInvalid) as captured:
            runner.parse_events(
                event_stream(usage={**USAGE, "input_tokens": True}),
                resolver=Resolver,
                task_text="task",
                condition="current",
                slot_id="s0",
                profile=PROFILE,
            )
        retained = captured.exception.outcome
        self.assertEqual(retained.parse_status, "malformed")
        self.assertEqual(retained.context_id, "unique-context")
        self.assertEqual(retained.usage["total_tokens"], 0)

    def test_event_parser_rejects_unknown_and_tool_events_after_completion(
        self,
    ) -> None:
        rows = [
            {"type": "thread.started", "thread_id": "unique-context"},
            {"type": "turn.started"},
            {"type": "tool.executed", "tool": "forbidden"},
            {
                "type": "item.completed",
                "item": {
                    "id": "m",
                    "type": "agent_message",
                    "text": '{"answer":"yes"}',
                },
            },
            {"type": "turn.completed", "usage": USAGE},
        ]
        with self.assertRaises(runner.CompletedInvalid) as captured:
            runner.parse_events(
                b"\n".join(json.dumps(row).encode() for row in rows),
                resolver=Resolver,
                task_text="task",
                condition="current",
                slot_id="s0",
                profile=PROFILE,
            )
        retained = captured.exception.outcome
        self.assertEqual(retained.context_id, "unique-context")
        self.assertEqual(retained.usage["total_tokens"], 5)
        rows.pop(2)
        rows.append({"type": "unexpected.after-completion"})
        with self.assertRaises(runner.CompletedInvalid):
            runner.parse_events(
                b"\n".join(json.dumps(row).encode() for row in rows),
                resolver=Resolver,
                task_text="task",
                condition="current",
                slot_id="s0",
                profile=PROFILE,
            )

    def test_packets_are_task_plus_one_card_and_four_calls_are_ordered(self) -> None:
        state = {"resolver": Resolver, "profile": PROFILE}
        packets = [
            runner.build_packet(
                state, task_text="task", condition="reduced", slot_id=slot
            )
            for slot in runner.SLOT_ORDER
        ]
        self.assertTrue(
            all(
                tuple(packet)
                == (
                    "instruction",
                    "task_text",
                    "condition_id",
                    "slot_id",
                    "condition_slot_card",
                    "anonymous_menu",
                )
                for packet in packets
            )
        )
        seen = []

        def invoke(packet, *, state, cli, condition, slot_id):
            del state, cli, condition
            seen.append(packet["slot_id"])
            return runner.InvocationOutcome(
                "parsed",
                {"answer": "yes"},
                {"slot_id": slot_id, "local_need": "yes", "reference_need": "focused"},
                b'{"answer":"yes"}',
                runner.sha256_bytes(b'{"answer":"yes"}'),
                f"context-{slot_id}",
                runner._usage(USAGE),
            )

        results = runner._four_calls(
            state,
            {"path": sys.executable},
            task_text="task",
            condition="current",
            invoke=invoke,
        )
        self.assertEqual(
            [result.projected["slot_id"] for result in results], list(runner.SLOT_ORDER)
        )
        self.assertEqual(set(seen), set(runner.SLOT_ORDER))

    def test_child_argv_disables_tools_and_uses_ephemeral_strict_isolation(
        self,
    ) -> None:
        argv = runner.child_argv({"path": "codex"}, Path("schema.json"))
        for flag in (
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--strict-config",
        ):
            self.assertIn(flag, argv)
        self.assertIn("read-only", argv)
        self.assertIn("never", argv)
        self.assertEqual(argv[-1], "-")
        self.assertNotIn("gpt-5.5-high", argv)

    def test_index_binding_uses_combined_content_and_both_split_identities(
        self,
    ) -> None:
        def sealed(suffix):
            return {
                "path": f"evals/ae-sq1/aq/split-{suffix}.json",
                "blob": suffix * 40,
                "sha256": suffix * 64,
            }

        state = {
            "root": ROOT,
            "commit": "a" * 40,
            "tree": "b" * 40,
            "run_manifest_sha256": "c" * 64,
            "run_manifest": {
                "candidate_manifest": {
                    "commit": "d" * 40,
                    "tree": "e" * 40,
                    "path": runner.CANDIDATE_MANIFEST_PATH,
                    "blob": "f" * 40,
                    "sha256": "1" * 64,
                },
                "corpus_freeze": {"commit": "2" * 40, "tree": "3" * 40},
                "corpus": {"split_a": sealed("4"), "split_b": sealed("5")},
                "schedule": {"seed": "seed"},
            },
            "profile": {
                "bindings": {
                    "candidate_authority": {
                        "commit": "6" * 40,
                        "tree": "7" * 40,
                        "path": "evals/ae-sq1/slec1-authority.json",
                        "blob": "8" * 40,
                        "sha256": "9" * 64,
                    },
                    "runner": {
                        "commit": "6" * 40,
                        "tree": "7" * 40,
                        "path": runner.RUNNER_PATH,
                        "blob": "a" * 40,
                        "sha256": "b" * 64,
                    },
                }
            },
            "corpus_digest": "c" * 64,
            "schedule_digest": "d" * 64,
            "host_sha256": "e" * 64,
        }
        cli = {"version": "codex-cli 0.147.0", "sha256": "f" * 64}
        with patch.object(runner, "git_blob", return_value="1" * 40):
            binding = runner._index_binding(state, cli)
        normalized = run_index.normalize_binding(binding)
        self.assertEqual(normalized["corpus"]["content_sha256"], state["corpus_digest"])
        self.assertEqual(
            tuple(normalized["corpus"]),
            ("content_sha256", "split_a", "split_b"),
        )
        self.assertEqual(normalized["corpus"]["split_a"]["commit"], "2" * 40)
        self.assertEqual(normalized["corpus"]["split_b"]["sha256"], "5" * 64)

    def test_actual_slec_parent_fold_is_the_presentation_resolver(self) -> None:
        state, task, raw, projected = actual_parent_fixture()
        self.assertEqual(
            runner._parent_resolution(
                state,
                task_text=task,
                condition="reduced",
                raw_outputs=raw,
                projected=projected,
            ),
            {
                "status": "selected",
                "selected_slots": ["s0"],
                "reference_bundle": [{"slot_id": "s0", "need": "focused"}],
            },
        )

    def test_parent_rejects_all_resolution_custody_and_semantic_mutants(self) -> None:
        state, task, raw, projected = actual_parent_fixture()
        trusted_json = state["profile"]["trusted_json"]
        valid = slec.resolve(
            task,
            "reduced",
            raw,
            trusted_json["candidate_authority"],
            trusted_json["reference_policy"],
            repository_root=ROOT,
        )
        mutants = {}
        mutant = deepcopy(valid)
        mutant["selected_slots"] = ["s1"]
        mutants["slot"] = mutant
        mutant = deepcopy(valid)
        mutant["reference_capability_ids"][0] = "cap.ae.verification.core.v1"
        mutants["capability"] = mutant
        mutant = deepcopy(valid)
        mutant["references"]["files"] = []
        mutants["file"] = mutant
        for label, field, value in (
            ("path", "path", "../../private/key"),
            ("digest", "sha256", "0" * 64),
            ("blob", "git_blob_sha1", "0" * 40),
            ("size", "size_bytes", valid["references"]["files"][0]["size_bytes"] + 1),
        ):
            mutant = deepcopy(valid)
            mutant["references"]["files"][0][field] = value
            mutants[label] = mutant
        mutant = deepcopy(valid)
        mutant["unexpected_schema_field"] = True
        mutants["schema"] = mutant
        mutant = deepcopy(valid)
        mutant["invocation_evidence"]["recognized_count"] = 1
        mutants["invocation"] = mutant

        for label, record in mutants.items():
            resolver = SimpleNamespace(
                resolve=lambda *_args, _record=record, **_kwargs: deepcopy(_record),
                verify_resolution_record=slec.verify_resolution_record,
            )
            with self.subTest(label=label), self.assertRaises(runner.CompletedInvalid):
                runner._parent_resolution(
                    {**state, "resolver": resolver},
                    task_text=task,
                    condition="reduced",
                    raw_outputs=raw,
                    projected=projected,
                )

        altered_schema = deepcopy(state["profile"]["documents"]["resolution_schema"])
        altered_schema["title"] += " mutant"
        altered_raw = runner.canonical_json(altered_schema)
        drifted_state = {
            **state,
            "profile": {
                **state["profile"],
                "trusted_json": dict(state["profile"]["trusted_json"]),
            },
        }
        drifted_state["profile"]["trusted_json"]["resolution_schema"] = (
            altered_raw,
            runner.sha256_bytes(altered_raw),
        )
        with self.assertRaises(runner.CompletedInvalid):
            runner._parent_resolution(
                drifted_state,
                task_text=task,
                condition="reduced",
                raw_outputs=raw,
                projected=projected,
            )

    def test_canary_verifier_failure_is_terminal_without_provider_retry(self) -> None:
        state, _task, _raw, _projected = actual_parent_fixture()

        class HostileResolver:
            build_assessor_packet = staticmethod(slec.build_assessor_packet)
            verify_resolution_record = staticmethod(slec.verify_resolution_record)

            @staticmethod
            def resolve(*args, **kwargs):
                record = slec.resolve(*args, **kwargs)
                record["invocation_evidence"]["recognized_count"] = 1
                return record

        class FakeIndex:
            def __init__(self) -> None:
                self.started = 0
                self.observed = 0
                self.completed = 0
                self.failed: bool | None = None
                self.passed = False

            def begin_canary(self, _binding):
                return b"capability"

            def canary_call_started(self, _binding, _capability):
                self.started += 1

            def canary_observation(self, _binding, _capability):
                self.observed += 1

            def canary_call_completed(self, _binding, _capability, _usage):
                self.completed += 1

            def fail_canary(self, _binding, _capability, *, invalid):
                self.failed = invalid

            def complete_canary(self, _binding, _capability, _aggregate):
                self.passed = True

        fake_index = FakeIndex()
        state["resolver"] = HostileResolver
        state["run_index_module"] = SimpleNamespace(
            AESQ1RunIndex=lambda _root: fake_index
        )
        state["snapshot"] = SimpleNamespace(close=lambda: None)
        invocations = 0

        def invoke(packet, *, state, cli, condition, slot_id):
            nonlocal invocations
            del state, cli, condition
            invocations += 1
            capsule_raw = runner._runtime_capsule_bytes(
                {
                    "slot_id": slot_id,
                    "local_need": "no",
                    "reference_need": "none",
                    "anchors": [
                        {
                            "start": 0,
                            "end": len(packet["task_text"]),
                            "text": packet["task_text"],
                        }
                    ],
                }
            )
            return runner.InvocationOutcome(
                "parsed",
                json.loads(capsule_raw),
                {"slot_id": slot_id, "local_need": "no", "reference_need": "none"},
                capsule_raw,
                runner.sha256_bytes(capsule_raw),
                f"context-{slot_id}",
                runner._usage(USAGE),
            )

        with (
            patch.object(runner, "preflight", return_value=state),
            patch.object(
                runner,
                "codex_preflight",
                return_value={
                    "path": "codex",
                    "version": "codex-cli 0.147.0",
                    "sha256": "0" * 64,
                },
            ),
            patch.object(runner, "_assert_cli_manifest"),
            patch.object(runner, "_index_binding", return_value={}),
            self.assertRaises(runner.CompletedInvalid),
        ):
            runner.run_canary(
                root=ROOT, run_commit="a" * 40, codex="codex", invoke=invoke
            )
        self.assertEqual(invocations, 4)
        self.assertEqual(
            (fake_index.started, fake_index.observed, fake_index.completed), (4, 4, 4)
        )
        self.assertIs(fake_index.failed, True)
        self.assertFalse(fake_index.passed)

    def test_completed_malformed_capsules_are_scored_through_all_80_presentations(
        self,
    ) -> None:
        schedule = [
            {
                "presentation_index": index,
                "presentation_id": f"presentation-{index}",
                "condition": "current" if index < 40 else "reduced",
                "case_id": "case-1",
            }
            for index in range(80)
        ]
        case = {
            "case_id": "case-1",
            "task_text": "task",
            "task_text_nfc_sha256": "1" * 64,
        }
        captured: dict[str, object] = {}

        class Scorer:
            @staticmethod
            def score_aq(**kwargs):
                captured.update(kwargs)
                self.assertIsInstance(kwargs["historical_digest_inventory"], bytes)
                self.assertEqual(len(kwargs["observations"]), 80)
                self.assertTrue(
                    all(
                        row["resolution"] is None
                        and len(row["capsules"]) == 4
                        and all(
                            capsule["parse_status"] == "malformed"
                            for capsule in row["capsules"]
                        )
                        for row in kwargs["observations"]
                    )
                )
                return {"status": "fail", "aggregate_digest": "a" * 64}

        class Index:
            def __init__(self):
                self.started = self.completed = self.calls = 0
                self.final = {
                    "batch_status": "failed",
                    "aggregate_digest": "a" * 64,
                }

            def begin_batch(self, _binding):
                return b"batch-capability"

            def presentation_started(self, _binding, _capability):
                self.started += 1

            def batch_call_started(self, _binding, _capability):
                self.calls += 1

            def batch_observation(self, _binding, _capability):
                return None

            def batch_call_completed(self, _binding, _capability, _usage):
                return None

            def presentation_completed(self, _binding, _capability):
                self.completed += 1

            def complete_batch(
                self, _binding, _capability, *, status, aggregate_digest
            ):
                self.final = {
                    "batch_status": status,
                    "aggregate_digest": aggregate_digest,
                }

            def state(self, _binding):
                return dict(self.final)

        malformed = [
            runner.InvocationOutcome(
                "malformed",
                None,
                None,
                b"not-json",
                runner.sha256_bytes(b"not-json"),
                f"context-{slot_id}",
                runner._usage(USAGE),
            )
            for slot_id in runner.SLOT_ORDER
        ]
        completed_invalid = []
        for _slot_id in runner.SLOT_ORDER:
            error = runner.CompletedInvalid("completed stream violation")
            error.observed = True
            completed_invalid.append(error)
        state = {
            "schedule": schedule,
            "cases": {"case-1": case},
            "validator": SimpleNamespace(
                digest=lambda _value: "2" * 64,
                capsule_packet_digest=lambda **_kwargs: "3" * 64,
            ),
            "scorer": Scorer,
            "scorer_binding": {},
            "schedule_digest": "4" * 64,
            "corpus_documents": [b"split-a", b"split-b"],
            "historical_inventory": b'{"trusted":"raw"}',
        }
        index = Index()
        with patch.object(
            runner,
            "_four_calls",
            side_effect=[completed_invalid, *([malformed] * 79)],
        ):
            final = runner._perform_batch(
                state, {}, {}, index, invoke=lambda *_a, **_k: None
            )
        self.assertEqual(final["batch_status"], "failed")
        self.assertEqual((index.started, index.completed, index.calls), (80, 80, 320))
        self.assertEqual(len(captured["observations"]), 80)

    def test_canary_retry_receipt_exposes_eight_attempted_four_completed(self) -> None:
        state = {
            "commit": "a" * 40,
            "tree": "b" * 40,
            "resolver": Resolver,
            "profile": PROFILE,
            "runner_entrypoint": {
                "commit": "c" * 40,
                "tree": "d" * 40,
                "path": runner.RUNNER_PATH,
                "blob": "e" * 40,
                "sha256": "f" * 64,
            },
            "snapshot_sha256": "1" * 64,
        }
        zero_usage = {
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

        class Index:
            def __init__(self):
                self.started = self.completed = 0
                self.usage = dict(zero_usage)
                self.retried = False
                self.aggregate = None

            def begin_canary(self, _binding):
                return b"canary-capability"

            def canary_call_started(self, _binding, _capability):
                self.started += 1

            def canary_observation(self, _binding, _capability):
                return None

            def canary_call_completed(self, _binding, _capability, usage):
                self.completed += 1
                normalized = runner._usage(usage)
                for key in self.usage:
                    self.usage[key] += normalized[key]

            def retry_canary(self, _binding, _capability):
                self.retried = True

            def complete_canary(self, _binding, _capability, aggregate):
                self.aggregate = aggregate

            def fail_canary(self, *_args, **_kwargs):
                raise AssertionError("retry canary must pass")

            def state(self, _binding):
                return {
                    "canary_calls_started": self.started,
                    "canary_calls_completed": self.completed,
                    "batch_calls_started": 0,
                    "batch_calls_completed": 0,
                    "canary_usage": dict(self.usage),
                    "aggregate_digest": self.aggregate,
                    "terminal_marker": None,
                }

        first = []
        for _slot_id in runner.SLOT_ORDER:
            error = runner.InfrastructureError("no observation")
            error.observed = False
            first.append(error)
        second = [
            runner.InvocationOutcome(
                "parsed",
                {"answer": "yes"},
                {"slot_id": slot_id, "local_need": "yes", "reference_need": "focused"},
                b'{"answer":"yes"}',
                runner.sha256_bytes(b'{"answer":"yes"}'),
                f"context-{slot_id}",
                runner._usage(USAGE),
            )
            for slot_id in runner.SLOT_ORDER
        ]
        index = Index()
        with (
            patch.object(runner, "_four_calls", side_effect=[first, second]),
            patch.object(
                runner,
                "_parent_resolution",
                return_value={
                    "status": "none",
                    "selected_slots": [],
                    "reference_bundle": [],
                },
            ),
        ):
            index_state = runner._perform_canary(
                state, {}, {}, index, invoke=lambda *_a, **_k: None
            )
        self.assertTrue(index.retried)
        value = runner.receipt("canary", "pass", state, index_state)
        self.assertEqual(value["live_calls_attempted"], 8)
        self.assertEqual(value["live_calls_completed"], 4)

    def test_execute_reuses_one_prepared_index_for_canary_then_batch(self) -> None:
        snapshot = SimpleNamespace(close=lambda: None)
        state = {
            "snapshot": snapshot,
            "commit": "a" * 40,
            "tree": "b" * 40,
            "runner_entrypoint": {
                "commit": "c" * 40,
                "tree": "d" * 40,
                "path": runner.RUNNER_PATH,
                "blob": "e" * 40,
                "sha256": "f" * 64,
            },
            "snapshot_sha256": "1" * 64,
        }
        index = object()
        final = {
            "canary_calls_started": 4,
            "canary_calls_completed": 4,
            "batch_calls_started": 320,
            "batch_calls_completed": 320,
            "canary_usage": {
                key: 0
                for key in (
                    "input_tokens",
                    "cached_input_tokens",
                    "output_tokens",
                    "total_tokens",
                )
            },
            "batch_usage": {
                key: 0
                for key in (
                    "input_tokens",
                    "cached_input_tokens",
                    "output_tokens",
                    "total_tokens",
                )
            },
            "batch_status": "passed",
            "aggregate_digest": "2" * 64,
            "terminal_marker": "consumed-pass",
        }
        seen: list[tuple[str, object]] = []

        def canary(_state, _cli, _binding, received, *, invoke):
            del invoke
            seen.append(("canary", received))
            return final

        def batch(_state, _cli, _binding, received, *, invoke):
            del invoke
            seen.append(("batch", received))
            return final

        with (
            patch.object(
                runner, "_prepared_execution", return_value=(state, {}, {}, index)
            ),
            patch.object(runner, "_perform_canary", side_effect=canary),
            patch.object(runner, "_perform_batch", side_effect=batch),
        ):
            value = runner.execute_batch(root=ROOT, run_commit="a" * 40, codex="codex")
        self.assertEqual(seen, [("canary", index), ("batch", index)])
        self.assertEqual(value["live_calls_attempted"], 324)

    def test_snapshot_import_ignores_later_live_runtime_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            live = Path(directory) / "runtime.py"
            live.write_text("VALUE = 'frozen'\n", encoding="utf-8")
            raw = live.read_bytes()
            binding = {
                "commit": "a" * 40,
                "tree": "b" * 40,
                "path": "scripts/frozen_runtime.py",
                "blob": "c" * 40,
                "sha256": runner.sha256_bytes(raw),
            }
            snapshot = runner.RuntimeSnapshot()
            try:
                snapshot.add(binding, raw, label="runtime")
                snapshot.seal()
                live.write_text("VALUE = 'mutated'\n", encoding="utf-8")
                module = runner._import_snapshot_module(
                    snapshot,
                    "_ae_sq1_snapshot_race_test",
                    binding["path"],
                )
                self.assertEqual(module.VALUE, "frozen")
                self.assertEqual((snapshot.root / binding["path"]).read_bytes(), raw)
            finally:
                snapshot.close()

    def test_receipt_is_aggregate_only(self) -> None:
        state = {
            "commit": "a" * 40,
            "tree": "b" * 40,
            "runner_entrypoint": {
                "commit": "c" * 40,
                "tree": "d" * 40,
                "path": runner.RUNNER_PATH,
                "blob": "e" * 40,
                "sha256": "f" * 64,
            },
            "snapshot_sha256": "1" * 64,
        }
        index_state = {
            "canary_calls_started": 4,
            "canary_calls_completed": 4,
            "batch_calls_started": 320,
            "batch_calls_completed": 320,
            "canary_usage": {
                "input_tokens": 1,
                "cached_input_tokens": 0,
                "output_tokens": 1,
                "total_tokens": 2,
            },
            "batch_usage": {
                "input_tokens": 1,
                "cached_input_tokens": 0,
                "output_tokens": 1,
                "total_tokens": 2,
            },
            "aggregate_digest": "c" * 64,
            "terminal_marker": "consumed-pass",
        }
        value = runner.receipt("execute", "pass", state, index_state)
        for forbidden in (
            "task",
            "case",
            "capsule",
            "context",
            "event",
            "trajectory",
            "stderr",
        ):
            self.assertNotIn(forbidden, json.dumps(value).casefold())
        self.assertEqual(value["live_calls_attempted"], 324)
        self.assertEqual(value["live_calls_completed"], 324)


if __name__ == "__main__":
    unittest.main()
