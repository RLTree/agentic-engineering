from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import unicodedata
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "evals/ae-sq3/f1/historical-task-digests.json"
INVENTORY_SHA256 = (
    "8ee69ae06f388c1b47386b312d31bcce7ae408d04e76659653335d55e12ac270"
)
TOP_KEYS = (
    "schema_version",
    "program_id",
    "role",
    "claim_ceiling",
    "derivation",
    "sources",
    "task_text_nfc_sha256",
    "inventory_count",
    "inventory_sha256",
    "coverage",
    "limitations",
)
SOURCE_KEYS = (
    "logical_role",
    "commit",
    "tree",
    "path",
    "git_blob",
    "raw_sha256",
    "task_text_selector",
    "occurrence_count",
    "unique_digest_count",
    "digest_set_sha256",
    "overlap_with_prior_union",
    "net_new_to_union",
)
DERIVATION = {
    "task_digest": "SHA256(UTF-8(NFC(exact selected prompt text)))",
    "source_set_digest": "SHA256(LF-joined sorted unique source digests plus final LF)",
    "inventory_digest": "SHA256(LF-joined sorted unique union digests plus final LF)",
    "duplicate_policy": "set-union-with-overlap-accounted-per-source",
}
COVERAGE = {
    "source_count": 20,
    "prompt_occurrence_count": 849,
    "unique_digest_count": 768,
    "first_19_sources_pairwise_disjoint": True,
    "scenarios_overlap_with_prior_union": 81,
    "scenarios_net_new": 9,
    "enumerated_universe_complete": True,
    "scope": "the 20 exact frozen committed evaluation-prompt sources listed in this artifact",
}
LIMITATIONS = {
    "raw_task_text_embedded": False,
    "case_or_scenario_objects_embedded": False,
    "labels_embedded": False,
    "results_or_events_embedded": False,
    "semantic_similarity_proven": False,
    "near_rewrite_detection_proven": False,
    "dictionary_resistance_claimed": False,
    "sources_outside_enumerated_universe_covered": False,
}

