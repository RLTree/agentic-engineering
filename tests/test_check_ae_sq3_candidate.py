from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_ae_sq3_candidate as checker  # noqa: E402


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sealed(commit: str, tree: str, path: str, blob: str, raw: bytes) -> dict[str, str]:
    return {
        "commit": commit,
        "tree": tree,
        "path": path,
        "blob": blob,
        "sha256": sha256(raw),
    }


def valid_freeze(
    *,
    f1a: str = "a" * 40,
    f1a_tree: str = "b" * 40,
    authority_commit: str | None = None,
    authority_tree: str = "c" * 40,
    authority_blob: str = "d" * 40,
    authority_raw: bytes = b"authority",
    diagnosis_commit: str | None = None,
    diagnosis_tree: str = "e" * 40,
    diagnosis_blob: str = "f" * 40,
    diagnosis_raw: bytes = b"diagnosis",
    role_rows: list[dict[str, str]] | None = None,
) -> dict:
    if role_rows is None:
        role_rows = [
            {
                "role": role,
                "path": path,
                "blob": f"{index + 1:040x}",
                "sha256": f"{index + 1:064x}",
            }
            for index, (role, path) in enumerate(checker.ROLE_PATHS)
        ]
    return {
        "schema_version": "ae-sq3-repaired-freeze-v1",
        "program_id": "AE-SQ3",
        "candidate_id": "AE-SQ3-SLEC-3",
        "mechanism_id": "SLEC-3",
        "authority_bindings": {
            "program_authority": sealed(
                authority_commit or checker.AUTHORITY_COMMIT,
                authority_tree,
                checker.AUTHORITY_PATH,
                authority_blob,
                authority_raw,
            ),
            "bounded_sq2_diagnosis": sealed(
                diagnosis_commit or checker.DIAGNOSTIC_COMMIT,
                diagnosis_tree,
                checker.DIAGNOSTIC_PATH,
                diagnosis_blob,
                diagnosis_raw,
            ),
        },
        "implementation_freeze": {"commit": f1a, "tree": f1a_tree},
        "role_order": list(checker.ROLE_ORDER),
        "files": role_rows,
        "runtime": {
            "cli": {
                "id": "codex-cli",
                "version": "codex-cli 0.147.0",
                "sha256": "19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37",
            },
            "model": "gpt-5.5",
            "reasoning": "medium",
            "fallback": False,
            "sandbox": "read-only",
            "approval_policy": "never",
            "ephemeral": True,
            "strict_isolation": True,
        },
        "qualification": {
            "f3_preflight_attempts": 1,
            "f3_model_calls": 0,
            "canary_calls": 4,
            "conditional_batch_presentations": 80,
            "calls_per_presentation": 4,
            "conditional_batch_calls": 320,
            "hard_call_ceiling": 324,
            "retry_calls": 0,
            "same_process_canary_then_batch": True,
            "standalone_canary_or_resume": False,
            "global_and": True,
        },
        "durable_state": {
            "directory": ".git-common-dir/.ae-sq3-one-shot",
            "path": ".git-common-dir/.ae-sq3-one-shot/state.json",
            "schema_version": "ae-sq3-one-shot-run-index-v1",
            "top_level_keys": [
                "binding",
                "custody_key",
                "program_id",
                "record_sha256",
                "schema_version",
                "state_sha256",
                "status",
            ],
            "binding_keys": [
                "corpus_manifest_sha256",
                "f1_freeze_sha256",
                "preflight_record_sha256",
                "program_authority_sha256",
                "run_manifest_sha256",
            ],
            "statuses": ["claimed", "completed", "invalid"],
            "claim_before_first_canary_child": True,
            "crash_is_terminal": True,
            "reset_delete_retry_reopen_or_replacement": False,
        },
        "privacy": {
            "raw_persistence": False,
            "subaggregate_persistence": False,
            "aggregate_only_projection": True,
            "private_runtime_snapshot": True,
            "private_child_tmp_cleanup_required": True,
        },
    }


