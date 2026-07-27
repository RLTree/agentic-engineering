# Graceful shutdown protocol for Rust agent services

Shutdown is a state transition with a deadline. It must stop new effects, propagate cancellation, drain owned work, reconcile ambiguity and flush durable evidence.

## Sequence

1. **Detect:** OS signal, admin command, lease loss, fatal invariant or deployment drain.
2. **Quiesce intake:** stop accepting new runs; return retryable/unavailable status as appropriate.
3. **Mark draining:** publish health/readiness state and shutdown deadline.
4. **Cancel:** signal run/task cancellation tokens; stop scheduling new nodes/actions.
5. **Drain:** close task trackers/queues as designed and wait for cooperative completion.
6. **Reconcile:** classify in-flight external effects; query by action/idempotency ID where needed.
7. **Persist:** checkpoint run state, effect journal/outbox, artifact references and cancellation reasons.
8. **Flush telemetry:** bounded flush; never wait indefinitely.
9. **Force boundary:** abort remaining abort-safe tasks or exit with an explicit dirty-shutdown record.

Tokio’s shutdown guidance commonly combines signal detection, cancellation tokens and waiting for tasks (for example via a task tracker). The exact primitives may differ; the lifecycle obligations do not.

## Per-task contract

Each task defines cancellation points, cleanup, effect ambiguity behavior, maximum drain time and whether forced abort is safe. Code must not swallow cancellation and start more work.

## Health behavior

Readiness should fail when intake is closed; liveness should remain healthy while bounded drain is progressing unless orchestration requires otherwise. Ensure load balancers stop new traffic before process termination.

## Data safety

Checkpoint before acknowledging shutdown completion. Avoid holding transactions/locks through long drain. External effects need explicit reconciliation; local RAII cannot undo a remote request.

## Tests

Signal at idle, queue wait, model stream, pre-effect, post-dispatch/pre-record, verification, checkpoint and human interrupt. Assert no new intake/effects, tasks terminate by deadline, state/evidence persists, ambiguous actions are visible, and repeated shutdown is idempotent.
