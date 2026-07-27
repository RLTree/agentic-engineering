---
name: harness-engineering
description: "Use when reliability depends on tools, permissions, sandboxes, state, effects, tracing, recovery, or runtime control."
---

# Harness Engineering

## Core principle

The harness owns guarantees the model cannot reliably enforce on itself. Treat the model as a semantic decision component inside a typed, observable, least-privilege, recoverable control plane.

## Workflow

### 1. Define control and execution planes

Separate the harness/control plane from sandboxes, workers and external services that execute effects. Name identities, trust boundaries, state stores and communication channels.

### 2. Inventory model decisions and deterministic controls

For each step, decide whether it belongs to model judgment, policy, validation, routing, authorization, state transition, effect execution or human judgment. Read [the harness reference architecture](references/harness-reference-architecture.md).

### 3. Design tool contracts

Give every tool a precise schema, semantic description, side-effect class, permission scope, timeout, idempotency behavior and actionable error taxonomy. Use [the tool gateway contract](references/tool-gateway-contract.md).

### 4. Define run state and lifecycle

Model queued, running, waiting, blocked, verifying, succeeded, failed, cancelled and escalated states. Persist stable run/task/action IDs, budgets, decisions, evidence and effects.

### 5. Place approvals at consequence boundaries

Require approval based on target, operation, data sensitivity, reversibility, cost and blast radius—not because the action is “a tool call.” The approval must show normalized intent and expected effect.

### 6. Engineer recovery

Classify transport/transient errors, invalid action, missing evidence, policy denial, stale state, dependency failure and invariant breach. Define retry, repair, replan, compensate, reconcile, escalate and terminate paths.

### 7. Make traces useful

Trace model calls, context provenance, tool decisions, policy checks, state transitions, effects, verification and human interventions with redaction and stable correlation IDs.

### 8. Threat-test and evaluate

Exercise injection, denied permissions, tool timeout, malformed results, duplicate effects, crash/restart, budget exhaustion and verification failure before production.

## Output contract

Return a **Harness Blueprint** with:

- component and trust-boundary diagram in text;
- model-versus-deterministic responsibility matrix;
- tool gateway and permission model;
- run-state schema and lifecycle;
- approval classes;
- budgets, recovery and effect-safety policy;
- trace schema and redaction plan;
- failure-injection and evaluation plan.

## Common failures

- **Prompt as permission system:** permissions and irreversible actions depend on compliance. Enforce outside the model.
- **Tool-shaped API wrappers:** schemas expose implementation detail but not task semantics or side effects. Redesign for agent use.
- **Sandbox equals authorization:** isolation is treated as full authorization. Apply identity, scope and approval independently.
- **Retry every error:** invalid or unsafe actions repeat. Classify retry versus repair versus escalation.
- **Opaque run state:** recovery and audit require transcript archaeology. Persist typed lifecycle and evidence.
- **Telemetry without decisions:** token counts exist but state, tool and effect causality are missing. Trace the control path.

## References

- [Harness reference architecture](references/harness-reference-architecture.md)
- [Tool gateway contract](references/tool-gateway-contract.md)
- [Recovery and effect safety](references/recovery-effect-safety.md)
- [Trace and run-state schema](references/trace-run-state-schema.md)

## Shared references

- [Seven-layer map](../../references/seven-layer-map.md)
- [Architecture escalation](../../references/architecture-escalation.md)
- [GPT-5.6 Sol operating profile](../../references/gpt-5.6-sol-operating-profile.md)
- [Evidence and confidence](../../references/evidence-and-confidence.md)

## Version 3 control contracts

A consequential harness design should support:

- `NoChangeDecision` before mutation;
- `TaskEvidencePacket` for bounded workers;
- `ReviewVerdict` for candidate-bound independent review;
- `RepairLoopContract` with structured feedback and semantic circuit breaking;
- layer-aware trace attribution before harness repair;
- continuous monitoring and update for agent security rather than one-time guardrails.

Read `../../references/no-change-and-abstention.md`, `../../references/task-evidence-and-review-contracts.md`, and `../../references/repair-budget-and-feedback.md`.
