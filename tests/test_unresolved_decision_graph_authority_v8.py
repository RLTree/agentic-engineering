"""Closed, corpus-blind authority checks for the prospective AQ8 H4 proposal."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT / "evals/foundation-v4/unresolved-decision-graph-authority-v8.json"
)
PROTOCOL_PATH = (
    ROOT / "evals/foundation-v4/unresolved-decision-graph-protocol-v8.json"
)
SEMANTIC_SCHEMA_PATH = (
    ROOT
    / "evals/foundation-v4/unresolved-decision-graph-selector-output-schema-v8.json"
)
RUNTIME_SCHEMA_PATH = (
    ROOT
    / "evals/foundation-v4/unresolved-decision-graph-runtime-output-schema-v8.json"
)
ADAPTER_PATH = (
    ROOT / "evals/foundation-v4/unresolved-decision-graph-condition-adapter-v8.json"
)
REFERENCE_POLICY_PATH = (
    ROOT / "evals/foundation-v4/unresolved-decision-graph-reference-policy-v8.json"
)

EXPECTED_TOP_LEVEL_ORDER = [
    "schema_version",
    "authority_id",
    "status",
    "claim_ceiling",
    "h2_catalog_authority",
    "h3_protocol_authority",
    "h3_selector_schema_authority",
    "h3_reference_policy_authority",
    "base_manifest_authority",
    "evaluator_surface",
    "cross_file_equality_contract",
    "mechanism",
    "diagnostics",
    "structural_discriminators",
    "structural_invariants",
    "terminal_stop",
    "prospective_qualification_boundary",
    "claims_proven",
]
AUTHORITY_KEY_ORDER = ["commit", "tree", "path", "sha256"]

EXPECTED_AUTHORITIES = {
    "h2_catalog_authority": {
        "commit": "8ddf39198cb0e21f321a01a9755e009bb1c1860f",
        "tree": "1fbf9964b10831da051d2e5cafe29b6086d4d599",
        "path": "evals/foundation-v4/decision-atom-candidate-v4.json",
        "sha256": "50fffcf10170cd022d78428909d0679527439a002a7e07dac30e321bbaff61d9",
    },
    "h3_protocol_authority": {
        "commit": "ccbe06be9a2ef5feca4104b6918985ee9c4527c0",
        "tree": "dd20449fdc45a73c55adb349d8c828687728ef4d",
        "path": "evals/foundation-v4/decision-certificate-protocol-v6.json",
        "sha256": "9ad483a26fe339f81c947507de9c1c66d54b2823a38f68b1c5ee7fdf5c426f84",
    },
    "h3_selector_schema_authority": {
        "commit": "ccbe06be9a2ef5feca4104b6918985ee9c4527c0",
        "tree": "dd20449fdc45a73c55adb349d8c828687728ef4d",
        "path": "evals/foundation-v4/decision-certificate-selector-output-schema-v6.json",
        "sha256": "9742f2255fed5452df52f9da789a6f2fd72e89aa94c3c6847fad6944445f5b25",
    },
    "h3_reference_policy_authority": {
        "commit": "c4e661a926e0ace78d9da83f71d9c52d311abb72",
        "tree": "f2abb05d32a888c9054ef2e7ab3ad0f08547de88",
        "path": "evals/foundation-v4/decision-certificate-reference-policy-v6.json",
        "sha256": "92982c278e33ff52edce1ba2a16082afb3ecc1989d8333a77eee9ca0911fee19",
    },
    "base_manifest_authority": {
        "commit": "f09a0544acf4b7a95fff796434273511a0683ca9",
        "tree": "38c8c8adf3bb633d33200df1ec65f33e985ae244",
        "path": "evals/foundation-v4/reduced-four-skills/candidate.json",
        "sha256": "854f67bdd03e7121bd20e5513ef61ac806d016b3a5f1d6e5891bf4d9e546eb1f",
    },
}

EXPECTED_COMPONENT_ROWS = [
    {
        "role": "protocol",
        "path": "evals/foundation-v4/unresolved-decision-graph-protocol-v8.json",
        "sha256": "a145766c475de5ed1411bc86467a1a82c3cdaa18782b772ef00901238f590fd5",
    },
    {
        "role": "semantic_selector_schema",
        "path": "evals/foundation-v4/unresolved-decision-graph-selector-output-schema-v8.json",
        "sha256": "5ef3bd8dc5a1a83a25c51d10513607c17e298086450b00181caecac0dba35af4",
    },
    {
        "role": "runtime_selector_schema",
        "path": "evals/foundation-v4/unresolved-decision-graph-runtime-output-schema-v8.json",
        "sha256": "e4d58b46e39ac65e56a339e7c0d2714d536a5d517de57c2bcc34cfd5c6fe301e",
    },
    {
        "role": "condition_adapter",
        "path": "evals/foundation-v4/unresolved-decision-graph-condition-adapter-v8.json",
        "sha256": "2b82d26b9f438b7cfef712d59817bb2cc8426941167350ec58c42a9a6e5e5b31",
    },
    {
        "role": "reference_policy",
        "path": "evals/foundation-v4/unresolved-decision-graph-reference-policy-v8.json",
        "sha256": "e16ad13602a3540b97b608d6a70223e5c7061530b748a6843e007eea791826f4",
    },
]

EXPECTED_EQUALITY_CONTRACT = {
    "fields": ["commit", "tree", "path", "sha256"],
    "authorities": [
        {
            "manifest_binding": "h2_catalog_authority",
            "component_locations": [
                "protocol.authority_basis.h2_catalog",
                "protocol.source_custody.slot_derivation_input",
                "condition_adapter.authority_basis.h2_catalog",
                "condition_adapter.source_custody.derivation_input",
            ],
        },
        {
            "manifest_binding": "h3_protocol_authority",
            "component_locations": [
                "protocol.authority_basis.h3.protocol",
                "condition_adapter.authority_basis.h3_grammar_lineage_only",
            ],
        },
        {
            "manifest_binding": "h3_selector_schema_authority",
            "component_locations": [
                "protocol.authority_basis.h3.selector_output_schema",
            ],
        },
        {
            "manifest_binding": "h3_reference_policy_authority",
            "component_locations": [
                "protocol.authority_basis.reference_policy",
                "reference_policy.authority_basis.h3_cover_authority",
            ],
        },
        {
            "manifest_binding": "base_manifest_authority",
            "component_locations": [
                "protocol.authority_basis.base_manifest_provenance_only",
                "reference_policy.authority_basis.base_candidate",
            ],
        },
    ],
    "active_h4_parent_parser": {
        "component_role": "protocol",
        "adapter_location": (
            "condition_adapter.authority_basis.h4_parent_parser_authority"
        ),
        "protocol_projection": "explicit_constraint.h4_parent_parser_contract",
        "projection_canonical_sha256": (
            "8920ab58abd9618fb1af4894e1b664d76d3c6f478d335e1d61e08ac47b9360d1"
        ),
    },
}

EXPECTED_MECHANISM = {
    "declaration": "anonymous unresolved-decision strict partial-order graph",
    "routing_rule": "graph roots are routes",
    "non_isomorphism": {
        "h1_adviser_ids": "not_isomorphic",
        "h2_atom_sets": "not_isomorphic",
        "h3_unary_facts": "not_isomorphic",
    },
    "causal_target": {
        "relation": "controlling-vs-downstream/independent relation",
        "prospective_only": True,
        "aq7_diagnosis": False,
    },
}

EXPECTED_DIAGNOSTICS = {
    "ordered_primary": [
        "graph_validity",
        "candidate_state_accuracy",
        "directed_control_precision",
        "directed_control_recall",
        "independent_relation_accuracy",
        "exact_root_set",
        "uncertainty_abstention",
        "cap_abstention",
    ],
    "graph_validity_required_exact": 1,
    "ordered_later_legacy_noncompensatory_gates": [
        "selected_set",
        "reference",
        "authority",
    ],
}

EXPECTED_TERMINAL_STOP = {
    "trigger": "any complete AQ8 noncompensatory aggregate failure",
    "noncompensatory": True,
    "actions": ["retire_H4", "stop_AQ"],
    "only_resume_condition": (
        "genuinely independent external evidence frozen before any later mechanism"
    ),
    "aq7_outcome_tuning_permitted": False,
    "aq8_outcome_tuning_permitted": False,
}

EXPECTED_QUALIFICATION_BOUNDARY = {
    "prospective_only": True,
    "authority_commit_required_before_corpus_authoring": True,
    "fresh_independently_authored_blinded_corpus_required": True,
    "historical_corpus_reuse_permitted": False,
}

EXPECTED_CLAIMS_PROVEN = {
    "runtime": False,
    "provider": False,
    "model": False,
    "sandbox": False,
    "product": False,
    "efficacy": False,
    "promotion": False,
}


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys
    )
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def raw_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return raw_sha256(encoded)


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def git_revision(expression: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--verify", expression], cwd=ROOT, text=True
    ).strip()


def binding_projection(
    value: dict[str, Any],
    *,
    inherited_commit: str | None = None,
    inherited_tree: str | None = None,
    path_key: str = "path",
    sha_key: str = "sha256",
) -> dict[str, str]:
    return {
        "commit": value.get("commit", inherited_commit),
        "tree": value.get("tree", inherited_tree),
        "path": value[path_key],
        "sha256": value[sha_key],
    }


def recursive_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        result = set(value)
        for item in value.values():
            result.update(recursive_keys(item))
        return result
    if isinstance(value, list):
        result: set[str] = set()
        for item in value:
            result.update(recursive_keys(item))
        return result
    return set()


def recursive_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(recursive_strings(item))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(recursive_strings(item))
        return result
    return []


def validate_manifest(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("closed manifest object required")
    if list(value) != EXPECTED_TOP_LEVEL_ORDER:
        raise ValueError("closed ordered top-level surface required")
    if value["schema_version"] != "8.0":
        raise ValueError("schema version drift")
    if value["authority_id"] != "H4-unresolved-decision-graph-authority-v8":
        raise ValueError("authority identity drift")
    if value["status"] != "frozen-proposal-only":
        raise ValueError("status drift")
    if value["claim_ceiling"] != "structural-proposal-only":
        raise ValueError("claim ceiling drift")

    for key, expected in EXPECTED_AUTHORITIES.items():
        actual = value[key]
        if not isinstance(actual, dict) or list(actual) != AUTHORITY_KEY_ORDER:
            raise ValueError(f"closed authority binding required: {key}")
        if actual != expected:
            raise ValueError(f"authority binding drift: {key}")

    surface = value["evaluator_surface"]
    if not isinstance(surface, dict) or list(surface) != ["files"]:
        raise ValueError("closed evaluator surface required")
    rows = surface["files"]
    if rows != EXPECTED_COMPONENT_ROWS:
        raise ValueError("exact ordered component rows required")
    if any(not isinstance(row, dict) or list(row) != ["role", "path", "sha256"] for row in rows):
        raise ValueError("closed component row required")

    expected_sections = {
        "cross_file_equality_contract": EXPECTED_EQUALITY_CONTRACT,
        "mechanism": EXPECTED_MECHANISM,
        "diagnostics": EXPECTED_DIAGNOSTICS,
        "terminal_stop": EXPECTED_TERMINAL_STOP,
        "prospective_qualification_boundary": EXPECTED_QUALIFICATION_BOUNDARY,
        "claims_proven": EXPECTED_CLAIMS_PROVEN,
    }
    for key, expected in expected_sections.items():
        if value[key] != expected:
            raise ValueError(f"closed {key} contract required")

    protocol = load_json(PROTOCOL_PATH)
    if value["structural_discriminators"] != protocol["structural_discriminators"]:
        raise ValueError("structural discriminator drift")
    if value["structural_invariants"] != protocol["structural_invariants"]:
        raise ValueError("structural invariant drift")


MANIFEST = load_json(MANIFEST_PATH)
PROTOCOL = load_json(PROTOCOL_PATH)
ADAPTER = load_json(ADAPTER_PATH)
REFERENCE_POLICY = load_json(REFERENCE_POLICY_PATH)


class UnresolvedDecisionGraphAuthorityV8Tests(unittest.TestCase):
    def test_manifest_has_exact_closed_surface(self) -> None:
        validate_manifest(MANIFEST)

    def test_component_surface_order_and_live_byte_hashes_are_exact(self) -> None:
        self.assertEqual(MANIFEST["evaluator_surface"]["files"], EXPECTED_COMPONENT_ROWS)
        for row in EXPECTED_COMPONENT_ROWS:
            with self.subTest(role=row["role"]):
                path = (ROOT / row["path"]).resolve()
                self.assertTrue(path.is_relative_to(ROOT.resolve()))
                self.assertEqual(raw_sha256(path.read_bytes()), row["sha256"])

    def test_upstream_bindings_resolve_exact_git_objects(self) -> None:
        for key, binding in EXPECTED_AUTHORITIES.items():
            with self.subTest(authority=key):
                self.assertEqual(
                    git_revision(f"{binding['commit']}^{{tree}}"), binding["tree"]
                )
                self.assertEqual(
                    raw_sha256(git_bytes(binding["commit"], binding["path"])),
                    binding["sha256"],
                )

    def test_upstream_authorities_are_equal_across_components(self) -> None:
        protocol_authority = PROTOCOL["authority_basis"]
        protocol_h3 = protocol_authority["h3"]
        adapter_authority = ADAPTER["authority_basis"]
        reference_authority = REFERENCE_POLICY["authority_basis"]

        actual_locations = {
            "h2_catalog_authority": [
                binding_projection(protocol_authority["h2_catalog"]),
                binding_projection(PROTOCOL["source_custody"]["slot_derivation_input"]),
                binding_projection(adapter_authority["h2_catalog"]),
                binding_projection(ADAPTER["source_custody"]["derivation_input"]),
            ],
            "h3_protocol_authority": [
                binding_projection(
                    protocol_h3["protocol"],
                    inherited_commit=protocol_h3["commit"],
                    inherited_tree=protocol_h3["tree"],
                ),
                binding_projection(
                    adapter_authority["h3_grammar_lineage_only"],
                    path_key="protocol_path",
                    sha_key="protocol_sha256",
                ),
            ],
            "h3_selector_schema_authority": [
                binding_projection(
                    protocol_h3["selector_output_schema"],
                    inherited_commit=protocol_h3["commit"],
                    inherited_tree=protocol_h3["tree"],
                )
            ],
            "h3_reference_policy_authority": [
                binding_projection(protocol_authority["reference_policy"]),
                binding_projection(reference_authority["h3_cover_authority"]),
            ],
            "base_manifest_authority": [
                binding_projection(
                    protocol_authority["base_manifest_provenance_only"]
                ),
                binding_projection(reference_authority["base_candidate"]),
            ],
        }

        self.assertEqual(
            MANIFEST["cross_file_equality_contract"], EXPECTED_EQUALITY_CONTRACT
        )
        for key, locations in actual_locations.items():
            with self.subTest(authority=key):
                self.assertTrue(locations)
                self.assertTrue(
                    all(location == MANIFEST[key] for location in locations)
                )

        h3_lineage = adapter_authority["h3_grammar_lineage_only"]
        self.assertEqual(h3_lineage["status"], "superseded-for-h4")
        self.assertFalse(h3_lineage["active_parent_authority"])

        active_parser = adapter_authority["h4_parent_parser_authority"]
        expected_parser = EXPECTED_EQUALITY_CONTRACT["active_h4_parent_parser"]
        self.assertEqual(active_parser["status"], "active-for-h4")
        self.assertEqual(active_parser["owner"], "H4 parent")
        self.assertEqual(
            active_parser["protocol_path"],
            EXPECTED_COMPONENT_ROWS[0]["path"],
        )
        self.assertEqual(
            active_parser["protocol_raw_sha256_binding"],
            "closed H4 authority manifest",
        )
        self.assertEqual(
            active_parser["projection_path"], expected_parser["protocol_projection"]
        )
        self.assertEqual(
            active_parser["projection_canonical_sha256"],
            expected_parser["projection_canonical_sha256"],
        )
        self.assertEqual(
            canonical_sha256(
                PROTOCOL["explicit_constraint"]["h4_parent_parser_contract"]
            ),
            expected_parser["projection_canonical_sha256"],
        )
        self.assertEqual(
            ADAPTER["parent_resolution_boundary"]["active_parent_parser_authority"],
            "authority_basis.h4_parent_parser_authority",
        )

    def test_no_corpus_case_result_or_evaluator_output_bindings(self) -> None:
        forbidden_keys = {
            "corpus",
            "corpus_authority",
            "corpus_binding",
            "corpus_id",
            "corpus_path",
            "prompt",
            "prompts",
            "case",
            "cases",
            "case_id",
            "case_ids",
            "case_path",
            "labels",
            "result",
            "results",
            "result_id",
            "result_path",
            "evaluator_output",
            "evaluator_outputs",
            "evaluator_output_id",
            "evaluator_output_path",
            "scores",
        }
        self.assertTrue(forbidden_keys.isdisjoint(recursive_keys(MANIFEST)))

        allowed_json_paths = {
            row["path"] for row in EXPECTED_COMPONENT_ROWS
        } | {binding["path"] for binding in EXPECTED_AUTHORITIES.values()}
        bound_json_paths = {
            value for value in recursive_strings(MANIFEST) if value.endswith(".json")
        }
        self.assertEqual(bound_json_paths, allowed_json_paths)
        strings = recursive_strings(MANIFEST)
        self.assertFalse(any("activation-heldout" in value for value in strings))
        self.assertFalse(any("activation-authoring" in value for value in strings))

    def test_mechanism_novelty_and_causal_target_are_prospective(self) -> None:
        self.assertEqual(MANIFEST["mechanism"], EXPECTED_MECHANISM)
        self.assertEqual(
            set(MANIFEST["mechanism"]["non_isomorphism"]),
            {"h1_adviser_ids", "h2_atom_sets", "h3_unary_facts"},
        )
        self.assertTrue(MANIFEST["mechanism"]["causal_target"]["prospective_only"])
        self.assertFalse(MANIFEST["mechanism"]["causal_target"]["aq7_diagnosis"])

    def test_diagnostics_are_predeclared_without_compensation(self) -> None:
        self.assertEqual(MANIFEST["diagnostics"], EXPECTED_DIAGNOSTICS)
        self.assertIs(type(MANIFEST["diagnostics"]["graph_validity_required_exact"]), int)
        self.assertEqual(
            MANIFEST["diagnostics"]["graph_validity_required_exact"], 1
        )

    def test_discriminators_and_invariants_match_the_protocol(self) -> None:
        self.assertEqual(
            MANIFEST["structural_discriminators"],
            PROTOCOL["structural_discriminators"],
        )
        self.assertEqual(
            [row["discriminator_id"] for row in MANIFEST["structural_discriminators"]],
            [
                "controller-and-downstream-select-root-only",
                "independent-pair-selects-both",
            ],
        )
        self.assertEqual(
            MANIFEST["structural_discriminators"][0]["expected"]["root_slots"],
            ["s0"],
        )
        self.assertEqual(
            MANIFEST["structural_discriminators"][1]["expected"]["root_slots"],
            ["s0", "s1"],
        )
        self.assertEqual(
            MANIFEST["structural_invariants"], PROTOCOL["structural_invariants"]
        )
        self.assertEqual(
            [row["invariant_id"] for row in MANIFEST["structural_invariants"]],
            ["single-direct-root", "no-unresolved-selects-none"],
        )

    def test_terminal_stop_freeze_order_and_claim_ceiling_are_exact(self) -> None:
        self.assertEqual(MANIFEST["terminal_stop"], EXPECTED_TERMINAL_STOP)
        self.assertEqual(
            MANIFEST["prospective_qualification_boundary"],
            EXPECTED_QUALIFICATION_BOUNDARY,
        )
        self.assertEqual(MANIFEST["claims_proven"], EXPECTED_CLAIMS_PROVEN)
        self.assertTrue(all(value is False for value in MANIFEST["claims_proven"].values()))

        protocol_policy = PROTOCOL["qualification_controls"]["aq8_failure_policy"]
        self.assertTrue(protocol_policy["terminal_stop"])
        self.assertFalse(protocol_policy["outcome_tuning_after_failure_permitted"])
        self.assertFalse(PROTOCOL["outcome_tuned"])
        self.assertFalse(ADAPTER["outcome_tuned"])
        self.assertFalse(
            REFERENCE_POLICY["qualification_controls"]["outcome_tuned"]
        )

    def test_component_surface_mutation_reds(self) -> None:
        mutations: list[tuple[str, dict[str, Any]]] = []

        wrong_role = deepcopy(MANIFEST)
        wrong_role["evaluator_surface"]["files"][0]["role"] = "resolver"
        mutations.append(("role", wrong_role))

        wrong_path = deepcopy(MANIFEST)
        wrong_path["evaluator_surface"]["files"][0]["path"] = "elsewhere.json"
        mutations.append(("path", wrong_path))

        wrong_hash = deepcopy(MANIFEST)
        wrong_hash["evaluator_surface"]["files"][0]["sha256"] = "0" * 64
        mutations.append(("hash", wrong_hash))

        wrong_order = deepcopy(MANIFEST)
        wrong_order["evaluator_surface"]["files"][0:2] = reversed(
            wrong_order["evaluator_surface"]["files"][0:2]
        )
        mutations.append(("order", wrong_order))

        missing = deepcopy(MANIFEST)
        missing["evaluator_surface"]["files"].pop()
        mutations.append(("missing", missing))

        extra = deepcopy(MANIFEST)
        extra["evaluator_surface"]["files"].append(
            deepcopy(extra["evaluator_surface"]["files"][0])
        )
        mutations.append(("extra", extra))

        for name, candidate in mutations:
            with self.subTest(mutation=name), self.assertRaises(ValueError):
                validate_manifest(candidate)

    def test_closed_surface_and_authority_mutation_reds(self) -> None:
        mutations: list[tuple[str, dict[str, Any]]] = []

        missing_top_level = deepcopy(MANIFEST)
        missing_top_level.pop("claims_proven")
        mutations.append(("missing_top_level", missing_top_level))

        extra_top_level = deepcopy(MANIFEST)
        extra_top_level["completion_claim"] = "AQ8 complete"
        mutations.append(("extra_top_level", extra_top_level))

        reordered_top_level = {
            key: MANIFEST[key] for key in reversed(EXPECTED_TOP_LEVEL_ORDER)
        }
        mutations.append(("top_level_order", reordered_top_level))

        wrong_authority_path = deepcopy(MANIFEST)
        wrong_authority_path["h2_catalog_authority"]["path"] = "elsewhere.json"
        mutations.append(("authority_path", wrong_authority_path))

        extra_authority_field = deepcopy(MANIFEST)
        extra_authority_field["h2_catalog_authority"]["branch"] = "master"
        mutations.append(("authority_extra", extra_authority_field))

        for name, candidate in mutations:
            with self.subTest(mutation=name), self.assertRaises(ValueError):
                validate_manifest(candidate)


if __name__ == "__main__":
    unittest.main()
