from __future__ import annotations

import importlib.util
import json
import os
import random
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/run_activation_trials_v8.py"
SPEC = importlib.util.spec_from_file_location("aq8_runner_test", PATH)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


@contextmanager
def fake_auth_home():
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "auth.json"
        source.write_text('{"test_only":"credential"}', encoding="utf-8")
        os.chmod(source, 0o600)
        with mock.patch.dict(os.environ, {"CODEX_HOME": directory}):
            yield source


def graph() -> dict:
    slots = ("s0", "s1", "s2", "s3")
    pairs = (
        ("s0", "s1"),
        ("s0", "s2"),
        ("s0", "s3"),
        ("s1", "s2"),
        ("s1", "s3"),
        ("s2", "s3"),
    )
    return {
        "candidate_states": [
            {"slot_id": slot, "state": "resolved_or_absent"} for slot in slots
        ],
        "pairwise_relations": [
            {"left_slot": left, "right_slot": right, "relation": "unrelated"}
            for left, right in pairs
        ],
        "reference_needs": [{"slot_id": slot, "need": "none"} for slot in slots],
    }


def profile() -> dict:
    return {
        "protocol": {},
        "selector_schema": {},
        "runtime_selector_schema": {},
        "adapter": {},
        "reference_policy": {},
        "base_manifest": {},
    }


def events(value: dict, *, thread: str = "fresh") -> bytes:
    rows = (
        {"type": "thread.started", "thread_id": thread},
        {"type": "turn.started"},
        {
            "type": "item.completed",
            "item": {"id": "item-0", "type": "agent_message", "text": json.dumps(value)},
        },
        {"type": "turn.completed"},
    )
    return b"\n".join(json.dumps(row).encode() for row in rows)


class Resolver:
    @staticmethod
    def validate_graph_output(value, _protocol, _schema):
        if not isinstance(value, dict) or tuple(value) != (
            "candidate_states",
            "pairwise_relations",
            "reference_needs",
        ):
            raise ValueError("closed graph")
        if (len(value["candidate_states"]), len(value["pairwise_relations"]), len(value["reference_needs"])) != (4, 6, 4):
            raise ValueError("graph size")
        return json.loads(json.dumps(value))

    @staticmethod
    def build_condition_packet(_adapter, condition, task):
        return {
            "instruction": "return graph",
            "task_text": task,
            "slot_order": ["s0", "s1", "s2", "s3"],
            "pair_order": [
                ["s0", "s1"], ["s0", "s2"], ["s0", "s3"],
                ["s1", "s2"], ["s1", "s3"], ["s2", "s3"],
            ],
            "condition_guidance": [condition],
            "support_legend": {"none": "none"},
        }

    @staticmethod
    def resolve_graph(_task, _graph, _protocol, _policy, _base):
        return {
            "graph_status": "valid",
            "automatic_selection_status": "automatic",
            "selection_status": "automatic",
            "root_slots": [],
            "selected_slots": [],
            "selected_adviser_ids": [],
            "complement_adviser_ids": ["a", "b", "c", "d"],
            "reference_requests": [],
            "reference_uncertain_slots": [],
            "reference_resolution": {
                "status": "resolved",
                "resolved_count": 0,
                "canonical_payload_id_tuple": [],
            },
        }


