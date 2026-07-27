# Rust error taxonomy for agent systems

Errors should drive recovery decisions. Preserve causal source and machine-readable class while keeping user-facing messages safe and actionable.

## Layers

### Domain errors
Invalid transition, exhausted budget, unsatisfied precondition, policy conflict, stale version, unsupported action. These are deterministic and generally not retryable unchanged.

### Adapter/dependency errors
Transport, timeout, rate limit, authentication, authorization, not found, conflict, malformed response, provider refusal, capacity, protocol violation. Include dispatch/effect ambiguity.

### Effect errors
Rejected before dispatch, failed before effect, ambiguous after dispatch, externally confirmed failure, succeeded but local recording failed, verification mismatch, compensation failure.

### Runtime errors
Cancellation, task panic/join failure, queue closed/full, shutdown deadline, state store unavailable, checkpoint corruption.

### Internal/invariant errors
Bug or corrupted state. Contain and stop rather than converting into an ordinary retry.

## Shape

```rust
#[derive(Debug, thiserror::Error)]
pub enum ToolError {
    #[error("tool input is invalid: {field}")]
    InvalidInput { field: &'static str },
    #[error("operation is not authorized")]
    Denied,
    #[error("dependency rate limited the operation")]
    RateLimited { retry_after: Option<Duration> },
    #[error("effect outcome is unknown; reconciliation required")]
    AmbiguousEffect { action_id: ActionId },
    #[error("dependency failed")]
    Dependency { #[source] source: anyhow::Error },
}
```

Use library-specific typed errors; reserve `anyhow`-style context for application boundaries where callers do not branch on variants.

## Recovery metadata

Do not rely on `is_retryable: bool` alone. Expose failure phase, effect status, suggested operator, retry-after, target/provider code and safe user message. The loop/harness chooses policy based on budgets and idempotency.

## Logging

Errors carry stable codes and correlation IDs. Redact secrets and sensitive payloads; avoid dumping provider response bodies automatically. Log once at the boundary that has context and responsibility—repeated logs at every `?` obscure causality.

## Tests

Assert error mapping from each adapter, timeout-before/after-dispatch distinction, source chain, redaction, policy outcome, and that invariant errors cannot enter generic retry paths.
