from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative); assert spec and spec.loader; module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


checker = load("scripts/check_reduced_four_skill_candidate_v5.py", "aq5_checker_test")


def make_case(case_id: str = "AQ5-H-001", *, mode: str = "automatic", atom: str = "task-contract"):
    adviser = checker.ATOM_TO_ADVISER[atom]; token = f"${adviser}"; prompt = f"Use {token} for one direct decision." if mode == "explicit" else "Define one direct bounded task decision."
    normalized = " ".join(prompt.casefold().split())
    return {"id": case_id, "nonce": f"nonce-{case_id}", "family": f"family-{case_id}", "prompt": prompt, "normalized_prompt": normalized, "prompt_sha256": hashlib.sha256(normalized.encode()).hexdigest(), "mode": mode, "expected_decision_atoms": [atom], "expected_advisers": [adviser], "must_not_select": [item for item in checker.ADVISERS if item != adviser], "reference_triggers": [], "deterministic_reference_expectations": [], "authority_prohibitions": checker.AUTHORITY_PROHIBITIONS, "effect_prohibitions": checker.EFFECT_PROHIBITIONS, "claim_prohibitions": checker.CLAIM_PROHIBITIONS, "exactly_two": False, "precedence": {"applies": False, "candidate_atoms": [], "winner": None, "rule": None}, "declared_invocation": token if mode == "explicit" else None, "condition_blind": True, "blinding_flags": checker.BLINDING_FLAGS, "full_schema_or_template_expected": False}


