#!/usr/bin/env python3
"""Run the Agentic 4.0.0 source-local release gates without default writes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# The default release path is a pure observation; importing its validator must not
# create bytecode artifacts in the checkout.
sys.dont_write_bytecode = True

from package_validation import (
    atomic_write_generated_json,
    repository_root,
    run_structural_release,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.write != bool(args.output):
        parser.error("--write and --output must be selected together")
    try:
        result = run_structural_release()
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
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
