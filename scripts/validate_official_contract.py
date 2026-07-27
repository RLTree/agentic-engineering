#!/usr/bin/env python3
"""Validate Codex progressive-disclosure and low-privilege plugin conventions."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import yaml

from _common import make_report, parse_frontmatter, plugin_root, print_report, results_dir, skill_dirs, write_json

PROCESS_SHORTCUTS = re.compile(r"\b(?:then|step-by-step|dispatches|runs the workflow|produces a|first .* then)\b", re.I)
PRIVILEGED_DIRS = {"hooks", "mcp", "connectors", "executables", "bin"}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--write", action="store_true"); args = parser.parse_args()
    errors: list[str] = []
    warnings = ["Negative activation is validated by the routing corpus rather than spending description budget on every explicit specialist."]
    descriptions: list[str] = []
    implicit: list[str] = []
    oversized: list[str] = []

    for d in skill_dirs():
        fields, text = parse_frontmatter(d / "SKILL.md")
        description = fields.get("description", "")
        descriptions.append(description)
        if not description.startswith("Use when"):
            errors.append(f"{d.name}: description must state its trigger first")
        if len(description) > 180:
            errors.append(f"{d.name}: description is too long for discovery")
        if PROCESS_SHORTCUTS.search(description):
            errors.append(f"{d.name}: description appears to summarize workflow instead of trigger")
        if len(text.encode("utf-8")) > 55_000:
            oversized.append(d.name)
        data = yaml.safe_load((d / "agents" / "openai.yaml").read_text(encoding="utf-8"))
        if (data.get("policy") or {}).get("allow_implicit_invocation"):
            implicit.append(d.name)

    if implicit:
        errors.append(f"Agentic co-install must expose no implicit skill: {implicit}")
    if len(descriptions) != len(set(descriptions)):
        errors.append("descriptions must be unique")
    if oversized:
        errors.append(f"oversized SKILL.md files: {oversized}")

    privileged = []
    for child in plugin_root().iterdir():
        if child.name.lower() in PRIVILEGED_DIRS:
            privileged.append(child.name)
    if privileged:
        errors.append(f"unexpected privileged plugin surfaces: {privileged}")

    # All specialist procedures must remain progressively disclosed locally.
    for d in skill_dirs():
        if not (d / "references").is_dir() or not any((d / "references").glob("*.md")):
            errors.append(f"{d.name}: no local progressive-disclosure references")

    report = make_report("official-contract-validation", not errors, errors, warnings, {
        "skills": len(descriptions), "unique_descriptions": len(set(descriptions)),
        "implicit_gateway": implicit, "oversized_files": len(oversized),
        "privileged_surfaces_declared": len(privileged),
    })
    if args.write: write_json(results_dir() / "official-contract-validation.json", report)
    print_report(report); return 0 if report["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
