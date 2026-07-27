# Control architecture review

Use this review before implementation, at design approval, and after a production incident. It tests whether important decisions live in enforceable mechanisms rather than optimistic prose.

## Review packet

Require these artifacts:

- outcome and acceptance-to-evidence matrix;
- component/trust-boundary view;
- authoritative state schema and ownership;
- model-versus-deterministic responsibility matrix;
- tool/effect catalog;
- loop or graph contract;
- budgets and stop/escalation policy;
- recovery and replay policy;
- security/approval policy;
- evaluation and observability plan.

## Questions

### Outcome and ownership

- What durable artifact or external state is the unit of value?
- Which actor is authoritative for each mutable field?
- Which invariants can be checked by code, and where are they checked?
- What decision remains intentionally human?

### Model boundary

- Is the model used for semantic judgment rather than deterministic validation or authorization?
- Are ambiguous model outputs rejected, repaired, or mapped through a typed adapter?
- Can retrieved or tool-provided text become control instruction without provenance and policy?

### State and flow

- Can every consequential transition be named and observed?
- Are retries distinguished from replans, repairs, reconciliation, and compensation?
- What happens after crash/restart at each side-effect boundary?
- Are joins deterministic and partial failures explicit?

### Effects and permissions

- Does every external effect have a stable action ID and outcome record?
- Are permissions scoped by identity, target, operation, duration, and environment?
- Does approval show normalized intent, target, expected effect, reversibility, and evidence?
- Can the system determine whether an ambiguous timed-out effect occurred?

### Verification and operations

- Does every completion claim map to observable evidence?
- Are outcome, trajectory, recovery, and safety evaluated separately?
- Can a trace reconstruct state, decisions, tool calls, approvals, effects, and verification without exposing secrets?
- Are kill switch, cancellation, drain, and incident procedures defined?

## Severity model

- **Blocker:** missing authorization boundary, irreversible effect without idempotency/reconciliation, no completion oracle, unowned state, or unsafe replay.
- **Major:** hidden branch/retry semantics, unbounded loop/queue, weak provenance, no recovery test, or non-deterministic fan-in.
- **Moderate:** unclear terminology, missing performance budget, incomplete telemetry, or excessive context.
- **Minor:** documentation, naming, or ergonomics that do not alter correctness.

## Review result

Return: decision; blockers; accepted risks; required changes; evidence needed for approval; owner and deadline; and explicit revisit triggers. “Approved with comments” is not sufficient unless every comment is classified as blocking or non-blocking and linked to evidence.
