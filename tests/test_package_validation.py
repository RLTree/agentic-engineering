from __future__ import annotations

import json
import shutil
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
    atomic_write_generated_json,
    frontmatter,
    package_inventory,
    package_manifest_digest,
    render,
    repository_root,
    safe_generated_output,
    validate,
    validate_marketplace,
)


class PackageValidationTests(unittest.TestCase):
    def test_render_has_a_stable_pack_set_shape(self) -> None:
        result = render(
            [
                PackageInventory(
                    name,
                    tuple(f"{name}-{index}" for index in range(count)),
                    f"sha256:{name}",
                )
                for name, count in PACKAGES.items()
            ]
        )
        self.assertEqual(result["schema_version"], "AgenticPackSet-v1")
        self.assertEqual(result["gateway"], "external:harness-ultragoal")
        self.assertEqual(len(result["packs"]), 4)
        self.assertEqual(len(result["skill_union"]), 30)
        self.assertTrue(result["aggregate_digest"].startswith("sha256:"))

    def test_render_is_json_serializable(self) -> None:
        result = render(
            [PackageInventory("agentic-engineering", ("one",), "sha256:one")]
        )
        self.assertEqual(
            json.loads(json.dumps(result))["packs"][0]["name"], "agentic-engineering"
        )

    def test_current_package_set_validates(self) -> None:
        root = Path(__file__).resolve().parents[1]
        inventories = validate(root)
        self.assertEqual([len(item.skills) for item in inventories], [8, 10, 7, 5])

    def test_marketplace_requires_current_host_fields_and_exact_packages(self) -> None:
        root = Path(__file__).resolve().parents[1]
        validate_marketplace(root)
        with TemporaryDirectory() as temporary:
            candidate = Path(temporary)
            original = json.loads(
                (root / ".agents" / "plugins" / "marketplace.json").read_text(
                    encoding="utf-8"
                )
            )
            path = candidate / ".agents" / "plugins" / "marketplace.json"
            path.parent.mkdir(parents=True)
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "document must be an object"):
                validate_marketplace(candidate)
            cases = [
                (
                    "schema version",
                    lambda value: value.__setitem__("schema_version", "2.0"),
                ),
                ("marketplace name", lambda value: value.pop("name")),
                ("interface", lambda value: value.pop("interface")),
                (
                    "interface",
                    lambda value: value["interface"].__setitem__(
                        "displayName",
                        "Changed",
                    ),
                ),
                ("plugins must be", lambda value: value.__setitem__("plugins", {})),
                ("package set", lambda value: value["plugins"].pop()),
                (
                    "source",
                    lambda value: value["plugins"][0].__setitem__("source", {}),
                ),
                (
                    "policy",
                    lambda value: value["plugins"][0].__setitem__("policy", {}),
                ),
                (
                    "category",
                    lambda value: value["plugins"][0].__setitem__(
                        "category",
                        "Other",
                    ),
                ),
            ]
            for expected, mutate in cases:
                with self.subTest(expected=expected):
                    manifest = json.loads(json.dumps(original))
                    mutate(manifest)
                    path.write_text(json.dumps(manifest), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, expected):
                        validate_marketplace(candidate)

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
            with self.assertRaisesRegex(ValueError, "frontmatter"):
                frontmatter(path)
            path.write_text(
                "---\nname: [unterminated\ndescription: value\n---\nbody\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "invalid YAML"):
                frontmatter(path)
            path.write_text(
                "---\nname: one\ndescription: 7\n---\nbody\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "strings"):
                frontmatter(path)

    def test_package_inventory_rejects_missing_policy_urls(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "plugins" / "agentic-engineering" / ".codex-plugin"
            manifest.mkdir(parents=True)
            (manifest.parent / "skills").mkdir()
            (manifest / "plugin.json").write_text(
                json.dumps(
                    {"name": "agentic-engineering", "version": "4.0.0", "interface": {}}
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "policy"):
                package_inventory(root, "agentic-engineering")

    def test_package_inventory_uses_effective_yaml_and_exact_gateway_prompt(
        self,
    ) -> None:
        source = Path(__file__).resolve().parents[1] / "plugins" / "agentic-engineering"
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "plugins" / "agentic-engineering"
            shutil.copytree(source, package)
            yaml_path = (
                package / "skills" / "codex-task-contract" / "agents" / "openai.yaml"
            )
            original = yaml_path.read_text(encoding="utf-8")
            yaml_path.write_text(
                original.replace(
                    "allow_implicit_invocation: false",
                    "allow_implicit_invocation: true # allow_implicit_invocation: false",
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "explicit-only"):
                package_inventory(root, "agentic-engineering")
            yaml_path.write_text(
                original.replace(
                    "through external:harness-ultragoal.",
                    "through external:harness-ultragoal and external:attacker.",
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "explicit-only"):
                package_inventory(root, "agentic-engineering")

    def test_package_inventory_rejects_unexpected_privileged_surface(self) -> None:
        source = Path(__file__).resolve().parents[1] / "plugins" / "agentic-engineering"
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "plugins" / "agentic-engineering"
            shutil.copytree(source, package)
            (package / "hooks").mkdir()
            (package / "hooks" / "control.md").write_text(
                "unexpected\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "contain only"):
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
        with TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "empty"):
                package_manifest_digest(Path(temporary))

    def test_package_manifest_rejects_symlinks_and_control_character_paths(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            external = root.parent / f"{root.name}-external"
            external.write_text("external\n", encoding="utf-8")
            (root / "link").symlink_to(external)
            with self.assertRaisesRegex(ValueError, "symlink"):
                package_manifest_digest(root)
            (root / "link").unlink()
            (root / "bad\tname").write_text("content\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "control character"):
                package_manifest_digest(root)
            external.unlink()

    def test_safe_generated_output_rejects_source_and_symlink_paths(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "evals").mkdir()
            source = root / "plugins" / "agentic-engineering" / "SKILL.md"
            with self.assertRaisesRegex(ValueError, "evals/results"):
                safe_generated_output(root, source)
            with self.assertRaisesRegex(ValueError, "repository"):
                safe_generated_output(root, root.parent / "outside.json")
            external = root.parent / f"{root.name}-external-results"
            external.mkdir()
            (root / "evals" / "results").symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                safe_generated_output(root, root / "evals" / "results" / "report.json")
            (root / "evals" / "results").unlink()
            external.rmdir()

    def test_atomic_generated_output_rejects_links_and_writes_json(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "evals" / "results" / "nested" / "report.json"
            atomic_write_generated_json(root, output, {"passed": True})
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8")),
                {"passed": True},
            )
            output.unlink()
            output.symlink_to(root / "outside.json")
            with self.assertRaisesRegex(ValueError, "symlink"):
                atomic_write_generated_json(root, output, {"passed": False})

    def test_render_normalizes_enabled_skill_order_for_the_digest(self) -> None:
        forward = render(
            [PackageInventory("agentic-engineering", ("one", "two"), "sha256:one")]
        )
        reverse = render(
            [PackageInventory("agentic-engineering", ("two", "one"), "sha256:one")]
        )
        self.assertEqual(forward["aggregate_digest"], reverse["aggregate_digest"])

    @patch.object(package_validation, "validate_marketplace")
    def test_validate_rejects_duplicate_and_mismatched_profiles(
        self,
        _marketplace,
    ) -> None:
        inventories = [
            PackageInventory(
                name,
                tuple(f"{name}-{index}" for index in range(count)),
                f"sha256:{name}",
            )
            for name, count in PACKAGES.items()
        ]
        duplicate = list(inventories)
        duplicate[1] = PackageInventory(
            duplicate[1].name,
            (inventories[0].skills[0],) + duplicate[1].skills[1:],
            "sha256:duplicate",
        )
        with patch.object(
            package_validation, "package_inventory", side_effect=duplicate
        ):
            with self.assertRaisesRegex(ValueError, "duplicates"):
                validate(Path("."))
        full = [skill for item in inventories for skill in item.skills]
        with patch.object(
            package_validation, "package_inventory", side_effect=inventories
        ):
            with patch.object(
                package_validation,
                "read_json",
                side_effect=[{"enabled_skills": ["wrong"]}],
            ):
                with self.assertRaisesRegex(ValueError, "full profile"):
                    validate(Path("."))
        with patch.object(
            package_validation, "package_inventory", side_effect=inventories
        ):
            with patch.object(
                package_validation,
                "read_json",
                side_effect=[{"enabled_skills": full}, {"enabled_skills": ["wrong"]}],
            ):
                with self.assertRaisesRegex(ValueError, "base package"):
                    validate(Path("."))
        wrong_count = list(inventories)
        wrong_count[0] = PackageInventory(
            wrong_count[0].name,
            wrong_count[0].skills[:-1],
            wrong_count[0].digest,
        )
        with patch.object(
            package_validation, "package_inventory", side_effect=wrong_count
        ):
            with self.assertRaisesRegex(ValueError, "counts"):
                validate(Path("."))

    @patch.object(package_validation, "validate_marketplace")
    def test_validate_selects_base_package_by_name_after_reordering(
        self,
        _marketplace,
    ) -> None:
        reordered = dict(reversed(list(PACKAGES.items())))
        by_name = {
            name: PackageInventory(
                name,
                tuple(f"{name}-{index}" for index in range(count)),
                f"sha256:{name}",
            )
            for name, count in reordered.items()
        }
        inventories = [by_name[name] for name in reordered]
        full = [skill for item in inventories for skill in item.skills]
        base = list(by_name["agentic-engineering"].skills)
        with patch.object(package_validation, "PACKAGES", reordered):
            with patch.object(
                package_validation,
                "package_inventory",
                side_effect=inventories,
            ):
                with patch.object(
                    package_validation,
                    "read_json",
                    side_effect=[
                        {"enabled_skills": full},
                        {"enabled_skills": base},
                    ],
                ):
                    self.assertEqual(validate(Path(".")), tuple(inventories))

    def test_default_repository_root_is_the_project(self) -> None:
        self.assertEqual(repository_root(), Path(__file__).resolve().parents[1])

    def test_obsolete_v3_aggregate_is_not_shipped(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertFalse((root / "scripts" / "release_check_v3.py").exists())
