# Provider and framework boundary

Agent frameworks and model SDKs can accelerate integration, but the application’s domain, state, policy, durability and evaluation should not depend on one provider’s message or tool-call representation.

## Boundary layers

```text
Domain: Objective, RunState, Decision, ProposedEffect, Evidence
Application: use cases, loop/graph policy, authorization, recovery
Ports: Model, Tool, StateStore, EffectJournal, Clock, Telemetry
Adapters: OpenAI/other model SDK, Rig/other framework, MCP, A2A, DB, HTTP
Composition: config, dependency injection, runtime startup
```

Dependencies point inward. Framework callbacks and provider response types are converted at the adapter boundary.

## Model port

Expose the semantic operation the application needs: `decide_next`, `classify_route`, `evaluate_artifact`, or a generic completion port with a versioned structured-output contract. Include model/effort/config metadata in trace, but do not scatter model names through domain code.

## Tool port

A framework’s function-tool abstraction is an adapter to your internal tool registry and policy, not the policy itself. Internal contracts carry side-effect class, capability, approval, timeout, idempotency and error taxonomy even when the SDK does not.

## Framework adoption record

Before adding a framework evaluate:

- exact capability gained versus custom code;
- lifecycle/cancellation and backpressure behavior;
- structured output and schema guarantees;
- observability and trace export;
- persistence/replay semantics;
- provider portability and escape hatches;
- maintenance cadence, license and security posture;
- ability to test without network/provider;
- how much domain logic would become framework-specific.

## Anti-corruption layer

Normalize roles/messages, tool calls, token/cost usage, refusal/finish reasons, streaming events and errors. Preserve raw provider IDs only as metadata. Reject semantically incomplete responses at the boundary.

## Migration test

A provider or framework can be replaced without rewriting domain state, effect policy, evaluation fixtures or core use cases. Build at least one fake adapter and one contract test suite that every provider adapter must pass.
