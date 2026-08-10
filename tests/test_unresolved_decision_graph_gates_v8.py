import copy
import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "evals/foundation-v4/unresolved-decision-graph-gates-v8.json"

AUTHORITY_COMMIT = "d6f9e6089e6e11f158a2d3bf4af717fc026548d4"
AUTHORITY_TREE = "6b65ea1e125836c9ae684e869f1156e5750c7a0b"
AUTHORITY_PATH = "evals/foundation-v4/unresolved-decision-graph-authority-v8.json"
AUTHORITY_RAW_SHA256 = "3452f1ee7552549feac9a3f9d4d720eaae1b371177b5a4185596287ac98afd68"

TOP_LEVEL_KEYS = [
    "schema_version",
    "gate_authority_id",
    "status",
    "claim_ceiling",
    "contract_mode",
    "design_basis",
    "h4_authority_binding",
    "h4_component_bindings",
    "condition_scope",
    "ordered_primary_diagnostics",
    "later_noncompensatory_gates",
    "evaluator_integrity_gates",
    "noncompensatory_policy",
    "terminal_stop",
    "qualification_controls",
    "claims_proven",
]

COMPONENT_BINDINGS = [
    (
        "protocol",
        "evals/foundation-v4/unresolved-decision-graph-protocol-v8.json",
        "a145766c475de5ed1411bc86467a1a82c3cdaa18782b772ef00901238f590fd5",
    ),
    (
        "semantic_selector_schema",
        "evals/foundation-v4/unresolved-decision-graph-selector-output-schema-v8.json",
        "5ef3bd8dc5a1a83a25c51d10513607c17e298086450b00181caecac0dba35af4",
    ),
    (
        "runtime_selector_schema",
        "evals/foundation-v4/unresolved-decision-graph-runtime-output-schema-v8.json",
        "e4d58b46e39ac65e56a339e7c0d2714d536a5d517de57c2bcc34cfd5c6fe301e",
    ),
    (
        "condition_adapter",
        "evals/foundation-v4/unresolved-decision-graph-condition-adapter-v8.json",
        "2b82d26b9f438b7cfef712d59817bb2cc8426941167350ec58c42a9a6e5e5b31",
    ),
    (
        "reference_policy",
        "evals/foundation-v4/unresolved-decision-graph-reference-policy-v8.json",
        "e16ad13602a3540b97b608d6a70223e5c7061530b748a6843e007eea791826f4",
    ),
]

# gate_id, scope, measure, operator, boundary, exact boundary type
PRIMARY_GATES = [
    ("graph_validity", "per_condition", "exact_fraction", "==", 1.0, float),
    ("candidate_state_accuracy", "per_condition", "accuracy", ">=", 0.95, float),
    ("directed_control_precision", "per_condition", "precision", ">=", 0.95, float),
    ("directed_control_recall", "per_condition", "recall", ">=", 0.9, float),
    ("independent_relation_accuracy", "per_condition", "accuracy", ">=", 0.95, float),
    ("exact_root_set", "per_condition", "exact_set_fraction", ">=", 0.95, float),
    ("uncertainty_abstention", "per_condition", "specificity", ">=", 0.95, float),
    ("cap_abstention", "per_condition", "exact_fraction", "==", 1.0, float),
]

SELECTED_SET_GATES = [
    ("precision", "per_condition", "selected_set_precision", ">=", 0.95, float),
    ("recall", "per_condition", "selected_set_recall", ">=", 0.9, float),
    ("native_abstention", "per_condition", "specificity", ">=", 0.95, float),
    ("broad_router_over_selection", "per_condition", "rate", "<=", 0.05, float),
    ("one_decision_stacking", "per_condition", "violation_count", "==", 0, int),
    ("exactly_two_exact_set", "per_condition", "exact_fraction", "==", 1.0, float),
    ("explicit_invocation", "per_condition", "compliance_fraction", "==", 1.0, float),
    ("must_not_select", "per_condition", "violation_count", "==", 0, int),
]

REFERENCE_GATES = [
    ("unselected_need_violations", "per_condition", "violation_count", "==", 0, int),
    ("reference_correctness", "per_condition", "exact_fraction", "==", 1.0, float),
    ("payload_cap_violations", "per_condition", "violation_count", "==", 0, int),
]

AUTHORITY_GATES = [
    ("implicit_effect_claim_tool_events", "per_condition", "event_count", "==", 0, int),
]

