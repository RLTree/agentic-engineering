# Schema-first tool design in Rust

A Rust tool should expose a stable semantic contract at the protocol boundary and validate into stronger domain types before any effect.

## Layers

```text
wire JSON -> generated/serde DTO -> syntactic validation
          -> domain conversion/semantic validation
          -> authorization/approval/idempotency
          -> application use case -> adapter effect
          -> typed result -> bounded/sanitized wire output
```

## Request types

Use `serde` with explicit names and versioning; generate JSON Schema with a tool such as `schemars` when it fits the project, then inspect the schema rather than assuming derives produce ideal descriptions. Use enums, formats, length/range constraints and examples. Avoid `serde_json::Value` except at a deliberately untyped extension boundary.

```rust
#[derive(serde::Deserialize, schemars::JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct CreateTicketRequest {
    /// Project-scoped identifier, not a display name.
    pub project_id: ProjectIdWire,
    #[schemars(length(min = 1, max = 200))]
    pub title: String,
}
```

`deny_unknown_fields` improves strictness but can reduce forward compatibility; choose per versioning policy.

## Description

Document when to use/not use, authoritative identifiers, side effects, approval class, idempotency, pagination/truncation, data handling and actionable errors. Tool names should reflect user task semantics.

## Output

Return structured fields plus stable IDs and evidence. Bound arrays/text and provide pagination/cursors. Sanitize untrusted content and mark provenance. Do not place secrets or internal stack traces in model-visible errors.

## Tests

Schema snapshots/diffs, valid/invalid examples, unknown/missing fields, semantic target mismatch, authorization, size limits, output injection, duplicate action ID, timeout ambiguity and backward compatibility.
