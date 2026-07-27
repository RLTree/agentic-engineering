# Autonomy and exposure ladder

Autonomy is not a binary product property. It is a scoped grant of decision and effect authority inside an operating envelope, with evidence-based promotion and demotion.

## Levels

| Level | Agent role | External effects | Minimum promotion evidence |
|---|---|---|---|
| Replay/offline | execute fixtures or historical tasks | none | deterministic correctness and known failure coverage |
| Observe-only | inspect live workflow without proposing action | none | privacy, access and representative-work controls |
| Shadow/silent | generate decisions/actions not shown or executed | none | trajectory quality, latency/cost and disagreement analysis |
| Recommendation-only | advise a human | human performs effect | useful recommendations, calibrated uncertainty, acceptable review burden |
| Approval-gated action | prepare action; named human approves | executed after approval | low ambiguity, reliable previews, safe idempotency/reconciliation, intervention learning |
| Bounded autonomy | act automatically on allowed low/medium-impact cases | constrained effects | stable guardrails, recovery, SLOs, representative field outcomes, rollback and incident readiness |
| Broader autonomy | act across a larger envelope | wider effects | sustained longitudinal evidence, governance, exception handling, auditability and demonstrated benefit |

## Promotion contract

Promotion requires:

- a named learning and product decision;
- evidence from the current level under representative conditions;
- no unresolved severe safety, security, privacy or effect-ambiguity failures;
- acceptable outcome, human-effort, reliability, cost and guardrail results by segment;
- verified rollback, kill switch, reconciliation and incident response;
- explicit authority and residual-risk acceptance;
- a smaller next blast radius than the maximum technically possible.

## Demotion and kill criteria

Demote, pause or stop when a guardrail breaches, data quality becomes unreliable, task distribution leaves the envelope, approval/intervention burden rises, effect outcomes become ambiguous, rollback fails, model/tool/harness versions materially change, severe incidents occur, or causal/qualitative evidence contradicts the expected value.

## Blast-radius budget

Specify limits for:

- users/accounts/tenants and task classes;
- effect value or irreversibility;
- data sensitivity and jurisdiction;
- model/tool calls, cost, latency and concurrency;
- cumulative errors, ambiguous outcomes and retries;
- duration and hours of operation;
- number of approval bypasses or emergency interventions.

## Oversight design

Oversight is a system, not a button. Define what the reviewer sees, what is hidden, expected review time, expertise, escalation, two-person control where needed, sampling of auto-approved successes, audit retention, and protection against approval fatigue. An approval gate that predictably receives blind clicks is not a control.

## Research basis

This ladder operationalizes current evidence on agent autonomy in practice, human oversight, deployed-AI monitoring, progressive delivery, and reliable launches [R73] [R75] [R93] [R94] [R106] [R107].
