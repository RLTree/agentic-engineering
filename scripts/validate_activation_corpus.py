#!/usr/bin/env python3
"""Zero-write structural qualification for the frozen AQ activation corpus."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "evals" / "foundation-v4"
ADVISERS = (
    "agentic-engineering",
    "codex-task-contract",
    "verification-strategy-engineering",
    "engineering-learning-loop",
)
CATALOG = {
    "architecture-boundary", "decision-contract", "verification-evidence",
    "learning-adoption", "decomposition-boundary", "no-change-abstention",
    "reference-isolation",
}
AUTOMATIC_DISTRIBUTION = {
    "decomposition": 6, "task-contract": 6, "verification": 6,
    "learning": 6, "native-sufficient": 4, "near-neighbor": 4,
}
ROOT_KEYS = {"schema_version", "corpus_id", "split", "candidate_independent", "routing_surface", "reference_catalog", "cases"}
CASE_KEYS = {"id", "family_id", "category", "mode", "prompt", "authority", "condition_blind", "labels_visible_to_runner", "outcomes_visible_to_authoring", "hidden_labels", "near_neighbor_kind", "declared_invocation"}
LABEL_KEYS = {"expected_advisers", "must_not_select", "reference_triggers"}
AUTHORITY_KEYS = {"effect_authority", "claim_authority"}
FAMILY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SCHEMA_METADATA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.local/agentic-engineering/evals/foundation-v4/activation-schema.json",
    "title": "Foundation V4 fixed-four-adviser activation corpus and route observation",
    "type": "object",
    "$ref": "#/$defs/corpus",
}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: document must be an object")
    return value


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def adviser_name_pattern(names: set[str]) -> re.Pattern[str]:
    variants = [re.escape(name).replace(r"\-", r"[-\s]+") for name in sorted(names, key=len, reverse=True)]
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(variants) + r")(?![a-z0-9])", re.I)


def validate_schema_metadata(root: Path, errors: list[str]) -> None:
    try:
        schema = load(root / "evals" / "foundation-v4" / "activation-schema.json")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors.append(f"schema: {error}")
        return
    if set(schema) != set(SCHEMA_METADATA) | {"$defs"}:
        errors.append("schema: root keys must be closed and exact")
    for key, value in SCHEMA_METADATA.items():
        if schema.get(key) != value:
            errors.append(f"schema: {key} is inaccurate")
    definitions = schema.get("$defs")
    if not isinstance(definitions, dict) or not {"corpus", "case", "hiddenLabels", "authority", "routeObservation"}.issubset(definitions):
        errors.append("schema: required corpus and route-observation definitions are missing")


def validate_document(document: dict[str, Any], split: str, errors: list[str], name_re: re.Pattern[str]) -> list[dict[str, Any]]:
    prefix = f"{split}:"
    if set(document) != ROOT_KEYS: errors.append(f"{prefix} root keys must be closed and exact")
    if document.get("schema_version") != "1.0": errors.append(f"{prefix} schema_version must be 1.0")
    if document.get("corpus_id") != f"foundation-v4-activation-{split}": errors.append(f"{prefix} corpus_id mismatch")
    if document.get("split") != split: errors.append(f"{prefix} split mismatch")
    if document.get("candidate_independent") is not True: errors.append(f"{prefix} candidate_independent must be true")
    if document.get("routing_surface") != "fixed-four-adviser": errors.append(f"{prefix} routing surface must be fixed-four-adviser")
    if set(document.get("reference_catalog", [])) != CATALOG or len(document.get("reference_catalog", [])) != len(CATALOG): errors.append(f"{prefix} reference catalog must be the closed catalog")
    cases = document.get("cases")
    if not isinstance(cases, list) or len(cases) != 36:
        errors.append(f"{prefix} must contain exactly 36 cases")
        return []
    expected_ids = [f"AQ-{'A' if split == 'authoring' else 'H'}-{index:03d}" for index in range(1, 37)]
    if [case.get("id") if isinstance(case, dict) else None for case in cases] != expected_ids:
        errors.append(f"{prefix} IDs must be exact sequential split IDs")
    automatic = [case for case in cases if isinstance(case, dict) and case.get("mode") == "automatic"]
    explicit = [case for case in cases if isinstance(case, dict) and case.get("mode") == "explicit"]
    if len(automatic) != 32 or len(explicit) != 4: errors.append(f"{prefix} requires 32 automatic and 4 explicit cases")
    if Counter(case.get("category") for case in automatic) != AUTOMATIC_DISTRIBUTION: errors.append(f"{prefix} automatic category distribution mismatch")
    if {case.get("declared_invocation") for case in explicit} != set(ADVISERS): errors.append(f"{prefix} explicit set must name each adviser once")
    if any(case.get("category") != "explicit-invocation" for case in explicit): errors.append(f"{prefix} explicit cases need explicit-invocation category")
    if Counter(case.get("near_neighbor_kind") for case in automatic if case.get("category") == "near-neighbor") != {"exactly_two": 2, "precedence": 2}: errors.append(f"{prefix} near-neighbor cases require two exactly_two and two precedence cases")
    for case in cases:
        if not isinstance(case, dict): errors.append(f"{prefix} case must be object"); continue
        cid = case.get("id", "?")
        if set(case) != CASE_KEYS: errors.append(f"{prefix} {cid}: case keys must be closed and exact")
        if not re.fullmatch(rf"AQ-{'A' if split == 'authoring' else 'H'}-\d{{3}}", str(cid)): errors.append(f"{prefix} {cid}: invalid id")
        if not isinstance(case.get("family_id"), str) or not FAMILY_RE.fullmatch(case["family_id"]): errors.append(f"{prefix} {cid}: family_id must be a lowercase hyphenated identifier")
        for key, expected in (("condition_blind", True), ("labels_visible_to_runner", False), ("outcomes_visible_to_authoring", False)):
            if case.get(key) is not expected: errors.append(f"{prefix} {cid}: {key} mismatch")
        if not isinstance(case.get("authority"), dict) or set(case["authority"]) != AUTHORITY_KEYS or case.get("authority") != {"effect_authority": False, "claim_authority": False}:
            errors.append(f"{prefix} {cid}: authority must deny both effect and claim authority")
        prompt = case.get("prompt")
        if not isinstance(prompt, str) or len(prompt) < 24: errors.append(f"{prefix} {cid}: prompt must be at least 24 characters"); continue
        labels = case.get("hidden_labels")
        if not isinstance(labels, dict): errors.append(f"{prefix} {cid}: hidden_labels required"); continue
        if set(labels) != LABEL_KEYS: errors.append(f"{prefix} {cid}: hidden_labels keys must be closed and exact")
        expected = labels.get("expected_advisers")
        must_not = labels.get("must_not_select")
        triggers = labels.get("reference_triggers")
        if not isinstance(expected, list) or len(expected) > 2 or len(expected) != len(set(expected)) or set(expected) - set(ADVISERS):
            errors.append(f"{prefix} {cid}: expected advisers must be unique known zero-to-two set")
            expected = []
        if not isinstance(must_not, list) or len(must_not) != len(set(must_not)) or set(must_not) - set(ADVISERS) or set(expected) & set(must_not):
            errors.append(f"{prefix} {cid}: must_not_select must be unique, fixed-four, and disjoint from expected")
            must_not = []
        if not isinstance(triggers, list) or len(triggers) > 3 or len(triggers) != len(set(triggers)) or set(triggers) - CATALOG:
            errors.append(f"{prefix} {cid}: reference triggers must be unique closed zero-to-three set")
            triggers = []
        if case.get("mode") == "automatic":
            if name_re.search(prompt): errors.append(f"{prefix} {cid}: automatic prompt leaks legacy or fixed-surface adviser name")
            if "$" in prompt: errors.append(f"{prefix} {cid}: automatic prompt contains forbidden dollar sign")
            if case.get("category") == "native-sufficient" and (expected != [] or triggers != []): errors.append(f"{prefix} {cid}: no-advice case must have empty expected set and no reference triggers")
            if case.get("category") == "near-neighbor":
                kind = case.get("near_neighbor_kind")
                if kind == "exactly_two" and len(expected) != 2: errors.append(f"{prefix} {cid}: exactly_two requires two advisers")
                if kind == "precedence" and (len(expected) != 1 or not must_not): errors.append(f"{prefix} {cid}: precedence requires one adviser and an actual competing adviser")
            elif case.get("near_neighbor_kind") is not None: errors.append(f"{prefix} {cid}: non-neighbor must not have neighbor kind")
            if case.get("declared_invocation") is not None: errors.append(f"{prefix} {cid}: automatic case must not declare invocation")
        elif case.get("mode") == "explicit":
            declared = case.get("declared_invocation")
            token = f"${declared}" if isinstance(declared, str) else ""
            remaining_prompt = prompt.replace(token, "", 1)
            if declared not in ADVISERS or prompt.count("$") != 1 or prompt.count(token) != 1 or name_re.search(remaining_prompt): errors.append(f"{prefix} {cid}: explicit prompt must contain exactly one declared dollar token and no other adviser token")
            if expected != [declared]: errors.append(f"{prefix} {cid}: explicit expected set must equal declared invocation")
            if case.get("near_neighbor_kind") is not None: errors.append(f"{prefix} {cid}: explicit case must not have neighbor kind")
        else: errors.append(f"{prefix} {cid}: invalid mode")
    return cases


def validate(root: Path = ROOT) -> tuple[bool, list[str], dict[str, int]]:
    errors: list[str] = []
    corpus_root = root / "evals" / "foundation-v4"
    try:
        authoring = load(corpus_root / "activation-authoring.json")
        heldout = load(corpus_root / "activation-heldout.json")
        legacy = load(root / "evals" / "routing-cases.json")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return False, [str(error)], {}
    validate_schema_metadata(root, errors)
    legacy_names = set(ADVISERS)
    for legacy_case in legacy.get("cases", []):
        if isinstance(legacy_case, dict):
            for key in ("expected_skills", "must_not_select"):
                values = legacy_case.get(key, [])
                if isinstance(values, list):
                    legacy_names.update(value for value in values if isinstance(value, str) and value)
    name_re = adviser_name_pattern(legacy_names)
    cases = validate_document(authoring, "authoring", errors, name_re) + validate_document(heldout, "heldout", errors, name_re)
    ids = [case.get("id") for case in cases]
    families = [case.get("family_id") for case in cases]
    prompts = [normalized(case.get("prompt", "")) for case in cases]
    for label, values in (("ids", ids), ("family IDs", families), ("prompts", prompts)):
        if len(values) != len(set(values)) or any(not value for value in values): errors.append(f"corpus {label} must be unique across files")
    legacy_prompts = {normalized(case.get("prompt", "")) for case in legacy.get("cases", []) if isinstance(case, dict)}
    if legacy_prompts.intersection(prompts): errors.append("corpus must not exactly reuse a legacy routing prompt")
    if len(cases) != 72: errors.append("combined corpus must contain exactly 72 cases")
    return not errors, errors, {"automatic_cases": sum(case.get("mode") == "automatic" for case in cases), "explicit_cases": sum(case.get("mode") == "explicit" for case in cases), "total_cases": len(cases)}


def main() -> int:
    passed, errors, metrics = validate()
    print("activation-corpus-structural-readiness:", "PASSED" if passed else "FAILED")
    for key, value in metrics.items(): print(f"- {key}: {value}")
    print("- claim_ceiling: frozen-input integrity only; no live routing claim")
    for error in errors: print(f"- error: {error}")
    return 0 if passed else 1


if __name__ == "__main__": raise SystemExit(main())
