# State, node, and edge contract

An explicit graph makes consequential control flow reviewable and testable. Its correctness depends on typed state and precise contracts, not the visual diagram alone.

## State contract

For each field define type, meaning, authority, default, persistence, sensitivity, merge/reducer rule, version and invariant. Separate domain state from execution metadata. Avoid one mutable `messages` bag as the only state.

Example fields: objective, current artifact refs, facts, assumptions, decisions, pending actions, approvals, budgets, acceptance evidence, failure, graph/schema version.

## Node contract

Each node declares:

- purpose and entry preconditions;
- state fields read and written;
- model/tools/capabilities used;
- deterministic versus semantic behavior;
- side effects and idempotency;
- timeout/cancellation behavior;
- output/update schema;
- errors and retry/recovery policy;
- exit invariants and trace evidence.

Keep nodes cohesive. A node that retrieves, decides, executes external effects, verifies, and routes is too large to reason about or replay safely.

## Edge contract

Each edge declares source, target, predicate/event, priority, exclusivity, evidence used, fallback and loop budget effect. Conditional routing should be deterministic when the condition can be derived from typed state.

For joins, define required/optional predecessors, timeout, partial failure, reducer and ordering. For cycles, define progress signal, maximum traversals and terminal escape.

## Terminal nodes

Use distinct terminal states for succeeded, failed, cancelled and escalated. Do not route all endings to “done.” Success must validate acceptance evidence. Failure should preserve recoverability and last safe checkpoint.

## Invariants

Recommended global invariants:

- only declared nodes update each state field;
- each effect has one semantic action ID;
- checkpoint occurs before/after configured consequence boundaries;
- graph never enters an undeclared state/version;
- joins are deterministic for the same predecessor outputs;
- replay does not repeat completed irreversible effects;
- terminal status is immutable except through an explicit administrative repair.
