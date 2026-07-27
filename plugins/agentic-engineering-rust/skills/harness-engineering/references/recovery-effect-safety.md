# Recovery and effect safety

Recovery is not “retry.” It is a policy chosen from failure class, effect status, remaining budget, and the ability to prove state.

## Failure classes

| Class | Example | Default response |
|---|---|---|
| Transient transport | connection reset before dispatch | bounded retry with backoff/jitter |
| Rate/capacity | 429, saturated worker | wait, shed, route or reschedule under deadline |
| Invalid action | schema or semantic precondition failure | repair input or replan; do not retry unchanged |
| Stale state/conflict | version mismatch | refresh authoritative state, reconcile, replan |
| Policy denial | capability or approval denied | stop affected path; offer safe alternative/escalate |
| Ambiguous effect | timeout after possible dispatch | reconcile using action ID; never blind retry |
| Dependency failure | sustained outage | circuit/open wait/fallback/escalation |
| Verification failure | output exists but criterion fails | localized repair or best-so-far rollback |
| Invariant breach | unauthorized transition/data corruption | contain, terminate, preserve evidence, incident path |

## Effect journal

Persist before and after each external effect:

- run/task/action IDs;
- normalized operation, target and arguments hash;
- capability and approval references;
- idempotency key;
- intent timestamp/status;
- dispatch attempt and provider request ID;
- observed result, verification and external identifiers;
- ambiguous/compensation/reconciliation status.

The journal is not merely a log; it is a control structure used to decide whether replay is safe.

## Recovery operators

- **Retry:** repeat the same valid operation after a transient pre-effect failure.
- **Repair:** correct malformed action while preserving goal.
- **Replan:** choose a different route based on new evidence.
- **Reconcile:** query authoritative external state to determine what happened.
- **Compensate:** apply a defined inverse/mitigation when true rollback is impossible.
- **Resume:** continue from durable state without repeating completed work.
- **Escalate:** require human/system decision.
- **Terminate:** stop and preserve evidence when safe continuation is not possible.

## Budgets and storms

Bound attempts per action and per run. Apply exponential backoff with jitter where appropriate, but cap by deadline. Detect repeated semantic actions even when wording differs. Use circuit breakers or shared rate controls so many agents do not amplify an outage.

## Fault-injection points

Crash before intent record, after intent/before dispatch, after external success/before result record, during verification, during checkpoint, and during compensation. The expected post-restart behavior must be specified for every point.
