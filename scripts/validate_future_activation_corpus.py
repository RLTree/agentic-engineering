#!/usr/bin/env python3
"""Generic-only structural validation for the future AQ v2 frozen corpus."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CORPUS_RELATIVE = Path("evals/foundation-v4/future-activation-v2")
OLD_CORPUS_RELATIVE = Path("evals/foundation-v4")
FROZEN_CORPUS_COMMIT = "25de0cb1fe86a802768de9bf64659206d69650d0"
FROZEN_CORPUS_TREE = "e5faff4b1a5ba678a7df1727b5bda3b3d0afe00a"
FROZEN_COMPARATOR_COMMIT = "407a2ac124856f0ce1fa33af8a61d0607e413820"
FROZEN_COMPARATOR_TREE = "8314ca6ad82fa4687720692d8c5762c7aabf6261"
COMPARATOR_FILES = (
    Path("evals/routing-cases.json"),
    OLD_CORPUS_RELATIVE / "activation-authoring.json",
    OLD_CORPUS_RELATIVE / "activation-heldout.json",
)
STAGED_CORPUS_FILES = (
    CORPUS_RELATIVE / "activation-schema.json",
    CORPUS_RELATIVE / "activation-authoring.json",
    CORPUS_RELATIVE / "activation-heldout.json",
    CORPUS_RELATIVE / "README.md",
)
ADVISERS = (
    "agentic-engineering", "codex-task-contract",
    "verification-strategy-engineering", "engineering-learning-loop",
)
CATALOG = {
    "architecture-boundary", "decision-contract", "verification-evidence",
    "learning-adoption", "decomposition-boundary", "no-change-abstention",
    "reference-isolation",
}
AUTOMATIC_DISTRIBUTION = Counter({
    "decomposition": 6, "task-contract": 6, "verification": 6,
    "learning": 6, "native-sufficient": 4, "near-neighbor": 4,
})
COMBINED_DISTRIBUTION = Counter({key: value * 2 for key, value in AUTOMATIC_DISTRIBUTION.items()})
def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("document must be an object")
    return value


def load_bytes(value: bytes) -> dict[str, Any]:
    document = json.loads(value.decode("utf-8"))
    if not isinstance(document, dict):
        raise ValueError("document must be an object")
    return document


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def digest(value: str) -> str:
    return hashlib.sha256(normalized(value).encode("utf-8")).hexdigest()


def exact_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def adviser_name_pattern(names: set[str]) -> re.Pattern[str]:
    variants = [re.escape(name).replace(r"\-", r"[-\s]+") for name in sorted(names, key=len, reverse=True)]
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(variants) + r")(?![a-z0-9])", re.I)


@dataclass(frozen=True)
class ComparatorFixture:
    """One-way legacy comparator data; it deliberately contains no prompt text."""

    adviser_names: frozenset[str]
    old_exact_digests: frozenset[str]
    old_normalized_digests: frozenset[str]


def legacy_adviser_names(document: dict[str, Any]) -> set[str]:
    names = set(ADVISERS)
    for case in document.get("cases", []):
        if not isinstance(case, dict):
            continue
        for key in ("expected_skills", "must_not_select"):
            values = case.get(key, [])
            if isinstance(values, list):
                names.update(value.strip() for value in values if isinstance(value, str) and value.strip())
    return names


def old_prompt_digests(documents: tuple[dict[str, Any], dict[str, Any]]) -> tuple[set[str], set[str]]:
    """Read historical prompts only as one-way digests; never return their text."""
    exact: set[str] = set()
    historical: set[str] = set()
    for document in documents:
        for case in document.get("cases", []):
            if isinstance(case, dict) and isinstance(case.get("prompt"), str):
                exact.add(exact_digest(case["prompt"]))
                historical.add(digest(case["prompt"]))
    return exact, historical


def frozen_comparator_fixture(root: Path) -> ComparatorFixture:
    """Load all legacy comparators from one verified historical tree, never disk."""
    commit = subprocess.run(
        ["git", "cat-file", "-e", f"{FROZEN_COMPARATOR_COMMIT}^{{commit}}"],
        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    if commit.returncode != 0:
        raise ValueError("frozen comparator commit unavailable")
    tree = subprocess.run(
        ["git", "rev-parse", f"{FROZEN_COMPARATOR_COMMIT}^{{tree}}"],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    if tree.returncode != 0 or tree.stdout.decode("ascii", errors="replace").strip() != FROZEN_COMPARATOR_TREE:
        raise ValueError("frozen comparator tree mismatch")
    documents: list[dict[str, Any]] = []
    for path in COMPARATOR_FILES:
        source = subprocess.run(
            ["git", "show", f"{FROZEN_COMPARATOR_COMMIT}:{path.as_posix()}"],
            cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
        if source.returncode != 0:
            raise ValueError("frozen comparator path unavailable")
        documents.append(load_bytes(source.stdout))
    exact, historical = old_prompt_digests((documents[1], documents[2]))
    return ComparatorFixture(frozenset(legacy_adviser_names(documents[0])), frozenset(exact), frozenset(historical))


def validate_readme(corpus_root: Path, errors: list[str]) -> None:
    try:
        readme = (corpus_root / "README.md").read_text(encoding="utf-8")
    except OSError:
        errors.append("README unavailable")
        return
    required = (
        "frozen routing inputs, not a live routing result",
        "frozen-input integrity only",
        "no routing, outcome, or candidate authority is conferred by this corpus",
    )
    if any(phrase not in readme.casefold() for phrase in required): errors.append("README authority and claim ceiling mismatch")
    if re.search(r"(?i)(?<![0-9a-f])[0-9a-f]{7,64}(?![0-9a-f])", readme): errors.append("README commit binding detected")


def validate_document(document: dict[str, Any], split: str, validator: Draft202012Validator, name_re: re.Pattern[str], errors: list[str]) -> list[dict[str, Any]]:
    for error in validator.iter_errors(document):
        errors.append(f"{split}: schema validation failed at {'/'.join(str(part) for part in error.path) or 'root'}")
    if document.get("schema_version") != "2.0": errors.append(f"{split}: schema version mismatch")
    if document.get("corpus_id") != f"foundation-v4-future-activation-v2-{split}": errors.append(f"{split}: corpus ID mismatch")
    if document.get("split") != split: errors.append(f"{split}: split mismatch")
    if document.get("candidate_independent") is not True: errors.append(f"{split}: candidate independence mismatch")
    if document.get("routing_surface") != "fixed-four-adviser": errors.append(f"{split}: routing surface mismatch")
    if set(document.get("reference_catalog", [])) != CATALOG or len(document.get("reference_catalog", [])) != 7: errors.append(f"{split}: reference catalog mismatch")
    cases = document.get("cases")
    if not isinstance(cases, list) or len(cases) != 36:
        errors.append(f"{split}: case count mismatch")
        return []
    expected_ids = [f"AQ2-{'A' if split == 'authoring' else 'H'}-{number:03d}" for number in range(1, 37)]
    if [case.get("id") if isinstance(case, dict) else None for case in cases] != expected_ids: errors.append(f"{split}: sequential IDs mismatch")
    automatic = [case for case in cases if isinstance(case, dict) and case.get("mode") == "automatic"]
    explicit = [case for case in cases if isinstance(case, dict) and case.get("mode") == "explicit"]
    if len(automatic) != 32 or len(explicit) != 4: errors.append(f"{split}: mode count mismatch")
    if Counter(case.get("category") for case in automatic) != AUTOMATIC_DISTRIBUTION: errors.append(f"{split}: automatic distribution mismatch")
    if Counter(case.get("declared_invocation") for case in explicit) != Counter(ADVISERS): errors.append(f"{split}: explicit adviser distribution mismatch")
    if Counter(case.get("near_neighbor_kind") for case in automatic if case.get("category") == "near-neighbor") != Counter({"exactly_two": 2, "precedence": 2}): errors.append(f"{split}: near-neighbor distribution mismatch")
    for case in cases:
        if not isinstance(case, dict):
            errors.append(f"{split}: non-object case")
            continue
        case_id = case.get("id", "unknown")
        prompt = case.get("prompt")
        labels = case.get("hidden_labels")
        if case.get("authority") != {"effect_authority": False, "claim_authority": False}: errors.append(f"{split}: {case_id} authority mismatch")
        if (case.get("condition_blind"), case.get("labels_visible_to_runner"), case.get("outcomes_visible_to_authoring")) != (True, False, False): errors.append(f"{split}: {case_id} blinding mismatch")
        if not isinstance(prompt, str) or not isinstance(labels, dict):
            errors.append(f"{split}: {case_id} required content missing")
            continue
        expected = labels.get("expected_advisers")
        denied = labels.get("must_not_select")
        triggers = labels.get("reference_triggers")
        if not isinstance(expected, list) or not isinstance(denied, list) or not isinstance(triggers, list) or len(expected) > 2 or len(triggers) > 3 or len(expected) != len(set(expected)) or len(denied) != len(set(denied)) or len(triggers) != len(set(triggers)) or set(expected) - set(ADVISERS) or set(denied) - set(ADVISERS) or set(expected) & set(denied) or set(triggers) - CATALOG:
            errors.append(f"{split}: {case_id} hidden labels mismatch")
            continue
        if case.get("mode") == "automatic":
            if name_re.search(prompt) or "$" in prompt: errors.append(f"{split}: {case_id} automatic name leakage")
            if case.get("declared_invocation") is not None or case.get("category") == "explicit-invocation": errors.append(f"{split}: {case_id} automatic mode mismatch")
            if case.get("category") == "native-sufficient" and (expected or triggers): errors.append(f"{split}: {case_id} native-sufficient mismatch")
            if case.get("category") == "near-neighbor":
                if case.get("near_neighbor_kind") == "exactly_two" and len(expected) != 2: errors.append(f"{split}: {case_id} exactly-two mismatch")
                elif case.get("near_neighbor_kind") == "precedence" and (len(expected) != 1 or not denied): errors.append(f"{split}: {case_id} precedence mismatch")
                elif case.get("near_neighbor_kind") not in {"exactly_two", "precedence"}: errors.append(f"{split}: {case_id} near-neighbor kind mismatch")
            elif case.get("near_neighbor_kind") is not None: errors.append(f"{split}: {case_id} non-neighbor kind mismatch")
        elif case.get("mode") == "explicit":
            declared = case.get("declared_invocation")
            token = f"${declared}" if declared in ADVISERS else ""
            remainder = prompt.replace(token, "", 1)
            if case.get("category") != "explicit-invocation" or not token or prompt.count("$") != 1 or prompt.count(token) != 1 or name_re.search(remainder) or expected != [declared] or case.get("near_neighbor_kind") is not None:
                errors.append(f"{split}: {case_id} explicit invocation mismatch")
        else:
            errors.append(f"{split}: {case_id} mode mismatch")
    return cases


def check_owned_diff(root: Path) -> bool:
    paths = [str(CORPUS_RELATIVE), "scripts/validate_future_activation_corpus.py", "tests/test_future_activation_corpus.py"]
    result = subprocess.run(["git", "diff", "--check", "--", *paths], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return result.returncode == 0


def check_staged_corpus_only(root: Path) -> bool:
    expected = {str(path) for path in STAGED_CORPUS_FILES}
    status = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "-z"],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    if status.returncode != 0:
        return False
    fields = status.stdout.decode("utf-8", errors="replace").split("\0")
    pairs = list(zip(fields[0::2], fields[1::2]))
    if any(not code or not path or code != "A" for code, path in pairs):
        return False
    if {path for _, path in pairs} != expected or len(pairs) != len(expected):
        return False
    checked = subprocess.run(
        ["git", "diff", "--cached", "--check"],
        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    return checked.returncode == 0


def frozen_corpus_errors(root: Path) -> list[str]:
    """Return generic integrity failures for the committed, live corpus boundary."""
    commit = subprocess.run(
        ["git", "cat-file", "-e", f"{FROZEN_CORPUS_COMMIT}^{{commit}}"],
        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    if commit.returncode != 0:
        return ["frozen corpus commit unavailable"]
    tree = subprocess.run(
        ["git", "rev-parse", f"{FROZEN_CORPUS_COMMIT}^{{tree}}"],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    if tree.returncode != 0 or tree.stdout.decode("ascii", errors="replace").strip() != FROZEN_CORPUS_TREE:
        return ["frozen corpus tree mismatch"]
    errors: list[str] = []
    for relative in STAGED_CORPUS_FILES:
        source = subprocess.run(
            ["git", "show", f"{FROZEN_CORPUS_COMMIT}:{relative.as_posix()}"],
            cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
        try:
            live = (root / relative).read_bytes()
        except OSError:
            errors.append("frozen corpus byte mismatch")
            continue
        if source.returncode != 0 or source.stdout != live:
            errors.append("frozen corpus byte mismatch")
    return errors


def validate(root: Path = ROOT, *, check_git: bool = False, require_staged_corpus_only: bool = False,
             enforce_frozen_corpus: bool = True,
             comparator_fixture: ComparatorFixture | None = None) -> tuple[bool, list[str], dict[str, int]]:
    """Validate the corpus.

    ``enforce_frozen_corpus=False`` is draft-structural-only and exists solely
    for isolated mutation/unit fixtures. Such callers must supply an explicit
    comparator fixture; this function never falls back to mutable legacy files.
    """
    errors: list[str] = []
    try:
        comparator = comparator_fixture or frozen_comparator_fixture(root)
        corpus_root = root / CORPUS_RELATIVE
        schema = load(corpus_root / "activation-schema.json")
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        authoring = load(corpus_root / "activation-authoring.json")
        heldout = load(corpus_root / "activation-heldout.json")
        name_re = adviser_name_pattern(set(comparator.adviser_names))
        old_exact = comparator.old_exact_digests
        historical_digests = comparator.old_normalized_digests
    except Exception:
        return False, ["corpus input unavailable or invalid"], {}
    validate_readme(corpus_root, errors)
    cases = validate_document(authoring, "authoring", validator, name_re, errors) + validate_document(heldout, "heldout", validator, name_re, errors)
    families = [case.get("family_id") for case in cases]
    prompts = [case.get("prompt") for case in cases]
    if len(cases) != 72: errors.append("combined case count mismatch")
    if len(families) != len(set(families)) or any(not isinstance(value, str) for value in families): errors.append("cross-split family uniqueness mismatch")
    prompt_digests = [digest(prompt) if isinstance(prompt, str) else None for prompt in prompts]
    if len(prompt_digests) != len(set(prompt_digests)) or any(not value for value in prompt_digests): errors.append("cross-split prompt uniqueness mismatch")
    if Counter(case.get("category") for case in cases if case.get("mode") == "automatic") != COMBINED_DISTRIBUTION: errors.append("combined automatic distribution mismatch")
    if Counter(case.get("declared_invocation") for case in cases if case.get("mode") == "explicit") != Counter({adviser: 2 for adviser in ADVISERS}): errors.append("combined explicit adviser distribution mismatch")
    for prompt in prompts:
        if isinstance(prompt, str) and (exact_digest(prompt) in old_exact or digest(prompt) in historical_digests):
            errors.append("historical prompt reuse detected")
            break
    if check_git and not check_owned_diff(root): errors.append("owned-file diff check failed")
    if require_staged_corpus_only and not check_staged_corpus_only(root): errors.append("staged corpus custody check failed")
    if enforce_frozen_corpus:
        errors.extend(frozen_corpus_errors(root))
    metrics = {"automatic_cases": sum(case.get("mode") == "automatic" for case in cases), "explicit_cases": sum(case.get("mode") == "explicit" for case in cases), "total_cases": len(cases)}
    return not errors, errors, metrics


def main() -> int:
    require_staged = "--require-staged-corpus-only" in sys.argv[1:]
    if any(argument != "--require-staged-corpus-only" for argument in sys.argv[1:]):
        print("future-activation-corpus: FAIL")
        print("- error: structural rule failed")
        return 2
    passed, errors, metrics = validate(check_git=True, require_staged_corpus_only=require_staged)
    print("future-activation-corpus:", "PASS" if passed else "FAIL")
    for name in ("automatic_cases", "explicit_cases", "total_cases"):
        print(f"- {name}: {metrics.get(name, 0)}")
    print("- claim_ceiling: frozen-input integrity only; no live routing claim")
    for _ in errors: print("- error: structural rule failed")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
