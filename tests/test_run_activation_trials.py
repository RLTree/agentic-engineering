#!/usr/bin/env python3
"""Focused no-network tests for the AQ prompt-only runner."""
from __future__ import annotations

import importlib.util
import contextlib
import hashlib
import io
import inspect
import json
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("runner", ROOT / "scripts/run_activation_trials.py")
runner = importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(runner)
SCORER_SPEC = importlib.util.spec_from_file_location("scorer", ROOT / "scripts/score_activation.py")
scorer = importlib.util.module_from_spec(SCORER_SPEC); assert SCORER_SPEC.loader; SCORER_SPEC.loader.exec_module(scorer)


class Fake:
    def __init__(self, results): self.results = iter(results); self.calls = []
    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs)); return next(self.results)


def response(raw: bytes, code: int = 0):
    return subprocess.CompletedProcess([], code, stdout=raw, stderr=b"")

def events(thread: str = "thread-a", selection: str = '{"selected_advisers":[]}') -> bytes:
    return (json.dumps({"type":"thread.started","thread_id":thread}) + "\n" +
            json.dumps({"type":"item.completed","item":{"type":"agent_message","text":selection}}) + "\n" +
            json.dumps({"type":"turn.completed"}) + "\n").encode()

def events_with_reasoning(thread: str = "thread-a") -> bytes:
    return (json.dumps({"type":"thread.started","thread_id":thread}) + "\n" +
            json.dumps({"type":"turn.started"}) + "\n" +
            json.dumps({"type":"item.started","item":{"type":"reasoning"}}) + "\n" +
            json.dumps({"type":"item.completed","item":{"type":"reasoning"}}) + "\n" +
            json.dumps({"type":"item.completed","item":{"type":"agent_message","text":'{"selected_advisers":[]}'}}) + "\n" +
            json.dumps({"type":"turn.completed"}) + "\n").encode()


