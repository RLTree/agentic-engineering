---
name: continuous-product-experimentation
description: "Use when a product decision needs an experiment, holdout, ramp, or causal observational design."
---

# Continuous Product Experimentation

## Core principle

An experiment is a decision instrument, not a dashboard event. Predefine the decision, mechanism, population, assignment, outcomes, guardrails, data-quality tests, analysis, and stopping rule; use observational evidence for diagnosis and randomized or credible quasi-experimental designs for causal claims when feasible.

## Workflow

### 1. State the decision and mechanism hypothesis

Define what product or system decision will change, why the intervention should affect the outcome, affected segments, expected time horizon, risks, and what evidence would reverse the preferred choice.

### 2. Select the evidence design

Choose randomized A/B, switchback, cluster randomization, holdout, stepped ramp, quasi-experiment, or observational analysis based on interference, unit of assignment, ethics, traffic, effect persistence, and operational constraints. State causal limitations.

### 3. Write metric contracts

For each outcome, diagnostic, guardrail, and data-quality metric, define construct, formula, population, event sources, attribution window, missingness, direction, sensitivity, segmentation, owner, gaming risk, and retirement condition.

### 4. Design assignment and exposure

Define eligibility, randomization unit, stable assignment, exclusions, concurrent experiments, novelty/carryover, sample size/power, ramp stages, cohort privacy, and sample-ratio-mismatch checks.

### 5. Define analysis and stopping

Predefine estimand, variance reduction if used, multiple-testing/peeking policy, confidence or decision interval, practical significance, heterogeneity, long-term follow-up, and early stop for harm or data invalidity.

### 6. Triangulate with authentic-use evidence

Review representative traces, interventions, user edits, support data, interviews, incidents, and success patterns to interpret mechanisms and detect aggregate masking. Do not turn qualitative evidence into false numerical certainty.

### 7. Decide and institutionalize learning

Record keep, change, ramp, narrow, revert, rerun, or stop; update product requirements, evals, tools, constraints, SLOs, and future experiment design; preserve the contract, analysis, and data-quality evidence.

## Output contract

Return a **Product Experiment and Decision Contract** with:

1. decision, mechanism hypothesis, population, segments, and time horizon;
2. evidence design and causal limitations;
3. outcome, diagnostic, guardrail, and data-quality metric contracts;
4. assignment, exposure, ramp, holdout, and sample-integrity plan;
5. analysis, practical-significance, multiplicity, and stopping policy;
6. qualitative and trace triangulation plan;
7. keep, change, ramp, narrow, revert, rerun, or stop rule;
8. learning-to-product/eval/tool/constraint update path.

## Common failures

- **metric movement as causality:** Claiming the product caused an outcome from uncontrolled telemetry or a confounded before/after comparison.
- **one metric optimizes the product:** Using a single target without guardrails, data-quality checks, segment analysis, or gaming assessment.
- **invalid experiment still shipped:** Ignoring sample-ratio mismatch, missing events, assignment contamination, peeking, or carryover because the result is favorable.

## References

- [Experiment Metric Contract](references/experiment-metric-contract.md)
- [Causal Evidence Design](references/causal-evidence-design.md)
- [Ramp Holdout Guardrails](references/ramp-holdout-guardrails.md)
- [Experiment Analysis Decision](references/experiment-analysis-decision.md)

## Shared references

- Metric And Causal Evidence (canonical repository reference library: metric-and-causal-evidence.md)
- Field Evidence Ladder (canonical repository reference library: field-evidence-ladder.md)
- Controlled Field Learning System (canonical repository reference library: controlled-field-learning-system.md)
- Evidence And Confidence (canonical repository reference library: evidence-and-confidence.md)
- Field-Learning and Full-Lifecycle Vocabulary (canonical repository reference library: field-lifecycle-vocabulary.md)
