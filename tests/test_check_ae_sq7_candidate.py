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
import check_ae_sq7_candidate as checker  # noqa: E402


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
        "schema_version": "ae-sq7-repaired-freeze-v1",
        "program_id": "AE-SQ7",
        "candidate_id": "AE-SQ7-SLEC-7",
        "mechanism_id": "SLEC-7",
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
            "directory": ".git-common-dir/.ae-sq7-one-shot",
            "path": ".git-common-dir/.ae-sq7-one-shot/state.json",
            "schema_version": "ae-sq7-one-shot-run-index-v1",
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


def git_bytes(repository: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
    ).stdout


def historical(commit: str, path: str) -> bytes:
    return git_bytes(ROOT, "show", f"{commit}:{path}")


def write(repository: Path, relative: str, raw: bytes) -> None:
    path = repository / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def build_freeze_repository(
    repository: Path,
    *,
    sibling_refreeze: bool,
    real_roles: bool = False,
) -> tuple[str, str, str, str]:
    repository.rmdir()
    subprocess.run(
        ["git", "clone", "-q", "--no-checkout", str(ROOT), str(repository)],
        check=True,
    )
    git(repository, "config", "user.email", "sq7-tests@example.invalid")
    git(repository, "config", "user.name", "AE SQ7 Tests")
    git(repository, "checkout", "-q", "--detach", checker.AUTHORITY_COMMIT)

    d0 = checker.DIAGNOSTIC_COMMIT
    diagnosis_raw = git_bytes(repository, "show", f"{d0}:{checker.DIAGNOSTIC_PATH}")
    f0 = checker.AUTHORITY_COMMIT
    authority_raw = git_bytes(repository, "show", f"{f0}:{checker.AUTHORITY_PATH}")
    d0_tree = git(repository, "rev-parse", f"{d0}^{{tree}}")
    f0_tree = git(repository, "rev-parse", "HEAD^{tree}")

    role_raw: dict[str, bytes] = {}
    for role, path in checker.ROLE_PATHS:
        if real_roles:
            raw = (ROOT / path).read_bytes()
        else:
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
        diagnosis_commit=d0,
        diagnosis_tree=d0_tree,
        diagnosis_blob=git(repository, "rev-parse", f"{d0}:{checker.DIAGNOSTIC_PATH}"),
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
    return d0, f0, f1a, f1b


def actual_semantic_fixture() -> tuple[dict[str, dict], dict[str, bytes]]:
    documents: dict[str, dict] = {}
    raw_roles: dict[str, bytes] = {}
    for role, path in checker.ROLE_PATHS:
        raw = (ROOT / path).read_bytes()
        raw_roles[role] = raw
        if path.endswith(".json"):
            documents[role] = json.loads(raw)
    return documents, raw_roles


def reseal_diagnosis(value: dict, *, aggregate: bool = True) -> bytes:
    if aggregate:
        value["aggregate_sha256"] = sha256(checker.canonical_json(value["calls"]))
    unsigned = dict(value)
    unsigned.pop("record_sha256", None)
    value["record_sha256"] = sha256(checker.canonical_json(unsigned))
    return checker.canonical_json(value)