class RunnerV8Tests(unittest.TestCase):
    def test_cli_requires_mode_lowercase_sha_and_exact_live_approval(self):
        with self.assertRaises(SystemExit):
            runner.main(["--dry-run"])
        with self.assertRaises(SystemExit):
            runner.main([
                "--canary", "--candidate-commit", "A" * 40,
                "--usage-approval", runner.APPROVAL,
            ])
        with self.assertRaises(SystemExit):
            runner.main([
                "--execute", "--candidate-commit", "a" * 40,
                "--usage-approval", "wrong",
            ])

    def test_packet_pair_is_exact_six_key_and_only_guidance_differs(self):
        current = Resolver.build_condition_packet({}, "current", "task")
        reduced = Resolver.build_condition_packet({}, "reduced", "task")
        runner._validate_packet_pair(current, reduced)
        with self.assertRaises(runner.PreflightError):
            runner._validate_packet_pair({**current, "case_id": "x"}, reduced)
        with self.assertRaises(runner.PreflightError):
            runner._validate_packet_pair(current, {**reduced, "task_text": "different"})
        with self.assertRaises(runner.PreflightError):
            runner._validate_packet_pair(current, {**reduced, "condition_guidance": current["condition_guidance"]})

    def test_runner_requires_the_exact_auth_isolation_execution_contract(self):
        exact = {"execution_contract": {"isolation": dict(runner.ISOLATION_CONTRACT)}}
        runner._require_isolation_contract(exact)
        changed = {"execution_contract": {"isolation": dict(runner.ISOLATION_CONTRACT)}}
        changed["execution_contract"]["isolation"]["global_agents_loaded"] = True
        with self.assertRaises(runner.PreflightError):
            runner._require_isolation_contract(changed)

    def test_codex_0147_completed_agent_message_shape_is_exact(self):
        parsed, context = runner.parse_events(events(graph(), thread="019-context"), Resolver, profile())
        self.assertEqual(parsed, graph())
        self.assertEqual(context, "019-context")
        text = json.dumps(graph())
        invalid = (
            {"type": "agent_message", "text": text},
            {"id": " ", "type": "agent_message", "text": text},
            {"id": 0, "type": "agent_message", "text": text},
            {"id": "x", "extra": "y", "type": "agent_message", "text": text},
            {"id": "x", "type": "agent_message", "text": " "},
        )
        for item in invalid:
            raw = b"\n".join(json.dumps(row).encode() for row in (
                {"type": "thread.started", "thread_id": "x"},
                {"type": "turn.started"},
                {"type": "item.completed", "item": item},
                {"type": "turn.completed"},
            ))
            with self.subTest(item=item), self.assertRaises(runner.CompletedInvalid):
                runner.parse_events(raw, Resolver, profile())

    def test_completed_malformed_is_content_and_turn_failure_is_infrastructure(self):
        with self.assertRaises(runner.CompletedInvalid):
            runner.parse_events(events({"candidate_states": []}), Resolver, profile())
        reasoning_only = b"\n".join(json.dumps(row).encode() for row in (
            {"type": "thread.started", "thread_id": "x"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"id": "r", "type": "reasoning", "text": "done"}},
            {"type": "turn.completed"},
        ))
        with self.assertRaises(runner.CompletedInvalid):
            runner.parse_events(reasoning_only, Resolver, profile())
        duplicate_message = b"\n".join(json.dumps(row).encode() for row in (
            {"type": "thread.started", "thread_id": "x"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {
                "id": "a", "type": "agent_message", "text": json.dumps(graph()),
            }},
            {"type": "item.completed", "item": {
                "id": "b", "type": "agent_message", "text": json.dumps(graph()),
            }},
            {"type": "turn.completed"},
        ))
        with self.assertRaises(runner.CompletedInvalid):
            runner.parse_events(duplicate_message, Resolver, profile())
        for row in ({"type": "turn.failed"}, {"type": "error", "message": "provider"}):
            raw = b"\n".join((
                json.dumps({"type": "thread.started", "thread_id": "x"}).encode(),
                json.dumps(row).encode(),
            ))
            with self.assertRaises(runner.InfrastructureError):
                runner.parse_events(raw, Resolver, profile())

    def test_duplicate_keys_and_nonfinite_constants_are_rejected_before_semantics(self):
        valid = json.dumps(graph(), separators=(",", ":"))
        duplicate_graph = '{"candidate_states":[],"candidate_states":' + valid.split(
            '"candidate_states":', 1
        )[1]
        self.assertEqual(json.loads(duplicate_graph), graph())
        duplicate_stream = b"\n".join(json.dumps(row).encode() for row in (
            {"type": "thread.started", "thread_id": "x"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {
                "id": "i", "type": "agent_message", "text": duplicate_graph,
            }},
            {"type": "turn.completed"},
        ))
        with self.assertRaises(runner.CompletedInvalid):
            runner.parse_events(duplicate_stream, Resolver, profile())

        duplicate_event = b'{"type":"ignored","type":"thread.started","thread_id":"x"}'
        with self.assertRaises(runner.TransportError):
            runner.parse_events(duplicate_event, Resolver, profile())

        nonfinite = valid.replace('"resolved_or_absent"', "NaN", 1)
        nonfinite_stream = b"\n".join(json.dumps(row).encode() for row in (
            {"type": "thread.started", "thread_id": "x"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {
                "id": "i", "type": "agent_message", "text": nonfinite,
            }},
            {"type": "turn.completed"},
        ))
        with self.assertRaises(runner.CompletedInvalid):
            runner.parse_events(nonfinite_stream, Resolver, profile())

    def test_lifecycle_order_is_fail_closed(self):
        invalid_streams = (
            (
                {"type": "turn.started"},
                {"type": "thread.started", "thread_id": "x"},
                {"type": "turn.completed"},
            ),
            (
                {"type": "thread.started", "thread_id": "x"},
                {"type": "item.completed", "item": {
                    "id": "i", "type": "agent_message", "text": json.dumps(graph()),
                }},
                {"type": "turn.completed"},
            ),
            (
                {"type": "thread.started", "thread_id": "x"},
                {"type": "turn.started"},
                {"type": "turn.completed"},
                {"type": "item.completed", "item": {
                    "id": "i", "type": "agent_message", "text": json.dumps(graph()),
                }},
            ),
        )
        for rows in invalid_streams:
            raw = b"\n".join(json.dumps(row).encode() for row in rows)
            with self.subTest(rows=rows), self.assertRaises(runner.RunnerError):
                runner.parse_events(raw, Resolver, profile())

    def test_unknown_or_effect_events_are_closed_six_boolean_content_failures(self):
        for item_type in ("tool_call", "mcp_tool_call", "command_execution", "file_change", "effect", "approval", "error"):
            raw = b"\n".join(json.dumps(row).encode() for row in (
                {"type": "thread.started", "thread_id": "x"},
                {"type": "turn.started"},
                {"type": "item.completed", "item": {"id": "i", "type": item_type, "text": "x"}},
            ))
            with self.subTest(item_type=item_type), self.assertRaises(runner.CompletedInvalid) as caught:
                runner.parse_events(raw, Resolver, profile())
            self.assertEqual(tuple(caught.exception.events), runner.EVENT_KEYS)
            self.assertTrue(all(isinstance(value, bool) for value in caught.exception.events.values()))

    def test_negative_exit_is_content_after_completion_and_transport_before_completion(self):
        state = {"resolver": Resolver, "profile": profile(), "checker": object()}

        def completed_child(*_args, **_kwargs):
            return SimpleNamespace(returncode=-9, stdout=events(graph()))

        with fake_auth_home(), mock.patch.object(
            runner, "_execution_byte_preflight", return_value=Path("/schema")
        ):
            with self.assertRaises(runner.CompletedInvalid):
                runner._invoke(
                    {"path": sys.executable, "digest": "a" * 64},
                    {},
                    root=ROOT,
                    commit="a" * 40,
                    state=state,
                    invoke=completed_child,
                )

        def precompletion_child(*_args, **_kwargs):
            return SimpleNamespace(returncode=-9, stdout=b"")

        with fake_auth_home(), mock.patch.object(
            runner, "_execution_byte_preflight", return_value=Path("/schema")
        ):
            with self.assertRaises(runner.TransportError):
                runner._invoke(
                    {"path": sys.executable, "digest": "a" * 64},
                    {},
                    root=ROOT,
                    commit="a" * 40,
                    state=state,
                    invoke=precompletion_child,
                )

    def test_fake_child_gets_empty_cwd_stdin_only_and_raw_is_not_persisted(self):
        seen = {}

        def child(argv, *, cwd, input, **kwargs):
            seen.update(argv=argv, cwd=cwd, packet=json.loads(input), kwargs=kwargs)
            self.assertEqual(list(Path(cwd).iterdir()), [])
            return SimpleNamespace(returncode=0, stdout=events(graph()))

        state = {"resolver": Resolver, "profile": profile(), "checker": object()}
        packet = Resolver.build_condition_packet({}, "current", "task")
        with fake_auth_home(), mock.patch.object(
            runner, "_execution_byte_preflight", return_value=Path("/runtime-schema")
        ):
            actual, context = runner._invoke(
                {"path": "/fake/codex", "digest": "a" * 64},
                packet,
                root=ROOT,
                commit="a" * 40,
                state=state,
                invoke=child,
            )
        self.assertEqual((actual, context), (graph(), "fresh"))
        self.assertEqual(seen["packet"], packet)
        self.assertFalse(Path(seen["cwd"]).exists())
        isolated_home = Path(seen["kwargs"]["env"]["CODEX_HOME"])
        self.assertEqual(seen["kwargs"]["env"]["HOME"], str(isolated_home))
        self.assertFalse(isolated_home.exists())
        self.assertNotIn("task", " ".join(seen["argv"]))

    def test_child_and_debug_probe_share_model_reasoning_and_disabled_surfaces(self):
        seen = []

        def probe(argv, **_kwargs):
            seen.append(argv)
            if argv[-1] == "--version":
                return SimpleNamespace(returncode=0, stdout="codex-cli 0.147.0\n", stderr="")
            if argv[-2:] == ["exec", "--help"]:
                flags = " ".join((
                    "--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config",
                    "--skip-git-repo-check", "--sandbox", "--output-schema", "--json",
                ))
                return SimpleNamespace(returncode=0, stdout=flags, stderr="")
            prompt = [{
                "id": "probe-message",
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": runner.ISOLATION_PROBE}],
                "internal_chat_message_metadata_passthrough": {"turn_id": "probe-turn"},
            }]
            return SimpleNamespace(returncode=0, stdout=json.dumps(prompt), stderr="")

        with fake_auth_home():
            runner.codex_preflight(sys.executable, probe)
        child = runner.child_argv({"path": sys.executable}, Path("/schema"))
        debug = seen[-1]
        for feature in runner.DISABLED_FEATURES:
            self.assertIn(feature, debug)
            self.assertIn(feature, child)
        for override in runner.CONFIG_OVERRIDES:
            self.assertIn(override, debug)
            self.assertIn(override, child)
        self.assertEqual(child[child.index("--model") + 1], "gpt-5.5")
        self.assertEqual(child[child.index("--sandbox") + 1], "read-only")
        self.assertEqual(child[child.index("--output-schema") + 1], "/schema")

    def test_probe_uses_auth_only_owner_home_explicit_env_and_cleans_immediately(self):
        homes = []
        workdirs = []
        with tempfile.TemporaryDirectory() as source_directory:
            source = Path(source_directory) / "auth.json"
            source.write_text('{"test_only":"credential"}', encoding="utf-8")
            os.chmod(source, 0o600)

            def probe(argv, **kwargs):
                environment = kwargs["env"]
                home = Path(environment["CODEX_HOME"])
                homes.append(home)
                self.assertEqual(environment["HOME"], str(home))
                self.assertEqual(os.stat(home).st_mode & 0o777, 0o700)
                self.assertEqual({path.name for path in home.iterdir()}, {"auth.json"})
                copied = home / "auth.json"
                self.assertEqual(os.stat(copied).st_mode & 0o777, 0o600)
                self.assertFalse(os.path.samefile(source, copied))
                self.assertNotIn("USER", environment)
                self.assertNotIn("XDG_CONFIG_HOME", environment)
                if "cwd" in kwargs:
                    workdir = Path(kwargs["cwd"])
                    workdirs.append(workdir)
                    self.assertEqual(list(workdir.iterdir()), [])
                if argv[-1] == "--version":
                    return SimpleNamespace(returncode=0, stdout="codex-cli 0.147.0\n", stderr="")
                if argv[-2:] == ["exec", "--help"]:
                    return SimpleNamespace(
                        returncode=0,
                        stdout=" ".join((
                            "--ephemeral", "--ignore-user-config", "--ignore-rules",
                            "--strict-config", "--skip-git-repo-check", "--sandbox",
                            "--output-schema", "--json",
                        )),
                        stderr="",
                    )
                prompt = [{
                    "id": "probe-message",
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": runner.ISOLATION_PROBE}],
                    "internal_chat_message_metadata_passthrough": {"turn_id": "probe-turn"},
                }]
                return SimpleNamespace(returncode=0, stdout=json.dumps(prompt), stderr="")

            with mock.patch.dict(os.environ, {"CODEX_HOME": source_directory}):
                info = runner.codex_preflight(sys.executable, probe)
            self.assertEqual(info["version"], "codex-cli 0.147.0")
            self.assertTrue(homes and len({str(path) for path in homes}) == 1)
            self.assertTrue(all(not path.exists() for path in homes))
            self.assertTrue(all(not path.exists() for path in workdirs))
            self.assertTrue(source.is_file())
            self.assertEqual(os.stat(source).st_mode & 0o777, 0o600)

    def test_insecure_or_symlink_auth_fails_before_probe(self):
        with tempfile.TemporaryDirectory() as source_directory:
            source = Path(source_directory) / "auth.json"
            source.write_text("test", encoding="utf-8")
            os.chmod(source, 0o644)
            probe = mock.Mock()
            with mock.patch.dict(os.environ, {"CODEX_HOME": source_directory}):
                with self.assertRaises(runner.PreflightError):
                    runner.codex_preflight(sys.executable, probe)
            probe.assert_not_called()

        with tempfile.TemporaryDirectory() as source_directory:
            target = Path(source_directory) / "target.json"
            target.write_text("test", encoding="utf-8")
            os.chmod(target, 0o600)
            (Path(source_directory) / "auth.json").symlink_to(target)
            probe = mock.Mock()
            with mock.patch.dict(os.environ, {"CODEX_HOME": source_directory}):
                with self.assertRaises(runner.PreflightError):
                    runner.codex_preflight(sys.executable, probe)
            probe.assert_not_called()

    def test_debug_prompt_isolation_rejects_empty_or_injected_prompt(self):
        def make(payload):
            def probe(argv, **_kwargs):
                if argv[-1] == "--version":
                    return SimpleNamespace(returncode=0, stdout="codex-cli 0.147.0\n", stderr="")
                if argv[-2:] == ["exec", "--help"]:
                    return SimpleNamespace(
                        returncode=0,
                        stdout=" ".join((
                            "--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config",
                            "--skip-git-repo-check", "--sandbox", "--output-schema", "--json",
                        )),
                        stderr="",
                    )
                return SimpleNamespace(returncode=0, stdout=payload, stderr="")
            return probe

        injected = json.dumps([
            {
                "id": "global",
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "# Global Working Agreement"}],
                "internal_chat_message_metadata_passthrough": {"turn_id": "global-turn"},
            },
            {
                "id": "probe",
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": runner.ISOLATION_PROBE}],
                "internal_chat_message_metadata_passthrough": {"turn_id": "probe-turn"},
            },
        ])
        with fake_auth_home():
            for payload in (
                "not-json",
                "[]",
                '[{"role":"user","content":"<skills_instructions>"}]',
                injected,
            ):
                with self.subTest(payload=payload), self.assertRaises(runner.PreflightError):
                    runner.codex_preflight(sys.executable, make(payload))

    def test_debug_preflight_rejects_non_0147_cli_lifecycle(self):
        def probe(argv, **_kwargs):
            if argv[-1] == "--version":
                return SimpleNamespace(returncode=0, stdout="codex-cli 0.148.0\n", stderr="")
            return SimpleNamespace(
                returncode=0,
                stdout=" ".join((
                    "--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config",
                    "--skip-git-repo-check", "--sandbox", "--output-schema", "--json",
                )),
                stderr="",
            )

        with fake_auth_home(), self.assertRaisesRegex(runner.PreflightError, "0.147"):
            runner.codex_preflight(sys.executable, probe)

    def test_receipt_is_aggregate_only_and_contains_no_trajectory_surface(self):
        value = runner.receipt(
            "execute",
            "failed",
            {"commit": "a" * 40, "tree": "b" * 40},
            live_calls=80,
            aggregate_digest="c" * 64,
        )
        self.assertEqual(value["aggregate_digest"], "c" * 64)
        for forbidden in ("prompt", "task", "graph", "context", "events", "stderr", "path", "index"):
            self.assertNotIn(forbidden, value)

    def test_execute_never_invokes_canary(self):
        with (
            mock.patch.object(runner, "preflight", side_effect=runner.PreflightError("stop")),
            mock.patch.object(runner, "run_canary") as canary,
        ):
            with self.assertRaises(runner.PreflightError):
                runner.execute_trials(root=ROOT, candidate_commit="a" * 40, codex="fake")
            canary.assert_not_called()

    def test_canary_retries_infrastructure_once_but_never_retries_content(self):
        calls = []

        class Index:
            def begin_canary(self, *_args, **_kwargs):
                return b"cap"

            def retry_canary(self, *_args, **_kwargs):
                calls.append("retry")

            def complete_canary(self, *_args, **_kwargs):
                calls.append("complete")

            def fail_canary(self, *_args, **kwargs):
                calls.append(("fail", kwargs.get("reason")))

        state = {
            "profile": profile(),
            "schedule_digest": "a" * 64,
            "commit": "a" * 40,
            "tree": "b" * 40,
            "binding": {},
            "index_module": SimpleNamespace(
                normalize_binding=lambda _binding: None,
                AQ8RunIndex=lambda _root: Index(),
            ),
            "resolver": Resolver,
            "checker": object(),
        }
        common = (
            mock.patch.object(runner, "preflight", return_value=state),
            mock.patch.object(runner, "codex_preflight", return_value={
                "id": "codex-cli", "path": sys.executable, "digest": "a" * 64,
            }),
            mock.patch.object(runner, "binding_from_profile", return_value={
                "corpus": {"commit": "c" * 40},
            }),
            mock.patch.object(runner, "_execution_byte_preflight", return_value=Path("/schema")),
            mock.patch.object(runner, "_unconsumed_marker", return_value="marker"),
        )
        with common[0], common[1], common[2], common[3], common[4], mock.patch.object(
            runner,
            "_invoke",
            side_effect=[runner.TransportError("infra"), (graph(), "ctx")],
        ) as invoke:
            result = runner.run_canary(root=ROOT, candidate_commit="a" * 40, codex="fake")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(invoke.call_count, 2)
        self.assertEqual(calls, ["retry", "complete"])

        calls.clear()
        common = (
            mock.patch.object(runner, "preflight", return_value=state),
            mock.patch.object(runner, "codex_preflight", return_value={
                "id": "codex-cli", "path": sys.executable, "digest": "a" * 64,
            }),
            mock.patch.object(runner, "binding_from_profile", return_value={
                "corpus": {"commit": "c" * 40},
            }),
            mock.patch.object(runner, "_execution_byte_preflight", return_value=Path("/schema")),
            mock.patch.object(runner, "_unconsumed_marker", return_value="marker"),
        )
        with common[0], common[1], common[2], common[3], common[4], mock.patch.object(
            runner,
            "_invoke",
            side_effect=runner.CompletedInvalid("content"),
        ) as invoke:
            with self.assertRaises(runner.CompletedInvalid):
                runner.run_canary(root=ROOT, candidate_commit="a" * 40, codex="fake")
        self.assertEqual(invoke.call_count, 1)
        self.assertEqual(calls, [("fail", "malformed_or_content_failure")])

    def test_every_postcompletion_failure_gets_exactly_one_canary_invocation(self):
        completed_prefix = b"\n".join(json.dumps(row).encode() for row in (
            {"type": "thread.started", "thread_id": "ctx"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {
                "id": "i", "type": "agent_message", "text": json.dumps(graph()),
            }},
        ))
        cases = {
            "missing_turn_completed": (completed_prefix, 0),
            "later_turn_failed": (
                completed_prefix + b"\n" + json.dumps({"type": "turn.failed"}).encode(),
                0,
            ),
            "malformed_trailing_event": (events(graph()) + b"\n{", 0),
            "malformed_before_completed_event": (
                b"\n".join((
                    json.dumps({"type": "thread.started", "thread_id": "ctx"}).encode(),
                    b"{",
                    json.dumps({"type": "item.completed", "item": {
                        "id": "i", "type": "agent_message", "text": json.dumps(graph()),
                    }}).encode(),
                    json.dumps({"type": "turn.completed"}).encode(),
                )),
                0,
            ),
            "signal_after_completion": (events(graph()), -9),
            "nonzero_after_completion": (events(graph()), 1),
        }

        for name, (stdout, returncode) in cases.items():
            transitions = []
            child_calls = []

            class Index:
                def begin_canary(self, *_args, **_kwargs):
                    return b"cap"

                def retry_canary(self, *_args, **_kwargs):
                    transitions.append("retry")

                def complete_canary(self, *_args, **_kwargs):
                    transitions.append("complete")

                def fail_canary(self, *_args, **kwargs):
                    transitions.append(("fail", kwargs.get("reason")))

            state = {
                "profile": profile(),
                "schedule_digest": "a" * 64,
                "commit": "a" * 40,
                "tree": "b" * 40,
                "binding": {},
                "index_module": SimpleNamespace(
                    normalize_binding=lambda _binding: None,
                    AQ8RunIndex=lambda _root: Index(),
                ),
                "resolver": Resolver,
                "checker": object(),
            }

            def child(*_args, **_kwargs):
                child_calls.append(name)
                return SimpleNamespace(returncode=returncode, stdout=stdout)

            with (
                self.subTest(name=name),
                fake_auth_home(),
                mock.patch.object(runner, "preflight", return_value=state),
                mock.patch.object(runner, "codex_preflight", return_value={
                    "id": "codex-cli", "path": sys.executable, "digest": "a" * 64,
                }),
                mock.patch.object(runner, "binding_from_profile", return_value={
                    "corpus": {"commit": "c" * 40},
                }),
                mock.patch.object(runner, "_execution_byte_preflight", return_value=Path("/schema")),
                mock.patch.object(runner, "_unconsumed_marker", return_value="marker"),
            ):
                with self.assertRaises(runner.CompletedInvalid):
                    runner.run_canary(
                        root=ROOT,
                        candidate_commit="a" * 40,
                        codex="fake",
                        invoke=child,
                    )
            self.assertEqual(child_calls, [name])
            self.assertEqual(transitions, [("fail", "malformed_or_content_failure")])

    def test_observation_has_closed_h4_content_and_six_event_flags(self):
        class Score:
            _expected_case_digest = staticmethod(lambda _case, _kind: "a" * 64)
            _packet_digest = staticmethod(lambda *_args: "b" * 64)
            _condition_digest = staticmethod(lambda *_args: "c" * 64)
            _profile_execution_digest = staticmethod(lambda *_args: "d" * 64)

        state = {
            "scorer": Score,
            "profile": profile(),
            "binding": {"runner": {"digest": "e" * 64}},
        }
        case = {"case_id": "case", "task_text": "safe"}
        actual = runner._observation(
            state,
            case,
            "current",
            0,
            "context",
            semantic_output=None,
            parent_derivation=None,
        )
        self.assertTrue(actual["terminal_completed"])
        self.assertEqual((actual["parse_status"], actual["semantic_output"], actual["parent_derivation"]), ("malformed", None, None))
        self.assertEqual(tuple(actual["events"]), runner.EVENT_KEYS)
        self.assertFalse(any(actual["events"].values()))

    def test_schedule_requires_exact_40x2_alternating_unique_context_inputs(self):
        identifiers = tuple(f"case-{index:02d}" for index in range(40))
        schedule = []
        for index, case_id in enumerate(identifiers):
            schedule.append(
                {"presentation_index": len(schedule), "condition": "current", "case_id": case_id}
            )
            schedule.append(
                {"presentation_index": len(schedule), "condition": "reduced", "case_id": case_id}
            )
        self.assertTrue(runner._schedule_ok(schedule, identifiers))
        schedule[2]["condition"] = "reduced"
        self.assertFalse(runner._schedule_ok(schedule, identifiers))

    def test_preflight_executes_exact_80_production_resolutions_and_scores_before_return(self):
        commit, tree = "a" * 40, "b" * 40
        identifiers = tuple(f"AQ8-heldout-{index:02d}" for index in range(40))
        cases = [
            {
                "case_id": case_id,
                "task_text": f"task {index}",
                "expected_semantic_output": graph(),
                "expected_parent_derivation": Resolver.resolve_graph("", graph(), {}, {}, {}),
            }
            for index, case_id in enumerate(identifiers)
        ]

        def sealed(char):
            return {"commit": char * 40, "tree": char * 40, "sha256": char * 64}

        manifest = {
            "protocol_authority": sealed("1"),
            "reference_policy_authority": sealed("2"),
            "corpus_authority": sealed("3"),
            "validator_authority": sealed("4"),
            "evaluator_surface": {"files": [
                {"role": "runner", "path": runner.RUNNER_PATH, "sha256": "5" * 64},
                {"role": "scorer", "path": runner.SCORER_PATH, "sha256": "6" * 64},
            ]},
        }
        candidate_profile = {
            **profile(),
            "candidate_commit": commit,
            "tree": tree,
            "digest": "7" * 64,
            "manifest": manifest,
            "authoring": {"cases": cases[:20]},
            "heldout": {"cases": cases[20:]},
            "qualified_ids": identifiers,
            "execution_contract": {"isolation": dict(runner.ISOLATION_CONTRACT)},
        }
        counts = {"validated": 0, "resolved": 0, "scored_rows": 0}

        class TrackingResolver(Resolver):
            @staticmethod
            def validate_graph_output(value, protocol, schema):
                counts["validated"] += 1
                return Resolver.validate_graph_output(value, protocol, schema)

            @staticmethod
            def resolve_graph(*args):
                counts["resolved"] += 1
                return Resolver.resolve_graph(*args)

        class Checker:
            load_verified_candidate = staticmethod(lambda *_args, **_kwargs: candidate_profile)
            verify_zero_model_projection = staticmethod(
                lambda _profile, selected: {
                    "status": "pass" if len(selected) == 40 else "fail",
                    "qualification_cases": 40,
                    "presentations": 80,
                    "live_calls": 0,
                }
            )

        class Score:
            _expected_case_digest = staticmethod(lambda _case, _kind: "8" * 64)
            _packet_digest = staticmethod(lambda *_args: "9" * 64)
            _condition_digest = staticmethod(lambda *_args: "a" * 64)
            _profile_execution_digest = staticmethod(lambda *_args: "b" * 64)

            @staticmethod
            def build_schedule(ids, seed):
                rng = random.Random(seed)
                current, reduced = list(ids), list(ids)
                rng.shuffle(current)
                rng.shuffle(reduced)
                rows = []
                for left, right in zip(current, reduced, strict=True):
                    rows.append(
                        {"presentation_index": len(rows), "condition": "current", "case_id": left}
                    )
                    rows.append(
                        {"presentation_index": len(rows), "condition": "reduced", "case_id": right}
                    )
                return tuple(rows)

            schedule_digest = staticmethod(lambda schedule: runner.sha256_json(list(schedule)))

            @staticmethod
            def score_synthetic(envelope, _profile):
                counts["scored_rows"] = sum(
                    len(condition["observations"]) for condition in envelope["conditions"]
                )
                return {"status": "pass"}

            validate_result = staticmethod(lambda result: result)

        index = SimpleNamespace(normalize_binding=lambda _binding: None)

        def module(_root, _commit, path, _name, _dependencies=None):
            return {
                runner.INDEX_PATH: index,
                runner.RESOLVER_PATH: TrackingResolver,
                runner.CHECKER_PATH: Checker,
                runner.SCORER_PATH: Score,
            }[path]

        with (
            mock.patch.object(runner, "require_exact_live_head", return_value=(commit, tree)),
            mock.patch.object(runner, "committed_module", side_effect=module),
            mock.patch.object(runner, "_runtime_graph_schema_path", return_value=Path("/schema")),
        ):
            state = runner.preflight(ROOT, commit)
        self.assertEqual((len(state["cases"]), len(state["schedule"])), (40, 80))
        self.assertEqual(counts, {"validated": 80, "resolved": 80, "scored_rows": 80})


if __name__ == "__main__":
    unittest.main()
