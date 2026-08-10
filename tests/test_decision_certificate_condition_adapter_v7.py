"""Corpus-blind structural checks for the AQ7 condition-input adapter."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = ROOT / "evals/foundation-v4/decision-certificate-condition-adapter-v7.json"
H3_COMMIT = "ccbe06be9a2ef5feca4104b6918985ee9c4527c0"
H3_TREE = "dd20449fdc45a73c55adb349d8c828687728ef4d"
H2_COMMIT = "8ddf39198cb0e21f321a01a9755e009bb1c1860f"
H2_TREE = "1fbf9964b10831da051d2e5cafe29b6086d4d599"
POLICY_COMMIT = "c4e661a926e0ace78d9da83f71d9c52d311abb72"
POLICY_TREE = "f2abb05d32a888c9054ef2e7ab3ad0f08547de88"
MANIFEST_COMMIT = "f09a0544acf4b7a95fff796434273511a0683ca9"
MANIFEST_TREE = "38c8c8adf3bb633d33200df1ec65f33e985ae244"
H3_PROTOCOL_PATH = "evals/foundation-v4/decision-certificate-protocol-v6.json"
H3_SCHEMA_PATH = "evals/foundation-v4/decision-certificate-selector-output-schema-v6.json"
H2_CATALOG_PATH = "evals/foundation-v4/decision-atom-candidate-v4.json"
POLICY_PATH = "evals/foundation-v4/decision-certificate-reference-policy-v6.json"
MANIFEST_PATH = "evals/foundation-v4/reduced-four-skills/candidate.json"

EXPECTED_AUTHORITY_BASIS = {
    "h3": {
        "commit": H3_COMMIT,
        "tree": H3_TREE,
        "protocol": {
            "path": H3_PROTOCOL_PATH,
            "sha256": "9ad483a26fe339f81c947507de9c1c66d54b2823a38f68b1c5ee7fdf5c426f84",
            "predicate_order_sha256": "cd890bb08444940bf1483dc48c0ca563476f7b4c2b25bbe65edfe861d839e4ae",
            "eligibility_rules_sha256": "3475626c995dfe801faeeded444ed249e72c0f50d8f19b01ee515ad12eba4ad2",
        },
        "selector_output_schema": {
            "path": H3_SCHEMA_PATH,
            "sha256": "9742f2255fed5452df52f9da789a6f2fd72e89aa94c3c6847fad6944445f5b25",
        },
    },
    "h2_catalog": {
        "commit": H2_COMMIT,
        "tree": H2_TREE,
        "path": H2_CATALOG_PATH,
        "sha256": "50fffcf10170cd022d78428909d0679527439a002a7e07dac30e321bbaff61d9",
    },
    "reference_policy": {
        "commit": POLICY_COMMIT,
        "tree": POLICY_TREE,
        "path": POLICY_PATH,
        "sha256": "92982c278e33ff52edce1ba2a16082afb3ecc1989d8333a77eee9ca0911fee19",
    },
    "base_manifest_provenance_only": {
        "commit": MANIFEST_COMMIT,
        "tree": MANIFEST_TREE,
        "path": MANIFEST_PATH,
        "sha256": "854f67bdd03e7121bd20e5513ef61ac806d016b3a5f1d6e5891bf4d9e546eb1f",
        "conditions": {
            "current": {
                "selector_catalog_sha256": "7947721cd7ce8a3321b89a5b17891cbc79f373acadb0351793aa481b8dac362a",
                "condition_input_sha256": "0f7d1ef19a63fceeacf86779042bb9269a098a4e1a88b3eb176f11e44b44f0a0",
            },
            "reduced": {
                "selector_catalog_sha256": "e6b62fd582f724f33d0ce63acb22fa3209f6936213aeba74113a4c0eac67eb4d",
                "condition_input_sha256": "a2bb7830b3dfccdd5decf1a63d4bcf5cd2bb2605ea35db0efad6ac4d892c78d1",
            },
        },
    },
}

EXPECTED_SOURCE_CUSTODY = {
    "derivation_input": {
        "classification": "controlling-frozen-git-object-only",
        "commit": H2_COMMIT,
        "tree": H2_TREE,
        "path": H2_CATALOG_PATH,
        "sha256": EXPECTED_AUTHORITY_BASIS["h2_catalog"]["sha256"],
        "git_blob_sha1": "c3e1f89ded468592e3ada8f23f7336c89f0d580d",
    },
    "live_workspace_observation": {
        "classification": "known-different-lineage-not-a-derivation-input",
        "path": H2_CATALOG_PATH,
        "sha256": "8f7d2d61cee5de217077d3767f3e6454a92c1a29c94fa4f73f121065a50e25cc",
        "git_blob_sha1": "fba49224df0791c4dc44e22d1ef44cc0fd983b2d",
    },
    "substitution_policy": "Guidance derivation must read only derivation_input by git commit and path. Live workspace bytes are observed custody evidence only and must never substitute for that frozen object.",
}

EXPECTED_PACKET_CONTRACT = {
    "packet_keys": ["instruction", "task_text", "predicate_order", "condition_guidance"],
    "instruction": "Extract only the ordered predicate facts supported by task text using the supplied predicate order and anonymous condition guidance. Return only the frozen predicate_facts JSON object.",
    "task_text": "caller-supplied task text only; no task text is stored in this adapter",
    "predicate_order": {
        "source_authority": "authority_basis.h3.protocol",
        "path": H3_PROTOCOL_PATH,
        "sha256": EXPECTED_AUTHORITY_BASIS["h3"]["protocol"]["predicate_order_sha256"],
    },
    "condition_guidance": {
        "source": "conditions.<condition>.condition_guidance",
        "canonical_sha256_source": "conditions.<condition>.condition_guidance_canonical_sha256",
    },
    "condition_variance": "Only condition_guidance may differ between condition packets for the same task text.",
}

EXPECTED_MODEL_SCHEMA = {
    "commit": H3_COMMIT,
    "tree": H3_TREE,
    "path": H3_SCHEMA_PATH,
    "sha256": EXPECTED_AUTHORITY_BASIS["h3"]["selector_output_schema"]["sha256"],
}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def raw_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_bytes(revision: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def git_object(revision: str, path: str) -> dict[str, Any]:
    return json.loads(git_bytes(revision, path))


def git_revision(expression: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", expression], cwd=ROOT, text=True
    ).strip()


def git_manifest_condition_digests() -> dict[str, Any]:
    """Read only the permitted manifest-digest projection, never corpus paths."""
    projection = (
        "{conditions: (.conditions | with_entries(.value |= "
        "{selector_catalog_sha256, condition_input_sha256}))}"
    )
    command = f"git show {MANIFEST_COMMIT}:{MANIFEST_PATH} | jq -c '{projection}'"
    return json.loads(subprocess.check_output(["bash", "-lc", command], cwd=ROOT))


def recursive_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(recursive_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(recursive_keys(item) for item in value))
    return set()


class DecisionCertificateConditionAdapterV7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = json.loads(ADAPTER_PATH.read_text(encoding="utf-8"))
        cls.h3_protocol = git_object(H3_COMMIT, H3_PROTOCOL_PATH)
        cls.h3_schema = git_object(H3_COMMIT, H3_SCHEMA_PATH)
        cls.h2_catalog = git_object(H2_COMMIT, H2_CATALOG_PATH)
        cls.reference_policy = git_object(POLICY_COMMIT, POLICY_PATH)

    def assert_frozen_authority(
        self,
        *,
        revision: str,
        tree: str,
        path: str,
        expected_sha256: str,
    ) -> bytes:
        self.assertEqual(git_revision(f"{revision}^{{commit}}"), revision)
        self.assertEqual(git_revision(f"{revision}^{{tree}}"), tree)
        frozen_bytes = git_bytes(revision, path)
        self.assertEqual(raw_sha256(frozen_bytes), expected_sha256)
        return frozen_bytes

    def assert_exact_authority_basis(self, authority_basis: dict[str, Any]) -> None:
        self.assertEqual(authority_basis, EXPECTED_AUTHORITY_BASIS)

    def assert_exact_source_custody(self, source_custody: dict[str, Any]) -> None:
        self.assertEqual(source_custody, EXPECTED_SOURCE_CUSTODY)

    def assert_exact_packet_and_output_contracts(self, adapter: dict[str, Any]) -> None:
        self.assertEqual(adapter["packet_contract"], EXPECTED_PACKET_CONTRACT)
        self.assertEqual(adapter["model_output_contract"]["schema"], EXPECTED_MODEL_SCHEMA)

    @staticmethod
    def reconstruct_guidance(
        h3_protocol: dict[str, Any], h2_catalog: dict[str, Any], condition: str
    ) -> list[dict[str, Any]]:
        rules = h3_protocol["deterministic_selection"]["eligibility_rules"]
        rows = h2_catalog["conditions"][condition]["atom_catalog"]
        if len(rules) != len(rows):
            raise ValueError("H2 catalog and H3 rule count differ")
        groups: list[dict[str, Any]] = []
        for rule, row in zip(rules, rows, strict=True):
            if rule["derived_atom"] != row["atom_id"]:
                raise ValueError("H2 catalog row is not in frozen H3 atom order")
            groups.append(
                {
                    "positive_predicate_ids": rule["positive_predicates"],
                    "exclusion_predicate_id": rule["exclusion_predicate"],
                    "declared_scope": row["declared_scope"],
                    "positive_boundary": row["positive_boundary"],
                    "admission_rule": row["admission_rule"],
                }
            )
        return groups

    def condition_packet(self, condition: str, task_text: str) -> dict[str, Any]:
        packet = self.adapter["packet_contract"]
        return {
            "instruction": packet["instruction"],
            "task_text": task_text,
            "predicate_order": self.h3_protocol["predicate_order"],
            "condition_guidance": self.adapter["conditions"][condition][
                "condition_guidance"
            ],
        }

    def test_closed_proposal_and_qualification_boundary(self) -> None:
        self.assertEqual(self.adapter["schema_version"], "7.0")
        self.assertEqual(self.adapter["status"], "frozen-proposal-only")
        self.assertEqual(self.adapter["claim_ceiling"], "structural-proposal-only")
        self.assertFalse(self.adapter["outcome_tuned"])
        self.assertTrue(self.adapter["model_agnostic"])
        self.assertEqual(
            self.adapter["qualification_boundary"],
            {
                "operationalizes": "condition input only",
                "does_not_establish": "qualification evidence",
                "authorized_observation_schedule": "one_canary_then_one_batch",
                "no_replay": True,
                "replay_permitted": False,
            },
        )
        self.assertNotIn("fixed_model", recursive_keys(self.adapter))
        self.assertNotIn("reasoning_effort", recursive_keys(self.adapter))

    def test_exact_frozen_authorities_and_git_objects_are_bound(self) -> None:
        self.assert_exact_authority_basis(self.adapter["authority_basis"])
        self.assert_frozen_authority(
            revision=H3_COMMIT,
            tree=H3_TREE,
            path=H3_PROTOCOL_PATH,
            expected_sha256=EXPECTED_AUTHORITY_BASIS["h3"]["protocol"]["sha256"],
        )
        self.assert_frozen_authority(
            revision=H3_COMMIT,
            tree=H3_TREE,
            path=H3_SCHEMA_PATH,
            expected_sha256=EXPECTED_AUTHORITY_BASIS["h3"]["selector_output_schema"]["sha256"],
        )
        self.assert_frozen_authority(
            revision=H2_COMMIT,
            tree=H2_TREE,
            path=H2_CATALOG_PATH,
            expected_sha256=EXPECTED_AUTHORITY_BASIS["h2_catalog"]["sha256"],
        )
        self.assert_frozen_authority(
            revision=POLICY_COMMIT,
            tree=POLICY_TREE,
            path=POLICY_PATH,
            expected_sha256=EXPECTED_AUTHORITY_BASIS["reference_policy"]["sha256"],
        )
        self.assert_frozen_authority(
            revision=MANIFEST_COMMIT,
            tree=MANIFEST_TREE,
            path=MANIFEST_PATH,
            expected_sha256=EXPECTED_AUTHORITY_BASIS["base_manifest_provenance_only"]["sha256"],
        )

    def test_authority_commit_tree_path_and_digest_mutations_are_red(self) -> None:
        mutations = (
            ("h3", "commit", "0" * 40),
            ("h2_catalog", "tree", "0" * 40),
            ("reference_policy", "path", "wrong/path.json"),
            ("base_manifest_provenance_only", "sha256", "0" * 64),
        )
        for section, field, replacement in mutations:
            with self.subTest(section=section, field=field):
                mutated = deepcopy(self.adapter["authority_basis"])
                mutated[section][field] = replacement
                with self.assertRaises(AssertionError):
                    self.assert_exact_authority_basis(mutated)

    def test_h3_projection_digests_and_h2_source_digests_are_bound(self) -> None:
        protocol = EXPECTED_AUTHORITY_BASIS["h3"]["protocol"]
        self.assertEqual(
            canonical_sha256(self.h3_protocol["predicate_order"]),
            protocol["predicate_order_sha256"],
        )
        self.assertEqual(
            canonical_sha256(
                self.h3_protocol["deterministic_selection"]["eligibility_rules"]
            ),
            protocol["eligibility_rules_sha256"],
        )
        for condition in ("current", "reduced"):
            self.assertEqual(
                self.adapter["conditions"][condition]["source_atom_catalog_sha256"],
                self.h2_catalog["conditions"][condition]["atom_catalog_sha256"],
            )

    def test_h2_source_custody_makes_live_drift_explicit_and_non_substitutable(self) -> None:
        custody = self.adapter["source_custody"]
        self.assertEqual(custody, EXPECTED_SOURCE_CUSTODY)
        frozen = custody["derivation_input"]
        observed_live = custody["live_workspace_observation"]
        self.assertEqual(git_bytes(frozen["commit"], frozen["path"]), git_bytes(H2_COMMIT, H2_CATALOG_PATH))
        self.assertEqual(raw_sha256(git_bytes(H2_COMMIT, H2_CATALOG_PATH)), frozen["sha256"])
        live_bytes = (ROOT / H2_CATALOG_PATH).read_bytes()
        live_blob = subprocess.check_output(
            ["git", "hash-object", H2_CATALOG_PATH], cwd=ROOT, text=True
        ).strip()
        self.assertEqual(raw_sha256(live_bytes), observed_live["sha256"])
        self.assertEqual(live_blob, observed_live["git_blob_sha1"])
        self.assertNotEqual(observed_live["sha256"], frozen["sha256"])
        self.assertNotEqual(observed_live["git_blob_sha1"], frozen["git_blob_sha1"])
        self.assertEqual(
            frozen["classification"], "controlling-frozen-git-object-only"
        )
        self.assertEqual(
            observed_live["classification"], "known-different-lineage-not-a-derivation-input"
        )
        self.assertIn("must never substitute", custody["substitution_policy"])

    def test_source_custody_live_digest_mutation_is_red(self) -> None:
        mutated = deepcopy(self.adapter["source_custody"])
        mutated["live_workspace_observation"]["sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            self.assert_exact_source_custody(mutated)

    def test_base_manifest_condition_digests_are_provenance_only_and_distinct(self) -> None:
        provenance = self.adapter["authority_basis"]["base_manifest_provenance_only"]
        current = provenance["conditions"]["current"]
        reduced = provenance["conditions"]["reduced"]
        self.assertNotEqual(
            current["selector_catalog_sha256"], reduced["selector_catalog_sha256"]
        )
        self.assertNotEqual(
            current["condition_input_sha256"], reduced["condition_input_sha256"]
        )
        self.assertEqual(
            provenance["conditions"], git_manifest_condition_digests()["conditions"]
        )
        self.assertNotIn("base_manifest_provenance_only", self.adapter["packet_contract"])
        for condition in ("current", "reduced"):
            packet = self.condition_packet(condition, "same task")
            self.assertNotIn("selector_catalog_sha256", json.dumps(packet))
            self.assertNotIn("condition_input_sha256", json.dumps(packet))

    def test_guidance_is_the_exact_mechanical_h2_to_h3_projection(self) -> None:
        transform = self.adapter["mechanical_transformation"]
        self.assertEqual(
            transform["output_group_keys"],
            [
                "positive_predicate_ids",
                "exclusion_predicate_id",
                "declared_scope",
                "positive_boundary",
                "admission_rule",
            ],
        )
        for condition in ("current", "reduced"):
            expected = self.reconstruct_guidance(
                self.h3_protocol, self.h2_catalog, condition
            )
            actual = self.adapter["conditions"][condition]["condition_guidance"]
            self.assertEqual(actual, expected)
            self.assertEqual(len(actual), len(self.h3_protocol["deterministic_selection"]["eligibility_rules"]))
            self.assertEqual(
                canonical_sha256(actual),
                self.adapter["conditions"][condition][
                    "condition_guidance_canonical_sha256"
                ],
            )
            self.assertTrue(all(set(group) == set(transform["output_group_keys"]) for group in actual))

    def test_guidance_rejects_reordering_missing_rows_and_hand_tuned_fields(self) -> None:
        for condition in ("current", "reduced"):
            guidance = self.adapter["conditions"][condition]["condition_guidance"]
            expected = self.reconstruct_guidance(
                self.h3_protocol, self.h2_catalog, condition
            )
            self.assertNotEqual(list(reversed(guidance)), expected)
            self.assertNotEqual(guidance[:-1], expected)
            self.assertFalse(any("atom_id" in group for group in guidance))
            self.assertFalse(any("pairwise_exclusions" in group for group in guidance))
            self.assertFalse(any("guidance_label" in group for group in guidance))
            self.assertFalse(any("case" in group for group in guidance))
            self.assertFalse(any("result" in group for group in guidance))
            self.assertFalse(any("label" in group for group in guidance))

    def test_model_visible_guidance_excludes_forbidden_data_and_keys(self) -> None:
        forbidden_tokens = (
            "$agentic-engineering",
            "$codex-task-contract",
            "$verification-strategy-engineering",
            "$engineering-learning-loop",
            "pairwise_exclusions",
            "payload",
            "reference",
            "route",
            "token",
            "case",
            "label",
            "result",
        )
        forbidden_keys = {
            "atom_id",
            "adviser_id",
            "route",
            "routes",
            "token",
            "tokens",
            "payload",
            "payloads",
            "pairwise_exclusions",
            "references",
            "case",
            "label",
            "result",
            "condition_label",
        }
        for condition in ("current", "reduced"):
            guidance = self.adapter["conditions"][condition]["condition_guidance"]
            serialized = json.dumps(guidance, sort_keys=True)
            self.assertTrue(all(token not in serialized for token in forbidden_tokens))
            self.assertTrue(recursive_keys(guidance).isdisjoint(forbidden_keys))

    def test_same_task_packets_are_distinct_only_at_condition_guidance(self) -> None:
        current = self.condition_packet("current", "same task text")
        reduced = self.condition_packet("reduced", "same task text")
        self.assertEqual(set(current), {"instruction", "task_text", "predicate_order", "condition_guidance"})
        self.assertNotEqual(
            self.adapter["conditions"]["current"]["condition_guidance_canonical_sha256"],
            self.adapter["conditions"]["reduced"]["condition_guidance_canonical_sha256"],
        )
        self.assertNotEqual(current["condition_guidance"], reduced["condition_guidance"])
        self.assertNotEqual(canonical_sha256(current), canonical_sha256(reduced))
        changed = {key for key in current if current[key] != reduced[key]}
        self.assertEqual(changed, {"condition_guidance"})

    def test_packet_contract_and_model_schema_pointers_are_exact(self) -> None:
        self.assert_exact_packet_and_output_contracts(self.adapter)
        self.assertEqual(
            raw_sha256(git_bytes(H3_COMMIT, H3_SCHEMA_PATH)),
            EXPECTED_MODEL_SCHEMA["sha256"],
        )
        packet_drift = deepcopy(self.adapter)
        packet_drift["packet_contract"]["predicate_order"]["sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            self.assert_exact_packet_and_output_contracts(packet_drift)
        schema_drift = deepcopy(self.adapter)
        schema_drift["model_output_contract"]["schema"]["path"] = "wrong/schema.json"
        with self.assertRaises(AssertionError):
            self.assert_exact_packet_and_output_contracts(schema_drift)

    def test_h3_fact_only_output_contract_is_unchanged(self) -> None:
        contract = self.adapter["model_output_contract"]
        self.assertEqual(contract["schema"], EXPECTED_MODEL_SCHEMA)
        self.assertEqual(contract["required_root"], "predicate_facts")
        self.assertEqual(contract["only_top_level_key"], "predicate_facts")
        self.assertEqual(contract["fact_count"], 12)
        self.assertEqual(contract["allowed_states"], ["present", "absent", "uncertain"])
        self.assertEqual(self.h3_schema["required"], ["predicate_facts"])
        self.assertFalse(self.h3_schema["additionalProperties"])
        facts = [
            {"predicate_id": predicate_id, "state": "uncertain"}
            for predicate_id in self.h3_protocol["predicate_order"]
        ]
        valid_output = {"predicate_facts": facts}
        self.assertTrue(self.is_h3_schema_valid(valid_output))
        self.assertFalse(self.is_h3_schema_valid({"predicate_facts": facts, "atoms": []}))
        self.assertFalse(self.is_h3_schema_valid({"predicate_facts": facts[:-1]}))

    def is_h3_schema_valid(self, output: Any) -> bool:
        if not isinstance(output, dict) or set(output) != {"predicate_facts"}:
            return False
        facts = output["predicate_facts"]
        if not isinstance(facts, list) or len(facts) != len(self.h3_protocol["predicate_order"]):
            return False
        return all(
            isinstance(fact, dict)
            and set(fact) == {"predicate_id", "state"}
            and fact["predicate_id"] == predicate_id
            and fact["state"] in {"present", "absent", "uncertain"}
            for fact, predicate_id in zip(facts, self.h3_protocol["predicate_order"], strict=True)
        )

    def test_parent_resolution_is_identical_and_not_model_visible(self) -> None:
        boundary = self.adapter["parent_resolution_boundary"]
        self.assertTrue(boundary["identical_for_all_conditions"])
        self.assertEqual(
            boundary["authority"],
            "H3 protocol, frozen reference policy, and frozen base manifest provenance only",
        )
        self.assertEqual(
            boundary["parent_authority_inputs"],
            [
                "H3 protocol",
                "frozen reference policy",
                "frozen base manifest provenance",
            ],
        )
        self.assertFalse(boundary["model_visible"])
        self.assertEqual(
            boundary["condition_guidance_must_not_control"],
            [
                "selection",
                "atom_to_adviser_mapping",
                "reference_resolution",
                "authority_assignment",
                "effects",
            ],
        )
        self.assertEqual(
            self.reference_policy["model_boundary"]["model_output_used"],
            "schema-valid ordered predicate_facts only",
        )


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    raise SystemExit(0 if result.wasSuccessful() else 1)
