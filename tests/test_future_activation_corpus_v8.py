"""Synthetic, no-result tests for the AQ8 freeze validator.

The suite never opens either real AQ8 split. All semantic fixtures come from
the already-frozen contract test and all public-failure assertions remain
prompt-free.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


V = load(ROOT / "scripts/validate_future_activation_corpus_v8.py", "aq8_validator")
CONTRACT_TEST_PATH = Path("tests/test_future_activation_contract_v8.py")
CONTRACT_TEST_SHA256 = (
    "659c0cde149a555e1a3c2ce618d871f2241d0bfc6e8e1795d0b12a0af254e934"
)
CONTRACT_TEST_RAW = V._commit_file(ROOT, V.CONTRACT_COMMIT, CONTRACT_TEST_PATH)
assert hashlib.sha256(CONTRACT_TEST_RAW).hexdigest() == CONTRACT_TEST_SHA256
assert (ROOT / CONTRACT_TEST_PATH).read_bytes() == CONTRACT_TEST_RAW
C = load(ROOT / CONTRACT_TEST_PATH, "aq8_contract_fixture")
SCHEMA_RAW = (ROOT / V.SCHEMA).read_bytes()
CONTEXT = V._load_authorities(ROOT, SCHEMA_RAW)


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _independent_text(corpus_id: str, ordinal: int) -> str:
    if corpus_id == "AQ8-authoring":
        stem = (
            f"Amber kiln record {ordinal:02d}: characterize a pending design "
            "dependency while keeping evidence and action boundaries separate."
        )
        explicit = "Apply the bounded route"
    else:
        stem = (
            f"Zephyr orchard memo {ordinal:02d}: map remaining choices before "
            "sequencing downstream work, with citations isolated from control."
        )
        explicit = "Use only the named path"
    if ordinal <= 32:
        return stem
    token = tuple(C.TOKEN_TO_SLOT)[ordinal - 33]
    return f"{stem} {explicit} ({token})."


def synthetic_pair() -> tuple[dict, dict]:
    documents = (
        C.build_synthetic_document("AQ8-authoring"),
        C.build_synthetic_document("AQ8-heldout"),
    )
    for document in documents:
        for ordinal, case in enumerate(document["cases"], start=1):
            task_text = _independent_text(document["corpus_id"], ordinal)
            case["task_text"] = task_text
            case["task_text_nfc_sha256"] = _sha_text(task_text)
            case["expected_parent_derivation"] = C._derive_parent(case)
    return documents


def validate_pair(authoring: dict, heldout: dict, *, historical=None):
    return V._validate_documents(
        ROOT,
        SCHEMA_RAW,
        (json.dumps(authoring).encode(), json.dumps(heldout).encode()),
        historical=[] if historical is None else historical,
    )


class FutureActivationCorpusV8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.authoring, cls.heldout = synthetic_pair()

    def test_synthetic_oracle_is_exact_contract_commit_bytes(self) -> None:
        self.assertEqual(
            CONTRACT_TEST_SHA256,
            hashlib.sha256(CONTRACT_TEST_RAW).hexdigest(),
        )
        self.assertEqual(CONTRACT_TEST_RAW, (ROOT / CONTRACT_TEST_PATH).read_bytes())

    def test_synthetic_closed_pair_passes_exact_counts_and_qualified_set(self) -> None:
        result = validate_pair(self.authoring, self.heldout)
        self.assertTrue(result.passed, result.errors)
        self.assertEqual(
            {
                "total_cases": 72,
                "automatic_cases": 64,
                "explicit_cases": 8,
                "qualified_cases": 40,
            },
            {
                key: result.metrics[key]
                for key in (
                    "total_cases",
                    "automatic_cases",
                    "explicit_cases",
                    "qualified_cases",
                )
            },
        )
        self.assertEqual(40, len(result.qualified_ids))
        self.assertTrue(
            all(
                case_id.startswith("AQ8-heldout-")
                for case_id in result.qualified_ids[:32]
            )
        )
        self.assertEqual(
            {
                "AQ8-authoring-33",
                "AQ8-authoring-34",
                "AQ8-authoring-35",
                "AQ8-authoring-36",
                "AQ8-heldout-33",
                "AQ8-heldout-34",
                "AQ8-heldout-35",
                "AQ8-heldout-36",
            },
            set(result.qualified_ids[32:]),
        )

    def test_closed_root_case_schema_and_semantic_order_reds(self) -> None:
        mutations = []
        bad = copy.deepcopy(self.authoring)
        bad["extra"] = False
        mutations.append(bad)
        bad = copy.deepcopy(self.authoring)
        bad["cases"][0]["extra"] = False
        mutations.append(bad)
        bad = copy.deepcopy(self.authoring)
        rows = bad["cases"][2]["expected_semantic_output"]["candidate_states"]
        rows[0], rows[1] = rows[1], rows[0]
        mutations.append(bad)
        bad = copy.deepcopy(self.authoring)
        rows = bad["cases"][6]["expected_semantic_output"]["pairwise_relations"]
        rows[0], rows[1] = rows[1], rows[0]
        mutations.append(bad)
        bad = copy.deepcopy(self.authoring)
        rows = bad["cases"][2]["expected_semantic_output"]["reference_needs"]
        rows[0], rows[1] = rows[1], rows[0]
        mutations.append(bad)
        for document in mutations:
            self.assertFalse(validate_pair(document, self.heldout).passed)

        duplicate_root = json.dumps(self.authoring, separators=(",", ":")).replace(
            '{"schema_version":"8.0"',
            '{"schema_version":"8.0","schema_version":"8.0"',
            1,
        )
        result = V._validate_documents(
            ROOT,
            SCHEMA_RAW,
            (duplicate_root.encode(), json.dumps(self.heldout).encode()),
            historical=[],
        )
        self.assertFalse(result.passed)
        with self.assertRaises(V.ContractError):
            V._json(b'{"value":NaN}')

    def test_every_parent_projection_is_equality_checked(self) -> None:
        mutations = (
            lambda row: row.update(graph_status="graph_uncertain"),
            lambda row: row.update(automatic_selection_status="cap_exceeded"),
            lambda row: row.update(selection_status="cap_exceeded"),
            lambda row: row.update(root_slots=[]),
            lambda row: row.update(selected_slots=[]),
            lambda row: row.update(selected_adviser_ids=[]),
            lambda row: row.update(complement_adviser_ids=[]),
            lambda row: row.update(reference_requests=[]),
            lambda row: row.update(reference_uncertain_slots=["s0"]),
            lambda row: row["reference_resolution"].update(resolved_count=0),
            lambda row: row["reference_resolution"].update(
                canonical_payload_id_tuple=[]
            ),
        )
        for mutate in mutations:
            bad = copy.deepcopy(self.authoring)
            mutate(bad["cases"][2]["expected_parent_derivation"])
            self.assertFalse(validate_pair(bad, self.heldout).passed)

    def test_graph_closure_cycle_pair_coherence_root_cap_and_uncertainty_reds(
        self,
    ) -> None:
        closure = copy.deepcopy(self.authoring)
        closure["cases"][18]["expected_semantic_output"]["pairwise_relations"][1][
            "relation"
        ] = "independent"
        self.assertFalse(validate_pair(closure, self.heldout).passed)

        pair = copy.deepcopy(self.authoring)
        pair["cases"][0]["expected_semantic_output"]["pairwise_relations"][0][
            "relation"
        ] = "independent"
        self.assertFalse(validate_pair(pair, self.heldout).passed)

        cycle = copy.deepcopy(self.authoring)
        semantic = cycle["cases"][18]["expected_semantic_output"]
        relations = {
            ("s0", "s1"): "left_controls_right_downstream",
            ("s0", "s2"): "right_controls_left_downstream",
            ("s1", "s2"): "left_controls_right_downstream",
        }
        for row in semantic["pairwise_relations"]:
            pair_id = (row["left_slot"], row["right_slot"])
            if pair_id in relations:
                row["relation"] = relations[pair_id]
        for row in semantic["reference_needs"]:
            row["need"] = "none"
        cycle["cases"][18]["expected_parent_derivation"] = V._derive_parent(
            CONTEXT, cycle["cases"][18]
        )
        self.assertEqual(
            "graph_cycle",
            cycle["cases"][18]["expected_parent_derivation"]["graph_status"],
        )
        self.assertFalse(validate_pair(cycle, self.heldout).passed)

        for ordinal, field, value in (
            (3, "root_slots", ["s1"]),
            (29, "selection_status", "automatic"),
            (31, "automatic_selection_status", "automatic"),
        ):
            bad = copy.deepcopy(self.authoring)
            bad["cases"][ordinal - 1]["expected_parent_derivation"][field] = value
            self.assertFalse(validate_pair(bad, self.heldout).passed)

    def test_reference_owner_cover_order_and_unselected_need_reds(self) -> None:
        bad_need = copy.deepcopy(self.authoring)
        bad_need["cases"][2]["expected_semantic_output"]["reference_needs"][1][
            "need"
        ] = "primary"
        self.assertFalse(validate_pair(bad_need, self.heldout).passed)

        bad_owner = copy.deepcopy(self.authoring)
        requests = bad_owner["cases"][2]["expected_parent_derivation"][
            "reference_requests"
        ]
        self.assertTrue(requests)
        requests[0]["owner_adviser_id"] = "codex-task-contract"
        self.assertFalse(validate_pair(bad_owner, self.heldout).passed)

        source = next(
            case
            for case in self.authoring["cases"]
            if len(
                case["expected_parent_derivation"]["reference_resolution"][
                    "canonical_payload_id_tuple"
                ]
            )
            == 2
        )
        bad_order = copy.deepcopy(self.authoring)
        index = self.authoring["cases"].index(source)
        bad_order["cases"][index]["expected_parent_derivation"]["reference_resolution"][
            "canonical_payload_id_tuple"
        ].reverse()
        self.assertFalse(validate_pair(bad_order, self.heldout).passed)

    def test_exact_unicode_parser_and_precedence_boundaries(self) -> None:
        token = next(
            token for token, slot in CONTEXT.token_to_slot.items() if slot == "s0"
        )
        fixtures = CONTEXT.parser["boundary"]["retained_rejection_fixtures"]
        for fixture in fixtures:
            codepoint = chr(int(fixture["codepoint"][2:], 16))
            self.assertEqual([], V._scan_invocation_like(CONTEXT, codepoint + token))
            self.assertEqual([], V._scan_invocation_like(CONTEXT, token + codepoint))
        for codepoint in ("é", "β", "\u0301", "_"):
            self.assertEqual([], V._scan_invocation_like(CONTEXT, codepoint + token))
            self.assertEqual([], V._scan_invocation_like(CONTEXT, token + codepoint))
        self.assertEqual([], V._scan_invocation_like(CONTEXT, "-" + token))
        self.assertEqual(
            ["$agentic-engineering-"],
            V._scan_invocation_like(CONTEXT, token + "-"),
        )
        graph = V._resolve_graph(
            CONTEXT, self.authoring["cases"][2]["expected_semantic_output"]
        )
        self.assertEqual(("exact", ["s0"]), V._resolve_selection(CONTEXT, token, graph))
        self.assertEqual(
            ("unrecognized", []),
            V._resolve_selection(CONTEXT, f"{token} $unknown-route", graph),
        )
        self.assertEqual(
            ("ambiguous", []),
            V._resolve_selection(CONTEXT, f"{token} {token}", graph),
        )

    def test_automatic_name_invocation_and_explicit_grammar_leakage_reds(self) -> None:
        for forbidden in (
            "AGENTIC ENGINEERING",
            "CODEX_TASK_CONTRACT",
            "VERIFICATION STRATEGY ENGINEERING",
            "ENGINEERING_LEARNING_LOOP",
            "$unknown-route",
        ):
            bad = copy.deepcopy(self.authoring)
            case = bad["cases"][0]
            case["task_text"] = forbidden
            case["task_text_nfc_sha256"] = _sha_text(forbidden)
            case["expected_parent_derivation"] = copy.deepcopy(
                self.authoring["cases"][0]["expected_parent_derivation"]
            )
            self.assertFalse(validate_pair(bad, self.heldout).passed)

        exact = copy.deepcopy(self.authoring)
        case = exact["cases"][32]
        case["task_text"] += " $unknown-route"
        case["task_text_nfc_sha256"] = _sha_text(case["task_text"])
        self.assertFalse(validate_pair(exact, self.heldout).passed)

        unicode_boundary = copy.deepcopy(self.authoring)
        case = unicode_boundary["cases"][32]
        case["task_text"] = case["task_text"].replace(
            "$agentic-engineering", "\u200c$agentic-engineering"
        )
        case["task_text_nfc_sha256"] = _sha_text(case["task_text"])
        self.assertFalse(validate_pair(unicode_boundary, self.heldout).passed)

    def test_prompt_hygiene_rejects_internal_ids_but_allows_natural_language(
        self,
    ) -> None:
        payload_id = CONTEXT.reference_payloads[0]["payload_id"]
        forbidden = (
            "reference-isolation",
            "s0",
            payload_id,
            "candidate_states",
            "task-contract",
            "H4",
            "AQ8-heldout-26",
            "schema_version",
            V.SPLIT_NONCES["AQ8-heldout"],
            V._case_nonce(V.SPLIT_NONCES["AQ8-heldout"], "AQ8-heldout-26"),
            V.CONTRACT_COMMIT,
            V.COMPARATORS[0].commit,
            V.SCHEMA.as_posix(),
        )
        for identifier in forbidden:
            self.assertIn(identifier, CONTEXT.forbidden_task_identifiers)
            self.assertFalse(
                V._task_hygiene_ok(CONTEXT, f"Review ({identifier}) before acting.")
            )
            bad = copy.deepcopy(self.authoring)
            case = bad["cases"][0]
            case["task_text"] = f"Review ({identifier}) before acting."
            case["task_text_nfc_sha256"] = _sha_text(case["task_text"])
            self.assertFalse(validate_pair(bad, self.heldout).passed)

        natural = (
            "reference isolation",
            "verification evidence",
            "task contract",
            "candidate states",
            "resolved or absent",
            "architecture boundary",
        )
        for phrase in natural:
            self.assertTrue(V._task_hygiene_ok(CONTEXT, phrase))
        self.assertTrue(V._task_hygiene_ok(CONTEXT, "Xs0Y"))
        self.assertFalse(V._task_hygiene_ok(CONTEXT, "$codex-task-contract"))
        self.assertTrue(
            V._task_hygiene_ok(
                CONTEXT,
                "$codex-task-contract",
                "$codex-task-contract",
            )
        )

        explicit_leak = copy.deepcopy(self.authoring)
        case = explicit_leak["cases"][32]
        case["task_text"] += " Plain codex-task-contract text is not allowed."
        case["task_text_nfc_sha256"] = _sha_text(case["task_text"])
        self.assertFalse(validate_pair(explicit_leak, self.heldout).passed)

    def test_distribution_drift_fails_after_downstream_recompute(self) -> None:
        bad = copy.deepcopy(self.authoring)
        case = bad["cases"][6]
        case["expected_semantic_output"]["pairwise_relations"][0]["relation"] = (
            "left_controls_right_downstream"
        )
        for row in case["expected_semantic_output"]["reference_needs"]:
            row["need"] = "none"
        case["expected_parent_derivation"] = V._derive_parent(CONTEXT, case)
        self.assertFalse(validate_pair(bad, self.heldout).passed)

    def test_ids_nonces_nfc_hash_authority_and_claim_reds(self) -> None:
        mutations = []
        bad = copy.deepcopy(self.authoring)
        bad["cases"][0]["case_id"] = "AQ8-heldout-01"
        bad["cases"][0]["case_nonce"] = V._case_nonce(
            bad["split_nonce"], "AQ8-heldout-01"
        )
        mutations.append(bad)
        bad = copy.deepcopy(self.authoring)
        bad["cases"][0]["case_nonce"] = "0" * 64
        mutations.append(bad)
        bad = copy.deepcopy(self.authoring)
        bad["cases"][0]["task_text_nfc_sha256"] = "0" * 64
        mutations.append(bad)
        bad = copy.deepcopy(self.authoring)
        bad["cases"][0]["task_text"] += " e\u0301"
        bad["cases"][0]["task_text_nfc_sha256"] = _sha_text(
            bad["cases"][0]["task_text"]
        )
        mutations.append(bad)
        bad = copy.deepcopy(self.authoring)
        bad["authority"]["h4"]["tree"] = "0" * 40
        mutations.append(bad)
        bad = copy.deepcopy(self.authoring)
        bad["authority"]["aq8_gate"]["sha256"] = "0" * 64
        mutations.append(bad)
        bad = copy.deepcopy(self.authoring)
        bad["claim_boundary"]["replay_policy"] = "replay-permitted"
        mutations.append(bad)
        for document in mutations:
            self.assertFalse(validate_pair(document, self.heldout).passed)

    def test_cross_split_and_historical_reuse_similarity_boundaries(self) -> None:
        prompt = self.authoring["cases"][0]["task_text"]
        exact_history = [(V._sha_text(prompt), V._signature(prompt))]
        self.assertFalse(
            validate_pair(self.authoring, self.heldout, historical=exact_history).passed
        )
        near_history = [("different", V._signature(prompt))]
        self.assertFalse(
            validate_pair(self.authoring, self.heldout, historical=near_history).passed
        )
        self.assertEqual(
            V._signature("Use $agentic-engineering shared text."),
            V._signature("Use $codex-task-contract shared text."),
        )
        self.assertEqual(V._signature("abc"), V._signature("abc "))
        self.assertEqual(1.0, V._jaccard(V._signature("abc"), V._signature("abc ")))
        self.assertLess(
            len(V._similarity_compact("abcdefghijk")),
            V.MIN_SIMILARITY_TEXT_LENGTH,
        )
        self.assertEqual(
            V.MIN_SIMILARITY_TEXT_LENGTH,
            len(V._similarity_compact("abcdefghijkl")),
        )
        self.assertTrue(
            all(
                len(item) == 64 and set(item) <= set("0123456789abcdef")
                for item in V._signature(prompt)
            )
        )
        at_boundary = V._jaccard(
            {"a", "b", "c"},
            {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"},
        )
        below = V._jaccard(
            {"a", "b"},
            {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"},
        )
        self.assertEqual(V.NEAR_REWRITE_THRESHOLD, at_boundary)
        self.assertGreaterEqual(at_boundary, V.NEAR_REWRITE_THRESHOLD)
        self.assertLess(below, V.NEAR_REWRITE_THRESHOLD)

        coupled = copy.deepcopy(self.heldout)
        coupled_case = coupled["cases"][0]
        coupled_case["task_text"] = prompt
        coupled_case["task_text_nfc_sha256"] = _sha_text(prompt)
        coupled_case["expected_parent_derivation"] = copy.deepcopy(
            self.authoring["cases"][0]["expected_parent_derivation"]
        )
        self.assertFalse(validate_pair(self.authoring, coupled).passed)

        short_authoring = copy.deepcopy(self.authoring)
        short_heldout = copy.deepcopy(self.heldout)
        for document, task_text in (
            (short_authoring, "abc"),
            (short_heldout, "abd"),
        ):
            case = document["cases"][0]
            case["task_text"] = task_text
            case["task_text_nfc_sha256"] = _sha_text(task_text)
        self.assertFalse(validate_pair(short_authoring, short_heldout).passed)

        boundary_authoring = copy.deepcopy(self.authoring)
        boundary_heldout = copy.deepcopy(self.heldout)
        for document, task_text in (
            (boundary_authoring, "abcdefghijk"),
            (boundary_heldout, "abcdefghijkl"),
        ):
            case = document["cases"][0]
            case["task_text"] = task_text
            case["task_text_nfc_sha256"] = _sha_text(task_text)
        self.assertFalse(validate_pair(boundary_authoring, boundary_heldout).passed)

    def test_historical_fingerprints_are_one_way_and_prompt_free(self) -> None:
        marker = "private-historical-fixture-sentinel"
        payload = json.dumps({"cases": [{"prompt": marker}]}).encode()
        comparator = V.Comparator("a" * 40, "b" * 40, Path("old"))
        with (
            patch.object(V, "COMPARATORS", (comparator,)),
            patch.object(V, "_assert_commit"),
            patch.object(V, "_commit_file", return_value=payload),
        ):
            fingerprints = V._historical_fingerprints(ROOT)
        self.assertEqual(2, len(fingerprints))
        self.assertNotIn(marker, repr(fingerprints))
        self.assertNotIn(marker[:4], repr(fingerprints))
        self.assertEqual(_sha_text(marker), fingerprints[0][0])

    def test_exact_two_split_staged_custody_and_extra_missing_drift_reds(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payloads = {
                V.SCHEMA: b"schema",
                V.README: b"readme",
                V.SPLITS[0]: b"A",
                V.SPLITS[1]: b"H",
            }
            for path, payload in payloads.items():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
            staged = (
                b"A\0evals/foundation-v4/future-activation-v8/activation-authoring.json\0"
                b"A\0evals/foundation-v4/future-activation-v8/activation-heldout.json\0"
            )

            def git_ok(_, args):
                if args[:3] == ["diff", "--cached", "--name-status"]:
                    return staged
                return next(
                    payload
                    for path, payload in payloads.items()
                    if args[-1].endswith(path.as_posix())
                )

            with (
                patch.object(V, "_contract_ok", return_value=True),
                patch.object(V, "_git", side_effect=git_ok),
            ):
                self.assertTrue(V.check_staged_split_custody(root, (b"A", b"H")))

            (root / V.SPLITS[0]).write_bytes(b"changed")

            def git_changed(_, args):
                if args[:3] == ["diff", "--cached", "--name-status"]:
                    return staged
                if args[-1].endswith(V.SPLITS[0].as_posix()):
                    return b"changed"
                return git_ok(_, args)

            with (
                patch.object(V, "_contract_ok", return_value=True),
                patch.object(V, "_git", side_effect=git_changed),
            ):
                self.assertFalse(V.check_staged_split_custody(root, (b"A", b"H")))
            (root / V.SPLITS[0]).write_bytes(b"A")

            def git_parent_drift(root_arg, args):
                if args[-1] == f"HEAD:{V.README.as_posix()}":
                    return b"drift"
                return git_ok(root_arg, args)

            with (
                patch.object(V, "_contract_ok", return_value=True),
                patch.object(V, "_git", side_effect=git_parent_drift),
            ):
                self.assertFalse(V.check_staged_split_custody(root, (b"A", b"H")))

            (root / V.SCHEMA).write_bytes(b"swapped")
            with (
                patch.object(V, "_contract_ok", return_value=True),
                patch.object(V, "_git", side_effect=git_ok),
            ):
                self.assertFalse(V.check_staged_split_custody(root, (b"A", b"H")))
            (root / V.SCHEMA).write_bytes(payloads[V.SCHEMA])

            extra = staged + b"A\0extra\0"
            missing = b"A\0evals/foundation-v4/future-activation-v8/activation-authoring.json\0"
            for bad_status in (extra, missing):
                with (
                    patch.object(V, "_contract_ok", return_value=True),
                    patch.object(
                        V,
                        "_git",
                        side_effect=lambda _, args, raw=bad_status: (
                            raw
                            if args[:3] == ["diff", "--cached", "--name-status"]
                            else b"A"
                        ),
                    ),
                ):
                    self.assertFalse(V.check_staged_split_custody(root))
            with (
                patch.object(V, "_contract_ok", return_value=True),
                patch.object(
                    V,
                    "_git",
                    side_effect=lambda _, args: (
                        staged
                        if args[:3] == ["diff", "--cached", "--name-status"]
                        else b"drift"
                    ),
                ),
            ):
                self.assertFalse(V.check_staged_split_custody(root))

    def test_contract_schema_readme_live_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payloads = {V.SCHEMA: b"schema", V.README: b"readme"}
            for path, payload in payloads.items():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
            hashes = {
                path: hashlib.sha256(raw).hexdigest() for path, raw in payloads.items()
            }
            with (
                patch.object(V, "_assert_commit"),
                patch.object(
                    V, "_commit_file", side_effect=lambda _, __, path: payloads[path]
                ),
                patch.dict(V.CONTRACT_HASHES, hashes, clear=True),
            ):
                self.assertTrue(V._contract_ok(root))
                (root / V.SCHEMA).write_bytes(b"drift")
                self.assertFalse(V._contract_ok(root))
                (root / V.SCHEMA).write_bytes(payloads[V.SCHEMA])
                (root / V.README).write_bytes(b"drift")
                self.assertFalse(V._contract_ok(root))

    def test_git_reads_disable_replace_objects_and_optional_locks(self) -> None:
        injected = {
            "GIT_INDEX_FILE": "/tmp/alternate-index",
            "GIT_OBJECT_DIRECTORY": "/tmp/alternate-objects",
            "GIT_TRACE": "/tmp/validator-trace",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.fsmonitor",
            "GIT_CONFIG_VALUE_0": "true",
        }
        with (
            patch.dict(V.os.environ, injected),
            patch.object(V.subprocess, "run") as run,
        ):
            run.return_value.returncode = 0
            run.return_value.stdout = b"value"
            self.assertEqual(b"value", V._git(ROOT, ["rev-parse", "HEAD"]))
        environment = run.call_args.kwargs["env"]
        self.assertEqual("1", environment["GIT_NO_REPLACE_OBJECTS"])
        self.assertEqual("0", environment["GIT_OPTIONAL_LOCKS"])
        self.assertFalse(set(injected) & set(environment))
        self.assertEqual(
            ["git", "rev-parse", "HEAD"],
            run.call_args.args[0],
        )
        with tempfile.TemporaryDirectory() as temp:
            trace = Path(temp) / "trace.log"
            with patch.dict(V.os.environ, {"GIT_TRACE": str(trace)}):
                self.assertIsNotNone(V._git(ROOT, ["rev-parse", "HEAD"]))
            self.assertFalse(trace.exists())

    def test_frozen_commit_custody_requires_exact_two_additions(self) -> None:
        exact = (
            b"A\0evals/foundation-v4/future-activation-v8/activation-authoring.json\0"
            b"A\0evals/foundation-v4/future-activation-v8/activation-heldout.json\0"
        )
        with patch.object(V, "_git", return_value=exact):
            self.assertTrue(V._frozen_commit_custody(ROOT, "c" * 40))
        for bad in (
            exact + b"A\0extra\0",
            b"A\0evals/foundation-v4/future-activation-v8/activation-authoring.json\0",
            exact.replace(b"A\0evals", b"M\0evals", 1),
        ):
            with patch.object(V, "_git", return_value=bad):
                self.assertFalse(V._frozen_commit_custody(ROOT, "c" * 40))

    def test_bound_default_passes_and_wrong_binding_is_fail_closed(self) -> None:
        self.assertEqual(
            "46174c0c5eb3da9b6134305329ebc36cc5108847",
            V.FROZEN_CORPUS_COMMIT,
        )
        self.assertEqual(
            "163677779d0db59b586a91d4d3becf21803afb2e",
            V.FROZEN_CORPUS_TREE,
        )
        self.assertEqual(
            {
                V.SPLITS[0]: (
                    "08318e0f01b386bba2a0932915a87d07e637ed5b495e822308c42c8371d63a4d"
                ),
                V.SPLITS[1]: (
                    "db9c55fff89bdb636f977bb6bebd4b88830d09e6ffa3d0f09c8d4c120eb42227"
                ),
            },
            V.FROZEN_CORPUS_HASHES,
        )
        result = V.validate_frozen(ROOT)
        self.assertTrue(result.passed, result.errors)
        self.assertEqual(72, result.metrics["total_cases"])
        self.assertEqual(40, result.metrics["qualified_cases"])
        with (
            patch.object(V, "FROZEN_CORPUS_COMMIT", "0" * 40),
            patch.object(V, "FROZEN_CORPUS_TREE", "0" * 40),
            patch.object(
                V,
                "FROZEN_CORPUS_HASHES",
                {V.SPLITS[0]: "0" * 64, V.SPLITS[1]: "0" * 64},
            ),
        ):
            self.assertFalse(V.validate_frozen(ROOT).passed)
        run = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/validate_future_activation_corpus_v8.py"),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertIn("future-activation-corpus-v8: PASS", run.stdout)

    def test_frozen_binding_requires_exact_commit_tree_hashes_and_live_bytes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payloads = {
                V.SCHEMA: b"schema",
                V.README: b"readme",
                V.SPLITS[0]: b"authoring",
                V.SPLITS[1]: b"heldout",
            }
            for path, payload in payloads.items():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
            contract_hashes = {
                path: hashlib.sha256(payloads[path]).hexdigest()
                for path in (V.SCHEMA, V.README)
            }
            split_hashes = {
                path: hashlib.sha256(payloads[path]).hexdigest() for path in V.SPLITS
            }
            passed = V.ValidationResult(
                (),
                {"total_cases": 72, "qualified_cases": 40},
                tuple(f"qualified-{index}" for index in range(40)),
            )
            with (
                patch.object(V, "FROZEN_CORPUS_COMMIT", "c" * 40),
                patch.object(V, "FROZEN_CORPUS_TREE", "t" * 40),
                patch.object(V, "FROZEN_CORPUS_HASHES", split_hashes),
                patch.dict(V.CONTRACT_HASHES, contract_hashes, clear=True),
                patch.object(V, "_contract_ok", return_value=True),
                patch.object(V, "_assert_commit"),
                patch.object(V, "_frozen_commit_custody", return_value=True),
                patch.object(
                    V, "_commit_file", side_effect=lambda _, __, path: payloads[path]
                ),
                patch.object(V, "_historical_fingerprints", return_value=[]),
                patch.object(V, "_validate_documents", return_value=passed),
            ):
                self.assertTrue(V.validate_frozen(root).passed)
                self.assertFalse(V.validate_frozen(root, commit="wrong-commit").passed)
                self.assertFalse(V.validate_frozen(root, tree="wrong-tree").passed)
                with patch.object(
                    V,
                    "FROZEN_CORPUS_HASHES",
                    {V.SPLITS[0]: split_hashes[V.SPLITS[0]]},
                ):
                    self.assertFalse(V.validate_frozen(root).passed)
                wrong_hash = dict(split_hashes)
                wrong_hash[V.SPLITS[0]] = "0" * 64
                with patch.object(V, "FROZEN_CORPUS_HASHES", wrong_hash):
                    self.assertFalse(V.validate_frozen(root).passed)
                with patch.object(V, "_frozen_commit_custody", return_value=False):
                    self.assertFalse(V.validate_frozen(root).passed)

                def validate_then_drift(*_args, **_kwargs):
                    (root / V.SPLITS[0]).write_bytes(b"drift-during-validation")
                    return passed

                with patch.object(
                    V, "_validate_documents", side_effect=validate_then_drift
                ):
                    self.assertFalse(V.validate_frozen(root).passed)
                (root / V.SPLITS[0]).write_bytes(payloads[V.SPLITS[0]])
                (root / V.SPLITS[0]).write_bytes(b"drift")
                self.assertFalse(V.validate_frozen(root).passed)
                (root / V.SPLITS[0]).write_bytes(payloads[V.SPLITS[0]])
                (root / V.README).write_bytes(b"drift")
                self.assertFalse(V.validate_frozen(root).passed)

    def test_working_tree_path_is_zero_write_and_exception_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for path in (V.SCHEMA, V.README, *V.SPLITS):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"fixture")
            before = {
                path: ((root / path).read_bytes(), (root / path).stat().st_mtime_ns)
                for path in (V.SCHEMA, V.README, *V.SPLITS)
            }
            passed = V.ValidationResult(
                (),
                {
                    "total_cases": 72,
                    "automatic_cases": 64,
                    "explicit_cases": 8,
                    "qualified_cases": 40,
                },
                tuple(f"qualified-{index}" for index in range(40)),
            )
            with (
                patch.object(V, "_contract_ok", return_value=True),
                patch.object(V, "_historical_fingerprints", return_value=[]),
                patch.object(V, "_validate_documents", return_value=passed),
                patch.object(V, "check_staged_split_custody", return_value=True),
            ):
                ok, errors, metrics = V.validate(root, working_tree=True)
            self.assertTrue(ok, errors)
            self.assertEqual(72, metrics["total_cases"])
            self.assertEqual(
                before,
                {
                    path: ((root / path).read_bytes(), (root / path).stat().st_mtime_ns)
                    for path in (V.SCHEMA, V.README, *V.SPLITS)
                },
            )

        marker = "private-current-fixture-sentinel"
        malformed = json.dumps({"cases": [{"task_text": marker}]}).encode()
        result = V._validate_documents(
            ROOT,
            SCHEMA_RAW,
            (malformed, json.dumps(self.heldout).encode()),
            historical=[],
        )
        self.assertEqual(("structural corpus validation failed",), result.errors)
        self.assertNotIn(marker, repr(result))


if __name__ == "__main__":
    unittest.main()
