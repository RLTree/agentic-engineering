---
name: rust-agent-protocols
description: "Use when building schema-first MCP, A2A, tool, agent-card, authorization, or conformance boundaries in Rust."
---

# Rust Agent Protocols

## Core principle

Protocols define wire interoperability, not application correctness or authorization. Keep protocol DTOs at the edge, validate both directions and map them into domain-owned contracts with explicit identity, state and effect semantics.

## Workflow

### 1. Choose the right boundary

Use MCP for model/agent access to tools and resources. Use A2A for communication and task collaboration between agentic applications. Do not add either protocol when a local function or ordinary service API is the simpler boundary.

### 2. Pin the contract

Record protocol/spec version, SDK/repository, transport, auth model, capability negotiation and compatibility policy. Re-check current official sources before implementation.

### 3. Design domain-owned schemas

Define typed request, result and error semantics first. Generate or validate JSON Schema where applicable. Keep `rmcp`/A2A SDK types in adapters. Read [schema-first tool design](references/schema-first-tool-design.md).

### 4. Engineer MCP tools

Give tools unique stable names, clear task semantics, bounded inputs, explicit output schema, side-effect/risk metadata, actionable execution errors and deterministic ordering. Validate authorization for every resource/state handle. Use [MCP in Rust](references/mcp-rust.md).

### 5. Engineer A2A tasks

Define agent card/capabilities, identity, task lifecycle, artifacts, streaming, cancellation, resumption, delegation scope and provenance. Do not expose internal memory or broad credentials to peers. Use [A2A in Rust](references/a2a-rust.md).

### 6. Apply security at the adapter

Authenticate channel and caller, authorize target/operation, rate-limit, time out, validate schemas, sanitize data, redact secrets and log with stable IDs. Treat annotations and remote content as untrusted.

### 7. Test conformance and interoperability

Run official conformance/TCK tools when available; maintain golden messages, schema round trips, version negotiation, malformed input, timeout/cancel, duplicate/replay and cross-implementation tests.

### 8. Plan evolution

Use additive schema change where possible, capability negotiation, explicit deprecation and adapter versioning. Keep domain logic independent from wire-version churn.

## Output contract

Return a **Rust Tool and Protocol Contract** with:

1. MCP/A2A/ordinary API decision;
2. pinned version, SDK and transport assumptions;
3. domain versus wire type map;
4. schema, result and error contracts;
5. identity, authorization and risk controls;
6. lifecycle/cancellation/resume semantics;
7. conformance/interoperability tests;
8. version evolution and deprecation plan.

## Common failures

- **Protocol as architecture:** MCP/A2A is used without a boundary need. Start from ownership and task semantics.
- **serde_json Value everywhere:** upgrades become domain migrations. Isolate adapters.
- **Schema without semantics:** fields validate but side effects, errors and limits are unclear. Document behavior.
- **Remote metadata grants authority:** guessed/stolen IDs cross tenants. Reauthorize every call.
- **Transport disconnect proves no effect:** clients cannot validate or integrate reliably. Provide structured output schema.
- **No conformance suite:** local happy path hides wire incompatibility. Test against official and independent implementations.

## References

- [Schema-first tool design](references/schema-first-tool-design.md)
- [MCP in Rust](references/mcp-rust.md)
- [A2A in Rust](references/a2a-rust.md)
- [Protocol conformance](references/protocol-conformance.md)

## Shared references

- Seven-layer map (canonical repository reference library: seven-layer-map.md)
- Architecture escalation (canonical repository reference library: architecture-escalation.md)
- GPT-5.6 Sol operating profile (canonical repository reference library: gpt-5.6-sol-operating-profile.md)
- Evidence and confidence (canonical repository reference library: evidence-and-confidence.md)
