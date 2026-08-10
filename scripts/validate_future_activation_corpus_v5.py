#!/usr/bin/env python3
"""Zero-write structural and immutable-custody validator for AQ5.

AQ5 is deliberately unbound while it is being authored.  Its default path
therefore fails before reading any candidate corpus bytes.  Once the two
frozen constants are filled, the authoritative path reads only ``git show``
bytes from that commit and verifies that the live packet is byte-identical.
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
CORPUS_RELATIVE = Path("evals/foundation-v4/future-activation-v5")
CORPUS_FILES = (
    CORPUS_RELATIVE / "activation-schema.json",
    CORPUS_RELATIVE / "activation-authoring.json",
    CORPUS_RELATIVE / "activation-heldout.json",
    CORPUS_RELATIVE / "README.md",
)
CANDIDATE_METADATA = Path("evals/foundation-v4/reduced-four-skills/candidate.json")

# Independently authored AQ5 corpus G freeze receipt.  The commit/tree and
# per-file digests jointly bind the only authoritative packet.
FROZEN_CORPUS_COMMIT: str | None = "39fd55df96e99e38d51d5fee13faa6b6294f9c43"
FROZEN_CORPUS_TREE: str | None = "b7b9eb94ffe14a59e924ac2c40926e1a2dc513dd"
FROZEN_CORPUS_SHA256 = {
    CORPUS_FILES[0]: "0afb63ea9c89f48d1455dcead39453ebf05a8ed438517249b21f8c7ca90d63ea",
    CORPUS_FILES[1]: "69e5e796f191165a2556054caf3aa961e4a03a48025ac18bccc6b2e7b1bca4b3",
    CORPUS_FILES[2]: "c884713124f12271cd7bdd4cbed43f47312f2d15c0f16339ab954b9db65b971f",
    CORPUS_FILES[3]: "4a0d9a621173e816cad0c44bd9717b40ff8739fd724d2dca9be3916224ee4027",
}

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
BLINDING_FLAGS = ["author_blind_to_candidate_selector", "author_blind_to_prior_outcomes"]
CASE_FIELDS = frozenset((
    "id", "nonce", "family", "prompt", "normalized_prompt", "prompt_sha256", "mode",
    "expected_decision_atoms", "expected_advisers", "must_not_select", "reference_triggers",
    "deterministic_reference_expectations", "authority_prohibitions", "effect_prohibitions",
    "claim_prohibitions", "exactly_two", "precedence", "declared_invocation", "condition_blind",
    "blinding_flags", "full_schema_or_template_expected",
))


@dataclass(frozen=True)
class ComparatorBinding:
    commit: str
    tree: str
    paths: tuple[Path, ...]


AQ1_BINDING = ComparatorBinding(
    "407a2ac124856f0ce1fa33af8a61d0607e413820", "8314ca6ad82fa4687720692d8c5762c7aabf6261",
    (Path("evals/routing-cases.json"), Path("evals/foundation-v4/activation-authoring.json"),
     Path("evals/foundation-v4/activation-heldout.json")),
)
AQ2_BINDING = ComparatorBinding(
    "25de0cb1fe86a802768de9bf64659206d69650d0", "e5faff4b1a5ba678a7df1727b5bda3b3d0afe00a",
    (Path("evals/foundation-v4/future-activation-v2/activation-authoring.json"),
     Path("evals/foundation-v4/future-activation-v2/activation-heldout.json")),
)
AQ3_BINDING = ComparatorBinding(
    "ee7be80441ce06e53615df74505a1b4549a4aa90", "e1c83c852b26a0c06753c591a689e1ecf00022b7",
    (Path("evals/foundation-v4/future-activation-v3/activation-authoring.json"),
     Path("evals/foundation-v4/future-activation-v3/activation-heldout.json")),
)
AQ4_BINDING = ComparatorBinding(
    "f110be6ccb3460719141fea74b2fdb4313924718", "ed3a0ee0afeb32f25033620519658b7b4774068c",
    (Path("evals/foundation-v4/future-activation-v4/activation-authoring.json"),
     Path("evals/foundation-v4/future-activation-v4/activation-heldout.json")),
)
COMPARATOR_BINDINGS = (AQ1_BINDING, AQ2_BINDING, AQ3_BINDING, AQ4_BINDING)


@dataclass(frozen=True)
class ComparatorFixture:
    prompt_digests: frozenset[str]
    adviser_names: frozenset[str]


@dataclass(frozen=True)
class Payload:
    payload_id: str
    owner_atom: str
    triggers: frozenset[str]


@dataclass(frozen=True)
class ValidationResult:
    """Machine-facing result with aggregate counts only."""

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
    names: set[str] = set()
    for binding in COMPARATOR_BINDINGS:
        for document in _bound_documents(root, binding):
            for case in document.get("cases", []):
                if not isinstance(case, dict):
                    continue
                if isinstance(case.get("prompt"), str):
                    digests.add(prompt_digest(case["prompt"]))
                for adviser in case.get("expected_advisers", []):
                    if isinstance(adviser, str):
                        names.add(adviser.removeprefix("$").split(":")[-1])
                declared = case.get("declared_invocation")
                if isinstance(declared, str):
                    names.add(declared.removeprefix("$").split(":")[-1])
    return ComparatorFixture(frozenset(digests), frozenset(names))


def payload_catalog(root: Path) -> tuple[Payload, ...]:
    """Read fixed candidate metadata only; never reference or template content."""
    candidate = load_bytes((root / CANDIDATE_METADATA).read_bytes())
    if candidate.get("claim_ceiling") != "structural-proposal-only" or not isinstance(candidate.get("skills"), list):
        raise ValueError("candidate metadata")
    owner_by_adviser = {adviser: atom for atom, adviser in ATOM_TO_CANDIDATE_ADVISER.items()}
    payloads: list[Payload] = []
    seen_skills: set[str] = set()
    for skill in candidate["skills"]:
        if not isinstance(skill, dict) or not isinstance(skill.get("id"), str) or skill["id"] not in owner_by_adviser:
            raise ValueError("candidate mapping")
        seen_skills.add(skill["id"])
        references = skill.get("references")
        if not isinstance(references, list):
            raise ValueError("candidate references")
        for reference in references:
            if (not isinstance(reference, dict) or not isinstance(reference.get("payload_id"), str)
                    or not isinstance(reference.get("trigger_ids"), list)
                    or reference.get("content_class") != "compact-reference"
                    or reference.get("full_schema_or_template") is not False):
                raise ValueError("candidate reference")
            triggers = reference["trigger_ids"]
            if not triggers or any(trigger not in TRIGGER_ORDER for trigger in triggers):
                raise ValueError("candidate triggers")
            payloads.append(Payload(reference["payload_id"], owner_by_adviser[skill["id"]], frozenset(triggers)))
    if seen_skills != set(owner_by_adviser) or len({item.payload_id for item in payloads}) != len(payloads):
        raise ValueError("candidate coverage")
    return tuple(sorted(payloads, key=lambda item: item.payload_id))


def minimum_reference_expectations(
    atoms: list[str], triggers: list[str], payloads: tuple[Payload, ...],
) -> tuple[dict[str, str], ...] | None:
    required = set(triggers)
    if not required:
        return ()
    eligible = [item for item in payloads if item.owner_atom in atoms and item.triggers & required]
    selected: tuple[Payload, ...] | None = None
    for count in range(len(eligible) + 1):
        choices = [choice for choice in itertools.combinations(eligible, count)
                   if all(any(trigger in item.triggers for item in choice) for trigger in required)]
        if choices:
            selected = min(choices, key=lambda choice: tuple(item.payload_id for item in choice))
            break
    if selected is None or len(selected) > 3:
        return None
    expectations = []
    for trigger in required:
        payload = min((item for item in selected if trigger in item.triggers), key=lambda item: item.payload_id)
        expectations.append({"owner_atom": payload.owner_atom, "trigger_id": trigger, "payload_id": payload.payload_id})
    return tuple(sorted(expectations, key=lambda item: (ATOMS.index(item["owner_atom"]), TRIGGER_ORDER.index(item["trigger_id"]), item["payload_id"])))


def _error(errors: list[str], message: str) -> None:
    errors.append(message)  # Never include corpus identifiers, labels, or prompts.


def _alias_pattern(extra_names: frozenset[str]) -> re.Pattern[str]:
    aliases = set(ATOMS) | set(ATOM_TO_ADVISER) | set(ATOM_TO_CANDIDATE_ADVISER.values()) | set(ATOM_TO_ADVISER.values()) | set(extra_names)
    variants = [re.escape(alias).replace(r"\-", r"[-\s]+") for alias in sorted(aliases, key=len, reverse=True) if alias]
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(variants) + r")(?![a-z0-9])", re.I)


def _valid_labels(case: dict[str, Any], payloads: tuple[Payload, ...]) -> bool:
    atoms, advisers, denied = (case.get("expected_decision_atoms"), case.get("expected_advisers"), case.get("must_not_select"))
    triggers, expectations = case.get("reference_triggers"), case.get("deterministic_reference_expectations")
    if case.get("full_schema_or_template_expected") is not False or not all(isinstance(value, list) for value in (atoms, advisers, denied, triggers, expectations)):
        return False
    fixed_advisers = set(ATOM_TO_CANDIDATE_ADVISER.values())
    if any(atom not in ATOMS for atom in atoms) or any(adviser not in fixed_advisers for adviser in denied) or len(atoms) != len(set(atoms)) or len(denied) != len(set(denied)):
        return False
    if advisers != [ATOM_TO_CANDIDATE_ADVISER[atom] for atom in atoms] or set(advisers) | set(denied) != fixed_advisers or set(advisers) & set(denied):
        return False
    if not all(isinstance(item, str) for item in triggers):
        return False
    if len(set(triggers)) != len(triggers):
        return False
    if any(item not in TRIGGER_ORDER for item in triggers):
        return False
    expected = minimum_reference_expectations(atoms, triggers, payloads)
    return expected is not None and tuple(expectations) == expected and len(expectations) <= 3


def _precedence_valid(case: dict[str, Any]) -> bool:
    atoms, precedence = case["expected_decision_atoms"], case.get("precedence")
    if not isinstance(precedence, dict):
        return False
    applies, candidates, winner, rule = (precedence.get("applies"), precedence.get("candidate_atoms"), precedence.get("winner"), precedence.get("rule"))
    if not isinstance(candidates, list) or len(candidates) != len(set(candidates)) or any(atom not in ATOMS for atom in candidates):
        return False
    if not atoms:
        return applies is False and candidates == [] and winner is None and rule is None and case.get("exactly_two") is False
    if case.get("exactly_two"):
        return applies is False and len(atoms) == 2 and candidates == [] and winner is None and rule is None
    if applies is True:
        return len(atoms) == 1 and atoms[0] in candidates and len(candidates) >= 2 and winner == atoms[0] and isinstance(rule, str) and bool(rule.strip())
    return applies is False and len(atoms) == 1 and candidates == [] and winner is None and rule is None and case.get("exactly_two") is False


def _split_ids_valid(ids: list[Any], split: str) -> bool:
    prefix = {"authoring": "A", "heldout": "H"}.get(split)
    if prefix is None or len(ids) != 36 or any(not isinstance(item, str) for item in ids):
        return False
    expected = {f"AQ5-{prefix}-{number:03d}" for number in range(1, 37)}
    return set(ids) == expected


def _explicit_invocation_valid(case: dict[str, Any], prompt: str, aliases: re.Pattern[str]) -> bool:
    atoms = case.get("expected_decision_atoms")
    advisers = case.get("expected_advisers")
    if not isinstance(atoms, list) or len(atoms) != 1 or atoms[0] not in ATOMS:
        return False
    bare_expected = ATOM_TO_CANDIDATE_ADVISER[atoms[0]]
    declared = case.get("declared_invocation")
    if advisers != [bare_expected] or declared != f"${bare_expected}":
        return False
    remainder = prompt.replace(declared, "", 1)
    return prompt.count(declared) == 1 and not aliases.search(remainder)


def validate_document(document: dict[str, Any], split: str, schema_validator: Draft202012Validator,
                      payloads: tuple[Payload, ...], aliases: re.Pattern[str], errors: list[str]) -> list[dict[str, Any]]:
    if any(True for _ in schema_validator.iter_errors(document)):
        _error(errors, f"{split}: schema validation failed")
    if (document.get("schema_version"), document.get("corpus_id"), document.get("condition_blind"), document.get("claim_ceiling")) != ("aq5-activation-corpus-v5", f"aq5-{split}-v5", True, "structural-proposal-only"):
        _error(errors, f"{split}: corpus metadata mismatch")
    cases = document.get("cases")
    if not isinstance(cases, list) or len(cases) != 36:
        _error(errors, f"{split}: case count mismatch")
        return []
    ids = [case.get("id") if isinstance(case, dict) else None for case in cases]
    if not _split_ids_valid(ids, split):
        _error(errors, f"{split}: AQ5 ID mismatch")
    automatic = [case for case in cases if isinstance(case, dict) and case.get("mode") == "automatic"]
    explicit = [case for case in cases if isinstance(case, dict) and case.get("mode") == "explicit"]
    if len(automatic) != 32 or len(explicit) != 4:
        _error(errors, f"{split}: mode distribution mismatch")
    native = [case for case in automatic if case.get("expected_decision_atoms") == []]
    exact_two = [case for case in automatic if case.get("exactly_two") is True]
    precedence = [case for case in automatic if isinstance(case.get("precedence"), dict) and case["precedence"].get("applies") is True]
    ordinary_single = [case for case in automatic if isinstance(case.get("expected_decision_atoms"), list) and len(case["expected_decision_atoms"]) == 1 and case not in precedence]
    if len(native) != 4 or len(exact_two) != 2 or len(precedence) != 2 or len(ordinary_single) != 24 or Counter(case["expected_decision_atoms"][0] for case in ordinary_single) != Counter({atom: 6 for atom in ATOMS}):
        _error(errors, f"{split}: automatic distribution mismatch")
    selected_zero = [case for case in ordinary_single if case.get("reference_triggers") == []]
    if Counter(case["expected_decision_atoms"][0] for case in selected_zero) != Counter(ATOMS) or any(case.get("reference_triggers") != [] or case.get("deterministic_reference_expectations") != [] for case in native):
        _error(errors, f"{split}: zero-reference balance mismatch")
    if Counter(case.get("expected_decision_atoms", [None])[0] if isinstance(case.get("expected_decision_atoms"), list) and len(case["expected_decision_atoms"]) == 1 else None for case in explicit) != Counter(ATOMS):
        _error(errors, f"{split}: explicit distribution mismatch")
    for case in cases:
        if not isinstance(case, dict):
            _error(errors, f"{split}: case shape mismatch")
            continue
        if set(case) != CASE_FIELDS:
            _error(errors, f"{split}: case field set mismatch")
        prompt = case.get("prompt")
        if (case.get("authority_prohibitions"), case.get("effect_prohibitions"), case.get("claim_prohibitions")) != (REQUIRED_AUTHORITY, REQUIRED_EFFECT, REQUIRED_CLAIM):
            _error(errors, f"{split}: prohibition mismatch")
        if case.get("condition_blind") is not True or case.get("blinding_flags") != BLINDING_FLAGS:
            _error(errors, f"{split}: blinding mismatch")
        if not isinstance(prompt, str) or case.get("normalized_prompt") != normalized(prompt) or case.get("prompt_sha256") != prompt_digest(prompt):
            _error(errors, f"{split}: prompt digest mismatch")
        if not _valid_labels(case, payloads):
            _error(errors, f"{split}: mapping/label/reference mismatch")
            continue
        if not _precedence_valid(case):
            _error(errors, f"{split}: precedence mismatch")
        if case.get("mode") == "automatic":
            if aliases.search(prompt) or case.get("declared_invocation") is not None:
                _error(errors, f"{split}: automatic adviser leakage")
        elif case.get("mode") == "explicit":
            if not _explicit_invocation_valid(case, prompt, aliases):
                _error(errors, f"{split}: explicit invocation mismatch")
        else:
            _error(errors, f"{split}: mode mismatch")
    return cases


def check_staged_corpus_only(root: Path) -> bool:
    raw = _git(root, ["diff", "--cached", "--name-status", "-z"], capture=True)
    if raw is None:
        return False
    fields = raw.decode("utf-8", errors="replace").split("\0")
    pairs = [(fields[index], fields[index + 1]) for index in range(0, len(fields) - 1, 2) if fields[index]]
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


def _historical_reuse_detected(cases: list[dict[str, Any]], comparator: ComparatorFixture) -> bool:
    return any(isinstance(case.get("prompt"), str) and prompt_digest(case["prompt"]) in comparator.prompt_digests for case in cases)


def _validate_documents(schema_bytes: bytes, authoring_bytes: bytes, heldout_bytes: bytes, *, root: Path,
                        comparator_fixture: ComparatorFixture | None = None) -> ValidationResult:
    errors: list[str] = []
    try:
        comparator = comparator_fixture or frozen_comparator_fixture(root)
        payloads = payload_catalog(root)
        schema = load_bytes(schema_bytes)
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise ValueError("schema dialect")
        for value in re.findall(r'"\$ref"\s*:\s*"([^"]+)"', json.dumps(schema)):
            if not value.startswith("#/"):
                raise ValueError("nonlocal schema reference")
        Draft202012Validator.check_schema(schema)
        schema_validator = Draft202012Validator(schema)
        authoring, heldout = load_bytes(authoring_bytes), load_bytes(heldout_bytes)
    except Exception:
        return ValidationResult(("corpus input unavailable or invalid",), {}, ())
    aliases = _alias_pattern(comparator.adviser_names)
    authoring_cases = validate_document(authoring, "authoring", schema_validator, payloads, aliases, errors)
    heldout_cases = validate_document(heldout, "heldout", schema_validator, payloads, aliases, errors)
    cases = authoring_cases + heldout_cases
    values = {name: [case.get(name) for case in cases] for name in ("id", "family", "nonce", "normalized_prompt", "prompt_sha256")}
    if len(cases) != 72:
        _error(errors, "combined case count mismatch")
    for name, entries in values.items():
        if any(not isinstance(entry, str) or not entry.strip() for entry in entries) or len(entries) != len(set(entries)):
            _error(errors, f"cross-split {name} uniqueness mismatch")
    if _historical_reuse_detected(cases, comparator):
        _error(errors, "historical prompt reuse detected")
    qualified = tuple(case["id"] for case in heldout_cases if case.get("mode") == "automatic") + tuple(case["id"] for case in authoring_cases + heldout_cases if case.get("mode") == "explicit")
    if len(qualified) != 40 or len(qualified) != len(set(qualified)):
        _error(errors, "qualified evaluation distribution mismatch")
        qualified = ()
    metrics = {"automatic_cases": sum(case.get("mode") == "automatic" for case in cases), "explicit_cases": sum(case.get("mode") == "explicit" for case in cases), "total_cases": len(cases), "qualified_cases": len(qualified)}
    return ValidationResult(tuple(errors), metrics, qualified)


def validate_frozen(root: Path = ROOT, commit: str | None = None,
                    tree: str | None = None) -> ValidationResult:
    """Validate only the exact AQ5 G packet through immutable ``git show`` bytes."""
    if commit is None:
        commit = FROZEN_CORPUS_COMMIT
    if tree is None:
        tree = FROZEN_CORPUS_TREE
    if (not isinstance(FROZEN_CORPUS_COMMIT, str) or not isinstance(FROZEN_CORPUS_TREE, str)
            or not re.fullmatch(r"[0-9a-f]{40}", FROZEN_CORPUS_COMMIT)
            or not re.fullmatch(r"[0-9a-f]{40}", FROZEN_CORPUS_TREE)
            or commit != FROZEN_CORPUS_COMMIT or tree != FROZEN_CORPUS_TREE):
        return ValidationResult(("AQ5 frozen corpus binding unavailable",), {}, ())
    if _git(root, ["cat-file", "-e", f"{commit}^{{commit}}"] ) is None:
        return ValidationResult(("AQ5 frozen corpus commit unavailable",), {}, ())
    observed_tree = _git(root, ["rev-parse", f"{commit}^{{tree}}"], capture=True)
    if observed_tree is None or observed_tree.decode("ascii", errors="replace").strip() != tree:
        return ValidationResult(("AQ5 frozen corpus tree mismatch",), {}, ())
    sources: list[bytes] = []
    for path in CORPUS_FILES:
        source = _git(root, ["show", f"{commit}:{path.as_posix()}"], capture=True)
        try:
            live = (root / path).read_bytes()
        except OSError:
            live = None
        if (source is None or hashlib.sha256(source).hexdigest() != FROZEN_CORPUS_SHA256.get(path)
                or source != live):
            return ValidationResult(("AQ5 frozen corpus byte mismatch",), {}, ())
        sources.append(source)
    return _validate_documents(*sources[:3], root=root)


def validate(root: Path = ROOT, *, working_tree: bool = False,
             comparator_fixture: ComparatorFixture | None = None) -> tuple[bool, list[str], dict[str, int]]:
    """Validate custody and structure; default is immutable and fail-closed."""
    if not working_tree:
        result = validate_frozen(root)
        return result.passed, list(result.errors), result.metrics
    try:
        packet = tuple((root / path).read_bytes() for path in CORPUS_FILES[:3])
    except Exception:
        return False, ["corpus input unavailable or invalid"], {}
    result = _validate_documents(*packet, root=root, comparator_fixture=comparator_fixture)
    errors = list(result.errors)
    if not check_staged_corpus_only(root):
        _error(errors, "staged corpus custody check failed")
    return not errors, errors, result.metrics


def main() -> int:
    arguments = sys.argv[1:]
    if arguments not in ([], ["--working-tree"]):
        print("future-activation-corpus-v5: FAIL\n- error: structural rule failed")
        return 2
    passed, errors, metrics = validate(working_tree=arguments == ["--working-tree"])
    print("future-activation-corpus-v5:", "PASS" if passed else "FAIL")
    for name in ("automatic_cases", "explicit_cases", "total_cases", "qualified_cases"):
        print(f"- {name}: {metrics.get(name, 0)}")
    print("- claim_ceiling: frozen-input structural integrity only")
    for _ in errors:
        print("- error: structural rule failed")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
