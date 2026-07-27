# Delegation contract

A delegation is a bounded work contract. “Investigate this” is not enough for reliable coordination.

## Required fields

```markdown
## Work package ID / owner
## Objective
## Inputs and provenance
## Scope and explicit exclusions
## Files/state exclusively owned
## Dependencies and assumptions
## Allowed tools/capabilities/budgets
## Deliverables and result schema
## Verification required
## Stop/escalation conditions
## Handoff evidence
```

## Ownership

Assign exclusive write ownership by files, modules, state fields or artifacts. When overlap is unavoidable, make one worker advisory and one authoritative, or serialize through an integration owner. Worktrees isolate filesystems but do not resolve semantic conflicts.

## Context packaging

Give each worker the minimum sufficient contract, relevant repository map, source/evidence pointers and current decisions. Do not copy the whole parent transcript. Label untrusted material and identify the authoritative state/version.

## Worker behavior

Workers should not silently expand scope, delegate again without permission, alter shared architecture, perform higher-risk effects, or claim global completion. They return local findings/artifacts/evidence and unresolved risks.

## Result schema

At minimum: status; findings/decisions; artifact paths/digests or patch; commands/tests and outcomes; assumptions; blockers; residual risks; suggested integration action. Structured results reduce fan-in ambiguity.

## Cancellation

Define how cancellation propagates, what partial artifacts are valid, how effects are reconciled, and whether another worker may safely take over. A cancelled worker must not continue external side effects.

## Acceptance

The parent/integrator verifies deliverables independently. Worker confidence is evidence about uncertainty, not proof of correctness.
