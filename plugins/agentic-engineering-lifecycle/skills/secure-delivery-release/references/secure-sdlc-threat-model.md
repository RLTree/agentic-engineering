# Secure SDLC and threat model

Secure agentic delivery models data, instructions, identities, tools, effects, dependencies, humans and operations as trust boundaries. Controls belong in architecture, schemas, permissions, runtime and verification—not only prompts.

## Vocabulary
- **trust boundary:** Point where data, instructions, authority or execution crosses between differently trusted principals/components.
- **confused deputy:** Authorized component tricked into using its authority for an untrusted requester or instruction.
- **indirect prompt injection:** Untrusted content that attempts to become control instructions through retrieval, tools or documents.
- **capability:** Specific permission to access data, invoke a tool, perform an effect or delegate authority.
- **abuse case:** Adversarial or misuse scenario describing actor, goal, path, impact and controls.

## Decision procedure
1. Define assets, actors, identities, data/instruction provenance, operating envelope, effect classes and lifecycle boundaries.
2. Map data/control flows and trust boundaries across user, model, context, retrieval, tools, protocols, storage, runtime, deployment and operators.
3. Enumerate threats: injection, data exfiltration, excessive agency, tool abuse, authorization bypass, supply chain, poisoning, cross-tenant leakage, denial/cost, unsafe delegation, logging leakage and incident concealment.
4. Select least privilege, isolation, schema validation, provenance separation, server-side authorization, approvals, quotas, effect identity/reconciliation, redaction and monitoring.
5. Write abuse/misuse cases and security acceptance evidence; test bypass, denied, compromised and recovery paths.
6. Maintain threat model through model/tool/workflow/version changes and field incidents.

## Decision table

| Threat | Primary control layer | Evidence |
|---|---|---|
| Untrusted content controls agent | context provenance + instruction/data separation | injection fixtures/red team |
| Unauthorized effect | identity/policy/least privilege/approval | policy integration tests |
| Tool argument abuse | closed schema + semantic validation | contract/property tests |
| Ambiguous external action | idempotency + journal + reconciliation | fault/replay tests |
| Telemetry leakage | redaction/minimization/access/retention | privacy tests/audit |

## Evidence obligations
- The model never decides its own authorization.
- Isolation limits execution reach but does not substitute for permission checks.
- Secrets are scoped, short-lived where possible, and never passed through model-visible context without necessity.
- Security findings update evals, tools, policies and incident playbooks.

## Review questions
1. What untrusted text can reach a control channel?
2. Which component has more authority than the requester or task requires?
3. Can an attacker cause repeated cost/effects through retry or delegation?
4. What evidence shows denial and recovery, not only successful use?

## Failure patterns
- Prompt-only security: instruction wording expected to enforce policy.
- Sandbox fallacy: isolated code still has overprivileged credentials or APIs.
- Static threat model: provider, tool and workflow changes never reviewed.

## Research basis

Grounded in NIST SSDF/AI profile, CISA Secure by Design, and OWASP agent security guidance [R95] [R97] [R100] [R124] [R125].