class CandidateV5Tests(unittest.TestCase):
    def setUp(self): self.candidate = checker.load_candidate(ROOT)

    def draft_candidate(self):
        candidate = copy.deepcopy(self.candidate)
        for row in candidate["evaluator_surface"]["files"]:
            row["sha256"] = f"{checker.UNBOUND}{row['path'].replace('/', '_')}"
        return candidate

    def bound_candidate(self):
        candidate = copy.deepcopy(self.candidate)
        corpus = candidate["corpus"]
        corpus["commit"] = "39fd55df96e99e38d51d5fee13faa6b6294f9c43"
        corpus["tree"] = "b7b9eb94ffe14a59e924ac2c40926e1a2dc513dd"
        for path_key, digest_key in (("schema_path", "schema_sha256"), ("authoring_path", "authoring_sha256"), ("heldout_path", "heldout_sha256")):
            corpus[digest_key] = hashlib.sha256(checker.git_show(ROOT, corpus["commit"], corpus[path_key])).hexdigest()
        corpus["validator_sha256"] = hashlib.sha256((ROOT / corpus["validator_path"]).read_bytes()).hexdigest()
        for row in candidate["evaluator_surface"]["files"]:
            row["sha256"] = hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest()
        return candidate

    def test_unbound_draft_is_structurally_valid_and_live_closed(self):
        draft = self.draft_candidate()
        self.assertEqual(checker.validate_candidate(draft, ROOT, allow_unbound=True), [])
        with self.assertRaisesRegex(ValueError, "AQ5 live execution is unbound"):
            checker.require_bound(draft)

    def test_h2_projection_is_unchanged_and_injective(self):
        protocol = checker.protocol(self.candidate)
        self.assertEqual(checker.canonical_sha256(protocol), self.candidate["h2_protocol"]["projection_sha256"])
        self.assertEqual(checker.atom_mapping(self.candidate), checker.ATOM_TO_ADVISER)
        for condition in ("current", "reduced"): checker.validate_atom_catalog(protocol["conditions"][condition]["atom_catalog"])
        self.assertNotEqual(checker.canonical_sha256(protocol["conditions"]["current"]["atom_catalog"]), checker.canonical_sha256(protocol["conditions"]["reduced"]["atom_catalog"]))

    def test_h2_candidate_projection_must_match_frozen_authority_even_when_binding_digest_is_rehashed(self):
        authority, _ = checker.load_h2(ROOT, checker.H2_AUTHORITY_COMMIT)
        changed = copy.deepcopy(authority); changed["conditions"]["current"]["atom_catalog"][0]["declared_scope"] += " changed"
        candidate = copy.deepcopy(self.candidate)
        candidate["h2_protocol"]["projection_sha256"] = checker.canonical_sha256(checker.h2_projection(authority))
        def load_h2(_root, commit=None): return (changed, b"") if commit == "candidate" else (authority, b"")
        with patch.object(checker, "load_h2", side_effect=load_h2):
            with self.assertRaisesRegex(ValueError, "candidate projection changed"):
                checker.protocol(candidate, ROOT, "candidate")

    def test_h2_catalog_requires_complete_exclusions_and_hides_adviser_mapping(self):
        catalog = copy.deepcopy(checker.protocol(self.candidate)["conditions"]["current"]["atom_catalog"]); catalog[0]["pairwise_exclusions"].pop()
        with self.assertRaisesRegex(ValueError, "exclusions incomplete"):
            checker.validate_atom_catalog(catalog)
        catalog = copy.deepcopy(checker.protocol(self.candidate)["conditions"]["current"]["atom_catalog"]); catalog[0]["declared_scope"] += " codex-task-contract"
        with self.assertRaisesRegex(ValueError, "exposes adviser mapping"):
            checker.validate_atom_catalog(catalog)

    def test_exact_top_level_case_shape_and_explicit_split_representation(self):
        automatic = make_case(); checker.validate_case_shape(automatic)
        explicit = make_case("AQ5-A-033", mode="explicit", atom="engineering-learning"); checker.validate_case_shape(explicit)
        self.assertEqual(explicit["declared_invocation"], "$engineering-learning-loop")
        self.assertEqual(explicit["expected_advisers"], ["engineering-learning-loop"])

    def test_missing_or_renested_reference_triggers_and_noncanonical_ids_are_rejected(self):
        missing = make_case(); del missing["reference_triggers"]
        with self.assertRaisesRegex(ValueError, "top-level shape"):
            checker.validate_case_shape(missing)
        nested = make_case(); nested["hidden_labels"] = {"reference_triggers": nested.pop("reference_triggers")}
        with self.assertRaisesRegex(ValueError, "top-level shape"):
            checker.validate_case_shape(nested)
        for invalid_id in ("aq5-heldout-01", "AQ5-H-000", "AQ5-H-037", "AQ5-A-999"):
            changed = make_case(); changed["id"] = invalid_id
            with self.assertRaisesRegex(ValueError, "identity"):
                checker.validate_case_shape(changed)

    def test_prompt_hash_is_normalized_not_raw_and_must_not_is_adviser_ids(self):
        case = make_case(); case["prompt"] = "Define   ONE direct bounded task decision."
        case["normalized_prompt"] = "define one direct bounded task decision."
        case["prompt_sha256"] = hashlib.sha256(case["normalized_prompt"].encode()).hexdigest(); checker.validate_case_shape(case)
        case["must_not_select"] = ["task-contract"]
        with self.assertRaisesRegex(ValueError, "must_not_select complement"):
            checker.validate_case_shape(case)

    def test_case_atom_ceiling_is_closed(self):
        case = make_case(); case["expected_decision_atoms"] = list(checker.ATOMS[:3]); case["expected_advisers"] = [checker.ATOM_TO_ADVISER[atom] for atom in case["expected_decision_atoms"]]
        with self.assertRaisesRegex(ValueError, "expected_decision_atoms"):
            checker.validate_case_shape(case)

    def test_constraint_parser_distinguishes_exact_ambiguous_and_bare_alias(self):
        self.assertEqual(checker.parse_constraint("Use $codex-task-contract."), {"status": "exact", "atom_id": "task-contract"})
        ambiguous = checker.parse_constraint("Use $codex-task-contract and $engineering-learning-loop.")
        self.assertEqual(ambiguous, {"status": "ambiguous", "atom_id": None})
        self.assertEqual(checker.enforce_constraint([], ambiguous), [])
        self.assertEqual(checker.parse_constraint("Use codex-task-contract."), {"status": "none", "atom_id": None})

    def test_document_requires_exact_frozen_identity_and_32_plus_4_modes(self):
        base, _ = checker.load_base(ROOT, "39fd55df96e99e38d51d5fee13faa6b6294f9c43")
        authoring = checker._json_object(checker.git_show(ROOT, "39fd55df96e99e38d51d5fee13faa6b6294f9c43", checker.CORPUS_AUTHORING_PATH), "authoring")
        self.assertEqual(checker.validate_document_shape(authoring, base), authoring["cases"])
        changed = copy.deepcopy(authoring); changed["cases"][-1]["id"] = "AQ5-H-036"
        with self.assertRaisesRegex(ValueError, "identity set"):
            checker.validate_document_shape(changed, base)
        changed = copy.deepcopy(authoring); changed["cases"][-1]["mode"] = "automatic"; changed["cases"][-1]["declared_invocation"] = None; changed["cases"][-1]["prompt"] = "Define one direct learning decision."; changed["cases"][-1]["normalized_prompt"] = "define one direct learning decision."; changed["cases"][-1]["prompt_sha256"] = hashlib.sha256(changed["cases"][-1]["normalized_prompt"].encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "mode distribution"):
            checker.validate_document_shape(changed, base)
        synthetic = copy.deepcopy(authoring); synthetic["schema_version"] = "5.0"
        with self.assertRaisesRegex(ValueError, "identity"):
            checker.validate_document_shape(synthetic, base)

    def test_case_shape_closes_fixed_fields_and_automatic_tokens(self):
        case = make_case(); case["authority_prohibitions"] = []
        with self.assertRaisesRegex(ValueError, "fixed prohibitions"):
            checker.validate_case_shape(case)
        case = make_case(); case["nonce"] = ""
        with self.assertRaisesRegex(ValueError, "nonce or family"):
            checker.validate_case_shape(case)
        case = make_case(); case["prompt"] += " $codex-task-contract"
        case["normalized_prompt"] = " ".join(case["prompt"].casefold().split())
        case["prompt_sha256"] = hashlib.sha256(case["normalized_prompt"].encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "automatic invocation"):
            checker.validate_case_shape(case)
        case = make_case(); case["precedence"] = {"applies": True, "candidate_atoms": ["task-contract", "verification-strategy"], "winner": "verification-strategy", "rule": "bad"}
        with self.assertRaisesRegex(ValueError, "precedence true branch"):
            checker.validate_case_shape(case)

    def test_reference_expectations_are_exact_minimum_cover_and_incomplete_is_unresolved(self):
        base, _ = checker.load_base(ROOT, "39fd55df96e99e38d51d5fee13faa6b6294f9c43")
        authoring = checker._json_object(checker.git_show(ROOT, "39fd55df96e99e38d51d5fee13faa6b6294f9c43", checker.CORPUS_AUTHORING_PATH), "authoring")
        case = copy.deepcopy(authoring["cases"][0]); checker.validate_case_references(case, base)
        case["deterministic_reference_expectations"] = []
        with self.assertRaisesRegex(ValueError, "expectations mismatch"):
            checker.validate_case_references(case, base)
        shape_case = make_case(); shape_case["deterministic_reference_expectations"] = [{"owner_atom": "task-contract", "trigger_id": "decision-contract", "payload_id": "x"}] * 4
        with self.assertRaisesRegex(ValueError, "expectation mismatch"):
            checker.validate_case_shape(shape_case)
        outcome = checker.resolve_payloads(base, ["architecture-boundary", "verification-evidence"], ["agentic-engineering"])
        self.assertEqual(outcome["status"], "unresolved")
        self.assertLessEqual(len(outcome["records"]), 3)

    def test_manifest_surface_and_canonical_paths_are_closed(self):
        changed = copy.deepcopy(self.candidate); changed["extra"] = True
        self.assertIn("AQ5 candidate top-level surface mismatch", checker.validate_candidate(changed, ROOT, allow_unbound=True))
        changed = copy.deepcopy(self.candidate); changed["corpus"]["schema_path"] = "candidate/chosen.json"
        self.assertIn("AQ5 corpus paths mismatch", checker.validate_candidate(changed, ROOT, allow_unbound=True))
        changed = copy.deepcopy(self.candidate); changed["corpus"]["validator_source"] = "corpus_commit"
        self.assertIn("AQ5 validator source mismatch", checker.validate_candidate(changed, ROOT, allow_unbound=True))

    def test_bound_corpus_bytes_and_digests_are_checked_against_frozen_commit(self):
        candidate = self.bound_candidate()
        self.assertEqual(checker.validate_candidate(candidate, ROOT), [])
        candidate["corpus"]["authoring_sha256"] = "0" * 64
        self.assertIn(f"AQ5 corpus digest mismatch for {checker.CORPUS_AUTHORING_PATH}", checker.validate_candidate(candidate, ROOT))

    def test_working_tree_success_uses_draft_pass_prefix(self):
        output = io.StringIO()
        with patch.object(checker, "load_candidate", return_value=self.draft_candidate()), redirect_stdout(output):
            self.assertEqual(checker.main(["--working-tree", "--allow-unbound-draft"]), 0)
        self.assertTrue(output.getvalue().startswith("DRAFT PASS:"))


if __name__ == "__main__": unittest.main()
