#!/usr/bin/env python3
"""Structural-only validator for the future AQ3 activation corpus.

The default entry point validates live AQ3 bytes against the exact frozen
commit and tree below. ``--working-tree`` is the bounded authoring check: it
accepts only the four corpus paths staged as additions and never writes.
"""
from __future__ import annotations

import hashlib
import itertools
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
CORPUS_RELATIVE = Path("evals/foundation-v4/future-activation-v3")
CORPUS_FILES = (
    CORPUS_RELATIVE / "activation-schema.json",
    CORPUS_RELATIVE / "activation-authoring.json",
    CORPUS_RELATIVE / "activation-heldout.json",
    CORPUS_RELATIVE / "README.md",
)

# Immutable AQ3 corpus custody, frozen before evaluator integration.
FROZEN_CORPUS_COMMIT: str | None = "ee7be80441ce06e53615df74505a1b4549a4aa90"
FROZEN_CORPUS_TREE: str | None = "e1c83c852b26a0c06753c591a689e1ecf00022b7"

ADVISERS = (
    "agentic-engineering",
    "codex-task-contract",
    "verification-strategy-engineering",
    "engineering-learning-loop",
)
CATALOG = frozenset({
    "architecture-boundary", "decision-contract", "verification-evidence",
    "learning-adoption", "decomposition-boundary", "no-change-abstention",
    "reference-isolation",
})
AUTOMATIC_DISTRIBUTION = Counter({
    "decomposition": 6, "task-contract": 6, "verification": 6,
    "learning": 6, "native-sufficient": 4, "near-neighbor": 4,
})
COMBINED_AUTOMATIC_DISTRIBUTION = Counter({key: count * 2 for key, count in AUTOMATIC_DISTRIBUTION.items()})
TRIGGER_ORDER = (
    "architecture-boundary", "decision-contract", "verification-evidence",
    "learning-adoption", "decomposition-boundary", "no-change-abstention",
    "reference-isolation",
)

# The closed, parent-resolved reduced-four catalog.  A reference expectation
# names a title, but its valid owner and trigger coverage are fixed here.  The
# AQ3 schema deliberately lists broader vocabulary; that must not make an
# unavailable title valid for this candidate surface.
REFERENCE_PAYLOADS = (
    ("aq-agentic-architecture", "agentic-engineering", "architecture-decision-table", frozenset({"architecture-boundary"})),
    ("aq-agentic-control", "agentic-engineering", "control-architecture-review", frozenset({"reference-isolation"})),
    ("aq-agentic-seven-layer", "agentic-engineering", "seven-layer-diagnostic", frozenset({"decomposition-boundary"})),
    ("aq-contract-assumption-approval", "codex-task-contract", "assumption-approval-policy", frozenset({"reference-isolation", "no-change-abstention"})),
    ("aq-contract-vocabulary", "codex-task-contract", "vocabulary-translator", frozenset({"decision-contract"})),
    ("aq-learning-attribution", "engineering-learning-loop", "failure-attribution-and-mechanism-hypotheses", frozenset({"reference-isolation"})),
    ("aq-learning-freshness", "engineering-learning-loop", "knowledge-freshness-supersession", frozenset({"learning-adoption", "no-change-abstention"})),
    ("aq-learning-hidden-evals", "engineering-learning-loop", "hidden-evals-mutation-spec-evolution", frozenset({"verification-evidence"})),
    ("aq-verify-boundary", "verification-strategy-engineering", "browser-field-and-effect-verification", frozenset({"reference-isolation"})),
    ("aq-verify-mode-selection", "verification-strategy-engineering", "verification-mode-selection", frozenset({"verification-evidence", "no-change-abstention"})),
    ("aq-verify-oracle-quality", "verification-strategy-engineering", "test-oracle-quality", frozenset({"verification-evidence"})),
)


@dataclass(frozen=True)
class ComparatorBinding:
    """An immutable historical source, read only through its verified tree."""

    commit: str
    tree: str
    paths: tuple[Path, ...]


