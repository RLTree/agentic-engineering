# Harness reference architecture

A harness is the control plane around model capability. It converts intent into bounded execution, assembles context, routes tools, enforces policy, persists state, records evidence, recovers from failure, and hands off durable artifacts. Sandboxes and workers are execution planes; isolation does not replace authorization.

## Logical components

```text
Request / issue / trigger
        |
Execution contract + policy resolver
        |
Run coordinator ---- durable run state ---- trace/evidence store
        |                    |                       |
Context assembler       checkpoint/recovery      eval/grader
        |
Model gateway ---- model output validator
        |
Decision router / loop / graph
        |
Tool gateway ---- authorization ---- approval ---- effect journal
        |
Sandbox / worker / external service
        |
Verification oracle ---- artifact registry ---- handoff
```

## Responsibilities

**Contract resolver** normalizes objective, constraints, deliverables, autonomy and verification. It rejects contradictory or policy-incompatible requests before execution.

**Context assembler** retrieves high-signal repository/state/evidence with provenance and isolates untrusted content from control instructions.

**Model gateway** standardizes model selection, effort, timeouts, structured output, rate/cost accounting, retry classification and trace links. It must not hide provider errors behind generic text.

**Run coordinator** owns lifecycle, budgets, cancellation, authoritative state, node/action IDs, checkpoints and terminal status.

**Tool gateway** exposes task-semantic contracts, validates input/output, checks capability scope, obtains approvals, applies deadlines, and records effects.

**Execution plane** runs code or invokes services under identity, environment, filesystem/network and resource boundaries.

**Verification oracle** evaluates acceptance evidence independently of the model’s completion claim where possible.

## Model versus deterministic responsibility

Use the model for semantic interpretation, ambiguous planning, synthesis and generation. Use deterministic code for authorization, schemas, invariant checking, state transitions, budget accounting, routing rules that can be enumerated, deduplication, effect recording and release gates.

## Deployment boundaries

Keep control state outside ephemeral sandboxes. Give workers scoped credentials rather than coordinator credentials. Separate read and write tools when their consequence classes differ. Prefer append-only evidence/effect records with immutable IDs. Redact or tokenize secrets before traces leave the execution boundary.

## Review invariants

- no effect without an authorized action record;
- no terminal success without acceptance evidence;
- no retry of an ambiguous effect without reconciliation/idempotency;
- no task without cancellation and budget ownership;
- no untrusted content silently promoted to policy;
- no approval that obscures target or consequence;
- no crash/restart path that depends on transcript reconstruction.
