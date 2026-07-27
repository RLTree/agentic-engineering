---
name: agent-security-governance
description: "Use when agents handle untrusted input, capabilities, secrets, external effects, approvals, identity, or incidents."
---

# Agent Security and Governance

## Core principle

Treat model output and retrieved content as untrusted proposals. Authorization, validation, irreversible effects and data boundaries must be enforced by deterministic systems with human control at consequence thresholds.

## Workflow

### 1. Model assets, actors and trust boundaries

Identify user, agent, model provider, tools, MCP/A2A peers, data stores, sandboxes, external systems, operators and attackers. Mark where instructions, data, credentials and effects cross trust boundaries.

### 2. Classify data and capabilities

For each tool or service, define identity, scopes, resources, operations, duration, environment and data classes. Use separate read and write capabilities. Deny by default.

### 3. Preserve provenance and instruction hierarchy

Label system/project/user instructions, trusted facts, tool data, retrieved content and model inference. Never promote untrusted content to control instructions. Read [the injection and provenance model](references/injection-provenance.md).

### 4. Gate effects by consequence

Classify operations by reversibility, external visibility, privilege, data sensitivity, cost and blast radius. Require normalized preview, target, diff/parameters, expected outcome and approval for high-consequence effects. Use [the approval and capability policy](references/approval-capability-policy.md).

### 5. Enforce tool safety

Validate schemas and business rules; authorize every call and state handle; time out and rate-limit; use idempotency keys; sanitize outputs; validate structured results; log usage; redact secrets.

### 6. Bound autonomous behavior

Set budgets, allowed domains/resources, network policy, secret access, data egress and kill switch. Make policy denial a terminal or escalation state, not a prompt to evade safeguards.

### 7. Threat-test the system

Exercise indirect prompt injection, data exfiltration, confused deputy, tool poisoning, schema smuggling, stale approval, replay, duplicate effect, privilege escalation, cross-tenant access and malicious peer-agent messages.

### 8. Define governance and incident response

Record owners, approvals, audit retention, exception process, model/tool/version inventory, evaluation gates, rollout, rollback, credential rotation, effect reconciliation and notification procedures. When controls are exercised through representative live exposure, compose with `$authentic-use-engineering`; when preparing the exact production artifact, compose with `$secure-delivery-release`.

## Output contract

Return an **Agent Threat and Governance Plan** with:

1. assets, actors and trust boundaries;
2. data/capability classification;
3. provenance and instruction policy;
4. tool authorization and validation controls;
5. effect/approval matrix;
6. budgets, isolation and emergency-stop design;
7. abuse/fault test cases;
8. audit, governance and incident-response plan.

## Common failures

- **Ambient broad credentials:** the agent is told not to misuse broad credentials. Enforce least privilege.
- **Approval without exact target/effect:** users habituate and approve blindly. Gate by consequence.
- **Sandbox equals trust:** isolated code still has authorized effects or data. Separate execution and capability boundaries.
- **Untrusted content as policy:** content injection controls actions. Preserve provenance.
- **State handle as capability:** opaque IDs bypass authorization. Reauthorize every operation.
- **Audit without recovery:** logs exist but duplicate/unsafe effects cannot be reconciled. Add effect records and playbooks.

## References

- [Threat model](references/agent-threat-model.md)
- [Injection and provenance](references/injection-provenance.md)
- [Approval and capability policy](references/approval-capability-policy.md)
- [Effect safety and incident response](references/effect-safety-incident.md)

## Shared references

- [Seven-layer map](../../references/seven-layer-map.md)
- [Architecture escalation](../../references/architecture-escalation.md)
- [GPT-5.6 Sol operating profile](../../references/gpt-5.6-sol-operating-profile.md)
- [Evidence and confidence](../../references/evidence-and-confidence.md)

## Version 3 continuous security posture

Treat fixed guardrails as one layer, not a permanent proof of robustness. Require continuous red-team discovery, monitored deployment, update paths, identity-bound authorization, effect containment, rapid recovery, and post-incident learning. Security, privacy, authorization, and destructive-effect boundaries remain mandatory under every proportional assurance profile.