AQ1_BINDING = ComparatorBinding(
    "407a2ac124856f0ce1fa33af8a61d0607e413820",
    "8314ca6ad82fa4687720692d8c5762c7aabf6261",
    (
        Path("evals/routing-cases.json"),
        Path("evals/foundation-v4/activation-authoring.json"),
        Path("evals/foundation-v4/activation-heldout.json"),
    ),
)
AQ2_BINDING = ComparatorBinding(
    "25de0cb1fe86a802768de9bf64659206d69650d0",
    "e5faff4b1a5ba678a7df1727b5bda3b3d0afe00a",
    (
        Path("evals/foundation-v4/future-activation-v2/activation-authoring.json"),
        Path("evals/foundation-v4/future-activation-v2/activation-heldout.json"),
    ),
)
COMPARATOR_BINDINGS = (AQ1_BINDING, AQ2_BINDING)


@dataclass(frozen=True)
class ComparatorFixture:
    """One-way comparator material; it deliberately retains no prompt text."""

    adviser_names: frozenset[str]
    exact_prompt_digests: frozenset[str]
    normalized_prompt_digests: frozenset[str]


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("document is not an object")
    return value


def load_bytes(value: bytes) -> dict[str, Any]:
    document = json.loads(value.decode("utf-8"))
    if not isinstance(document, dict):
        raise ValueError("document is not an object")
    return document


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def exact_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def prompt_digest(value: str) -> str:
    return hashlib.sha256(normalized(value).encode("utf-8")).hexdigest()


def adviser_name_pattern(names: frozenset[str]) -> re.Pattern[str]:
    variants = [re.escape(name).replace(r"\-", r"[-\s]+") for name in sorted(names, key=len, reverse=True)]
    if not variants:
        raise ValueError("empty historical adviser set")
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(variants) + r")(?![a-z0-9])", re.I)


def _git(root: Path, args: list[str], *, capture: bool = False) -> bytes | None:
    result = subprocess.run(
        ["git", *args], cwd=root, stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, check=False,
    )
    return result.stdout if result.returncode == 0 and capture else (b"" if result.returncode == 0 else None)


def _bound_documents(root: Path, binding: ComparatorBinding) -> list[dict[str, Any]]:
    if _git(root, ["cat-file", "-e", f"{binding.commit}^{{commit}}"] ) is None:
        raise ValueError("comparator commit unavailable")
    tree = _git(root, ["rev-parse", f"{binding.commit}^{{tree}}"], capture=True)
    if tree is None or tree.decode("ascii", errors="replace").strip() != binding.tree:
        raise ValueError("comparator tree mismatch")
    documents: list[dict[str, Any]] = []
    for path in binding.paths:
        source = _git(root, ["show", f"{binding.commit}:{path.as_posix()}"], capture=True)
        if source is None:
            raise ValueError("comparator path unavailable")
        documents.append(load_bytes(source))
    return documents


