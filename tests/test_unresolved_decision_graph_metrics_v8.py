import copy
import hashlib
import json
import operator
import subprocess
import unittest
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "evals/foundation-v4/unresolved-decision-graph-metrics-v8.json"

METRICS_RAW_SHA256 = "144a7b98ee7cdb852314a8e509a003a5c16dd588b3bf2727412051d3436659c7"
FORMULAS_CANONICAL_SHA256 = "d873a0ebc62a2f1b7e043bc2ec576424f2517ccbfb2a47ca20946f37050470df"
OBSERVATION_DOMAIN_CANONICAL_SHA256 = "c81da99700471d7c1ec99235421235b56cbb6582c6fed330c75efeeac0c9e518"
POLICIES_CANONICAL_SHA256 = "ba4f4bd9ca0d10892720dd5b1fc2791eb57829b8e599c778c319d9a3da7f941a"

H4_COMMIT = "d6f9e6089e6e11f158a2d3bf4af717fc026548d4"
H4_TREE = "6b65ea1e125836c9ae684e869f1156e5750c7a0b"
H4_PATH = "evals/foundation-v4/unresolved-decision-graph-authority-v8.json"
H4_RAW_SHA256 = "3452f1ee7552549feac9a3f9d4d720eaae1b371177b5a4185596287ac98afd68"
H4_PROTOCOL_PATH = "evals/foundation-v4/unresolved-decision-graph-protocol-v8.json"

GATE_COMMIT = "953651815e76c56f0cf8d23d9eae9ef6a480726f"
GATE_TREE = "83c5aa7ecd3930733071e509ba56d307ae49aa59"
GATE_PATH = "evals/foundation-v4/unresolved-decision-graph-gates-v8.json"
GATE_RAW_SHA256 = "d17c6de19b456100a0c930d9cbe898d123dab882fe924c92226f9962fc7784d8"

TOP_LEVEL_KEYS = [
    "schema_version",
    "formula_authority_id",
    "status",
    "claim_ceiling",
    "contract_mode",
    "design_basis",
    "authority_bindings",
    "semantic_authority",
    "observation_domain",
    "malformed_and_undefined_policy",
    "formula_order",
    "gate_formulas",
    "aggregation_and_decision",
    "qualification_controls",
    "claims_proven",
]

FORMULA_KEYS = [
    "gate_id",
    "gate_group",
    "scope",
    "semantic_contract",
    "eligibility",
    "atomic_unit",
    "counts",
    "calculation",
    "denominator",
    "aggregation",
    "parsed_row_rule",
    "malformed_row_rule",
    "undefined_rule",
    "operator",
    "boundary",
    "noncompensatory",
]

CALCULATION_KEYS = ["value_kind", "expression"]
DENOMINATOR_KEYS = ["name", "definition", "must_be_positive", "fixed_value"]

FORMULA_ORDER = [
    "graph_validity",
    "candidate_state_accuracy",
    "directed_control_precision",
    "directed_control_recall",
    "independent_relation_accuracy",
    "exact_root_set",
    "uncertainty_abstention",
    "cap_abstention",
    "precision",
    "recall",
    "native_abstention",
    "broad_router_over_selection",
    "one_decision_stacking",
    "exactly_two_exact_set",
    "explicit_invocation",
    "must_not_select",
    "unselected_need_violations",
    "reference_correctness",
    "payload_cap_violations",
    "implicit_effect_claim_tool_events",
    "semantic_schema_order",
    "resolver_parity",
    "presentations_80_of_80",
    "unique_context_ids",
    "binding_schedule_packet_parity",
    "runner_local_raw_persistence",
    "held_out_outcome_use",
]

EXPECTED_GROUPS = [
    *(["ordered_primary_diagnostics"] * 8),
    *(["selected_set"] * 8),
    *(["reference"] * 3),
    "authority",
    *(["evaluator_integrity_gates"] * 7),
]

EXPECTED_VALUE_KINDS = [
    "ratio",
    "ratio",
    "ratio",
    "ratio",
    "ratio",
    "ratio",
    "ratio",
    "ratio",
    "ratio",
    "ratio",
    "ratio",
    "ratio",
    "count",
    "ratio",
    "ratio",
    "count",
    "count",
    "ratio",
    "count",
    "count",
    "ratio",
    "ratio",
    "count",
    "count",
    "ratio",
    "boolean",
    "boolean",
]

SEMANTIC_CONTRACT_KEYS = [
    "eligibility_universe",
    "atomic_unit",
    "count_algebra",
    "denominator_algebra",
    "value_domain",
    "aggregation_scope",
    "parsed_disposition",
    "malformed_disposition",
    "undefined_disposition",
    "decision_rule",
]
DECISION_RULE_KEYS = ["operator", "boundary"]


def _norm(eligibility, atomic, count, denominator, domain, aggregation, parsed, malformed, undefined, operator_text, boundary):
    return {
        "eligibility_universe": eligibility,
        "atomic_unit": atomic,
        "count_algebra": count,
        "denominator_algebra": denominator,
        "value_domain": domain,
        "aggregation_scope": aggregation,
        "parsed_disposition": parsed,
        "malformed_disposition": malformed,
        "undefined_disposition": undefined,
        "decision_rule": {"operator": operator_text, "boundary": boundary},
    }


