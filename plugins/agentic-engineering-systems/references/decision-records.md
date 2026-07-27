# Decision records for agentic systems

Record decisions that constrain future work, not every thought.

## Agentic architecture decision record

Use an ADR when choosing topology, state ownership, durable runtime, protocol, provider/framework boundary, approval model or security posture.

Required fields:

- **Context:** current system, pressure and evidence.
- **Decision:** one precise commitment.
- **Alternatives:** at least two credible options and why they lost.
- **Consequences:** benefits, costs, new failure modes and operational obligations.
- **Invariants:** conditions that must remain true.
- **Validation:** tests/evals/telemetry that support the decision.
- **Revisit trigger:** fact, scale, failure or dependency change that should reopen it.

## Assumption ledger

For substantial Codex work, maintain:

| Assumption | Reversible? | Consequence if wrong | Validation | Owner | Status |
|---|---|---|---|---|---|

Proceed without asking when an assumption is reversible, low-consequence and testable. Escalate when it changes public contracts, data, security, cost, architecture or user-visible product direction.

## Effect decision record

Before an external side effect, persist:

- stable run/task/action identifiers;
- requested operation and normalized parameters;
- target resource and authorization context;
- idempotency key;
- precondition/version;
- approval record when required;
- attempt count and timestamps;
- result, receipt or error;
- reconciliation/compensation state.

The effect record is the boundary between model intent and deterministic execution.

## Handoff record

A reviewable handoff should include:

1. objective and scope completed;
2. decisions and assumptions;
3. files/artifacts changed;
4. commands and exact results;
5. acceptance-to-evidence mapping;
6. known limitations and residual risks;
7. follow-up work that was deliberately excluded.

Do not use the chat transcript as the only durable record.
