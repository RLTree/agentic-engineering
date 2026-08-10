from __future__ import annotations

import importlib.util
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/run_activation_trials_v7.py"
spec = importlib.util.spec_from_file_location("aq7_runner_test", PATH)
runner = importlib.util.module_from_spec(spec); assert spec and spec.loader; sys.modules[spec.name] = runner; spec.loader.exec_module(runner)
sys.path.insert(0, str(ROOT / "scripts"))
import check_reduced_four_skill_candidate_v7 as candidate_checker  # noqa: E402
import aq_run_index_v7 as run_index  # noqa: E402


def profile():
    return {"protocol": {"predicate_order": [f"p{n}" for n in range(12)]}, "selector_schema": {}, "runtime_selector_schema": {}, "adapter": {}, "reference_policy": {}, "base_manifest": {}}


def events(value, *, thread="fresh"):
    return b"\n".join(json.dumps(row).encode() for row in (
        {"type": "thread.started", "thread_id": thread}, {"type": "turn.started"},
        {"type": "item.completed", "item": {"id": "item-0", "type": "agent_message", "text": json.dumps(value)}}, {"type": "turn.completed"},
    ))


class Resolver:
    @staticmethod
    def validate_fact_output(value, _protocol, _schema):
        if set(value) != {"predicate_facts"}: raise ValueError("closed")
        facts = tuple(value["predicate_facts"])
        if len(facts) != 12: raise ValueError("size")
        return facts


