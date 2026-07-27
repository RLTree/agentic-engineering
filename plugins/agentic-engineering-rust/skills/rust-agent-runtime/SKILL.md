---
name: rust-agent-runtime
description: "Use when a Tokio agent needs supervision, bounded concurrency, cancellation, deadlines, backpressure, or shutdown."
---

# Rust Agent Runtime

## Core principle

Every spawned task, queue and in-flight effect needs an owner, budget and shutdown path. Concurrency should make lifecycle and pressure explicit rather than detach work from the run that created it.

## Workflow

### 1. Define the runtime tree

Identify process, supervisor, run, node/worker and tool-call lifetimes. Assign task ownership, cancellation propagation and join/drain behavior. Read [structured concurrency in Tokio](references/structured-concurrency-tokio.md).

### 2. Use bounded communication

Choose bounded `mpsc`/semaphore capacity from memory, rate and latency constraints. Define behavior on full queues: wait with deadline, reject, shed, coalesce or persist. Never use unbounded queues by habit.

### 3. Propagate cancellation and deadlines

Use cancellation tokens or owned channels plus `select!`. Give external calls timeouts and total run deadlines. Distinguish caller cancellation from timeout and dependency failure.

### 4. Supervise tasks

Track spawned tasks; surface panics and errors; cancel dependents; wait for completion on shutdown. Avoid detached `tokio::spawn` for work whose result or cleanup matters.

### 5. Protect shared state

Prefer message passing or short critical sections. Do not hold synchronous or async locks across network/model/tool awaits. Define ordering, version checks and ownership for mutable state.

### 6. Implement graceful shutdown

Stop intake, signal cancellation, allow bounded drain, flush checkpoints/effect journals/telemetry, close trackers and enforce a final deadline. Use [the graceful-shutdown protocol](references/graceful-shutdown-protocol.md).

### 7. Propagate observability

Attach run/task/action IDs and tracing spans to spawned tasks and tool calls. Record queue depth, wait time, active tasks, cancellation reason, timeout and shutdown outcome.

### 8. Test runtime failures

Exercise saturation, slow consumers, cancellation at every await boundary, panic, timeout, shutdown during effect, lost receiver, duplicate message and restart. Use [the runtime fault matrix](references/runtime-fault-matrix.md).

## Output contract

Return a **Rust Runtime Contract** with:

1. task ownership tree;
2. queue/semaphore capacity and overload policy;
3. cancellation/deadline propagation;
4. supervision and panic/error handling;
5. shared-state synchronization rules;
6. graceful-shutdown sequence;
7. runtime telemetry;
8. saturation/cancellation/fault tests.

## Common failures

- **Detached tasks:** shutdown reports success while work/effects continue. Track and join.
- **Unbounded channels by habit:** pressure becomes memory growth and stale work. Bound and define overload.
- **Cancellation blindness:** tasks ignore run cancellation during awaits. Select on cancellation and deadlines.
- **Lock held across external await:** throughput collapses or deadlocks. Copy state or redesign ownership.
- **Timeout as retry:** expired operations repeat without idempotency. Classify and reconcile effects.
- **Abrupt shutdown:** state/evidence is lost. Stop intake, cancel, drain and flush under a deadline.

## References

- [Structured concurrency in Tokio](references/structured-concurrency-tokio.md)
- [Backpressure and deadlines](references/backpressure-deadlines.md)
- [Graceful shutdown protocol](references/graceful-shutdown-protocol.md)
- [Runtime fault matrix](references/runtime-fault-matrix.md)

## Shared references

- Seven-layer map (canonical repository reference library: seven-layer-map.md)
- Architecture escalation (canonical repository reference library: architecture-escalation.md)
- GPT-5.6 Sol operating profile (canonical repository reference library: gpt-5.6-sol-operating-profile.md)
- Evidence and confidence (canonical repository reference library: evidence-and-confidence.md)

## Version 3 bounded repair and worker ownership

Bind each spawned task to a typed task/lease identity, cancellation lineage, budget, and return envelope. Distinguish task liveness from absence of a coordination message. Prevent detached repair loops and enforce semantic circuit-break decisions when repeated mechanisms produce no new evidence.
