# Effect journal protocol in Rust

The effect journal is the authoritative record of intended and observed external side effects. It supports idempotency, reconciliation, replay and audit.

## State machine

```text
Proposed -> Authorized -> Prepared -> Dispatched ->
  Confirmed | Rejected | FailedBeforeEffect | Ambiguous -> Reconciled
                                      Confirmed -> Verified
                                      Confirmed -> Compensating -> Compensated|CompensationFailed
```

Not every adapter can distinguish every state; preserve ambiguity rather than inventing certainty.

## Record

```rust
pub struct EffectRecord {
    pub action_id: ActionId,
    pub run_id: RunId,
    pub kind: EffectKind,
    pub target: NormalizedTarget,
    pub args_digest: Digest,
    pub idempotency_key: IdempotencyKey,
    pub status: EffectStatus,
    pub approval_ref: Option<ApprovalRef>,
    pub provider_request_id: Option<String>,
    pub attempts: Vec<AttemptRecord>,
    pub version: u64,
}
```

Keep sensitive arguments in a protected store or encrypted payload; journal normalized metadata/digests sufficient for control and audit.

## Transaction boundary

Persist prepared intent before dispatch. Where a local database mutation must accompany publication, use a transactional outbox. After dispatch, persist the provider identifier/result and verify authoritative external state. Use optimistic version checks to prevent two workers dispatching the same action.

## Adapter contract

Adapters accept action/idempotency ID and return a result that distinguishes pre-dispatch failure, confirmed outcome and ambiguity. They expose reconciliation by stable external/client key when the provider supports it.

## Replay

On resume, inspect journal first. Never infer “not done” from missing in-memory result. Prepared may be dispatchable; Dispatched/Ambiguous must reconcile; Confirmed should verify or continue without redispatch; terminal failed states follow explicit policy.

## Tests

Concurrent dispatch race, duplicate delivery, crash at each transition, store failure after remote success, provider ignores idempotency, reconciliation not found/uncertain, approval stale, compensation failure and journal migration.