def git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write(repository: Path, relative: str, raw: bytes) -> None:
    path = repository / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def build_freeze_repository(repository: Path, *, sibling_refreeze: bool) -> tuple[str, str, str]:
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    git(repository, "config", "user.email", "sq3-tests@example.invalid")
    git(repository, "config", "user.name", "AE SQ3 Tests")

    authority_raw = json.dumps(
        {
            "program_id": "AE-SQ3",
            "authority_status": "F0_INITIAL_AUTHORITY_CLOSED",
            "imported_diagnosis": {"classification_counts": {"schema_unsupported": 4}},
        },
        sort_keys=True,
    ).encode()
    diagnosis_raw = b'{"mode":"diagnostic","program_id":"AE-SQ2"}'
    write(repository, checker.AUTHORITY_PATH, authority_raw)
    write(repository, checker.DIAGNOSTIC_PATH, diagnosis_raw)
    git(repository, "add", "--all")
    git(repository, "commit", "-q", "-m", "F0")
    f0 = git(repository, "rev-parse", "HEAD")
    f0_tree = git(repository, "rev-parse", "HEAD^{tree}")

    role_raw: dict[str, bytes] = {}
    for role, path in checker.ROLE_PATHS:
        raw = b"{}" if path.endswith(".json") else f"# {role}\n".encode()
        role_raw[path] = raw
        write(repository, path, raw)
    git(repository, "add", "--all")
    git(repository, "commit", "-q", "-m", "F1A")
    f1a = git(repository, "rev-parse", "HEAD")
    f1a_tree = git(repository, "rev-parse", "HEAD^{tree}")
    role_rows = [
        {
            "role": role,
            "path": path,
            "blob": git(repository, "rev-parse", f"{f1a}:{path}"),
            "sha256": sha256(role_raw[path]),
        }
        for role, path in checker.ROLE_PATHS
    ]
    freeze = valid_freeze(
        f1a=f1a,
        f1a_tree=f1a_tree,
        authority_commit=f0,
        authority_tree=f0_tree,
        authority_blob=git(repository, "rev-parse", f"{f0}:{checker.AUTHORITY_PATH}"),
        authority_raw=authority_raw,
        diagnosis_commit=f0,
        diagnosis_tree=f0_tree,
        diagnosis_blob=git(repository, "rev-parse", f"{f0}:{checker.DIAGNOSTIC_PATH}"),
        diagnosis_raw=diagnosis_raw,
        role_rows=role_rows,
    )
    freeze_raw = json.dumps(freeze, sort_keys=True, separators=(",", ":")).encode()
    write(repository, checker.FREEZE_PATH, freeze_raw)
    git(repository, "add", checker.FREEZE_PATH)
    git(repository, "commit", "-q", "-m", "F1B")
    f1b = git(repository, "rev-parse", "HEAD")
    if sibling_refreeze:
        git(repository, "switch", "-q", "-c", "forbidden-refreeze", f1a)
        write(repository, checker.FREEZE_PATH, freeze_raw)
        git(repository, "add", checker.FREEZE_PATH)
        git(repository, "commit", "-q", "-m", "second F1B")
        git(repository, "switch", "-q", "--detach", f1b)
    return f0, f1a, f1b


def actual_semantic_fixture() -> tuple[dict[str, dict], dict[str, bytes]]:
    documents: dict[str, dict] = {}
    raw_roles: dict[str, bytes] = {}
    for role, path in checker.ROLE_PATHS:
        raw = (ROOT / path).read_bytes()
        raw_roles[role] = raw
        if path.endswith(".json"):
            documents[role] = json.loads(raw)
    return documents, raw_roles


