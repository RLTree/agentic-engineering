# Concurrency and fault testing in Rust

Async bugs hide in rare interleavings and failure timing. Build controllable boundaries so tests can pause and fail operations precisely.

## Techniques

### Deterministic dependency fakes
Model, tool, store and clock fakes expose barriers: wait before dispatch, after remote success, before journal update, during checkpoint, and during shutdown.

### Paused time
Use Tokio test time controls for timers/backoff/deadlines where appropriate. Avoid real sleeps. Assert absolute deadline propagation and retry schedules.

### Loom
For small synchronization components, Loom explores valid thread interleavings under its model. Keep state spaces small, abstract synchronization primitives behind cfg/modules, and assert invariants such as one dispatch, no lost wakeup and eventual terminal state.

### Miri
Run compatible tests under Miri to detect classes of undefined behavior, especially when unsafe code or FFI exists. Miri is not a concurrency scheduler or substitute for integration tests.

### Process fault tests
Kill/restart workers around durable boundaries. Use real database/queue containers where transaction/lease semantics matter.

## Required scenarios

Concurrent duplicate action claim; cancellation while acquiring permit; sender/receiver drop; panic in child; slow consumer; lock contention; retry storm; crash after external success; stale version conflict; shutdown deadline; duplicate/reordered message; telemetry/store failure.

## Assertions

Hard outer timeout; no leaked tracked tasks/permits; invariant-preserving final state; effect at most once or reconciled; monotonic version; bounded attempts/memory; cancellation reason retained; trace causal chain complete.

## Test design

Test one causal property per fixture. Keep failures reproducible with seed/event script. Do not rely on high iteration count alone—instrument the exact interleaving that matters.
