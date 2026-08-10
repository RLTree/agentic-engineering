from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VERDICT_PATH = (
    ROOT / "evals/foundation-v4/aq9-h5-independent-evidence-verdict-v1.json"
)
VERDICT = json.loads(VERDICT_PATH.read_text())

TOP_LEVEL_KEYS = [
    "schema_version",
    "verdict_id",
    "status",
    "reason_code",
    "claim_ceiling",
    "authority_basis",
    "review_disposition",
    "independence_and_role_exclusions",
    "terminal_transition",
    "prohibitions",
    "maximum_claim",
]
AUTHORITY_KEYS = ["amendment", "evidence_packet", "packet_test"]
AMENDMENT_KEYS = ["commit", "tree", "path", "git_blob_sha1", "sha256"]
ARTIFACT_KEYS = ["path", "sha256"]
REVIEW_KEYS = [
    "allowed_durable_bit",
    "access_boundary_status",
    "packet_content_inspected",
    "source_artifacts_inspected",
    "review_aborted_before_packet_or_source_inspection",
    "e0_pass_recorded",
    "mechanism_selection_performed",
    "mechanism_ranking_performed",
]
INDEPENDENCE_KEYS = [
    "reviewer_role",
    "independent_of_packet_authors",
    "excluded_future_roles",
    "future_h5_or_k_role_allowed",
    "no_further_access_declaration",
]
TERMINAL_KEYS = [
    "aq9_status",
    "e0_status",
    "h5_work_allowed",
    "k_work_allowed",
    "recovery_allowed",
    "review_restart_allowed",
    "role_transfer_cures_breach",
    "only_allowed_next_transition",
]

EXPECTED_VERDICT = {
    "schema_version": "1.0",
    "verdict_id": "AQ9-H5-independent-evidence-E0-terminal-failure-v1",
    "status": "E0=FAIL",
    "reason_code": "role-wide-firewall-breach-during-independent-review",
    "claim_ceiling": "structural-process-failure-only",
    "authority_basis": {
        "amendment": {
            "commit": "e7ca9e9b89aad1a1933da5378d11d84240c210f7",
            "tree": "475d93faf9b4853eb120a6230f5e5cef36178f84",
            "path": "EXECPLAN.md",
            "git_blob_sha1": "9d26f09877ea55ddc17eddd8b97ce8b387b96f1b",
            "sha256": (
                "acf1b68b3194ee4852f773aac7c18b8e7222fd47f6091e5858b5e06eea0bc141"
            ),
        },
        "evidence_packet": {
            "path": "evals/foundation-v4/aq9-h5-independent-evidence-v1.json",
            "sha256": (
                "1ec15fa32f3ad262eb95d913c964854799546a0397874cfa803322b4bb761fcd"
            ),
        },
        "packet_test": {
            "path": "tests/test_aq9_h5_independent_evidence_v1.py",
            "sha256": (
                "8d8c298af881b0e8d80a773dbdacae35fba8614acf5ffae4301fe169ca8aa876"
            ),
        },
    },
    "review_disposition": {
        "allowed_durable_bit": "AQ8 aggregate=fail",
        "access_boundary_status": "exceeded_allowed_durable_bit",
        "packet_content_inspected": False,
        "source_artifacts_inspected": False,
        "review_aborted_before_packet_or_source_inspection": True,
        "e0_pass_recorded": False,
        "mechanism_selection_performed": False,
        "mechanism_ranking_performed": False,
    },
    "independence_and_role_exclusions": {
        "reviewer_role": "independent-E0-verdict-owner",
        "independent_of_packet_authors": True,
        "excluded_future_roles": [
            "H5-author",
            "H5-reviewer",
            "H5-validator",
            "H5-integrator",
            "H5-executor",
            "H5-decision-owner",
            "K-author",
            "K-reviewer",
            "K-validator",
            "K-integrator",
            "K-executor",
            "K-decision-owner",
        ],
        "future_h5_or_k_role_allowed": False,
        "no_further_access_declaration": (
            "No further access to the packet, its sources, additional amendment "
            "context, or protected evaluation material is permitted."
        ),
    },
    "terminal_transition": {
        "aq9_status": "terminally_closed",
        "e0_status": "failed",
        "h5_work_allowed": False,
        "k_work_allowed": False,
        "recovery_allowed": False,
        "review_restart_allowed": False,
        "role_transfer_cures_breach": False,
        "only_allowed_next_transition": "AR-bounded-retirement",
    },
    "prohibitions": [
        "no-e0-pass",
        "no-h5-or-k-work",
        "no-role-transfer-recovery",
        "no-further-protected-material-access",
        "no-mechanism-selection-or-ranking",
        "no-expanded-claim",
    ],
    "maximum_claim": (
        "This artifact establishes only a structural process failure and its "
        "terminal transition; it makes no behavioral or external-system claim."
    ),
}

