"""Synthetic and adversarial tests for the closed AE-SQ1 aggregate scorer."""

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
sys.path.insert(0, str(ROOT / "tests"))

import score_ae_sq1_aq as scorer  # noqa: E402
import validate_ae_sq1_corpus as validator  # noqa: E402
from test_ae_sq1_corpus_contract import historical_bytes, make_pair  # noqa: E402


def make_binding(pair: tuple[dict, dict]) -> dict:
    validation = validator.validate_corpora(
        pair, historical_digest_inventory=historical_bytes()
    )
    assert validation.passed and validation.corpus_digest
    authority = pair[0]["authority"]
    return {
        "program_id": "AE-SQ1",
        "candidate_id": authority["candidate_id"],
        "candidate_commit": authority["candidate_commit"],
        "candidate_tree": authority["candidate_tree"],
        "candidate_manifest_sha256": authority["candidate_manifest_sha256"],
        "runner_sha256": "d" * 64,
        "evaluator_sha256": hashlib.sha256(
            (ROOT / "scripts/score_ae_sq1_aq.py").read_bytes()
        ).hexdigest(),
        "corpus_validator_sha256": hashlib.sha256(
            (ROOT / "scripts/validate_ae_sq1_corpus.py").read_bytes()
        ).hexdigest(),
        "corpus_sha256": validation.corpus_digest,
        "model_id": "synthetic-no-model",
        "reasoning": "none",
        "tools_sha256": "e" * 64,
        "host_sha256": "f" * 64,
    }


def make_observations(pair: tuple[dict, dict], binding: dict) -> list[dict]:
    cases = {case["case_id"]: case for document in pair for case in document["cases"]}
    schedule = validator.build_schedule(tuple(sorted(cases)))
    schedule_sha = validator.schedule_digest(schedule)
    binding_sha = validator.digest(binding)
    observations = []
    for row in schedule:
        case = cases[row["case_id"]]
        capsules = []
        for slot_id, expected in zip(
            validator.SLOT_ORDER, case["expected_capsules"], strict=True
        ):
            capsules.append(
                {
                    "slot_id": slot_id,
                    "context_id": f"context-{row['presentation_index']:02d}-{slot_id}",
                    "invocation_count": 1,
                    "terminal_completed": True,
                    "parse_status": "parsed",
                    "output": copy.deepcopy(expected),
                    "binding_sha256": binding_sha,
                    "schedule_sha256": schedule_sha,
                    "packet_sha256": validator.capsule_packet_digest(
                        binding_digest=binding_sha,
                        schedule_sha256=schedule_sha,
                        condition=row["condition"],
                        case_id=case["case_id"],
                        task_sha256=case["task_text_nfc_sha256"],
                        slot_id=slot_id,
                    ),
                    "task_sha256": case["task_text_nfc_sha256"],
                }
            )
        observations.append(
            {
                "presentation_index": row["presentation_index"],
                "presentation_id": row["presentation_id"],
                "condition": row["condition"],
                "case_id": row["case_id"],
                "terminal_completed": True,
                "capsules": capsules,
                "resolution": copy.deepcopy(case["expected_resolution"]),
                "events": {key: False for key in scorer.EVENT_KEYS},
            }
        )
    return observations


def perfect() -> tuple[tuple[dict, dict], dict, list[dict]]:
    pair = make_pair()
    binding = make_binding(pair)
    return pair, binding, make_observations(pair, binding)


def score(pair: tuple[dict, dict], binding: dict, observations: list[dict]) -> dict:
    return scorer.score_synthetic(
        documents=pair,
        historical_digest_inventory=historical_bytes(),
        observations=observations,
        binding=binding,
        complete_run_assertions={
            "runner_local_raw_persistence": False,
            "heldout_outcome_use": False,
        },
    )