@contextmanager
def committed_fixture():
    """A clean, shared-history candidate containing the actual AQ7 sources."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "repo"
        subprocess.run(["git", "clone", "-q", "--shared", str(ROOT), str(root)], check=True)
        subprocess.run(["git", "config", "user.name", "AQ7 runner test"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "aq7@example.invalid"], cwd=root, check=True)
        files = (runner.CHECKER_PATH, runner.RESOLVER_PATH, runner.SCORER_PATH, runner.RUNNER_PATH,
                 runner.EVALUATOR_SCHEMA_PATH, candidate_checker.RUNTIME_SELECTOR_SCHEMA, candidate_checker.ADAPTER_PATH)
        for relative in files:
            target = root / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / relative, target)
        def digest(relative): return hashlib.sha256((root / relative).read_bytes()).hexdigest()
        surface = []
        paths = (runner.CHECKER_PATH, runner.RESOLVER_PATH, runner.SCORER_PATH, runner.RUNNER_PATH,
                 runner.EVALUATOR_SCHEMA_PATH, candidate_checker.RUNTIME_SELECTOR_SCHEMA, candidate_checker.VALIDATOR_PATH, candidate_checker.RUN_INDEX_PATH,
                 candidate_checker.ADAPTER_PATH)
        for role, relative in zip(candidate_checker.ROLES, paths, strict=True):
            surface.append({"role": role, "path": relative, "sha256": digest(relative)})
        contract = {
            "conditions": [{"id": key, "condition_guidance_canonical_sha256": value} for key, value in candidate_checker.CONDITIONS],
            "model": {"id": "gpt-5.5", "reasoning_effort": "medium"},
            "schedule": {"seed": runner.SCHEDULE_SEED, "qualification_cases": 40, "presentations": 80, "strict_alternation": True},
            "packet": {"keys": ["instruction", "task_text", "predicate_order", "condition_guidance"], "sole_condition_variance": "condition_guidance", "model_output_root": "predicate_facts", "fact_count": 12},
            "isolation": {"fresh_empty_cwd": True, "ephemeral_context_requested": True, "sandbox": "read-only", "approval_policy": "never", "tools_enabled": False, "apps_enabled": False, "plugins_enabled": False, "mcp_enabled": False},
            "integrity": {"unique_contexts_required": 80, "content_retries": 0, "canary_precompletion_infrastructure_retries_max": 1, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown"},
            "gates": {"automatic_precision_min": "0.95", "automatic_recall_min": "0.90", "native_abstention_specificity_min": "0.95", "broad_router_overselection_max": "0.05", "one_decision_stacking_max": 0, "exactly_two_exact_set_min": "1.00", "must_not_select_violations_max": 0, "explicit_exact_set_min": "1.00", "selector_invalid_max": 0, "resolver_mismatch_max": 0, "payload_cap_violations_max": 0, "reference_load_correct_min": "1.00", "authority_tool_violations_max": 0},
            "result_claims": {"maximum_claim": "unattested deterministic AQ7 decision-certificate telemetry from supplied observations", "runtime_provenance_proven": False, "provider_identity_proven": False, "telemetry_attested": False, "product_behavior_proven": False, "promotion_eligible": False},
        }
        manifest = {"schema_version": "7.0", "claim_ceiling": "structural-only", "h3_authority": candidate_checker.H3_BINDING, "selector_schema_authority": candidate_checker.SCHEMA_BINDING, "reference_policy_authority": candidate_checker.POLICY_BINDING, "base_manifest_authority": candidate_checker.BASE_BINDING, "aq7_contract_authority": candidate_checker.CONTRACT_BINDING, "corpus_authority": candidate_checker.CORPUS_BINDING, "validator_authority": candidate_checker.VALIDATOR_BINDING, "run_index_authority": candidate_checker.RUN_INDEX_BINDING, "condition_adapter_authority": candidate_checker.ADAPTER_BINDING, "evaluator_surface": {"files": surface}, "execution_contract": contract}
        (root / candidate_checker.MANIFEST_PATH).write_text(json.dumps(manifest), encoding="utf-8")
        plan = root / "EXECPLAN.md"
        plan.write_text("\n".join(line for line in plan.read_text(encoding="utf-8").splitlines() if not line.startswith("AQ7-RUN-AUTHORITY ")) + f"\nAQ7-RUN-AUTHORITY corpus={candidate_checker.CORPUS[0]} status=unconsumed\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True); subprocess.run(["git", "commit", "-qm", "AQ7 candidate"], cwd=root, check=True)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        yield root, commit


class RunnerV7Tests(unittest.TestCase):
    def test_cli_requires_explicit_mode_sha_and_exact_approval(self):
        with self.assertRaises(SystemExit): runner.main(["--dry-run"])
        with self.assertRaises(SystemExit): runner.main(["--canary", "--candidate-commit", "A" * 40, "--usage-approval", runner.APPROVAL])
        with self.assertRaises(SystemExit): runner.main(["--execute", "--candidate-commit", "a" * 40, "--usage-approval", "wrong"])

    def test_packet_pair_is_closed_and_guidance_is_only_delta(self):
        current = {"instruction": "i", "task_text": "t", "predicate_order": ["p"], "condition_guidance": ["current"]}
        reduced = {"instruction": "i", "task_text": "t", "predicate_order": ["p"], "condition_guidance": ["reduced"]}
        runner._validate_packet_pair(current, reduced)
        with self.assertRaises(runner.PreflightError): runner._validate_packet_pair({**current, "case_id": "x"}, reduced)
        with self.assertRaises(runner.PreflightError): runner._validate_packet_pair(current, {**reduced, "task_text": "no"})

    def test_event_allowlist_rejects_every_non_message_item_and_unknown_event(self):
        facts = [{"predicate_id": f"p{n}", "state": "absent"} for n in range(12)]
        self.assertEqual(runner.parse_events(events({"predicate_facts": facts}), Resolver, profile())[0], tuple(facts))
        for item_type in ("reasoning", "tool_call", "mcp_tool_call", "command_execution", "file_change", "effect", "approval", "error"):
            raw = b"\n".join((json.dumps({"type": "thread.started", "thread_id": "x"}).encode(), json.dumps({"type": "item.completed", "item": {"id": "item-0", "type": item_type, "text": "x"}}).encode()))
            with self.assertRaises((runner.CompletedInvalid, runner.TransportError)): runner.parse_events(raw, Resolver, profile())

    def test_codex_0147_completed_agent_message_wire_shape_is_exact(self):
        facts = [{"predicate_id": f"p{n}", "state": "absent"} for n in range(12)]
        text = json.dumps({"predicate_facts": facts})

        def stream(item):
            return b"\n".join(json.dumps(row).encode() for row in (
                {"type": "thread.started", "thread_id": "019-item-context"},
                {"type": "turn.started"},
                {"type": "item.completed", "item": item},
                {"type": "turn.completed", "usage": {"input_tokens": 1, "cached_input_tokens": 0, "output_tokens": 1}},
            ))

        actual = {"id": "item_0", "type": "agent_message", "text": text}
        parsed, context = runner.parse_events(stream(actual), Resolver, profile())
        self.assertEqual((parsed, context), (tuple(facts), "019-item-context"))

        invalid = {
            "legacy_two_key_missing_id": {"type": "agent_message", "text": text},
            "blank_id": {"id": " ", "type": "agent_message", "text": text},
            "non_string_id": {"id": 0, "type": "agent_message", "text": text},
            "extra_id_field": {"id": "item_0", "extra_id": "item_1", "type": "agent_message", "text": text},
            "blank_text": {"id": "item_0", "type": "agent_message", "text": " "},
        }
        for name, item in invalid.items():
            with self.subTest(name=name), self.assertRaises(runner.CompletedInvalid):
                runner.parse_events(stream(item), Resolver, profile())

    def test_completed_malformed_is_not_transport_retry_class(self):
        raw = events({"predicate_facts": []})
        with self.assertRaises(runner.CompletedInvalid): runner.parse_events(raw, Resolver, profile())

    def test_turn_failure_or_root_error_is_transport_not_scored_content(self):
        for row in ({"type": "turn.failed"}, {"type": "error", "message": "provider"}):
            raw = b"\n".join((json.dumps({"type": "thread.started", "thread_id": "x"}).encode(), json.dumps(row).encode()))
            with self.assertRaises(runner.TransportError): runner.parse_events(raw, Resolver, profile())

    def test_negative_child_exit_is_transport_even_with_parseable_stdout(self):
        state = {"resolver": Resolver, "profile": profile(), "checker": object()}
        facts = [{"predicate_id": f"p{n}", "state": "absent"} for n in range(12)]
        child = lambda *_args, **_kwargs: SimpleNamespace(returncode=-9, stdout=events({"predicate_facts": facts}))
        with mock.patch.object(runner, "require_exact_live_head"), mock.patch.object(runner, "sha256_file", return_value="a" * 64), mock.patch.object(runner, "_runtime_selector_schema_path", return_value=Path("/runtime-schema")):
            with self.assertRaises(runner.TransportError):
                runner._invoke({"path": sys.executable, "digest": "a" * 64}, {}, root=ROOT, commit="a" * 40, state=state, invoke=child)

    def test_message_and_reasoning_lifecycle_is_discarded_until_one_completion(self):
        facts = [{"predicate_id": f"p{n}", "state": "absent"} for n in range(12)]
        raw = b"\n".join(json.dumps(row).encode() for row in (
            {"type": "thread.started", "thread_id": "x"}, {"type": "item.started", "item": {"type": "reasoning", "text": "discard"}},
            {"type": "item.updated", "item": {"type": "agent_message", "text": "discard"}}, {"type": "item.completed", "item": {"id": "item-0", "type": "agent_message", "text": json.dumps({"predicate_facts": facts})}}, {"type": "turn.completed"},
        ))
        self.assertEqual(runner.parse_events(raw, Resolver, profile())[1], "x")

    def test_completed_invalid_observation_is_null_and_retains_context_authority_flags(self):
        class Score:
            _expected_case_digest = staticmethod(lambda _case, _kind: "a" * 64)
            _packet_digest = staticmethod(lambda *_args: "b" * 64)
            _condition_digest = staticmethod(lambda *_args: "c" * 64)
            _profile_execution_digest = staticmethod(lambda *_args: "d" * 64)
        state = {"scorer": Score, "resolver": object(), "profile": profile(), "binding": {"runner": {"digest": "e" * 64}}}
        case = {"case_id": "case", "packet": {"task_text": "safe"}}
        observation = runner._observation(state, case, "current", 0, "real-context", facts=None, resolution=None)
        observation["events"] = {"effect_requested": False, "effect_granted": False, "claim_requested": False, "claim_granted": False, "tool_requested": True, "tool_granted": True, "full_schema_or_template_loaded": False}
        self.assertEqual((observation["parse_status"], observation["fact_output"], observation["parent_resolution"], observation["context_id"]), ("malformed", None, None, "real-context"))
        self.assertTrue(observation["events"]["tool_requested"] and observation["events"]["tool_granted"])

    def test_zero_model_scorer_rejection_is_a_pre_codex_hold(self):
        with committed_fixture() as (root, commit), mock.patch.object(runner, "codex_preflight") as codex, mock.patch.object(runner, "zero_model_score_preflight", side_effect=runner.PreflightError("drift")):
            with self.assertRaises(runner.PreflightError): runner.preflight(root, commit)
            codex.assert_not_called()

    def test_unsupported_runtime_schema_holds_before_codex_and_index(self):
        with committed_fixture() as (root, _commit):
            schema_path = root / candidate_checker.RUNTIME_SELECTOR_SCHEMA
            bad = json.loads(schema_path.read_text(encoding="utf-8")); bad["allOf"] = []
            schema_path.write_text(json.dumps(bad), encoding="utf-8")
            manifest_path = root / candidate_checker.MANIFEST_PATH
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            row = next(item for item in manifest["evaluator_surface"]["files"] if item["role"] == runner.RUNTIME_SELECTOR_SCHEMA_ROLE)
            row["sha256"] = hashlib.sha256(schema_path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            subprocess.run(["git", "add", candidate_checker.RUNTIME_SELECTOR_SCHEMA, candidate_checker.MANIFEST_PATH], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "unsupported runtime schema"], cwd=root, check=True)
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            with mock.patch.object(runner, "codex_preflight") as codex:
                with self.assertRaisesRegex(ValueError, "runtime selector schema"):
                    runner.run_canary(root=root, candidate_commit=commit, codex="fake")
            codex.assert_not_called()
            self.assertFalse((run_index.git_common_dir(root) / run_index.INDEX_NAME).exists())

    def test_runtime_schema_byte_drift_holds_before_index_or_child(self):
        with committed_fixture() as (root, commit):
            state = runner.preflight(root, commit)
            schema_path = root / candidate_checker.RUNTIME_SELECTOR_SCHEMA
            schema_path.write_bytes(schema_path.read_bytes() + b"\n")
            info = {"id": "codex-cli", "path": sys.executable, "version": "fake", "digest": runner.sha256_file(Path(sys.executable))}
            child = mock.Mock()
            with self.assertRaises(runner.PreflightError):
                runner._invoke(info, {}, root=root, commit=commit, state=state, invoke=child)
            child.assert_not_called()
            with mock.patch.object(runner, "preflight", return_value=state), mock.patch.object(runner, "codex_preflight", return_value=info), mock.patch.object(state["index_module"], "AQ7RunIndex") as index_factory:
                with self.assertRaises(runner.PreflightError):
                    runner.run_canary(root=root, candidate_commit=commit, codex="fake", invoke=child)
            index_factory.assert_not_called(); child.assert_not_called()

    def test_child_argv_isolated_and_contains_no_prompt_argument(self):
        argv = runner.child_argv({"path": "/x"}, Path("/runtime-schema"))
        self.assertEqual(argv[:4], ["/x", "--ask-for-approval", "never", "exec"])
        self.assertIn("--ephemeral", argv); self.assertIn("--skip-git-repo-check", argv); self.assertIn("read-only", argv)
        self.assertEqual(argv[argv.index("--output-schema") + 1], "/runtime-schema")
        self.assertNotIn("task_text", " ".join(argv)); self.assertNotIn("prompt", " ".join(argv))

    def test_probe_and_child_share_medium_reasoning_and_disable_surface(self):
        seen = []
        def probe(argv, **_kwargs):
            seen.append(argv)
            if argv[-1] == "--version": return SimpleNamespace(returncode=0, stdout="fake\n", stderr="")
            if argv[-2:] == ["exec", "--help"]: return SimpleNamespace(returncode=0, stdout=" ".join(("--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config", "--skip-git-repo-check", "--sandbox", "--output-schema", "--json")), stderr="")
            return SimpleNamespace(returncode=0, stdout='[{"role":"user","content":"isolated"}]', stderr="")
        runner.codex_preflight(sys.executable, probe)
        child = runner.child_argv({"path": sys.executable}, Path("/schema"))
        isolation = seen[-1]
        for feature in runner.DISABLED_FEATURES:
            self.assertIn(feature, isolation); self.assertIn(feature, child)
        for override in runner.CONFIG_OVERRIDES:
            self.assertIn(override, isolation); self.assertIn(override, child)
        self.assertIn('model_reasoning_effort="medium"', isolation)
        self.assertIn('model="gpt-5.5"', isolation)
        self.assertIn("--model", child); self.assertEqual(child[child.index("--model") + 1], "gpt-5.5")
        self.assertIn("--sandbox", isolation); self.assertEqual(isolation[isolation.index("--sandbox") + 1], "read-only")

    def test_prompt_isolation_rejects_empty_malformed_or_forbidden_prompt(self):
        def make(payload):
            def probe(argv, **_kwargs):
                if argv[-1] == "--version": return SimpleNamespace(returncode=0, stdout="fake\n", stderr="")
                if argv[-2:] == ["exec", "--help"]: return SimpleNamespace(returncode=0, stdout=" ".join(("--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config", "--skip-git-repo-check", "--sandbox", "--output-schema", "--json")), stderr="")
                return SimpleNamespace(returncode=0, stdout=payload, stderr="")
            return probe
        for payload in ("not-json", "[]", '[{"role":"user","content":"<skills_instructions>"}]'):
            with self.assertRaises(runner.PreflightError): runner.codex_preflight(sys.executable, make(payload))

    def test_receipt_is_generic_and_never_contains_raw_or_context(self):
        value = runner.receipt("execute", "failed", {"commit": "a" * 40, "tree": "b" * 40}, live_calls=80, aggregate_digest="c" * 64)
        self.assertEqual(value["aggregate_digest"], "c" * 64)
        for forbidden in ("prompt", "task", "facts", "context", "events", "stderr", "path", "index"):
            self.assertNotIn(forbidden, value)

    def test_execute_does_not_call_canary(self):
        with mock.patch.object(runner, "preflight", side_effect=runner.PreflightError("stop")), mock.patch.object(runner, "run_canary") as canary:
            with self.assertRaises(runner.PreflightError): runner.execute_trials(root=ROOT, candidate_commit="a" * 40, codex="fake")
            canary.assert_not_called()

    def test_canary_retries_only_transport_once(self):
        state = {"profile": profile(), "schedule_digest": "a" * 64, "commit": "a" * 40, "tree": "b" * 40, "binding": {}, "index_module": SimpleNamespace(AQ7RunIndex=lambda _root: Index()), "resolver": Resolver, "checker": object()}
        class Index:
            def begin_canary(self, *_a, **_k): return b"x"
            def retry_canary(self, *_a, **_k): calls.append("retry")
            def complete_canary(self, *_a, **_k): calls.append("complete")
            def fail_canary(self, *_a, **_k): calls.append("fail")
        calls = []
        with mock.patch.object(runner, "preflight", return_value=state), mock.patch.object(runner, "codex_preflight", return_value={"id": "codex-cli", "path": sys.executable, "digest": "a" * 64}), mock.patch.object(runner, "binding_from_profile", return_value={}), mock.patch.object(runner, "_unconsumed_marker", return_value="marker"), mock.patch.object(runner, "_runtime_selector_schema_path", return_value=Path("/runtime-schema")), mock.patch.object(runner, "_invoke", side_effect=[runner.TransportError("x"), (tuple({"predicate_id": f"p{n}", "state": "absent"} for n in range(12)), "x")]):
            result = runner.run_canary(root=ROOT, candidate_commit="a" * 40, codex="fake")
        self.assertEqual(result["status"], "passed"); self.assertEqual(calls, ["retry", "complete"])

    def test_repaired_binding_can_start_after_failed_precompletion_canary_but_cannot_replay(self):
        def sealed(commit_char, tree_char):
            return {"commit": commit_char * 40, "tree": tree_char * 40, "digest": commit_char * 64}
        identities = {name: sealed(commit_char, tree_char) for name, commit_char, tree_char in zip(run_index._IDENTITY_NAMES, "1234567", "2345678", strict=True)}
        old = {**identities, "cli": {"id": "codex-cli", "digest": "8" * 64}, "model": {"id": "gpt-5.5", "digest": "9" * 64}, "reasoning": {"id": "medium", "digest": "a" * 64}, "tools": {"digest": "b" * 64}, "host": {"digest": "c" * 64}, "schedule": {"seed": runner.SCHEDULE_SEED, "digest": "d" * 64}}
        repaired = json.loads(json.dumps(old)); repaired["candidate"] = sealed("a", "b"); repaired["runner"] = sealed("c", "d")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"; root.mkdir(); subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            marker = f"AQ7-RUN-AUTHORITY corpus={old['corpus']['commit']} status=unconsumed"
            (root / "EXECPLAN.md").write_text(marker + "\n", encoding="utf-8")
            subprocess.run(["git", "add", "EXECPLAN.md"], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=AQ7", "-c", "user.email=aq7@example.invalid", "commit", "-qm", "authority"], cwd=root, check=True)
            index = run_index.AQ7RunIndex(root)
            old_cap = index.begin_canary(old, unconsumed_marker=marker)
            index.retry_canary(old, unconsumed_marker=marker, canary_cap=old_cap, reason="precompletion_infrastructure")
            index.fail_canary(old, unconsumed_marker=marker, canary_cap=old_cap, reason="retry_exhausted")
            self.assertEqual((index.state(old)["canary_status"], index.state(old)["corpus_status"]), ("failed", "unconsumed"))
            repaired_cap = index.begin_canary(repaired, unconsumed_marker=marker)
            self.assertIsInstance(repaired_cap, bytes)
            with self.assertRaises(run_index.RunIndexError):
                index.begin_canary(repaired, unconsumed_marker=marker)

    def test_real_committed_preflight_canary_then_exact_80_batch_with_fake_child(self):
        with committed_fixture() as (root, commit):
            state = runner.preflight(root, commit)
            self.assertEqual((len(state["cases"]), len(state["schedule"])), (40, 80))
            self.assertEqual({row["condition"] for row in state["schedule"]}, {"current", "reduced"})
            calls = []
            def child(argv, *, cwd, input, **_kwargs):
                self.assertTrue(Path(cwd).is_dir() and not any(Path(cwd).iterdir()))
                packet = json.loads(input); calls.append((argv, cwd, packet))
                facts = [{"predicate_id": name, "state": "absent"} for name in packet["predicate_order"]]
                return SimpleNamespace(returncode=0, stdout=events({"predicate_facts": facts}, thread=f"ctx-{len(calls)}"))
            info = {"id": "codex-cli", "path": sys.executable, "version": "fake", "digest": runner.sha256_file(Path(sys.executable))}
            with mock.patch.object(runner, "codex_preflight", return_value=info):
                canary = runner.run_canary(root=root, candidate_commit=commit, codex="fake", invoke=child)
                batch = runner.execute_trials(root=root, candidate_commit=commit, codex="fake", invoke=child)
            self.assertEqual(canary["status"], "passed")
            self.assertEqual(batch["status"], "failed")
            self.assertEqual(len(calls), 81)
            self.assertEqual(len({row[1] for row in calls}), 81)
            self.assertTrue(all("--ephemeral" in row[0] and "--skip-git-repo-check" in row[0] and "read-only" in row[0] for row in calls))
            self.assertTrue(all(tuple(row[2]) == ("instruction", "task_text", "predicate_order", "condition_guidance") for row in calls))
            runtime_path = str(root / candidate_checker.RUNTIME_SELECTOR_SCHEMA)
            semantic_path = str(root / candidate_checker.SELECTOR_SCHEMA)
            self.assertTrue(all(row[0][row[0].index("--output-schema") + 1] == runtime_path for row in calls))
            self.assertTrue(all(semantic_path not in row[0] for row in calls))
            self.assertEqual([row[2]["condition_guidance"] for row in calls[1:]].count(calls[1][2]["condition_guidance"]), 40)
            self.assertEqual(batch["live_calls"], 80)


if __name__ == "__main__": unittest.main()
