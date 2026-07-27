# Deprecation and migration

Deprecation preserves the underlying user need while ending a specific interface, model, tool, workflow or service. It requires consumer evidence, alternatives, lead time, compatibility, support and explicit closure—not an announcement alone.

## Vocabulary
- **deprecation:** Notice and controlled transition away from a supported capability before removal.
- **consumer inventory:** Users, agents, APIs, jobs, data flows, contracts, docs, dashboards and dependencies relying on the capability.
- **migration cohort:** Segment moved under a defined sequence, support and rollback plan.
- **compatibility shim:** Temporary adapter preserving old behavior while consumers migrate.
- **sunset criterion:** Evidence and date/condition allowing support or compatibility to end.

## Decision procedure
1. State why change is needed: declining value, risk, cost, replacement, contract, provider EOL or architecture simplification.
2. Inventory direct/indirect consumers using code/config/search, runtime telemetry, ownership records, contracts, support and stakeholder outreach.
3. Define replacement or preserved user outcome, differences, data/permission changes, migration tooling, compatibility window and rollback.
4. Segment cohorts by criticality and readiness; communicate rationale, dates, actions, support, impact and escalation with adequate lead time.
5. Migrate progressively; monitor traffic, errors, outcome, support burden, stragglers and hidden dependencies.
6. End compatibility only after sunset criteria and authority; update docs, permissions, tests, monitors and ownership.

## Decision table

| Consumer state | Action | Evidence |
|---|---|---|
| Known active | guided migration | successful outcome on replacement |
| Unknown/unowned traffic | trace and escalate | identity/owner confirmed |
| Critical unable to migrate | extend/narrow or alternative | risk and deadline decision |
| Inactive/no dependency | remove after watch | zero traffic and restore test |

## Evidence obligations
- Deprecation preserves accessibility, data rights, contracts and critical workflows.
- Compatibility paths have owner, telemetry, cost and removal date.
- External API/partner lead times reflect contractual and operational reality.
- Agent/tool clients are included; silent schema changes are prohibited.

## Review questions
1. What user need survives after this capability ends?
2. Which consumers are invisible to source search?
3. What makes the migration reversible during each cohort?
4. Who has authority to extend or enforce the sunset?

## Failure patterns
- Announcement-only deprecation: no inventory, tooling or support.
- Forever shim: temporary compatibility becomes permanent complexity.
- Traffic=need: low volume critical consumers missed.

## Research basis

Uses lifecycle retirement guidance, GOV.UK retirement practice, safe decommissioning and secure dependency management [R92] [R112].
