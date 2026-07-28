from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import _common


class CommonOutputTests(unittest.TestCase):
    def test_write_json_stays_in_non_symlink_results_directory(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(_common, "plugin_root", return_value=root):
                path = root / "evals" / "results" / "report.json"
                _common.write_json(path, {"passed": True})
                self.assertEqual(
                    json.loads(path.read_text(encoding="utf-8")), {"passed": True}
                )

    def test_results_directory_symlink_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary, TemporaryDirectory() as external:
            root = Path(temporary)
            (root / "evals").mkdir()
            (root / "evals" / "results").symlink_to(
                Path(external),
                target_is_directory=True,
            )
            with patch.object(_common, "plugin_root", return_value=root):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    _common.write_json(
                        root / "evals" / "results" / "report.json",
                        {"passed": True},
                    )

    def test_plugin_root_symlinks_are_rejected_before_traversal(self) -> None:
        with TemporaryDirectory() as temporary, TemporaryDirectory() as external:
            root = Path(temporary)
            plugins = root / "plugins"
            plugins.mkdir()
            (plugins / "linked").symlink_to(Path(external), target_is_directory=True)
            with patch.object(_common, "plugin_root", return_value=root):
                with self.assertRaisesRegex(ValueError, "package root"):
                    _common.package_roots()
                with self.assertRaisesRegex(ValueError, "package root"):
                    _common.skill_dirs()
            (plugins / "linked").unlink()
            (plugins / "broken").symlink_to(root / "missing", target_is_directory=True)
            with patch.object(_common, "plugin_root", return_value=root):
                with self.assertRaisesRegex(ValueError, "package root"):
                    _common.package_roots()

    def test_symlinked_skills_root_is_rejected_before_traversal(self) -> None:
        with TemporaryDirectory() as temporary, TemporaryDirectory() as external:
            root = Path(temporary)
            package = root / "plugins" / "package"
            package.mkdir(parents=True)
            (package / "skills").symlink_to(Path(external), target_is_directory=True)
            with patch.object(_common, "plugin_root", return_value=root):
                with self.assertRaisesRegex(ValueError, "skills root"):
                    _common.skill_dirs()


if __name__ == "__main__":
    unittest.main()
