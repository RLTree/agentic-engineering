# Traceability, verification, and validation

Traceability connects why the product exists to what is built, how it is tested, what happens in operation, and when assumptions change. Verification asks whether artifacts satisfy specified requirements; validation asks whether the resulting system meets stakeholder need in context.

## Vocabulary
- **bidirectional trace:** Link from need/claim to downstream artifacts and back from artifact/evidence to its justification.
- **verification:** Objective evidence that a specified requirement or artifact criterion is met.
- **validation:** Evidence that the system supports intended outcomes and use in representative context.
- **coverage gap:** Need, requirement, risk, effect or lifecycle obligation lacking implementation/evidence—or an artifact lacking justification.
- **trace debt:** Stale, ambiguous or missing links that make change impact and assurance unreliable.

## Decision procedure
1. Assign stable IDs to stakeholder needs, mission threads, risks, requirements, architecture decisions, code/config, tests/evals, telemetry, releases, field observations and retirement obligations.
2. Create typed links such as derives, satisfies, verifies, validates, mitigates, monitors, supersedes, invalidates and retires.
3. Define verification method and acceptance evidence for each requirement before implementation.
4. Map validation evidence to representative outcomes, users and operating conditions; include human effort and adverse effects.
5. Automate structural coverage checks and periodically sample semantic correctness.
6. Use traces for change impact: update or invalidate linked artifacts and evidence on material change.

## Decision table

| Claim | Verification evidence | Validation evidence |
|---|---|---|
| Tool schema rejects invalid action | Contract/property tests | Field reduction in malformed/review burden |
| Loop stops on budget | State-machine tests | Real task completion without thrash |
| Service meets SLO | Load/fault/monitor checks | Users achieve outcome under representative load |
| Approval protects high-risk effect | Policy tests | Reviewers catch errors without unacceptable fatigue |

## Evidence obligations
- Traceability is selective and decision-relevant; do not create every possible link.
- Field evidence can invalidate a requirement or architecture assumption, not merely add a bug.
- A passed test references exact version/artifact/environment.
- Coverage dashboards distinguish link presence from semantic adequacy.

## Review questions
1. Which need or risk justifies this implementation?
2. What requirement has no credible validation in real context?
3. What artifact changes when this field observation arrives?
4. Can a release claim be reconstructed without chat history?

## Failure patterns
- Trace matrix theater: links exist but carry no meaning or updates.
- Verification=validation confusion: passing tests treated as proof of product value.
- Orphan implementation: code or telemetry with no requirement/risk/outcome link.

## Research basis

Grounded in requirements and lifecycle standards, post-deployment monitoring, and assurance practice [R75] [R83] [R84] [R85].
