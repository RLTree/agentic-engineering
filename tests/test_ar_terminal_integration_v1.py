from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "EXECPLAN.md"
DECISION_LOG = ROOT / "docs" / "foundations" / "decision-log.csv"
CURRENT_FOUNDATION = ROOT / "docs" / "foundations" / "current-2026-08-08.md"
SUCCESSOR_AUTHORITY = ROOT / "evals" / "ae-sq1" / "program-authority.json"
PLAN_PATH = "EXECPLAN.md"
DECISION_LOG_PATH = "docs/foundations/decision-log.csv"

AR_COMMIT = "8b08f2a829e05d8de6ed737321b4d1a32cc9df87"
AR_TREE = "777ab9af3450802b03679650d87441ab6a07495d"
AR_FILES = (
    (
        "evals/foundation-v4/ar-terminal-decision-v1.json",
        "841bab37a125a986da8b41d8591e6fc09da6ed26",
        "62f4f2f222962c58fdd5cca09231edb533ad5a4339e2f09a0e0084decb3dbc3b",
    ),
    (
        "tests/test_ar_terminal_decision_v1.py",
        "ab8da0e5bc38c2d8eb1ec9b4518abcb3f0c2b41e",
        "20ca2404034dc21e0aba1cfa2411f5255e664b49cec6a8a4d755f3ca9a7d767c",
    ),
)
AR_PATHS = frozenset(path for path, _, _ in AR_FILES)
HISTORICAL_PATHS = AR_PATHS | {PLAN_PATH, DECISION_LOG_PATH}

BASE_AR_CHECKBOX = (
    "- [ ] AR retire superseded current authority, publish the bounded decision, "
    "and stop."
)
TERMINAL_AR_CHECKBOX = BASE_AR_CHECKBOX.replace("[ ]", "[x]", 1)

PROGRESS_LINES = (
    "- [x] A0 re-resolve the candidate and establish current foundation authority.",
    "- [x] A1 align release identity and compute release results from executed checks.",
    "- [ ] AQ qualify activation, abstention, and bounded reference loading.",
    "- [ ] AS reduce and test four representative skills in isolation.",
    "- [ ] AC test bounded composition only if AS passes.",
    (
        "- [ ] AH verify exact archives, host behavior, UltraGoal coexistence, "
        "and protocol/supply-chain truth."
    ),
    "- [ ] AF run field evidence only if separately authorized and actually needed.",
    TERMINAL_AR_CHECKBOX,
)

TERMINAL_RECORD_LINES = (
    "AR-TERMINAL-RECORD:",
    "decision=DO_NOT_RELEASE_OR_PROMOTE",
    "claim_ceiling=structural-terminal-closeout-only",
    f"custody_commit={AR_COMMIT}",
    f"custody_tree={AR_TREE}",
    (
        "artifact=evals/foundation-v4/ar-terminal-decision-v1.json"
        "|blob=841bab37a125a986da8b41d8591e6fc09da6ed26"
        "|sha256=62f4f2f222962c58fdd5cca09231edb533ad5a4339e2f09a0e0084decb3dbc3b"
    ),
    (
        "test=tests/test_ar_terminal_decision_v1.py"
        "|blob=ab8da0e5bc38c2d8eb1ec9b4518abcb3f0c2b41e"
        "|sha256=20ca2404034dc21e0aba1cfa2411f5255e664b49cec6a8a4d755f3ca9a7d767c"
    ),
    (
        "unmet_successful_program_conditions=package_reproducibility,archive_safety,"
        "four_skill_activation_and_isolated_value,"
        "exact_archive_host_install_discovery_coexistence,"
        "protocol_AH_verification,field_usefulness"
    ),
    "deletion=not_authorized_or_executed",
    "migration=not_authorized_or_executed",
    "action=none_authorized_or_executed",
    (
        "forbidden_actions=release,promote,publish,model_execution,field_execution,"
        "deletion,migration_execution,reopen,downstream_stage_execution"
    ),
    (
        "owner_decisions_below="
        "superseded_for_this_terminal_program_no_later_authorization_cure"
    ),
    "permanently_blocked=AQ9,AS,AC,AH,AF",
    "terminal_state=STOP",
)
TERMINAL_RECORD = "\n".join(TERMINAL_RECORD_LINES)
TERMINAL_BLOCK = f"```text\n{TERMINAL_RECORD}\n```"
PLAN_INSERTION_ANCHOR = (
    "- no parallel audit, receipt, source-law, or superseded-plan graph remains "
    "active.\n\n"
)