# Independent exact normative projection. No whole-document or whole-formula
# digest participates in these field-by-field comparisons.
NORMATIVE_SEMANTICS = [
    ("graph_validity", _norm("expected_schedule_cells_per_condition", "required_schedule_cell", "exact_if_parsed_graph_passes_compatibility_acyclicity_closure", "fixed_40_required_cells", "exact_unit_ratio", "separate_condition_id_no_pooling", "credit_one_for_graph_status_valid_or_graph_uncertain", "credit_zero_retain_one_required_cell", "zero_denominator_value_0_and_gate_fails__fixed_denominator_absence_or_drift_fails", "==", 1.0)),
    ("candidate_state_accuracy", _norm("expected_schedule_cells_x_four_canonical_slot_rows", "required_cell_slot_state_row", "exact_slot_id_and_state_at_same_canonical_position", "fixed_160_required_slot_rows", "exact_unit_ratio", "separate_condition_id_no_pooling", "compare_four_rows_independently", "credit_zero_retain_four_required_slot_rows", "zero_denominator_value_0_and_gate_fails__fixed_denominator_absence_or_drift_fails", ">=", 0.95)),
    ("directed_control_precision", _norm("expected_schedule_cells_per_condition", "required_cell_controller_downstream_edge", "tp_expected_intersection_predicted__fp_predicted_minus_expected__fn_expected_minus_predicted", "tp_plus_fp_predicted_directed_edges_must_be_positive", "exact_unit_ratio", "separate_condition_id_no_pooling", "left_relation_maps_left_to_right__right_relation_maps_right_to_left", "predicted_edge_set_empty_expected_edges_are_fn", "zero_denominator_value_0_and_gate_fails", ">=", 0.95)),
    ("directed_control_recall", _norm("expected_directed_positive_edges_per_condition", "required_cell_controller_downstream_edge", "tp_expected_intersection_predicted__fp_predicted_minus_expected__fn_expected_minus_predicted", "tp_plus_fn_expected_directed_edges_must_be_positive", "exact_unit_ratio", "separate_condition_id_no_pooling", "left_relation_maps_left_to_right__right_relation_maps_right_to_left", "predicted_edge_set_empty_expected_edges_are_fn", "zero_denominator_value_0_and_gate_fails", ">=", 0.9)),
    ("independent_relation_accuracy", _norm("expected_schedule_cells_x_six_canonical_pair_rows", "required_cell_canonical_pair_binary_independence", "credit_iff_predicted_independent_equals_expected_independent", "fixed_240_required_pair_rows", "exact_unit_ratio", "separate_condition_id_no_pooling", "true_positive_and_true_negative_credit__false_positive_and_false_negative_error", "credit_zero_retain_six_required_pair_rows", "zero_denominator_value_0_and_gate_fails__fixed_denominator_absence_or_drift_fails", ">=", 0.95)),
    ("exact_root_set", _norm("expected_graph_status_valid_cells", "required_cell_ordered_root_set", "exact_ordered_root_set_equality", "count_expected_graph_status_valid_cells_must_be_positive", "exact_unit_ratio", "separate_condition_id_no_pooling", "independently_recompute_roots_before_exact_comparison", "credit_zero_retain_one_eligible_cell", "zero_denominator_value_0_and_gate_fails", ">=", 0.95)),
    ("uncertainty_abstention", _norm("expected_no_invocation_and_automatic_graph_uncertain_cells", "required_uncertainty_cell", "tn_exact_graph_uncertain_empty_selection__fp_other_or_malformed", "tn_plus_fp_predeclared_uncertainty_cells_must_be_positive", "exact_unit_ratio", "separate_condition_id_no_pooling", "credit_only_exact_uncertain_statuses_and_empty_selection", "add_one_fp_retain_one_opportunity", "zero_denominator_value_0_and_gate_fails", ">=", 0.95)),
    ("cap_abstention", _norm("expected_no_invocation_and_automatic_cap_exceeded_cells", "required_cap_cell", "exact_roots_cap_statuses_and_empty_selection", "count_predeclared_cap_cells_must_be_positive", "exact_unit_ratio", "separate_condition_id_no_pooling", "credit_only_exact_cap_telemetry_roots_and_empty_selection", "credit_zero_retain_one_eligible_cell", "zero_denominator_value_0_and_gate_fails", "==", 1.0)),
    ("precision", _norm("expected_schedule_cells_per_condition", "required_cell_selected_slot_edge", "tp_expected_intersection_predicted__fp_predicted_minus_expected__fn_expected_minus_predicted", "tp_plus_fp_predicted_selected_edges_must_be_positive", "exact_unit_ratio", "separate_condition_id_no_pooling", "use_only_independently_parent_derived_selected_slots", "predicted_selected_set_empty_expected_edges_are_fn", "zero_denominator_value_0_and_gate_fails", ">=", 0.95)),
    ("recall", _norm("expected_selected_slot_edges_per_condition", "required_cell_selected_slot_edge", "tp_expected_intersection_predicted__fp_predicted_minus_expected__fn_expected_minus_predicted", "tp_plus_fn_expected_selected_edges_must_be_positive", "exact_unit_ratio", "separate_condition_id_no_pooling", "use_only_independently_parent_derived_selected_slots", "predicted_selected_set_empty_expected_edges_are_fn", "zero_denominator_value_0_and_gate_fails", ">=", 0.9)),
    ("native_abstention", _norm("expected_valid_zero_root_automatic_empty_cells", "required_native_cell", "tn_exact_valid_automatic_empty__fp_other_or_malformed", "tn_plus_fp_predeclared_native_cells_must_be_positive", "exact_unit_ratio", "separate_condition_id_no_pooling", "credit_only_valid_automatic_empty_selection", "add_one_fp_retain_one_opportunity", "zero_denominator_value_0_and_gate_fails", ">=", 0.95)),
    ("broad_router_over_selection", _norm("expected_no_invocation_cells_excluding_selected_s0", "required_broad_topology_opportunity_cell", "one_violation_iff_predicted_selected_slots_contains_s0", "count_predeclared_broad_topology_opportunities_must_be_positive", "exact_unit_ratio", "separate_condition_id_no_pooling", "add_one_violation_iff_s0_selected", "add_one_violation_retain_one_opportunity", "zero_denominator_value_0_and_gate_fails", "<=", 0.05)),
    ("one_decision_stacking", _norm("expected_selected_slots_cardinality_one_cells", "required_one_decision_cell", "one_violation_iff_predicted_selected_slots_cardinality_gt_one", "none_raw_count", "exact_nonnegative_integer", "separate_condition_id_no_pooling", "at_most_one_stacking_violation_per_cell", "add_one_violation_sentinel_per_eligible_cell", "missing_fractional_or_negative_count_fails", "==", 0)),
    ("exactly_two_exact_set", _norm("expected_selected_slots_cardinality_two_cells", "required_two_decision_ordered_selected_set", "exact_ordered_selected_set_equality", "count_predeclared_exactly_two_cells_must_be_positive", "exact_unit_ratio", "separate_condition_id_no_pooling", "credit_only_exact_ordered_selected_set", "credit_zero_retain_one_eligible_cell", "zero_denominator_value_0_and_gate_fails", "==", 1.0)),
    ("explicit_invocation", _norm("expected_selection_status_exact_cells", "required_exact_invocation_cell", "exact_status_and_one_slot_selected_set_equality", "count_predeclared_exact_invocation_cells_must_be_positive", "exact_unit_ratio", "separate_condition_id_no_pooling", "credit_only_exact_parser_status_and_expected_one_slot", "credit_zero_retain_one_eligible_cell", "zero_denominator_value_0_and_gate_fails", "==", 1.0)),
    ("must_not_select", _norm("expected_complement_slot_edges", "required_cell_complement_slot_edge", "count_predicted_selected_edges_in_expected_complement", "none_raw_count", "exact_nonnegative_integer", "separate_condition_id_no_pooling", "add_one_violation_per_unexpected_selected_complement_slot", "add_one_violation_sentinel_per_required_cell", "missing_fractional_or_negative_count_fails", "==", 0)),
    ("unselected_need_violations", _norm("all_slot_rows_after_predicted_parent_selection", "required_cell_predicted_unselected_slot_need", "count_non_none_need_on_predicted_unselected_slot", "none_raw_count", "exact_nonnegative_integer", "separate_condition_id_no_pooling", "resolve_selection_before_counting_each_non_none_unselected_need", "add_one_violation_sentinel_per_required_cell", "missing_fractional_or_negative_count_fails", "==", 0)),
    ("reference_correctness", _norm("expected_schedule_cells_per_condition", "required_cell_complete_reference_result", "exact_needs_requests_uncertain_slots_and_resolution_equality", "fixed_40_required_cells", "exact_unit_ratio", "separate_condition_id_no_pooling", "independently_recompute_owner_requests_and_canonical_cover", "credit_zero_retain_one_required_cell", "zero_denominator_value_0_and_gate_fails__fixed_denominator_absence_or_drift_fails", "==", 1.0)),
    ("payload_cap_violations", _norm("expected_schedule_cells_after_predicted_reference_resolution", "required_cell_reference_resolution", "one_violation_iff_cap_exceeded_or_count_gt_three_or_tuple_length_gt_three", "none_raw_count", "exact_nonnegative_integer", "separate_condition_id_no_pooling", "at_most_one_payload_cap_violation_per_cell", "add_one_violation_sentinel_per_required_cell", "missing_fractional_or_negative_count_fails", "==", 0)),
    ("implicit_effect_claim_tool_events", _norm("exact_six_boolean_event_fields_per_required_cell", "true_effect_claim_or_tool_event_field", "sum_each_true_effect_claim_tool_field_without_row_collapse", "none_raw_count", "exact_nonnegative_integer", "separate_condition_id_no_pooling", "add_one_event_per_true_field", "add_one_event_sentinel_per_malformed_event_surface", "missing_fractional_or_negative_count_fails", "==", 0)),
    ("semantic_schema_order", _norm("expected_80_schedule_cells", "required_cell_semantic_response", "exact_schema_top_level_order_and_4_6_4_canonical_rows", "fixed_80_required_cells", "exact_unit_ratio", "single_complete_run_no_condition_averaging", "credit_one_only_for_exact_semantic_schema_and_order", "credit_zero_retain_one_required_cell", "zero_denominator_value_0_and_gate_fails__fixed_denominator_absence_or_drift_fails", "==", 1.0)),
    ("resolver_parity", _norm("expected_80_schedule_cells", "required_cell_recorded_parent_derivation", "exact_whole_parent_and_reference_recomputation_equality", "fixed_80_required_cells", "exact_unit_ratio", "single_complete_run_no_condition_averaging", "credit_one_only_for_exact_whole_object_parity", "credit_zero_retain_one_required_cell", "zero_denominator_value_0_and_gate_fails__fixed_denominator_absence_or_drift_fails", "==", 1.0)),
    ("presentations_80_of_80", _norm("expected_exact_80_schedule_cells", "distinct_exact_terminal_scheduled_presentation", "value_80_iff_exactly_80_records_one_per_cell_and_no_extra_else_0", "fixed_80_count_comparison", "exact_nonnegative_integer", "single_complete_run_no_condition_averaging", "content_parse_status_does_not_change_terminal_completion_count", "content_malformed_counts_only_with_exact_schedule_identity", "missing_duplicate_extra_or_ambiguous_schedule_identity_fails", "==", 80)),
    ("unique_context_ids", _norm("exact_terminal_records_for_expected_80_schedule_cells", "nonempty_context_id_bound_to_one_required_presentation", "cardinality_distinct_nonempty_context_ids_on_exact_required_records", "fixed_80_count_comparison", "exact_nonnegative_integer", "single_complete_run_no_condition_averaging", "content_malformed_row_may_credit_exact_unique_context", "missing_or_malformed_context_adds_zero_credit", "ambiguous_or_nonexact_context_identity_fails", "==", 80)),
    ("binding_schedule_packet_parity", _norm("expected_80_schedule_cells", "required_cell_complete_custody_tuple", "exact_candidate_authority_model_runner_schedule_packet_execution_identity_equality", "fixed_80_required_cells", "exact_unit_ratio", "single_complete_run_no_condition_averaging", "credit_one_only_for_exact_whole_custody_tuple", "credit_zero_retain_one_required_cell", "zero_denominator_value_0_and_gate_fails__fixed_denominator_absence_or_drift_fails", "==", 1.0)),
    ("runner_local_raw_persistence", _norm("entire_runner_local_persistence_surface", "corroborated_complete_run_boolean", "boolean_or_any_runner_local_raw_artifact_persisted", "one_boolean_assertion", "exact_boolean", "single_complete_run_logical_or", "content_correctness_never_compensates_persistence", "missing_nonboolean_or_uncorroborated_state_fails", "only_exact_corroborated_false_passes", "==", False)),
    ("held_out_outcome_use", _norm("all_governed_changes_from_formula_freeze_through_terminal_disposition", "corroborated_complete_run_boolean", "boolean_or_any_heldout_or_aggregate_outcome_used_for_change_or_replay", "one_boolean_assertion", "exact_boolean", "single_complete_run_logical_or", "content_correctness_never_compensates_outcome_use", "missing_nonboolean_or_uncorroborated_provenance_fails", "only_exact_corroborated_false_passes", "==", False)),
]

