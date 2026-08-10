"""Synthetic-only tests for the pure AQ8 resolver and custody checker."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_reduced_four_skill_candidate_v8 as checker  # noqa: E402
import resolve_h4_unresolved_decision_graph_v8 as resolver  # noqa: E402


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


PROTOCOL = load(checker.PROTOCOL_PATH)
SCHEMA = load(checker.SELECTOR_SCHEMA_PATH)
RUNTIME_SCHEMA = load(checker.RUNTIME_SELECTOR_SCHEMA_PATH)
POLICY = load(checker.REFERENCE_POLICY_PATH)
BASE = load(checker.BASE_PATH)
ADAPTER = load(checker.ADAPTER_PATH)
SLOTS = ("s0", "s1", "s2", "s3")
PAIRS = (("s0", "s1"), ("s0", "s2"), ("s0", "s3"), ("s1", "s2"), ("s1", "s3"), ("s2", "s3"))


def graph(*, states: dict[str, str] | None = None,
          relations: dict[tuple[str, str], str] | None = None,
          needs: dict[str, str] | None = None) -> dict:
    states = states or {}
    relations = relations or {}
    needs = needs or {}
    state_rows = [{"slot_id": slot, "state": states.get(slot, "resolved_or_absent")} for slot in SLOTS]
    state_map = {row["slot_id"]: row["state"] for row in state_rows}
    relation_rows = []
    for left, right in PAIRS:
        default = (
            "uncertain"
            if "uncertain" in (state_map[left], state_map[right])
            else ("unrelated" if "resolved_or_absent" in (state_map[left], state_map[right]) else "independent")
        )
        relation_rows.append({"left_slot": left, "right_slot": right, "relation": relations.get((left, right), default)})
    return {
        "candidate_states": state_rows,
        "pairwise_relations": relation_rows,
        "reference_needs": [{"slot_id": slot, "need": needs.get(slot, "none")} for slot in SLOTS],
    }


def valid_metric_binding() -> dict[str, str]:
    return copy.deepcopy(checker.METRIC_BINDING)


def execution_contract(metric: dict[str, str]) -> dict:
    return {
        "conditions": [{"id": name, "condition_guidance_canonical_sha256": digest} for name, digest in checker.CONDITIONS],
        "model": {"id": "gpt-5.5", "reasoning_effort": "medium"},
        "schedule": {"seed": "aq8-h4-v1", "qualification_cases": 40, "presentations": 80, "strict_alternation": True},
        "packet": {
            "keys": ["instruction", "task_text", "slot_order", "pair_order", "condition_guidance", "support_legend"],
            "sole_condition_variance": "condition_guidance",
            "model_output_roots": ["candidate_states", "pairwise_relations", "reference_needs"],
            "candidate_state_count": 4,
            "pair_relation_count": 6,
            "reference_need_count": 4,
        },
        "isolation": {
            "fresh_empty_cwd": True,
            "ephemeral_context_requested": True,
            "sandbox": "read-only",
            "approval_policy": "never",
            "tools_enabled": False,
            "apps_enabled": False,
            "plugins_enabled": False,
            "mcp_enabled": False,
            "isolated_codex_home": True,
            "isolated_home_mode": "0700",
            "auth_source": "owner-owned-regular-nonsymlink-0600",
            "auth_seed": "private-copy-0600-only",
            "explicit_subprocess_env": True,
            "exact_single_probe_input": True,
            "temp_cleanup_required": True,
            "global_agents_loaded": False,
        },
        "integrity": {
            "unique_contexts_required": 80,
            "content_retries": 0,
            "canary_precompletion_infrastructure_retries_max": 1,
            "runner_local_raw_trajectories_persisted": False,
            "provider_raw_trajectory_retention_status": "unknown",
            "held_out_outcome_use": False,
        },
        "authorities": {
            "h4_commit": checker.H4_BINDING["commit"],
            "h4_tree": checker.H4_BINDING["tree"],
            "h4_sha256": checker.H4_BINDING["sha256"],
            "gate_commit": checker.GATE_BINDING["commit"],
            "gate_tree": checker.GATE_BINDING["tree"],
            "gate_sha256": checker.GATE_BINDING["sha256"],
            "metric_commit": metric["commit"],
            "metric_tree": metric["tree"],
            "metric_sha256": metric["sha256"],
            "semantic_selector_schema_sha256": checker.SCHEMA_BINDING["sha256"],
            "runtime_selector_schema_sha256": checker.RUNTIME_SCHEMA_BINDING["sha256"],
        },
        "result_claims": {
            "maximum_claim": "unattested deterministic AQ8 unresolved-decision graph telemetry from supplied observations",
            "behavioral_qualification_proven": False,
            "runtime_provenance_proven": False,
            "provider_identity_proven": False,
            "telemetry_attested": False,
            "product_behavior_proven": False,
            "promotion_eligible": False,
        },
    }


def resolved_manifest(metric: dict[str, str]) -> dict:
    manifest = load(checker.MANIFEST_PATH)
    if manifest["metric_authority"] != metric:
        raise AssertionError("test metric binding drift")
    return manifest


class ResolverTests(unittest.TestCase):
    def test_semantic_schema_and_order_are_exact(self) -> None:
        value = graph(states={"s0": "unresolved"})
        canonical = resolver.validate_graph_output(value, PROTOCOL, SCHEMA)
        self.assertEqual(canonical, value)
        for mutate in (
            lambda item: item.__setitem__("selected_slots", []),
            lambda item: item["candidate_states"].reverse(),
            lambda item: item["pairwise_relations"].reverse(),
            lambda item: item["reference_needs"].reverse(),
            lambda item: item["candidate_states"][0].__setitem__("state", "complete"),
        ):
            broken = copy.deepcopy(value)
            mutate(broken)
            with self.assertRaises(resolver.ResolverError):
                resolver.validate_graph_output(broken, PROTOCOL, SCHEMA)
        widened = copy.deepcopy(SCHEMA)
        widened["additionalProperties"] = True
        with self.assertRaises(resolver.ResolverError):
            resolver.validate_graph_output(value, PROTOCOL, widened)
        bool_as_int = copy.deepcopy(SCHEMA)
        bool_as_int["additionalProperties"] = 0
        with self.assertRaises(resolver.ResolverError):
            resolver.validate_graph_output(value, PROTOCOL, bool_as_int)

    def test_graph_precedence_chain_closure_cycle_uncertainty_and_cap(self) -> None:
        chain = graph(
            states={"s0": "unresolved", "s1": "unresolved", "s2": "unresolved"},
            relations={
                ("s0", "s1"): "left_controls_right_downstream",
                ("s0", "s2"): "left_controls_right_downstream",
                ("s1", "s2"): "left_controls_right_downstream",
            },
        )
        self.assertEqual(resolver.resolve_graph("task", chain, PROTOCOL, POLICY, BASE)["selected_slots"], ["s0"])

        closure_missing = copy.deepcopy(chain)
        closure_missing["pairwise_relations"][1]["relation"] = "independent"
        self.assertEqual(resolver.resolve_graph("task", closure_missing, PROTOCOL, POLICY, BASE)["graph_status"], "graph_invalid")

        cycle = graph(
            states={"s0": "unresolved", "s1": "unresolved", "s2": "unresolved"},
            relations={
                ("s0", "s1"): "left_controls_right_downstream",
                ("s0", "s2"): "right_controls_left_downstream",
                ("s1", "s2"): "left_controls_right_downstream",
            },
        )
        self.assertEqual(resolver.resolve_graph("task", cycle, PROTOCOL, POLICY, BASE)["graph_status"], "graph_cycle")

        uncertain = graph(states={"s0": "uncertain"})
        self.assertEqual(resolver.resolve_graph("task", uncertain, PROTOCOL, POLICY, BASE)["selection_status"], "graph_uncertain")
        capped = graph(states={"s0": "unresolved", "s1": "unresolved", "s2": "unresolved"})
        result = resolver.resolve_graph("task", capped, PROTOCOL, POLICY, BASE)
        self.assertEqual((result["root_slots"], result["selection_status"], result["selected_slots"]), (["s0", "s1", "s2"], "cap_exceeded", []))

    def test_unicode_invocation_precedence_and_graph_telemetry(self) -> None:
        invalid = graph(
            states={"s0": "unresolved", "s1": "unresolved"},
            relations={("s0", "s1"): "unrelated"},
        )
        exact = resolver.resolve_graph("Use $verification-strategy-engineering.", invalid, PROTOCOL, POLICY, BASE)
        self.assertEqual((exact["graph_status"], exact["selection_status"], exact["selected_slots"]), ("graph_invalid", "exact", ["s2"]))
        self.assertEqual(resolver.resolve_graph("$agentic-engineering $agentic-engineering", graph(), PROTOCOL, POLICY, BASE)["selection_status"], "ambiguous")
        self.assertEqual(resolver.resolve_graph("$agentic-engineering $unknown", graph(), PROTOCOL, POLICY, BASE)["selection_status"], "unrecognized")
        for token in ("$agentic-engineering", "$codex-task-contract"):
            for text in (f"Use ({token}).", f"Use {token}, then stop.", f" {token} "):
                self.assertEqual(
                    resolver.resolve_graph(text, graph(), PROTOCOL, POLICY, BASE)["selection_status"],
                    "exact",
                )
        for unknown in ("$codex-task-contract-extra", "$Agentic-engineering", "$unknown99-tail"):
            self.assertEqual(
                resolver.resolve_graph(unknown, graph(), PROTOCOL, POLICY, BASE)["selection_status"],
                "unrecognized",
            )
        for adjacent in ("é", "β", "\u0301", "\u200d", "\u203f"):
            for text in (
                f"{adjacent}$agentic-engineering",
                f"$agentic-engineering{adjacent}",
            ):
                self.assertEqual(
                    resolver.resolve_graph(text, graph(), PROTOCOL, POLICY, BASE)["selection_status"],
                    "automatic",
                )

    def test_reference_resolution_is_route_independent_and_owner_qualified(self) -> None:
        routed = graph(states={"s0": "unresolved"}, needs={"s0": "primary"})
        result = resolver.resolve_graph("task", routed, PROTOCOL, POLICY, BASE)
        self.assertEqual(result["selected_adviser_ids"], ["agentic-engineering"])
        self.assertEqual(result["reference_requests"], [{"owner_adviser_id": "agentic-engineering", "trigger_id": "decomposition-boundary"}])
        self.assertEqual(
            result["reference_resolution"],
            {"status": "resolved", "resolved_count": 1, "canonical_payload_id_tuple": ["aq-agentic-seven-layer"]},
        )
        broken = graph(states={"s0": "unresolved"}, needs={"s1": "primary"})
        with self.assertRaises(resolver.ResolverError):
            resolver.resolve_graph("task", broken, PROTOCOL, POLICY, BASE)
        changed = graph(states={"s0": "unresolved"}, needs={"s0": "uncertain"})
        uncertain = resolver.resolve_graph("task", changed, PROTOCOL, POLICY, BASE)
        self.assertEqual((uncertain["selected_slots"], uncertain["reference_uncertain_slots"]), (["s0"], ["s0"]))

    def test_canonical_cover_owner_tie_cap_and_unresolved_branches(self) -> None:
        request = [{"owner_adviser_id": "agentic-engineering", "trigger_id": "decomposition-boundary"}]
        lexical_base = {
            "skills": [{
                "id": "agentic-engineering",
                "references": [
                    {"payload_id": "z-choice", "sha256": "1" * 64, "trigger_ids": ["decomposition-boundary"]},
                    {"payload_id": "a-choice", "sha256": "2" * 64, "trigger_ids": ["decomposition-boundary"]},
                ],
            }],
        }
        self.assertEqual(
            resolver._canonical_cover(request, POLICY, lexical_base),
            {"status": "resolved", "resolved_count": 1, "canonical_payload_id_tuple": ["a-choice"]},
        )
        cross_owner = {
            "skills": [{
                "id": "codex-task-contract",
                "references": [{"payload_id": "wrong-owner", "sha256": "3" * 64, "trigger_ids": ["decomposition-boundary"]}],
            }],
        }
        self.assertEqual(
            resolver._canonical_cover(request, POLICY, cross_owner),
            {"status": "unresolved", "resolved_count": 0, "canonical_payload_id_tuple": []},
        )
        unresolved = [{"owner_adviser_id": "agentic-engineering", "trigger_id": "missing-trigger"}]
        self.assertEqual(
            resolver._canonical_cover(unresolved, POLICY, lexical_base),
            {"status": "unresolved", "resolved_count": 0, "canonical_payload_id_tuple": []},
        )
        owners = ("owner-a", "owner-b", "owner-c", "owner-d")
        requests = [
            {"owner_adviser_id": owner, "trigger_id": f"trigger-{index}"}
            for index, owner in enumerate(owners, start=1)
        ]
        cap_base = {
            "skills": [
                {
                    "id": owner,
                    "references": [{
                        "payload_id": f"payload-{index}",
                        "sha256": str(index) * 64,
                        "trigger_ids": [f"trigger-{index}"],
                    }],
                }
                for index, owner in enumerate(owners, start=1)
            ],
        }
        self.assertEqual(
            resolver._canonical_cover(requests, POLICY, cap_base),
            {"status": "cap_exceeded", "resolved_count": 4, "canonical_payload_id_tuple": []},
        )

    def test_condition_packet_has_exact_keys_and_only_guidance_varies(self) -> None:
        current = resolver.build_condition_packet(ADAPTER, "current", "same task")
        reduced = resolver.build_condition_packet(ADAPTER, "reduced", "same task")
        self.assertEqual(list(current), ["instruction", "task_text", "slot_order", "pair_order", "condition_guidance", "support_legend"])
        self.assertNotEqual(current["condition_guidance"], reduced["condition_guidance"])
        self.assertEqual({key: value for key, value in current.items() if key != "condition_guidance"}, {key: value for key, value in reduced.items() if key != "condition_guidance"})


class CheckerTests(unittest.TestCase):
    def test_json_loader_rejects_duplicate_keys_and_nonfinite_constants(self) -> None:
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}'):
            with self.assertRaises(checker.CandidateError):
                checker._json(raw, "probe")

    def test_live_clean_rejects_tracked_untracked_and_ignored_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "AQ8 test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "aq8@example.invalid"], cwd=root, check=True)
            (root / ".gitignore").write_text("ignored.tmp\n", encoding="utf-8")
            (root / "tracked.txt").write_text("frozen", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=root, text=True).strip()
            checker._live_clean(root, commit)
            raw = b"frozen"
            self.assertEqual(checker._authority(root, (commit, tree), "tracked.txt", hashlib.sha256(raw).hexdigest()), raw)

            (root / "untracked.txt").write_text("drift", encoding="utf-8")
            with self.assertRaises(checker.CandidateError):
                checker._live_clean(root, commit)
            (root / "untracked.txt").unlink()
            (root / "ignored.tmp").write_text("drift", encoding="utf-8")
            with self.assertRaises(checker.CandidateError):
                checker._live_clean(root, commit)
            (root / "ignored.tmp").unlink()
            (root / "tracked.txt").write_text("drift", encoding="utf-8")
            with self.assertRaises(checker.CandidateError):
                checker._live_clean(root, commit)

    def test_checker_entrypoints_prevent_self_generated_bytecode(self) -> None:
        source = (ROOT / checker.ROLE_PATHS["checker"]).read_text(encoding="utf-8")
        self.assertLess(
            source.index("sys.dont_write_bytecode = True"),
            source.index("from resolve_h4_unresolved_decision_graph_v8 import"),
        )
        with tempfile.TemporaryDirectory() as directory:
            scripts = Path(directory) / "scripts"
            scripts.mkdir()
            checker_copy = scripts / "check_reduced_four_skill_candidate_v8.py"
            resolver_copy = scripts / "resolve_h4_unresolved_decision_graph_v8.py"
            checker_copy.write_bytes((ROOT / checker.ROLE_PATHS["checker"]).read_bytes())
            resolver_copy.write_bytes((ROOT / checker.ROLE_PATHS["resolver"]).read_bytes())
            subprocess.run(["git", "init", "-q"], cwd=directory, check=True)
            subprocess.run(["git", "config", "user.name", "AQ8 bytecode test"], cwd=directory, check=True)
            subprocess.run(["git", "config", "user.email", "aq8-bytecode@example.invalid"], cwd=directory, check=True)
            subprocess.run(["git", "add", "."], cwd=directory, check=True)
            subprocess.run(["git", "commit", "-qm", "clean entrypoint fixture"], cwd=directory, check=True)
            subprocess.run([sys.executable, "-B", str(checker_copy)], cwd=directory, check=True)
            self.assertFalse((scripts / "__pycache__").exists())
            subprocess.run([sys.executable, str(checker_copy)], cwd=directory, check=True)
            self.assertFalse((scripts / "__pycache__").exists())
            status = subprocess.check_output(
                ["git", "status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching"],
                cwd=directory,
                text=True,
            )
            self.assertEqual(status, "")

    def test_runtime_graph_schema_is_exact_provider_projection(self) -> None:
        checker.validate_runtime_graph_schema(PROTOCOL, RUNTIME_SCHEMA)
        mutations = (
            lambda value: value.__setitem__("prefixItems", []),
            lambda value: value.__setitem__("additionalProperties", 0),
            lambda value: value["properties"]["candidate_states"].__setitem__("minItems", 3),
            lambda value: value["properties"]["pairwise_relations"]["items"]["properties"]["relation"]["enum"].reverse(),
            lambda value: value["properties"]["reference_needs"]["items"].__setitem__("additionalProperties", True),
        )
        for mutate in mutations:
            broken = copy.deepcopy(RUNTIME_SCHEMA)
            mutate(broken)
            with self.assertRaises(checker.CandidateError):
                checker.validate_runtime_graph_schema(PROTOCOL, broken)

    def test_final_manifest_has_no_placeholder_and_each_synthetic_occurrence_fails_closed(self) -> None:
        draft = load(checker.MANIFEST_PATH)
        with self.assertRaises(checker.CandidateError):
            checker.validate_manifest_document(draft)
        self.assertNotIn("__AQ8_", json.dumps(draft))
        metric = valid_metric_binding()
        complete = resolved_manifest(metric)
        mutations = (
            ("metric_authority.commit", lambda value: value["metric_authority"].__setitem__("commit", "__AQ8_METRIC_COMMIT__")),
            ("metric_authority.tree", lambda value: value["metric_authority"].__setitem__("tree", "__AQ8_METRIC_TREE__")),
            ("metric_authority.sha256", lambda value: value["metric_authority"].__setitem__("sha256", "__AQ8_METRIC_SHA256__")),
            ("execution.authorities.metric_commit", lambda value: value["execution_contract"]["authorities"].__setitem__("metric_commit", "__AQ8_METRIC_COMMIT__")),
            ("execution.authorities.metric_tree", lambda value: value["execution_contract"]["authorities"].__setitem__("metric_tree", "__AQ8_METRIC_TREE__")),
            ("execution.authorities.metric_sha256", lambda value: value["execution_contract"]["authorities"].__setitem__("metric_sha256", "__AQ8_METRIC_SHA256__")),
            ("surface.metric_authority", lambda value: value["evaluator_surface"]["files"][10].__setitem__("sha256", "__AQ8_METRIC_SHA256__")),
            ("surface.checker", lambda value: value["evaluator_surface"]["files"][0].__setitem__("sha256", "__AQ8_CHECKER_SHA256__")),
            ("surface.resolver", lambda value: value["evaluator_surface"]["files"][1].__setitem__("sha256", "__AQ8_RESOLVER_SHA256__")),
            ("surface.scorer", lambda value: value["evaluator_surface"]["files"][2].__setitem__("sha256", "__AQ8_SCORER_SHA256__")),
            ("surface.runner", lambda value: value["evaluator_surface"]["files"][3].__setitem__("sha256", "__AQ8_RUNNER_SHA256__")),
            ("surface.evaluator_schema", lambda value: value["evaluator_surface"]["files"][4].__setitem__("sha256", "__AQ8_EVALUATOR_SCHEMA_SHA256__")),
        )
        self.assertEqual(len(mutations), 12)
        with patch.object(checker, "METRIC_BINDING", metric):
            checker.validate_manifest_structure(complete)
            for location, mutate in mutations:
                with self.subTest(location=location):
                    broken = copy.deepcopy(complete)
                    mutate(broken)
                    with self.assertRaises(checker.CandidateError):
                        checker.validate_manifest_structure(broken)

    def test_custody_validation_requires_commit_and_committed_manifest_equality(self) -> None:
        metric = valid_metric_binding()
        complete = resolved_manifest(metric)
        with patch.object(checker, "METRIC_BINDING", metric):
            checker.validate_manifest_structure(complete)
            for require_live in (False, True):
                with self.subTest(require_live=require_live):
                    with self.assertRaises(checker.CandidateError):
                        checker.validate_manifest_document(complete, require_live=require_live)
            commit = "6" * 40
            with (
                patch.object(checker, "_commit", return_value=commit),
                patch.object(checker, "_show", return_value=b'{}'),
            ):
                with self.assertRaises(checker.CandidateError):
                    checker.validate_manifest_document(complete, candidate_commit=commit)

    def test_execution_contract_and_forty_by_two_projection(self) -> None:
        metric = valid_metric_binding()
        contract = execution_contract(metric)
        with patch.object(checker, "METRIC_BINDING", metric):
            checker._execution_contract(contract)
            base_graph = graph()
            expected = resolver.resolve_graph("synthetic task", base_graph, PROTOCOL, POLICY, BASE)
            identifiers = tuple(f"synthetic-{index:02d}" for index in range(40))
            cases = {
                case_id: {
                    "task_text": "synthetic task",
                    "expected_semantic_output": copy.deepcopy(base_graph),
                    "expected_parent_derivation": copy.deepcopy(expected),
                }
                for case_id in identifiers
            }
            profile = {
                "protocol": PROTOCOL,
                "selector_schema": SCHEMA,
                "reference_policy": POLICY,
                "base_manifest": BASE,
                "adapter": ADAPTER,
                "qualified_ids": identifiers,
                "execution_contract": contract,
            }
            self.assertEqual(
                checker.verify_zero_model_projection(profile, cases),
                {"status": "pass", "qualification_cases": 40, "presentations": 80, "live_calls": 0},
            )
            for condition, digest in checker.CONDITIONS:
                packet = resolver.build_condition_packet(ADAPTER, condition, "synthetic task")
                self.assertEqual(
                    hashlib.sha256(resolver.canonical_json(packet["condition_guidance"])).hexdigest(),
                    digest,
                )
            broken = copy.deepcopy(cases)
            broken[identifiers[0]]["expected_parent_derivation"]["selected_slots"] = ["s0"]
            with self.assertRaises(checker.CandidateError):
                checker.verify_zero_model_projection(profile, broken)

    def test_runner_critical_isolation_fields_each_fail_closed(self) -> None:
        metric = valid_metric_binding()
        contract = execution_contract(metric)
        expected = {
            "isolated_codex_home": True,
            "isolated_home_mode": "0700",
            "auth_source": "owner-owned-regular-nonsymlink-0600",
            "auth_seed": "private-copy-0600-only",
            "explicit_subprocess_env": True,
            "exact_single_probe_input": True,
            "temp_cleanup_required": True,
            "global_agents_loaded": False,
        }
        self.assertEqual(
            {key: contract["isolation"][key] for key in expected},
            expected,
        )
        with patch.object(checker, "METRIC_BINDING", metric):
            checker._execution_contract(contract)
            for field, value in expected.items():
                with self.subTest(field=field):
                    broken = copy.deepcopy(contract)
                    broken["isolation"][field] = (
                        not value if type(value) is bool else f"{value}-drift"
                    )
                    with self.assertRaises(checker.CandidateError):
                        checker._execution_contract(broken)
                    wrong_type = copy.deepcopy(contract)
                    wrong_type["isolation"][field] = (
                        int(not value) if type(value) is bool else 700
                    )
                    with self.assertRaises(checker.CandidateError):
                        checker._execution_contract(wrong_type)
            missing = copy.deepcopy(contract)
            del missing["isolation"]["isolated_codex_home"]
            with self.assertRaises(checker.CandidateError):
                checker._execution_contract(missing)
            extra = copy.deepcopy(contract)
            extra["isolation"]["ambient_home_permitted"] = False
            with self.assertRaises(checker.CandidateError):
                checker._execution_contract(extra)

    def test_closed_manifest_document_with_synthetic_bindings(self) -> None:
        metric = valid_metric_binding()
        draft = resolved_manifest(metric)
        self.assertEqual(
            draft["metric_authority"],
            {
                "commit": "a07147eee19ac17f22113fc6b8cc673a0c761764",
                "tree": "8ddbad21796ece86c2676dea622d0235e37990d8",
                "path": checker.METRIC_PATH,
                "sha256": "144a7b98ee7cdb852314a8e509a003a5c16dd588b3bf2727412051d3436659c7",
            },
        )
        self.assertEqual(
            {row["role"]: row["sha256"] for row in draft["evaluator_surface"]["files"]},
            {
                "checker": "e5cf729809a31d96b1b0b1af6037dfaba01bc3cc429e81a3d2d293bd330765e5",
                "resolver": "aa4e1fc218e864a56c854f716c0a9576134614184d62979ae91296feaa1a2a8d",
                "scorer": "908b1d7df1c8d0f16fb15da8b355ba40fec83e267acb652343230c9f052adfc3",
                "runner": "687dd4787bc5bedb21db31a894cd88e6c6595f1a49c4945f6d8c1dc70f12b881",
                "evaluator_schema": "bf73597408fbc567fe30803bcf36e1e3e51a9b8926ed5d82bdfbdd28b8adc61c",
                "runtime_graph_schema": "e4d58b46e39ac65e56a339e7c0d2714d536a5d517de57c2bcc34cfd5c6fe301e",
                "validator": "bd1769f9ad328c99706c2b5c6cff19a0cb2fddfa9760a14b4e70f41160e1ec33",
                "run_index": "ef6fd9fc7255eaca759641418fab65e8028676a91634163735d767a78925bd2d",
                "condition_adapter": "2b82d26b9f438b7cfef712d59817bb2cc8426941167350ec58c42a9a6e5e5b31",
                "gate_authority": "d17c6de19b456100a0c930d9cbe898d123dab882fe924c92226f9962fc7784d8",
                "metric_authority": "144a7b98ee7cdb852314a8e509a003a5c16dd588b3bf2727412051d3436659c7",
            },
        )
        with patch.object(checker, "METRIC_BINDING", metric):
            checker.validate_manifest_structure(draft)
            extra = copy.deepcopy(draft)
            extra["completion_claim"] = True
            with self.assertRaises(checker.CandidateError):
                checker.validate_manifest_structure(extra)
            reordered = copy.deepcopy(draft)
            reordered["evaluator_surface"]["files"].reverse()
            with self.assertRaises(checker.CandidateError):
                checker.validate_manifest_structure(reordered)

    def test_no_shadow_resolver_definition(self) -> None:
        for path in (ROOT / "scripts").glob("*_v8.py"):
            if path.name == "resolve_h4_unresolved_decision_graph_v8.py":
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("def resolve_graph(", text, path.name)


if __name__ == "__main__":
    unittest.main()
