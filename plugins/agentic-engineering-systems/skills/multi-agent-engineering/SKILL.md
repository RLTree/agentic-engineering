---
name: multi-agent-engineering
description: "Use when work may divide into independent agent streams and needs ownership, evidence, fan-in, or cancellation."
---

# Multi-Agent Engineering

## Core principle

Multiple agents are a coordination architecture, not a quality toggle. Use them only for meaningful, low-coupling decomposition with explicit authority and deterministic integration.

## Workflow

### 1. Run the parallelism test

Estimate independent work, critical path, shared-state coupling, communication volume, merge difficulty, failure blast radius and verification cost. Read [the multi-agent decision model](references/multi-agent-decision-model.md).

### 2. Define authoritative orchestration

Name the task owner, source of truth, dependency graph, work package lifecycle and who may create, reassign, cancel, merge or close work.

### 3. Write delegation contracts

Every package must include objective, context slice, owned files/artifacts, exclusions, dependencies, deliverable schema, evidence, budget, stop condition and escalation path. Use [the delegation contract](references/delegation-contract.md).

### 4. Isolate work

Prefer worktrees, separate branches or immutable artifact outputs. Avoid concurrent edits to the same files or decisions. Provide a protocol for shared discoveries without turning chat into authoritative state.

### 5. Bound communication

Choose report-at-completion, milestone, event or query-based communication. Require concise evidence-bearing messages and stable identifiers. Avoid continuous unconstrained peer chatter.

### 6. Define fan-in and integration

Specify ordering, conflict resolution, missing/failed worker policy, provenance, integration owner and final system-level verification. The supervisor must not merely concatenate plausible answers.

### 7. Handle cancellation and partial failure

Define dependency cancellation, orphan cleanup, budget exhaustion, stale work, duplicated tasks and whether partial results are usable.

### 8. Evaluate against a single-agent baseline

Measure quality, elapsed time, total tokens/cost, coordination errors, duplicate work, merge defects and reviewer effort. Keep multi-agent only when it wins on the target distribution.

## Output contract

Return a **Multi-Agent Coordination Plan** with:

1. evidence that parallelism/specialization is justified;
2. orchestrator authority and task-state model;
3. dependency graph and work packages;
4. ownership/isolation rules;
5. delegation and communication contracts;
6. fan-in/merge policy;
7. cancellation and partial-failure behavior;
8. single-agent versus multi-agent evaluation plan.

## Common failures

- **Parallelism because task is hard:** subagents are used for a monolithic task. Decompose first or stay single-agent.
- **Several agents editing same state without owner:** workers edit the same files or decide the same architecture. Partition work.
- **Consensus treated as proof:** no deterministic merge or final oracle. Define integration semantics.
- **Communication explosion:** token/cost and contradictions erase parallel speed. Bound messages.
- **No cancellation propagation:** invalidated work continues consuming resources. Model dependency cancellation.
- **No baseline:** complexity is retained without evidence it helps. Compare against a strong single-agent run.

## References

- [Multi-agent decision model](references/multi-agent-decision-model.md)
- [Delegation contract](references/delegation-contract.md)
- [Coordination and fan-in](references/coordination-fan-in.md)
- [Ultra operating protocol](references/ultra-operating-protocol.md)

## Shared references

- Seven-layer map (canonical repository reference library: seven-layer-map.md)
- Architecture escalation (canonical repository reference library: architecture-escalation.md)
- GPT-5.6 Sol operating profile (canonical repository reference library: gpt-5.6-sol-operating-profile.md)
- Evidence and confidence (canonical repository reference library: evidence-and-confidence.md)

## Version 3 worker and reviewer evidence

Parallelize only dependency-independent work. The root owns shared schemas, dependencies, public APIs, migrations, effect authority, claim promotion, and final acceptance. Each child has one Task Evidence Packet, disjoint path and semantic ownership, an explicit budget, cancellation lineage, and one return envelope. Reviewers return candidate-bound Review Verdicts. Close completed children after evidence is consumed and distinguish mailbox silence from liveness. Read the canonical repository reference library (task-evidence-and-review-contracts.md) and the canonical repository reference library (repair-budget-and-feedback.md).
