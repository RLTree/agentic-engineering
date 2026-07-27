# Rust agent ecosystem and selection posture

**Research lock:** 2026-07-22. Rust agent libraries and protocol SDKs evolve quickly. Confirm current official documentation and crate versions before implementation.

## Stable foundations

Prefer stable, general Rust mechanisms for system guarantees:

- `serde` for explicit data contracts;
- a JSON Schema layer such as `schemars` when protocol/tool schemas are needed;
- Tokio for async runtime, bounded channels, cancellation and task supervision;
- `tracing` plus OpenTelemetry-compatible export for structured run/tool/effect telemetry;
- a durable database or workflow engine for checkpoints and effect journals;
- Cargo's format, check, test and Clippy gates;
- property, concurrency and fault tests appropriate to the state/effect model.

These should contain the application's invariants. Provider and agent-framework APIs should remain adapters.

## MCP

The Model Context Protocol project maintains an official Rust SDK (`rmcp`). Use it for protocol mechanics, but preserve your own domain tool contract, authorization, idempotency and audit layers. Treat server-provided annotations and tool output as untrusted input unless the server and channel are trusted.

## A2A

The A2A project lists Rust among its official SDK languages. Use A2A when the boundary is agent-to-agent delegation or task collaboration, not merely tool/resource access. Pin a protocol version, run conformance tests and isolate protocol DTOs from domain state because the standard and SDKs continue to mature.

## Agent frameworks

Rust frameworks such as Rig can accelerate model/provider integration, agent builders, tool macros and observability. Use them behind ports/adapters. Do not let framework message types, tool abstractions or error types become the domain model. Current documentation and APIs may change faster than the application's invariants.

## Durable runtimes

Options include:

- a local state machine plus transactional checkpoint/effect tables;
- a durable workflow system with Rust support, such as Restate where its execution model fits;
- service-specific queues and workers with an outbox/inbox and leases;
- external workflow engines through a service boundary when first-class Rust support is limited.

Select based on failure model, replay semantics, operational ownership, latency, scale and migration needs—not on the label “agent framework.”

## Default architecture

Use a workspace with clear boundaries:

- `domain` — typed state, decisions, invariants, errors;
- `application` — use cases and orchestration ports;
- `runtime` — loop/graph execution, budgets, cancellation, supervision;
- `tools` — typed tool definitions and effect classification;
- `adapters` — model, MCP/A2A, storage, queue and network implementations;
- `durability` — checkpoints, journals, idempotency and recovery;
- `telemetry` — traces, metrics and redaction;
- `evals` — fixtures, trajectory records and graders;
- `bin/*` — composition roots.

Keep the decision core as pure as practical. Return intended effects as data, validate them against policy, then execute through an effect boundary.
