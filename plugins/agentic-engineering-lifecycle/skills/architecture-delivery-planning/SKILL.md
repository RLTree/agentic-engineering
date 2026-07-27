---
name: architecture-delivery-planning
description: "Use when requirements and uncertainty must become architecture decisions and risk-retiring delivery slices."
---

# Architecture & Delivery Planning

## Core principle

Architecture is a set of consequential tradeoffs under quality and lifecycle constraints; delivery planning should retire uncertainty, not merely schedule features. Use scenario-based analysis, explicit decision records, and thin vertical slices that generate evidence early.

## Workflow

### 1. Establish architectural drivers

Extract business/mission goals, quality-attribute scenarios, constraints, operating envelope, scale, data/effect semantics, security and privacy boundaries, lifecycle horizon, team capabilities, and unresolved risks.

### 2. Generate materially different options

Include simpler and lower-autonomy alternatives. For each option, identify components, state/effect boundaries, dependencies, deployment topology, failure containment, observability, evolution path, and retirement cost.

### 3. Analyze tradeoffs and sensitivity

Walk critical scenarios through each option. Identify risks, sensitivity points, tradeoff points, assumptions, coupling, bottlenecks, recovery behavior, and operational burden. Do not hide incompatible quality goals in a single score.

### 4. Record decisions and reversibility

Create ADRs with context, decision, alternatives, evidence, consequences, owner, reversibility, expiration/revisit trigger, and migration path. Distinguish one-way doors from easily reversible choices.

### 5. Plan risk-retiring vertical slices

Sequence walking skeleton, high-risk integration, end-to-end representative task, effect safety, observability, recovery, security, performance, and authentic-use slices. Each slice must yield a durable artifact and a decision-relevant evidence result.

### 6. Plan dependencies, capacity, and assurance

Map critical path, external contracts, environment/tooling readiness, data acquisition, review authorities, staffing/skills, release and operations work, and evidence gates. Reserve capacity for integration, defects, resilience, and learning.

### 7. Define replanning triggers

Set thresholds for architecture revisit, scope change, envelope narrowing, model/tool replacement, dependency failure, SLO risk, security finding, experiment result, and retirement. Keep the plan synchronized with evidence, not calendar optimism.

## Output contract

Return a **Architecture and Evidence-Driven Delivery Plan** with:

1. architectural drivers and quality-attribute scenarios;
2. materially different options including simpler alternatives;
3. scenario-based tradeoff, sensitivity, risk, and operational-burden analysis;
4. ADRs with evidence, consequences, reversibility, and revisit triggers;
5. risk-ranked thin vertical slices and walking skeleton;
6. dependency, critical-path, capacity, and assurance map;
7. field-learning, release, operations, maintenance, and retirement implications;
8. replanning thresholds and residual uncertainty.

## Common failures

- **architecture by fashion:** Selecting frameworks, graphs, agents, or event systems before naming the quality or lifecycle requirement they satisfy.
- **feature calendar as delivery plan:** Ordering work by stakeholder wish list rather than risk, dependency, integration, and evidence value.
- **decision record without consequences:** Recording what was chosen but not alternatives, evidence, tradeoffs, owner, reversibility, or revisit conditions.

## References

- [Architecture Tradeoff Analysis](references/architecture-tradeoff-analysis.md)
- [Thin Slice Risk Planning](references/thin-slice-risk-planning.md)
- [Architecture Decision Evidence](references/architecture-decision-evidence.md)
- [Dependency Capacity Plan](references/dependency-capacity-plan.md)

## Shared references

- [Architecture Escalation](../../references/architecture-escalation.md)
- [Lifecycle Evidence And Readiness](../../references/lifecycle-evidence-and-readiness.md)
- [Decision Records](../../references/decision-records.md)
- [Agent Mediated Product Operating Model](../../references/agent-mediated-product-operating-model.md)
- [Field-Learning and Full-Lifecycle Vocabulary](../../references/field-lifecycle-vocabulary.md)
