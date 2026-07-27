# Idempotency, deduplication, inbox and outbox

These mechanisms solve related but different problems.

## Definitions

- **Idempotent operation:** repeating with the same semantic key produces no additional effect.
- **Deduplication:** receiver recognizes a duplicate message/action and suppresses or returns prior result.
- **Outbox:** records local state change and message/effect intent atomically, then dispatches asynchronously.
- **Inbox:** records consumed message IDs so at-least-once delivery does not reapply processing.

## Key design

Generate a stable key from semantic action identity, not a random key per retry. Scope it by tenant/operation/target and retain it for at least the provider’s duplicate window. Bind it to an arguments digest so accidental reuse with different payload is rejected.

## Transactional outbox

In one database transaction write domain transition and outbox entry. A dispatcher leases pending entries, sends under action key, and marks result. Leases expire so another worker can recover. Exactly-once delivery is generally not assumed; consumers/effects remain idempotent or reconcilable.

## Inbox

Store message ID, handler/version, result digest/status and processing time. Use atomic claim/update. Decide whether duplicate returns cached result or acknowledgment. Bound retention based on replay horizon and risk.

## Ordering

If effects require per-entity order, include stream/aggregate sequence and reject/gap-handle out-of-order messages. Global ordering is expensive and often unnecessary.

## Rust implementation concerns

Use database uniqueness constraints as final dedupe authority, not only in-memory sets. Keep transactions short and do network I/O after commit. Use typed IDs/statuses and optimistic concurrency. Ensure cancellation releases leases or lets them expire safely.

## Tests

Same key/same payload, same key/different payload, concurrent claim, crash before/after dispatch, redelivery after lease expiry, out-of-order sequence, retention expiry, provider duplicate response and reconciliation.