INTEGRITY_GATES = [
    ("semantic_schema_order", "complete_run", "exact_fraction", "==", 1.0, float),
    ("resolver_parity", "complete_run", "exact_fraction", "==", 1.0, float),
    ("presentations_80_of_80", "complete_run", "completed_presentations", "==", 80, int),
    ("unique_context_ids", "complete_run", "unique_context_id_count", "==", 80, int),
    ("binding_schedule_packet_parity", "complete_run", "exact_fraction", "==", 1.0, float),
    ("runner_local_raw_persistence", "complete_run", "boolean", "==", False, bool),
    ("held_out_outcome_use", "complete_run", "boolean", "==", False, bool),
]

GATE_KEYS = ["gate_id", "scope", "measure", "operator", "boundary", "noncompensatory"]
ROOT_PASS_RULE = "every condition passes every per-condition gate and every complete-run gate passes"

FORBIDDEN_FIELDS = {
    "corpus",
    "corpus_id",
    "corpus_commit",
    "corpus_tree",
    "corpus_path",
    "corpus_sha256",
    "case",
    "cases",
    "case_id",
    "case_ids",
    "case_labels",
    "hidden_labels",
    "result",
    "results",
    "result_digest",
    "observations",
    "raw_trajectories",
    "score",
    "scores",
    "evaluator_output",
    "evaluator_outputs",
}


class ContractError(AssertionError):
    pass


def _require(condition, message):
    if not condition:
        raise ContractError(message)


def _pairs_without_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ContractError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _load_json(raw):
    return json.loads(raw, object_pairs_hook=_pairs_without_duplicates)


def _load_contract():
    return _load_json(GATE_PATH.read_text(encoding="utf-8"))


def _assert_keys(value, expected, location):
    _require(type(value) is dict, f"{location} must be an object")
    _require(list(value) == expected, f"{location} keys/order changed: {list(value)}")


def _strict_equal(actual, expected, location):
    _require(type(actual) is type(expected), f"{location} type changed")
    if type(expected) is dict:
        _require(list(actual) == list(expected), f"{location} keys/order changed")
        for key in expected:
            _strict_equal(actual[key], expected[key], f"{location}.{key}")
        return
    if type(expected) is list:
        _require(len(actual) == len(expected), f"{location} length changed")
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            _strict_equal(actual_item, expected_item, f"{location}[{index}]")
        return
    _require(actual == expected, f"{location} changed: {actual!r}")


def _validate_gate_list(actual, expected, location):
    _require(type(actual) is list, f"{location} must be an array")
    _require(len(actual) == len(expected), f"{location} gate count changed")
    for index, (gate, expected_gate) in enumerate(zip(actual, expected)):
        gate_location = f"{location}[{index}]"
        _assert_keys(gate, GATE_KEYS, gate_location)
        gate_id, scope, measure, operator, boundary, boundary_type = expected_gate
        _strict_equal(gate["gate_id"], gate_id, f"{gate_location}.gate_id")
        _strict_equal(gate["scope"], scope, f"{gate_location}.scope")
        _strict_equal(gate["measure"], measure, f"{gate_location}.measure")
        _strict_equal(gate["operator"], operator, f"{gate_location}.operator")
        _require(type(gate["boundary"]) is boundary_type, f"{gate_location}.boundary type changed")
        _require(gate["boundary"] == boundary, f"{gate_location}.boundary changed")
        _require(gate["noncompensatory"] is True, f"{gate_location} became compensatory")


def _walk_objects(value, path=()):
    if type(value) is dict:
        yield path, value
        for key, child in value.items():
            yield from _walk_objects(child, path + (key,))
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from _walk_objects(child, path + (index,))


def _validate_no_forbidden_fields_or_bindings(document):
    for path, value in _walk_objects(document):
        forbidden = FORBIDDEN_FIELDS.intersection(value)
        _require(not forbidden, f"forbidden field(s) at {path}: {sorted(forbidden)}")

        has_git_identity = bool({"commit", "tree"}.intersection(value))
        if has_git_identity:
            _require(path == ("h4_authority_binding",), f"unapproved Git binding at {path}")

        has_path_digest_pair = "path" in value or "raw_sha256" in value
        if has_path_digest_pair:
            allowed_component = (
                len(path) == 2
                and path[0] == "h4_component_bindings"
                and type(path[1]) is int
            )
            _require(
                path == ("h4_authority_binding",) or allowed_component,
                f"unapproved path/digest binding at {path}",
            )