def _legacy_adviser_names(document: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for case in document.get("cases", []):
        if not isinstance(case, dict):
            continue
        for key in ("expected_skills", "must_not_select", "declared_invocation"):
            value = case.get(key)
            values = value if isinstance(value, list) else [value]
            names.update(item.strip() for item in values if isinstance(item, str) and item.strip())
        labels = case.get("hidden_labels")
        if isinstance(labels, dict):
            for key in ("expected_advisers", "must_not_select"):
                values = labels.get(key, [])
                names.update(item.strip() for item in values if isinstance(item, str) and item.strip())
    return names


def frozen_comparator_fixture(root: Path = ROOT) -> ComparatorFixture:
    """Read both AQ1 and AQ2 only from their separately verified historical trees."""
    documents = [document for binding in COMPARATOR_BINDINGS for document in _bound_documents(root, binding)]
    names = set(ADVISERS)
    exact: set[str] = set()
    normalized_digests: set[str] = set()
    for document in documents:
        names.update(_legacy_adviser_names(document))
        for case in document.get("cases", []):
            if isinstance(case, dict) and isinstance(case.get("prompt"), str):
                exact.add(exact_digest(case["prompt"]))
                normalized_digests.add(prompt_digest(case["prompt"]))
    return ComparatorFixture(frozenset(names), frozenset(exact), frozenset(normalized_digests))


def _error(errors: list[str], message: str) -> None:
    # Messages are aggregate rule names only: never include case IDs, labels, or prompts.
    errors.append(message)


def validate_readme(corpus_root: Path, errors: list[str]) -> None:
    try:
        readme = (corpus_root / "README.md").read_text(encoding="utf-8")
    except OSError:
        _error(errors, "README unavailable")
        return
    required = (
        "proposal-only, blinded, future-run-only",
        "no candidate authority, routing authority, effect authority, or claim authority",
        "not evidence that any candidate passes aq",
    )
    if any(phrase not in readme.casefold() for phrase in required):
        _error(errors, "README authority and claim ceiling mismatch")
    if re.search(r"(?i)(?<![0-9a-f])[0-9a-f]{7,64}(?![0-9a-f])", readme):
        _error(errors, "README commit binding detected")


def minimum_reference_expectations(expected_advisers: list[str], triggers: list[str]) -> tuple[dict[str, Any], ...] | None:
    """Project the parent's deterministic minimum-cover result into labels.

    Payload IDs break ties exactly as the candidate resolver does.  The public
    expectation contains no payload bytes or prompt data, only the fixed
    title/owner/trigger projection needed for structural validation.
    """
    required = set(triggers)
    if not required:
        return ()
    eligible = [payload for payload in REFERENCE_PAYLOADS if payload[1] in expected_advisers and payload[3] & required]
    eligible.sort(key=lambda payload: payload[0])
    selected: tuple[tuple[str, str, str, frozenset[str]], ...] | None = None
    for size in range(len(eligible) + 1):
        choices = [choice for choice in itertools.combinations(eligible, size) if set().union(*(payload[3] for payload in choice)) & required == required]
        if choices:
            selected = min(choices, key=lambda choice: tuple(payload[0] for payload in choice))
            break
    if selected is None or len(selected) > 3:
        return None
    by_trigger: dict[str, tuple[str, str, str, frozenset[str]]] = {}
    for trigger in required:
        covering = [payload for payload in selected if trigger in payload[3]]
        if not covering:
            return None
        by_trigger[trigger] = min(covering, key=lambda payload: payload[0])
    return tuple(
        {"trigger": trigger, "reference_title": by_trigger[trigger][2], "required": True}
        for trigger in TRIGGER_ORDER if trigger in required
    )


def _valid_labels(labels: Any) -> bool:
    if not isinstance(labels, dict):
        return False
    expected, denied, triggers, expectations = (
        labels.get("expected_advisers"), labels.get("must_not_select"),
        labels.get("reference_triggers"), labels.get("reference_expectations"),
    )
    if not all(isinstance(value, list) for value in (expected, denied, triggers, expectations)):
        return False
    if any(not isinstance(item, str) for values in (expected, denied, triggers) for item in values):
        return False
    if len(expected) != len(set(expected)) or len(denied) != len(set(denied)) or len(triggers) != len(set(triggers)):
        return False
    if set(expected) | set(denied) != set(ADVISERS) or set(expected) & set(denied) or set(triggers) - CATALOG:
        return False
    if not expected and (triggers or expectations):
        return False
    if len(expectations) != len(triggers) or len(expectations) > 3:
        return False
    seen_triggers: set[str] = set()
    for expectation in expectations:
        if not isinstance(expectation, dict):
            return False
        trigger, title = expectation.get("trigger"), expectation.get("reference_title")
        valid_triple = any(owner in expected and payload_title == title and trigger in payload_triggers for _, owner, payload_title, payload_triggers in REFERENCE_PAYLOADS)
        if not isinstance(trigger, str) or not isinstance(title, str) or trigger not in triggers or expectation.get("required") is not True or not valid_triple or trigger in seen_triggers:
            return False
        seen_triggers.add(trigger)
    expected_expectations = minimum_reference_expectations(expected, triggers)
    return seen_triggers == set(triggers) and expected_expectations is not None and tuple(expectations) == expected_expectations


def _precedence_matches(case: dict[str, Any], labels: dict[str, Any]) -> bool:
    precedence = case.get("precedence")
    if not isinstance(precedence, dict):
        return False
    expected = labels["expected_advisers"]
    denied = labels["must_not_select"]
    rule, primary, competing = precedence.get("rule"), precedence.get("primary_owner"), precedence.get("competing_owner")
    category, kind = case.get("category"), case.get("near_neighbor_kind")
    if category == "native-sufficient":
        return rule == "native-sufficient" and not expected and primary is None and competing is None
    if category == "near-neighbor" and kind == "exactly_two":
        return rule == "exactly-two-owners" and len(expected) == 2 and primary in expected and competing in expected and primary != competing
    if category == "near-neighbor" and kind == "precedence":
        return rule == "specific-over-umbrella" and len(expected) == 1 and primary == expected[0] and competing in denied
    return rule == "single-owner" and len(expected) == 1 and primary == expected[0] and competing is None


def validate_document(document: dict[str, Any], split: str, validator: Draft202012Validator,
                      name_re: re.Pattern[str], errors: list[str]) -> list[dict[str, Any]]:
    for error in validator.iter_errors(document):
        _error(errors, f"{split}: schema validation failed")
    if document.get("schema_version") != "3.0": _error(errors, f"{split}: schema version mismatch")
    if document.get("corpus_id") != f"foundation-v4-future-activation-v3-{split}": _error(errors, f"{split}: corpus ID mismatch")
    if document.get("split") != split: _error(errors, f"{split}: split mismatch")
    if (document.get("candidate_independent"), document.get("future_run_only"), document.get("no_replay_after_use")) != (True, True, True):
        _error(errors, f"{split}: corpus state flags mismatch")
    if document.get("routing_surface") != "fixed-four-adviser": _error(errors, f"{split}: routing surface mismatch")
    catalog = document.get("reference_catalog")
    if not isinstance(catalog, list) or set(catalog) != CATALOG or len(catalog) != len(CATALOG): _error(errors, f"{split}: reference catalog mismatch")
    cases = document.get("cases")
    if not isinstance(cases, list) or len(cases) != 36:
        _error(errors, f"{split}: case count mismatch")
        return []
    prefix = "A" if split == "authoring" else "H"
    if [case.get("id") if isinstance(case, dict) else None for case in cases] != [f"AQ3-{prefix}-{number:03d}" for number in range(1, 37)]:
        _error(errors, f"{split}: sequential IDs mismatch")
    automatic = [case for case in cases if isinstance(case, dict) and case.get("mode") == "automatic"]
    explicit = [case for case in cases if isinstance(case, dict) and case.get("mode") == "explicit"]
    if len(automatic) != 32 or len(explicit) != 4: _error(errors, f"{split}: mode count mismatch")
    if Counter(case.get("category") for case in automatic) != AUTOMATIC_DISTRIBUTION: _error(errors, f"{split}: automatic category mismatch")
    if Counter(case.get("declared_invocation") for case in explicit) != Counter(ADVISERS): _error(errors, f"{split}: explicit invocation distribution mismatch")
    if Counter(case.get("near_neighbor_kind") for case in automatic if case.get("category") == "near-neighbor") != Counter({"exactly_two": 2, "precedence": 2}):
        _error(errors, f"{split}: near-neighbor distribution mismatch")
    selected_zero_reference = [
        case for case in automatic
        if isinstance(case.get("hidden_labels"), dict)
        and isinstance(case["hidden_labels"].get("expected_advisers"), list)
        and case["hidden_labels"]["expected_advisers"]
        and case["hidden_labels"].get("reference_triggers") == []
    ]
    selected_zero_owners = [
        case["hidden_labels"]["expected_advisers"][0]
        for case in selected_zero_reference
        if len(case["hidden_labels"]["expected_advisers"]) == 1
        and isinstance(case.get("precedence"), dict)
        and case["precedence"].get("rule") == "single-owner"
        and case["precedence"].get("primary_owner") == case["hidden_labels"]["expected_advisers"][0]
        and case["precedence"].get("competing_owner") is None
    ]
    if len(selected_zero_reference) != 4 or Counter(selected_zero_owners) != Counter(ADVISERS):
        _error(errors, f"{split}: selected zero-reference distribution mismatch")
    for case in cases:
        if not isinstance(case, dict):
            _error(errors, f"{split}: non-object case")
            continue
        prompt, labels = case.get("prompt"), case.get("hidden_labels")
        if case.get("authority") != {"effect_authority": False, "claim_authority": False}:
            _error(errors, f"{split}: authority mismatch")
        if (case.get("condition_blind"), case.get("labels_visible_to_runner"), case.get("outcomes_visible_to_authoring")) != (True, False, False):
            _error(errors, f"{split}: blinding flags mismatch")
        anti_reuse = case.get("anti_reuse")
        if not isinstance(anti_reuse, dict) or (anti_reuse.get("origin"), anti_reuse.get("prior_prompt_content_reviewed"), anti_reuse.get("preuse_status"), anti_reuse.get("post_result_policy")) != ("aq3-independent-future-corpus", False, "unconsumed", "no-replay-create-new-future-holdout"):
            _error(errors, f"{split}: anti-reuse state mismatch")
        if not isinstance(prompt, str) or not _valid_labels(labels):
            _error(errors, f"{split}: hidden labels or prompt mismatch")
            continue
        if not _precedence_matches(case, labels): _error(errors, f"{split}: precedence mismatch")
        mode, category = case.get("mode"), case.get("category")
        if mode == "automatic":
            if name_re.search(prompt) or "$" in prompt: _error(errors, f"{split}: automatic adviser-name leakage")
            if case.get("declared_invocation") is not None or category == "explicit-invocation": _error(errors, f"{split}: automatic mode mismatch")
            if category != "near-neighbor" and case.get("near_neighbor_kind") is not None: _error(errors, f"{split}: non-neighbor kind mismatch")
        elif mode == "explicit":
            declared = case.get("declared_invocation")
            token = f"`${declared}`" if declared in ADVISERS else ""
            remainder = prompt.replace(token, "", 1) if token else prompt
            if category != "explicit-invocation" or not token or prompt.count("`") != 2 or prompt.count("$") != 1 or prompt.count(token) != 1 or prompt.count(declared) != 1 or name_re.search(remainder) or labels["expected_advisers"] != [declared] or case.get("near_neighbor_kind") is not None:
                _error(errors, f"{split}: explicit invocation mismatch")
        else:
            _error(errors, f"{split}: mode mismatch")
    return cases


def check_staged_corpus_only(root: Path) -> bool:
    result = _git(root, ["diff", "--cached", "--name-status", "-z"], capture=True)
    if result is None:
        return False
    fields = result.decode("utf-8", errors="replace").split("\0")
    pairs = list(zip(fields[0::2], fields[1::2]))
    expected = {str(path) for path in CORPUS_FILES}
    if any(code != "A" or not path for code, path in pairs) or {path for _, path in pairs} != expected or len(pairs) != len(expected):
        return False
    if _git(root, ["diff", "--cached", "--check"]) is None:
        return False
    for path in CORPUS_FILES:
        staged = _git(root, ["show", f":{path.as_posix()}"], capture=True)
        try:
            live = (root / path).read_bytes()
        except OSError:
            return False
        if staged is None or staged != live:
            return False
    return True


def frozen_corpus_errors(root: Path) -> list[str]:
    if not FROZEN_CORPUS_COMMIT or not FROZEN_CORPUS_TREE:
        return ["AQ3 frozen corpus binding unavailable"]
    if _git(root, ["cat-file", "-e", f"{FROZEN_CORPUS_COMMIT}^{{commit}}"] ) is None:
        return ["AQ3 frozen corpus commit unavailable"]
    tree = _git(root, ["rev-parse", f"{FROZEN_CORPUS_COMMIT}^{{tree}}"], capture=True)
    if tree is None or tree.decode("ascii", errors="replace").strip() != FROZEN_CORPUS_TREE:
        return ["AQ3 frozen corpus tree mismatch"]
    errors: list[str] = []
    for path in CORPUS_FILES:
        source = _git(root, ["show", f"{FROZEN_CORPUS_COMMIT}:{path.as_posix()}"], capture=True)
        try:
            live = (root / path).read_bytes()
        except OSError:
            live = None
        if source is None or live != source:
            _error(errors, "AQ3 frozen corpus byte mismatch")
    return errors


def validate(root: Path = ROOT, *, working_tree: bool = False, comparator_fixture: ComparatorFixture | None = None,
             enforce_frozen_corpus: bool | None = None) -> tuple[bool, list[str], dict[str, int]]:
    """Validate only structural integrity; never establish routing or outcome claims."""
    errors: list[str] = []
    if enforce_frozen_corpus is None:
        enforce_frozen_corpus = not working_tree
    try:
        comparator = comparator_fixture or frozen_comparator_fixture(root)
        corpus_root = root / CORPUS_RELATIVE
        schema = load(corpus_root / "activation-schema.json")
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        authoring = load(corpus_root / "activation-authoring.json")
        heldout = load(corpus_root / "activation-heldout.json")
        name_re = adviser_name_pattern(comparator.adviser_names)
    except Exception:
        return False, ["corpus input unavailable or invalid"], {}
    validate_readme(corpus_root, errors)
    cases = validate_document(authoring, "authoring", validator, name_re, errors) + validate_document(heldout, "heldout", validator, name_re, errors)
    families = [case.get("family_id") for case in cases]
    nonces = [case.get("anti_reuse", {}).get("case_nonce") if isinstance(case.get("anti_reuse"), dict) else None for case in cases]
    signatures = [tuple(case.get("anti_reuse", {}).get("semantic_signature", [])) if isinstance(case.get("anti_reuse"), dict) else None for case in cases]
    prompts = [case.get("prompt") for case in cases]
    if len(cases) != 72: _error(errors, "combined case count mismatch")
    if len(families) != len(set(families)) or any(not isinstance(value, str) or not value.strip() for value in families): _error(errors, "cross-split family uniqueness mismatch")
    if len(nonces) != len(set(nonces)) or any(not isinstance(value, str) or not value for value in nonces): _error(errors, "cross-split nonce uniqueness mismatch")
    if len(signatures) != len(set(signatures)) or any(not value for value in signatures): _error(errors, "cross-split signature uniqueness mismatch")
    digests = [prompt_digest(prompt) if isinstance(prompt, str) else None for prompt in prompts]
    if len(digests) != len(set(digests)) or any(not value for value in digests): _error(errors, "cross-split prompt uniqueness mismatch")
    if Counter(case.get("category") for case in cases if case.get("mode") == "automatic") != COMBINED_AUTOMATIC_DISTRIBUTION: _error(errors, "combined automatic category mismatch")
    if Counter(case.get("declared_invocation") for case in cases if case.get("mode") == "explicit") != Counter({adviser: 2 for adviser in ADVISERS}): _error(errors, "combined explicit invocation mismatch")
    if any(isinstance(prompt, str) and (exact_digest(prompt) in comparator.exact_prompt_digests or prompt_digest(prompt) in comparator.normalized_prompt_digests) for prompt in prompts):
        _error(errors, "historical prompt reuse detected")
    if working_tree and not check_staged_corpus_only(root): _error(errors, "staged corpus custody check failed")
    if enforce_frozen_corpus: errors.extend(frozen_corpus_errors(root))
    metrics = {"automatic_cases": sum(case.get("mode") == "automatic" for case in cases), "explicit_cases": sum(case.get("mode") == "explicit" for case in cases), "total_cases": len(cases)}
    return not errors, errors, metrics


def main() -> int:
    arguments = sys.argv[1:]
    if arguments not in ([], ["--working-tree"]):
        print("future-activation-corpus-v3: FAIL")
        print("- error: structural rule failed")
        return 2
    passed, errors, metrics = validate(working_tree=arguments == ["--working-tree"])
    print("future-activation-corpus-v3:", "PASS" if passed else "FAIL")
    for name in ("automatic_cases", "explicit_cases", "total_cases"):
        print(f"- {name}: {metrics.get(name, 0)}")
    print("- claim_ceiling: frozen-input structural integrity only")
    for _ in errors:
        print("- error: structural rule failed")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
