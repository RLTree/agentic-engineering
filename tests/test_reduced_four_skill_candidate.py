from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_reduced_four_skill_candidate as checker  # noqa: E402


class ReducedFourCandidateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.path = ROOT / checker.MANIFEST_PATH
        self.candidate = json.loads(self.path.read_text(encoding="utf-8"))

    def errors_for(self, mutate):
        candidate = copy.deepcopy(self.candidate)
        mutate(candidate)
        return checker.validate_candidate(candidate, ROOT)

    def assert_error(self, errors, text: str) -> None:
        self.assertTrue(any(text in error for error in errors), errors)

    def test_working_draft_passes(self) -> None:
        self.assertEqual(checker.validate_candidate(self.candidate, ROOT), [])

    def test_source_reference_and_fixture_digest_reds(self) -> None:
        self.assert_error(self.errors_for(lambda d: d["skills"][0]["current"].__setitem__("skill_sha256", "0" * 64)), "current skill_path digest mismatch")
        self.assert_error(self.errors_for(lambda d: d["skills"][1]["references"][0].__setitem__("sha256", "0" * 64)), "frozen reference digest mismatch")
        self.assert_error(self.errors_for(lambda d: d["skills"][2]["reduced"].__setitem__("yaml_sha256", "0" * 64)), "reduced YAML digest mismatch")
        self.assert_error(self.errors_for(lambda d: d["skills"][1]["current"].__setitem__("yaml_sha256", "0" * 64)), "current yaml_path digest mismatch")
        self.assert_error(self.errors_for(lambda d: d["evaluator_surface"]["files"][3].__setitem__("sha256", "0" * 64)), "evaluator surface digest mismatch")

    def test_source_tree_and_identical_condition_digest_reds(self) -> None:
        self.assertEqual(self.candidate["source"], {"commit": checker.SOURCE_COMMIT, "tree": checker.SOURCE_TREE})
        self.assertEqual(
            {key: self.candidate["corpus"][key] for key in ("commit", "tree")},
            {"commit": checker.CORPUS_COMMIT, "tree": checker.CORPUS_TREE},
        )
        self.assert_error(self.errors_for(lambda d: d["source"].__setitem__("tree", "0" * 40)), "source tree mismatch")
        self.assert_error(self.errors_for(lambda d: d["conditions"]["reduced"].__setitem__("condition_input_sha256", d["conditions"]["current"]["condition_input_sha256"])), "input digests must differ")

    def test_reference_limit_coverage_context_and_schema_payload_reds(self) -> None:
        self.assert_error(self.errors_for(lambda d: d["skills"][3]["references"].append(copy.deepcopy(d["skills"][3]["references"][0]))), "zero to three")
        self.assert_error(self.errors_for(lambda d: d["skills"][3]["references"].__setitem__(slice(None), d["skills"][3]["references"][:1])), "coverage gap")
        self.assert_error(self.errors_for(lambda d: d["skills"][1]["reduced"].__setitem__("context_id", "")), "context IDs")
        self.assert_error(self.errors_for(lambda d: d["skills"][0]["references"][0].__setitem__("full_schema_or_template", True)), "compact non-schema/template")

    def test_aq3_exactly_two_payload_limit_reds(self) -> None:
        def errors_with_ref_mutation(mutate):
            candidate = copy.deepcopy(self.candidate)
            mutate(candidate)
            for condition in ("current", "reduced"):
                candidate["conditions"][condition]["condition_input_sha256"] = checker.condition_input_digest(candidate, condition, ROOT)
            return checker.validate_candidate(candidate, ROOT)

        def a029(data):
            data["skills"][1]["references"][1]["trigger_ids"] = ["no-change-abstention"]
        self.assert_error(errors_with_ref_mutation(a029), "AQ3-H-029")

        def generic(data):
            data["skills"][0]["references"][1]["trigger_ids"] = ["decomposition-boundary"]
        self.assert_error(errors_with_ref_mutation(generic), "corpus trigger coverage gap")

    def test_yaml_frontmatter_router_and_forbidden_content_reds(self) -> None:
        yaml = 'interface:\n  display_name: "Agentic Engineering"\n  short_description: "x"\n  brand_color: "#0F766E"\n  default_prompt: "Use $agentic-engineering-lifecycle:agentic-engineering only as proposal-only. Do not act."\npolicy:\n  allow_implicit_invocation: true\n'
        yaml_errors = []
        checker._validate_yaml_identity(checker._parse_yaml(yaml.encode()), "agentic-engineering", "Agentic Engineering", "$agentic-engineering-lifecycle:agentic-engineering", True, yaml_errors)
        self.assertTrue(yaml_errors)
        frontmatter = b'---\nname: wrong\ndescription: "x"\n---\n'
        self.assertEqual(checker._parse_frontmatter(frontmatter)["name"], "wrong")
        self.assertFalse(checker.router_has_explicit_deferrals("Defer to a specialist."))
        problems = checker.forbidden_content("Version 3\nShared references\nThis skill grants completion authority.")
        self.assertIn("Version 3 content", problems)
        self.assertIn("shared-reference content", problems)
        self.assertIn("effect/adoption/completion/efficacy/claim authority", problems)
        self.assertEqual(checker.forbidden_content("Do not grant authority or claim completion."), [])

    def test_unexpected_overlay_inventory_red(self) -> None:
        with patch.object(checker, "_overlay_inventory", return_value={checker.MANIFEST_PATH, f"{checker.OVERLAY}/unexpected.txt"}):
            self.assert_error(checker.validate_candidate(self.candidate, ROOT), "overlay inventory mismatch")

    def test_parent_resolver_is_deterministic_and_parent_owned(self) -> None:
        resolved = checker.resolve_parent_payloads(self.candidate, {"architecture-boundary", "verification-evidence"}, ["agentic-engineering", "verification-strategy-engineering"])
        self.assertEqual([item["payload_id"] for item in resolved], sorted(item["payload_id"] for item in resolved))
        self.assertTrue(all(set(item) == {"payload_id", "owner_adviser_id", "source_path", "sha256", "trigger_ids", "content_class", "full_schema_or_template"} for item in resolved))

    def test_schema_permitted_capacity_overflow_must_use_the_closed_form(self) -> None:
        breach = {"status": "cap_exceeded", "resolved_count": 3, "records": []}
        with patch.object(checker, "resolve_parent_payload_resolution", return_value=breach):
            errors = checker.validate_candidate(self.candidate, ROOT)
        self.assert_error(errors, "resolver capacity overflow is not closed")

    def test_exhaustive_capacity_proof_detects_more_than_three_trigger_overflow(self) -> None:
        required = {"architecture-boundary", "decision-contract", "decomposition-boundary", "no-change-abstention"}
        outcome = checker.resolve_parent_payload_resolution(self.candidate, required, ["agentic-engineering", "codex-task-contract"])
        self.assertEqual((outcome["status"], outcome["resolved_count"], outcome["records"]), ("cap_exceeded", 4, []))
        self.assertIn("range(len(TRIGGER_ORDER) + 1)", (ROOT / "scripts/check_reduced_four_skill_candidate.py").read_text(encoding="utf-8"))

    def test_condition_digests_are_deterministic_and_distinct(self) -> None:
        descriptor = checker.condition_input_descriptor(self.candidate, "current", ROOT)
        self.assertEqual(descriptor["parent_resolver"], {"policy": "minimum-trigger-cover", "max_payloads": 3})
        self.assertEqual(checker.condition_input_digest(self.candidate, "current", ROOT), self.candidate["conditions"]["current"]["condition_input_sha256"])
        self.assertEqual(checker.condition_input_digest(self.candidate, "reduced", ROOT), self.candidate["conditions"]["reduced"]["condition_input_sha256"])
        self.assertNotEqual(self.candidate["conditions"]["current"]["condition_input_sha256"], self.candidate["conditions"]["reduced"]["condition_input_sha256"])

    def test_evaluator_schema_requires_resolved_records_and_selector_packet(self) -> None:
        schema = json.loads((ROOT / "evals/foundation-v4/activation-evaluator-schema.json").read_text(encoding="utf-8"))
        broken = copy.deepcopy(schema)
        broken["$defs"]["observation"]["required"].remove("resolved_payloads")
        errors = []
        checker._validate_evaluator_schema(broken, errors)
        self.assertTrue(errors, errors)
        self.assertIn("selector packet or resolved payload records", errors[0])

    def test_evaluator_schema_mechanically_requires_schedule_index_and_payload_caps(self) -> None:
        schema = json.loads((ROOT / "evals/foundation-v4/activation-evaluator-schema.json").read_text(encoding="utf-8"))
        errors = []
        checker._validate_evaluator_schema(schema, errors)
        self.assertEqual(errors, [])
        broken = copy.deepcopy(schema)
        broken["$defs"]["payloadResolution"]["oneOf"][0]["properties"]["resolved_count"]["maximum"] = 4
        errors = []
        checker._validate_evaluator_schema(broken, errors)
        self.assertIn("evaluator schema payload resolution status/count is not closed", errors)
        broken = copy.deepcopy(schema)
        broken["$defs"]["execution"]["properties"]["runner_path"] = {"type": "string"}
        errors = []
        checker._validate_evaluator_schema(broken, errors)
        self.assertIn("evaluator schema lacks exact runner path or nonblank schedule seed", errors)

    def test_future_corpus_validator_is_closed_evaluator_surface_with_fixed_digest(self) -> None:
        entry = next(item for item in self.candidate["evaluator_surface"]["files"] if item["path"] == "scripts/validate_future_activation_corpus_v3.py")
        self.assertEqual(entry["sha256"], checker.FUTURE_CORPUS_VALIDATOR_SHA256)

    def test_historical_v1_validator_rejects_invalid_lineage_shape(self) -> None:
        schema = json.loads(subprocess.check_output(["git", "show", f"{checker.SOURCE_COMMIT}:evals/foundation-v4/activation-schema.json"], cwd=ROOT))
        corpus = json.loads(subprocess.check_output(["git", "show", f"{checker.SOURCE_COMMIT}:evals/foundation-v4/activation-authoring.json"], cwd=ROOT))
        corpus["schema_version"] = "broken"
        errors = []
        checker._validate_frozen_corpus(schema, corpus, "authoring", errors)
        self.assertTrue(any("fails Draft202012Validator" in error for error in errors), errors)

    def test_committed_loader_cannot_be_changed_by_simultaneous_live_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            committed = repo / checker.MANIFEST_PATH
            committed.parent.mkdir(parents=True)
            committed.write_text(json.dumps({"schema_version": "committed"}), encoding="utf-8")
            fixture = repo / f"{checker.OVERLAY}/skills/x/SKILL.md"
            fixture.parent.mkdir(parents=True)
            fixture.write_text("committed fixture", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "snapshot"], cwd=repo, check=True)
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
            committed.write_text("{}", encoding="utf-8")
            fixture.write_text("tampered fixture", encoding="utf-8")
            self.assertEqual(checker.load_candidate_from_commit(repo, commit), {"schema_version": "committed"})

    def test_default_and_working_cli_are_zero_write(self) -> None:
        targets = sorted({
            *[path for path in (ROOT / checker.OVERLAY).rglob("*") if path.is_file()],
            ROOT / "evals/foundation-v4/future-activation-v3/activation-schema.json",
            ROOT / "evals/foundation-v4/future-activation-v3/activation-authoring.json",
            ROOT / "evals/foundation-v4/future-activation-v3/activation-heldout.json",
            ROOT / "evals/foundation-v4/activation-evaluator-schema.json",
            ROOT / "evals/foundation-v4/selector-output-schema.json",
            ROOT / "scripts/check_reduced_four_skill_candidate.py",
            ROOT / "scripts/score_activation.py",
            ROOT / "scripts/run_activation_trials.py",
        })
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in targets}
        status_before = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT)
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        default = subprocess.run([sys.executable, str(ROOT / "scripts/check_reduced_four_skill_candidate.py")], cwd=ROOT, capture_output=True, text=True, check=False, env=env)
        draft = subprocess.run([sys.executable, str(ROOT / "scripts/check_reduced_four_skill_candidate.py"), "--working-tree"], cwd=ROOT, capture_output=True, text=True, check=False, env=env)
        if default.returncode == 0:
            self.assertEqual(default.returncode, 0, default.stderr)
            self.assertIn("PASS: COMMITTED structural custody", default.stdout)
        else:
            self.assertNotEqual(default.returncode, 0)
            self.assertIn("HOLD:", default.stderr)
        self.assertEqual(draft.returncode, 0, draft.stderr)
        self.assertIn("PASS: DRAFT structural custody", draft.stdout)
        self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns) for path in targets}, before)
        self.assertEqual(subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT), status_before)


if __name__ == "__main__":
    unittest.main()
