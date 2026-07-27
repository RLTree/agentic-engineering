# Trace and run-state schema

State answers “what is authoritative now?” Trace answers “how did it become so?” Keep them linked but do not use logs as the state store.

## Core identities

- `run_id`: one execution of an objective;
- `task_id`: stable work item across retries/resumptions;
- `node_id` / `attempt_id`: graph or loop execution instance;
- `action_id`: intended tool/effect operation;
- `artifact_id`: durable output and digest;
- `trace_id` / `span_id`: observability correlation.

IDs must remain stable across retry where identity is the same and change where a new semantic action is created.

## Run-state skeleton

```json
{
  "schema_version": 1,
  "run_id": "...",
  "status": "running",
  "objective_ref": "...",
  "topology": "bounded_loop",
  "current_node": "verify",
  "budgets": {"iterations_left": 3, "deadline": "...", "cost_left": 2.1},
  "facts": [],
  "assumptions": [],
  "decisions": [],
  "pending_approvals": [],
  "actions": [],
  "artifacts": [],
  "acceptance": [],
  "failure": null,
  "checkpoint_version": 8
}
```

## Lifecycle

Recommended statuses: queued, running, waiting, blocked, verifying, compensating, succeeded, failed, cancelled, escalated. Transitions must be enumerated and validated. `succeeded` requires acceptance evidence; `cancelled` records whether effects remain in flight; `failed` records recoverability and last safe checkpoint.

## Trace events

Record contract resolution, context retrieval/provenance, model request metadata, structured decision, policy check, approval, tool dispatch/result, state transition, checkpoint, effect reconciliation, verification, recovery, human intervention and artifact publication.

Avoid storing hidden model reasoning. Store observable inputs/outputs, decision summaries, policy results and evidence needed for debugging. Apply redaction at instrumentation source; tag sensitive fields and keep raw payload access separate.

## Evidence links

Each acceptance criterion should point to test/command/trace/artifact evidence with timestamp, target digest and outcome. Each completion statement should be reconstructable without reading free-form chat.

## Operational queries

The schema should support: runs stuck in a node; repeated actions; approval latency; tool failure by code; effect ambiguity; budget exhaustion; recovery success; verification failure; artifacts without evidence; and traces containing forbidden data.
