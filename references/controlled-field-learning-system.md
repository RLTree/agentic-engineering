# Controlled field-learning system

Controlled field learning is the disciplined use of representative real work to reduce product and system uncertainty while limiting harm. It is neither an uncontrolled production experiment nor a replacement for offline tests.

## Core loop

```text
learning decision
  → operating envelope
  → least-risk exposure/autonomy level
  → instrumentation and representative sampling
  → observation and analysis
  → mechanism hypothesis
  → product/eval/tool/policy intervention
  → controlled rollout and verification
  → keep, narrow, ramp, revert, redesign, or retire
```

## Required contracts

### Learning contract

State the decision, uncertainty, why proxies are insufficient, affected users, expected evidence, and thresholds for continue/change/pause/stop.

### Operating envelope

Define allowed users, workflows, task classes, data classes, tools, environments, jurisdictions, effects, scale, time/cost budgets, failure tolerance, and exclusions. The envelope is a safety and validity boundary: findings do not automatically generalize beyond it.

### Exposure contract

Choose replay, observe-only, shadow/silent, recommendation-only, approval-gated, bounded autonomy, or broader autonomy. Define cohort, comparator/holdout, blast-radius budget, ramp sequence, approvals, rollback, kill switch, and stop conditions.

### Observation contract

Capture stable identities and versions; workload attributes; decisions and alternatives; model/tool calls; effects and effect status; approvals, edits, overrides, escalations and abandonment; retries and recovery; outcome; time, cost and human effort; incidents and near misses; privacy class; and trace completeness.

### Change contract

Every material observation should produce one of: no change with rationale, new evidence request, product/UX change, requirement, context/prompt/skill change, tool contract, permission or approval change, loop/graph/runtime control, eval fixture, monitor/alert, documentation/runbook, architecture decision, rollout change, or retirement action.

## Review cadence

Use both event-triggered and periodic review:

- immediate review for safety, security, privacy, ambiguous external effects or severe user harm;
- daily/weekly trace triage during early exposure;
- cohort and task-segment review at each ramp step;
- periodic success deconstruction, not just failure review;
- experiment decision review after validity checks;
- lifecycle review when evidence changes a requirement, architecture assumption, operating envelope, or retirement obligation.

## Validity and safety rules

- Offline evaluation is required preflight evidence but does not establish field effectiveness.
- Observational data can diagnose mechanisms and generate hypotheses; causal claims need a valid comparison design when feasible.
- Representative work matters more than convenient volume.
- Human intervention is an outcome and design signal; do not treat it only as noise.
- Success can conceal hidden labor, risk transfer, gaming, or missing cohorts.
- Exposure must be progressive, reversible, attributable, and observable.
- Feature flags control exposure, not authorization.
- Telemetry collection must be necessary, minimized, access-controlled, retained intentionally, and redacted at source.

## Research basis

The system operationalizes agent-improvement loops, macro/trajectory evals,
autonomy practice, monitoring questions, silent-trial literature, controlled
experimentation, and SRE progressive exposure. NIST AI 800-4 is a descriptive
challenge taxonomy rather than a prescribed method (`F-NIST-AI800-4`).
Historical lineage: [R71] [R72] [R73] [R74] [R75] [R77] [R78] [R79] [R107].
