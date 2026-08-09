# Rollback and release evidence

Rollback is a designed state transition with data, effect, compatibility and operator semantics. A script that restores a previous binary is not enough when schemas, queues, external effects or user expectations have changed.

## Vocabulary
- **roll back:** Return exposure or implementation to a prior known state.
- **roll forward:** Deploy a corrective version when reversal is unsafe or impossible.
- **compensation:** Domain action that mitigates or reverses a previously confirmed effect.
- **reconciliation:** Determine authoritative outcome after an ambiguous or partial external operation.
- **release evidence package:** Artifacts proving identity, security, verification, readiness, rollout and recovery of a release.

## Decision procedure
1. Classify changes to code, config, models/prompts, data/schema, state machines, tools/protocols, permissions and external effects.
2. For each, define reverse, forward-fix, compatibility, migration, reconciliation and compensation paths.
3. Create release package: artifact hashes/provenance, SBOM, test/eval results, threat changes, migrations, PRR/SLO impact, cohort plan, rollback commands, owners and known gaps.
4. Test rollback/forward from realistic state, including in-flight work, old/new workers, queues, caches and ambiguous effects.
5. Define stop authority, decision latency, evidence collection and communication during rollback.
6. After release, verify expected version/exposure, state integrity, effects, data quality and user outcome; close temporary controls.

## Decision table

| Change | Rollback challenge | Required evidence |
|---|---|---|
| Stateless code | compatibility with requests | smoke/canary rollback test |
| Schema/data | irreversible writes or mixed readers | expand-contract/migration restore |
| Agent state graph | old checkpoints incompatible | versioned replay/migration test |
| External effect | cannot un-send action | idempotency/reconcile/compensate |
| Permission/autonomy | cached/derived authority | policy propagation and revoke test |

## Evidence obligations
- Rollback criteria and commands are reviewed before exposure.
- Irreversible migrations/effects require alternative containment and explicit authority.
- Release evidence is attached to the exact artifact and environment.
- Recovery exercises include human communication and customer/contract obligations where relevant.

## Review questions
1. What state cannot be restored by redeploying the old version?
2. What happens to in-flight or resumed agent runs?
3. Can an ambiguous effect be safely distinguished from failure?
4. Who can stop exposure and how quickly?

## Failure patterns
- Binary-only rollback: data, state and effects ignored.
- Untested runbook: recovery exists only as prose.
- Evidence after the fact: provenance, criteria and authority assembled during incident.

## Research basis

Uses SRE release/canary guidance, secure delivery, effect durability and
supply-chain evidence. SLSA v1.2 Source and Build tracks support provenance and
integrity, not behavioral correctness (`F-SLSA-12`). Historical lineage: [R98]
[R106] [R107] [R108].
