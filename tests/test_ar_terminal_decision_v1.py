from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "evals" / "foundation-v4" / "ar-terminal-decision-v1.json"

EXPECTED_COMMIT = "bbd1c53de6000bb51dbb128c81ae39ab5c1ff554"
EXPECTED_TREE = "e600a17c18ec1517233a89a47ab4093049d7ebf1"
EXPECTED_E0_COMMIT = "a8ae421c4e8619f4cc72cd91bbd7f65da1928f5d"
EXPECTED_E0_TREE = "077968d10f9172c2cf86468c3b91c2137dfbffa4"
EXPECTED_RELEASE_STDOUT_SHA256 = (
    "d67c600bb49642f38b7da0fe41699f5bfffe4bfd06935c620bf5d74e0aedb996"
)

TOP_LEVEL_KEYS = (
    "schema_version",
    "candidate",
    "authority_custody",
    "e0_terminal_authority",
    "package_structural_result",
    "claim_vector",
    "retention_no_delete",
    "unmet_success_conditions",
    "forbidden_stage_edges",
    "forbidden_actions",
    "forbidden_results",
    "decision",
    "terminal_state",
    "claim_ceiling",
)
FILE_KEYS = ("role", "path", "blob", "sha256")

AUTHORITY_FILES = (
    (
        "terminal_plan",
        "EXECPLAN.md",
        "a6fd3d461c8fcde9cdfc82c8b75f20baa4365535",
        "0d70e3984a1e68726d7fe1e8c38455a1205f2b6660174aa280a55be06e66943f",
    ),
    (
        "terminal_decision_log",
        "docs/foundations/decision-log.csv",
        "eecf25ceb534a856bc5a9915247a1166e755512a",
        "80289a531d8e4dde54ea03ec2539fe024d9bef015acf76d0f617e89608a63aa6",
    ),
    (
        "current_foundation",
        "docs/foundations/current-2026-08-08.md",
        "f264a69485bed2882a84d36d375f249603db5900",
        "1cc550b2539cd638bd046dcc40c7d0f7251948e575bbdb060f3d2add5ed4ca34",
    ),
    (
        "current_foundation_register",
        "docs/foundations/register.csv",
        "eade50e09f117bb7c40e394f5c7b8b2686fb48ad",
        "3043ad8ff93cbf35779638be9e8a7c8e7082d14166297fdddab9b9d1ddadeaf3",
    ),
    (
        "structural_release_checker",
        "scripts/release_check.py",
        "3e8bee25d8c3a13b8224a9393ceb20374ffa5d70",
        "8038b19990ad800047e20088ddfcb5eb5f51b91a9dbb05b28a3762bf14e7e8a9",
    ),
)

E0_FILES = (
    (
        "packet",
        "evals/foundation-v4/aq9-h5-independent-evidence-v1.json",
        "34bb5efc8411961227b374d7ae3b610cda628de7",
        "1ec15fa32f3ad262eb95d913c964854799546a0397874cfa803322b4bb761fcd",
    ),
    (
        "verdict",
        "evals/foundation-v4/aq9-h5-independent-evidence-verdict-v1.json",
        "b6b142e935381baada66e4d148364d4f22d55e88",
        "374825c130d076e4d298c0a8d004fc5d6f33c201715ffefb190f98c2c87815da",
    ),
)
E0_OBJECT_SIZES = (34869, 2697)
E0_PATHS = frozenset(record[1] for record in E0_FILES)

CLAIM_VECTOR = (
    ("foundation_currentness", "observed_current_authority"),
    ("release_identity", "observed_structural_exact_candidate"),
    ("executed_structural_checks", "observed_one_package_structure_pass"),
    ("package_reproducibility", "unobserved"),
    ("archive_safety", "unobserved"),
    ("activation_abstention", "unobserved_terminally_blocked"),
    ("isolated_advice_value", "unobserved_terminally_blocked"),
    ("composition", "explicitly_not_adopted"),
    (
        "host_install_discovery_coexistence",
        "unobserved_terminally_blocked",
    ),
    ("protocol_currentness", "source_review_only_terminally_blocked"),
    (
        "field_usefulness",
        "unobserved_terminally_blocked_not_requested_or_authorized",
    ),
)

