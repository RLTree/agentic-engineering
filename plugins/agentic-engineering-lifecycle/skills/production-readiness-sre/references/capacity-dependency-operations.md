# Capacity, dependency, and operations

Operate agentic systems as queues of work, decisions and effects with bounded resources and explicit dependency semantics. Reliability depends on overload behavior, deadlines, retry/reconciliation, human capacity, and graceful degradation.

## Vocabulary
- **admission control:** Decision to accept, delay, degrade or reject work before resources are exhausted.
- **backpressure:** Propagation of downstream capacity limits to upstream producers.
- **load shedding:** Intentional rejection or degradation of lower-priority work to protect critical outcomes.
- **dependency SLO:** Expected latency, availability, quota and correctness contribution from an external/internal service.
- **operational envelope:** Scale, workload and failure conditions for which runbooks and reliability evidence apply.

## Decision procedure
1. Model task classes, priority, arrival, concurrency, loop/graph fan-out, payload/state, model/tool calls, effects, tracing and human review.
2. Define resource and dependency budgets, deadlines, quotas, retry/idempotency/reconciliation and failure ownership.
3. Implement bounded queues/semaphores, admission, cancellation, timeouts, circuit breaking, degradation, shedding and fairness.
4. Instrument queue depth/age, saturation, downstream latency/error, retries, ambiguous effects, cancellations, cost and review backlog.
5. Exercise burst, sustained overload, slow/failed dependency, quota exhaustion, exporter failure, operator absence, recovery and shutdown.
6. Set scaling, forecast, procurement/vendor, failover and decommission triggers.

## Decision table

| Failure | Safe behavior | Unsafe behavior |
|---|---|---|
| Queue saturation | shed/degrade with clear outcome | unbounded memory/latency |
| Dependency timeout | respect absolute deadline | nested retry storm |
| Ambiguous action | reconcile before retry | duplicate effect |
| Reviewer backlog | narrow autonomy/exposure | silent bypass |
| Telemetry outage | degrade evidence/alert | block effects or lose audit silently |

## Evidence obligations
- Every queue and concurrency boundary is bounded or has a justified external bound.
- Deadlines propagate; retries cannot outlive the user/task budget.
- Critical and best-effort work have explicit priority/fairness policy.
- Operations cover model/tool/provider replacement and exit.

## Review questions
1. What happens when arrival rate stays above service rate?
2. Which dependency failure amplifies through loops or fan-out?
3. Can the system distinguish timeout from failed external effect?
4. What human workload becomes the bottleneck during incidents or ramps?

## Failure patterns
- Scale by hope: no saturation or shedding behavior.
- Retry storm: local resilience causes global failure.
- Hidden human queue: approvals/support omitted from capacity model.

## Research basis

Uses SRE capacity/reliability and Rust structured-concurrency principles [R102] [R103] [R106].
