from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
F1 = ROOT / "evals/ae-sq8/f1"
RESOLVER = ROOT / "scripts/resolve_ae_sq8_slec.py"
SPEC = importlib.util.spec_from_file_location("resolve_ae_sq8_slec", RESOLVER)
assert SPEC is not None and SPEC.loader is not None
SLEC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SLEC)


def trusted(path: Path) -> tuple[bytes, str]:
    raw = path.read_bytes()
    return raw, hashlib.sha256(raw).hexdigest()


def custody(value: object) -> tuple[bytes, str]:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return raw, hashlib.sha256(raw).hexdigest()


class AESQ8ProviderSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.authority = trusted(F1 / "slec8-authority.json")
        cls.schema = json.loads((F1 / "slec8-capsule-schema.json").read_text())
        cls.schema_custody = trusted(F1 / "slec8-capsule-schema.json")

    def lint(self, schema: object, authority: tuple[bytes, str] | None = None) -> None:
        del authority
        SLEC._lint_provider_node(schema, root=schema)

    def test_real_provider_schema_is_pinned_and_recursively_closed(self) -> None:
        parsed = SLEC.validate_provider_schema(self.schema_custody, self.authority)
        self.assertEqual(parsed, self.schema)

    def test_unsupported_keyword_rejected_at_every_recursive_position(self) -> None:
        mutations = []
        root = deepcopy(self.schema)
        root["allOf"] = []
        mutations.append(root)
        nested = deepcopy(self.schema)
        nested["properties"]["slot_id"]["if"] = {}
        mutations.append(nested)
        item = deepcopy(self.schema)
        item["properties"]["anchors"]["items"]["then"] = {}
        mutations.append(item)
        defs = deepcopy(self.schema)
        defs["$defs"] = {"unused": {"type": "string", "uniqueItems": True}}
        mutations.append(defs)
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(SLEC.SLECError):
                self.lint(mutation)

    def test_refs_must_be_local_resolved_and_acyclic(self) -> None:
        base = {
            "type": "object",
            "properties": {"x": {"$ref": "#/$defs/x"}},
            "required": ["x"],
            "additionalProperties": False,
            "$defs": {"x": {"type": "string"}},
        }
        self.lint(base)
        for ref in ("https://example.test/x", "#/missing", "#/$defs/../x"):
            mutation = deepcopy(base)
            mutation["properties"]["x"]["$ref"] = ref
            with self.subTest(ref=ref), self.assertRaises(SLEC.SLECError):
                self.lint(mutation)
        cycle = deepcopy(base)
        cycle["$defs"]["x"] = {"$ref": "#/$defs/x"}
        with self.assertRaises(SLEC.SLECError):
            self.lint(cycle)

    def test_all_objects_closed_and_required_exact_order(self) -> None:
        mutations = []
        missing = deepcopy(self.schema)
        del missing["additionalProperties"]
        mutations.append(missing)
        opened = deepcopy(self.schema)
        opened["properties"]["anchors"]["items"]["additionalProperties"] = True
        mutations.append(opened)
        absent = deepcopy(self.schema)
        absent["required"].pop()
        mutations.append(absent)
        extra = deepcopy(self.schema)
        extra["required"].append("ghost")
        mutations.append(extra)
        duplicate = deepcopy(self.schema)
        duplicate["required"].append("slot_id")
        mutations.append(duplicate)
        reordered = deepcopy(self.schema)
        reordered["required"] = list(reversed(reordered["required"]))
        mutations.append(reordered)
        for mutation in mutations:
            with self.assertRaises(SLEC.SLECError):
                self.lint(mutation)

    def test_provider_types_enums_and_array_bounds_fail_closed(self) -> None:
        mutations = []
        bool_bound = deepcopy(self.schema)
        bool_bound["properties"]["anchors"]["minItems"] = True
        mutations.append(bool_bound)
        inverted = deepcopy(self.schema)
        inverted["properties"]["anchors"]["minItems"] = 3
        mutations.append(inverted)
        bad_type = deepcopy(self.schema)
        bad_type["properties"]["slot_id"]["type"] = ["string"]
        mutations.append(bad_type)
        duplicate_enum = deepcopy(self.schema)
        duplicate_enum["properties"]["slot_id"]["enum"].append("s0")
        mutations.append(duplicate_enum)
        for mutation in mutations:
            with self.assertRaises(SLEC.SLECError):
                self.lint(mutation)

    def test_official_provider_resource_limits_are_closed(self) -> None:
        def object_schema(count: int) -> dict[str, object]:
            properties = {f"p{index}": {"type": "string"} for index in range(count)}
            return {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            }

        with self.assertRaises(SLEC.SLECError):
            self.lint(object_schema(5001))
        with self.assertRaises(SLEC.SLECError):
            self.lint(
                {"type": "string", "enum": [f"v{index}" for index in range(1001)]}
            )
        with self.assertRaises(SLEC.SLECError):
            self.lint({"type": "string", "enum": ["x" * 120001]})
        with self.assertRaises(SLEC.SLECError):
            self.lint({"type": "string", "enum": [1]})

        nested: dict[str, object] = {"type": "string"}
        for _ in range(10):
            nested = {"type": "array", "items": nested}
        with self.assertRaises(SLEC.SLECError):
            self.lint(nested)

        large_enum = {
            "type": "string",
            "enum": ["x" * 60 + str(index) for index in range(251)],
        }
        with self.assertRaises(SLEC.SLECError):
            self.lint(large_enum)

    def test_provider_resource_limit_boundaries_pass(self) -> None:
        properties = {f"p{index}": {"type": "string"} for index in range(5000)}
        self.lint(
            {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            }
        )
        self.lint({"type": "string", "enum": [f"v{index}" for index in range(1000)]})
        nested: dict[str, object] = {"type": "string"}
        for _ in range(9):
            nested = {"type": "array", "items": nested}
        self.lint(nested)

    def test_authority_drift_and_raw_digest_drift_rejected(self) -> None:
        raw, digest = self.schema_custody
        with self.assertRaises(SLEC.SLECError):
            SLEC.validate_provider_schema((raw, "0" * 64), self.authority)
        authority = json.loads(self.authority[0])
        authority["model_binding"]["model_id"] = "other"
        with self.assertRaises(SLEC.SLECError):
            SLEC.validate_provider_schema((raw, digest), custody(authority))

    def test_owned_lane_contains_no_stale_predecessor_candidate_identity(self) -> None:
        paths = list(F1.glob("slec8-*.json")) + [RESOLVER]
        text = "\n".join(path.read_text() for path in paths).lower()
        for forbidden in (
            "ae-sq1-slec-1",
            "ae-sq2-slec-2",
            "ae-sq3-slec-3",
            "slec-1",
            "slec-2",
            "slec-3",
            "slec1",
            "slec2",
            "slec3",
            ".core.v3",
            ".focused.v3",
            "sq3-f4",
            "sq3-f5",
            "resolve_ae_sq3",
        ):
            self.assertNotIn(forbidden, text)

        authority = json.loads((F1 / "slec8-authority.json").read_text())
        self.assertEqual(
            authority["model_binding"]["live_phases_only"],
            ["SQ8-F4", "SQ8-F5"],
        )
        self.assertEqual(
            authority["predecessor_terminal_provenance"]["program_id"],
            "AE-SQ7",
        )
        self.assertEqual(
            authority["repair_provenance"]["diagnostic_binding"]["path"],
            "evals/ae-sq2/d0/diagnostic-record.json",
        )


if __name__ == "__main__":
    unittest.main()
