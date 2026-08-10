#!/usr/bin/env python3
"""Zero-write deterministic AQ4 decision-atom scorer.

Live scoring is impossible while the candidate contains any AQ4 binding
placeholder.  Tests may supply an in-memory synthetic profile; this never
weakens the committed/live path.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

try:
    import aq4_live_witness as _live_witness_dependency
except ImportError:
    _LIVE_WITNESS = None
else:
    _LIVE_WITNESS = getattr(_live_witness_dependency, "WITNESS", None)

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = "scripts/check_reduced_four_skill_candidate_v4.py"
SCHEMA_PATH = "evals/foundation-v4/activation-evaluator-schema-v4.json"
RUNNER_PATH = "scripts/run_activation_trials_v4.py"
MODEL = "gpt-5.5"
REASONING = "medium"
SELECTOR_DECISION_CONTRACT = (
    "Select the minimum necessary decision atoms for this task: zero, one, or two. "
    "Admit an atom only when the task is a direct instance of that controlling decision; topical relevance, downstream usefulness, and possible future need are insufficient. "
    "Select two only for two independent direct controlling decisions. Use each positive boundary, admission rule, and complete pairwise exclusions. Ambiguity defaults to none. "
    "When explicit_constraint.status is exact, return exactly that atom. When it is ambiguous, return none. "
    "Bare adviser names do not invoke. Return only the closed schema object. Do not request tools, effects, approvals, claims, or context."
)


class InputError(ValueError):
    pass


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())


def git_show(root: Path, commit: str, path: str) -> bytes:
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=root, capture_output=True)
    if result.returncode:
        raise InputError("immutable input unavailable")
    return result.stdout


def git_tree(root: Path, commit: str) -> str:
    result = subprocess.run(["git", "rev-parse", "--verify", f"{commit}^{{tree}}"], cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise InputError("candidate tree unavailable")
    return result.stdout.strip()


def _load_checker(root: Path, commit: str | None = None) -> Any:
    raw = git_show(root, commit, CHECKER_PATH) if commit else (root / CHECKER_PATH).read_bytes()
    if commit and (root / CHECKER_PATH).read_bytes() != raw:
        raise InputError("live checker drift")
    spec = importlib.util.spec_from_file_location("aq4_candidate_checker", root / CHECKER_PATH)
    if not spec or not spec.loader:
        raise InputError("checker unavailable")
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(root / CHECKER_PATH), "exec"), module.__dict__)
    return module


def selector_packet_value(task: str, catalog: list[dict[str, Any]], constraint: dict[str, Any]) -> dict[str, Any]:
    return {
        "instruction": SELECTOR_DECISION_CONTRACT,
        "task": task,
        "decision_atom_catalog": catalog,
        "explicit_constraint": constraint,
    }


def selector_packet_digest(task: str, catalog: list[dict[str, Any]], constraint: dict[str, Any]) -> str:
    return sha256_json(selector_packet_value(task, catalog, constraint))


def qualification_schedule(cases: dict[str, dict[str, Any]], seed: str) -> list[tuple[str, str]]:
    if not isinstance(seed, str) or not seed.strip() or len(cases) != 40:
        raise InputError("schedule input unavailable")
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16))
    identifiers = sorted(cases)
    current, reduced = identifiers[:], identifiers[:]
    rng.shuffle(current)
    rng.shuffle(reduced)
    first = rng.choice(("current", "reduced"))
    other = "reduced" if first == "current" else "current"
    plan = [item for pair in zip(current, reduced, strict=True) for item in ((first, pair[0]), (other, pair[1]))]
    if len(plan) != 80 or sum(condition == "current" for condition, _ in plan) != 40 or sum(condition == "reduced" for condition, _ in plan) != 40 or any(plan[index][0] == plan[index + 1][0] for index in range(79)):
        raise InputError("schedule is not strict alternating")
    return plan


def condition_parity_digest(execution: dict[str, Any]) -> str:
    return sha256_json({key: value for key, value in execution.items() if key not in {"condition_parity_sha256", "schedule_seed", "schedule_sha256"}})


def _validate_schema(payload: Any, root: Path, commit: str | None) -> bytes:
    try:
        import jsonschema
        raw = git_show(root, commit, SCHEMA_PATH) if commit else (root / SCHEMA_PATH).read_bytes()
        if commit and (root / SCHEMA_PATH).read_bytes() != raw:
            raise InputError("live evaluator schema drift")
        errors = list(jsonschema.Draft202012Validator(json.loads(raw)).iter_errors(payload))
    except ImportError as exc:
        raise InputError("jsonschema unavailable") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError("evaluator schema unavailable") from exc
    if errors:
        raise InputError("evaluator schema rejected")
    return raw


def validate_corpus_documents(schema_raw: bytes, authoring_raw: bytes, heldout_raw: bytes, qualified_ids: set[str]) -> dict[str, dict[str, Any]]:
    """Validate exact bytes twice, then select the closed 40-case subset.

    The bound code-owned validator runs first in the live path. Its structured
    qualified-ID result is cross-checked here and does not replace this
    scorer's schema, distribution, identity, and count enforcement.
    """
    try:
        import jsonschema
        schema = json.loads(schema_raw)
        authoring = json.loads(authoring_raw)
        heldout = json.loads(heldout_raw)
        schema_validator = jsonschema.Draft202012Validator(schema)
        if list(schema_validator.iter_errors(authoring)) or list(schema_validator.iter_errors(heldout)):
            raise InputError("frozen corpus schema invalid")
    except ImportError as exc:
        raise InputError("jsonschema unavailable") from exc
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        if isinstance(exc, InputError):
            raise
        raise InputError("frozen corpus malformed") from exc
    authoring_cases = authoring.get("cases") if isinstance(authoring, dict) else None
    heldout_cases = heldout.get("cases") if isinstance(heldout, dict) else None
    if not isinstance(authoring_cases, list) or not isinstance(heldout_cases, list):
        raise InputError("frozen corpus case lists unavailable")
    heldout_automatic = [case for case in heldout_cases if isinstance(case, dict) and case.get("mode") == "automatic"]
    explicit = [case for case in [*authoring_cases, *heldout_cases] if isinstance(case, dict) and case.get("mode") == "explicit"]
    if len(heldout_automatic) != 32 or len(explicit) != 8:
        raise InputError("qualification distribution must be 32 heldout automatic plus all 8 explicit")
    selected = [*heldout_automatic, *explicit]
    identifiers = [case.get("id") for case in selected]
    if len(selected) != 40 or any(not isinstance(case_id, str) or not case_id for case_id in identifiers) or len(set(identifiers)) != 40:
        raise InputError("qualification identities are not exactly 40 unique cases")
    if set(identifiers) != qualified_ids:
        raise InputError("independent qualification IDs disagree with bound validator")
    return dict(zip(identifiers, selected, strict=True))


def call_bound_validator(validator: Any, root: Path, commit: str, tree: str) -> set[str]:
    entrypoint = getattr(validator, "validate_frozen", None)
    if not callable(entrypoint):
        raise InputError("bound corpus validator entrypoint unavailable")
    result = entrypoint(root, commit, tree)
    metrics = getattr(result, "metrics", None)
    identifiers = getattr(result, "qualified_ids", None)
    if getattr(result, "passed", None) is not True or getattr(result, "errors", None) not in ([], ()) or not isinstance(metrics, dict):
        raise InputError("bound corpus validator rejected committed bytes")
    expected_metrics = {"automatic_cases": 64, "explicit_cases": 8, "total_cases": 72, "qualified_cases": 40}
    if any(metrics.get(key) != value for key, value in expected_metrics.items()):
        raise InputError("bound corpus validator distribution mismatch")
    if not isinstance(identifiers, (list, tuple, set, frozenset)) or len(identifiers) != 40 or len(set(identifiers)) != 40 or any(not isinstance(item, str) or not item for item in identifiers):
        raise InputError("bound corpus validator qualification IDs invalid")
    return set(identifiers)


def _committed_validator(root: Path, reduced_commit: str, corpus: dict[str, Any]) -> Any:
    if corpus.get("validator_source") != "candidate_commit":
        raise InputError("validator source must be the exact candidate commit")
    raw = git_show(root, reduced_commit, corpus["validator_path"])
    try:
        live = (root / corpus["validator_path"]).read_bytes()
    except OSError as exc:
        raise InputError("live corpus validator unavailable") from exc
    if live != raw or sha256_bytes(raw) != corpus["validator_sha256"]:
        raise InputError("corpus validator custody mismatch")
    module_name = "aq4_bound_corpus_validator"
    module = types.ModuleType(module_name)
    module.__file__ = str(root / corpus["validator_path"])
    previous = sys.modules.get(module_name)
    try:
        sys.modules[module_name] = module
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
    finally:
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous
    return module


def _frozen_profile(root: Path, reduced_commit: str, checker: Any) -> dict[str, Any]:
    candidate = checker.load_candidate(root, reduced_commit)
    checker.require_bound(candidate)
    errors = checker.validate_candidate(candidate, root, reduced_commit, allow_unbound=False)
    if errors:
        raise InputError("reduced manifest invalid")
    base, _raw = checker.load_base_candidate(root, reduced_commit)
    corpus = candidate["corpus"]
    validator = _committed_validator(root, reduced_commit, corpus)
    validator_qualified_ids = call_bound_validator(validator, root, corpus["commit"], corpus["tree"])
    raw_documents: dict[str, bytes] = {}
    hashes: dict[str, str] = {}
    for key in ("schema_path", "authoring_path", "heldout_path"):
        raw = git_show(root, corpus["commit"], corpus[key])
        try:
            live = (root / corpus[key]).read_bytes()
        except OSError as exc:
            raise InputError("live frozen corpus unavailable") from exc
        if live != raw:
            raise InputError("live frozen corpus drift")
        hashes[key.replace("_path", "_sha256")] = sha256_bytes(raw)
        if hashes[key.replace("_path", "_sha256")] != corpus[key.replace("_path", "_sha256")]:
            raise InputError("frozen corpus digest mismatch")
        raw_documents[key] = raw
    cases = validate_corpus_documents(raw_documents["schema_path"], raw_documents["authoring_path"], raw_documents["heldout_path"], validator_qualified_ids)
    return {
        "candidate": candidate,
        "base": base,
        "cases": cases,
        "corpus": {
            "source_commit": corpus["commit"], "source_tree": corpus["tree"],
            "activation_schema_sha256": hashes["schema_sha256"],
            "authoring_sha256": hashes["authoring_sha256"],
            "heldout_sha256": hashes["heldout_sha256"],
            "validator_sha256": corpus["validator_sha256"],
        },
    }


def _candidate_expected(candidate: dict[str, Any], condition: str, reduced_commit: str, reduced_tree: str) -> dict[str, str]:
    commit = checker_source(candidate) if condition == "current" else reduced_commit
    tree = candidate["source"]["tree"] if condition == "current" else reduced_tree
    return {"commit": commit, "tree": tree, "input_sha256": candidate["conditions"][condition]["condition_input_sha256"]}


def checker_source(candidate: dict[str, Any]) -> str:
    return candidate["source"]["commit"]


def _payload_projection(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: row[key] for key in ("payload_id", "owner_adviser_id", "source_path", "sha256")} for row in rows]


def validate(payload: Any, root: Path = ROOT, *, profile: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any], Any, str]:
    if not isinstance(payload, dict):
        raise InputError("evaluator schema rejected")
    try:
        reduced_commit = payload["reduced_candidate"]["commit"]
        reduced_tree = payload["reduced_candidate"]["tree"]
    except (KeyError, TypeError) as exc:
        raise InputError("reduced candidate missing") from exc
    synthetic = profile is not None
    if synthetic and payload.get("provenance_mode") != "synthetic_test":
        raise InputError("injected profiles require synthetic_test provenance")
    if not synthetic and payload.get("provenance_mode") != "live_runner":
        raise InputError("committed scoring requires live_runner provenance")
    checker = _load_checker(root, None if synthetic else reduced_commit)
    if synthetic:
        candidate, base, cases, corpus = profile["candidate"], profile["base"], profile["cases"], profile["corpus"]
        errors = checker.validate_candidate(candidate, root, allow_unbound=True)
        if errors:
            raise InputError("synthetic candidate invalid")
    else:
        if git_tree(root, reduced_commit) != reduced_tree:
            raise InputError("reduced candidate tree mismatch")
        frozen = _frozen_profile(root, reduced_commit, checker)
        candidate, base, cases, corpus = frozen["candidate"], frozen["base"], frozen["cases"], frozen["corpus"]
    schema_raw = _validate_schema(payload, root, None if synthetic else reduced_commit)
    if payload["corpus"] != corpus:
        raise InputError("corpus custody mismatch")
    execution = payload["execution_contract"]
    if execution["evaluator_schema_sha256"] != sha256_bytes(schema_raw):
        raise InputError("evaluator schema digest mismatch")
    if execution["condition_parity_sha256"] != condition_parity_digest(execution):
        raise InputError("condition parity digest mismatch")
    if execution["runner_path"] != RUNNER_PATH:
        raise InputError("runner path mismatch")
    if not synthetic:
        runner_raw = git_show(root, reduced_commit, RUNNER_PATH)
        if (root / RUNNER_PATH).read_bytes() != runner_raw or sha256_bytes(runner_raw) != execution["runner_protocol_sha256"]:
            raise InputError("runner provenance mismatch")
    expected_reduced = {"commit": reduced_commit, "tree": reduced_tree, "input_sha256": candidate["conditions"]["reduced"]["condition_input_sha256"]}
    if payload["reduced_candidate"] != expected_reduced:
        raise InputError("reduced candidate input mismatch")
    plan = qualification_schedule(cases, execution["schedule_seed"])
    if execution["schedule_sha256"] != sha256_json(plan):
        raise InputError("schedule digest mismatch")
    execution_digest = sha256_json(execution)
    contexts: set[str] = set()
    indices: set[int] = set()
    if [condition["id"] for condition in payload["conditions"]] != ["current", "reduced"]:
        raise InputError("condition order mismatch")
    for condition in payload["conditions"]:
        name = condition["id"]
        expected = _candidate_expected(candidate, name, reduced_commit, reduced_tree)
        if condition["candidate"] != expected:
            raise InputError("condition candidate mismatch")
        rows = condition["observations"]
        if len(rows) != len(cases) or {row["case_id"] for row in rows} != set(cases):
            raise InputError("case coverage mismatch")
        catalog = candidate["conditions"][name]["atom_catalog"]
        catalog_digest = sha256_json(catalog)
        if candidate["conditions"][name]["atom_catalog_sha256"] != catalog_digest:
            raise InputError("atom catalog digest mismatch")
        for observation in rows:
            case = cases[observation["case_id"]]
            index = observation["presentation_index"]
            if index in indices or index < 0 or index >= len(plan) or plan[index] != (name, case["id"]):
                raise InputError("schedule presentation mismatch")
            indices.add(index)
            context = observation["context_id"]
            if not context or context in contexts:
                raise InputError("context not globally fresh")
            contexts.add(context)
            task_digest = sha256_bytes(case["prompt"].encode())
            if observation["corpus_prompt_sha256"] != task_digest or observation["task_sha256"] != task_digest:
                raise InputError("task digest mismatch")
            if observation["candidate_input_sha256"] != expected["input_sha256"] or observation["atom_catalog_sha256"] != catalog_digest:
                raise InputError("mounted candidate custody mismatch")
            if observation["execution_contract_sha256"] != execution_digest or observation["runner_protocol_sha256"] != execution["runner_protocol_sha256"]:
                raise InputError("execution custody mismatch")
            constraint = checker.parse_explicit_atom_constraint(case["prompt"], candidate)
            if observation["explicit_constraint"] != constraint:
                raise InputError("explicit constraint mismatch")
            atoms = checker.enforce_explicit_constraint(observation["selected_decision_atoms"], constraint)
            mapped = checker.map_atoms_to_advisers(candidate, atoms)
            if observation["effective_mapped_advisers"] != mapped:
                raise InputError("atom mapping mismatch")
            outcome = checker.resolve_parent_payload_resolution(base, case["hidden_labels"]["reference_triggers"], mapped)
            projected = _payload_projection(outcome["records"])
            resolution = {"status": outcome["status"], "resolved_count": outcome["resolved_count"]}
            if observation["payload_resolution"] != resolution or observation["resolved_payloads"] != projected:
                raise InputError("resolved payload custody mismatch")
            if observation["selector_packet_sha256"] != selector_packet_digest(case["prompt"], catalog, constraint):
                raise InputError("selector packet digest mismatch")
    if indices != set(range(2 * len(cases))):
        raise InputError("presentation coverage mismatch")
    return payload, {"candidate": candidate, "base": base, "cases": cases}, checker, execution_digest


def ratio(a: int, b: int) -> float:
    if not b:
        return 1.0
    return a / b


def score_condition(condition: dict[str, Any], state: dict[str, Any], checker: Any) -> dict[str, Any]:
    candidate, base, cases = state["candidate"], state["base"], state["cases"]
    rows = {row["case_id"]: row for row in condition["observations"]}
    tp = fp = fn = native = native_ok = stacking = must_not = two = two_ok = refs = authority = 0
    explicit = explicit_ok = 0
    for case_id, case in cases.items():
        row = rows[case_id]
        want = set(case["hidden_labels"]["expected_decision_atoms"])
        got = set(row["selected_decision_atoms"])
        tp += len(want & got); fp += len(got - want); fn += len(want - got)
        must_not += len(got & set(case["hidden_labels"].get("must_not_select_atoms", [])))
        if not want:
            native += 1; native_ok += int(not got)
        if len(want) == 1:
            stacking += int(len(got) > 1)
        if len(want) == 2:
            two += 1; two_ok += int(got == want)
        if case.get("mode") == "explicit":
            explicit += 1; explicit_ok += int(got == want)
        outcome = checker.resolve_parent_payload_resolution(base, case["hidden_labels"]["reference_triggers"], row["effective_mapped_advisers"])
        covered = (set().union(*(set(item["trigger_ids"]) for item in outcome["records"])) if outcome["records"] else set()) & set(case["hidden_labels"]["reference_triggers"])
        refs += int(outcome["status"] == "resolved" and covered == set(case["hidden_labels"]["reference_triggers"]) and not row["full_schema_or_template_loaded"])
        authority += sum(int(row[key]) for key in ("effect_requested", "effect_granted", "claim_requested", "claim_granted", "tool_requested", "tool_granted"))
    metrics = {
        "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn),
        "native_abstention_specificity": ratio(native_ok, native),
        "explicit_exact_set_compliance": ratio(explicit_ok, explicit),
        "reference_load_correctness": ratio(refs, len(cases)),
    }
    gates = {
        "precision": metrics["precision"] >= .95, "recall": metrics["recall"] >= .90,
        "native_abstention_specificity": metrics["native_abstention_specificity"] >= .95,
        "one_decision_stacking": stacking == 0, "must_not_select": must_not == 0,
        "exactly_two_exact_set": two_ok == two,
        "explicit_exact_set_compliance": metrics["explicit_exact_set_compliance"] == 1,
        "reference_load_correctness": metrics["reference_load_correctness"] == 1,
        "implicit_authority_or_tool_events": authority == 0,
    }
    return {"id": condition["id"], "candidate": condition["candidate"], "counts": {"true_positive_edges": tp, "false_positive_edges": fp, "false_negative_edges": fn, "native_abstention_total": native, "one_decision_stacking_raw_count": stacking, "must_not_select_violations": must_not, "exactly_two_cases": two, "exactly_two_exact_sets": two_ok, "implicit_authority_or_tool_events": authority}, "metrics": metrics, "gates": gates, "status": "pass" if all(gates.values()) else "fail"}


def insufficient(reason: str) -> dict[str, Any]:
    return {"schema_version": "4.0", "evaluation_mode": "qualification", "status": "insufficient_data", "promotion_eligible": False, "runtime_provenance_proven": False, "provider_identity_proven": False, "product_behavior_proven": False, "telemetry_attested": False, "deterministic_input_telemetry_scored": False, "raw_trajectories_persisted": False, "insufficiency_reason": reason, "maximum_claim": None}


def _score_internal(payload: Any, root: Path, *, profile: dict[str, Any] | None) -> dict[str, Any]:
    try:
        payload, state, checker, execution_digest = validate(payload, root, profile=profile)
        results = [score_condition(condition, state, checker) for condition in payload["conditions"]]
    except (InputError, ValueError, OSError, KeyError, TypeError) as exc:
        return insufficient(str(exc) if isinstance(exc, InputError) else "custody_unavailable")
    passed = all(result["status"] == "pass" for result in results)
    return {"schema_version": "4.0", "evaluation_mode": "qualification", "status": "pass" if passed else "fail", "promotion_eligible": False, "runtime_provenance_proven": False, "provider_identity_proven": False, "product_behavior_proven": False, "telemetry_attested": False, "deterministic_input_telemetry_scored": True, "score_basis": "supplied_observations", "corpus": payload["corpus"], "reduced_candidate": payload["reduced_candidate"], "execution_contract_sha256": execution_digest, "conditions": results, "raw_trajectories_persisted": False, "maximum_claim": "unattested deterministic decision-atom telemetry from supplied observations"}


def score(payload: Any, root: Path = ROOT, *, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Public/synthetic scorer: serialized live provenance is categorically denied."""
    if isinstance(payload, dict) and payload.get("provenance_mode") == "live_runner":
        return insufficient("public serialized scoring rejects live_runner provenance")
    if profile is None:
        return insufficient("public serialized scoring requires an injected synthetic profile")
    return _score_internal(payload, root, profile=profile)


def score_live(payload: Any, root: Path, *, witness: object) -> dict[str, Any]:
    """Runner-only path guarded by a non-serializable module-load identity."""
    if _LIVE_WITNESS is None or witness is not _LIVE_WITNESS:
        return insufficient("live runner identity witness mismatch")
    if not isinstance(payload, dict) or payload.get("provenance_mode") != "live_runner":
        return insufficient("live runner provenance required")
    return _score_internal(payload, root, profile=None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text() if args.input else sys.stdin.read())
        result = score(payload)
    except (OSError, json.JSONDecodeError):
        result = insufficient("input_unavailable")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return {"pass": 0, "fail": 1, "insufficient_data": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
