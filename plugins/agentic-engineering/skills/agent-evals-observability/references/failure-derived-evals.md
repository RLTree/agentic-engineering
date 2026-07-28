# Failure-derived evaluations

The highest-value evals often come from real corrections, incidents and near misses. Turn each recurrence into a durable fixture at the layer that can prevent it.

## Conversion protocol

1. Capture the observable failure and affected outcome.
2. Remove sensitive data while preserving causal structure.
3. Identify the missing decision and responsible layer.
4. Create the minimal initial state/context/tools that reproduce it.
5. Define desired and forbidden trajectories, not only final output.
6. Choose deterministic and semantic graders.
7. Run against baseline and proposed repair.
8. Promote the repair to task contract, AGENTS.md, skill, harness, test, schema or policy.
9. Keep the fixture in regression and record source incident ID.

## Useful categories

- over/under-triggered skill;
- stale or poisoned context;
- wrong tool or malformed arguments;
- repeated action/looping;
- premature completion;
- hidden graph branch;
- duplicate external effect;
- unsafe approval or permission bypass;
- multi-agent overlap/integration loss;
- crash/replay error;
- Rust task leak, deadlock, unbounded queue or shutdown loss;
- source-only success while packaged artifact fails.

## Counterfactuals

Add nearby cases that should not trigger the repair. A skill that fixes one failure by activating everywhere creates new regressions. Test adversarial wording and incomplete evidence.

## Decision delta

Document what behavior should change, why the mechanism should cause it, and what metrics could regress. This connects evidence to operationalization and prevents cargo-cult instructions.
