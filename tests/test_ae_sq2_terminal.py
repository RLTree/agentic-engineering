"""Terminal governance closeout checks for AE-SQ2."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = ROOT / "evals/ae-sq2/ar/terminal-decision.json"
RECORD_PATH = ROOT / "evals/ae-sq2/d0/diagnostic-record.json"
AUTHORITY_PATH = ROOT / "evals/ae-sq2/program-authority.json"
PLAN_PATH = ROOT / "docs/exec-plans/active/ae-sq2.md"
RECORD_COMMIT = "e2562ca4da5f3dc14fb07c1522f911e2dfe4334d"
HEX64 = set("0123456789abcdef")


def strict(raw: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite: {token}")
        ),
    )
    if not isinstance(value, dict):
        raise ValueError("root must be object")
    return value


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def is_sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and not (set(value) - HEX64)


def valid_terminal(document: dict[str, Any]) -> bool:
    return (
        tuple(document)
        == (
            "schema_version",
            "program_id",
            "stage",
            "status",
            "decision",
            "stop",
            "claim_ceiling",
            "terminal_reason",
            "diagnostic_outcome",
            "diagnostic_record_custody",
            "persistence_violation",
            "phase_status",
            "retention",
            "successor_route",
            "terminal_edges",
        )
        and document["schema_version"] == "ae-sq2-ar-terminal-decision-v1"
        and document["program_id"] == "AE-SQ2"
        and document["stage"] == "SQ2-AR"
        and document["status"] == "terminal"
        and document["decision"] == "DO_NOT_RELEASE_OR_PROMOTE"
        and document["stop"] is True
        and document["terminal_reason"]
        == "durable-one-shot-state-fields-outside-frozen-F0-exhaustive-persistence-allowlist"
        and document["persistence_violation"]["route"] == "SQ2-AR"
        and document["persistence_violation"]["repair_within_AE_SQ2_permitted"] is False
        and document["successor_route"] == "new-owner-authorized-program-id-only"
        and document["phase_status"]["SQ2_F1"] == "not_started"
        and document["phase_status"]["SQ2_F2"] == "not_started-no-corpus-authored"
        and document["phase_status"]["SQ2_F4"] == "not_started"
        and document["phase_status"]["SQ2_F5"] == "not_started"
        and document["phase_status"]["SQ2_AS_HANDOFF"] == "blocked"
        and len(document["terminal_edges"]) == 16
        and "no_SQ2_retry" in document["terminal_edges"]
        and "no_reopen" in document["terminal_edges"]
        and "no_H6" in document["terminal_edges"]
        and "no_downstream" in document["terminal_edges"]
    )


class AeSq2TerminalTests(unittest.TestCase):
    def test_exact_terminal_decision_and_diagnostic_custody(self) -> None:
        decision = strict(DECISION_PATH.read_bytes())
        record = strict(RECORD_PATH.read_bytes())
        self.assertTrue(valid_terminal(decision))
        custody = decision["diagnostic_record_custody"]
        committed = subprocess.run(
            ["git", "show", f"{RECORD_COMMIT}:evals/ae-sq2/d0/diagnostic-record.json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(committed, RECORD_PATH.read_bytes())
        self.assertEqual(hashlib.sha256(committed).hexdigest(), custody["raw_sha256"])
        self.assertEqual(
            subprocess.run(
                ["git", "hash-object", "evals/ae-sq2/d0/diagnostic-record.json"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            custody["blob"],
        )
        self.assertEqual(record["record_sha256"], custody["record_sha256"])
        self.assertEqual(record["aggregate_sha256"], custody["aggregate_sha256"])
        self.assertEqual(record["calls_started"], 4)
        self.assertEqual(record["calls_completed"], 4)
        self.assertEqual(record["classification_counts"]["schema_unsupported"], 4)
        self.assertEqual(sum(record["classification_counts"].values()), 4)
        self.assertTrue(all(value == 0 for value in record["usage"].values()))

    def test_persisted_state_reconstructs_and_exceeds_frozen_allowlist(self) -> None:
        decision = strict(DECISION_PATH.read_bytes())
        authority = strict(AUTHORITY_PATH.read_bytes())
        violation = decision["persistence_violation"]
        state = {
            "binding": violation["persisted_binding"],
            "custody_key": violation["custody_key"],
            "record_sha256": violation["state_record_sha256"],
            "schema_version": "ae-sq2-d0-custody-v1",
            "state_sha256": violation["state_sha256"],
            "status": violation["state_status"],
        }
        self.assertEqual(list(state), violation["persisted_top_level_keys"])
        self.assertEqual(
            hashlib.sha256(canonical(state)).hexdigest(), violation["state_raw_sha256"]
        )
        unsealed = dict(state)
        unsealed.pop("state_sha256")
        self.assertEqual(
            hashlib.sha256(canonical(unsealed)).hexdigest(), violation["state_sha256"]
        )
        self.assertEqual(
            hashlib.sha256(canonical(state["binding"])).hexdigest(),
            violation["custody_key"],
        )
        allowlist = set(authority["diagnostic_contract"]["permitted_persisted_fields"])
        self.assertTrue(
            set(violation["top_level_keys_outside_allowlist"]).isdisjoint(allowlist)
        )
        self.assertTrue(
            set(violation["binding_keys_outside_allowlist"]).isdisjoint(allowlist)
        )
        self.assertTrue(all(is_sha(value) for value in state["binding"].values()))

    def test_plan_is_terminal_and_no_sq2_later_artifacts_exist(self) -> None:
        plan = PLAN_PATH.read_text(encoding="utf-8")
        self.assertIn("Status: **TERMINAL — SQ2-AR", plan)
        self.assertIn("## 16. Terminal checkpoint after SQ2-D0", plan)
        self.assertIn("no result; D0 cannot qualify AQ", plan)
        for path in (
            "evals/ae-sq2/f1",
            "evals/ae-sq2/f2",
            "evals/ae-sq2/f3",
            "evals/ae-sq2/f4",
            "evals/ae-sq2/f5",
            "evals/ae-sq2/f6",
        ):
            self.assertFalse((ROOT / path).exists(), path)

    def test_mutation_reds_fail_closed(self) -> None:
        decision = strict(DECISION_PATH.read_bytes())
        mutations = []
        for key, value in (
            ("stop", False),
            ("status", "open"),
            ("decision", "RELEASE"),
            ("successor_route", "retry"),
        ):
            mutation = copy.deepcopy(decision)
            mutation[key] = value
            mutations.append(mutation)
        mutation = copy.deepcopy(decision)
        mutation["phase_status"]["SQ2_F1"] = "started"
        mutations.append(mutation)
        mutation = copy.deepcopy(decision)
        mutation["terminal_edges"].remove("no_reopen")
        mutations.append(mutation)
        mutation = copy.deepcopy(decision)
        mutation["unexpected"] = True
        mutations.append(mutation)
        self.assertTrue(all(not valid_terminal(mutation) for mutation in mutations))


if __name__ == "__main__":
    unittest.main()
