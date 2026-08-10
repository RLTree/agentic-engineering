#!/usr/bin/env python3
"""Fail-closed AQ5 H2 candidate and frozen-case custody checker."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = "evals/foundation-v4/decision-atom-candidate-v5.json"
BASE_MANIFEST_PATH = "evals/foundation-v4/reduced-four-skills/candidate.json"
H2_PATH = "evals/foundation-v4/decision-atom-candidate-v4.json"
CORPUS_ROOT = "evals/foundation-v4/future-activation-v5"
CORPUS_SCHEMA_PATH = f"{CORPUS_ROOT}/activation-schema.json"
CORPUS_AUTHORING_PATH = f"{CORPUS_ROOT}/activation-authoring.json"
CORPUS_HELDOUT_PATH = f"{CORPUS_ROOT}/activation-heldout.json"
CORPUS_VALIDATOR_PATH = "scripts/validate_future_activation_corpus_v5.py"
SOURCE_COMMIT = "407a2ac124856f0ce1fa33af8a61d0607e413820"
SOURCE_TREE = "8314ca6ad82fa4687720692d8c5762c7aabf6261"
H2_AUTHORITY_COMMIT = "8ddf39198cb0e21f321a01a9755e009bb1c1860f"
H2_AUTHORITY_TREE = "1fbf9964b10831da051d2e5cafe29b6086d4d599"
ATOMS = ("topology-control-boundary", "task-contract", "verification-strategy", "engineering-learning")
ADVISERS = ("agentic-engineering", "codex-task-contract", "verification-strategy-engineering", "engineering-learning-loop")
ATOM_TO_ADVISER = dict(zip(ATOMS, ADVISERS, strict=True))
EXPLICIT_TOKENS = {atom: f"${adviser}" for atom, adviser in ATOM_TO_ADVISER.items()}
TRIGGERS = ("architecture-boundary", "decision-contract", "verification-evidence", "learning-adoption", "decomposition-boundary", "no-change-abstention", "reference-isolation")
CASE_FIELDS = frozenset((
    "id", "nonce", "family", "prompt", "normalized_prompt", "prompt_sha256", "mode",
    "expected_decision_atoms", "expected_advisers", "must_not_select", "reference_triggers",
    "deterministic_reference_expectations", "authority_prohibitions", "effect_prohibitions",
    "claim_prohibitions", "exactly_two", "precedence", "declared_invocation",
    "condition_blind", "blinding_flags", "full_schema_or_template_expected",
))
DOCUMENT_FIELDS = frozenset(("schema_version", "corpus_id", "condition_blind", "claim_ceiling", "cases"))
EVALUATOR_PATHS = (
    "evals/foundation-v4/activation-evaluator-schema-v5.json",
    "evals/foundation-v4/decision-atom-selector-output-schema.json",
    "scripts/check_reduced_four_skill_candidate_v5.py",
    "scripts/score_activation_v5.py",
    "scripts/run_activation_trials_v5.py",
    CORPUS_VALIDATOR_PATH,
)
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^AQ5-(A|H)-([0-9]{3})$")
UNBOUND = "UNBOUND_AQ5_"
DIRECT_ADMISSION = "Admit only for a direct instance of this controlling decision; topical relevance, downstream usefulness, and possible future need are insufficient."
AUTHORITY_PROHIBITIONS = ["no_authority_assignment", "no_policy_adoption"]
EFFECT_PROHIBITIONS = ["no_effect_execution", "no_external_action"]
CLAIM_PROHIBITIONS = ["no_completion_claim", "no_efficacy_claim", "no_product_claim"]
BLINDING_FLAGS = ["author_blind_to_candidate_selector", "author_blind_to_prior_outcomes"]


def sha256_bytes(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def canonical_sha256(value: Any) -> str: return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())


def git(root: Path, args: list[str], *, text: bool = False) -> bytes | str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=text)
    if result.returncode:
        detail = result.stderr if text else result.stderr.decode(errors="replace")
        raise ValueError(detail.strip() or "immutable Git input unavailable")
    return result.stdout


def git_show(root: Path, commit: str, path: str) -> bytes: return bytes(git(root, ["show", f"{commit}:{path}"]))
def resolve_commit(root: Path, commit: str) -> str: return str(git(root, ["rev-parse", "--verify", f"{commit}^{{commit}}"], text=True)).strip()
def git_tree(root: Path, commit: str) -> str: return str(git(root, ["rev-parse", "--verify", f"{commit}^{{tree}}"], text=True)).strip()
def _read(root: Path, path: str, commit: str | None) -> bytes: return git_show(root, commit, path) if commit else (root / path).read_bytes()


def _json_object(raw: bytes, label: str) -> dict[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict): raise ValueError(f"{label} is not an object")
    return value


def load_candidate(root: Path = ROOT, commit: str | None = None) -> dict[str, Any]: return _json_object(_read(root, MANIFEST_PATH, commit), "AQ5 candidate")
def load_base(root: Path = ROOT, commit: str | None = None) -> tuple[dict[str, Any], bytes]:
    raw = _read(root, BASE_MANIFEST_PATH, commit); return _json_object(raw, "base candidate"), raw
def load_h2(root: Path = ROOT, commit: str | None = None) -> tuple[dict[str, Any], bytes]:
    raw = _read(root, H2_PATH, commit); return _json_object(raw, "H2 candidate"), raw
def h2_projection(h2: dict[str, Any]) -> dict[str, Any]: return {"atom_to_adviser": h2["atom_to_adviser"], "conditions": h2["conditions"]}


def unresolved(candidate: dict[str, Any]) -> list[str]:
    found: list[str] = []
    def walk(value: Any, path: str) -> None:
        if isinstance(value, str) and value.startswith(UNBOUND): found.append(path)
        elif isinstance(value, dict):
            for key, item in value.items(): walk(item, f"{path}.{key}" if path else key)
        elif isinstance(value, list):
            for index, item in enumerate(value): walk(item, f"{path}[{index}]")
    walk(candidate, ""); return sorted(found)


def require_bound(candidate: dict[str, Any]) -> None:
    missing = unresolved(candidate)
    if missing: raise ValueError("AQ5 live execution is unbound: " + ", ".join(missing))


def protocol(candidate: dict[str, Any], root: Path = ROOT, commit: str | None = None) -> dict[str, Any]:
    if resolve_commit(root, H2_AUTHORITY_COMMIT) != H2_AUTHORITY_COMMIT or git_tree(root, H2_AUTHORITY_COMMIT) != H2_AUTHORITY_TREE:
        raise ValueError("AQ5 H2 authority custody mismatch")
    authority, _ = load_h2(root, H2_AUTHORITY_COMMIT)
    candidate_h2, _ = load_h2(root, commit)
    authority_projection = h2_projection(authority)
    candidate_projection = h2_projection(candidate_h2)
    binding = candidate.get("h2_protocol")
    expected = {"status": "unchanged", "path": H2_PATH, "projection_sha256": canonical_sha256(authority_projection)}
    if binding != expected: raise ValueError("H2 protocol projection custody mismatch")
    if canonical_sha256(candidate_projection) != canonical_sha256(authority_projection):
        raise ValueError("H2 candidate projection changed from frozen authority")
    return candidate_projection


def conditions(candidate: dict[str, Any], root: Path = ROOT, commit: str | None = None) -> dict[str, Any]: return protocol(candidate, root, commit)["conditions"]


def atom_mapping(candidate: dict[str, Any], root: Path = ROOT, commit: str | None = None) -> dict[str, str]:
    rows = protocol(candidate, root, commit)["atom_to_adviser"]
    if not isinstance(rows, list) or [row.get("atom_id") for row in rows if isinstance(row, dict)] != list(ATOMS): raise ValueError("H2 atom mapping order mismatch")
    mapping = {row["atom_id"]: row["adviser_id"] for row in rows}
    if mapping != ATOM_TO_ADVISER or len(set(mapping.values())) != 4: raise ValueError("H2 atom mapping is not total and injective")
    if any(row.get("explicit_token") != EXPLICIT_TOKENS[row["atom_id"]] for row in rows): raise ValueError("H2 explicit token mismatch")
    return mapping


def map_atoms(candidate: dict[str, Any], atoms: Iterable[str], root: Path = ROOT, commit: str | None = None) -> list[str]:
    selected = list(atoms)
    if len(selected) > 2 or len(selected) != len(set(selected)) or any(atom not in ATOMS for atom in selected): raise ValueError("selected atoms outside closed 0-2 contract")
    mapping = atom_mapping(candidate, root, commit); return [mapping[atom] for atom in selected]


def validate_atom_catalog(catalog: Any) -> None:
    if not isinstance(catalog, list) or [row.get("atom_id") for row in catalog if isinstance(row, dict)] != list(ATOMS): raise ValueError("AQ5 H2 atom catalog order mismatch")
    for row in catalog:
        if set(row) != {"atom_id", "declared_scope", "positive_boundary", "admission_rule", "pairwise_exclusions"}: raise ValueError("AQ5 H2 atom catalog surface mismatch")
        if not isinstance(row["declared_scope"], str) or not row["declared_scope"].strip() or not isinstance(row["positive_boundary"], str) or not row["positive_boundary"].startswith("Own ") or not row["positive_boundary"].endswith(" itself.") or row["admission_rule"] != DIRECT_ADMISSION: raise ValueError("AQ5 H2 decision-boundary language mismatch")
        exclusions = row["pairwise_exclusions"]
        if not isinstance(exclusions, list) or any(not isinstance(item, dict) or set(item) != {"atom_id", "boundary"} or not isinstance(item["boundary"], str) or not item["boundary"].startswith("Exclude when ") for item in exclusions): raise ValueError("AQ5 H2 pairwise exclusion surface mismatch")
        if {item["atom_id"] for item in exclusions} != set(ATOMS) - {row["atom_id"]} or len(exclusions) != 3: raise ValueError("AQ5 H2 pairwise exclusions incomplete")
    serialized = json.dumps(catalog, sort_keys=True, separators=(",", ":"))
    if "adviser_id" in serialized or "explicit_token" in serialized or any(adviser in serialized for adviser in ADVISERS): raise ValueError("AQ5 H2 catalog exposes adviser mapping")


def parse_constraint(task: str) -> dict[str, str | None]:
    found = [atom for atom, token in EXPLICIT_TOKENS.items() if re.search(rf"(?<![A-Za-z0-9_:$-]){re.escape(token)}(?![A-Za-z0-9_$-])", task)]
    if len(found) == 1: return {"status": "exact", "atom_id": found[0]}
    if len(found) > 1: return {"status": "ambiguous", "atom_id": None}
    return {"status": "none", "atom_id": None}


def enforce_constraint(selected: list[str], constraint: dict[str, Any]) -> list[str]:
    if constraint == {"status": "none", "atom_id": None}: return selected
    if constraint.get("status") == "exact" and selected == [constraint.get("atom_id")]: return selected
    if constraint == {"status": "ambiguous", "atom_id": None} and not selected: return selected
    raise ValueError("selection violates explicit constraint")


def validate_case_shape(case: Any) -> None:
    if not isinstance(case, dict) or set(case) != CASE_FIELDS: raise ValueError("AQ5 frozen case top-level shape mismatch")
    identity = ID_RE.fullmatch(case["id"]) if isinstance(case["id"], str) else None
    if identity is None or not 1 <= int(identity.group(2)) <= 36: raise ValueError("AQ5 case identity mismatch")
    if case["mode"] not in {"automatic", "explicit"} or not isinstance(case["prompt"], str) or not case["prompt"]: raise ValueError("AQ5 case mode or prompt mismatch")
    normalized = " ".join(case["prompt"].casefold().split())
    if case["normalized_prompt"] != normalized or not SHA_RE.fullmatch(case["prompt_sha256"]) or sha256_bytes(normalized.encode()) != case["prompt_sha256"]: raise ValueError("AQ5 prompt custody mismatch")
    value = case["expected_decision_atoms"]
    if not isinstance(value, list) or len(value) > 2 or len(value) != len(set(value)) or any(item not in ATOMS for item in value): raise ValueError("AQ5 expected_decision_atoms mismatch")
    expected_advisers = [ATOM_TO_ADVISER[atom] for atom in case["expected_decision_atoms"]]
    if case["expected_advisers"] != expected_advisers: raise ValueError("AQ5 expected adviser mapping mismatch")
    expected_exclusions = [adviser for adviser in ADVISERS if adviser not in expected_advisers]
    if case["must_not_select"] != expected_exclusions: raise ValueError("AQ5 must_not_select complement mismatch")
    triggers = case["reference_triggers"]
    if not isinstance(triggers, list) or len(triggers) != len(set(triggers)) or any(item not in TRIGGERS for item in triggers): raise ValueError("AQ5 top-level reference_triggers mismatch")
    if not isinstance(case["exactly_two"], bool) or case["exactly_two"] != (len(case["expected_decision_atoms"]) == 2): raise ValueError("AQ5 exactly-two marker mismatch")
    precedence = case["precedence"]
    if not isinstance(precedence, dict) or set(precedence) != {"applies", "candidate_atoms", "winner", "rule"} or not isinstance(precedence["applies"], bool): raise ValueError("AQ5 precedence shape mismatch")
    candidate_atoms = precedence["candidate_atoms"]
    if not isinstance(candidate_atoms, list) or len(candidate_atoms) > 2 or len(candidate_atoms) != len(set(candidate_atoms)) or any(atom not in ATOMS for atom in candidate_atoms): raise ValueError("AQ5 precedence candidate atoms mismatch")
    if precedence["applies"]:
        if len(candidate_atoms) != 2 or precedence["winner"] not in candidate_atoms or case["expected_decision_atoms"] != [precedence["winner"]] or not isinstance(precedence["rule"], str) or not precedence["rule"].strip(): raise ValueError("AQ5 precedence true branch mismatch")
    elif candidate_atoms or precedence["winner"] is not None or precedence["rule"] is not None:
        raise ValueError("AQ5 precedence false branch mismatch")
    constraint = parse_constraint(case["prompt"])
    if case["mode"] == "explicit":
        if len(case["expected_decision_atoms"]) != 1: raise ValueError("AQ5 explicit case must have one atom")
        token = EXPLICIT_TOKENS[case["expected_decision_atoms"][0]]
        if case["declared_invocation"] != token or len(re.findall(rf"(?<![A-Za-z0-9_:$-]){re.escape(token)}(?![A-Za-z0-9_$-])", case["prompt"])) != 1 or constraint != {"status": "exact", "atom_id": case["expected_decision_atoms"][0]}: raise ValueError("AQ5 explicit invocation mismatch")
    elif case["declared_invocation"] is not None or constraint != {"status": "none", "atom_id": None}:
        raise ValueError("AQ5 automatic invocation mismatch")
    if not isinstance(case["nonce"], str) or not case["nonce"].strip() or not isinstance(case["family"], str) or not case["family"].strip(): raise ValueError("AQ5 nonce or family mismatch")
    if case["condition_blind"] is not True or case["full_schema_or_template_expected"] is not False or case["authority_prohibitions"] != AUTHORITY_PROHIBITIONS or case["effect_prohibitions"] != EFFECT_PROHIBITIONS or case["claim_prohibitions"] != CLAIM_PROHIBITIONS or case["blinding_flags"] != BLINDING_FLAGS: raise ValueError("AQ5 fixed prohibitions or blinding mismatch")
    expectations = case["deterministic_reference_expectations"]
    if not isinstance(expectations, list) or len(expectations) > 3 or any(not isinstance(item, dict) or set(item) != {"owner_atom", "trigger_id", "payload_id"} or item["owner_atom"] not in ATOMS or item["trigger_id"] not in TRIGGERS or not isinstance(item["payload_id"], str) or not item["payload_id"] for item in expectations): raise ValueError("AQ5 deterministic reference expectation mismatch")
    if "hidden_labels" in case: raise ValueError("AQ5 nested labels prohibited")


def validate_case_references(case: dict[str, Any], base: dict[str, Any]) -> None:
    expected_advisers = [ATOM_TO_ADVISER[atom] for atom in case["expected_decision_atoms"]]
    outcome = resolve_payloads(base, case["reference_triggers"], expected_advisers)
    if outcome["status"] != "resolved" or len(outcome["records"]) > 3:
        raise ValueError("AQ5 deterministic references do not fully resolve")
    adviser_to_atom = {adviser: atom for atom, adviser in ATOM_TO_ADVISER.items()}
    expected = [
        {"owner_atom": adviser_to_atom[row["owner_adviser_id"]], "trigger_id": trigger, "payload_id": row["payload_id"]}
        for trigger in case["reference_triggers"]
        for row in outcome["records"]
        if trigger in row["trigger_ids"]
    ]
    if case["deterministic_reference_expectations"] != expected:
        raise ValueError("AQ5 deterministic reference expectations mismatch")


def validate_document_shape(document: Any, base: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if not isinstance(document, dict) or set(document) != DOCUMENT_FIELDS: raise ValueError("AQ5 frozen document top-level shape mismatch")
    if document["schema_version"] != "aq5-activation-corpus-v5" or document["corpus_id"] not in {"aq5-authoring-v5", "aq5-heldout-v5"} or document["condition_blind"] is not True or document["claim_ceiling"] != "structural-proposal-only": raise ValueError("AQ5 document identity mismatch")
    if not isinstance(document["cases"], list): raise ValueError("AQ5 document cases mismatch")
    cases = document["cases"]
    for case in cases: validate_case_shape(case)
    identifiers = {case["id"] for case in cases}
    split = "A" if document["corpus_id"] == "aq5-authoring-v5" else "H"
    expected_identifiers = {f"AQ5-{split}-{index:03d}" for index in range(1, 37)}
    if len(cases) != 36 or identifiers != expected_identifiers: raise ValueError("AQ5 frozen document identity set mismatch")
    if sum(case["mode"] == "automatic" for case in cases) != 32 or sum(case["mode"] == "explicit" for case in cases) != 4: raise ValueError("AQ5 frozen document mode distribution mismatch")
    if base is not None:
        for case in cases: validate_case_references(case, base)
    return cases


def _base_skill(base: dict[str, Any], adviser: str) -> dict[str, Any]: return next(row for row in base["skills"] if row["id"] == adviser)
def payload_catalog(base: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for adviser in ADVISERS:
        for ref in _base_skill(base, adviser)["references"]:
            rows.append({"payload_id": ref["payload_id"], "owner_adviser_id": adviser, "source_path": ref["path"], "sha256": ref["sha256"], "trigger_ids": list(ref["trigger_ids"]), "content_class": ref["content_class"], "full_schema_or_template": ref["full_schema_or_template"]})
    return sorted(rows, key=lambda row: row["payload_id"])


def resolve_payloads(base: dict[str, Any], triggers: Iterable[str], advisers: list[str]) -> dict[str, Any]:
    required = set(triggers)
    if not required.issubset(TRIGGERS) or len(advisers) > 2 or len(advisers) != len(set(advisers)) or any(item not in ADVISERS for item in advisers): raise ValueError("reference resolver input mismatch")
    eligible = [row for row in payload_catalog(base) if row["owner_adviser_id"] in advisers and required.intersection(row["trigger_ids"])]
    def covered(rows: tuple[dict[str, Any], ...]) -> set[str]: return (set().union(*(set(row["trigger_ids"]) for row in rows)) if rows else set()) & required
    for size in range(len(eligible) + 1):
        choices = [rows for rows in itertools.combinations(eligible, size) if covered(rows) == required]
        if choices:
            choice = min(choices, key=lambda rows: tuple(row["payload_id"] for row in rows))
            return {"status": "cap_exceeded", "resolved_count": size, "records": []} if size > 3 else {"status": "resolved", "resolved_count": size, "records": list(choice)}
    choices = itertools.chain.from_iterable(itertools.combinations(eligible, size) for size in range(min(3, len(eligible)) + 1))
    choice = min(choices, key=lambda rows: (-len(covered(rows)), len(rows), tuple(row["payload_id"] for row in rows)))
    return {"status": "unresolved", "resolved_count": len(choice), "records": list(choice)}


def validate_candidate(candidate: dict[str, Any], root: Path = ROOT, commit: str | None = None, *, allow_unbound: bool = False) -> list[str]:
    errors: list[str] = []
    try:
        if set(candidate) != {"schema_version", "claim_ceiling", "source", "base_candidate", "h2_protocol", "corpus", "evaluator_surface"}: errors.append("AQ5 candidate top-level surface mismatch")
        if candidate.get("schema_version") != "5.0" or candidate.get("claim_ceiling") != "structural-proposal-only": errors.append("AQ5 schema or claim ceiling mismatch")
        if candidate.get("source") != {"commit": SOURCE_COMMIT, "tree": SOURCE_TREE} or git_tree(root, SOURCE_COMMIT) != SOURCE_TREE: errors.append("AQ5 source custody mismatch")
        base, base_raw = load_base(root, commit)
        if candidate.get("base_candidate") != {"path": BASE_MANIFEST_PATH, "sha256": sha256_bytes(base_raw)}: errors.append("AQ5 base candidate digest mismatch")
        h2 = protocol(candidate, root, commit)
        atom_mapping(candidate, root, commit)
        for condition in ("current", "reduced"):
            catalog = h2["conditions"][condition]["atom_catalog"]
            try: validate_atom_catalog(catalog)
            except ValueError as exc: errors.append(f"AQ5 {condition} H2 catalog mismatch: {exc}")
        if canonical_sha256(h2["conditions"]["current"]["atom_catalog"]) == canonical_sha256(h2["conditions"]["reduced"]["atom_catalog"]): errors.append("AQ5 condition atom catalogs are not model-visible distinct")
        corpus = candidate.get("corpus", {})
        required_corpus = {"commit", "tree", "schema_path", "schema_sha256", "authoring_path", "authoring_sha256", "heldout_path", "heldout_sha256", "validator_path", "validator_sha256", "validator_source"}
        if not isinstance(corpus, dict) or set(corpus) != required_corpus: errors.append("AQ5 corpus binding shape mismatch")
        else:
            paths = (corpus["schema_path"], corpus["authoring_path"], corpus["heldout_path"], corpus["validator_path"])
            if paths != (CORPUS_SCHEMA_PATH, CORPUS_AUTHORING_PATH, CORPUS_HELDOUT_PATH, CORPUS_VALIDATOR_PATH): errors.append("AQ5 corpus paths mismatch")
            if corpus["validator_source"] != "candidate_commit": errors.append("AQ5 validator source mismatch")
            if not allow_unbound:
                if corpus["commit"] != "39fd55df96e99e38d51d5fee13faa6b6294f9c43" or corpus["tree"] != "b7b9eb94ffe14a59e924ac2c40926e1a2dc513dd": errors.append("AQ5 frozen corpus authority mismatch")
                elif resolve_commit(root, corpus["commit"]) != corpus["commit"] or git_tree(root, corpus["commit"]) != corpus["tree"]: errors.append("AQ5 corpus commit/tree mismatch")
                else:
                    for path_key, digest_key in (("schema_path", "schema_sha256"), ("authoring_path", "authoring_sha256"), ("heldout_path", "heldout_sha256")):
                        raw = git_show(root, corpus["commit"], corpus[path_key])
                        if corpus[digest_key] != sha256_bytes(raw): errors.append(f"AQ5 corpus digest mismatch for {corpus[path_key]}")
                        if (root / corpus[path_key]).read_bytes() != raw: errors.append(f"AQ5 live corpus bytes mismatch for {corpus[path_key]}")
                    validator_raw = _read(root, corpus["validator_path"], commit)
                    if corpus["validator_sha256"] != sha256_bytes(validator_raw): errors.append("AQ5 candidate validator digest mismatch")
                    if (root / corpus["validator_path"]).read_bytes() != validator_raw: errors.append("AQ5 live candidate validator bytes mismatch")
            try:
                base_for_references = load_base(root, commit)[0]
                corpus_commit = None if allow_unbound else corpus["commit"]
                validate_document_shape(_json_object(_read(root, corpus["authoring_path"], corpus_commit), "AQ5 authoring corpus"), base_for_references)
                validate_document_shape(_json_object(_read(root, corpus["heldout_path"], corpus_commit), "AQ5 heldout corpus"), base_for_references)
            except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
                errors.append(str(exc) or "AQ5 corpus document validation failed")
        surface = candidate.get("evaluator_surface", {})
        files = surface.get("files") if isinstance(surface, dict) else None
        if not isinstance(surface, dict) or set(surface) != {"claim_ceiling", "jsonschema_dialect", "files"} or surface.get("claim_ceiling") != "decision-atom-structural-and-deterministic-telemetry-only" or surface.get("jsonschema_dialect") != "Draft 2020-12" or not isinstance(files, list): errors.append("AQ5 evaluator surface mismatch")
        elif len(files) != len(EVALUATOR_PATHS) or any(not isinstance(row, dict) for row in files) or [row.get("path") for row in files] != list(EVALUATOR_PATHS): errors.append("AQ5 evaluator path set mismatch")
        else:
            for row in files:
                if set(row) != {"path", "sha256"}: errors.append("AQ5 evaluator file binding not closed"); continue
                if allow_unbound and isinstance(row["sha256"], str) and row["sha256"].startswith(UNBOUND): continue
                if not SHA_RE.fullmatch(row["sha256"]): errors.append(f"AQ5 evaluator digest invalid for {row['path']}"); continue
                raw = _read(root, row["path"], commit)
                if sha256_bytes(raw) != row["sha256"]: errors.append(f"AQ5 evaluator digest mismatch for {row['path']}")
                if not allow_unbound and (root / row["path"]).read_bytes() != raw: errors.append(f"AQ5 live evaluator bytes mismatch for {row['path']}")
        if not allow_unbound:
            missing = unresolved(candidate)
            if missing: errors.append("AQ5 unresolved bindings: " + ", ".join(missing))
        for size in range(3):
            for atoms in itertools.combinations(ATOMS, size):
                advisers = map_atoms(candidate, atoms, root, commit)
                for trigger_size in range(len(TRIGGERS) + 1):
                    for triggers in itertools.combinations(TRIGGERS, trigger_size):
                        outcome = resolve_payloads(base, triggers, advisers)
                        if outcome["status"] == "resolved" and len(outcome["records"]) > 3: errors.append("AQ5 payload cap escaped")
    except (KeyError, StopIteration, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        errors.append(str(exc) or "AQ5 candidate validation failed")
    return sorted(set(errors))


def validate_committed(root: Path = ROOT, commit: str = "HEAD") -> list[str]:
    try:
        exact = resolve_commit(root, commit); candidate = load_candidate(root, exact)
    except (ValueError, OSError, json.JSONDecodeError) as exc: return [f"AQ5 candidate unavailable: {exc}"]
    return validate_candidate(candidate, root, exact)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--commit", default="HEAD"); parser.add_argument("--working-tree", action="store_true"); parser.add_argument("--allow-unbound-draft", action="store_true"); args = parser.parse_args(argv)
    try:
        if args.working_tree and not args.allow_unbound_draft:
            errors = ["AQ5 working-tree validation is draft-only; pass --allow-unbound-draft"]
        elif args.working_tree:
            errors = validate_candidate(load_candidate(ROOT), ROOT, allow_unbound=True)
        elif args.allow_unbound_draft:
            errors = ["AQ5 --allow-unbound-draft requires --working-tree"]
        else:
            errors = validate_committed(ROOT, args.commit)
    except (ValueError, OSError, json.JSONDecodeError) as exc: errors = [str(exc)]
    if errors:
        for error in errors: print(f"HOLD: {error}", file=sys.stderr)
        return 1
    prefix = "DRAFT PASS" if args.working_tree else "PASS"
    print(f"{prefix}: AQ5 H2 structural custody; no runtime, provider, product, promotion, adoption, efficacy, or completion claim.")
    return 0


if __name__ == "__main__": raise SystemExit(main())
