---
name: agent-first-software-engineering
description: "Use when a repository or delivery system must become legible, verifiable, resumable, and correction-resistant for agents."
---

# Agent-First Software Engineering

## Core principle

Treat the repository, issue tracker, tests, CI and artifacts as the interface through which agents work. Human attention should resolve priorities and consequential decisions, while durable systems make routine correctness discoverable and enforceable.

## Workflow

### 1. Assess repository readiness

Evaluate discoverability, composition roots, public contracts, modularity, testability, run commands, deterministic checks, generated code, dependency boundaries and fresh-agent onboarding. Use [the agent-ready repository rubric](references/agent-ready-repository-rubric.md).

### 2. Establish issue-to-artifact control

Make the work item the authoritative objective, scope, acceptance and status record. Define branch/worktree, plan, implementation, verification, review and merge artifacts.

### 3. Use executable plans for substantial work

Write milestones, file/contract impacts, risk, tests and evidence. Keep progress and decisions current so another agent can resume. Read [the issue-to-artifact protocol](references/issue-to-artifact-protocol.md).

### 4. Isolate parallel work

Use worktrees or branches with non-overlapping ownership. Define dependency and integration order. Avoid agents sharing uncommitted mutable state.

### 5. Make verification local and exact

Provide one-command format/lint/check/test paths where practical. Add architecture fitness tests, contract tests, migrations, package/deploy checks and end-to-end evidence for the exact delivered artifact.

### 6. Review from a fresh context

Use an independent reviewer or new session to inspect intent, diff, tests, security, performance, maintainability and evidence. Review the smallest coherent diff, not the conversation.

### 7. Turn correction into infrastructure

For every repeated reviewer instruction, choose AGENTS.md, a skill, template, test, linter, hook, CI rule, tool schema or approval policy. Use [the correction-to-infrastructure ladder](references/correction-infrastructure-ladder.md).

### 8. Measure the operating system

Track lead time, rework, escaped defects, verification coverage, review effort, failed handoffs, agent stalls and recurring correction categories—not only generated lines or task count.

## Output contract

Return an **Agent-Ready Repository and Delivery Plan** with:

- repository readiness findings;
- issue/spec/plan/artifact lifecycle;
- guidance and skill layout;
- worktree/parallel ownership policy;
- local and CI verification commands;
- fresh-context review and exact-delivery checks;
- correction-to-infrastructure backlog;
- process metrics and rollout stages.

## Common failures

- **Agent as autocomplete:** no durable issue, plan or artifact flow. Design the operating system.
- **Conversation as artifact:** work cannot resume or be reviewed independently. Persist plans and evidence.
- **Huge ambiguous diff:** agents optimize broadly. Use scope, anti-goals and work packages.
- **Source-only verification:** package, migration or deployed behavior is untested. Verify exact delivery.
- **Massive agent manual instead of enforcement:** every agent relearns rules. Encode and enforce them.
- **Throughput vanity:** more parallel tasks increase integration debt. Measure review and escaped defects.

## References

- [Agent-ready repository rubric](references/agent-ready-repository-rubric.md)
- [Issue-to-artifact protocol](references/issue-to-artifact-protocol.md)
- [Correction-to-infrastructure ladder](references/correction-infrastructure-ladder.md)
- [Delivery verification](references/delivery-verification.md)

## Shared references

- Seven-layer map (canonical repository reference library: seven-layer-map.md)
- Architecture escalation (canonical repository reference library: architecture-escalation.md)
- GPT-5.6 Sol operating profile (canonical repository reference library: gpt-5.6-sol-operating-profile.md)
- Evidence and confidence (canonical repository reference library: evidence-and-confidence.md)

## Version 3 compounding without duplicate authority

Turn recurring corrections into the smallest reusable infrastructure, but adopt them through `engineering-learning-loop`. Keep one authoritative learning registry and generate discoverable human projections with reverse links. Measure whether each rule, skill, tool, or validator reduces future work; narrow or retire mechanisms whose attention and maintenance cost exceeds their benefit. Read the canonical repository reference library (knowledge-evolution-and-garbage-collection.md).
