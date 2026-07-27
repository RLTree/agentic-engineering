# Experiment analysis and decision

Analyze experiments in an order that protects validity: identity and data quality, guardrails, primary outcome, uncertainty and practical significance, heterogeneity, mechanisms and long-term implications—then execute the predeclared decision.

## Vocabulary
- **sample-ratio mismatch:** Observed assignment proportions differ materially from design, signaling possible validity failure.
- **practical significance:** Effect large enough to justify cost, risk and complexity.
- **heterogeneous treatment effect:** Different effect across users, tasks, risk or environments.
- **sensitivity analysis:** Check how conclusions change under plausible assumptions or analytic choices.
- **decision debt:** Completed analysis without a timely product action or explicit no-change rationale.

## Decision procedure
1. Freeze/identify data, queries, metric versions, exclusions, assignment and exposure; run completeness, duplication, freshness, SRM and contamination checks.
2. Review incidents and hard guardrails before primary outcomes.
3. Estimate primary and secondary effects with uncertainty and practical thresholds using predeclared methods.
4. Inspect segments defined before analysis; label exploratory slices and correct for multiple comparisons.
5. Review representative trajectories, qualitative evidence, interventions, successes and failures to test the mechanism.
6. Assess novelty, carryover, long-term cost/reliability, externalities and missing populations.
7. Decide ship/ramp/narrow/redesign/revert/stop/no-change; record rationale, residual uncertainty and follow-up.

## Decision table

| Result | Interpretation | Decision tendency |
|---|---|---|
| Positive, valid, guardrails healthy | Supported bounded value | Ramp/ship within envelope |
| Neutral but precise | No material benefit | Stop or remove complexity |
| Neutral and underpowered | Insufficient evidence | Continue only if decision value justifies |
| Positive average, harmed segment | Heterogeneous risk | Narrow/redesign/stop |
| Invalid data/assignment | No trustworthy effect | Repair and rerun |

## Evidence obligations
- Exploratory findings are labeled and validated independently before broad commitment.
- Statistical significance alone does not decide practical value.
- No-result and negative-result learning is preserved; experiments are not success contests.
- Decision and implementation/rollback ownership are explicit.

## Review questions
1. Did we validate the data and assignment before reading outcomes?
2. Is the effect large enough to matter after total lifecycle cost and review burden?
3. What trace/qualitative evidence supports the proposed mechanism?
4. What action closes the experiment?

## Failure patterns
- P-value launch: detectable but trivial effect shipped.
- Average hides harm: no task/user/risk segmentation.
- Analysis without decision: dashboard becomes permanent ambiguity.

## Research basis

Based on trustworthy experimentation, SRM, long-term analysis and mixed-method GenAI evaluation [R79] [R80] [R81] [R82].
