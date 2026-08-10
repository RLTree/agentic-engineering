"""Synthetic-only AQ7 contract tests; no corpus, prompt, label, or result is read."""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import re
import subprocess
import unicodedata
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "evals/foundation-v4/future-activation-v7/activation-schema.json"
H3_COMMIT = "ccbe06be9a2ef5feca4104b6918985ee9c4527c0"
H3_TREE = "dd20449fdc45a73c55adb349d8c828687728ef4d"
POLICY_COMMIT = "c4e661a926e0ace78d9da83f71d9c52d311abb72"
POLICY_TREE = "f2abb05d32a888c9054ef2e7ab3ad0f08547de88"
BASE_PATH = "evals/foundation-v4/reduced-four-skills/candidate.json"
BASE_SHA256 = "854f67bdd03e7121bd20e5513ef61ac806d016b3a5f1d6e5891bf4d9e546eb1f"
BASE_COMMIT = "f09a0544acf4b7a95fff796434273511a0683ca9"
BASE_TREE = "38c8c8adf3bb633d33200df1ec65f33e985ae244"


def frozen_json(commit: str, path: str) -> tuple[dict, str]:
    raw = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def commit_tree(commit: str) -> str:
    return subprocess.check_output(["git", "rev-parse", f"{commit}^{{tree}}"], cwd=ROOT, text=True).strip()


def authority_inputs() -> tuple[dict, dict, dict, dict, dict]:
    assert commit_tree(H3_COMMIT) == H3_TREE
    assert commit_tree(POLICY_COMMIT) == POLICY_TREE
    assert commit_tree(BASE_COMMIT) == BASE_TREE
    h3, h3_sha = frozen_json(H3_COMMIT, "evals/foundation-v4/decision-certificate-protocol-v6.json")
    selector, selector_sha = frozen_json(H3_COMMIT, "evals/foundation-v4/decision-certificate-selector-output-schema-v6.json")
    policy, policy_sha = frozen_json(POLICY_COMMIT, "evals/foundation-v4/decision-certificate-reference-policy-v6.json")
    base_bytes = subprocess.check_output(["git", "show", f"{BASE_COMMIT}:{BASE_PATH}"], cwd=ROOT)
    assert hashlib.sha256(base_bytes).hexdigest() == BASE_SHA256
    assert (ROOT / BASE_PATH).read_bytes() == base_bytes
    return h3, selector, policy, json.loads(base_bytes), {"h3": h3_sha, "selector": selector_sha, "policy": policy_sha}


def ordered_facts(h3: dict, state: str = "absent") -> list[dict]:
    return [{"predicate_id": name, "state": state} for name in h3["predicate_order"]]


def select_atoms(h3: dict, facts: list[dict]) -> tuple[str, list[str]]:
    states = {fact["predicate_id"]: fact["state"] for fact in facts}
    eligible = []
    for rule in h3["deterministic_selection"]["eligibility_rules"]:
        relevant = [*rule["positive_predicates"], rule["exclusion_predicate"]]
        if any(states[name] == "uncertain" for name in relevant):
            continue
        if any(states[name] == "present" for name in rule["positive_predicates"]) and states[rule["exclusion_predicate"]] == "absent":
            eligible.append(rule["derived_atom"])
    return ("cap_exceeded", []) if len(eligible) > h3["deterministic_selection"]["selection_cap"] else ("automatic", eligible)


def explicit_status(h3: dict, task_text: str) -> tuple[str, list[str]]:
    import re
    import unicodedata

    text = unicodedata.normalize("NFC", task_text)
    exact = re.findall(h3["explicit_constraint"]["qualified_invocation_grammar"]["exact_pattern"], text)
    invocation_like = re.findall(h3["explicit_constraint"]["qualified_invocation_grammar"]["invocation_like_pattern"], text)
    if any(token not in exact for token in invocation_like):
        return "unrecognized", []
    if len(exact) > 1:
        return "ambiguous", []
    if len(exact) == 1:
        mapping = dict((row["token"], row["logical_atom"]) for row in h3["explicit_constraint"]["ordered_token_to_logical_atom"])
        return "exact", [mapping[exact[0]]]
    return "automatic", []


