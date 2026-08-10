#!/usr/bin/env python3
"""Fail-closed AQ8 candidate custody checker.

Invalid documents always raise :class:`CandidateError`; an empty returned list
is the sole manifest-validation success convention.  This module owns the
Git/filesystem boundary.  The imported H4 resolver remains pure.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from resolve_h4_unresolved_decision_graph_v8 import (  # noqa: E402
    ResolverError,
    build_condition_packet,
    canonical_json,
    resolve_graph,
    validate_graph_output,
)


class CandidateError(ValueError):
    """An AQ8 candidate is incomplete, unbound, or not byte-custodied."""


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = "evals/foundation-v4/decision-certificate-candidate-v8.json"

H4 = ("d6f9e6089e6e11f158a2d3bf4af717fc026548d4", "6b65ea1e125836c9ae684e869f1156e5750c7a0b")
GATE = ("953651815e76c56f0cf8d23d9eae9ef6a480726f", "83c5aa7ecd3930733071e509ba56d307ae49aa59")
BASE = ("f09a0544acf4b7a95fff796434273511a0683ca9", "38c8c8adf3bb633d33200df1ec65f33e985ae244")
CONTRACT = ("a31038253e6cb0900731c33ee3dc2f20985c2e47", "aabe520b88571f56d7ae65a34e3722ccbf08f01f")
CORPUS = ("46174c0c5eb3da9b6134305329ebc36cc5108847", "163677779d0db59b586a91d4d3becf21803afb2e")
VALIDATOR = ("a062c8319bde9296068749e85612bb9061016efa", "d644cd465ef13fcbfebf1311d115030c58859119")
RUN_INDEX = ("c1e76aa60a6dc47a1f93405f2f9cc68768ea529a", "40658253ac3d471e52b1696011b92308480986ff")

METRIC = ("a07147eee19ac17f22113fc6b8cc673a0c761764", "8ddbad21796ece86c2676dea622d0235e37990d8")
METRIC_SHA256 = "144a7b98ee7cdb852314a8e509a003a5c16dd588b3bf2727412051d3436659c7"

H4_AUTHORITY_PATH = "evals/foundation-v4/unresolved-decision-graph-authority-v8.json"
PROTOCOL_PATH = "evals/foundation-v4/unresolved-decision-graph-protocol-v8.json"
SELECTOR_SCHEMA_PATH = "evals/foundation-v4/unresolved-decision-graph-selector-output-schema-v8.json"
RUNTIME_SELECTOR_SCHEMA_PATH = "evals/foundation-v4/unresolved-decision-graph-runtime-output-schema-v8.json"
ADAPTER_PATH = "evals/foundation-v4/unresolved-decision-graph-condition-adapter-v8.json"
REFERENCE_POLICY_PATH = "evals/foundation-v4/unresolved-decision-graph-reference-policy-v8.json"
GATE_PATH = "evals/foundation-v4/unresolved-decision-graph-gates-v8.json"
METRIC_PATH = "evals/foundation-v4/unresolved-decision-graph-metrics-v8.json"
BASE_PATH = "evals/foundation-v4/reduced-four-skills/candidate.json"
CORPUS_ROOT = "evals/foundation-v4/future-activation-v8"
CORPUS_SCHEMA = f"{CORPUS_ROOT}/activation-schema.json"
CORPUS_README = f"{CORPUS_ROOT}/README.md"
AUTHORING = f"{CORPUS_ROOT}/activation-authoring.json"
HELDOUT = f"{CORPUS_ROOT}/activation-heldout.json"
VALIDATOR_PATH = "scripts/validate_future_activation_corpus_v8.py"
RUN_INDEX_PATH = "scripts/aq_run_index_v8.py"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ROLES = (
    "checker",
    "resolver",
    "scorer",
    "runner",
    "evaluator_schema",
    "runtime_graph_schema",
    "validator",
    "run_index",
    "condition_adapter",
    "gate_authority",
    "metric_authority",
)
ROLE_PATHS = {
    "checker": "scripts/check_reduced_four_skill_candidate_v8.py",
    "resolver": "scripts/resolve_h4_unresolved_decision_graph_v8.py",
    "scorer": "scripts/score_activation_v8.py",
    "runner": "scripts/run_activation_trials_v8.py",
    "evaluator_schema": "evals/foundation-v4/activation-evaluator-schema-v8.json",
    "runtime_graph_schema": RUNTIME_SELECTOR_SCHEMA_PATH,
    "validator": VALIDATOR_PATH,
    "run_index": RUN_INDEX_PATH,
    "condition_adapter": ADAPTER_PATH,
    "gate_authority": GATE_PATH,
    "metric_authority": METRIC_PATH,
}
CONDITIONS = (
    ("current", "e0c21c0ff763dc53f3ca4a6edb711d935edc041ff5d9c951dea890ddef4603af"),
    ("reduced", "e4085d2a637e63fb459dbdc3a64281afbbf9362501c7654ba1b95d6aff26f87b"),
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git(root: Path, arguments: list[str]) -> bytes:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
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
    def closed_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw,
            object_pairs_hook=closed_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise CandidateError(f"{label} is not closed JSON") from error
    if not isinstance(value, dict):
        raise CandidateError(f"{label} is not an object")
    return value


def _authority(root: Path, pair: tuple[str, str], path: str, digest: str) -> bytes:
    commit, tree = pair
    if _commit(root, commit) != commit or _tree(root, commit) != tree:
        raise CandidateError("frozen authority commit/tree mismatch")
    raw = _show(root, commit, path)
    if not isinstance(digest, str) or not HEX64.fullmatch(digest) or _sha(raw) != digest:
        raise CandidateError("frozen authority digest mismatch")
    return raw


def _binding(pair: tuple[str, str], path: str, digest: str) -> dict[str, str]:
    return {"commit": pair[0], "tree": pair[1], "path": path, "sha256": digest}


H4_BINDING = _binding(H4, H4_AUTHORITY_PATH, "3452f1ee7552549feac9a3f9d4d720eaae1b371177b5a4185596287ac98afd68")
PROTOCOL_BINDING = _binding(H4, PROTOCOL_PATH, "a145766c475de5ed1411bc86467a1a82c3cdaa18782b772ef00901238f590fd5")
SCHEMA_BINDING = _binding(H4, SELECTOR_SCHEMA_PATH, "5ef3bd8dc5a1a83a25c51d10513607c17e298086450b00181caecac0dba35af4")
RUNTIME_SCHEMA_BINDING = _binding(H4, RUNTIME_SELECTOR_SCHEMA_PATH, "e4d58b46e39ac65e56a339e7c0d2714d536a5d517de57c2bcc34cfd5c6fe301e")
ADAPTER_BINDING = _binding(H4, ADAPTER_PATH, "2b82d26b9f438b7cfef712d59817bb2cc8426941167350ec58c42a9a6e5e5b31")
REFERENCE_POLICY_BINDING = _binding(H4, REFERENCE_POLICY_PATH, "e16ad13602a3540b97b608d6a70223e5c7061530b748a6843e007eea791826f4")
BASE_BINDING = _binding(BASE, BASE_PATH, "854f67bdd03e7121bd20e5513ef61ac806d016b3a5f1d6e5891bf4d9e546eb1f")
GATE_BINDING = _binding(GATE, GATE_PATH, "d17c6de19b456100a0c930d9cbe898d123dab882fe924c92226f9962fc7784d8")
METRIC_BINDING = _binding(METRIC, METRIC_PATH, METRIC_SHA256)
CONTRACT_BINDING = {
    **_binding(CONTRACT, CORPUS_SCHEMA, "4fd0b52885cfa46364f7b3265484fc50d8b8af424c4b4dbf2205b0291385db51"),
    "readme_path": CORPUS_README,
    "readme_sha256": "6c3a6f2019a99cc8b22333ed596bcf7b3306d2dde538e8fe7d68a831deded83f",
}
CORPUS_BINDING = {
    **_binding(CORPUS, CORPUS_SCHEMA, "4fd0b52885cfa46364f7b3265484fc50d8b8af424c4b4dbf2205b0291385db51"),
    "authoring_path": AUTHORING,
    "authoring_sha256": "08318e0f01b386bba2a0932915a87d07e637ed5b495e822308c42c8371d63a4d",
    "heldout_path": HELDOUT,
    "heldout_sha256": "db9c55fff89bdb636f977bb6bebd4b88830d09e6ffa3d0f09c8d4c120eb42227",
}
VALIDATOR_BINDING = _binding(VALIDATOR, VALIDATOR_PATH, "bd1769f9ad328c99706c2b5c6cff19a0cb2fddfa9760a14b4e70f41160e1ec33")
RUN_INDEX_BINDING = _binding(RUN_INDEX, RUN_INDEX_PATH, "ef6fd9fc7255eaca759641418fab65e8028676a91634163735d767a78925bd2d")


def _require_closed(value: Any, keys: set[str], message: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise CandidateError(message)
    return value


def _exact_value(value: Any, expected: Any) -> bool:
    """Compare closed JSON-like values without Python's bool/int equivalence."""
    if type(value) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(value) == set(expected) and all(
            _exact_value(value[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(value) == len(expected) and all(
            _exact_value(item, target)
            for item, target in zip(value, expected, strict=True)
        )
    return value == expected


def _complete_binding(binding: Any, *, extended: set[str] | None = None) -> None:
    keys = {"commit", "tree", "path", "sha256"} | (extended or set())
    value = _require_closed(binding, keys, "authority binding is not closed")
    if (
        not HEX40.fullmatch(value["commit"])
        or not HEX40.fullmatch(value["tree"])
        or not HEX64.fullmatch(value["sha256"])
        or not isinstance(value["path"], str)
        or value["path"].startswith("/")
        or ".." in Path(value["path"]).parts
    ):
        raise CandidateError("authority binding contains an unresolved placeholder")


def _expected_runtime_graph_schema(protocol: Any) -> dict[str, Any]:
    if not isinstance(protocol, dict):
        raise CandidateError("H4 protocol is unavailable")
    output = protocol.get("model_output_contract")
    slots = protocol.get("slot_contract")
    if not isinstance(output, dict) or not isinstance(slots, dict):
        raise CandidateError("H4 runtime projection source is unavailable")
    slot_order = slots.get("stable_slot_order")
    pair_order = slots.get("stable_pair_order")
    if slot_order != ["s0", "s1", "s2", "s3"] or pair_order != [["s0", "s1"], ["s0", "s2"], ["s0", "s3"], ["s1", "s2"], ["s1", "s3"], ["s2", "s3"]]:
        raise CandidateError("H4 runtime projection order is invalid")

    def row(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
        return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}

    def array(items: dict[str, Any], count: int) -> dict[str, Any]:
        return {"type": "array", "items": items, "minItems": count, "maxItems": count}

    properties = {
        "candidate_states": array(
            row(
                {
                    "slot_id": {"type": "string", "enum": slot_order},
                    "state": {"type": "string", "enum": output["candidate_states"]["allowed_states"]},
                },
                ["slot_id", "state"],
            ),
            4,
        ),
        "pairwise_relations": array(
            row(
                {
                    "left_slot": {"type": "string", "enum": ["s0", "s1", "s2"]},
                    "right_slot": {"type": "string", "enum": ["s1", "s2", "s3"]},
                    "relation": {"type": "string", "enum": output["pairwise_relations"]["allowed_relations"]},
                },
                ["left_slot", "right_slot", "relation"],
            ),
            6,
        ),
        "reference_needs": array(
            row(
                {
                    "slot_id": {"type": "string", "enum": slot_order},
                    "need": {"type": "string", "enum": output["reference_needs"]["allowed_needs"]},
                },
                ["slot_id", "need"],
            ),
            4,
        ),
    }
    return {"type": "object", "properties": properties, "required": ["candidate_states", "pairwise_relations", "reference_needs"], "additionalProperties": False}


def validate_runtime_graph_schema(protocol: Any, runtime_schema: Any) -> None:
    """Reject any runtime schema that is not the exact provider-safe H4 projection."""
    if not _exact_value(runtime_schema, _expected_runtime_graph_schema(protocol)):
        raise CandidateError("runtime graph schema is not the exact H4 projection")


def _live_clean(root: Path, commit: str) -> None:
    head = _git(root, ["rev-parse", "--verify", "HEAD^{commit}"]).decode().strip()
    status = _git(root, ["status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching"])
    if head != commit or status:
        raise CandidateError("live execution requires clean candidate HEAD with no tracked, untracked, or ignored drift")


def _result_claims() -> dict[str, Any]:
    # Kept in one helper so scorer, schema, tests, and manifest bind one literal.
    return {
        "maximum_claim": "unattested deterministic AQ8 unresolved-decision graph telemetry from supplied observations",
        "behavioral_qualification_proven": False,
        "runtime_provenance_proven": False,
        "provider_identity_proven": False,
        "telemetry_attested": False,
        "product_behavior_proven": False,
        "promotion_eligible": False,
    }


def _execution_contract(value: Any) -> None:
    contract = _require_closed(
        value,
        {"conditions", "model", "schedule", "packet", "isolation", "integrity", "authorities", "result_claims"},
        "execution contract is not closed",
    )
    if not _exact_value(contract["conditions"], [{"id": name, "condition_guidance_canonical_sha256": digest} for name, digest in CONDITIONS]):
        raise CandidateError("condition guidance contract mismatch")
    if not _exact_value(contract["model"], {"id": "gpt-5.5", "reasoning_effort": "medium"}):
        raise CandidateError("model contract mismatch")
    if not _exact_value(contract["schedule"], {"seed": "aq8-h4-v1", "qualification_cases": 40, "presentations": 80, "strict_alternation": True}):
        raise CandidateError("schedule contract mismatch")
    packet = {
        "keys": ["instruction", "task_text", "slot_order", "pair_order", "condition_guidance", "support_legend"],
        "sole_condition_variance": "condition_guidance",
        "model_output_roots": ["candidate_states", "pairwise_relations", "reference_needs"],
        "candidate_state_count": 4,
        "pair_relation_count": 6,
        "reference_need_count": 4,
    }
    if not _exact_value(contract["packet"], packet):
        raise CandidateError("packet contract mismatch")
    isolation = {
        "fresh_empty_cwd": True,
        "ephemeral_context_requested": True,
        "sandbox": "read-only",
        "approval_policy": "never",
        "tools_enabled": False,
        "apps_enabled": False,
        "plugins_enabled": False,
        "mcp_enabled": False,
        "isolated_codex_home": True,
        "isolated_home_mode": "0700",
        "auth_source": "owner-owned-regular-nonsymlink-0600",
        "auth_seed": "private-copy-0600-only",
        "explicit_subprocess_env": True,
        "exact_single_probe_input": True,
        "temp_cleanup_required": True,
        "global_agents_loaded": False,
    }
    if not _exact_value(contract["isolation"], isolation):
        raise CandidateError("isolation contract mismatch")
    integrity = {
        "unique_contexts_required": 80,
        "content_retries": 0,
        "canary_precompletion_infrastructure_retries_max": 1,
        "runner_local_raw_trajectories_persisted": False,
        "provider_raw_trajectory_retention_status": "unknown",
        "held_out_outcome_use": False,
    }
    if not _exact_value(contract["integrity"], integrity):
        raise CandidateError("integrity contract mismatch")
    _complete_binding(METRIC_BINDING)
    authorities = {
        "h4_commit": H4_BINDING["commit"],
        "h4_tree": H4_BINDING["tree"],
        "h4_sha256": H4_BINDING["sha256"],
        "gate_commit": GATE_BINDING["commit"],
        "gate_tree": GATE_BINDING["tree"],
        "gate_sha256": GATE_BINDING["sha256"],
        "metric_commit": METRIC_BINDING["commit"],
        "metric_tree": METRIC_BINDING["tree"],
        "metric_sha256": METRIC_BINDING["sha256"],
        "semantic_selector_schema_sha256": SCHEMA_BINDING["sha256"],
        "runtime_selector_schema_sha256": RUNTIME_SCHEMA_BINDING["sha256"],
    }
    if not _exact_value(contract["authorities"], authorities):
        raise CandidateError("execution authority contract mismatch")
    if not _exact_value(contract["result_claims"], _result_claims()):
        raise CandidateError("result claim ceiling mismatch")


def _all_primary_bindings() -> tuple[dict[str, str], ...]:
    return (
        H4_BINDING,
        PROTOCOL_BINDING,
        SCHEMA_BINDING,
        RUNTIME_SCHEMA_BINDING,
        ADAPTER_BINDING,
        REFERENCE_POLICY_BINDING,
        BASE_BINDING,
        GATE_BINDING,
        METRIC_BINDING,
        CONTRACT_BINDING,
        CORPUS_BINDING,
        VALIDATOR_BINDING,
        RUN_INDEX_BINDING,
    )


def validate_manifest_structure(manifest: Any) -> list[str]:
    """Validate a draft's closed structure without making a custody claim."""
    return _validate_manifest(manifest, ROOT, None, False)


def validate_manifest_document(manifest: Any, root: Path | None = None,
                               candidate_commit: str | None = None,
                               require_live: bool = False) -> list[str]:
    """Validate exact committed custody; a candidate commit is mandatory."""
    workspace = ROOT if root is None else Path(root)
    if candidate_commit is None:
        raise CandidateError("candidate custody requires an exact commit")
    commit = _commit(workspace, candidate_commit)
    committed_raw = _show(workspace, commit, MANIFEST_PATH)
    committed_manifest = _json(committed_raw, "AQ8 committed candidate")
    if not _exact_value(committed_manifest, manifest):
        raise CandidateError("supplied manifest differs from committed candidate")
    if require_live:
        try:
            if (workspace / MANIFEST_PATH).read_bytes() != committed_raw:
                raise CandidateError("live candidate manifest bytes differ")
        except OSError as error:
            raise CandidateError("live candidate manifest is unavailable") from error
    return _validate_manifest(manifest, workspace, commit, require_live)


def _validate_manifest(manifest: Any, workspace: Path,
                       candidate_commit: str | None,
                       require_live: bool) -> list[str]:
    try:
        required = {
            "schema_version",
            "claim_ceiling",
            "h4_authority",
            "protocol_authority",
            "selector_schema_authority",
            "runtime_selector_schema_authority",
            "condition_adapter_authority",
            "reference_policy_authority",
            "base_manifest_authority",
            "gate_authority",
            "metric_authority",
            "aq8_contract_authority",
            "corpus_authority",
            "validator_authority",
            "run_index_authority",
            "evaluator_surface",
            "execution_contract",
        }
        document = _require_closed(manifest, required, "candidate manifest is not closed")
        if document["schema_version"] != "8.0" or document["claim_ceiling"] != "structural-only":
            raise CandidateError("candidate identity or claim ceiling mismatch")
        expected = (
            ("h4_authority", H4_BINDING),
            ("protocol_authority", PROTOCOL_BINDING),
            ("selector_schema_authority", SCHEMA_BINDING),
            ("runtime_selector_schema_authority", RUNTIME_SCHEMA_BINDING),
            ("condition_adapter_authority", ADAPTER_BINDING),
            ("reference_policy_authority", REFERENCE_POLICY_BINDING),
            ("base_manifest_authority", BASE_BINDING),
            ("gate_authority", GATE_BINDING),
            ("metric_authority", METRIC_BINDING),
            ("aq8_contract_authority", CONTRACT_BINDING),
            ("corpus_authority", CORPUS_BINDING),
            ("validator_authority", VALIDATOR_BINDING),
            ("run_index_authority", RUN_INDEX_BINDING),
        )
        for key, binding in expected:
            _complete_binding(
                binding,
                extended={"readme_path", "readme_sha256"} if key == "aq8_contract_authority" else ({"authoring_path", "authoring_sha256", "heldout_path", "heldout_sha256"} if key == "corpus_authority" else None),
            )
            if document[key] != binding:
                raise CandidateError(f"{key} binding mismatch")
        _execution_contract(document["execution_contract"])
        surface = _require_closed(document["evaluator_surface"], {"files"}, "evaluator surface is not closed")
        files = surface["files"]
        if not isinstance(files, list) or len(files) != len(ROLES):
            raise CandidateError("evaluator surface cardinality mismatch")
        if [row.get("role") if isinstance(row, dict) else None for row in files] != list(ROLES):
            raise CandidateError("evaluator surface roles are unordered or incomplete")
        for row in files:
            _require_closed(row, {"role", "path", "sha256"}, "evaluator surface row is not closed")
            if row["path"] != ROLE_PATHS[row["role"]] or not isinstance(row["sha256"], str) or not HEX64.fullmatch(row["sha256"]):
                raise CandidateError("evaluator surface row mismatch or unresolved")

        if candidate_commit is not None:
            commit = _commit(workspace, candidate_commit)
            if require_live:
                _live_clean(workspace, commit)
            for binding in _all_primary_bindings():
                frozen = _authority(workspace, (binding["commit"], binding["tree"]), binding["path"], binding["sha256"])
                if _show(workspace, commit, binding["path"]) != frozen:
                    raise CandidateError("candidate changed an authority-controlled byte")
            frozen_readme = _authority(workspace, CONTRACT, CONTRACT_BINDING["readme_path"], CONTRACT_BINDING["readme_sha256"])
            if _show(workspace, commit, CONTRACT_BINDING["readme_path"]) != frozen_readme:
                raise CandidateError("candidate changed AQ8 contract readme")
            for key in ("authoring_path", "heldout_path"):
                path = CORPUS_BINDING[key]
                digest = CORPUS_BINDING[key.replace("_path", "_sha256")]
                if _show(workspace, commit, path) != _authority(workspace, CORPUS, path, digest):
                    raise CandidateError("candidate changed frozen AQ8 corpus byte")
            for row in files:
                committed = _show(workspace, commit, row["path"])
                if _sha(committed) != row["sha256"]:
                    raise CandidateError("evaluator surface digest mismatch")
                if require_live and (workspace / row["path"]).read_bytes() != committed:
                    raise CandidateError("live evaluator surface bytes differ")
            protocol = _json(_show(workspace, commit, PROTOCOL_PATH), "H4 protocol")
            semantic = _json(_show(workspace, commit, SELECTOR_SCHEMA_PATH), "semantic graph schema")
            runtime = _json(_show(workspace, commit, RUNTIME_SELECTOR_SCHEMA_PATH), "runtime graph schema")
            validate_runtime_graph_schema(protocol, runtime)
            # A minimal valid zero-root graph binds the semantic schema to the
            # resolver's exact projection without consulting any corpus row.
            slots = ["s0", "s1", "s2", "s3"]
            pairs = [("s0", "s1"), ("s0", "s2"), ("s0", "s3"), ("s1", "s2"), ("s1", "s3"), ("s2", "s3")]
            probe = {
                "candidate_states": [{"slot_id": slot, "state": "resolved_or_absent"} for slot in slots],
                "pairwise_relations": [{"left_slot": left, "right_slot": right, "relation": "unrelated"} for left, right in pairs],
                "reference_needs": [{"slot_id": slot, "need": "none"} for slot in slots],
            }
            validate_graph_output(probe, protocol, semantic)
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
    prior = sys.modules.get(name)
    try:
        sys.modules[name] = module
        spec.loader.exec_module(module)
    finally:
        if prior is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
    return module


def _load_module_bytes(raw: bytes, source_path: Path, name: str) -> Any:
    """Execute exact committed Python bytes without importing mutable live bytes."""
    module = types.ModuleType(name)
    module.__file__ = str(source_path)
    module.__package__ = ""
    prior = sys.modules.get(name)
    try:
        code = compile(raw, str(source_path), "exec")
        sys.modules[name] = module
        exec(code, module.__dict__)
    except (SyntaxError, ValueError, TypeError, ImportError) as error:
        raise CandidateError("committed validator import is unavailable") from error
    finally:
        if prior is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
    return module


def load_verified_candidate(root: Path | str, candidate_commit: str,
                            require_live: bool = True) -> dict[str, Any]:
    """Load the closed, byte-custodied profile used by AQ8 scorer and runner."""
    workspace = Path(root)
    commit = _commit(workspace, candidate_commit)
    if require_live:
        _live_clean(workspace, commit)
    manifest = _json(_show(workspace, commit, MANIFEST_PATH), "AQ8 candidate")
    validate_manifest_document(manifest, workspace, commit, require_live)
    validator = _load_module_bytes(
        _show(workspace, commit, VALIDATOR_PATH),
        workspace / VALIDATOR_PATH,
        "aq8_candidate_validator",
    )
    result = validator.validate_frozen(workspace, commit=CORPUS[0], tree=CORPUS[1])
    qualified_ids = tuple(getattr(result, "qualified_ids", ()))
    if getattr(result, "errors", (None,)) or len(qualified_ids) != 40 or len(set(qualified_ids)) != 40:
        raise CandidateError("AQ8 frozen qualified-id receipt is unavailable")
    protocol = _json(_show(workspace, commit, PROTOCOL_PATH), "H4 protocol")
    selector_schema = _json(_show(workspace, commit, SELECTOR_SCHEMA_PATH), "semantic graph schema")
    runtime_selector_schema = _json(_show(workspace, commit, RUNTIME_SELECTOR_SCHEMA_PATH), "runtime graph schema")
    validate_runtime_graph_schema(protocol, runtime_selector_schema)
    profile = {
        "candidate_commit": commit,
        "tree": _tree(workspace, commit),
        "digest": _sha(_show(workspace, commit, MANIFEST_PATH)),
        "manifest": manifest,
        "protocol": protocol,
        "selector_schema": selector_schema,
        "runtime_selector_schema": runtime_selector_schema,
        "reference_policy": _json(_show(workspace, commit, REFERENCE_POLICY_PATH), "H4 reference policy"),
        "base_manifest": _json(_show(workspace, commit, BASE_PATH), "base manifest"),
        "adapter": _json(_show(workspace, commit, ADAPTER_PATH), "condition adapter"),
        "corpus_schema": _json(_show(workspace, commit, CORPUS_SCHEMA), "AQ8 corpus schema"),
        "authoring": _json(_show(workspace, commit, AUTHORING), "AQ8 authoring"),
        "heldout": _json(_show(workspace, commit, HELDOUT), "AQ8 heldout"),
        "qualified_cases": qualified_ids,
        "qualified_ids": qualified_ids,
        "metric_authority": _json(_show(workspace, commit, METRIC_PATH), "AQ8 metric authority"),
        "gate_authority": _json(_show(workspace, commit, GATE_PATH), "AQ8 gate authority"),
        "execution_contract": manifest["execution_contract"],
    }
    expected = {
        "candidate_commit", "tree", "digest", "manifest", "protocol", "selector_schema",
        "runtime_selector_schema", "reference_policy", "base_manifest", "adapter",
        "corpus_schema", "authoring", "heldout", "qualified_cases", "qualified_ids",
        "metric_authority", "gate_authority", "execution_contract",
    }
    if set(profile) != expected:
        raise CandidateError("verified profile shape drift")
    return profile


def verify_zero_model_projection(profile: Any, cases: Any) -> dict[str, Any]:
    """Verify exactly forty qualified cases across both conditions without model I/O."""
    required = {
        "protocol", "selector_schema", "reference_policy", "base_manifest", "adapter",
        "qualified_ids", "execution_contract",
    }
    if not isinstance(profile, dict) or not required.issubset(profile) or not isinstance(cases, dict):
        raise CandidateError("zero-model projection inputs are invalid")
    identifiers = tuple(profile["qualified_ids"])
    if len(identifiers) != 40 or len(set(identifiers)) != 40 or set(cases) != set(identifiers):
        raise CandidateError("zero-model projection requires exactly the forty qualified cases")
    _execution_contract(profile["execution_contract"])
    checked = 0
    try:
        for case_id in identifiers:
            case = cases[case_id]
            if not isinstance(case, dict) or not isinstance(case.get("task_text"), str):
                raise CandidateError("qualified case is invalid")
            expected_semantic = validate_graph_output(
                case.get("expected_semantic_output"),
                profile["protocol"],
                profile["selector_schema"],
            )
            expected_parent = case.get("expected_parent_derivation")
            if not isinstance(expected_parent, dict):
                raise CandidateError("evaluator-owned parent derivation is unavailable")
            resolved = resolve_graph(
                case["task_text"],
                expected_semantic,
                profile["protocol"],
                profile["reference_policy"],
                profile["base_manifest"],
            )
            if resolved != expected_parent:
                raise CandidateError("evaluator-owned expected parent projection mismatch")
            packets = [
                build_condition_packet(profile["adapter"], condition, case["task_text"])
                for condition, _ in CONDITIONS
            ]
            if any(
                _sha(canonical_json(packet["condition_guidance"])) != digest
                for packet, (_, digest) in zip(packets, CONDITIONS, strict=True)
            ):
                raise CandidateError("condition guidance digest mismatch")
            if list(packets[0]) != profile["execution_contract"]["packet"]["keys"]:
                raise CandidateError("condition packet key order mismatch")
            if any(
                packets[0][key] != packets[1][key]
                for key in packets[0]
                if key != "condition_guidance"
            ) or packets[0]["condition_guidance"] == packets[1]["condition_guidance"]:
                raise CandidateError("condition packet variance mismatch")
            checked += 2
    except ResolverError as error:
        raise CandidateError("evaluator-owned expected graph is invalid") from error
    if checked != 80:
        raise CandidateError("presentation count mismatch")
    return {"status": "pass", "qualification_cases": 40, "presentations": 80, "live_calls": 0}
