from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
F1 = ROOT / "evals/ae-sq3/f1"
RESOLVER = ROOT / "scripts/resolve_ae_sq3_slec.py"
SPEC = importlib.util.spec_from_file_location("resolve_ae_sq3_slec", RESOLVER)
assert SPEC is not None and SPEC.loader is not None
SLEC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SLEC)


def trusted(path: Path) -> tuple[bytes, str]:
    raw = path.read_bytes()
    return raw, hashlib.sha256(raw).hexdigest()


def custody(value: object, *, compact: bool = True) -> tuple[bytes, str]:
    raw = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":") if compact else None,
    ).encode("ascii")
    return raw, hashlib.sha256(raw).hexdigest()


def anchor(task: str, text: str) -> dict[str, object]:
    start = task.index(text)
    return {"start": start, "end": start + len(text), "text": text}


def capsule(
    task: str,
    slot: str,
    local: str = "no",
    reference: str = "none",
    text: str | None = "unique",
) -> dict[str, object]:
    return {
        "slot_id": slot,
        "local_need": local,
        "reference_need": reference,
        "anchors": [] if text is None else [anchor(task, text)],
    }


class AESQ3SLECTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.authority = trusted(F1 / "slec3-authority.json")
        cls.policy = trusted(F1 / "slec3-reference-policy.json")
        cls.provider_schema = trusted(F1 / "slec3-capsule-schema.json")
        cls.semantic_schema = trusted(F1 / "slec3-semantic-capsule-schema.json")
        cls.resolution_schema = trusted(F1 / "slec3-resolution-schema.json")

    def setUp(self) -> None:
        self.task = "unique architecture acceptance verification learning"
        self.values = [capsule(self.task, slot) for slot in SLEC.SLOTS]

    def resolve(
        self, values: list[dict[str, object]] | None = None
    ) -> dict[str, object]:
        return SLEC.resolve_capsules(
            task=self.task,
            condition_id="current",
            capsule_ingresses=[custody(value) for value in (values or self.values)],
            authority_custody=self.authority,
            policy_custody=self.policy,
            resolution_schema_custody=self.resolution_schema,
            semantic_schema_custody=self.semantic_schema,
        )

    def test_real_frozen_bytes_end_to_end(self) -> None:
        provider = SLEC.validate_provider_schema(self.provider_schema, self.authority)
        self.assertEqual(provider["type"], "object")
        packet = SLEC.build_assessor_packet(self.task, "current", "s0", self.authority)
        self.assertEqual(packet["slot_id"], "s0")
        self.assertEqual(
            set(packet),
            set(
                json.loads(self.authority[0])["assessor_packet_contract"]["packet_keys"]
            ),
        )
        self.assertNotEqual(
            packet["condition_slot_card"],
            SLEC.build_assessor_packet(self.task, "reduced", "s0", self.authority)[
                "condition_slot_card"
            ],
        )
        record = self.resolve()
        self.assertEqual(record["resolution_status"], "no_selection")
        self.assertEqual(record["candidate_id"], "AE-SQ3-SLEC-3")
        self.assertEqual(record["mechanism_id"], "SLEC-3")

    def test_local_truth_table_and_cardinality(self) -> None:
        valid = [
            ("yes", "none", "unique"),
            ("yes", "core", "unique"),
            ("yes", "focused", "unique"),
            ("no", "none", "unique"),
            ("uncertain", "uncertain", None),
        ]
        for local, reference, text in valid:
            value = capsule(self.task, "s0", local, reference, text)
            with self.subTest(valid=(local, reference)):
                self.assertEqual(
                    SLEC.normalize_runtime_capsule(
                        self.task,
                        "s0",
                        custody(value),
                        self.authority,
                        self.semantic_schema,
                    )["local_need"],
                    local,
                )
        invalid = [
            capsule(self.task, "s0", "no", "core", "unique"),
            capsule(self.task, "s0", "uncertain", "core", None),
            capsule(self.task, "s0", "yes", "none", None),
            capsule(self.task, "s0", "uncertain", "uncertain", "unique"),
            capsule(self.task, "s0", "yes", "uncertain", "unique"),
        ]
        too_many = capsule(self.task, "s0")
        too_many["anchors"] = [anchor(self.task, "unique")] * 3
        invalid.append(too_many)
        for value in invalid:
            with self.subTest(invalid=value), self.assertRaises(SLEC.SLECError):
                SLEC.normalize_runtime_capsule(
                    self.task,
                    "s0",
                    custody(value),
                    self.authority,
                    self.semantic_schema,
                )

    def test_uncertainty_cross_product_matches_committed_sq1_semantics(self) -> None:
        local_values = ("yes", "no", "uncertain")
        reference_values = ("none", "core", "focused", "uncertain")
        for local in local_values:
            for reference in reference_values:
                uncertain = "uncertain" in (local, reference)
                value = capsule(
                    self.task,
                    "s0",
                    local,
                    reference,
                    None if uncertain else "unique",
                )
                sq1_accepts = not (
                    (local == "no" and reference != "none")
                    or (local == "uncertain" and reference != "uncertain")
                )
                with self.subTest(local=local, reference=reference):
                    if sq1_accepts:
                        normalized = SLEC.normalize_runtime_capsule(
                            self.task,
                            "s0",
                            custody(value),
                            self.authority,
                            self.semantic_schema,
                        )
                        self.assertEqual(normalized["reference_need"], reference)
                    else:
                        with self.assertRaises(SLEC.SLECError):
                            SLEC.normalize_runtime_capsule(
                                self.task,
                                "s0",
                                custody(value),
                                self.authority,
                                self.semantic_schema,
                            )

    def test_yes_uncertain_reaches_fold_as_abstain_uncertain(self) -> None:
        values = deepcopy(self.values)
        values[0] = capsule(self.task, "s0", "yes", "uncertain", None)
        record = self.resolve(values)
        self.assertEqual(record["resolution_status"], "abstain_uncertain")
        self.assertEqual(record["slot_outcomes"][0]["local_need"], "yes")
        self.assertEqual(record["slot_outcomes"][0]["reference_need"], "uncertain")

    def test_exact_raw_digest_and_json_key_custody(self) -> None:
        valid = capsule(self.task, "s0")
        raw, digest = custody(valid)
        self.assertEqual(
            SLEC.normalize_runtime_capsule(
                self.task, "s0", (raw, digest), self.authority, self.semantic_schema
            )["slot_id"],
            "s0",
        )
        invalid_ingress = [
            raw,
            valid,
            (raw, "0" * 64),
            [raw, digest],
            (bytearray(raw), digest),
        ]
        for ingress in invalid_ingress:
            with self.subTest(ingress=type(ingress)), self.assertRaises(SLEC.SLECError):
                SLEC.normalize_runtime_capsule(
                    self.task, "s0", ingress, self.authority, self.semantic_schema
                )
        duplicates = b'{"slot_id":"s0","slot_id":"s0","local_need":"no","reference_need":"none","anchors":[]}'
        nonfinite = b'{"slot_id":"s0","local_need":"no","reference_need":"none","anchors":[{"start":NaN,"end":6,"text":"unique"}]}'
        for bad in (duplicates, nonfinite, b"\xef\xbb\xbf" + raw, raw + b" garbage"):
            with self.assertRaises(SLEC.SLECError):
                SLEC.normalize_runtime_capsule(
                    self.task,
                    "s0",
                    (bad, hashlib.sha256(bad).hexdigest()),
                    self.authority,
                    self.semantic_schema,
                )

    def test_exact_order_bool_as_int_wrong_slot_and_anchor_mutations_rejected(
        self,
    ) -> None:
        value = capsule(self.task, "s0")
        reordered = {
            "local_need": "no",
            "slot_id": "s0",
            "reference_need": "none",
            "anchors": [anchor(self.task, "unique")],
        }
        extra = deepcopy(value)
        extra["extra"] = 1
        wrong_slot = deepcopy(value)
        wrong_slot["slot_id"] = "s1"
        boolean = deepcopy(value)
        boolean["anchors"][0]["start"] = False
        bad_slice = deepcopy(value)
        bad_slice["anchors"][0]["text"] = "wrong"
        repeated_task = "unique and unique"
        repeated = capsule(repeated_task, "s0")
        overlap = deepcopy(value)
        overlap["anchors"] = [anchor(self.task, "unique"), anchor(self.task, "unique")]
        cases = [
            (self.task, reordered),
            (self.task, extra),
            (self.task, wrong_slot),
            (self.task, boolean),
            (self.task, bad_slice),
            (repeated_task, repeated),
            (self.task, overlap),
        ]
        for task, mutation in cases:
            with self.subTest(mutation=mutation), self.assertRaises(SLEC.SLECError):
                SLEC.normalize_runtime_capsule(
                    task, "s0", custody(mutation), self.authority, self.semantic_schema
                )

    def test_parent_requires_exact_four_unique_slots_and_never_scans_invalid(
        self,
    ) -> None:
        cases = [
            self.values[:3],
            self.values + [deepcopy(self.values[0])],
            [deepcopy(self.values[0])] * 4,
        ]
        for values in cases:
            with mock.patch.object(
                SLEC, "_scan_invocations", side_effect=AssertionError("must not scan")
            ):
                record = self.resolve(values)
            self.assertEqual(record["resolution_status"], "abstain_invalid")
            self.assertEqual(record["selected_slots"], [])

    def test_local_invalid_never_reaches_fold_selection_or_broker(self) -> None:
        values = deepcopy(self.values)
        values[0]["reference_need"] = "core"
        with mock.patch.object(
            SLEC, "_scan_invocations", side_effect=AssertionError("must not scan")
        ):
            record = self.resolve(values)
        self.assertEqual(record["resolution_status"], "abstain_invalid")
        self.assertEqual(record["reference_capability_ids"], [])

    def test_semantic_schema_and_resolution_schema_are_active_and_pinned(self) -> None:
        semantic = json.loads(self.semantic_schema[0])
        semantic["properties"]["local_need"]["enum"] = ["yes"]
        with self.assertRaises(SLEC.SLECError):
            SLEC.normalize_runtime_capsule(
                self.task,
                "s0",
                custody(self.values[0]),
                self.authority,
                custody(semantic),
            )
        record = self.resolve()
        record_raw = custody(record)
        self.assertEqual(
            SLEC.verify_resolution_record(
                record_raw, self.authority, self.policy, self.resolution_schema
            ),
            record,
        )
        resolution = json.loads(self.resolution_schema[0])
        resolution["required"].remove("candidate_id")
        with self.assertRaises(SLEC.SLECError):
            SLEC.verify_resolution_record(
                record_raw, self.authority, self.policy, custody(resolution)
            )

    def test_resolve_capsules_validates_generated_record_schema_then_relations(
        self,
    ) -> None:
        valid = self.resolve()
        extra = deepcopy(valid)
        extra["unexpected"] = "forbidden"
        contradictory = deepcopy(valid)
        contradictory["resolution_status"] = "selected"
        contradictory["selected_slots"] = ["s0"]
        for mutation in (extra, contradictory):
            with self.subTest(mutation=mutation), mock.patch.object(
                SLEC, "fold", return_value=mutation
            ), self.assertRaises(SLEC.SLECError):
                SLEC.resolve_capsules(
                    task=self.task,
                    condition_id="current",
                    capsule_ingresses=[custody(value) for value in self.values],
                    authority_custody=self.authority,
                    policy_custody=self.policy,
                    resolution_schema_custody=self.resolution_schema,
                    semantic_schema_custody=self.semantic_schema,
                )

    def test_program_candidate_model_diagnostic_and_policy_binding_drift_rejected(
        self,
    ) -> None:
        mutations = []
        authority = json.loads(self.authority[0])
        for path, value in (
            (("f0_custody", "commit"), "0" * 40),
            (("candidate_id",), "other"),
            (("model_binding", "model_id"), "other"),
            (("repair_provenance", "diagnostic_binding", "raw_sha256"), "0" * 64),
            (("repair_provenance", "behavioral_tuning_permitted"), True),
            (("local_semantic_contract", "provider_validation_substitute"), True),
        ):
            mutation = deepcopy(authority)
            target = mutation
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            mutations.append(mutation)
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(SLEC.SLECError):
                SLEC.validate_provider_schema(self.provider_schema, custody(mutation))
        policy = json.loads(self.policy[0])
        policy["capability_catalog"][0]["file"]["sha256"] = "0" * 64
        with self.assertRaises(SLEC.SLECError):
            SLEC.resolve_capsules(
                task=self.task,
                condition_id="current",
                capsule_ingresses=[custody(v) for v in self.values],
                authority_custody=self.authority,
                policy_custody=custody(policy),
                resolution_schema_custody=self.resolution_schema,
                semantic_schema_custody=self.semantic_schema,
            )

    def test_selection_cap_uncertainty_and_explicit_invocation_fail_closed(
        self,
    ) -> None:
        yes = [capsule(self.task, slot, "yes", "none") for slot in SLEC.SLOTS]
        self.assertEqual(self.resolve(yes)["resolution_status"], "abstain_cap")
        uncertain = deepcopy(self.values)
        uncertain[2] = capsule(self.task, "s2", "uncertain", "uncertain", None)
        self.assertEqual(
            self.resolve(uncertain)["resolution_status"], "abstain_uncertain"
        )
        invoked_task = self.task + " $agentic-engineering:codex-task-contract"
        invoked_capsules = [capsule(invoked_task, slot) for slot in SLEC.SLOTS]
        invoked_capsules[1] = capsule(
            invoked_task, "s1", "yes", "focused", "acceptance"
        )
        record = SLEC.resolve_capsules(
            task=invoked_task,
            condition_id="current",
            capsule_ingresses=[custody(value) for value in invoked_capsules],
            authority_custody=self.authority,
            policy_custody=self.policy,
            resolution_schema_custody=self.resolution_schema,
            semantic_schema_custody=self.semantic_schema,
        )
        self.assertEqual(record["selected_slots"], ["s1"])
        self.assertEqual(record["reference_capability_ids"], [])
        self.assertEqual(record["references"], {"status": "not_requested", "files": []})

    def test_reference_broker_reads_only_pinned_capability_and_is_atomic(self) -> None:
        result = SLEC.broker_references(
            ["cap.ae.task-contract.core.v3"], self.policy, ROOT
        )
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(len(result["files"]), 1)
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                SLEC.broker_references(
                    ["cap.ae.task-contract.core.v3"], self.policy, directory
                ),
                {"status": "custody_failure", "files": []},
            )


if __name__ == "__main__":
    unittest.main()
