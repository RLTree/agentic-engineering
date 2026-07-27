# Rust workspace architecture for agentic applications

Prefer a workspace that makes policy and effects visible. The exact crate count should follow team/deployment needs; boundaries matter more than maximal decomposition.

## Reference layout

```text
Cargo.toml
crates/
  agent-domain/       # IDs, state, decisions, effects, invariants
  agent-application/  # use cases, loop/graph policies, ports
  agent-runtime/      # Tokio supervision, queues, cancellation
  agent-model-openai/ # provider adapter
  agent-tools/        # tool registry, schemas, policy integration
  agent-protocol-mcp/ # MCP server/client adapter
  agent-protocol-a2a/ # A2A adapter, if needed
  agent-persistence/  # state/effect journal/outbox adapters
  agent-observability/# tracing/metrics/evidence mapping
  agent-app/          # composition root, config, CLI/server
  agent-testkit/      # fakes, fixtures, deterministic clock/model/tools
tests/scenarios/
```

Small applications can merge several crates while retaining modules and dependency direction.

## Dependency rules

Domain has minimal dependencies and no Tokio/provider/database types. Application depends on domain and port traits. Adapters depend on ports and external SDKs. Composition owns concrete wiring. Runtime concerns do not leak into persisted domain state.

Use workspace lint configuration and dependency policy. Pin the minimum supported Rust version when consumers require it; test intended feature combinations and platforms.

## Configuration and secrets

Deserialize configuration into raw DTOs, validate into typed config, and fail startup with actionable errors. Keep secrets behind redacted wrappers and secret stores; do not derive `Debug`/`Serialize` indiscriminately. Separate environment-specific capability policy from code defaults.

## Feature flags

Use features for genuinely optional integrations, not for mutually inconsistent architecture. Test the supported matrix and prevent accidental default activation of privileged/network components.

## Public API

Keep provider and persistence details private. Expose domain/application interfaces and stable error classes. Use `#[non_exhaustive]` or explicit compatibility strategy for public enums where evolution matters.

## Repository guidance

Add root and crate-scoped AGENTS.md, architecture diagrams/ADRs, fast/full commands, generated-file rules and scenario fixtures. Agentic code benefits from examples showing cancellation, effect journaling and tests—not merely style instructions.
