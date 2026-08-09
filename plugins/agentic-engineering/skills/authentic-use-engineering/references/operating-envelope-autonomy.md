# Operating envelope and autonomy

An operating envelope defines where claims, permissions, controls, and evidence apply. Autonomy is promoted only inside that envelope and is demoted when conditions or evidence leave it.

## Vocabulary
- **operating envelope:** Allowed users, tasks, data, tools, environment, effects, scale, time, cost, jurisdictions, and failure tolerance.
- **out-of-envelope condition:** Any observed case not covered by the approved assumptions or controls.
- **autonomy grant:** Scoped authority to decide or act without synchronous approval.
- **effect class:** Category of external change by reversibility, impact, ambiguity, and authorization need.
- **promotion gate:** Evidence and controls required to increase exposure or autonomy.

## Decision procedure
1. Enumerate users/roles, task taxonomy, data classes, tools/dependencies, environments, effect classes, scale, budgets, and jurisdictions.
2. Specify explicit exclusions, denial behavior, escalation owner, and how out-of-envelope cases are detected.
3. Choose replay, observe, shadow, recommend, approval-gated, bounded autonomy, or broader autonomy.
4. Define controls: permissions, schemas, preview, approvals, idempotency, reconciliation, rate/value limits, kill switch, rollback, and incident response.
5. Set promotion/demotion criteria tied to segmented outcomes, interventions, guardrails, data quality, recovery, and version changes.

## Decision table

| Condition | Default response | Evidence needed to expand |
|---|---|---|
| Unknown task/data/effect | Deny or escalate | Representative tests plus field evidence |
| Known low-impact reversible action | Bounded execution | Reliable verification and rollback |
| Ambiguous external outcome | Reconcile; do not blind retry | Effect journal and provider evidence |
| High-impact/irreversible action | Named approval or prohibit | Independent assurance and explicit authority |

## Evidence obligations
- Envelope fields are machine-readable where they govern runtime behavior.
- Findings are labeled with the envelope actually exercised; no automatic generalization.
- Version changes to model, prompt, skill, tool, data, harness or policy trigger review.
- Promotion requires evidence at the current level; commercial pressure is not evidence.

## Review questions
1. What exact conditions make this action authorized and valid?
2. How does the runtime detect and respond to an excluded case?
3. What changes would invalidate prior field evidence?
4. What is the smallest next promotion that answers the decision?

## Failure patterns
- Implicit envelope: “normal use” or “safe tasks” has no operational definition.
- Feature flag as permission: exposure control substitutes for authorization.
- Autonomy ratchet: levels increase but no demotion, expiry, or reauthorization exists.

## Research basis

Based on monitoring questions, autonomy-in-practice guidance, secure capability
controls, and progressive delivery. NIST AI 800-4 is a challenge taxonomy, not a
prescribed operating-envelope method (`F-NIST-AI800-4`). Historical lineage:
[R73] [R75] [R106] [R107] [R115] [R124].
