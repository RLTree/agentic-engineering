from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validator = load("validate_ae_sq7_corpus", SCRIPTS / "validate_ae_sq7_corpus.py")
builder = load(
    "build_ae_sq7_author_template", SCRIPTS / "build_ae_sq7_author_template.py"
)
runner = load("run_ae_sq7_aq_gate_test", SCRIPTS / "run_ae_sq7_aq.py")


def git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write(repository: Path, relative: str, raw: bytes) -> None:
    destination = repository / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)


def sealed(repository: Path, commit: str, path: str) -> dict[str, str]:
    raw = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=repository,
        check=True,
        capture_output=True,
    ).stdout
    return {
        "blob": git(repository, "rev-parse", f"{commit}:{path}"),
        "commit": commit,
        "path": path,
        "sha256": builder.sha256(raw),
        "tree": git(repository, "rev-parse", f"{commit}^{{tree}}"),
    }


def commit_one(
    repository: Path, parent: str, path: str, raw: bytes, message: str
) -> str:
    git(repository, "checkout", "-q", "--detach", parent)
    write(repository, path, raw)
    git(repository, "add", path)
    git(repository, "commit", "-q", "-m", message)
    return git(repository, "rev-parse", "HEAD")


def profile() -> dict:
    sha = "1" * 64
    return {
        "program_id": "AE-SQ7",
        "candidate_id": "AE-SQ7-SLEC-7",
        "implementation_commit": "a" * 40,
        "implementation_tree": "b" * 40,
        "freeze_commit": "c" * 40,
        "freeze_tree": "d" * 40,
        "freeze_path": "evals/ae-sq7/f1/repaired-freeze.json",
        "freeze_sha256": "e" * 64,
        "bindings": {
            "corpus_schema": {"sha256": sha},
            "gates": {"sha256": "2" * 64},
            "metrics": {"sha256": "3" * 64},
            "evaluator_schema": {"sha256": "4" * 64},
        },
    }


