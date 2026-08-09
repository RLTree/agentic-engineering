from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FOUNDATIONS = ROOT / "docs" / "foundations"
HISTORICAL_SENTINEL = "Historical research snapshot through 2026-07-22"
CURRENT_OWNER = "docs/foundations/current-2026-08-08.md"
NAMED_SOURCE_IDS = {
    "R27",
    "R28",
    "R39",
    "R66",
    "R67",
    "R75",
    "R96",
    "R98",
    "R122",
    "R147",
    "R148",
    "R149",
    "R150",
    "R151",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class FoundationTruthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.current = read_text(FOUNDATIONS / "current-2026-08-08.md")
        with (FOUNDATIONS / "register.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            cls.register_fields = reader.fieldnames
            cls.register_rows = list(reader)
        with (FOUNDATIONS / "decision-log.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            cls.decision_log_fields = reader.fieldnames
            cls.decision_log_rows = list(reader)
        cls.manifest = json.loads(read_text(ROOT / "SOURCE-MANIFEST.json"))
        with (ROOT / "EVIDENCE-MATRIX.csv").open(newline="", encoding="utf-8") as handle:
            cls.matrix_rows = list(csv.DictReader(handle))

    def test_current_foundation_has_one_owner_and_no_missing_disposition_file(self) -> None:
        self.assertIn("single canonical owner", self.current)
        self.assertIn("register.csv", self.current)
        self.assertIn("decision-log.csv", self.current)
        self.assertIn("decision_owner", self.current)
        self.assertIn("single owner path controls the\nrepository decision", self.current)
        self.assertIn("R-series citations are non-owning historical\nlineage consumers", self.current)
        self.assertNotIn("MATERIAL-DISPOSITION.csv", self.current)
        for status in (
            "Controlling current",
            "Stable supporting",
            "Empirical directional",
            "Draft provisional",
            "Emerging, not normative",
            "Historical lineage",
        ):
            self.assertIn(status, self.current)
        self.assertIn("## 6. Claim ceilings", self.current)
        self.assertIn("No lower row proves a higher row.", self.current)

    def test_register_is_scoped_unique_and_review_triggered(self) -> None:
        self.assertEqual(35, len(self.register_rows))
        by_id = {row["foundation_id"]: row for row in self.register_rows}
        self.assertEqual(len(self.register_rows), len(by_id))
        self.assertEqual(
            {"agentic-engineering", "both"},
            {row["applies_to"] for row in self.register_rows},
        )
        self.assertTrue(all(row["review_trigger"].strip() for row in self.register_rows))
        self.assertEqual(
            "decision_owner",
            self.register_fields[self.register_fields.index("implementation_use") + 1],
        )
        for row in self.register_rows:
            decision_owner = row["decision_owner"]
            self.assertEqual(decision_owner, decision_owner.strip(), row["foundation_id"])
            self.assertNotRegex(decision_owner, r"[\s,;]", row["foundation_id"])
            self.assertFalse(Path(decision_owner).is_absolute(), row["foundation_id"])
            self.assertTrue((ROOT / decision_owner).is_file(), row["foundation_id"])
        for foundation_id in (
            "F-MCP-20260728",
            "F-A2A-10",
            "F-OTEL-159",
            "F-SLSA-12",
            "F-SSDF-11",
            "F-SSDF-12-DRAFT",
        ):
            self.assertIn(foundation_id, by_id)
            self.assertTrue(by_id[foundation_id]["review_trigger"].strip())

        owner_terms = {
            "F-MCP-20260728": ("2026-07-28", "stateless-first", "deprecated"),
            "F-A2A-10": ("A2A v1.0", "independently operated", "Native subagent"),
            "F-OTEL-159": ("1.59.0", "1.43.0", "version-sensitive"),
            "F-SSDF-11": ("SSDF 1.1", "controlling"),
            "F-SSDF-12-DRAFT": ("SSDF 1.2", "provisional"),
            "F-SLSA-12": ("SLSA v1.2", "Source and Build", "does not prove"),
            "F-NIST-AI800-4": ("NIST AI 800-4", "taxonomy", "not as a validated"),
            "F-NIST-AI800-3": ("evaluated population", "statistical limits"),
            "F-NIST-AGENT-INIT": ("emerging/draft", "not conformance authority"),
            "F-NIST-IDENTITY": ("emerging/draft", "not conformance authority"),
        }
        for foundation_id, terms in owner_terms.items():
            owner_text = read_text(ROOT / by_id[foundation_id]["decision_owner"])
            for term in terms:
                self.assertIn(term, owner_text, (foundation_id, term))

    def test_decision_log_is_persistence_only(self) -> None:
        self.assertEqual(
            [
                "decision_id",
                "repository",
                "foundation_id",
                "observed_change",
                "affected_decision",
                "decision_owner",
                "disposition_no_change_update_replace_retire",
                "implementation_or_test_delta",
                "claim_ceiling",
                "review_trigger",
                "date",
                "candidate_commit",
                "notes",
            ],
            self.decision_log_fields,
        )
        self.assertTrue(all(row["decision_id"].strip() for row in self.decision_log_rows))

    def test_historical_surfaces_are_explicitly_non_authoritative(self) -> None:
        for name in ("RESEARCH.md", "RESEARCH-V3-ADDENDUM.md"):
            text = read_text(ROOT / name)
            self.assertIn(HISTORICAL_SENTINEL, text[:600])
            self.assertIn(CURRENT_OWNER, text[:600])

        self.assertIn(HISTORICAL_SENTINEL, self.manifest["scope_addendum"])
        self.assertIn(CURRENT_OWNER, self.manifest["scope_addendum"])

        readme = read_text(ROOT / "README.md")
        self.assertIn("Research authority", readme[:1600])
        self.assertIn("EVIDENCE-MATRIX.csv", readme[:1600])
        self.assertIn(CURRENT_OWNER, readme[:1600])

        for name, sentinel in (
            ("CONFIDENCE.md", "Superseded aggregate model"),
            ("EVALUATION.md", "Superseded Version 3 strategy"),
            ("PLUGIN-DESIGN-BRIEF.md", "Historical Version 2/3 design and release record"),
        ):
            text = read_text(ROOT / name)
            self.assertIn(sentinel, text[:600])
            self.assertIn(CURRENT_OWNER, text[:600])

    def test_named_historical_rows_match_their_csv_projection(self) -> None:
        manifest_rows = {row["id"]: row for row in self.manifest["sources"]}
        matrix_rows = {row["id"]: row for row in self.matrix_rows}
        self.assertEqual(151, self.manifest["source_count"])
        self.assertEqual(
            [f"R{index:02d}" for index in range(1, 152)],
            [row["id"] for row in self.manifest["sources"]],
        )
        self.assertEqual(list(manifest_rows), list(matrix_rows))

        for source_id in NAMED_SOURCE_IDS:
            manifest_row = manifest_rows[source_id]
            matrix_row = matrix_rows[source_id]
            for field in (
                "id",
                "evidence_class",
                "topic",
                "source",
                "date",
                "key_finding",
                "operationalization",
                "url",
            ):
                self.assertEqual(manifest_row[field], matrix_row[field], (source_id, field))
            self.assertEqual(
                "; ".join(manifest_row["affected_skills"]),
                matrix_row["affected_skills"],
                source_id,
            )

        self.assertIn("Challenges to the Monitoring", manifest_rows["R75"]["source"])
        self.assertIn("does not prescribe", manifest_rows["R75"]["key_finding"])
        self.assertIn("Source and Build tracks", manifest_rows["R98"]["key_finding"])
        self.assertIn("does not establish behavioral", manifest_rows["R98"]["key_finding"])
        for source_id in ("R27", "R66"):
            self.assertIn("2026-07-28", manifest_rows[source_id]["source"])
            self.assertIn("deprecated", manifest_rows[source_id]["key_finding"])
        for source_id in ("R28", "R67"):
            self.assertIn("independent", manifest_rows[source_id]["key_finding"])
            self.assertIn("internal subagents", manifest_rows[source_id]["key_finding"])
        self.assertIn("1.59.0", manifest_rows["R39"]["source"])
        self.assertIn("1.43.0", manifest_rows["R122"]["source"])
        for source_id in ("R147", "R148", "R149", "R150"):
            source_type = manifest_rows[source_id]["type"]
            self.assertTrue(
                "not normative" in source_type or "provisional" in source_type,
                source_id,
            )
        self.assertIn("single provisional entry", manifest_rows["R96"]["operationalization"])
        self.assertIn("duplicates", manifest_rows["R151"]["key_finding"])
        self.assertIn("SSDF 1.1 remains final", manifest_rows["R151"]["operationalization"])

    def test_update_policy_uses_decision_deltas_not_synchronized_refresh(self) -> None:
        policy = read_text(ROOT / "UPDATE-POLICY.md")
        self.assertIn(
            "Record one row in the foundation log only when the decision must survive the session.",
            self.current,
        )
        self.assertIn("sole current external-research authority", policy)
        self.assertIn("no_change`, `update`, `replace`, or `retire", policy)
        self.assertIn("cheapest falsifier", policy)
        self.assertIn("zero-write by default", policy)
        self.assertNotIn(
            "update `SOURCE-MANIFEST.json`, `EVIDENCE-MATRIX.csv` and `RESEARCH.md` together",
            policy,
        )
        self.assertIn("do not establish package quality or release validity", policy)


if __name__ == "__main__":
    unittest.main()
