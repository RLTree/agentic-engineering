#!/usr/bin/env python3
"""Fail-closed AQ4 H2 decision-atom candidate custody checker.

The model-facing protocol selects closed decision atoms.  This evaluator-owned
module alone maps atoms to logical advisers and resolves compact references.
Unbound AQ4 corpus or evaluator digests make committed/live validation fail.
"""
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
MANIFEST_PATH = "evals/foundation-v4/decision-atom-candidate-v4.json"
BASE_MANIFEST_PATH = "evals/foundation-v4/reduced-four-skills/candidate.json"
CORPUS_SCHEMA_PATH = "evals/foundation-v4/future-activation-v4/activation-schema.json"
CORPUS_AUTHORING_PATH = "evals/foundation-v4/future-activation-v4/activation-authoring.json"
CORPUS_HELDOUT_PATH = "evals/foundation-v4/future-activation-v4/activation-heldout.json"
CORPUS_VALIDATOR_PATH = "scripts/validate_future_activation_corpus_v4.py"
SOURCE_COMMIT = "407a2ac124856f0ce1fa33af8a61d0607e413820"
SOURCE_TREE = "8314ca6ad82fa4687720692d8c5762c7aabf6261"
ATOMS = (
    "topology-control-boundary",
    "task-contract",
    "verification-strategy",
    "engineering-learning",
)
ADVISERS = (
    "agentic-engineering",
    "codex-task-contract",
    "verification-strategy-engineering",
    "engineering-learning-loop",
)
ATOM_TO_ADVISER = dict(zip(ATOMS, ADVISERS, strict=True))
EXPLICIT_TOKENS = {atom: f"${adviser}" for atom, adviser in ATOM_TO_ADVISER.items()}
PAIRWISE_OTHERS = {atom: tuple(other for other in ATOMS if other != atom) for atom in ATOMS}
TRIGGERS = (
    "architecture-boundary", "decision-contract", "verification-evidence",
    "learning-adoption", "decomposition-boundary", "no-change-abstention",
    "reference-isolation",
)
EVALUATOR_PATHS = (
    "evals/foundation-v4/activation-evaluator-schema-v4.json",
    "evals/foundation-v4/decision-atom-selector-output-schema.json",
    "scripts/check_reduced_four_skill_candidate_v4.py",
    "scripts/score_activation_v4.py",
    "scripts/run_activation_trials_v4.py",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
UNBOUND_PREFIX = "UNBOUND_AQ4_"


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())


def git(root: Path, args: list[str], *, text: bool = False) -> bytes | str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=text)
    if result.returncode:
        detail = result.stderr if text else result.stderr.decode(errors="replace")
        raise ValueError(detail.strip() or "git input unavailable")
    return result.stdout


def resolve_commit(root: Path, commit: str) -> str:
    return str(git(root, ["rev-parse", "--verify", f"{commit}^{{commit}}"], text=True)).strip()


def git_tree(root: Path, commit: str) -> str:
    return str(git(root, ["rev-parse", "--verify", f"{commit}^{{tree}}"], text=True)).strip()


def git_show(root: Path, commit: str, path: str) -> bytes:
    return bytes(git(root, ["show", f"{commit}:{path}"]))


def _read(root: Path, path: str, commit: str | None) -> bytes:
    return git_show(root, commit, path) if commit else (root / path).read_bytes()


def load_candidate(root: Path = ROOT, commit: str | None = None) -> dict[str, Any]:
    value = json.loads(_read(root, MANIFEST_PATH, commit))
    if not isinstance(value, dict):
        raise ValueError("AQ4 candidate is not an object")
    return value


def load_base_candidate(root: Path = ROOT, commit: str | None = None) -> tuple[dict[str, Any], bytes]:
    raw = _read(root, BASE_MANIFEST_PATH, commit)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("base candidate is not an object")
    return value, raw


def is_unbound(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(UNBOUND_PREFIX)


def unresolved_bindings(candidate: dict[str, Any]) -> list[str]:
    found: list[str] = []
    def walk(value: Any, path: str) -> None:
        if is_unbound(value):
            found.append(path)
        elif isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{path}.{key}" if path else key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")
    walk(candidate, "")
    return sorted(found)