# logical role, commit, tree, path, blob, raw SHA-256, selector,
# occurrence count, unique count, set commitment, prior overlap, net-new count.
PINNED_SOURCES = (
    (
        "committed-eval-prompt-source-01",
        "340b79399a987e6aad0d5435fa540a1db511489d",
        "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
        "evals/foundation-v4/future-activation-v2/activation-authoring.json",
        "abe198d0c7f97797a1112454edabbdbd4b2c4aa1",
        "e077a07b99f8782656cd59619eb13e287bb3fc4e6fed3e5fdc8b256b9b97f038",
        "cases[].prompt",
        36,
        36,
        "2582680911971a625bce90d3b4f89cb2cabf9ad87b4f2c3d70c1776b551bffdf",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-02",
        "340b79399a987e6aad0d5435fa540a1db511489d",
        "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
        "evals/foundation-v4/future-activation-v2/activation-heldout.json",
        "5200a3c4fb529fc5673d83ae7c1e248cceb3842f",
        "2af0e58c0c8b9e009bc7b8716850dc02e000e9702cfdd0bc90cf96740e45d66e",
        "cases[].prompt",
        36,
        36,
        "4dd1454dab4ddede45000d6d19ea0c954d73db64a0904d88b1d748b7943d0bea",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-03",
        "340b79399a987e6aad0d5435fa540a1db511489d",
        "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
        "evals/foundation-v4/future-activation-v3/activation-authoring.json",
        "3c4d307e6ca85a7a251bb97926125e297d47a50a",
        "f67d9e31e64e3c37dde389f984e41b963224263cbe8e82c1643c25a9fee91b65",
        "cases[].prompt",
        36,
        36,
        "9d08d6e0dce059712dbdd35c1fedd28603c7b707a3a8b350d094895f183d10a1",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-04",
        "340b79399a987e6aad0d5435fa540a1db511489d",
        "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
        "evals/foundation-v4/future-activation-v3/activation-heldout.json",
        "3f0f5c7544f96e59c282acc9e56cf15a466e40a9",
        "b02773d6757f37a332aaf8d43f78cc1061ac060ef45a253451fded012c40bd75",
        "cases[].prompt",
        36,
        36,
        "f061f6fa83ddcccf3bf1d20250d9fd23a77d3086d8e7b7efb164dd1a068b57f2",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-05",
        "340b79399a987e6aad0d5435fa540a1db511489d",
        "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
        "evals/foundation-v4/future-activation-v4/activation-authoring.json",
        "867610fe6219fbc7302e74e58dbd4caaead1cc22",
        "149a4b88ba49493d03d9ac625891f1a45e818e6d2349f108e4129ba2dd2548f4",
        "cases[].prompt",
        36,
        36,
        "f460a77f7f9351ac2a93349f3e980c74882a225ef73c985b361b9e18f7c619a2",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-06",
        "340b79399a987e6aad0d5435fa540a1db511489d",
        "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
        "evals/foundation-v4/future-activation-v4/activation-heldout.json",
        "205b6c0e5820e0759a1f0267d05b283d4cf220a5",
        "376291b0f0b6c3a9e20cbe608aa74dd1cbcbf3241d59b33c2f2ec717f4964fac",
        "cases[].prompt",
        36,
        36,
        "85e3baaef31e9711e87afbec81531f07b7c029c73ba4bee1ee15bc658399c52c",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-07",
        "340b79399a987e6aad0d5435fa540a1db511489d",
        "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
        "evals/foundation-v4/future-activation-v5/activation-authoring.json",
        "3bc824272b308dae8046ff82fb3e6a9e74f1e26a",
        "69e5e796f191165a2556054caf3aa961e4a03a48025ac18bccc6b2e7b1bca4b3",
        "cases[].prompt",
        36,
        36,
        "1fc5c57ea6f93a4ad123e052cde789d3159aabc30c36ef657a182b3c2aff34a9",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-08",
        "340b79399a987e6aad0d5435fa540a1db511489d",
        "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
        "evals/foundation-v4/future-activation-v5/activation-heldout.json",
        "c98e13c1f7382ead31704ffe21492ff8fc67ab4e",
        "c884713124f12271cd7bdd4cbed43f47312f2d15c0f16339ab954b9db65b971f",
        "cases[].prompt",
        36,
        36,
        "db28418e1765d6943a7505e5c4d6dd434dcb510e499231d6e0e1b0a41de263e6",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-09",
        "340b79399a987e6aad0d5435fa540a1db511489d",
        "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
        "evals/foundation-v4/future-activation-v6/activation-authoring.json",
        "d569b81e4a8a6c0de73c38b76e6f47979c539eec",
        "0c8b8430cfde0dea2f40c78423dd5aaeaf2a8c97052252bd11c448693d087d3f",
        "cases[].prompt",
        36,
        36,
        "4023b592a8029a583e166fbf857b817a28058ece1259c0af8682a1643937f808",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-10",
        "340b79399a987e6aad0d5435fa540a1db511489d",
        "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
        "evals/foundation-v4/future-activation-v6/activation-heldout.json",
        "9a58fe46ff58a35ac4bde6ab3f4ed128f13b37d3",
        "05f4570284a4149e40d8f710100490e1a67d0a8362e69a3b40e5901214ded102",
        "cases[].prompt",
        36,
        36,
        "f44e15a02cd45f23b9ab7665cb1053f26a4fd7de504b7b52d8916b661c805566",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-11",
        "340b79399a987e6aad0d5435fa540a1db511489d",
        "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
        "evals/foundation-v4/future-activation-v7/activation-authoring.json",
        "fafc31402ab1c604069bfa4595e9e78fb8b6d239",
        "331c24018ca70164eaddf88ac6ff4a0cbe6a94b6017a9e73223559f6d264a225",
        "cases[].packet.task_text",
        36,
        36,
        "2062d3f9f02f3ef179b8e20747ce5436e2b450afee16558612c575b007eed4df",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-12",
        "340b79399a987e6aad0d5435fa540a1db511489d",
        "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
        "evals/foundation-v4/future-activation-v7/activation-heldout.json",
        "298b2bc9a07b4eedbed98c5aacf02ca0911dc4a0",
        "fec755bd8838b3e23e96e8374bb28ad3e06229c176058a5a020f4a528326afd3",
        "cases[].packet.task_text",
        36,
        36,
        "8fec5cded0d60d2f8f3138db28aa13f5f05039565896904e4d94f013d154d1d0",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-13",
        "340b79399a987e6aad0d5435fa540a1db511489d",
        "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
        "evals/foundation-v4/future-activation-v8/activation-authoring.json",
        "5698051d33cf69768fa7f26b06116576cf2001e7",
        "08318e0f01b386bba2a0932915a87d07e637ed5b495e822308c42c8371d63a4d",
        "cases[].task_text",
        36,
        36,
        "30fdcf127d751953dc58dd51b91607bf99ebf4f1c237c997046b3793d17dd559",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-14",
        "340b79399a987e6aad0d5435fa540a1db511489d",
        "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
        "evals/foundation-v4/future-activation-v8/activation-heldout.json",
        "72086b219f1a92210bbf31c4b70caa711ee09baa",
        "db9c55fff89bdb636f977bb6bebd4b88830d09e6ffa3d0f09c8d4c120eb42227",
        "cases[].task_text",
        36,
        36,
        "7157513c5aa2df1238302bab8ca59da0b2e2f50c7ad13ced57bbc9dfc28a5902",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-15",
        "407a2ac124856f0ce1fa33af8a61d0607e413820",
        "8314ca6ad82fa4687720692d8c5762c7aabf6261",
        "evals/routing-cases.json",
        "7f5ea934a2e01ec9c594afeab0fe541526c776f7",
        "24ce4002d2d846f7e58aba7ed96a6258553a5053d46067049dc8c7012d3a1e28",
        "cases[].prompt",
        143,
        143,
        "922ecd10e6f00be048e0cbe0222a73234b44b1ad01bba91c19456fdb09f2a3f8",
        0,
        143,
    ),
    (
        "committed-eval-prompt-source-16",
        "407a2ac124856f0ce1fa33af8a61d0607e413820",
        "8314ca6ad82fa4687720692d8c5762c7aabf6261",
        "evals/foundation-v4/activation-authoring.json",
        "8b6714cae19bc609cc2bf55cc3691c233a55785a",
        "e1dba40f8c0c5a6bfcf43394cdf49b4085e9110c4bd018aa8fdaa6470fe79588",
        "cases[].prompt",
        36,
        36,
        "826357dbc617b44ef1461939c43ca626a92bd14ac31bd7eecea6729aa5b5b764",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-17",
        "407a2ac124856f0ce1fa33af8a61d0607e413820",
        "8314ca6ad82fa4687720692d8c5762c7aabf6261",
        "evals/foundation-v4/activation-heldout.json",
        "dc6221054da898fb608670fa0aa87c91ce6288d8",
        "f8849201ec99ab52b3e629d9aba7e11c24325e0db608df964234b60f182b79d1",
        "cases[].prompt",
        36,
        36,
        "141f45b32037e61acb6401d4c21c15505c9cf333d48a1b08c924eb3952f71c74",
        0,
        36,
    ),
    (
        "committed-eval-prompt-source-18",
        "f0b377accbebc9612f198123cacf7f34b5fce89e",
        "bfc25b7a77fa1d1c2a4102e0dfb23ad1b329a28d",
        "evals/ae-sq1/aq/corpus-split-a.json",
        "2b9803375d617aa0e4325845f05492ca076bcab2",
        "d75dfb4ad1b72838729fb47343081cadcc741fd39e5f893a05fd92b53d36d11a",
        "cases[].task_text",
        20,
        20,
        "c5a98aac58fc9ded80d80c08508d659742899eb2f71bb96e1eb7b144ba304536",
        0,
        20,
    ),
    (
        "committed-eval-prompt-source-19",
        "f0b377accbebc9612f198123cacf7f34b5fce89e",
        "bfc25b7a77fa1d1c2a4102e0dfb23ad1b329a28d",
        "evals/ae-sq1/aq/corpus-split-b.json",
        "1659006fb2e809563e0718691435cdbf01749f38",
        "e10b41fd2a48b3fdd254e64f8543d8613a824f2daaacf070d0d5f27e7921ba93",
        "cases[].task_text",
        20,
        20,
        "489efd73494b77ba8763507989f639a56befd86626a838311aed218513231595",
        0,
        20,
    ),
    (
        "committed-eval-prompt-source-20",
        "f3055c9ffc3b2d7f41de76fb53a5b8fa06d0a916",
        "632fbb5101910f19aa642303c769fce0c6a46698",
        "evals/scenarios.json",
        "a9700cbda6f747f8400d8aae49486eafd7a4e8c8",
        "3b503618ef08168dd39b8a03446ab8b9862e795b425b9c14a41c7dda0304ef07",
        "scenarios[].prompt",
        90,
        90,
        "c1a75d30c21c0cb870381a0e2ed5a47b2258532dafbe848986cbb6c65c334326",
        81,
        9,
    ),
)


