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
PATH = ROOT / "evals/ae-sq1/historical-task-digests.json"
TOP_KEYS = (
    "schema_version",
    "program_id",
    "claim_ceiling",
    "source",
    "files",
    "task_text_nfc_sha256",
    "inventory_count",
    "inventory_sha256",
    "limitations",
)
PINNED_SOURCE = {
    "commit": "340b79399a987e6aad0d5435fa540a1db511489d",
    "tree": "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933",
    "task_digest_derivation": "SHA256(UTF-8(NFC(exact extracted task text)))",
}
PINNED_FILES = (
    (
        "evals/foundation-v4/future-activation-v2/activation-authoring.json",
        "abe198d0c7f97797a1112454edabbdbd4b2c4aa1",
        "e077a07b99f8782656cd59619eb13e287bb3fc4e6fed3e5fdc8b256b9b97f038",
        "cases[].prompt",
        36,
    ),
    (
        "evals/foundation-v4/future-activation-v2/activation-heldout.json",
        "5200a3c4fb529fc5673d83ae7c1e248cceb3842f",
        "2af0e58c0c8b9e009bc7b8716850dc02e000e9702cfdd0bc90cf96740e45d66e",
        "cases[].prompt",
        36,
    ),
    (
        "evals/foundation-v4/future-activation-v3/activation-authoring.json",
        "3c4d307e6ca85a7a251bb97926125e297d47a50a",
        "f67d9e31e64e3c37dde389f984e41b963224263cbe8e82c1643c25a9fee91b65",
        "cases[].prompt",
        36,
    ),
    (
        "evals/foundation-v4/future-activation-v3/activation-heldout.json",
        "3f0f5c7544f96e59c282acc9e56cf15a466e40a9",
        "b02773d6757f37a332aaf8d43f78cc1061ac060ef45a253451fded012c40bd75",
        "cases[].prompt",
        36,
    ),
    (
        "evals/foundation-v4/future-activation-v4/activation-authoring.json",
        "867610fe6219fbc7302e74e58dbd4caaead1cc22",
        "149a4b88ba49493d03d9ac625891f1a45e818e6d2349f108e4129ba2dd2548f4",
        "cases[].prompt",
        36,
    ),
    (
        "evals/foundation-v4/future-activation-v4/activation-heldout.json",
        "205b6c0e5820e0759a1f0267d05b283d4cf220a5",
        "376291b0f0b6c3a9e20cbe608aa74dd1cbcbf3241d59b33c2f2ec717f4964fac",
        "cases[].prompt",
        36,
    ),
    (
        "evals/foundation-v4/future-activation-v5/activation-authoring.json",
        "3bc824272b308dae8046ff82fb3e6a9e74f1e26a",
        "69e5e796f191165a2556054caf3aa961e4a03a48025ac18bccc6b2e7b1bca4b3",
        "cases[].prompt",
        36,
    ),
    (
        "evals/foundation-v4/future-activation-v5/activation-heldout.json",
        "c98e13c1f7382ead31704ffe21492ff8fc67ab4e",
        "c884713124f12271cd7bdd4cbed43f47312f2d15c0f16339ab954b9db65b971f",
        "cases[].prompt",
        36,
    ),
    (
        "evals/foundation-v4/future-activation-v6/activation-authoring.json",
        "d569b81e4a8a6c0de73c38b76e6f47979c539eec",
        "0c8b8430cfde0dea2f40c78423dd5aaeaf2a8c97052252bd11c448693d087d3f",
        "cases[].prompt",
        36,
    ),
    (
        "evals/foundation-v4/future-activation-v6/activation-heldout.json",
        "9a58fe46ff58a35ac4bde6ab3f4ed128f13b37d3",
        "05f4570284a4149e40d8f710100490e1a67d0a8362e69a3b40e5901214ded102",
        "cases[].prompt",
        36,
    ),
    (
        "evals/foundation-v4/future-activation-v7/activation-authoring.json",
        "fafc31402ab1c604069bfa4595e9e78fb8b6d239",
        "331c24018ca70164eaddf88ac6ff4a0cbe6a94b6017a9e73223559f6d264a225",
        "cases[].packet.task_text",
        36,
    ),
    (
        "evals/foundation-v4/future-activation-v7/activation-heldout.json",
        "298b2bc9a07b4eedbed98c5aacf02ca0911dc4a0",
        "fec755bd8838b3e23e96e8374bb28ad3e06229c176058a5a020f4a528326afd3",
        "cases[].packet.task_text",
        36,
    ),
    (
        "evals/foundation-v4/future-activation-v8/activation-authoring.json",
        "5698051d33cf69768fa7f26b06116576cf2001e7",
        "08318e0f01b386bba2a0932915a87d07e637ed5b495e822308c42c8371d63a4d",
        "cases[].task_text",
        36,
    ),
    (
        "evals/foundation-v4/future-activation-v8/activation-heldout.json",
        "72086b219f1a92210bbf31c4b70caa711ee09baa",
        "db9c55fff89bdb636f977bb6bebd4b88830d09e6ffa3d0f09c8d4c120eb42227",
        "cases[].task_text",
        36,
    ),
)
LIMITATIONS = {
    "task_text_exposed_to_successor_authors": False,
    "semantic_similarity_proven": False,
    "near_rewrite_detection_proven": False,
    "dictionary_resistance_claimed": False,
    "legacy_v4_v5_stored_prompt_sha256_used_as_task_digest": False,
}


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
    if not isinstance(value, dict):
        raise ValueError("root must be an object")
    return value


