from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = ROOT / "evals/ae-sq1/slec1-authority.json"
CAPSULE_SCHEMA_PATH = ROOT / "evals/ae-sq1/slec1-capsule-schema.json"
RESOLUTION_SCHEMA_PATH = ROOT / "evals/ae-sq1/slec1-resolution-schema.json"
POLICY_PATH = ROOT / "evals/ae-sq1/slec1-reference-policy.json"
RESOLVER_PATH = ROOT / "scripts/resolve_ae_sq1_slec.py"
EXTERNAL_EVIDENCE_PATH = ROOT / "evals/ae-sq1/external-evidence.json"

SPEC = importlib.util.spec_from_file_location("resolve_ae_sq1_slec", RESOLVER_PATH)
assert SPEC is not None and SPEC.loader is not None
SLEC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SLEC)


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
    ).hexdigest()


def trusted(path: Path) -> tuple[bytes, str]:
    raw = path.read_bytes()
    return raw, hashlib.sha256(raw).hexdigest()


def raw_capsules(values: list[dict[str, object]]) -> list[tuple[bytes, str]]:
    result = []
    for value in values:
        raw = json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode(
            "ascii"
        )
        result.append((raw, hashlib.sha256(raw).hexdigest()))
    return result


def trusted_value(value: object) -> tuple[bytes, str]:
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    return raw, hashlib.sha256(raw).hexdigest()


def anchor(task: str, text: str) -> dict[str, object]:
    start = task.index(text)
    return {"start": start, "end": start + len(text), "text": text}


def capsule(
    task: str, slot: str, local: str, reference: str, text: str | None
) -> dict[str, object]:
    return {
        "slot_id": slot,
        "local_need": local,
        "reference_need": reference,
        "anchors": [] if text is None else [anchor(task, text)],
    }