DECISION_LOG_HEADER = (
    "decision_id",
    "repository",
    "foundation_id",
    "observed_change",
    "affected_decision",
    "decision_owner",
    "disposition_no_change_update_replace_retire",
    "implementation_or_test_delta",
    "claim_ceiling",
    "review_trigger",
    "date",
    "candidate_commit",
    "notes",
)
TERMINAL_DECISION_ROW = (
    "AE-AR-TERMINAL-2026-08-10",
    "RLTree/agentic-engineering",
    "current-2026-08-08",
    (
        "terminal AR pair records a bounded structural closeout after the terminal "
        "AQ9 process failure; no prohibited detail"
    ),
    "further program execution",
    "root conductor",
    "retire",
    (
        "record DO_NOT_RELEASE_OR_PROMOTE and STOP only; retain all surfaces in "
        "place; execute no deletion, migration, release, promotion, publication, "
        "model, field, or downstream-stage action"
    ),
    "structural-terminal-closeout-only",
    "none; terminal STOP; do not reopen",
    "2026-08-10",
    AR_COMMIT,
    (
        f"tree {AR_TREE}; artifact path "
        "evals/foundation-v4/ar-terminal-decision-v1.json blob "
        "841bab37a125a986da8b41d8591e6fc09da6ed26 SHA256 "
        "62f4f2f222962c58fdd5cca09231edb533ad5a4339e2f09a0e0084decb3dbc3b; "
        "test path tests/test_ar_terminal_decision_v1.py blob "
        "ab8da0e5bc38c2d8eb1ec9b4518abcb3f0c2b41e SHA256 "
        "20ca2404034dc21e0aba1cfa2411f5255e664b49cec6a8a4d755f3ca9a7d767c; "
        "successful-program conditions remain unmet; AQ9/AS/AC/AH/AF "
        "permanently blocked"
    ),
)

CURRENT_FOUNDATION_SUCCESSOR_POINTER = (
    "**Active successor plan:** `docs/exec-plans/active/ae-sq1.md` for AE-SQ1 "
    "only; `EXECPLAN.md` remains immutable predecessor terminal history"
)
SUCCESSOR_F0_DECISION_ROW = (
    "AE-SQ1-F0-2026-08-10",
    "RLTree/agentic-engineering",
    "current-2026-08-08",
    (
        "Owner authorized AE-SQ1 as a distinct successor after immutable "
        "predecessor terminal closeout; only terminal bits cross the boundary"
    ),
    "active successor program authority",
    "root conductor",
    "update",
    (
        "Freeze docs/exec-plans/active/ae-sq1.md and "
        "evals/ae-sq1/program-authority.json before candidate, heldout, or model "
        "work; preserve predecessor Git bytes"
    ),
    (
        "structural-program-authority-frozen only; no candidate, evaluation, "
        "runtime, host, field, release, publication, promotion, deletion, or "
        "migration claim"
    ),
    ("F1 independent external-evidence authority or any proposed F0 semantic change"),
    "2026-08-10",
    "340b79399a987e6aad0d5435fa540a1db511489d",
    (
        "Plan raw SHA256 "
        "a7080db226bf499dd3037afe683361e4ccba0c1093ce3bc4e456520e2176a382; "
        "predecessor tree c47aeb3642d7fdcf90f47f990ddf3915f3cbb933; base commit "
        "is historical custody, not a future AE-SQ1 commit; AE-SQ1 is not AQ10, "
        "H6, retry, resume, reopen, cure, or reinterpretation; all stage work "
        "remains HOLD"
    ),
)
VALIDATED_SUCCESSOR_DECISION_ROWS = (SUCCESSOR_F0_DECISION_ROW,)

