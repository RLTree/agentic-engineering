---
name: rust-agent-durability
description: "Use when a Rust agent must survive retries, crashes, restarts, duplicate delivery, waits, or ambiguous effects."
---

# Rust Agent Durability

## Core principle

Assume at-least-once execution around failure boundaries. Persist enough typed intent, state and effect evidence that replay can continue or reconcile without duplicating externally visible consequences.

## Workflow

### 1. State the failure model

List crashes, process restarts, deployments, network ambiguity, duplicate messages, reordered delivery, stale workers, human latency, storage failure and partial external effects. Durability requirements follow from these, not from framework labels.

### 2. Define authoritative durable state

Persist run version, node/phase, input hashes, decisions, budgets, evidence references, approvals, pending effects, receipts and terminal reason. Separate large artifacts from transactional metadata.

### 3. Build an effect journal

Before executing an external effect, durably record normalized intent, target, precondition, risk, idempotency key and approval. After execution, record receipt/result or unknown outcome. Use [the effect-journal protocol](references/effect-journal-protocol.md).

### 4. Use idempotency and transactional messaging

Choose stable keys from business intent, not attempt number. Use outbox/inbox or equivalent atomic boundaries for state plus messages. Deduplicate at the receiver and retain results long enough for retry windows.

### 5. Design replay

Make pure decisions deterministic or record their outputs. Version state, prompts/model configuration and node logic when replay semantics depend on them. Treat “unknown effect outcome” as reconciliation, not blind retry.

### 6. Define ownership and leases

Use fencing tokens/version checks so a stale worker cannot commit after takeover. Bound leases and renewals; make ownership transitions observable.

### 7. Plan compensation and reconciliation

For non-idempotent effects, define compensating action, human reconciliation or irreversible terminal state. Compensation is a business operation with its own failures and evidence.

### 8. Select runtime strategy

Compare database-backed state machine, queue/outbox workers, Restate or another durable workflow boundary against the failure model. Keep the domain state/effect contracts portable.

### 9. Fault-test recovery

Kill at every persistence/effect boundary, duplicate messages, reorder delivery, expire leases, corrupt/stale versions and resume approvals. Assert final state and external effects, not only process survival.

## Output contract

Return a **Rust Durability and Effect Plan** with:

- explicit failure model;
- durable state/checkpoint schema;
- effect journal and idempotency design;
- outbox/inbox and transaction boundaries;
- replay/versioning rules;
- lease/fencing ownership model;
- compensation/reconciliation policy;
- runtime-option tradeoff;
- crash/duplicate/recovery test matrix.

## Common failures

- **In-memory result as durability:** state resumes but effects duplicate. Journal and idempotency are required.
- **Attempt-based key:** retries generate new idempotency identities. Derive from business intent.
- **Blind retry after timeout:** the first effect may have succeeded. Reconcile by key/receipt.
- **Stale worker commits:** lease expiry lacks fencing. Use versions/tokens at commit.
- **Replay calls model again:** decisions drift unexpectedly. Record or version nondeterministic outputs.
- **Network I/O inside local transaction:** rollback itself is untested. Treat it as a first-class workflow.

## References

- [Effect journal protocol](references/effect-journal-protocol.md)
- [Idempotency and outbox](references/idempotency-outbox.md)
- [Replay and versioning](references/replay-versioning.md)
- [Durable runtime options](references/durable-runtime-options.md)

## Shared references

- [Seven-layer map](../../references/seven-layer-map.md)
- [Architecture escalation](../../references/architecture-escalation.md)
- [GPT-5.6 Sol operating profile](../../references/gpt-5.6-sol-operating-profile.md)
- [Evidence and confidence](../../references/evidence-and-confidence.md)
