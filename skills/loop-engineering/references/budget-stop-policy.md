# Budget and stop policy

Budgets make autonomy accountable. They limit resource use and force the loop to decide whether another action has sufficient expected value.

## Budget dimensions

- iterations/replans;
- model calls and reasoning effort;
- tool calls per type;
- wall-clock/deadline;
- cost/tokens;
- concurrent workers/tasks;
- external side effects;
- approval requests;
- failed or repeated semantic actions;
- context size/retrieval volume.

Set both per-action and per-run limits where one operation could consume the whole budget.

## Stop predicates

Stop successfully only when all required acceptance criteria have evidence. Stop for escalation when a missing decision is consequence-bearing. Stop for failure when an invariant is breached or safe recovery is unavailable. Stop for budget exhaustion before the final unit is consumed so there is room to checkpoint, reconcile, and report.

## Progress signal

Define progress as change in observable acceptance state, reduction in uncertainty, or production of discriminating evidence. Number of messages, edits, or tool calls is not progress.

Track:

- acceptance criteria newly satisfied;
- defect count/severity delta;
- uncertainty/evidence delta;
- score delta with grader confidence;
- repeated state/action fingerprints;
- time/cost per unit progress.

## Diminishing returns

Stop or change strategy when several iterations fail to improve the same criterion, the score oscillates, new actions repeat prior semantics, or expected gain falls below a configured threshold. Preserve best-so-far.

## Budget transfer

Do not silently increase a budget because the loop is close. A budget extension is a decision with rationale, evidence and authority. In a multi-agent run, reserve coordination/fan-in budget rather than allocating all resources to workers.

## Exhaustion report

Return the best verified artifact/state, criteria met/unmet, evidence, actions attempted, reason for stopping, unresolved effect status, and the next discriminating action. Do not label budget exhaustion as success.
