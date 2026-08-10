"""Corpus-blind structural checks for the AQ8 H4 condition adapter."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = (
    ROOT
    / "evals/foundation-v4/unresolved-decision-graph-condition-adapter-v8.json"
)
H2_COMMIT = "8ddf39198cb0e21f321a01a9755e009bb1c1860f"
H2_TREE = "1fbf9964b10831da051d2e5cafe29b6086d4d599"
H2_PATH = "evals/foundation-v4/decision-atom-candidate-v4.json"
H2_SHA256 = "50fffcf10170cd022d78428909d0679527439a002a7e07dac30e321bbaff61d9"
H2_BLOB = "c3e1f89ded468592e3ada8f23f7336c89f0d580d"
H3_COMMIT = "ccbe06be9a2ef5feca4104b6918985ee9c4527c0"
H3_TREE = "dd20449fdc45a73c55adb349d8c828687728ef4d"
H3_PATH = "evals/foundation-v4/decision-certificate-protocol-v6.json"
H3_SHA256 = "9ad483a26fe339f81c947507de9c1c66d54b2823a38f68b1c5ee7fdf5c426f84"
H4_PROTOCOL_PATH = "evals/foundation-v4/unresolved-decision-graph-protocol-v8.json"

SLOT_ORDER = ["s0", "s1", "s2", "s3"]
PAIR_ORDER = [
    ["s0", "s1"],
    ["s0", "s2"],
    ["s0", "s3"],
    ["s1", "s2"],
    ["s1", "s3"],
    ["s2", "s3"],
]
GUIDANCE_KEYS = [
    "slot_id",
    "declared_scope",
    "positive_boundary",
    "admission_rule",
    "pairwise_boundaries",
]
PAIRWISE_BOUNDARY_KEYS = ["other_slot_id", "boundary"]
PACKET_KEYS = [
    "instruction",
    "task_text",
    "slot_order",
    "pair_order",
    "condition_guidance",
    "support_legend",
]
INSTRUCTION = (
    "Read the task text using the ordered anonymous decision guidance and support "
    "legend. Return only the three exact ordered arrays required by the frozen H4 "
    "output contract: four candidate states in slot order, six pairwise relations "
    "in pair order, and four reference needs in slot order. A candidate state is "
    "unresolved when the decision remains, resolved_or_absent when it does not "
    "remain, and uncertain when applicability cannot be established. For two "
    "unresolved slots, use left_controls_right_downstream when the left slot "
    "controls the right slot downstream, right_controls_left_downstream when the "
    "right slot controls the left slot downstream, independent when neither "
    "controls the other, or uncertain when the relation cannot be established. Use "
    "unrelated when at least one endpoint is resolved_or_absent. A pair incident to "
    "an uncertain state must use uncertain. Reference needs are none, primary, "
    "secondary, or uncertain and never affect routing."
)
INSTRUCTION_SEMANTIC_CLAUSES = (
    "three exact ordered arrays",
    "four candidate states in slot order",
    "six pairwise relations in pair order",
    "four reference needs in slot order",
    "unresolved when the decision remains",
    "resolved_or_absent when it does not remain",
    "uncertain when applicability cannot be established",
    "For two unresolved slots, use left_controls_right_downstream",
    "right_controls_left_downstream when the right slot controls the left slot downstream",
    "independent when neither controls the other",
    "uncertain when the relation cannot be established",
    "Use unrelated when at least one endpoint is resolved_or_absent",
    "A pair incident to an uncertain state must use uncertain",
    "Reference needs are none, primary, secondary, or uncertain and never affect routing",
)
SUPPORT_LEGEND = [
    {
        "slot_id": "s0",
        "primary": "smallest decomposition boundary",
        "secondary": "architecture/control boundary",
    },
    {
        "slot_id": "s1",
        "primary": "task outcome/authority/evidence/done contract",
        "secondary": "assumption/approval/reference-isolation boundary",
    },
    {
        "slot_id": "s2",
        "primary": "proportional verification evidence/mode",
        "secondary": "effect/field/reference-isolation boundary",
    },
    {
        "slot_id": "s3",
        "primary": "failure attribution/adaptation",
        "secondary": "knowledge/evaluation lifecycle adoption",
    },
]

EXPECTED_AUTHORITY_BASIS = {
    "h2_catalog": {
        "commit": H2_COMMIT,
        "tree": H2_TREE,
        "path": H2_PATH,
        "sha256": H2_SHA256,
        "git_blob_sha1": H2_BLOB,
        "source_slot_order_canonical_sha256": (
            "852f84da56a3a658c9de7d66fbb202b71c626fa61782d76dfe7daf846b01c860"
        ),
    },
    "h3_grammar_lineage_only": {
        "classification": "frozen-superseded-lineage-only",
        "commit": H3_COMMIT,
        "tree": H3_TREE,
        "protocol_path": H3_PATH,
        "protocol_sha256": H3_SHA256,
        "projection_path": "explicit_constraint.qualified_invocation_grammar",
        "projection_canonical_sha256": (
            "4900859123c43250b1622f461e8cf6e2f11df97d50e85f6cadd46906ef4e34c5"
        ),
        "status": "superseded-for-h4",
        "active_parent_authority": False,
    },
    "h4_parent_parser_authority": {
        "classification": "active-parent-parser-authority",
        "protocol_path": H4_PROTOCOL_PATH,
        "protocol_raw_sha256_binding": "closed H4 authority manifest",
        "projection_path": "explicit_constraint.h4_parent_parser_contract",
        "projection_canonical_sha256": (
            "8920ab58abd9618fb1af4894e1b664d76d3c6f478d335e1d61e08ac47b9360d1"
        ),
        "status": "active-for-h4",
        "owner": "H4 parent",
    },
}

EXPECTED_SOURCE_CUSTODY = {
    "derivation_input": {
        "classification": "controlling-frozen-git-object-only",
        "commit": H2_COMMIT,
        "tree": H2_TREE,
        "path": H2_PATH,
        "sha256": H2_SHA256,
        "git_blob_sha1": H2_BLOB,
    },
    "live_workspace_observation": {
        "classification": "known-different-lineage-not-a-derivation-input",
        "path": H2_PATH,
        "sha256": "8f7d2d61cee5de217077d3767f3e6454a92c1a29c94fa4f73f121065a50e25cc",
        "git_blob_sha1": "fba49224df0791c4dc44e22d1ef44cc0fd983b2d",
        "substitution_permitted": False,
    },
    "substitution_policy": (
        "Read the derivation input only with git show at the frozen commit and path "
        "after commit, tree, raw SHA-256, and blob identity checks. Never substitute "
        "live workspace bytes, even when a permitted projection happens to compare "
        "equal."
    ),
}

EXPECTED_QUALIFICATION_BOUNDARY = {
    "operationalizes": "H4 condition packet construction only",
    "does_not_establish": (
        "behavioral qualification or any runtime, product, efficacy, promotion, "
        "authority, effect, or external-action claim"
    ),
    "fresh_blinded_holdout_required": True,
    "authorized_observation_schedule": "one_canary_then_one_batch",
    "no_replay": True,
    "replay_permitted": False,
    "aq8_failure_terminal_stop": True,
}

EXPECTED_MODEL_OUTPUT_CONTRACT = {
    "schema_path": (
        "evals/foundation-v4/unresolved-decision-graph-selector-output-schema-v8.json"
    ),
    "sibling_digest_binding": "deferred to the closed H4 authority manifest",
    "only_top_level_keys": [
        "candidate_states",
        "pairwise_relations",
        "reference_needs",
    ],
    "candidate_state_count": 4,
    "pairwise_relation_count": 6,
    "reference_need_count": 4,
    "additional_properties": False,
    "condition_identical": True,
    "model_must_not_output": [
        "selected_slots",
        "root_slots",
        "graph_status",
        "automatic_selection_status",
        "selection_status",
        "logical_atoms",
        "atoms",
        "advisers",
        "routes",
        "authority",
        "effects",
        "claims",
    ],
}

EXPECTED_CONDITION_IDENTITY_CONTRACT = {
    "same_task_text_required": True,
    "only_condition_variant": "condition_guidance",
    "packet_fields_identical": [
        "instruction",
        "task_text",
        "slot_order",
        "pair_order",
        "support_legend",
    ],
    "condition_invariant_surfaces": [
        "model_output_contract",
        "parent_resolver",
        "model",
        "reasoning_effort",
        "tools",
        "host",
    ],
    "identity_values": {
        "model_output_contract": (
            "same exact semantic schema path and SHA-256 bound by the closed H4 "
            "authority manifest"
        ),
        "parent_resolver": (
            "same exact parent resolver path and SHA-256 bound by the closed H4 "
            "authority manifest"
        ),
        "model": "same exact model identity",
        "reasoning_effort": "same exact reasoning effort",
        "tools": "same exact tools profile",
        "host": "same exact host execution profile",
    },
}

EXPECTED_PARENT_RESOLUTION_BOUNDARY = {
    "protocol_path": "evals/foundation-v4/unresolved-decision-graph-protocol-v8.json",
    "sibling_digest_binding": "deferred to the closed H4 authority manifest",
    "identical_for_all_conditions": True,
    "model_visible": False,
    "active_parent_parser_authority": "authority_basis.h4_parent_parser_authority",
    "condition_guidance_must_not_control": [
        "explicit invocation parsing",
        "parent graph validation",
        "root selection",
        "slot-to-adviser mapping",
        "support resolution",
        "authority assignment",
        "effects",
    ],
    "reference_needs_must_not_control": [
        "pair compatibility",
        "edge construction",
        "cycle detection",
        "transitive closure",
        "root selection",
        "automatic selection status",
        "explicit invocation selection",
        "selected slots",
    ],
    "prohibitions": [
        "no_model_owned_selection",
        "no_authority_assignment",
        "no_policy_adoption",
        "no_effect_execution",
        "no_external_action",
        "no_completion_claim",
        "no_efficacy_claim",
        "no_runtime_claim",
        "no_provider_claim",
        "no_product_claim",
        "no_promotion_claim",
    ],
}

FORBIDDEN_ASSERTION_KEYS = {
    "claims",
    "assertions",
    "completion",
    "runtime",
    "provider",
    "product",
    "promotion",
    "completion_claim",
    "completion_assertion",
    "runtime_claim",
    "runtime_assertion",
    "provider_claim",
    "provider_assertion",
    "product_claim",
    "product_assertion",
    "promotion_claim",
    "promotion_assertion",
}
FORBIDDEN_ASSERTION_VALUES = {
    "completion established",
    "runtime behavior established",
    "provider behavior established",
    "product behavior established",
    "promotion authorized",
}

EXPECTED_TOP_LEVEL_KEYS = {
    "schema_version",
    "adapter_id",
    "status",
    "claim_ceiling",
    "corpus_blind",
    "outcome_tuned",
    "model_agnostic",
    "qualification_boundary",
    "authority_basis",
    "source_custody",
    "mechanical_transformation",
    "slot_order",
    "pair_order",
    "support_legend_authority",
    "support_legend_canonical_sha256",
    "support_legend",
    "packet_contract",
    "model_output_contract",
    "condition_identity_contract",
    "parent_resolution_boundary",
    "condition_difference_contract",
    "conditions",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def raw_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_bytes(revision: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def git_revision(expression: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", expression], cwd=ROOT, text=True
    ).strip()


def git_blob_for_bytes(value: bytes) -> str:
    return subprocess.check_output(
        ["git", "hash-object", "--stdin"], cwd=ROOT, input=value
    ).decode("utf-8").strip()


def recursive_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(recursive_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(recursive_keys(item) for item in value))
    return set()


class UnresolvedDecisionGraphConditionAdapterV8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = json.loads(ADAPTER_PATH.read_text(encoding="utf-8"))
        cls.h2_bytes = git_bytes(H2_COMMIT, H2_PATH)
        cls.h2 = json.loads(cls.h2_bytes)
        cls.h3_bytes = git_bytes(H3_COMMIT, H3_PATH)
        cls.h3 = json.loads(cls.h3_bytes)
        cls.h4_protocol = json.loads(
            (ROOT / H4_PROTOCOL_PATH).read_text(encoding="utf-8")
        )

    def assert_exact_authority_basis(self, value: dict[str, Any]) -> None:
        self.assertEqual(value, EXPECTED_AUTHORITY_BASIS)

    def assert_exact_active_parser_authority(
        self, adapter: dict[str, Any], protocol: dict[str, Any]
    ) -> None:
        authority = adapter["authority_basis"]
        self.assert_exact_authority_basis(authority)
        active = authority["h4_parent_parser_authority"]
        self.assertEqual(active["protocol_path"], H4_PROTOCOL_PATH)
        self.assertEqual(
            canonical_sha256(
                protocol["explicit_constraint"]["h4_parent_parser_contract"]
            ),
            active["projection_canonical_sha256"],
        )
        boundary = protocol["explicit_constraint"]["h4_parent_parser_contract"][
            "boundary"
        ]
        self.assertEqual(
            boundary["disallowed_unicode_general_category_prefixes"],
            ["L", "N", "M"],
        )
        self.assertEqual(
            boundary["disallowed_unicode_general_categories"], ["Cf", "Pc"]
        )
        self.assertEqual(
            boundary["retained_rejection_fixtures"],
            [
                {"codepoint": "U+200C", "category": "Cf"},
                {"codepoint": "U+200D", "category": "Cf"},
                {"codepoint": "U+2060", "category": "Cf"},
                {"codepoint": "U+FEFF", "category": "Cf"},
                {"codepoint": "U+202E", "category": "Cf"},
                {"codepoint": "U+203F", "category": "Pc"},
            ],
        )
        lineage = authority["h3_grammar_lineage_only"]
        protocol_lineage = protocol["explicit_constraint"][
            "superseded_h3_grammar_lineage"
        ]
        self.assertEqual(lineage["protocol_path"], protocol_lineage["authority_path"])
        self.assertEqual(
            lineage["protocol_sha256"], protocol_lineage["authority_sha256"]
        )
        self.assertEqual(
            lineage["projection_path"], protocol_lineage["superseded_surface"]
        )
        self.assertEqual(lineage["status"], protocol_lineage["status"])
        self.assertFalse(lineage["active_parent_authority"])
        self.assertEqual(
            adapter["parent_resolution_boundary"][
                "active_parent_parser_authority"
            ],
            "authority_basis.h4_parent_parser_authority",
        )

    def assert_exact_source_custody(self, value: dict[str, Any]) -> None:
        self.assertEqual(value, EXPECTED_SOURCE_CUSTODY)

    def assert_no_forbidden_claim_assertions(
        self, value: Any, path: tuple[str, ...] = ()
    ) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_path = (*path, key)
                self.assertNotIn(key, FORBIDDEN_ASSERTION_KEYS, ".".join(key_path))
                self.assertFalse(
                    key.endswith("_claim") or key.endswith("_assertion"),
                    ".".join(key_path),
                )
                self.assert_no_forbidden_claim_assertions(item, key_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                self.assert_no_forbidden_claim_assertions(item, (*path, str(index)))
        elif isinstance(value, str):
            for forbidden_value in FORBIDDEN_ASSERTION_VALUES:
                self.assertNotIn(
                    forbidden_value, value.lower(), ".".join(path)
                )

    def assert_exact_safety_contract(self, adapter: dict[str, Any]) -> None:
        self.assertEqual(set(adapter), EXPECTED_TOP_LEVEL_KEYS)
        self.assertEqual(adapter["status"], "frozen-proposal-only")
        self.assertEqual(adapter["claim_ceiling"], "structural-proposal-only")
        self.assertTrue(adapter["corpus_blind"])
        self.assertFalse(adapter["outcome_tuned"])
        self.assertTrue(adapter["model_agnostic"])
        self.assertEqual(
            adapter["qualification_boundary"], EXPECTED_QUALIFICATION_BOUNDARY
        )
        self.assertEqual(
            adapter["model_output_contract"], EXPECTED_MODEL_OUTPUT_CONTRACT
        )
        self.assertEqual(
            adapter["condition_identity_contract"],
            EXPECTED_CONDITION_IDENTITY_CONTRACT,
        )
        self.assertEqual(
            adapter["parent_resolution_boundary"],
            EXPECTED_PARENT_RESOLUTION_BOUNDARY,
        )
        for condition in ("current", "reduced"):
            self.assertEqual(
                set(adapter["conditions"][condition]),
                {
                    "source_atom_catalog_canonical_sha256",
                    "condition_guidance_canonical_sha256",
                    "condition_guidance",
                },
            )
        self.assert_no_forbidden_claim_assertions(adapter)

    def assert_exact_h2_derivation_identity(
        self,
        *,
        revision: str,
        tree: str,
        path: str,
        source_bytes: bytes,
    ) -> None:
        self.assertEqual(revision, H2_COMMIT)
        self.assertEqual(tree, H2_TREE)
        self.assertEqual(path, H2_PATH)
        self.assertEqual(raw_sha256(source_bytes), H2_SHA256)
        self.assertEqual(git_blob_for_bytes(source_bytes), H2_BLOB)

    @staticmethod
    def reconstruct_guidance(
        h2: dict[str, Any], condition: str
    ) -> list[dict[str, Any]]:
        current_rows = h2["conditions"]["current"]["atom_catalog"]
        reduced_rows = h2["conditions"]["reduced"]["atom_catalog"]
        current_order = [row["atom_id"] for row in current_rows]
        reduced_order = [row["atom_id"] for row in reduced_rows]
        if current_order != reduced_order or len(current_order) != len(SLOT_ORDER):
            raise ValueError("frozen H2 condition catalogs do not share four-row order")
        source_to_slot = dict(zip(current_order, SLOT_ORDER, strict=True))
        guidance: list[dict[str, Any]] = []
        for slot_id, row in zip(
            SLOT_ORDER, h2["conditions"][condition]["atom_catalog"], strict=True
        ):
            pairwise_boundaries = []
            for exclusion in row["pairwise_exclusions"]:
                source_id = exclusion["atom_id"]
                if source_id not in source_to_slot or source_id == row["atom_id"]:
                    raise ValueError("invalid frozen H2 pairwise source mapping")
                pairwise_boundaries.append(
                    {
                        "other_slot_id": source_to_slot[source_id],
                        "boundary": exclusion["boundary"],
                    }
                )
            guidance.append(
                {
                    "slot_id": slot_id,
                    "declared_scope": row["declared_scope"],
                    "positive_boundary": row["positive_boundary"],
                    "admission_rule": row["admission_rule"],
                    "pairwise_boundaries": pairwise_boundaries,
                }
            )
        return guidance

    def condition_packet(self, condition: str, task_text: str) -> dict[str, Any]:
        return {
            "instruction": self.adapter["packet_contract"]["instruction"],
            "task_text": task_text,
            "slot_order": self.adapter["slot_order"],
            "pair_order": self.adapter["pair_order"],
            "condition_guidance": self.adapter["conditions"][condition][
                "condition_guidance"
            ],
            "support_legend": self.adapter["support_legend"],
        }

    def test_closed_structural_proposal_and_terminal_boundary(self) -> None:
        self.assert_exact_safety_contract(self.adapter)
        self.assertEqual(self.adapter["schema_version"], "8.0")
        self.assertEqual(
            self.adapter["adapter_id"],
            "AQ8-unresolved-decision-graph-condition-adapter",
        )
        self.assertEqual(self.adapter["status"], "frozen-proposal-only")
        self.assertEqual(self.adapter["claim_ceiling"], "structural-proposal-only")
        self.assertTrue(self.adapter["corpus_blind"])
        self.assertFalse(self.adapter["outcome_tuned"])
        self.assertTrue(self.adapter["model_agnostic"])
        boundary = self.adapter["qualification_boundary"]
        self.assertEqual(boundary, EXPECTED_QUALIFICATION_BOUNDARY)
        self.assertTrue(boundary["fresh_blinded_holdout_required"])
        self.assertTrue(boundary["no_replay"])
        self.assertFalse(boundary["replay_permitted"])
        self.assertTrue(boundary["aq8_failure_terminal_stop"])

    def test_exact_frozen_h2_h3_lineage_and_active_h4_authorities_are_bound(self) -> None:
        self.assert_exact_authority_basis(self.adapter["authority_basis"])
        self.assertEqual(git_revision(f"{H2_COMMIT}^{{commit}}"), H2_COMMIT)
        self.assertEqual(git_revision(f"{H2_COMMIT}^{{tree}}"), H2_TREE)
        self.assertEqual(raw_sha256(self.h2_bytes), H2_SHA256)
        self.assertEqual(git_revision(f"{H2_COMMIT}:{H2_PATH}"), H2_BLOB)
        self.assertEqual(git_revision(f"{H3_COMMIT}^{{commit}}"), H3_COMMIT)
        self.assertEqual(git_revision(f"{H3_COMMIT}^{{tree}}"), H3_TREE)
        self.assertEqual(raw_sha256(self.h3_bytes), H3_SHA256)

        source_order = [
            row["atom_id"]
            for row in self.h2["conditions"]["current"]["atom_catalog"]
        ]
        self.assertEqual(
            canonical_sha256(source_order),
            EXPECTED_AUTHORITY_BASIS["h2_catalog"][
                "source_slot_order_canonical_sha256"
            ],
        )
        self.assertEqual(
            canonical_sha256(
                self.h3["explicit_constraint"]["qualified_invocation_grammar"]
            ),
            EXPECTED_AUTHORITY_BASIS["h3_grammar_lineage_only"][
                "projection_canonical_sha256"
            ],
        )
        self.assert_exact_active_parser_authority(
            self.adapter, self.h4_protocol
        )

    def test_authority_commit_tree_path_and_digest_drift_is_red(self) -> None:
        mutations = (
            ("h2_catalog", "commit", "0" * 40),
            ("h2_catalog", "tree", "0" * 40),
            ("h2_catalog", "path", "wrong/catalog.json"),
            ("h2_catalog", "sha256", "0" * 64),
            ("h2_catalog", "git_blob_sha1", "0" * 40),
            ("h2_catalog", "source_slot_order_canonical_sha256", "0" * 64),
            ("h3_grammar_lineage_only", "classification", "active-authority"),
            ("h3_grammar_lineage_only", "commit", "0" * 40),
            ("h3_grammar_lineage_only", "tree", "0" * 40),
            ("h3_grammar_lineage_only", "protocol_path", "wrong/protocol.json"),
            ("h3_grammar_lineage_only", "protocol_sha256", "0" * 64),
            ("h3_grammar_lineage_only", "projection_path", "wrong_projection"),
            ("h3_grammar_lineage_only", "projection_canonical_sha256", "0" * 64),
            ("h3_grammar_lineage_only", "status", "active-for-h4"),
            ("h3_grammar_lineage_only", "active_parent_authority", True),
            ("h4_parent_parser_authority", "classification", "lineage-only"),
            ("h4_parent_parser_authority", "protocol_path", "wrong/protocol.json"),
            ("h4_parent_parser_authority", "protocol_raw_sha256_binding", "unbound"),
            ("h4_parent_parser_authority", "projection_path", "wrong_projection"),
            ("h4_parent_parser_authority", "projection_canonical_sha256", "0" * 64),
            ("h4_parent_parser_authority", "status", "superseded-for-h4"),
            ("h4_parent_parser_authority", "owner", "H3 parent"),
        )
        for section, field, replacement in mutations:
            with self.subTest(section=section, field=field):
                mutated = deepcopy(self.adapter["authority_basis"])
                mutated[section][field] = replacement
                with self.assertRaises(AssertionError):
                    self.assert_exact_authority_basis(mutated)

    def test_old_h3_active_label_and_h4_parser_contract_drift_are_red(self) -> None:
        self.assert_exact_active_parser_authority(self.adapter, self.h4_protocol)

        old_labeling = deepcopy(self.adapter)
        old_labeling["authority_basis"]["h3_explicit_grammar"] = (
            old_labeling["authority_basis"].pop("h3_grammar_lineage_only")
        )
        old_labeling["authority_basis"].pop("h4_parent_parser_authority")
        old_labeling["parent_resolution_boundary"].pop(
            "active_parent_parser_authority"
        )
        old_labeling["parent_resolution_boundary"]["explicit_grammar_authority"] = (
            "authority_basis.h3_explicit_grammar"
        )
        with self.assertRaises(AssertionError):
            self.assert_exact_active_parser_authority(
                old_labeling, self.h4_protocol
            )

        h3_reactivated = deepcopy(self.adapter)
        h3_reactivated["authority_basis"]["h3_grammar_lineage_only"].update(
            {"status": "active-for-h4", "active_parent_authority": True}
        )
        with self.assertRaises(AssertionError):
            self.assert_exact_active_parser_authority(
                h3_reactivated, self.h4_protocol
            )

        stale_parent_pointer = deepcopy(self.adapter)
        stale_parent_pointer["parent_resolution_boundary"][
            "active_parent_parser_authority"
        ] = "authority_basis.h3_grammar_lineage_only"
        with self.assertRaises(AssertionError):
            self.assert_exact_active_parser_authority(
                stale_parent_pointer, self.h4_protocol
            )

        pre_cf_pc_projection = deepcopy(self.adapter)
        pre_cf_pc_projection["authority_basis"]["h4_parent_parser_authority"][
            "projection_canonical_sha256"
        ] = "33f90544d60f2eb3e094a17d5c4f2bf4001d358d16fbdd8c6f2c4c0f217f4ba1"
        with self.assertRaises(AssertionError):
            self.assert_exact_active_parser_authority(
                pre_cf_pc_projection, self.h4_protocol
            )

        changed_h4_contract = deepcopy(self.h4_protocol)
        changed_h4_contract["explicit_constraint"]["h4_parent_parser_contract"][
            "normalization"
        ] = "none"
        with self.assertRaises(AssertionError):
            self.assert_exact_active_parser_authority(
                self.adapter, changed_h4_contract
            )

    def test_frozen_custody_rejects_live_workspace_substitution(self) -> None:
        self.assert_exact_source_custody(self.adapter["source_custody"])
        self.assert_exact_h2_derivation_identity(
            revision=H2_COMMIT,
            tree=H2_TREE,
            path=H2_PATH,
            source_bytes=self.h2_bytes,
        )
        live_bytes = (ROOT / H2_PATH).read_bytes()
        live_observation = self.adapter["source_custody"][
            "live_workspace_observation"
        ]
        self.assertEqual(raw_sha256(live_bytes), live_observation["sha256"])
        self.assertEqual(git_blob_for_bytes(live_bytes), live_observation["git_blob_sha1"])
        self.assertNotEqual(live_observation["sha256"], H2_SHA256)
        self.assertNotEqual(live_observation["git_blob_sha1"], H2_BLOB)
        self.assertFalse(live_observation["substitution_permitted"])
        with self.assertRaises(AssertionError):
            self.assert_exact_h2_derivation_identity(
                revision="WORKTREE",
                tree="WORKTREE",
                path=H2_PATH,
                source_bytes=live_bytes,
            )
        mutated_frozen = self.h2_bytes + b"\n"
        with self.assertRaises(AssertionError):
            self.assert_exact_h2_derivation_identity(
                revision=H2_COMMIT,
                tree=H2_TREE,
                path=H2_PATH,
                source_bytes=mutated_frozen,
            )
        for field, replacement in (
            ("commit", "0" * 40),
            ("tree", "0" * 40),
            ("path", "wrong/catalog.json"),
            ("sha256", "0" * 64),
            ("git_blob_sha1", "0" * 40),
        ):
            with self.subTest(custody_field=field):
                mutated_custody = deepcopy(self.adapter["source_custody"])
                mutated_custody["derivation_input"][field] = replacement
                with self.assertRaises(AssertionError):
                    self.assert_exact_source_custody(mutated_custody)

    def test_slot_pair_and_guidance_keys_are_closed_and_ordered(self) -> None:
        self.assertEqual(self.adapter["slot_order"], SLOT_ORDER)
        self.assertEqual(self.adapter["pair_order"], PAIR_ORDER)
        self.assertTrue(all(len(pair) == 2 for pair in PAIR_ORDER))
        self.assertTrue(all(left != right for left, right in PAIR_ORDER))
        self.assertEqual(
            self.adapter["mechanical_transformation"]["output_guidance_keys"],
            GUIDANCE_KEYS,
        )
        self.assertEqual(
            self.adapter["mechanical_transformation"]["pairwise_boundary_keys"],
            PAIRWISE_BOUNDARY_KEYS,
        )
        for condition in ("current", "reduced"):
            condition_data = self.adapter["conditions"][condition]
            self.assertEqual(
                set(condition_data),
                {
                    "source_atom_catalog_canonical_sha256",
                    "condition_guidance_canonical_sha256",
                    "condition_guidance",
                },
            )
            guidance = condition_data["condition_guidance"]
            self.assertEqual([row["slot_id"] for row in guidance], SLOT_ORDER)
            for row in guidance:
                self.assertEqual(list(row), GUIDANCE_KEYS)
                self.assertEqual(len(row["pairwise_boundaries"]), 3)
                self.assertNotIn(row["slot_id"], {
                    item["other_slot_id"] for item in row["pairwise_boundaries"]
                })
                for pairwise in row["pairwise_boundaries"]:
                    self.assertEqual(list(pairwise), PAIRWISE_BOUNDARY_KEYS)

    def test_guidance_and_digests_are_exact_frozen_h2_projections(self) -> None:
        for condition in ("current", "reduced"):
            with self.subTest(condition=condition):
                source_rows = self.h2["conditions"][condition]["atom_catalog"]
                condition_data = self.adapter["conditions"][condition]
                expected = self.reconstruct_guidance(self.h2, condition)
                actual = condition_data["condition_guidance"]
                self.assertEqual(canonical_bytes(actual), canonical_bytes(expected))
                self.assertEqual(
                    canonical_sha256(source_rows),
                    condition_data["source_atom_catalog_canonical_sha256"],
                )
                self.assertEqual(
                    canonical_sha256(actual),
                    condition_data["condition_guidance_canonical_sha256"],
                )
                self.assertNotEqual(list(reversed(actual)), expected)
                self.assertNotEqual(actual[:-1], expected)

    def test_only_declared_scope_differs_between_condition_guidance(self) -> None:
        current = self.adapter["conditions"]["current"]["condition_guidance"]
        reduced = self.adapter["conditions"]["reduced"]["condition_guidance"]
        differing_fields: set[str] = set()
        for current_row, reduced_row in zip(current, reduced, strict=True):
            self.assertEqual(current_row["slot_id"], reduced_row["slot_id"])
            differing_fields.update(
                key
                for key in GUIDANCE_KEYS
                if current_row[key] != reduced_row[key]
            )
        self.assertEqual(differing_fields, {"declared_scope"})
        self.assertTrue(
            all(
                current_row["declared_scope"] != reduced_row["declared_scope"]
                for current_row, reduced_row in zip(current, reduced, strict=True)
            )
        )
        self.assertEqual(
            self.adapter["condition_difference_contract"],
            {
                "comparison_unit": "same slot_id at the same frozen position",
                "permitted_differing_guidance_fields": ["declared_scope"],
                "observed_differing_guidance_fields": ["declared_scope"],
                "observed_identical_guidance_fields": [
                    "slot_id",
                    "positive_boundary",
                    "admission_rule",
                    "pairwise_boundaries",
                ],
                "pairwise_boundaries_condition_specific": False,
                "digest_paths": {
                    "current": (
                        "conditions.current.condition_guidance_canonical_sha256"
                    ),
                    "reduced": (
                        "conditions.reduced.condition_guidance_canonical_sha256"
                    ),
                },
            },
        )
        current_digest = canonical_sha256(current)
        reduced_digest = canonical_sha256(reduced)
        self.assertNotEqual(current_digest, reduced_digest)
        self.assertEqual(
            current_digest,
            self.adapter["conditions"]["current"][
                "condition_guidance_canonical_sha256"
            ],
        )
        self.assertEqual(
            reduced_digest,
            self.adapter["conditions"]["reduced"][
                "condition_guidance_canonical_sha256"
            ],
        )

    def test_support_legend_is_closed_anonymous_identical_and_digest_bound(self) -> None:
        self.assertEqual(self.adapter["support_legend"], SUPPORT_LEGEND)
        self.assertEqual(
            [row["slot_id"] for row in self.adapter["support_legend"]], SLOT_ORDER
        )
        self.assertTrue(
            all(list(row) == ["slot_id", "primary", "secondary"] for row in SUPPORT_LEGEND)
        )
        self.assertEqual(
            canonical_sha256(self.adapter["support_legend"]),
            self.adapter["support_legend_canonical_sha256"],
        )
        authority = self.adapter["support_legend_authority"]
        self.assertEqual(
            authority["path"],
            "evals/foundation-v4/unresolved-decision-graph-reference-policy-v8.json",
        )
        self.assertTrue(authority["condition_identical"])
        self.assertEqual(
            authority["sibling_digest_binding"],
            "deferred to the closed H4 authority manifest",
        )

    def test_packet_has_exact_six_keys_and_only_guidance_varies(self) -> None:
        contract = self.adapter["packet_contract"]
        self.assertEqual(contract["packet_keys"], PACKET_KEYS)
        self.assertEqual(contract["instruction"], INSTRUCTION)
        for clause in INSTRUCTION_SEMANTIC_CLAUSES:
            with self.subTest(instruction_clause=clause):
                self.assertIn(clause, INSTRUCTION)
        instruction_forbidden_names = (
            "$agentic-engineering",
            "$codex-task-contract",
            "$verification-strategy-engineering",
            "$engineering-learning-loop",
            "topology-control-boundary",
            "task-contract",
            "verification-strategy",
            "engineering-learning",
            "adviser",
            "atom",
            "route",
            "payload",
        )
        self.assertTrue(
            all(name not in INSTRUCTION for name in instruction_forbidden_names)
        )
        current = self.condition_packet("current", "same task text")
        reduced = self.condition_packet("reduced", "same task text")
        self.assertEqual(list(current), PACKET_KEYS)
        self.assertEqual(list(reduced), PACKET_KEYS)
        changed = {key for key in PACKET_KEYS if current[key] != reduced[key]}
        self.assertEqual(changed, {"condition_guidance"})
        self.assertNotEqual(canonical_sha256(current), canonical_sha256(reduced))
        self.assertEqual(
            contract["condition_variance"],
            "Only condition_guidance may differ between condition packets for the same task text.",
        )

    def test_output_parent_and_execution_identity_are_condition_invariant(self) -> None:
        output = self.adapter["model_output_contract"]
        self.assertEqual(output, EXPECTED_MODEL_OUTPUT_CONTRACT)
        self.assertEqual(
            output["schema_path"],
            "evals/foundation-v4/unresolved-decision-graph-selector-output-schema-v8.json",
        )
        self.assertEqual(
            output["only_top_level_keys"],
            ["candidate_states", "pairwise_relations", "reference_needs"],
        )
        self.assertEqual(
            (
                output["candidate_state_count"],
                output["pairwise_relation_count"],
                output["reference_need_count"],
            ),
            (4, 6, 4),
        )
        self.assertFalse(output["additional_properties"])
        self.assertTrue(output["condition_identical"])
        self.assertEqual(
            output["model_must_not_output"],
            EXPECTED_MODEL_OUTPUT_CONTRACT["model_must_not_output"],
        )

        identity = self.adapter["condition_identity_contract"]
        self.assertEqual(identity, EXPECTED_CONDITION_IDENTITY_CONTRACT)
        self.assertTrue(identity["same_task_text_required"])
        self.assertEqual(identity["only_condition_variant"], "condition_guidance")
        self.assertEqual(
            identity["packet_fields_identical"],
            ["instruction", "task_text", "slot_order", "pair_order", "support_legend"],
        )
        self.assertEqual(
            identity["condition_invariant_surfaces"],
            [
                "model_output_contract",
                "parent_resolver",
                "model",
                "reasoning_effort",
                "tools",
                "host",
            ],
        )
        self.assertEqual(set(identity["identity_values"]), set(identity["condition_invariant_surfaces"]))
        parent = self.adapter["parent_resolution_boundary"]
        self.assertEqual(parent, EXPECTED_PARENT_RESOLUTION_BOUNDARY)
        self.assertTrue(parent["identical_for_all_conditions"])
        self.assertFalse(parent["model_visible"])
        self.assertEqual(
            parent["active_parent_parser_authority"],
            "authority_basis.h4_parent_parser_authority",
        )
        self.assertIn(
            "root selection", parent["condition_guidance_must_not_control"]
        )
        self.assertIn(
            "root selection", parent["reference_needs_must_not_control"]
        )
        self.assertEqual(
            parent["prohibitions"],
            EXPECTED_PARENT_RESOLUTION_BOUNDARY["prohibitions"],
        )

    def test_claim_identity_and_noninterference_mutations_are_red(self) -> None:
        def inject_nested_assertion(adapter: dict[str, Any], key: str) -> None:
            adapter["mechanical_transformation"]["nested_assertion_probe"] = {
                key: True
            }

        mutations = (
            (
                "reverse does_not_establish",
                lambda value: value["qualification_boundary"].__setitem__(
                    "does_not_establish",
                    "behavioral qualification and runtime behavior are established",
                ),
            ),
            (
                "remove does_not_establish",
                lambda value: value["qualification_boundary"].pop(
                    "does_not_establish"
                ),
            ),
            (
                "weaken claim ceiling",
                lambda value: value.__setitem__("claim_ceiling", "runtime-proven"),
            ),
            (
                "enable outcome tuning",
                lambda value: value.__setitem__("outcome_tuned", True),
            ),
            (
                "remove terminal stop",
                lambda value: value["qualification_boundary"].__setitem__(
                    "aq8_failure_terminal_stop", False
                ),
            ),
            (
                "set model as condition variant",
                lambda value: value["condition_identity_contract"].__setitem__(
                    "only_condition_variant", "model"
                ),
            ),
            (
                "inject condition-local model",
                lambda value: value["conditions"]["current"].__setitem__(
                    "model", "condition-specific-model"
                ),
            ),
            (
                "remove model identity invariant",
                lambda value: value["condition_identity_contract"][
                    "condition_invariant_surfaces"
                ].remove("model"),
            ),
            (
                "remove guidance root-selection noninterference",
                lambda value: value["parent_resolution_boundary"][
                    "condition_guidance_must_not_control"
                ].remove("root selection"),
            ),
            (
                "remove reference root-selection noninterference",
                lambda value: value["parent_resolution_boundary"][
                    "reference_needs_must_not_control"
                ].remove("root selection"),
            ),
            (
                "remove reference noninterference surface",
                lambda value: value["parent_resolution_boundary"].pop(
                    "reference_needs_must_not_control"
                ),
            ),
            (
                "alter parent resolver identity",
                lambda value: value["condition_identity_contract"][
                    "identity_values"
                ].__setitem__("parent_resolver", "condition-specific resolver"),
            ),
            (
                "unbind parent resolver identity",
                lambda value: value["condition_identity_contract"][
                    "identity_values"
                ].pop("parent_resolver"),
            ),
            (
                "remove model-output prohibition",
                lambda value: value["model_output_contract"][
                    "model_must_not_output"
                ].remove("claims"),
            ),
            (
                "remove completion prohibition",
                lambda value: value["parent_resolution_boundary"][
                    "prohibitions"
                ].remove("no_completion_claim"),
            ),
            (
                "nested completion claim",
                lambda value: inject_nested_assertion(value, "completion_claim"),
            ),
            (
                "nested runtime assertion",
                lambda value: inject_nested_assertion(value, "runtime_assertion"),
            ),
            (
                "nested provider assertion",
                lambda value: inject_nested_assertion(value, "provider_assertion"),
            ),
            (
                "nested product assertion",
                lambda value: inject_nested_assertion(value, "product_assertion"),
            ),
            (
                "nested promotion assertion",
                lambda value: inject_nested_assertion(value, "promotion_assertion"),
            ),
            (
                "forbidden assertion value",
                lambda value: value["mechanical_transformation"].__setitem__(
                    "source", "This adapter declares runtime behavior established."
                ),
            ),
        )
        for name, mutate in mutations:
            with self.subTest(mutation=name):
                mutated = deepcopy(self.adapter)
                mutate(mutated)
                with self.assertRaises(AssertionError):
                    self.assert_exact_safety_contract(mutated)

    def test_model_visible_packet_has_no_hidden_identifiers_or_forbidden_fields(self) -> None:
        forbidden_keys = {
            "atom_id",
            "adviser_id",
            "explicit_token",
            "token",
            "tokens",
            "route",
            "routes",
            "payload",
            "payloads",
            "reference",
            "references",
            "case",
            "case_id",
            "label",
            "labels",
            "result",
            "results",
            "condition",
            "condition_id",
            "condition_label",
        }
        forbidden_substrings = (
            "$agentic-engineering",
            "$codex-task-contract",
            "$verification-strategy-engineering",
            "$engineering-learning-loop",
            "adviser_id",
            "explicit_token",
            "trigger_id",
            "payload_id",
            "route_id",
            "case_id",
            "condition_label",
        )
        for condition in ("current", "reduced"):
            packet = self.condition_packet(condition, "same anonymous task")
            self.assertTrue(recursive_keys(packet).isdisjoint(forbidden_keys))
            serialized = canonical_bytes(packet).decode("utf-8")
            self.assertTrue(
                all(token not in serialized for token in forbidden_substrings),
                serialized,
            )

    def test_adapter_contains_no_corpus_or_evaluator_outcome_data(self) -> None:
        forbidden_data_keys = {
            "corpus",
            "prompt",
            "prompts",
            "case_data",
            "cases",
            "label_data",
            "labels",
            "result_data",
            "results",
            "evaluator_output",
            "evaluator_outputs",
            "score",
            "scores",
        }
        self.assertTrue(recursive_keys(self.adapter).isdisjoint(forbidden_data_keys))
        self.assertEqual(
            set(self.adapter["authority_basis"]),
            {
                "h2_catalog",
                "h3_grammar_lineage_only",
                "h4_parent_parser_authority",
            },
        )
        self.assertNotIn("future-activation", json.dumps(self.adapter, sort_keys=True))


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    raise SystemExit(0 if result.wasSuccessful() else 1)
