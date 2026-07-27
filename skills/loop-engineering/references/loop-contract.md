# Loop contract

A production agent loop is a bounded state machine, not an instruction to “keep trying.” Externalize the information required to decide the next action and whether continued work is justified.

## Canonical phases

```text
OBSERVE -> ORIENT -> PLAN -> ACT -> VERIFY -> UPDATE
    ^                                      |
    +-------- recover / continue ----------+
                        |
                succeed / escalate / fail
```

**Observe:** acquire fresh authoritative state and tool evidence.  
**Orient:** classify facts, uncertainty, failure, policy and remaining budget.  
**Plan:** choose one or a small batch of actions whose expected information/value is explicit.  
**Act:** execute through typed tools under permission and deadline.  
**Verify:** compare outcome to an oracle, not to the plan’s plausibility.  
**Update:** persist state/evidence, best-so-far, budgets and next decision.

## Contract fields

- objective and terminal success predicate;
- authoritative state schema and owner;
- admissible action types and effect classes;
- observation sources and freshness requirements;
- planning output schema;
- verification oracle(s);
- retry/repair/replan/escalation transitions;
- iteration, tool, time, token/cost and side-effect budgets;
- repeated-action/convergence detector;
- cancellation and human interrupt behavior;
- checkpoint and handoff requirements.

## One-action discipline

Prefer the smallest action that can produce discriminating evidence. Large speculative action batches hide which premise failed and increase rollback cost. Batch only independent, low-risk operations with clear aggregation.

## Best-so-far

Evaluator–optimizer loops should preserve the best verified artifact and its score/evidence. A later iteration must not overwrite it merely because it is newer. Define tie-breaking and regression rules.

## Terminal states

- **Succeeded:** all required acceptance predicates have evidence.
- **Escalated:** a consequence-bearing decision or missing capability requires another actor.
- **Budget exhausted:** return best verified state, gaps, and next discriminating action.
- **Failed:** invariant or unrecoverable dependency prevents safe progress.
- **Cancelled:** stop intake/actions, reconcile in-flight effects, checkpoint and report.

## Loop review

Reject a loop design that lacks a falsifiable oracle, explicit budgets, state update, semantic repeated-action detection, or safe treatment of external effects.