RETENTION_SURFACES = (
    "historical_source_count_coverage_release_gates",
    "obsolete_confidence_model",
    "synchronized_research_update_choreography",
    "executable_version_3_history",
    "generic_shared_reference_catalogs_without_measured_use",
    "duplicated_draft_sources",
    "superseded_protocol_guidance",
)
RETENTION_REASON = "active_or_external_readers_remain_or_rendered_absence_not_proven"

UNMET_SUCCESS_CONDITIONS = (
    (
        "package_reproducibility_is_observed",
        "unmet_unobserved_terminal_stop_no_execution",
    ),
    (
        "archive_safety_is_observed",
        "unmet_unobserved_terminal_stop_no_execution",
    ),
    (
        "four_skill_activation_and_isolated_value_decisions_are_measured",
        "unmet_terminally_blocked",
    ),
    (
        "exact_archives_pass_host_install_discovery_coexistence_journey",
        "unmet_terminally_blocked",
    ),
    (
        "protocol_currentness_is_AH_verified",
        "unmet_source_review_only_terminally_blocked",
    ),
    (
        "field_usefulness_is_observed",
        "unmet_terminally_blocked_not_requested_or_authorized",
    ),
)

FORBIDDEN_EDGES = (
    ("AR", "AQ"),
    ("AR", "H5"),
    ("AR", "H6"),
    ("AR", "AS"),
    ("AR", "AC"),
    ("AR", "AH"),
    ("AR", "AF"),
)
FORBIDDEN_ACTIONS = (
    "release",
    "promote",
    "publish",
    "install",
    "monitor",
    "model_execution",
    "field_execution",
    "deletion",
    "migration_execution",
    "retry",
    "reopen",
    "resume",
    "h6_execution",
    "activation_execution",
    "corpus_execution",
    "later_authorization",
)
FORBIDDEN_RESULTS = (
    "release_or_promotion_claim",
    "package_reproducibility_observed",
    "archive_safety_observed",
    "activation_abstention_observed",
    "isolated_advice_value_observed",
    "composition_adopted",
    "host_install_discovery_coexistence_observed",
    "protocol_AH_verified",
    "field_usefulness_observed",
    "later_authorization_cure",
    "reopen_cure",
    "aggregate_confidence",
)


def no_duplicate_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate JSON object key")
    return dict(pairs)


def reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def parse_json_document(raw: bytes | str) -> object:
    text = raw.decode("utf-8") if type(raw) is bytes else raw
    return json.loads(
        text,
        object_pairs_hook=no_duplicate_object,
        parse_constant=reject_json_constant,
    )


def exact_dict(value: object, keys: tuple[str, ...], label: str) -> dict:
    if type(value) is not dict:
        raise AssertionError(f"{label} must be an object")
    if tuple(value) != keys:
        raise AssertionError(f"{label} keys/order differ: {tuple(value)!r}")
    return value


def exact_list(value: object, label: str) -> list:
    if type(value) is not list:
        raise AssertionError(f"{label} must be an array")
    return value


def exact_string(value: object, label: str) -> str:
    if type(value) is not str:
        raise AssertionError(f"{label} must be a string")
    return value


def exact_bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise AssertionError(f"{label} must be a boolean")
    return value


def exact_int(value: object, label: str) -> int:
    if type(value) is not int:
        raise AssertionError(f"{label} must be an integer, not a boolean")
    return value


def assert_string_array(value: object, expected: tuple[str, ...], label: str) -> None:
    items = exact_list(value, label)
    for index, item in enumerate(items):
        exact_string(item, f"{label}[{index}]")
    if tuple(items) != expected:
        raise AssertionError(f"{label} values/order differ")


def assert_no_aggregate_confidence_key(value: object, label: str = "document") -> None:
    if type(value) is dict:
        if "aggregate_confidence" in value:
            raise AssertionError(f"{label} contains aggregate confidence")
        for key, child in value.items():
            assert_no_aggregate_confidence_key(child, f"{label}.{key}")
    elif type(value) is list:
        for index, child in enumerate(value):
            assert_no_aggregate_confidence_key(child, f"{label}[{index}]")


