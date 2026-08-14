#!/usr/bin/env python3
"""Strict, zero-write validator for the fresh AE-SQ8 AQ corpus pair.

Corpus splits may be caller-supplied bytes or in-memory mappings.  The one-way
historical digest authority is accepted only as its trusted raw bytes.  The
validator never opens historical corpora, never emits task text, and cannot
turn an absent historical authority into a non-replay PASS.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator
from resolve_ae_sq8_slec import (
    SLECError,
    normalize_runtime_capsule as _canonical_slec_normalize,
    resolve_capsules as _canonical_slec_resolve,
)


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
AQ_ROOT = ROOT / "evals/ae-sq8/f1"
SCHEMA_PATH = AQ_ROOT / "corpus-schema.json"
GATES_PATH = AQ_ROOT / "gates.json"
METRICS_PATH = AQ_ROOT / "metrics.json"
EVALUATOR_SCHEMA_PATH = AQ_ROOT / "evaluator-schema.json"
CANDIDATE_AUTHORITY_PATH = AQ_ROOT / "slec8-authority.json"
CANDIDATE_POLICY_PATH = AQ_ROOT / "slec8-reference-policy.json"
CANDIDATE_RESOLUTION_SCHEMA_PATH = AQ_ROOT / "slec8-resolution-schema.json"
CANDIDATE_SEMANTIC_SCHEMA_PATH = AQ_ROOT / "slec8-semantic-capsule-schema.json"

PROGRAM_ID = "AE-SQ8"
CORPUS_ID = "AE-SQ8-AQ-FRESH-V1"
SLOT_ORDER = ("s0", "s1", "s2", "s3")
CONDITIONS = ("current", "reduced")
SCHEDULE_SEED = "AE-SQ8-AQ-FRESH-V1-SCHEDULE"
NORMALIZATION_ID = "ae-sq8-task-v1"
EXPECTED_PROFILES = Counter(
    {"none": 6, "single": 16, "two": 8, "cap": 4, "explicit": 4, "uncertain": 2}
)
EXPECTED_SINGLE_SLOTS = Counter({slot: 4 for slot in SLOT_ORDER})
EXPECTED_EXPLICIT_SLOTS = Counter({slot: 1 for slot in SLOT_ORDER})
ALL_PAIRS = {
    (left, right)
    for index, left in enumerate(SLOT_ORDER)
    for right in SLOT_ORDER[index + 1 :]
}
NEAR_SIMILARITY_THRESHOLD = 0.80
MIN_NEAR_TEXT_LENGTH = 24
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_TOKEN = re.compile(r"[a-z0-9]+")
TRUSTED_HISTORICAL_INVENTORY_SHA256 = (
    "0e49a967d9a59021c0f1aa5fc8d80fd53fdf3ab1885925b0d86f1e8c4f9dc157"
)
TRUSTED_HISTORICAL_CONTENT_SHA256 = (
    "8ee69ae06f388c1b47386b312d31bcce7ae408d04e76659653335d55e12ac270"
)
HISTORICAL_TOP_KEYS = (
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
HISTORICAL_DERIVATION = {
    "task_digest": "SHA256(UTF-8(NFC(exact selected prompt text)))",
    "source_set_digest": (
        "SHA256(LF-joined sorted unique source digests plus final LF)"
    ),
    "inventory_digest": "SHA256(LF-joined sorted unique union digests plus final LF)",
    "duplicate_policy": "set-union-with-overlap-accounted-per-source",
}
HISTORICAL_SOURCES_SHA256 = (
    "1279b46945bb56b107a7463e9000c7f460e64e7404c09db72ee96cb934df60e0"
)
HISTORICAL_COVERAGE = {
    "source_count": 20,
    "prompt_occurrence_count": 849,
    "unique_digest_count": 768,
    "first_19_sources_pairwise_disjoint": True,
    "scenarios_overlap_with_prior_union": 81,
    "scenarios_net_new": 9,
    "enumerated_universe_complete": True,
    "scope": "the 20 exact frozen committed evaluation-prompt sources listed in this artifact",
}
HISTORICAL_LIMITATIONS = {
    "raw_task_text_embedded": False,
    "case_or_scenario_objects_embedded": False,
    "labels_embedded": False,
    "results_or_events_embedded": False,
    "semantic_similarity_proven": False,
    "near_rewrite_detection_proven": False,
    "dictionary_resistance_claimed": False,
    "sources_outside_enumerated_universe_covered": False,
}


class CorpusContractError(ValueError):
    """A closed corpus or authority invariant was violated."""


@dataclass(frozen=True)
class ValidationResult:
    status: str
    errors: tuple[str, ...]
    holds: tuple[str, ...]
    metrics: dict[str, int]
    qualified_case_ids: tuple[str, ...]
    corpus_digest: str | None

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    @property
    def structurally_valid(self) -> bool:
        return not self.errors


def canonical_json(value: Any) -> bytes:
    """Return the sole canonical byte representation used for local digests."""
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as error:
        raise CorpusContractError("value is not canonical JSON") from error
    return text.encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(value: Any) -> str:
    return sha256(canonical_json(value))


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CorpusContractError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(_: str) -> Any:
    raise CorpusContractError("non-finite JSON constant")


def parse_json(raw: bytes) -> dict[str, Any]:
    """Parse strict UTF-8 JSON while rejecting duplicate keys and NaN/Infinity."""
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_closed_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CorpusContractError("invalid strict JSON") from error
    if not isinstance(value, dict):
        raise CorpusContractError("root must be an object")
    _validate_json_domain(value)
    return value


def _validate_json_domain(value: Any) -> None:
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise CorpusContractError("all strings must be NFC")
        return
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CorpusContractError("non-finite number")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_domain(item)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CorpusContractError("object key must be a string")
            _validate_json_domain(key)
            _validate_json_domain(item)
        return
    raise CorpusContractError("unsupported JSON value")


def _as_document(value: bytes | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, bytes):
        return parse_json(value)
    if not isinstance(value, Mapping):
        raise CorpusContractError("document must be bytes or a mapping")
    # Round-trip mappings through the strict representation.  Duplicate keys
    # cannot survive construction, while all other byte-domain rules still do.
    return parse_json(canonical_json(value))


def contract_digests() -> dict[str, str]:
    paths = {
        "corpus_contract_sha256": SCHEMA_PATH,
        "gates_sha256": GATES_PATH,
        "metrics_sha256": METRICS_PATH,
        "evaluator_schema_sha256": EVALUATOR_SCHEMA_PATH,
    }
    try:
        return {name: sha256(path.read_bytes()) for name, path in paths.items()}
    except OSError as error:
        raise CorpusContractError("AQ contract authority unavailable") from error


def authority_digest(authority: Mapping[str, Any]) -> str:
    return digest(dict(authority))


def expected_split_authority(profile: Mapping[str, Any]) -> dict[str, str]:
    """Derive the sole lawful split authority from a verified F1B profile.

    Candidate identity is deliberately the F1A implementation. F1B remains a
    separately bound freeze object. This boundary rejects merely string-shaped
    custody so an unchecked caller cannot substitute malformed Git identities
    or digests for the checker-verified profile.
    """
    try:
        bindings = profile["bindings"]
        result = {
            "program_id": PROGRAM_ID,
            "candidate_id": "AE-SQ8-SLEC-8",
            "candidate_commit": profile["implementation_commit"],
            "candidate_tree": profile["implementation_tree"],
            "f1_freeze_sha256": profile["freeze_sha256"],
            "corpus_contract_sha256": bindings["corpus_schema"]["sha256"],
            "gates_sha256": bindings["gates"]["sha256"],
            "metrics_sha256": bindings["metrics"]["sha256"],
            "evaluator_schema_sha256": bindings["evaluator_schema"]["sha256"],
        }
    except (KeyError, TypeError) as error:
        raise CorpusContractError("verified F1 profile is incomplete") from error
    if (
        profile.get("program_id") != PROGRAM_ID
        or profile.get("candidate_id") != "AE-SQ8-SLEC-8"
        or profile.get("freeze_commit") == profile.get("implementation_commit")
        or not all(isinstance(value, str) for value in result.values())
        or _HEX40.fullmatch(result["candidate_commit"]) is None
        or _HEX40.fullmatch(result["candidate_tree"]) is None
        or any(
            _HEX64.fullmatch(result[field]) is None
            for field in (
                "f1_freeze_sha256",
                "corpus_contract_sha256",
                "gates_sha256",
                "metrics_sha256",
                "evaluator_schema_sha256",
            )
        )
    ):
        raise CorpusContractError("verified F1 profile identity is invalid")
    return result


def task_digest(task_text: str) -> str:
    if unicodedata.normalize("NFC", task_text) != task_text:
        raise CorpusContractError("task is not NFC")
    return sha256(task_text.encode("utf-8"))


def expected_case_nonce(split_nonce: str, case_id: str, task_sha256: str) -> str:
    return sha256(f"{PROGRAM_ID}|{split_nonce}|{case_id}|{task_sha256}".encode("ascii"))


def _candidate_custody(path: Path) -> tuple[bytes, str]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise CorpusContractError("candidate custody unavailable") from error
    return raw, sha256(raw)


def candidate_custody() -> dict[str, tuple[bytes, str]]:
    """Return exact raw-plus-digest candidate inputs for pure local validation."""
    return {
        "authority": _candidate_custody(CANDIDATE_AUTHORITY_PATH),
        "policy": _candidate_custody(CANDIDATE_POLICY_PATH),
        "resolution_schema": _candidate_custody(CANDIDATE_RESOLUTION_SCHEMA_PATH),
        "semantic_schema": _candidate_custody(CANDIDATE_SEMANTIC_SCHEMA_PATH),
    }


def _capsule_ingress(capsule: Mapping[str, Any]) -> tuple[bytes, str]:
    if not isinstance(capsule, Mapping):
        raise CorpusContractError("capsule row must be an object")
    anchors = capsule.get("anchors")
    if not isinstance(anchors, list):
        raise CorpusContractError("capsule anchors must be an array")
    ordered = {
        "slot_id": capsule.get("slot_id"),
        "local_need": capsule.get("local_need"),
        "reference_need": capsule.get("reference_need"),
        "anchors": [
            {"start": row.get("start"), "end": row.get("end"), "text": row.get("text")}
            if isinstance(row, Mapping)
            else row
            for row in anchors
        ],
    }
    raw = json.dumps(
        ordered,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("ascii")
    return raw, sha256(raw)


def resolve_expected_capsules(
    task_text: str,
    condition: str,
    capsules: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Delegate all candidate semantics to the canonical SLEC-8 resolver."""
    try:
        return resolve_capsule_ingresses(
            task_text,
            condition,
            tuple(_capsule_ingress(capsule) for capsule in capsules),
        )
    except (SLECError, CorpusContractError, TypeError, ValueError) as error:
        raise CorpusContractError("canonical candidate resolution failed") from error


