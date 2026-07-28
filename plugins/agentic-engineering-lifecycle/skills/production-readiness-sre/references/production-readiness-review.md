# Production readiness review

A production-readiness review challenges whether the service can be owned, observed, scaled, secured, recovered and evolved under representative load and failure. It is a risk review with accountable follow-through, not a launch form.

## Vocabulary
- **PRR:** Structured review of service readiness before or during production exposure.
- **service owner:** Named team/person accountable for operation, SLOs, incidents, changes and lifecycle health.
- **runbook:** Actionable diagnostic/recovery procedure linked to signals and authority.
- **game day:** Controlled exercise of failure and response in a realistic environment.
- **operational debt:** Known missing control, automation, capacity, documentation or ownership that raises ongoing risk.

## Decision procedure
1. State service boundary, users/outcomes, operating envelope, criticality, effect classes, dependencies, scale and launch/ramp decision.
2. Review architecture/state, SLOs, capacity, dependencies, observability, alerts, dashboards, runbooks, on-call/support, security/privacy, data, deployment/rollback, incident and disaster recovery.
3. Exercise representative load, saturation, dependency failure, cancellation/restart, ambiguous effects, rollback and operator workflows.
4. Record blockers, conditional risks, owners, due dates, compensating controls, and authority.
5. Launch progressively with heightened observation; hold a post-launch review and feed findings into requirements, architecture, tests and operations.

## Decision table

| Area | Ready evidence | Blocker example |
|---|---|---|
| Ownership | on-call/support/escalation and service catalog | no accountable responder |
| Reliability | SLO, error budget, tested failure/recovery | unknown failure semantics |
| Capacity | representative load and dependency budgets | unbounded queue/fan-out |
| Observability | actionable signals and trace completeness | cannot identify effect/status/version |
| Release | canary, rollback, migration rehearsal | irreversible untested change |

## Evidence obligations
- PRR depth is tailored to criticality, novelty and irreversibility.
- Conditional launch risks have explicit blast-radius limits and expiry.
- Alerts map to user impact or actionable failure, not arbitrary resource thresholds alone.
- Field and incident evidence can reopen readiness findings.

## Review questions
1. Who owns this at 03:00 during a partial provider failure?
2. Can operators determine authoritative state and effect outcome?
3. What happens at saturation or dependency quota exhaustion?
4. Which known debt makes broader exposure unsafe?

## Failure patterns
- Checklist launch: all boxes checked without executable evidence.
- Hero dependency: readiness assumes one expert is available.
- Post-launch amnesia: findings never change system controls or backlog priority.

## Research basis

Grounded in Google SRE production readiness and reliable launch guidance [R102] [R106].