class AuthorTemplateTests(unittest.TestCase):
    def test_authoring_cli_refuses_without_committed_f1g_gate(self) -> None:
        with self.assertRaises(SystemExit):
            builder.main(
                [
                    "--root",
                    str(ROOT),
                    "--freeze-commit",
                    "0" * 40,
                    "--split-id",
                    "A",
                    "--author-id",
                    "sq7-author-a",
                ]
            )

    def test_expected_authority_uses_f1a_and_parent_uses_f1b(self) -> None:
        current = profile()
        authority = validator.expected_split_authority(current)
        self.assertEqual(
            authority["candidate_commit"], current["implementation_commit"]
        )
        self.assertEqual(authority["candidate_tree"], current["implementation_tree"])
        self.assertEqual(authority["f1_freeze_sha256"], current["freeze_sha256"])
        raw = builder.render_author_template(
            current, split_id="A", author_id="sq7-author-a"
        )
        document = builder.verify_author_template(
            raw, current, split_id="A", author_id="sq7-author-a"
        )
        self.assertEqual(
            document["f1b_provenance_parent"]["commit"], current["freeze_commit"]
        )
        self.assertNotIn("cases", document)
        self.assertEqual(raw, builder.canonical_json(json.loads(raw)))

    def test_f1b_substitution_and_mixed_identity_reject(self) -> None:
        current = profile()
        raw = builder.render_author_template(
            current, split_id="B", author_id="sq7-author-b"
        )
        document = json.loads(raw)
        document["split_authority"]["candidate_commit"] = current["freeze_commit"]
        document["split_authority"]["candidate_tree"] = current["freeze_tree"]
        with self.assertRaises(builder.AuthorTemplateError):
            builder.verify_author_template(
                builder.canonical_json(document),
                current,
                split_id="B",
                author_id="sq7-author-b",
            )
        mixed = copy.deepcopy(current)
        mixed["implementation_tree"] = mixed["freeze_tree"]
        self.assertNotEqual(
            validator.expected_split_authority(mixed)["candidate_commit"],
            mixed["freeze_commit"],
        )

    def test_invalid_or_conflated_profile_rejects(self) -> None:
        current = profile()
        current["freeze_commit"] = current["implementation_commit"]
        with self.assertRaises(validator.CorpusContractError):
            validator.expected_split_authority(current)
        with self.assertRaises(builder.AuthorTemplateError):
            builder.render_author_template(
                current, split_id="A", author_id="sq7-author-a"
            )

    def test_real_ephemeral_f1g_to_f2b_graph_passes_production_loader(self) -> None:
        checker_test = load(
            "_sq7_checker_fixture",
            ROOT / "tests/test_check_ae_sq7_candidate.py",
        )
        corpus_test = load(
            "_sq7_corpus_fixture",
            ROOT / "tests/test_ae_sq7_corpus_contract.py",
        )
        checker = load("_sq7_target_checker", SCRIPTS / "check_ae_sq7_candidate.py")
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repo"
            repository.mkdir()
            _d0, _f0, f1a, f1b = checker_test.build_freeze_repository(
                repository, sibling_refreeze=False, real_roles=True
            )
            current = checker.load_verified_candidate(
                repository, f1b, require_live=False
            )
            template_raw = builder.render_author_template(
                current, split_id="A", author_id="synthetic-author-a"
            )
            freeze_binding = sealed(repository, f1b, checker.FREEZE_PATH)
            gate = {
                "schema_version": "ae-sq7-author-template-gate-v1",
                "program_id": "AE-SQ7",
                "candidate_id": "AE-SQ7-SLEC-7",
                "attempt": 1,
                "status": "PASS",
                "model_calls": 0,
                "f1a_implementation": {
                    "commit": f1a,
                    "tree": current["implementation_tree"],
                },
                "f1b_freeze": freeze_binding,
                "builder": current["bindings"]["author_template_builder"],
                "validator": current["bindings"][
                    "corpus_validator_and_expected_authority_helper"
                ],
                "template_sha256": builder.sha256(template_raw),
                "positive_round_trip": {
                    "production_loader": "_load_base_state",
                    "status": "PASS",
                },
                "selected_reference_anchor_gate": (
                    runner._run_selected_reference_anchor_gate(current)
                ),
                "red_fixture": {
                    "exception_class": "PreflightError",
                    "exception_message": "F1G receipt is not exact canonical UTF-8 JSON",
                    "mutation": "exact-canonical-receipt-plus-one-line-feed",
                    "status": "REJECTED",
                },
            }
            gate["aggregate_sha256"] = builder.sha256(builder.canonical_json(gate))
            f1g = commit_one(
                repository,
                f1b,
                runner.F1G_RECEIPT_PATH,
                builder.canonical_json(gate),
                "F1G taskless identity gate",
            )
            f1g_binding = sealed(repository, f1g, runner.F1G_RECEIPT_PATH)
            preauthor = runner._load_base_state(repository, f1g, preauthor=True)
            self.assertTrue(preauthor["preauthor_verified"])
            self.assertEqual(preauthor["f1g"]["binding"], f1g_binding)

            bad_f1g = commit_one(
                repository,
                f1b,
                runner.F1G_RECEIPT_PATH,
                builder.canonical_json(gate) + b"\n",
                "F1G trailing-line-feed red",
            )
            with self.assertRaisesRegex(
                runner.PreflightError,
                "F1G receipt is not exact canonical UTF-8 JSON",
            ):
                runner._load_base_state(repository, bad_f1g, preauthor=True)

            alternate_gate = copy.deepcopy(gate)
            alternate_gate["selected_reference_anchor_gate"]["production_resolver"] = (
                "alternate_resolver"
            )
            alternate_gate.pop("aggregate_sha256")
            alternate_gate["aggregate_sha256"] = builder.sha256(
                builder.canonical_json(alternate_gate)
            )
            alternate_f1g = commit_one(
                repository,
                f1b,
                runner.F1G_RECEIPT_PATH,
                builder.canonical_json(alternate_gate),
                "F1G alternate resolver red",
            )
            with self.assertRaisesRegex(
                runner.PreflightError,
                "F1G receipt violates its frozen schema",
            ):
                runner._load_base_state(repository, alternate_f1g, preauthor=True)
            git(repository, "checkout", "-q", "--detach", f1g)

            split_documents = list(corpus_test.make_pair())
            expected_authority = validator.expected_split_authority(current)
            for document in split_documents:
                document["authority"] = copy.deepcopy(expected_authority)
            split_raws = [validator.canonical_json(value) for value in split_documents]
            author_commits = []
            for split_id, raw in zip(("A", "B"), split_raws, strict=True):
                author_commits.append(
                    commit_one(
                        repository,
                        f1g,
                        f"evals/ae-sq7/f2/split-{split_id.lower()}.json",
                        raw,
                        f"synthetic author {split_id}",
                    )
                )

            inventory_binding = current["external_bindings"]["historical_task_digests"]
            inventory_raw = subprocess.run(
                [
                    "git",
                    "show",
                    f"{inventory_binding['commit']}:{inventory_binding['path']}",
                ],
                cwd=repository,
                check=True,
                capture_output=True,
            ).stdout
            validation = validator.validate_corpora(
                split_raws,
                historical_digest_inventory=inventory_raw,
                expected_authority=expected_authority,
            )
            self.assertTrue(validation.passed)
            schedule = list(validator.build_schedule(validation.qualified_case_ids))
            schedule_raw = validator.canonical_json({"presentations": schedule})
            schedule_sha = validator.schedule_digest(schedule)
            provenance = []
            split_rows = []
            for split_id, author_commit, document, raw in zip(
                ("A", "B"), author_commits, split_documents, split_raws, strict=True
            ):
                path = f"evals/ae-sq7/f2/split-{split_id.lower()}.json"
                row = {
                    "split_id": split_id,
                    "path": path,
                    "raw_sha256": builder.sha256(raw),
                    "content_sha256": validator.digest(document),
                    "case_count": 20,
                }
                split_rows.append(row)
                provenance.append(
                    {
                        "provenance_version": "ae-sq7-author-provenance-v1",
                        "split_id": split_id,
                        "author_id": document["author_id"],
                        "commit": author_commit,
                        "tree": git(
                            repository, "rev-parse", f"{author_commit}^{{tree}}"
                        ),
                        "parent_f1g_commit": f1g,
                        "path": path,
                        "blob": git(repository, "rev-parse", f"{author_commit}:{path}"),
                        "raw_sha256": builder.sha256(raw),
                        "content_sha256": validator.digest(document),
                        "case_count": 20,
                        "other_split_route_permitted": False,
                        "predecessor_material_route_permitted": False,
                        "diagnostic_or_live_result_route_permitted": False,
                        "outcome_route_permitted": False,
                        "claim_ceiling": runner.AUTHOR_CLAIM_CEILING,
                    }
                )
            corpus_manifest = {
                "schema_version": "ae-sq7-corpus-manifest-v1",
                "program_id": "AE-SQ7",
                "candidate_id": "AE-SQ7-SLEC-7",
                "corpus_id": "AE-SQ7-AQ-FRESH-V1",
                "f1_freeze": freeze_binding,
                "implementation_freeze": {
                    "commit": f1a,
                    "tree": current["implementation_tree"],
                },
                "corpus_contract_sha256": current["bindings"]["corpus_schema"][
                    "sha256"
                ],
                "historical_inventory": {
                    "path": inventory_binding["path"],
                    "raw_sha256": builder.sha256(inventory_raw),
                    "inventory_sha256": validator.TRUSTED_HISTORICAL_CONTENT_SHA256,
                    "inventory_count": 768,
                    "source_count": 20,
                },
                "splits": split_rows,
                "authoring_provenance": provenance,
                "combined_corpus_sha256": validation.corpus_digest,
                "schedule": {
                    "path": "evals/ae-sq7/f2/schedule.json",
                    "raw_sha256": builder.sha256(schedule_raw),
                    "schedule_sha256": schedule_sha,
                    "presentations": 80,
                    "calls_per_presentation": 4,
                },
                "freshness": {
                    "split_authors_distinct": True,
                    "other_split_access": False,
                    "predecessor_material_access": False,
                    "diagnostic_or_live_result_access": False,
                    "outcome_blind_at_authoring": True,
                    "corpus_freeze_self_reference": False,
                },
            }
            git(repository, "checkout", "-q", "--detach", f1g)
            for path, raw in (
                ("evals/ae-sq7/f2/split-a.json", split_raws[0]),
                ("evals/ae-sq7/f2/split-b.json", split_raws[1]),
                ("evals/ae-sq7/f2/schedule.json", schedule_raw),
                (
                    "evals/ae-sq7/f2/corpus-manifest.json",
                    validator.canonical_json(corpus_manifest),
                ),
            ):
                write(repository, path, raw)
                git(repository, "add", path)
            f2a_tree = git(repository, "write-tree")
            f2a = subprocess.run(
                [
                    "git",
                    "commit-tree",
                    f2a_tree,
                    "-p",
                    f1g,
                    "-p",
                    author_commits[0],
                    "-p",
                    author_commits[1],
                ],
                cwd=repository,
                input="synthetic F2A\n",
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            git(repository, "checkout", "-q", "--detach", f2a)
            corpus_manifest_binding = sealed(
                repository, f2a, "evals/ae-sq7/f2/corpus-manifest.json"
            )
            schedule_binding = sealed(repository, f2a, "evals/ae-sq7/f2/schedule.json")
            split_bindings = [
                sealed(repository, f2a, f"evals/ae-sq7/f2/split-{name}.json")
                for name in ("a", "b")
            ]
            artifacts = [
                {
                    "blob": corpus_manifest_binding["blob"],
                    "content_or_semantic_sha256": validation.corpus_digest,
                    "path": corpus_manifest_binding["path"],
                    "raw_sha256": corpus_manifest_binding["sha256"],
                },
                *[
                    {
                        "blob": binding["blob"],
                        "content_or_semantic_sha256": validator.digest(document),
                        "path": binding["path"],
                        "raw_sha256": binding["sha256"],
                    }
                    for binding, document in zip(
                        split_bindings, split_documents, strict=True
                    )
                ],
                {
                    "blob": schedule_binding["blob"],
                    "content_or_semantic_sha256": schedule_sha,
                    "path": schedule_binding["path"],
                    "raw_sha256": schedule_binding["sha256"],
                },
            ]
            receipt = {
                "aggregate_sha256": "0" * 64,
                "artifacts": artifacts,
                "author_commits": [
                    {
                        "author_id": document["author_id"],
                        "blob": binding["blob"],
                        "commit": author_commit,
                        "content_sha256": validator.digest(document),
                        "path": binding["path"],
                        "raw_sha256": binding["sha256"],
                        "tree": git(
                            repository, "rev-parse", f"{author_commit}^{{tree}}"
                        ),
                    }
                    for document, binding, author_commit in zip(
                        split_documents, split_bindings, author_commits, strict=True
                    )
                ],
                "authorship_performed": False,
                "claim_ceiling": runner.VALIDATOR_CLAIM_CEILING,
                "errors": [],
                "f1a_implementation": {
                    "commit": f1a,
                    "role_ledger_sha256": current["role_ledger_sha256"],
                    "tree": current["implementation_tree"],
                },
                "f1b_freeze": freeze_binding,
                "f1g_gate": f1g_binding,
                "f2a_corpus": {
                    "commit": f2a,
                    "ordered_parents": [f1g, *author_commits],
                    "tree": f2a_tree,
                },
                "holds": [],
                "receipt_version": "ae-sq7-independent-validation-v1",
                "status": "PASS",
                "validator": {
                    "blob": current["bindings"][
                        "corpus_validator_and_expected_authority_helper"
                    ]["blob"],
                    "commit": f1a,
                    "path": current["bindings"][
                        "corpus_validator_and_expected_authority_helper"
                    ]["path"],
                    "raw_sha256": current["bindings"][
                        "corpus_validator_and_expected_authority_helper"
                    ]["sha256"],
                    "tree": current["implementation_tree"],
                    "validator_id": "independent-nonauthor-validator",
                },
            }
            unsigned = dict(receipt)
            unsigned.pop("aggregate_sha256")
            receipt["aggregate_sha256"] = builder.sha256(
                builder.canonical_json(unsigned)
            )

            def path_digest(binding: dict[str, str]) -> dict[str, str]:
                return {key: binding[key] for key in ("path", "blob", "sha256")}

            manifest = {
                "schema_version": "ae-sq7-run-manifest-v1",
                "program_id": "AE-SQ7",
                "candidate_id": "AE-SQ7-SLEC-7",
                "run_id": "AE-SQ7-AQ-F1G-SENTINEL",
                "author_template_gate": f1g_binding,
                "f1_freeze": freeze_binding,
                "implementation_freeze": {
                    "commit": f1a,
                    "tree": current["implementation_tree"],
                },
                "corpus_freeze": {"commit": f2a, "tree": f2a_tree},
                "corpus": {
                    "corpus_id": "AE-SQ7-AQ-FRESH-V1",
                    "schema": current["bindings"]["corpus_schema"],
                    "manifest": path_digest(corpus_manifest_binding),
                    "split_a": path_digest(split_bindings[0]),
                    "split_b": path_digest(split_bindings[1]),
                    "historical_inventory": inventory_binding,
                },
                "schedule": {
                    "document": path_digest(schedule_binding),
                    "seed": validator.SCHEDULE_SEED,
                    "sha256": schedule_sha,
                    "presentations": 80,
                    "calls_per_presentation": 4,
                    "conditions": ["current", "reduced"],
                },
                "runtime": {
                    "cli": {
                        "id": "codex-cli",
                        "version": runner.CLI_VERSION,
                        "sha256": runner.CLI_SHA256,
                    },
                    "model": runner.MODEL,
                    "reasoning": runner.REASONING,
                    "fallback": False,
                    "sandbox": "read-only",
                    "approval_policy": "never",
                    "ephemeral": True,
                    "strict_isolation": True,
                },
                "execution": {
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
                    "raw_persistence": False,
                    "aggregate_only_projection": True,
                },
                "validation_receipt": receipt,
                "usage_authority": runner.USAGE_APPROVAL,
            }
            f2b = commit_one(
                repository,
                f2a,
                runner.RUN_MANIFEST_PATH,
                runner.canonical_json(manifest),
                "synthetic F2B",
            )
            ambient = {
                name: sys.modules.pop(name)
                for name in ("resolve_ae_sq7_slec", "validate_ae_sq7_corpus")
                if name in sys.modules
            }
            state = runner._load_base_state(repository, f2b)
            try:
                self.assertTrue(state["validation_receipt_verified"])
                self.assertEqual(state["f1g"]["binding"], f1g_binding)
                self.assertEqual(state["expected_authority"], expected_authority)
            finally:
                state["snapshot"].close()
                sys.modules.update(ambient)

            wrong_documents = copy.deepcopy(split_documents)
            wrong_authority = copy.deepcopy(expected_authority)
            wrong_authority["candidate_commit"] = f1b
            wrong_authority["candidate_tree"] = current["freeze_tree"]
            for document in wrong_documents:
                document["authority"] = copy.deepcopy(wrong_authority)
            wrong_raws = [validator.canonical_json(value) for value in wrong_documents]
            wrong_authors = [
                commit_one(
                    repository,
                    f1g,
                    f"evals/ae-sq7/f2/split-{split_id.lower()}.json",
                    raw,
                    f"red synthetic author {split_id}",
                )
                for split_id, raw in zip(("A", "B"), wrong_raws, strict=True)
            ]
            wrong_provenance = []
            wrong_split_rows = []
            for split_id, author_commit, document, raw in zip(
                ("A", "B"), wrong_authors, wrong_documents, wrong_raws, strict=True
            ):
                path = f"evals/ae-sq7/f2/split-{split_id.lower()}.json"
                raw_sha = builder.sha256(raw)
                content_sha = validator.digest(document)
                wrong_split_rows.append(
                    {
                        "split_id": split_id,
                        "path": path,
                        "raw_sha256": raw_sha,
                        "content_sha256": content_sha,
                        "case_count": 20,
                    }
                )
                wrong_provenance.append(
                    {
                        "provenance_version": "ae-sq7-author-provenance-v1",
                        "split_id": split_id,
                        "author_id": document["author_id"],
                        "commit": author_commit,
                        "tree": git(
                            repository, "rev-parse", f"{author_commit}^{{tree}}"
                        ),
                        "parent_f1g_commit": f1g,
                        "path": path,
                        "blob": git(repository, "rev-parse", f"{author_commit}:{path}"),
                        "raw_sha256": raw_sha,
                        "content_sha256": content_sha,
                        "case_count": 20,
                        "other_split_route_permitted": False,
                        "predecessor_material_route_permitted": False,
                        "diagnostic_or_live_result_route_permitted": False,
                        "outcome_route_permitted": False,
                        "claim_ceiling": runner.AUTHOR_CLAIM_CEILING,
                    }
                )
            wrong_corpus_manifest = copy.deepcopy(corpus_manifest)
            wrong_corpus_manifest["splits"] = wrong_split_rows
            wrong_corpus_manifest["authoring_provenance"] = wrong_provenance
            wrong_corpus_manifest["combined_corpus_sha256"] = "0" * 64
            git(repository, "checkout", "-q", "--detach", f1g)
            for path, raw in (
                ("evals/ae-sq7/f2/split-a.json", wrong_raws[0]),
                ("evals/ae-sq7/f2/split-b.json", wrong_raws[1]),
                ("evals/ae-sq7/f2/schedule.json", schedule_raw),
                (
                    "evals/ae-sq7/f2/corpus-manifest.json",
                    validator.canonical_json(wrong_corpus_manifest),
                ),
            ):
                write(repository, path, raw)
                git(repository, "add", path)
            wrong_f2a_tree = git(repository, "write-tree")
            wrong_f2a = subprocess.run(
                [
                    "git",
                    "commit-tree",
                    wrong_f2a_tree,
                    "-p",
                    f1g,
                    "-p",
                    wrong_authors[0],
                    "-p",
                    wrong_authors[1],
                ],
                cwd=repository,
                input="red synthetic F2A\n",
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            git(repository, "checkout", "-q", "--detach", wrong_f2a)
            wrong_manifest_binding = sealed(
                repository, wrong_f2a, "evals/ae-sq7/f2/corpus-manifest.json"
            )
            wrong_split_bindings = [
                sealed(repository, wrong_f2a, f"evals/ae-sq7/f2/split-{name}.json")
                for name in ("a", "b")
            ]
            wrong_receipt = copy.deepcopy(receipt)
            wrong_receipt["f2a_corpus"] = {
                "commit": wrong_f2a,
                "ordered_parents": [f1g, *wrong_authors],
                "tree": wrong_f2a_tree,
            }
            wrong_receipt["author_commits"] = [
                {
                    "author_id": document["author_id"],
                    "blob": binding["blob"],
                    "commit": author_commit,
                    "content_sha256": validator.digest(document),
                    "path": binding["path"],
                    "raw_sha256": binding["sha256"],
                    "tree": git(repository, "rev-parse", f"{author_commit}^{{tree}}"),
                }
                for document, binding, author_commit in zip(
                    wrong_documents, wrong_split_bindings, wrong_authors, strict=True
                )
            ]
            wrong_receipt["artifacts"][0] = {
                "blob": wrong_manifest_binding["blob"],
                "content_or_semantic_sha256": "0" * 64,
                "path": wrong_manifest_binding["path"],
                "raw_sha256": wrong_manifest_binding["sha256"],
            }
            for index in (0, 1):
                wrong_receipt["artifacts"][index + 1] = {
                    "blob": wrong_split_bindings[index]["blob"],
                    "content_or_semantic_sha256": validator.digest(
                        wrong_documents[index]
                    ),
                    "path": wrong_split_bindings[index]["path"],
                    "raw_sha256": wrong_split_bindings[index]["sha256"],
                }
            wrong_unsigned = dict(wrong_receipt)
            wrong_unsigned.pop("aggregate_sha256")
            wrong_receipt["aggregate_sha256"] = builder.sha256(
                builder.canonical_json(wrong_unsigned)
            )
            wrong_manifest = copy.deepcopy(manifest)
            wrong_manifest["corpus_freeze"] = {
                "commit": wrong_f2a,
                "tree": wrong_f2a_tree,
            }
            wrong_manifest["corpus"]["manifest"] = path_digest(wrong_manifest_binding)
            wrong_manifest["corpus"]["split_a"] = path_digest(wrong_split_bindings[0])
            wrong_manifest["corpus"]["split_b"] = path_digest(wrong_split_bindings[1])
            wrong_manifest["validation_receipt"] = wrong_receipt
            wrong_f2b = commit_one(
                repository,
                wrong_f2a,
                runner.RUN_MANIFEST_PATH,
                runner.canonical_json(wrong_manifest),
                "red synthetic F2B",
            )
            ambient = {
                name: sys.modules.pop(name)
                for name in ("resolve_ae_sq7_slec", "validate_ae_sq7_corpus")
                if name in sys.modules
            }
            try:
                with self.assertRaisesRegex(
                    runner.PreflightError,
                    "corpus split authority is not the frozen F1 candidate",
                ):
                    runner._load_base_state(repository, wrong_f2b)
            finally:
                sys.modules.update(ambient)


if __name__ == "__main__":
    unittest.main()
