# Typed state and effects in Rust agent systems

Use Rust’s type system to separate semantic decisions from executable effects and to make illegal lifecycle transitions difficult to express.

## Domain-first model

Represent domain intent independently from provider SDKs, JSON blobs and async runtime types:

```rust
#[derive(Clone, Debug)]
pub struct RunId(pub uuid::Uuid);

#[derive(Clone, Debug)]
pub enum RunStatus {
    Queued,
    Running { step: StepId },
    WaitingApproval { action: ActionId },
    Verifying,
    Succeeded,
    Failed { kind: FailureKind },
    Cancelled,
}

#[derive(Clone, Debug)]
pub enum ProposedEffect {
    ReadRepository { query: SearchQuery },
    WriteArtifact { path: SafePath, content: ArtifactBody },
    SendMessage { destination: Destination, body: MessageBody },
}
```

Newtypes prevent accidental interchange of run, task, user, provider and external resource IDs. Validated constructors should enforce path, URL, model, capability and size constraints at boundaries.

## Decision/effect split

A model proposes a typed `Decision` or `ProposedEffect`. Deterministic application code validates preconditions, authorization, budget, approval and idempotency before an adapter executes it. The model never receives a raw credential or direct production client.

```text
Model output -> parse/validate -> policy -> authorize/approve
             -> journal intent -> execute adapter -> reconcile/verify -> state transition
```

## State transitions

Prefer methods or a transition function that consumes an expected state/version and returns a new state plus domain events. Avoid public mutable fields and ad hoc status strings. For durable stores use optimistic concurrency (`expected_version`) so two workers cannot silently overwrite state.

## Effect traits

Define capabilities around task semantics, not vendor APIs:

```rust
#[async_trait::async_trait]
pub trait ArtifactStore: Send + Sync {
    async fn put(&self, intent: PutArtifact) -> Result<StoredArtifact, EffectError>;
}
```

Keep trait methods bounded and typed. Avoid a universal `execute(json)` escape hatch. Group traits by security/effect boundary so tests can replace them with deterministic fakes.

## Serialization

Persist versioned wire/domain DTOs with explicit enums and deny or preserve unknown fields according to compatibility policy. Do not serialize runtime handles, cancellation tokens, provider clients or borrowed data into durable state. Validate after deserialization; syntactic success does not prove domain invariants.

## Invariants to encode

- terminal states cannot dispatch new actions;
- approval references match action digest/version;
- budgets never become negative;
- completed action IDs cannot complete twice;
- only verified acceptance can produce `Succeeded`;
- effect-bearing transitions require journal evidence;
- sensitive payloads are wrapped/classified and excluded from `Debug`/traces.
