# Incident, resilience, and learning

An incident is a disruption or credible near miss to user outcome, safety, security, privacy, reliability or operations. Response restores control; learning changes the system so recurrence is less likely or less harmful.

## Vocabulary
- **incident command:** Explicit roles and coordination for response, communication and decisions.
- **near miss:** Condition that could have caused material harm but was interrupted or avoided.
- **resilience:** Ability to anticipate, withstand, recover and adapt while preserving critical outcomes.
- **contributing factor:** Condition that shaped the event without reducing analysis to one root cause.
- **corrective action:** Owned, prioritized system change with verification and closure evidence.

## Decision procedure
1. Declare based on user/effect/safety impact or credible risk; assign commander, operations, communications and subject-matter roles.
2. Stabilize: stop/ramp down effects, preserve evidence, establish authoritative state, reconcile ambiguity, protect users and communicate.
3. Build a timeline from traces, changes, alerts, decisions, interventions and external dependencies.
4. Analyze contributing technical, process, interface, organizational and incentive conditions; include successful adaptations.
5. Create actions at prevention, detection, containment, recovery and learning layers; link to tests/evals, tools, policies, architecture and field monitors.
6. Verify actions, share learning, update PRR/runbooks/SLOs/threat model/requirements, and sample recurrence.

## Decision table

| Phase | Priority | Evidence |
|---|---|---|
| Detect/declare | user/effect impact and scope | alerts, support, trace anomaly |
| Stabilize | contain blast radius and ambiguity | kill, rollback, reconcile |
| Understand | timeline and mechanisms | versions, trajectories, decisions |
| Improve | durable controls | tests, tools, architecture, policy |
| Verify | field and exercise closure | game day/monitor/result |

## Evidence obligations
- Preserve blame-aware accountability but avoid incentives that hide reporting.
- Near misses and operator interventions receive proportional analysis.
- Action items have owner, due date, priority, linked risk and verification; “be more careful” is invalid.
- Incident communication includes uncertainty and updates, not false precision.

## Review questions
1. What protected users or prevented a worse outcome?
2. Which control failed, was absent, or was bypassed by incentives?
3. How did human and agent behavior interact?
4. What test or monitor will prove the corrective action works?

## Failure patterns
- Single root cause: complex system reduced to one person or line.
- Postmortem theater: prose without prioritized verified actions.
- Recovery blindness: service restored but ambiguous effects or user harm unresolved.

## Research basis

Grounded in SRE incident management/postmortem culture and agent field-learning practice [R71] [R104] [R105].
