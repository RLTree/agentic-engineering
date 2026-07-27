# Operational concept and mission threads

An operational concept describes the joint human-agent-system environment and lifecycle behavior before implementation. Mission threads exercise end-to-end scenarios across actors, tools, effects, failures, recovery, and operations.

## Vocabulary
- **operational concept:** Narrative and model of how stakeholders and system elements achieve outcomes under real conditions.
- **mission thread:** End-to-end scenario crossing actors/components from trigger to outcome and closure.
- **actor:** Human, agent, service, operator, authority, adversary, or external system with a role.
- **effect boundary:** Point at which the system changes an external state and requires authorization, verification, or reconciliation.
- **off-nominal thread:** Scenario involving denial, ambiguity, degradation, attack, cancellation, timeout, partial failure, or recovery.

## Decision procedure
1. Define system-of-interest, external environment, lifecycle context, stakeholders, outcomes, constraints, and operating envelope.
2. Map actors, responsibilities, information, decisions, handoffs, tools/services, data trust, and effect boundaries.
3. Write nominal threads from trigger through verified outcome, including human work and evidence.
4. Write off-nominal threads for invalid input, policy denial, tool/model failure, ambiguous effects, concurrency, overload, drift, incident, and recovery.
5. Derive functional, quality, interface, security, observability, support, migration, and retirement requirements.
6. Validate threads with representative stakeholders and link them to architecture, tests, field instrumentation and runbooks.

## Decision table

| Thread type | Required content | Derived evidence |
|---|---|---|
| Nominal value | actor, task, decisions, effects, outcome | Acceptance and field-outcome tests |
| Approval/escalation | authority, preview, rationale, timeout | Oversight and workflow tests |
| Failure/recovery | fault, state, retry/reconcile/compensate | Fault and durability tests |
| Operational | deploy, observe, support, incident, rollback | PRR/runbook evidence |
| Retirement | migrate, disable, archive, delete | Closure checklist |

## Evidence obligations
- Threads identify preconditions, postconditions, authoritative state, and evidence of completion.
- Humans are modeled as participants with workload and limitations, not generic approval boxes.
- External effects have identity, status, authorization, idempotency/reconciliation, and recovery.
- The operational concept includes maintenance and retirement, not only first use.

## Review questions
1. Can every actor tell what happens when the agent is wrong or uncertain?
2. Where is authoritative state and who may change it?
3. Which thread crosses the highest-risk effect or dependency?
4. What evidence proves the outcome rather than only task execution?

## Failure patterns
- Chat-flow specification: only messages modeled, not work, effects or operations.
- Nominal-only threads: recovery and denial left to implementation improvisation.
- Invisible human labor: review and cleanup absent from the system model.

## Research basis

Grounded in systems lifecycle and requirements standards plus agent effect/durability practice [R83] [R84] [R85].