def assert_release_result_structure(value: object) -> dict:
    result = exact_dict(
        value,
        ("candidate", "checks", "claim_states", "package_set", "passed"),
        "package_structural_result.result",
    )
    candidate = exact_dict(
        result["candidate"],
        ("commit", "tree", "validation_input_digest"),
        "package_structural_result.result.candidate",
    )
    for key, item in candidate.items():
        exact_string(item, f"package_structural_result.result.candidate.{key}")

    checks = exact_list(result["checks"], "package_structural_result.result.checks")
    if len(checks) != 1:
        raise AssertionError("exactly one structural check must be recorded")
    check = exact_dict(
        checks[0],
        ("id", "maximum_claim", "observations", "status"),
        "package_structural_result.result.checks[0]",
    )
    observations = exact_dict(
        check["observations"],
        (
            "candidate_commit",
            "candidate_tree",
            "marketplace_contract_version",
            "package_count",
            "package_names",
            "package_set_digest",
            "package_set_version",
            "package_versions",
            "skill_count",
            "validation_input_digest",
        ),
        "package_structural_result.result.checks[0].observations",
    )
    for key in ("id", "maximum_claim", "status"):
        exact_string(check[key], f"package_structural_result.result.checks[0].{key}")
    for key, item in observations.items():
        exact_string(
            item,
            f"package_structural_result.result.checks[0].observations.{key}",
        )

    claim_states = exact_dict(
        result["claim_states"],
        (
            "activation_abstention",
            "composition",
            "field_usefulness",
            "host_install_discovery",
            "isolated_advice_value",
            "structural_package",
        ),
        "package_structural_result.result.claim_states",
    )
    for key, item in claim_states.items():
        exact_string(item, f"package_structural_result.result.claim_states.{key}")

    package_set = exact_dict(
        result["package_set"],
        (
            "aggregate_digest",
            "gateway",
            "package_set_version",
            "packs",
            "schema_version",
            "skill_union",
        ),
        "package_structural_result.result.package_set",
    )
    for key in ("aggregate_digest", "gateway", "package_set_version", "schema_version"):
        exact_string(
            package_set[key],
            f"package_structural_result.result.package_set.{key}",
        )
    packs = exact_list(
        package_set["packs"], "package_structural_result.result.package_set.packs"
    )
    if len(packs) != 4:
        raise AssertionError("the exact structural result must contain four packs")
    for index, pack_value in enumerate(packs):
        pack = exact_dict(
            pack_value,
            ("enabled_skills", "manifest_digest", "name", "version"),
            f"package_structural_result.result.package_set.packs[{index}]",
        )
        skills = exact_list(
            pack["enabled_skills"],
            (
                "package_structural_result.result.package_set"
                f".packs[{index}].enabled_skills"
            ),
        )
        for skill_index, skill in enumerate(skills):
            exact_string(
                skill,
                (
                    "package_structural_result.result.package_set"
                    f".packs[{index}].enabled_skills[{skill_index}]"
                ),
            )
        for key in ("manifest_digest", "name", "version"):
            exact_string(
                pack[key],
                f"package_structural_result.result.package_set.packs[{index}].{key}",
            )
    skill_union = exact_list(
        package_set["skill_union"],
        "package_structural_result.result.package_set.skill_union",
    )
    for index, skill in enumerate(skill_union):
        exact_string(
            skill,
            f"package_structural_result.result.package_set.skill_union[{index}]",
        )
    if (
        exact_bool(result["passed"], "package_structural_result.result.passed")
        is not True
    ):
        raise AssertionError("the exact structural result must pass")
    return result


