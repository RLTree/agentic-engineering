# Architecture decision table

Escalate architecture only when a named requirement cannot be satisfied by a simpler topology. Complexity creates coordination, state, observability, security, and testing obligations.

## Selection table

| Topology | Choose when | Do not choose merely because | New obligations |
|---|---|---|---|
| Direct model call | one semantic transformation; bounded context; no tools or durable state | the task sounds “AI-like” | schema/output validation, input provenance |
| Deterministic workflow | steps and branches are known; model is a component in fixed control flow | there are several steps | step contracts, error propagation, test fixtures |
| Router | inputs require classification into known handlers | one prompt could mention several cases | routing oracle, fallback, confidence/ambiguity policy |
| Fan-out/fan-in | independent items or evidence sources can run concurrently | parallelism appears faster | partitioning, bounded concurrency, reducer, partial-failure rule |
| Evaluator–optimizer | quality can be judged by a repeatable rubric and repaired locally | “iterate until good” sounds appealing | grader reliability, iteration budget, best-so-far retention |
| Bounded agent loop | the next action must adapt to evidence and available tools | the model has tools | authoritative state, action budgets, stop/recovery policy, effect safety |
| Explicit state graph | consequential branches/cycles/joins/interrupts/recovery must be visible | a diagram looks professional | typed state, node/edge contracts, reducers, checkpoints, versioning |
| Durable workflow | work must survive process loss, long waits, or human latency | the task is long | replay-safe code, durable timers/state, idempotent effects, migrations |
| Multi-agent system | meaningful work packages are independent or require distinct context/roles | the task is difficult | delegation contracts, ownership, fan-in, cancellation, coordination evals |

## Decision sequence

Ask these questions in order:

1. Can one call produce the result under a verifiable schema?
2. Is the path known enough to encode in deterministic code?
3. Does only the handler vary, or does the next action depend on evidence?
4. Are branches, cycles, joins, or approval interrupts consequential enough to externalize?
5. Must execution survive restart or wait longer than a process/session lifetime?
6. Is there enough independent work to outweigh multi-agent coordination cost?

Stop at the first sufficient topology. Compose patterns locally rather than labeling the entire system with its most complex component.

## Escalation evidence

A recommendation must cite the requirement that causes each escalation:

- **Loop:** “The tool result determines which query or repair is next.”
- **Graph:** “Failure, approval, and verification produce different resumable paths.”
- **Durability:** “The workflow waits for human review and must resume after deployment.”
- **Multi-agent:** “Four repositories can be inspected independently, then merged by one integration owner.”

Statements such as “more robust,” “more agentic,” or “enterprise grade” are not escalation evidence.

## De-escalation triggers

Record what would allow simplification. Examples: a formerly open-ended route becomes a finite rules table; a human interrupt disappears; one worker can complete the task within latency limits; or a durable run is no longer needed. Architecture should be reversible where practical.

## Architecture scorecard

Before commitment, score 0–2 for: adaptive uncertainty, branch visibility, persistence need, parallel independence, side-effect risk, human latency, auditability, and recovery complexity. The score is not a mechanical selector. It forces the rationale to name actual pressure. Any topology above a deterministic workflow requires an explicit verification oracle and failure policy.
