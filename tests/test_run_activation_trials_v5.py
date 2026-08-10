from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative); assert spec and spec.loader; module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


checker = load("scripts/check_reduced_four_skill_candidate_v5.py", "aq5_checker_runner_test")
scorer = load("scripts/score_activation_v5.py", "aq5_scorer_runner_test")
runner = load("scripts/run_activation_trials_v5.py", "aq5_runner_test")
fixtures = load("tests/test_activation_evaluator_v5.py", "aq5_fixture_helpers")


def events(selection):
    rows = [{"type": "thread.started", "thread_id": "aq5-synthetic-thread"}, {"type": "turn.started"}, {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps({"selected_decision_atoms": selection})}}, {"type": "turn.completed"}]
    return b"\n".join(json.dumps(row).encode() for row in rows)


class RunnerV5Tests(unittest.TestCase):
    def test_positive_observation_uses_top_level_reference_triggers(self):
        candidate = checker.load_candidate(ROOT); base, _ = checker.load_base(ROOT); case = fixtures.case("AQ5-H-001"); h2 = checker.conditions(candidate); contract = {"runner_protocol_sha256": "a" * 64}; info = {"path": str(Path(sys.executable).resolve()), "version": "synthetic", "sha256": runner.sha256_file(Path(sys.executable).resolve())}
        calls = []
        def invoke(*_args, **_kwargs): calls.append(1); return SimpleNamespace(stdout=events(["task-contract"]), stderr=b"", returncode=0)
        observation = runner.trial_observation(checker=checker, scorer=scorer, candidate=candidate, base=base, case=case, condition="current", index=0, contract=contract, info=info, invoke=invoke, custody=lambda: None)
        self.assertEqual(calls, [1]); self.assertEqual(observation["selected_decision_atoms"], ["task-contract"]); self.assertEqual(observation["effective_mapped_advisers"], ["codex-task-contract"]); self.assertEqual(observation["corpus_prompt_sha256"], case["prompt_sha256"]); self.assertEqual(observation["task_sha256"], runner.sha256_bytes(case["prompt"].encode())); self.assertEqual(observation["atom_catalog_sha256"], runner.sha256_json(h2["current"]["atom_catalog"]))

    def test_missing_or_renested_triggers_stop_before_invoke(self):
        candidate = checker.load_candidate(ROOT); base, _ = checker.load_base(ROOT); info = {"path": str(Path(sys.executable).resolve()), "version": "synthetic", "sha256": runner.sha256_file(Path(sys.executable).resolve())}; calls = []
        def invoke(*_args, **_kwargs): calls.append(1); return SimpleNamespace(stdout=events([]), stderr=b"", returncode=0)
        for mutation in ("missing", "nested"):
            case = fixtures.case("AQ5-H-001")
            if mutation == "missing": del case["reference_triggers"]
            else: case["hidden_labels"] = {"reference_triggers": case.pop("reference_triggers")}
            with self.assertRaisesRegex(ValueError, "top-level shape"):
                runner.trial_observation(checker=checker, scorer=scorer, candidate=candidate, base=base, case=case, condition="current", index=0, contract={"runner_protocol_sha256": "a" * 64}, info=info, invoke=invoke, custody=lambda: None)
        self.assertEqual(calls, [])

    def test_full_zero_model_label_and_scorer_preflight_is_40x2(self):
        envelope, profile = fixtures.envelope_and_profile(); commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(); tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        result = runner.zero_model_label_preflight(root=ROOT, checker=checker, scorer=scorer, candidate=profile["candidate"], base=profile["base"], cases=profile["cases"], corpus=profile["corpus"], commit=commit, tree=tree)
        self.assertEqual(result, {"status": "pass", "qualification_cases": 40, "presentations": 80, "live_calls": 0, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown"})
        broken = dict(profile["cases"]); first = next(iter(broken)); broken[first] = dict(broken[first]); broken[first]["hidden_labels"] = {"reference_triggers": broken[first].pop("reference_triggers")}
        with self.assertRaisesRegex(ValueError, "top-level shape"):
            runner.zero_model_label_preflight(root=ROOT, checker=checker, scorer=scorer, candidate=profile["candidate"], base=profile["base"], cases=broken, corpus=profile["corpus"], commit=commit, tree=tree)

    def test_real_frozen_document_metadata_and_top_level_label_shape_are_validated_before_probe(self):
        document = json.loads((ROOT / "evals/foundation-v4/future-activation-v5/activation-heldout.json").read_text())
        self.assertEqual(document["schema_version"], "aq5-activation-corpus-v5")
        checker.validate_document_shape(document)
        wrong_version = dict(document); wrong_version["schema_version"] = "5.0"
        with self.assertRaises(ValueError): checker.validate_document_shape(wrong_version)
        nested = json.loads(json.dumps(document)); nested["cases"][0]["hidden_labels"] = {"reference_triggers": nested["cases"][0].pop("reference_triggers")}
        with self.assertRaises(ValueError): checker.validate_document_shape(nested)

    def test_content_never_retries_but_canary_transport_can_retry_once(self):
        calls = []
        def invoke(*_args, **_kwargs): calls.append(1); return SimpleNamespace(stdout=b"malformed", stderr=b"", returncode=1)
        with self.assertRaises(runner.ChildExecutionError): runner.run_one(argv_factory=lambda: ["synthetic"], packet="{}", invoke=invoke, before_invoke=lambda: None, allow_retry=False)
        self.assertEqual(len(calls), 1); calls.clear()
        with self.assertRaises(runner.ChildExecutionError): runner.run_one(argv_factory=lambda: ["synthetic"], packet="{}", invoke=invoke, before_invoke=lambda: None, allow_retry=True)
        self.assertEqual(len(calls), 2)

    def test_preflight_failure_precedes_codex_probe(self):
        with mock.patch.object(runner, "live_state", side_effect=runner.RunnerError("shape mismatch")), mock.patch.object(runner, "codex_preflight") as probe:
            with self.assertRaises(runner.RunnerError): runner.run_canary(root=ROOT, candidate_commit="HEAD", codex="codex")
            probe.assert_not_called()

    def test_live_scorer_insufficiency_is_terminal_not_success(self):
        with self.assertRaisesRegex(runner.ChildExecutionError, "live score unavailable"):
            runner.require_live_score({"status": "insufficient_data"})
        envelope, profile = fixtures.envelope_and_profile(); accepted = scorer.score(envelope, ROOT, profile=profile); accepted["status"] = "fail"
        self.assertIs(runner.require_live_score(accepted), accepted)
        malformed = dict(accepted); malformed["unexpected"] = True
        with self.assertRaisesRegex(runner.ChildExecutionError, "live score unavailable"): runner.require_live_score(malformed)
        legacy = dict(accepted); legacy["raw_trajectories_persisted"] = legacy.pop("runner_local_raw_trajectories_persisted")
        with self.assertRaisesRegex(runner.ChildExecutionError, "live score unavailable"): runner.require_live_score(legacy)
        provider_claim = dict(accepted); provider_claim["provider_raw_trajectory_retention_status"] = "retained"
        with self.assertRaisesRegex(runner.ChildExecutionError, "claim promotion"): runner.require_live_score(provider_claim)

    def test_canary_receipt_closes_context_and_raw_retention_claims(self):
        receipt = runner.canary_result([], context_id_received=True)
        self.assertEqual(set(receipt), {"stage", "protocol", "mode", "status", "ephemeral_context_requested", "context_id_received", "selected_decision_atoms", "provider_identity_proven", "runner_local_raw_trajectories_persisted", "provider_raw_trajectory_retention_status", "maximum_claim"})
        self.assertIs(receipt["ephemeral_context_requested"], True)
        self.assertIs(receipt["context_id_received"], True)
        self.assertFalse(receipt["runner_local_raw_trajectories_persisted"])
        self.assertEqual(receipt["provider_raw_trajectory_retention_status"], "unknown")
        self.assertNotIn("context_id", receipt)
        self.assertNotIn("thread_id", receipt)

    def test_direct_launch_oserror_is_distinct_from_post_launch_child_failure(self):
        def launch_error(*_args, **_kwargs): raise OSError("missing executable")
        with self.assertRaises(runner.LaunchError):
            runner.run_one(argv_factory=lambda: ["synthetic"], packet="{}", invoke=launch_error, before_invoke=lambda: None, allow_retry=True)
        with self.assertRaises(runner.ChildExecutionError):
            runner.run_one(argv_factory=lambda: ["synthetic"], packet="{}", invoke=lambda *_args, **_kwargs: SimpleNamespace(stdout=b"malformed", stderr=b"", returncode=1), before_invoke=lambda: None, allow_retry=False)

    def test_error_receipts_distinguish_launch_child_and_generic_mid_batch_safe(self):
        def receipt_for(side_effect, mode):
            stdout = io.StringIO()
            with mock.patch.object(runner, mode, side_effect=side_effect), mock.patch("sys.stdout", stdout):
                code = runner.main(["--canary" if mode == "run_canary" else "--execute", "--usage-approval", "test"])
            return code, json.loads(stdout.getvalue())
        code, launch = receipt_for(runner.LaunchError("missing"), "run_canary")
        self.assertEqual(code, 2); self.assertEqual(launch["status"], "launch_failed"); self.assertFalse(launch["failed_child_started"])
        code, child = receipt_for(runner.ChildExecutionError("malformed"), "run_canary")
        self.assertEqual(code, 2); self.assertEqual(child["status"], "child_failed"); self.assertTrue(child["failed_child_started"])
        code, generic = receipt_for(runner.RunnerError("score closure"), "execute_trials")
        self.assertEqual(code, 2); self.assertEqual(generic["status"], "runner_failed"); self.assertNotIn("live_calls", generic); self.assertNotIn("failed_child_started", generic)
        for receipt in (launch, child, generic):
            self.assertFalse(receipt["runner_local_raw_trajectories_persisted"]); self.assertEqual(receipt["provider_raw_trajectory_retention_status"], "unknown"); self.assertNotIn("prompt", receipt); self.assertNotIn("selection", receipt)


if __name__ == "__main__": unittest.main()
