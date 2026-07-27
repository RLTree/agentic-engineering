#!/usr/bin/env python3
"""Audit all local Markdown links in the plugin without fetching external URLs."""
from __future__ import annotations

import argparse
import urllib.parse
from pathlib import Path

from _common import local_markdown_targets, make_report, plugin_root, print_report, results_dir, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    checked = 0
    markdown_files = sorted(plugin_root().rglob("*.md"))
    root = plugin_root().resolve()

    for source in markdown_files:
        for raw_target in local_markdown_targets(source):
            checked += 1
            target = urllib.parse.unquote(raw_target)
            if target.startswith("/"):
                errors.append(f"{source.relative_to(root)}: absolute local path is not portable: {raw_target}")
                continue
            resolved = (source.parent / target).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                errors.append(f"{source.relative_to(root)}: link escapes plugin root: {raw_target}")
                continue
            if not resolved.exists():
                errors.append(f"{source.relative_to(root)}: broken local link: {raw_target}")

    report = make_report(
        "link-audit",
        not errors,
        errors,
        warnings,
        {"markdown_files": len(markdown_files), "local_links_checked": checked, "broken_links": len(errors)},
    )
    if args.write:
        write_json(results_dir() / "link-audit.json", report)
    print_report(report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