class RunnerTests(unittest.TestCase):
    def test_selection_schema_is_closed(self):
        schema = runner.validate_selector_schema()
        self.assertNotIn("uniqueItems", schema["properties"]["selected_advisers"])
        self.assertEqual(runner.validate_selection({"selected_advisers": []}), [])
        for invalid in ({}, {"selected_advisers": ["bad"]}, {"selected_advisers": [], "x": 1}, {"selected_advisers": ["agentic-engineering"] * 2}):
            with self.assertRaises(runner.RunnerError): runner.validate_selection(invalid)

    def test_packet_is_condition_and_label_blind(self):
        case = {"id": "AQ3-H-001", "prompt": "Decide whether a bounded contract needs an adviser.", "hidden_labels": {"expected_advisers": ["agentic-engineering"], "reference_triggers": ["architecture-boundary"]}}
        packet = runner.selector_packet(case, [{"adviser_id": item, "description": item + " description"} for item in runner.ADVISERS])
        self.assertNotIn("hidden_labels", packet); self.assertNotIn("architecture-boundary", packet); self.assertNotIn("current", packet); self.assertNotIn("plugins/", packet); self.assertIn("logical_advisers", packet); self.assertIn("$agentic-engineering", packet); self.assertIn(case["prompt"], packet)

    def test_real_frozen_case_shape_is_accepted_and_packet_only_exposes_prompt(self):
        cases, _corpus = runner.load_qualification_cases(ROOT)
        case = cases[0]
        catalog = [{"adviser_id": item, "description": item + " description"} for item in runner.ADVISERS]
        packet = json.loads(runner.selector_packet(case, catalog))
        self.assertEqual(set(case), runner.FROZEN_CASE_FIELDS)
        self.assertEqual(set(packet), {"instruction", "logical_advisers", "task"})
        self.assertEqual(packet["task"], case["prompt"])
        self.assertEqual(packet["logical_advisers"], [{"id": item, "description": item + " description"} for item in runner.ADVISERS])

    def test_packet_rejects_fields_outside_the_frozen_case_allowlist(self):
        with self.assertRaisesRegex(runner.RunnerError, "unexpected frozen case shape"):
            runner.selector_packet({"id": "synthetic", "prompt": "Synthetic routing decision.", "unexpected": True}, [])

    def test_packet_orders_the_minimum_owner_decision_contract(self):
        catalog = [{"adviser_id": item, "description": item + " description"} for item in runner.ADVISERS]
        packet = json.loads(runner.selector_packet({"id": "synthetic", "prompt": "Synthetic routing decision."}, catalog))
        instruction = packet["instruction"]
        clauses = (
            "Select the minimum necessary decision owner or owners",
            "Shared topical relevance is insufficient",
            "For one controlling decision, select exactly one best owner",
            "Select exactly two only when the task has two independent controlling decisions",
            "Select none when native work is sufficient",
            "An explicit evaluator-vocabulary invocation is decisive",
            "Evaluator vocabulary maps $agentic-engineering",
            "Return only the schema object",
        )
        self.assertEqual([record["id"] for record in packet["logical_advisers"]], list(runner.ADVISERS))
        self.assertEqual(sorted(packet), ["instruction", "logical_advisers", "task"])
        self.assertEqual([instruction.index(clause) for clause in clauses], sorted(instruction.index(clause) for clause in clauses))

    def test_packet_rejects_shared_relevance_as_a_reason_to_stack(self):
        packet = json.loads(runner.selector_packet({"id": "synthetic", "prompt": "Synthetic routing decision."}, [{"adviser_id": item, "description": "related decision support"} for item in runner.ADVISERS]))
        instruction = packet["instruction"]
        self.assertIn("do not select every adviser whose description seems related", instruction)
        self.assertIn("prefer the more specific decision owner over a broad or downstream lens", instruction)
        self.assertIn("do not stack advisers for a single decision", instruction)
        self.assertIn("do not add others merely for shared relevance", instruction)

    def test_scorer_packet_digest_uses_the_runner_contract_bytes(self):
        catalog = [{"adviser_id": item, "description": item + " description"} for item in runner.ADVISERS]
        case = {"id": "synthetic", "prompt": "Synthetic routing decision."}
        self.assertEqual(scorer.SELECTOR_DECISION_CONTRACT, runner.SELECTOR_DECISION_CONTRACT)
        self.assertEqual(scorer.selector_packet_digest(case["prompt"], catalog), hashlib.sha256(runner.selector_packet(case, catalog).encode()).hexdigest())

    def test_trial_packet_digest_mismatch_prevents_child_invocation(self):
        class MismatchedScorer:
            @staticmethod
            def selector_packet_digest(*_args): return "0" * 64
        fake = Fake([])
        with self.assertRaisesRegex(runner.RunnerError, "selector packet digest mismatch"):
            runner.trial_observation(scorer=MismatchedScorer, checker=None, candidate={}, condition="current", candidate_commit="c", candidate_tree="t", case={"id":"AQ3-H-001","prompt":"synthetic packet binding"}, catalog=[{"adviser_id": item, "description": item} for item in runner.ADVISERS], contract={}, codex_path="codex", invoke=fake, root=ROOT)
        self.assertEqual(fake.calls, [])

    def test_candidate_custody_rejects_nonhead_and_all_nonignored_drift_before_module_or_model(self):
        def repository():
            raw = tempfile.TemporaryDirectory()
            repo = Path(raw.name)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            tracked = repo / "tracked.txt"
            tracked.write_text("one", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
            subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "one"], cwd=repo, check=True)
            tracked.write_text("two", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
            subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "two"], cwd=repo, check=True)
            return raw, repo, tracked
        cases = (
            ("HEAD^", lambda repo, tracked: None, "candidate commit is not live HEAD"),
            ("HEAD", lambda repo, tracked: (repo / "staged.txt").write_text("staged", encoding="utf-8"), "repository worktree is not clean"),
            ("HEAD", lambda repo, tracked: tracked.write_text("unstaged", encoding="utf-8"), "repository worktree is not clean"),
            ("HEAD", lambda repo, tracked: (repo / "untracked.txt").write_text("untracked", encoding="utf-8"), "repository worktree is not clean"),
        )
        for commit, arrange, expected in cases:
            with self.subTest(expected=expected):
                temporary, repo, tracked = repository()
                try:
                    arrange(repo, tracked)
                    if (repo / "staged.txt").exists():
                        subprocess.run(["git", "add", "staged.txt"], cwd=repo, check=True)
                    with mock.patch.object(runner, "committed_module", side_effect=AssertionError("module import is forbidden")) as modules, \
                         mock.patch.object(runner, "codex_preflight", side_effect=AssertionError("model probe is forbidden")) as preflight:
                        with self.assertRaisesRegex(runner.RunnerError, "^" + expected + "$"):
                            runner.validate_candidate(repo, commit)
                    modules.assert_not_called()
                    preflight.assert_not_called()
                finally:
                    temporary.cleanup()

    def test_executable_drift_after_preflight_prevents_child_invocation(self):
        with tempfile.TemporaryDirectory() as raw:
            executable = Path(raw) / "codex"
            executable.write_bytes(b"captured at preflight")
            captured_sha256 = runner.sha256_file(executable)
            executable.write_bytes(b"substituted after preflight")
            fake = Fake([])
            with self.assertRaisesRegex(runner.RunnerError, "^Codex executable drift detected$"):
                runner.invoke_packet(codex_path=str(executable), packet="{}", invoke=fake, codex_sha256=captured_sha256)
            self.assertEqual(fake.calls, [])

    def test_argv_keeps_approval_after_exec_and_disables_features(self):
        argv = runner.child_argv("/tmp/codex", "/tmp/clean", runner.SCHEMA_PATH)
        self.assertEqual(argv[:4], ["/tmp/codex", "--ask-for-approval", "never", "exec"])
        self.assertEqual(runner.MODEL, "gpt-5.5")
        self.assertEqual(runner.REASONING, "medium")
        self.assertEqual(argv[argv.index("--model") + 1], runner.MODEL)
        self.assertIn("--ephemeral", argv); self.assertIn("--json", argv); self.assertEqual(argv[-1], "-")
        self.assertTrue(all(feature in argv for feature in runner.DISABLED_FEATURES))
        self.assertTrue(all(override in argv for override in runner.CONFIG_OVERRIDES))
        self.assertIn("skills.bundled.enabled=false", argv)
        self.assertIn("skills.include_instructions=false", argv)
        self.assertIn(f'model_reasoning_effort="{runner.REASONING}"', argv)
        self.assertIn('web_search="disabled"', argv)
        self.assertIn("code_mode", runner.DISABLED_FEATURES)
        self.assertIn("code_mode_only", runner.DISABLED_FEATURES)
        for feature in ("view_image", "image_generation", "goals", "workspace_dependencies", "default_mode_request_user_input"):
            self.assertIn(feature, runner.DISABLED_FEATURES)

    def test_codex_preflight_proves_prompt_blocks_absent_without_model_call(self):
        calls = []
        def probe(argv, **kwargs):
            calls.append((argv, kwargs))
            if argv[-1] == "--version":
                return subprocess.CompletedProcess(argv, 0, stdout="codex-cli test\n", stderr="")
            if argv[-2:] == ["exec", "--help"]:
                flags = "--ephemeral --ignore-user-config --strict-config --output-schema --json --sandbox --disable"
                return subprocess.CompletedProcess(argv, 0, stdout=flags, stderr="")
            self.assertEqual(argv[-3:], ["debug", "prompt-input", "AQ local isolation preflight"])
            self.assertTrue(all(feature in argv for feature in runner.DISABLED_FEATURES))
            self.assertTrue(all(override in argv for override in runner.CONFIG_OVERRIDES))
            self.assertIn("cwd", kwargs)
            return subprocess.CompletedProcess(argv, 0, stdout='[{"role":"user","content":"AQ local isolation preflight"}]', stderr="")
        info = runner.codex_preflight(str(Path(__file__).resolve()), probe=probe)
        self.assertEqual(info["version"], "codex-cli test")
        self.assertEqual(len(calls), 3)

    def test_codex_preflight_rejects_injected_skill_prompt(self):
        results = iter((
            subprocess.CompletedProcess([], 0, stdout="codex-cli test\n", stderr=""),
            subprocess.CompletedProcess([], 0, stdout="--ephemeral --ignore-user-config --strict-config --output-schema --json --sandbox --disable", stderr=""),
            subprocess.CompletedProcess([], 0, stdout='[{"content":"<skills_instructions>SKILL.md</skills_instructions>"}]', stderr=""),
        ))
        with self.assertRaisesRegex(runner.RunnerError, "prompt isolation preflight failed"):
            runner.codex_preflight(str(Path(__file__).resolve()), probe=lambda *args, **kwargs: next(results))

    def test_codex_preflight_rejects_config_warning(self):
        results = iter((
            subprocess.CompletedProcess([], 0, stdout="codex-cli test\n", stderr=""),
            subprocess.CompletedProcess([], 0, stdout="--ephemeral --ignore-user-config --strict-config --output-schema --json --sandbox --disable", stderr=""),
            subprocess.CompletedProcess([], 0, stdout='[{"content":"clean"}]', stderr="deprecated config warning"),
        ))
        with self.assertRaisesRegex(runner.RunnerError, "prompt isolation preflight failed"):
            runner.codex_preflight(str(Path(__file__).resolve()), probe=lambda *args, **kwargs: next(results))

    def test_schedule_is_deterministic_strict_and_complete(self):
        cases = [{"id": f"AQ3-H-{index:03d}", "prompt": "x"} for index in range(1, 41)]
        one = runner.schedule(cases, "seed"); two = runner.schedule(cases, "seed")
        self.assertEqual(one, two); self.assertEqual(len(one), 80)
        self.assertEqual({condition for condition, _ in one}, {"current", "reduced"})
        self.assertTrue(all(one[index][0] != one[index + 1][0] for index in range(79)))
        with self.assertRaises(runner.RunnerError):
            runner.schedule(cases, "   ")

    def test_preflight_binds_future_corpus_validator_and_observations_reject_out_of_range_indices(self):
        self.assertIn("scripts/validate_future_activation_corpus_v3.py", inspect.getsource(runner.immutable_preflight))
        with self.assertRaises(runner.RunnerError):
            runner.trial_observation(scorer=None, checker=None, candidate={}, condition="current", candidate_commit="c", candidate_tree="t", case={}, catalog=[], contract={}, codex_path="codex", invoke=Fake([]), root=ROOT, presentation_index=80)

    def test_completed_malformed_is_not_retried(self):
        fake = Fake([response(events(selection='{"selected_advisers":["bad"]}')), response(events())])
        with self.assertRaises(runner.RunnerError): runner.run_one(argv=["codex"], packet="{}", invoke=fake)
        self.assertEqual(len(fake.calls), 1)

    def test_non_corpus_transport_canary_may_retry_once_before_completion(self):
        fake = Fake([response(b"not-json\n"), response(events())])
        selected, raw, context = runner.invoke_packet(codex_path="/tmp/codex", packet="{}", invoke=fake, allow_retry=True)
        self.assertEqual(selected, []); self.assertTrue(raw.startswith(b'{"type": "thread.started"')); self.assertEqual(len(fake.calls), 2)

    def test_qualification_packet_never_retries_after_thread_started_without_completion(self):
        class MatchingScorer:
            @staticmethod
            def selector_packet_digest(task, catalog): return hashlib.sha256(runner.selector_packet({"id":"AQ3-H-001","prompt":task}, catalog).encode()).hexdigest()
        raw = b'{"type":"thread.started","thread_id":"qualification-thread"}\nnot-json\n'
        fake = Fake([response(raw), response(events())])
        with self.assertRaises(runner.InfrastructureError):
            runner.trial_observation(scorer=MatchingScorer, checker=None, candidate={}, condition="current", candidate_commit="c", candidate_tree="t", case={"id":"AQ3-H-001","prompt":"bounded qualification"}, catalog=[], contract={}, codex_path="codex", invoke=fake, root=ROOT)
        self.assertEqual(len(fake.calls), 1)
        with self.assertRaisesRegex(runner.RunnerError, "qualification trials never retry"):
            runner.trial_observation(scorer=MatchingScorer, checker=None, candidate={}, condition="current", candidate_commit="c", candidate_tree="t", case={"id":"AQ3-H-001","prompt":"bounded qualification"}, catalog=[], contract={}, codex_path="codex", invoke=Fake([]), root=ROOT, allow_retry=True)

    def test_terminal_error_item_is_diagnostic_and_not_retried(self):
        raw = b'{"type":"thread.started","thread_id":"x"}\n{"type":"item.completed","item":{"type":"error","message":"provider unavailable"}}\n'
        fake = Fake([response(raw), response(events())])
        with self.assertRaisesRegex(runner.RunnerError, "^child error item$"):
            runner.run_one(argv=["codex"], packet="{}", invoke=fake)
        self.assertEqual(len(fake.calls), 1)

    def test_top_level_and_turn_errors_are_diagnostic(self):
        cases = (
            (b'{"type":"error","message":"stream failed"}\n', "^child stream error$"),
            (b'{"type":"turn.failed","error":{"message":"turn failed"}}\n', "^child turn failed$"),
        )
        for raw, expected in cases:
            with self.subTest(expected=expected), self.assertRaisesRegex(runner.RunnerError, expected):
                runner.parse_events(raw)

    def test_tool_event_is_rejected(self):
        with self.assertRaises(runner.RunnerError):
            runner.parse_events(b'{"type":"thread.started","thread_id":"x"}\n{"type":"item.completed","item":{"type":"tool_call"}}\n')

    def test_unknown_event_and_item_report_fixed_classification(self):
        cases = (
            (b'{"type":"future.event"}\n', "^unrecognized Codex JSONL event$"),
            (b'{"type":"item.completed","item":{"type":"future_item"}}\n', "^unrecognized Codex JSONL item$"),
        )
        for raw, expected in cases:
            with self.subTest(expected=expected), self.assertRaisesRegex(runner.RunnerError, expected):
                runner.parse_events(raw)

    def test_child_diagnostics_never_reflect_child_controlled_text(self):
        secret = "AQ3-H-999-synthetic-corpus-like-secret"
        cases = (
            (json.dumps({"type":"error", "message":secret}).encode() + b"\n", "child stream error"),
            (json.dumps({"type":"turn.failed", "error":{"message":secret}}).encode() + b"\n", "child turn failed"),
            (json.dumps({"type":"thread.started", "thread_id":"x"}).encode() + b"\n" + json.dumps({"type":"item.completed", "item":{"type":"error", "message":secret}}).encode() + b"\n", "child error item"),
            (json.dumps({"type":"future." + secret}).encode() + b"\n", "unrecognized Codex JSONL event"),
            (json.dumps({"type":"item.completed", "item":{"type":"future_item_" + secret}}).encode() + b"\n", "unrecognized Codex JSONL item"),
        )
        for raw, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(runner.RunnerError, "^" + expected + "$") as raised:
                    runner.parse_events(raw)
                self.assertNotIn(secret, str(raised.exception))

    def test_mcp_tool_item_is_rejected_in_any_phase(self):
        with self.assertRaises(runner.RunnerError):
            runner.parse_events(b'{"type":"thread.started","thread_id":"x"}\n{"type":"item.started","item":{"type":"mcp_tool_call"}}\n')

    def test_reasoning_plus_agent_message_is_accepted(self):
        selected, raw, context = runner.parse_events(events_with_reasoning("thread-real"))
        self.assertEqual(selected, []); self.assertTrue(raw); self.assertEqual(context, "thread-real")

    def test_nonzero_after_completed_output_is_not_retried(self):
        fake = Fake([response(events(), code=1), response(events())])
        with self.assertRaises(runner.RunnerError): runner.run_one(argv=["codex"], packet="{}", invoke=fake)
        self.assertEqual(len(fake.calls), 1)

    def test_temp_directory_is_cleaned_after_packet(self):
        fake = Fake([response(events())])
        runner.invoke_packet(codex_path="/tmp/codex", packet="{}", invoke=fake)
        temporary = fake.calls[0][0][fake.calls[0][0].index("--cd") + 1]
        self.assertFalse(Path(temporary).exists())

    def test_missing_turn_or_thread_is_infrastructure(self):
        with self.assertRaises(runner.InfrastructureError):
            runner.parse_events(b'{"type":"item.completed","item":{"type":"agent_message","text":"{\\"selected_advisers\\":[]}"}}\n{"type":"turn.completed"}\n')

    def test_dry_run_and_execute_are_mutually_exclusive(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                runner.main(["--dry-run", "--execute"])

    def test_canary_and_execute_need_usage_approval(self):
        for mode in ("--canary", "--execute"):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit): runner.main([mode])

    def test_dry_run_is_zero_write_and_no_model_call(self):
        watched = [
            ROOT / "scripts/run_activation_trials.py",
            ROOT / "evals/foundation-v4/selector-output-schema.json",
            ROOT / "evals/foundation-v4/future-activation-v3/activation-heldout.json",
            ROOT / "evals/foundation-v4/reduced-four-skills/candidate.json",
        ]
        before = {path: path.read_bytes() for path in watched}
        status_before = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, check=True).stdout
        stdout = io.StringIO()
        codex_info = {"path": "/test/codex", "version": "codex-cli test", "sha256": "a" * 64}
        committed = all(
            subprocess.run(["git", "show", f"HEAD:{path.relative_to(ROOT)}"], cwd=ROOT, capture_output=True).stdout == path.read_bytes()
            for path in watched
        )
        preflight = mock.Mock(return_value=codex_info) if committed else mock.Mock(side_effect=AssertionError("draft HOLD must precede Codex preflight"))
        with mock.patch.object(runner, "codex_preflight", preflight), \
             mock.patch.object(runner, "invoke_packet", side_effect=AssertionError("dry-run must not make a model call")), \
             contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(stdout):
            self.assertEqual(runner.main(["--dry-run", "--candidate-commit", "HEAD"]), 0 if committed else 2)
        if committed:
            self.assertEqual(json.loads(stdout.getvalue())["live_calls"], 0)
        status_after = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, check=True).stdout
        self.assertEqual(before, {path: path.read_bytes() for path in watched})
        self.assertEqual(status_before, status_after)

    def test_immutable_preflight_failure_prevents_child_invoke(self):
        called = []
        with mock.patch.object(runner, "validate_candidate", return_value=(object(), {}, "c" * 40, "d" * 40)), \
             mock.patch.object(runner, "immutable_preflight", side_effect=runner.RunnerError("drift")), \
             mock.patch.object(runner, "codex_preflight", side_effect=AssertionError("must not reach child preflight")):
            with self.assertRaises(runner.RunnerError):
                runner.execute_trials(root=ROOT, candidate_commit="HEAD", seed="seed", codex="codex", invoke=lambda *args, **kwargs: called.append(args))
        self.assertEqual(called, [])

    def test_execute_returns_evaluator_owned_aggregate_not_envelope(self):
        cases = [{"id": f"AQ3-H-{index:03d}", "prompt": "task"} for index in range(1, 41)]
        candidate = {"conditions": {name: {"condition_input_sha256": name * 64, "selector_catalog_sha256": ("a" if name == "current" else "b") * 64} for name in ("current", "reduced")}}
        class Checker:
            @staticmethod
            def selector_catalog(candidate, condition, root, commit):
                return [{"adviser_id": item, "description": item} for item in runner.ADVISERS]
        captured = {}
        class Scorer:
            @staticmethod
            def selector_packet_digest(task, catalog): return "p" * 64
            @staticmethod
            def score(envelope, root):
                captured["envelope"] = envelope
                return {"stage":"AQ", "status":"fail", "promotion_eligible":False, "runtime_provenance_proven":False, "raw_trajectories_persisted":False}
        indices = []
        def observation(**kwargs):
            case, condition = kwargs["case"], kwargs["condition"]
            indices.append(kwargs["presentation_index"])
            return {"case_id":case["id"], "context_id":f"thread-{condition}-{case['id']}"}
        with mock.patch.object(runner, "validate_candidate", return_value=(Checker, candidate, "c" * 40, "d" * 40)), \
             mock.patch.object(runner, "immutable_preflight"), \
             mock.patch.object(runner, "load_qualification_cases", return_value=(cases, {"source_commit":"x"})), \
             mock.patch.object(runner, "codex_preflight", return_value={"path":"codex","version":"v","sha256":"a" * 64}), \
             mock.patch.object(runner, "execution_contract", return_value={"schedule_sha256":"s"}), \
             mock.patch.object(runner, "invoke_packet", return_value=([], events("canary-thread"), "canary-thread")), \
             mock.patch.object(runner, "trial_observation", side_effect=observation), \
             mock.patch.object(runner, "scorer_module", return_value=Scorer):
            result = runner.execute_trials(root=ROOT, candidate_commit="HEAD", seed="seed", codex="codex", invoke=Fake([]))
        self.assertEqual(result["stage"], "AQ")
        self.assertEqual(len(captured["envelope"]["conditions"][0]["observations"]), 40)
        self.assertEqual(len(captured["envelope"]["conditions"][1]["observations"]), 40)
        self.assertEqual(indices, list(range(80)))
        self.assertNotIn("raw_event_sha256", json.dumps(captured["envelope"]))

    def test_execute_rejects_scorer_runtime_or_promotion_claims(self):
        cases = [{"id": f"AQ3-H-{index:03d}", "prompt": "task"} for index in range(1, 41)]
        candidate = {"conditions": {name: {"condition_input_sha256": name * 64, "selector_catalog_sha256": ("a" if name == "current" else "b") * 64} for name in ("current", "reduced")}}
        class Checker:
            @staticmethod
            def selector_catalog(*_args): return [{"adviser_id": item, "description": item} for item in runner.ADVISERS]
        class Scorer:
            @staticmethod
            def selector_packet_digest(*_args): return "p" * 64
            @staticmethod
            def score(*_args): return {"promotion_eligible":False, "runtime_provenance_proven":True}
        with mock.patch.object(runner, "validate_candidate", return_value=(Checker, candidate, "c" * 40, "d" * 40)), \
             mock.patch.object(runner, "immutable_preflight"), \
             mock.patch.object(runner, "load_qualification_cases", return_value=(cases, {"source_commit":"x"})), \
             mock.patch.object(runner, "codex_preflight", return_value={"path":"codex","version":"v","sha256":"a" * 64}), \
             mock.patch.object(runner, "execution_contract", return_value={"schedule_sha256":"s"}), \
             mock.patch.object(runner, "invoke_packet", return_value=([], events("canary-thread"), "canary-thread")), \
             mock.patch.object(runner, "trial_observation", return_value={"case_id":"AQ3-H-001", "context_id":"thread"}), \
             mock.patch.object(runner, "scorer_module", return_value=Scorer):
            with self.assertRaisesRegex(runner.RunnerError, "runtime provenance claim"):
                runner.execute_trials(root=ROOT, candidate_commit="HEAD", seed="seed", codex="codex", invoke=Fake([]))

    def test_raw_bytes_do_not_appear_in_observation_shape(self):
        selected, raw, context = runner.parse_events(events("real-thread"))
        self.assertEqual(selected, []); self.assertTrue(raw); self.assertNotIn("raw_event", {"context_id": context})
        self.assertEqual(context, "real-thread")

    def test_capacity_breach_is_a_compact_completed_resolution(self):
        class Checker:
            @staticmethod
            def resolve_parent_payload_resolution(*args, **kwargs):
                return {"status": "cap_exceeded", "resolved_count": 4, "records": []}
        case = {"hidden_labels": {"reference_triggers": ["architecture-boundary"]}}
        status, records = runner.resolve_payloads(Checker, {}, case, ["agentic-engineering"], ROOT)
        self.assertEqual(status, {"status": "cap_exceeded", "resolved_count": 4})
        self.assertEqual(records, [])


if __name__ == "__main__": unittest.main()
