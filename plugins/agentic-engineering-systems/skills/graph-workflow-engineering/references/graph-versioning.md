# Graph and state versioning

Long-lived or durable runs may outlive code deployments. Treat graph topology, state schema, node semantics and tool contracts as versioned protocols.

## Version axes

- graph topology version;
- persisted state schema version;
- node implementation/semantic version;
- tool/protocol schema version;
- model/prompt/skill version used for decisions;
- artifact/effect record version.

Do not assume a single application version is enough to reconstruct a run.

## Compatibility policy

For every release declare whether it can: start new runs, resume checkpoints from supported versions, read old evidence, and reconcile old effects. Choose one strategy:

- finish old runs on old workers;
- migrate state/checkpoints forward;
- maintain compatible node/tool adapters;
- terminate and administratively repair unsupported runs.

## Migration design

Migrations should be deterministic, idempotent and separately testable. Preserve original state/evidence or a digest for audit. Validate invariants before and after. Do not execute external effects during state migration.

## Semantic changes

A schema-compatible change may still alter behavior: routing threshold, prompt, model, reducer, retry rule or approval class. Record semantic versions/digests in trace and evaluate historical fixtures against the new behavior.

## Rollout

Use canary runs or version-pinned cohorts. Monitor branch distribution, recovery rate, action count, cost, latency, effect ambiguity and acceptance scores. Define rollback behavior for in-flight runs before deployment.

## Historical replay

Replay with dependencies stubbed or in read-only mode. Compare state transitions and decisions, not only final output. Any difference affecting side effects, approvals or terminal state requires review.