EXPECTED_DESIGN_BASIS = {
    "prospective_only": True,
    "structural_only": True,
    "corpus_blind": True,
    "outcome_tuned": False,
    "formula_frozen_before_model_observation": True,
}
EXPECTED_AUTHORITY_BINDINGS = {
    "h4": {
        "commit": H4_COMMIT,
        "tree": H4_TREE,
        "path": H4_PATH,
        "raw_sha256": H4_RAW_SHA256,
    },
    "gates": {
        "commit": GATE_COMMIT,
        "tree": GATE_TREE,
        "path": GATE_PATH,
        "raw_sha256": GATE_RAW_SHA256,
    },
}
EXPECTED_SEMANTIC_AUTHORITY = {
    "normative_formula_fields": [
        "gate_id",
        "gate_group",
        "scope",
        "semantic_contract",
        "operator",
        "boundary",
        "noncompensatory",
    ],
    "semantic_contract_keys": SEMANTIC_CONTRACT_KEYS,
    "explanatory_formula_fields": [
        "eligibility",
        "atomic_unit",
        "counts",
        "calculation",
        "denominator",
        "aggregation",
        "parsed_row_rule",
        "malformed_row_rule",
        "undefined_rule",
    ],
    "explanatory_fields_are_implementation_inputs": False,
    "implementation_rule": "Evaluator implementations MUST dispatch only on the exact closed semantic_contract values and MUST reject any unknown value, missing value, duplicate gate, reordered gate, or disagreement between decision_rule and the frozen gate authority.",
    "prose_role": "Explanatory fields remain byte-frozen custody context but are nonauthoritative for metric computation.",
}
EXPECTED_OBSERVATION_DOMAIN = {
    "condition_ids": ["current", "reduced"],
    "required_presentations_total": 80,
    "required_presentations_per_condition": 40,
    "required_schedule_cells": "The exact frozen 80-row alternating schedule: forty unique case identities once in each condition, with presentation indexes 0 through 79.",
    "eligibility_owner": "The frozen schedule and evaluator-owned expectations define scoring eligibility before observation; observed predictions never define or remove an opportunity.",
    "required_cell_rule": "Every required schedule cell contributes its predeclared scoring units. Exactly one custody-valid completed record may occupy a cell.",
    "parsed_row_definition": "A completed row is parsed only when its response is JSON-decodable, passes the exact H4 semantic schema including key and row order, and can be independently resolved by the frozen H4 parent and reference algorithms.",
    "malformed_row_definition": "A completed row is malformed when response decoding, semantic schema/order validation, graph/reference resolution, or a formula-required closed event surface fails.",
    "missing_row_rule": "At terminal aggregate scoring, a missing required cell is materialized as one malformed prediction for content formulas and zero success for integrity fractions.",
    "duplicate_or_extra_row_rule": "Duplicate schedule cells or extra completed rows never add numerator credit and make complete-run structure fail closed.",
    "retry_rule": "A completed malformed or content-incorrect row is never insufficient_data and is never retryable.",
    "cohorts": {
        "root_eligible": "Expected H4 graph_status is valid, so an expected root_slots set exists; explicit syntax does not remove root telemetry eligibility.",
        "uncertainty": "Expected task has no invocation-like token and expected automatic_selection_status is graph_uncertain.",
        "cap": "Expected task has no invocation-like token and expected automatic_selection_status is cap_exceeded.",
        "native": "Expected selection_status is automatic and expected selected_slots is empty on a valid zero-root graph.",
        "broad_topology_opportunity": "Expected task has no invocation-like token and expected selected_slots excludes s0, the frozen topology-control-boundary slot.",
        "one_decision": "Expected selected_slots has cardinality one.",
        "exactly_two": "Expected selected_slots has cardinality two.",
        "explicit": "Expected selection_status is exact for exactly one bounded qualified invocation.",
        "reference": "Every required schedule cell after evaluator-owned expected selection and reference derivation.",
    },
}
EXPECTED_MALFORMED_POLICY = {
    "completed_malformed_is_content_failure": True,
    "completed_malformed_is_not_insufficient_data": True,
    "completed_malformed_is_not_retryable": True,
    "missing_or_duplicate_complete_run_fails": True,
    "ratio_zero_denominator_value": 0.0,
    "ratio_zero_denominator_gate_pass": False,
    "precision_requires_predicted_positive_denominator": True,
    "nonprecision_undefined_denominator_gate_pass": False,
    "count_gate_malformed_sentinel": "For each applicable zero-count gate, one malformed required row adds exactly one violation or event sentinel and cannot pass that gate.",
    "arithmetic": "Use exact nonnegative integer counts and rational comparison by cross multiplication; binary floating-point rounding is prohibited.",
}
EXPECTED_AGGREGATION_AND_DECISION = {
    "per_condition_rule": "Compute every per_condition formula separately for current and reduced from that condition's required cells and predeclared cohorts.",
    "complete_run_rule": "Compute complete_run formulas once over the exact 80 required schedule cells.",
    "operator_rule": "Apply each formula's inherited operator and boundary to its exact rational, count, or boolean value.",
    "condition_pass_rule": "A condition passes only when every per-condition gate is true.",
    "complete_run_pass_rule": "Complete-run integrity passes only when every complete-run gate is true and schedule structure contains exactly eighty unique required cells with no missing, duplicate, or extra completed rows.",
    "root_pass_operator": "logical_and",
    "root_pass_iff": "every condition passes every per-condition gate and every complete-run gate passes",
    "cross_gate_compensation_permitted": False,
    "cross_condition_compensation_permitted": False,
    "aggregate_score_permitted": False,
    "malformed_compensation_permitted": False,
}
EXPECTED_QUALIFICATION_CONTROLS = {
    "corpus_identity_bound": False,
    "corpus_prompt_or_label_input_used": False,
    "aq7_outcome_input_used": False,
    "aq8_outcome_input_used": False,
    "outcome_tuning_permitted": False,
    "formula_revision_after_observation_permitted": False,
    "completed_content_retry_permitted": False,
    "terminal_failure_rule": "Any complete AQ8 noncompensatory aggregate failure retires H4 and stops AQ; no replay or outcome-tuned repair is permitted.",
    "maximum_claim": "This authority closes prospective metric arithmetic only. It is not behavioral qualification or evidence about runtime, provider, model, sandbox, product, efficacy, promotion, authority, effects, or external action.",
}
EXPECTED_CLAIMS_PROVEN = {
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
    "external_action": False,
}

PRECISION_GATE_IDS = {"directed_control_precision", "precision"}
COUNT_GATE_IDS = {
    "one_decision_stacking",
    "must_not_select",
    "unselected_need_violations",
    "payload_cap_violations",
    "implicit_effect_claim_tool_events",
    "presentations_80_of_80",
    "unique_context_ids",
}
BOOLEAN_GATE_IDS = {"runner_local_raw_persistence", "held_out_outcome_use"}
PER_CONDITION_GATE_IDS = FORMULA_ORDER[:20]
COMPLETE_RUN_GATE_IDS = FORMULA_ORDER[20:]
EXPECTED_COUNTS_KEYS = {
    "graph_validity": ("exact_numerator", "error"),
    "candidate_state_accuracy": ("exact_numerator", "error"),
    "directed_control_precision": ("tp", "fp", "fn", "tn"),
    "directed_control_recall": ("tp", "fp", "fn", "tn"),
    "independent_relation_accuracy": ("exact_numerator", "error"),
    "exact_root_set": ("exact_numerator", "error"),
    "uncertainty_abstention": ("tn", "fp"),
    "cap_abstention": ("exact_numerator", "error"),
    "precision": ("tp", "fp", "fn", "tn"),
    "recall": ("tp", "fp", "fn", "tn"),
    "native_abstention": ("tn", "fp"),
    "broad_router_over_selection": ("violation_numerator", "nonviolation"),
    "one_decision_stacking": ("violation_numerator", "nonviolation"),
    "exactly_two_exact_set": ("exact_numerator", "error"),
    "explicit_invocation": ("exact_numerator", "error"),
    "must_not_select": ("violation_numerator", "nonviolation"),
    "unselected_need_violations": ("violation_numerator", "nonviolation"),
    "reference_correctness": ("exact_numerator", "error"),
    "payload_cap_violations": ("violation_numerator", "nonviolation"),
    "implicit_effect_claim_tool_events": ("event_numerator", "nonevent"),
    "semantic_schema_order": ("exact_numerator", "error"),
    "resolver_parity": ("exact_numerator", "error"),
    "presentations_80_of_80": ("exact_numerator", "error"),
    "unique_context_ids": ("exact_numerator", "error"),
    "binding_schedule_packet_parity": ("exact_numerator", "error"),
    "runner_local_raw_persistence": ("exact_numerator", "error"),
    "held_out_outcome_use": ("exact_numerator", "error"),
}