FORBIDDEN_ACTIONS = (
    "release",
    "promote",
    "publish",
    "install",
    "monitor",
    "model_execution",
    "field_execution",
    "deletion",
    "migration_execution",
    "retry",
    "reopen",
    "resume",
    "h6_execution",
    "activation_execution",
    "corpus_execution",
    "later_authorization",
)
FORBIDDEN_EDGES = (
    ("AR", "AQ"),
    ("AR", "H5"),
    ("AR", "H6"),
    ("AR", "AS"),
    ("AR", "AC"),
    ("AR", "AH"),
    ("AR", "AF"),
)


def parse_csv_rows(raw: str) -> tuple[tuple[str, ...], ...]:
    if not raw.endswith("\n"):
        raise AssertionError("decision log must end with a newline")
    rows = tuple(tuple(row) for row in csv.reader(io.StringIO(raw), strict=True))
    if not rows:
        raise AssertionError("decision log is empty")
    if rows[0] != DECISION_LOG_HEADER:
        raise AssertionError("decision log header differs")
    if any(len(row) != len(DECISION_LOG_HEADER) for row in rows):
        raise AssertionError("decision log row is not exactly 13 columns")
    decision_ids = tuple(row[0] for row in rows[1:])
    if len(decision_ids) != len(set(decision_ids)):
        raise AssertionError("decision IDs are not unique")
    return rows


def canonical_csv_row(row: tuple[str, ...]) -> bytes:
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n").writerow(row)
    return buffer.getvalue().encode("utf-8")


def canonical_successor_csv_row(row: tuple[str, ...]) -> bytes:
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n", quoting=csv.QUOTE_ALL).writerow(row)
    return buffer.getvalue().encode("utf-8")


def strict_csv_rows(
    raw: str,
    historical_raw: str,
    foundation_raw: str,
    successor_authority_raw: bytes,
) -> tuple[tuple[str, ...], ...]:
    rows = parse_csv_rows(raw)
    historical_rows = parse_csv_rows(historical_raw)
    matching = tuple(row for row in rows[1:] if row[0] == TERMINAL_DECISION_ROW[0])
    if matching != (TERMINAL_DECISION_ROW,):
        raise AssertionError("terminal decision row is missing, duplicated, or changed")

    terminal_index = len(historical_rows)
    if rows[:terminal_index] != historical_rows:
        raise AssertionError("historical decision-log rows differ")
    if len(rows) <= terminal_index or rows[terminal_index] != TERMINAL_DECISION_ROW:
        raise AssertionError("terminal decision row moved from its historical index")

    validated_successors = validate_successor_authority(
        foundation_raw,
        successor_authority_raw,
    )
    if rows[terminal_index + 1 :] != validated_successors:
        raise AssertionError("post-terminal row is not a validated successor decision")

    expected = project_terminal_decision_log(historical_raw.encode("utf-8"))
    expected += b"".join(
        canonical_successor_csv_row(row) for row in validated_successors
    )
    if raw.encode("utf-8") != expected:
        raise AssertionError("decision log is not the exact canonical projection")
    return rows


def replace_bytes_once(source: bytes, old: bytes, new: bytes, label: str) -> bytes:
    if source.count(old) != 1:
        raise AssertionError(f"historical {label} does not occur exactly once")
    return source.replace(old, new, 1)


def project_terminal_plan(base: bytes) -> bytes:
    projected = replace_bytes_once(
        base,
        BASE_AR_CHECKBOX.encode("utf-8"),
        TERMINAL_AR_CHECKBOX.encode("utf-8"),
        "AR checkbox",
    )
    anchor = PLAN_INSERTION_ANCHOR.encode("utf-8")
    insertion = anchor + TERMINAL_BLOCK.encode("utf-8") + b"\n\n"
    return replace_bytes_once(projected, anchor, insertion, "AR record anchor")


def project_terminal_decision_log(base: bytes) -> bytes:
    if not base.endswith(b"\n"):
        raise AssertionError("historical decision log lacks its final newline")
    if TERMINAL_DECISION_ROW[0].encode("utf-8") in base:
        raise AssertionError("historical decision log already has the terminal row")
    return base + canonical_csv_row(TERMINAL_DECISION_ROW)


