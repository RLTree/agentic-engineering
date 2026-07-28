# Agent evaluation taxonomy

Evaluate the behavior distribution you intend to operate, not one polished demonstration. Multi-step agents need separate measures for result, trajectory, recovery and safety.

## Evaluation layers

### Outcome
Did the durable artifact or external state satisfy acceptance criteria? Use tests, schemas, human rubric, exact-render checks, or authoritative system state.

### Trajectory
Did the agent choose appropriate tools/actions, use relevant context, respect budgets, avoid unnecessary steps, and preserve state/evidence? A correct final answer can still have an unacceptable trajectory.

### Recovery
Did it classify failure correctly, avoid duplicate effects, reconcile ambiguity, resume from checkpoint, preserve best-so-far, and escalate appropriately?

### Safety/governance
Did it maintain provenance, permissions, approvals, data boundaries, and prohibited-action rules under adversarial or misleading inputs?

### Operational
Latency, cost, token/tool use, queue pressure, approval load, failure rate, trace completeness and variance.

## Eval unit

Define task distribution, fixture/environment, initial state, available tools/capabilities, hidden ground truth, expected evidence, graders and pass thresholds. Preserve seeds/configuration/model/skill/harness versions.

## Skill evals

Test both routing and behavior:

- should invoke;
- should not invoke;
- ambiguous overlap;
- correct procedure and deliverable;
- forbidden shortcuts/common failures;
- graceful behavior when evidence/tools are unavailable.

## Regression policy

Gate on critical invariants and statistically meaningful aggregate change. Keep a small fast set for every change and a broader representative set for release. Add production failures as fixtures after sanitization.

## Reporting

Show per-dimension scores, severity-weighted failures, confidence intervals where applicable, model/judge version, unexecuted tests and representative traces. Avoid one composite score that hides a safety or recovery regression.
