# Multi-agent decision model

Multiple agents are an escalation for independent parallel work or genuinely distinct roles/context, not a synonym for high quality. Coordination cost can exceed capability gain.

## Preconditions

Use multiple agents only when most are true:

- work can be partitioned into meaningful packages with low overlap;
- each package has a bounded deliverable and local verification;
- shared state has one owner or a deterministic merge rule;
- parallelism reduces critical path or context interference materially;
- failure of one worker can be isolated or represented explicitly;
- integration budget and owner are reserved;
- permissions can be scoped per worker;
- the task is valuable enough to justify added cost and traces.

## Poor candidates

Avoid multi-agent for one tightly coupled edit set, one architecture decision that needs coherent global judgment, tasks dominated by shared mutable state, or work with no reliable way to grade worker outputs.

## Pattern choices

- **Orchestrator–workers:** orchestrator decomposes, assigns and integrates. Good for variable research/implementation packages.
- **Supervisor–specialists:** stable roles with distinct expertise/tools. Good when role boundaries are persistent.
- **Fan-out/fan-in:** deterministic partition and reducer. Prefer this over “agents” when workers do the same bounded operation.
- **Debate/ensemble:** use sparingly for consequential judgments with an independent adjudicator; correlated errors and cost remain.

## Coordination tax

Budget for decomposition, context packaging, worker startup, duplicate exploration, result normalization, conflict resolution, fan-in review, final verification and cancellation. Measure total accepted work per cost/latency, not number of workers.

## Go/no-go record

State: independent work packages; overlap risk; shared-state owner; expected critical-path gain; worker permissions; result schema; partial-failure behavior; integration owner; and the simpler single-agent alternative. Reject escalation if these cannot be specified.
