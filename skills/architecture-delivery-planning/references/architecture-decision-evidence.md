# Architecture decision evidence

An architecture decision record should expose the decision context, alternatives, evidence and consequences while it is still possible to disagree. It should also declare what field or operational evidence will reopen the decision.

## Vocabulary
- **ADR:** Versioned record of a consequential architecture decision.
- **decision status:** Proposed, accepted, conditional, superseded, deprecated or rejected.
- **evidence link:** Reference to scenario, experiment, benchmark, incident, field observation or constraint supporting the choice.
- **reversibility:** Cost, time, migration and risk required to undo or replace the decision.
- **fitness function:** Automated or reviewable signal that the architecture continues to satisfy a driver.

## Decision procedure
1. State context, decision question, scope, constraints, drivers and deadline.
2. Describe at least two viable alternatives plus “delay/do nothing” when meaningful.
3. Compare against quality scenarios, security, operations, cost, skills, dependencies, migration and retirement.
4. Attach evidence with conditions, limitations and provenance; separate fact, inference and preference.
5. Record decision, authority, consequences, follow-up experiments, fitness signals and revisit triggers.
6. Supersede rather than rewrite history; link outcomes and lessons after operation.

## Decision table

| Evidence type | Use | Caution |
|---|---|---|
| Scenario analysis | Tradeoff reasoning | Depends on assumption quality |
| Prototype/benchmark | Technical uncertainty | May omit workflow/operations |
| Incident/field trace | Real mechanism | Selection and confounding |
| Standard/constraint | Non-negotiable boundary | Version and applicability |
| Cost model | Economic comparison | Include lifecycle and uncertainty |

## Evidence obligations
- Decision authority and dissent are visible.
- Evidence applies to the selected environment, scale and versions—or transfer is explicit.
- Consequences include organizational and lifecycle costs, not only technical benefits.
- Revisit triggers are observable and assigned.

## Review questions
1. What alternative would a skeptical reviewer prefer and why?
2. Which evidence could falsify this decision?
3. What future migration or retirement cost are we creating?
4. How will operation reveal that the tradeoff has changed?

## Failure patterns
- ADR as changelog: records what was done but not why.
- Evidence-free preference: “industry standard” substitutes for local scenarios.
- History rewriting: old rationale edited after outcomes are known.

## Research basis

Based on architecture tradeoff methods, lifecycle traceability, and evidence-calibrated decisions [R84] [R88] [R89].
