# Progressive delivery and release

Separate deployment from exposure and authorization. Release incrementally through observable cohorts with predeclared health, product, safety, data-quality and rollback rules.

## Vocabulary
- **deployment:** Making a version available in an environment.
- **exposure:** Routing users/tasks to a capability or variant.
- **authorization:** Permission for a principal to access data or perform an effect.
- **canary:** Small initial production cohort used to compare and detect regressions.
- **progressive delivery:** Controlled increase of exposure based on evidence and automated/manual gates.

## Decision procedure
1. Define exact artifact/config/model/tool versions, target environment, migrations, dependencies and compatibility.
2. Set exposure units, cohorts, order, ramp percentages/time, holdouts/comparators and blast-radius budget.
3. Predeclare release health, SLO, guardrail, product outcome, human-effort and data-quality criteria with owners.
4. Verify rollback/roll-forward, kill switch, feature flag behavior, migration reversibility, effect safety and incident readiness.
5. Deploy dark or shadow where useful, then canary and ramp only after sufficient observation windows and validity checks.
6. Record each gate decision; stop/revert/narrow automatically or through named authority when criteria fail.
7. Clean up flags, old paths, permissions and temporary instrumentation after stabilization.

## Decision table

| Control | Purpose | Not sufficient for |
|---|---|---|
| Feature flag | Exposure/variant control | Authorization or data access |
| Canary | Limit blast radius and compare | Rare/long-term effects alone |
| Blue-green | Fast environment rollback | Irreversible data/effects |
| Shadow traffic | Behavior/latency evidence | User value/adoption |
| Holdout | Counterfactual/long-term effects | All ethical or operational questions |

## Evidence obligations
- Every ramp has observation duration tied to traffic and risk, not arbitrary optimism.
- Guardrails and data-quality checks run before interpreting product wins.
- Release decisions preserve exact versions and cohort assignment.
- Rollback handles state/schema/effect changes, not just binary version.

## Review questions
1. What is the smallest exposure unit that limits harm and contamination?
2. Which metric or incident stops the ramp immediately?
3. Can the change be disabled without losing or corrupting authoritative state?
4. What temporary release mechanism needs an explicit cleanup date?

## Failure patterns
- Deploy=release: all users exposed immediately after build.
- Flag as security boundary: unauthorized calls possible when enabled incorrectly.
- Ramp by calendar: percentages increase without adequate evidence.

## Research basis

Grounded in SRE canary/release practice, safe deployment, Argo Rollouts, Flagger, and OpenFeature [R107] [R108] [R112] [R113] [R114] [R115].
