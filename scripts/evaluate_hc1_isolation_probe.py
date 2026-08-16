#!/usr/bin/env python3
"""Evaluate one synthetic host-isolation matrix without invoking the host probe.

This module owns the complete case matrix, canonical aggregate, schema check,
atomic write, and post-write verification.  It intentionally does not launch
Docker or contact a remote host; a separately authorized host adapter may feed
it child events and postchecks only after this evaluator is frozen.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

sys.dont_write_bytecode = True

SCHEMA_VERSION = "hc1-isolation-evaluator-summary-v1"
EVALUATOR_VERSION = "HC1-E1-V1"
ACCEPTANCE_CONTRACT = "process-exit-0-and-exact-pass-summary-v1"
SUMMARY_SCHEMA_PATH = Path("evals/host-isolation/hc1-evaluator-summary-schema.json")

EXPECTED_CASES: tuple[tuple[str, str], ...] = (
    ("positive", "PASS"),
    ("repository_read", "DENIED"),
    ("git_read", "DENIED"),
    ("predecessor_read", "DENIED"),
    ("sibling_read", "DENIED"),
    ("other_worktree_read", "DENIED"),
    ("absolute_escape", "DENIED"),
    ("dotdot_escape", "DENIED"),
    ("symlink_escape", "DENIED"),
    ("environment", "DENIED"),
    ("broad_search", "DENIED"),
    ("repository_write", "DENIED"),
    ("kit_write", "DENIED"),
    ("extra_output", "DENIED"),
    ("network", "DENIED"),
)

POSTCHECK_NAMES: tuple[str, ...] = (
    "forbidden_hash_unchanged",
    "kit_hash_unchanged",
    "no_surviving_children",
    "output_count_exact",
    "output_hash_exact",
    "unauthorized_writes_absent",
)

OBSERVED_OUTCOMES = frozenset({"PASS", "DENIED", "LEAK", "INVALID", "MISSING"})


class EvaluationError(ValueError):
    """Raised when evaluator inputs or a produced summary are not admissible."""


class PublicationError(EvaluationError):
    """Raised after PASS publication is rolled back or invalidated."""

    def __init__(
        self,
        message: str,
        *,
        rollback_installed: bool,
        rollback_durable: bool,
    ) -> None:
        super().__init__(message)
        self.rollback_installed = rollback_installed
        self.rollback_durable = rollback_durable


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise EvaluationError("value is not canonical finite JSON") from error


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw: bytes) -> Any:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise EvaluationError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise EvaluationError(f"non-finite JSON value: {value}")

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=object_pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvaluationError("invalid UTF-8 JSON") from error


def load_schema(root: Path) -> dict[str, Any]:
    raw = (root / SUMMARY_SCHEMA_PATH).read_bytes()
    value = strict_json(raw)
    if not isinstance(value, dict):
        raise EvaluationError("summary schema is not an object")
    Draft202012Validator.check_schema(value)
    return value


def _case_row(
    name: str, expected: str, event: Mapping[str, Any] | None
) -> dict[str, Any]:
    if event is None:
        return {
            "case": name,
            "child_started": False,
            "expected": expected,
            "observed": "MISSING",
            "rc": -1,
            "status": "HOLD",
        }
    child_started = event.get("child_started") is True
    observed = event.get("outcome")
    rc = event.get("rc")
    if observed not in OBSERVED_OUTCOMES:
        observed = "INVALID"
    if isinstance(rc, bool) or not isinstance(rc, int):
        rc = -1
    passed = child_started and observed == expected and rc == 0
    return {
        "case": name,
        "child_started": child_started,
        "expected": expected,
        "observed": observed,
        "rc": rc,
        "status": "PASS" if passed else "HOLD",
    }


def _unsigned_summary(
    events: Any,
    postchecks: Any,
    attempt_id: str,
) -> dict[str, Any]:
    if not isinstance(attempt_id, str) or not attempt_id:
        raise EvaluationError("attempt_id must be a nonempty string")

    failures: set[str] = set()
    indexed: dict[str, Mapping[str, Any]] = {}
    observed_count = 0
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes, bytearray)):
        failures.add("events:not-array")
        events = ()
    expected_names = {name for name, _ in EXPECTED_CASES}
    for index, event in enumerate(events):
        observed_count += 1
        if not isinstance(event, Mapping):
            failures.add(f"event:{index}:not-object")
            continue
        name = event.get("case")
        if not isinstance(name, str) or name not in expected_names:
            failures.add(f"event:{index}:unexpected-case")
            continue
        if name in indexed:
            failures.add(f"case:{name}:duplicate")
            continue
        indexed[name] = event

    rows: list[dict[str, Any]] = []
    for name, expected in EXPECTED_CASES:
        row = _case_row(name, expected, indexed.get(name))
        rows.append(row)
        if row["observed"] == "MISSING":
            failures.add(f"case:{name}:missing")
        if not row["child_started"]:
            failures.add(f"case:{name}:child-not-started")
        if row["observed"] != expected:
            failures.add(f"case:{name}:outcome")
        if row["rc"] != 0:
            failures.add(f"case:{name}:rc")

    normalized_postchecks: dict[str, bool] = {}
    if not isinstance(postchecks, Mapping):
        failures.add("postchecks:not-object")
        postchecks = {}
    unknown_postchecks = set(postchecks) - set(POSTCHECK_NAMES)
    for name in sorted(unknown_postchecks):
        failures.add(f"postcheck:{name}:unexpected")
    for name in POSTCHECK_NAMES:
        passed = postchecks.get(name) is True
        normalized_postchecks[name] = passed
        if not passed:
            failures.add(f"postcheck:{name}:failed-or-missing")

    status = "PASS" if not failures else "HOLD"
    return {
        "acceptance_contract": ACCEPTANCE_CONTRACT,
        "attempt_id": attempt_id,
        "capability_gate": status,
        "case_count_expected": len(EXPECTED_CASES),
        "case_count_observed": observed_count,
        "cases": rows,
        "evaluator_version": EVALUATOR_VERSION,
        "failures": sorted(failures),
        "postchecks": normalized_postchecks,
        "schema_version": SCHEMA_VERSION,
        "status": status,
    }


def evaluate(events: Any, postchecks: Any, attempt_id: str) -> dict[str, Any]:
    unsigned = _unsigned_summary(events, postchecks, attempt_id)
    return {"aggregate_sha256": sha256_bytes(canonical_json(unsigned)), **unsigned}


def validate_summary_document(document: Any, schema: Mapping[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        raise EvaluationError(f"summary schema violation: {errors[0].message}")
    if not isinstance(document, dict):
        raise EvaluationError("summary is not an object")
    unsigned = dict(document)
    aggregate = unsigned.pop("aggregate_sha256")
    if aggregate != sha256_bytes(canonical_json(unsigned)):
        raise EvaluationError("summary aggregate mismatch")
    if document["capability_gate"] != document["status"]:
        raise EvaluationError("status and capability gate differ")
    expected_order = [name for name, _ in EXPECTED_CASES]
    if [row["case"] for row in document["cases"]] != expected_order:
        raise EvaluationError("case order or closure drifted")
    expected_outcomes = dict(EXPECTED_CASES)
    for row in document["cases"]:
        if row["expected"] != expected_outcomes[row["case"]]:
            raise EvaluationError("case expectation drifted")
        row_should_pass = (
            row["child_started"] is True
            and row["observed"] == row["expected"]
            and row["rc"] == 0
        )
        if (row["status"] == "PASS") != row_should_pass:
            raise EvaluationError("case status does not match evidence")
    should_pass = (
        not document["failures"]
        and all(row["status"] == "PASS" for row in document["cases"])
        and all(document["postchecks"].values())
        and document["case_count_observed"] == len(EXPECTED_CASES)
    )
    if (document["status"] == "PASS") != should_pass:
        raise EvaluationError("summary status does not match evidence")
    if document["failures"] != sorted(document["failures"]):
        raise EvaluationError("failure list is not canonical")


def summary_bytes(document: Mapping[str, Any], schema: Mapping[str, Any]) -> bytes:
    validate_summary_document(document, schema)
    return canonical_json(document) + b"\n"


def verify_summary_bytes(raw: bytes, schema: Mapping[str, Any]) -> dict[str, Any]:
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise EvaluationError("summary must end in exactly one line feed")
    document = strict_json(raw)
    if not isinstance(document, dict) or canonical_json(document) + b"\n" != raw:
        raise EvaluationError("summary is not exact canonical JSON plus one line feed")
    validate_summary_document(document, schema)
    return document


def verify_accepted_summary(
    path: Path, process_exit_code: int, schema: Mapping[str, Any]
) -> dict[str, Any]:
    if process_exit_code != 0:
        raise EvaluationError("nonzero process exit cannot qualify a summary")
    document = verify_summary_bytes(path.read_bytes(), schema)
    if document["acceptance_contract"] != ACCEPTANCE_CONTRACT:
        raise EvaluationError("summary acceptance contract drifted")
    if document["status"] != "PASS" or document["capability_gate"] != "PASS":
        raise EvaluationError("exit zero does not bind an exact PASS summary")
    return document


def _prepare_summary_temp(path: Path, raw: bytes) -> Path:
    temporary: Path | None = None
    descriptor = -1
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=path.parent
        )
        temporary = Path(temporary_name)
        os.fchmod(descriptor, stat.S_IRUSR | stat.S_IWUSR)
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("summary write made no progress")
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        prepared = temporary
        temporary = None
        return prepared
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def atomic_write_summary(
    path: Path,
    raw: bytes,
    schema: Mapping[str, Any],
    *,
    rollback_raw: bytes | None = None,
) -> None:
    verify_summary_bytes(raw, schema)
    if rollback_raw is not None:
        rollback_document = verify_summary_bytes(rollback_raw, schema)
        if rollback_document["status"] != "HOLD":
            raise EvaluationError("publication rollback is not HOLD")
    parent = path.parent
    directory_descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    candidate: Path | None = None
    rollback: Path | None = None
    try:
        candidate = _prepare_summary_temp(path, raw)
        if rollback_raw is not None:
            rollback = _prepare_summary_temp(path, rollback_raw)
        os.replace(candidate, path)
        candidate = None
        try:
            os.fsync(directory_descriptor)
            if path.read_bytes() != raw:
                raise EvaluationError("post-write summary bytes drifted")
            verify_summary_bytes(path.read_bytes(), schema)
        except BaseException as publish_error:
            rollback_installed = False
            rollback_durable = False
            if rollback is not None and rollback_raw is not None:
                try:
                    os.replace(rollback, path)
                    rollback = None
                    rollback_installed = True
                    try:
                        os.fsync(directory_descriptor)
                        rollback_durable = True
                    except BaseException:
                        rollback_durable = False
                    if path.read_bytes() != rollback_raw:
                        raise EvaluationError("rollback summary bytes drifted")
                    verify_summary_bytes(path.read_bytes(), schema)
                except BaseException:
                    rollback_installed = False
            if not rollback_installed:
                try:
                    path.unlink(missing_ok=True)
                    os.fsync(directory_descriptor)
                except BaseException:
                    pass
            raise PublicationError(
                "PASS publication failed post-write verification",
                rollback_installed=rollback_installed,
                rollback_durable=rollback_durable,
            ) from publish_error
    finally:
        if candidate is not None:
            candidate.unlink(missing_ok=True)
        if rollback is not None:
            rollback.unlink(missing_ok=True)
        os.close(directory_descriptor)


def _exception_summary(attempt_id: str, error: BaseException) -> dict[str, Any]:
    document = evaluate((), {}, attempt_id)
    unsigned = dict(document)
    unsigned.pop("aggregate_sha256")
    unsigned["failures"] = sorted(
        set(unsigned["failures"]) | {f"evaluation-exception:{type(error).__name__}"}
    )
    unsigned["status"] = "HOLD"
    unsigned["capability_gate"] = "HOLD"
    return {"aggregate_sha256": sha256_bytes(canonical_json(unsigned)), **unsigned}


def execute(
    events: Any,
    postchecks: Any,
    attempt_id: str,
    output: Path,
    schema: Mapping[str, Any],
    evaluator: Callable[[Any, Any, str], dict[str, Any]] = evaluate,
) -> tuple[int, dict[str, Any] | None]:
    try:
        document = evaluator(events, postchecks, attempt_id)
        raw = summary_bytes(document, schema)
    except BaseException as error:
        try:
            document = _exception_summary(attempt_id, error)
            raw = summary_bytes(document, schema)
        except BaseException:
            return 70, None

    rollback: dict[str, Any] | None = None
    rollback_raw: bytes | None = None
    if document["status"] == "PASS":
        rollback = _exception_summary(
            attempt_id, EvaluationError("PASS publication rollback")
        )
        rollback_raw = summary_bytes(rollback, schema)
    try:
        atomic_write_summary(output, raw, schema, rollback_raw=rollback_raw)
        verified = verify_summary_bytes(output.read_bytes(), schema)
        return (0 if verified["status"] == "PASS" else 1), verified
    except PublicationError as error:
        if error.rollback_installed and rollback is not None:
            if error.rollback_durable:
                return 1, rollback
            return 70, None
        return 70, None
    except BaseException as error:
        try:
            if document["status"] == "HOLD":
                return 70, None
            fallback = rollback or _exception_summary(attempt_id, error)
            fallback_raw = rollback_raw or summary_bytes(fallback, schema)
            atomic_write_summary(output, fallback_raw, schema)
            verified = verify_summary_bytes(output.read_bytes(), schema)
            return 1, verified
        except BaseException:
            return 70, None


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--postchecks", type=Path, required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        schema = load_schema(repository_root())
        events = strict_json(args.events.read_bytes())
        postchecks = strict_json(args.postchecks.read_bytes())
    except (OSError, EvaluationError, ValueError) as error:
        print(f"hc1-evaluator input failure: {error}", file=sys.stderr)
        return 70
    code, document = execute(
        events,
        postchecks,
        args.attempt_id,
        args.summary,
        schema,
    )
    if document is None:
        print("hc1-evaluator failed without a valid durable summary", file=sys.stderr)
        return 70
    if code == 0:
        try:
            verify_accepted_summary(args.summary, code, schema)
        except (OSError, EvaluationError) as error:
            print(f"hc1-evaluator acceptance failure: {error}", file=sys.stderr)
            return 70
    sys.stdout.buffer.write(canonical_json(document) + b"\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