def validate_document(value: object) -> dict:
    document = exact_dict(value, TOP_LEVEL_KEYS, "document")
    if exact_string(document["schema_version"], "schema_version") != (
        "AR-terminal-decision-v1"
    ):
        raise AssertionError("schema version differs")

    candidate = exact_dict(document["candidate"], ("commit", "tree"), "candidate")
    if candidate != {"commit": EXPECTED_COMMIT, "tree": EXPECTED_TREE}:
        raise AssertionError("candidate custody differs")

    authority = exact_dict(
        document["authority_custody"],
        ("commit", "tree", "files"),
        "authority_custody",
    )
    if authority["commit"] != EXPECTED_COMMIT or authority["tree"] != EXPECTED_TREE:
        raise AssertionError("current authority commit/tree differs")
    authority_files = exact_list(authority["files"], "authority_custody.files")
    if len(authority_files) != len(AUTHORITY_FILES):
        raise AssertionError("current authority file count differs")
    for index, (record_value, expected) in enumerate(
        zip(authority_files, AUTHORITY_FILES, strict=True)
    ):
        record = exact_dict(
            record_value, FILE_KEYS, f"authority_custody.files[{index}]"
        )
        for key, item in record.items():
            exact_string(item, f"authority_custody.files[{index}].{key}")
        if tuple(record.values()) != expected:
            raise AssertionError(f"authority_custody.files[{index}] differs")

    e0 = exact_dict(
        document["e0_terminal_authority"],
        ("status", "commit", "tree", "inspection_scope", "files"),
        "e0_terminal_authority",
    )
    if (
        e0["status"] != "fail"
        or e0["commit"] != EXPECTED_E0_COMMIT
        or e0["tree"] != EXPECTED_E0_TREE
        or e0["inspection_scope"] != "git_object_metadata_only"
    ):
        raise AssertionError("E0 terminal metadata differs")
    e0_files = exact_list(e0["files"], "e0_terminal_authority.files")
    if len(e0_files) != len(E0_FILES):
        raise AssertionError("E0 terminal metadata file count differs")
    for index, (record_value, expected) in enumerate(
        zip(e0_files, E0_FILES, strict=True)
    ):
        record = exact_dict(
            record_value,
            FILE_KEYS,
            f"e0_terminal_authority.files[{index}]",
        )
        for key, item in record.items():
            exact_string(item, f"e0_terminal_authority.files[{index}].{key}")
        if tuple(record.values()) != expected:
            raise AssertionError(f"e0_terminal_authority.files[{index}] differs")

    structural = exact_dict(
        document["package_structural_result"],
        ("command", "executed_check_count", "stdout_sha256", "result"),
        "package_structural_result",
    )
    assert_string_array(
        structural["command"],
        ("python3", "scripts/release_check.py"),
        "package_structural_result.command",
    )
    if (
        exact_int(
            structural["executed_check_count"],
            "package_structural_result.executed_check_count",
        )
        != 1
    ):
        raise AssertionError("executed structural check count differs")
    if (
        exact_string(
            structural["stdout_sha256"], "package_structural_result.stdout_sha256"
        )
        != EXPECTED_RELEASE_STDOUT_SHA256
    ):
        raise AssertionError("structural result stdout digest differs")
    release_result = assert_release_result_structure(structural["result"])
    rendered_release_result = (
        json.dumps(release_result, sort_keys=True).encode("utf-8") + b"\n"
    )
    if hashlib.sha256(rendered_release_result).hexdigest() != (
        EXPECTED_RELEASE_STDOUT_SHA256
    ):
        raise AssertionError("embedded structural result values differ")
    if release_result["candidate"] != {
        "commit": EXPECTED_COMMIT,
        "tree": EXPECTED_TREE,
        "validation_input_digest": (
            "sha256:33bc963d170b5be3a3000bcef39b64f429e45565372736dac27b6d8be252994f"
        ),
    }:
        raise AssertionError("structural result candidate differs")
    check = release_result["checks"][0]
    if (check["id"], check["status"], check["maximum_claim"]) != (
        "package-structure",
        "passed",
        "structural",
    ):
        raise AssertionError("structural check identity/status/claim differs")

    claims = exact_dict(
        document["claim_vector"],
        tuple(key for key, _ in CLAIM_VECTOR),
        "claim_vector",
    )
    for key, item in claims.items():
        exact_string(item, f"claim_vector.{key}")
    if tuple(claims.items()) != CLAIM_VECTOR:
        raise AssertionError("claim vector values differ")
    observed = tuple(
        key for key, state in claims.items() if state.startswith("observed_")
    )
    if observed != (
        "foundation_currentness",
        "release_identity",
        "executed_structural_checks",
    ):
        raise AssertionError("higher-stage claims are inflated")

    retention = exact_list(document["retention_no_delete"], "retention_no_delete")
    if len(retention) != len(RETENTION_SURFACES):
        raise AssertionError("retention table row count differs")
    for index, (row_value, surface) in enumerate(
        zip(retention, RETENTION_SURFACES, strict=True)
    ):
        row = exact_dict(
            row_value,
            (
                "surface",
                "disposition",
                "deletion_authorized",
                "migration_executed",
                "reason",
            ),
            f"retention_no_delete[{index}]",
        )
        if exact_string(row["surface"], f"retention_no_delete[{index}].surface") != (
            surface
        ):
            raise AssertionError(f"retention_no_delete[{index}] surface differs")
        if row["disposition"] != "retain_in_place":
            raise AssertionError(f"retention_no_delete[{index}] disposition differs")
        if (
            exact_bool(
                row["deletion_authorized"],
                f"retention_no_delete[{index}].deletion_authorized",
            )
            is not False
        ):
            raise AssertionError(f"retention_no_delete[{index}] permits deletion")
        if (
            exact_bool(
                row["migration_executed"],
                f"retention_no_delete[{index}].migration_executed",
            )
            is not False
        ):
            raise AssertionError(f"retention_no_delete[{index}] records migration")
        if row["reason"] != RETENTION_REASON:
            raise AssertionError(f"retention_no_delete[{index}] reason differs")

    unmet = exact_list(document["unmet_success_conditions"], "unmet_success_conditions")
    if len(unmet) != len(UNMET_SUCCESS_CONDITIONS):
        raise AssertionError("unmet success condition count differs")
    for index, (row_value, expected) in enumerate(
        zip(unmet, UNMET_SUCCESS_CONDITIONS, strict=True)
    ):
        row = exact_dict(
            row_value,
            ("condition", "status"),
            f"unmet_success_conditions[{index}]",
        )
        if tuple(row.values()) != expected:
            raise AssertionError(f"unmet_success_conditions[{index}] differs")

    edges = exact_list(document["forbidden_stage_edges"], "forbidden_stage_edges")
    if len(edges) != len(FORBIDDEN_EDGES):
        raise AssertionError("forbidden stage edge count differs")
    for index, (row_value, expected) in enumerate(
        zip(edges, FORBIDDEN_EDGES, strict=True)
    ):
        row = exact_dict(
            row_value,
            ("from", "to"),
            f"forbidden_stage_edges[{index}]",
        )
        if tuple(row.values()) != expected:
            raise AssertionError(f"forbidden_stage_edges[{index}] differs")
    assert_string_array(
        document["forbidden_actions"], FORBIDDEN_ACTIONS, "forbidden_actions"
    )
    assert_string_array(
        document["forbidden_results"], FORBIDDEN_RESULTS, "forbidden_results"
    )

    if document["decision"] != "DO_NOT_RELEASE_OR_PROMOTE":
        raise AssertionError("terminal decision differs")
    if document["terminal_state"] != "STOP":
        raise AssertionError("terminal state differs")
    if document["claim_ceiling"] != "structural-terminal-closeout-only":
        raise AssertionError("claim ceiling differs")
    assert_no_aggregate_confidence_key(document)
    return document


