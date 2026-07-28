# Loop failure and recovery taxonomy

The loop should classify why progress failed before selecting a response. Repeating the same action is rarely a universal remedy.

## Categories

### Observation failure
Evidence is missing, stale, contradictory, truncated or from an untrusted source. Response: retrieve authoritative data, broaden/narrow search, compare provenance, or escalate when truth is unavailable.

### Orientation failure
The system misclassified state, constraints, or failure. Response: re-evaluate against invariants, ask a discriminating question, run an independent check, or invoke a specialized evaluator.

### Planning failure
The action does not address the observed defect, violates constraints, or is too broad. Response: repair plan, reduce action size, choose a different hypothesis, or restore best-so-far.

### Action failure
Tool validation, permission, timeout, dependency or execution error. Response depends on whether dispatch/effect occurred. Use typed tool error policy and effect reconciliation.

### Verification failure
Action completed but acceptance did not improve. Response: localize the failed criterion, compare before/after evidence, update hypothesis, and prevent identical retries.

### Convergence failure
The loop cycles, oscillates, or produces diminishing returns. Response: detect repeated semantic state/action pairs, tighten the oracle, change method, reduce scope, escalate, or stop with best evidence.

### Policy/invariant failure
Action would exceed privilege, budget, safety, data or product boundary. Response: deny, contain, record, and obtain explicit approval or terminate.

## Recovery decision record

For each failure record:

- class and evidence;
- whether an external effect may have occurred;
- remaining budgets;
- attempted semantic actions and outcomes;
- selected operator: retry, repair, replan, reconcile, compensate, escalate, terminate;
- why the operator is safe and likely to add information/value;
- next verification predicate.

## Retry eligibility

Retry only when the action is still valid, the failure is plausibly transient, effect identity is safe, deadline/budget remains, and retry is not part of a fleet-wide storm. Use server-provided retry hints where trustworthy. Otherwise repair or replan.

## Recovery evaluation

Create fixtures for each class, especially ambiguous effects and verification regressions. Grade not only eventual outcome but whether the chosen recovery action was appropriate and bounded.
