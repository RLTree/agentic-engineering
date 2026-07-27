# Rust verification ladder for agentic systems

Run the cheapest discriminating checks early and the broadest exact-delivery checks before release. Adapt commands to the repository’s supported features and targets.

## Ladder

1. **Format:** `cargo fmt --all -- --check`.
2. **Type/borrow checking:** `cargo check --workspace --all-targets` plus supported feature/target combinations. `cargo check` is faster than full code generation but does not detect every codegen/link issue.
3. **Unit/doc/integration tests:** `cargo test --workspace` with relevant features; include doctests when part of the API contract.
4. **Lint:** `cargo clippy --workspace --all-targets --all-features -- -D warnings` or project-specific lint policy.
5. **Release build/package:** clean `cargo build --release` / `cargo package` and inspect the exact binary/crate/container.
6. **Scenario/e2e:** deterministic fake model/tools, then authorized live smoke tests for supported providers/protocols.
7. **Concurrency:** cancellation/saturation/fault tests; Loom for small synchronization primitives where valuable.
8. **Unsafe/UB:** Miri on compatible tests; sanitizer/platform-specific tools where configured.
9. **Supply chain:** locked dependencies, advisories, licenses, provenance, secrets and generated-code review.
10. **Operational:** startup/readiness, graceful shutdown, crash/replay, migrations, telemetry/redaction and resource limits.

## Matrix

Cover supported Rust version/MSRV, OS/architecture, feature combinations, storage/provider adapters and protocol versions. Use a documented reduced PR matrix and full release/nightly matrix.

## Agent-specific assertions

No success without evidence; no external effect without authorized journal record; no duplicate action on replay; cancellation drains tasks; queues bounded; trace IDs propagate; sensitive data redacted; model/tool adapters pass contract tests.

## Evidence

Record command, environment/toolchain, feature/target, exact commit/artifact digest, exit code, summarized output and skipped checks. “Builds on my machine” is not release evidence.
