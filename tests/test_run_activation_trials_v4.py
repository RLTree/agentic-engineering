from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_module(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load_module("scripts/check_reduced_four_skill_candidate_v4.py", "aq4_checker_runner_test")
scorer = load_module("scripts/score_activation_v4.py", "aq4_scorer_runner_test")
runner = load_module("scripts/run_activation_trials_v4.py", "aq4_runner_test")


def event_stream(selection):
    lines = [
        {"type": "thread.started", "thread_id": "synthetic-thread"},
        {"type": "turn.started"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps({"selected_decision_atoms": selection})}},
        {"type": "turn.completed"},
    ]
    return b"\n".join(json.dumps(line).encode() for line in lines)


class RunnerV4Tests(unittest.TestCase):
    def test_selector_packet_excludes_labels_mapping_and_adviser_catalog(self) -> None:
        candidate = checker.load_candidate(ROOT)
        packet = runner.selector_packet(scorer=scorer, task="Synthetic task text.", catalog=candidate["conditions"]["current"]["atom_catalog"], constraint={"status": "none", "atom_id": None})
        value = json.loads(packet)
        self.assertEqual(set(value), {"instruction", "task", "decision_atom_catalog", "explicit_constraint"})
        self.assertNotIn("hidden_labels", packet)
        self.assertNotIn("atom_to_adviser", packet)
        self.assertNotIn("adviser_id", packet)
        self.assertIn("direct instance", value["instruction"])
        for row in value["decision_atom_catalog"]:
            self.assertEqual(len(row["pairwise_exclusions"]), 3)

    def test_closed_selection_parser_handles_none_one_two_and_reds(self) -> None:
        for selection in ([], [checker.ATOMS[0]], list(checker.ATOMS[:2])):
            parsed, context = runner.parse_events(event_stream(selection), checker.ATOMS)
            self.assertEqual(parsed, selection)
            self.assertEqual(context, "synthetic-thread")
        with self.assertRaisesRegex(runner.RunnerError, "fixed atom contract"):
            runner.parse_events(event_stream(["invalid-atom"]), checker.ATOMS)
        with self.assertRaisesRegex(runner.RunnerError, "fixed atom contract"):
            runner.parse_events(event_stream([checker.ATOMS[0], checker.ATOMS[0]]), checker.ATOMS)

    def test_content_never_retries_and_canary_may_retry_once(self) -> None:
        calls = []
        def invoke(_argv, **_kwargs):
            calls.append(1)
            return SimpleNamespace(stdout=b"not-json", stderr=b"", returncode=1)
        with self.assertRaises(runner.InfrastructureError):
            runner.run_one(argv_factory=lambda: ["synthetic"], packet="{}", invoke=invoke, before_invoke=lambda: None, allow_retry=False)
        self.assertEqual(len(calls), 1)
        calls.clear()
        with self.assertRaises(runner.InfrastructureError):
            runner.run_one(argv_factory=lambda: ["synthetic"], packet="{}", invoke=invoke, before_invoke=lambda: None, allow_retry=True)
        self.assertEqual(len(calls), 2)

    def test_child_contract_is_prompt_only_read_only_and_no_approval(self) -> None:
        argv = runner.child_argv("/synthetic/codex", "/synthetic/empty", ROOT / runner.SELECTOR_SCHEMA_PATH)
        rendered = " ".join(argv)
        for required in ("--ask-for-approval never", "--ephemeral", "--ignore-user-config", "--strict-config", "--sandbox read-only", "--output-schema"):
            self.assertIn(required, rendered)
        self.assertNotIn("--full-auto", rendered)

    def test_injected_unbound_manifest_stops_before_any_codex_call(self) -> None:
        candidate = checker.load_candidate(ROOT)
        candidate["corpus"]["commit"] = "UNBOUND_AQ4_CORPUS_COMMIT"
        with self.assertRaisesRegex(ValueError, "live execution is unbound"):
            checker.require_bound(candidate)

    def test_custody_drift_before_child_yields_zero_invoke(self) -> None:
        codex_path = Path(sys.executable).resolve()
        info = {"path": str(codex_path), "sha256": runner.sha256_file(codex_path), "version": "synthetic"}
        for drift in ("synthetic evaluator drift", "synthetic selector schema drift"):
            calls = []
            def invoke(*_args, **_kwargs):
                calls.append(1)
                return SimpleNamespace(stdout=event_stream([]), stderr=b"", returncode=0)
            with self.assertRaisesRegex(runner.RunnerError, drift):
                runner.invoke_packet(codex_info=info, packet="{}", invoke=invoke, allow_retry=False, custody_recheck=lambda drift=drift: (_ for _ in ()).throw(runner.RunnerError(drift)))
            self.assertEqual(calls, [])

    def test_canary_result_contains_no_child_context_identifier(self) -> None:
        result = runner.canary_result([])
        self.assertTrue(result["fresh_context_observed"])
        self.assertNotIn("context_id", result)
        self.assertNotIn("thread_id", result)

    def test_live_state_failure_stops_before_codex_probe(self) -> None:
        with mock.patch.object(runner, "_live_state", side_effect=runner.RunnerError("synthetic corpus invalid")), mock.patch.object(runner, "codex_preflight") as probe:
            with self.assertRaisesRegex(runner.RunnerError, "synthetic corpus invalid"):
                runner.run_canary(root=ROOT, candidate_commit="HEAD", codex="codex")
            probe.assert_not_called()

    def test_preflight_reads_validator_from_candidate_and_documents_from_corpus(self) -> None:
        candidate_commit, corpus_commit, corpus_tree = "c" * 40, "f" * 40, "e" * 40
        validator_path = checker.CORPUS_VALIDATOR_PATH
        document_paths = (checker.CORPUS_SCHEMA_PATH, checker.CORPUS_AUTHORING_PATH, checker.CORPUS_HELDOUT_PATH)
        content = {validator_path: b"synthetic validator", document_paths[0]: b"synthetic schema", document_paths[1]: b"synthetic authoring", document_paths[2]: b"synthetic heldout"}
        corpus = {"commit": corpus_commit, "tree": corpus_tree, "validator_source": "candidate_commit", "validator_path": validator_path, "validator_sha256": runner.sha256_bytes(content[validator_path]), "schema_path": document_paths[0], "schema_sha256": runner.sha256_bytes(content[document_paths[0]]), "authoring_path": document_paths[1], "authoring_sha256": runner.sha256_bytes(content[document_paths[1]]), "heldout_path": document_paths[2], "heldout_sha256": runner.sha256_bytes(content[document_paths[2]])}
        candidate = {"corpus": corpus, "evaluator_surface": {"files": [{"path": validator_path, "sha256": corpus["validator_sha256"]}]}}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative, raw in content.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            calls = []
            def show(_root, commit, relative):
                calls.append((commit, relative))
                if relative == validator_path:
                    if commit != candidate_commit:
                        raise AssertionError("validator requested from corpus commit")
                elif commit != corpus_commit:
                    raise AssertionError("corpus document requested from candidate commit")
                return content[relative]
            with mock.patch.object(runner, "require_live_head_and_clean"), mock.patch.object(runner, "git_identity", return_value=(corpus_commit, corpus_tree)), mock.patch.object(runner, "git_show", side_effect=show):
                runner.immutable_preflight(root, candidate_commit, candidate)
            self.assertIn((candidate_commit, validator_path), calls)
            self.assertNotIn((corpus_commit, validator_path), calls)
            for relative in document_paths:
                self.assertIn((corpus_commit, relative), calls)

            wrong = {**candidate, "corpus": {**corpus, "validator_source": "corpus_commit"}}
            with mock.patch.object(runner, "require_live_head_and_clean"), mock.patch.object(runner, "git_identity", return_value=(corpus_commit, corpus_tree)), mock.patch.object(runner, "git_show") as show_mock:
                with self.assertRaisesRegex(runner.RunnerError, "exact candidate commit"):
                    runner.immutable_preflight(root, candidate_commit, wrong)
                show_mock.assert_not_called()

            with mock.patch.object(runner, "require_live_head_and_clean"), mock.patch.object(runner, "git_identity", return_value=(corpus_commit, corpus_tree)), mock.patch.object(runner, "git_show", side_effect=runner.RunnerError("candidate validator missing")):
                with self.assertRaisesRegex(runner.RunnerError, "candidate validator missing"):
                    runner.immutable_preflight(root, candidate_commit, candidate)

            (root / validator_path).write_bytes(b"drift")
            with mock.patch.object(runner, "require_live_head_and_clean"), mock.patch.object(runner, "git_identity", return_value=(corpus_commit, corpus_tree)), mock.patch.object(runner, "git_show", side_effect=show):
                with self.assertRaisesRegex(runner.RunnerError, "live evaluator input"):
                    runner.immutable_preflight(root, candidate_commit, candidate)

    def test_default_cli_is_zero_call_and_tracks_exact_clean_candidate(self) -> None:
        committed = subprocess.run(
            ["git", "show", "HEAD:scripts/run_activation_trials_v4.py"],
            cwd=ROOT, capture_output=True,
        )
        clean = not subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout
        exact = committed.returncode == 0 and committed.stdout == (ROOT / "scripts/run_activation_trials_v4.py").read_bytes()
        result = subprocess.run(["python3", "scripts/run_activation_trials_v4.py", "--dry-run"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0 if exact and clean else 2)
        if exact and clean:
            payload = json.loads(result.stdout)
            self.assertEqual(payload["live_calls"], 0)
            self.assertFalse(payload["raw_trajectories_persisted"])
        else:
            self.assertIn("HOLD:", result.stderr)


if __name__ == "__main__":
    unittest.main()
