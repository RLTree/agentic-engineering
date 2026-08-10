#!/usr/bin/env python3
"""Zero-write AQ7 freeze validator.

This module deliberately has no result/model path.  Normal use is fail-closed
until a corpus receipt is bound below; ``--working-tree`` is the narrow,
pre-freeze authoring-custody seam and requires the two split roots only.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, SchemaError


ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path("evals/foundation-v4/future-activation-v7")
SCHEMA = CORPUS / "activation-schema.json"
README = CORPUS / "README.md"
SPLITS = (CORPUS / "activation-authoring.json", CORPUS / "activation-heldout.json")
CONTRACT_COMMIT = "77d0502b88b6a69bd52cc09cbd4235b9ace119d0"
CONTRACT_TREE = "2b43d4f0b67ae9747fb07ea8dd5a77a6244281b4"
CONTRACT_HASHES = {SCHEMA: "47cc24936a28be13f496f2d0a6674f2998147eaa0030607f262f0769acf4aeb9", README: "8d842b4dbf2bcd06ddda1e4ed1eb7ff5a95d10507ee03d25a93bbcd62893f047"}
# AQ7's authorized one-way freeze receipt.
FROZEN_CORPUS_COMMIT: str | None = "4a8efb300a1cd26a72d8ac3bef1d1ba5250481ee"
FROZEN_CORPUS_TREE: str | None = "753d15a7b7dceacca7e66d39ab42fe89d94b237b"
FROZEN_CORPUS_HASHES: dict[Path, str] = {
    SPLITS[0]: "331c24018ca70164eaddf88ac6ff4a0cbe6a94b6017a9e73223559f6d264a225",
    SPLITS[1]: "fec755bd8838b3e23e96e8374bb28ad3e06229c176058a5a020f4a528326afd3",
}

H3 = ("ccbe06be9a2ef5feca4104b6918985ee9c4527c0", "dd20449fdc45a73c55adb349d8c828687728ef4d")
POLICY = ("c4e661a926e0ace78d9da83f71d9c52d311abb72", "f2abb05d32a888c9054ef2e7ab3ad0f08547de88")
BASE = ("f09a0544acf4b7a95fff796434273511a0683ca9", "38c8c8adf3bb633d33200df1ec65f33e985ae244")
H3_PATH = Path("evals/foundation-v4/decision-certificate-protocol-v6.json")
SELECTOR_PATH = Path("evals/foundation-v4/decision-certificate-selector-output-schema-v6.json")
POLICY_PATH = Path("evals/foundation-v4/decision-certificate-reference-policy-v6.json")
BASE_PATH = Path("evals/foundation-v4/reduced-four-skills/candidate.json")
AUTHORITY_HASHES = {
    H3_PATH: "9ad483a26fe339f81c947507de9c1c66d54b2823a38f68b1c5ee7fdf5c426f84",
    SELECTOR_PATH: "9742f2255fed5452df52f9da789a6f2fd72e89aa94c3c6847fad6944445f5b25",
    POLICY_PATH: "92982c278e33ff52edce1ba2a16082afb3ecc1989d8333a77eee9ca0911fee19",
    BASE_PATH: "854f67bdd03e7121bd20e5513ef61ac806d016b3a5f1d6e5891bf4d9e546eb1f",
}
ATOMS = ("topology-control-boundary", "task-contract", "verification-strategy", "engineering-learning")
ADVISERS = ("agentic-engineering", "codex-task-contract", "verification-strategy-engineering", "engineering-learning-loop")
INVOKE = re.compile(r"(?<![A-Za-z0-9_-])\$[A-Za-z][A-Za-z0-9-]*(?![A-Za-z0-9_-])")
NEAR_REWRITE_THRESHOLD = 0.30
_EXPECTED_INPUT_ERRORS = (OSError, UnicodeDecodeError, json.JSONDecodeError, SchemaError, TypeError, KeyError, ValueError, AttributeError, IndexError)


@dataclass(frozen=True)
class Comparator:
    commit: str
    tree: str
    directory: Path


COMPARATORS = (
    Comparator("407a2ac124856f0ce1fa33af8a61d0607e413820", "8314ca6ad82fa4687720692d8c5762c7aabf6261", Path("evals/foundation-v4")),
    Comparator("25de0cb1fe86a802768de9bf64659206d69650d0", "e5faff4b1a5ba678a7df1727b5bda3b3d0afe00a", Path("evals/foundation-v4/future-activation-v2")),
    Comparator("ee7be80441ce06e53615df74505a1b4549a4aa90", "e1c83c852b26a0c06753c591a689e1ecf00022b7", Path("evals/foundation-v4/future-activation-v3")),
    Comparator("f110be6ccb3460719141fea74b2fdb4313924718", "ed3a0ee0afeb32f25033620519658b7b4774068c", Path("evals/foundation-v4/future-activation-v4")),
    Comparator("39fd55df96e99e38d51d5fee13faa6b6294f9c43", "b7b9eb94ffe14a59e924ac2c40926e1a2dc513dd", Path("evals/foundation-v4/future-activation-v5")),
    Comparator("4ba09a422b5485a885c7e12409dae84639bdb513", "937c6ed971a4c58049ed3a5f8ee891f5d6b5809a", Path("evals/foundation-v4/future-activation-v6")),
)


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]
    metrics: dict[str, int]
    qualified_ids: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors


def _git(root: Path, args: list[str]) -> bytes | None:
    run = subprocess.run(["git", *args], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return run.stdout if run.returncode == 0 else None


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(raw: bytes) -> dict[str, Any]:
    result = json.loads(raw.decode("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("object")
    return result


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _prompt_hash(text: str) -> str:
    return _sha(_nfc(text).encode())


def _commit_file(root: Path, commit: str, path: Path) -> bytes:
    raw = _git(root, ["show", f"{commit}:{path.as_posix()}"])
    if raw is None:
        raise ValueError("immutable source")
    return raw


def _assert_commit(root: Path, commit: str, tree: str) -> None:
    if _git(root, ["cat-file", "-e", f"{commit}^{{commit}}"] ) is None:
        raise ValueError("immutable commit")
    observed = _git(root, ["rev-parse", f"{commit}^{{tree}}"])
    if observed is None or observed.decode().strip() != tree:
        raise ValueError("immutable tree")


def _contract_ok(root: Path) -> bool:
    try:
        _assert_commit(root, CONTRACT_COMMIT, CONTRACT_TREE)
        for path, digest in CONTRACT_HASHES.items():
            raw = _commit_file(root, CONTRACT_COMMIT, path)
            if _sha(raw) != digest or (root / path).read_bytes() != raw:
                return False
        return True
    except (OSError, ValueError):
        return False


def _authorities(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    for commit, tree in (H3, POLICY, BASE):
        _assert_commit(root, commit, tree)
    raws = {path: _commit_file(root, H3[0] if path in (H3_PATH, SELECTOR_PATH) else POLICY[0] if path == POLICY_PATH else BASE[0], path) for path in AUTHORITY_HASHES}
    if any(_sha(raws[path]) != digest for path, digest in AUTHORITY_HASHES.items()):
        raise ValueError("authority hash")
    h3, selector, policy, base = (_json(raws[p]) for p in (H3_PATH, SELECTOR_PATH, POLICY_PATH, BASE_PATH))
    if (h3.get("schema_version"), h3.get("status"), policy.get("schema_version"), policy.get("status")) != ("6.0", "frozen-proposal-only", "6.0", "frozen-proposal-only"):
        raise ValueError("authority status")
    if selector.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ValueError("selector dialect")
    return h3, selector, policy, base


def _parse(h3: dict[str, Any], task: str) -> tuple[str, list[str], list[str], list[str]]:
    grammar = h3["explicit_constraint"]["qualified_invocation_grammar"]
    text = _nfc(task)
    exact = re.findall(grammar["exact_pattern"], text)
    invoke = re.findall(grammar["invocation_like_pattern"], text)
    if any(token not in exact for token in invoke): return "unrecognized", [], exact, invoke
    if len(exact) > 1: return "ambiguous", [], exact, invoke
    if len(exact) == 1:
        mapping = {x["token"]: x["logical_atom"] for x in h3["explicit_constraint"]["ordered_token_to_logical_atom"]}
        return "exact", [mapping[exact[0]]], exact, invoke
    return "no_invocation_like", [], exact, invoke


def _select(h3: dict[str, Any], facts: list[dict[str, Any]]) -> tuple[str, list[str]]:
    states = {x.get("predicate_id"): x.get("state") for x in facts}
    selected = []
    for rule in h3["deterministic_selection"]["eligibility_rules"]:
        relevant = [*rule["positive_predicates"], rule["exclusion_predicate"]]
        if any(states.get(x) == "uncertain" for x in relevant): continue
        if any(states.get(x) == "present" for x in rule["positive_predicates"]) and states.get(rule["exclusion_predicate"]) == "absent": selected.append(rule["derived_atom"])
    return ("cap_exceeded", []) if len(selected) > h3["deterministic_selection"]["selection_cap"] else ("automatic", selected)


def _requests(h3: dict[str, Any], policy: dict[str, Any], facts: list[dict[str, Any]], status: str, atoms: list[str]) -> list[dict[str, str]]:
    if status not in policy["request_derivation"]["emitting_selection_statuses"]: return []
    states = {x["predicate_id"]: x["state"] for x in facts}; rules = {x["derived_atom"]: x for x in h3["deterministic_selection"]["eligibility_rules"]}; out = []
    for atom in atoms:
        if states[rules[atom]["exclusion_predicate"]] == "present": continue
        for row in policy["request_derivation"]["ordered_mapping_rows"]:
            if row["atom_id"] == atom and states[row["predicate_id"]] == "present":
                request = {"owner_adviser_id": row["adviser_id"], "trigger_id": row["trigger_id"]}
                if request not in out: out.append(request)
                break
    return out


def _cover(policy: dict[str, Any], base: dict[str, Any], requests: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    if not requests: return "resolved", []
    payloads = [{"owner_adviser_id": skill["id"], "payload_id": ref["payload_id"], "sha256": ref["sha256"], "trigger_ids": ref["trigger_ids"]} for skill in base["skills"] for ref in skill["references"]]
    eligible = [p for p in payloads if any(p["owner_adviser_id"] == r["owner_adviser_id"] and r["trigger_id"] in p["trigger_ids"] for r in requests)]
    for count in range(policy["canonical_cover"]["maximum_payloads"] + 1):
        options = [x for x in itertools.combinations(eligible, count) if all(any(p["owner_adviser_id"] == r["owner_adviser_id"] and r["trigger_id"] in p["trigger_ids"] for p in x) for r in requests)]
        if options:
            chosen = min(options, key=lambda x: tuple(sorted(p["payload_id"] for p in x)))
            return "resolved", [{k: p[k] for k in ("owner_adviser_id", "payload_id", "sha256")} for p in sorted(chosen, key=lambda x: x["payload_id"])]
    return "unresolved", []


def _family_ok(case: dict[str, Any], h3: dict[str, Any], facts: list[dict[str, Any]], status: str, atoms: list[str]) -> bool:
    family = case.get("case_family")
    if case.get("case_kind") == "explicit": return family == "exact-explicit" and len(atoms) == 1 and case.get("family_atom") == atoms[0] and not case.get("exactly_two")
    if family == "single-owner": return status == "automatic" and len(atoms) == 1 and case.get("family_atom") == atoms[0] and not case.get("exactly_two")
    if family == "exactly-two": return status == "automatic" and len(atoms) == 2 and case.get("family_atom") is None and case.get("exactly_two") is True
    if family == "native-no-advice": return not atoms and case.get("family_atom") is None and not case.get("exactly_two") and case.get("near_neighbor_kind") is None
    if family != "exclusion-or-uncertainty-near-neighbor" or atoms or case.get("family_atom") is not None or case.get("exactly_two") or case.get("near_neighbor_kind") not in ("exclusion", "uncertainty"): return False
    states = {x["predicate_id"]: x["state"] for x in facts}; matches = []
    for rule in h3["deterministic_selection"]["eligibility_rules"]:
        positive = any(states[p] == "present" for p in rule["positive_predicates"])
        if positive and states[rule["exclusion_predicate"]] == "present": matches.append("exclusion")
        if positive and any(states[p] == "uncertain" for p in [*rule["positive_predicates"], rule["exclusion_predicate"]]): matches.append("uncertainty")
    return matches == [case["near_neighbor_kind"]]


def _automatic_surface_ok(task: str) -> bool:
    normalized = re.sub(r"[-_\s]", "", _nfc(task)).casefold()
    return "$" not in task and not any(x.replace("-", "") in normalized for x in ADVISERS)


def _distribution(cases: list[dict[str, Any]]) -> bool:
    if len(cases) != 36 or Counter(x.get("case_kind") for x in cases) != {"automatic": 32, "explicit": 4}: return False
    c = Counter((x.get("case_family"), x.get("family_atom")) for x in cases)
    return (all(c[("single-owner", atom)] == 6 for atom in ATOMS) and c[("native-no-advice", None)] == 4 and c[("exactly-two", None)] == 2 and c[("exclusion-or-uncertainty-near-neighbor", None)] == 2 and c[("exact-explicit", "topology-control-boundary")] == c[("exact-explicit", "task-contract")] == c[("exact-explicit", "verification-strategy")] == c[("exact-explicit", "engineering-learning")] == 1 and Counter(x.get("near_neighbor_kind") for x in cases)["exclusion"] == Counter(x.get("near_neighbor_kind") for x in cases)["uncertainty"] == 1)


def _signature(text: str) -> set[str]:
    """Token-masked, NFC-normalized character four-grams; never diagnostic text."""
    # A single sentinel masks the mandatory exact token without contributing
    # token spelling or a large common n-gram surface to similarity scores.
    masked = INVOKE.sub("¤", _nfc(text)).casefold()
    compact = re.sub(r"\s+", " ", masked).strip()
    return {compact[index:index + 4] for index in range(max(0, len(compact) - 3))}


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 0.0


def _historical(root: Path) -> list[tuple[str, set[str], str]]:
    out = []
    for binding in COMPARATORS:
        _assert_commit(root, binding.commit, binding.tree)
        for leaf in ("activation-authoring.json", "activation-heldout.json"):
            doc = _json(_commit_file(root, binding.commit, binding.directory / leaf))
            for case in doc.get("cases", []):
                if isinstance(case, dict):
                    text = case.get("normalized_prompt", case.get("prompt"))
                    if isinstance(text, str): out.append((_prompt_hash(text), _signature(text), str(case.get("id", case.get("case_id", "historical")))))
    return out


def _validate_documents(root: Path, schema_raw: bytes, split_raws: tuple[bytes, bytes], *, historical: list[tuple[str, set[str], str]] | None = None) -> ValidationResult:
    try:
        h3, _, policy, base = _authorities(root); schema = _json(schema_raw)
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema": raise ValueError("schema")
        Draft202012Validator.check_schema(schema); validator = Draft202012Validator(schema)
        docs = (_json(split_raws[0]), _json(split_raws[1]))
    except _EXPECTED_INPUT_ERRORS:
        return ValidationResult(("structural authority unavailable",), {}, ())
    errors: list[str] = []; all_cases: list[dict[str, Any]] = []; groups: dict[str, list[dict[str, Any]]] = {}
    for split, doc in zip(("authoring", "heldout"), docs):
        if list(validator.iter_errors(doc)): errors.append("schema validation failed")
        cases = doc.get("cases")
        if not isinstance(cases, list) or any(not isinstance(x, dict) for x in cases): errors.append("case shape mismatch"); continue
        groups[split] = cases; all_cases += cases
        expected_ids = [f"AQ7-{'A' if split == 'authoring' else 'H'}-{i:03d}" for i in range(1, 37)]
        if [x.get("case_id") for x in cases] != expected_ids or not _distribution(cases): errors.append("split distribution mismatch")
        for case in cases:
            task = case.get("packet", {}).get("task_text") if isinstance(case.get("packet"), dict) else None; grading = case.get("grading")
            if not isinstance(task, str) or not isinstance(grading, dict) or task != _nfc(task) or case.get("prompt_sha256") != _prompt_hash(task): errors.append("packet hash or NFC mismatch"); continue
            facts = grading.get("expected_predicate_facts")
            if not isinstance(facts, list) or len(facts) != 12: errors.append("fact projection mismatch"); continue
            parse, parsed_atoms, exact, invoke = _parse(h3, task)
            if case.get("case_kind") == "explicit": status, atoms = (parse, parsed_atoms); constraint = {"parse_status": parse, "selected_atom": atoms[0] if atoms else None, "qualified_tokens": exact, "invocation_like_tokens": invoke}; surface = parse == "exact" and len(exact) == len(invoke) == 1
            else: status, atoms = _select(h3, facts); constraint = {"parse_status": "no_invocation_like", "selected_atom": None, "qualified_tokens": [], "invocation_like_tokens": []}; surface = _automatic_surface_ok(task)
            advisers = [ADVISERS[ATOMS.index(atom)] for atom in atoms]; requests = _requests(h3, policy, facts, status, atoms); resolved, payloads = _cover(policy, base, requests)
            if not surface or not _family_ok(case, h3, facts, status, atoms): errors.append("case semantics mismatch")
            if (grading.get("expected_selection_status"), grading.get("expected_selected_atoms"), grading.get("expected_selection_constraint"), grading.get("expected_advisers"), grading.get("expected_must_not_select_advisers"), grading.get("expected_reference_requests")) != (status, atoms, constraint, advisers, [x for x in ADVISERS if x not in advisers], requests): errors.append("derived projection mismatch")
            if grading.get("deterministic_reference_expectations") != {"status": resolved, "resolved_payload_count": len(payloads), "payloads": payloads, "derivation": "H3+frozen-reference-policy+base-candidate"}: errors.append("payload projection mismatch")
    fields = ("case_id", "nonce_sha256", "prompt_sha256")
    if len(all_cases) != 72 or any(len({x.get(f) for x in all_cases}) != 72 for f in fields): errors.append("combined uniqueness mismatch")
    max_similarity = 0.0
    authoring_cases, heldout_cases = groups.get("authoring", []), groups.get("heldout", [])
    for left, right in itertools.product(authoring_cases, heldout_cases):
        left_task, right_task = left.get("packet", {}).get("task_text", ""), right.get("packet", {}).get("task_text", "")
        if not isinstance(left_task, str) or not isinstance(right_task, str): continue
        score = _jaccard(_signature(left_task), _signature(right_task)); max_similarity = max(max_similarity, score)
        if score >= NEAR_REWRITE_THRESHOLD: errors.append(f"cross-split near rewrite: {left.get('case_id', 'unknown')}/{right.get('case_id', 'unknown')}")
    if historical is not None:
        for case in all_cases:
            task = case.get("packet", {}).get("task_text", "")
            if not isinstance(task, str): continue
            digest, sig = _prompt_hash(task), _signature(task)
            for old_digest, old_sig, _ in historical:
                score = _jaccard(sig, old_sig); max_similarity = max(max_similarity, score)
                if digest == old_digest or score >= NEAR_REWRITE_THRESHOLD: errors.append(f"historical reuse or near rewrite: {case.get('case_id', 'unknown')}")
    qualified = tuple(x["case_id"] for x in groups.get("heldout", []) if x.get("case_kind") == "automatic") + tuple(x["case_id"] for x in all_cases if x.get("case_kind") == "explicit")
    if len(qualified) != 40 or len(set(qualified)) != 40: errors.append("qualified set mismatch"); qualified = ()
    return ValidationResult(tuple(errors), {"total_cases": len(all_cases), "qualified_cases": len(qualified), "max_prompt_similarity_milli": round(max_similarity * 1000)}, qualified)


def check_staged_split_custody(root: Path) -> bool:
    raw = _git(root, ["diff", "--cached", "--name-status", "-z"])
    if raw is None or not _contract_ok(root): return False
    values = raw.decode("utf-8", "replace").split("\0"); pairs = [(values[i], values[i + 1]) for i in range(0, len(values) - 1, 2) if values[i]]
    if len(pairs) != 2 or {p for _, p in pairs} != {x.as_posix() for x in SPLITS} or any(code != "A" for code, _ in pairs): return False
    return all((staged := _git(root, ["show", f":{path.as_posix()}"])) is not None and staged == (root / path).read_bytes() for path in SPLITS)


def validate_frozen(root: Path = ROOT, commit: str | None = None, tree: str | None = None) -> ValidationResult:
    if not isinstance(FROZEN_CORPUS_COMMIT, str) or not isinstance(FROZEN_CORPUS_TREE, str) or commit not in (None, FROZEN_CORPUS_COMMIT) or tree not in (None, FROZEN_CORPUS_TREE): return ValidationResult(("AQ7 frozen corpus binding unavailable",), {}, ())
    try:
        if not _contract_ok(root) or set(FROZEN_CORPUS_HASHES) != set(SPLITS): raise ValueError("contract binding")
        _assert_commit(root, FROZEN_CORPUS_COMMIT, FROZEN_CORPUS_TREE)
        schema = _commit_file(root, FROZEN_CORPUS_COMMIT, SCHEMA); readme = _commit_file(root, FROZEN_CORPUS_COMMIT, README); splits = tuple(_commit_file(root, FROZEN_CORPUS_COMMIT, p) for p in SPLITS)
        if _sha(schema) != CONTRACT_HASHES[SCHEMA] or _sha(readme) != CONTRACT_HASHES[README]: raise ValueError("frozen contract drift")
        if any(_sha(x) != FROZEN_CORPUS_HASHES.get(p) or x != (root / p).read_bytes() for p, x in zip(SPLITS, splits)): raise ValueError("freeze bytes")
        return _validate_documents(root, schema, splits, historical=_historical(root))
    except _EXPECTED_INPUT_ERRORS:
        return ValidationResult(("AQ7 frozen corpus authority unavailable",), {}, ())


def validate(root: Path = ROOT, *, working_tree: bool = False) -> tuple[bool, list[str], dict[str, int]]:
    if not working_tree:
        result = validate_frozen(root); return result.passed, list(result.errors), result.metrics
    custody = False
    try:
        result = _validate_documents(root, (root / SCHEMA).read_bytes(), tuple((root / p).read_bytes() for p in SPLITS), historical=_historical(root))
        custody = check_staged_split_custody(root)
    except _EXPECTED_INPUT_ERRORS:
        result = ValidationResult(("structural corpus inputs unavailable",), {}, ())
    errors = list(result.errors)
    if not custody: errors.append("staged split custody failed")
    return not errors, errors, result.metrics


def main() -> int:
    args = sys.argv[1:]
    if args not in ([], ["--working-tree"]): print("future-activation-corpus-v7: FAIL\n- error: structural rule failed"); return 2
    passed, errors, metrics = validate(working_tree=args == ["--working-tree"])
    print("future-activation-corpus-v7:", "PASS" if passed else "FAIL")
    print(f"- total_cases: {metrics.get('total_cases', 0)}\n- qualified_cases: {metrics.get('qualified_cases', 0)}\n- claim_ceiling: structural corpus integrity only")
    for _ in errors: print("- error: structural rule failed")
    return 0 if passed else 1


if __name__ == "__main__": raise SystemExit(main())
