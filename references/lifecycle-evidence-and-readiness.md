# Lifecycle evidence and readiness

A readiness gate is a decision rule tied to a claim, not a document checklist. The goal is to prevent unsupported confidence while preserving fast, reversible learning.

## Readiness record

For every consequential transition or ramp, record:

1. **Decision:** what will change if the gate passes.
2. **Claim:** the proposition believed to be true.
3. **Operating conditions:** users, tasks, data, tools, environments, effect types, scale, and exclusions for which the claim applies.
4. **Evidence:** direct observations, tests, analyses, reviews, and provenance.
5. **Strength:** constraint/standard, supported practice, emerging evidence, or directional signal.
6. **Counterevidence and uncertainty:** known failures, missing segments, confounders, and transfer assumptions.
7. **Owner and authority:** who assembles evidence, who challenges it, who accepts residual risk.
8. **Decision rule:** pass, conditional pass, hold, narrow, revert, pivot, or stop.
9. **Expiration and revisit trigger:** time, version, workload change, incident, metric drift, or dependency change.

## Evidence ladder

Prefer evidence closest to the consequential claim:

1. verbal assertion or model self-report;
2. source inspection and static analysis;
3. unit/property tests;
4. integration and contract tests;
5. fault, recovery, concurrency, and security tests;
6. end-to-end evidence in the packaged deployment;
7. shadow or recommendation-only evidence on representative work;
8. controlled approval-gated or bounded-autonomy exposure;
9. field outcomes with representative traces and qualitative evidence;
10. causal evidence from a valid randomized or quasi-experimental design when the claim is causal.

Higher is not universally better. Match evidence cost and risk to the decision. A reversible copy change may not need a field experiment; an autonomous financial or security effect cannot rely on an offline benchmark alone.

## Gate types

- **Discovery confidence:** representative problem evidence exists; the team is not merely collecting feature requests.
- **Feasibility:** the hardest technical, workflow, safety, legal, and operational assumptions have discriminating evidence.
- **Requirements baseline:** operational conditions, quality attributes, effects, and verification methods are testable and traceable.
- **Architecture commitment:** major tradeoffs and irreversible choices are supported by scenarios and alternatives.
- **Construction acceptance:** implementation and exact delivery artifact satisfy acceptance criteria with reproducible evidence.
- **Security and release:** threats, permissions, provenance, rollback, and progressive exposure are controlled.
- **Production readiness:** SLOs, capacity, dependencies, observability, operations, incident response, and ownership are adequate.
- **Experiment validity:** assignment, telemetry, sample, guardrails, analysis, and decision thresholds are valid.
- **Maintenance/retirement:** continuing value or removal safety is supported by usage, dependency, migration, and closure evidence.

## Anti-checklist rule

A complete template does not prove a claim. Reviewers should ask:

- What decision would change if this evidence were different?
- Which operating conditions were actually exercised?
- What could make the result transfer poorly?
- What representative failure, intervention, near miss, or success is missing?
- Is the system measuring the outcome or merely activity around it?
- Can a favorable metric be gamed while user or system harm rises?
- Who has authority to accept the residual risk?

## Research basis

This contract combines assurance-case reasoning, systems and requirements
traceability, SRE launch and error-budget practice, secure release evidence, and
monitoring questions. NIST AI 800-4 is descriptive rather than a prescribed
readiness method (`F-NIST-AI800-4`). Historical lineage: [R75] [R76] [R83]
[R84] [R85] [R95] [R102] [R103] [R106].
