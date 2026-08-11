from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "evals/ae-sq1/external-evidence.json"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
WORD = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")
EXPECTED_SEMANTIC_SHA256 = (
    "a0f7a0936727d24d7bcebb2fb0ecde4e5d4c4780bb0712a179d667eb257e7517"
)
EXPECTED_PACKET_RAW_SHA256 = (
    "fb9ff669f848fde71dcf2eb0d223edb63dce271cd9cfbb297519377ab31eb55f"
)
EXPECTED_FOUNDATION_COMMIT = "340b79399a987e6aad0d5435fa540a1db511489d"
EXPECTED_FOUNDATION_TREE = "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933"
EXPECTED_COMPARISON_COMMIT = "d6f9e6089e6e11f158a2d3bf4af717fc026548d4"
EXPECTED_COMPARISON_TREE = "6b65ea1e125836c9ae684e869f1156e5750c7a0b"
EXPECTED_COMPARISON_PATH = (
    "evals/foundation-v4/unresolved-decision-graph-protocol-v8.json"
)
EXPECTED_COMPARISON_SHA256 = (
    "a145766c475de5ed1411bc86467a1a82c3cdaa18782b772ef00901238f590fd5"
)
EXPECTED_SOURCE_ORDER = (
    "anthropic-building-effective-agents",
    "nist-sp-800-207",
    "mcp-security-best-practices-2026-07-28",
    "json-schema-draft-2020-12",
    "angelopoulos-et-al-conformal-risk-control",
)
EXPECTED_CLAIM_ORDER = {
    "anthropic-building-effective-agents": (
        "ANTHROPIC-SIMPLEST-SUFFICIENT",
        "ANTHROPIC-PARALLEL-SECTIONING",
    ),
    "nist-sp-800-207": ("NIST-NO-LOCATION-TRUST", "NIST-PER-RESOURCE-ACCESS"),
    "mcp-security-best-practices-2026-07-28": (
        "MCP-LOCAL-SANDBOX",
        "MCP-TOCTOU",
        "MCP-PROGRESSIVE-SCOPE",
    ),
    "json-schema-draft-2020-12": (
        "JSON-SCHEMA-ASSERTIONS",
        "JSON-SCHEMA-PREFIX-ORDER",
        "JSON-SCHEMA-DECLARED-ASSERTIONS-ONLY",
    ),
    "angelopoulos-et-al-conformal-risk-control": (
        "CRC-EXCHANGEABLE-MONOTONE-BOUNDED",
        "CRC-DATA-DEPENDENT-SELECTION",
        "CRC-NONMONOTONE-FAILURE",
    ),
}
EXPECTED_CONSTRAINT_ORDER = (
    "SLEC1-INDEPENDENT-FOUR",
    "SLEC1-FAIL-CLOSED",
    "SLEC1-LEAST-REFERENCE",
    "SLEC1-ATOMIC-CUSTODY",
    "SLEC1-NO-STATISTICAL-PRETENSE",
)
EXPECTED_PINPOINT_HOST = {
    "anthropic-building-effective-agents": "www.anthropic.com",
    "nist-sp-800-207": "doi.org",
    "mcp-security-best-practices-2026-07-28": "modelcontextprotocol.io",
    "json-schema-draft-2020-12": "www.ietf.org",
    "angelopoulos-et-al-conformal-risk-control": "proceedings.iclr.cc",
}

KNOWN_CUSTODY = {
    "anthropic-building-effective-agents": (
        "3ce0e5b4f87aee1fee306bafba2a39a2275d9e9a424c112ea7d18707daa07ed9",
        180307,
        "text/html",
    ),
    "nist-sp-800-207": (
        "0290d6ece24874287316f4bf430fef770aa4ec08a2227c8f2c1e5b2ff975e03d",
        966908,
        "application/pdf",
    ),
    "mcp-security-best-practices-2026-07-28": (
        "37c3cd910aa853769f6c815321d4a2452647c4ef61c92a12f9f95a0f5cd1f876",
        545388,
        "text/html",
    ),
    "json-schema-draft-2020-12": (
        "03834e2a60caff313476df9913dac2ccf9a34aad569df570f8ab80db7bd6d24a",
        162227,
        "text/plain",
    ),
    "angelopoulos-et-al-conformal-risk-control": (
        "0fff32a0254a47f06a399522b83ba463d0ca62f71e3a0e094985d80cba166c0c",
        1468508,
        "application/pdf",
    ),
}


def semantic_sha256(value: object) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


