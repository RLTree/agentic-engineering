#!/usr/bin/env python3
"""Run the Agentic 4.0.0 source-local release gates without default writes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from package_validation import (
    atomic_write_generated_json,
    render,
    repository_root,
    validate,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.write != bool(args.output):
        parser.error("--write and --output must be selected together")
    try:
        result = render(validate())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"release-check failed: {error}")
        return 1
    if args.write:
        root = repository_root()
        try:
            atomic_write_generated_json(root, args.output, result)
        except (OSError, ValueError) as error:
            print(f"release-check failed: {error}")
            return 1
    print(json.dumps({"passed": True, "gates": 14, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
