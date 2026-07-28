# Dependency and capacity plan

Agentic products depend on models, tool providers, queues, data stores, identity/policy, observability, human reviewers and vendors. Capacity planning must include workload mix, fan-out, retries, approvals, external quotas, degradation and cost—not only average requests per second.

## Vocabulary
- **dependency budget:** Allowed contribution of a dependency to latency, error, availability, cost and recovery.
- **fan-out multiplier:** Number of downstream/model/tool operations generated per user task or loop iteration.
- **saturation point:** Load at which queues, latency, errors or quality degrade nonlinearly.
- **degradation mode:** Deliberate reduced capability when a dependency or resource is constrained.
- **human capacity:** Available reviewer/operator/support time and expertise as a system resource.

## Decision procedure
1. Model representative workload by task class, arrival pattern, concurrency, loop depth, fan-out, payload, model/tool mix, and effect type.
2. Inventory internal/external and human dependencies, quotas, SLOs, contracts, data/security constraints, failure modes, retry semantics and alternatives.
3. Compute end-to-end latency/cost/error budgets and worst credible amplification from retries, workers and graph branches.
4. Define bounds, admission control, backpressure, queue policy, deadlines, circuit breaking, degradation, caching, batching and failover.
5. Test nominal, burst, saturation, dependency failure, quota exhaustion, slow approval and recovery; validate telemetry.
6. Set forecasts, triggers, ownership, vendor/exit plans and rollout capacity gates.

## Decision table

| Constraint | Control | Evidence |
|---|---|---|
| Model/tool quota | admission + concurrency limits | quota-exhaustion test |
| Slow downstream | absolute deadlines + bounded queues | tail latency/saturation test |
| Retry amplification | semantic action budget + jitter/backoff | fault-injection trajectory |
| Reviewer bottleneck | risk-based sampling/approval routing | approval latency and fatigue evidence |
| Provider outage | degrade/failover/hold effects | game day and runbook |

## Evidence obligations
- Capacity includes tokens, tool calls, state size, trace volume, human review and external effect rates.
- Retries respect deadlines and idempotency; ambiguous outcomes are reconciled before redispatch.
- Load tests use realistic task distributions and fan-out, not a single simple endpoint.
- Cost guardrails are segmented by outcome and task class.

## Review questions
1. What multiplies one user request into many model/tool/effect calls?
2. Where does backpressure surface to users and agents?
3. What happens to authoritative state on timeout or partial failure?
4. Which human or vendor dependency has no capacity/exit plan?

## Failure patterns
- Average-load planning: tails, bursts and loop amplification ignored.
- Unbounded resilience: retries and parallelism worsen an outage.
- CPU-only capacity: tokens, quotas, trace volume and reviewer labor omitted.

## Research basis

Grounded in SRE capacity/reliability, reliable launches, Rust async controls, and agent loop budgets [R102] [R103] [R106].
