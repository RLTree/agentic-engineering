# Trace evidence schema

An eval-ready trace captures observable causal events without relying on hidden reasoning. It must connect objective, context, decisions, state, actions, effects and acceptance evidence.

## Event envelope

```json
{
  "schema_version": 1,
  "timestamp": "...",
  "run_id": "...",
  "task_id": "...",
  "trace_id": "...",
  "span_id": "...",
  "parent_span_id": "...",
  "event_type": "tool.result",
  "actor": "worker:runtime-review",
  "state_version": 7,
  "data_classification": "internal",
  "payload": {},
  "evidence_refs": []
}
```

## Event types

contract.resolved, context.retrieved, model.request/response, decision.recorded, policy.checked, approval.requested/resolved, node.entered/exited, action.intended/dispatched/resolved, tool.result, state.updated/checkpointed, verification.result, recovery.selected, artifact.published, run.terminal.

## Evidence object

Include criterion ID, evidence type, target artifact/state ID and digest, method/command, environment, timestamp, outcome, raw-result pointer, grader/version and limitations. Evidence should be immutable or content-addressed when possible.

## Privacy and security

Do not record secrets, access tokens, full sensitive documents, or hidden model reasoning. Redact/tokenize at source, classify fields, restrict raw payload access and test redaction. Preserve enough normalized metadata to debug permission and effect decisions.

## Trace quality checks

- stable IDs link all actions and effects;
- every state transition has cause and prior/new version;
- approvals link to exact normalized action;
- terminal success links to all required criteria;
- ambiguous effects remain visible until reconciled;
- sampling never removes security/effect events needed for audit;
- clock/order ambiguity is handled with sequence or causal parentage.

## OpenTelemetry alignment

Map model/agent/tool spans to current OpenTelemetry GenAI conventions where practical, but version your internal semantic layer because the conventions may evolve. Do not expose sensitive prompts solely to satisfy a telemetry convention.
