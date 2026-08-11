"""Synthetic-only contract tests for the AE-SQ1 fresh AQ corpus pair."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_ae_sq1_corpus as validator  # noqa: E402


HISTORICAL_PATH = ROOT / "evals/ae-sq1/historical-task-digests.json"


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
        "program_id": "AE-SQ1",
        "candidate_id": "slec-1-test",
        "candidate_commit": "a" * 40,
        "candidate_tree": "b" * 40,
        "candidate_manifest_sha256": "c" * 64,
        **contracts,
        "outcome_blind_at_authoring": True,
        "prior_corpus_text_access": False,
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
            task_sha = validator.task_digest(task)
            capsules = []
            for slot in validator.SLOT_ORDER:
                local_need = "yes" if slot in selected else "no"
                reference_need = "focused" if slot in selected else "none"
                if profile == "uncertain" and slot == "s0":
                    local_need, reference_need = "uncertain", "uncertain"
                capsules.append(
                    {
                        "slot_id": slot,
                        "local_need": local_need,
                        "reference_need": reference_need,
                    }
                )
            case_id = f"AE-SQ1-{split_id}-{local_index + 1:02d}"
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
                    "expected_resolution": validator.resolve_capsules(capsules),
                }
            )
        documents.append(
            {
                "schema_version": "1.0",
                "program_id": "AE-SQ1",
                "corpus_id": "AE-SQ1-AQ-FRESH-V1",
                "split_id": split_id,
                "split_nonce": split_nonce,
                "authority": copy.deepcopy(authority),
                "no_replay": {
                    "normalization_id": "ae-sq1-task-v1",
                    "historical_digest_inventory_sha256": inventory_sha,
                    "historical_text_embedded": False,
                },
                "cases": cases,
            }
        )
    return documents[0], documents[1]


class AeSq1CorpusContractTests(unittest.TestCase):
    def test_valid_pair_holds_without_inventory_and_passes_with_exact_authority(
        self,
    ) -> None:
        pair = make_pair()
        held = validator.validate_corpora(pair)
        self.assertEqual("hold", held.status)
        self.assertTrue(held.structurally_valid)
        passed = validator.validate_corpora(
            pair, historical_digest_inventory=historical_bytes()
        )
        self.assertTrue(passed.passed, (passed.errors, passed.holds))
        self.assertEqual(40, passed.metrics["total_cases"])
        self.assertEqual(400, passed.metrics["cross_split_similarity_checks"])
        self.assertEqual(504, passed.metrics["historical_digest_count"])

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
            result = validator.validate_corpora((candidate, pair[1]))
            self.assertEqual("fail", result.status)
            self.assertNotIn(pair[0]["cases"][0]["task_text"], repr(result))
        decomposed = copy.deepcopy(pair[0])
        decomposed["cases"][0]["task_text"] += " e\u0301"
        self.assertEqual(
            "fail", validator.validate_corpora((decomposed, pair[1])).status
        )

    def test_identity_digest_profile_distribution_and_derivation_reds(self) -> None:
        pair = make_pair()
        mutations = []
        bad = copy.deepcopy(pair[0])
        bad["cases"][0]["case_id"] = "AE-SQ1-A-20"
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
                validator.validate_corpora(
                    (mutation, pair[1]), historical_digest_inventory=historical_bytes()
                ).status,
            )

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
        result = validator.validate_corpora(
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
        result = validator.validate_corpora(
            (pair[0], near), historical_digest_inventory=historical_bytes()
        )
        self.assertIn("cross_split_near_collision", result.errors)

        forbidden = copy.deepcopy(pair[0])
        forbidden["prior_outcome_digest"] = "0" * 64
        self.assertEqual(
            "fail", validator.validate_corpora((forbidden, pair[1])).status
        )

    def test_historical_inventory_is_pinned_closed_complete_and_recomputed(
        self,
    ) -> None:
        pair = make_pair()
        trusted_raw = historical_bytes()
        self.assertEqual(
            validator.TRUSTED_HISTORICAL_INVENTORY_SHA256,
            hashlib.sha256(trusted_raw).hexdigest(),
        )
        original = json.loads(trusted_raw)
        self.assertEqual("1.1", original["schema_version"])
        self.assertEqual(list(validator.HISTORICAL_SOURCE), list(original["source"]))
        self.assertEqual(validator.HISTORICAL_SOURCE, original["source"])
        self.assertEqual(
            validator.TRUSTED_HISTORICAL_CONTENT_SHA256,
            hashlib.sha256(
                ("\n".join(original["task_text_nfc_sha256"]) + "\n").encode("ascii")
            ).hexdigest(),
        )
        self.assertEqual(
            [row[3] for row in validator.HISTORICAL_FILE_ROWS],
            [row["task_text_selector"] for row in original["files"]],
        )
        self.assertTrue(
            validator.validate_corpora(
                pair, historical_digest_inventory=trusted_raw
            ).passed
        )

        whitespace_mutation = trusted_raw + b"\n"
        result = validator.validate_corpora(
            pair, historical_digest_inventory=whitespace_mutation
        )
        self.assertIn("historical_inventory", result.errors)

        mapping_result = validator.validate_corpora(
            pair,
            historical_digest_inventory=original,  # type: ignore[arg-type]
        )
        self.assertIn("historical_inventory", mapping_result.errors)
        mutations = []

        old_schema = copy.deepcopy(original)
        old_schema["schema_version"] = "1.0"
        mutations.append(old_schema)

        empty = copy.deepcopy(original)
        empty["task_text_nfc_sha256"] = []
        empty["inventory_count"] = 0
        empty["inventory_sha256"] = hashlib.sha256(b"").hexdigest()
        mutations.append(empty)

        truncated = copy.deepcopy(original)
        truncated["task_text_nfc_sha256"] = truncated["task_text_nfc_sha256"][:-1]
        truncated["inventory_count"] = 503
        truncated["inventory_sha256"] = hashlib.sha256(
            ("\n".join(truncated["task_text_nfc_sha256"]) + "\n").encode()
        ).hexdigest()
        mutations.append(truncated)

        substituted = copy.deepcopy(original)
        substituted["task_text_nfc_sha256"][0] = "0" * 64
        substituted["task_text_nfc_sha256"].sort()
        substituted["inventory_sha256"] = hashlib.sha256(
            ("\n".join(substituted["task_text_nfc_sha256"]) + "\n").encode()
        ).hexdigest()
        mutations.append(substituted)

        wrong_source = copy.deepcopy(original)
        wrong_source["source"]["commit"] = "f" * 40
        mutations.append(wrong_source)

        missing_source = copy.deepcopy(original)
        missing_source["source"].pop("task_digest_derivation")
        mutations.append(missing_source)

        extra_source = copy.deepcopy(original)
        extra_source["source"]["extra"] = "forbidden"
        mutations.append(extra_source)

        reordered_source = copy.deepcopy(original)
        reordered_source["source"] = {
            key: reordered_source["source"][key]
            for key in reversed(reordered_source["source"])
        }
        mutations.append(reordered_source)

        wrong_file = copy.deepcopy(original)
        wrong_file["files"][0]["sha256"] = "f" * 64
        mutations.append(wrong_file)

        wrong_selector = copy.deepcopy(original)
        wrong_selector["files"][0]["task_text_selector"] = "cases[].prompt_sha256"
        mutations.append(wrong_selector)

        missing_file = copy.deepcopy(original)
        missing_file["files"] = missing_file["files"][:-1]
        mutations.append(missing_file)

        extra_file = copy.deepcopy(original)
        extra_file["files"].append(copy.deepcopy(extra_file["files"][-1]))
        mutations.append(extra_file)

        reordered_file = copy.deepcopy(original)
        reordered_file["files"][0], reordered_file["files"][1] = (
            reordered_file["files"][1],
            reordered_file["files"][0],
        )
        mutations.append(reordered_file)

        duplicate_file = copy.deepcopy(original)
        duplicate_file["files"][1] = copy.deepcopy(duplicate_file["files"][0])
        mutations.append(duplicate_file)

        reordered_tasks = copy.deepcopy(original)
        reordered_tasks["task_text_nfc_sha256"].reverse()
        mutations.append(reordered_tasks)

        duplicate_task = copy.deepcopy(original)
        duplicate_task["task_text_nfc_sha256"][1] = duplicate_task[
            "task_text_nfc_sha256"
        ][0]
        mutations.append(duplicate_task)

        extra_task = copy.deepcopy(original)
        extra_task["task_text_nfc_sha256"].append("f" * 64)
        extra_task["inventory_count"] = 505
        mutations.append(extra_task)

        elevated = copy.deepcopy(original)
        elevated["limitations"]["semantic_similarity_proven"] = True
        mutations.append(elevated)

        for mutation in mutations:
            mutation_raw = json.dumps(
                mutation,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
            trusted_mutation_sha = hashlib.sha256(mutation_raw).hexdigest()
            rebound = copy.deepcopy(pair)
            for document in rebound:
                document["no_replay"]["historical_digest_inventory_sha256"] = (
                    trusted_mutation_sha
                )
            result = validator.validate_corpora(
                rebound,
                historical_digest_inventory=mutation_raw,
                trusted_historical_inventory_sha256=trusted_mutation_sha,
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
                result = validator.validate_corpora(
                    pair, historical_digest_inventory=historical_bytes()
                )
            finally:
                os.chdir(previous)
            self.assertTrue(result.passed)
            self.assertEqual(before, set(os.listdir(directory)))


if __name__ == "__main__":
    unittest.main()
