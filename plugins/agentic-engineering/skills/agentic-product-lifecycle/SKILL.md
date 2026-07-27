---
name: agentic-product-lifecycle
description: "Use when one product decision spans discovery, delivery, operation, experimentation, maintenance, or retirement."
---

# Agentic Product Lifecycle

## Core principle

Treat the lifecycle as a continuous, risk-tailored evidence system rather than a sequence of handoffs. Every consequential claim must have an owner, evidence, a decision rule, a durable artifact, and a path for field observations to revise earlier assumptions.

## Workflow

### 1. Frame the product and operating context

State the user and organizational outcomes, system boundary, consequential effects, regulatory or contractual constraints, expected service life, affected stakeholders, and the decision currently at stake. Separate current evidence from assumptions and commitments.

### 2. Tailor the lifecycle

Map the work across discovery, concept and feasibility, requirements and systems engineering, architecture and planning, construction and quality, secure release, production readiness and SRE, experimentation, maintenance, and retirement. Combine or deepen stages according to risk; never treat the map as a mandatory waterfall.

### 3. Build the decision–evidence graph

For each major decision, record the claim, owner, alternatives, evidence required, uncertainty, approval authority, irreversible effects, readiness criterion, revisit trigger, and downstream artifacts. Link requirements to architecture, implementation, verification, operations, field evidence, and retirement obligations.

### 4. Assign agent and human decision rights

Use agents for synthesis, traceability, option generation, implementation, test generation, evidence assembly, and anomaly discovery. Keep value judgments, risk acceptance, stakeholder tradeoffs, policy interpretation, and irreversible or high-impact approvals with named humans.

### 5. Plan thin slices and authentic-use learning

Prefer the smallest end-to-end slice that can test the highest-risk assumptions. Define its operating envelope, autonomy level, instrumentation, cohort, success and guardrail metrics, rollback, and evidence-to-change review before broad implementation.

### 6. Establish assurance and operating cadence

Define architecture reviews, requirement baselines, quality and security gates, release evidence, production-readiness review, SLO/error-budget policy, experiment review, maintenance health review, and retirement readiness. Specify which gates are blocking and which are advisory.

### 7. Produce a revisable plan

State the current lifecycle posture, missing evidence, next decision, next smallest slice, owners, dependencies, and stop/pivot/escalation triggers. Preserve a durable evidence ledger so later agents do not reconstruct decisions from chat history.

## Output contract

Return a **Lifecycle Assurance Plan** with:

1. product/system context, stakeholders, outcomes, constraints, and current decision;
2. tailored lifecycle map with active, upcoming, and intentionally deferred stages;
3. decision-rights matrix for humans, agents, services, and governance authorities;
4. decision–evidence–artifact traceability graph;
5. highest-risk assumptions and thin-slice learning plan;
6. readiness gates for quality, security, release, operations, experimentation, and retirement;
7. field-evidence feedback paths and change-control policy;
8. owners, cadence, residual risks, and explicit revisit or termination triggers.

## Common failures

- **lifecycle as waterfall:** Treating stages as one-way approvals hides feedback and encourages premature specification. Tailor and iterate around the riskiest decision.
- **artifact handoff without decision continuity:** Documents exist but claims, evidence, owners, and revisit triggers are disconnected. Build traceability across the lifecycle.
- **agent authority by convenience:** Letting an agent silently accept risk or redefine product value. Name human decision rights and approval boundaries.

## References

- [Lifecycle Stage Map](references/lifecycle-stage-map.md)
- [Lifecycle Assurance Case](references/lifecycle-assurance-case.md)
- [Agent Human Decision Rights](references/agent-human-decision-rights.md)
- [Lifecycle Tailoring And Feedback](references/lifecycle-tailoring-and-feedback.md)

## Shared references

- Full Lifecycle Map (canonical repository reference library: full-lifecycle-map.md)
- Lifecycle Evidence And Readiness (canonical repository reference library: lifecycle-evidence-and-readiness.md)
- Agent Mediated Product Operating Model (canonical repository reference library: agent-mediated-product-operating-model.md)
- Evidence And Confidence (canonical repository reference library: evidence-and-confidence.md)
- Field-Learning and Full-Lifecycle Vocabulary (canonical repository reference library: field-lifecycle-vocabulary.md)
