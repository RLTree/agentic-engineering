# Ramp, holdout, and guardrails

Progressively increase exposure only after health, validity, safety and product evidence is sufficient. Holdouts provide counterfactual and long-term learning; guardrails enforce product and system constraints.

## Vocabulary
- **ramp:** Stepwise increase in treatment exposure.
- **holdout:** Population retained on baseline/control for comparison, sometimes long term.
- **A/A test:** No-treatment-difference test used to validate assignment, telemetry and false-positive behavior.
- **ramp gate:** Decision checkpoint with predeclared evidence and authority.
- **kill switch:** Fast, tested mechanism to stop exposure/effects independent of the experimental analysis pipeline.

## Decision procedure
1. Define exposure unit, eligibility, exclusions, ramp steps, observation windows, holdout, blast-radius budget and authority.
2. Validate assignment/exposure telemetry with A/A or dry run; define sample-ratio and data-quality alerts.
3. Attach service health, safety/security/privacy, severe-error, human-burden and product guardrails to every step.
4. Start with shadow/recommendation/approval-gated exposure where it can answer the question with lower risk.
5. At each gate, inspect versions, cohort balance, telemetry quality, incidents/near misses, segment outcomes and operational capacity.
6. Ramp, hold, narrow, revert or stop; preserve long-term holdout where delayed effects justify it; clean up treatment paths after decision.

## Decision table

| Gate result | Action | Reason |
|---|---|---|
| Validity failure | Hold/repair | Outcome estimate uninterpretable |
| Hard guardrail breach | Stop/revert | Risk overrides product result |
| Mixed segment result | Narrow/investigate | Average hides heterogeneity |
| Healthy but underpowered | Hold | Avoid premature conclusion |
| Supported value and controls | Next bounded ramp | Evidence earns exposure |

## Evidence obligations
- Kill and rollback paths are tested before first consequential exposure.
- Observation windows reflect traffic, delayed effects and task cycles.
- Holdout eligibility/ethics and user obligations are reviewed.
- Feature flag context is observable but never substitutes for authorization.

## Review questions
1. What evidence is required before the next percentage, not just the next date?
2. Which delayed or rare effects require a persistent holdout?
3. Can rollback stop effects and preserve state integrity?
4. Who can stop the experiment outside business hours?

## Failure patterns
- Calendar ramp: exposure increases automatically without evidence.
- Guardrail theater: alerts exist but no authority/action rule.
- Control erosion: treatment leaks or baseline changes silently.

## Research basis

Uses SRE canarying, safe deployment, experimentation validity, and OpenFeature context guidance [R79] [R80] [R107] [R112] [R115].