class AESQ1ExternalEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    def test_packet_and_nested_records_are_closed(self) -> None:
        self.assertEqual(
            set(self.evidence),
            {
                "schema_version",
                "packet_id",
                "status",
                "claim_ceiling",
                "retrieval",
                "sources",
                "cross_source_constraints",
                "forbidden_bindings",
                "conclusion",
            },
        )
        self.assertEqual(
            set(self.evidence["retrieval"]),
            {
                "retrieved_at_utc",
                "method",
                "network_content_is_evidence_not_authority",
                "packet_embeds_source_bytes",
                "reproducibility_limit",
            },
        )
        self.assertTrue(
            self.evidence["retrieval"]["network_content_is_evidence_not_authority"]
        )
        self.assertFalse(self.evidence["retrieval"]["packet_embeds_source_bytes"])

        source_keys = {
            "source_id",
            "disposition",
            "identity",
            "content_custody",
            "claims_used",
            "transfer_limits",
            "contradictions_or_tensions",
            "mechanism_constraints",
        }
        identity_keys = {
            "title",
            "owner",
            "authors",
            "publication_date",
            "version",
            "canonical_uri",
            "version_uri",
            "retrieval_uri",
        }
        custody_keys = {
            "sha256",
            "size_bytes",
            "media_type",
            "digest_scope",
            "content_addressed_uri",
            "publisher_bytes_mutable",
            "retrieval_reproducibility",
        }
        claim_keys = {
            "claim_id",
            "claim",
            "pinpoint",
            "evidence_excerpt",
            "evidence_excerpt_utf8_sha256",
            "supports_constraints",
            "inference",
        }
        pinpoint_keys = {"section", "page", "anchor", "uri"}

        for source in self.evidence["sources"]:
            self.assertEqual(set(source), source_keys)
            self.assertEqual(set(source["identity"]), identity_keys)
            self.assertEqual(set(source["content_custody"]), custody_keys)
            for claim in source["claims_used"]:
                self.assertEqual(set(claim), claim_keys)
                self.assertEqual(set(claim["pinpoint"]), pinpoint_keys)
                self.assertIs(type(claim["inference"]), bool)

        for constraint in self.evidence["cross_source_constraints"]:
            self.assertEqual(set(constraint), {"constraint_id", "derivation", "rule"})

    def test_exact_required_sources_and_known_retrieved_byte_custody(self) -> None:
        self.assertEqual(
            tuple(source["source_id"] for source in self.evidence["sources"]),
            EXPECTED_SOURCE_ORDER,
        )
        sources = {source["source_id"]: source for source in self.evidence["sources"]}
        self.assertEqual(set(sources), set(KNOWN_CUSTODY))
        self.assertEqual(len(sources), 5)

        for source_id, (
            expected_digest,
            expected_size,
            expected_media,
        ) in KNOWN_CUSTODY.items():
            source = sources[source_id]
            custody = source["content_custody"]
            self.assertEqual(custody["sha256"], expected_digest)
            self.assertEqual(custody["size_bytes"], expected_size)
            self.assertEqual(custody["media_type"], expected_media)
            self.assertRegex(custody["sha256"], HEX64)
            self.assertEqual(
                custody["content_addressed_uri"],
                f"urn:sha256:{expected_digest}",
            )

    def test_independent_exact_semantic_oracle_covers_the_complete_packet(self) -> None:
        self.assertEqual(semantic_sha256(self.evidence), EXPECTED_SEMANTIC_SHA256)
        self.assertEqual(
            tuple(
                row["constraint_id"]
                for row in self.evidence["cross_source_constraints"]
            ),
            EXPECTED_CONSTRAINT_ORDER,
        )
        for source in self.evidence["sources"]:
            self.assertEqual(
                tuple(claim["claim_id"] for claim in source["claims_used"]),
                EXPECTED_CLAIM_ORDER[source["source_id"]],
            )

    def test_semantic_oracle_rejects_coordinated_and_structural_mutants(self) -> None:
        mutants = []

        coordinated_excerpt = deepcopy(self.evidence)
        claim = coordinated_excerpt["sources"][0]["claims_used"][0]
        claim["evidence_excerpt"] = "coordinated replacement"
        claim["evidence_excerpt_utf8_sha256"] = hashlib.sha256(
            claim["evidence_excerpt"].encode("utf-8")
        ).hexdigest()
        mutants.append(coordinated_excerpt)

        duplicate_source = deepcopy(self.evidence)
        duplicate_source["sources"].append(deepcopy(duplicate_source["sources"][0]))
        mutants.append(duplicate_source)

        duplicate_constraint = deepcopy(self.evidence)
        duplicate_constraint["cross_source_constraints"].append(
            deepcopy(duplicate_constraint["cross_source_constraints"][0])
        )
        mutants.append(duplicate_constraint)

        off_domain = deepcopy(self.evidence)
        off_domain["sources"][0]["claims_used"][0]["pinpoint"]["uri"] = (
            "https://example.invalid/substitution"
        )
        mutants.append(off_domain)

        reordered = deepcopy(self.evidence)
        reordered["sources"] = list(reversed(reordered["sources"]))
        mutants.append(reordered)

        wrong_type = deepcopy(self.evidence)
        wrong_type["sources"][0]["content_custody"]["size_bytes"] = "180307"
        mutants.append(wrong_type)

        for mutant in mutants:
            self.assertNotEqual(semantic_sha256(mutant), EXPECTED_SEMANTIC_SHA256)

    def test_identity_has_version_and_retrieval_uris(self) -> None:
        for source in self.evidence["sources"]:
            identity = source["identity"]
            self.assertIs(type(source["source_id"]), str)
            self.assertIs(type(source["disposition"]), str)
            self.assertTrue(identity["title"])
            self.assertTrue(identity["owner"])
            self.assertIs(type(identity["authors"]), list)
            self.assertTrue(
                all(type(author) is str and author for author in identity["authors"])
            )
            self.assertTrue(identity["publication_date"])
            self.assertTrue(identity["version"])
            for key in ("canonical_uri", "version_uri", "retrieval_uri"):
                self.assertIs(type(identity[key]), str)
                self.assertTrue(
                    identity[key].startswith("https://"), (source["source_id"], key)
                )
        anthropic = self.evidence["sources"][0]
        self.assertEqual(anthropic["identity"]["authors"], ["Erik S.", "Barry Zhang"])

    def test_every_reliance_is_a_pinpointed_hashed_claim(self) -> None:
        claim_ids: set[str] = set()
        for source in self.evidence["sources"]:
            self.assertTrue(source["claims_used"])
            source_quote_words = 0
            for claim in source["claims_used"]:
                claim_id = claim["claim_id"]
                self.assertNotIn(claim_id, claim_ids)
                claim_ids.add(claim_id)

                self.assertTrue(claim["claim"])
                self.assertLessEqual(len(claim["claim"]), 500)
                excerpt = claim["evidence_excerpt"]
                self.assertTrue(excerpt)
                self.assertLessEqual(len(excerpt.encode("utf-8")), 180)
                self.assertEqual(
                    hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
                    claim["evidence_excerpt_utf8_sha256"],
                )
                source_quote_words += len(WORD.findall(excerpt))

                pinpoint = claim["pinpoint"]
                self.assertIs(type(pinpoint["section"]), str)
                self.assertTrue(
                    pinpoint["page"] is None or type(pinpoint["page"]) is str
                )
                self.assertIs(type(pinpoint["anchor"]), str)
                self.assertIs(type(pinpoint["uri"]), str)
                self.assertTrue(pinpoint["section"])
                self.assertTrue(pinpoint["anchor"])
                self.assertTrue(pinpoint["uri"].startswith("https://"))
                self.assertEqual(
                    urlsplit(pinpoint["uri"]).netloc,
                    EXPECTED_PINPOINT_HOST[source["source_id"]],
                )
                if pinpoint["page"] is None:
                    self.assertIn(f"#{pinpoint['anchor']}", pinpoint["uri"])
                else:
                    self.assertTrue(pinpoint["page"])

                self.assertTrue(claim["supports_constraints"])
                self.assertTrue(
                    all(type(value) is str for value in claim["supports_constraints"])
                )
                self.assertEqual(
                    len(claim["supports_constraints"]),
                    len(set(claim["supports_constraints"])),
                )

            self.assertLessEqual(source_quote_words, 25, source["source_id"])

    def test_claim_support_exactly_covers_each_source_constraints(self) -> None:
        for source in self.evidence["sources"]:
            supported = {
                constraint
                for claim in source["claims_used"]
                for constraint in claim["supports_constraints"]
            }
            self.assertEqual(
                supported, set(source["mechanism_constraints"]), source["source_id"]
            )

    def test_constraint_derivations_close_over_declared_source_constraints(
        self,
    ) -> None:
        declared = {
            constraint
            for source in self.evidence["sources"]
            for constraint in source["mechanism_constraints"]
        }
        used = {
            constraint
            for row in self.evidence["cross_source_constraints"]
            for constraint in row["derivation"]
        }
        self.assertEqual(used, declared)
        self.assertEqual(len(declared), 19)
        source_ids = [source["source_id"] for source in self.evidence["sources"]]
        constraint_ids = [
            row["constraint_id"] for row in self.evidence["cross_source_constraints"]
        ]
        self.assertEqual(len(source_ids), len(set(source_ids)))
        self.assertEqual(len(constraint_ids), len(set(constraint_ids)))
        for row in self.evidence["cross_source_constraints"]:
            self.assertIs(type(row["constraint_id"]), str)
            self.assertIs(type(row["derivation"]), list)
            self.assertTrue(all(type(value) is str for value in row["derivation"]))
            self.assertIs(type(row["rule"]), str)

    def test_custody_limitations_cover_mutability_and_reproducibility(self) -> None:
        packet_limit = self.evidence["retrieval"]["reproducibility_limit"].lower()
        self.assertIn("urn:sha256", packet_limit)
        self.assertIn("not a storage", packet_limit)
        self.assertIn("retained", packet_limit)

        for source in self.evidence["sources"]:
            custody = source["content_custody"]
            self.assertIs(type(custody["sha256"]), str)
            self.assertIs(type(custody["size_bytes"]), int)
            self.assertIs(type(custody["media_type"]), str)
            self.assertIs(type(custody["publisher_bytes_mutable"]), bool)
            limitation = custody["retrieval_reproducibility"].lower()
            self.assertIn("exact reproduction", limitation)
            self.assertIn("digest", limitation)
            self.assertTrue(source["transfer_limits"])
            self.assertTrue(source["contradictions_or_tensions"])
        mutable_by_source = {
            source["source_id"]: source["content_custody"]["publisher_bytes_mutable"]
            for source in self.evidence["sources"]
        }
        self.assertIs(mutable_by_source["json-schema-draft-2020-12"], False)
        self.assertTrue(
            all(
                mutable
                for source_id, mutable in mutable_by_source.items()
                if source_id != "json-schema-draft-2020-12"
            )
        )

    def test_unavailable_saltzer_is_absent_and_json_schema_uses_ietf_archive(
        self,
    ) -> None:
        source_records = json.dumps(self.evidence["sources"], sort_keys=True).lower()
        self.assertNotIn("saltzer", source_records)
        self.assertNotIn("csr-rfc-060", source_records)
        source = next(
            row
            for row in self.evidence["sources"]
            if row["source_id"] == "json-schema-draft-2020-12"
        )
        self.assertEqual(
            source["identity"]["retrieval_uri"],
            "https://www.ietf.org/archive/id/draft-bhutton-json-schema-01.txt",
        )
        self.assertEqual(source["content_custody"]["media_type"], "text/plain")
        self.assertFalse(source["content_custody"]["publisher_bytes_mutable"])
        self.assertIn("five-source", self.evidence["conclusion"])

    def test_conformal_risk_control_is_the_only_rejected_alternative(self) -> None:
        rejected = [
            row
            for row in self.evidence["sources"]
            if row["disposition"] == "rejected_alternative"
        ]
        self.assertEqual(len(rejected), 1)
        self.assertEqual(
            rejected[0]["source_id"], "angelopoulos-et-al-conformal-risk-control"
        )
        self.assertIn(
            "NO_CONFORMAL_THRESHOLD", " ".join(rejected[0]["mechanism_constraints"])
        )

    def test_packet_contains_no_embedded_source_or_oversized_free_text(self) -> None:
        raw = EVIDENCE_PATH.read_bytes()
        self.assertLess(len(raw), 64_000)
        serialized = raw.decode("utf-8")
        self.assertNotIn("data:application", serialized)
        self.assertNotIn("base64,", serialized)
        for source in self.evidence["sources"]:
            for field in ("transfer_limits", "contradictions_or_tensions"):
                for value in source[field]:
                    self.assertLessEqual(len(value), 700)

    def test_no_historical_evaluation_binding_is_present(self) -> None:
        serialized = json.dumps(self.evidence, sort_keys=True).lower()
        forbidden = (
            "activation-heldout",
            "activation-authoring",
            "per-case-output",
            "aq8",
            "aq9",
            "e0 packet",
            "observed metric",
        )
        for token in forbidden:
            self.assertNotIn(token, serialized)

    def test_packet_digest_and_exact_comparison_git_bytes(self) -> None:
        self.assertEqual(
            hashlib.sha256(EVIDENCE_PATH.read_bytes()).hexdigest(),
            EXPECTED_PACKET_RAW_SHA256,
        )
        tree = subprocess.run(
            ["git", "show", "-s", "--format=%T", EXPECTED_COMPARISON_COMMIT],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        raw = subprocess.run(
            ["git", "show", f"{EXPECTED_COMPARISON_COMMIT}:{EXPECTED_COMPARISON_PATH}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(tree, EXPECTED_COMPARISON_TREE)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), EXPECTED_COMPARISON_SHA256)

    def test_foundation_custody_is_an_existing_exact_commit_tree(self) -> None:
        tree = subprocess.run(
            ["git", "show", "-s", "--format=%T", EXPECTED_FOUNDATION_COMMIT],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(tree, EXPECTED_FOUNDATION_TREE)


if __name__ == "__main__":
    unittest.main()
