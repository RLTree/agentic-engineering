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
                self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"passed": True})

    def test_results_directory_symlink_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            external = root.parent / f"{root.name}-external-results"
            external.mkdir()
            (root / "evals").mkdir()
            (root / "evals" / "results").symlink_to(
                external,
                target_is_directory=True,
            )
            with patch.object(_common, "plugin_root", return_value=root):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    _common.write_json(
                        root / "evals" / "results" / "report.json",
                        {"passed": True},
                    )
            (root / "evals" / "results").unlink()
            external.rmdir()


if __name__ == "__main__":
    unittest.main()