class ARTerminalDecisionV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw_artifact = ARTIFACT.read_bytes()
        cls.document = parse_json_document(cls.raw_artifact)

    def git(self, *arguments: str) -> str:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    def git_bytes(self, *arguments: str) -> bytes:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        return completed.stdout

    def assert_git_object_metadata(
        self,
        commit: str,
        tree: str,
        record: dict,
        *,
        expected_object_size: int | None = None,
    ) -> None:
        path = record["path"]
        self.assertEqual(tree, self.git("rev-parse", f"{commit}^{{tree}}"))
        entry = self.git("ls-tree", commit, "--", path)
        mode, object_type, blob, resolved_path = entry.split(maxsplit=3)
        self.assertEqual("100644", mode)
        self.assertEqual("blob", object_type)
        self.assertEqual(record["blob"], blob)
        self.assertEqual(path, resolved_path)
        self.assertEqual("blob", self.git("cat-file", "-t", blob))
        object_size = int(self.git("cat-file", "-s", blob))
        self.assertGreater(object_size, 0)
        if expected_object_size is not None:
            self.assertEqual(expected_object_size, object_size)

    def assert_non_e0_historical_sha256(self, commit: str, record: dict) -> None:
        path = record["path"]
        self.assertNotIn(path, E0_PATHS)
        self.assertEqual(
            record["sha256"],
            hashlib.sha256(self.git_bytes("show", f"{commit}:{path}")).hexdigest(),
        )

    def assert_mutation_rejected(self, mutation) -> None:
        changed = copy.deepcopy(self.document)
        mutation(changed)
        with self.assertRaises(AssertionError):
            validate_document(changed)

    def test_artifact_is_closed_ordered_typed_and_exact(self) -> None:
        self.assertTrue(self.raw_artifact.endswith(b"\n"))
        validate_document(self.document)

    def test_git_custody_is_historical_and_e0_is_metadata_only(self) -> None:
        authority = self.document["authority_custody"]
        for record in authority["files"]:
            self.assert_git_object_metadata(
                authority["commit"],
                authority["tree"],
                record,
            )
            self.assert_non_e0_historical_sha256(authority["commit"], record)
        e0 = self.document["e0_terminal_authority"]
        for record, object_size in zip(e0["files"], E0_OBJECT_SIZES, strict=True):
            self.assert_git_object_metadata(
                e0["commit"],
                e0["tree"],
                record,
                expected_object_size=object_size,
            )

    def test_structural_result_is_bound_historical_structural_evidence(self) -> None:
        structural = self.document["package_structural_result"]
        result = assert_release_result_structure(structural["result"])
        canonical_stdout = json.dumps(result, sort_keys=True).encode("utf-8") + b"\n"
        self.assertEqual(
            EXPECTED_RELEASE_STDOUT_SHA256,
            hashlib.sha256(canonical_stdout).hexdigest(),
        )
        self.assertEqual(EXPECTED_RELEASE_STDOUT_SHA256, structural["stdout_sha256"])
        self.assertEqual(
            {
                "commit": EXPECTED_COMMIT,
                "tree": EXPECTED_TREE,
                "validation_input_digest": (
                    "sha256:33bc963d170b5be3a3000bcef39b64f429e45565372736dac27b6d8be252994f"
                ),
            },
            result["candidate"],
        )
        self.assertEqual(1, structural["executed_check_count"])
        self.assertEqual(structural["executed_check_count"], len(result["checks"]))
        check = result["checks"][0]
        self.assertEqual("package-structure", check["id"])
        self.assertEqual("passed", check["status"])
        self.assertEqual("structural", check["maximum_claim"])
        self.assertEqual(
            "sha256:33bc963d170b5be3a3000bcef39b64f429e45565372736dac27b6d8be252994f",
            check["observations"]["validation_input_digest"],
        )
        self.assertEqual(
            "sha256:376fa7f43a052658319979aa8200e82006dd61235d345cb8e5b3be94f5fbf1b3",
            check["observations"]["package_set_digest"],
        )
        self.assertEqual(
            check["observations"]["package_set_digest"],
            result["package_set"]["aggregate_digest"],
        )

    def test_claims_retention_and_terminal_boundaries_are_noninflating(self) -> None:
        claims = self.document["claim_vector"]
        self.assertEqual(
            {
                "foundation_currentness",
                "release_identity",
                "executed_structural_checks",
            },
            {key for key, state in claims.items() if state.startswith("observed_")},
        )
        self.assertTrue(
            all(
                row["disposition"] == "retain_in_place"
                and row["deletion_authorized"] is False
                and row["migration_executed"] is False
                for row in self.document["retention_no_delete"]
            )
        )
        self.assertEqual(
            FORBIDDEN_EDGES,
            tuple(
                (edge["from"], edge["to"])
                for edge in self.document["forbidden_stage_edges"]
            ),
        )
        self.assertEqual(FORBIDDEN_ACTIONS, tuple(self.document["forbidden_actions"]))
        self.assertEqual(FORBIDDEN_RESULTS, tuple(self.document["forbidden_results"]))

    def test_raw_json_rejects_duplicate_keys_and_nonfinite_constants(self) -> None:
        duplicate_samples = (
            '{"schema_version":"first","schema_version":"second"}',
            (
                '{"claim_vector":{"foundation_currentness":"first",'
                '"foundation_currentness":"second"}}'
            ),
        )
        for raw in duplicate_samples:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_json_document(raw)

        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant), self.assertRaises(ValueError):
                parse_json_document(f'{{"value":{constant}}}')

    def test_claim_vector_shape_mutation_reds(self) -> None:
        def remove_claim(document) -> None:
            document["claim_vector"].pop("archive_safety")

        def add_claim(document) -> None:
            document["claim_vector"]["future_claim"] = "unobserved"

        def reorder_claims(document) -> None:
            claims = document["claim_vector"]
            document["claim_vector"] = {
                key: claims[key] for key in reversed(tuple(claims))
            }

        def empty_claims(document) -> None:
            document["claim_vector"] = {}

        mutations = {
            "missing_claim": remove_claim,
            "extra_claim": add_claim,
            "reordered_claims": reorder_claims,
            "empty_claims": empty_claims,
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                self.assert_mutation_rejected(mutation)

    def test_null_scalar_container_and_type_mutation_reds(self) -> None:
        mutations = {
            "null_candidate": lambda document: document.__setitem__("candidate", None),
            "scalar_claim_vector": lambda document: document.__setitem__(
                "claim_vector", "unobserved"
            ),
            "container_for_actions": lambda document: document.__setitem__(
                "forbidden_actions", {}
            ),
            "container_for_decision": lambda document: document.__setitem__(
                "decision", []
            ),
            "null_claim_value": lambda document: document["claim_vector"].__setitem__(
                "archive_safety", None
            ),
            "container_for_result": lambda document: document[
                "package_structural_result"
            ].__setitem__("result", []),
            "bool_as_int": lambda document: document[
                "package_structural_result"
            ].__setitem__("executed_check_count", True),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                self.assert_mutation_rejected(mutation)

    def test_terminal_e0_and_claim_inflation_mutation_reds(self) -> None:
        mutations = {
            "e0_fail_to_pass": lambda document: document[
                "e0_terminal_authority"
            ].__setitem__("status", "pass"),
            "e0_scope_drift": lambda document: document[
                "e0_terminal_authority"
            ].__setitem__("inspection_scope", "content_inspected"),
            "blocked_to_observed": lambda document: document[
                "claim_vector"
            ].__setitem__("activation_abstention", "observed"),
            "source_only_to_observed": lambda document: document[
                "claim_vector"
            ].__setitem__("protocol_currentness", "observed"),
            "blocked_to_pass": lambda document: document["claim_vector"].__setitem__(
                "field_usefulness", "pass"
            ),
            "skipped_claim": lambda document: document["claim_vector"].__setitem__(
                "isolated_advice_value", "skipped"
            ),
            "undefined_claim": lambda document: document["claim_vector"].__setitem__(
                "protocol_currentness", "undefined"
            ),
            "nested_aggregate_confidence": lambda document: document[
                "package_structural_result"
            ]["result"]["claim_states"].__setitem__("aggregate_confidence", 0.99),
            "structural_to_behavioral": lambda document: document[
                "package_structural_result"
            ]["result"]["checks"][0].__setitem__("maximum_claim", "behavioral"),
            "terminal_stop_drift": lambda document: document.__setitem__(
                "terminal_state", "PAUSED"
            ),
            "release_decision": lambda document: document.__setitem__(
                "decision", "RELEASE"
            ),
            "aggregate_confidence": lambda document: document.__setitem__(
                "aggregate_confidence", 0.99
            ),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                self.assert_mutation_rejected(mutation)

    def test_retention_action_edge_and_array_mutation_reds(self) -> None:
        def remove_retention(document) -> None:
            document["retention_no_delete"].pop()

        def permit_deletion(document) -> None:
            document["retention_no_delete"][0]["deletion_authorized"] = True

        def remove_retry(document) -> None:
            document["forbidden_actions"].remove("retry")

        def remove_h6_action(document) -> None:
            document["forbidden_actions"].remove("h6_execution")

        def remove_h6_edge(document) -> None:
            document["forbidden_stage_edges"].remove({"from": "AR", "to": "H6"})

        def add_unbounded_action(document) -> None:
            document["forbidden_actions"].append("unbounded_execution")

        def add_unbounded_edge(document) -> None:
            document["forbidden_stage_edges"].append({"from": "AR", "to": "H7"})

        mutations = {
            "removed_retention": remove_retention,
            "deletion_enabled": permit_deletion,
            "retry_removed": remove_retry,
            "h6_action_removed": remove_h6_action,
            "h6_edge_removed": remove_h6_edge,
            "actions_empty": lambda document: document.__setitem__(
                "forbidden_actions", []
            ),
            "edges_empty": lambda document: document.__setitem__(
                "forbidden_stage_edges", []
            ),
            "retention_empty": lambda document: document.__setitem__(
                "retention_no_delete", []
            ),
            "actions_unbounded": add_unbounded_action,
            "edges_unbounded": add_unbounded_edge,
            "unmet_conditions_unbounded": lambda document: document[
                "unmet_success_conditions"
            ].append({"condition": "future", "status": "open"}),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                self.assert_mutation_rejected(mutation)

    def test_key_order_and_hash_mutation_reds(self) -> None:
        mutations = {
            "key_addition": lambda document: document["candidate"].__setitem__(
                "unexpected", "forbidden"
            ),
            "hash_drift": lambda document: document["authority_custody"]["files"][
                0
            ].__setitem__("sha256", "0" * 64),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                self.assert_mutation_rejected(mutation)

        reversed_document = dict(reversed(tuple(self.document.items())))
        with self.assertRaises(AssertionError):
            validate_document(reversed_document)


if __name__ == "__main__":
    unittest.main()