class AESQ1SLECTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.authority = trusted(AUTHORITY_PATH)
        cls.authority_map = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
        cls.capsule_schema = json.loads(CAPSULE_SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.resolution_schema = json.loads(
            RESOLUTION_SCHEMA_PATH.read_text(encoding="utf-8")
        )
        cls.resolution_schema_trusted = trusted(RESOLUTION_SCHEMA_PATH)
        cls.policy = trusted(POLICY_PATH)
        cls.policy_map = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def setUp(self) -> None:
        self.task = "Design architecture, define acceptance, verify behavior, and adopt learning."
        self.outputs = [
            capsule(self.task, "s0", "yes", "focused", "architecture"),
            capsule(self.task, "s1", "yes", "none", "acceptance"),
            capsule(self.task, "s2", "no", "none", "verify"),
            capsule(self.task, "s3", "no", "none", "learning"),
        ]

    def fold(
        self, task: str | None = None, outputs: list[dict[str, object]] | None = None
    ) -> dict[str, object]:
        return SLEC.fold(
            self.task if task is None else task,
            "current",
            raw_capsules(self.outputs if outputs is None else outputs),
            self.authority,
            self.policy,
        )

    def verify(self, record: dict[str, object]) -> dict[str, object]:
        return SLEC.verify_resolution_record(
            trusted_value(record),
            self.authority,
            self.policy,
            self.resolution_schema_trusted,
        )

    def single_selected_record(
        self, slot_index: int, reference_need: str
    ) -> dict[str, object]:
        words = ("architecture", "acceptance", "verify", "learning")
        outputs = [
            capsule(self.task, f"s{i}", "no", "none", word)
            for i, word in enumerate(words)
        ]
        outputs[slot_index] = capsule(
            self.task,
            f"s{slot_index}",
            "yes",
            reference_need,
            words[slot_index],
        )
        return SLEC.resolve(
            self.task,
            "current",
            raw_capsules(outputs),
            self.authority,
            self.policy,
            repository_root=ROOT,
        )

    def test_schemas_are_valid_closed_and_conditional(self) -> None:
        Draft202012Validator.check_schema(self.capsule_schema)
        Draft202012Validator.check_schema(self.resolution_schema)
        validator = Draft202012Validator(self.capsule_schema)
        self.assertFalse(list(validator.iter_errors(self.outputs[0])))
        mutations = []
        extra = deepcopy(self.outputs[0])
        extra["extra"] = True
        mutations.append(extra)
        uncertain_anchor = deepcopy(self.outputs[0])
        uncertain_anchor["local_need"] = "uncertain"
        mutations.append(uncertain_anchor)
        no_reference = deepcopy(self.outputs[0])
        no_reference["local_need"] = "no"
        mutations.append(no_reference)
        no_anchor = deepcopy(self.outputs[0])
        no_anchor["anchors"] = []
        mutations.append(no_anchor)
        for mutation in mutations:
            self.assertTrue(list(validator.iter_errors(mutation)))

    def test_condition_packets_are_one_card_only_and_not_identical(self) -> None:
        current = SLEC.build_assessor_packet(self.task, "current", "s0", self.authority)
        reduced = SLEC.build_assessor_packet(self.task, "reduced", "s0", self.authority)
        self.assertEqual(
            set(current),
            {
                "instruction",
                "task_text",
                "condition_id",
                "slot_id",
                "condition_slot_card",
                "anonymous_menu",
            },
        )
        self.assertNotEqual(SLEC.canonical_json(current), SLEC.canonical_json(reduced))
        serialized = json.dumps(current)
        for slot in self.authority_map["slots"][1:]:
            for capability_id in slot["capability_ids"].values():
                self.assertNotIn(capability_id, serialized)
            self.assertNotIn(slot["qualified_invocation"], serialized)

    def test_cards_are_mechanically_bound_and_digest_pinned(self) -> None:
        for slot in self.authority_map["slots"]:
            for card in slot["cards"].values():
                binding = card["source_binding"]
                raw = (ROOT / binding["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), binding["sha256"])
                projection = {
                    key: value
                    for key, value in card.items()
                    if key != "canonical_card_sha256"
                }
                self.assertEqual(
                    canonical_sha256(projection), card["canonical_card_sha256"]
                )
                text = raw.decode("utf-8")
                self.assertIn(f'description: "{card["body"]["description"]}"', text)
                self.assertIn(card["body"]["decision_scope"], text)

    def test_normalizer_discards_anchors_and_enforces_exact_unique_slices(self) -> None:
        normalized = SLEC.normalize_runtime_capsule(
            self.outputs[0],
            self.task,
            "current",
            "s0",
            self.authority_map,
            self.policy_map,
        )
        self.assertEqual(
            normalized,
            {"slot_id": "s0", "local_need": "yes", "reference_need": "focused"},
        )
        for changed in (
            {**self.outputs[0], "slot_id": "s1"},
            {
                **self.outputs[0],
                "anchors": [{"start": 0, "end": 6, "text": "Design"}] * 2,
            },
            {
                **self.outputs[0],
                "anchors": [{"start": 1, "end": 13, "text": "architecture"}],
            },
            {**self.outputs[0], "local_need": "no"},
        ):
            with self.assertRaises(SLEC.SLECError):
                SLEC.normalize_runtime_capsule(
                    changed,
                    self.task,
                    "current",
                    "s0",
                    self.authority_map,
                    self.policy_map,
                )

    def test_raw_utf8_and_digest_are_fail_closed(self) -> None:
        raw_outputs = []
        for value in self.outputs:
            raw = json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode(
                "ascii"
            )
            raw_outputs.append((raw, hashlib.sha256(raw).hexdigest()))
        good = SLEC.fold(self.task, "current", raw_outputs, self.authority, self.policy)
        self.assertEqual(good["resolution_status"], "selected")
        broken = list(raw_outputs)
        broken[0] = (broken[0][0], "0" * 64)
        self.assertEqual(
            SLEC.fold(self.task, "current", broken, self.authority, self.policy)[
                "resolution_status"
            ],
            "abstain_invalid",
        )
        invalid_utf8 = list(raw_outputs)
        invalid_utf8[0] = (b"\xff", hashlib.sha256(b"\xff").hexdigest())
        self.assertEqual(
            SLEC.fold(self.task, "current", invalid_utf8, self.authority, self.policy)[
                "resolution_status"
            ],
            "abstain_invalid",
        )

    def test_only_exact_raw_digest_tuples_and_exact_json_key_order_enter_fold(
        self,
    ) -> None:
        ingress = raw_capsules(self.outputs)

        class TupleSubclass(tuple):
            pass

        original_raw, original_digest = ingress[0]
        reordered = (
            b'{"local_need":"yes","slot_id":"s0","reference_need":"focused",'
            b'"anchors":[{"start":7,"end":19,"text":"architecture"}]}'
        )
        reordered_anchor = original_raw.replace(
            b'{"start":7,"end":19,"text":"architecture"}',
            b'{"text":"architecture","start":7,"end":19}',
        )
        duplicate = original_raw.replace(
            b'{"slot_id":"s0",', b'{"slot_id":"s0","slot_id":"s0",'
        )
        nonfinite = original_raw.replace(b'"start":7', b'"start":NaN')
        trailing = original_raw + b"{}"
        bypasses = [
            self.outputs[0],
            original_raw,
            [original_raw, original_digest],
            TupleSubclass((original_raw, original_digest)),
            (original_raw, original_digest.upper()),
            (reordered, hashlib.sha256(reordered).hexdigest()),
            (reordered_anchor, hashlib.sha256(reordered_anchor).hexdigest()),
            (duplicate, hashlib.sha256(duplicate).hexdigest()),
            (nonfinite, hashlib.sha256(nonfinite).hexdigest()),
            (trailing, hashlib.sha256(trailing).hexdigest()),
        ]
        for bypass in bypasses:
            changed = list(ingress)
            changed[0] = bypass
            record = SLEC.fold(
                self.task, "current", changed, self.authority, self.policy
            )
            self.assertEqual(record["resolution_status"], "abstain_invalid")
            self.assertEqual(record["input_custody"]["capsule_count"], 4)

    def test_invalid_multiset_custody_is_complete_and_order_independent(self) -> None:
        ingress: list[object] = list(raw_capsules(self.outputs))
        ingress[0] = self.outputs[0]
        raw, _ = ingress[1]
        ingress[1] = (raw, "0" * 64)
        first = SLEC.fold(self.task, "current", ingress, self.authority, self.policy)
        second = SLEC.fold(
            self.task, "current", list(reversed(ingress)), self.authority, self.policy
        )
        self.assertEqual(first, second)
        self.assertEqual(first["resolution_status"], "abstain_invalid")
        self.assertEqual(first["input_custody"]["capsule_count"], len(ingress))

    def test_invalid_ingress_custody_domain_separates_exact_types_and_structures(
        self,
    ) -> None:
        ordered = {"a": 1, "b": 2}
        reordered = {"b": 2, "a": 1}
        collision_pairs = (
            (({}, "x"), [{}, "x"]),
            (True, 1),
            (b"x", "x"),
            ({1: "x"}, {"1": "x"}),
            (ordered, reordered),
            ({"nested": [1, {"x": b"y"}]}, {"nested": (1, {"x": b"y"})}),
        )
        observed: set[str] = set()
        for left, right in collision_pairs:
            left_record = SLEC.fold(
                self.task, "current", [left], self.authority, self.policy
            )
            right_record = SLEC.fold(
                self.task, "current", [right], self.authority, self.policy
            )
            for record in (left_record, right_record):
                self.assertEqual(record["resolution_status"], "abstain_invalid")
                self.assertTrue(record["input_custody"]["capsule_custody_complete"])
                observed.add(record["input_custody"]["capsule_set_sha256"])
            self.assertNotEqual(
                left_record["input_custody"]["capsule_set_sha256"],
                right_record["input_custody"]["capsule_set_sha256"],
            )
        self.assertEqual(len(observed), len(collision_pairs) * 2)

        cyclic: list[object] = []
        cyclic.append(cyclic)
        unavailable = SLEC.fold(
            self.task, "current", [cyclic], self.authority, self.policy
        )
        self.assertEqual(unavailable["resolution_status"], "abstain_invalid")
        self.assertFalse(unavailable["input_custody"]["capsule_custody_complete"])

    def test_authority_and_policy_require_exact_pinned_raw_bytes(self) -> None:
        ingress = raw_capsules(self.outputs)
        self.assertEqual(
            SLEC.fold(self.task, "current", ingress, self.authority_map, self.policy)[
                "resolution_status"
            ],
            "abstain_invalid",
        )
        wrong_authority = (self.authority[0], "0" * 64)
        self.assertEqual(
            SLEC.fold(self.task, "current", ingress, wrong_authority, self.policy)[
                "resolution_status"
            ],
            "abstain_invalid",
        )
        policy_extra = deepcopy(self.policy_map)
        policy_extra["extra"] = True
        self.assertEqual(
            SLEC.broker_references(
                ["cap.ae.architecture.core.v1"], trusted_value(policy_extra), ROOT
            ),
            {"status": "custody_failure", "files": []},
        )
        authority_extra = deepcopy(self.authority_map)
        authority_extra["extra"] = True
        with self.assertRaises(SLEC.SLECError):
            SLEC.build_assessor_packet(
                self.task, "current", "s0", trusted_value(authority_extra)
            )

    def test_completion_order_is_invariant_and_anchors_are_not_durable(self) -> None:
        ingress = raw_capsules(self.outputs)
        first = SLEC.fold(self.task, "current", ingress, self.authority, self.policy)
        second = SLEC.fold(
            self.task, "current", list(reversed(ingress)), self.authority, self.policy
        )
        self.assertEqual(first, second)
        serialized = json.dumps(first)
        self.assertNotIn("anchors", serialized)
        self.assertNotIn(self.task, serialized)
        self.assertEqual(first["selected_slots"], ["s0", "s1"])
        self.assertEqual(
            first["reference_capability_ids"], ["cap.ae.architecture.focused.v1"]
        )
        self.assertFalse(
            list(Draft202012Validator(self.resolution_schema).iter_errors(first))
        )

    def test_uncertain_invalid_and_over_cap_all_abstain(self) -> None:
        uncertain = deepcopy(self.outputs)
        uncertain[0] = capsule(self.task, "s0", "uncertain", "uncertain", None)
        self.assertEqual(
            self.fold(outputs=uncertain)["resolution_status"],
            "abstain_uncertain",
        )
        duplicate = deepcopy(self.outputs)
        duplicate[3]["slot_id"] = "s2"
        self.assertEqual(
            self.fold(outputs=duplicate)["resolution_status"],
            "abstain_invalid",
        )
        over = deepcopy(self.outputs)
        over[2]["local_need"] = "yes"
        self.assertEqual(
            self.fold(outputs=over)["resolution_status"],
            "abstain_cap",
        )

    def test_core_focused_none_and_uncertain_have_distinct_fixed_mappings(self) -> None:
        for slot_index, slot in enumerate(self.authority_map["slots"]):
            pair = slot["capability_ids"]
            self.assertNotEqual(pair["core"], pair["focused"])
            catalog_rows = [
                row
                for row in self.policy_map["capability_catalog"]
                if row["slot_id"] == slot["slot_id"]
            ]
            self.assertEqual(
                [row["reference_need"] for row in catalog_rows], ["core", "focused"]
            )
            self.assertNotEqual(
                catalog_rows[0]["file"]["path"], catalog_rows[1]["file"]["path"]
            )
            for need in ("core", "focused"):
                outputs = [
                    capsule(self.task, f"s{i}", "no", "none", word)
                    for i, word in enumerate(
                        ("architecture", "acceptance", "verify", "learning")
                    )
                ]
                outputs[slot_index] = capsule(
                    self.task,
                    slot["slot_id"],
                    "yes",
                    need,
                    ("architecture", "acceptance", "verify", "learning")[slot_index],
                )
                self.assertEqual(
                    self.fold(outputs=outputs)["reference_capability_ids"], [pair[need]]
                )
                brokered = SLEC.broker_references([pair[need]], self.policy, ROOT)
                self.assertEqual(brokered["status"], "resolved")
                expected_path = next(
                    row["file"]["path"]
                    for row in catalog_rows
                    if row["reference_need"] == need
                )
                self.assertEqual(brokered["files"][0]["path"], expected_path)

        none_outputs = deepcopy(self.outputs)
        none_outputs[0]["reference_need"] = "none"
        self.assertEqual(
            self.fold(outputs=none_outputs)["reference_capability_ids"], []
        )
        uncertain = deepcopy(self.outputs)
        uncertain[0] = capsule(self.task, "s0", "uncertain", "uncertain", None)
        self.assertEqual(
            self.fold(outputs=uncertain)["resolution_status"], "abstain_uncertain"
        )

    def test_explicit_one_or_two_tokens_select_exactly_and_no_references(self) -> None:
        tokens = [row["qualified_invocation"] for row in self.authority_map["slots"]]
        for selected_tokens, expected in (
            (tokens[:1], ["s0"]),
            (tokens[1:3], ["s1", "s2"]),
        ):
            task = "alpha beta gamma delta " + " ".join(selected_tokens)
            outputs = [
                capsule(task, "s0", "no", "none", "alpha"),
                capsule(task, "s1", "no", "none", "beta"),
                capsule(task, "s2", "no", "none", "gamma"),
                capsule(task, "s3", "no", "none", "delta"),
            ]
            record = self.fold(task=task, outputs=outputs)
            self.assertEqual(record["selected_slots"], expected)
            self.assertEqual(record["reference_capability_ids"], [])
            self.assertEqual(record["selection_mode"], "explicit_invocation")
        task = "alpha beta gamma delta " + " ".join(tokens[:3])
        outputs = [
            capsule(task, f"s{i}", "no", "none", word)
            for i, word in enumerate(("alpha", "beta", "gamma", "delta"))
        ]
        self.assertEqual(
            self.fold(task=task, outputs=outputs)["resolution_status"],
            "abstain_cap",
        )

    def test_unicode_boundaries_and_unknown_tokens_fail_closed(self) -> None:
        token = self.authority_map["slots"][0]["qualified_invocation"]
        for boundary in ("é", "\u0301", "\u200c", "\u203f", "_", "-"):
            for candidate in (f"{token}{boundary}", f"{boundary}{token}"):
                task = f"alpha beta gamma delta {candidate}"
                outputs = [
                    capsule(task, f"s{i}", "no", "none", word)
                    for i, word in enumerate(("alpha", "beta", "gamma", "delta"))
                ]
                record = self.fold(task=task, outputs=outputs)
                self.assertEqual(record["resolution_status"], "abstain_invalid")
        task = f"alpha beta gamma delta {token} {token}"
        outputs = [
            capsule(task, f"s{i}", "no", "none", word)
            for i, word in enumerate(("alpha", "beta", "gamma", "delta"))
        ]
        self.assertEqual(
            self.fold(task=task, outputs=outputs)["resolution_status"],
            "abstain_invalid",
        )

        tokens = [
            row["qualified_invocation"] for row in self.authority_map["slots"][:2]
        ]
        selections = []
        for ordered in (tokens, list(reversed(tokens))):
            task = "alpha beta gamma delta " + " ".join(ordered)
            outputs = [
                capsule(task, f"s{i}", "no", "none", word)
                for i, word in enumerate(("alpha", "beta", "gamma", "delta"))
            ]
            record = self.fold(task=task, outputs=outputs)
            selections.append(record["selected_slots"])
        self.assertEqual(selections, [["s0", "s1"], ["s0", "s1"]])

        task = "alpha beta gamma delta $unknown:skill"
        outputs = [
            capsule(task, f"s{i}", "no", "none", word)
            for i, word in enumerate(("alpha", "beta", "gamma", "delta"))
        ]
        self.assertEqual(
            self.fold(task=task, outputs=outputs)["resolution_status"],
            "abstain_invalid",
        )

    def _temp_catalog(
        self,
    ) -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, object]]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        for row in self.policy_map["capability_catalog"]:
            target = root / row["file"]["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / row["file"]["path"], target)
        return temporary, root, deepcopy(self.policy_map)

    def test_broker_is_capability_only_atomic_and_race_safe(self) -> None:
        success = SLEC.broker_references(
            ["cap.ae.architecture.core.v1", "cap.ae.learning.focused.v1"],
            self.policy,
            ROOT,
        )
        self.assertEqual(success["status"], "resolved")
        self.assertEqual(len(success["files"]), 2)
        self.assertEqual(
            SLEC.broker_references(["cap.unknown"], self.policy, ROOT),
            {"status": "custody_failure", "files": []},
        )
        for malformed in (
            [[]],
            [1],
            [None],
            ["cap.ae.architecture.core.v1", "cap.ae.architecture.focused.v1"],
        ):
            self.assertEqual(
                SLEC.broker_references(malformed, self.policy, ROOT),
                {"status": "custody_failure", "files": []},
            )

        temporary, root, policy = self._temp_catalog()
        try:
            target = root / policy["capability_catalog"][0]["file"]["path"]
            target.unlink()
            target.symlink_to(ROOT / "references/seven-layer-map.md")
            self.assertEqual(
                SLEC.broker_references(
                    [CAP := "cap.ae.architecture.core.v1"], trusted_value(policy), root
                )["status"],
                "custody_failure",
            )
            target.unlink()
            shutil.copyfile(ROOT / "references/seven-layer-map.md", target)

            def mutate(path: Path, _: int) -> None:
                path.write_bytes(path.read_bytes() + b"x")

            self.assertEqual(
                SLEC.broker_references(
                    [CAP], trusted_value(policy), root, _after_open_hook=mutate
                )["status"],
                "custody_failure",
            )
            escaped = deepcopy(policy)
            escaped["capability_catalog"][0]["file"]["path"] = "../outside"
            self.assertEqual(
                SLEC.broker_references([CAP], trusted_value(escaped), root)["status"],
                "custody_failure",
            )
            noncanonical = deepcopy(policy)
            noncanonical["capability_catalog"][0]["file"]["path"] = (
                "./references/seven-layer-map.md"
            )
            self.assertEqual(
                SLEC.broker_references([CAP], trusted_value(noncanonical), root)[
                    "status"
                ],
                "custody_failure",
            )
        finally:
            temporary.cleanup()

        temporary, root, policy = self._temp_catalog()
        try:
            parent = root / "references"
            shutil.rmtree(parent)
            parent.symlink_to(ROOT / "references", target_is_directory=True)
            self.assertEqual(
                SLEC.broker_references(
                    ["cap.ae.architecture.core.v1"], trusted_value(policy), root
                )["status"],
                "custody_failure",
            )
        finally:
            temporary.cleanup()

        temporary, root, policy = self._temp_catalog()
        try:
            capability = "cap.ae.architecture.core.v1"

            def replace_target(path: Path, _: int) -> None:
                moved = path.with_name(path.name + ".opened")
                path.rename(moved)
                shutil.copyfile(moved, path)

            self.assertEqual(
                SLEC.broker_references(
                    [capability],
                    trusted_value(policy),
                    root,
                    _after_open_hook=replace_target,
                )["status"],
                "custody_failure",
            )
        finally:
            temporary.cleanup()

        temporary, root, policy = self._temp_catalog()
        try:
            capability = "cap.ae.architecture.focused.v1"

            def relocate_parent(path: Path, _: int) -> None:
                moved = path.parent.with_name(path.parent.name + "-opened")
                path.parent.rename(moved)
                path.parent.mkdir()
                shutil.copyfile(moved / path.name, path)

            self.assertEqual(
                SLEC.broker_references(
                    [capability],
                    trusted_value(policy),
                    root,
                    _after_open_hook=relocate_parent,
                )["status"],
                "custody_failure",
            )
            root_link = root.with_name(root.name + "-link")
            root_link.symlink_to(root, target_is_directory=True)
            try:
                self.assertEqual(
                    SLEC.broker_references(
                        [capability], trusted_value(policy), root_link
                    )["status"],
                    "custody_failure",
                )
            finally:
                root_link.unlink()
        finally:
            temporary.cleanup()

    def test_resolve_requires_reference_root_and_schema_branches_are_discriminated(
        self,
    ) -> None:
        ingress = raw_capsules(self.outputs)
        denied = SLEC.resolve(
            self.task,
            "current",
            ingress,
            self.authority,
            self.policy,
            repository_root=None,
        )
        self.assertEqual(denied["resolution_status"], "abstain_invalid")
        self.assertEqual(
            denied["references"], {"status": "custody_failure", "files": []}
        )
        self.assertFalse(
            list(Draft202012Validator(self.resolution_schema).iter_errors(denied))
        )

        resolved = SLEC.resolve(
            self.task,
            "current",
            ingress,
            self.authority,
            self.policy,
            repository_root=ROOT,
        )
        self.assertEqual(resolved["resolution_status"], "selected")
        self.assertEqual(resolved["references"]["status"], "resolved")
        validator = Draft202012Validator(self.resolution_schema)
        self.assertFalse(list(validator.iter_errors(resolved)))

        invalid_with_files = deepcopy(resolved)
        invalid_with_files["resolution_status"] = "abstain_invalid"
        invalid_with_files["selection_mode"] = "none"
        invalid_with_files["selected_slots"] = []
        invalid_with_files["reference_capability_ids"] = []
        self.assertTrue(list(validator.iter_errors(invalid_with_files)))

        selected_without_mode = deepcopy(resolved)
        selected_without_mode["selection_mode"] = "none"
        self.assertTrue(list(validator.iter_errors(selected_without_mode)))

        token = self.authority_map["slots"][0]["qualified_invocation"]
        explicit_task = f"alpha beta gamma delta {token}"
        explicit_outputs = [
            capsule(explicit_task, f"s{i}", "no", "none", word)
            for i, word in enumerate(("alpha", "beta", "gamma", "delta"))
        ]
        explicit = self.fold(task=explicit_task, outputs=explicit_outputs)
        self.assertEqual(explicit["selection_mode"], "explicit_invocation")
        self.assertFalse(list(validator.iter_errors(explicit)))

        explicit_reference_bypass = deepcopy(explicit)
        explicit_reference_bypass["reference_capability_ids"] = deepcopy(
            resolved["reference_capability_ids"]
        )
        explicit_reference_bypass["references"] = deepcopy(resolved["references"])
        self.assertTrue(list(validator.iter_errors(explicit_reference_bypass)))

    def test_record_verifier_replays_all_eight_frozen_reference_mappings(self) -> None:
        catalog = self.policy_map["capability_catalog"]
        self.assertEqual(len(catalog), 8)
        for index, expected in enumerate(catalog):
            slot_index, need_index = divmod(index, 2)
            reference_need = ("core", "focused")[need_index]
            record = self.single_selected_record(slot_index, reference_need)
            self.assertEqual(self.verify(record), record)
            self.assertEqual(record["selected_slots"], [expected["slot_id"]])
            self.assertEqual(
                record["reference_capability_ids"], [expected["capability_id"]]
            )
            self.assertEqual(
                record["references"]["files"],
                [
                    {
                        "slot_id": expected["slot_id"],
                        "reference_need": expected["reference_need"],
                        "capability_id": expected["capability_id"],
                        "path": expected["file"]["path"],
                        "sha256": expected["file"]["sha256"],
                        "git_blob_sha1": expected["file"]["git_blob_sha1"],
                        "size_bytes": expected["file"]["size_bytes"],
                    }
                ],
            )

            replacement = catalog[(index + 1) % len(catalog)]["capability_id"]
            mapping_mutant = deepcopy(record)
            mapping_mutant["references"]["files"][0]["capability_id"] = replacement
            missing_mutant = deepcopy(record)
            missing_mutant["references"]["files"][0].pop("sha256")
            extra_mutant = deepcopy(record)
            extra_mutant["references"]["files"][0]["unexpected"] = True
            slot_mutant = deepcopy(record)
            slot_mutant["references"]["files"][0]["slot_id"] = (
                f"s{(slot_index + 1) % 4}"
            )
            need_mutant = deepcopy(record)
            need_mutant["references"]["files"][0]["reference_need"] = (
                "focused" if reference_need == "core" else "core"
            )
            path_mutant = deepcopy(record)
            path_mutant["references"]["files"][0]["path"] += ".mutant"
            digest_mutant = deepcopy(record)
            digest_mutant["references"]["files"][0]["sha256"] = "0" * 64
            blob_mutant = deepcopy(record)
            blob_mutant["references"]["files"][0]["git_blob_sha1"] = "0" * 40
            size_mutant = deepcopy(record)
            size_mutant["references"]["files"][0]["size_bytes"] += 1
            for mutant in (
                mapping_mutant,
                missing_mutant,
                extra_mutant,
                slot_mutant,
                need_mutant,
                path_mutant,
                digest_mutant,
                blob_mutant,
                size_mutant,
            ):
                with self.assertRaises(SLEC.SLECError):
                    self.verify(mutant)

    def test_record_verifier_rejects_cross_field_order_and_path_bypasses(self) -> None:
        words = ("architecture", "acceptance", "verify", "learning")
        outputs = [
            capsule(self.task, f"s{i}", "no", "none", word)
            for i, word in enumerate(words)
        ]
        outputs[0] = capsule(self.task, "s0", "yes", "core", words[0])
        outputs[3] = capsule(self.task, "s3", "yes", "focused", words[3])
        record = SLEC.resolve(
            self.task,
            "current",
            raw_capsules(outputs),
            self.authority,
            self.policy,
            repository_root=ROOT,
        )
        self.assertEqual(self.verify(record), record)

        reversed_slots = deepcopy(record)
        reversed_slots["selected_slots"].reverse()
        reversed_capabilities = deepcopy(record)
        reversed_capabilities["reference_capability_ids"].reverse()
        reversed_files = deepcopy(record)
        reversed_files["references"]["files"].reverse()
        missing_capability = deepcopy(record)
        missing_capability["reference_capability_ids"].pop()
        missing_file = deepcopy(record)
        missing_file["references"]["files"].pop()
        extra_capability = self.single_selected_record(0, "core")
        extra_capability["reference_capability_ids"].append(
            "cap.ae.verification.core.v1"
        )
        extra_file = self.single_selected_record(0, "core")
        extra_file["references"]["files"].append(
            deepcopy(record["references"]["files"][1])
        )
        for mutant in (
            reversed_slots,
            reversed_capabilities,
            reversed_files,
            missing_capability,
            missing_file,
            extra_capability,
            extra_file,
        ):
            with self.assertRaises(SLEC.SLECError):
                self.verify(mutant)

        exact_red = self.single_selected_record(3, "focused")
        exact_red["references"]["files"][0]["capability_id"] = (
            "cap.ae.verification.core.v1"
        )
        exact_red["references"]["files"][0]["path"] = "../../private/key"
        with self.assertRaises(SLEC.SLECError):
            self.verify(exact_red)

    def test_record_verifier_rejects_invocation_slot_and_schema_contradictions(
        self,
    ) -> None:
        token = self.authority_map["slots"][2]["qualified_invocation"]
        task = f"alpha beta gamma delta {token}"
        outputs = [
            capsule(task, f"s{i}", "no", "none", word)
            for i, word in enumerate(("alpha", "beta", "gamma", "delta"))
        ]
        explicit = SLEC.resolve(
            task,
            "current",
            raw_capsules(outputs),
            self.authority,
            self.policy,
            repository_root=ROOT,
        )
        self.assertEqual(self.verify(explicit), explicit)

        wrong_selected = deepcopy(explicit)
        wrong_selected["selected_slots"] = ["s3"]
        wrong_recognized = deepcopy(explicit)
        wrong_recognized["invocation_evidence"]["recognized_slots"] = ["s3"]
        wrong_count = deepcopy(explicit)
        wrong_count["invocation_evidence"]["recognized_count"] = 0
        malformed = deepcopy(explicit)
        malformed["invocation_evidence"]["has_unrecognized_or_malformed"] = True

        folded = self.single_selected_record(3, "focused")
        wrong_outcome = deepcopy(folded)
        wrong_outcome["slot_outcomes"][3] = {
            "slot_id": "s3",
            "local_need": "no",
            "reference_need": "none",
        }
        wrong_need = deepcopy(folded)
        wrong_need["slot_outcomes"][3]["reference_need"] = "core"
        for mutant in (
            wrong_selected,
            wrong_recognized,
            wrong_count,
            malformed,
            wrong_outcome,
            wrong_need,
        ):
            with self.assertRaises(SLEC.SLECError):
                self.verify(mutant)

        altered_schema = deepcopy(self.resolution_schema)
        altered_schema["title"] += " mutant"
        with self.assertRaises(SLEC.SLECError):
            SLEC.verify_resolution_record(
                trusted_value(explicit),
                self.authority,
                self.policy,
                trusted_value(altered_schema),
            )
        raw_record, _ = trusted_value(explicit)
        with self.assertRaises(SLEC.SLECError):
            SLEC.verify_resolution_record(
                (raw_record, "0" * 64),
                self.authority,
                self.policy,
                self.resolution_schema_trusted,
            )

    def test_record_verifier_accepts_only_reachable_broker_custody_failures(
        self,
    ) -> None:
        words = ("architecture", "acceptance", "verify", "learning")

        def outputs_with(*selected: tuple[int, str]) -> list[dict[str, object]]:
            outputs = [
                capsule(self.task, f"s{i}", "no", "none", word)
                for i, word in enumerate(words)
            ]
            for slot_index, reference_need in selected:
                outputs[slot_index] = capsule(
                    self.task,
                    f"s{slot_index}",
                    "yes",
                    reference_need,
                    words[slot_index],
                )
            return outputs

        one_slot_failure = SLEC.resolve(
            self.task,
            "current",
            raw_capsules(outputs_with((0, "core"))),
            self.authority,
            self.policy,
            repository_root=None,
        )
        two_slot_failure = SLEC.resolve(
            self.task,
            "current",
            raw_capsules(outputs_with((1, "focused"), (3, "core"))),
            self.authority,
            self.policy,
            repository_root=None,
        )
        for record in (one_slot_failure, two_slot_failure):
            self.assertEqual(record["resolution_status"], "abstain_invalid")
            self.assertEqual(
                record["references"], {"status": "custody_failure", "files": []}
            )
            self.assertEqual(self.verify(record), record)

        over_cap = self.fold(
            outputs=outputs_with((0, "core"), (1, "core"), (2, "core"))
        )
        self.assertEqual(over_cap["resolution_status"], "abstain_cap")
        over_cap_red = deepcopy(over_cap)
        over_cap_red["resolution_status"] = "abstain_invalid"
        over_cap_red["references"] = {"status": "custody_failure", "files": []}

        no_selection = self.fold(outputs=outputs_with())
        no_selection_red = deepcopy(no_selection)
        no_selection_red["resolution_status"] = "abstain_invalid"
        no_selection_red["selection_mode"] = "none"
        no_selection_red["references"] = {"status": "custody_failure", "files": []}

        native_only = self.fold(outputs=outputs_with((0, "none")))
        native_only_red = deepcopy(native_only)
        native_only_red["resolution_status"] = "abstain_invalid"
        native_only_red["selection_mode"] = "none"
        native_only_red["selected_slots"] = []
        native_only_red["references"] = {"status": "custody_failure", "files": []}

        uncertain_outputs = outputs_with()
        uncertain_outputs[0] = capsule(self.task, "s0", "uncertain", "uncertain", None)
        uncertain_red = self.fold(outputs=uncertain_outputs)
        uncertain_red["resolution_status"] = "abstain_invalid"
        uncertain_red["references"] = {"status": "custody_failure", "files": []}

        invalid_ingress = raw_capsules(outputs_with())
        raw, _ = invalid_ingress[0]
        invalid_ingress[0] = (raw, "0" * 64)
        invalid_red = SLEC.fold(
            self.task, "current", invalid_ingress, self.authority, self.policy
        )
        invalid_red["references"] = {"status": "custody_failure", "files": []}

        token = self.authority_map["slots"][0]["qualified_invocation"]
        explicit_task = f"alpha beta gamma delta {token}"
        explicit_outputs = [
            capsule(explicit_task, f"s{i}", "no", "none", word)
            for i, word in enumerate(("alpha", "beta", "gamma", "delta"))
        ]
        explicit_red = self.fold(task=explicit_task, outputs=explicit_outputs)
        explicit_red["resolution_status"] = "abstain_invalid"
        explicit_red["selection_mode"] = "none"
        explicit_red["selected_slots"] = []
        explicit_red["references"] = {"status": "custody_failure", "files": []}

        incomplete_custody = deepcopy(one_slot_failure)
        incomplete_custody["input_custody"]["capsule_custody_complete"] = False
        wrong_capsule_count = deepcopy(one_slot_failure)
        wrong_capsule_count["input_custody"]["capsule_count"] = 3

        for mutant in (
            over_cap_red,
            no_selection_red,
            native_only_red,
            uncertain_red,
            invalid_red,
            explicit_red,
            incomplete_custody,
            wrong_capsule_count,
        ):
            with self.assertRaises(SLEC.SLECError):
                self.verify(mutant)

    def test_authority_binds_external_packet_and_exact_git_custody(self) -> None:
        source_packet = self.authority_map["source_packet"]
        self.assertEqual(source_packet["path"], "evals/ae-sq1/external-evidence.json")
        self.assertEqual(
            source_packet["sha256"],
            hashlib.sha256(EXTERNAL_EVIDENCE_PATH.read_bytes()).hexdigest(),
        )
        resolution_contract = self.authority_map["resolution_contract"]
        self.assertEqual(
            resolution_contract["schema_path"],
            "evals/ae-sq1/slec1-resolution-schema.json",
        )
        self.assertEqual(
            resolution_contract["schema_sha256"],
            hashlib.sha256(RESOLUTION_SCHEMA_PATH.read_bytes()).hexdigest(),
        )
        resolver_contract = self.authority_map["resolver_contract"]
        self.assertEqual(resolver_contract["path"], "scripts/resolve_ae_sq1_slec.py")
        self.assertEqual(
            resolver_contract["sha256"],
            hashlib.sha256(RESOLVER_PATH.read_bytes()).hexdigest(),
        )

        def git_bytes(*arguments: str) -> bytes:
            return subprocess.run(
                ["git", *arguments],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout

        comparison = self.authority_map["comparison_authority"]
        self.assertEqual(
            git_bytes("cat-file", "-t", comparison["commit"]).strip(), b"commit"
        )
        self.assertEqual(
            git_bytes("cat-file", "-t", comparison["tree"]).strip(), b"tree"
        )
        self.assertEqual(
            git_bytes("rev-parse", f"{comparison['commit']}^{{tree}}").decode().strip(),
            comparison["tree"],
        )
        comparison_raw = git_bytes(
            "show", f"{comparison['commit']}:{comparison['path']}"
        )
        self.assertEqual(
            hashlib.sha256(comparison_raw).hexdigest(), comparison["sha256"]
        )

        foundation = self.authority_map["foundation_custody"]
        self.assertEqual(
            git_bytes("cat-file", "-t", foundation["commit"]).strip(), b"commit"
        )
        self.assertEqual(
            git_bytes("cat-file", "-t", foundation["tree"]).strip(), b"tree"
        )
        self.assertEqual(
            git_bytes("rev-parse", f"{foundation['commit']}^{{tree}}").decode().strip(),
            foundation["tree"],
        )

    def test_no_cross_slot_structure_and_synthetic_difference(self) -> None:
        forbidden_keys = {
            "pairwise_relations",
            "root_slots",
            "edges",
            "dependency_order",
        }

        def keys(value: object) -> set[str]:
            if isinstance(value, dict):
                return set(value) | {
                    key for child in value.values() for key in keys(child)
                }
            if isinstance(value, list):
                return {key for child in value for key in keys(child)}
            return set()

        record = self.fold()
        self.assertFalse(forbidden_keys & keys(self.capsule_schema))
        self.assertFalse(forbidden_keys & keys(self.resolution_schema))
        self.assertFalse(forbidden_keys & keys(record))
        witness = self.authority_map["non_isomorphism_witness"]
        self.assertEqual(witness["slec1_expected_selected_slots"], ["s0", "s1"])
        self.assertEqual(record["selected_slots"], ["s0", "s1"])


if __name__ == "__main__":
    unittest.main()
