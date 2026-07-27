---
name: software-construction-quality
description: "Use when implementing or reviewing agentic software with proportional verification, review, CI, and artifact evidence."
---

# Software Construction & Quality

## Core principle

Build in small end-to-end increments that keep the system releasable and make defects local. Quality evidence must cover code, contracts, state/effects, agent behavior, integration, recovery, security, performance, and the exact deliverable—not merely compilation or a happy-path demo.

## Workflow

### 1. Convert the slice into an executable contract

State behavior, invariants, interfaces, acceptance evidence, non-goals, migration/compatibility constraints, observability, and rollback. Link it to requirements, ADRs, threats, and field-learning objectives.

### 2. Establish a fast inner loop

Use formatting, static checks, targeted tests, schemas, deterministic fixtures, local integration environments, and reproducible commands. Keep failures actionable and preserve exact versions/configuration.

### 3. Implement in small coherent increments

Prefer thin vertical increments over broad unfinished layers. Isolate provider and protocol adapters, keep state/effect boundaries explicit, and avoid combining refactor, behavior change, dependency upgrade, and migration without evidence.

### 4. Apply a risk-based verification ladder

Use unit, property, contract, integration, system/end-to-end, agent outcome/trajectory/recovery, fault/concurrency, security, performance, usability/accessibility, and migration tests according to failure consequence.

### 5. Review design and evidence, not only diff style

Review requirements and architecture alignment, data/effect semantics, failure handling, observability, test oracles, security, maintainability, and exact artifact behavior. Use a fresh-context or independent review for high-risk changes.

### 6. Turn defects into prevention

Classify escaped defects and near misses by mechanism. Update tests, fixtures, schemas, linters, skill guidance, tool contracts, runtime constraints, documentation, or monitoring—not only the immediate code.

### 7. Produce exact handoff evidence

Run checks against the packaged or deployable artifact, record commands and results, list unexecuted checks, attach representative traces/screenshots/logs where relevant, and preserve provenance and reproducibility.

## Output contract

Return a **Construction and Quality Evidence Plan** with:

1. executable slice contract and linked decisions;
2. increment and integration strategy;
3. fast inner-loop and CI command matrix;
4. risk-based verification ladder and oracles;
5. code/design/evidence review plan;
6. defect and near-miss prevention loop;
7. exact artifact, provenance, and handoff evidence requirements;
8. known gaps, waivers, and next verification step.

## Common failures

- **compile means correct:** Treating a successful build or generated code as proof of behavior, integration, recovery, security, or product value.
- **wide batch hidden behind one review:** Combining many independent risks so failures cannot be localized and review becomes superficial.
- **defect fix without prevention:** Patching the symptom while leaving the missing test, contract, constraint, tool, or monitor unchanged.

## References

- [Small Batch Construction](references/small-batch-construction.md)
- [Verification Ladder](references/verification-ladder.md)
- [Review And Defect Learning](references/review-and-defect-learning.md)
- [Artifact Integrity Handoff](references/artifact-integrity-handoff.md)

## Shared references

- Lifecycle Evidence And Readiness (canonical repository reference library: lifecycle-evidence-and-readiness.md)
- Controlled Field Learning System (canonical repository reference library: controlled-field-learning-system.md)
- Evidence And Confidence (canonical repository reference library: evidence-and-confidence.md)
- Decision Records (canonical repository reference library: decision-records.md)
- Field-Learning and Full-Lifecycle Vocabulary (canonical repository reference library: field-lifecycle-vocabulary.md)

## Version 3 construction decisions

Before coding, permit `no_change` and `partial_change` outcomes. Select verification modes by risk and oracle rather than imposing universal TDD. Prefer real behavior over mocks and require representative boundary evidence for critical mocked paths. Bound review/fix loops and return structured feedback. Use `verification-strategy-engineering`, the canonical repository reference library (no-change-and-abstention.md), and the canonical repository reference library (repair-budget-and-feedback.md).
