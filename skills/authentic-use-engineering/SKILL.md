---
name: authentic-use-engineering
description: Use when representative real work should guide product, eval, tool, policy,
  or autonomy decisions.
---

# Authentic Use Engineering

## Core principle

Offline tests are preflight evidence; controlled exposure to representative work is the learning instrument. Increase exposure and autonomy only inside an explicit operating envelope, with effect safety, privacy, observability, rollback, and a review process that converts field evidence into durable system changes.

## Workflow

### 1. State the learning decision

Name the product decision that authentic use must inform, the uncertainty that cannot be resolved credibly with simulation or anecdotes, the affected users, the consequential effects, and the evidence threshold for keep, change, pause, or stop.

### 2. Define the operating envelope

Specify allowed users, tasks, data classes, tools, environments, jurisdictions, hours, effect types, spend/latency limits, failure tolerance, and excluded conditions. Treat anything outside this envelope as an escalation or denial, not an invitation to improvise.

### 3. Choose exposure and autonomy levels

Select the least risky level that can answer the learning question: replay, observe-only, shadow/silent, recommendation-only, approval-gated action, bounded autonomy, or broader autonomy. Define blast radius, cohort, ramp steps, holdout or comparator, approval latency, rollback, and kill criteria.

### 4. Instrument task, trajectory, effect, and human work

Capture stable run/task/action/effect IDs; versions; cohort; context provenance; decisions; tool calls; approvals; interventions; edits; retries; errors; ambiguous effects; recovery; outcome; latency/cost; user effort; and privacy labels. Preserve representative traces, not only aggregates.

### 5. Establish evidence quality and analysis

Predefine outcome, diagnostic, guardrail, and data-quality measures. Segment by task and risk. Combine trace review, interviews or contextual inquiry, incident and near-miss analysis, success deconstruction, and quantitative comparisons. Distinguish observational diagnosis from causal claims.

### 6. Run the evidence-to-change review

Convert each material observation into a mechanism hypothesis and one or more durable changes: product workflow, UX, requirement, prompt/context, tool contract, permission, approval gate, loop policy, graph transition, runtime control, eval fixture, monitoring rule, or documentation. Link the change to a test and rollout decision.

### 7. Decide and preserve learning

Record whether to continue, ramp, hold, revert, redesign, narrow the envelope, or retire the capability. Store the observation, evidence strength, decision, owner, change, verification, and outcome in a field-learning ledger.

## Output contract

Return a **Controlled Field-Learning Plan** with:

1. learning question and decision thresholds;
2. operating envelope and explicit exclusions;
3. exposure/autonomy ladder with cohorts, blast-radius budgets, approvals, rollback, and kill criteria;
4. field instrumentation and privacy/retention contract;
5. representative task distribution and evidence-quality rubric;
6. metric, qualitative-research, trace-review, and causal-analysis plan;
7. evidence-to-change ledger and review cadence;
8. ramp, hold, revert, redesign, or retirement decision rules.

## Common failures

- **production as an unbounded experiment:** Exposing consequential work without an envelope, approval policy, rollback, or learning question. Use controlled field learning.
- **aggregate metric as truth:** Letting one satisfaction, success-rate, or benchmark number hide task segments, interventions, safety regressions, or data-quality failure.
- **telemetry without product change:** Collecting traces that never become requirements, evals, tools, constraints, or decisions. Require an evidence-to-change ledger.

## References

- [Controlled Field Learning](references/controlled-field-learning.md)
- [Operating Envelope Autonomy](references/operating-envelope-autonomy.md)
- [Field Instrumentation Evidence](references/field-instrumentation-evidence.md)
- [Evidence To Change Loop](references/evidence-to-change-loop.md)

## Shared references

- [Controlled Field Learning System](../../references/controlled-field-learning-system.md)
- [Field Evidence Ladder](../../references/field-evidence-ladder.md)
- [Autonomy And Exposure Ladder](../../references/autonomy-and-exposure-ladder.md)
- [Metric And Causal Evidence](../../references/metric-and-causal-evidence.md)
- [Field-Learning and Full-Lifecycle Vocabulary](../../references/field-lifecycle-vocabulary.md)

## Version 3 product-fitness handoff

Use `product-fitness-engineering` when the question is not merely how to expose the product safely, but whether intended users achieve value with acceptable intervention, recovery, risk, and continuance. Feed observations into `engineering-learning-loop`; do not promote a product or universal policy claim directly from one field observation.
