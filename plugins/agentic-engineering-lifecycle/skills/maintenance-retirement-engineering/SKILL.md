---
name: maintenance-retirement-engineering
description: "Use when sustaining, migrating, deprecating, or retiring an agentic product, dependency, model, tool, or data asset."
---

# Maintenance & Retirement Engineering

## Core principle

Maintenance and retirement are designed lifecycle states, not residual work. Monitor product value and system health, control compatibility and debt, communicate deprecation, migrate users and data, disable before deleting, verify the absence of hidden dependencies, and preserve the evidence needed to explain and reverse decisions.

## Workflow

### 1. Assess continuing value and health

Review user need, task volume and distribution, outcome quality, reliability, support burden, security exposure, dependency status, cost, operator effort, model/harness drift, and alternative services. Segment by users who would be harmed by removal.

### 2. Classify sustainment work

Separate corrective, adaptive, perfective, preventive, security, compliance, model/eval refresh, data/schema, and operational work. Prioritize by consequence, recurrence, error budget, vulnerability, and lifecycle risk rather than visibility alone.

### 3. Plan compatibility and evolution

Define versioning, contract tests, schema/data migration, model/tool replacement, feature-flag cleanup, dependency upgrades, deprecation warnings, support windows, and rollback. Avoid indefinite dual paths without an exit criterion.

### 4. Decide deprecate, replace, consolidate, or retire

State evidence, alternatives, affected stakeholders, user-need continuity, authority, timing, economic/security rationale, and conditions that would reverse or delay the decision.

### 5. Execute migration and communication

Inventory consumers, APIs, agents, jobs, data, credentials, dashboards, alerts, runbooks, documentation, contracts, and ownership. Provide lead time, migration tooling, support, status visibility, and explicit data handling.

### 6. Decommission safely

Stop new adoption, shadow or redirect traffic, disable effects and writes, observe a watch window, archive required evidence, revoke access and secrets, remove dependencies and monitoring, then delete resources. Test fallback and restoration before irreversible deletion.

### 7. Verify closure and capture learning

Confirm user journeys, data retention/disposal, financial and security closure, absence of traffic/dependencies, documentation updates, ownership transfer, and lessons for future architecture and lifecycle decisions.

## Output contract

Return a **Maintenance, Deprecation, and Retirement Plan** with:

1. continuing-value and health assessment;
2. sustainment backlog classified by lifecycle risk;
3. compatibility, versioning, model/tool/dependency, and migration strategy;
4. deprecate, replace, consolidate, or retire decision with authority and reversal criteria;
5. consumer/user inventory, communication, support, and lead-time plan;
6. disable-observe-delete sequence with fallback and evidence preservation;
7. data, credential, contract, monitoring, cost, and ownership closure checks;
8. post-retirement learning and lifecycle updates.

## Common failures

- **delete before disable and observe:** Removing a service or data path before proving traffic, dependencies, fallback, and restoration behavior.
- **deprecation without user continuity:** Announcing an end date without preserving the user need, migration path, support, data rights, or API lead time.
- **maintenance as unbounded backlog:** Accumulating debt and compatibility paths without health signals, risk prioritization, ownership, or exit criteria.

## References

- [Sustainment Debt Dependencies](references/sustainment-debt-dependencies.md)
- [Deprecation Migration](references/deprecation-migration.md)
- [Safe Decommissioning](references/safe-decommissioning.md)
- [Retirement Evidence Continuity](references/retirement-evidence-continuity.md)

## Shared references

- Full Lifecycle Map (canonical repository reference library: full-lifecycle-map.md)
- Lifecycle Evidence And Readiness (canonical repository reference library: lifecycle-evidence-and-readiness.md)
- Controlled Field Learning System (canonical repository reference library: controlled-field-learning-system.md)
- Decision Records (canonical repository reference library: decision-records.md)
- Field-Learning and Full-Lifecycle Vocabulary (canonical repository reference library: field-lifecycle-vocabulary.md)
