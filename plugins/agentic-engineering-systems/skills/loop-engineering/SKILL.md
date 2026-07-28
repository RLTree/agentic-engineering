---
name: loop-engineering
description: "Use when an agent selects successive actions from feedback and needs budgets, repair, stop, or escalation policy."
---

# Loop Engineering

## Core principle

A production loop is a bounded state machine for evidence-driven adaptation, not “keep trying.” Every iteration must consume new evidence, update typed state and move toward a measurable terminal condition.

## Workflow

### 1. Prove a loop is needed

Identify the uncertainty that prevents a predetermined route. If the stages are known, use a deterministic workflow instead.

### 2. Define typed loop state

Include objective, current hypothesis/plan, observations, evidence, attempted actions, effect receipts, verification status, budgets, blockers and terminal reason. Read [the loop contract](references/loop-contract.md).

### 3. Specify phases

- **Observe:** collect bounded, provenance-labeled evidence.
- **Orient:** interpret evidence and update the working model.
- **Plan:** choose the smallest discriminating next action.
- **Act:** invoke a typed tool or produce a candidate artifact.
- **Verify:** run an independent oracle.
- **Update:** persist state, budget, evidence and next status.

### 4. Define progress and convergence

Use task-relevant measures: failing tests reduced, invariant violations removed, uncertainty narrowed, required evidence completed, objective score improved or no novel failure. Prevent repeated equivalent actions.

### 5. Classify failures

Distinguish transient retry, parameter repair, hypothesis change, plan change, missing capability, policy denial, invariant breach and human decision. Use [the failure and recovery taxonomy](references/failure-recovery-taxonomy.md).

### 6. Set budgets and stop conditions

Bound iterations, wall time, tokens, cost, tool calls, external effects and repeated failures. Terminate as succeeded, failed, blocked, cancelled or escalated with a reason and evidence.

### 7. Evaluate trajectories

Test not only final success but action efficiency, unsafe attempts, recovery quality, evidence use and stop discipline.

## Output contract

Return a **Loop Contract** with:

1. need-for-loop rationale;
2. typed state schema;
3. phase inputs/outputs;
4. action selection policy;
5. verification oracle;
6. progress/convergence measures;
7. budgets and terminal conditions;
8. failure/recovery matrix;
9. trajectory evaluation cases.

## Common failures

- **Iterate until good:** no budget or terminal state. Make limits first-class state.
- **Same action, new wording:** iterations do not consume new evidence. Detect equivalence and escalate.
- **Self-verification:** the generator judges its own plausible output. Use deterministic or independent oracles.
- **Unbounded retries:** invalid actions are retried unchanged. Classify the failure.
- **State only in context:** compaction or crash loses history. Persist authoritative loop state.
- **Success without oracle:** a candidate exists but acceptance evidence does not. Gate success on the oracle.

## References

- [Loop contract](references/loop-contract.md)
- [Failure and recovery taxonomy](references/failure-recovery-taxonomy.md)
- [Budget and stop policy](references/budget-stop-policy.md)
- [Loop test cases](references/loop-test-cases.md)

## Shared references

- Seven-layer map (canonical repository reference library: seven-layer-map.md)
- Architecture escalation (canonical repository reference library: architecture-escalation.md)
- GPT-5.6 Sol operating profile (canonical repository reference library: gpt-5.6-sol-operating-profile.md)
- Evidence and confidence (canonical repository reference library: evidence-and-confidence.md)

## Version 3 repair discipline

Every repair attempt records a hypothesis, mechanism class, changed variable, validator identity, failure location, observed value, admissible alternatives, and evidence gained. Repeated attempts using the same mechanism without new evidence trip a circuit breaker before the numeric budget is exhausted. Calibrate budgets empirically; do not assume unlimited retries or a universal fixed count. Read the canonical repository reference library (repair-budget-and-feedback.md).
