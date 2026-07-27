# Durable runtime options for Rust agent systems

Choose durability based on required semantics, not branding. A long-running Tokio process is not durable if state and timers disappear on restart.

## Options

### Application-managed state machine
Rust service plus database tables for run state, actions, checkpoints, outbox/inbox and leases. Best when workflow semantics are modest and the team can own recovery/versioning. Requires careful crash/fault testing.

### Durable execution platform
A workflow/runtime such as Temporal-compatible services or Rust-oriented systems such as Restate can provide persisted invocations, retries, timers and recovery abstractions. Verify current Rust SDK maturity and exact semantics before adoption; hide platform APIs behind application ports where practical.

### Queue plus workers
Durable broker, idempotent handlers and state database. Good for independent jobs/events; complex branching/human waits still need an explicit state machine.

### Event sourcing
Immutable events rebuild state and support audit/time travel. Useful for complex domain history, but adds schema/upcaster and projection complexity.

## Selection criteria

- maximum run/wait duration and restart requirements;
- number/complexity of branches, timers and human interrupts;
- effect idempotency/reconciliation support;
- throughput/latency and geographic needs;
- deployment/operations expertise;
- local development and deterministic testing;
- schema/version migration model;
- observability and administrative repair;
- vendor/platform lock-in and portability;
- security/data residency.

## Adoption proof

Prototype the hardest semantics: crash after remote success, long human interrupt, timer, cancellation, version deployment, partial worker failure and backfill/replay. A happy-path demo does not validate durability.

## Boundary

Keep domain state/effect contracts independent of runtime-specific decorators/contexts. The durable runtime owns scheduling/replay; your application still owns business invariants, permissions, effect safety, acceptance and incident policy.
