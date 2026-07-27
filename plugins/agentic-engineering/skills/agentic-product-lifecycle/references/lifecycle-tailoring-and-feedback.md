# Lifecycle tailoring and feedback

Tailor rigor to risk and uncertainty while preserving every consequential decision and feedback path. Fast work comes from small reversible commitments and rapid evidence, not from deleting controls invisibly.

## Vocabulary
- **tailoring:** Deliberate adaptation of lifecycle activities, artifacts, depth, and authority to context.
- **revisit trigger:** Observable condition that reopens a prior decision.
- **evidence cadence:** Frequency at which evidence is reviewed, refreshed, or allowed to expire.
- **change impact analysis:** Trace-based assessment of downstream and upstream consequences of a proposed change.
- **learning backlog:** Ranked uncertainties and evidence tasks, distinct from a feature backlog.

## Decision procedure
1. Profile consequence, novelty, irreversibility, scale, regulatory exposure, dependency risk, and uncertainty.
2. For each lifecycle decision, select minimum artifact, evidence strength, reviewer, and cadence.
3. Record omissions or combinations explicitly with rationale and triggers.
4. Define feedback edges from field observations, experiments, incidents, support, drift, and maintenance to requirements, architecture, tests, policies, and retirement.
5. At each review, update the decision/evidence graph, not only the delivery plan.

## Decision table

| Risk profile | Tailoring stance | Evidence cadence |
|---|---|---|
| Low consequence, reversible, familiar | Combine artifacts; automate checks | Per change or release |
| Novel workflow or model behavior | Prototype and field-learn early | Per cohort/ramp |
| High consequence or regulated | Independent review and stronger assurance | Gate plus continuous monitoring |
| Long-lived or dependency-heavy | Deep maintenance/retirement planning | Periodic health and expiry review |

## Evidence obligations
- Tailoring decisions are themselves documented and reviewable.
- Every omitted control has compensating evidence or an accepted residual risk.
- Revisit triggers are observable: version change, workload drift, incident, guardrail, cost, scale, or dependency change.
- Feedback may invalidate upstream decisions; schedule and ownership must allow rework.

## Review questions
1. Which control adds decision value, and which is ceremony?
2. What risk increases because we combined or deferred this work?
3. Which production signal maps to each major assumption?
4. How quickly can the plan change when evidence contradicts it?

## Failure patterns
- Risk laundering: labeling work “agile” to avoid explicit authority or evidence.
- Fixed gate set: identical process for a typo and a high-impact autonomous effect.
- Feedback without capacity: observations are collected but no owner or budget exists to change the system.

## Research basis

Supported by lifecycle-tailoring standards, agile service guidance, SRE feedback systems, and agent-improvement practice [R71] [R83] [R84] [R87] [R90].
