# Rust Agent Observability Downstream Check

## Purpose

Compile and behaviorally validate the adaptable Rust field-observation, rollout-gate, and telemetry-policy fragments with a downstream version-pinned `tracing`, Tokio, OpenTelemetry, serde, schema, and test stack.

The source package does not claim this protocol ran in the build environment.

## Temporary crate

Create a clean crate outside the plugin tree. Copy or adapt:

- `assets/rust/field_observation.rs`;
- `assets/rust/rollout_gate.rs`;
- `assets/rust/telemetry_policy.rs`;
- relevant domain/effect/runtime fragments;
- the six new JSON Schemas.

Pin all crate and toolchain versions in `Cargo.lock` and record them with the result.

## Static and build gates

Run, as supported by the target repository:

```text
cargo fmt --check
cargo check --all-targets --all-features
cargo test --all-targets --all-features
cargo clippy --all-targets --all-features -- -D warnings
cargo build --release --all-features
```

Record unavailable tools or unsupported feature/target combinations as not executed, not passed.

## Required tests

### Domain identity and schema

- IDs are typed and cannot be accidentally interchanged.
- serialization round trips preserve schema version and required fields;
- unknown fields are rejected where the wire contract is closed;
- invalid outcome/effect/evidence combinations are rejected;
- JSON instances validate against the packaged draft-2020-12 schemas.

### `tracing` and async propagation

- run span parents model/tool/effect spans correctly;
- spawned Tokio tasks preserve intended span context;
- channels carry durable domain identity even when trace context is lost;
- W3C trace context propagates across an HTTP or in-memory boundary;
- trace identity is not used as effect identity or authorization;
- cancellation and timeout events retain run/action/effect context.

### Field observation joins

- task, run, action, effect, assignment, exposure, and observation records join;
- missing assignment or exposure is detectable;
- system/model/harness/tool/envelope versions are present;
- intervention and human-work evidence can be attached without raw workload content;
- ambiguous effects remain nonterminal until reconciliation.

### Privacy and cardinality

- prohibited fields and secret-like values are rejected or redacted at source;
- raw prompts/tool payloads are absent by default;
- metric labels are allowlisted and bounded;
- high-cardinality IDs appear only in approved traces/evidence stores;
- pseudonymous IDs are treated as protected data;
- retention/privacy classes survive serialization.

### Sampling and priority retention

- deterministic representative sampling is stable for the same seed/identity;
- routine successes can be sampled;
- security events, severe failures, near misses, ambiguous effects, and interventions are always retained;
- sampling probability and policy version are observable;
- coverage gaps can be calculated by task/risk stratum.

### Rollout decision function

Use table and property/state-machine tests for:

- advance only when success, guardrails, joins, timing, and error budget satisfy the contract;
- hold on insufficient evidence or unresolved data quality;
- narrow on segment-specific success/failure;
- revert on guardrail or reliability breach;
- stop on critical security, unauthorized effect, or unrecoverable evidence failure;
- flags/variants never bypass authorization;
- repeated evaluation is deterministic for the same evidence snapshot.

### Exporter and shutdown

- exporter delay/failure does not block consequential work indefinitely;
- loss/drop accounting is visible;
- graceful shutdown stops intake, drains bounded work, flushes telemetry under a deadline, and reports incomplete flush;
- priority evidence uses a durable path appropriate to the product risk.

## Optional concurrency and fault tools

Use Loom for narrow synchronization primitives and Miri for applicable unsafe/FFI-sensitive code. Add process crash points around observation persistence, effect dispatch, confirmation, and reconciliation where durability is in scope.

## Evidence package

Return:

- toolchain and dependency versions;
- exact copied/adapted source hashes;
- commands and exit codes;
- test inventory and results;
- schema-validation report;
- trace examples with sensitive fields removed;
- cardinality and sampling checks;
- known incompatibilities or adaptations;
- residual risks and production integration decisions.
