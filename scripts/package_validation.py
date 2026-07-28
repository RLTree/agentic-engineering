#!/usr/bin/env python3
"""Validate the explicit-only Agentic Engineering 4.0.0 package set."""

from __future__ import annotations

import json
import os
import secrets
import stat
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import yaml


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
PACK_SET_SCHEMA = "AgenticPackSet-v1"
GATEWAY = "external:harness-ultragoal"
PACKAGE_TOP_LEVEL = {".codex-plugin", "skills"}


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
    try:
        values = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as error:
        raise ValueError("invalid YAML frontmatter") from error
    if not isinstance(values, dict) or set(values) != {"name", "description"}:
        raise ValueError("frontmatter must contain only name and description")
    if any(not isinstance(values[key], str) for key in values):
        raise ValueError("frontmatter values must be strings")
    return values


def package_manifest_digest(package_root: Path) -> str:
    entries: list[bytes] = []
    for path in sorted(package_root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"{package_root.name}: package contains symlink {path}")
        mode = path.stat().st_mode
        if path.is_dir():
            continue
        if not stat.S_ISREG(mode):
            raise ValueError(
                f"{package_root.name}: package contains non-regular file {path}"
            )
        relative = path.relative_to(package_root).as_posix()
        if any(character in relative for character in ("\x00", "\n", "\r", "\t")):
            raise ValueError(
                f"{package_root.name}: package path contains a control character"
            )
        content = path.read_bytes()
        encoded_path = relative.encode("utf-8")
        entries.append(
            len(encoded_path).to_bytes(8, "big")
            + encoded_path
            + len(content).to_bytes(8, "big")
            + sha256(content).digest()
        )
    if not entries:
        raise ValueError(f"{package_root.name}: package manifest is empty")
    return f"sha256:{sha256(b''.join(entries)).hexdigest()}"


def safe_generated_output(root: Path, requested: Path) -> Path:
    """Resolve a report path inside the repository's ignored generated-output root."""
    root = Path(os.path.abspath(root))
    requested = Path(os.path.abspath(requested))
    allowed = root / "evals" / "results"
    try:
        relative = requested.relative_to(root)
    except ValueError as error:
        raise ValueError("output must stay inside the repository") from error
    if relative.parts[:2] != ("evals", "results") or len(relative.parts) < 3:
        raise ValueError("output must be a file under evals/results")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("output path must not contain symlinks")
    resolved = requested.resolve(strict=False)
    if allowed.resolve(strict=False) not in resolved.parents:
        raise ValueError("output must stay under evals/results")
    return resolved


def atomic_write_generated_json(root: Path, requested: Path, value: dict) -> Path:
    """Atomically write JSON beneath evals/results without following links."""
    output = safe_generated_output(root, requested)
    lexical_root = Path(os.path.abspath(root))
    relative = Path(os.path.abspath(requested)).relative_to(lexical_root)
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptors: list[int] = []
    temporary_name: str | None = None
    try:
        descriptors.append(os.open(lexical_root, directory_flags))
        for part in relative.parts[:-1]:
            try:
                os.mkdir(part, mode=0o700, dir_fd=descriptors[-1])
            except FileExistsError:
                pass
            descriptors.append(os.open(part, directory_flags, dir_fd=descriptors[-1]))
        parent = descriptors[-1]
        filename = relative.parts[-1]
        try:
            target = os.stat(filename, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            target = None
        if target is not None and stat.S_ISLNK(target.st_mode):
            raise ValueError("output path must not contain symlinks")
        payload = (json.dumps(value, indent=2) + "\n").encode("utf-8")
        temporary_name = f".{filename}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(temporary_name, flags, 0o600, dir_fd=parent)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(
            temporary_name,
            filename,
            src_dir_fd=parent,
            dst_dir_fd=parent,
        )
        temporary_name = None
        os.fsync(parent)
        return output
    finally:
        if temporary_name is not None and descriptors:
            try:
                os.unlink(temporary_name, dir_fd=descriptors[-1])
            except FileNotFoundError:
                pass
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def package_inventory(root: Path, name: str) -> PackageInventory:
    package_root = root / "plugins" / name
    top_level = {path.name for path in package_root.iterdir()}
    if top_level != PACKAGE_TOP_LEVEL:
        raise ValueError(
            f"{name}: package root must contain only {sorted(PACKAGE_TOP_LEVEL)}; "
            f"found {sorted(top_level)}"
        )
    manifest = read_json(package_root / ".codex-plugin" / "plugin.json")
    if manifest.get("name") != name or manifest.get("version") != "4.0.0":
        raise ValueError(f"{name}: manifest identity is invalid")
    interface = manifest.get("interface")
    if not isinstance(interface, dict) or any(
        not isinstance(interface.get(key), str)
        or not interface[key].startswith("https://")
        for key in POLICY_URLS
    ):
        raise ValueError(f"{name}: policy URLs are incomplete")
    skills: list[str] = []
    for skill_dir in sorted((package_root / "skills").iterdir()):
        if not skill_dir.is_dir():
            continue
        meta = frontmatter(skill_dir / "SKILL.md")
        if meta["name"] != skill_dir.name or not meta["description"].startswith(
            "Use when "
        ):
            raise ValueError(f"{name}: invalid skill trigger for {skill_dir.name}")
        agent_path = skill_dir / "agents" / "openai.yaml"
        try:
            agent = yaml.safe_load(agent_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise ValueError(
                f"{name}: invalid agent YAML for {skill_dir.name}"
            ) from error
        expected_prompt = f"Use ${name}:{skill_dir.name} as an explicit advisory lens through {GATEWAY}."
        if (
            not isinstance(agent, dict)
            or set(agent) != {"interface", "policy"}
            or not isinstance(agent.get("interface"), dict)
            or not isinstance(agent.get("policy"), dict)
            or agent["interface"].get("default_prompt") != expected_prompt
            or agent["policy"].get("allow_implicit_invocation") is not False
        ):
            raise ValueError(f"{name}: {skill_dir.name} is not explicit-only")
        skills.append(skill_dir.name)
    return PackageInventory(name, tuple(skills), package_manifest_digest(package_root))


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
    base_inventory = next(
        (item for item in inventories if item.name == "agentic-engineering"),
        None,
    )
    if base_inventory is None or set(base_inventory.skills) != base:
        raise ValueError("base package does not equal the Ultragoal profile")
    return inventories


def render(inventories: Iterable[PackageInventory]) -> dict:
    entries = list(inventories)
    packs = [
        {
            "name": item.name,
            "version": "4.0.0",
            "manifest_digest": item.digest,
            "enabled_skills": list(item.skills),
        }
        for item in entries
    ]
    aggregate = sha256(
        "\n".join(
            [PACK_SET_SCHEMA, GATEWAY]
            + [
                "\t".join(
                    [
                        pack["name"],
                        pack["version"],
                        pack["manifest_digest"],
                        ",".join(sorted(pack["enabled_skills"])),
                    ]
                )
                for pack in packs
            ]
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": PACK_SET_SCHEMA,
        "gateway": GATEWAY,
        "packs": packs,
        "aggregate_digest": f"sha256:{aggregate}",
        "skill_union": sorted(skill for item in entries for skill in item.skills),
    }
