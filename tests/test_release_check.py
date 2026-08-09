from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import package_validation
from package_validation import (
    CLAIM_STATES,
    Candidate,
    CheckResult,
    PACKAGE_SET_VERSION,
    REQUIRED_CHECK_IDS,
    capture_candidate,
    render_release_result,
    run_structural_release,
    validate,
    validate_release_result,
)


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class ReleaseCheckContractTests(unittest.TestCase):
    def _git(self, root: Path, *arguments: str) -> None:
        subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )

    def _release_root(self) -> Path:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for name in (
            "agentic-engineering",
            "agentic-engineering-lifecycle",
            "agentic-engineering-rust",
            "agentic-engineering-systems",
        ):
            shutil.copytree(SOURCE_ROOT / "plugins" / name, root / "plugins" / name)
        shutil.copytree(SOURCE_ROOT / ".agents", root / ".agents")
        shutil.copytree(SOURCE_ROOT / "profiles", root / "profiles")
        (root / ".gitignore").write_text("ignored-input.txt\n", encoding="utf-8")
        self._git(root, "init", "--quiet")
        self._git(root, "add", ".")
        self._git(
            root,
            "-c",
            "user.name=Release Test",
            "-c",
            "user.email=release-test@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "candidate",
        )
        return root

    def _result(self, root: Path) -> dict:
        return run_structural_release(root)

    def test_release_result_is_exact_structural_full_scope(self) -> None:
        result = self._result(self._release_root())
        self.assertEqual(result["candidate"].keys(), {"commit", "tree", "validation_input_digest"})
        self.assertEqual(tuple(item["id"] for item in result["checks"]), REQUIRED_CHECK_IDS)
        self.assertNotIn("gates", result)
        self.assertNotIn("check_count", result)
        self.assertEqual(result["claim_states"], CLAIM_STATES)
        self.assertEqual(result["claim_states"]["structural_package"], "observed")
        self.assertTrue(
            all(value == "unobserved" for key, value in result["claim_states"].items() if key != "structural_package")
        )
        self.assertEqual(result["package_set"]["package_set_version"], PACKAGE_SET_VERSION)
        self.assertTrue(all(check["observations"] for check in result["checks"]))

    def test_count_is_derived_and_forged_count_is_rejected(self) -> None:
        result = self._result(self._release_root())
        result["executed_check_count"] = 0
        with self.assertRaisesRegex(ValueError, "count differs"):
            validate_release_result(result)
        result.pop("executed_check_count")
        result["gates"] = 1
        with self.assertRaisesRegex(ValueError, "never reported"):
            validate_release_result(result)

    def test_missing_required_package_fails_release(self) -> None:
        root = self._release_root()
        shutil.rmtree(root / "plugins" / "agentic-engineering-rust")
        self._git(root, "add", "-A")
        self._git(
            root,
            "-c",
            "user.name=Release Test",
            "-c",
            "user.email=release-test@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "remove package",
        )
        with self.assertRaisesRegex(ValueError, "package set|missing"):
            self._result(root)

    def test_manifest_version_mismatch_fails_release(self) -> None:
        root = self._release_root()
        manifest_path = root / "plugins" / "agentic-engineering" / ".codex-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = "4.0.1"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self._git(root, "add", ".")
        self._git(
            root,
            "-c",
            "user.name=Release Test",
            "-c",
            "user.email=release-test@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "version mismatch",
        )
        with self.assertRaisesRegex(ValueError, "identity"):
            self._result(root)

    def test_duplicate_skill_identity_fails_release(self) -> None:
        root = self._release_root()
        skills = root / "plugins" / "agentic-engineering-rust" / "skills"
        original = skills / "rust-agent-runtime"
        duplicate = skills / "codex-task-contract"
        original.rename(duplicate)
        skill = duplicate / "SKILL.md"
        skill.write_text(
            skill.read_text(encoding="utf-8").replace(
                "name: rust-agent-runtime", "name: codex-task-contract", 1
            ),
            encoding="utf-8",
        )
        agent = duplicate / "agents" / "openai.yaml"
        agent.write_text(
            agent.read_text(encoding="utf-8").replace(
                "rust-agent-runtime", "codex-task-contract"
            ),
            encoding="utf-8",
        )
        self._git(root, "add", "-A")
        self._git(
            root,
            "-c",
            "user.name=Release Test",
            "-c",
            "user.email=release-test@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "duplicate skill",
        )
        with self.assertRaisesRegex(ValueError, "duplicates"):
            self._result(root)

    def test_post_capture_input_mutation_is_rejected(self) -> None:
        root = self._release_root()
        original_validate = package_validation.validate

        def validate_then_mutate(candidate_root: Path):
            inventories = original_validate(candidate_root)
            target = (
                candidate_root
                / "plugins"
                / "agentic-engineering"
                / "untracked-after-capture.txt"
            )
            target.write_text("mutation\n", encoding="utf-8")
            return inventories

        with patch.object(
            package_validation,
            "validate",
            side_effect=validate_then_mutate,
        ):
            with self.assertRaisesRegex(ValueError, "clean|changed"):
                run_structural_release(root)

    def test_full_release_rejects_selected_subset(self) -> None:
        candidate = Candidate("commit", "tree", "sha256:inputs")
        check = CheckResult(
            "package-structure",
            "passed",
            "structural",
            {"observation": "present"},
        )
        inventories = validate(SOURCE_ROOT)
        with self.assertRaisesRegex(ValueError, "complete ordered package set"):
            render_release_result(candidate, inventories[:-1], (check,))

    def test_pass_without_observations_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires observations"):
            CheckResult("package-structure", "passed", "structural", {})
        with self.assertRaisesRegex(ValueError, "nonblank"):
            CheckResult(
                "package-structure",
                "passed",
                "structural",
                {"observation": "   "},
            )

    def test_behavioral_claim_is_rejected_from_structural_release(self) -> None:
        with self.assertRaisesRegex(ValueError, "behavioral efficacy"):
            CheckResult("package-structure", "passed", "behavioral", {"proof": "none"})

    def test_candidate_capture_rejects_staged_unstaged_untracked_and_ignored_inputs(self) -> None:
        cases = ("staged", "unstaged", "untracked", "ignored")
        for case in cases:
            with self.subTest(case=case):
                root = self._release_root()
                target = root / "plugins" / "agentic-engineering" / "ignored-input.txt"
                if case == "staged":
                    target = root / "profiles" / "full.json"
                    target.write_text("{}\n", encoding="utf-8")
                    self._git(root, "add", str(target.relative_to(root)))
                elif case == "unstaged":
                    target = root / "profiles" / "full.json"
                    target.write_text("{}\n", encoding="utf-8")
                elif case == "untracked":
                    target.write_text("untracked\n", encoding="utf-8")
                else:
                    target.write_text("ignored\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "must be clean"):
                    capture_candidate(root)

    def test_default_command_writes_no_output_or_bytecode(self) -> None:
        root = self._release_root()
        (root / "scripts").mkdir()
        for filename in ("release_check.py", "package_validation.py"):
            shutil.copy2(SOURCE_ROOT / "scripts" / filename, root / "scripts" / filename)
        self._git(root, "add", "scripts")
        self._git(
            root,
            "-c",
            "user.name=Release Test",
            "-c",
            "user.email=release-test@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "release command",
        )
        completed = subprocess.run(
            [sys.executable, "scripts/release_check.py"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": ""},
        )
        result = json.loads(completed.stdout)
        self.assertTrue(result["passed"])
        self.assertFalse((root / "evals" / "results").exists())
        self.assertFalse((root / "scripts" / "__pycache__").exists())