class AeSq1EvaluatorTests(unittest.TestCase):
    def test_perfect_80_presentations_320_capsules_global_and_pass(self) -> None:
        pair, binding, observations = perfect()
        result = score(pair, binding, observations)
        self.assertEqual("pass", result["status"])
        self.assertEqual(
            ["current", "reduced"], [row["condition"] for row in result["conditions"]]
        )
        self.assertTrue(all(all(row["gates"].values()) for row in result["conditions"]))
        self.assertTrue(all(result["complete_run"]["gates"].values()))
        self.assertEqual(
            320, result["complete_run"]["metrics"]["invocation_count_320"]["value"]
        )
        self.assertEqual(
            320,
            result["complete_run"]["metrics"]["unique_capsule_contexts_320"]["value"],
        )
        body = copy.deepcopy(result)
        closure = body.pop("aggregate_digest")
        self.assertEqual(validator.digest(body), closure)
        scorer.validate_result(result, expected_aggregate_digest=closure)
        self.assertIn(
            "not a signature",
            json.loads((ROOT / "evals/ae-sq1/aq/metrics.json").read_text())["claim"],
        )

    def test_live_session_is_single_use_and_clears_observations(self) -> None:
        pair, binding, observations = perfect()
        session = scorer.create_live_score_session(
            documents=pair,
            historical_digest_inventory=historical_bytes(),
            binding=binding,
        )
        for observation in observations:
            session.add(observation)
        self.assertEqual(80, session.observation_count)
        result = session.close(
            {"runner_local_raw_persistence": False, "heldout_outcome_use": False}
        )
        self.assertEqual("pass", result["status"])
        self.assertEqual(0, session.observation_count)
        with self.assertRaises(scorer.EvaluationError):
            session.add(observations[0])

    def test_public_scoring_boundaries_reject_historical_inventory_mappings(
        self,
    ) -> None:
        pair, binding, observations = perfect()
        inventory_mapping = json.loads(historical_bytes())
        with self.assertRaisesRegex(scorer.EvaluationError, "trusted raw bytes"):
            scorer.create_live_score_session(
                documents=pair,
                historical_digest_inventory=inventory_mapping,  # type: ignore[arg-type]
                binding=binding,
            )
        with self.assertRaisesRegex(scorer.EvaluationError, "trusted raw bytes"):
            scorer.score_synthetic(
                documents=pair,
                historical_digest_inventory=inventory_mapping,  # type: ignore[arg-type]
                observations=observations,
                binding=binding,
                complete_run_assertions={
                    "runner_local_raw_persistence": False,
                    "heldout_outcome_use": False,
                },
            )

    def test_malformed_capsule_retains_fixed_denominators_and_fails_safety(
        self,
    ) -> None:
        pair, binding, observations = perfect()
        bad = copy.deepcopy(observations)
        condition = bad[0]["condition"]
        bad[0]["capsules"][0]["parse_status"] = "malformed"
        bad[0]["capsules"][0]["output"] = None
        result = score(pair, binding, bad)
        row = next(
            item for item in result["conditions"] if item["condition"] == condition
        )
        self.assertEqual(
            160, row["metrics"]["capsule_local_need_accuracy"]["denominator"]
        )
        self.assertEqual(
            159, row["metrics"]["capsule_local_need_accuracy"]["numerator"]
        )
        self.assertFalse(row["gates"]["one_decision_stacking"])
        self.assertFalse(row["gates"]["must_not_select"])
        self.assertFalse(result["complete_run"]["gates"]["semantic_schema_order"])
        self.assertEqual("fail", result["status"])

    def test_missing_duplicate_extra_wrong_binding_and_context_collision_fail_closed(
        self,
    ) -> None:
        pair, binding, observations = perfect()
        mutations = []
        mutations.append(observations[:-1])
        duplicate = copy.deepcopy(observations)
        duplicate.append(copy.deepcopy(duplicate[0]))
        mutations.append(duplicate)
        extra = copy.deepcopy(observations)
        row = copy.deepcopy(extra[0])
        row["presentation_index"] = 80
        extra.append(row)
        mutations.append(extra)
        wrong_binding = copy.deepcopy(observations)
        wrong_binding[0]["capsules"][0]["binding_sha256"] = "0" * 64
        mutations.append(wrong_binding)
        collision = copy.deepcopy(observations)
        collision[1]["capsules"][0]["context_id"] = collision[0]["capsules"][0][
            "context_id"
        ]
        mutations.append(collision)
        for mutation in mutations:
            self.assertEqual("fail", score(pair, binding, mutation)["status"])

    def test_conditions_never_pool_and_every_gate_is_global_and(self) -> None:
        pair, binding, observations = perfect()
        bad = copy.deepcopy(observations)
        target_condition = bad[0]["condition"]
        expected = bad[0]["capsules"][0]["output"]["local_need"]
        bad[0]["capsules"][0]["output"]["local_need"] = (
            "no" if expected != "no" else "yes"
        )
        bad[0]["resolution"] = validator.resolve_capsules(
            [capsule["output"] for capsule in bad[0]["capsules"]]
        )
        result = score(pair, binding, bad)
        by_condition = {row["condition"]: row for row in result["conditions"]}
        other = "reduced" if target_condition == "current" else "current"
        self.assertEqual("fail", by_condition[target_condition]["status"])
        self.assertEqual("pass", by_condition[other]["status"])
        self.assertEqual("fail", result["status"])

    def test_invocation_count_is_exact_per_terminal_parsed_capsule(self) -> None:
        pair, binding, observations = perfect()
        redistributed = copy.deepcopy(observations)
        redistributed[0]["capsules"][0]["invocation_count"] = 0
        redistributed[0]["capsules"][1]["invocation_count"] = 2
        result = score(pair, binding, redistributed)
        invocation = result["complete_run"]["metrics"]["invocation_count_320"]
        self.assertEqual(318, invocation["value"])
        self.assertFalse(result["complete_run"]["gates"]["invocation_count_320"])
        self.assertEqual("fail", result["status"])

    def test_capsule_and_output_key_reordering_fail_semantic_schema_order(self) -> None:
        pair, binding, observations = perfect()
        mutations = []

        reordered_capsule = copy.deepcopy(observations)
        capsule = reordered_capsule[0]["capsules"][0]
        reordered_capsule[0]["capsules"][0] = {
            key: capsule[key] for key in reversed(scorer.CAPSULE_KEYS)
        }
        mutations.append(reordered_capsule)

        reordered_output = copy.deepcopy(observations)
        output = reordered_output[0]["capsules"][0]["output"]
        reordered_output[0]["capsules"][0]["output"] = {
            key: output[key] for key in ("reference_need", "local_need", "slot_id")
        }
        mutations.append(reordered_output)

        for mutation in mutations:
            result = score(pair, binding, mutation)
            semantic = result["complete_run"]["metrics"]["semantic_schema_order"]
            self.assertEqual(319, semantic["numerator"])
            self.assertEqual(320, semantic["denominator"])
            self.assertFalse(result["complete_run"]["gates"]["semantic_schema_order"])
            self.assertEqual("fail", result["status"])

    def test_public_result_validator_recomputes_semantics_and_retained_closure(
        self,
    ) -> None:
        pair, binding, observations = perfect()
        result = score(pair, binding, observations)
        retained = result["aggregate_digest"]

        def remint(document: dict) -> None:
            document.pop("aggregate_digest", None)
            document["aggregate_digest"] = validator.digest(document)

        swapped = copy.deepcopy(result)
        swapped["conditions"].reverse()
        remint(swapped)
        with self.assertRaises(scorer.EvaluationError):
            scorer.validate_result(
                swapped, expected_aggregate_digest=swapped["aggregate_digest"]
            )

        wrong_denominator = copy.deepcopy(result)
        metric = wrong_denominator["conditions"][0]["metrics"][
            "capsule_local_need_accuracy"
        ]
        metric.update(
            {
                "numerator": 159,
                "denominator": 159,
                "value": 1.0,
                "exact": {"numerator": 1, "denominator": 1},
                "defined": True,
            }
        )
        remint(wrong_denominator)
        with self.assertRaises(scorer.EvaluationError):
            scorer.validate_result(
                wrong_denominator,
                expected_aggregate_digest=wrong_denominator["aggregate_digest"],
            )

        wrong_gate = copy.deepcopy(result)
        wrong_gate["conditions"][0]["gates"]["capsule_local_need_accuracy"] = False
        wrong_gate["conditions"][0]["status"] = "fail"
        wrong_gate["status"] = "fail"
        remint(wrong_gate)
        with self.assertRaises(scorer.EvaluationError):
            scorer.validate_result(
                wrong_gate, expected_aggregate_digest=wrong_gate["aggregate_digest"]
            )

        stale_authority = copy.deepcopy(result)
        stale_authority["metric_authority_digest"] = "0" * 64
        remint(stale_authority)
        with self.assertRaises(scorer.EvaluationError):
            scorer.validate_result(
                stale_authority,
                expected_aggregate_digest=stale_authority["aggregate_digest"],
            )

        self_consistent_but_wrong = copy.deepcopy(result)
        metric = self_consistent_but_wrong["conditions"][0]["metrics"][
            "capsule_local_need_accuracy"
        ]
        metric.update(
            {
                "numerator": 159,
                "denominator": 160,
                "value": 159 / 160,
                "exact": {"numerator": 159, "denominator": 160},
                "defined": True,
            }
        )
        remint(self_consistent_but_wrong)
        with self.assertRaises(scorer.EvaluationError):
            scorer.validate_result(
                self_consistent_but_wrong,
                expected_aggregate_digest=retained,
            )

    def test_exact_fraction_threshold_neighbors_and_zero_dynamic_denominator(
        self,
    ) -> None:
        rows = {row["gate_id"]: row for row in scorer._gate_rows()}
        self.assertTrue(
            scorer._passes(scorer._ratio(152, 160), rows["capsule_local_need_accuracy"])
        )
        self.assertFalse(
            scorer._passes(scorer._ratio(151, 160), rows["capsule_local_need_accuracy"])
        )
        self.assertTrue(
            scorer._passes(scorer._ratio(36, 40), rows["exact_selected_set"])
        )
        self.assertFalse(
            scorer._passes(scorer._ratio(35, 40), rows["exact_selected_set"])
        )
        zero = scorer._ratio(0, 0)
        self.assertEqual(0, zero["value"])
        self.assertFalse(zero["defined"])
        self.assertFalse(scorer._passes(zero, rows["selected_precision"]))

    def test_no_caller_denominators_no_case_output_and_zero_write(self) -> None:
        pair, binding, observations = perfect()
        forged = copy.deepcopy(observations)
        forged[0]["counts"] = {
            "selected_precision": {"numerator": 999, "denominator": 1}
        }
        result = score(pair, binding, forged)
        self.assertEqual("fail", result["status"])
        self.assertNotIn("cases", result)
        self.assertNotIn("observations", result)
        with tempfile.TemporaryDirectory() as directory:
            before = set(os.listdir(directory))
            previous = Path.cwd()
            try:
                os.chdir(directory)
                clean = score(pair, binding, observations)
            finally:
                os.chdir(previous)
            self.assertEqual("pass", clean["status"])
            self.assertEqual(before, set(os.listdir(directory)))


if __name__ == "__main__":
    unittest.main()
