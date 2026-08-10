#!/usr/bin/env python3
"""Exact-candidate AQ8 unresolved-decision-graph runner.

The runner retains no model trajectory.  Per-presentation bytes and semantic
objects live only in this process until the closed scorer returns one aggregate
status and digest.  The Git-common-directory index stores custody state only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import types
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = "scripts/check_reduced_four_skill_candidate_v8.py"
RESOLVER_PATH = "scripts/resolve_h4_unresolved_decision_graph_v8.py"
SCORER_PATH = "scripts/score_activation_v8.py"
INDEX_PATH = "scripts/aq_run_index_v8.py"
RUNNER_PATH = "scripts/run_activation_trials_v8.py"
EVALUATOR_SCHEMA_PATH = "evals/foundation-v4/activation-evaluator-schema-v8.json"
RUNTIME_GRAPH_SCHEMA_ROLE = "runtime_graph_schema"
MODEL = "gpt-5.5"
REASONING = "medium"
SCHEDULE_SEED = "aq8-h4-v1"
APPROVAL = "aq8-authorized-canary-batch"
ISOLATION_PROBE = "AQ8 isolation preflight"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
PACKET_KEYS = (
    "instruction",
    "task_text",
    "slot_order",
    "pair_order",
    "condition_guidance",
    "support_legend",
)
EVENT_KEYS = (
    "effect_requested",
    "effect_granted",
    "claim_requested",
    "claim_granted",
    "tool_requested",
    "tool_granted",
)
ISOLATION_CONTRACT = {
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
DISABLED_FEATURES = (
    "apply_patch_streaming_events",
    "apps",
    "artifact",
    "auth_elicitation",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "chronicle",
    "code_mode",
    "code_mode_buffered_exec",
    "code_mode_host",
    "code_mode_only",
    "computer_use",
    "default_mode_request_user_input",
    "enable_mcp_apps",
    "goals",
    "guardian_approval",
    "hooks",
    "image_generation",
    "in_app_browser",
    "memories",
    "multi_agent",
    "multi_agent_v2",
    "plugin_sharing",
    "plugins",
    "recommended_plugins",
    "remote_plugin",
    "request_permissions_tool",
    "shell_tool",
    "skill_mcp_dependency_install",
    "skill_search",
    "standalone_web_search",
    "tool_call_mcp_elicitation",
    "tool_suggest",
    "unified_exec",
    "view_image",
    "workspace_dependencies",
)
CONFIG_OVERRIDES = (
    f'model="{MODEL}"',
    f'model_reasoning_effort="{REASONING}"',
    'web_search="disabled"',
    "skills.bundled.enabled=false",
    "skills.include_instructions=false",
    "include_permissions_instructions=false",
    "include_apps_instructions=false",
    "include_collaboration_mode_instructions=false",
    "include_environment_context=false",
    "mcp_servers={}",
)


class RunnerError(ValueError):
    """The requested AQ8 operation cannot proceed."""


class PreflightError(RunnerError):
    """Immutable custody or zero-model validation failed."""


class InfrastructureError(RunnerError):
    """No completed model content was available for scoring."""


class LaunchError(InfrastructureError):
    """The isolated child could not be launched."""


class TransportError(InfrastructureError):
    """The child transport did not yield one completed response."""


class CompletedInvalid(RunnerError):
    """A completed response is malformed content and is never retryable."""


def _empty_events() -> dict[str, bool]:
    return {key: False for key in EVENT_KEYS}


def _completed_invalid(
    reason: str,
    context: str | None,
    *,
    events: dict[str, bool] | None = None,
) -> CompletedInvalid:
    error = CompletedInvalid(reason)
    error.context = context  # type: ignore[attr-defined]
    error.events = events or _empty_events()  # type: ignore[attr-defined]
    return error


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return sha256_bytes(raw)


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> Any:
    raise ValueError("non-finite JSON constant")


def _json_loads_closed(value: str | bytes) -> Any:
    return json.loads(
        value,
        object_pairs_hook=_closed_object,
        parse_constant=_reject_json_constant,
    )


def _git(root: Path, args: list[str], *, text: bool = False) -> Any:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=text)


def git_show(root: Path, commit: str, path: str) -> bytes:
    result = _git(root, ["show", f"{commit}:{path}"])
    if result.returncode:
        raise PreflightError("immutable input unavailable")
    return result.stdout


def git_identity(root: Path, commit: str) -> tuple[str, str]:
    resolved = _git(root, ["rev-parse", "--verify", f"{commit}^{{commit}}"], text=True)
    tree = _git(root, ["rev-parse", "--verify", f"{commit}^{{tree}}"], text=True)
    if resolved.returncode or tree.returncode:
        raise PreflightError("candidate identity unavailable")
    return resolved.stdout.strip(), tree.stdout.strip()


def require_exact_live_head(root: Path, requested: str) -> tuple[str, str]:
    if not isinstance(requested, str) or not HEX40.fullmatch(requested):
        raise PreflightError("exact lowercase candidate required")
    commit, tree = git_identity(root, requested)
    head = _git(root, ["rev-parse", "--verify", "HEAD^{commit}"], text=True)
    status = _git(
        root,
        ["status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching"],
        text=True,
    )
    if head.returncode or commit != requested or head.stdout.strip() != commit:
        raise PreflightError("candidate is not live HEAD")
    if status.returncode or status.stdout:
        raise PreflightError("execution input drift")
    return commit, tree


def committed_module(
    root: Path,
    commit: str,
    path: str,
    name: str,
    dependencies: dict[str, Any] | None = None,
) -> Any:
    require_exact_live_head(root, commit)
    raw = git_show(root, commit, path)
    destination = root / path
    try:
        live = destination.read_bytes()
    except OSError as error:
        raise PreflightError("committed module unavailable") from error
    if live != raw:
        raise PreflightError("committed module byte drift")
    module = types.ModuleType(name)
    module.__file__ = str(destination)
    old = {key: sys.modules.get(key) for key in [name, *(dependencies or {})]}
    try:
        sys.modules[name] = module
        for key, value in (dependencies or {}).items():
            sys.modules[key] = value
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
    finally:
        for key, value in old.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value
    return module


def _sealed(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or not all(
        isinstance(value.get(key), str) for key in ("commit", "tree", "sha256")
    ):
        raise PreflightError("sealed run binding unavailable")
    if not HEX40.fullmatch(value["commit"]) or not HEX40.fullmatch(value["tree"]):
        raise PreflightError("sealed run binding unavailable")
    if not HEX64.fullmatch(value["sha256"]):
        raise PreflightError("sealed run binding unavailable")
    return {
        "commit": value["commit"],
        "tree": value["tree"],
        "digest": value["sha256"],
    }


def binding_from_profile(
    profile: dict[str, Any],
    *,
    cli: dict[str, str] | None,
    schedule_digest: str,
) -> dict[str, Any]:
    """Project checker-sealed identities into the run-index grammar."""
    manifest = profile.get("manifest")
    if not isinstance(manifest, dict):
        raise PreflightError("execution contract unavailable")
    rows = manifest.get("evaluator_surface", {}).get("files") if isinstance(
        manifest.get("evaluator_surface"), dict
    ) else None
    runner = next(
        (row for row in rows if isinstance(row, dict) and row.get("role") == "runner"),
        None,
    ) if isinstance(rows, list) else None
    scorer = next(
        (row for row in rows if isinstance(row, dict) and row.get("role") == "scorer"),
        None,
    ) if isinstance(rows, list) else None
    if not isinstance(runner, dict) or not isinstance(scorer, dict):
        raise PreflightError("evaluator surface unavailable")
    binding: dict[str, Any] = {
        "protocol": _sealed(manifest.get("protocol_authority")),
        "reference_policy": _sealed(manifest.get("reference_policy_authority")),
        "corpus": _sealed(manifest.get("corpus_authority")),
        "candidate": {
            "commit": profile.get("candidate_commit"),
            "tree": profile.get("tree"),
            "digest": profile.get("digest"),
        },
        "runner": {
            "commit": profile.get("candidate_commit"),
            "tree": profile.get("tree"),
            "digest": runner.get("sha256"),
        },
        "evaluator": {
            "commit": profile.get("candidate_commit"),
            "tree": profile.get("tree"),
            "digest": scorer.get("sha256"),
        },
        "validator": _sealed(manifest.get("validator_authority")),
    }
    if cli is None:
        cli = {"id": "zero-model", "digest": "0" * 64}
    try:
        binding["cli"] = {
            "id": "zero-model" if cli["id"] == "zero-model" else "codex-cli",
            "digest": cli["digest"],
        }
        binding["model"] = {"id": MODEL, "digest": sha256_json({"id": MODEL})}
        binding["reasoning"] = {
            "id": REASONING,
            "digest": sha256_json({"id": REASONING}),
        }
        binding["tools"] = {
            "digest": sha256_json(
                {
                    "disabled": DISABLED_FEATURES,
                    "sandbox": "read-only",
                    "approval": "never",
                }
            )
        }
        binding["host"] = {
            "digest": sha256_json(
                {
                    "stdin_only": True,
                    "isolation_contract": ISOLATION_CONTRACT,
                }
            )
        }
        binding["schedule"] = {"seed": SCHEDULE_SEED, "digest": schedule_digest}
    except (KeyError, TypeError) as error:
        raise PreflightError("sealed run binding unavailable") from error
    return binding


def _validate_packet_pair(current: Any, reduced: Any) -> None:
    if (
        not isinstance(current, dict)
        or not isinstance(reduced, dict)
        or tuple(current) != PACKET_KEYS
        or tuple(reduced) != PACKET_KEYS
    ):
        raise PreflightError("packet closure unavailable")
    if any(current[key] != reduced[key] for key in PACKET_KEYS if key != "condition_guidance"):
        raise PreflightError("condition packet parity unavailable")
    if current["condition_guidance"] == reduced["condition_guidance"]:
        raise PreflightError("condition guidance delta unavailable")

    def keys(value: Any) -> set[str]:
        if isinstance(value, dict):
            return set(value) | set().union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value)) if value else set()
        return set()

    forbidden = (
        "expected",
        "parent_derivation",
        "case_id",
        "corpus_id",
        "outcome",
        "payload_id",
        "adviser_id",
    )
    if any(term in name.casefold() for name in keys(current) | keys(reduced) for term in forbidden):
        raise PreflightError("packet exposed evaluator material")


def _runtime_graph_schema_path(
    root: Path,
    commit: str,
    profile: dict[str, Any],
    checker: Any,
) -> Path:
    require_exact_live_head(root, commit)
    manifest = profile.get("manifest") if isinstance(profile, dict) else None
    surface = manifest.get("evaluator_surface") if isinstance(manifest, dict) else None
    rows = surface.get("files") if isinstance(surface, dict) else None
    matches = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("role") == RUNTIME_GRAPH_SCHEMA_ROLE
    ] if isinstance(rows, list) else []
    if len(matches) != 1 or set(matches[0]) != {"role", "path", "sha256"}:
        raise PreflightError("runtime graph schema binding unavailable")
    row = matches[0]
    path, digest = row.get("path"), row.get("sha256")
    if (
        not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        or not isinstance(digest, str)
        or not HEX64.fullmatch(digest)
    ):
        raise PreflightError("runtime graph schema binding unavailable")
    raw = git_show(root, commit, path)
    destination = root / path
    try:
        live = destination.read_bytes()
        value = _json_loads_closed(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise PreflightError("runtime graph schema unavailable") from error
    if sha256_bytes(raw) != digest or live != raw or not isinstance(value, dict):
        raise PreflightError("runtime graph schema byte drift")
    if value != profile.get("runtime_selector_schema"):
        raise PreflightError("runtime graph schema profile drift")
    validate = getattr(checker, "validate_runtime_graph_schema", None)
    if not callable(validate):
        raise PreflightError("runtime graph schema validator unavailable")
    try:
        validate(profile.get("protocol"), value)
    except Exception as error:
        raise PreflightError("runtime graph schema projection unavailable") from error
    return destination


def _case_map(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    documents = (profile.get("authoring"), profile.get("heldout"))
    rows: list[dict[str, Any]] = []
    for document in documents:
        if not isinstance(document, dict) or not isinstance(document.get("cases"), list):
            raise PreflightError("qualified corpus unavailable")
        rows.extend(case for case in document["cases"] if isinstance(case, dict))
    result = {
        case["case_id"]: case
        for case in rows
        if isinstance(case.get("case_id"), str) and case["case_id"]
    }
    if len(result) != len(rows):
        raise PreflightError("qualified corpus unavailable")
    return result


def _require_isolation_contract(profile: dict[str, Any]) -> None:
    execution = profile.get("execution_contract")
    isolation = execution.get("isolation") if isinstance(execution, dict) else None
    if not isinstance(isolation, dict) or isolation != ISOLATION_CONTRACT:
        raise PreflightError("isolated execution contract unavailable")


def _schedule_ok(schedule: Any, qualified_ids: tuple[str, ...]) -> bool:
    if not isinstance(schedule, (tuple, list)) or len(schedule) != 80:
        return False
    by_condition = {"current": [], "reduced": []}
    for index, row in enumerate(schedule):
        if (
            not isinstance(row, dict)
            or set(row) != {"presentation_index", "condition", "case_id"}
            or row.get("presentation_index") != index
            or row.get("condition") not in by_condition
            or row.get("case_id") not in qualified_ids
        ):
            return False
        by_condition[row["condition"]].append(row["case_id"])
        if index and schedule[index - 1]["condition"] == row["condition"]:
            return False
    expected = set(qualified_ids)
    return all(len(values) == 40 and set(values) == expected for values in by_condition.values())


def preflight(root: Path, requested: str) -> dict[str, Any]:
    """Run exact candidate and 40x2 production resolution/scoring with no model."""
    commit, tree = require_exact_live_head(root, requested)
    index_module = committed_module(root, commit, INDEX_PATH, "aq_run_index_v8")
    resolver = committed_module(
        root,
        commit,
        RESOLVER_PATH,
        "resolve_h4_unresolved_decision_graph_v8",
        {"aq_run_index_v8": index_module},
    )
    checker = committed_module(
        root,
        commit,
        CHECKER_PATH,
        "check_reduced_four_skill_candidate_v8",
        {"resolve_h4_unresolved_decision_graph_v8": resolver},
    )
    scorer = committed_module(
        root,
        commit,
        SCORER_PATH,
        "score_activation_v8",
        {
            "aq_run_index_v8": index_module,
            "resolve_h4_unresolved_decision_graph_v8": resolver,
        },
    )
    profile = checker.load_verified_candidate(root, commit, require_live=True)
    if (
        not isinstance(profile, dict)
        or profile.get("candidate_commit") != commit
        or profile.get("tree") != tree
    ):
        raise PreflightError("candidate custody unavailable")
    _require_isolation_contract(profile)
    runtime_path = _runtime_graph_schema_path(root, commit, profile, checker)
    qualified = profile.get("qualified_ids")
    if (
        not isinstance(qualified, (tuple, list))
        or len(qualified) != 40
        or len(set(qualified)) != 40
        or any(not isinstance(case_id, str) or not case_id for case_id in qualified)
    ):
        raise PreflightError("qualified corpus unavailable")
    qualified_ids = tuple(qualified)
    all_cases = _case_map(profile)
    if any(case_id not in all_cases for case_id in qualified_ids):
        raise PreflightError("qualified corpus unavailable")
    cases = {case_id: all_cases[case_id] for case_id in qualified_ids}
    verified = checker.verify_zero_model_projection(profile, cases)
    if not isinstance(verified, dict) or verified.get("status") != "pass":
        raise PreflightError("zero-model projection unavailable")
    schedule = scorer.build_schedule(qualified_ids, SCHEDULE_SEED)
    schedule_digest = scorer.schedule_digest(schedule)
    if not _schedule_ok(schedule, qualified_ids) or not isinstance(schedule_digest, str) or not HEX64.fullmatch(schedule_digest):
        raise PreflightError("exact schedule unavailable")
    for case in cases.values():
        task = case.get("task_text")
        if not isinstance(task, str) or not task:
            raise PreflightError("case task unavailable")
        current = resolver.build_condition_packet(profile["adapter"], "current", task)
        reduced = resolver.build_condition_packet(profile["adapter"], "reduced", task)
        _validate_packet_pair(current, reduced)
    state = {
        "checker": checker,
        "resolver": resolver,
        "scorer": scorer,
        "index_module": index_module,
        "profile": profile,
        "cases": cases,
        "schedule": list(schedule),
        "schedule_digest": schedule_digest,
        "commit": commit,
        "tree": tree,
        "runtime_graph_schema_path": runtime_path,
    }
    state["binding"] = binding_from_profile(
        profile,
        cli=None,
        schedule_digest=schedule_digest,
    )
    index_module.normalize_binding(state["binding"])
    zero_model_score_preflight(state)
    return state


def _complete_run_assertions() -> dict[str, bool]:
    return {
        "runner_local_raw_persistence": False,
        "runner_local_raw_persistence_corroborated": True,
        "held_out_outcome_use": False,
        "held_out_outcome_use_corroborated": True,
    }


def _envelope(
    state: dict[str, Any],
    grouped: dict[str, list[dict[str, Any]]],
    *,
    provenance_mode: str,
) -> dict[str, Any]:
    scorer = state["scorer"]
    profile = state["profile"]
    return {
        "schema_version": "8.0",
        "evaluation_mode": "qualification",
        "provenance_mode": provenance_mode,
        "binding": state["binding"],
        "execution_contract": profile["execution_contract"],
        "schedule": {
            "seed": SCHEDULE_SEED,
            "digest": state["schedule_digest"],
            "presentations": state["schedule"],
        },
        "complete_run_assertions": _complete_run_assertions(),
        "conditions": [
            {
                "id": condition,
                "digest": scorer._condition_digest(profile, condition),
                "observations": grouped[condition],
            }
            for condition in ("current", "reduced")
        ],
    }


def zero_model_score_preflight(state: dict[str, Any]) -> None:
    """Score the exact 40x2 production resolver path before Codex or index use."""
    scorer = state["scorer"]
    resolver = state["resolver"]
    profile = state["profile"]
    grouped: dict[str, list[dict[str, Any]]] = {"current": [], "reduced": []}
    for slot in state["schedule"]:
        case = state["cases"].get(slot["case_id"])
        if not isinstance(case, dict):
            raise PreflightError("zero-model case unavailable")
        try:
            graph = resolver.validate_graph_output(
                case.get("expected_semantic_output"),
                profile["protocol"],
                profile["selector_schema"],
            )
            parent = resolver.resolve_graph(
                case["task_text"],
                graph,
                profile["protocol"],
                profile["reference_policy"],
                profile["base_manifest"],
            )
        except Exception as error:
            raise PreflightError("zero-model resolution unavailable") from error
        grouped[slot["condition"]].append(
            _observation(
                state,
                case,
                slot["condition"],
                slot["presentation_index"],
                f"zero-model-{slot['presentation_index']}",
                semantic_output=graph,
                parent_derivation=parent,
            )
        )
    try:
        result = scorer.score_synthetic(
            _envelope(state, grouped, provenance_mode="synthetic"),
            profile,
        )
        scorer.validate_result(result)
    except Exception as error:
        raise PreflightError("zero-model scorer unavailable") from error
    if result.get("status") != "pass":
        raise PreflightError("zero-model scorer rejected production projection")


def _validated_auth_source() -> tuple[Path, os.stat_result]:
    configured = os.environ.get("CODEX_HOME")
    if configured is None:
        base = Path.home() / ".codex"
    else:
        base = Path(configured)
        if not base.is_absolute():
            raise PreflightError("Codex auth source configuration unavailable")
    source = base / "auth.json"
    try:
        metadata = source.lstat()
    except OSError as error:
        raise PreflightError("Codex auth source unavailable") from error
    mode = stat.S_IMODE(metadata.st_mode)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or source.is_symlink()
        or metadata.st_uid != os.getuid()
        or mode != 0o600
        or metadata.st_nlink != 1
        or metadata.st_size <= 0
    ):
        raise PreflightError("Codex auth source is not owner-only")
    return source, metadata


def _auth_fingerprint(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _explicit_codex_env(home: Path) -> dict[str, str]:
    allowed = (
        "PATH",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TMPDIR",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
    )
    environment = {key: os.environ[key] for key in allowed if key in os.environ}
    environment["HOME"] = str(home)
    environment["CODEX_HOME"] = str(home)
    return environment


@contextmanager
def _isolated_codex_home(source: Path, source_metadata: os.stat_result) -> Iterator[dict[str, str]]:
    temporary = tempfile.TemporaryDirectory(prefix="aq8-codex-home-")
    home = Path(temporary.name)
    try:
        os.chmod(home, 0o700)
        home_metadata = home.lstat()
        if (
            not stat.S_ISDIR(home_metadata.st_mode)
            or home.is_symlink()
            or home_metadata.st_uid != os.getuid()
            or stat.S_IMODE(home_metadata.st_mode) != 0o700
        ):
            raise PreflightError("isolated Codex home unavailable")
        current_source, current_metadata = _validated_auth_source()
        if current_source != source or _auth_fingerprint(current_metadata) != _auth_fingerprint(source_metadata):
            raise PreflightError("Codex auth source changed before isolation")
        destination = home / "auth.json"
        shutil.copyfile(source, destination, follow_symlinks=False)
        os.chmod(destination, 0o600)
        after_metadata = source.lstat()
        copied_metadata = destination.lstat()
        if (
            _auth_fingerprint(after_metadata) != _auth_fingerprint(source_metadata)
            or not stat.S_ISREG(copied_metadata.st_mode)
            or destination.is_symlink()
            or copied_metadata.st_uid != os.getuid()
            or stat.S_IMODE(copied_metadata.st_mode) != 0o600
            or copied_metadata.st_nlink != 1
            or copied_metadata.st_size != source_metadata.st_size
            or {path.name for path in home.iterdir()} != {"auth.json"}
        ):
            raise PreflightError("isolated Codex auth copy unavailable")
        yield _explicit_codex_env(home)
    finally:
        temporary.cleanup()
        if home.exists():
            raise PreflightError("isolated Codex home cleanup unavailable")


def _exact_isolation_probe(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        return False
    message = value[0]
    if set(message) != {
        "id",
        "type",
        "role",
        "content",
        "internal_chat_message_metadata_passthrough",
    }:
        return False
    metadata = message.get("internal_chat_message_metadata_passthrough")
    content = message.get("content")
    return (
        isinstance(message.get("id"), str)
        and bool(message["id"])
        and message.get("type") == "message"
        and message.get("role") == "user"
        and isinstance(metadata, dict)
        and set(metadata) == {"turn_id"}
        and isinstance(metadata.get("turn_id"), str)
        and bool(metadata["turn_id"])
        and isinstance(content, list)
        and len(content) == 1
        and isinstance(content[0], dict)
        and set(content[0]) == {"type", "text"}
        and content[0].get("type") == "input_text"
        and content[0].get("text") == ISOLATION_PROBE
    )


def codex_preflight(
    codex: str,
    probe: Callable[..., Any] = subprocess.run,
) -> dict[str, str]:
    resolved = Path(codex).resolve() if Path(codex).is_absolute() else (
        Path(shutil.which(codex)).resolve() if shutil.which(codex) else None
    )
    if resolved is None or not resolved.is_file():
        raise PreflightError("codex unavailable")
    auth_source, auth_metadata = _validated_auth_source()
    with _isolated_codex_home(auth_source, auth_metadata) as environment:
        version = probe(
            [str(resolved), "--version"],
            env=environment,
            capture_output=True,
            text=True,
        )
        help_result = probe(
            [str(resolved), "exec", "--help"],
            env=environment,
            capture_output=True,
            text=True,
        )
        help_text = (help_result.stdout or "") + (help_result.stderr or "")
        required = (
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--strict-config",
            "--skip-git-repo-check",
            "--sandbox",
            "--output-schema",
            "--json",
        )
        if version.returncode or help_result.returncode or any(flag not in help_text for flag in required):
            raise PreflightError("codex capability unavailable")
        version_text = version.stdout.strip()
        if re.fullmatch(r"codex-cli 0\.147\.\d+", version_text) is None:
            raise PreflightError("codex 0.147 lifecycle unavailable")
        info = {
            "id": "codex-cli",
            "path": str(resolved),
            "version": version_text,
            "digest": sha256_file(resolved),
        }
        argv = [
            str(resolved),
            "--ask-for-approval",
            "never",
            "--model",
            MODEL,
            "--sandbox",
            "read-only",
        ]
        for feature in DISABLED_FEATURES:
            argv.extend(["--disable", feature])
        for override in CONFIG_OVERRIDES:
            argv.extend(["-c", override])
        argv.extend(["debug", "prompt-input", ISOLATION_PROBE])
        with tempfile.TemporaryDirectory(prefix="aq8-prompt-isolation-") as directory:
            if any(Path(directory).iterdir()):
                raise PreflightError("Codex prompt probe cwd unavailable")
            rendered = probe(
                argv,
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
            )
    if rendered.returncode or rendered.stderr:
        raise PreflightError("codex isolation preflight unavailable")
    try:
        prompt = _json_loads_closed(rendered.stdout)
    except (TypeError, json.JSONDecodeError, ValueError) as error:
        raise PreflightError("codex isolation preflight unavailable") from error
    if not _exact_isolation_probe(prompt):
        raise PreflightError("codex isolation preflight unavailable")
    return info


def child_argv(info: dict[str, str], schema: Path) -> list[str]:
    argv = [
        info["path"],
        "--ask-for-approval",
        "never",
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--strict-config",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--model",
        MODEL,
        "--output-schema",
        str(schema),
        "--color",
        "never",
        "--json",
    ]
    for feature in DISABLED_FEATURES:
        argv.extend(["--disable", feature])
    for override in CONFIG_OVERRIDES:
        argv.extend(["-c", override])
    return [*argv, "-"]


def _stream_completion_markers(raw: bytes) -> tuple[bool, str | None]:
    """Conservatively detect completed content even across an earlier bad line."""
    completed = False
    context: str | None = None
    for line in raw.splitlines():
        try:
            event = _json_loads_closed(line)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            continue
        if not isinstance(event, dict):
            continue
        if (
            context is None
            and event.get("type") == "thread.started"
            and isinstance(event.get("thread_id"), str)
            and event["thread_id"]
        ):
            context = event["thread_id"]
        item = event.get("item")
        if (
            event.get("type") == "item.completed"
            and isinstance(item, dict)
            and item.get("type") == "agent_message"
        ):
            completed = True
    return completed, context


def parse_events(
    raw: bytes,
    resolver: Any,
    profile: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    """Accept only the Codex 0.147 lifecycle and one completed agent message."""
    context: str | None = None
    completed: list[str] = []
    turn_started = False
    turn_completed = False
    completed_anywhere, fallback_context = _stream_completion_markers(raw)
    for line in raw.splitlines():
        try:
            event = _json_loads_closed(line)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            if completed_anywhere:
                raise _completed_invalid(
                    "postcompletion event stream invalid",
                    context or fallback_context,
                ) from error
            raise TransportError("malformed event stream") from error
        if not isinstance(event, dict):
            if completed_anywhere:
                raise _completed_invalid(
                    "postcompletion event stream invalid",
                    context or fallback_context,
                )
            raise TransportError("event stream unavailable")
        kind = event.get("type")
        if kind == "thread.started":
            if (
                set(event) != {"type", "thread_id"}
                or not isinstance(event.get("thread_id"), str)
                or not event["thread_id"]
                or context is not None
                or turn_started
                or turn_completed
                or completed
            ):
                if completed_anywhere:
                    raise _completed_invalid(
                        "postcompletion lifecycle invalid",
                        context or fallback_context,
                    )
                raise TransportError("context unavailable")
            context = event["thread_id"]
            continue
        if kind == "turn.started":
            if not context or set(event) != {"type"} or turn_started or turn_completed:
                raise _completed_invalid("lifecycle extension", context)
            turn_started = True
            continue
        if kind == "turn.completed":
            if (
                not context
                or set(event) - {"type", "usage"}
                or not turn_started
                or turn_completed
            ):
                raise _completed_invalid("lifecycle extension", context)
            turn_completed = True
            continue
        if kind in {"turn.failed", "error"}:
            if completed_anywhere:
                raise _completed_invalid(
                    "postcompletion provider failure",
                    context or fallback_context,
                )
            raise TransportError("provider turn unavailable")
        item = event.get("item")
        if kind in {"item.started", "item.updated", "item.completed"} and (
            not context or not turn_started or turn_completed
        ):
            raise _completed_invalid("lifecycle extension", context)
        if (
            kind in {"item.started", "item.updated", "item.completed"}
            and isinstance(item, dict)
            and item.get("type") == "reasoning"
        ):
            continue
        if (
            kind in {"item.started", "item.updated"}
            and isinstance(item, dict)
            and item.get("type") == "agent_message"
        ):
            continue
        completed_agent_message = (
            kind == "item.completed"
            and isinstance(item, dict)
            and set(item) == {"id", "type", "text"}
            and item.get("type") == "agent_message"
            and isinstance(item.get("id"), str)
            and bool(item["id"].strip())
            and isinstance(item.get("text"), str)
            and bool(item["text"].strip())
        )
        if not completed_agent_message:
            item_type = item.get("type") if isinstance(item, dict) else ""
            effect = item_type in {"effect", "approval"}
            tool = item_type in {
                "tool_call",
                "mcp_tool_call",
                "command_execution",
                "file_change",
            }
            flags = _empty_events()
            flags.update(
                {
                    "effect_requested": effect,
                    "effect_granted": effect,
                    "claim_requested": item_type == "approval",
                    "claim_granted": item_type == "approval",
                    "tool_requested": tool,
                    "tool_granted": tool,
                }
            )
            raise _completed_invalid("prohibited or unknown event", context, events=flags)
        completed.append(item["text"])
    if not context or not turn_started or not turn_completed:
        if completed_anywhere:
            raise _completed_invalid(
                "postcompletion lifecycle incomplete",
                context or fallback_context,
            )
        raise TransportError("incomplete event stream")
    if len(completed) != 1:
        raise _completed_invalid("completed response count invalid", context)
    try:
        value = _json_loads_closed(completed[0])
    except (json.JSONDecodeError, ValueError) as error:
        raise _completed_invalid("completed graph output malformed", context) from error
    try:
        graph = resolver.validate_graph_output(
            value,
            profile["protocol"],
            profile["selector_schema"],
        )
    except Exception as error:
        raise _completed_invalid("completed graph output invalid", context) from error
    if not isinstance(graph, dict):
        raise _completed_invalid("completed graph output invalid", context)
    return graph, context


def _execution_byte_preflight(
    info: dict[str, str],
    *,
    root: Path,
    commit: str,
    state: dict[str, Any],
) -> Path:
    require_exact_live_head(root, commit)
    executable = Path(info["path"])
    try:
        digest = sha256_file(executable)
    except OSError as error:
        raise PreflightError("resolved executable unavailable") from error
    if digest != info.get("digest"):
        raise PreflightError("resolved executable drift")
    return _runtime_graph_schema_path(root, commit, state["profile"], state["checker"])


def _invoke(
    info: dict[str, str],
    packet: dict[str, Any],
    *,
    root: Path,
    commit: str,
    state: dict[str, Any],
    invoke: Callable[..., Any],
    on_raw: Callable[[], None] | None = None,
) -> tuple[dict[str, Any], str]:
    schema = _execution_byte_preflight(info, root=root, commit=commit, state=state)
    auth_source, auth_metadata = _validated_auth_source()
    encoded = json.dumps(packet, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    with _isolated_codex_home(auth_source, auth_metadata) as environment:
        with tempfile.TemporaryDirectory(prefix="aq8-isolated-") as directory:
            if any(Path(directory).iterdir()):
                raise PreflightError("isolated cwd unavailable")
            try:
                result = invoke(
                    child_argv(info, schema),
                    cwd=directory,
                    env=environment,
                    input=encoded,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
            except OSError as error:
                raise LaunchError("child launch unavailable") from error
    if result.returncode and not result.stdout:
        raise TransportError("child transport unavailable")
    if result.stdout and on_raw is not None:
        on_raw()
    graph, context = parse_events(result.stdout or b"", state["resolver"], state["profile"])
    if result.returncode:
        raise _completed_invalid("completed graph exited nonzero", context)
    return graph, context


def _canary_graph() -> dict[str, Any]:
    slots = ("s0", "s1", "s2", "s3")
    pairs = (
        ("s0", "s1"),
        ("s0", "s2"),
        ("s0", "s3"),
        ("s1", "s2"),
        ("s1", "s3"),
        ("s2", "s3"),
    )
    return {
        "candidate_states": [
            {"slot_id": slot, "state": "resolved_or_absent"} for slot in slots
        ],
        "pairwise_relations": [
            {"left_slot": left, "right_slot": right, "relation": "unrelated"}
            for left, right in pairs
        ],
        "reference_needs": [{"slot_id": slot, "need": "none"} for slot in slots],
    }


def _canary_packet(state: dict[str, Any]) -> dict[str, Any]:
    task = (
        "This isolated transport check has no remaining architecture, task-contract, "
        "verification, or engineering-learning decision. Each anonymous candidate is "
        "resolved or absent, and no supporting reference is needed."
    )
    resolver = state["resolver"]
    profile = state["profile"]
    current = resolver.build_condition_packet(profile["adapter"], "current", task)
    reduced = resolver.build_condition_packet(profile["adapter"], "reduced", task)
    _validate_packet_pair(current, reduced)
    return current


def _canary_preflight(state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    packet = _canary_packet(state)
    expected = state["resolver"].validate_graph_output(
        _canary_graph(),
        state["profile"]["protocol"],
        state["profile"]["selector_schema"],
    )
    parent = state["resolver"].resolve_graph(
        packet["task_text"],
        expected,
        state["profile"]["protocol"],
        state["profile"]["reference_policy"],
        state["profile"]["base_manifest"],
    )
    expected_fields = {
        "graph_status": "valid",
        "automatic_selection_status": "automatic",
        "selection_status": "automatic",
        "root_slots": [],
        "selected_slots": [],
        "reference_requests": [],
        "reference_uncertain_slots": [],
    }
    if any(parent.get(key) != value for key, value in expected_fields.items()):
        raise PreflightError("canary parent resolution unavailable")
    return packet, expected


def _validate_canary_result(
    graph: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    if graph != expected:
        raise CompletedInvalid("canary graph mismatch")


def _unconsumed_marker(root: Path, corpus_commit: str) -> str:
    expected = f"AQ8-RUN-AUTHORITY corpus={corpus_commit} status=unconsumed"
    try:
        lines = [
            line
            for line in (root / "EXECPLAN.md").read_text(encoding="utf-8").splitlines()
            if line.startswith(f"AQ8-RUN-AUTHORITY corpus={corpus_commit} ")
        ]
    except OSError as error:
        raise PreflightError("authority marker unavailable") from error
    if lines != [expected]:
        raise PreflightError("authority marker unavailable")
    return expected


def run_canary(
    *,
    root: Path,
    candidate_commit: str,
    codex: str,
    invoke: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    state = preflight(root, candidate_commit)
    info = codex_preflight(codex)
    state["binding"] = binding_from_profile(
        state["profile"],
        cli=info,
        schedule_digest=state["schedule_digest"],
    )
    state["index_module"].normalize_binding(state["binding"])
    _execution_byte_preflight(info, root=root, commit=state["commit"], state=state)
    marker = _unconsumed_marker(root, state["binding"]["corpus"]["commit"])
    packet, expected = _canary_preflight(state)
    index = state["index_module"].AQ8RunIndex(root)
    cap = index.begin_canary(state["binding"], unconsumed_marker=marker)
    for attempt in range(2):
        try:
            graph, _context = _invoke(
                info,
                packet,
                root=root,
                commit=state["commit"],
                state=state,
                invoke=invoke,
            )
            _validate_canary_result(graph, expected)
            index.complete_canary(
                state["binding"],
                unconsumed_marker=marker,
                canary_cap=cap,
            )
            return receipt("canary", "passed", state, live_calls=attempt + 1)
        except InfrastructureError:
            if attempt == 0:
                index.retry_canary(
                    state["binding"],
                    unconsumed_marker=marker,
                    canary_cap=cap,
                    reason="precompletion_infrastructure",
                )
                continue
            index.fail_canary(
                state["binding"],
                unconsumed_marker=marker,
                canary_cap=cap,
                reason="retry_exhausted",
            )
            raise
        except Exception:
            index.fail_canary(
                state["binding"],
                unconsumed_marker=marker,
                canary_cap=cap,
                reason="malformed_or_content_failure",
            )
            raise
    raise AssertionError("unreachable")


def _observation(
    state: dict[str, Any],
    case: dict[str, Any],
    condition: str,
    presentation_index: int,
    context: str,
    *,
    semantic_output: dict[str, Any] | None,
    parent_derivation: dict[str, Any] | None,
) -> dict[str, Any]:
    scorer = state["scorer"]
    profile = state["profile"]
    if semantic_output is None:
        parent_derivation = None
    if semantic_output is not None and not isinstance(parent_derivation, dict):
        raise PreflightError("resolver observation unavailable")
    return {
        "case_id": case["case_id"],
        "presentation_index": presentation_index,
        "context_id": context,
        "terminal_completed": True,
        "case_sha256": scorer._expected_case_digest(case, "case"),
        "task_sha256": scorer._expected_case_digest(case, "task"),
        "packet_sha256": scorer._packet_digest(profile, condition, case),
        "condition_sha256": scorer._condition_digest(profile, condition),
        "execution_sha256": scorer._profile_execution_digest(profile),
        "runner_sha256": state["binding"]["runner"]["digest"],
        "parse_status": "parsed" if semantic_output is not None else "malformed",
        "semantic_output": semantic_output,
        "parent_derivation": parent_derivation,
        "events": _empty_events(),
    }


def _packet_for_slot(state: dict[str, Any], slot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    condition = slot.get("condition")
    case = state["cases"].get(slot.get("case_id"))
    if condition not in {"current", "reduced"} or not isinstance(case, dict):
        raise PreflightError("schedule case unavailable")
    task = case.get("task_text")
    if not isinstance(task, str) or not task:
        raise PreflightError("schedule task unavailable")
    resolver = state["resolver"]
    packet = resolver.build_condition_packet(state["profile"]["adapter"], condition, task)
    other = resolver.build_condition_packet(
        state["profile"]["adapter"],
        "reduced" if condition == "current" else "current",
        task,
    )
    _validate_packet_pair(packet, other)
    return case, packet


def execute_trials(
    *,
    root: Path,
    candidate_commit: str,
    codex: str,
    invoke: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    state = preflight(root, candidate_commit)
    info = codex_preflight(codex)
    state["binding"] = binding_from_profile(
        state["profile"],
        cli=info,
        schedule_digest=state["schedule_digest"],
    )
    state["index_module"].normalize_binding(state["binding"])
    _execution_byte_preflight(info, root=root, commit=state["commit"], state=state)
    marker = _unconsumed_marker(root, state["binding"]["corpus"]["commit"])
    session = state["scorer"].create_live_score_session(state["profile"], state["binding"])
    grouped: dict[str, list[dict[str, Any]]] = {"current": [], "reduced": []}
    first_case, first_packet = _packet_for_slot(state, state["schedule"][0])
    index = state["index_module"].AQ8RunIndex(root)
    # No canary is invoked here.  The index accepts only the previously passed
    # canary for this exact binding and consumes corpus custody immediately.
    cap = index.begin_batch(state["binding"], unconsumed_marker=marker)
    try:
        for presentation_index, slot in enumerate(state["schedule"]):
            if presentation_index == 0:
                case, packet = first_case, first_packet
            else:
                case, packet = _packet_for_slot(state, slot)
            condition = slot["condition"]
            index.presentation_started(state["binding"], batch_cap=cap)
            try:
                graph, context = _invoke(
                    info,
                    packet,
                    root=root,
                    commit=state["commit"],
                    state=state,
                    invoke=invoke,
                    on_raw=(
                        lambda: index.response_observed(state["binding"], batch_cap=cap)
                    ) if presentation_index == 0 else None,
                )
                try:
                    parent = state["resolver"].resolve_graph(
                        case["task_text"],
                        graph,
                        state["profile"]["protocol"],
                        state["profile"]["reference_policy"],
                        state["profile"]["base_manifest"],
                    )
                except Exception as error:
                    raise _completed_invalid(
                        "completed parent resolution invalid",
                        context,
                    ) from error
                observation = _observation(
                    state,
                    case,
                    condition,
                    presentation_index,
                    context,
                    semantic_output=graph,
                    parent_derivation=parent,
                )
            except CompletedInvalid as error:
                context = getattr(error, "context", None)
                if not isinstance(context, str) or not context:
                    raise TransportError("completed content lacked context")
                observation = _observation(
                    state,
                    case,
                    condition,
                    presentation_index,
                    context,
                    semantic_output=None,
                    parent_derivation=None,
                )
                events = getattr(error, "events", None)
                if not isinstance(events, dict) or tuple(events) != EVENT_KEYS or any(
                    not isinstance(value, bool) for value in events.values()
                ):
                    raise PreflightError("completed event surface unavailable")
                observation["events"] = events
            grouped[condition].append(observation)
            index.presentation_completed(state["binding"], batch_cap=cap)
        result = session.score(_envelope(state, grouped, provenance_mode="live_runner"))
        state["scorer"].validate_result(result)
        if result.get("status") == "insufficient_data":
            raise PreflightError("live score custody unavailable")
        aggregate = result.get("aggregate_digest")
        if not isinstance(aggregate, str) or not HEX64.fullmatch(aggregate):
            raise PreflightError("aggregate digest unavailable")
        status = "passed" if result.get("status") == "pass" else "failed"
        index.complete_batch(
            state["binding"],
            batch_cap=cap,
            status=status,
            aggregate_digest=aggregate,
        )
        return receipt("execute", status, state, live_calls=80, aggregate_digest=aggregate)
    except Exception:
        try:
            index.mark_batch_ambiguous(
                state["binding"],
                batch_cap=cap,
                reason="infrastructure_interrupted",
            )
        except Exception:
            pass
        raise


def receipt(
    mode: str,
    status: str,
    state: dict[str, Any],
    *,
    live_calls: int,
    aggregate_digest: str | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "mode": mode,
        "status": status,
        "candidate": {"commit": state["commit"], "tree": state["tree"]},
        "presentations": 80 if mode == "execute" else 0,
        "live_calls": live_calls,
        "runner_local_raw_trajectories_persisted": False,
        "provider_raw_trajectory_retention_status": "unknown",
        "runtime_provenance_proven": False,
        "provider_identity_proven": False,
        "model_behavior_proven": False,
        "sandbox_proven": False,
        "product_behavior_proven": False,
        "promotion_eligible": False,
    }
    if aggregate_digest is not None:
        value["aggregate_digest"] = aggregate_digest
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--canary", action="store_true")
    modes.add_argument("--execute", action="store_true")
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--usage-approval", default="")
    parser.add_argument("--codex", default="codex")
    args = parser.parse_args(argv)
    if (args.canary or args.execute) and args.usage_approval != APPROVAL:
        parser.error("live AQ8 requires exact usage approval")
    if not HEX40.fullmatch(args.candidate_commit):
        parser.error("candidate commit must be lowercase forty-hex")
    try:
        if args.dry_run:
            state = preflight(ROOT, args.candidate_commit)
            result = receipt("dry-run", "passed", state, live_calls=0)
        elif args.canary:
            result = run_canary(
                root=ROOT,
                candidate_commit=args.candidate_commit,
                codex=args.codex,
            )
        else:
            result = execute_trials(
                root=ROOT,
                candidate_commit=args.candidate_commit,
                codex=args.codex,
            )
    except Exception:
        print(
            json.dumps(
                {
                    "mode": "hold",
                    "status": "hold",
                    "runner_local_raw_trajectories_persisted": False,
                    "provider_raw_trajectory_retention_status": "unknown",
                    "runtime_provenance_proven": False,
                    "provider_identity_proven": False,
                    "model_behavior_proven": False,
                    "sandbox_proven": False,
                    "product_behavior_proven": False,
                    "promotion_eligible": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
