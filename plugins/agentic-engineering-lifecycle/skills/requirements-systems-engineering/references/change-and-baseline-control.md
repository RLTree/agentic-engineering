# Change and baseline control

A baseline is an agreed, versioned decision state used for coordination—not a freeze on learning. Change control preserves coherence, authority, impact analysis, evidence validity and rollback while allowing field evidence to revise prior commitments.

## Vocabulary
- **baseline:** Approved version of related requirements, architecture, interfaces, tests, operating envelope or release evidence.
- **change request:** Proposed modification with rationale, evidence, impact and authority.
- **configuration item:** Version-controlled artifact whose identity matters to product behavior or assurance.
- **evidence invalidation:** Loss of applicability caused by a material change in artifact, environment, population or method.
- **compatibility window:** Declared period and conditions under which old and new contracts coexist.

## Decision procedure
1. Identify configuration items: model, prompt/skill, tools, schemas, data, policy, runtime, infrastructure, requirements, architecture, tests/evals, telemetry and docs.
2. For a change, record driver/evidence, affected claims and traces, alternatives, compatibility, migration, risk, verification, rollout, rollback and authority.
3. Classify change by consequence and reversibility; choose automated, peer, specialist, or governance review.
4. Update baselines atomically where possible; preserve provenance and supersession links.
5. Invalidate or rerun evidence whose operating conditions or versions changed.
6. Observe field results and close, revise or revert the change.

## Decision table

| Change class | Control | Example |
|---|---|---|
| Low-risk internal/refactor | Automated checks + peer review | No contract/behavior change |
| Behavior/interface | Impact analysis + contract/field evidence | Tool schema or workflow |
| High-impact effect/policy | Named authority + progressive rollout | Permission/autonomy change |
| Emergency | Preauthorized bounded path + retrospective | Incident mitigation |

## Evidence obligations
- Baselines include model/harness/tool/data/policy versions, not only source commit.
- Emergency change cannot bypass provenance, verification and follow-up indefinitely.
- Compatibility has an exit date and migration owner.
- Evidence invalidation is recorded; old results are not silently reused.

## Review questions
1. Which claims and cohorts does this change invalidate?
2. Can the system run mixed versions, and what state/schema hazards arise?
3. Who is authorized to accept the changed risk?
4. How will we know in the field whether the change should remain?

## Failure patterns
- Baseline as bureaucracy: changes wait without risk-based value.
- Baseline as fiction: runtime models/prompts/tools differ from reviewed versions.
- Compatibility forever: dual paths accumulate with no exit criterion.

## Research basis

Uses lifecycle/configuration and requirements standards, secure release, and
monitoring questions. NIST AI 800-4 is a challenge taxonomy rather than a
prescribed change-control method (`F-NIST-AI800-4`). Historical lineage: [R75]
[R83] [R84] [R85] [R95].
