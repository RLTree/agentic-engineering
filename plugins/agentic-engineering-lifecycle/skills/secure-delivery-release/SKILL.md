---
name: secure-delivery-release
description: "Use when an agentic product needs secure development, provenance, progressive release, authorization, or rollback."
---

# Secure Delivery & Release

## Core principle

A release is an authorized transition of a specific, provenance-verifiable artifact into a bounded operating envelope. Security, supply-chain integrity, migration, observability, progressive exposure, rollback, and operator readiness are part of the product change—not post-build paperwork.

## Workflow

### 1. Define the release object and trust boundaries

Identify exact source revision, dependencies, build environment, artifact, configuration, data/schema migrations, feature flags, target environments, identities, secrets, permissions, tools/effects, and external services.

### 2. Update the threat and misuse model

Cover prompt/context injection, poisoned retrieval, tool abuse, privilege escalation, data exfiltration, dependency compromise, unsafe autonomy, ambiguous effects, denial of service, telemetry leakage, and operator error. Map mitigations to deterministic enforcement.

### 3. Build supply-chain evidence

Use pinned/locked dependencies, vulnerability and license policy, SBOM, isolated build, provenance/attestation, signing where applicable, secret scanning, code review, protected branches, and artifact hash verification. Record waivers with owner and expiry.

### 4. Verify release and migration behavior

Run quality, security, schema/contract, compatibility, upgrade/downgrade, backup/restore, rollback, performance/capacity, and agent safety/recovery tests against the release candidate and production-like environment.

### 5. Design progressive delivery

Specify dark launch, shadow, internal cohort, design partner, canary, staged percentage/segment ramp, or regional rollout. Define exposure unit, assignment stability, guardrails, sample/data-quality checks, approval gates, pause/rollback thresholds, and maximum blast radius.

### 6. Prepare operations and authorization

Confirm ownership, on-call, dashboards, alerts, runbooks, change window, communications, support, incident command, kill switch, data handling, and production-readiness approvals. Separate deployment permission from effect authorization.

### 7. Execute, observe, and close the release

Record artifact/config versions, rollout events, guardrail state, interventions, incidents, rollback or completion decision, and residual risks. Feed release findings into tests, threat model, requirements, tools, and future gates.

## Output contract

Return a **Secure Release Evidence Package** with:

1. exact release object, environments, identities, and trust boundaries;
2. threat/misuse update and enforced mitigations;
3. dependency, SBOM, provenance, signing/hash, secret, and waiver evidence;
4. release-candidate, migration, compatibility, backup, and rollback verification;
5. progressive-delivery ramp with guardrails and blast-radius limits;
6. operations, support, incident, and authorization readiness;
7. rollout observation and keep/pause/revert decision record;
8. post-release prevention and lifecycle updates.

## Common failures

- **deployment as release proof:** Treating “it deployed” as evidence of provenance, behavior, migration safety, guardrails, operations, or rollback.
- **feature flag as authorization:** Assuming a targeting flag replaces server-side permission, approval, or effect policy.
- **rollback plan never exercised:** Documenting reversion without verifying artifact, schema, state, dependency, and operator behavior under rollback.

## References

- [Secure Sdlc Threat Model](references/secure-sdlc-threat-model.md)
- [Supply Chain Provenance](references/supply-chain-provenance.md)
- [Progressive Delivery Release](references/progressive-delivery-release.md)
- [Rollback And Release Evidence](references/rollback-and-release-evidence.md)

## Shared references

- Autonomy And Exposure Ladder (canonical repository reference library: autonomy-and-exposure-ladder.md)
- Lifecycle Evidence And Readiness (canonical repository reference library: lifecycle-evidence-and-readiness.md)
- Agent Mediated Product Operating Model (canonical repository reference library: agent-mediated-product-operating-model.md)
- Evidence And Confidence (canonical repository reference library: evidence-and-confidence.md)
- Field-Learning and Full-Lifecycle Vocabulary (canonical repository reference library: field-lifecycle-vocabulary.md)
