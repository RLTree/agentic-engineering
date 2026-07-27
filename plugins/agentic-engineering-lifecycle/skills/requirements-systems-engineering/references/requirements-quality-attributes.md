# Requirements and quality attributes

Requirements translate stakeholder needs and operational scenarios into bounded, verifiable claims. Quality attributes must be scenario-based because words such as secure, reliable, scalable, safe, or usable are not testable by themselves.

## Vocabulary
- **stakeholder need:** Outcome or constraint from a stakeholder perspective, not yet a solution requirement.
- **system requirement:** Necessary, feasible, unambiguous, singular, traceable and verifiable statement about behavior or quality.
- **quality-attribute scenario:** Source, stimulus, environment, artifact, response and response measure.
- **derived requirement:** Requirement created by architecture, interface, safety, security, operations, or lifecycle constraints.
- **verification method:** Inspection, analysis, demonstration, test, field observation, or mixed evidence used to judge satisfaction.

## Decision procedure
1. Trace stakeholder outcomes and mission threads into functional behavior, effects, interfaces, data, human roles, constraints and quality attributes.
2. Write each requirement with conditions, response, measurable threshold, rationale, priority, owner, verification method, and lifecycle links.
3. Create quality-attribute scenarios for performance, reliability, availability, resilience, security, privacy, safety, usability, accessibility, observability, maintainability, portability, cost, and sustainability as relevant.
4. Resolve conflicts through explicit tradeoff and decision authority; avoid impossible simultaneous maxima.
5. Review feasibility, necessity, ambiguity, testability, singularity, consistency, and traceability; baseline only what is supported.

## Decision table

| Weak phrase | Scenario transformation | Evidence |
|---|---|---|
| “fast” | Under workload X, p95 response ≤Y with queue ≤Z | Load/performance test |
| “reliable” | Given dependency failure, preserve state and recover within RTO/RPO | Fault/recovery test |
| “safe” | For effect class H, deny outside envelope and require approval | Policy/effect test |
| “usable” | Target role completes task with bounded time/error/review burden | Representative usability evidence |

## Evidence obligations
- Requirements distinguish desired outcome, system behavior, control, and evidence.
- Thresholds include population/environment and acceptable degradation.
- Non-functional qualities map to architecture mechanisms, tests, operations and field guardrails.
- Requirements carry version, source, rationale and change impact.

## Review questions
1. Can two reviewers reach the same pass/fail conclusion?
2. Does this requirement specify a product outcome, a design choice, or both?
3. Which stakeholder or lifecycle obligation justifies it?
4. What quality tradeoff is hidden by an absolute adjective?

## Failure patterns
- Adjective requirements: “robust,” “enterprise,” or “safe” with no scenario.
- Implementation masquerading as need: premature technology constraints.
- Unverifiable aspiration: no condition, measure, method, or owner.

## Research basis

Uses ISO/IEC/IEEE requirements engineering and quality model guidance plus QAW/ATAM [R85] [R86] [R88] [R89].