FORBIDDEN_DETAIL_FRAGMENTS = (
    "case_id",
    "metric",
    "result",
    "corpus",
    "prompt",
    "task_text",
    "trajectory",
    "output",
    "score",
    "precision",
    "recall",
)


def raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision(expression: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", "--verify", expression],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def git_path_bytes(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout


def assert_no_forbidden_detail(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = key.lower()
            if any(fragment in lowered for fragment in FORBIDDEN_DETAIL_FRAGMENTS):
                raise ValueError("forbidden detail key")
            assert_no_forbidden_detail(nested)
    elif isinstance(value, list):
        for nested in value:
            assert_no_forbidden_detail(nested)
    elif isinstance(value, str):
        lowered = value.lower()
        if value == "E0=PASS" or any(
            fragment in lowered for fragment in FORBIDDEN_DETAIL_FRAGMENTS
        ):
            raise ValueError("forbidden detail value")


def validate_verdict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("closed verdict object required")
    assert_no_forbidden_detail(value)
    if list(value) != TOP_LEVEL_KEYS:
        raise ValueError("closed ordered top-level verdict required")
    authority = value["authority_basis"]
    if not isinstance(authority, dict) or list(authority) != AUTHORITY_KEYS:
        raise ValueError("closed ordered authority required")
    if list(authority["amendment"]) != AMENDMENT_KEYS:
        raise ValueError("closed ordered amendment custody required")
    for artifact_key in ("evidence_packet", "packet_test"):
        if list(authority[artifact_key]) != ARTIFACT_KEYS:
            raise ValueError("closed ordered artifact binding required")
    if list(value["review_disposition"]) != REVIEW_KEYS:
        raise ValueError("closed ordered review disposition required")
    if list(value["independence_and_role_exclusions"]) != INDEPENDENCE_KEYS:
        raise ValueError("closed ordered independence declaration required")
    if list(value["terminal_transition"]) != TERMINAL_KEYS:
        raise ValueError("closed ordered terminal transition required")

    string_fields = (
        value["schema_version"],
        value["verdict_id"],
        value["status"],
        value["reason_code"],
        value["claim_ceiling"],
        value["maximum_claim"],
    )
    if any(not isinstance(field, str) or not field for field in string_fields):
        raise ValueError("nonempty string verdict fields required")
    if not isinstance(value["prohibitions"], list) or any(
        not isinstance(item, str) or not item for item in value["prohibitions"]
    ):
        raise ValueError("closed prohibition list required")

    boolean_fields = (
        value["review_disposition"]["packet_content_inspected"],
        value["review_disposition"]["source_artifacts_inspected"],
        value["review_disposition"][
            "review_aborted_before_packet_or_source_inspection"
        ],
        value["review_disposition"]["e0_pass_recorded"],
        value["review_disposition"]["mechanism_selection_performed"],
        value["review_disposition"]["mechanism_ranking_performed"],
        value["independence_and_role_exclusions"][
            "independent_of_packet_authors"
        ],
        value["independence_and_role_exclusions"]["future_h5_or_k_role_allowed"],
        value["terminal_transition"]["h5_work_allowed"],
        value["terminal_transition"]["k_work_allowed"],
        value["terminal_transition"]["recovery_allowed"],
        value["terminal_transition"]["review_restart_allowed"],
        value["terminal_transition"]["role_transfer_cures_breach"],
    )
    if any(type(field) is not bool for field in boolean_fields):
        raise ValueError("exact boolean verdict fields required")

    roles = value["independence_and_role_exclusions"]["excluded_future_roles"]
    if not isinstance(roles, list) or any(
        not isinstance(role, str) or not role for role in roles
    ):
        raise ValueError("closed future-role exclusion list required")
    if value != EXPECTED_VERDICT:
        raise ValueError("closed terminal verdict value mismatch")
    return value


class Aq9H5IndependentEvidenceVerdictV1Tests(unittest.TestCase):
    def test_verdict_is_closed_ordered_typed_and_exact(self):
        self.assertIs(validate_verdict(VERDICT), VERDICT)

    def test_packet_and_test_live_hashes_match_without_parsing_content(self):
        authority = VERDICT["authority_basis"]
        for artifact_key in ("evidence_packet", "packet_test"):
            binding = authority[artifact_key]
            self.assertEqual(raw_sha256(ROOT / binding["path"]), binding["sha256"])

    def test_amendment_custody_uses_exact_commit_tree_and_direct_path(self):
        amendment = VERDICT["authority_basis"]["amendment"]
        commit = amendment["commit"]
        path = amendment["path"]
        self.assertEqual(git_revision(f"{commit}^{{commit}}"), commit)
        self.assertEqual(git_revision(f"{commit}^{{tree}}"), amendment["tree"])
        self.assertEqual(git_revision(f"{commit}:{path}"), amendment["git_blob_sha1"])
        self.assertEqual(
            hashlib.sha256(git_path_bytes(commit, path)).hexdigest(),
            amendment["sha256"],
        )

    def test_failure_reason_and_terminal_transition_are_exact(self):
        self.assertEqual(VERDICT["status"], "E0=FAIL")
        self.assertEqual(
            VERDICT["reason_code"],
            "role-wide-firewall-breach-during-independent-review",
        )
        review = VERDICT["review_disposition"]
        self.assertEqual(review["allowed_durable_bit"], "AQ8 aggregate=fail")
        self.assertEqual(
            review["access_boundary_status"], "exceeded_allowed_durable_bit"
        )
        self.assertFalse(review["packet_content_inspected"])
        self.assertFalse(review["source_artifacts_inspected"])
        self.assertTrue(review["review_aborted_before_packet_or_source_inspection"])
        self.assertFalse(review["e0_pass_recorded"])

        terminal = VERDICT["terminal_transition"]
        self.assertEqual(terminal["aq9_status"], "terminally_closed")
        self.assertEqual(terminal["e0_status"], "failed")
        self.assertFalse(terminal["h5_work_allowed"])
        self.assertFalse(terminal["k_work_allowed"])
        self.assertFalse(terminal["recovery_allowed"])
        self.assertFalse(terminal["review_restart_allowed"])
        self.assertFalse(terminal["role_transfer_cures_breach"])
        self.assertEqual(
            terminal["only_allowed_next_transition"], "AR-bounded-retirement"
        )

    def test_independence_role_exclusions_and_no_further_access_are_exact(self):
        declaration = VERDICT["independence_and_role_exclusions"]
        self.assertEqual(declaration["reviewer_role"], "independent-E0-verdict-owner")
        self.assertTrue(declaration["independent_of_packet_authors"])
        self.assertEqual(
            declaration["excluded_future_roles"],
            EXPECTED_VERDICT["independence_and_role_exclusions"][
                "excluded_future_roles"
            ],
        )
        self.assertFalse(declaration["future_h5_or_k_role_allowed"])
        self.assertEqual(
            declaration["no_further_access_declaration"],
            EXPECTED_VERDICT["independence_and_role_exclusions"][
                "no_further_access_declaration"
            ],
        )

    def test_claim_ceiling_and_no_mechanism_selection_are_exact(self):
        self.assertEqual(VERDICT["claim_ceiling"], "structural-process-failure-only")
        review = VERDICT["review_disposition"]
        self.assertFalse(review["mechanism_selection_performed"])
        self.assertFalse(review["mechanism_ranking_performed"])
        self.assertEqual(
            VERDICT["maximum_claim"], EXPECTED_VERDICT["maximum_claim"]
        )
        assert_no_forbidden_detail(VERDICT)

    def test_mutation_reds_reject_pass_recovery_drift_and_forbidden_detail(self):
        mutations: list[dict[str, Any]] = []

        pass_flip = copy.deepcopy(VERDICT)
        pass_flip["status"] = "E0=PASS"
        mutations.append(pass_flip)

        reason_removed = copy.deepcopy(VERDICT)
        del reason_removed["reason_code"]
        mutations.append(reason_removed)

        recovery_allowed = copy.deepcopy(VERDICT)
        recovery_allowed["terminal_transition"]["recovery_allowed"] = True
        mutations.append(recovery_allowed)

        ar_only_changed = copy.deepcopy(VERDICT)
        ar_only_changed["terminal_transition"]["only_allowed_next_transition"] = (
            "another-transition"
        )
        mutations.append(ar_only_changed)

        packet_hash_drift = copy.deepcopy(VERDICT)
        packet_hash_drift["authority_basis"]["evidence_packet"]["sha256"] = "0" * 64
        mutations.append(packet_hash_drift)

        mechanism_selection = copy.deepcopy(VERDICT)
        mechanism_selection["review_disposition"]["mechanism_selection_performed"] = (
            True
        )
        mutations.append(mechanism_selection)

        for mutant in mutations:
            with self.assertRaises(ValueError):
                validate_verdict(mutant)

        forbidden_detail = copy.deepcopy(VERDICT)
        forbidden_detail["review_disposition"]["metric_detail"] = "redacted"
        with self.assertRaisesRegex(ValueError, "forbidden detail"):
            validate_verdict(forbidden_detail)


if __name__ == "__main__":
    unittest.main()
