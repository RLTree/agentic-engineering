#!/usr/bin/env python3
"""Shared validation utilities for the Agentic Engineering Codex plugin."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
MARKDOWN_LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")


def plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


def repo_root() -> Path:
    return plugin_root()


def results_dir() -> Path:
    path = plugin_root() / "evals" / "results"
    for candidate in (path.parent, path):
        if candidate.is_symlink():
            raise ValueError("generated results path must not contain symlinks")
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    generated = results_dir().resolve()
    requested = Path(os.path.abspath(path))
    if (
        requested.is_symlink()
        or generated not in requested.resolve(strict=False).parents
    ):
        raise ValueError("report path must be a non-symlink beneath evals/results")
    requested.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(requested, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    fields: dict[str, str] = {}
    for raw in match.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields, text


def skill_dirs() -> list[Path]:
    roots: list[Path] = []
    for package in sorted((plugin_root() / "plugins").iterdir()):
        if package.is_symlink():
            raise ValueError(f"symlinked package root: {package}")
        if not package.is_dir():
            continue
        root = package / "skills"
        if root.is_symlink():
            raise ValueError(f"symlinked skills root: {root}")
        if root.is_dir():
            roots.append(root)
    return sorted(
        path
        for root in roots
        for path in root.iterdir()
        if path.is_dir() and not path.is_symlink()
    )


def package_roots() -> list[Path]:
    entries = sorted((plugin_root() / "plugins").iterdir())
    links = [path for path in entries if path.is_symlink()]
    if links:
        raise ValueError(f"symlinked package root: {links[0]}")
    return [path for path in entries if path.is_dir()]


def local_markdown_targets(path: Path) -> Iterable[str]:
    text = path.read_text(encoding="utf-8")
    for raw in MARKDOWN_LINK_RE.findall(text):
        target = raw.strip().split()[0].strip("<>")
        target = target.split("#", 1)[0].strip()
        if not target:
            continue
        lowered = target.lower()
        if lowered.startswith(("http://", "https://", "mailto:", "plugin://", "data:")):
            continue
        if target.startswith("#"):
            continue
        yield target


def make_report(
    name: str,
    passed: bool,
    errors: list[str],
    warnings: list[str],
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "check": name,
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics or {},
    }


def print_report(report: dict[str, Any]) -> None:
    status = "PASSED" if report.get("passed") else "FAILED"
    print(f"{report.get('check', 'CHECK')}: {status}")
    metrics = report.get("metrics") or {}
    for key, value in metrics.items():
        print(f"- {key}: {value}")
    for warning in report.get("warnings") or []:
        print(f"- warning: {warning}")
    for error in report.get("errors") or []:
        print(f"- error: {error}")