def selected_reference_anchors_valid(
    resolution: Mapping[str, Any], capsules: Sequence[Mapping[str, Any]]
) -> bool:
    """Apply the production selected-reference invariant to resolved capsules."""
    selected = resolution.get("selected_slots")
    if not isinstance(selected, list):
        return False
    selected_rows = {
        row.get("slot_id"): row
        for row in capsules
        if isinstance(row, Mapping) and row.get("slot_id") in selected
    }
    reference_requiring_rows = [
        row
        for row in capsules
        if isinstance(row, Mapping) and row.get("local_need") == "yes"
    ]
    return (
        len(selected_rows) == len(selected)
        and all(
            row.get("reference_need") in {"core", "focused"}
            for row in selected_rows.values()
        )
        and all(
            row.get("reference_need") in {"core", "focused"}
            for row in reference_requiring_rows
        )
    )


def selected_reference_anchor_fixture() -> dict[str, Any]:
    """Exercise the exact resolver and production anchor invariant without corpus data."""
    task = "Synthetic noncorpus reference-anchor gate requests bounded architecture advice."
    whole = [{"start": 0, "end": len(task), "text": task}]

    def capsules(reference_need: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for slot in SLOT_ORDER:
            selected = slot == "s0"
            uncertain = selected and reference_need == "uncertain"
            rows.append(
                {
                    "slot_id": slot,
                    "local_need": "yes" if selected else "no",
                    "reference_need": reference_need if selected else "none",
                    "anchors": [] if uncertain else list(whole),
                }
            )
        return rows

    positive = capsules("focused")
    missing = capsules("none")
    wrong = capsules("uncertain")
    positive_resolution = resolve_expected_capsules(task, "current", positive)
    missing_resolution = resolve_expected_capsules(task, "current", missing)
    wrong_resolution = resolve_expected_capsules(task, "current", wrong)
    if not selected_reference_anchors_valid(positive_resolution, positive):
        raise CorpusContractError("selected-reference positive fixture failed")
    if selected_reference_anchors_valid(missing_resolution, missing):
        raise CorpusContractError("selected-reference missing fixture accepted")
    if selected_reference_anchors_valid(wrong_resolution, wrong):
        raise CorpusContractError("selected-reference wrong fixture accepted")
    return {
        "production_validator": "validate_corpora:selected_reference_anchors_valid",
        "production_resolver": "resolve_expected_capsules",
        "positive": {"status": "PASS"},
        "red_missing": {
            "error": "selected_reference_anchor",
            "status": "REJECTED",
        },
        "red_wrong": {
            "error": "selected_reference_anchor",
            "status": "REJECTED",
        },
    }


def normalize_capsule_ingress(
    task_text: str,
    expected_slot: str,
    capsule_ingress: tuple[bytes, str],
) -> dict[str, str]:
    """Authenticate and normalize one exact runtime capsule via SLEC-8 only."""
    custody = candidate_custody()
    try:
        return _canonical_slec_normalize(
            task_text,
            expected_slot,
            capsule_ingress,
            custody["authority"],
            custody["semantic_schema"],
        )
    except (SLECError, TypeError, ValueError) as error:
        raise CorpusContractError("canonical capsule normalization failed") from error


def resolve_capsule_ingresses(
    task_text: str,
    condition: str,
    capsule_ingresses: Sequence[tuple[bytes, str]],
) -> dict[str, Any]:
    """Resolve four exact runtime ingresses through the canonical SLEC-8 fold."""
    custody = candidate_custody()
    try:
        record = _canonical_slec_resolve(
            task=task_text,
            condition_id=condition,
            capsule_ingresses=capsule_ingresses,
            authority_custody=custody["authority"],
            policy_custody=custody["policy"],
            resolution_schema_custody=custody["resolution_schema"],
            semantic_schema_custody=custody["semantic_schema"],
        )
    except (SLECError, TypeError, ValueError) as error:
        raise CorpusContractError("canonical candidate resolution failed") from error
    status_map = {
        "selected": "selected",
        "no_selection": "none",
        "abstain_cap": "cap_abstain",
        "abstain_uncertain": "uncertain_abstain",
    }
    status = status_map.get(record.get("resolution_status"))
    selected = record.get("selected_slots")
    outcomes = record.get("slot_outcomes")
    if (
        status is None
        or not isinstance(selected, list)
        or not isinstance(outcomes, list)
    ):
        raise CorpusContractError("canonical candidate abstained invalid")
    references = [
        {"slot_id": row["slot_id"], "need": row["reference_need"]}
        for row in outcomes
        if isinstance(row, Mapping)
        and row.get("slot_id") in selected
        and row.get("reference_need") in {"core", "focused"}
        and record.get("selection_mode") != "explicit_invocation"
    ]
    return {
        "status": status,
        "selected_slots": selected,
        "reference_bundle": references,
    }


def _derived_profile(case: Mapping[str, Any]) -> str:
    capsules = case["expected_capsules"]
    explicit = case["explicit_slot_id"]
    resolution = resolve_expected_capsules(case["task_text"], "current", capsules)
    yes_slots = [row["slot_id"] for row in capsules if row["local_need"] == "yes"]
    if explicit is not None:
        if resolution["status"] != "selected" or resolution["selected_slots"] != [
            explicit
        ]:
            raise CorpusContractError("explicit profile is not exact")
        return "explicit"
    if resolution["status"] == "uncertain_abstain":
        return "uncertain"
    if resolution["status"] == "cap_abstain":
        return "cap"
    if len(yes_slots) == 0:
        return "none"
    if len(yes_slots) == 1:
        return "single"
    if len(yes_slots) == 2:
        return "two"
    raise CorpusContractError("profile cannot be derived")


def normalize_task(task_text: str) -> str:
    normalized = unicodedata.normalize("NFC", task_text).casefold()
    return " ".join(_TOKEN.findall(normalized))


def normalized_task_digest(task_text: str) -> str:
    return sha256(normalize_task(task_text).encode("utf-8"))


def _fivegrams(value: str) -> set[str]:
    compact = " ".join(value.split())
    if len(compact) < 5:
        return {compact}
    return {compact[index : index + 5] for index in range(len(compact) - 4)}


def near_similarity(left: str, right: str) -> float:
    left_set, right_set = (
        _fivegrams(normalize_task(left)),
        _fivegrams(normalize_task(right)),
    )
    union = left_set | right_set
    return len(left_set & right_set) / len(union) if union else 1.0


def build_schedule(
    case_ids: Sequence[str], seed: str = SCHEDULE_SEED
) -> tuple[dict[str, Any], ...]:
    if (
        len(case_ids) != 40
        or len(set(case_ids)) != 40
        or any(not isinstance(item, str) for item in case_ids)
    ):
        raise CorpusContractError("schedule requires forty unique case IDs")
    if not isinstance(seed, str) or not seed:
        raise CorpusContractError("schedule seed invalid")
    rng = random.Random(int(sha256(seed.encode("utf-8")), 16))
    current, reduced = sorted(case_ids), sorted(case_ids)
    rng.shuffle(current)
    rng.shuffle(reduced)
    first = CONDITIONS[rng.randrange(2)]
    second = CONDITIONS[1] if first == CONDITIONS[0] else CONDITIONS[0]
    rows: list[dict[str, Any]] = []
    for current_id, reduced_id in zip(current, reduced, strict=True):
        for condition in (first, second):
            case_id = current_id if condition == "current" else reduced_id
            index = len(rows)
            presentation_id = sha256(
                f"{PROGRAM_ID}|{seed}|{index}|{condition}|{case_id}".encode("ascii")
            )
            rows.append(
                {
                    "presentation_index": index,
                    "presentation_id": presentation_id,
                    "condition": condition,
                    "case_id": case_id,
                }
            )
    return tuple(rows)


def schedule_digest(schedule: Sequence[Mapping[str, Any]]) -> str:
    return digest([dict(row) for row in schedule])


def capsule_packet_digest(
    *,
    binding_digest: str,
    schedule_sha256: str,
    condition: str,
    case_id: str,
    task_sha256: str,
    slot_id: str,
) -> str:
    packet = {
        "program_id": PROGRAM_ID,
        "binding_digest": binding_digest,
        "schedule_digest": schedule_sha256,
        "condition": condition,
        "case_id": case_id,
        "task_sha256": task_sha256,
        "slot_id": slot_id,
    }
    return digest(packet)


def _inventory(inventory: bytes) -> tuple[str, set[str]]:
    if not isinstance(inventory, bytes):
        raise CorpusContractError("historical inventory must be trusted raw bytes")
    document = parse_json(inventory)
    inventory_digest = sha256(inventory)
    if inventory_digest != TRUSTED_HISTORICAL_INVENTORY_SHA256:
        raise CorpusContractError("historical inventory is not the trusted artifact")
    if tuple(document) != HISTORICAL_TOP_KEYS:
        raise CorpusContractError("historical inventory is not closed")
    if (
        document["schema_version"] != "AE-SQ4-historical-task-digests-v2"
        or document["program_id"] != "AE-SQ4"
        or document["role"] != "historical_digest_inventory"
    ):
        raise CorpusContractError("historical inventory identity invalid")
    if document["claim_ceiling"] != (
        "exact-nfc-sha256-nonreuse-vs-enumerated-20-frozen-committed-"
        "eval-prompt-sources-only"
    ):
        raise CorpusContractError("historical inventory claim invalid")
    if (
        not isinstance(document["derivation"], Mapping)
        or tuple(document["derivation"]) != tuple(HISTORICAL_DERIVATION)
        or dict(document["derivation"]) != HISTORICAL_DERIVATION
    ):
        raise CorpusContractError("historical inventory derivation invalid")
    sources = document["sources"]
    source_keys = (
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
    if (
        not isinstance(sources, list)
        or len(sources) != 20
        or any(
            not isinstance(row, Mapping) or tuple(row) != source_keys for row in sources
        )
        or digest(sources) != HISTORICAL_SOURCES_SHA256
    ):
        raise CorpusContractError("historical inventory source custody invalid")

    values = document["task_text_nfc_sha256"]
    if (
        not isinstance(values, list)
        or len(values) != 768
        or values != sorted(values)
        or len(values) != len(set(values))
    ):
        raise CorpusContractError("historical digest inventory invalid")
    if any(not isinstance(item, str) or not _HEX64.fullmatch(item) for item in values):
        raise CorpusContractError("historical digest inventory invalid")
    if (
        type(document["inventory_count"]) is not int
        or document["inventory_count"] != 768
        or document["inventory_count"] != len(values)
    ):
        raise CorpusContractError("historical digest count mismatch")
    recomputed_inventory = sha256(("\n".join(values) + "\n").encode("ascii"))
    if (
        document["inventory_sha256"] != recomputed_inventory
        or document["inventory_sha256"] != TRUSTED_HISTORICAL_CONTENT_SHA256
    ):
        raise CorpusContractError("historical digest inventory custody invalid")
    coverage = document["coverage"]
    if (
        not isinstance(coverage, Mapping)
        or tuple(coverage) != tuple(HISTORICAL_COVERAGE)
        or dict(coverage) != HISTORICAL_COVERAGE
    ):
        raise CorpusContractError("historical inventory coverage invalid")
    limitations = document["limitations"]
    if (
        not isinstance(limitations, Mapping)
        or tuple(limitations) != tuple(HISTORICAL_LIMITATIONS)
        or dict(limitations) != HISTORICAL_LIMITATIONS
        or any(type(value) is not bool for value in limitations.values())
    ):
        raise CorpusContractError("historical inventory privacy claim invalid")
    return inventory_digest, set(values)


def _schema() -> dict[str, Any]:
    try:
        return parse_json(SCHEMA_PATH.read_bytes())
    except OSError as error:
        raise CorpusContractError("corpus schema unavailable") from error


def validate_corpora(
    documents: Sequence[bytes | Mapping[str, Any]],
    *,
    historical_digest_inventory: bytes | None = None,
    expected_authority: Mapping[str, Any] | None = None,
) -> ValidationResult:
    """Validate two splits against explicit, verified F1 authority.

    A caller that omits ``expected_authority`` can obtain content diagnostics,
    but can never receive qualification PASS.
    """
    errors: list[str] = []
    holds: list[str] = []
    metrics: Counter[str] = Counter()
    parsed: list[dict[str, Any]] = []
    if not isinstance(documents, (list, tuple)) or len(documents) != 2:
        return ValidationResult("fail", ("split_count",), (), {}, (), None)
    try:
        schema = _schema()
        validator = Draft202012Validator(schema)
        expected_contracts = contract_digests()
        for value in documents:
            document = _as_document(value)
            if list(validator.iter_errors(document)):
                errors.append("schema")
            parsed.append(document)
    except (CorpusContractError, OSError, TypeError, ValueError):
        return ValidationResult(
            "fail", ("strict_parse_or_authority",), (), {}, (), None
        )

    if errors:
        return ValidationResult("fail", tuple(sorted(set(errors))), (), {}, (), None)

    by_split = {document["split_id"]: document for document in parsed}
    if set(by_split) != {"A", "B"} or len(by_split) != 2:
        errors.append("split_identity")
    else:
        parsed = [by_split["A"], by_split["B"]]

    if len({document["split_nonce"] for document in parsed}) != 2:
        errors.append("split_nonce")
    # Split bytes only carry opaque references.  External F2 Git/orchestrator
    # receipts must establish author-commit isolation and process routing.
    if len({document["author_id"] for document in parsed}) != 2:
        errors.append("author_receipt_cross_reference_identity")
    authorities = [document["authority"] for document in parsed]
    if authorities[0] != authorities[1]:
        errors.append("authority_mismatch")
    if expected_authority is None:
        holds.append("expected_authority_unavailable")
    elif not isinstance(expected_authority, Mapping):
        errors.append("expected_authority_invalid")
    elif any(authority != dict(expected_authority) for authority in authorities):
        errors.append("expected_authority_mismatch")
    for authority in authorities:
        for field, expected in expected_contracts.items():
            if authority.get(field) != expected:
                errors.append("contract_binding")
    case_by_id: dict[str, dict[str, Any]] = {}
    task_normalizations: dict[str, str] = {}
    profile_counts: Counter[str] = Counter()
    single_slots: Counter[str] = Counter()
    explicit_slots: Counter[str] = Counter()
    two_pairs: Counter[tuple[str, str]] = Counter()
    split_texts: dict[str, list[str]] = {"A": [], "B": []}
    case_nonces: set[str] = set()

    for document in parsed:
        split_id = document["split_id"]
        expected_ids = [f"AE-SQ8-{split_id}-{ordinal:02d}" for ordinal in range(1, 21)]
        if [case["case_id"] for case in document["cases"]] != expected_ids:
            errors.append("case_identity_or_order")
        for case in document["cases"]:
            case_id = case["case_id"]
            if case_id in case_by_id:
                errors.append("duplicate_case")
                continue
            case_by_id[case_id] = case
            task_sha = task_digest(case["task_text"])
            if case["task_text_nfc_sha256"] != task_sha:
                errors.append("task_digest")
            expected_nonce = expected_case_nonce(
                document["split_nonce"], case_id, task_sha
            )
            if (
                case["case_nonce"] != expected_nonce
                or case["case_nonce"] in case_nonces
            ):
                errors.append("case_nonce")
            case_nonces.add(case["case_nonce"])
            normalized = normalize_task(case["task_text"])
            if normalized in task_normalizations:
                errors.append("exact_task_collision")
            task_normalizations[normalized] = case_id
            split_texts[split_id].append(case["task_text"])
            if [row.get("slot_id") for row in case["expected_capsules"]] != list(
                SLOT_ORDER
            ):
                errors.append("capsule_label_order")
            try:
                resolution = resolve_expected_capsules(
                    case["task_text"], "current", case["expected_capsules"]
                )
                reduced_resolution = resolve_expected_capsules(
                    case["task_text"], "reduced", case["expected_capsules"]
                )
                profile = _derived_profile(case)
            except (CorpusContractError, KeyError, TypeError):
                errors.append("derivation")
                continue
            if (
                case["expected_resolution"] != resolution
                or reduced_resolution != resolution
            ):
                errors.append("resolution_parity")
            if case["profile"] != profile:
                errors.append("profile_derivation")
            expected_selected = resolution["selected_slots"]
            if not selected_reference_anchors_valid(
                resolution, case["expected_capsules"]
            ):
                errors.append("selected_reference_anchor")
            profile_counts[profile] += 1
            if profile == "single":
                single_slots[expected_selected[0]] += 1
            elif profile == "explicit":
                explicit_slots[case["explicit_slot_id"]] += 1
            elif profile == "two":
                two_pairs[tuple(expected_selected)] += 1

    if len(case_by_id) != 40:
        errors.append("case_count")
    if profile_counts != EXPECTED_PROFILES:
        errors.append("profile_distribution")
    if single_slots != EXPECTED_SINGLE_SLOTS:
        errors.append("single_slot_distribution")
    if explicit_slots != EXPECTED_EXPLICIT_SLOTS:
        errors.append("explicit_slot_distribution")
    if set(two_pairs) != ALL_PAIRS:
        errors.append("two_pair_coverage")

    near_checks = 0
    for left in split_texts["A"]:
        for right in split_texts["B"]:
            near_checks += 1
            if (
                min(len(left), len(right)) >= MIN_NEAR_TEXT_LENGTH
                and near_similarity(left, right) >= NEAR_SIMILARITY_THRESHOLD
            ):
                errors.append("cross_split_near_collision")
    metrics["cross_split_similarity_checks"] = near_checks

    inventory_digest: str | None = None
    inventory_values: set[str] = set()
    if historical_digest_inventory is None:
        holds.append("historical_digest_inventory_unavailable")
    else:
        try:
            inventory_digest, inventory_values = _inventory(historical_digest_inventory)
        except (CorpusContractError, TypeError, KeyError):
            errors.append("historical_inventory")
        if inventory_digest is not None:
            if any(
                document["no_replay"]["historical_digest_inventory_sha256"]
                != inventory_digest
                for document in parsed
            ):
                errors.append("historical_inventory_binding")
            if any(
                task_digest(case["task_text"]) in inventory_values
                for case in case_by_id.values()
            ):
                errors.append("historical_digest_collision")
    if historical_digest_inventory is None and any(
        document["no_replay"]["historical_digest_inventory_sha256"] is not None
        for document in parsed
    ):
        holds.append("historical_digest_inventory_not_supplied_for_bound_digest")

    metrics.update(profile_counts)
    metrics["total_cases"] = len(case_by_id)
    metrics["historical_digest_count"] = len(inventory_values)
    corpus_digest_value = digest(parsed) if len(parsed) == 2 else None
    unique_errors = tuple(sorted(set(errors)))
    unique_holds = tuple(sorted(set(holds)))
    status = "fail" if unique_errors else ("hold" if unique_holds else "pass")
    return ValidationResult(
        status,
        unique_errors,
        unique_holds,
        dict(metrics),
        tuple(sorted(case_by_id)),
        corpus_digest_value,
    )


def _main(argv: Sequence[str]) -> int:
    if (
        len(argv) != 7
        or argv[1] != "--freeze-commit"
        or argv[3] != "--historical-inventory"
    ):
        print(
            "usage: validate_ae_sq8_corpus.py --freeze-commit F1B --historical-inventory INVENTORY SPLIT_A SPLIT_B",
            file=sys.stderr,
        )
        return 2
    try:
        from check_ae_sq8_candidate import load_verified_candidate

        profile = load_verified_candidate(ROOT, argv[2], require_live=True)
        expected_authority = expected_split_authority(profile)
        inventory = Path(argv[4]).read_bytes()
        documents = (Path(argv[5]).read_bytes(), Path(argv[6]).read_bytes())
        result = validate_corpora(
            documents,
            historical_digest_inventory=inventory,
            expected_authority=expected_authority,
        )
    except (CorpusContractError, OSError, ValueError):
        print("AE-SQ8 corpus validation: FAIL", file=sys.stderr)
        return 1
    # The CLI deliberately emits no task, case, or historical content.
    print(f"AE-SQ8 corpus validation: {result.status.upper()}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
