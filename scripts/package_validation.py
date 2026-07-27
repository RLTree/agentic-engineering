#!/usr/bin/env python3
"""Validate the explicit-only Agentic Engineering 4.0.0 package set."""
from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable


PACKAGES = {
    "agentic-engineering": 8,
    "agentic-engineering-lifecycle": 10,
    "agentic-engineering-rust": 7,
    "agentic-engineering-systems": 5,
}
POLICY_URLS = (
    "websiteURL",
    "privacyPolicyURL",
    "termsOfServiceURL",
)


@dataclass(frozen=True)
class PackageInventory:
    name: str
    skills: tuple[str, ...]
    digest: str


def repository_root(start: Path | None = None) -> Path:
    if start is not None:
        return start.resolve()
    return Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 4 or lines[0] != "---":
        raise ValueError("missing YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError("unterminated YAML frontmatter") from error
    values: dict[str, str] = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError("invalid frontmatter line")
        values[key] = value.strip().strip('"')
    if set(values) != {"name", "description"}:
        raise ValueError("frontmatter must contain only name and description")
    return values


def package_inventory(root: Path, name: str) -> PackageInventory:
    package_root = root / "plugins" / name
    manifest = read_json(package_root / ".codex-plugin" / "plugin.json")
    if manifest.get("name") != name or manifest.get("version") != "4.0.0":
        raise ValueError(f"{name}: manifest identity is invalid")
    interface = manifest.get("interface")
    if not isinstance(interface, dict) or any(
        not isinstance(interface.get(key), str) or not interface[key].startswith("https://")
        for key in POLICY_URLS
    ):
        raise ValueError(f"{name}: policy URLs are incomplete")
    skills: list[str] = []
    for skill_dir in sorted((package_root / "skills").iterdir()):
        if not skill_dir.is_dir():
            continue
        meta = frontmatter(skill_dir / "SKILL.md")
        if meta["name"] != skill_dir.name or not meta["description"].startswith("Use when "):
            raise ValueError(f"{name}: invalid skill trigger for {skill_dir.name}")
        agent = (skill_dir / "agents" / "openai.yaml").read_text(encoding="utf-8")
        expected = f"$${name}:{skill_dir.name}".replace("$$", "$")
        if "allow_implicit_invocation: false" not in agent or expected not in agent:
            raise ValueError(f"{name}: {skill_dir.name} is not explicit-only")
        skills.append(skill_dir.name)
    digest = sha256("\n".join(skills).encode("utf-8")).hexdigest()
    return PackageInventory(name, tuple(skills), f"sha256:{digest}")


def validate(root: Path | None = None) -> tuple[PackageInventory, ...]:
    root = repository_root(root)
    inventories = tuple(package_inventory(root, name) for name in PACKAGES)
    counts = {inventory.name: len(inventory.skills) for inventory in inventories}
    if counts != PACKAGES:
        raise ValueError(f"package skill counts differ: {counts}")
    union = [skill for inventory in inventories for skill in inventory.skills]
    if len(union) != len(set(union)):
        raise ValueError("package skill union contains duplicates")
    full = read_json(root / "profiles" / "full.json")["enabled_skills"]
    if set(union) != set(full) or len(full) != 30:
        raise ValueError("package skill union does not equal the 30-skill full profile")
    base = set(read_json(root / "profiles" / "ultragoal.json")["enabled_skills"])
    if set(inventories[0].skills) != base:
        raise ValueError("base package does not equal the Ultragoal profile")
    return inventories


def render(inventories: Iterable[PackageInventory]) -> dict:
    entries = list(inventories)
    aggregate = sha256(
        "\n".join(f"{item.name}:{item.digest}" for item in entries).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "AgenticPackSet-v1",
        "packages": [
            {"name": item.name, "version": "4.0.0", "skill_count": len(item.skills), "digest": item.digest}
            for item in entries
        ],
        "aggregate_digest": f"sha256:{aggregate}",
        "skill_union": sorted(skill for item in entries for skill in item.skills),
    }