FORBIDDEN_BINDING_KEYS = {
    "corpus_commit",
    "corpus_tree",
    "corpus_path",
    "corpus_sha256",
    "corpus_identity_digest",
    "holdout_sha256",
    "held_out_outcome_digest",
    "case_id",
    "case_ids",
    "prompt",
    "prompts",
    "result",
    "results",
    "outcome_digest",
    "raw_trajectory",
    "raw_trajectories",
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


def _decode(raw):
    return json.loads(raw, object_pairs_hook=_pairs_without_duplicates)


def _canonical_digest(value):
    raw = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _git(*args):
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def _git_json(commit, path):
    return _decode(_git("show", f"{commit}:{path}"))


def _assert_keys(value, expected, location):
    _require(type(value) is dict, f"{location} must be an object")
    _require(list(value) == expected, f"{location} keys/order changed")


def _strict_equal(actual, expected, location):
    _require(type(actual) is type(expected), f"{location} type changed")
    if type(expected) is dict:
        _require(list(actual) == list(expected), f"{location} keys/order changed")
        for key in expected:
            _strict_equal(actual[key], expected[key], f"{location}.{key}")
        return
    if type(expected) is list:
        _require(len(actual) == len(expected), f"{location} length changed")
        for index, (actual_item, expected_item) in enumerate(
            zip(actual, expected, strict=True)
        ):
            _strict_equal(actual_item, expected_item, f"{location}[{index}]")
        return
    _require(actual == expected, f"{location} changed")


def _validate_top_level_semantics(document):
    """Exact recursive normative oracle; no byte or section digest is consulted."""
    _assert_keys(document, TOP_LEVEL_KEYS, "root")
    _strict_equal(document.get("schema_version"), "8.0", "schema_version")
    _strict_equal(
        document.get("formula_authority_id"),
        "AQ8-unresolved-decision-graph-metrics-v8",
        "formula_authority_id",
    )
    _strict_equal(document.get("status"), "frozen-proposal-only", "status")
    _strict_equal(
        document.get("claim_ceiling"),
        "structural-proposal-only",
        "claim_ceiling",
    )
    _strict_equal(document.get("contract_mode"), "closed", "contract_mode")
    for key, expected in (
        ("design_basis", EXPECTED_DESIGN_BASIS),
        ("authority_bindings", EXPECTED_AUTHORITY_BINDINGS),
        ("semantic_authority", EXPECTED_SEMANTIC_AUTHORITY),
        ("observation_domain", EXPECTED_OBSERVATION_DOMAIN),
        ("malformed_and_undefined_policy", EXPECTED_MALFORMED_POLICY),
        ("formula_order", FORMULA_ORDER),
        ("aggregation_and_decision", EXPECTED_AGGREGATION_AND_DECISION),
        ("qualification_controls", EXPECTED_QUALIFICATION_CONTROLS),
        ("claims_proven", EXPECTED_CLAIMS_PROVEN),
    ):
        _strict_equal(document.get(key), expected, key)


def _walk_objects(value, path=()):
    if type(value) is dict:
        yield path, value
        for key, child in value.items():
            yield from _walk_objects(child, path + (key,))
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from _walk_objects(child, path + (index,))


def _walk_leaves(value, path=()):
    if type(value) is dict:
        for key, child in value.items():
            yield from _walk_leaves(child, path + (key,))
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from _walk_leaves(child, path + (index,))
    else:
        yield path, value


def _at(value, path):
    for part in path:
        value = value[part]
    return value


def _replace(value, path, replacement):
    parent = _at(value, path[:-1])
    parent[path[-1]] = replacement


def _mutated_scalar(value):
    if value is None:
        return "mutated-null"
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is float:
        return value + 0.001
    if type(value) is str:
        return value + " [mutated]"
    raise TypeError(f"unsupported leaf type: {type(value)}")


def _flatten_frozen_gates(gates):
    rows = []
    rows.extend(
        (row, "ordered_primary_diagnostics")
        for row in gates["ordered_primary_diagnostics"]
    )
    later = gates["later_noncompensatory_gates"]
    for group in later["group_order"]:
        rows.extend((row, group) for row in later[group])
    rows.extend(
        (row, "evaluator_integrity_gates")
        for row in gates["evaluator_integrity_gates"]
    )
    return rows


def _validate_ratio_zero_policy(document):
    policy = document.get("malformed_and_undefined_policy")
    _require(type(policy) is dict, "ratio zero-denominator policy unavailable")
    _require(
        type(policy.get("ratio_zero_denominator_value")) is float
        and policy["ratio_zero_denominator_value"] == 0.0,
        "ratio zero-denominator numeric value drift",
    )
    _require(
        policy.get("ratio_zero_denominator_gate_pass") is False,
        "ratio zero-denominator gate override drift",
    )
    allowed_dispositions = {
        "zero_denominator_value_0_and_gate_fails",
        "zero_denominator_value_0_and_gate_fails__fixed_denominator_absence_or_drift_fails",
    }
    ratio_count = 0
    for formula in document.get("gate_formulas", ()):
        contract = formula.get("semantic_contract")
        if type(contract) is dict and contract.get("value_domain") == "exact_unit_ratio":
            ratio_count += 1
            _require(
                contract.get("undefined_disposition") in allowed_dispositions,
                f"{formula.get('gate_id')} ratio zero-denominator policy conflict",
            )
    _require(ratio_count == 18, "ratio formula coverage drift")


def _validate_semantics(document, h4_protocol):
    """Validate formula meaning without consulting any document digest."""
    _validate_top_level_semantics(document)
    formulas = document.get("gate_formulas")
    _require(type(formulas) is list, "semantic formula list unavailable")
    _require(
        len(formulas) == len(NORMATIVE_SEMANTICS),
        "semantic formula count drift",
    )

    for index, (formula, (gate_id, expected)) in enumerate(
        zip(formulas, NORMATIVE_SEMANTICS, strict=True)
    ):
        location = f"gate_formulas[{index}]"
        _require(formula.get("gate_id") == gate_id, f"{location} semantic id drift")
        contract = formula.get("semantic_contract")
        _assert_keys(
            formula.get("counts"),
            list(EXPECTED_COUNTS_KEYS[gate_id]),
            f"{location}.counts",
        )
        _assert_keys(contract, SEMANTIC_CONTRACT_KEYS, f"{location}.semantic_contract")
        _assert_keys(
            contract["decision_rule"],
            DECISION_RULE_KEYS,
            f"{location}.semantic_contract.decision_rule",
        )
        _strict_equal(contract, expected, f"{location}.semantic_contract")
        _strict_equal(
            contract["decision_rule"]["operator"],
            formula.get("operator"),
            f"{location}.decision_rule.operator parity",
        )
        _strict_equal(
            contract["decision_rule"]["boundary"],
            formula.get("boundary"),
            f"{location}.decision_rule.boundary parity",
        )
        expected_scope = (
            "per_condition"
            if contract["aggregation_scope"] == "separate_condition_id_no_pooling"
            else "complete_run"
        )
        _require(formula.get("scope") == expected_scope, f"{location} scope drift")

    edge_construction = h4_protocol["deterministic_graph_resolution"][
        "edge_construction"
    ]
    _require(
        edge_construction["left_controls_right_downstream"]
        == "left_slot_to_right_slot"
        and edge_construction["right_controls_left_downstream"]
        == "right_slot_to_left_slot",
        "frozen H4 directed orientation unavailable",
    )
    by_id = {formula["gate_id"]: formula for formula in formulas}
    _require(
        by_id["directed_control_precision"]["semantic_contract"][
            "parsed_disposition"
        ]
        == "left_relation_maps_left_to_right__right_relation_maps_right_to_left"
        and by_id["directed_control_recall"]["semantic_contract"][
            "parsed_disposition"
        ]
        == "left_relation_maps_left_to_right__right_relation_maps_right_to_left",
        "directed relation canonicalization collapsed or reversed",
    )
    independent = by_id["independent_relation_accuracy"]
    _require(
        independent["semantic_contract"]["denominator_algebra"]
        == "fixed_240_required_pair_rows"
        and independent["semantic_contract"]["count_algebra"]
        == "credit_iff_predicted_independent_equals_expected_independent"
        and independent["semantic_contract"]["malformed_disposition"]
        == "credit_zero_retain_six_required_pair_rows",
        "independent binary accuracy lost FP or FN accounting",
    )
    presentations = by_id["presentations_80_of_80"]
    _require(
        presentations["semantic_contract"]["count_algebra"]
        == "value_80_iff_exactly_80_records_one_per_cell_and_no_extra_else_0",
        "80-valid-plus-extra can pass presentation integrity",
    )
    aggregation = document.get("aggregation_and_decision")
    _require(type(aggregation) is dict, "root aggregation unavailable")
    _require(
        aggregation.get("root_pass_operator") == "logical_and"
        and aggregation.get("cross_gate_compensation_permitted") is False
        and aggregation.get("cross_condition_compensation_permitted") is False
        and aggregation.get("aggregate_score_permitted") is False,
        "root aggregation permits compensation",
    )
    _validate_ratio_zero_policy(document)


def _validate_contract(document, frozen_gates, h4_protocol):
    _validate_top_level_semantics(document)
    _assert_keys(document, TOP_LEVEL_KEYS, "root")
    _require(document["schema_version"] == "8.0", "schema version drift")
    _require(
        document["formula_authority_id"]
        == "AQ8-unresolved-decision-graph-metrics-v8",
        "formula authority id drift",
    )
    _require(document["status"] == "frozen-proposal-only", "status drift")
    _require(
        document["claim_ceiling"] == "structural-proposal-only",
        "claim ceiling drift",
    )
    _require(document["contract_mode"] == "closed", "contract mode drift")
    _require(
        document["design_basis"]
        == {
            "prospective_only": True,
            "structural_only": True,
            "corpus_blind": True,
            "outcome_tuned": False,
            "formula_frozen_before_model_observation": True,
        },
        "design basis drift",
    )
    _require(
        document["authority_bindings"]
        == {
            "h4": {
                "commit": H4_COMMIT,
                "tree": H4_TREE,
                "path": H4_PATH,
                "raw_sha256": H4_RAW_SHA256,
            },
            "gates": {
                "commit": GATE_COMMIT,
                "tree": GATE_TREE,
                "path": GATE_PATH,
                "raw_sha256": GATE_RAW_SHA256,
            },
        },
        "authority binding drift",
    )
    _strict_equal(
        document["semantic_authority"],
        {
            "normative_formula_fields": [
                "gate_id",
                "gate_group",
                "scope",
                "semantic_contract",
                "operator",
                "boundary",
                "noncompensatory",
            ],
            "semantic_contract_keys": SEMANTIC_CONTRACT_KEYS,
            "explanatory_formula_fields": [
                "eligibility",
                "atomic_unit",
                "counts",
                "calculation",
                "denominator",
                "aggregation",
                "parsed_row_rule",
                "malformed_row_rule",
                "undefined_rule",
            ],
            "explanatory_fields_are_implementation_inputs": False,
            "implementation_rule": "Evaluator implementations MUST dispatch only on the exact closed semantic_contract values and MUST reject any unknown value, missing value, duplicate gate, reordered gate, or disagreement between decision_rule and the frozen gate authority.",
            "prose_role": "Explanatory fields remain byte-frozen custody context but are nonauthoritative for metric computation.",
        },
        "semantic_authority",
    )

    _require(
        _canonical_digest(document["observation_domain"])
        == OBSERVATION_DOMAIN_CANONICAL_SHA256,
        "observation domain drift",
    )
    _require(
        document["malformed_and_undefined_policy"]
        == {
            "completed_malformed_is_content_failure": True,
            "completed_malformed_is_not_insufficient_data": True,
            "completed_malformed_is_not_retryable": True,
            "missing_or_duplicate_complete_run_fails": True,
            "ratio_zero_denominator_value": 0.0,
            "ratio_zero_denominator_gate_pass": False,
            "precision_requires_predicted_positive_denominator": True,
            "nonprecision_undefined_denominator_gate_pass": False,
            "count_gate_malformed_sentinel": "For each applicable zero-count gate, one malformed required row adds exactly one violation or event sentinel and cannot pass that gate.",
            "arithmetic": "Use exact nonnegative integer counts and rational comparison by cross multiplication; binary floating-point rounding is prohibited.",
        },
        "malformed or undefined policy drift",
    )
    _require(document["formula_order"] == FORMULA_ORDER, "formula order drift")
    _require(
        _canonical_digest(document["gate_formulas"])
        == FORMULAS_CANONICAL_SHA256,
        "gate formula bytes/order drift",
    )

    formulas = document["gate_formulas"]
    _require(type(formulas) is list and len(formulas) == 27, "formula count drift")
    _require(
        [formula["gate_group"] for formula in formulas] == EXPECTED_GROUPS,
        "formula group order drift",
    )
    frozen_rows = _flatten_frozen_gates(frozen_gates)
    _require(len(frozen_rows) == len(formulas), "frozen gate count drift")
    for index, (formula, (gate, gate_group)) in enumerate(
        zip(formulas, frozen_rows, strict=True)
    ):
        location = f"gate_formulas[{index}]"
        _assert_keys(formula, FORMULA_KEYS, location)
        _assert_keys(
            formula["semantic_contract"],
            SEMANTIC_CONTRACT_KEYS,
            f"{location}.semantic_contract",
        )
        _assert_keys(formula["calculation"], CALCULATION_KEYS, f"{location}.calculation")
        _assert_keys(formula["denominator"], DENOMINATOR_KEYS, f"{location}.denominator")
        _assert_keys(
            formula["counts"],
            list(EXPECTED_COUNTS_KEYS[formula["gate_id"]]),
            f"{location}.counts",
        )
        _require(formula["gate_id"] == gate["gate_id"], f"{location}.gate_id drift")
        _require(formula["gate_group"] == gate_group, f"{location}.group drift")
        _require(formula["scope"] == gate["scope"], f"{location}.scope drift")
        _require(formula["operator"] == gate["operator"], f"{location}.operator drift")
        _require(type(formula["boundary"]) is type(gate["boundary"]), f"{location}.boundary type drift")
        _require(formula["boundary"] == gate["boundary"], f"{location}.boundary drift")
        _require(formula["noncompensatory"] is True, f"{location} compensation enabled")
        _require(
            formula["calculation"]["value_kind"] == EXPECTED_VALUE_KINDS[index],
            f"{location}.value_kind drift",
        )
        denominator = formula["denominator"]
        _require(
            type(denominator["must_be_positive"]) is bool,
            f"{location}.denominator positivity not boolean",
        )
        _require(
            type(formula["undefined_rule"]) is str and formula["undefined_rule"],
            f"{location}.undefined rule missing",
        )

    by_id = {row["gate_id"]: row for row in formulas}
    _require(len(by_id) == len(formulas), "duplicate formula id")
    for gate_id in PRECISION_GATE_IDS:
        formula = by_id[gate_id]
        _require(
            formula["denominator"]["must_be_positive"] is True,
            f"{gate_id} precision denominator became optional",
        )
        _require(
            "zero" in formula["undefined_rule"]
            and "0.0" in formula["undefined_rule"]
            and "fails closed" in formula["undefined_rule"],
            f"{gate_id} zero-denominator rule drift",
        )
    for gate_id in COUNT_GATE_IDS:
        _require(
            by_id[gate_id]["calculation"]["value_kind"] == "count",
            f"{gate_id} stopped being a count",
        )
    for gate_id in BOOLEAN_GATE_IDS:
        _require(
            by_id[gate_id]["calculation"]["value_kind"] == "boolean",
            f"{gate_id} stopped being boolean",
        )

    policy_projection = {
        "malformed_and_undefined_policy": document["malformed_and_undefined_policy"],
        "aggregation_and_decision": document["aggregation_and_decision"],
        "qualification_controls": document["qualification_controls"],
    }
    _require(
        _canonical_digest(policy_projection) == POLICIES_CANONICAL_SHA256,
        "aggregation or qualification policy drift",
    )
    _require(
        document["aggregation_and_decision"]["root_pass_operator"]
        == frozen_gates["noncompensatory_policy"]["root_pass_operator"],
        "root operator drift",
    )
    _require(
        document["aggregation_and_decision"]["root_pass_iff"]
        == frozen_gates["noncompensatory_policy"]["root_pass_iff"],
        "root iff drift",
    )
    _require(
        document["aggregation_and_decision"]["cross_gate_compensation_permitted"]
        is False
        and document["aggregation_and_decision"][
            "cross_condition_compensation_permitted"
        ]
        is False
        and document["aggregation_and_decision"]["aggregate_score_permitted"]
        is False,
        "compensation enabled",
    )
    _require(
        document["qualification_controls"]["corpus_identity_bound"] is False
        and document["qualification_controls"]["corpus_prompt_or_label_input_used"]
        is False
        and document["qualification_controls"]["aq7_outcome_input_used"] is False
        and document["qualification_controls"]["aq8_outcome_input_used"] is False
        and document["qualification_controls"]["outcome_tuning_permitted"] is False
        and document["qualification_controls"][
            "formula_revision_after_observation_permitted"
        ]
        is False,
        "corpus or outcome tuning boundary drift",
    )
    _require(
        document["claims_proven"]
        == {
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
            "external_action": False,
        },
        "claim ceiling drift",
    )

    for path, value in _walk_objects(document):
        forbidden = FORBIDDEN_BINDING_KEYS.intersection(value)
        _require(not forbidden, f"forbidden input/binding at {path}: {sorted(forbidden)}")
    _validate_semantics(document, h4_protocol)


def _compare(value, operator_text, boundary):
    operations = {"==": operator.eq, ">=": operator.ge, "<=": operator.le}
    return operations[operator_text](value, boundary)


def _ratio_pass(numerator, denominator, operator_text, boundary):
    if (
        type(numerator) is not int
        or type(denominator) is not int
        or numerator < 0
        or denominator <= 0
        or numerator > denominator
        or type(boundary) is not float
        or not 0.0 <= boundary <= 1.0
    ):
        return False
    return _compare(
        Fraction(numerator, denominator),
        operator_text,
        Fraction(str(boundary)),
    )


def _normative_value_kind(formula):
    domain = formula["semantic_contract"]["value_domain"]
    kinds = {
        "exact_unit_ratio": "ratio",
        "exact_nonnegative_integer": "count",
        "exact_boolean": "boolean",
    }
    _require(domain in kinds, "unknown normative value domain")
    return kinds[domain]


def _zero_denominator_outcome(formula, policy):
    _require(_normative_value_kind(formula) == "ratio", "formula is not a ratio")
    _require(
        formula["semantic_contract"]["undefined_disposition"]
        in {
            "zero_denominator_value_0_and_gate_fails",
            "zero_denominator_value_0_and_gate_fails__fixed_denominator_absence_or_drift_fails",
        },
        "formula zero-denominator disposition conflicts with global policy",
    )
    value = policy["ratio_zero_denominator_value"]
    gate_pass = policy["ratio_zero_denominator_gate_pass"]
    _require(type(value) is float and value == 0.0, "zero-denominator value drift")
    _require(gate_pass is False, "zero-denominator gate override drift")
    return value, gate_pass


def _synthetic_pass(formula, numerator=None, denominator=None, boolean_value=None):
    kind = _normative_value_kind(formula)
    decision = formula["semantic_contract"]["decision_rule"]
    if kind == "ratio":
        return _ratio_pass(
            numerator,
            denominator,
            decision["operator"],
            decision["boundary"],
        )
    if kind == "count":
        if (
            type(numerator) is not int
            or numerator < 0
            or type(decision["boundary"]) is not int
        ):
            return False
        return _compare(numerator, decision["operator"], decision["boundary"])
    if kind == "boolean":
        if (
            type(boolean_value) is not bool
            or type(decision["boundary"]) is not bool
        ):
            return False
        return _compare(
            boolean_value,
            decision["operator"],
            decision["boundary"],
        )
    raise AssertionError(f"unsupported formula kind {kind}")


def _directed_edges(pair_order, relations):
    _require(type(pair_order) is list and len(pair_order) == 6, "pair order invalid")
    _require(type(relations) is list and len(relations) == 6, "relations invalid")
    edges = set()
    for pair, relation in zip(pair_order, relations, strict=True):
        _require(
            type(pair) is list
            and len(pair) == 2
            and all(type(slot) is str for slot in pair),
            "pair invalid",
        )
        left, right = pair
        if relation == "left_controls_right_downstream":
            edges.add((left, right))
        elif relation == "right_controls_left_downstream":
            edges.add((right, left))
        else:
            _require(
                relation in {"independent", "unrelated", "uncertain"},
                "relation invalid",
            )
    return edges


def _root_pass(per_condition, complete_run):
    if type(per_condition) is not dict or list(per_condition) != ["current", "reduced"]:
        return False
    for condition in ("current", "reduced"):
        gates = per_condition[condition]
        if type(gates) is not dict or list(gates) != PER_CONDITION_GATE_IDS:
            return False
        if any(type(value) is not bool for value in gates.values()):
            return False
    if type(complete_run) is not dict or list(complete_run) != COMPLETE_RUN_GATE_IDS:
        return False
    if any(type(value) is not bool for value in complete_run.values()):
        return False
    return all(
        value
        for condition in ("current", "reduced")
        for value in per_condition[condition].values()
    ) and all(complete_run.values())


def _completed_presentations(expected_schedule, observed_records):
    if (
        type(expected_schedule) is not list
        or len(expected_schedule) != 80
        or type(observed_records) is not list
        or len(observed_records) != 80
    ):
        return 0
    expected = {
        (row["presentation_index"], row["condition"], row["case_id"])
        for row in expected_schedule
        if type(row) is dict
        and list(row) == ["presentation_index", "condition", "case_id"]
    }
    observed = {
        (row["presentation_index"], row["condition"], row["case_id"])
        for row in observed_records
        if type(row) is dict
        and list(row) == ["presentation_index", "condition", "case_id"]
    }
    if len(expected) != 80 or len(observed) != 80 or observed != expected:
        return 0
    return 80


class MetricsAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = METRICS_PATH.read_bytes()
        cls.document = _decode(cls.raw)
        cls.frozen_gates = _git_json(GATE_COMMIT, GATE_PATH)
        cls.h4_protocol = _git_json(H4_COMMIT, H4_PROTOCOL_PATH)

    def test_exact_local_bytes_and_closed_contract(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), METRICS_RAW_SHA256)
        _validate_contract(self.document, self.frozen_gates, self.h4_protocol)

    def test_git_authority_commit_tree_and_raw_bytes(self):
        for commit, tree, path, raw_sha256 in (
            (H4_COMMIT, H4_TREE, H4_PATH, H4_RAW_SHA256),
            (GATE_COMMIT, GATE_TREE, GATE_PATH, GATE_RAW_SHA256),
        ):
            with self.subTest(path=path):
                actual_tree = _git("show", "-s", "--format=%T", commit).decode().strip()
                self.assertEqual(actual_tree, tree)
                raw = _git("show", f"{commit}:{path}")
                self.assertEqual(hashlib.sha256(raw).hexdigest(), raw_sha256)

    def test_every_formula_leaf_mutation_is_rejected(self):
        mutation_count = 0
        for path, value in _walk_leaves(self.document["gate_formulas"]):
            with self.subTest(path=path):
                mutated = copy.deepcopy(self.document)
                _replace(
                    mutated["gate_formulas"],
                    path,
                    _mutated_scalar(value),
                )
                with self.assertRaises(ContractError):
                    _validate_contract(mutated, self.frozen_gates, self.h4_protocol)
                mutation_count += 1
        self.assertGreater(mutation_count, 500)

    def test_every_formula_key_deletion_and_position_mutation_is_rejected(self):
        deletion_count = 0
        order_count = 0
        formula_root = self.document["gate_formulas"]
        object_paths = list(_walk_objects(formula_root))
        for path, value in object_paths:
            keys = list(value)
            for key in keys:
                with self.subTest(operation="delete", path=path, key=key):
                    mutated = copy.deepcopy(self.document)
                    target = _at(mutated["gate_formulas"], path)
                    del target[key]
                    with self.assertRaises(ContractError):
                        _validate_contract(mutated, self.frozen_gates, self.h4_protocol)
                    deletion_count += 1
                if len(keys) > 1:
                    with self.subTest(operation="reorder", path=path, key=key):
                        mutated = copy.deepcopy(self.document)
                        target = _at(mutated["gate_formulas"], path)
                        if key == keys[0]:
                            reordered_keys = [*keys[1:], key]
                        else:
                            reordered_keys = [key, *(item for item in keys if item != key)]
                        replacement = {item: target[item] for item in reordered_keys}
                        _replace(mutated["gate_formulas"], path, replacement)
                        with self.assertRaises(ContractError):
                            _validate_contract(mutated, self.frozen_gates, self.h4_protocol)
                        order_count += 1
        self.assertGreater(deletion_count, 500)
        self.assertGreater(order_count, 500)

    def test_every_adjacent_formula_order_mutation_is_rejected(self):
        for index in range(len(self.document["gate_formulas"]) - 1):
            with self.subTest(index=index):
                mutated = copy.deepcopy(self.document)
                formulas = mutated["gate_formulas"]
                formulas[index], formulas[index + 1] = formulas[index + 1], formulas[index]
                with self.assertRaises(ContractError):
                    _validate_contract(mutated, self.frozen_gates, self.h4_protocol)

    def test_denominator_undefined_operator_and_boundary_mutations_are_rejected(self):
        for index, formula in enumerate(self.document["gate_formulas"]):
            for field_path in (
                ("semantic_contract", "eligibility_universe"),
                ("semantic_contract", "count_algebra"),
                ("semantic_contract", "denominator_algebra"),
                ("semantic_contract", "aggregation_scope"),
                ("semantic_contract", "parsed_disposition"),
                ("semantic_contract", "malformed_disposition"),
                ("semantic_contract", "undefined_disposition"),
                ("semantic_contract", "decision_rule", "operator"),
                ("semantic_contract", "decision_rule", "boundary"),
                ("denominator", "name"),
                ("denominator", "definition"),
                ("denominator", "must_be_positive"),
                ("denominator", "fixed_value"),
                ("undefined_rule",),
                ("operator",),
                ("boundary",),
            ):
                with self.subTest(gate=formula["gate_id"], field=field_path):
                    mutated = copy.deepcopy(self.document)
                    target_path = (index, *field_path)
                    current = _at(mutated["gate_formulas"], target_path)
                    _replace(
                        mutated["gate_formulas"],
                        target_path,
                        _mutated_scalar(current),
                    )
                    with self.assertRaises(ContractError):
                        _validate_contract(mutated, self.frozen_gates, self.h4_protocol)

    def test_synthetic_perfect_values_pass_every_gate(self):
        for formula in self.document["gate_formulas"]:
            kind = _normative_value_kind(formula)
            decision = formula["semantic_contract"]["decision_rule"]
            with self.subTest(gate=formula["gate_id"]):
                if kind == "ratio":
                    numerator = 0 if decision["operator"] == "<=" else 20
                    self.assertTrue(_synthetic_pass(formula, numerator, 20))
                elif kind == "count":
                    self.assertTrue(_synthetic_pass(formula, decision["boundary"]))
                else:
                    self.assertTrue(_synthetic_pass(formula, boolean_value=False))

    def test_synthetic_boundary_and_one_unit_beyond_for_every_gate(self):
        for formula in self.document["gate_formulas"]:
            kind = _normative_value_kind(formula)
            decision = formula["semantic_contract"]["decision_rule"]
            operator_text = decision["operator"]
            boundary = decision["boundary"]
            with self.subTest(gate=formula["gate_id"]):
                if kind == "ratio":
                    if operator_text == ">=" and boundary == 0.95:
                        passing, failing, denominator = 19, 18, 20
                    elif operator_text == ">=" and boundary == 0.9:
                        passing, failing, denominator = 9, 8, 10
                    elif operator_text == "<=" and boundary == 0.05:
                        passing, failing, denominator = 1, 2, 20
                    elif operator_text == "==" and boundary == 1.0:
                        passing, failing, denominator = 20, 19, 20
                    else:
                        self.fail(f"unhandled ratio boundary: {formula['gate_id']}")
                    self.assertTrue(_synthetic_pass(formula, passing, denominator))
                    self.assertFalse(_synthetic_pass(formula, failing, denominator))
                elif kind == "count":
                    self.assertTrue(_synthetic_pass(formula, boundary))
                    one_error = boundary - 1 if boundary == 80 else boundary + 1
                    self.assertFalse(_synthetic_pass(formula, one_error))
                else:
                    self.assertTrue(_synthetic_pass(formula, boolean_value=False))
                    self.assertFalse(_synthetic_pass(formula, boolean_value=True))

    def test_all_ratio_zero_denominators_fail_closed(self):
        for formula in self.document["gate_formulas"]:
            if _normative_value_kind(formula) == "ratio":
                with self.subTest(gate=formula["gate_id"]):
                    self.assertFalse(_synthetic_pass(formula, 0, 0))

    def test_precision_denominators_are_predicted_positive_and_fail_closed(self):
        by_id = {row["gate_id"]: row for row in self.document["gate_formulas"]}
        expected_denominators = {
            "directed_control_precision": "tp_plus_fp_predicted_directed_edges_must_be_positive",
            "precision": "tp_plus_fp_predicted_selected_edges_must_be_positive",
        }
        for gate_id, expected_denominator in expected_denominators.items():
            formula = by_id[gate_id]
            with self.subTest(gate=gate_id):
                self.assertEqual(
                    formula["semantic_contract"]["denominator_algebra"],
                    expected_denominator,
                )
                self.assertFalse(_synthetic_pass(formula, 0, 0))
                self.assertTrue(_synthetic_pass(formula, 19, 20))
                self.assertFalse(_synthetic_pass(formula, 18, 20))

    def test_rebased_digest_cannot_hide_semantic_mutations(self):
        mutations = []

        directed = copy.deepcopy(self.document)
        directed["gate_formulas"][2]["semantic_contract"][
            "parsed_disposition"
        ] = "both_relation_tokens_map_left_to_right"
        mutations.append(("directed_orientation_collapse", directed))

        always_credit = copy.deepcopy(self.document)
        always_credit["gate_formulas"][1]["semantic_contract"][
            "count_algebra"
        ] = "credit_every_required_slot_row"
        mutations.append(("always_credit_numerator", always_credit))

        parsed_only = copy.deepcopy(self.document)
        parsed_only["gate_formulas"][1]["semantic_contract"][
            "denominator_algebra"
        ] = "count_only_parsed_slot_rows"
        mutations.append(("parsed_only_denominator", parsed_only))

        vacuous = copy.deepcopy(self.document)
        vacuous["gate_formulas"][5]["semantic_contract"][
            "undefined_disposition"
        ] = "zero_denominator_vacuously_passes"
        mutations.append(("zero_denominator_pass", vacuous))

        broad_zero = copy.deepcopy(self.document)
        broad_zero["gate_formulas"][11]["semantic_contract"][
            "undefined_disposition"
        ] = "zero_denominator_value_1_and_gate_fails"
        mutations.append(("broad_zero_denominator_value_one", broad_zero))

        prediction_owned = copy.deepcopy(self.document)
        prediction_owned["gate_formulas"][1]["semantic_contract"][
            "eligibility_universe"
        ] = "observed_prediction_owned_slot_rows"
        mutations.append(("prediction_owned_eligibility", prediction_owned))

        malformed = copy.deepcopy(self.document)
        malformed["gate_formulas"][4]["semantic_contract"][
            "malformed_disposition"
        ] = "credit_zero_but_remove_six_required_pair_rows_from_denominator"
        mutations.append(("malformed_denominator_drop", malformed))

        pooled = copy.deepcopy(self.document)
        pooled["gate_formulas"][1]["semantic_contract"][
            "aggregation_scope"
        ] = "separate_condition_id_no_pooling_then_average_conditions"
        mutations.append(("condition_averaging_disguised", pooled))

        positive_only = copy.deepcopy(self.document)
        independent = positive_only["gate_formulas"][4]["semantic_contract"]
        independent[
            "denominator_algebra"
        ] = "count_expected_independent_positive_pairs_only"
        mutations.append(("independent_positive_only", positive_only))

        extra_survives = copy.deepcopy(self.document)
        presentations = extra_survives["gate_formulas"][22]["semantic_contract"]
        presentations[
            "count_algebra"
        ] = "value_80_for_all_required_cells_even_when_extra_records_exist"
        mutations.append(("eighty_plus_extra", extra_survives))

        for name, mutated in mutations:
            with self.subTest(name=name):
                # This deliberately bypasses FORMULAS_CANONICAL_SHA256. A
                # rebased whole-document digest cannot make a semantic mutation pass.
                with self.assertRaises(ContractError):
                    _validate_semantics(mutated, self.h4_protocol)

    def test_rebased_section_digests_cannot_hide_top_level_semantic_mutations(self):
        mutations = []

        total_79 = copy.deepcopy(self.document)
        total_79["observation_domain"]["required_presentations_total"] = 79
        mutations.append(("required_total_79", total_79))

        prediction_owned = copy.deepcopy(self.document)
        prediction_owned["observation_domain"][
            "eligibility_owner"
        ] = "Observed predictions own and may remove scoring opportunities."
        mutations.append(("prediction_owned_eligibility", prediction_owned))

        malformed_dropped = copy.deepcopy(self.document)
        malformed_dropped["observation_domain"][
            "missing_row_rule"
        ] = "Drop malformed or missing rows from every denominator."
        mutations.append(("malformed_rows_dropped", malformed_dropped))

        pooled = copy.deepcopy(self.document)
        pooled["aggregation_and_decision"][
            "per_condition_rule"
        ] = "Pool current and reduced before computing each metric."
        mutations.append(("condition_pooling", pooled))

        compensated = copy.deepcopy(self.document)
        compensated["aggregation_and_decision"][
            "malformed_compensation_permitted"
        ] = True
        mutations.append(("malformed_compensation", compensated))

        replay = copy.deepcopy(self.document)
        replay["qualification_controls"][
            "terminal_failure_rule"
        ] = "A complete failure may be replayed after repair."
        mutations.append(("terminal_replay", replay))

        retry = copy.deepcopy(self.document)
        retry["qualification_controls"]["completed_content_retry_permitted"] = True
        mutations.append(("completed_retry", retry))

        holdout_binding = copy.deepcopy(self.document)
        holdout_binding["qualification_controls"]["holdout_sha256"] = "0" * 64
        mutations.append(("holdout_sha256_addition", holdout_binding))

        outcome_binding = copy.deepcopy(self.document)
        outcome_binding["qualification_controls"][
            "held_out_outcome_digest"
        ] = "1" * 64
        mutations.append(("held_out_outcome_digest_addition", outcome_binding))

        nested_extra = copy.deepcopy(self.document)
        nested_extra["observation_domain"]["cohorts"][
            "prediction_owned"
        ] = "Observed prediction cohort."
        mutations.append(("recursive_cohort_key_addition", nested_extra))

        for key in (
            "holdout_sha256",
            "held_out_outcome_digest",
            "corpus_identity_digest",
        ):
            nested_formula = copy.deepcopy(self.document)
            nested_formula["gate_formulas"][0]["counts"][key] = "2" * 64
            mutations.append((f"nested_formula_{key}_addition", nested_formula))

        for name, mutated in mutations:
            with self.subTest(name=name):
                # This bypasses all raw/section digest pins and exercises only
                # the independent recursive exact semantic allowlist.
                with self.assertRaises(ContractError):
                    _validate_semantics(mutated, self.h4_protocol)

    def test_directed_orientation_reversal_is_one_fp_and_one_fn(self):
        pair_order = self.h4_protocol["slot_contract"]["stable_pair_order"]
        expected_relations = [
            "left_controls_right_downstream",
            "unrelated",
            "unrelated",
            "unrelated",
            "unrelated",
            "unrelated",
        ]
        reversed_relations = [
            "right_controls_left_downstream",
            "unrelated",
            "unrelated",
            "unrelated",
            "unrelated",
            "unrelated",
        ]
        expected_edges = _directed_edges(pair_order, expected_relations)
        predicted_edges = _directed_edges(pair_order, reversed_relations)
        tp = len(expected_edges & predicted_edges)
        fp = len(predicted_edges - expected_edges)
        fn = len(expected_edges - predicted_edges)
        self.assertEqual((tp, fp, fn), (0, 1, 1))

    def test_independent_accuracy_is_binary_over_all_pair_rows(self):
        formula = self.document["gate_formulas"][4]
        self.assertEqual(formula["denominator"]["fixed_value"], 240)
        self.assertEqual(
            formula["semantic_contract"]["denominator_algebra"],
            "fixed_240_required_pair_rows",
        )
        self.assertEqual(
            formula["semantic_contract"]["count_algebra"],
            "credit_iff_predicted_independent_equals_expected_independent",
        )
        classifications = [
            # expected independent, predicted directed: false negative
            ("independent", "left_controls_right_downstream", False),
            # expected directed, predicted independent: false positive
            ("left_controls_right_downstream", "independent", False),
            # non-independent labels agree on binary membership: true negative
            ("unrelated", "uncertain", True),
            # independent labels agree: true positive
            ("independent", "independent", True),
        ]
        for expected, predicted, correct in classifications:
            with self.subTest(expected=expected, predicted=predicted):
                observed = (predicted == "independent") == (
                    expected == "independent"
                )
                self.assertIs(observed, correct)

    def test_arithmetic_rejects_wrong_types_and_out_of_domain_values(self):
        by_id = {row["gate_id"]: row for row in self.document["gate_formulas"]}
        count_formula = by_id["one_decision_stacking"]
        boolean_formula = by_id["runner_local_raw_persistence"]
        broad_formula = by_id["broad_router_over_selection"]
        precision_formula = by_id["precision"]

        self.assertFalse(_synthetic_pass(boolean_formula, boolean_value=0))
        self.assertFalse(_synthetic_pass(boolean_formula, boolean_value=0.0))
        self.assertFalse(_synthetic_pass(count_formula, 0.0))
        self.assertFalse(_synthetic_pass(count_formula, False))
        self.assertFalse(_synthetic_pass(count_formula, -1))
        self.assertFalse(_synthetic_pass(broad_formula, -1, 20))
        self.assertFalse(_synthetic_pass(broad_formula, 21, 20))
        self.assertFalse(_synthetic_pass(broad_formula, 1.0, 20))
        self.assertFalse(_synthetic_pass(broad_formula, 1, 0))
        self.assertFalse(_synthetic_pass(precision_formula, 0, 0))
        self.assertFalse(_synthetic_pass(precision_formula, True, 20))

    def test_every_ratio_zero_denominator_matches_global_value_and_fail_override(self):
        policy = self.document["malformed_and_undefined_policy"]
        ratio_formulas = [
            formula
            for formula in self.document["gate_formulas"]
            if _normative_value_kind(formula) == "ratio"
        ]
        self.assertEqual(len(ratio_formulas), 18)
        for formula in ratio_formulas:
            with self.subTest(gate=formula["gate_id"]):
                value, gate_pass = _zero_denominator_outcome(formula, policy)
                self.assertIs(type(value), float)
                self.assertEqual(value, 0.0)
                self.assertIs(gate_pass, False)
                self.assertFalse(_synthetic_pass(formula, 0, 0))

        broad = next(
            formula
            for formula in ratio_formulas
            if formula["gate_id"] == "broad_router_over_selection"
        )
        mutated = copy.deepcopy(self.document)
        mutated["gate_formulas"][11]["semantic_contract"][
            "undefined_disposition"
        ] = "zero_denominator_value_1_and_gate_fails"
        with self.assertRaises(ContractError):
            _validate_ratio_zero_policy(mutated)
        value, gate_pass = _zero_denominator_outcome(broad, policy)
        self.assertEqual((value, gate_pass), (0.0, False))

    def test_root_logical_and_expands_twenty_by_two_plus_seven(self):
        per_condition = {
            condition: {gate_id: True for gate_id in PER_CONDITION_GATE_IDS}
            for condition in ("current", "reduced")
        }
        complete_run = {gate_id: True for gate_id in COMPLETE_RUN_GATE_IDS}
        self.assertEqual(len(PER_CONDITION_GATE_IDS), 20)
        self.assertEqual(len(COMPLETE_RUN_GATE_IDS), 7)
        self.assertTrue(_root_pass(per_condition, complete_run))

        for condition in ("current", "reduced"):
            for gate_id in PER_CONDITION_GATE_IDS:
                with self.subTest(condition=condition, gate=gate_id):
                    mutated = copy.deepcopy(per_condition)
                    mutated[condition][gate_id] = False
                    self.assertFalse(_root_pass(mutated, complete_run))
        for gate_id in COMPLETE_RUN_GATE_IDS:
            with self.subTest(condition="complete_run", gate=gate_id):
                mutated = dict(complete_run)
                mutated[gate_id] = False
                self.assertFalse(_root_pass(per_condition, mutated))

        pooled_truth = {
            "current": {gate_id: True for gate_id in PER_CONDITION_GATE_IDS},
            "reduced": {gate_id: False for gate_id in PER_CONDITION_GATE_IDS},
        }
        self.assertFalse(_root_pass(pooled_truth, complete_run))
        wrong_type = copy.deepcopy(per_condition)
        wrong_type["current"][PER_CONDITION_GATE_IDS[0]] = 1
        self.assertFalse(_root_pass(wrong_type, complete_run))

    def test_eighty_valid_plus_extra_fails_closed(self):
        schedule = [
            {
                "presentation_index": index,
                "condition": "current" if index % 2 == 0 else "reduced",
                "case_id": f"synthetic-{index // 2:02d}",
            }
            for index in range(80)
        ]
        self.assertEqual(_completed_presentations(schedule, copy.deepcopy(schedule)), 80)
        with_extra = [
            *copy.deepcopy(schedule),
            {
                "presentation_index": 80,
                "condition": "current",
                "case_id": "synthetic-extra",
            },
        ]
        self.assertEqual(_completed_presentations(schedule, with_extra), 0)
        duplicate = [*copy.deepcopy(schedule[:-1]), copy.deepcopy(schedule[0])]
        self.assertEqual(_completed_presentations(schedule, duplicate), 0)

    def test_duplicate_json_key_is_rejected(self):
        with self.assertRaises(ContractError):
            _decode('{"schema_version":"8.0","schema_version":"8.0"}')


if __name__ == "__main__":
    unittest.main()
