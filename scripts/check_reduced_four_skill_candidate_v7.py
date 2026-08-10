#!/usr/bin/env python3
"""Fail-closed AQ7 candidate custody checker.

Invalid documents always raise :class:`CandidateError`; an empty returned list
is the sole success convention.  This module is the Git/filesystem boundary;
the imported resolver remains pure.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from resolve_h3_decision_certificate_v7 import (
    ResolverError,
    canonical_json,
    resolve_decision_certificate,
    validate_fact_output,
)


class CandidateError(ValueError):
    """An AQ7 candidate is incomplete, unbound, or not byte-custodied."""


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = "evals/foundation-v4/decision-certificate-candidate-v7.json"
H3 = ("ccbe06be9a2ef5feca4104b6918985ee9c4527c0", "dd20449fdc45a73c55adb349d8c828687728ef4d")
POLICY = ("c4e661a926e0ace78d9da83f71d9c52d311abb72", "f2abb05d32a888c9054ef2e7ab3ad0f08547de88")
BASE = ("f09a0544acf4b7a95fff796434273511a0683ca9", "38c8c8adf3bb633d33200df1ec65f33e985ae244")
CONTRACT = ("77d0502b88b6a69bd52cc09cbd4235b9ace119d0", "2b43d4f0b67ae9747fb07ea8dd5a77a6244281b4")
CORPUS = ("4a8efb300a1cd26a72d8ac3bef1d1ba5250481ee", "753d15a7b7dceacca7e66d39ab42fe89d94b237b")
VALIDATOR = ("3e8cfc7d5a1350762b486f000446a8a4c4d4c6d4", "827beaeb4568d35580b75a486556df4370ca5edd")
RUN_INDEX = ("f63670dda7e5bba4127ce59750844b52e35835fb", "b1cd3a8cde4a0867cb7da0432342a593a3278e54")
ADAPTER = ("ca046add50cdececfdbe14fe897d27a538431d55", "3fd841749eb117041e814a01890fda5cffe448d4")
H3_PROTOCOL = "evals/foundation-v4/decision-certificate-protocol-v6.json"
SELECTOR_SCHEMA = "evals/foundation-v4/decision-certificate-selector-output-schema-v6.json"
POLICY_PATH = "evals/foundation-v4/decision-certificate-reference-policy-v6.json"
BASE_PATH = "evals/foundation-v4/reduced-four-skills/candidate.json"
CORPUS_ROOT = "evals/foundation-v4/future-activation-v7"
CORPUS_SCHEMA = f"{CORPUS_ROOT}/activation-schema.json"
AUTHORING = f"{CORPUS_ROOT}/activation-authoring.json"
HELDOUT = f"{CORPUS_ROOT}/activation-heldout.json"
VALIDATOR_PATH = "scripts/validate_future_activation_corpus_v7.py"
RUN_INDEX_PATH = "scripts/aq_run_index_v7.py"
ADAPTER_PATH = "evals/foundation-v4/decision-certificate-condition-adapter-v7.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ROLES = ("checker", "resolver", "scorer", "runner", "evaluator_schema", "validator", "run_index", "condition_adapter")
CONDITIONS = (
    ("current", "6aea72c13ffc2aa8be66aa7ea2131b0b9045adc1fc23d3e338a04ad8fad7d6a0"),
    ("reduced", "237502bfde87c3b3cd2ad813fcda2e229591a858213816f7a903ade2746c8e8f"),
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git(root: Path, arguments: list[str]) -> bytes:
    try:
        result = subprocess.run(["git", *arguments], cwd=root, check=True,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError) as error:
        raise CandidateError("required Git custody object is unavailable") from error
    return result.stdout


def _commit(root: Path, revision: str) -> str:
    if not isinstance(revision, str) or not HEX40.fullmatch(revision):
        raise CandidateError("candidate commit must be a lowercase SHA")
    return _git(root, ["rev-parse", "--verify", f"{revision}^{{commit}}"]).decode().strip()


def _tree(root: Path, revision: str) -> str:
    return _git(root, ["rev-parse", "--verify", f"{revision}^{{tree}}"]).decode().strip()


def _show(root: Path, revision: str, path: str) -> bytes:
    if not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts:
        raise CandidateError("custody path escaped repository")
    return _git(root, ["show", f"{revision}:{path}"])


def _json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CandidateError(f"{label} is not JSON") from error
    if not isinstance(value, dict):
        raise CandidateError(f"{label} is not an object")
    return value


def _authority(root: Path, pair: tuple[str, str], path: str, digest: str) -> bytes:
    commit, tree = pair
    if _commit(root, commit) != commit or _tree(root, commit) != tree:
        raise CandidateError("frozen authority commit/tree mismatch")
    raw = _show(root, commit, path)
    if _sha(raw) != digest:
        raise CandidateError("frozen authority digest mismatch")
    return raw


def _binding(pair: tuple[str, str], path: str, digest: str) -> dict[str, str]:
    return {"commit": pair[0], "tree": pair[1], "path": path, "sha256": digest}


H3_BINDING = _binding(H3, H3_PROTOCOL, "9ad483a26fe339f81c947507de9c1c66d54b2823a38f68b1c5ee7fdf5c426f84")
SCHEMA_BINDING = _binding(H3, SELECTOR_SCHEMA, "9742f2255fed5452df52f9da789a6f2fd72e89aa94c3c6847fad6944445f5b25")
POLICY_BINDING = _binding(POLICY, POLICY_PATH, "92982c278e33ff52edce1ba2a16082afb3ecc1989d8333a77eee9ca0911fee19")
BASE_BINDING = _binding(BASE, BASE_PATH, "854f67bdd03e7121bd20e5513ef61ac806d016b3a5f1d6e5891bf4d9e546eb1f")
CONTRACT_BINDING = {**_binding(CONTRACT, CORPUS_SCHEMA, "47cc24936a28be13f496f2d0a6674f2998147eaa0030607f262f0769acf4aeb9"),
                    "readme_path": f"{CORPUS_ROOT}/README.md", "readme_sha256": "8d842b4dbf2bcd06ddda1e4ed1eb7ff5a95d10507ee03d25a93bbcd62893f047"}
CORPUS_BINDING = {**_binding(CORPUS, CORPUS_SCHEMA, "47cc24936a28be13f496f2d0a6674f2998147eaa0030607f262f0769acf4aeb9"),
                  "authoring_path": AUTHORING, "authoring_sha256": "331c24018ca70164eaddf88ac6ff4a0cbe6a94b6017a9e73223559f6d264a225",
                  "heldout_path": HELDOUT, "heldout_sha256": "fec755bd8838b3e23e96e8374bb28ad3e06229c176058a5a020f4a528326afd3"}
VALIDATOR_BINDING = _binding(VALIDATOR, VALIDATOR_PATH, "6121b4dc87dabcd3aa8d59a1af50523ea21f36fb1933c9e72d1cdb0ac4a8c443")
RUN_INDEX_BINDING = _binding(RUN_INDEX, RUN_INDEX_PATH, "e2e3243bd5fafc7430bed07e60ee27d91792d6784ca3aebf023c0de009167673")
ADAPTER_BINDING = _binding(ADAPTER, ADAPTER_PATH, "53a43ccf0df55791c867096c63315f50338fc4fd98f15bbae6060487b3b23576")


def _require_closed(value: Any, keys: set[str], message: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise CandidateError(message)
    return value


def _live_clean(root: Path, commit: str) -> None:
    head = _git(root, ["rev-parse", "--verify", "HEAD^{commit}"]).decode().strip()
    if head != commit or _git(root, ["status", "--porcelain=v1", "--untracked-files=all"]):
        raise CandidateError("live execution requires clean candidate HEAD with no untracked drift")


def _candidate_raw(root: Path, path: str, commit: str) -> bytes:
    raw = _show(root, commit, path)
    if raw != (root / path).read_bytes():
        raise CandidateError("committed and live candidate bytes differ")
    return raw


def _execution_contract(value: Any) -> None:
    contract = _require_closed(value, {"conditions", "model", "schedule", "packet", "isolation", "integrity", "gates", "result_claims"}, "execution contract is not closed")
    if contract["conditions"] != [{"id": name, "condition_guidance_canonical_sha256": digest} for name, digest in CONDITIONS]:
        raise CandidateError("condition guidance contract mismatch")
    if contract["model"] != {"id": "gpt-5.5", "reasoning_effort": "medium"}:
        raise CandidateError("model contract mismatch")
    if contract["schedule"] != {"seed": "aq7-h3-ci1-v1", "qualification_cases": 40, "presentations": 80, "strict_alternation": True}:
        raise CandidateError("schedule contract mismatch")
    if contract["packet"] != {"keys": ["instruction", "task_text", "predicate_order", "condition_guidance"], "sole_condition_variance": "condition_guidance", "model_output_root": "predicate_facts", "fact_count": 12}:
        raise CandidateError("packet contract mismatch")
    if contract["isolation"] != {"fresh_empty_cwd": True, "ephemeral_context_requested": True, "sandbox": "read-only", "approval_policy": "never", "tools_enabled": False, "apps_enabled": False, "plugins_enabled": False, "mcp_enabled": False}:
        raise CandidateError("isolation contract mismatch")
    if contract["integrity"] != {"unique_contexts_required": 80, "content_retries": 0, "canary_precompletion_infrastructure_retries_max": 1, "runner_local_raw_trajectories_persisted": False, "provider_raw_trajectory_retention_status": "unknown"}:
        raise CandidateError("integrity contract mismatch")
    gates = {"automatic_precision_min": "0.95", "automatic_recall_min": "0.90", "native_abstention_specificity_min": "0.95", "broad_router_overselection_max": "0.05", "one_decision_stacking_max": 0, "exactly_two_exact_set_min": "1.00", "must_not_select_violations_max": 0, "explicit_exact_set_min": "1.00", "selector_invalid_max": 0, "resolver_mismatch_max": 0, "payload_cap_violations_max": 0, "reference_load_correct_min": "1.00", "authority_tool_violations_max": 0}
    if contract["gates"] != gates:
        raise CandidateError("noncompensatory gate contract mismatch")
    claims = {"maximum_claim": "unattested deterministic AQ7 decision-certificate telemetry from supplied observations", "runtime_provenance_proven": False, "provider_identity_proven": False, "telemetry_attested": False, "product_behavior_proven": False, "promotion_eligible": False}
    if contract["result_claims"] != claims:
        raise CandidateError("result claim ceiling mismatch")


def validate_manifest_document(manifest: Any, root: Path | None = None, candidate_commit: str | None = None,
                               require_live: bool = False) -> list[str]:
    """Fail closed: return ``[]`` only for a fully bound, exact candidate."""
    workspace = ROOT if root is None else Path(root)
    commit = candidate_commit
    try:
        required = {"schema_version", "claim_ceiling", "h3_authority", "selector_schema_authority", "reference_policy_authority", "base_manifest_authority", "aq7_contract_authority", "corpus_authority", "validator_authority", "run_index_authority", "condition_adapter_authority", "evaluator_surface", "execution_contract"}
        document = _require_closed(manifest, required, "candidate manifest is not closed")
        if document["schema_version"] != "7.0" or document["claim_ceiling"] != "structural-only":
            raise CandidateError("candidate identity or claim ceiling mismatch")
        expected = (("h3_authority", H3_BINDING), ("selector_schema_authority", SCHEMA_BINDING), ("reference_policy_authority", POLICY_BINDING), ("base_manifest_authority", BASE_BINDING), ("aq7_contract_authority", CONTRACT_BINDING), ("corpus_authority", CORPUS_BINDING), ("validator_authority", VALIDATOR_BINDING), ("run_index_authority", RUN_INDEX_BINDING), ("condition_adapter_authority", ADAPTER_BINDING))
        for key, binding in expected:
            if document[key] != binding:
                raise CandidateError(f"{key} binding mismatch")
        _execution_contract(document["execution_contract"])
        surface = _require_closed(document["evaluator_surface"], {"files"}, "evaluator surface is not closed")
        files = surface["files"]
        if not isinstance(files, list) or len(files) != len(ROLES):
            raise CandidateError("evaluator surface cardinality mismatch")
        paths = {"checker": "scripts/check_reduced_four_skill_candidate_v7.py", "resolver": "scripts/resolve_h3_decision_certificate_v7.py", "scorer": "scripts/score_activation_v7.py", "runner": "scripts/run_activation_trials_v7.py", "evaluator_schema": "evals/foundation-v4/activation-evaluator-schema-v7.json", "validator": VALIDATOR_PATH, "run_index": RUN_INDEX_PATH, "condition_adapter": ADAPTER_PATH}
        if [row.get("role") if isinstance(row, dict) else None for row in files] != list(ROLES):
            raise CandidateError("evaluator surface roles are unordered or incomplete")
        for row in files:
            _require_closed(row, {"role", "path", "sha256"}, "evaluator surface row is not closed")
            if row["path"] != paths[row["role"]] or not isinstance(row["sha256"], str) or not HEX64.fullmatch(row["sha256"]):
                raise CandidateError("evaluator surface row mismatch")
        if commit is not None:
            commit = _commit(workspace, commit)
            if require_live:
                _live_clean(workspace, commit)
            for binding in (H3_BINDING, SCHEMA_BINDING, POLICY_BINDING, BASE_BINDING, CONTRACT_BINDING, CORPUS_BINDING, VALIDATOR_BINDING, RUN_INDEX_BINDING, ADAPTER_BINDING):
                primary = _authority(workspace, (binding["commit"], binding["tree"]), binding["path"], binding["sha256"])
                if _show(workspace, commit, binding["path"]) != primary:
                    raise CandidateError("candidate changed an authority-controlled byte")
            if _authority(workspace, CONTRACT, CONTRACT_BINDING["readme_path"], CONTRACT_BINDING["readme_sha256"]) != _show(workspace, commit, CONTRACT_BINDING["readme_path"]):
                raise CandidateError("candidate changed AQ7 contract readme")
            for key in ("authoring_path", "heldout_path"):
                path, digest = CORPUS_BINDING[key], CORPUS_BINDING[key.replace("_path", "_sha256")]
                frozen = _authority(workspace, CORPUS, path, digest)
                if _show(workspace, commit, path) != frozen:
                    raise CandidateError("candidate changed frozen AQ7 corpus byte")
            for row in files:
                if _sha(_show(workspace, commit, row["path"])) != row["sha256"]:
                    raise CandidateError("evaluator surface digest mismatch")
                if require_live and (workspace / row["path"]).read_bytes() != _show(workspace, commit, row["path"]):
                    raise CandidateError("live evaluator surface bytes differ")
        return []
    except CandidateError:
        raise
    except (OSError, TypeError, KeyError, json.JSONDecodeError, ResolverError) as error:
        raise CandidateError("candidate validation failed closed") from error


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CandidateError("validator import is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_verified_candidate(root: Path | str, candidate_commit: str, require_live: bool = True) -> dict[str, Any]:
    """Load the closed, byte-custodied profile used by AQ7 scorer and runner."""
    workspace = Path(root)
    commit = _commit(workspace, candidate_commit)
    if require_live:
        _live_clean(workspace, commit)
    manifest = _json(_show(workspace, commit, MANIFEST_PATH), "AQ7 candidate")
    validate_manifest_document(manifest, workspace, commit, require_live)
    validator = _load_module(workspace / VALIDATOR_PATH, "aq7_candidate_validator")
    result = validator.validate_frozen(workspace, commit=CORPUS[0], tree=CORPUS[1])
    if getattr(result, "errors", (None,)) or len(getattr(result, "qualified_ids", ())) != 40:
        raise CandidateError("AQ7 frozen qualified-id receipt is unavailable")
    protocol = _json(_show(workspace, commit, H3_PROTOCOL), "H3 protocol")
    selector_schema = _json(_show(workspace, commit, SELECTOR_SCHEMA), "selector schema")
    profile = {
        "candidate_commit": commit,
        "tree": _tree(workspace, commit),
        "digest": _sha(_show(workspace, commit, MANIFEST_PATH)),
        "manifest": manifest,
        "protocol": protocol,
        "selector_schema": selector_schema,
        "reference_policy": _json(_show(workspace, commit, POLICY_PATH), "reference policy"),
        "base_manifest": _json(_show(workspace, commit, BASE_PATH), "base manifest"),
        "adapter": _json(_show(workspace, commit, ADAPTER_PATH), "condition adapter"),
        "corpus_schema": _json(_show(workspace, commit, CORPUS_SCHEMA), "AQ7 schema"),
        "authoring": _json(_show(workspace, commit, AUTHORING), "AQ7 authoring"),
        "heldout": _json(_show(workspace, commit, HELDOUT), "AQ7 heldout"),
        "qualified_cases": tuple(getattr(result, "qualified_ids")),
        "qualified_ids": tuple(getattr(result, "qualified_ids")),
        "execution_contract": manifest["execution_contract"],
    }
    if set(profile) != {"candidate_commit", "tree", "digest", "manifest", "protocol", "selector_schema", "reference_policy", "base_manifest", "adapter", "corpus_schema", "authoring", "heldout", "qualified_cases", "qualified_ids", "execution_contract"}:
        raise CandidateError("verified profile shape drift")
    return profile


def verify_zero_model_projection(profile: Any, cases: Any) -> dict[str, Any]:
    """Verify exactly 40 qualified IDs across current/reduced without model I/O."""
    required = {"protocol", "selector_schema", "reference_policy", "base_manifest", "qualified_ids", "execution_contract"}
    if not isinstance(profile, dict) or not required.issubset(profile) or not isinstance(cases, dict):
        raise CandidateError("zero-model projection inputs are invalid")
    identifiers = tuple(profile["qualified_ids"])
    if len(identifiers) != 40 or len(set(identifiers)) != 40 or set(cases) != set(identifiers):
        raise CandidateError("zero-model projection requires exactly the 40 qualified cases")
    contract = profile["execution_contract"]
    _execution_contract(contract)
    checked = 0
    try:
        for case_id in identifiers:
            case = cases[case_id]
            if not isinstance(case, dict):
                raise CandidateError("qualified case is invalid")
            packet = case.get("packet")
            grading = case.get("grading")
            if not isinstance(packet, dict) or set(packet) != {"task_text"} or not isinstance(grading, dict):
                raise CandidateError("projection case shape is invalid")
            facts = validate_fact_output({"predicate_facts": grading.get("expected_predicate_facts")}, profile["protocol"], profile["selector_schema"])
            resolved = resolve_decision_certificate(packet["task_text"], list(facts), profile["protocol"], profile["reference_policy"], profile["base_manifest"])
            expected = {"selection_status": grading.get("expected_selection_status"), "selected_atoms": grading.get("expected_selected_atoms"), "selection_constraint": grading.get("expected_selection_constraint"), "mapped_advisers": grading.get("expected_advisers"), "reference_requests": grading.get("expected_reference_requests")}
            if any(resolved[key] != value for key, value in expected.items()):
                raise CandidateError("evaluator-owned expected projection mismatch")
            payload_expectation = grading.get("deterministic_reference_expectations")
            if (not isinstance(payload_expectation, dict)
                    or resolved["payload_resolution"] != {
                        "status": payload_expectation.get("status"),
                        "resolved_count": payload_expectation.get("resolved_payload_count"),
                        "payloads": payload_expectation.get("payloads"),
                    }):
                raise CandidateError("evaluator-owned payload projection mismatch")
            checked += 2
    except ResolverError as error:
        raise CandidateError("evaluator-owned expected facts are invalid") from error
    if checked != 80:
        raise CandidateError("presentation count mismatch")
    return {"status": "pass", "qualification_cases": 40, "presentations": 80, "live_calls": 0}
