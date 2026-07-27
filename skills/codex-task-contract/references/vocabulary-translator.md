# Vocabulary translator: instinct to engineering request

Use this table to replace intuitive adjectives with controllable concepts.

| You may be thinking | Ask for |
|---|---|
| “Make it more agentic” | Name the adaptive decision, tools, authoritative state, effect boundary, budgets, stop and recovery policy |
| “Use a loop” | Observe–orient–plan–act–verify–update contract with iteration/tool/time/cost budgets and convergence criteria |
| “Use a graph” | Typed state, node/edge contracts, reducers, joins, checkpoints, interrupts, terminal states and replay semantics |
| “Make it robust” | Failure taxonomy, deadlines, backpressure, idempotency, reconciliation, graceful shutdown, fault-injection tests |
| “Make it professional” | Product truth, hierarchy, interaction/operational contract, acceptance-to-evidence matrix, exact-delivery QA |
| “Give the agent context” | Repository map, retrieval policy, provenance, relevance filter, progressive disclosure, compaction checkpoint |
| “Add guardrails” | Capability scopes, policy enforcement point, schema validation, approval classes, deny behavior, audit evidence |
| “Let it keep trying” | Retry/repair/replan distinctions, best-so-far retention, repeated-action detection, stop/escalation thresholds |
| “Use multiple agents” | Independent work packages, exclusive ownership, delegation contract, result schema, fan-in owner, cancellation |
| “Remember progress” | Durable run state, checkpoint schema, decision log, artifact index, resume protocol, state migrations |
| “Avoid duplicates” | Stable action ID, idempotency key, effect journal, deduplication, outbox/inbox, reconciliation |
| “Test the agent” | Task distribution, fixtures, outcome/trajectory/recovery/safety graders, trace evidence, regression gates |
| “Make the repo Codex-friendly” | Layered AGENTS.md, fast validation commands, architecture map, conventions, examples, local skills and evals |
| “Use Rust safely” | Typed state/effects, structured concurrency, bounded channels, cancellation tokens, deadlines, supervised tasks |

## Prompt transformation pattern

Transform `adjective + object` into:

1. **Observable quality** — what behavior should improve?
2. **Owning mechanism** — which layer can enforce it?
3. **Artifact** — what contract, schema, code, test, trace, or report must exist?
4. **Evidence** — how will the result be falsified?

Example:

> “Build a robust Rust agent.”

Becomes:

> “Build a Tokio-based agent worker with typed run/action state, bounded queues, propagated cancellation and deadlines, supervised tasks, an idempotent effect journal, graceful shutdown with bounded drain, and tests for saturation, timeout, cancellation at each await boundary, crash after external success, and replay. Preserve the provider behind a trait and return a trace-linked acceptance report.”

## Useful distinction pairs

- workflow vs agent;
- context vs memory;
- sandbox vs authorization;
- retry vs repair vs replan;
- checkpoint vs cache;
- idempotency vs deduplication;
- model judgment vs deterministic control;
- outcome eval vs trajectory eval;
- tool schema vs tool policy;
- concurrency vs parallelism;
- run state vs domain state;
- durable execution vs long timeout;
- delegation vs vague handoff.

Use the precise term only when its obligations are desired. Vocabulary is valuable because it exposes design consequences, not because technical nouns make a request sound advanced.
