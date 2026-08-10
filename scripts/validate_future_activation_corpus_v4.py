#!/usr/bin/env python3
"""Zero-write structural and custody validator for the AQ4 future corpus.

The live default is bound to the independently frozen AQ4 corpus commit/tree.
``--working-tree`` is the draft-only path and requires
exactly the four corpus files staged as additions with byte-identical working
copies.  Historical comparators are read only through verified ``git show``
bindings and are retained as one-way prompt digests.
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
CORPUS_RELATIVE = Path("evals/foundation-v4/future-activation-v4")
CORPUS_FILES = (
    CORPUS_RELATIVE / "activation-schema.json",
    CORPUS_RELATIVE / "activation-authoring.json",
    CORPUS_RELATIVE / "activation-heldout.json",
    CORPUS_RELATIVE / "README.md",
)
CANDIDATE_METADATA = Path("evals/foundation-v4/reduced-four-skills/candidate.json")

# Independently authored, structurally validated, and frozen before evaluator
# integration.  These bytes are future-run-only and become no-replay after use.
FROZEN_CORPUS_COMMIT = "f110be6ccb3460719141fea74b2fdb4313924718"
FROZEN_CORPUS_TREE = "ed3a0ee0afeb32f25033620519658b7b4774068c"

ATOMS = (
    "topology-control-boundary",
    "task-contract",
    "verification-strategy",
    "engineering-learning",
)
ATOM_TO_ADVISER = {
    "topology-control-boundary": "$agentic-engineering-lifecycle:agentic-engineering",
    "task-contract": "$agentic-engineering:codex-task-contract",
    "verification-strategy": "$agentic-engineering:verification-strategy-engineering",
    "engineering-learning": "$agentic-engineering:engineering-learning-loop",
}
ATOM_TO_CANDIDATE_ADVISER = {
    "topology-control-boundary": "agentic-engineering",
    "task-contract": "codex-task-contract",
    "verification-strategy": "verification-strategy-engineering",
    "engineering-learning": "engineering-learning-loop",
}
TRIGGER_ORDER = (
    "decomposition-boundary", "architecture-boundary", "reference-isolation",
    "no-change-abstention", "decision-contract", "verification-evidence",
    "learning-adoption",
)
REQUIRED_AUTHORITY = ["no_authority_assignment", "no_policy_adoption"]
REQUIRED_EFFECT = ["no_effect_execution", "no_external_action"]
REQUIRED_CLAIM = ["no_completion_claim", "no_efficacy_claim", "no_product_claim"]


@dataclass(frozen=True)
class ComparatorBinding:
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
AQ3_BINDING = ComparatorBinding(
    "ee7be80441ce06e53615df74505a1b4549a4aa90",
    "e1c83c852b26a0c06753c591a689e1ecf00022b7",
    (
        Path("evals/foundation-v4/future-activation-v3/activation-authoring.json"),
        Path("evals/foundation-v4/future-activation-v3/activation-heldout.json"),
    ),
)
COMPARATOR_BINDINGS = (AQ1_BINDING, AQ2_BINDING, AQ3_BINDING)


@dataclass(frozen=True)
class ComparatorFixture:
    prompt_digests: frozenset[str]


@dataclass(frozen=True)
class Payload:
    payload_id: str
    owner_atom: str
    triggers: frozenset[str]


@dataclass(frozen=True)
class ValidationResult:
    """Machine-facing structural result; it contains no prompt or outcome data."""

    errors: tuple[str, ...]
    metrics: dict[str, int]
    qualified_ids: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors


def _git(root: Path, args: list[str], *, capture: bool = False) -> bytes | None:
    result = subprocess.run(
        ["git", *args], cwd=root, stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, check=False,
    )
    return result.stdout if result.returncode == 0 and capture else (b"" if result.returncode == 0 else None)


def load_bytes(raw: bytes) -> dict[str, Any]:
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("not an object")
    return value


def load(path: Path) -> dict[str, Any]:
    return load_bytes(path.read_bytes())


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def prompt_digest(value: str) -> str:
    return hashlib.sha256(normalized(value).encode("utf-8")).hexdigest()


def _bound_documents(root: Path, binding: ComparatorBinding) -> list[dict[str, Any]]:
    if _git(root, ["cat-file", "-e", f"{binding.commit}^{{commit}}"] ) is None:
        raise ValueError("comparator commit unavailable")
    tree = _git(root, ["rev-parse", f"{binding.commit}^{{tree}}"], capture=True)
    if tree is None or tree.decode("ascii", errors="replace").strip() != binding.tree:
        raise ValueError("comparator tree mismatch")
    documents = []
    for path in binding.paths:
        raw = _git(root, ["show", f"{binding.commit}:{path.as_posix()}"], capture=True)
        if raw is None:
            raise ValueError("comparator path unavailable")
        documents.append(load_bytes(raw))
    return documents


def frozen_comparator_fixture(root: Path = ROOT) -> ComparatorFixture:
    digests: set[str] = set()
    for binding in COMPARATOR_BINDINGS:
        for document in _bound_documents(root, binding):
            for case in document.get("cases", []):
                if isinstance(case, dict) and isinstance(case.get("prompt"), str):
                    digests.add(prompt_digest(case["prompt"]))
    return ComparatorFixture(frozenset(digests))


def payload_catalog(root: Path) -> tuple[Payload, ...]:
    """Read permitted candidate metadata only; never reference content or schemas."""
    candidate = load(root / CANDIDATE_METADATA)
    if candidate.get("claim_ceiling") != "structural-proposal-only":
        raise ValueError("candidate metadata ceiling")
    skills = candidate.get("skills")
    if not isinstance(skills, list):
        raise ValueError("candidate metadata skills")
    owner_by_adviser = {adviser: atom for atom, adviser in ATOM_TO_CANDIDATE_ADVISER.items()}
    payloads: list[Payload] = []
    for skill in skills:
        if not isinstance(skill, dict) or not isinstance(skill.get("id"), str):
            raise ValueError("candidate metadata skill")
        owner = owner_by_adviser.get(skill["id"])
        refs = skill.get("references")
        if owner is None or not isinstance(refs, list):
            raise ValueError("candidate metadata mapping")
        for ref in refs:
            if (not isinstance(ref, dict) or not isinstance(ref.get("payload_id"), str)
                    or not isinstance(ref.get("trigger_ids"), list)
                    or ref.get("content_class") != "compact-reference"
                    or ref.get("full_schema_or_template") is not False):
                raise ValueError("candidate metadata reference")
            triggers = ref["trigger_ids"]
            if not triggers or any(trigger not in TRIGGER_ORDER for trigger in triggers):
                raise ValueError("candidate metadata triggers")
            payloads.append(Payload(ref["payload_id"], owner, frozenset(triggers)))
    if set(owner_by_adviser) != {skill.get("id") for skill in skills} or len({payload.payload_id for payload in payloads}) != len(payloads):
        raise ValueError("candidate metadata coverage")
    return tuple(sorted(payloads, key=lambda payload: payload.payload_id))


def minimum_reference_expectations(
    atoms: list[str], trigger_pairs: list[dict[str, str]], payloads: tuple[Payload, ...],
) -> tuple[dict[str, str], ...] | None:
    required = {(item["owner_atom"], item["trigger_id"]) for item in trigger_pairs}
    if not required:
        return ()
    eligible = [payload for payload in payloads if any(payload.owner_atom == atom and trigger in payload.triggers for atom, trigger in required)]
    selected: tuple[Payload, ...] | None = None
    for count in range(len(eligible) + 1):
        choices = [choice for choice in itertools.combinations(eligible, count)
                   if all(any(payload.owner_atom == atom and trigger in payload.triggers for payload in choice) for atom, trigger in required)]
        if choices:
            selected = min(choices, key=lambda choice: tuple(payload.payload_id for payload in choice))
            break
    if selected is None or len(selected) > 3:
        return None
    expected = []
    for atom, trigger in required:
        payload = min((payload for payload in selected if payload.owner_atom == atom and trigger in payload.triggers), key=lambda item: item.payload_id)
        expected.append({"owner_atom": atom, "trigger_id": trigger, "payload_id": payload.payload_id})
    return tuple(sorted(expected, key=lambda item: (ATOMS.index(item["owner_atom"]), TRIGGER_ORDER.index(item["trigger_id"]))))


def _error(errors: list[str], message: str) -> None:
    # Output is generic by contract: do not disclose IDs, labels, or prompts.
    errors.append(message)


def _alias_pattern() -> re.Pattern[str]:
    aliases = list(ATOMS) + list(ATOM_TO_ADVISER) + list(ATOM_TO_CANDIDATE_ADVISER.values()) + list(ATOM_TO_ADVISER.values())
    variants = [re.escape(alias).replace(r"\-", r"[-\s]+") for alias in sorted(aliases, key=len, reverse=True)]
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(variants) + r")(?![a-z0-9])", re.I)


def _valid_labels(case: dict[str, Any], payloads: tuple[Payload, ...]) -> bool:
    atoms = case.get("expected_decision_atoms")
    advisers = case.get("expected_advisers")
    denied = case.get("must_not_select")
    triggers = case.get("reference_triggers")
    expectations = case.get("deterministic_reference_expectations")
    if case.get("full_schema_or_template_expected") is not False:
        return False
    if not all(isinstance(value, list) for value in (atoms, advisers, denied, triggers, expectations)):
        return False
    if any(atom not in ATOMS for atom in atoms + denied) or len(atoms) != len(set(atoms)) or len(denied) != len(set(denied)):
        return False
    if advisers != [ATOM_TO_ADVISER[atom] for atom in atoms] or set(atoms) | set(denied) != set(ATOMS) or set(atoms) & set(denied):
        return False
    if not all(isinstance(item, dict) and set(item) == {"owner_atom", "trigger_id"} for item in triggers):
        return False
    if len({(item["owner_atom"], item["trigger_id"]) for item in triggers}) != len(triggers):
        return False
    if any(item["owner_atom"] not in atoms or item["trigger_id"] not in TRIGGER_ORDER for item in triggers):
        return False
    expected = minimum_reference_expectations(atoms, triggers, payloads)
    return expected is not None and tuple(expectations) == expected


def _precedence_valid(case: dict[str, Any]) -> bool:
    atoms = case["expected_decision_atoms"]
    precedence = case.get("precedence")
    if not isinstance(precedence, dict):
        return False
    applies, candidates, winner, rule = (precedence.get("applies"), precedence.get("candidate_atoms"), precedence.get("winner"), precedence.get("rule"))
    if not isinstance(candidates, list) or any(atom not in ATOMS for atom in candidates):
        return False
    if not atoms:
        return applies is False and candidates == [] and winner is None and rule is None and case.get("exactly_two") is False
    if case.get("exactly_two"):
        return applies is False and len(atoms) == 2 and candidates == [] and winner is None and rule is None
    if applies:
        return len(atoms) == 1 and set(candidates) == set(atoms) | {atom for atom in ATOMS if atom not in atoms and atom in candidates} and winner == atoms[0] and isinstance(rule, str) and rule.strip()
    return len(atoms) == 1 and candidates == [] and winner is None and rule is None and case.get("exactly_two") is False


def validate_document(document: dict[str, Any], split: str, schema_validator: Draft202012Validator,
                      payloads: tuple[Payload, ...], aliases: re.Pattern[str], errors: list[str]) -> list[dict[str, Any]]:
    if any(True for _ in schema_validator.iter_errors(document)):
        _error(errors, f"{split}: schema validation failed")
    if (document.get("schema_version"), document.get("corpus_id"), document.get("condition_blind"), document.get("claim_ceiling")) != ("aq4-activation-corpus-v4", f"aq4-{split}-v4", True, "structural-proposal-only"):
        _error(errors, f"{split}: corpus metadata mismatch")
    cases = document.get("cases")
    if not isinstance(cases, list) or len(cases) != 36:
        _error(errors, f"{split}: case count mismatch")
        return []
    ids = [case.get("id") if isinstance(case, dict) else None for case in cases]
    if len(ids) != len(set(ids)) or any(not isinstance(identifier, str) or not re.fullmatch(rf"aq4-{split}-[0-9]{{2}}", identifier) for identifier in ids):
        _error(errors, f"{split}: AQ4 ID mismatch")
    automatic = [case for case in cases if isinstance(case, dict) and case.get("mode") == "automatic"]
    explicit = [case for case in cases if isinstance(case, dict) and case.get("mode") == "explicit"]
    if len(automatic) != 32 or len(explicit) != 4:
        _error(errors, f"{split}: mode distribution mismatch")
    if sum(not case.get("expected_decision_atoms") for case in automatic) != 4:
        _error(errors, f"{split}: native distribution mismatch")
    if sum(case.get("exactly_two") is True for case in automatic) != 2:
        _error(errors, f"{split}: exactly-two distribution mismatch")
    if sum(isinstance(case.get("precedence"), dict) and case["precedence"].get("applies") is True for case in automatic) != 2:
        _error(errors, f"{split}: precedence distribution mismatch")
    selected_zero = [case for case in automatic if isinstance(case.get("expected_decision_atoms"), list) and len(case["expected_decision_atoms"]) == 1 and case.get("reference_triggers") == []]
    if Counter(case["expected_decision_atoms"][0] for case in selected_zero) != Counter(ATOMS):
        _error(errors, f"{split}: selected zero-reference distribution mismatch")
    for case in cases:
        if not isinstance(case, dict):
            _error(errors, f"{split}: case shape mismatch")
            continue
        prompt = case.get("prompt")
        if (case.get("authority_prohibitions"), case.get("effect_prohibitions"), case.get("claim_prohibitions")) != (REQUIRED_AUTHORITY, REQUIRED_EFFECT, REQUIRED_CLAIM):
            _error(errors, f"{split}: authority/effect/claim mismatch")
        if case.get("condition_blind") is not True or case.get("blinding_flags") != ["author_blind_to_candidate_selector", "author_blind_to_prior_outcomes"]:
            _error(errors, f"{split}: blinding mismatch")
        if not isinstance(prompt, str) or case.get("normalized_prompt") != normalized(prompt) or case.get("prompt_sha256") != prompt_digest(prompt):
            _error(errors, f"{split}: prompt digest mismatch")
        if not _valid_labels(case, payloads):
            _error(errors, f"{split}: mapping/label/reference mismatch")
            continue
        if not _precedence_valid(case):
            _error(errors, f"{split}: precedence mismatch")
        if case.get("mode") == "automatic":
            if aliases.search(prompt) or "$" in prompt or case.get("declared_invocation") is not None:
                _error(errors, f"{split}: automatic alias leakage")
        elif case.get("mode") == "explicit":
            declared = case.get("declared_invocation")
            if declared not in ATOM_TO_ADVISER.values() or case.get("expected_advisers") != [declared] or len(case.get("expected_decision_atoms", [])) != 1:
                _error(errors, f"{split}: explicit mapping mismatch")
            remainder = prompt.replace(declared, "", 1) if isinstance(declared, str) else prompt
            if not isinstance(declared, str) or prompt.count(declared) != 1 or prompt.count("$") != 1 or aliases.search(remainder):
                _error(errors, f"{split}: explicit invocation mismatch")
        else:
            _error(errors, f"{split}: mode mismatch")
    return cases


def check_staged_corpus_only(root: Path) -> bool:
    raw = _git(root, ["diff", "--cached", "--name-status", "-z"], capture=True)
    if raw is None:
        return False
    fields = raw.decode("utf-8", errors="replace").split("\0")
    pairs = list(zip(fields[0::2], fields[1::2]))
    expected = {path.as_posix() for path in CORPUS_FILES}
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
        return ["AQ4 frozen corpus binding unavailable"]
    if _git(root, ["cat-file", "-e", f"{FROZEN_CORPUS_COMMIT}^{{commit}}"] ) is None:
        return ["AQ4 frozen corpus commit unavailable"]
    tree = _git(root, ["rev-parse", f"{FROZEN_CORPUS_COMMIT}^{{tree}}"], capture=True)
    if tree is None or tree.decode("ascii", errors="replace").strip() != FROZEN_CORPUS_TREE:
        return ["AQ4 frozen corpus tree mismatch"]
    errors = []
    for path in CORPUS_FILES:
        source = _git(root, ["show", f"{FROZEN_CORPUS_COMMIT}:{path.as_posix()}"], capture=True)
        try:
            live = (root / path).read_bytes()
        except OSError:
            live = None
        if source is None or source != live:
            _error(errors, "AQ4 frozen corpus byte mismatch")
    return errors


def _validate_documents(schema_bytes: bytes, authoring_bytes: bytes, heldout_bytes: bytes, *, root: Path,
                        comparator_fixture: ComparatorFixture | None = None) -> ValidationResult:
    """Validate supplied corpus bytes without loading schemas, templates, or prompts from disk.

    This is the protocol entrypoint for an already-bound committed packet.  It
    returns only aggregate metrics, generic structural errors, and the 40
    evaluator-qualified IDs: all heldout automatic cases plus every explicit
    case across both splits.
    """
    errors: list[str] = []
    try:
        comparator = comparator_fixture or frozen_comparator_fixture(root)
        payloads = payload_catalog(root)
        schema = load_bytes(schema_bytes)
        # Draft 2020-12 permits its declared dialect and local refs only; no
        # resolver, template loader, or reference content is consulted.
        for value in re.findall(r'"\$ref"\s*:\s*"([^"]+)"', json.dumps(schema)):
            if not value.startswith("#/"):
                raise ValueError("nonlocal schema reference")
        Draft202012Validator.check_schema(schema)
        schema_validator = Draft202012Validator(schema)
        authoring = load_bytes(authoring_bytes)
        heldout = load_bytes(heldout_bytes)
    except Exception:
        return ValidationResult(("corpus input unavailable or invalid",), {}, ())
    aliases = _alias_pattern()
    authoring_cases = validate_document(authoring, "authoring", schema_validator, payloads, aliases, errors)
    heldout_cases = validate_document(heldout, "heldout", schema_validator, payloads, aliases, errors)
    cases = authoring_cases + heldout_cases
    values = {name: [case.get(name) for case in cases] for name in ("id", "family", "nonce", "normalized_prompt", "prompt_sha256")}
    if len(cases) != 72:
        _error(errors, "combined case count mismatch")
    for name, entries in values.items():
        if any(not isinstance(entry, str) or not entry.strip() for entry in entries) or len(entries) != len(set(entries)):
            _error(errors, f"cross-split {name} uniqueness mismatch")
    prompts = [case.get("prompt") for case in cases]
    if any(isinstance(prompt, str) and prompt_digest(prompt) in comparator.prompt_digests for prompt in prompts):
        _error(errors, "historical prompt reuse detected")
    qualified = tuple(
        case["id"] for case in heldout_cases if case.get("mode") == "automatic"
    ) + tuple(
        case["id"] for case in authoring_cases + heldout_cases if case.get("mode") == "explicit"
    )
    if len(qualified) != 40 or len(qualified) != len(set(qualified)):
        _error(errors, "qualified evaluation distribution mismatch")
        qualified = ()
    metrics = {"automatic_cases": sum(case.get("mode") == "automatic" for case in cases), "explicit_cases": sum(case.get("mode") == "explicit" for case in cases), "total_cases": len(cases), "qualified_cases": len(qualified)}
    return ValidationResult(tuple(errors), metrics, qualified)


def validate_frozen(root: Path, commit: str, tree: str) -> ValidationResult:
    """Validate an exact frozen corpus packet through verified ``git show`` bytes only.

    The supplied commit/tree are mandatory and are checked before any corpus
    bytes are read.  Generic errors keep comparator and corpus details sealed.
    """
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or not re.fullmatch(r"[0-9a-f]{40}", tree):
        return ValidationResult(("AQ4 frozen corpus binding unavailable",), {}, ())
    if _git(root, ["cat-file", "-e", f"{commit}^{{commit}}"] ) is None:
        return ValidationResult(("AQ4 frozen corpus commit unavailable",), {}, ())
    observed_tree = _git(root, ["rev-parse", f"{commit}^{{tree}}"], capture=True)
    if observed_tree is None or observed_tree.decode("ascii", errors="replace").strip() != tree:
        return ValidationResult(("AQ4 frozen corpus tree mismatch",), {}, ())
    sources = []
    for path in CORPUS_FILES:
        raw = _git(root, ["show", f"{commit}:{path.as_posix()}"], capture=True)
        if raw is None:
            return ValidationResult(("AQ4 frozen corpus byte mismatch",), {}, ())
        sources.append(raw)
    return _validate_documents(*sources[:3], root=root)


def validate(root: Path = ROOT, *, working_tree: bool = False, comparator_fixture: ComparatorFixture | None = None,
             enforce_frozen_corpus: bool | None = None) -> tuple[bool, list[str], dict[str, int]]:
    """Validate structure/custody only; never assess routing or model behavior."""
    if enforce_frozen_corpus is None:
        enforce_frozen_corpus = not working_tree
    try:
        corpus_root = root / CORPUS_RELATIVE
        packet = tuple((corpus_root / path.name).read_bytes() for path in CORPUS_FILES[:3])
    except Exception:
        return False, ["corpus input unavailable or invalid"], {}
    result = _validate_documents(*packet, root=root, comparator_fixture=comparator_fixture)
    errors = list(result.errors)
    if working_tree and not check_staged_corpus_only(root):
        _error(errors, "staged corpus custody check failed")
    if enforce_frozen_corpus:
        errors.extend(frozen_corpus_errors(root))
    return not errors, errors, result.metrics


def main() -> int:
    arguments = sys.argv[1:]
    if arguments not in ([], ["--working-tree"]):
        print("future-activation-corpus-v4: FAIL\n- error: structural rule failed")
        return 2
    passed, errors, metrics = validate(working_tree=arguments == ["--working-tree"])
    print("future-activation-corpus-v4:", "PASS" if passed else "FAIL")
    for name in ("automatic_cases", "explicit_cases", "total_cases"):
        print(f"- {name}: {metrics.get(name, 0)}")
    print("- claim_ceiling: frozen-input structural integrity only")
    for _ in errors:
        print("- error: structural rule failed")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
