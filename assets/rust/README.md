# Adaptable Rust reference fragments

These files are architecture fragments, not a version-pinned crate. Copy only the pieces that fit the target repository, place provider/telemetry SDKs behind adapters, and select dependency versions deliberately.

They demonstrate:

- provider-independent typed run state and proposed effects (`agent_domain.rs`);
- versioned effect-journal and reconciliation semantics (`effect_journal.rs`);
- tracked Tokio tasks, cancellation, deadlines, bounded concurrency and drain (`runtime_supervisor.rs`);
- schema-first tool DTOs and domain validation (`tool_contract.rs`);
- deterministic model fakes for trajectory scenarios (`testkit.rs`);
- typed authentic-use observations with stable run/task/effect identities (`field_observation.rs`);
- pure evidence-based progressive-rollout gates (`rollout_gate.rs`);
- privacy, metric-cardinality and representative/priority sampling policy (`telemetry_policy.rs`).

## Downstream integration rules

1. Keep domain identities independent of OpenTelemetry trace/span IDs; traces can be sampled or unavailable while effect reconciliation and product evidence remain authoritative.
2. Use `tracing` spans/events for causal structure and OpenTelemetry/W3C Trace Context at process boundaries. Capture context explicitly across Tokio task spawning, channels, queues and durable resume.
3. Keep high-cardinality values such as user, run, prompt, URL and error detail out of metric labels. Redact/minimize workload content at the producer.
4. Treat feature flags as exposure controls, never as authorization. Enforce identity, policy, permissions and effect limits server-side.
5. Gate autonomy/ramp changes on outcome, guardrail, data-quality, trace-completeness, ambiguous-effect and error-budget evidence. Hard safety/security criteria may override aggregate improvement.
6. Test golden trajectories, context propagation, schema compatibility, redaction, cardinality, sampling, exporter failure/backpressure, shutdown flush, field queries and exact packaged configuration.

Before production use, choose crate versions from the target repository, run the full Rust verification ladder, adapt errors/data/security policy, and exercise crash points against the real store/provider. The plugin release does not claim these fragments compiled in its build environment because `cargo` and `rustc` were unavailable; `evals/run-rust-compile-check.md` and `evals/run-rust-observability-compile-check.md` specify downstream protocols.


## Version 3 control evidence additions

- `control_evidence.rs` — typed worker ownership, evidence packet, and review verdict.
- `repair_budget.rs` — pure repair-budget and semantic circuit-breaker policy.
- `learning_record.rs` — governed learning and no-change decision types.

These are adaptable domain sketches. Keep serialization, persistence, transport, and provider SDK types behind adapters; compile them inside the target workspace with its actual error, serde, and testing conventions.
