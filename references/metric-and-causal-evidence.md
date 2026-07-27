# Metric and causal evidence

Metrics are decision instruments with failure modes. Define what decision they support, how they can be gamed, and what evidence is needed before interpreting a change as product value.

## Metric contract

Every product or field-learning decision should include four classes:

1. **Outcome metrics:** direct evidence of user or organizational value, task completion, quality, time-to-value, avoided harm, or sustained behavior.
2. **Diagnostic metrics:** mechanisms and trajectory signals such as tool errors, edit distance, intervention, retries, abandonment, approval time, queueing, latency or cost.
3. **Guardrail metrics:** safety, security, privacy, fairness, reliability, operator burden, support contacts, severe errors, rollback rate or unacceptable side effects.
4. **Data-quality metrics:** assignment integrity, exposure logging, event completeness, join rate, freshness, duplication, sample-ratio mismatch, instrumentation version and missingness by segment.

For each metric record definition, unit, population, exclusions, window, aggregation, segmentation, direction, materiality threshold, owner, source of truth, known gaming path, and expiration/review condition.

## Observational versus causal claims

Observational field data is strong for discovering failure mechanisms, task distributions, correlations, rare events, workflow friction and hypotheses. It is weak for attributing outcome changes when users self-select, exposure differs, the product changes behavior, or concurrent changes exist.

For causal product claims prefer:

- randomized controlled exposure with intention-to-treat analysis;
- cluster or switchback randomization when interference or shared resources matter;
- stepped-wedge/staggered rollout with predeclared analysis when universal rollout is required;
- regression discontinuity, difference-in-differences or synthetic controls only when assumptions are defensible and checked;
- longitudinal holdouts when novelty, adaptation, maintenance burden or delayed harm matters.

## Validity checks before results

Do not interpret outcome deltas until checking:

- sample-ratio mismatch and assignment/exposure mismatch;
- missing, duplicated, delayed or version-inconsistent events;
- treatment contamination and spillovers;
- peeking, repeated testing and multiple comparisons;
- novelty, learning, carryover and network effects;
- attrition, survivorship and non-user exclusion;
- segment heterogeneity and guardrail regressions;
- instrumentation changes during the test;
- whether the metric can improve while the actual workflow worsens.

## Decision rule

Predeclare: primary outcome, guardrails, minimum detectable/material effect, horizon, sample or stopping logic, analysis population, segmentation, invalidation rules, and actions for win/neutral/loss/mixed results. A statistically detectable change is not automatically practically valuable; a neutral average can conceal beneficial and harmful segments.

## Generative-AI specific evidence

Combine quantitative metrics with representative trace review and qualitative inquiry. Model-based graders are useful diagnostic instruments but require calibration against human judgments, drift checks, adversarial fixtures and uncertainty reporting. Do not let the same model generate, grade and declare its own success without independent evidence.

## Research basis

The contract follows trustworthy experimentation practice, sample-ratio mismatch diagnostics, long-term experimentation guidance, mixed-method GenAI evaluation, agent trajectory evaluation, and feature-flag context rules [R72] [R79] [R80] [R81] [R82] [R115] [R116].