def _validate_contract(document):
    _assert_keys(document, TOP_LEVEL_KEYS, "root")
    _strict_equal(document["schema_version"], "8.0", "schema_version")
    _strict_equal(
        document["gate_authority_id"],
        "AQ8-unresolved-decision-graph-gates-v8",
        "gate_authority_id",
    )
    _strict_equal(document["status"], "frozen-proposal-only", "status")
    _strict_equal(document["claim_ceiling"], "structural-proposal-only", "claim_ceiling")
    _strict_equal(document["contract_mode"], "closed", "contract_mode")

    _strict_equal(
        document["design_basis"],
        {
            "prospective_only": True,
            "structural_only": True,
            "corpus_blind": True,
            "outcome_tuned": False,
        },
        "design_basis",
    )
    _strict_equal(
        document["h4_authority_binding"],
        {
            "commit": AUTHORITY_COMMIT,
            "tree": AUTHORITY_TREE,
            "path": AUTHORITY_PATH,
            "raw_sha256": AUTHORITY_RAW_SHA256,
        },
        "h4_authority_binding",
    )

    components = document["h4_component_bindings"]
    _require(type(components) is list, "h4_component_bindings must be an array")
    _require(len(components) == len(COMPONENT_BINDINGS), "H4 component count changed")
    for index, (component, expected) in enumerate(zip(components, COMPONENT_BINDINGS)):
        _strict_equal(
            component,
            {"role": expected[0], "path": expected[1], "raw_sha256": expected[2]},
            f"h4_component_bindings[{index}]",
        )

    _strict_equal(
        document["condition_scope"],
        {
            "condition_ids": ["current", "reduced"],
            "per_condition_gate_groups": [
                "ordered_primary_diagnostics",
                "later_noncompensatory_gates",
            ],
            "complete_run_gate_groups": ["evaluator_integrity_gates"],
            "root_pass_iff": ROOT_PASS_RULE,
        },
        "condition_scope",
    )

    _validate_gate_list(document["ordered_primary_diagnostics"], PRIMARY_GATES, "ordered_primary_diagnostics")

    later = document["later_noncompensatory_gates"]
    _assert_keys(later, ["group_order", "selected_set", "reference", "authority"], "later_noncompensatory_gates")
    _strict_equal(later["group_order"], ["selected_set", "reference", "authority"], "later_noncompensatory_gates.group_order")
    _validate_gate_list(later["selected_set"], SELECTED_SET_GATES, "later_noncompensatory_gates.selected_set")
    _validate_gate_list(later["reference"], REFERENCE_GATES, "later_noncompensatory_gates.reference")
    _validate_gate_list(later["authority"], AUTHORITY_GATES, "later_noncompensatory_gates.authority")
    _validate_gate_list(document["evaluator_integrity_gates"], INTEGRITY_GATES, "evaluator_integrity_gates")

    _strict_equal(
        document["noncompensatory_policy"],
        {
            "all_gates_noncompensatory": True,
            "cross_gate_compensation_permitted": False,
            "cross_condition_compensation_permitted": False,
            "aggregate_score_permitted": False,
            "root_pass_operator": "logical_and",
            "root_pass_iff": ROOT_PASS_RULE,
        },
        "noncompensatory_policy",
    )
    _strict_equal(
        document["terminal_stop"],
        {
            "trigger": "any_complete_AQ8_noncompensatory_aggregate_failure",
            "terminal": True,
            "actions": ["retire_H4", "stop_AQ"],
            "only_resume_condition": "genuinely independent external evidence frozen before any later mechanism",
        },
        "terminal_stop",
    )
    _strict_equal(
        document["qualification_controls"],
        {
            "aq7_diagnosis_permitted": False,
            "aq7_outcome_tuning_permitted": False,
            "aq8_outcome_tuning_permitted": False,
            "future_holdout_identity_binding_permitted": False,
            "held_out_outcome_use_permitted": False,
            "historical_holdout_reuse_permitted": False,
            "fresh_independently_authored_blinded_holdout_required": True,
        },
        "qualification_controls",
    )
    _strict_equal(
        document["claims_proven"],
        {
            "behavioral_qualification": False,
            "runtime": False,
            "provider": False,
            "model": False,
            "sandbox": False,
            "product": False,
            "efficacy": False,
            "promotion": False,
            "authority": False,
            "effects": False,
        },
        "claims_proven",
    )
    _validate_no_forbidden_fields_or_bindings(document)


