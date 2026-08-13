from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/diagnose_ae_sq2_handshake.py"
SPEC = importlib.util.spec_from_file_location("ae_sq2_diagnostic_test", PATH)
diagnostic = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = diagnostic
SPEC.loader.exec_module(diagnostic)


def raw(
    stdout: bytes = b"",
    *,
    stderr: bytes = b"",
    returncode: int | None = 0,
    timeout: bool = False,
    spawn: bool = False,
    overflow: bool = False,
) -> diagnostic.RawProcessResult:
    return diagnostic.RawProcessResult(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        stdout_bytes=len(stdout),
        stderr_bytes=len(stderr),
        stdout_sha256=diagnostic.sha256_bytes(stdout),
        stderr_sha256=diagnostic.sha256_bytes(stderr),
        timed_out=timeout,
        spawn_failed=spawn,
        overflowed=overflow,
    )


def jsonl(*rows: object) -> bytes:
    return b"\n".join(json.dumps(row, separators=(",", ":")).encode() for row in rows)


def valid_capsule(probe: diagnostic.Probe) -> dict[str, object]:
    phrase = f"reversible quartz marker {probe.probe_id}"
    text = probe.request.decode()
    start = text.index(phrase)
    return {
        "slot_id": probe.slot_id,
        "local_need": "yes",
        "reference_need": "none",
        "anchors": [{"start": start, "end": start + len(phrase), "text": phrase}],
    }


def stream(
    probe: diagnostic.Probe,
    capsule: object | None = None,
    *,
    usage: dict[str, int] | None = None,
) -> bytes:
    rows: list[object] = [
        {"type": "thread.started", "thread_id": "must-not-persist"},
        {"type": "turn.started"},
    ]
    if capsule is not None:
        rows.append(
            {
                "type": "item.completed",
                "item": {
                    "id": "message-id",
                    "type": "agent_message",
                    "text": json.dumps(capsule, separators=(",", ":")),
                },
            }
        )
    terminal: dict[str, object] = {"type": "turn.completed"}
    if usage is not None:
        terminal["usage"] = usage
    rows.append(terminal)
    return jsonl(*rows)


class DiagnosticHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads((ROOT / diagnostic.SQ1_SCHEMA_PATH).read_text())
        cls.probe = diagnostic.probes()[0]

    def classify(self, value: diagnostic.RawProcessResult) -> dict[str, object]:
        return diagnostic.classify_result(self.probe, value, self.schema)

    def test_fixed_probes_are_exact_and_nonadaptive(self) -> None:
        fixed = diagnostic.probes()
        self.assertEqual(tuple(probe.probe_id for probe in fixed), diagnostic.PROBE_IDS)
        self.assertEqual(tuple(probe.slot_id for probe in fixed), diagnostic.SLOT_IDS)
        self.assertEqual(
            tuple(diagnostic.sha256_bytes(probe.request) for probe in fixed),
            (
                "91594ddbbbc902142b421b380282ffbeb704f14ab83d7af56d9d066941811693",
                "287e8e57dd05941886a2f51c1d0ebc3d02bdcd70dab33f986a851a68e8b9ae6a",
                "1afc2297e3c6d34f7a1835bdfa782cd965e1d27ff2bba10e08cdad125d7ee910",
                "ee653e53197a617cc1f8961b3c69dd8803b9b17260720564ebddfb31802af559",
            ),
        )
        combined = b"\n".join(probe.request for probe in fixed).lower()
        for forbidden in (b"corpus", b"holdout", b"ae-sq1-aq-fresh", b"result"):
            self.assertNotIn(forbidden, combined)

    def test_diagnostic_authority_binds_current_parent_program_bytes(self) -> None:
        authority = json.loads(diagnostic.AUTHORITY_PATH.read_text())
        raw = diagnostic.PROGRAM_AUTHORITY_PATH.read_bytes()
        self.assertEqual(
            authority["parent_program_authority"],
            {
                "path": "evals/ae-sq2/program-authority.json",
                "sha256": diagnostic.sha256_bytes(raw),
            },
        )

    def test_cli_requires_explicit_schema_digest_and_exact_live_approval(self) -> None:
        with self.assertRaises(SystemExit):
            diagnostic.parse_args(["--dry-run", "--schema", diagnostic.SQ1_SCHEMA_PATH])
        with self.assertRaises(SystemExit):
            diagnostic.parse_args(
                [
                    "--execute",
                    "--schema",
                    diagnostic.SQ1_SCHEMA_PATH,
                    "--schema-sha256",
                    diagnostic.SQ1_SCHEMA_SHA256,
                    "--usage-approval",
                    "wrong",
                ]
            )
        with self.assertRaises(SystemExit):
            diagnostic.parse_args(
                [
                    "--dry-run",
                    "--schema",
                    diagnostic.SQ1_SCHEMA_PATH,
                    "--schema-sha256",
                    diagnostic.SQ1_SCHEMA_SHA256,
                    "--usage-approval",
                    diagnostic.APPROVAL,
                ]
            )

    def test_input_schema_reproduces_exact_sq1_bytes_and_accepts_later_explicit_schema(
        self,
    ) -> None:
        path, info, schema = diagnostic.resolve_schema(
            diagnostic.SQ1_SCHEMA_PATH, diagnostic.SQ1_SCHEMA_SHA256
        )
        self.assertEqual(path, (ROOT / diagnostic.SQ1_SCHEMA_PATH).resolve())
        self.assertEqual(info["sha256"], diagnostic.SQ1_SCHEMA_SHA256)
        self.assertEqual(
            schema["title"], "AE-SQ1 SLEC-1 closed slot-local runtime capsule"
        )
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic.resolve_schema(diagnostic.SQ1_SCHEMA_PATH, "0" * 64)
        with tempfile.NamedTemporaryFile(dir=ROOT, suffix=".json") as temp:
            temp.write(b'{"type":"object"}')
            temp.flush()
            digest = diagnostic.sha256_bytes(Path(temp.name).read_bytes())
            resolved, later_info, _ = diagnostic.resolve_schema(temp.name, digest)
            self.assertEqual(resolved, Path(temp.name).resolve())
            self.assertEqual(later_info["sha256"], digest)

    def test_child_argv_pins_isolation_schema_model_reasoning_and_no_fallback(
        self,
    ) -> None:
        cli = {
            "path": "/exact/codex",
            "version": diagnostic.CLI_VERSION,
            "sha256": diagnostic.CLI_SHA256,
        }
        argv = diagnostic.child_argv(cli, Path("/exact/schema"))
        self.assertEqual(
            argv[:4], ["/exact/codex", "--ask-for-approval", "never", "exec"]
        )
        self.assertEqual(argv[argv.index("--model") + 1], "gpt-5.5")
        self.assertEqual(argv[argv.index("--output-schema") + 1], "/exact/schema")
        self.assertIn('model_reasoning_effort="medium"', argv)
        self.assertIn("--ephemeral", argv)
        self.assertIn("--ignore-user-config", argv)
        self.assertIn("--ignore-rules", argv)
        self.assertIn("--strict-config", argv)
        self.assertEqual(argv[-1], "-")
        self.assertNotIn("fallback", " ".join(argv).lower())

    def test_dry_run_makes_exactly_zero_invocations(self) -> None:
        _, info, schema = diagnostic.resolve_schema(
            diagnostic.SQ1_SCHEMA_PATH, diagnostic.SQ1_SCHEMA_SHA256
        )
        cli = {
            "path": "/exact/codex",
            "version": diagnostic.CLI_VERSION,
            "sha256": diagnostic.CLI_SHA256,
        }
        calls: list[object] = []

        def forbidden(*args: object, **kwargs: object) -> diagnostic.RawProcessResult:
            calls.append((args, kwargs))
            raise AssertionError("dry run invoked model")

        record = diagnostic.run_diagnostic(
            mode="dry_run",
            schema_path=ROOT / diagnostic.SQ1_SCHEMA_PATH,
            schema_document=schema,
            schema_info=info,
            cli=cli,
            invoke=forbidden,
        )
        self.assertEqual(calls, [])
        self.assertEqual(record["calls_started"], 0)
        self.assertEqual(record["calls"], [])
        self.assertEqual(record["status"], "ready")
        self.assertEqual(
            tuple(record["classification_counts"]), diagnostic.CLASSIFICATIONS
        )

    def test_direct_live_entrypoint_also_requires_exact_approval(self) -> None:
        _, info, schema = diagnostic.resolve_schema(
            diagnostic.SQ1_SCHEMA_PATH, diagnostic.SQ1_SCHEMA_SHA256
        )
        cli = {
            "path": "/exact/codex",
            "version": diagnostic.CLI_VERSION,
            "sha256": diagnostic.CLI_SHA256,
        }
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic.run_diagnostic(
                mode="live",
                schema_path=ROOT / diagnostic.SQ1_SCHEMA_PATH,
                schema_document=schema,
                schema_info=info,
                cli=cli,
            )

    def test_transport_timeout_signal_process_empty_and_overflow_classes(self) -> None:
        cases = (
            (raw(returncode=None, spawn=True), "transport_spawn"),
            (raw(timeout=True), "timeout"),
            (raw(b"x", returncode=-9), "signal_exit"),
            (raw(b"x", returncode=2), "process_exit"),
            (raw(), "empty_stdout"),
            (raw(b"x", overflow=True), "other_fail_closed"),
        )
        for value, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(self.classify(value)["classification"], expected)

    def test_invalid_jsonl_unknown_event_and_missing_message_classes(self) -> None:
        self.assertEqual(
            self.classify(raw(b"not-json"))["classification"], "invalid_jsonl"
        )
        unknown = jsonl(
            {"type": "thread.started", "thread_id": "secret"},
            {"type": "future.event", "payload": "secret"},
        )
        self.assertEqual(self.classify(raw(unknown))["classification"], "unknown_event")
        self.assertEqual(
            self.classify(raw(stream(self.probe, None)))["classification"],
            "missing_completed_message",
        )

    def test_provider_invalid_schema_and_other_request_rejections_take_precedence(
        self,
    ) -> None:
        unsupported = jsonl(
            {"type": "thread.started", "thread_id": "secret"},
            {
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "code": "invalid_json_schema",
                    "message": "raw provider detail must not persist",
                },
            },
        )
        for returncode in (0, 1):
            result = self.classify(raw(unsupported, returncode=returncode))
            self.assertEqual(result["classification"], "schema_unsupported")
            self.assertEqual(result["error_class"], "invalid_json_schema")
        for needle, expected_error in (
            ("invalid_request", "invalid_request"),
            ("authentication failed", "authentication"),
            ("401 Unauthorized", "authentication"),
            ("authorization forbidden", "authorization"),
            ("rate limit", "rate_limit"),
            ("429", "rate_limit"),
            ("network connection", "network"),
            ("internal server", "server"),
            ("provider refused", "other"),
        ):
            with self.subTest(needle=needle):
                failure = jsonl(
                    {"type": "thread.started", "thread_id": "secret"},
                    {"type": "turn.failed", "error": {"message": needle}},
                )
                result = self.classify(raw(failure, returncode=0))
                self.assertEqual(result["classification"], "provider_request_rejected")
                self.assertEqual(result["error_class"], expected_error)

    def test_arbitrary_stderr_never_impersonates_structured_provider_error(
        self,
    ) -> None:
        completed = stream(self.probe, valid_capsule(self.probe))
        for stderr in (
            b"invalid_json_schema internal server 429",
            b"401 Unauthorized invalid_request",
        ):
            with self.subTest(stderr=stderr):
                result = self.classify(raw(completed, stderr=stderr, returncode=0))
                self.assertEqual(result["classification"], "valid_completed")
                self.assertEqual(result["error_class"], "none")
        result = self.classify(
            raw(b"not-json", stderr=b"invalid_json_schema", returncode=2)
        )
        self.assertEqual(result["classification"], "process_exit")
        self.assertEqual(result["error_class"], "none")
        malformed_error = jsonl(
            {"type": "thread.started", "thread_id": "secret"},
            {
                "type": "error",
                "error": {
                    "code": "invalid_json_schema",
                    "message": "invalid_json_schema",
                    "unrecognized": "provider-shaped but not closed",
                },
            },
        )
        result = self.classify(raw(malformed_error, returncode=0))
        self.assertEqual(result["classification"], "missing_completed_message")
        self.assertEqual(result["error_class"], "none")

    def test_schema_semantic_and_valid_completed_classes(self) -> None:
        schema_invalid = valid_capsule(self.probe)
        schema_invalid["extra"] = True
        self.assertEqual(
            self.classify(raw(stream(self.probe, schema_invalid)))["classification"],
            "schema_invalid",
        )
        semantic_invalid = valid_capsule(self.probe)
        semantic_invalid["slot_id"] = "s1"
        self.assertEqual(
            self.classify(raw(stream(self.probe, semantic_invalid)))["classification"],
            "semantic_invalid",
        )
        usage = {"input_tokens": 11, "cached_input_tokens": 2, "output_tokens": 7}
        result = self.classify(
            raw(stream(self.probe, valid_capsule(self.probe), usage=usage))
        )
        self.assertEqual(result["classification"], "valid_completed")
        self.assertTrue(result["usage_observed"])
        self.assertEqual(result["usage"]["total_tokens"], 18)
        extra_usage = {**usage, "provider_detail": 1}
        result = self.classify(
            raw(stream(self.probe, valid_capsule(self.probe), usage=extra_usage))
        )
        self.assertFalse(result["usage_observed"])
        self.assertEqual(result["usage"], diagnostic._zero_usage())

    def test_live_path_invokes_each_fixed_probe_once_and_persists_no_raw(self) -> None:
        _, info, schema = diagnostic.resolve_schema(
            diagnostic.SQ1_SCHEMA_PATH, diagnostic.SQ1_SCHEMA_SHA256
        )
        cli = {
            "path": "/exact/codex",
            "version": diagnostic.CLI_VERSION,
            "sha256": diagnostic.CLI_SHA256,
        }
        seen: list[str] = []

        def invoke(
            probe: diagnostic.Probe, _cli: object, _schema: Path
        ) -> diagnostic.RawProcessResult:
            seen.append(probe.probe_id)
            return raw(
                stream(probe, valid_capsule(probe)),
                stderr=b"secret stderr that may only be hashed",
            )

        record = diagnostic.run_diagnostic(
            mode="live",
            usage_approval=diagnostic.APPROVAL,
            schema_path=ROOT / diagnostic.SQ1_SCHEMA_PATH,
            schema_document=schema,
            schema_info=info,
            cli=cli,
            invoke=invoke,
            custody_root=self._fresh_repo(),
        )
        self.assertCountEqual(seen, diagnostic.PROBE_IDS)
        self.assertEqual(len(seen), diagnostic.CALLS)
        self.assertEqual(record["calls_started"], 4)
        self.assertEqual(record["calls_completed"], 4)
        self.assertEqual(record["classification_counts"]["valid_completed"], 4)
        self.assertEqual(
            tuple(record["classification_counts"]), diagnostic.CLASSIFICATIONS
        )
        encoded = json.dumps(record).casefold()
        for forbidden in (
            "secret stderr",
            "must-not-persist",
            "reversible quartz marker",
            '"slot_id"',
            "message-id",
        ):
            self.assertNotIn(forbidden, encoded)
        record_schema = json.loads(diagnostic.RECORD_SCHEMA_PATH.read_text())
        Draft202012Validator(record_schema).validate(record)
        copy = dict(record)
        digest = copy.pop("record_sha256")
        self.assertEqual(
            digest, diagnostic.sha256_bytes(diagnostic.canonical_json(copy))
        )

    def test_calls_completed_means_process_returned_not_valid_output(self) -> None:
        _, info, schema = diagnostic.resolve_schema(
            diagnostic.SQ1_SCHEMA_PATH, diagnostic.SQ1_SCHEMA_SHA256
        )
        cli = {
            "path": "/exact/codex",
            "version": diagnostic.CLI_VERSION,
            "sha256": diagnostic.CLI_SHA256,
        }
        outcomes = {
            "p0": raw(returncode=None, spawn=True),
            "p1": raw(b"not-json", returncode=2),
            "p2": raw(b"not-json", returncode=-9),
            "p3": raw(b"", returncode=0),
        }

        def invoke(
            probe: diagnostic.Probe, _cli: object, _schema: Path
        ) -> diagnostic.RawProcessResult:
            return outcomes[probe.probe_id]

        record = diagnostic.run_diagnostic(
            mode="live",
            usage_approval=diagnostic.APPROVAL,
            schema_path=ROOT / diagnostic.SQ1_SCHEMA_PATH,
            schema_document=schema,
            schema_info=info,
            cli=cli,
            invoke=invoke,
            custody_root=self._fresh_repo(),
        )
        self.assertEqual(record["calls_started"], 4)
        self.assertEqual(record["calls_completed"], 3)

    def test_isolated_child_uses_0700_dirs_private_auth_and_cleans_up(self) -> None:
        with tempfile.TemporaryDirectory() as source_directory:
            auth = Path(source_directory) / "auth.json"
            auth.write_text('{"test":"credential"}', encoding="utf-8")
            os.chmod(auth, 0o600)
            captured: tuple[Path, Path] | None = None
            with mock.patch.dict(os.environ, {"CODEX_HOME": source_directory}):
                with diagnostic.isolated_child() as (cwd, environment):
                    home = Path(environment["CODEX_HOME"])
                    captured = (cwd, home)
                    self.assertEqual(os.stat(cwd).st_mode & 0o777, 0o700)
                    self.assertEqual(os.stat(home).st_mode & 0o777, 0o700)
                    self.assertEqual(os.stat(home / "auth.json").st_mode & 0o777, 0o600)
                    self.assertEqual(
                        {path.name for path in home.iterdir()}, {"auth.json", "tmp"}
                    )
                    private_tmp = Path(environment["TMPDIR"])
                    self.assertEqual(private_tmp, home / "tmp")
                    self.assertEqual(os.stat(private_tmp).st_mode & 0o777, 0o700)
                    self.assertEqual(list(private_tmp.iterdir()), [])
                    self.assertEqual(list(cwd.iterdir()), [])
                    self.assertEqual(environment["HOME"], str(home))
            assert captured is not None
            self.assertFalse(captured[0].exists())
            self.assertFalse(captured[1].exists())

    def _fresh_repo(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        repo = Path(temporary.name) / "repo"
        repo.mkdir()
        import subprocess

        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        return repo

    def _custody_fixture(
        self, repo: Path
    ) -> tuple[dict[str, str], dict[str, object], object]:
        _, info, schema = diagnostic.resolve_schema(
            diagnostic.SQ1_SCHEMA_PATH, diagnostic.SQ1_SCHEMA_SHA256
        )
        cli = {
            "path": "/exact/codex",
            "version": diagnostic.CLI_VERSION,
            "sha256": diagnostic.CLI_SHA256,
        }
        _, authority_raw, record_schema_raw = diagnostic._load_closed_authority()
        binding = diagnostic._custody_binding(
            authority_raw=authority_raw,
            record_schema_raw=record_schema_raw,
            input_schema_info=info,
            cli=cli,
        )
        return cli, info, schema, binding  # type: ignore[return-value]

    def test_second_live_execute_is_rejected_before_any_call(self) -> None:
        repo = self._fresh_repo()
        cli, info, schema, _ = self._custody_fixture(repo)
        seen: list[str] = []

        def invoke(
            probe: diagnostic.Probe, _cli: object, _schema: Path
        ) -> diagnostic.RawProcessResult:
            seen.append(probe.probe_id)
            return raw(stream(probe, valid_capsule(probe)))

        kwargs = dict(
            mode="live",
            usage_approval=diagnostic.APPROVAL,
            schema_path=ROOT / diagnostic.SQ1_SCHEMA_PATH,
            schema_document=schema,
            schema_info=info,
            cli=cli,
            invoke=invoke,
            custody_root=repo,
        )
        diagnostic.run_diagnostic(**kwargs)
        self.assertEqual(len(seen), 4)
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic.run_diagnostic(**kwargs)
        self.assertEqual(len(seen), 4)

    def test_crash_after_claim_blocks_reuse_without_any_call(self) -> None:
        repo = self._fresh_repo()
        cli, info, schema, _ = self._custody_fixture(repo)
        calls: list[str] = []

        def invoke(
            probe: diagnostic.Probe, _cli: object, _schema: Path
        ) -> diagnostic.RawProcessResult:
            calls.append(probe.probe_id)
            return raw()

        def crash(_claim: diagnostic.CustodyClaim) -> None:
            raise KeyboardInterrupt("synthetic crash")

        kwargs = dict(
            mode="live",
            usage_approval=diagnostic.APPROVAL,
            schema_path=ROOT / diagnostic.SQ1_SCHEMA_PATH,
            schema_document=schema,
            schema_info=info,
            cli=cli,
            invoke=invoke,
            custody_root=repo,
        )
        with self.assertRaises(KeyboardInterrupt):
            diagnostic.run_diagnostic(**kwargs, after_claim=crash)
        self.assertEqual(calls, [])
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic.run_diagnostic(**kwargs)
        self.assertEqual(calls, [])

    def test_concurrent_atomic_claim_has_exactly_one_winner(self) -> None:
        repo = self._fresh_repo()
        _, _, _, binding = self._custody_fixture(repo)
        barrier = threading.Barrier(2)
        outcomes: list[str] = []

        def contender() -> None:
            barrier.wait()
            try:
                diagnostic._claim_d0(repo, binding)
            except diagnostic.DiagnosticError:
                outcomes.append("rejected")
            else:
                outcomes.append("claimed")

        threads = [threading.Thread(target=contender) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertCountEqual(outcomes, ["claimed", "rejected"])

    def test_unsafe_or_noncanonical_existing_custody_fails_closed(self) -> None:
        mutations = ("symlink", "hardlink", "mode", "duplicate", "noncanonical")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                repo = self._fresh_repo()
                _, _, _, binding = self._custody_fixture(repo)
                claim = diagnostic._claim_d0(repo, binding)
                if mutation == "symlink":
                    target = claim.path.with_suffix(".target")
                    claim.path.rename(target)
                    claim.path.symlink_to(target.name)
                elif mutation == "hardlink":
                    os.link(claim.path, claim.path.with_suffix(".alias"))
                elif mutation == "mode":
                    os.chmod(claim.path, 0o644)
                elif mutation == "duplicate":
                    state = json.loads(claim.path.read_text())
                    raw_state = json.dumps(state, separators=(",", ":"))
                    claim.path.write_text(
                        raw_state.replace(
                            '"status":', '"status":"claimed","status":', 1
                        )
                    )
                    os.chmod(claim.path, 0o600)
                else:
                    claim.path.write_bytes(claim.path.read_bytes() + b"\n")
                with self.assertRaises(diagnostic.DiagnosticError):
                    diagnostic._claim_d0(repo, binding)

    def test_binding_change_cannot_create_a_second_d0_state(self) -> None:
        repo = self._fresh_repo()
        _, _, _, binding = self._custody_fixture(repo)
        diagnostic._claim_d0(repo, binding)
        changed = dict(binding)
        changed["input_schema_sha256"] = "f" * 64
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic._claim_d0(repo, changed)

    def test_unsafe_custody_directory_fails_closed(self) -> None:
        for mutation in ("symlink", "mode"):
            with self.subTest(mutation=mutation):
                repo = self._fresh_repo()
                _, _, _, binding = self._custody_fixture(repo)
                common = diagnostic._git_common_dir(repo)
                directory = common / diagnostic.CUSTODY_DIRECTORY
                if mutation == "symlink":
                    target = common / "custody-target"
                    target.mkdir(mode=0o700)
                    directory.symlink_to(target.name)
                else:
                    directory.mkdir(mode=0o700)
                    os.chmod(directory, 0o755)
                with self.assertRaises(diagnostic.DiagnosticError):
                    diagnostic._claim_d0(repo, binding)

    def test_unexpected_sibling_in_custody_directory_fails_closed(self) -> None:
        repo = self._fresh_repo()
        _, _, _, binding = self._custody_fixture(repo)
        directory = diagnostic._custody_directory(repo)
        sibling = directory / "unexpected"
        sibling.write_bytes(b"x")
        os.chmod(sibling, 0o600)
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic._claim_d0(repo, binding)

    def test_bounded_subprocess_caps_retention_and_reports_overflow(self) -> None:
        command = [
            sys.executable,
            "-c",
            "import sys;sys.stdin.buffer.read();sys.stdout.buffer.write(b'x'*2048)",
        ]
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            diagnostic, "MAX_STDOUT_BYTES", 1024
        ):
            result = diagnostic._run_bounded(
                command,
                b"input",
                cwd=Path(directory),
                env={"PATH": os.environ.get("PATH", "")},
                timeout_seconds=10,
            )
        self.assertTrue(result.overflowed)
        self.assertGreater(result.stdout_bytes, 1024)
        self.assertLessEqual(
            len(result.stdout),
            diagnostic.MAX_STDOUT_BYTES + diagnostic.READ_CHUNK_BYTES,
        )

    def test_spawn_oserror_is_closed_without_raw_exception_text(self) -> None:
        def broken(*args: object, **kwargs: object) -> object:
            raise OSError("super secret launch path")

        with tempfile.TemporaryDirectory() as directory:
            result = diagnostic._run_bounded(
                ["/missing"],
                b"request",
                cwd=Path(directory),
                env={},
                popen=broken,
            )
        self.assertTrue(result.spawn_failed)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(result.stderr, b"")

    def test_resolve_cli_requires_exact_binary_bytes(self) -> None:
        with tempfile.NamedTemporaryFile() as temp:
            temp.write(b"wrong")
            temp.flush()
            with self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.resolve_cli(temp.name)


if __name__ == "__main__":
    unittest.main()
