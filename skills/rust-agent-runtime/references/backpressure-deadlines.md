# Backpressure and deadlines

Backpressure turns overload into an explicit policy instead of memory growth, stale work and dependency collapse.

## Bounded queues

Use bounded `tokio::sync::mpsc` channels and semaphores. Derive capacity from accepted memory, item size, service rate, burst and maximum staleness. Record queue depth and wait time.

When full choose deliberately:

- wait under deadline;
- reject with overload signal;
- shed low-priority work;
- coalesce superseded work;
- persist to a durable queue;
- route to another healthy worker.

Unbounded channels are acceptable only when a proven external bound exists and is documented/tested.

## Concurrency limits

Separate limits for model calls, each tool/provider, CPU-heavy work and external effects. A global semaphore alone can let one dependency starve all others. Acquire permits with cancellation/deadline and release through RAII.

## Deadline propagation

Carry an absolute run deadline and derive child budgets rather than stacking independent full timeouts. Reserve time for verification, checkpoint and shutdown. Distinguish queue wait, connect, request/stream, effect reconciliation and total action timeout.

```rust
let remaining = deadline.saturating_duration_since(Instant::now());
let result = tokio::time::timeout(remaining.min(tool_budget), call()).await;
```

A timeout means the caller stopped waiting; it does not prove the remote effect did not occur.

## Fairness and priority

Define priority classes and starvation policy. Avoid holding a permit while waiting for unrelated approval or long backoff. Limit retry concurrency and use jitter/circuit breaking so agents do not amplify outages.

## Observability

Queue length/capacity, enqueue/drop/reject counts, wait and service time, active permits, deadline remaining, timeout phase, oldest item age and per-provider saturation.

## Fault tests

Slow consumer/provider, burst, permanently full queue, cancellation while acquiring, timeout after dispatch, priority starvation, retry storm, receiver closure and graceful shutdown with queued work.
