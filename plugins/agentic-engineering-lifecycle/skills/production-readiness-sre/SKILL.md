---
name: production-readiness-sre
description: "Use when deciding whether an agentic service is operable, reliable, supportable, and ready for production exposure."
---

# Production Readiness & SRE

## Core principle

Production readiness is evidence that the service can be owned, observed, changed, degraded, recovered, and supported within agreed reliability and risk boundaries. Reliability targets must derive from user outcomes and drive release, experimentation, and maintenance decisions.

## Workflow

### 1. Define service ownership and critical journeys

Name service owners, on-call and escalation, users and downstreams, critical mission threads, operating envelope, dependencies, data/effects, failure consequences, and acceptable degraded modes.

### 2. Define SLIs, SLOs, and error-budget policy

Choose user-relevant availability, correctness, latency, freshness, task-success, effect-integrity, or recovery indicators. Specify windows, exclusions, segmentation, data quality, targets, and what budget consumption changes about release and experiment policy.

### 3. Review architecture and dependencies for operations

Assess failure domains, redundancy, capacity, queue/backpressure behavior, timeouts, retries, idempotency, graceful degradation, dependency contracts, disaster recovery, state restoration, and kill/containment mechanisms.

### 4. Verify observability and response

Require actionable dashboards, symptoms before causes, trace/effect correlation, data-quality monitors, privacy-safe logs, alerts tied to user impact, runbooks, access, tooling, and rehearsal of likely incidents.

### 5. Assess capacity, performance, and cost

Model normal, peak, burst, degraded, and recovery load; model token/tool/provider quotas and cost; define saturation signals, admission control, load shedding, queue limits, and scaling constraints.

### 6. Run resilience and incident-learning exercises

Test dependency loss, model/tool degradation, bad rollout, stale state, ambiguous effects, permission failures, telemetry loss, and operator intervention. Use blameless learning to improve controls and reduce recurrence.

### 7. Make a readiness decision

Approve, conditionally approve, narrow the envelope, require remediation, or block. Record evidence, waivers, owners, dates, ramp constraints, revisit triggers, and the first post-launch learning review.

## Output contract

Return a **Production Readiness and Reliability Plan** with:

1. ownership, critical journeys, operating envelope, dependencies, and failure consequences;
2. SLIs, SLOs, error budgets, segmentation, and policy actions;
3. capacity, saturation, backpressure, degradation, and cost plan;
4. observability, alerting, runbook, access, and response evidence;
5. resilience, disaster recovery, state/effect recovery, and incident exercises;
6. production-readiness findings, waivers, and blocking conditions;
7. progressive-launch and post-launch learning constraints;
8. approve, conditional, narrow, remediate, or block decision.

## Common failures

- **monitoring as dashboard inventory:** Counting logs and charts without user-relevant indicators, action thresholds, ownership, or response paths.
- **slo without policy:** Publishing a target that does not change release, experiment, prioritization, or escalation behavior.
- **readiness review at the finish line:** Discovering operability, capacity, dependency, or recovery gaps only after implementation is complete.

## References

- [Production Readiness Review](references/production-readiness-review.md)
- [Slo Error Budget](references/slo-error-budget.md)
- [Incident Resilience Learning](references/incident-resilience-learning.md)
- [Capacity Dependency Operations](references/capacity-dependency-operations.md)

## Shared references

- [Lifecycle Evidence And Readiness](../../references/lifecycle-evidence-and-readiness.md)
- [Controlled Field Learning System](../../references/controlled-field-learning-system.md)
- [Metric And Causal Evidence](../../references/metric-and-causal-evidence.md)
- [Agent Mediated Product Operating Model](../../references/agent-mediated-product-operating-model.md)
- [Field-Learning and Full-Lifecycle Vocabulary](../../references/field-lifecycle-vocabulary.md)

## Version 3 operational learning

Production readiness includes continuous security monitoring, product-fitness evidence quality, repair-loop budgets, and a governed route from incidents and near misses into evals, tools, policies, architecture, or retirement. Track supervisory work and intervention burden alongside service metrics when agents are part of the operating system.