def _closed_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def load_closed(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_closed_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid strict JSON") from error
    if type(value) is not dict:
        raise ValueError("root must be an object")
    return value


def _hex(value: Any, length: int) -> bool:
    return (
        type(value) is str
        and len(value) == length
        and all(char in "0123456789abcdef" for char in value)
    )


def _source_rows(document: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    sources = document.get("sources")
    if type(sources) is not list:
        raise ValueError("sources")
    observed: list[tuple[Any, ...]] = []
    for source in sources:
        if type(source) is not dict or tuple(source) != SOURCE_KEYS:
            raise ValueError("source order/closure")
        observed.append(tuple(source[key] for key in SOURCE_KEYS))
    return tuple(observed)


def _exact_closed_mapping(
    value: Any, expected: dict[str, Any], description: str
) -> None:
    if type(value) is not dict:
        raise ValueError(description)
    if tuple(value) != tuple(expected) or value != expected:
        raise ValueError(f"{description} order/closure/value")


def validate(document: dict[str, Any]) -> None:
    if type(document) is not dict or tuple(document) != TOP_KEYS:
        raise ValueError("top-level order/closure")
    if document["schema_version"] != "AE-SQ3-historical-task-digests-v2":
        raise ValueError("schema identity")
    if document["program_id"] != "AE-SQ3":
        raise ValueError("program identity")
    if document["role"] != "historical_digest_inventory":
        raise ValueError("role identity")
    if document["claim_ceiling"] != (
        "exact-nfc-sha256-nonreuse-vs-enumerated-20-frozen-committed-"
        "eval-prompt-sources-only"
    ):
        raise ValueError("claim ceiling")

    _exact_closed_mapping(document["derivation"], DERIVATION, "derivation")
    rows = _source_rows(document)
    if rows != PINNED_SOURCES:
        raise ValueError("source custody/order/completeness")
    for row in rows:
        (
            role,
            commit,
            tree,
            path,
            blob,
            raw_sha,
            selector,
            occurrences,
            unique_count,
            set_sha,
            overlap,
            net_new,
        ) = row
        if not role.startswith("committed-eval-prompt-source-"):
            raise ValueError("source role")
        if not _hex(commit, 40) or not _hex(tree, 40) or not _hex(blob, 40):
            raise ValueError("source Git identity")
        if not _hex(raw_sha, 64) or not _hex(set_sha, 64):
            raise ValueError("source SHA-256 identity")
        if type(path) is not str or type(selector) is not str:
            raise ValueError("source path/selector")
        if any(type(value) is not int for value in (occurrences, unique_count, overlap, net_new)):
            raise ValueError("source count type")
        if occurrences <= 0 or unique_count <= 0 or unique_count > occurrences:
            raise ValueError("source count range")
        if overlap < 0 or net_new < 0 or overlap + net_new != unique_count:
            raise ValueError("source overlap arithmetic")

    digests = document["task_text_nfc_sha256"]
    if type(digests) is not list or len(digests) != 768:
        raise ValueError("inventory size")
    if any(not _hex(value, 64) for value in digests):
        raise ValueError("inventory digest")
    if digests != sorted(digests) or len(set(digests)) != 768:
        raise ValueError("inventory order/uniqueness")
    if type(document["inventory_count"]) is not int:
        raise ValueError("inventory count type")
    if document["inventory_count"] != 768:
        raise ValueError("inventory count")
    if document["inventory_sha256"] != INVENTORY_SHA256:
        raise ValueError("inventory pinned commitment")
    if _set_commitment(digests) != INVENTORY_SHA256:
        raise ValueError("inventory content commitment")

    _exact_closed_mapping(document["coverage"], COVERAGE, "coverage")
    _exact_closed_mapping(document["limitations"], LIMITATIONS, "limitations")


def _git_bytes(*arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise ValueError("pinned Git authority unavailable")
    return completed.stdout


def _git_oid(*arguments: str) -> str:
    try:
        return _git_bytes(*arguments).decode("ascii", errors="strict").strip()
    except UnicodeDecodeError as error:
        raise ValueError("pinned Git identity invalid") from error


def _selected_texts(document: dict[str, Any], selector: str) -> tuple[str, ...]:
    if selector.startswith("cases[]"):
        collection = document.get("cases")
    elif selector.startswith("scenarios[]"):
        collection = document.get("scenarios")
    else:
        raise ValueError("historical task selector invalid")
    if type(collection) is not list:
        raise ValueError("historical collection invalid")

    values: list[str] = []
    try:
        for item in collection:
            if type(item) is not dict:
                raise ValueError("historical item invalid")
            if selector in ("cases[].prompt", "scenarios[].prompt"):
                value = item["prompt"]
            elif selector == "cases[].packet.task_text":
                packet = item["packet"]
                if type(packet) is not dict:
                    raise ValueError("historical packet invalid")
                value = packet["task_text"]
            elif selector == "cases[].task_text":
                value = item["task_text"]
            else:
                raise ValueError("historical task selector invalid")
            if type(value) is not str:
                raise ValueError("historical task value invalid")
            values.append(value)
    except KeyError as error:
        raise ValueError("historical task extraction invalid") from error
    return tuple(values)


def _set_commitment(values: Any) -> str:
    ordered = sorted(set(values))
    return hashlib.sha256(("\n".join(ordered) + "\n").encode("ascii")).hexdigest()


def recompute_from_pinned_git(
    document: dict[str, Any],
) -> tuple[tuple[str, ...], tuple[frozenset[str], ...], int]:
    """Recompute digest custody from pinned bytes without returning prompt text."""
    validate(document)
    prior_union: set[str] = set()
    source_sets: list[frozenset[str]] = []
    occurrence_total = 0

    for source in document["sources"]:
        commit = _git_oid("rev-parse", f"{source['commit']}^{{commit}}")
        tree = _git_oid("rev-parse", f"{source['commit']}^{{tree}}")
        if commit != source["commit"] or tree != source["tree"]:
            raise ValueError("pinned commit/tree mismatch")
        blob = _git_oid("rev-parse", f"{commit}:{source['path']}")
        if blob != source["git_blob"]:
            raise ValueError("pinned blob mismatch")
        raw = _git_bytes("cat-file", "blob", blob)
        if hashlib.sha256(raw).hexdigest() != source["raw_sha256"]:
            raise ValueError("pinned file SHA-256 mismatch")

        historical = load_closed(raw)
        selected = _selected_texts(historical, source["task_text_selector"])
        if len(selected) != source["occurrence_count"]:
            raise ValueError("pinned source occurrence count mismatch")
        occurrence_total += len(selected)
        digests = tuple(
            hashlib.sha256(
                unicodedata.normalize("NFC", value).encode("utf-8")
            ).hexdigest()
            for value in selected
        )
        source_set = frozenset(digests)
        if len(source_set) != source["unique_digest_count"]:
            raise ValueError("pinned source unique count mismatch")
        if _set_commitment(source_set) != source["digest_set_sha256"]:
            raise ValueError("pinned source set commitment mismatch")
        if len(source_set & prior_union) != source["overlap_with_prior_union"]:
            raise ValueError("pinned source prior-overlap mismatch")
        if len(source_set - prior_union) != source["net_new_to_union"]:
            raise ValueError("pinned source net-new mismatch")
        source_sets.append(source_set)
        prior_union.update(source_set)

    if occurrence_total != 849:
        raise ValueError("recomputed occurrence total mismatch")
    if len(prior_union) != 768:
        raise ValueError("recomputed union count mismatch")
    ordered_union = tuple(sorted(prior_union))
    if list(ordered_union) != document["task_text_nfc_sha256"]:
        raise ValueError("recomputed union differs from artifact inventory")
    if _set_commitment(ordered_union) != INVENTORY_SHA256:
        raise ValueError("recomputed union commitment mismatch")
    return ordered_union, tuple(source_sets), occurrence_total


def assert_digest_only_artifact(document: dict[str, Any], artifact_raw: bytes) -> None:
    """Prove prompt and labeled/result objects are absent without echoing content."""
    validate(document)
    artifact_text = artifact_raw.decode("utf-8", errors="strict")
    labeled_or_result_fields = (
        "expected_semantic_output",
        "expected_parent_derivation",
        "expected_skills",
        "must_not_select",
        "rationale",
        "category",
        "mode",
        "authority",
        "condition_blind",
        "labels_visible_to_runner",
        "outcomes_visible_to_authoring",
        "hidden_labels",
        "near_neighbor_kind",
        "declared_invocation",
        "profile",
        "explicit_slot_id",
        "expected_capsules",
        "expected_resolution",
        "domain",
        "expected_topology",
        "required_decisions",
        "forbidden_behaviors",
        "evidence_requirements",
        "severity",
        "aggregate_result",
        "per_case",
        "provider_log",
        "trajectory",
        "model_id",
        "result",
        "output",
        "response",
        "events",
    )
    for field in labeled_or_result_fields:
        if f'"{field}"' in artifact_text:
            raise ValueError("labeled or result payload field leaked")

    for source in document["sources"]:
        raw = _git_bytes("cat-file", "blob", source["git_blob"])
        historical = load_closed(raw)
        for text in _selected_texts(historical, source["task_text_selector"]):
            if text and text in artifact_text:
                raise ValueError("historical prompt text leaked")


class HistoricalTaskDigestManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = PATH.read_bytes()
        cls.document = load_closed(cls.raw)

    def test_manifest_is_exactly_closed_and_self_consistent(self) -> None:
        validate(self.document)

    def test_all_20_pinned_sources_recompute_849_occurrences_and_768_union(self) -> None:
        union, source_sets, occurrences = recompute_from_pinned_git(self.document)
        self.assertEqual(20, len(source_sets))
        self.assertEqual(849, occurrences)
        self.assertEqual(768, len(union))
        self.assertEqual(INVENTORY_SHA256, _set_commitment(union))

    def test_first_19_sources_are_pairwise_disjoint(self) -> None:
        _, source_sets, _ = recompute_from_pinned_git(self.document)
        for left_index in range(19):
            for right_index in range(left_index + 1, 19):
                self.assertTrue(
                    source_sets[left_index].isdisjoint(source_sets[right_index])
                )

    def test_scenarios_overlap_81_and_add_exactly_9(self) -> None:
        _, source_sets, _ = recompute_from_pinned_git(self.document)
        prior_union = frozenset().union(*source_sets[:19])
        scenarios = source_sets[19]
        self.assertEqual(81, len(prior_union & scenarios))
        self.assertEqual(9, len(scenarios - prior_union))
        self.assertEqual(768, len(prior_union | scenarios))

    def test_artifact_contains_no_raw_prompt_label_or_result_payload(self) -> None:
        assert_digest_only_artifact(self.document, self.raw)

    def test_missing_extra_reordered_and_duplicate_mutations_are_rejected(self) -> None:
        mutations: list[dict[str, Any]] = []

        missing_top = copy.deepcopy(self.document)
        missing_top.pop("inventory_sha256")
        mutations.append(missing_top)
        extra_top = copy.deepcopy(self.document)
        extra_top["extra"] = "forbidden"
        mutations.append(extra_top)
        mutations.append({key: self.document[key] for key in reversed(TOP_KEYS)})

        for field, expected in (
            ("derivation", DERIVATION),
            ("coverage", COVERAGE),
            ("limitations", LIMITATIONS),
        ):
            missing = copy.deepcopy(self.document)
            missing[field].pop(next(iter(expected)))
            mutations.append(missing)
            extra = copy.deepcopy(self.document)
            extra[field]["extra"] = "forbidden"
            mutations.append(extra)
            reordered = copy.deepcopy(self.document)
            reordered[field] = {
                key: reordered[field][key] for key in reversed(expected)
            }
            mutations.append(reordered)

        missing_source = copy.deepcopy(self.document)
        missing_source["sources"] = missing_source["sources"][:-1]
        mutations.append(missing_source)
        extra_source = copy.deepcopy(self.document)
        extra_source["sources"].append(copy.deepcopy(extra_source["sources"][-1]))
        mutations.append(extra_source)
        reordered_sources = copy.deepcopy(self.document)
        reordered_sources["sources"][0], reordered_sources["sources"][1] = (
            reordered_sources["sources"][1],
            reordered_sources["sources"][0],
        )
        mutations.append(reordered_sources)
        duplicate_source = copy.deepcopy(self.document)
        duplicate_source["sources"][1] = copy.deepcopy(duplicate_source["sources"][0])
        mutations.append(duplicate_source)
        reordered_source_fields = copy.deepcopy(self.document)
        reordered_source_fields["sources"][0] = {
            key: reordered_source_fields["sources"][0][key]
            for key in reversed(SOURCE_KEYS)
        }
        mutations.append(reordered_source_fields)
        extra_source_field = copy.deepcopy(self.document)
        extra_source_field["sources"][0]["result"] = "forbidden"
        mutations.append(extra_source_field)

        missing_digest = copy.deepcopy(self.document)
        missing_digest["task_text_nfc_sha256"] = missing_digest[
            "task_text_nfc_sha256"
        ][:-1]
        mutations.append(missing_digest)
        extra_digest = copy.deepcopy(self.document)
        extra_digest["task_text_nfc_sha256"].append("f" * 64)
        mutations.append(extra_digest)
        reordered_digests = copy.deepcopy(self.document)
        reordered_digests["task_text_nfc_sha256"].reverse()
        mutations.append(reordered_digests)
        duplicate_digest = copy.deepcopy(self.document)
        duplicate_digest["task_text_nfc_sha256"][1] = duplicate_digest[
            "task_text_nfc_sha256"
        ][0]
        mutations.append(duplicate_digest)

        wrong_count_type = copy.deepcopy(self.document)
        wrong_count_type["inventory_count"] = True
        mutations.append(wrong_count_type)
        wrong_source_count_type = copy.deepcopy(self.document)
        wrong_source_count_type["sources"][0]["occurrence_count"] = True
        mutations.append(wrong_source_count_type)
        elevated_claim = copy.deepcopy(self.document)
        elevated_claim["limitations"]["semantic_similarity_proven"] = True
        mutations.append(elevated_claim)

        for mutation in mutations:
            with self.assertRaises(ValueError):
                validate(mutation)

    def test_duplicate_keys_nonfinite_and_invalid_utf8_are_rejected(self) -> None:
        for raw in (
            b'{"program_id":"AE-SQ3","program_id":"AE-SQ2"}',
            b'{"derivation":{"task_digest":"a","task_digest":"b"}}',
            b'{"sources":[{"commit":"a","commit":"b"}]}',
            b'{"coverage":{"source_count":20,"source_count":19}}',
            b'{"value":NaN}',
            b'{"value":Infinity}',
            b'{"value":-Infinity}',
            b"\xff",
        ):
            with self.assertRaises(ValueError):
                load_closed(raw)


if __name__ == "__main__":
    unittest.main()