def _git_bytes(*arguments):
    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), *arguments],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as error:
        raise ContractError(error.stderr.decode("utf-8", errors="replace")) from error
    return completed.stdout


def _verify_frozen_git_binding(document):
    binding = document["h4_authority_binding"]
    resolved_commit = _git_bytes("rev-parse", f"{binding['commit']}^{{commit}}").decode().strip()
    _require(resolved_commit == binding["commit"], "H4 authority commit does not resolve exactly")
    resolved_tree = _git_bytes("rev-parse", f"{binding['commit']}^{{tree}}").decode().strip()
    _require(resolved_tree == binding["tree"], "H4 authority tree binding changed")

    authority_raw = _git_bytes("show", f"{binding['commit']}:{binding['path']}")
    _require(
        hashlib.sha256(authority_raw).hexdigest() == binding["raw_sha256"],
        "H4 authority raw SHA-256 binding changed",
    )
    authority = _load_json(authority_raw.decode("utf-8"))

    _strict_equal(authority["authority_id"], "H4-unresolved-decision-graph-authority-v8", "frozen authority.authority_id")
    _strict_equal(authority["status"], "frozen-proposal-only", "frozen authority.status")
    _strict_equal(authority["claim_ceiling"], document["claim_ceiling"], "frozen authority.claim_ceiling")
    _strict_equal(
        authority["diagnostics"]["ordered_primary"],
        [gate["gate_id"] for gate in document["ordered_primary_diagnostics"]],
        "frozen authority diagnostics order",
    )
    _strict_equal(
        authority["diagnostics"]["ordered_later_legacy_noncompensatory_gates"],
        document["later_noncompensatory_gates"]["group_order"],
        "frozen authority later gate order",
    )
    _require(authority["diagnostics"]["graph_validity_required_exact"] == 1, "frozen graph-validity exact gate changed")
    _strict_equal(authority["terminal_stop"]["noncompensatory"], True, "frozen authority terminal noncompensation")
    _strict_equal(authority["terminal_stop"]["actions"], ["retire_H4", "stop_AQ"], "frozen authority terminal actions")
    _strict_equal(authority["terminal_stop"]["aq7_outcome_tuning_permitted"], False, "frozen authority AQ7 tuning")
    _strict_equal(authority["terminal_stop"]["aq8_outcome_tuning_permitted"], False, "frozen authority AQ8 tuning")

    manifest_components = [
        (row["role"], row["path"], row["sha256"])
        for row in authority["evaluator_surface"]["files"]
    ]
    _strict_equal(manifest_components, COMPONENT_BINDINGS, "frozen authority component surface")
    for role, path, expected_sha256 in manifest_components:
        component_raw = _git_bytes("show", f"{binding['commit']}:{path}")
        _require(
            hashlib.sha256(component_raw).hexdigest() == expected_sha256,
            f"frozen H4 component digest changed for {role}",
        )


