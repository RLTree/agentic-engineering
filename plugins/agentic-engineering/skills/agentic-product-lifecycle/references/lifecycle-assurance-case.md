# Lifecycle assurance case

An assurance case is a structured argument that the product is fit for a bounded purpose under stated conditions. It links claims to evidence and makes counterevidence, uncertainty, authority, and expiry reviewable.

## Vocabulary
- **top claim:** The bounded proposition whose acceptance enables a decision.
- **subclaim:** A necessary quality, safety, value, or operational proposition supporting the top claim.
- **defeater:** Evidence or condition that would invalidate or weaken a claim.
- **assumption ledger:** Conditions accepted temporarily and the evidence/revisit trigger for each.
- **confidence debt:** Risk created when a decision outruns the strength or coverage of its evidence.

## Decision procedure
1. Write the top claim with exact users, tasks, data, effects, scale, environment, and version.
2. Decompose it into value, workflow fit, functional behavior, quality attributes, security/privacy, effect safety, operability, and lifecycle continuity.
3. Attach evidence items with provenance, recency, operating conditions, strength, and limitations.
4. List defeaters, counterevidence, excluded segments, transfer assumptions, and evidence expiry.
5. Name the human authority and pass/conditional/hold/revert decision rule; record residual risk and follow-up evidence.

## Decision table

| Evidence state | Disposition | Example |
|---|---|---|
| Direct and representative | May support pass | Bounded field outcome plus trajectory/effect evidence |
| Strong but transferred | Conditional pass | Comparable environment with explicit transfer assumptions |
| Proxy only | Hold or narrow | Synthetic benchmark for real workflow value |
| Contradictory/invalid | Revert, redesign, or collect new evidence | Guardrail regression or broken instrumentation |

## Evidence obligations
- Claims must be falsifiable and narrower than the artifact name or marketing promise.
- Evidence must identify the version and operating conditions actually exercised.
- Counterevidence and missing populations are first-class, not buried in notes.
- A passed assurance case expires on material model, tool, data, workflow, architecture, scale, or policy change.

## Review questions
1. What exactly are we claiming, and where does the claim stop?
2. Which evidence observes the actual outcome rather than a convenient proxy?
3. What is the strongest defeater?
4. Who is authorized to accept the residual uncertainty?

## Failure patterns
- Assurance by volume: many tests that do not address the consequential claim.
- Unbounded claims: evidence from a narrow cohort generalized to all users and tasks.
- Static safety case: no expiry or feedback from incidents, drift, or field learning.

## Research basis

Synthesizes systems assurance, requirements traceability, post-deployment monitoring, and production readiness [R75] [R84] [R85] [R102].
