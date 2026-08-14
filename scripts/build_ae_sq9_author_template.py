#!/usr/bin/env python3
"""Build the taskless AE-SQ9 author authority from a verified F1B profile.

This module never accepts task, case, label, schedule, or result material.  It
exists to keep F1A implementation identity and F1B parent/freeze custody in
separate, machine-derived fields before either author lane opens.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from validate_ae_sq9_corpus import (
    CorpusContractError,
    expected_split_authority,
)


sys.dont_write_bytecode = True

PROGRAM_ID = "AE-SQ9"
CANDIDATE_ID = "AE-SQ9-SLEC-9"
HISTORICAL_INVENTORY = {
    "commit": "3762efae80ead1461d973b4737c5dcab6bae026a",
    "tree": "6a071b4ee33246cc2ef448cf4d574f51abc89348",
    "path": "evals/ae-sq4/f1/historical-task-digests.json",
    "blob": "6af74b660a9cf8fb04cde70abd527a88307f8cc3",
    "raw_sha256": "0e49a967d9a59021c0f1aa5fc8d80fd53fdf3ab1885925b0d86f1e8c4f9dc157",
    "content_sha256": "8ee69ae06f388c1b47386b312d31bcce7ae408d04e76659653335d55e12ac270",
    "count": 768,
}


class AuthorTemplateError(ValueError):
    """The verified profile cannot produce the sole lawful author template."""


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise AuthorTemplateError("template is not canonical finite JSON") from error


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def render_author_template(
    profile: Mapping[str, Any], *, split_id: str, author_id: str
) -> bytes:
    if split_id not in {"A", "B"}:
        raise AuthorTemplateError("split_id must be A or B")
    if not isinstance(author_id, str) or not author_id or len(author_id) > 128:
        raise AuthorTemplateError("author_id is invalid")
    try:
        authority = expected_split_authority(profile)
    except CorpusContractError as error:
        raise AuthorTemplateError("verified profile is invalid") from error
    if profile["implementation_commit"] == profile["freeze_commit"]:
        raise AuthorTemplateError("F1A implementation and F1B freeze are conflated")
    document = {
        "allowed_split_path": f"evals/ae-sq9/f2/split-{split_id.lower()}.json",
        "f1b_provenance_parent": {
            "commit": profile["freeze_commit"],
            "tree": profile["freeze_tree"],
        },
        "author_id": author_id,
        "candidate_id": CANDIDATE_ID,
        "f1_freeze": {
            "commit": profile["freeze_commit"],
            "path": profile["freeze_path"],
            "sha256": profile["freeze_sha256"],
            "tree": profile["freeze_tree"],
        },
        "historical_inventory": HISTORICAL_INVENTORY,
        "implementation_freeze": {
            "commit": profile["implementation_commit"],
            "tree": profile["implementation_tree"],
        },
        "program_id": PROGRAM_ID,
        "schema_version": "ae-sq9-author-template-v1",
        "split_authority": authority,
        "split_id": split_id,
    }
    raw = canonical_json(document)
    forbidden = (b'"cases"', b'"task_text"', b'"expected_capsules"', b'"result"')
    if any(token in raw for token in forbidden):
        raise AuthorTemplateError(
            "template contains forbidden corpus or result material"
        )
    return raw


def verify_author_template(
    raw: bytes, profile: Mapping[str, Any], *, split_id: str, author_id: str
) -> Mapping[str, Any]:
    try:
        decoded = json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuthorTemplateError("template is not strict UTF-8 JSON") from error
    expected = render_author_template(profile, split_id=split_id, author_id=author_id)
    if raw != expected or canonical_json(decoded) != raw:
        raise AuthorTemplateError("template bytes differ from the verified profile")
    return decoded


def main(argv: list[str] | None = None) -> int:
    import argparse
    from run_ae_sq9_aq import _load_base_state

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--gate-commit", required=True)
    parser.add_argument("--split-id", choices=("A", "B"), required=True)
    parser.add_argument("--author-id", required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve(strict=True)
    state = _load_base_state(root, args.gate_commit, preauthor=True)
    profile = state["profile"]
    if profile["freeze_commit"] != args.freeze_commit:
        raise AuthorTemplateError("F1G does not bind the requested F1B freeze")
    sys.stdout.buffer.write(
        render_author_template(
            profile, split_id=args.split_id, author_id=args.author_id
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
