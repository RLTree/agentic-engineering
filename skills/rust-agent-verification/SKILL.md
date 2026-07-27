---
name: rust-agent-verification
description: Use when an agentic Rust system needs layered, concurrency, fault, protocol,
  supply-chain, or outcome verification.
---

# Rust Agent Verification

## Core principle

Verify from pure invariants outward to exact external behavior. Rust compilation and unit tests are necessary but do not prove concurrency, replay, protocol, model trajectory or side-effect correctness.

## Workflow

### 1. Map risks to evidence

List domain invariants, state transitions, tool schemas, async lifecycles, side effects, durability, protocols, security, performance and model behavior. Assign the cheapest discriminating test to each.

### 2. Establish the Cargo baseline

Run formatting, `cargo check`, Clippy with the repository's warning policy, unit/integration/doc tests and relevant feature/target matrices. Keep commands reproducible in AGENTS.md and CI.

### 3. Test pure state and policy

Use table and property tests for transitions, budgets, reducers, idempotency-key derivation, approval classification, serialization compatibility and impossible-state rejection. Read [the Rust verification ladder](references/rust-verification-ladder.md).

### 4. Test concurrency and cancellation

Use deterministic tests, paused time, controlled fakes and concurrency exploration such as Loom where appropriate. Exercise queue saturation, cancellation at awaits, shutdown, panic and lock/order assumptions. Use [concurrency and fault testing](references/concurrency-fault-testing.md).

### 5. Test durability and effects

Inject crashes before/after journal/outbox/effect/receipt commits; duplicate and reorder delivery; expire leases; return unknown outcomes; assert one business effect and a recoverable final state.

### 6. Test protocols and providers

Use schema round trips, golden messages, conformance/TCK suites, malformed inputs, rate limits, timeouts and provider contract fakes. Keep a small opt-in live-provider suite with cost/data controls.

### 7. Evaluate agent trajectories

Create fixed tasks and environments; record state transitions, tool calls, effects, verification and stop reason. Score outcome, efficiency, recovery, safety and determinism. Use [agent evals in Rust](references/agent-evals-rust.md).

### 8. Secure the supply chain

Audit vulnerabilities and advisories, dependency policy, licenses, unmaintained crates, features, unsafe code, secret handling and reproducible lockfiles. Use Miri or sanitizers where the unsafe/concurrency risk warrants it.

### 9. Gate the exact artifact

Run packaged binary/container/service with real configuration, migrations, graceful shutdown and observability. Preserve command results and trace/effect evidence.

## Output contract

Return a **Rust Verification and CI Matrix** with:

- risk/invariant inventory;
- Cargo and feature/target gates;
- unit/property/state-machine tests;
- async/concurrency/cancellation tests;
- durability/fault-injection cases;
- protocol/provider contract tests;
- agent outcome/trajectory evals;
- security/supply-chain checks;
- exact-artifact evidence and release thresholds.

## Common failures

- **Cargo check as complete proof:** runtime/state/effect semantics are untested. Build the ladder.
- **Only happy-path async tests:** cancellation and saturation fail in production. Inject them.
- **Skipped tools marked passed:** mocks accept behavior real protocols reject. Add golden/conformance/live smoke tests.
- **No feature matrix:** optional combinations rot. Declare supported combinations and test them.
- **Flaky sleeps:** timing-based tests hide races. Use controlled time/events and deterministic exploration.
- **Agent eval absent:** code works but tool trajectories loop or violate policy. Score the run, not only functions.

## References

- [Rust verification ladder](references/rust-verification-ladder.md)
- [Concurrency and fault testing](references/concurrency-fault-testing.md)
- [Agent evals in Rust](references/agent-evals-rust.md)
- [CI and supply-chain gates](references/ci-supply-chain.md)

## Shared references

- [Seven-layer map](../../references/seven-layer-map.md)
- [Architecture escalation](../../references/architecture-escalation.md)
- [GPT-5.6 Sol operating profile](../../references/gpt-5.6-sol-operating-profile.md)
- [Evidence and confidence](../../references/evidence-and-confidence.md)

## Version 3 Rust assurance assets

Use `../../assets/rust/control_evidence.rs`, `../../assets/rust/repair_budget.rs`, and `../../assets/rust/learning_record.rs` as adaptable domain sketches. Verify ownership and candidate identity, no-change decisions, circuit-break behavior, review evidence, and learning-record lifecycle in addition to code correctness.