def derive_requests(h3: dict, policy: dict, facts: list[dict], status: str, selected_atoms: list[str]) -> list[dict]:
    if status not in policy["request_derivation"]["emitting_selection_statuses"]:
        return []
    states = {fact["predicate_id"]: fact["state"] for fact in facts}
    rules = {rule["derived_atom"]: rule for rule in h3["deterministic_selection"]["eligibility_rules"]}
    emitted = []
    for atom in selected_atoms:
        if states[rules[atom]["exclusion_predicate"]] == "present":
            continue
        for row in policy["request_derivation"]["ordered_mapping_rows"]:
            if row["atom_id"] == atom and states[row["predicate_id"]] == "present":
                request = {"owner_adviser_id": row["adviser_id"], "trigger_id": row["trigger_id"]}
                if request not in emitted:
                    emitted.append(request)
                break
    return emitted


def canonical_cover(policy: dict, base: dict, requests: list[dict]) -> tuple[str, list[dict]]:
    if not requests:
        return "resolved", []
    payloads = []
    for skill in base["skills"]:
        for reference in skill["references"]:
            payloads.append({"owner_adviser_id": skill["id"], "payload_id": reference["payload_id"], "sha256": reference["sha256"], "trigger_ids": reference["trigger_ids"]})
    eligible = [payload for payload in payloads if any(payload["owner_adviser_id"] == request["owner_adviser_id"] and request["trigger_id"] in payload["trigger_ids"] for request in requests)]
    candidates = []
    for count in range(policy["canonical_cover"]["maximum_payloads"] + 1):
        for subset in itertools.combinations(eligible, count):
            if all(any(payload["owner_adviser_id"] == request["owner_adviser_id"] and request["trigger_id"] in payload["trigger_ids"] for payload in subset) for request in requests):
                candidates.append(subset)
        if candidates:
            chosen = min(candidates, key=lambda subset: tuple(sorted(item["payload_id"] for item in subset)))
            return "resolved", [{"owner_adviser_id": item["owner_adviser_id"], "payload_id": item["payload_id"], "sha256": item["sha256"]} for item in sorted(chosen, key=lambda item: item["payload_id"])]
    return "unresolved", []


