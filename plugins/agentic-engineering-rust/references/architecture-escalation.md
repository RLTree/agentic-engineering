# Architecture escalation: choose the smallest fitting topology

Architecture is a cost decision. Every increase in autonomy or topology introduces state, testing, observability, recovery and security obligations. Escalate only when the simpler form cannot satisfy a named requirement.

## Level 0 — Direct model call

Use when one bounded semantic transformation can be evaluated at the output boundary: summarize, classify, extract, draft, explain or produce one structured object.

Required controls: explicit input/output schema, validation, deterministic post-processing and fallback.

Do not add a loop merely to make the request sound agentic.

## Level 1 — Deterministic workflow

Use when the stages and routing are known in advance. Examples: retrieve → transform → validate → publish; classify → route → specialized handler; parallel independent analyses → deterministic reducer.

Required controls: stage contracts, typed handoffs, failure policy, observability and test fixtures.

Prefer this over an agent when code can determine the next step.

## Level 2 — Bounded agent loop

Use when the next useful action cannot be prescribed before observing tool results, repository state or verification feedback.

Required controls: typed run state; observe–orient–plan–act–verify–update phases; action/time/token/cost/side-effect budgets; progress and convergence measures; retry versus repair classification; explicit terminal, blocked and escalated states.

A loop without a verification oracle and stop policy is an unbounded retry machine.

## Level 3 — Explicit state graph

Use when branches, cycles, joins, interrupts, human decisions, parallel work or recovery paths need to be inspectable and testable as first-class structure.

Required controls: state schema; node preconditions/postconditions; edge predicates; reducer laws; checkpoint identity; idempotent replay; interrupt/resume contract; graph-level invariant tests.

Do not hide the graph inside one giant prompt.

## Level 4 — Durable workflow

Use when work must survive process failure, deployment, long delays, human latency, duplicate delivery or at-least-once execution.

Required controls: durable checkpoint or event history; idempotency keys; effect journal; outbox/inbox; leases or ownership fencing; retry schedule; replay-safe decisions; compensation or reconciliation; migration/version policy.

Persistence alone is not durability. The system must reproduce decisions safely after interruption.

## Level 5 — Multi-agent system

Use when parallelism or specialization produces material benefit that exceeds coordination cost. Good candidates have separable work, non-overlapping ownership, independent evidence and a deterministic integration point.

Required controls: delegation contract; authoritative task/state owner; dependency graph; isolation, usually worktrees or separate artifacts; communication budget; worker evidence contract; merge/reducer policy; duplicate/conflict handling; cancellation and partial-failure semantics.

Do not use multiple agents to compensate for an underspecified task, weak context or missing verification.

## Escalation questions

Move upward only when the answer is **yes**:

1. Does the next action genuinely depend on evidence not yet available?
2. Must branching, cycling or human interruption be explicit and resumable?
3. Must the run survive time, process failure or duplicate delivery?
4. Can the work be split into meaningful, low-coupling parts with a clear merge contract?
5. Is the added control architecture worth its operational and evaluation burden?

## De-escalation questions

Move downward when:

- the route is already known;
- a deterministic validator can replace model judgment;
- retries repeat the same action without new information;
- parallel agents share mutable files or decisions;
- the only rationale is novelty, fashion or a desire to call the system agentic.

## Default recommendation

Start with a deterministic workflow containing a single bounded model step. Add one capability at a time, tied to a failing requirement and a regression evaluation.
