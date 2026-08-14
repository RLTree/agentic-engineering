"""Synthetic-only contract tests for the AE-SQ8 fresh AQ corpus pair."""

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


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_ae_sq8_corpus as validator  # noqa: E402


HISTORICAL_PATH = ROOT / "evals/ae-sq4/f1/historical-task-digests.json"
GATES_PATH = ROOT / "evals/ae-sq8/f1/gates.json"
INVOCATIONS = {
    "s0": "$agentic-engineering-lifecycle:agentic-engineering",
    "s1": "$agentic-engineering:codex-task-contract",
    "s2": "$agentic-engineering:verification-strategy-engineering",
    "s3": "$agentic-engineering:engineering-learning-loop",
}


def _specifications() -> list[tuple[str, tuple[str, ...], str | None]]:
    specs: list[tuple[str, tuple[str, ...], str | None]] = []
    specs.extend(("none", (), None) for _ in range(6))
    for _ in range(4):
        specs.extend(("single", (slot,), None) for slot in validator.SLOT_ORDER)
    pairs = sorted(validator.ALL_PAIRS) + [("s0", "s1"), ("s2", "s3")]
    specs.extend(("two", pair, None) for pair in pairs)
    specs.extend(("cap", ("s0", "s1", "s2"), None) for _ in range(4))
    specs.extend(("explicit", (slot,), slot) for slot in validator.SLOT_ORDER)
    specs.extend(("uncertain", (), None) for _ in range(2))
    assert len(specs) == 40
    return specs


def historical_bytes() -> bytes:
    return HISTORICAL_PATH.read_bytes()


def make_pair() -> tuple[dict, dict]:
    inventory_sha = hashlib.sha256(historical_bytes()).hexdigest()
    contracts = validator.contract_digests()
    authority = {
        "program_id": "AE-SQ8",
        "candidate_id": "AE-SQ8-SLEC-8",
        "candidate_commit": "a" * 40,
        "candidate_tree": "b" * 40,
        "f1_freeze_sha256": "c" * 64,
        **contracts,
    }
    specs = _specifications()
    documents = []
    for split_index, split_id in enumerate(("A", "B")):
        split_nonce = ("1" if split_id == "A" else "2") * 64
        cases = []
        for local_index in range(20):
            global_index = split_index * 20 + local_index
            profile, selected, explicit = specs[global_index]
            task = (
                f"Aurora lattice inquiry {local_index + 1:02d} asks for a bounded systems judgment "
                f"with independent anchors and cobalt evidence {global_index:02d}."
                if split_id == "A"
                else f"Juniper harbor brief {local_index + 1:02d} requests a careful operational choice "
                f"using separate sources and vermilion constraints {global_index:02d}."
            )
            if profile == "explicit" and explicit is not None:
                task = f"{task} Invoke {INVOCATIONS[explicit]} exactly."
            task_sha = validator.task_digest(task)
            capsules = []
            for slot in validator.SLOT_ORDER:
                local_need = "yes" if slot in selected else "no"
                reference_need = "focused" if slot in selected else "none"
                if profile == "uncertain" and slot == "s0":
                    local_need, reference_need = "uncertain", "uncertain"
                anchors = (
                    []
                    if "uncertain" in (local_need, reference_need)
                    else [{"start": 0, "end": len(task), "text": task}]
                )
                capsules.append(
                    {
                        "slot_id": slot,
                        "local_need": local_need,
                        "reference_need": reference_need,
                        "anchors": anchors,
                    }
                )
            case_id = f"AE-SQ8-{split_id}-{local_index + 1:02d}"
            cases.append(
                {
                    "case_id": case_id,
                    "case_nonce": validator.expected_case_nonce(
                        split_nonce, case_id, task_sha
                    ),
                    "task_text": task,
                    "task_text_nfc_sha256": task_sha,
                    "profile": profile,
                    "explicit_slot_id": explicit,
                    "expected_capsules": capsules,
                    "expected_resolution": validator.resolve_expected_capsules(
                        task, "current", capsules
                    ),
                }
            )
        documents.append(
            {
                "schema_version": "1.0",
                "program_id": "AE-SQ8",
                "corpus_id": "AE-SQ8-AQ-FRESH-V1",
                "split_id": split_id,
                "split_nonce": split_nonce,
                "author_id": f"synthetic-author-{split_id.lower()}",
                "authority": copy.deepcopy(authority),
                "no_replay": {
                    "normalization_id": "ae-sq8-task-v1",
                    "historical_digest_inventory_sha256": inventory_sha,
                    "historical_inventory_content_sha256": validator.TRUSTED_HISTORICAL_CONTENT_SHA256,
                    "historical_inventory_count": 768,
                    "historical_text_embedded": False,
                    "predecessor_case_label_or_result_material_embedded": False,
                },
                "cases": cases,
            }
        )
    return documents[0], documents[1]