def synthetic_case(h3: dict, policy: dict, base: dict, number: int) -> dict:
    atoms = ["topology-control-boundary", "task-contract", "verification-strategy", "engineering-learning"]
    advisers = ["agentic-engineering", "codex-task-contract", "verification-strategy-engineering", "engineering-learning-loop"]
    atom = atoms[(number - 1) // 6] if number <= 24 else (atoms[number - 33] if number >= 33 else None)
    family = "single-owner" if number <= 24 else "native-no-advice" if number <= 28 else "exactly-two" if number <= 30 else "exclusion-or-uncertainty-near-neighbor" if number <= 32 else "exact-explicit"
    explicit = number >= 33
    token = ["$agentic-engineering", "$codex-task-contract", "$verification-strategy-engineering", "$engineering-learning-loop"][number - 33] if explicit else None
    facts = ordered_facts(h3)
    if number <= 24:
        facts[2 * atoms.index(atom)]["state"] = "present"
    elif family == "exactly-two":
        facts[0]["state"] = facts[2]["state"] = "present"
    elif family == "exclusion-or-uncertainty-near-neighbor":
        facts[0]["state"] = "present"
        facts[8]["state"] = "present" if number == 31 else "uncertain"
    if explicit:
        status, selected = explicit_status(h3, f"Synthetic packet {token}.")
    else:
        status, selected = select_atoms(h3, facts)
    selected_advisers = [advisers[atoms.index(item)] for item in selected]
    requests = derive_requests(h3, policy, facts, status, selected)
    resolved_status, payloads = canonical_cover(policy, base, requests)
    task_text = f"Synthetic packet {token}." if token else f"Synthetic packet {number}."
    prompt_sha256 = hashlib.sha256(unicodedata.normalize("NFC", task_text).encode()).hexdigest()
    return {
        "case_id": f"AQ7-A-{number:03d}", "case_kind": "explicit" if explicit else "automatic", "case_family": family,
        "family_atom": atom, "near_neighbor_kind": "exclusion" if number == 31 else "uncertainty" if number == 32 else None, "exactly_two": family == "exactly-two", "nonce_sha256": f"{number:064x}", "prompt_sha256": prompt_sha256,
        "packet": {"task_text": task_text},
        "grading": {
            "expected_predicate_facts": facts, "expected_selected_atoms": selected,
            "expected_selection_status": status,
            "expected_selection_constraint": {"parse_status": "exact", "selected_atom": atom, "qualified_tokens": [token], "invocation_like_tokens": [token]} if explicit else {"parse_status": "no_invocation_like", "selected_atom": None, "qualified_tokens": [], "invocation_like_tokens": []},
            "expected_advisers": selected_advisers,
            "expected_must_not_select_advisers": [adviser for adviser in advisers if adviser not in selected_advisers],
            "expected_reference_requests": requests,
            "deterministic_reference_expectations": {"status": resolved_status, "resolved_payload_count": len(payloads), "payloads": payloads, "derivation": "H3+frozen-reference-policy+base-candidate"}
        }
    }


def synthetic_root(h3: dict, policy: dict, base: dict) -> dict:
    cases = [synthetic_case(h3, policy, base, number) for number in range(1, 37)]
    return {
        "schema_version": "7.0", "corpus_id": "AQ7-authoring", "split": "authoring", "status": "future-only-unconsumed", "claim_ceiling": "structural-only",
        "authority": {"h3_protocol": {"commit": H3_COMMIT, "tree": H3_TREE, "path": "evals/foundation-v4/decision-certificate-protocol-v6.json", "sha256": "9ad483a26fe339f81c947507de9c1c66d54b2823a38f68b1c5ee7fdf5c426f84"}, "h3_selector_schema": {"commit": H3_COMMIT, "tree": H3_TREE, "path": "evals/foundation-v4/decision-certificate-selector-output-schema-v6.json", "sha256": "9742f2255fed5452df52f9da789a6f2fd72e89aa94c3c6847fad6944445f5b25"}, "reference_policy": {"commit": POLICY_COMMIT, "tree": POLICY_TREE, "path": "evals/foundation-v4/decision-certificate-reference-policy-v6.json", "sha256": "92982c278e33ff52edce1ba2a16082afb3ecc1989d8333a77eee9ca0911fee19"}, "base_candidate": {"commit": "f09a0544acf4b7a95fff796434273511a0683ca9", "tree": "38c8c8adf3bb633d33200df1ec65f33e985ae244", "path": BASE_PATH, "sha256": BASE_SHA256}},
        "blinding": {"corpus_fields_exposed_to_model": ["task_text"], "runner_code_owned_context": ["instruction", "predicate_order"], "grading_only_fields": ["expected_predicate_facts", "expected_selected_atoms", "expected_selection_status", "expected_selection_constraint", "expected_advisers", "expected_must_not_select_advisers", "expected_reference_requests", "deterministic_reference_expectations"], "labels_are_not_packet_or_inference_inputs": True, "fresh_blinded_corpus_required": True},
        "precedence": {"schema_valid_exact_explicit_overrides_automatic_eligibility": True, "multiple_qualified_tokens_are_ambiguous": True, "unrecognized_invocation_like_token_blocks_selection": True, "cap_exceeded_selects_no_atoms": True},
        "prohibitions": ["no_model_visible_reference_policy", "no_authority_assignment", "no_policy_adoption", "no_effect_execution", "no_external_action", "no_completion_claim", "no_efficacy_claim", "no_product_claim", "no_runtime_claim", "no_provider_claim", "no_promotion_claim"],
        "freeze_controls": {"future_only": True, "no_model_call": True, "no_result_inputs": True, "no_replay_inputs": True, "derived_projection_before_freeze": True, "nonce_sha256_must_be_unique_within_split": True, "prompt_sha256_must_be_unique_within_split": True, "freeze_commit_permitted": True},
        "nonce_source_contract": {"split_scope": "AQ7-authoring", "nonce_source": "future-split-local", "hash_algorithm": "SHA-256"},
        "case_count": 36, "cases": cases
    }


def enforce_freeze_invariants(root: dict) -> None:
    """The two cross-case invariants are declared by the schema extension."""
    for field in ("nonce_sha256", "prompt_sha256"):
        values = [case[field] for case in root["cases"]]
        assert len(values) == len(set(values)), f"duplicate packet.{field}"
    for case in root["cases"]:
        expected = hashlib.sha256(unicodedata.normalize("NFC", case["packet"]["task_text"]).encode()).hexdigest()
        assert case["prompt_sha256"] == expected, "prompt_sha256 must hash NFC task_text"


def enforce_grading_only_invariants(h3: dict, policy: dict, base: dict, case: dict) -> None:
    grading = case["grading"]
    facts = grading["expected_predicate_facts"]
    if case["case_kind"] == "explicit":
        status, atoms = explicit_status(h3, case["packet"]["task_text"])
        task = unicodedata.normalize("NFC", case["packet"]["task_text"])
        grammar = h3["explicit_constraint"]["qualified_invocation_grammar"]
        qualified_tokens = re.findall(grammar["exact_pattern"], task)
        invocation_like_tokens = re.findall(grammar["invocation_like_pattern"], task)
        assert status == "exact"
        assert grading["expected_selection_constraint"]["parse_status"] == "exact"
        assert grading["expected_selection_constraint"]["selected_atom"] == atoms[0]
        assert grading["expected_selection_constraint"]["qualified_tokens"] == qualified_tokens
        assert grading["expected_selection_constraint"]["invocation_like_tokens"] == invocation_like_tokens
        assert case["case_family"] == "exact-explicit" and case["family_atom"] == atoms[0] and not case["exactly_two"]
    else:
        normalized_task = re.sub(r"[-_\s]", "", case["packet"]["task_text"]).casefold()
        assert "$" not in case["packet"]["task_text"]
        assert not any(name in normalized_task for name in ("agenticengineering", "codextaskcontract", "verificationstrategyengineering", "engineeringlearningloop"))
        status, atoms = select_atoms(h3, facts)
        assert grading["expected_selection_constraint"] == {"parse_status": "no_invocation_like", "selected_atom": None, "qualified_tokens": [], "invocation_like_tokens": []}
        if case["case_family"] == "single-owner":
            assert len(atoms) == 1 and case["family_atom"] == atoms[0] and not case["exactly_two"]
        elif case["case_family"] == "exactly-two":
            assert len(atoms) == 2 and case["family_atom"] is None and case["exactly_two"]
        elif case["case_family"] == "native-no-advice":
            assert not atoms and case["family_atom"] is None and not case["exactly_two"]
        else:
            assert case["case_family"] == "exclusion-or-uncertainty-near-neighbor"
            assert not atoms and case["family_atom"] is None and not case["exactly_two"]
            states = {fact["predicate_id"]: fact["state"] for fact in facts}
            matching = []
            for rule in h3["deterministic_selection"]["eligibility_rules"]:
                positive = any(states[predicate] == "present" for predicate in rule["positive_predicates"])
                exclusion = states[rule["exclusion_predicate"]]
                if positive and exclusion == "present":
                    matching.append("exclusion")
                if positive and any(states[predicate] == "uncertain" for predicate in [*rule["positive_predicates"], rule["exclusion_predicate"]]):
                    matching.append("uncertainty")
            assert matching == [case["near_neighbor_kind"]]
    assert (status, atoms) == (grading["expected_selection_status"], grading["expected_selected_atoms"])
    atom_to_adviser = {row["logical_atom"]: row["token"][1:] for row in h3["explicit_constraint"]["ordered_token_to_logical_atom"]}
    assert grading["expected_advisers"] == [atom_to_adviser[atom] for atom in atoms]
    all_advisers = [row["token"][1:] for row in h3["explicit_constraint"]["ordered_token_to_logical_atom"]]
    assert grading["expected_must_not_select_advisers"] == [adviser for adviser in all_advisers if adviser not in grading["expected_advisers"]]
    assert grading["expected_reference_requests"] == derive_requests(h3, policy, facts, status, atoms)
    projection = grading["deterministic_reference_expectations"]
    assert projection["status"] == "resolved"
    assert projection["resolved_payload_count"] == len(projection["payloads"])
    assert (projection["status"], projection["payloads"]) == canonical_cover(policy, base, grading["expected_reference_requests"])


def check_contract_is_closed_and_validates_synthetic_split() -> None:
    h3, selector, policy, base, hashes = authority_inputs()
    assert h3["schema_version"] == policy["schema_version"] == "6.0"
    assert h3["status"] == policy["status"] == "frozen-proposal-only"
    assert h3["qualification_controls"]["fresh_blinded_corpus_required"] is True
    assert policy["authority_basis"]["base_candidate"]["sha256"] == BASE_SHA256
    assert selector["properties"]["predicate_facts"]["minItems"] == 12
    assert hashes["h3"] == "9ad483a26fe339f81c947507de9c1c66d54b2823a38f68b1c5ee7fdf5c426f84"
    assert hashes["selector"] == "9742f2255fed5452df52f9da789a6f2fd72e89aa94c3c6847fad6944445f5b25"
    assert hashes["policy"] == "92982c278e33ff52edce1ba2a16082afb3ecc1989d8333a77eee9ca0911fee19"
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema["properties"]["status"] == {"const": "future-only-unconsumed"}
    root = synthetic_root(h3, policy, base)
    jsonschema.Draft202012Validator(schema).validate(root)
    assert root["blinding"]["corpus_fields_exposed_to_model"] == ["task_text"]
    assert root["blinding"]["runner_code_owned_context"] == ["instruction", "predicate_order"]
    assert schema["x-freeze-invariants"]["pairwise_unique_case_fields"] == ["nonce_sha256", "prompt_sha256"]
    enforce_freeze_invariants(root)
    for case in root["cases"]:
        enforce_grading_only_invariants(h3, policy, base, case)


def check_schema_rejects_closure_order_and_status_violations() -> None:
    h3, _, policy, base, _ = authority_inputs()
    validator = jsonschema.Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))
    root = synthetic_root(h3, policy, base)
    broken = copy.deepcopy(root); broken["unexpected"] = True
    assert list(validator.iter_errors(broken))
    broken = copy.deepcopy(root); broken["cases"][0]["grading"]["expected_predicate_facts"][0], broken["cases"][0]["grading"]["expected_predicate_facts"][1] = broken["cases"][0]["grading"]["expected_predicate_facts"][1], broken["cases"][0]["grading"]["expected_predicate_facts"][0]
    assert list(validator.iter_errors(broken))
    broken = copy.deepcopy(root); broken["cases"][0]["grading"]["expected_selection_status"] = "exact"
    assert list(validator.iter_errors(broken))
    broken = copy.deepcopy(root); broken["cases"][0]["packet"]["task_text"] = "Synthetic $agentic-engineering packet."
    assert list(validator.iter_errors(broken))
    broken = copy.deepcopy(root); broken["cases"][1]["case_id"] = "AQ7-A-001"
    assert list(validator.iter_errors(broken))
    broken = copy.deepcopy(root); broken["cases"][0]["case_family"] = "native-no-advice"; broken["cases"][0]["family_atom"] = None
    assert list(validator.iter_errors(broken))
    broken = copy.deepcopy(root); broken["nonce_source_contract"]["split_scope"] = "AQ7-heldout"
    assert list(validator.iter_errors(broken))
    duplicate = copy.deepcopy(root); duplicate["cases"][1]["nonce_sha256"] = duplicate["cases"][0]["nonce_sha256"]
    try:
        enforce_freeze_invariants(duplicate)
    except AssertionError:
        pass
    else:
        raise AssertionError("duplicate nonce must fail the declared freeze invariant")
    bad_explicit = copy.deepcopy(root["cases"][32]); bad_explicit["packet"]["task_text"] += " $unknown-skill"
    try:
        enforce_grading_only_invariants(h3, policy, base, bad_explicit)
    except AssertionError:
        pass
    else:
        raise AssertionError("an explicit packet with another invocation-like token must fail")
    bad_projection = copy.deepcopy(root["cases"][32]); bad_projection["grading"]["deterministic_reference_expectations"]["resolved_payload_count"] = 1
    try:
        enforce_grading_only_invariants(h3, policy, base, bad_projection)
    except AssertionError:
        pass
    else:
        raise AssertionError("resolved payload count must equal the canonical payload tuple length")
    wrong_single = copy.deepcopy(root["cases"][0]); wrong_single["family_atom"] = "task-contract"
    try:
        enforce_grading_only_invariants(h3, policy, base, wrong_single)
    except AssertionError:
        pass
    else:
        raise AssertionError("single-owner family_atom must equal its sole derived atom")
    wrong_explicit_constraint = copy.deepcopy(root["cases"][32]); wrong_explicit_constraint["grading"]["expected_selection_constraint"]["qualified_tokens"] = ["$codex-task-contract"]
    try:
        enforce_grading_only_invariants(h3, policy, base, wrong_explicit_constraint)
    except AssertionError:
        pass
    else:
        raise AssertionError("explicit parser arrays must equal the task parse")
    wrong_two = copy.deepcopy(root["cases"][28]); wrong_two["grading"]["expected_predicate_facts"][2]["state"] = "absent"
    try:
        enforce_grading_only_invariants(h3, policy, base, wrong_two)
    except AssertionError:
        pass
    else:
        raise AssertionError("exactly-two family must derive exactly two atoms")
    reversed_complement = copy.deepcopy(root["cases"][0]); reversed_complement["grading"]["expected_must_not_select_advisers"].reverse()
    try:
        enforce_grading_only_invariants(h3, policy, base, reversed_complement)
    except AssertionError:
        pass
    else:
        raise AssertionError("must-not adviser complement must retain frozen adviser order")
    all_absent_near_neighbor = copy.deepcopy(root["cases"][30])
    for fact in all_absent_near_neighbor["grading"]["expected_predicate_facts"]:
        fact["state"] = "absent"
    try:
        enforce_grading_only_invariants(h3, policy, base, all_absent_near_neighbor)
    except AssertionError:
        pass
    else:
        raise AssertionError("near-neighbor must retain a same-rule positive and exclusion/uncertainty structure")
    wrong_near_kind = copy.deepcopy(root["cases"][30]); wrong_near_kind["near_neighbor_kind"] = "uncertainty"
    try:
        enforce_grading_only_invariants(h3, policy, base, wrong_near_kind)
    except AssertionError:
        pass
    else:
        raise AssertionError("near-neighbor kind must equal its derived H3 structure")
    for forbidden_text in ("$unknown-skill", "Agentic Engineering", "CODEX-TASK-CONTRACT", "verification strategy engineering"):
        bad_automatic = copy.deepcopy(root["cases"][0]); bad_automatic["packet"]["task_text"] = forbidden_text
        try:
            enforce_grading_only_invariants(h3, policy, base, bad_automatic)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"automatic packet must reject {forbidden_text!r}")
    mixed_explicit = copy.deepcopy(root["cases"][32]); mixed_explicit["packet"]["task_text"] += " $codex-task-contract"
    try:
        enforce_grading_only_invariants(h3, policy, base, mixed_explicit)
    except AssertionError:
        pass
    else:
        raise AssertionError("multiple explicit tokens must fail")
    for mutate in (
        lambda case: case["grading"].update(expected_selected_atoms=[]),
        lambda case: case["grading"].update(expected_advisers=[]),
        lambda case: case["grading"].update(expected_must_not_select_advisers=[]),
        lambda case: case["grading"].update(expected_reference_requests=[]),
        lambda case: case["grading"]["expected_selection_constraint"].update(parse_status="ambiguous"),
        lambda case: case["grading"]["deterministic_reference_expectations"].update(payloads=[]),
    ):
        mutated = copy.deepcopy(root["cases"][0]); mutate(mutated)
        try:
            enforce_grading_only_invariants(h3, policy, base, mutated)
        except AssertionError:
            pass
        else:
            raise AssertionError("every downstream grading field must be mechanically derived")