def _hex(value: Any, length: int) -> bool:
    return (
        type(value) is str
        and len(value) == length
        and all(char in "0123456789abcdef" for char in value)
    )


def _rows(document: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    files = document.get("files")
    if type(files) is not list:
        raise ValueError("files")
    observed: list[tuple[Any, ...]] = []
    for row in files:
        if type(row) is not dict or tuple(row) != (
            "path",
            "git_blob",
            "sha256",
            "task_text_selector",
            "digest_count",
        ):
            raise ValueError("file closure")
        observed.append(
            (
                row["path"],
                row["git_blob"],
                row["sha256"],
                row["task_text_selector"],
                row["digest_count"],
            )
        )
    return tuple(observed)


def validate(document: dict[str, Any]) -> None:
    if tuple(document) != TOP_KEYS:
        raise ValueError("top-level order/closure")
    if document["schema_version"] != "1.1" or document["program_id"] != "AE-SQ1":
        raise ValueError("identity")
    if document["claim_ceiling"] != "exact-nfc-sha256-nonreuse-only":
        raise ValueError("claim ceiling")
    source = document["source"]
    if type(source) is not dict or dict(source) != PINNED_SOURCE:
        raise ValueError("source custody")
    if tuple(source) != tuple(PINNED_SOURCE):
        raise ValueError("source order/closure")
    if not _hex(source["commit"], 40) or not _hex(source["tree"], 40):
        raise ValueError("source identity")

    rows = _rows(document)
    if rows != PINNED_FILES:
        raise ValueError("file custody/order/completeness")
    if any(
        not _hex(blob, 40)
        or not _hex(raw_sha, 64)
        or type(count) is not int
        or count != 36
        for _, blob, raw_sha, _, count in rows
    ):
        raise ValueError("file metadata")

    digests = document["task_text_nfc_sha256"]
    if type(digests) is not list or len(digests) != 504:
        raise ValueError("inventory count")
    if digests != sorted(digests) or len(set(digests)) != 504:
        raise ValueError("inventory order/uniqueness")
    if any(not _hex(value, 64) for value in digests):
        raise ValueError("inventory digest")
    if type(document["inventory_count"]) is not int:
        raise ValueError("declared inventory count type")
    if document["inventory_count"] != len(digests):
        raise ValueError("declared inventory count")
    expected = hashlib.sha256(("\n".join(digests) + "\n").encode("ascii")).hexdigest()
    if document["inventory_sha256"] != expected:
        raise ValueError("inventory custody")

    limitations = document["limitations"]
    if type(limitations) is not dict or tuple(limitations) != tuple(LIMITATIONS):
        raise ValueError("limitations closure")
    if dict(limitations) != LIMITATIONS:
        raise ValueError("limitations")


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


def _task_texts(document: dict[str, Any], selector: str) -> tuple[str, ...]:
    cases = document.get("cases")
    if type(cases) is not list:
        raise ValueError("historical cases invalid")
    values: list[str] = []
    try:
        for case in cases:
            if type(case) is not dict:
                raise ValueError("historical case invalid")
            if selector == "cases[].prompt":
                value = case["prompt"]
            elif selector == "cases[].packet.task_text":
                packet = case["packet"]
                if type(packet) is not dict:
                    raise ValueError("historical packet invalid")
                value = packet["task_text"]
            elif selector == "cases[].task_text":
                value = case["task_text"]
            else:
                raise ValueError("historical task selector invalid")
            if type(value) is not str:
                raise ValueError("historical task value invalid")
            values.append(value)
    except KeyError as error:
        raise ValueError("historical task extraction invalid") from error
    return tuple(values)


def recompute_from_pinned_git(
    document: dict[str, Any],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Independently derive every digest from pinned blob bytes without echoing text."""
    validate(document)
    source = document["source"]
    commit = _git_oid("rev-parse", f"{source['commit']}^{{commit}}")
    tree = _git_oid("rev-parse", f"{source['commit']}^{{tree}}")
    if commit != source["commit"] or tree != source["tree"]:
        raise ValueError("pinned source mismatch")

    task_digests: list[str] = []
    task_texts: list[str] = []
    for row in document["files"]:
        blob = _git_oid("rev-parse", f"{commit}:{row['path']}")
        if blob != row["git_blob"]:
            raise ValueError("pinned blob mismatch")
        raw = _git_bytes("cat-file", "blob", blob)
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("pinned file SHA-256 mismatch")
        historical = load_closed(raw)
        extracted = _task_texts(historical, row["task_text_selector"])
        if len(extracted) != row["digest_count"]:
            raise ValueError("pinned file task count mismatch")
        task_texts.extend(extracted)
        task_digests.extend(
            hashlib.sha256(
                unicodedata.normalize("NFC", value).encode("utf-8")
            ).hexdigest()
            for value in extracted
        )

    task_digests.sort()
    if len(task_digests) != 504 or len(set(task_digests)) != 504:
        raise ValueError("recomputed inventory count/uniqueness mismatch")
    if task_digests != document["task_text_nfc_sha256"]:
        raise ValueError("recomputed inventory differs from pinned task text")
    return tuple(task_digests), tuple(task_texts)


def legacy_v4_v5_substitution(document: dict[str, Any]) -> tuple[str, ...]:
    """Recreate the rejected normalized-prompt substitution without text output."""
    values: list[str] = []
    commit = document["source"]["commit"]
    for row in document["files"]:
        raw = _git_bytes("cat-file", "blob", row["git_blob"])
        historical = load_closed(raw)
        is_legacy = "/future-activation-v4/" in row["path"] or (
            "/future-activation-v5/" in row["path"]
        )
        if is_legacy:
            cases = historical.get("cases")
            if type(cases) is not list:
                raise ValueError("legacy cases invalid")
            for case in cases:
                if type(case) is not dict:
                    raise ValueError("legacy case invalid")
                stored = case.get("prompt_sha256")
                normalized = case.get("normalized_prompt")
                if not _hex(stored, 64) or type(normalized) is not str:
                    raise ValueError("legacy prompt digest invalid")
                if hashlib.sha256(normalized.encode("utf-8")).hexdigest() != stored:
                    raise ValueError("legacy normalized prompt custody invalid")
                values.append(stored)
        else:
            blob = _git_oid("rev-parse", f"{commit}:{row['path']}")
            if blob != row["git_blob"]:
                raise ValueError("pinned blob mismatch")
            extracted = _task_texts(historical, row["task_text_selector"])
            values.extend(
                hashlib.sha256(
                    unicodedata.normalize("NFC", value).encode("utf-8")
                ).hexdigest()
                for value in extracted
            )
    values.sort()
    return tuple(values)


class HistoricalTaskDigestManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = PATH.read_bytes()
        cls.document = load_closed(cls.raw)

    def test_manifest_is_closed_and_self_consistent(self) -> None:
        validate(self.document)

    def test_all_pinned_git_bytes_recompute_exact_504_row_inventory(self) -> None:
        recomputed, _ = recompute_from_pinned_git(self.document)
        observed = set(self.document["task_text_nfc_sha256"])
        expected = set(recomputed)
        self.assertEqual(504, len(expected & observed))
        self.assertEqual(0, len(expected - observed))
        self.assertEqual(0, len(observed - expected))

    def test_legacy_v4_v5_prompt_sha256_substitution_is_rejected(self) -> None:
        exact = set(self.document["task_text_nfc_sha256"])
        legacy = legacy_v4_v5_substitution(self.document)
        self.assertEqual(504, len(legacy))
        self.assertEqual(504, len(set(legacy)))
        self.assertEqual(368, len(exact & set(legacy)))
        self.assertEqual(136, len(exact - set(legacy)))
        self.assertEqual(136, len(set(legacy) - exact))

        substituted = copy.deepcopy(self.document)
        substituted["task_text_nfc_sha256"] = list(legacy)
        substituted["inventory_sha256"] = hashlib.sha256(
            ("\n".join(legacy) + "\n").encode("ascii")
        ).hexdigest()
        validate(substituted)
        with self.assertRaisesRegex(ValueError, "recomputed inventory differs"):
            recompute_from_pinned_git(substituted)

    def test_manifest_contains_no_historical_text_or_outcome_payload(self) -> None:
        _, task_texts = recompute_from_pinned_git(self.document)
        for task_text in task_texts:
            if task_text.encode("utf-8") in self.raw:
                self.fail("historical task text leaked into digest inventory")
        lowered = self.raw.lower()
        for forbidden in (
            b'"aggregate_result"',
            b'"per_case"',
            b'"provider_log"',
            b'"trajectory"',
            b'"model_id"',
            b'"result"',
            b'"output"',
        ):
            if forbidden in lowered:
                self.fail("historical outcome or provider material leaked")

    def test_missing_extra_reordered_and_duplicate_rows_are_rejected(self) -> None:
        mutations: list[dict[str, Any]] = []

        missing_top = copy.deepcopy(self.document)
        missing_top.pop("inventory_sha256")
        mutations.append(missing_top)
        mutations.append({key: self.document[key] for key in reversed(TOP_KEYS)})

        for operation in ("missing", "extra", "reordered", "duplicate"):
            source = copy.deepcopy(self.document)
            if operation == "missing":
                source["source"].pop("tree")
            elif operation == "extra":
                source["source"]["extra"] = "forbidden"
            elif operation == "reordered":
                source["source"] = {
                    key: source["source"][key] for key in reversed(PINNED_SOURCE)
                }
            else:
                source["source"]["tree"] = source["source"]["commit"]
            mutations.append(source)

        missing_file = copy.deepcopy(self.document)
        missing_file["files"] = missing_file["files"][:-1]
        mutations.append(missing_file)
        extra_file = copy.deepcopy(self.document)
        extra_file["files"].append(copy.deepcopy(extra_file["files"][-1]))
        mutations.append(extra_file)
        reordered_file = copy.deepcopy(self.document)
        reordered_file["files"][0], reordered_file["files"][1] = (
            reordered_file["files"][1],
            reordered_file["files"][0],
        )
        mutations.append(reordered_file)
        duplicate_file = copy.deepcopy(self.document)
        duplicate_file["files"][1] = copy.deepcopy(duplicate_file["files"][0])
        mutations.append(duplicate_file)

        missing_task = copy.deepcopy(self.document)
        missing_task["task_text_nfc_sha256"] = missing_task["task_text_nfc_sha256"][:-1]
        missing_task["inventory_count"] = 503
        mutations.append(missing_task)
        extra_task = copy.deepcopy(self.document)
        extra_task["task_text_nfc_sha256"].append("f" * 64)
        extra_task["inventory_count"] = 505
        mutations.append(extra_task)
        reordered_task = copy.deepcopy(self.document)
        reordered_task["task_text_nfc_sha256"].reverse()
        mutations.append(reordered_task)
        duplicate_task = copy.deepcopy(self.document)
        duplicate_task["task_text_nfc_sha256"][1] = duplicate_task[
            "task_text_nfc_sha256"
        ][0]
        mutations.append(duplicate_task)

        wrong_count_type = copy.deepcopy(self.document)
        wrong_count_type["inventory_count"] = True
        mutations.append(wrong_count_type)
        elevated = copy.deepcopy(self.document)
        elevated["limitations"]["semantic_similarity_proven"] = True
        mutations.append(elevated)
        extra_file_field = copy.deepcopy(self.document)
        extra_file_field["files"][0]["result"] = "pass"
        mutations.append(extra_file_field)

        for mutation in mutations:
            with self.assertRaises(ValueError):
                validate(mutation)

    def test_duplicate_keys_nonfinite_and_invalid_utf8_are_rejected(self) -> None:
        for raw in (
            b'{"schema_version":"1.1","schema_version":"2.0"}',
            b'{"source":{"commit":"a","commit":"b"}}',
            b'{"files":[{"path":"a","path":"b"}]}',
            b'{"value":NaN}',
            b"\xff",
        ):
            with self.assertRaises(ValueError):
                load_closed(raw)


if __name__ == "__main__":
    unittest.main()
