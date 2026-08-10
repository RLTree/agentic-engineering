#!/usr/bin/env python3
"""Read-only custody checker for the AQ reduced-four candidate.

Default mode reads the manifest and every overlay byte from a Git commit.  The
working tree is an explicit draft-only mode, never evidence of a committed
candidate.
"""
from __future__ import annotations

import argparse
import itertools
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:  # Deliberately fail closed in validation below.
    jsonschema = None

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = "evals/foundation-v4/reduced-four-skills"
MANIFEST_PATH = f"{OVERLAY}/candidate.json"
SOURCE_COMMIT = "407a2ac124856f0ce1fa33af8a61d0607e413820"
SOURCE_TREE = "8314ca6ad82fa4687720692d8c5762c7aabf6261"
ADVISERS = (
    ("agentic-engineering", "agentic-engineering-lifecycle", "Agentic Engineering", "plugins/agentic-engineering-lifecycle/skills/agentic-engineering/SKILL.md", "agentic-engineering-lifecycle--agentic-engineering"),
    ("codex-task-contract", "agentic-engineering", "Codex Task Contract", "plugins/agentic-engineering/skills/codex-task-contract/SKILL.md", "agentic-engineering--codex-task-contract"),
    ("verification-strategy-engineering", "agentic-engineering", "Verification Strategy Engineering", "plugins/agentic-engineering/skills/verification-strategy-engineering/SKILL.md", "agentic-engineering--verification-strategy-engineering"),
    ("engineering-learning-loop", "agentic-engineering", "Engineering Learning Loop", "plugins/agentic-engineering/skills/engineering-learning-loop/SKILL.md", "agentic-engineering--engineering-learning-loop"),
)
ADVISER_IDS = tuple(item[0] for item in ADVISERS)
TRIGGER_ORDER = ("architecture-boundary", "decision-contract", "verification-evidence", "learning-adoption", "decomposition-boundary", "no-change-abstention", "reference-isolation")
TRIGGERS = frozenset(TRIGGER_ORDER)
CORPUS_COMMIT = "25de0cb1fe86a802768de9bf64659206d69650d0"
CORPUS_TREE = "e5faff4b1a5ba678a7df1727b5bda3b3d0afe00a"
CORPUS_PATHS = {"schema": "evals/foundation-v4/future-activation-v2/activation-schema.json", "authoring": "evals/foundation-v4/future-activation-v2/activation-authoring.json", "heldout": "evals/foundation-v4/future-activation-v2/activation-heldout.json"}
EVALUATOR_PATHS = (
    "evals/foundation-v4/activation-evaluator-schema.json",
    "evals/foundation-v4/selector-output-schema.json",
    "scripts/check_reduced_four_skill_candidate.py",
    "scripts/score_activation.py",
    "scripts/run_activation_trials.py",
    "scripts/validate_future_activation_corpus.py",
)
FUTURE_CORPUS_VALIDATOR_SHA256 = "bc59b649ef4c25ca253dee1bbd483d7eb9de5b1a9827f0094c7cb219504333ee"
CATEGORY_COUNTS = {"decomposition": 6, "task-contract": 6, "verification": 6, "learning": 6, "native-sufficient": 4, "near-neighbor": 4, "explicit-invocation": 4}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CONTEXT_ID_RE = re.compile(r"^aq-reduced-four-[a-z0-9]+(?:-[a-z0-9]+)*$")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git(root: Path, args: list[str], text: bool = False) -> bytes | str:
    result = subprocess.run(["git", *args], cwd=root, check=False, capture_output=True, text=text)
    if result.returncode:
        stderr = result.stderr if text else result.stderr.decode(errors="replace")
        raise ValueError(stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def resolve_commit(root: Path, commit: str) -> str:
    return str(git(root, ["rev-parse", "--verify", f"{commit}^{{commit}}"], text=True)).strip()


def git_tree(root: Path, commit: str) -> str:
    return str(git(root, ["rev-parse", "--verify", f"{commit}^{{tree}}"], text=True)).strip()


def git_show(root: Path, commit: str, path: str) -> bytes:
    return bytes(git(root, ["show", f"{commit}:{path}"]))


def load_candidate_from_commit(root: Path, commit: str) -> dict[str, Any]:
    """Load the immutable candidate manifest from *commit*, never live bytes."""
    resolved = resolve_commit(root, commit)
    try:
        value = json.loads(git_show(root, resolved, MANIFEST_PATH))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"committed candidate unavailable at {resolved}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("committed candidate is not a JSON object")
    return value


def _closed(value: Any, expected: set[str], label: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    if set(value) != expected:
        errors.append(f"{label} must have exactly {sorted(expected)}; got {sorted(value)}")
        return False
    return True


def _digest(value: Any, label: str, errors: list[str]) -> bool:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        errors.append(f"{label} must be a lowercase SHA-256")
        return False
    return True


def _read_overlay(root: Path, path: str, commit: str | None) -> bytes:
    return git_show(root, commit, path) if commit else (root / path).read_bytes()


def _overlay_inventory(root: Path, candidate: dict[str, Any], commit: str | None) -> set[str]:
    if commit:
        return set(str(git(root, ["ls-tree", "-r", "--name-only", commit, "--", OVERLAY], text=True)).splitlines())
    base = root / OVERLAY
    return {item.relative_to(root).as_posix() for item in base.rglob("*") if item.is_file()}


def _parse_frontmatter(raw: bytes) -> dict[str, str]:
    text = raw.decode("utf-8", errors="strict")
    match = re.match(r"\A---\nname: ([^\n]+)\ndescription: \"([^\n]+)\"\n---\n", text)
    if not match:
        raise ValueError("frontmatter must contain exactly name and quoted description first")
    return {"name": match.group(1), "description": match.group(2)}


def _parse_yaml(raw: bytes) -> dict[str, str | bool]:
    text = raw.decode("utf-8", errors="strict")
    match = re.fullmatch(
        r'interface:\n  display_name: "([^\n]+)"\n  short_description: "([^\n]+)"\n  brand_color: "(#(?:[0-9A-F]{6}))"\n  default_prompt: "([^\n]+)"\npolicy:\n  allow_implicit_invocation: (true|false)\n',
        text,
    )
    if not match:
        raise ValueError("openai.yaml must use the constrained interface/policy shape")
    return {"display_name": match.group(1), "short_description": match.group(2), "brand_color": match.group(3), "default_prompt": match.group(4), "allow_implicit_invocation": match.group(5) == "true"}


def _negative(line: str) -> bool:
    return bool(re.search(r"\b(?:do not|does not|no |never|without|only as|proposal-only)\b", line, re.I))


def forbidden_content(skill_text: str) -> list[str]:
    problems: list[str] = []
    for line in skill_text.splitlines():
        if _negative(line):
            continue
        if re.search(r"\bversion\s*3\b", line, re.I): problems.append("Version 3 content")
        if re.search(r"\bshared references?\b", line, re.I): problems.append("shared-reference content")
        if re.search(r"\bgeneric(?:\s|-)?(?:reference\s+)?catalog\b", line, re.I): problems.append("generic-catalog content")
        if re.search(r"\bcanonical repository reference library\b|\b(?:templates|schemas)/|\bcanonical\b.*\b(?:template|schema)\b", line, re.I): problems.append("nonlocal template/schema content")
        if re.search(r"\b(?:takes?|grants?|assigns?|authorizes?|claims?)\s+(?:an?\s+)?(?:effect|effects|authority|claim authority|completion authority|policy|completion|efficacy|claim)\b|\b(?:adoption|completion|efficacy)\s+(?:is|has been|will be)\s+(?:authorized|approved|confirmed|established|complete|effective)\b", line, re.I): problems.append("effect/adoption/completion/efficacy/claim authority")
    return sorted(set(problems))


def fixture_reference_paths(skill_text: str) -> set[str]:
    return set(re.findall(r"`(plugins/[^`]+/references/[^`]+\.md)`", skill_text))


def router_has_explicit_deferrals(skill_text: str) -> bool:
    return "Defer with no architecture output when a single task-contract, verification, or learning specialist owns the decision." in skill_text


def payload_catalog(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the canonical parent-owned payload catalog; it contains no contents."""
    records: list[dict[str, Any]] = []
    for skill in candidate.get("skills", []):
        if not isinstance(skill, dict):
            continue
        for ref in skill.get("references", []):
            if isinstance(ref, dict):
                records.append({"payload_id": ref.get("payload_id"), "owner_adviser_id": skill.get("id"), "source_path": ref.get("path"), "sha256": ref.get("sha256"), "trigger_ids": ref.get("trigger_ids"), "content_class": ref.get("content_class"), "full_schema_or_template": ref.get("full_schema_or_template")})
    return sorted(records, key=lambda record: str(record["payload_id"]))


def resolve_parent_payload_resolution(candidate: dict[str, Any], required_triggers: set[str] | list[str], selected_adviser_ids: list[str]) -> dict[str, Any]:
    """Choose the deterministic minimum trigger cover without exceeding three.

    A true minimum cover above three is represented compactly as a capacity
    breach; unavailable triggers instead produce the deterministic best partial
    subset so reference correctness, not parsing/custody, can fail.
    """
    required = set(required_triggers)
    eligible = [record for record in payload_catalog(candidate) if record["owner_adviser_id"] in selected_adviser_ids and required.intersection(record["trigger_ids"] or [])]
    eligible.sort(key=lambda record: str(record["payload_id"]))
    def covered(records: tuple[dict[str, Any], ...]) -> set[str]:
        return set().union(*(set(record["trigger_ids"] or []) for record in records)) & required if records else set()
    for size in range(len(eligible) + 1):
        choices = [choice for choice in itertools.combinations(eligible, size) if covered(choice) == required]
        if choices:
            choice = min(choices, key=lambda records: tuple(str(record["payload_id"]) for record in records))
            if size > 3:
                return {"status": "cap_exceeded", "resolved_count": size, "records": []}
            return {"status": "resolved", "resolved_count": size, "records": list(choice)}
    choices = list(itertools.chain.from_iterable(itertools.combinations(eligible, size) for size in range(min(3, len(eligible)) + 1)))
    best = min(choices, key=lambda records: (-len(covered(records)), len(records), tuple(str(record["payload_id"]) for record in records)))
    return {"status": "resolved", "resolved_count": len(best), "records": list(best)}


def resolve_parent_payloads(candidate: dict[str, Any], required_triggers: set[str] | list[str], selected_adviser_ids: list[str]) -> list[dict[str, Any]]:
    """Compatibility projection: never returns more than three payload records."""
    return resolve_parent_payload_resolution(candidate, required_triggers, selected_adviser_ids)["records"]


def _skill_for(candidate: dict[str, Any], adviser_id: str) -> dict[str, Any]:
    return next(skill for skill in candidate["skills"] if skill["id"] == adviser_id)


def selector_catalog(candidate: dict[str, Any], condition: str, root: Path = ROOT, overlay_commit: str | None = None) -> list[dict[str, str]]:
    records = []
    for adviser_id, _, _, source_path, _ in ADVISERS:
        skill = _skill_for(candidate, adviser_id)
        raw = git_show(root, SOURCE_COMMIT, source_path) if condition == "current" else _read_overlay(root, skill["reduced"]["skill_path"], overlay_commit)
        records.append({"adviser_id": adviser_id, "description": _parse_frontmatter(raw)["description"]})
    return records


def condition_input_descriptor(candidate: dict[str, Any], condition: str, root: Path = ROOT, overlay_commit: str | None = None) -> dict[str, Any]:
    condition_data = candidate["conditions"][condition]
    entries = []
    for adviser_id in ADVISER_IDS:
        skill = _skill_for(candidate, adviser_id)
        entry = skill[condition]
        entries.append({"adviser_id": adviser_id, "corpus_alias": skill["corpus_alias"], "skill_sha256": entry["skill_sha256"], "yaml_sha256": entry["yaml_sha256"], "invocation_token": entry["invocation_token"]})
    surface = {key: condition_data[key] for key in ("adviser_ids", "reference_payload_resolution", "reference_payload_catalog", "host_install_claim")}
    return {"surface": surface, "selector_catalog": selector_catalog(candidate, condition, root, overlay_commit), "advisers": entries, "permitted_payload_catalog": payload_catalog(candidate), "parent_resolver": {"policy": "minimum-trigger-cover", "max_payloads": 3}}


def condition_input_digest(candidate: dict[str, Any], condition: str, root: Path = ROOT, overlay_commit: str | None = None) -> str:
    return canonical_sha256(condition_input_descriptor(candidate, condition, root, overlay_commit))


def _validate_yaml_identity(parsed: dict[str, str | bool], adviser_id: str, display_name: str, token: str, reduced: bool, errors: list[str]) -> None:
    if parsed["display_name"] != display_name or not parsed["short_description"] or parsed["brand_color"] != "#0F766E": errors.append(f"{adviser_id} YAML identity/display mismatch")
    prompt = str(parsed["default_prompt"])
    if parsed["allow_implicit_invocation"] is not False or token not in prompt: errors.append(f"{adviser_id} YAML permits implicit activation or has wrong token")
    if reduced and not ("proposal-only" in prompt.lower() and "do not" in prompt.lower() and re.search(r"\bonly\b", prompt, re.I)): errors.append(f"{adviser_id} reduced YAML has an unbounded default prompt")
    if not reduced and prompt != f"Use {token} as an explicit advisory lens through external:harness-ultragoal.": errors.append(f"{adviser_id} current YAML default prompt mismatch")


def _validate_evaluator_schema(schema: dict[str, Any], errors: list[str]) -> None:
    """Mechanically guard the evaluator observation/payload evidence boundary."""
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        errors.append("evaluator schema is not Draft 2020-12")
        return
    defs = schema.get("$defs")
    if not isinstance(defs, dict):
        errors.append("evaluator schema lacks definitions")
        return
    payload, observation, execution = defs.get("payload"), defs.get("observation"), defs.get("execution")
    if not isinstance(payload, dict) or payload.get("additionalProperties") is not False or not {"payload_id", "owner_adviser_id", "source_path", "sha256"}.issubset(payload.get("required", [])):
        errors.append("evaluator schema payload record is not closed owner/path/digest evidence")
    if not isinstance(observation, dict) or not {"selector_packet_sha256", "payload_resolution", "resolved_payloads"}.issubset(observation.get("required", [])):
        errors.append("evaluator schema observation lacks selector packet or resolved payload records")
        return
    index = observation.get("properties", {}).get("presentation_index", {})
    if "presentation_index" not in observation.get("required", []) or index != {"type": "integer", "minimum": 0, "maximum": 79}:
        errors.append("evaluator schema observation lacks exact 0..79 presentation index")
    runner = execution.get("properties", {}).get("runner_path", {}) if isinstance(execution, dict) else {}
    seed = execution.get("properties", {}).get("schedule_seed", {}) if isinstance(execution, dict) else {}
    if not isinstance(execution, dict) or "schedule_seed" not in execution.get("required", []) or runner != {"const": "scripts/run_activation_trials.py"} or seed != {"type": "string", "pattern": ".*\\S.*"}:
        errors.append("evaluator schema lacks exact runner path or nonblank schedule seed")
    resolved = observation.get("properties", {}).get("resolved_payloads", {})
    if resolved.get("type") != "array" or resolved.get("maxItems") != 3 or resolved.get("items") != {"$ref": "#/$defs/payload"}:
        errors.append("evaluator schema resolved_payloads is not a closed max-three payload record array")
    resolution = defs.get("payloadResolution", {})
    expected_resolution = [
        {"properties": {"status": {"const": "resolved"}, "resolved_count": {"maximum": 3}}},
        {"properties": {"status": {"const": "cap_exceeded"}, "resolved_count": {"minimum": 4}}},
    ]
    if not isinstance(resolution, dict) or resolution.get("additionalProperties") is not False or set(resolution.get("required", [])) != {"status", "resolved_count"} or resolution.get("oneOf") != expected_resolution:
        errors.append("evaluator schema payload resolution status/count is not closed")


def _validate_selector_schema(schema: dict[str, Any], errors: list[str]) -> None:
    selected = schema.get("properties", {}).get("selected_advisers", {})
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema" or schema.get("additionalProperties") is not False or selected.get("maxItems") != 2 or selected.get("items", {}).get("enum") != list(ADVISER_IDS):
        errors.append("selector schema logical adviser shape mismatch")


def _validate_frozen_corpus(schema: dict[str, Any], corpus: dict[str, Any], split: str, errors: list[str]) -> None:
    if jsonschema is None:
        errors.append("jsonschema Draft202012Validator is unavailable")
        return
    try:
        validator = jsonschema.Draft202012Validator(schema)
        schema_errors = sorted(validator.iter_errors(corpus), key=lambda error: list(error.absolute_path))
    except Exception as exc:
        errors.append(f"jsonschema Draft202012Validator failure: {exc}")
        return
    if schema_errors:
        errors.append(f"{split} corpus fails Draft202012Validator: {schema_errors[0].message}")


def validate_candidate(candidate: Any, root: Path = ROOT, overlay_commit: str | None = None) -> list[str]:
    """Validate a working draft (``overlay_commit=None``) or immutable commit overlay."""
    errors: list[str] = []
    top = {"schema_version", "claim_ceiling", "source", "corpus", "evaluator_surface", "conditions", "skills"}
    if not _closed(candidate, top, "candidate", errors): return errors
    if candidate["schema_version"] != "2.0" or candidate["claim_ceiling"] != "structural-proposal-only": errors.append("candidate version or structural claim ceiling mismatch")
    source = candidate["source"]
    if _closed(source, {"commit", "tree"}, "source", errors):
        if source["commit"] != SOURCE_COMMIT: errors.append("source commit mismatch")
        if source["tree"] != SOURCE_TREE or git_tree(root, SOURCE_COMMIT) != SOURCE_TREE: errors.append("source tree mismatch")
    try:
        inventory = _overlay_inventory(root, candidate, overlay_commit)
    except ValueError as exc:
        errors.append(f"candidate tree mismatch: {exc}")
        inventory = set()
    expected_inventory = {MANIFEST_PATH}
    for _, _, _, _, fixture_slug in ADVISERS:
        expected_inventory.update({f"{OVERLAY}/skills/{fixture_slug}/SKILL.md", f"{OVERLAY}/skills/{fixture_slug}/agents/openai.yaml"})
    if inventory != expected_inventory: errors.append("candidate overlay inventory mismatch")

    corpus_data: list[dict[str, Any]] = []
    corpus_schema: dict[str, Any] | None = None
    corpus = candidate["corpus"]
    if _closed(corpus, set(CORPUS_PATHS) | {"commit", "tree"}, "corpus", errors):
        if corpus["commit"] != CORPUS_COMMIT or corpus["tree"] != CORPUS_TREE or git_tree(root, CORPUS_COMMIT) != CORPUS_TREE: errors.append("corpus commit/tree mismatch")
        for split, expected_path in CORPUS_PATHS.items():
            item = corpus[split]
            if not _closed(item, {"path", "sha256"}, f"corpus.{split}", errors): continue
            if item["path"] != expected_path: errors.append(f"corpus {split} path mismatch")
            if not _digest(item["sha256"], f"corpus.{split}.sha256", errors): continue
            raw = git_show(root, CORPUS_COMMIT, item["path"])
            if sha256_bytes(raw) != item["sha256"]: errors.append(f"corpus {split} digest mismatch")
            parsed = json.loads(raw)
            if split != "schema": corpus_data.append(parsed)
            else:
                corpus_schema = parsed
                if "referenceTrigger" not in parsed.get("$defs", {}): errors.append("corpus schema shape mismatch")

    evaluator = candidate["evaluator_surface"]
    if _closed(evaluator, {"claim_ceiling", "jsonschema_dialect", "files"}, "evaluator_surface", errors):
        if evaluator["claim_ceiling"] != "logical-catalog-structural-only" or evaluator["jsonschema_dialect"] != "Draft 2020-12": errors.append("evaluator surface claim ceiling or dialect mismatch")
        files = evaluator["files"]
        if not isinstance(files, list) or [entry.get("path") for entry in files if isinstance(entry, dict)] != list(EVALUATOR_PATHS): errors.append("evaluator surface file inventory mismatch")
        else:
            evaluator_json: dict[str, Any] | None = None
            selector_json: dict[str, Any] | None = None
            for entry in files:
                if not _closed(entry, {"path", "sha256"}, "evaluator surface file", errors) or not _digest(entry["sha256"], "evaluator surface sha256", errors): continue
                try:
                    raw = _read_overlay(root, entry["path"], overlay_commit)
                except (OSError, ValueError) as exc:
                    errors.append(f"cannot read evaluator surface {entry['path']}: {exc}")
                    continue
                if sha256_bytes(raw) != entry["sha256"]: errors.append(f"evaluator surface digest mismatch for {entry['path']}")
                if entry["path"] == "scripts/validate_future_activation_corpus.py" and entry["sha256"] != FUTURE_CORPUS_VALIDATOR_SHA256: errors.append("future corpus validator digest mismatch")
                if entry["path"] == EVALUATOR_PATHS[0]: evaluator_json = json.loads(raw)
                if entry["path"] == EVALUATOR_PATHS[1]: selector_json = json.loads(raw)
            if evaluator_json is not None: _validate_evaluator_schema(evaluator_json, errors)
            if selector_json is not None: _validate_selector_schema(selector_json, errors)
    if corpus_schema is not None:
        for corpus_item, split in zip(corpus_data, ("authoring", "heldout")):
            _validate_frozen_corpus(corpus_schema, corpus_item, split, errors)

    conditions = candidate["conditions"]
    static_condition_keys = {"adviser_ids", "reference_payload_resolution", "reference_payload_catalog", "host_install_claim"}
    condition_keys = static_condition_keys | {"selector_catalog_sha256", "condition_input_sha256"}
    if _closed(conditions, {"current", "reduced"}, "conditions", errors):
        static_values = []
        for condition in ("current", "reduced"):
            item = conditions[condition]
            if not _closed(item, condition_keys, f"conditions.{condition}", errors): continue
            static_values.append({key: item[key] for key in static_condition_keys})
            if item["adviser_ids"] != list(ADVISER_IDS) or item["reference_payload_resolution"] != "parent-resolved" or item["reference_payload_catalog"] != "identical" or item["host_install_claim"] is not False: errors.append(f"conditions.{condition} fixed surface mismatch")
            try:
                if item["selector_catalog_sha256"] != canonical_sha256(selector_catalog(candidate, condition, root, overlay_commit)): errors.append(f"conditions.{condition} selector catalog digest mismatch")
                if item["condition_input_sha256"] != condition_input_digest(candidate, condition, root, overlay_commit): errors.append(f"conditions.{condition} input digest mismatch")
            except (ValueError, OSError) as exc: errors.append(f"conditions.{condition} cannot bind selector input: {exc}")
        if len(static_values) == 2 and static_values[0] != static_values[1]: errors.append("current and reduced fixed surfaces differ")
        if len(static_values) == 2 and conditions["current"]["selector_catalog_sha256"] == conditions["reduced"]["selector_catalog_sha256"]: errors.append("current and reduced selector catalog digests must differ")
        if len(static_values) == 2 and conditions["current"]["condition_input_sha256"] == conditions["reduced"]["condition_input_sha256"]: errors.append("current and reduced input digests must differ")

    if not isinstance(candidate["skills"], list) or len(candidate["skills"]) != 4: return errors + ["skills must contain exactly four entries"]
    if [item.get("id") for item in candidate["skills"] if isinstance(item, dict)] != list(ADVISER_IDS): errors.append("skill IDs must be fixed-four deterministic order")
    contexts, payload_ids, available = [], set(), {}
    expected = {item[0]: item[1:] for item in ADVISERS}
    for skill in candidate["skills"]:
        if not _closed(skill, {"id", "corpus_alias", "current", "reduced", "references"}, "skill entry", errors): continue
        adviser_id = skill["id"]
        if adviser_id not in expected: errors.append(f"unknown adviser ID: {adviser_id}"); continue
        namespace, display_name, source_path, slug = expected[adviser_id]
        if skill["corpus_alias"] != adviser_id: errors.append(f"{adviser_id} corpus alias mismatch")
        token = f"${namespace}:{adviser_id}"
        current = skill["current"]
        current_keys = {"plugin_namespace", "skill_path", "skill_sha256", "yaml_path", "yaml_sha256", "invocation_token"}
        if _closed(current, current_keys, f"{adviser_id}.current", errors):
            expected_yaml = source_path.removesuffix("SKILL.md") + "agents/openai.yaml"
            if current["plugin_namespace"] != namespace or current["skill_path"] != source_path or current["yaml_path"] != expected_yaml or current["invocation_token"] != token: errors.append(f"{adviser_id} current identity/path/token mismatch")
            for path_key, digest_key in (("skill_path", "skill_sha256"), ("yaml_path", "yaml_sha256")):
                if _digest(current[digest_key], f"{adviser_id}.current.{digest_key}", errors) and sha256_bytes(git_show(root, SOURCE_COMMIT, current[path_key])) != current[digest_key]: errors.append(f"{adviser_id} current {path_key} digest mismatch")
            try:
                front = _parse_frontmatter(git_show(root, SOURCE_COMMIT, source_path))
                if front["name"] != adviser_id or not front["description"]: errors.append(f"{adviser_id} current frontmatter identity mismatch")
                _validate_yaml_identity(_parse_yaml(git_show(root, SOURCE_COMMIT, expected_yaml)), adviser_id, display_name, token, False, errors)
            except ValueError as exc: errors.append(f"{adviser_id} current metadata parse failure: {exc}")
        reduced = skill["reduced"]
        reduced_keys = {"context_id", "skill_path", "skill_sha256", "yaml_path", "yaml_sha256", "invocation_token"}
        if _closed(reduced, reduced_keys, f"{adviser_id}.reduced", errors):
            contexts.append(reduced["context_id"])
            base = f"{OVERLAY}/skills/{slug}"
            if reduced["skill_path"] != f"{base}/SKILL.md" or reduced["yaml_path"] != f"{base}/agents/openai.yaml" or reduced["invocation_token"] != token: errors.append(f"{adviser_id} reduced identity/path/token mismatch")
            raw_skill = _read_overlay(root, reduced["skill_path"], overlay_commit)
            raw_yaml = _read_overlay(root, reduced["yaml_path"], overlay_commit)
            if sha256_bytes(raw_skill) != reduced["skill_sha256"]: errors.append(f"{adviser_id} reduced SKILL digest mismatch")
            if sha256_bytes(raw_yaml) != reduced["yaml_sha256"]: errors.append(f"{adviser_id} reduced YAML digest mismatch")
            try:
                front = _parse_frontmatter(raw_skill)
                if front["name"] != adviser_id or not front["description"]: errors.append(f"{adviser_id} reduced frontmatter identity mismatch")
                _validate_yaml_identity(_parse_yaml(raw_yaml), adviser_id, display_name, token, True, errors)
            except ValueError as exc: errors.append(f"{adviser_id} reduced metadata parse failure: {exc}")
            text = raw_skill.decode("utf-8", errors="replace")
            for problem in forbidden_content(text): errors.append(f"{adviser_id} reduced SKILL contains {problem}")
            if adviser_id == "agentic-engineering" and not router_has_explicit_deferrals(text): errors.append("broad router lacks explicit task-contract, verification, and learning deferral")
        refs = skill["references"]
        if not isinstance(refs, list) or len(refs) > 3: errors.append(f"{adviser_id} must have zero to three references"); continue
        paths, triggers = [], set()
        for ref in refs:
            if not _closed(ref, {"payload_id", "path", "sha256", "trigger_ids", "content_class", "full_schema_or_template"}, f"{adviser_id}.reference", errors): continue
            pid = ref["payload_id"]
            if not isinstance(pid, str) or not pid or pid in payload_ids: errors.append("payload IDs must be globally unique and nonblank")
            payload_ids.add(pid); paths.append(ref["path"])
            if ref["content_class"] != "compact-reference" or ref["full_schema_or_template"] is not False: errors.append(f"{adviser_id} reference is not a compact non-schema/template payload")
            ids = ref["trigger_ids"]
            if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)) or not set(ids).issubset(TRIGGERS): errors.append(f"{adviser_id} reference has missing, unknown, or duplicate trigger IDs")
            else: triggers.update(ids)
            if _digest(ref["sha256"], f"{adviser_id}.reference.sha256", errors) and sha256_bytes(git_show(root, SOURCE_COMMIT, ref["path"])) != ref["sha256"]: errors.append(f"{adviser_id} frozen reference digest mismatch")
        if len(paths) != len(set(paths)): errors.append(f"{adviser_id} has duplicate reference paths")
        available[adviser_id] = triggers
        try:
            fixture_text = _read_overlay(root, skill["reduced"]["skill_path"], overlay_commit).decode("utf-8")
            if set(paths) != fixture_reference_paths(fixture_text): errors.append(f"{adviser_id} references do not exactly match reduced fixture")
        except (OSError, ValueError): pass
    if len(contexts) != len(set(contexts)) or any(not isinstance(value, str) or not CONTEXT_ID_RE.fullmatch(value) for value in contexts): errors.append("fixture context IDs must be unique nonblank static aq-reduced-four IDs")
    # Mechanical capacity proof over the entire schema-permitted selection and
    # trigger surface; it does not depend on a model result or prompt content.
    for size in range(3):
        for advisers in itertools.combinations(ADVISER_IDS, size):
            for trigger_size in range(4):
                for needed in itertools.combinations(TRIGGER_ORDER, trigger_size):
                    outcome = resolve_parent_payload_resolution(candidate, set(needed), list(advisers))
                    if outcome["status"] == "cap_exceeded" or len(outcome["records"]) > 3:
                        errors.append("schema-permitted resolver capacity exceeds three")
                        break
    for corpus_item, split in zip(corpus_data, ("authoring", "heldout")):
        if corpus_item.get("schema_version") != "2.0" or corpus_item.get("corpus_id") != f"foundation-v4-future-activation-v2-{split}" or corpus_item.get("split") != split or corpus_item.get("candidate_independent") is not True or corpus_item.get("routing_surface") != "fixed-four-adviser" or corpus_item.get("reference_catalog") != list(TRIGGER_ORDER): errors.append(f"{split} corpus schema-shape mismatch")
        cases = corpus_item.get("cases")
        if not isinstance(cases, list) or len(cases) != 36: errors.append(f"{split} corpus case-count mismatch"); continue
        counts = {category: 0 for category in CATEGORY_COUNTS}
        for case in cases:
            labels = case.get("hidden_labels", {})
            advisers = labels.get("expected_advisers", []) if isinstance(labels, dict) else []
            needed = set(labels.get("reference_triggers", [])) if isinstance(labels, dict) else set()
            if not isinstance(case, dict) or not set(advisers).issubset(ADVISER_IDS) or not needed.issubset(TRIGGERS): errors.append(f"{split} corpus case schema-shape mismatch"); continue
            counts[case.get("category")] = counts.get(case.get("category"), 0) + 1
            resolved = resolve_parent_payloads(candidate, needed, advisers)
            if not needed.issubset(set().union(*(available.get(adviser, set()) for adviser in advisers)) if advisers else set()): errors.append(f"corpus trigger coverage gap for {case.get('id')}")
            if any(record["owner_adviser_id"] not in advisers or record["content_class"] != "compact-reference" or record["full_schema_or_template"] is not False for record in resolved): errors.append(f"corpus resolver custody mismatch for {case.get('id')}")
        if counts != CATEGORY_COUNTS: errors.append(f"{split} corpus distribution mismatch")
    return errors


def validate_committed_candidate(root: Path, commit: str = "HEAD") -> list[str]:
    try:
        resolved = resolve_commit(root, commit)
        candidate = load_candidate_from_commit(root, resolved)
    except ValueError as exc:
        return [f"candidate tree mismatch: {exc}"]
    return validate_candidate(candidate, root, overlay_commit=resolved)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", default="HEAD", help="immutable commit to validate (default: HEAD)")
    parser.add_argument("--working-tree", action="store_true", help="validate mutable draft bytes only")
    args = parser.parse_args(argv)
    if args.working_tree:
        try: candidate = json.loads((ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"HOLD: cannot load working-tree draft: {exc}", file=sys.stderr); return 1
        errors = validate_candidate(candidate, ROOT)
        label = "DRAFT structural custody"
    else:
        errors = validate_committed_candidate(ROOT, args.commit)
        label = "COMMITTED structural custody"
    if errors:
        for error in errors: print(f"HOLD: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {label}; no behavioral, host-install, adoption, efficacy, or completion claim is established.")
    return 0


if __name__ == "__main__": raise SystemExit(main())