def check_h3_status_branches_and_reference_projection_are_mechanical() -> None:
    h3, _, policy, base, _ = authority_inputs()
    facts = ordered_facts(h3)
    for fact in facts[:8]: fact["state"] = "present"
    for fact in facts[8:]: fact["state"] = "absent"
    assert select_atoms(h3, facts) == ("cap_exceeded", [])
    assert explicit_status(h3, "Use $agentic-engineering.") == ("exact", ["topology-control-boundary"])
    assert explicit_status(h3, "Use $agentic-engineering and $codex-task-contract.")[0] == "ambiguous"
    assert explicit_status(h3, "Use $unknown-skill.")[0] == "unrecognized"
    facts = ordered_facts(h3); facts[0]["state"] = "uncertain"; facts[1]["state"] = "present"
    assert select_atoms(h3, facts) == ("automatic", [])
    facts = ordered_facts(h3); facts[0]["state"] = facts[2]["state"] = "present"
    status, atoms = select_atoms(h3, facts)
    requests = derive_requests(h3, policy, facts, status, atoms)
    assert (status, atoms) == ("automatic", ["topology-control-boundary", "task-contract"])
    assert requests == [{"owner_adviser_id": "agentic-engineering", "trigger_id": "decomposition-boundary"}, {"owner_adviser_id": "codex-task-contract", "trigger_id": "decision-contract"}]
    status, payloads = canonical_cover(policy, base, requests)
    assert status == "resolved"
    assert len(payloads) == 2
    assert [(item["owner_adviser_id"], item["payload_id"], item["sha256"]) for item in payloads] == [("agentic-engineering", "aq-agentic-seven-layer", "b32a84de05a0bbebac86064f37be4c9b6e79a0f70b5c83a23d8073e9091a2232"), ("codex-task-contract", "aq-contract-vocabulary", "0a19fbde8ab13b459931e4f353dfbe5ae95108e21414cc5d6087930c5c13c4bb")]


class TestFutureActivationContractV7(unittest.TestCase):
    def test_contract_is_closed_and_validates_synthetic_split(self) -> None:
        check_contract_is_closed_and_validates_synthetic_split()

    def test_schema_rejects_closure_order_and_status_violations(self) -> None:
        check_schema_rejects_closure_order_and_status_violations()

    def test_h3_status_branches_and_reference_projection_are_mechanical(self) -> None:
        check_h3_status_branches_and_reference_projection_are_mechanical()


def main() -> int:
    tests = [
        check_contract_is_closed_and_validates_synthetic_split,
        check_schema_rejects_closure_order_and_status_violations,
        check_h3_status_branches_and_reference_projection_are_mechanical,
    ]
    assert tests, "nonzero test count is required"
    for test in tests:
        test()
    print(f"{len(tests)} synthetic AQ7 contract tests passed")
    return len(tests)


if __name__ == "__main__":
    assert main() > 0
