#!/usr/bin/env python3
"""Validate package structure, skill contracts, profiles, and single-front-door routing."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

from _common import HEX_RE, NAME_RE, SEMVER_RE, load_json, make_report, parse_frontmatter, plugin_root, print_report, repo_root, results_dir, skill_dirs, write_json

REQUIRED_HEADINGS = ("## Core principle", "## Workflow", "## Output contract", "## Common failures", "## References")
REQUIRED_DOCS = {
    "README.md", "RESEARCH.md", "RESEARCH-V3-ADDENDUM.md", "SOURCE-MANIFEST.json",
    "EVIDENCE-MATRIX.csv", "EVALUATION.md", "CONFIDENCE.md", "PLUGIN-DESIGN-BRIEF.md",
    "V3-DECISION-RECORD.md", "UPDATE-POLICY.md", "CHANGELOG.md", "LICENSE.txt",
}
FORBIDDEN_PLACEHOLDERS = ("TBD", "[TODO", "implement later", "fill this in")


def validate_marketplace(errors: list[str]) -> None:
    path = repo_root() / ".agents" / "plugins" / "marketplace.json"
    if not path.is_file():
        errors.append(f"missing marketplace manifest: {path}")
        return
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid marketplace JSON: {exc}")
        return
    entries = [x for x in data.get("plugins", []) if isinstance(x, dict) and x.get("name") == "agentic-engineering"]
    if len(entries) != 1:
        errors.append(f"marketplace must contain one agentic-engineering entry; found {len(entries)}")
        return
    entry = entries[0]
    if entry.get("source") != {"source": "local", "path": "./plugins/agentic-engineering"}:
        errors.append("marketplace source must be the packaged local plugin")
    policy = entry.get("policy") or {}
    if policy.get("installation") not in {"NOT_AVAILABLE", "AVAILABLE", "INSTALLED_BY_DEFAULT"}:
        errors.append("invalid marketplace installation policy")
    if policy.get("authentication") not in {"ON_INSTALL", "ON_USE"}:
        errors.append("invalid marketplace authentication policy")


def validate_manifest(errors: list[str]) -> dict[str, Any]:
    path = plugin_root() / ".codex-plugin" / "plugin.json"
    if not path.is_file():
        errors.append("missing .codex-plugin/plugin.json")
        return {}
    data = load_json(path)
    required = {"name", "version", "description", "author", "license", "keywords", "skills", "interface"}
    missing = required - set(data)
    if missing:
        errors.append(f"plugin manifest missing {sorted(missing)}")
    if data.get("name") != "agentic-engineering":
        errors.append("plugin manifest name mismatch")
    if not SEMVER_RE.fullmatch(str(data.get("version", ""))):
        errors.append("plugin version must use semantic versioning")
    if data.get("skills") != "./skills/":
        errors.append("plugin manifest skills must be './skills/'")
    if not isinstance(data.get("author"), dict) or not str(data.get("author", {}).get("name", "")).strip():
        errors.append("plugin author.name is required")
    if not isinstance(data.get("keywords"), list) or len(data.get("keywords", [])) < 10:
        errors.append("plugin manifest needs at least ten keywords")
    interface = data.get("interface") or {}
    for key in ("displayName", "shortDescription", "longDescription", "developerName", "category", "capabilities", "defaultPrompt", "brandColor"):
        if key not in interface:
            errors.append(f"plugin interface.{key} is required")
    if not HEX_RE.fullmatch(str(interface.get("brandColor", ""))):
        errors.append("plugin interface.brandColor must be a hex color")
    prompts = interface.get("defaultPrompt")
    if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3 or any(not isinstance(x, str) or not x.strip() or len(x) > 180 for x in prompts or []):
        errors.append("plugin defaultPrompt must contain one to three concise strings")
    return data


def validate_skill(path: Path, errors: list[str], descriptions: list[str], implicit: list[str]) -> None:
    skill_md = path / "SKILL.md"
    if not skill_md.is_file():
        errors.append(f"{path.name}: missing SKILL.md")
        return
    fields, text = parse_frontmatter(skill_md)
    if set(fields) != {"name", "description"}:
        errors.append(f"{path.name}: frontmatter must contain name and description only")
    name = fields.get("name", "")
    description = fields.get("description", "")
    descriptions.append(description)
    if name != path.name or not NAME_RE.fullmatch(name):
        errors.append(f"{path.name}: invalid or mismatched skill name {name!r}")
    if not description.startswith("Use when"):
        errors.append(f"{path.name}: description must begin with 'Use when'")
    if not 60 <= len(description) <= 180:
        errors.append(f"{path.name}: description length {len(description)} is outside 60..180")
    if len(text.splitlines()) > 520:
        errors.append(f"{path.name}: SKILL.md exceeds 520 lines; move detail to references")
    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            errors.append(f"{path.name}: missing heading {heading}")
    lowered = text.lower()
    for marker in FORBIDDEN_PLACEHOLDERS:
        if marker.lower() in lowered:
            errors.append(f"{path.name}: contains placeholder {marker!r}")

    refs = sorted((path / "references").glob("*.md"))
    if len(refs) < 3:
        errors.append(f"{path.name}: needs at least three progressive-disclosure references")
    for ref in refs:
        if ref.stat().st_size < 500:
            errors.append(f"{path.name}: reference {ref.name} is under 500 bytes")

    agent_yaml = path / "agents" / "openai.yaml"
    if not agent_yaml.is_file():
        errors.append(f"{path.name}: missing agents/openai.yaml")
        return
    if yaml is None:
        errors.append("PyYAML is required")
        return
    data = yaml.safe_load(agent_yaml.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"interface", "policy"}:
        errors.append(f"{path.name}: openai.yaml must contain interface and policy only")
        return
    interface = data.get("interface") or {}
    policy = data.get("policy") or {}
    for key in ("display_name", "short_description", "brand_color", "default_prompt"):
        if not isinstance(interface.get(key), str) or not interface.get(key, "").strip():
            errors.append(f"{path.name}: interface.{key} must be non-empty")
    if not HEX_RE.fullmatch(str(interface.get("brand_color", ""))):
        errors.append(f"{path.name}: invalid brand color")
    value = policy.get("allow_implicit_invocation")
    if not isinstance(value, bool):
        errors.append(f"{path.name}: allow_implicit_invocation must be boolean")
    elif value:
        implicit.append(path.name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    validate_marketplace(errors)
    manifest = validate_manifest(errors)

    dirs = skill_dirs()
    actual = {p.name for p in dirs}
    full_profile = load_json(plugin_root() / "profiles" / "full.json")
    expected = set(full_profile.get("enabled_skills", []))
    if actual != expected:
        errors.append(f"skill/full-profile mismatch: missing={sorted(expected-actual)} extra={sorted(actual-expected)}")
    descriptions: list[str] = []
    implicit: list[str] = []
    for path in dirs:
        validate_skill(path, errors, descriptions, implicit)
    if len(descriptions) != len(set(descriptions)):
        errors.append("skill descriptions must be unique")
    combined = sum(map(len, descriptions))
    if combined > 7600:
        errors.append(f"combined descriptions exceed conservative 7600-character release budget: {combined}")
    if implicit:
        errors.append(f"Agentic co-install must expose no implicit skill; found {implicit}")

    missing_docs = sorted(name for name in REQUIRED_DOCS if not (plugin_root() / name).is_file())
    if missing_docs:
        errors.append(f"missing required docs: {missing_docs}")
    if manifest.get("version") != "3.0.1":
        errors.append(f"expected plugin version 3.0.1, found {manifest.get('version')}")

    metrics = {
        "skills": len(dirs),
        "skill_references": sum(len(list((p / 'references').glob('*.md'))) for p in dirs),
        "combined_description_chars": combined,
        "implicit_skills": implicit,
        "required_docs": len(REQUIRED_DOCS),
    }
    report = make_report("plugin-validation", not errors, errors, warnings, metrics)
    if args.write:
        write_json(results_dir() / "plugin-validation.json", report)
    print_report(report)
    return 0 if report["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
