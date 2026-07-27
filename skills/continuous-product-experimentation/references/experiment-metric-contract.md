# Experiment and metric contract

An experiment contract binds a product decision to a population, intervention, comparison, outcomes, guardrails, data-quality checks, analysis and action. It prevents favorable but invalid numbers from becoming release evidence.

## Vocabulary
- **estimand:** Exact causal quantity the experiment seeks to estimate for a population and horizon.
- **unit of randomization:** Entity assigned to variants, such as user, team, account, task, time block or cluster.
- **exposure:** Actual opportunity to experience the treatment, distinct from assignment.
- **guardrail:** Measure that can block or reverse a decision despite primary-outcome improvement.
- **minimum practically important effect:** Smallest outcome change worth the cost, risk and complexity—not merely detectable statistically.

## Decision procedure
1. State product decision, mechanism hypothesis, target population, operating envelope, intervention and alternatives.
2. Choose unit of assignment, treatment variants, baseline/control, exposure logging, interference policy and analysis population.
3. Define primary outcome, diagnostic, guardrail and data-quality metrics with exact formulas, windows, segments and owners.
4. Predeclare materiality, horizon, sample/stopping rule, multiple-testing policy, invalidation conditions and actions for win/neutral/loss/mixed.
5. Run an instrumentation/A/A check and ramp progressively; inspect sample-ratio mismatch, contamination, missingness and guardrails before outcomes.
6. Analyze uncertainty, practical effect, heterogeneity, qualitative/trace mechanisms and long-term risk; make and record the decision.

## Decision table

| Metric class | Question | Example |
|---|---|---|
| Outcome | Did users/systems obtain value? | verified task outcome or time-to-value |
| Diagnostic | Why did result change? | intervention, retries, edit distance |
| Guardrail | What must not worsen? | severe error, privacy, operator burden |
| Data quality | Can result be trusted? | assignment/exposure match, join completeness |

## Evidence obligations
- The primary decision and metric are selected before outcome inspection.
- Metrics include population, denominator, missing-event treatment and segmentation.
- Model-based quality graders are calibrated against independent human/ground-truth samples.
- Aggregate wins cannot override severe or policy hard-stop guardrails.

## Review questions
1. What decision will a win, neutral, loss or mixed result cause?
2. Can the metric improve while the actual workflow or user welfare worsens?
3. Does assignment match exposure and analysis?
4. Which task/user segments could experience opposite effects?

## Failure patterns
- Metric shopping: choosing the favorable measure after results.
- Activity metric as value: clicks, tokens or completions replace outcomes.
- Invalid experiment still shipped: SRM or missing telemetry ignored.

## Research basis

Based on trustworthy experimentation, SRM, GenAI mixed-method evaluation, and agent trajectory evidence [R72] [R79] [R80] [R82].
