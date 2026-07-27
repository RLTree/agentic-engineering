# Structured concurrency with Tokio

Tokio tasks are cheap, but spawned work is not automatically scoped to the request that created it. Build an explicit ownership tree with cancellation and join/drain semantics.

## Ownership tree

```text
process
  supervisor
    run task
      graph/loop node tasks
        model/tool calls
```

Every task has one owner that observes completion and decides how child failure affects siblings and parent. Avoid detached `tokio::spawn` for work whose result, side effect or cleanup matters.

## Supervisor pattern

Use a `CancellationToken` (or equivalent owned cancellation channel) and a `TaskTracker`/`JoinSet`-style collection. Spawn through a small wrapper that creates tracing spans, catches join errors/panics, registers task metadata and returns typed results.

```rust
let child = cancel.child_token();
let handle = tokio::spawn(async move {
    tokio::select! {
        _ = child.cancelled() => Err(RuntimeError::Cancelled),
        result = run_node(ctx) => result,
    }
});
```

Cancellation is cooperative. Every potentially long wait must select on cancellation or use a future that is cancelled by drop with understood semantics.

## Failure policy

Specify whether a child failure cancels siblings, is collected as a partial result, triggers replacement or escalates. Surface `JoinError`; a panic is not a successful `None`. For critical invariants, contain the run and preserve evidence.

## Blocking work

Do not run CPU-heavy or blocking I/O on Tokio core threads. Use `spawn_blocking`, a dedicated pool or an external worker, with concurrency limits and cancellation limitations documented. Dropping a blocking task handle does not necessarily stop the underlying work.

## Resource ownership

Own permits, channels, temporary files, transactions and effect leases within the task scope. Use RAII for local cleanup, but remember external effects need explicit journal/reconciliation.

## Tests

Cancellation before start, during queue wait, model stream, tool request and verification; child panic; parent drop; sibling cancellation; shutdown with long blocking task; no leaked tasks; trace parentage; and deterministic cleanup.
