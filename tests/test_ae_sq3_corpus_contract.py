"""Synthetic-only contract tests for the AE-SQ3 fresh AQ corpus pair."""

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

import validate_ae_sq3_corpus as validator  # noqa: E402


HISTORICAL_PATH = ROOT / "evals/ae-sq3/f1/historical-task-digests.json"
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
        "program_id": "AE-SQ3",
        "candidate_id": "AE-SQ3-SLEC-3",
        "candidate_commit": "a" * 40,
        "candidate_tree": "b" * 40,
        "f1_freeze_sha256": "c" * 64,
        **contracts,
        "outcome_blind_at_authoring": True,
        "predecessor_material_access": False,
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
            case_id = f"AE-SQ3-{split_id}-{local_index + 1:02d}"
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
                "program_id": "AE-SQ3",
                "corpus_id": "AE-SQ3-AQ-FRESH-V1",
                "split_id": split_id,
                "split_nonce": split_nonce,
                "author_id": f"synthetic-author-{split_id.lower()}",
                "independence": {
                    "single_author": True,
                    "other_split_access": False,
                    "predecessor_task_case_corpus_or_label_access": False,
                    "diagnostic_model_material_or_live_result_access": False,
                },
                "authority": copy.deepcopy(authority),
                "no_replay": {
                    "normalization_id": "ae-sq3-task-v1",
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


class AeSq3CorpusContractTests(unittest.TestCase):
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
        bad["cases"][0]["case_id"] = "AE-SQ3-A-20"
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
                ("\n".join(original["task_text_nfc_sha256"]) + "\n").encode(
                    "ascii"
                )
            ).hexdigest(),
        )
        passed = validator.validate_corpora(
            pair, historical_digest_inventory=trusted_raw
        )
        self.assertTrue(passed.passed, (passed.errors, passed.holds))
        self.assertEqual(768, passed.metrics["historical_digest_count"])

        whitespace_mutation = trusted_raw + b"\n"
        result = validator.validate_corpora(
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
            result = validator.validate_corpora(
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
                result = validator.validate_corpora(
                    pair, historical_digest_inventory=historical_bytes()
                )
            finally:
                os.chdir(previous)
            self.assertTrue(result.passed)
            self.assertEqual(before, set(os.listdir(directory)))


if __name__ == "__main__":
    unittest.main()