def qualification_validate(documents, *, historical_digest_inventory=None):
    try:
        first = validator._as_document(documents[0])
    except validator.CorpusContractError:
        first = make_pair()[0]
    return validator.validate_corpora(
        documents,
        historical_digest_inventory=historical_digest_inventory,
        expected_authority=first["authority"],
    )


class AeSq8CorpusContractTests(unittest.TestCase):
    def test_expected_split_authority_rejects_string_shaped_false_custody(
        self,
    ) -> None:
        contracts = validator.contract_digests()
        profile = {
            "program_id": "AE-SQ8",
            "candidate_id": "AE-SQ8-SLEC-8",
            "implementation_commit": "1" * 40,
            "implementation_tree": "2" * 40,
            "freeze_commit": "3" * 40,
            "freeze_sha256": "4" * 64,
            "bindings": {
                "corpus_schema": {"sha256": contracts["corpus_contract_sha256"]},
                "gates": {"sha256": contracts["gates_sha256"]},
                "metrics": {"sha256": contracts["metrics_sha256"]},
                "evaluator_schema": {"sha256": contracts["evaluator_schema_sha256"]},
            },
        }
        expected = validator.expected_split_authority(profile)
        self.assertEqual("1" * 40, expected["candidate_commit"])
        self.assertEqual("4" * 64, expected["f1_freeze_sha256"])

        for field, invalid in (
            ("implementation_commit", "not-a-commit"),
            ("implementation_tree", "f" * 39),
            ("freeze_sha256", "g" * 64),
        ):
            mutated = copy.deepcopy(profile)
            mutated[field] = invalid
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(
                    validator.CorpusContractError, "identity is invalid"
                ),
            ):
                validator.expected_split_authority(mutated)

        mutated = copy.deepcopy(profile)
        mutated["bindings"]["metrics"]["sha256"] = "0" * 63
        with self.assertRaisesRegex(
            validator.CorpusContractError, "identity is invalid"
        ):
            validator.expected_split_authority(mutated)

    def test_selected_reference_anchor_production_fixture_and_reds(self) -> None:
        self.assertEqual(
            validator.selected_reference_anchor_fixture(),
            {
                "production_validator": (
                    "validate_corpora:selected_reference_anchors_valid"
                ),
                "production_resolver": "resolve_expected_capsules",
                "positive": {"status": "PASS"},
                "red_missing": {
                    "error": "selected_reference_anchor",
                    "status": "REJECTED",
                },
                "red_wrong": {
                    "error": "selected_reference_anchor",
                    "status": "REJECTED",
                },
            },
        )

        pair = make_pair()
        for reference_need, anchors in (("none", None), ("uncertain", [])):
            mutated = copy.deepcopy(pair[0])
            capsule = mutated["cases"][6]["expected_capsules"][0]
            capsule["reference_need"] = reference_need
            if anchors is not None:
                capsule["anchors"] = anchors
            mutated["cases"][6]["expected_resolution"] = (
                validator.resolve_expected_capsules(
                    mutated["cases"][6]["task_text"],
                    "current",
                    mutated["cases"][6]["expected_capsules"],
                )
            )
            result = qualification_validate(
                (mutated, pair[1]),
                historical_digest_inventory=historical_bytes(),
            )
            self.assertIn("selected_reference_anchor", result.errors)

    def test_json_authorities_have_exactly_one_terminal_newline(self) -> None:
        for path in (GATES_PATH, HISTORICAL_PATH):
            raw = path.read_bytes()
            self.assertEqual(b"}\n", raw[-2:], path)
            self.assertFalse(raw.endswith(b"\n\n"), path)

    def test_valid_pair_holds_without_inventory_and_passes_with_exact_authority(
        self,
    ) -> None:
        pair = make_pair()
        held = validator.validate_corpora(pair)
        self.assertEqual("hold", held.status)
        self.assertTrue(held.structurally_valid)
        passed = qualification_validate(
            pair, historical_digest_inventory=historical_bytes()
        )
        self.assertTrue(passed.passed, (passed.errors, passed.holds))
        self.assertEqual(40, passed.metrics["total_cases"])
        self.assertEqual(400, passed.metrics["cross_split_similarity_checks"])
        self.assertEqual(768, passed.metrics["historical_digest_count"])
        explicit_cases = [
            case
            for document in pair
            for case in document["cases"]
            if case["profile"] == "explicit"
        ]
        self.assertEqual(4, len(explicit_cases))
        self.assertTrue(
            all(
                case["expected_resolution"]
                == {
                    "status": "selected",
                    "selected_slots": [case["explicit_slot_id"]],
                    "reference_bundle": [],
                }
                for case in explicit_cases
            )
        )

    def test_strict_utf8_duplicate_nonfinite_and_nfc_rejected_without_echo(
        self,
    ) -> None:
        pair = make_pair()
        raw = json.dumps(pair[0], ensure_ascii=False, separators=(",", ":")).encode()
        duplicate = raw.replace(
            b'{"schema_version":"1.0"',
            b'{"schema_version":"1.0","schema_version":"1.0"',
            1,
        )
        malformed = (
            duplicate,
            b'{"value":NaN}',
            b"\xff",
        )
        for candidate in malformed:
            result = qualification_validate((candidate, pair[1]))
            self.assertEqual("fail", result.status)
            self.assertNotIn(pair[0]["cases"][0]["task_text"], repr(result))
        decomposed = copy.deepcopy(pair[0])
        decomposed["cases"][0]["task_text"] += " e\u0301"
        self.assertEqual("fail", qualification_validate((decomposed, pair[1])).status)

    def test_identity_digest_profile_distribution_and_derivation_reds(self) -> None:
        pair = make_pair()
        mutations = []
        bad = copy.deepcopy(pair[0])
        bad["cases"][0]["case_id"] = "AE-SQ8-A-20"
        mutations.append(bad)
        bad = copy.deepcopy(pair[0])
        bad["cases"][0]["case_nonce"] = "f" * 64
        mutations.append(bad)
        bad = copy.deepcopy(pair[0])
        bad["cases"][0]["task_text_nfc_sha256"] = "f" * 64
        mutations.append(bad)
        bad = copy.deepcopy(pair[0])
        bad["cases"][0]["profile"] = "single"
        mutations.append(bad)
        bad = copy.deepcopy(pair[0])
        (
            bad["cases"][6]["expected_capsules"][0],
            bad["cases"][6]["expected_capsules"][1],
        ) = (
            bad["cases"][6]["expected_capsules"][1],
            bad["cases"][6]["expected_capsules"][0],
        )
        mutations.append(bad)
        bad = copy.deepcopy(pair[0])
        bad["cases"][6]["expected_resolution"]["selected_slots"] = []
        mutations.append(bad)
        for mutation in mutations:
            self.assertEqual(
                "fail",
                qualification_validate(
                    (mutation, pair[1]), historical_digest_inventory=historical_bytes()
                ).status,
            )

    def test_cli_requires_exact_historical_inventory_and_emits_aggregate_only(
        self,
    ) -> None:
        pair = make_pair()
        script = ROOT / "scripts/validate_ae_sq8_corpus.py"
        secret_task = pair[0]["cases"][0]["task_text"]
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            split_a = temporary / "split-a.json"
            split_b = temporary / "split-b.json"
            inventory = temporary / "historical.json"
            substituted = temporary / "substituted.json"
            split_a.write_bytes(validator.canonical_json(pair[0]))
            split_b.write_bytes(validator.canonical_json(pair[1]))
            inventory.write_bytes(historical_bytes())
            substituted.write_bytes(b"{}\n")

            unverified = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--freeze-commit",
                    "0" * 40,
                    "--historical-inventory",
                    str(inventory),
                    str(split_a),
                    str(split_b),
                ],
                cwd=temporary,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(1, unverified.returncode)

            missing = subprocess.run(
                [sys.executable, str(script), str(split_a), str(split_b)],
                cwd=temporary,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, missing.returncode)

            rejected = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--freeze-commit",
                    "0" * 40,
                    "--historical-inventory",
                    str(substituted),
                    str(split_a),
                    str(split_b),
                ],
                cwd=temporary,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(1, rejected.returncode)

            combined = (
                unverified.stdout + unverified.stderr + missing.stdout + missing.stderr
            )
            combined += rejected.stdout + rejected.stderr
            self.assertNotIn(secret_task, combined)

    def test_cross_split_exact_and_near_collision_and_forbidden_binding_reds(
        self,
    ) -> None:
        pair = make_pair()
        exact = copy.deepcopy(pair[1])
        exact["cases"][0]["task_text"] = pair[0]["cases"][0]["task_text"]
        task_sha = validator.task_digest(exact["cases"][0]["task_text"])
        exact["cases"][0]["task_text_nfc_sha256"] = task_sha
        exact["cases"][0]["case_nonce"] = validator.expected_case_nonce(
            exact["split_nonce"], exact["cases"][0]["case_id"], task_sha
        )
        result = qualification_validate(
            (pair[0], exact), historical_digest_inventory=historical_bytes()
        )
        self.assertIn("exact_task_collision", result.errors)

        near = copy.deepcopy(pair[1])
        near_text = pair[0]["cases"][0]["task_text"] + " Additional bounded note."
        task_sha = validator.task_digest(near_text)
        near["cases"][0]["task_text"] = near_text
        near["cases"][0]["task_text_nfc_sha256"] = task_sha
        near["cases"][0]["case_nonce"] = validator.expected_case_nonce(
            near["split_nonce"], near["cases"][0]["case_id"], task_sha
        )
        result = qualification_validate(
            (pair[0], near), historical_digest_inventory=historical_bytes()
        )
        self.assertIn("cross_split_near_collision", result.errors)

        forbidden = copy.deepcopy(pair[0])
        forbidden["prior_outcome_digest"] = "0" * 64
        self.assertEqual("fail", qualification_validate((forbidden, pair[1])).status)
        self_attested = copy.deepcopy(pair[0])
        self_attested["independence"] = {
            "single_author": True,
            "other_split_access": False,
        }
        self.assertEqual(
            "fail", qualification_validate((self_attested, pair[1])).status
        )
        authority_attested = copy.deepcopy(pair[0])
        authority_attested["authority"]["outcome_blind_at_authoring"] = True
        self.assertEqual(
            "fail", qualification_validate((authority_attested, pair[1])).status
        )

    def test_historical_inventory_is_exact_20_source_768_digest_authority(
        self,
    ) -> None:
        pair = make_pair()
        trusted_raw = historical_bytes()
        self.assertEqual(
            validator.TRUSTED_HISTORICAL_INVENTORY_SHA256,
            hashlib.sha256(trusted_raw).hexdigest(),
        )
        original = json.loads(trusted_raw)
        self.assertEqual(20, len(original["sources"]))
        self.assertEqual(768, original["inventory_count"])
        self.assertEqual(
            validator.TRUSTED_HISTORICAL_CONTENT_SHA256,
            hashlib.sha256(
                ("\n".join(original["task_text_nfc_sha256"]) + "\n").encode("ascii")
            ).hexdigest(),
        )
        passed = qualification_validate(pair, historical_digest_inventory=trusted_raw)
        self.assertTrue(passed.passed, (passed.errors, passed.holds))
        self.assertEqual(768, passed.metrics["historical_digest_count"])

        whitespace_mutation = trusted_raw + b"\n"
        result = qualification_validate(
            pair, historical_digest_inventory=whitespace_mutation
        )
        self.assertIn("historical_inventory", result.errors)

        mutations = []
        extra_source = copy.deepcopy(original)
        extra_source["sources"].append(copy.deepcopy(extra_source["sources"][-1]))
        mutations.append(extra_source)
        reordered_sources = copy.deepcopy(original)
        reordered_sources["sources"].reverse()
        mutations.append(reordered_sources)
        truncated = copy.deepcopy(original)
        truncated["task_text_nfc_sha256"].pop()
        truncated["inventory_count"] = 767
        truncated["inventory_sha256"] = hashlib.sha256(
            ("\n".join(truncated["task_text_nfc_sha256"]) + "\n").encode("ascii")
        ).hexdigest()
        mutations.append(truncated)
        elevated = copy.deepcopy(original)
        elevated["limitations"]["semantic_similarity_proven"] = True
        mutations.append(elevated)
        for mutation in mutations:
            raw = json.dumps(
                mutation,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
            result = qualification_validate(
                pair,
                historical_digest_inventory=raw,
            )
            self.assertIn("historical_inventory", result.errors)

    def test_schedule_is_exact_deterministic_alternating_80_rows(self) -> None:
        pair = make_pair()
        ids = [case["case_id"] for document in pair for case in document["cases"]]
        first = validator.build_schedule(ids)
        second = validator.build_schedule(tuple(reversed(ids)))
        self.assertEqual(first, second)
        self.assertEqual(80, len(first))
        self.assertEqual(set(range(80)), {row["presentation_index"] for row in first})
        self.assertTrue(
            all(
                first[index]["condition"] != first[index + 1]["condition"]
                for index in range(79)
            )
        )
        self.assertTrue(
            all(sum(row["case_id"] == case_id for row in first) == 2 for case_id in ids)
        )

    def test_validation_is_zero_write_and_never_prints_task_text(self) -> None:
        pair = make_pair()
        with tempfile.TemporaryDirectory() as directory:
            before = set(os.listdir(directory))
            previous = Path.cwd()
            try:
                os.chdir(directory)
                result = qualification_validate(
                    pair, historical_digest_inventory=historical_bytes()
                )
            finally:
                os.chdir(previous)
            self.assertTrue(result.passed)
            self.assertEqual(before, set(os.listdir(directory)))


if __name__ == "__main__":
    unittest.main()
