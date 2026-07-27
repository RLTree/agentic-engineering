# Replay and versioning for Rust agent runtimes

Durable execution re-runs code against historical state/events. Replay safety requires stable semantics or explicit version gates.

## Persisted inputs

Record state/event schema version, graph/workflow version, node/handler version, model/prompt/skill identity, tool contract version, effect/action IDs and deterministic decision outputs needed for replay.

## Determinism boundary

Do not call clocks, random generators, models, network tools or environment-dependent APIs directly inside deterministic replay logic. Inject/record their results as events or execute them as activities/effects whose outcomes are persisted.

## Versioning strategies

- pin in-flight runs to old worker/code;
- branch behavior using persisted version markers;
- migrate state/events before resume;
- rebuild state from immutable events with upcasters;
- explicitly terminate/repair unsupported histories.

Choose and test one. Silent semantic change is the dangerous default.

## Schema evolution

Use versioned DTOs and conversion to current domain types. Additive fields need safe defaults only when absence has a well-defined meaning. Renames/removals/enum changes require migration or compatibility adapters. Preserve unknown data when round-trip compatibility matters.

## Model decisions

Model calls are non-deterministic. Persist accepted structured decisions and relevant evidence/model configuration. Historical replay should normally reuse the recorded decision, while offline re-evaluation can compare what a new model would have chosen without executing effects.

## Verification

Maintain golden histories for each supported version. Replay to the same semantic state/effect sequence, inject crash at boundaries, test upgrade/downgrade policy and verify unsupported history yields an explicit administrative state rather than corruption.
