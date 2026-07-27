from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import package_validation
from package_validation import (
    PACKAGES,
    PackageInventory,
    frontmatter,
    package_inventory,
    package_manifest_digest,
    render,
    repository_root,
    validate,
)


class PackageValidationTests(unittest.TestCase):
    def test_render_has_a_stable_pack_set_shape(self) -> None:
        result = render(
            [
                PackageInventory(name, tuple(f"{name}-{index}" for index in range(count)), f"sha256:{name}")
                for name, count in PACKAGES.items()
            ]
        )
        self.assertEqual(result["schema_version"], "AgenticPackSet-v1")
        self.assertEqual(result["gateway"], "external:harness-ultragoal")
        self.assertEqual(len(result["packs"]), 4)
        self.assertEqual(len(result["skill_union"]), 30)
        self.assertTrue(result["aggregate_digest"].startswith("sha256:"))

    def test_render_is_json_serializable(self) -> None:
        result = render([PackageInventory("agentic-engineering", ("one",), "sha256:one")])
        self.assertEqual(json.loads(json.dumps(result))["packs"][0]["name"], "agentic-engineering")

    def test_current_package_set_validates(self) -> None:
        root = Path(__file__).resolve().parents[1]
        inventories = validate(root)
        self.assertEqual([len(item.skills) for item in inventories], [8, 10, 7, 5])

    def test_frontmatter_rejects_malformed_documents(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "SKILL.md"
            path.write_text("not frontmatter\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing"):
                frontmatter(path)
            path.write_text("---\nname: one\nextra: value\nno-end\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unterminated"):
                frontmatter(path)
            path.write_text("---\nname one\n---\nbody\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid"):
                frontmatter(path)

    def test_package_inventory_rejects_missing_policy_urls(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "plugins" / "agentic-engineering" / ".codex-plugin"
            manifest.mkdir(parents=True)
            (manifest / "plugin.json").write_text(
                json.dumps({"name": "agentic-engineering", "version": "4.0.0", "interface": {}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "policy"):
                package_inventory(root, "agentic-engineering")

    def test_package_manifest_digest_binds_paths_lengths_and_content(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "skills").mkdir()
            first = root / "skills" / "one.md"
            first.write_text("one\n", encoding="utf-8")
            original = package_manifest_digest(root)
            first.write_text("two\n", encoding="utf-8")
            changed_content = package_manifest_digest(root)
            first.rename(root / "skills" / "two.md")
            changed_path = package_manifest_digest(root)
        self.assertNotEqual(original, changed_content)
        self.assertNotEqual(changed_content, changed_path)

    def test_render_normalizes_enabled_skill_order_for_the_digest(self) -> None:
        forward = render(
            [PackageInventory("agentic-engineering", ("one", "two"), "sha256:one")]
        )
        reverse = render(
            [PackageInventory("agentic-engineering", ("two", "one"), "sha256:one")]
        )
        self.assertEqual(forward["aggregate_digest"], reverse["aggregate_digest"])

    def test_validate_rejects_duplicate_and_mismatched_profiles(self) -> None:
        inventories = [
            PackageInventory(name, tuple(f"{name}-{index}" for index in range(count)), f"sha256:{name}")
            for name, count in PACKAGES.items()
        ]
        duplicate = list(inventories)
        duplicate[1] = PackageInventory(duplicate[1].name, (inventories[0].skills[0],) + duplicate[1].skills[1:], "sha256:duplicate")
        with patch.object(package_validation, "package_inventory", side_effect=duplicate):
            with self.assertRaisesRegex(ValueError, "duplicates"):
                validate(Path("."))
        full = [skill for item in inventories for skill in item.skills]
        with patch.object(package_validation, "package_inventory", side_effect=inventories):
            with patch.object(package_validation, "read_json", side_effect=[{"enabled_skills": ["wrong"]}]):
                with self.assertRaisesRegex(ValueError, "full profile"):
                    validate(Path("."))
        with patch.object(package_validation, "package_inventory", side_effect=inventories):
            with patch.object(package_validation, "read_json", side_effect=[{"enabled_skills": full}, {"enabled_skills": ["wrong"]}]):
                with self.assertRaisesRegex(ValueError, "base package"):
                    validate(Path("."))

    def test_default_repository_root_is_the_project(self) -> None:
        self.assertEqual(repository_root(), Path(__file__).resolve().parents[1])
