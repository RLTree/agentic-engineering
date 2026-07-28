# Reducers, checkpoints, and interrupts

These mechanisms determine whether a graph remains correct under parallelism, pause/resume and replay.

## Reducers

A reducer combines concurrent or incremental updates to a state field. Define algebraic behavior where possible:

- **set union** for unique evidence IDs;
- **append with stable ordering key** for event history;
- **map merge with conflict rejection** for exclusive ownership;
- **maximum/minimum** for monotonic metrics;
- **custom fan-in** for ranked worker results.

Reducers should be deterministic, associative where execution order can vary, and explicit about duplicate handling. Never use last-writer-wins for decisions or effects unless the ordering is authoritative and tested.

## Checkpoints

Checkpoint before long waits, human interrupts, costly work, or external effects; after verified effects and meaningful state transitions; and at bounded intervals for long computation. A checkpoint includes graph/schema version, node position, state digest, pending actions, completed effects, budgets and trace cursor.

Checkpointing does not make code replay-safe. Nodes before a resume point must be deterministic or idempotent, and external effects must be journaled/reconciled.

## Interrupts

An interrupt payload should contain the decision, normalized proposed action, target, consequence, evidence, alternatives, and resume schema. Persist state before surfacing it. On resume, validate the actor, approval scope, state version and expiration.

Do not repeat side effects before an interrupt because some graph runtimes re-enter the node on resume. Split prepare/approve/execute into distinct nodes or use effect journal guards.

## Resume semantics

Define whether resume supplies a command, decision value, corrected data, or capability. Reject stale resumes when state has changed materially. Make repeated resume requests idempotent.

## Tests

Exercise concurrent update ordering, duplicate predecessor result, missing worker, checkpoint corruption, crash at every effect boundary, stale approval, cancel while interrupted, graph version upgrade and replay of historical state.
