# Effect safety and incident protocol

An agent incident is any loss or credible near loss of control over permissions, sensitive data, external effects, durable state, or auditability. Optimize first for containment and truth, not task completion.

## Immediate containment

1. stop new intake and fan-out;
2. cancel active runs and revoke scoped credentials/capabilities;
3. disable affected tools/routes or move to read-only;
4. preserve immutable logs, checkpoints, approvals and effect journals;
5. identify in-flight/ambiguous external effects and reconcile them;
6. rotate exposed secrets and isolate compromised workers/services;
7. notify the authorized incident owner.

Do not delete evidence, blindly retry, or allow the same model/context to “fix” the incident with unchanged privilege.

## Triage record

- detection time and reporter;
- affected runs, identities, tools, targets and data;
- suspected entry vector and provenance;
- confirmed and ambiguous effects;
- credentials/capabilities at risk;
- containment actions;
- current authoritative state;
- customer/system impact;
- legal/security escalation owner.

## Recovery

Restore from a verified checkpoint only after the causal control gap is fixed. Reconcile external state, compensate where appropriate, invalidate poisoned memory/context, reissue minimal credentials, replay under read-only/fake dependencies first, and verify invariants before resuming production effects.

## Learning loop

Produce a causal timeline and control-layer diagnosis. Add failure-derived evals; tighten schemas/capabilities/approvals; improve trace/redaction; update AGENTS.md/skills/runbooks only where prose is the right mechanism; and add deterministic enforcement for recurring invariants.

## Close criteria

All external effects classified; sensitive exposure assessed; credentials remediated; durable state repaired/versioned; causal vulnerability fixed and regression-tested; monitoring updated; residual risk accepted by an authorized owner; and evidence retained according to policy.
