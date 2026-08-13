"""Fail-closed terminal custody checks for AE-SQ4."""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = ROOT / "evals/ae-sq4/ar/terminal-decision.json"
PLAN_PATH = ROOT / "docs/exec-plans/active/ae-sq4.md"
F1A = "3762efae80ead1461d973b4737c5dcab6bae026a"
F1B = "6357b87cfae9e488bbb1489541ec03d577803463"
F2A = "8b1a26dc6951d7052429197af5d8dffe3636bbb3"
HEX = set("0123456789abcdef")
sys.dont_write_bytecode = True


KEYS = {
    "/": (
        "schema_version",
        "program_id",
        "candidate_id",
        "stage",
        "status",
        "decision",
        "stop",
        "claim_ceiling",
        "terminal_reason",
        "frozen_program",
        "sealed_author_objects",
        "f2a_object",
        "durable_evidence_refs",
        "standalone_validation",
        "frozen_runtime_rejection",
        "phase_status",
        "live_call_accounting",
        "preservation",
        "successor_route",
        "terminal_edges",
    ),
    "/frozen_program": ("f0", "f1a", "f1b"),
    "/frozen_program/f0": (
        "commit",
        "tree",
        "program_authority_path",
        "program_authority_blob",
        "program_authority_raw_sha256",
        "active_plan_path",
        "preterminal_active_plan_blob",
        "preterminal_active_plan_raw_sha256",
    ),
    "/frozen_program/f1a": (
        "commit",
        "tree",
        "parent",
        "status",
        "runner_path",
        "runner_blob",
        "runner_raw_sha256",
    ),
    "/frozen_program/f1b": (
        "commit",
        "tree",
        "parent",
        "status",
        "freeze_path",
        "freeze_blob",
        "freeze_raw_sha256",
    ),
    "/f2a_object": (
        "commit",
        "tree",
        "ordered_parents",
        "status",
        "corpus_manifest",
        "schedule",
    ),
    "/f2a_object/corpus_manifest": ("path", "blob", "raw_sha256"),
    "/f2a_object/schedule": (
        "path",
        "blob",
        "raw_sha256",
        "semantic_sha256",
        "presentations",
        "calls_per_presentation",
    ),
    "/durable_evidence_refs": (
        "evidence_commit",
        "local_branch",
        "remote_tracking_branch",
        "ref_mutation_authorized",
    ),
    "/durable_evidence_refs/local_branch": ("name", "target"),
    "/durable_evidence_refs/remote_tracking_branch": ("name", "target"),
    "/standalone_validation": (
        "evidence_kind",
        "validator_id",
        "authorship_performed",
        "status",
        "errors",
        "holds",
        "case_count",
        "historical_digest_count",
        "similarity_check_count",
        "maximum_similarity",
        "maximum_similarity_threshold",
        "combined_corpus_sha256",
        "qualification_effect",
    ),
    "/frozen_runtime_rejection": (
        "exception_class",
        "exception_message",
        "split_authority_actual",
        "frozen_runtime_required",
        "runner_path",
        "runner_line_interval",
        "classification",
        "route",
    ),
    "/frozen_runtime_rejection/split_authority_actual": (
        "candidate_commit",
        "candidate_tree",
    ),
    "/frozen_runtime_rejection/frozen_runtime_required": (
        "candidate_commit",
        "candidate_tree",
    ),
    "/phase_status": (
        "SQ4_F0",
        "SQ4_F1A",
        "SQ4_F1B",
        "SQ4_F2",
        "SQ4_F2B",
        "SQ4_F3",
        "SQ4_F4",
        "SQ4_F5",
        "SQ4_F6",
        "SQ4_AS_HANDOFF",
    ),
    "/live_call_accounting": (
        "diagnostic_calls",
        "canary_calls",
        "batch_calls",
        "total_model_calls",
    ),
    "/preservation": (
        "retain_f0_f1_author_and_f2a_objects",
        "sq4_bytes_rewrite_delete_or_migrate_permitted",
        "sq4_candidate_identity_or_bytes_reuse_permitted",
        "sq4_split_or_f2a_reuse_permitted",
        "sq4_retry_reopen_resume_repair_refreeze_or_H6_permitted",
    ),
}


