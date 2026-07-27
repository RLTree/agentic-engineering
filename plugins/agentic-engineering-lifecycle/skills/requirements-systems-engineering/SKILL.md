---
name: requirements-systems-engineering
description: "Use when an agentic product needs operational concepts, mission threads, quality requirements, interfaces, or traceability."
---

# Requirements & Systems Engineering

## Core principle

Requirements are testable claims about stakeholder and system outcomes in context—not a feature list. Derive them from an operational concept and representative mission threads, express quality attributes as scenarios, and trace each consequential requirement to evidence, architecture, verification, validation, operation, and retirement.

## Workflow

### 1. Define the system of interest and operational concept

Describe actors, environment, workflows, modes, lifecycle, external systems, authority, data, effects, degraded operation, support, and retirement. Use real-work evidence and identify where the concept is still hypothetical.

### 2. Capture stakeholder needs and tensions

Record needs from users, operators, maintainers, approvers, security/privacy, legal/compliance, finance, support, and downstream parties. Preserve conflicts and decision authority instead of silently resolving them.

### 3. Write representative mission threads

Specify end-to-end nominal, alternate, degraded, adversarial, recovery, and retirement scenarios. Include triggers, preconditions, state, human/agent roles, tools, effects, timing, data, and observable outcomes.

### 4. Derive requirements and quality scenarios

Write functional requirements plus quality-attribute scenarios for safety, security, privacy, reliability, performance, usability, accessibility, interoperability, maintainability, observability, and cost. Make conditions and measurable responses explicit.

### 5. Define interfaces and control boundaries

Specify tool/service contracts, schema/version rules, trust boundaries, permissions, approval gates, idempotency/effect semantics, state ownership, error taxonomy, and provenance.

### 6. Establish verification, validation, and traceability

For every requirement, name verification method, validation evidence in representative use, owner, lifecycle phase, source, and downstream artifacts. Distinguish “built right” verification from “right system in context” validation.

### 7. Baseline and control change

Set requirement status, rationale, priority, uncertainty, dependencies, waivers, change authority, impact analysis, and revisit triggers. Keep field failures and successes linked to requirement changes and regression evidence.

## Output contract

Return a **Operational Concept and Traceability Baseline** with:

1. system boundary and operational concept;
2. stakeholder-needs map with conflicts and decision authorities;
3. nominal, alternate, degraded, adversarial, recovery, and retirement mission threads;
4. functional, interface, constraint, and quality-attribute requirements;
5. agent/human/tool/effect and trust boundaries;
6. requirement-to-source-to-architecture-to-verification-to-validation traceability;
7. baseline, waiver, change-control, and impact-analysis policy;
8. open assumptions and field-evidence revisit triggers.

## Common failures

- **feature list as requirements:** Listing desired capabilities without operational conditions, measurable response, owner, or verification method.
- **verification substituted for validation:** Proving the implementation matches a spec without showing the system solves the representative real-world need.
- **traceability after the fact:** Reconstructing links only for an audit. Create and maintain traceability as decisions are made.

## References

- [Operational Concept Mission Threads](references/operational-concept-mission-threads.md)
- [Requirements Quality Attributes](references/requirements-quality-attributes.md)
- [Traceability Verification Validation](references/traceability-verification-validation.md)
- [Change And Baseline Control](references/change-and-baseline-control.md)

## Shared references

- [Full Lifecycle Map](../../references/full-lifecycle-map.md)
- [Lifecycle Evidence And Readiness](../../references/lifecycle-evidence-and-readiness.md)
- [Controlled Field Learning System](../../references/controlled-field-learning-system.md)
- [Decision Records](../../references/decision-records.md)
- [Field-Learning and Full-Lifecycle Vocabulary](../../references/field-lifecycle-vocabulary.md)
