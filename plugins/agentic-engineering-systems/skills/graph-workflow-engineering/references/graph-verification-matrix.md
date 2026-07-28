# Graph verification matrix

Verify topology, state, behavior, recovery and operations. A final-output test alone cannot show that the graph is safe to resume or that branches are correct.

| Dimension | Evidence |
|---|---|
| Compile/schema | state and node I/O schemas validate; all edge targets exist; terminal nodes reachable |
| Topology | intended branches/cycles/joins present; no unintended cycles/dead ends; budgets dominate cycles |
| State ownership | write sets are declared; reducers tested; version monotonic; sensitive fields classified |
| Node behavior | preconditions, output schema, timeouts, errors and exit invariants tested per node |
| Routing | boundary and ambiguous predicates; fallback; mutually exclusive/exhaustive behavior |
| Parallelism | deterministic fan-in; duplicate/missing/late worker; bounded concurrency |
| Effects | action IDs, idempotency, approval, crash points, reconciliation, compensation |
| Checkpoint/replay | resume at each checkpoint; same verified state; no duplicate effect |
| Interrupts | informed payload; stale/duplicate/denied resume; cancellation while paused |
| Recovery | retry/repair/replan/terminate transitions per failure class |
| Termination | success evidence; budget exhaustion; failure; cancellation; escalation |
| Observability | state transition and causal trace reconstructable; sensitive data redacted |
| Migration | old checkpoint/schema replay or explicit incompatibility/repair procedure |

## Model-based testing

For critical graphs, generate sequences of events and assert global invariants rather than enumerating only happy paths. Useful properties: no unauthorized effect; no terminal success without evidence; budget never negative; action completion at most once; every running node has an owner; all nonterminal states have at least one legal next transition.

## Golden traces

Keep small canonical traces for representative scenarios. Compare semantic events and state transitions rather than volatile model text. Golden traces are useful for detecting topology changes, but they should not freeze legitimate implementation detail.

## Production gates

Before release, run deterministic graph validation, node/unit tests, integration fixtures with fake dependencies, crash/replay tests, security cases, and at least one exact-environment end-to-end scenario. Report unexecuted dimensions explicitly.