def strict(raw: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite: {token}")
        ),
    )
    if not isinstance(value, dict):
        raise ValueError("root must be object")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def is_hex(value: object, length: int) -> bool:
    return isinstance(value, str) and len(value) == length and not (set(value) - HEX)


def validate(document: dict[str, Any]) -> None:
    for pointer, keys in KEYS.items():
        value: Any = document
        for component in pointer.strip("/").split("/") if pointer != "/" else ():
            value = value[component]
        require(type(value) is dict and tuple(value) == keys, f"closed keys: {pointer}")
    require(document["schema_version"] == "ae-sq4-ar-terminal-decision-v1", "schema")
    require(document["program_id"] == "AE-SQ4", "program")
    require(document["candidate_id"] == "AE-SQ4-SLEC-4", "candidate")
    require((document["stage"], document["status"]) == ("SQ4-AR", "terminal"), "state")
    require(document["decision"] == "DO_NOT_RELEASE_OR_PROMOTE", "decision")
    require(document["stop"] is True, "stop")
    require(
        document["claim_ceiling"]
        == "structural-F2A-and-standalone-corpus-validation-only-not-F2-pass-qualification-runtime-or-provider-evidence",
        "claim ceiling",
    )
    require(
        document["terminal_reason"]
        == "frozen-runtime-rejects-both-authored-split-authorities-because-they-bind-F1B-instead-of-the-frozen-F1A-implementation",
        "terminal reason",
    )
    frozen = document["frozen_program"]
    require(
        frozen["f0"]
        == {
            "commit": "e8163ebfd74799cef546da176e73589f4a50d31a",
            "tree": "10a7a1f22068045b441ce958c00fe424c036138d",
            "program_authority_path": "evals/ae-sq4/program-authority.json",
            "program_authority_blob": "4b9519f2d7d5c45fb50d0c0511377d40918d5192",
            "program_authority_raw_sha256": "583f103440ba66828e402f3de6ff3e657e8660004cc362b33b8d177b6ebe6ac9",
            "active_plan_path": "docs/exec-plans/active/ae-sq4.md",
            "preterminal_active_plan_blob": "6c80a3acd126edafe30c899defb2026fa9b5ef72",
            "preterminal_active_plan_raw_sha256": "848c85a3bd6c922fb079f673cadea38c59fa9aeb7876ee7ee57e46bff90f41ad",
        },
        "F0",
    )
    require(
        frozen["f1a"]
        == {
            "commit": F1A,
            "tree": "6a071b4ee33246cc2ef448cf4d574f51abc89348",
            "parent": "e8163ebfd74799cef546da176e73589f4a50d31a",
            "status": "PASS",
            "runner_path": "scripts/run_ae_sq4_aq.py",
            "runner_blob": "537bb66dc5e008c080eb28ca52f3bad8139d283a",
            "runner_raw_sha256": "52b8a047b2067c847c9b86231a4189a188fc9455dc218f10cce3a50711615cb2",
        },
        "F1A",
    )
    require(
        frozen["f1b"]
        == {
            "commit": F1B,
            "tree": "6a04e5aa846cbe196425c58671bf390c499b4d59",
            "parent": F1A,
            "status": "PASS",
            "freeze_path": "evals/ae-sq4/f1/repaired-freeze.json",
            "freeze_blob": "30dd13fc674fdb45e3934bb5429cf8d20a8d1d0c",
            "freeze_raw_sha256": "580b08484a5ae9f35a942d1063ba7ce82ca83521533b0f8e0e6f763187f83893",
        },
        "F1B",
    )
    f2a = document["f2a_object"]
    require(
        (f2a["commit"], f2a["tree"], f2a["status"])
        == (F2A, "fd76825a250466fbfabff8b75d307cb8cb017814", "NOT_PASS"),
        "F2A",
    )
    require(
        f2a["ordered_parents"]
        == [
            F1B,
            "c2a38ef3b797ca8350102eca7e0bd9dc480332eb",
            "1629eb1c4054d54f397346613a56dba22fcbd607",
        ],
        "F2A parents",
    )
    require(
        f2a["corpus_manifest"]
        == {
            "path": "evals/ae-sq4/f2/corpus-manifest.json",
            "blob": "bf38e2e0f45a66f08bafd89f27a0aa657b5e16ef",
            "raw_sha256": "4bcdfe75f77099dfcda4301c083b40d277494bff2b43fcab490a72689074f5b4",
        },
        "corpus manifest",
    )
    require(
        f2a["schedule"]
        == {
            "path": "evals/ae-sq4/f2/schedule.json",
            "blob": "9ef21967259903d49e975d88c520c45d567a0d76",
            "raw_sha256": "6ce97e14c1a8db3d551ca44c3c305ba659eb7821db688b3255402c506a352468",
            "semantic_sha256": "59507386b745eb331c8812903d0b4dc6aa8281c4ff10933a4e18713669809ebb",
            "presentations": 80,
            "calls_per_presentation": 4,
        },
        "schedule",
    )
    refs = document["durable_evidence_refs"]
    require(refs["evidence_commit"] == F2A, "evidence ref commit")
    require(
        refs["local_branch"]
        == {
            "name": "refs/heads/codex/ae-sq4-f2-not-pass",
            "target": F2A,
        },
        "local evidence ref",
    )
    require(
        refs["remote_tracking_branch"]
        == {
            "name": "refs/remotes/origin/codex/ae-sq4-f2-not-pass",
            "target": F2A,
        },
        "remote evidence ref",
    )
    require(refs["ref_mutation_authorized"] is False, "ref mutation")
    authors = document["sealed_author_objects"]
    require(type(authors) is list and len(authors) == 2, "authors")
    author_keys = (
        "split_id",
        "commit",
        "tree",
        "parent",
        "path",
        "blob",
        "raw_sha256",
        "content_sha256",
        "case_count",
    )
    require(
        all(type(row) is dict and tuple(row) == author_keys for row in authors),
        "author keys",
    )
    require([row["split_id"] for row in authors] == ["A", "B"], "split order")
    require([row["case_count"] for row in authors] == [20, 20], "case counts")
    standalone = document["standalone_validation"]
    require(
        standalone["evidence_kind"]
        == "recomputed-aggregate-evidence-not-a-prior-durable-receipt",
        "evidence kind",
    )
    require(standalone["status"] == "PASS", "standalone PASS")
    require(standalone["authorship_performed"] is False, "validator authorship")
    require(
        standalone["errors"] == [] and standalone["holds"] == [], "validator closure"
    )
    require(standalone["qualification_effect"] == "none", "qualification effect")
    require(standalone["case_count"] == 40, "case count")
    require(standalone["historical_digest_count"] == 768, "history")
    require(standalone["similarity_check_count"] == 400, "similarity count")
    require(standalone["maximum_similarity"] == 0.406626506, "maximum similarity")
    require(standalone["maximum_similarity_threshold"] == 0.8, "similarity threshold")
    require(
        standalone["maximum_similarity"] < standalone["maximum_similarity_threshold"],
        "similarity threshold",
    )
    require(
        standalone["combined_corpus_sha256"]
        == "feaa03f2afd815bbc661d6c9de99c2cf53410f472206b2a2cd4b964f5bb1f122",
        "corpus digest",
    )
    rejection = document["frozen_runtime_rejection"]
    require(rejection["exception_class"] == "PreflightError", "exception class")
    require(
        rejection["exception_message"]
        == "corpus split authority is not the frozen F1 candidate",
        "exception message",
    )
    require(
        rejection["split_authority_actual"]
        == {
            "candidate_commit": F1B,
            "candidate_tree": "6a04e5aa846cbe196425c58671bf390c499b4d59",
        },
        "actual split authority",
    )
    require(
        rejection["frozen_runtime_required"]
        == {
            "candidate_commit": F1A,
            "candidate_tree": "6a071b4ee33246cc2ef448cf4d574f51abc89348",
        },
        "required split authority",
    )
    require(rejection["route"] == "SQ4-F2:NOT_PASS->SQ4-AR", "route")
    require(
        rejection["classification"]
        == "corpus-split-authority-candidate-identity-mismatch-before-F2B",
        "classification",
    )
    phases = document["phase_status"]
    require(
        phases
        == {
            "SQ4_F0": "completed-authority-only",
            "SQ4_F1A": "PASS",
            "SQ4_F1B": "PASS",
            "SQ4_F2": "NOT_PASS-terminal-authority-mismatch",
            "SQ4_F2B": "not-created",
            "SQ4_F3": "not-started-no-preflight",
            "SQ4_F4": "not-started-zero-canary-calls",
            "SQ4_F5": "not-started-zero-batch-calls",
            "SQ4_F6": "not-started-no-AQ-result",
            "SQ4_AS_HANDOFF": "blocked",
        },
        "phase status",
    )
    require(
        all(
            type(value) is int and value == 0
            for value in document["live_call_accounting"].values()
        ),
        "zero calls",
    )
    preservation = document["preservation"]
    require(preservation["retain_f0_f1_author_and_f2a_objects"] is True, "retain")
    require(
        all(
            value is False
            for key, value in preservation.items()
            if key != "retain_f0_f1_author_and_f2a_objects"
        ),
        "preservation prohibitions",
    )
    require(
        document["terminal_edges"]
        == [
            "no_SQ4_F2B",
            "no_SQ4_F3",
            "no_SQ4_F4",
            "no_SQ4_F5",
            "no_SQ4_F6",
            "no_SQ4_AS_HANDOFF",
            "no_SQ4_retry",
            "no_SQ4_reopen",
            "no_SQ4_resume",
            "no_SQ4_repair",
            "no_SQ4_refreeze",
            "no_SQ4_H6",
            "no_SQ4_candidate_identity_or_byte_reuse",
            "no_SQ4_split_reuse",
            "no_SQ4_F2A_reuse",
            "no_downstream",
            "no_release",
            "no_publish",
            "no_promotion",
            "no_deletion",
            "no_migration",
        ],
        "terminal edges",
    )
    require(
        document["successor_route"]
        == "distinct-owner-authorized-new-program-id-with-fresh-candidate-and-fresh-corpus-only",
        "successor route",
    )