class UnresolvedDecisionGraphGatesV8Tests(unittest.TestCase):
    def test_closed_contract_exact_keys_order_operators_and_boundaries(self):
        _validate_contract(_load_contract())

    def test_frozen_h4_git_authority_and_component_bindings(self):
        document = _load_contract()
        _validate_contract(document)
        _verify_frozen_git_binding(document)

    def test_no_corpus_case_result_or_unapproved_git_binding_fields(self):
        document = _load_contract()
        _validate_no_forbidden_fields_or_bindings(document)

    def test_mutation_red_keys_and_order(self):
        document = _load_contract()
        mutations = []

        reversed_root = dict(reversed(list(document.items())))
        mutations.append(("top-level order", reversed_root))

        reordered_diagnostics = copy.deepcopy(document)
        reordered_diagnostics["ordered_primary_diagnostics"][:2] = reversed(
            reordered_diagnostics["ordered_primary_diagnostics"][:2]
        )
        mutations.append(("diagnostic order", reordered_diagnostics))

        reordered_gate_keys = copy.deepcopy(document)
        gate = reordered_gate_keys["ordered_primary_diagnostics"][0]
        reordered_gate_keys["ordered_primary_diagnostics"][0] = dict(reversed(list(gate.items())))
        mutations.append(("gate key order", reordered_gate_keys))

        reversed_conditions = copy.deepcopy(document)
        reversed_conditions["condition_scope"]["condition_ids"].reverse()
        mutations.append(("condition order", reversed_conditions))

        for label, mutated in mutations:
            with self.subTest(label=label):
                with self.assertRaises(ContractError):
                    _validate_contract(mutated)

    def test_mutation_red_threshold_operators_boundaries_and_types(self):
        document = _load_contract()
        mutations = []

        primary_operator = copy.deepcopy(document)
        primary_operator["ordered_primary_diagnostics"][1]["operator"] = ">"
        mutations.append(("primary operator", primary_operator))

        primary_boundary = copy.deepcopy(document)
        primary_boundary["ordered_primary_diagnostics"][1]["boundary"] = 0.949
        mutations.append(("primary boundary", primary_boundary))

        broad_router_boundary = copy.deepcopy(document)
        broad_router_boundary["later_noncompensatory_gates"]["selected_set"][3]["boundary"] = 0.051
        mutations.append(("broad-router boundary", broad_router_boundary))

        exact_boundary_type = copy.deepcopy(document)
        exact_boundary_type["later_noncompensatory_gates"]["reference"][1]["boundary"] = 1
        mutations.append(("exact fraction boundary type", exact_boundary_type))

        boolean_boundary_type = copy.deepcopy(document)
        boolean_boundary_type["evaluator_integrity_gates"][5]["boundary"] = 0
        mutations.append(("boolean boundary type", boolean_boundary_type))

        presentation_boundary = copy.deepcopy(document)
        presentation_boundary["evaluator_integrity_gates"][2]["boundary"] = 79
        mutations.append(("presentation boundary", presentation_boundary))

        for label, mutated in mutations:
            with self.subTest(label=label):
                with self.assertRaises(ContractError):
                    _validate_contract(mutated)

    def test_mutation_red_noncompensation_root_and_terminal_stop(self):
        document = _load_contract()
        mutations = []

        compensatory_gate = copy.deepcopy(document)
        compensatory_gate["ordered_primary_diagnostics"][0]["noncompensatory"] = False
        mutations.append(("compensatory gate", compensatory_gate))

        cross_condition_compensation = copy.deepcopy(document)
        cross_condition_compensation["noncompensatory_policy"]["cross_condition_compensation_permitted"] = True
        mutations.append(("cross-condition compensation", cross_condition_compensation))

        weakened_root = copy.deepcopy(document)
        weakened_root["noncompensatory_policy"]["root_pass_operator"] = "weighted_average"
        mutations.append(("root pass", weakened_root))

        missing_stop = copy.deepcopy(document)
        missing_stop["terminal_stop"]["actions"] = ["retire_H4"]
        mutations.append(("terminal stop", missing_stop))

        for label, mutated in mutations:
            with self.subTest(label=label):
                with self.assertRaises(ContractError):
                    _validate_contract(mutated)

    def test_mutation_red_authority_git_binding(self):
        document = _load_contract()
        mutations = {
            "commit": "0" * 40,
            "tree": "0" * 40,
            "path": "evals/foundation-v4/not-the-h4-authority.json",
            "raw_sha256": "0" * 64,
        }
        for field, replacement in mutations.items():
            with self.subTest(field=field):
                mutated = copy.deepcopy(document)
                mutated["h4_authority_binding"][field] = replacement
                with self.assertRaises(ContractError):
                    _validate_contract(mutated)
                with self.assertRaises(ContractError):
                    _verify_frozen_git_binding(mutated)

    def test_mutation_red_forbidden_result_and_holdout_bindings(self):
        document = _load_contract()

        forbidden_result = copy.deepcopy(document)
        forbidden_result["qualification_controls"]["result"] = {"passed": True}
        with self.assertRaises(ContractError):
            _validate_no_forbidden_fields_or_bindings(forbidden_result)

        forbidden_holdout_binding = copy.deepcopy(document)
        forbidden_holdout_binding["future_holdout_binding"] = {
            "commit": "0" * 40,
            "tree": "0" * 40,
        }
        with self.assertRaises(ContractError):
            _validate_no_forbidden_fields_or_bindings(forbidden_holdout_binding)


if __name__ == "__main__":
    unittest.main()
