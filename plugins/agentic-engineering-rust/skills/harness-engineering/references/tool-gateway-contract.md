# Tool gateway contract

Design tools for agent decisions, not as thin wrappers over internal endpoints. A tool contract must tell the model what outcome it provides, when to use it, what it changes, and how failure can be acted upon.

## Required contract

```yaml
name: issue.lookup
purpose: Retrieve authoritative issue state and selected comments.
input_schema: <JSON Schema>
output_schema: <JSON Schema>
side_effect_class: none | local_reversible | external_reversible | irreversible
capabilities: [issue:read]
timeout_ms: 10000
idempotency: not_applicable | caller_key | server_key | reconcile_required
approval_class: none | batch | per_action | prohibited
data_classification: internal
errors:
  - code: NOT_FOUND
    retryable: false
    repair: verify identifier
  - code: RATE_LIMITED
    retryable: true
    retry_after: required
```

## Naming and description

Name the task semantic action: `repository.search_symbols`, `deployment.promote`, `message.send`, not `call_api`. Front-load usage and non-usage conditions. Explain pagination, freshness, ordering, truncation, identifiers, side effects, and common confusion with adjacent tools.

## Schema rules

Use explicit enums, formats, ranges and descriptions. Prefer structured output over prose blobs. Preserve stable opaque IDs separately from display text. Make optionality meaningful; avoid “stringly typed” operations with several hidden modes. Validate both model-supplied input and service-supplied output.

## Side-effect protocol

Before an external effect:

1. normalize action and target;
2. authorize capability and environment;
3. obtain required approval;
4. allocate stable action/idempotency ID;
5. write intent to effect journal;
6. execute under deadline;
7. write observed result or ambiguous status;
8. verify/reconcile external state;
9. publish evidence to run state.

## Error taxonomy

Return machine-readable codes plus actionable context. Distinguish validation, authorization, not-found/stale-state, conflict, rate limit, timeout-before-dispatch, timeout-after-possible-dispatch, dependency outage, and invariant breach. Do not label all failures “retryable.”

## Security

Tool annotations and descriptions can be untrusted when discovered remotely; policy must not rely on them alone. Sanitize outputs that may contain instructions, secrets, markup or executable content. Bound output size. Log access without recording sensitive payloads unnecessarily.

## Evaluation cases

Test correct selection, refusal of wrong tool, malformed input repair, permission denial, pagination, stale target, timeout before/after dispatch, duplicate action ID, result truncation, output injection, and user-visible approval wording.