class CandidateCheckerTests(unittest.TestCase):
    def test_real_d0_shape_passes_full_git_fixture_f1b_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repo"
            repository.mkdir()
            d0, f0, f1a, f1b = build_freeze_repository(
                repository,
                sibling_refreeze=False,
                real_roles=True,
            )
            with (
                patch.object(checker, "AUTHORITY_COMMIT", f0),
                patch.object(checker, "DIAGNOSTIC_COMMIT", d0),
            ):
                profile = checker.load_verified_candidate(
                    repository, f1b, require_live=False
                )
            self.assertEqual(profile["implementation_commit"], f1a)
            self.assertEqual(profile["freeze_commit"], f1b)
            self.assertEqual(
                profile["manifest"]["authority_bindings"]["bounded_sq2_diagnosis"][
                    "commit"
                ],
                d0,
            )

    def test_bounded_diagnostic_identity_counts_usage_and_digests(self) -> None:
        raw = historical(checker.DIAGNOSTIC_COMMIT, checker.DIAGNOSTIC_PATH)
        original = json.loads(raw)
        checker._validate_diagnostic_record(ROOT, original, raw)

        mutations: list[tuple[str, str, dict, bytes]] = []

        identity = copy.deepcopy(original)
        identity["diagnostic_id"] = "AE-SQ2-D0-drift"
        mutations.append(
            ("identity", "closed schema", identity, reseal_diagnosis(identity))
        )

        mode = copy.deepcopy(original)
        mode["mode"] = "dry_run"
        mutations.append(("mode", "completion identity", mode, reseal_diagnosis(mode)))

        invented = copy.deepcopy(original)
        invented["program_id"] = "AE-SQ2"
        mutations.append(
            ("invented-program", "field closure", invented, reseal_diagnosis(invented))
        )

        classification = copy.deepcopy(original)
        classification["calls"][0]["classification"] = "process_exit"
        mutations.append(
            (
                "classification",
                "classification counts",
                classification,
                reseal_diagnosis(classification),
            )
        )

        started_count = copy.deepcopy(original)
        started_count["calls_started"] = 3
        mutations.append(
            (
                "count",
                "started-call count",
                started_count,
                reseal_diagnosis(started_count),
            )
        )

        probe_order = copy.deepcopy(original)
        probe_order["calls"][0], probe_order["calls"][1] = (
            probe_order["calls"][1],
            probe_order["calls"][0],
        )
        mutations.append(
            (
                "probe-order",
                "probe identity or order",
                probe_order,
                reseal_diagnosis(probe_order),
            )
        )

        usage = copy.deepcopy(original)
        usage["usage"]["input_tokens"] = 1
        usage["usage"]["total_tokens"] = 1
        mutations.append(("usage", "usage counters", usage, reseal_diagnosis(usage)))

        aggregate = copy.deepcopy(original)
        aggregate["aggregate_sha256"] = "0" * 64
        mutations.append(
            (
                "aggregate-digest",
                "aggregate digest",
                aggregate,
                reseal_diagnosis(aggregate, aggregate=False),
            )
        )

        record_digest = copy.deepcopy(original)
        record_digest["record_sha256"] = "0" * 64
        mutations.append(
            (
                "record-digest",
                "record digest",
                record_digest,
                checker.canonical_json(record_digest),
            )
        )

        for label, message, changed, changed_raw in mutations:
            with (
                self.subTest(label=label),
                self.assertRaisesRegex(checker.CandidateError, message),
            ):
                checker._validate_diagnostic_record(ROOT, changed, changed_raw)

    def test_f0_rejects_internally_resealed_classification_drift(self) -> None:
        diagnosis = json.loads(
            historical(checker.DIAGNOSTIC_COMMIT, checker.DIAGNOSTIC_PATH)
        )
        diagnosis["calls"][0]["classification"] = "process_exit"
        diagnosis["classification_counts"]["schema_unsupported"] = 3
        diagnosis["classification_counts"]["process_exit"] = 1
        changed_raw = reseal_diagnosis(diagnosis)

        baseline = valid_freeze(diagnosis_raw=changed_raw)
        manifest = {
            "authority_bindings": baseline["authority_bindings"],
            "runtime": baseline["runtime"],
        }
        with self.assertRaisesRegex(checker.CandidateError, "exact four-call"):
            checker._validate_bounded_diagnosis(ROOT, manifest, diagnosis, changed_raw)

    def test_freeze_contract_is_exact_closed_and_ordered(self) -> None:
        value = valid_freeze()
        self.assertEqual(
            checker._validate_freeze(value)["candidate_id"], "AE-SQ7-SLEC-7"
        )
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

    def test_cross_document_paths_hashes_formulas_and_public_schema_are_bound(
        self,
    ) -> None:
        documents, raw_roles = actual_semantic_fixture()
        checker._validate_role_semantics(documents, raw_roles)
        mutations: list[tuple[str, dict[str, dict]]] = []
        for label, mutate in (
            (
                "resolution-digest",
                lambda value: value["candidate_authority"][
                    "resolution_contract"
                ].__setitem__("schema_sha256", "0" * 64),
            ),
            (
                "reference-path",
                lambda value: value["candidate_authority"][
                    "reference_contract"
                ].__setitem__("policy_path", "evals/ae-sq7/f1/other.json"),
            ),
            (
                "formula-order",
                lambda value: value["metrics"]["formula_order"].pop(),
            ),
            (
                "public-status",
                lambda value: value["evaluator_schema"]["properties"][
                    "status"
                ].__setitem__("enum", ["PASS", "FAIL", "HOLD"]),
            ),
            (
                "selected-reference-gate",
                lambda value: value["author_template_gate_schema"]["required"].remove(
                    "selected_reference_anchor_gate"
                ),
            ),
        ):
            changed = copy.deepcopy(documents)
            mutate(changed)
            mutations.append((label, changed))
        for label, changed in mutations:
            with self.subTest(label=label), self.assertRaises(checker.CandidateError):
                checker._validate_role_semantics(changed, raw_roles)

        weakened_raw = dict(raw_roles)
        weakened_raw["runner"] = weakened_raw["runner"].replace(
            b"def _run_selected_reference_anchor_gate(",
            b"def _removed_selected_reference_anchor_gate(",
            1,
        )
        with self.assertRaises(checker.CandidateError):
            checker._validate_role_semantics(documents, weakened_raw)

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
            d0, f0, _f1a, f1b = build_freeze_repository(
                repository, sibling_refreeze=True
            )
            with (
                patch.object(checker, "AUTHORITY_COMMIT", f0),
                patch.object(checker, "DIAGNOSTIC_COMMIT", d0),
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
            d0, f0, _f1a, f1b = build_freeze_repository(
                repository, sibling_refreeze=False
            )
            target = repository / checker.ROLE_PATHS[0][1]
            os.chmod(target, 0o666)
            with (
                patch.object(checker, "AUTHORITY_COMMIT", f0),
                patch.object(checker, "DIAGNOSTIC_COMMIT", d0),
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
                self.assertEqual(
                    checker.provisional_hashes(repository)["role"], sha256(b"{}")
                )
                os.chmod(target, 0o666)
                self.assertEqual(
                    checker.provisional_hashes(repository)["role"], "UNAVAILABLE"
                )
                os.chmod(target, 0o644)
                os.link(target, repository / "alias")
                self.assertEqual(
                    checker.provisional_hashes(repository)["role"], "UNAVAILABLE"
                )


if __name__ == "__main__":
    unittest.main()