def validate_plan(raw: str) -> None:
    if raw.count("AR-TERMINAL-RECORD:") != 1:
        raise AssertionError("plan must contain one terminal record marker")
    record_open = "```text\nAR-TERMINAL-RECORD:\n"
    if raw.count(record_open) != 1:
        raise AssertionError("plan must contain one fenced terminal record")
    record_start = raw.index(record_open)
    record_end = raw.find("\n```", record_start)
    if record_end < 0:
        raise AssertionError("terminal record fence is not closed")
    fenced_record = raw[record_start : record_end + len("\n```")]
    if fenced_record != TERMINAL_BLOCK:
        raise AssertionError("complete fenced terminal record differs")

    progress = raw.split("## 5. Progress\n", maxsplit=1)[1].split("\n---", maxsplit=1)[
        0
    ]
    checkbox_lines = tuple(
        line for line in progress.splitlines() if line.startswith("- [")
    )
    if checkbox_lines != PROGRESS_LINES:
        raise AssertionError("progress checkbox text, order, or state differs")
    checked = tuple(line for line in checkbox_lines if line.startswith("- [x]"))
    unchecked = tuple(line for line in checkbox_lines if line.startswith("- [ ]"))
    if len(checked) != 3 or len(unchecked) != 5:
        raise AssertionError("progress checkbox counts differ")
    if tuple(line[6:].split(maxsplit=1)[0] for line in checked) != (
        "A0",
        "A1",
        "AR",
    ):
        raise AssertionError("only A0, A1, and terminal AR may be checked")
    if tuple(line[6:].split(maxsplit=1)[0] for line in unchecked) != (
        "AQ",
        "AS",
        "AC",
        "AH",
        "AF",
    ):
        raise AssertionError("AQ/AS/AC/AH/AF must remain unchecked")

    completion_start = raw.index("## AR completion")
    owner_decisions_start = raw.index("## Owner decisions with no safe default")
    marker_start = raw.index("AR-TERMINAL-RECORD:")
    if not completion_start < marker_start < owner_decisions_start:
        raise AssertionError("terminal record is not scoped to AR completion")


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def parse_ar_artifact(raw: bytes) -> dict[str, object]:
    document = json.loads(
        raw,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_nonfinite,
    )
    if not isinstance(document, dict):
        raise AssertionError("AR artifact must be an object")
    return document


def validate_successor_authority(
    foundation_raw: str,
    successor_authority_raw: bytes,
) -> tuple[tuple[str, ...], ...]:
    if foundation_raw.count(CURRENT_FOUNDATION_SUCCESSOR_POINTER) != 1:
        raise AssertionError("current foundation lacks the exact successor pointer")

    authority = parse_ar_artifact(successor_authority_raw)
    if authority.get("schema_version") != "AE-SQ1-program-authority-v1":
        raise AssertionError("successor authority schema differs")
    if authority.get("program_id") != "AE-SQ1":
        raise AssertionError("successor program identity differs")
    if authority.get("authority_status") != "F0_STATIC_AUTHORITY_FROZEN":
        raise AssertionError("successor F0 authority is not closed")
    if authority.get("claim_ceiling") != "structural-program-authority-frozen-only":
        raise AssertionError("successor F0 claim ceiling differs")

    owner = authority.get("owner_authorization")
    if not isinstance(owner, dict):
        raise AssertionError("successor owner authorization is absent")
    if owner.get("authorized") is not True:
        raise AssertionError("successor owner authorization is not affirmative")
    if owner.get("successor_kind") != "distinct-owner-authorized-successor-program":
        raise AssertionError("successor is not explicitly distinct")
    if tuple(owner.get("not_semantics", ())) != (
        "AQ10",
        "H6",
        "retry",
        "resume",
        "reopen",
        "cure",
        "reinterpretation",
    ):
        raise AssertionError("successor anti-reopen semantics differ")
    for key in (
        "candidate_authority_authorized",
        "heldout_authoring_authorized",
        "model_work_authorized",
        "model_or_corpus_observation_authorized",
        "downstream_staging_or_commit_authorized",
        "external_action_authorized",
    ):
        if owner.get(key) is not False:
            raise AssertionError(f"successor F0 unexpectedly authorizes {key}")

    predecessor = authority.get("predecessor_terminal_history")
    if not isinstance(predecessor, dict):
        raise AssertionError("predecessor terminal binding is absent")
    if predecessor.get("commit") != SUCCESSOR_F0_DECISION_ROW[11]:
        raise AssertionError("successor row and predecessor commit binding differ")
    if predecessor.get("tree") != "c47aeb3642d7fdcf90f47f990ddf3915f3cbb933":
        raise AssertionError("successor predecessor tree binding differs")
    if predecessor.get("custody_purpose") != "immutable-history-verification-only":
        raise AssertionError("successor authority can mutate predecessor custody")
    if tuple(predecessor.get("permitted_imported_bits", ())) != (
        "terminal-and-stopped",
        "successful-program-conditions-unmet",
        "public-release-and-promotion-negative",
        "artifacts-remain-immutable-history",
    ):
        raise AssertionError("successor imports more than terminal predecessor bits")

    active_plan = authority.get("active_plan")
    if not isinstance(active_plan, dict):
        raise AssertionError("successor active-plan binding is absent")
    if active_plan.get("path") != "docs/exec-plans/active/ae-sq1.md":
        raise AssertionError("successor active-plan path differs")
    if (
        active_plan.get("raw_sha256")
        != "a7080db226bf499dd3037afe683361e4ccba0c1093ce3bc4e456520e2176a382"
    ):
        raise AssertionError("successor active-plan digest differs")
    if active_plan.get("successor_commit") != "ABSENT_NOT_SELF_BOUND":
        raise AssertionError("successor F0 authority is unexpectedly self-bound")

    return VALIDATED_SUCCESSOR_DECISION_ROWS