class CandidateCheckerTests(unittest.TestCase):
    def test_freeze_contract_is_exact_closed_and_ordered(self) -> None:
        value = valid_freeze()
        self.assertEqual(checker._validate_freeze(value)["candidate_id"], "AE-SQ3-SLEC-3")
        mutations = []
        for path, replacement in (
            (("program_id",), "AE-SQ2"),
            (("implementation_freeze", "commit"), "A" * 40),
            (("role_order", 0), "other"),
            (("files", 0, "path"), "../escape"),
            (("runtime", "fallback"), True),
            (("qualification", "retry_calls"), 1),
            (("qualification", "same_process_canary_then_batch"), False),
            (("durable_state", "statuses"), ["claimed", "completed"]),
            (("privacy", "raw_persistence"), True),
        ):
            changed = copy.deepcopy(value)
            target = changed
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = replacement
            mutations.append(("/".join(map(str, path)), changed))
        extra = copy.deepcopy(value)
        extra["later_override"] = True
        mutations.append(("extra", extra))
        omitted = copy.deepcopy(value)
        omitted["files"].pop()
        mutations.append(("omitted-role", omitted))
        reordered = copy.deepcopy(value)
        reordered["files"][0], reordered["files"][1] = (
            reordered["files"][1],
            reordered["files"][0],
        )
        mutations.append(("reordered-role", reordered))
        for label, changed in mutations:
            with self.subTest(label=label), self.assertRaises(checker.CandidateError):
                checker._validate_freeze(changed)

    def test_cross_document_paths_hashes_formulas_and_public_schema_are_bound(self) -> None:
        documents, raw_roles = actual_semantic_fixture()
        checker._validate_role_semantics(documents, raw_roles)
        mutations: list[tuple[str, dict[str, dict]]] = []
        for label, mutate in (
            (
                "resolution-digest",
                lambda value: value["candidate_authority"]["resolution_contract"].__setitem__(
                    "schema_sha256", "0" * 64
                ),
            ),
            (
                "reference-path",
                lambda value: value["candidate_authority"]["reference_contract"].__setitem__(
                    "policy_path", "evals/ae-sq3/f1/other.json"
                ),
            ),
            (
                "formula-order",
                lambda value: value["metrics"]["formula_order"].pop(),
            ),
            (
                "public-status",
                lambda value: value["evaluator_schema"]["properties"]["status"].__setitem__(
                    "enum", ["PASS", "FAIL", "HOLD"]
                ),
            ),
        ):
            changed = copy.deepcopy(documents)
            mutate(changed)
            mutations.append((label, changed))
        for label, changed in mutations:
            with self.subTest(label=label), self.assertRaises(checker.CandidateError):
                checker._validate_role_semantics(changed, raw_roles)

    def test_f1a_json_role_cannot_smuggle_heldout_or_result_material(self) -> None:
        documents, raw_roles = actual_semantic_fixture()
        for key, value in (
            ("heldout_corpus", [{"task_text": "smuggled"}]),
            ("live_result", {"status": "PASS"}),
            ("model_event", {"type": "turn.completed"}),
        ):
            changed = copy.deepcopy(documents)
            changed["candidate_authority"][key] = value
            with self.subTest(key=key), self.assertRaises(checker.CandidateError):
                checker._validate_role_semantics(changed, raw_roles)

    def test_same_f1a_cannot_have_a_second_referenced_f1b(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repo"
            repository.mkdir()
            f0, _f1a, f1b = build_freeze_repository(
                repository, sibling_refreeze=True
            )
            with (
                patch.object(checker, "AUTHORITY_COMMIT", f0),
                patch.object(checker, "DIAGNOSTIC_COMMIT", f0),
                patch.object(checker, "_validate_role_semantics"),
                self.assertRaisesRegex(
                    checker.CandidateError, r"(?i)(unique|refreeze|sibling)"
                ),
            ):
                checker.load_verified_candidate(repository, f1b, require_live=False)

    def test_live_candidate_requires_clean_single_link_safe_mode_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repo"
            repository.mkdir()
            f0, _f1a, f1b = build_freeze_repository(
                repository, sibling_refreeze=False
            )
            target = repository / checker.ROLE_PATHS[0][1]
            os.chmod(target, 0o666)
            with (
                patch.object(checker, "AUTHORITY_COMMIT", f0),
                patch.object(checker, "DIAGNOSTIC_COMMIT", f0),
                patch.object(checker, "_validate_role_semantics"),
                self.assertRaisesRegex(
                    checker.CandidateError, r"(?i)(mode|writable|clean|live)"
                ),
            ):
                checker.load_verified_candidate(repository, f1b, require_live=True)

    def test_provisional_hashes_fail_closed_for_link_and_unsafe_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            relative = "role.json"
            target = repository / relative
            target.write_bytes(b"{}")
            with patch.object(checker, "ROLE_PATHS", (("role", relative),)):
                self.assertEqual(checker.provisional_hashes(repository)["role"], sha256(b"{}"))
                os.chmod(target, 0o666)
                self.assertEqual(checker.provisional_hashes(repository)["role"], "UNAVAILABLE")
                os.chmod(target, 0o644)
                os.link(target, repository / "alias")
                self.assertEqual(checker.provisional_hashes(repository)["role"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