def require_bound(candidate: dict[str, Any]) -> None:
    missing = unresolved_bindings(candidate)
    if missing:
        raise ValueError("AQ4 live execution is unbound: " + ", ".join(missing))


def atom_mapping(candidate: dict[str, Any]) -> dict[str, str]:
    rows = candidate.get("atom_to_adviser")
    if not isinstance(rows, list):
        raise ValueError("atom mapping unavailable")
    mapping: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"atom_id", "adviser_id", "explicit_token"}:
            raise ValueError("atom mapping row is not closed")
        atom, adviser = row["atom_id"], row["adviser_id"]
        if atom in mapping:
            raise ValueError("atom mapping duplicates an atom")
        if row["explicit_token"] != EXPLICIT_TOKENS.get(atom):
            raise ValueError("atom mapping explicit token mismatch")
        mapping[atom] = adviser
    if tuple(mapping) != ATOMS or tuple(mapping.values()) != ADVISERS or len(set(mapping.values())) != len(ADVISERS):
        raise ValueError("atom mapping is not total, ordered, and injective")
    return mapping


def map_atoms_to_advisers(candidate: dict[str, Any], atoms: Iterable[str]) -> list[str]:
    chosen = list(atoms)
    if len(chosen) > 2 or len(chosen) != len(set(chosen)) or any(atom not in ATOMS for atom in chosen):
        raise ValueError("selected atoms are outside the closed 0-2 contract")
    mapping = atom_mapping(candidate)
    return [mapping[atom] for atom in chosen]


def parse_explicit_atom_constraint(task: str, candidate: dict[str, Any]) -> dict[str, str | None]:
    """Parse only exact canonical `$<adviser>` tokens; bare names never invoke."""
    if not isinstance(task, str):
        raise ValueError("task must be text")
    atom_mapping(candidate)
    found: list[str] = []
    for atom, token in EXPLICIT_TOKENS.items():
        pattern = rf"(?<![A-Za-z0-9_:$-]){re.escape(token)}(?![A-Za-z0-9_:-])"
        if re.search(pattern, task):
            found.append(atom)
    if len(found) == 1:
        return {"status": "exact", "atom_id": found[0]}
    if len(found) > 1:
        return {"status": "ambiguous", "atom_id": None}
    return {"status": "none", "atom_id": None}


def enforce_explicit_constraint(selected: list[str], constraint: dict[str, Any]) -> list[str]:
    if constraint == {"status": "none", "atom_id": None}:
        return selected
    if constraint.get("status") == "exact" and selected == [constraint.get("atom_id")]:
        return selected
    if constraint == {"status": "ambiguous", "atom_id": None} and selected == []:
        return selected
    raise ValueError("selected atoms violate the deterministic explicit constraint")


def _base_skill(base: dict[str, Any], adviser: str) -> dict[str, Any]:
    try:
        return next(row for row in base["skills"] if row["id"] == adviser)
    except (KeyError, StopIteration, TypeError) as exc:
        raise ValueError("base adviser metadata unavailable") from exc