def validate_ar_contract(document: dict[str, object]) -> None:
    if document.get("decision") != "DO_NOT_RELEASE_OR_PROMOTE":
        raise AssertionError("AR decision differs")
    if document.get("terminal_state") != "STOP":
        raise AssertionError("AR terminal state differs")
    if document.get("claim_ceiling") != "structural-terminal-closeout-only":
        raise AssertionError("AR claim ceiling differs")
    if tuple(document.get("forbidden_actions", ())) != FORBIDDEN_ACTIONS:
        raise AssertionError("AR forbidden actions differ")

    edges = tuple(
        (edge["from"], edge["to"]) for edge in document.get("forbidden_stage_edges", ())
    )
    if edges != FORBIDDEN_EDGES:
        raise AssertionError("AR forbidden stage edges differ")

    retention = document.get("retention_no_delete")
    if not isinstance(retention, list) or not retention:
        raise AssertionError("AR retention contract is absent")
    if any(
        row.get("disposition") != "retain_in_place"
        or row.get("deletion_authorized") is not False
        or row.get("migration_executed") is not False
        for row in retention
    ):
        raise AssertionError("AR permits deletion or records migration")

    unmet = document.get("unmet_success_conditions")
    if not isinstance(unmet, list) or len(unmet) != 6:
        raise AssertionError("AR unmet-success contract differs")
    if any(not str(row.get("status", "")).startswith("unmet_") for row in unmet):
        raise AssertionError("AR inflates an unmet success condition")


class ARTerminalIntegrationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan_bytes = PLAN.read_bytes()
        cls.plan = cls.plan_bytes.decode("utf-8")
        cls.decision_log_bytes = DECISION_LOG.read_bytes()
        cls.decision_log = cls.decision_log_bytes.decode("utf-8")
        cls.current_foundation = CURRENT_FOUNDATION.read_text(encoding="utf-8")
        cls.successor_authority_bytes = SUCCESSOR_AUTHORITY.read_bytes()

    def git_text(self, *arguments: str) -> str:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    def historical_bytes(self, path: str) -> bytes:
        if path not in HISTORICAL_PATHS:
            raise AssertionError(
                "historical byte access is restricted to approved files"
            )
        completed = subprocess.run(
            ["git", "show", f"{AR_COMMIT}:{path}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        return completed.stdout

    def test_plan_has_one_exact_terminal_record_and_closed_progress(self) -> None:
        validate_plan(self.plan)

    def test_plan_is_exact_historical_projection(self) -> None:
        base = self.historical_bytes(PLAN_PATH)
        self.assertEqual(1, base.count(BASE_AR_CHECKBOX.encode("utf-8")))
        self.assertNotIn(b"AR-TERMINAL-RECORD:", base)
        self.assertEqual(project_terminal_plan(base), self.plan_bytes)

    def test_decision_log_is_strict_unique_13_column_and_exact(self) -> None:
        historical = self.historical_bytes(DECISION_LOG_PATH).decode("utf-8")
        rows = strict_csv_rows(
            self.decision_log,
            historical,
            self.current_foundation,
            self.successor_authority_bytes,
        )
        self.assertEqual(13, len(rows[0]))
        self.assertEqual(
            1,
            sum(row[0] == TERMINAL_DECISION_ROW[0] for row in rows[1:]),
        )

    def test_decision_log_is_exact_canonical_historical_append(self) -> None:
        base = self.historical_bytes(DECISION_LOG_PATH)
        base_rows = parse_csv_rows(base.decode("utf-8"))
        live_rows = strict_csv_rows(
            self.decision_log,
            base.decode("utf-8"),
            self.current_foundation,
            self.successor_authority_bytes,
        )
        expected = project_terminal_decision_log(base) + canonical_successor_csv_row(
            SUCCESSOR_F0_DECISION_ROW
        )
        self.assertEqual(expected, self.decision_log_bytes)
        terminal_index = len(base_rows)
        self.assertEqual(base_rows, live_rows[:terminal_index])
        self.assertEqual(TERMINAL_DECISION_ROW, live_rows[terminal_index])
        self.assertEqual(
            VALIDATED_SUCCESSOR_DECISION_ROWS,
            live_rows[terminal_index + 1 :],
        )
        self.assertEqual(
            canonical_csv_row(TERMINAL_DECISION_ROW),
            self.decision_log_bytes[
                len(base) : len(base) + len(canonical_csv_row(TERMINAL_DECISION_ROW))
            ],
        )

    def test_ar_pair_has_exact_historical_git_custody(self) -> None:
        self.assertEqual(AR_TREE, self.git_text("rev-parse", f"{AR_COMMIT}^{{tree}}"))
        for path, expected_blob, expected_sha256 in AR_FILES:
            with self.subTest(path=path):
                entry = self.git_text("ls-tree", AR_COMMIT, "--", path)
                mode, object_type, blob, resolved_path = entry.split(maxsplit=3)
                self.assertEqual("100644", mode)
                self.assertEqual("blob", object_type)
                self.assertEqual(expected_blob, blob)
                self.assertEqual(path, resolved_path)
                self.assertEqual("blob", self.git_text("cat-file", "-t", blob))
                raw = self.historical_bytes(path)
                self.assertEqual(
                    int(self.git_text("cat-file", "-s", blob)),
                    len(raw),
                )
                self.assertEqual(expected_sha256, hashlib.sha256(raw).hexdigest())

        with self.assertRaisesRegex(AssertionError, "restricted to approved files"):
            self.historical_bytes("evals/foundation-v4/non-ar-artifact.json")

    def test_plan_log_and_artifact_share_the_closed_stop_ceiling(self) -> None:
        artifact = parse_ar_artifact(self.historical_bytes(AR_FILES[0][0]))
        validate_ar_contract(artifact)
        self.assertIn(f"decision={artifact['decision']}", TERMINAL_RECORD_LINES)
        self.assertIn(
            f"claim_ceiling={artifact['claim_ceiling']}", TERMINAL_RECORD_LINES
        )
        self.assertIn(
            f"terminal_state={artifact['terminal_state']}", TERMINAL_RECORD_LINES
        )
        self.assertEqual(artifact["decision"], TERMINAL_DECISION_ROW[7].split()[1])
        self.assertEqual(artifact["claim_ceiling"], TERMINAL_DECISION_ROW[8])
        self.assertIn(artifact["terminal_state"], TERMINAL_DECISION_ROW[9])
        for action in (
            "release",
            "reopen",
            "publish",
            "model_execution",
            "field_execution",
            "deletion",
        ):
            self.assertIn(action, artifact["forbidden_actions"])

    def test_plan_csv_and_artifact_mutations_fail_closed(self) -> None:
        plan_mutations = (
            self.plan.replace(
                PROGRESS_LINES[-1], PROGRESS_LINES[-1].replace("[x]", "[ ]")
            ),
            self.plan.replace(
                PROGRESS_LINES[3], PROGRESS_LINES[3].replace("[ ]", "[x]")
            ),
            self.plan.replace("decision=DO_NOT_RELEASE_OR_PROMOTE", "decision=RELEASE"),
            self.plan.replace("terminal_state=STOP", "terminal_state=RESUME"),
            self.plan.replace(
                "terminal_state=STOP\n```",
                "terminal_state=STOP\nrelease=authorized\n```",
            ),
            self.plan.replace(
                "superseded_for_this_terminal_program_no_later_authorization_cure",
                "active_later_authorization_cure",
            ),
            self.plan + "\n" + TERMINAL_RECORD + "\n",
        )
        for index, mutation in enumerate(plan_mutations):
            with (
                self.subTest(kind="plan", index=index),
                self.assertRaises(AssertionError),
            ):
                validate_plan(mutation)

        historical = self.historical_bytes(DECISION_LOG_PATH).decode("utf-8")
        successor_row_bytes = canonical_successor_csv_row(SUCCESSOR_F0_DECISION_ROW)
        csv_mutations = (
            self.decision_log + self.decision_log.splitlines()[-1] + "\n",
            self.decision_log.replace(
                "structural-terminal-closeout-only",
                "behavioral-release-authorized",
                1,
            ),
            self.decision_log.replace(
                "none; terminal STOP; do not reopen",
                "release and reopen",
                1,
            ),
            self.decision_log.replace(
                TERMINAL_DECISION_ROW[-1],
                "custody removed",
                1,
            ),
            self.decision_log + "too,few,columns\n",
            self.decision_log.replace(
                successor_row_bytes.decode("utf-8"),
                canonical_successor_csv_row(
                    (
                        *SUCCESSOR_F0_DECISION_ROW[:3],
                        "Owner authorized AQ10 to reopen the predecessor program",
                        *SUCCESSOR_F0_DECISION_ROW[4:],
                    )
                ).decode("utf-8"),
                1,
            ),
            self.decision_log.replace(
                successor_row_bytes.decode("utf-8"),
                canonical_successor_csv_row(
                    (
                        "AE-SQ1-H6-2026-08-10",
                        *SUCCESSOR_F0_DECISION_ROW[1:4],
                        "predecessor AQ9/H5 continuation",
                        *SUCCESSOR_F0_DECISION_ROW[5:],
                    )
                ).decode("utf-8"),
                1,
            ),
            self.decision_log
            + canonical_csv_row(
                (
                    "AE-SQ1-F1-2026-08-10",
                    "RLTree/agentic-engineering",
                    "current-2026-08-08",
                    "arbitrary successor-looking append",
                    "active successor program authority",
                    "root conductor",
                    "update",
                    "unvalidated delta",
                    "structural-only",
                    "none",
                    "2026-08-10",
                    "340b79399a987e6aad0d5435fa540a1db511489d",
                    "unvalidated",
                )
            ).decode("utf-8"),
        )
        for index, mutation in enumerate(csv_mutations):
            with (
                self.subTest(kind="csv", index=index),
                self.assertRaises(AssertionError),
            ):
                strict_csv_rows(
                    mutation,
                    historical,
                    self.current_foundation,
                    self.successor_authority_bytes,
                )

        artifact = parse_ar_artifact(self.historical_bytes(AR_FILES[0][0]))
        artifact_mutations = []
        for key, value in (
            ("decision", "RELEASE"),
            ("terminal_state", "RESUME"),
            ("claim_ceiling", "behavioral"),
        ):
            changed = copy.deepcopy(artifact)
            changed[key] = value
            artifact_mutations.append(changed)
        changed = copy.deepcopy(artifact)
        changed["forbidden_actions"].remove("publish")
        artifact_mutations.append(changed)
        changed = copy.deepcopy(artifact)
        changed["retention_no_delete"][0]["deletion_authorized"] = True
        artifact_mutations.append(changed)
        changed = copy.deepcopy(artifact)
        changed["forbidden_stage_edges"].pop()
        artifact_mutations.append(changed)

        for index, mutation in enumerate(artifact_mutations):
            with (
                self.subTest(kind="artifact", index=index),
                self.assertRaises(AssertionError),
            ):
                validate_ar_contract(mutation)


if __name__ == "__main__":
    unittest.main()
