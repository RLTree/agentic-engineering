---
name: rust-agentic-architecture
description: "Use when designing or refactoring an agentic Rust system’s domain, boundaries, state, effects, errors, or workspace."
---

# Rust Agentic Architecture

## Core principle

Use Rust types to make invalid agent states and unsafe effect requests difficult to represent. Keep domain decisions independent of model providers, agent frameworks, protocols, async runtime details and storage implementations.

## Workflow

### 1. Model the domain before the framework

Define run, task, action, observation, evidence, decision, effect, approval, budget and terminal-state types. Use enums for finite lifecycle states and newtypes for stable IDs.

### 2. Separate pure decision core and effectful shell

The core consumes typed state plus observations and returns a decision: intended actions/effects, state delta and rationale metadata. Adapters execute effects and return typed observations/receipts. Read [typed state and effect design](references/typed-state-effects.md).

### 3. Define ports and adapters

Create domain-owned traits for model inference, tools, storage, clock, IDs, approvals, telemetry and policy. Keep provider/framework DTOs in adapter modules. Use [the provider/framework boundary](references/provider-framework-boundary.md).

### 4. Design module/workspace boundaries

Separate `domain`, `application`, `runtime`, `tools`, `durability`, `adapters`, `telemetry`, `evals` and binary composition roots. Enforce one-way dependencies with domain at the center.

### 5. Design errors for recovery

Use explicit error enums that distinguish invalid input, policy denial, transient dependency, timeout, stale version, duplicate, invariant breach, unavailable capability and terminal failure. Avoid string matching to choose control flow.

### 6. Make effects data

Give each intended effect a stable action ID, kind, normalized parameters, target, risk class, idempotency key and preconditions. Validate/authorize before execution.

### 7. Choose libraries last

Evaluate Tokio, provider SDKs, Rig, MCP/A2A SDKs and durable runtimes against the ports and failure model. Record version/maturity risks and keep replacement seams.

### 8. Prove architecture with tests

Unit-test pure transitions; compile-test adapters; property-test invariants; contract-test providers/tools; run architecture dependency checks and serialize/deserialize compatibility cases.

## Output contract

Return a **Rust Agent Architecture** with:

- domain vocabulary and state enums;
- pure decision/effect boundary;
- port traits and adapter map;
- workspace/module dependency diagram;
- error and recovery taxonomy;
- effect/idempotency schema;
- framework/runtime selection rationale;
- architecture and invariant test plan.

## Common failures

- **Provider DTOs as domain:** provider messages and agent builders leak everywhere. Own domain types and ports.
- **Stringly lifecycle:** arbitrary strings encode state/action/error. Use enums and newtypes.
- **Runtime handles in durable state:** pure policy becomes hard to test. Keep decision logic synchronous/pure where practical.
- **Side effects inside planning:** retries duplicate external operations. Return intended effects as data.
- **Universal execute JSON escape hatch:** every function becomes an abstraction. Create ports only at volatility, effect or test boundaries.
- **Library-first architecture:** crate choice determines invariants. Model failure and contracts first.

## References

- [Typed state and effects](references/typed-state-effects.md)
- [Provider and framework boundary](references/provider-framework-boundary.md)
- [Workspace architecture](references/workspace-architecture.md)
- [Rust error taxonomy](references/rust-error-taxonomy.md)

## Shared references

- Seven-layer map (canonical repository reference library: seven-layer-map.md)
- Architecture escalation (canonical repository reference library: architecture-escalation.md)
- GPT-5.6 Sol operating profile (canonical repository reference library: gpt-5.6-sol-operating-profile.md)
- Evidence and confidence (canonical repository reference library: evidence-and-confidence.md)