def payload_catalog(base: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for adviser in ADVISERS:
        skill = _base_skill(base, adviser)
        for ref in skill.get("references", []):
            rows.append({
                "payload_id": ref["payload_id"], "owner_adviser_id": adviser,
                "source_path": ref["path"], "sha256": ref["sha256"],
                "trigger_ids": list(ref["trigger_ids"]),
                "content_class": ref["content_class"],
                "full_schema_or_template": ref["full_schema_or_template"],
            })
    return sorted(rows, key=lambda row: row["payload_id"])


def resolve_parent_payload_resolution(base: dict[str, Any], triggers: Iterable[str], mapped_advisers: list[str]) -> dict[str, Any]:
    """Accept mapped adviser IDs only, proving references cannot consume atoms."""
    required = set(triggers)
    if not required.issubset(TRIGGERS):
        raise ValueError("unknown reference trigger")
    if len(mapped_advisers) > 2 or len(mapped_advisers) != len(set(mapped_advisers)) or any(item not in ADVISERS for item in mapped_advisers):
        raise ValueError("reference resolver requires mapped adviser IDs")
    eligible = [row for row in payload_catalog(base) if row["owner_adviser_id"] in mapped_advisers and required.intersection(row["trigger_ids"])]
    def covered(rows: tuple[dict[str, Any], ...]) -> set[str]:
        return (set().union(*(set(row["trigger_ids"]) for row in rows)) if rows else set()) & required
    for size in range(len(eligible) + 1):
        choices = [rows for rows in itertools.combinations(eligible, size) if covered(rows) == required]
        if choices:
            selected = min(choices, key=lambda rows: tuple(row["payload_id"] for row in rows))
            if size > 3:
                return {"status": "cap_exceeded", "resolved_count": size, "records": []}
            return {"status": "resolved", "resolved_count": size, "records": list(selected)}
    choices = itertools.chain.from_iterable(itertools.combinations(eligible, size) for size in range(min(3, len(eligible)) + 1))
    selected = min(choices, key=lambda rows: (-len(covered(rows)), len(rows), tuple(row["payload_id"] for row in rows)))
    return {"status": "resolved", "resolved_count": len(selected), "records": list(selected)}


def resolve_atoms_then_payloads(candidate: dict[str, Any], base: dict[str, Any], triggers: Iterable[str], atoms: list[str]) -> dict[str, Any]:
    return resolve_parent_payload_resolution(base, triggers, map_atoms_to_advisers(candidate, atoms))


def _frontmatter_description(raw: bytes) -> str:
    match = re.match(rb'\A---\nname: [^\n]+\ndescription: "([^\n]+)"\n---\n', raw)
    if not match:
        raise ValueError("skill frontmatter unavailable")
    return match.group(1).decode("utf-8")


def expected_catalog(candidate: dict[str, Any], base: dict[str, Any], condition: str, root: Path, commit: str | None) -> list[dict[str, Any]]:
    declared: dict[str, str] = {}
    for atom, adviser in ATOM_TO_ADVISER.items():
        skill = _base_skill(base, adviser)
        entry = skill[condition]
        raw = git_show(root, SOURCE_COMMIT, entry["skill_path"]) if condition == "current" else _read(root, entry["skill_path"], commit)
        declared[atom] = _frontmatter_description(raw)
    actual = candidate["conditions"][condition]["atom_catalog"]
    # Keep parent-authored discriminative boundaries fixed across conditions.
    return [{**row, "declared_scope": declared[row["atom_id"]]} for row in actual]


def condition_descriptor(candidate: dict[str, Any], base: dict[str, Any], condition: str) -> dict[str, Any]:
    return {
        "condition": condition,
        "mapping": candidate["atom_to_adviser"],
        "atom_catalog": candidate["conditions"][condition]["atom_catalog"],
        "base_condition": base["conditions"][condition],
        "parent_reference_policy": {"mapping_precedes_resolution": True, "max_compact_references": 3},
    }


def validate_candidate(candidate: dict[str, Any], root: Path = ROOT, commit: str | None = None, *, allow_unbound: bool = False) -> list[str]:
    errors: list[str] = []
    try:
        expected_top_level = {"schema_version", "claim_ceiling", "source", "base_candidate", "corpus", "evaluator_surface", "atom_to_adviser", "conditions"}
        if set(candidate) != expected_top_level:
            errors.append("candidate top-level surface is not exact and closed")
        if candidate.get("schema_version") != "4.0" or candidate.get("claim_ceiling") != "structural-proposal-only":
            errors.append("candidate schema or claim ceiling mismatch")
        if candidate.get("source") != {"commit": SOURCE_COMMIT, "tree": SOURCE_TREE}:
            errors.append("source custody mismatch")
        if git_tree(root, SOURCE_COMMIT) != SOURCE_TREE:
            errors.append("source tree unavailable")
        base, base_raw = load_base_candidate(root, commit)
        binding = candidate.get("base_candidate", {})
        if binding != {"path": BASE_MANIFEST_PATH, "sha256": sha256_bytes(base_raw)}:
            errors.append("base candidate digest mismatch")
        mapping = atom_mapping(candidate)
        if mapping != ATOM_TO_ADVISER:
            errors.append("atom mapping mismatch")
        conditions = candidate.get("conditions")
        if not isinstance(conditions, dict) or tuple(conditions) != ("current", "reduced"):
            errors.append("condition order or identity mismatch")
        else:
            catalogs = []
            for name in ("current", "reduced"):
                data = conditions[name]
                if set(data) != {"condition_input_sha256", "atom_catalog_sha256", "atom_catalog"}:
                    errors.append(f"{name} condition is not closed")
                    continue
                catalog = data["atom_catalog"]
                if not isinstance(catalog, list) or [row.get("atom_id") for row in catalog if isinstance(row, dict)] != list(ATOMS):
                    errors.append(f"{name} atom catalog order mismatch")
                    continue
                for row in catalog:
                    if set(row) != {"atom_id", "declared_scope", "positive_boundary", "admission_rule", "pairwise_exclusions"}:
                        errors.append(f"{name} atom catalog row is not closed")
                        continue
                    exclusions = row["pairwise_exclusions"]
                    if [item.get("atom_id") for item in exclusions if isinstance(item, dict)] != list(PAIRWISE_OTHERS[row["atom_id"]]) or any(set(item) != {"atom_id", "boundary"} or not item["boundary"] for item in exclusions):
                        errors.append(f"{name} complete pairwise exclusions mismatch for {row['atom_id']}")
                    if not row["positive_boundary"] or not row["declared_scope"] or row["admission_rule"] != "Admit only for a direct instance of this controlling decision; topical relevance, downstream usefulness, and possible future need are insufficient.":
                        errors.append(f"{name} atom boundary is blank")
                if catalog != expected_catalog(candidate, base, name, root, commit):
                    errors.append(f"{name} declared scope does not match candidate condition")
                catalog_digest = canonical_sha256(catalog)
                input_digest = canonical_sha256(condition_descriptor(candidate, base, name))
                if not allow_unbound or not is_unbound(data["atom_catalog_sha256"]):
                    if data["atom_catalog_sha256"] != catalog_digest:
                        errors.append(f"{name} atom catalog digest mismatch")
                if not allow_unbound or not is_unbound(data["condition_input_sha256"]):
                    if data["condition_input_sha256"] != input_digest:
                        errors.append(f"{name} condition input digest mismatch")
                catalogs.append(catalog)
            if len(catalogs) == 2:
                if canonical_sha256(catalogs[0]) == canonical_sha256(catalogs[1]):
                    errors.append("current and reduced model-visible catalogs are not distinct")
                for index in range(len(ATOMS)):
                    left, right = catalogs[0][index], catalogs[1][index]
                    if left["positive_boundary"] != right["positive_boundary"] or left["admission_rule"] != right["admission_rule"] or left["pairwise_exclusions"] != right["pairwise_exclusions"]:
                        errors.append("condition catalogs changed fixed boundaries")
        surface = candidate.get("evaluator_surface", {})
        files = surface.get("files") if isinstance(surface, dict) else None
        if not isinstance(surface, dict) or set(surface) != {"claim_ceiling", "jsonschema_dialect", "files"} or surface.get("claim_ceiling") != "decision-atom-structural-and-deterministic-telemetry-only" or surface.get("jsonschema_dialect") != "Draft 2020-12" or not isinstance(files, list):
            errors.append("evaluator surface mismatch")
        else:
            paths = [row.get("path") for row in files if isinstance(row, dict)]
            expected_paths = [*EVALUATOR_PATHS, CORPUS_VALIDATOR_PATH]
            if paths != expected_paths or len(paths) != len(set(paths)):
                errors.append("evaluator file path set is not exact, unique, and ordered")
            for row in files:
                if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
                    errors.append("evaluator file binding is not closed")
                    continue
                if allow_unbound and (is_unbound(row["path"]) or is_unbound(row["sha256"])):
                    continue
                if not SHA256_RE.fullmatch(row["sha256"]):
                    errors.append(f"evaluator digest invalid for {row['path']}")
                    continue
                if sha256_bytes(_read(root, row["path"], commit)) != row["sha256"]:
                    errors.append(f"evaluator digest mismatch for {row['path']}")
        corpus = candidate.get("corpus", {})
        required_corpus = {"commit", "tree", "schema_path", "schema_sha256", "authoring_path", "authoring_sha256", "heldout_path", "heldout_sha256", "validator_path", "validator_sha256", "validator_source"}
        if not isinstance(corpus, dict) or set(corpus) != required_corpus:
            errors.append("corpus binding shape mismatch")
        elif {key: corpus[key] for key in ("schema_path", "authoring_path", "heldout_path", "validator_path")} != {"schema_path": CORPUS_SCHEMA_PATH, "authoring_path": CORPUS_AUTHORING_PATH, "heldout_path": CORPUS_HELDOUT_PATH, "validator_path": CORPUS_VALIDATOR_PATH}:
            errors.append("corpus paths are not the canonical code-owned set")
        elif corpus["validator_source"] != "candidate_commit":
            errors.append("validator source must be the exact candidate commit")
        if not allow_unbound:
            missing = unresolved_bindings(candidate)
            if missing:
                errors.append("unresolved AQ4 bindings: " + ", ".join(missing))
            elif not COMMIT_RE.fullmatch(corpus["commit"]) or not COMMIT_RE.fullmatch(corpus["tree"]) or any(not SHA256_RE.fullmatch(corpus[key]) for key in ("schema_sha256", "authoring_sha256", "heldout_sha256", "validator_sha256")):
                errors.append("corpus binding format mismatch")
            elif git_tree(root, corpus["commit"]) != corpus["tree"]:
                errors.append("corpus tree mismatch")
        # Exhaustive mapping and compact-reference cap proof over every legal
        # atom subset and every trigger subset.  No prompt or hidden label is read.
        for size in range(3):
            for atoms in itertools.combinations(ATOMS, size):
                mapped = map_atoms_to_advisers(candidate, atoms)
                if len(mapped) != len(atoms) or len(mapped) != len(set(mapped)):
                    errors.append("mapping subset is not injective")
                for trigger_size in range(len(TRIGGERS) + 1):
                    for triggers in itertools.combinations(TRIGGERS, trigger_size):
                        outcome = resolve_parent_payload_resolution(base, triggers, mapped)
                        if outcome["status"] == "cap_exceeded":
                            if outcome["resolved_count"] <= 3 or outcome["records"]:
                                errors.append(f"reference cap did not close for atoms {atoms}")
                                raise StopIteration
                        elif outcome["resolved_count"] > 3 or len(outcome["records"]) > 3:
                            errors.append(f"reference resolver escaped cap for atoms {atoms}")
                            raise StopIteration
    except StopIteration:
        pass
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        errors.append(str(exc) or "AQ4 candidate validation failed")
    return sorted(set(errors))


def validate_committed_candidate(root: Path = ROOT, commit: str = "HEAD") -> list[str]:
    try:
        resolved = resolve_commit(root, commit)
        candidate = load_candidate(root, resolved)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return [f"candidate unavailable: {exc}"]
    return validate_candidate(candidate, root, resolved, allow_unbound=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--working-tree", action="store_true")
    parser.add_argument("--allow-unbound-draft", action="store_true")
    args = parser.parse_args(argv)
    if args.working_tree:
        try:
            candidate = load_candidate(ROOT)
            errors = validate_candidate(candidate, ROOT, allow_unbound=args.allow_unbound_draft)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            errors = [str(exc)]
        label = "DRAFT"
    else:
        errors = validate_committed_candidate(ROOT, args.commit)
        label = "COMMITTED"
    if errors:
        for error in errors:
            print(f"HOLD: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {label} AQ4 atom protocol structural custody; no runtime, provider, product, adoption, efficacy, or completion claim is established.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