def git_output(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True
    ).stdout


def frozen_modules() -> tuple[Any, Any, Any]:
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    checker = importlib.import_module("check_ae_sq4_candidate")
    runner = importlib.import_module("run_ae_sq4_aq")
    validator = importlib.import_module("validate_ae_sq4_corpus")
    return checker, runner, validator


class AeSq4TerminalV1Tests(unittest.TestCase):
    def test_strict_terminal_contract(self) -> None:
        validate(strict(DECISION_PATH.read_bytes()))

    def test_git_objects_and_aggregate_bytes_are_exact(self) -> None:
        document = strict(DECISION_PATH.read_bytes())
        for row in document["durable_evidence_refs"].values():
            if not isinstance(row, dict):
                continue
            self.assertEqual(
                row["target"],
                git_output("show-ref", "--verify", "--hash", row["name"])
                .decode()
                .strip(),
            )
        for role in ("f0", "f1a", "f1b"):
            row = document["frozen_program"][role]
            self.assertEqual(
                row["tree"],
                git_output("rev-parse", f"{row['commit']}^{{tree}}").decode().strip(),
            )
        self.assertEqual(
            document["frozen_program"]["f1a"]["parent"],
            git_output("show", "-s", "--format=%P", F1A).decode().strip(),
        )
        self.assertEqual(
            document["frozen_program"]["f1b"]["parent"],
            git_output("show", "-s", "--format=%P", F1B).decode().strip(),
        )
        bound_files = (
            (
                document["frozen_program"]["f0"],
                "program_authority_path",
                "program_authority_blob",
                "program_authority_raw_sha256",
            ),
            (
                document["frozen_program"]["f0"],
                "active_plan_path",
                "preterminal_active_plan_blob",
                "preterminal_active_plan_raw_sha256",
            ),
            (
                document["frozen_program"]["f1a"],
                "runner_path",
                "runner_blob",
                "runner_raw_sha256",
            ),
            (
                document["frozen_program"]["f1b"],
                "freeze_path",
                "freeze_blob",
                "freeze_raw_sha256",
            ),
        )
        for row, path_key, blob_key, raw_key in bound_files:
            raw = git_output("show", f"{row['commit']}:{row[path_key]}")
            self.assertEqual(
                row[blob_key],
                git_output("rev-parse", f"{row['commit']}:{row[path_key]}")
                .decode()
                .strip(),
            )
            self.assertEqual(row[raw_key], hashlib.sha256(raw).hexdigest())
        self.assertEqual(
            document["f2a_object"]["ordered_parents"],
            git_output("show", "-s", "--format=%P", F2A).decode().strip().split(),
        )
        for row in document["sealed_author_objects"]:
            self.assertEqual(
                row["tree"],
                git_output("rev-parse", f"{row['commit']}^{{tree}}").decode().strip(),
            )
            self.assertEqual(
                row["blob"],
                git_output("rev-parse", f"{row['commit']}:{row['path']}")
                .decode()
                .strip(),
            )
            raw = git_output("show", f"{row['commit']}:{row['path']}")
            self.assertEqual(row["raw_sha256"], hashlib.sha256(raw).hexdigest())
        for key in ("corpus_manifest", "schedule"):
            row = document["f2a_object"][key]
            self.assertEqual(
                row["blob"],
                git_output("rev-parse", f"{F2A}:{row['path']}").decode().strip(),
            )
            self.assertEqual(
                row["raw_sha256"],
                hashlib.sha256(git_output("show", f"{F2A}:{row['path']}")).hexdigest(),
            )
        _, _, validator = frozen_modules()
        split_raws = [
            git_output("show", f"{F2A}:evals/ae-sq4/f2/split-a.json"),
            git_output("show", f"{F2A}:evals/ae-sq4/f2/split-b.json"),
        ]
        inventory_raw = git_output(
            "show", f"{F1A}:evals/ae-sq4/f1/historical-task-digests.json"
        )
        validation = validator.validate_corpora(
            split_raws, historical_digest_inventory=inventory_raw
        )
        self.assertEqual("pass", validation.status)
        self.assertEqual([], list(validation.errors))
        self.assertEqual([], list(validation.holds))
        self.assertEqual(
            document["standalone_validation"]["combined_corpus_sha256"],
            validation.corpus_digest,
        )
        for row, raw in zip(document["sealed_author_objects"], split_raws, strict=True):
            self.assertEqual(row["content_sha256"], validator.digest(json.loads(raw)))
        split_documents = [json.loads(raw) for raw in split_raws]
        maximum_similarity = max(
            validator.near_similarity(left["task_text"], right["task_text"])
            for left in split_documents[0]["cases"]
            for right in split_documents[1]["cases"]
        )
        self.assertEqual(
            document["standalone_validation"]["maximum_similarity"],
            round(maximum_similarity, 9),
        )
        self.assertEqual(
            document["standalone_validation"]["similarity_check_count"],
            len(split_documents[0]["cases"]) * len(split_documents[1]["cases"]),
        )
        schedule_raw = git_output("show", f"{F2A}:evals/ae-sq4/f2/schedule.json")
        schedule = json.loads(schedule_raw)
        self.assertEqual(
            document["f2a_object"]["schedule"]["semantic_sha256"],
            validator.schedule_digest(schedule["presentations"]),
        )

    def test_frozen_runner_real_byte_boundary_rejects_exact_mismatch(self) -> None:
        document = strict(DECISION_PATH.read_bytes())
        runner = git_output("show", f"{F1A}:scripts/run_ae_sq4_aq.py")
        self.assertEqual(
            document["frozen_program"]["f1a"]["runner_raw_sha256"],
            hashlib.sha256(runner).hexdigest(),
        )
        checker, runner_module, validator = frozen_modules()
        self.assertEqual(
            hashlib.sha256(
                (ROOT / "scripts/run_ae_sq4_aq.py").read_bytes()
            ).hexdigest(),
            document["frozen_program"]["f1a"]["runner_raw_sha256"],
        )
        profile = checker.load_verified_candidate(ROOT, F1B, require_live=False)
        manifest_raw = git_output("show", f"{F2A}:evals/ae-sq4/f2/corpus-manifest.json")
        manifest = json.loads(manifest_raw)
        split_raws = [
            git_output("show", f"{F2A}:evals/ae-sq4/f2/split-a.json"),
            git_output("show", f"{F2A}:evals/ae-sq4/f2/split-b.json"),
        ]
        split_documents = [json.loads(raw) for raw in split_raws]
        inventory_raw = git_output(
            "show", f"{F1A}:evals/ae-sq4/f1/historical-task-digests.json"
        )
        schedule_raw = git_output("show", f"{F2A}:evals/ae-sq4/f2/schedule.json")
        schedule = json.loads(schedule_raw)
        validation = validator.validate_corpora(
            split_raws, historical_digest_inventory=inventory_raw
        )
        with self.assertRaisesRegex(
            runner_module.PreflightError,
            "^corpus split authority is not the frozen F1 candidate$",
        ):
            runner_module._validate_corpus_manifest_document(
                raw=manifest_raw,
                run_manifest={
                    "f1_freeze": manifest["f1_freeze"],
                    "implementation_freeze": manifest["implementation_freeze"],
                },
                run_schema=profile["documents"]["run_manifest_schema"],
                profile=profile,
                split_raws=split_raws,
                split_documents=split_documents,
                inventory_raw=inventory_raw,
                schedule_raw=schedule_raw,
                schedule_digest=validator.schedule_digest(schedule["presentations"]),
                validation=validation,
                validator=validator,
            )

    def test_terminal_plan_is_closed(self) -> None:
        plan = PLAN_PATH.read_text(encoding="utf-8")
        for text in (
            "TERMINAL — SQ4-AR",
            "SQ4-F2:NOT_PASS -> SQ4-AR",
            "PreflightError: corpus split authority is not the frozen F1 candidate",
            "zero diagnostic, canary, batch, or other model calls",
            "refs/remotes/origin/codex/ae-sq4-f2-not-pass",
            "docs/exec-plans/active/ae-sq5.md",
        ):
            self.assertIn(text, plan)

    def test_mutations_fail_closed(self) -> None:
        document = strict(DECISION_PATH.read_bytes())
        for path, value in (
            (("status",), "active"),
            (("stop",), False),
            (("claim_ceiling",), "qualification-PASS"),
            (("terminal_reason",), "changed"),
            (("frozen_program", "f0", "program_authority_blob"), "0" * 40),
            (("frozen_program", "f0", "program_authority_raw_sha256"), "0" * 64),
            (("frozen_program", "f0", "preterminal_active_plan_blob"), "0" * 40),
            (("frozen_program", "f0", "preterminal_active_plan_raw_sha256"), "0" * 64),
            (("frozen_program", "f1a", "parent"), "0" * 40),
            (("frozen_program", "f1a", "status"), "NOT_PASS"),
            (("frozen_program", "f1b", "parent"), "0" * 40),
            (("frozen_program", "f1b", "freeze_blob"), "0" * 40),
            (("frozen_program", "f1b", "freeze_raw_sha256"), "0" * 64),
            (("f2a_object", "status"), "PASS"),
            (("f2a_object", "tree"), "0" * 40),
            (("f2a_object", "schedule", "semantic_sha256"), "0" * 64),
            (("durable_evidence_refs", "evidence_commit"), "0" * 40),
            (("durable_evidence_refs", "local_branch", "name"), "refs/heads/main"),
            (
                ("durable_evidence_refs", "remote_tracking_branch", "target"),
                "0" * 40,
            ),
            (("durable_evidence_refs", "ref_mutation_authorized"), True),
            (("standalone_validation", "errors"), ["hidden"]),
            (("standalone_validation", "maximum_similarity"), 0.1),
            (("standalone_validation", "maximum_similarity_threshold"), 0.9),
            (("standalone_validation", "combined_corpus_sha256"), "0" * 64),
            (("standalone_validation", "qualification_effect"), "F2-PASS"),
            (("frozen_runtime_rejection", "route"), "SQ4-F3"),
            (("phase_status", "SQ4_F4"), "PASS"),
            (("phase_status", "SQ4_F5"), "completed"),
            (("live_call_accounting", "canary_calls"), 4),
            (
                ("preservation", "sq4_candidate_identity_or_bytes_reuse_permitted"),
                True,
            ),
            (("preservation", "sq4_split_or_f2a_reuse_permitted"), True),
            (("successor_route",), "same-program-retry"),
            (
                ("terminal_edges",),
                strict(DECISION_PATH.read_bytes())["terminal_edges"]
                + ["SQ4-AR->SQ4-F3"],
            ),
        ):
            mutation = copy.deepcopy(document)
            target: Any = mutation
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate(mutation)
        extension = copy.deepcopy(document)
        extension["frozen_runtime_rejection"]["extra"] = True
        with self.assertRaises(ValueError):
            validate(extension)
        extension = copy.deepcopy(document)
        extension["sealed_author_objects"][0]["extra"] = True
        with self.assertRaises(ValueError):
            validate(extension)
        with self.assertRaises(ValueError):
            strict(b'{"status":"terminal","status":"active"}')
        with self.assertRaises(ValueError):
            strict(b'{"value":NaN}')


if __name__ == "__main__":
    unittest.main()
