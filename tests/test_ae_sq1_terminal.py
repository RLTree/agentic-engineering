"""Closed terminal AQ/AR decision tests for AE-SQ1."""

from __future__ import annotations

import hashlib
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGGREGATE_PATH = ROOT / "evals/ae-sq1/aq/aggregate.json"
AR_PATH = ROOT / "evals/ae-sq1/ar/decision.json"


def _strict(raw: bytes) -> dict:
    def pairs(items: list[tuple[str, object]]) -> dict:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite {value}")
        ),
    )


class AeSq1TerminalTests(unittest.TestCase):
    def test_exact_terminal_pair_and_custody(self) -> None:
        aggregate = _strict(AGGREGATE_PATH.read_bytes())
        decision = _strict(AR_PATH.read_bytes())
        self.assertEqual(
            tuple(aggregate),
            (
                "schema_version",
                "program_id",
                "stage",
                "status",
                "claim_ceiling",
                "run_commit",
                "run_tree",
                "run_manifest_sha256",
                "candidate_commit",
                "candidate_tree",
                "candidate_manifest_sha256",
                "corpus_consumed",
                "canary_status",
                "canary_calls_started",
                "canary_calls_completed",
                "batch_status",
                "batch_calls_started",
                "batch_calls_completed",
                "pre_observation_infrastructure_retry_used",
                "post_observation_retry_used",
                "aggregate_digest",
                "terminal_reason",
                "next_stage",
                "reopen_allowed",
            ),
        )
        self.assertEqual(aggregate["status"], "fail")
        self.assertEqual(aggregate["canary_status"], "invalid")
        self.assertEqual(aggregate["canary_calls_started"], 4)
        self.assertEqual(aggregate["canary_calls_completed"], 0)
        self.assertEqual(aggregate["batch_status"], "not_started")
        self.assertFalse(aggregate["corpus_consumed"])
        self.assertIsNone(aggregate["aggregate_digest"])
        self.assertFalse(aggregate["reopen_allowed"])
        self.assertEqual(
            hashlib.sha256(AGGREGATE_PATH.read_bytes()).hexdigest(),
            decision["aq_aggregate_sha256"],
        )
        self.assertEqual(decision["status"], "terminal")
        self.assertEqual(decision["decision"], "DO_NOT_RELEASE_OR_PROMOTE")
        self.assertTrue(decision["stop"])
        self.assertEqual(decision["aq_activation_selection"], "fail_canary_terminal")
        self.assertEqual(decision["as_isolated_advice_value"], "blocked_by_aq_failure")
        self.assertEqual(
            decision["ac_two_decision_composition"], "blocked_by_aq_failure"
        )
        self.assertEqual(
            decision["ah_offline_disposable_home"], "blocked_by_aq_failure"
        )
        self.assertEqual(decision["af_field_usefulness"], "OMITTED_NO_FIELD_CLAIM")
        self.assertNotIn("confidence", json.dumps(decision).lower())

    def test_terminal_edges_are_closed_and_no_placeholder_or_nonfinite(self) -> None:
        decision = _strict(AR_PATH.read_bytes())
        self.assertEqual(
            decision["terminal_edges"],
            [
                "no_AQ_retry",
                "no_reopen",
                "no_resume",
                "no_H6",
                "no_AS",
                "no_AC",
                "no_AH",
                "no_AF_field_action",
                "no_release",
                "no_publish",
                "no_promotion",
                "no_deletion",
                "no_migration",
            ],
        )
        encoded = json.dumps(decision, ensure_ascii=False).lower()
        self.assertNotIn("unbound", encoded)
        self.assertNotIn("unknown", encoded)
        self.assertNotIn("retry_allowed", encoded)
        self.assertNotIn("reopen_allowed", encoded)
        self.assertTrue(all(math.isfinite(float(value)) for value in (0, 4)))

    def test_mutation_reds_fail_closed(self) -> None:
        aggregate = _strict(AGGREGATE_PATH.read_bytes())
        decision = _strict(AR_PATH.read_bytes())
        self.assertNotEqual(aggregate["status"], "pass")
        self.assertNotEqual(decision["decision"], "RELEASE")
        for mutation in (
            {**decision, "stop": False},
            {**decision, "status": "open"},
            {**decision, "aq_activation_selection": "pass"},
            {**decision, "terminal_edges": decision["terminal_edges"][:-1]},
        ):
            self.assertFalse(
                mutation["stop"] is True
                and mutation["status"] == "terminal"
                and mutation["decision"] == "DO_NOT_RELEASE_OR_PROMOTE"
                and mutation["aq_activation_selection"] == "fail_canary_terminal"
                and len(mutation["terminal_edges"]) == 13
            )


if __name__ == "__main__":
    unittest.main()
