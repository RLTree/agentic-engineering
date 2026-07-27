---
name: concept-feasibility-validation
description: Use when a proposed agentic concept needs the cheapest credible desirability,
  feasibility, viability, or safety test.
---

# Concept & Feasibility Validation

## Core principle

Validate the riskiest assumptions with the cheapest test that preserves the property being judged. Separate desirability, usability, technical feasibility, operational supportability, economics, security, and safety so a polished prototype cannot conceal a fatal constraint.

## Workflow

### 1. Decompose the concept into claims

List user-value, workflow, data, model capability, tool/effect, latency, cost, integration, security, compliance, operations, adoption, and business claims. Rank by uncertainty multiplied by consequence.

### 2. Choose a faithful test for each decisive claim

Use sketches or concierge tests for workflow/value, Wizard-of-Oz for interaction, model probes for capability, technical spikes for integration/performance, threat modeling for misuse, and shadow or approval-gated trials for real-context behavior. State what each test cannot prove.

### 3. Define baseline, comparator, and thresholds

Compare against the current workflow and the simplest non-agentic alternative. Predefine minimum useful outcome, unacceptable harm, human-effort ceiling, cost/latency boundary, and evidence-quality threshold.

### 4. Test edge conditions early

Include difficult task segments, missing/ambiguous data, tool denial, stale context, interruptions, adversarial content, permission boundaries, degraded dependencies, and recovery. Measure human correction and verification work, not just model output.

### 5. Assess operational and lifecycle feasibility

Evaluate observability, support ownership, release/rollback, capacity, data retention, evaluation maintainability, dependency risk, model/harness change, and retirement/migration—not only whether a demo works.

### 6. Update the assumption map

For each test, record result, confidence, limitations, mechanism interpretation, and whether the claim is supported, weakened, contradicted, or unresolved. Avoid averaging incompatible risks into one score.

### 7. Make a go, pivot, narrow, pause, or stop decision

Recommend the smallest next investment and specify which evidence would reverse the decision. A successful concept may still require a narrower operating envelope or lower autonomy level.

## Output contract

Return a **Concept and Feasibility Evidence Case** with:

1. concept and decisive claim decomposition;
2. risk-ranked assumption map;
3. prototype, spike, probe, or field-test design for each decisive assumption;
4. baseline, comparator, thresholds, and explicit non-claims;
5. edge-condition, safety, security, operations, and economics evidence;
6. updated evidence strength and unresolved uncertainty;
7. go, pivot, narrow, pause, or stop recommendation;
8. next smallest investment and reversal criteria.

## Common failures

- **prototype theater:** Using visual polish or one happy-path demo as evidence of value, feasibility, safety, or supportability.
- **capability score without workflow fit:** Measuring isolated model accuracy while ignoring integration, human correction, latency, cost, effects, and adoption.
- **sunk-cost validation:** Designing tests only to confirm the preferred concept. Predefine disconfirming evidence and stop criteria.

## References

- [Assumption And Risk Map](references/assumption-and-risk-map.md)
- [Prototype Spike Strategy](references/prototype-spike-strategy.md)
- [Feasibility Evidence](references/feasibility-evidence.md)
- [Go Pivot Stop Criteria](references/go-pivot-stop-criteria.md)

## Shared references

- [Field Evidence Ladder](../../references/field-evidence-ladder.md)
- [Metric And Causal Evidence](../../references/metric-and-causal-evidence.md)
- [Lifecycle Evidence And Readiness](../../references/lifecycle-evidence-and-readiness.md)
- [Evidence And Confidence](../../references/evidence-and-confidence.md)
- [Field-Learning and Full-Lifecycle Vocabulary](../../references/field-lifecycle-vocabulary.md)
