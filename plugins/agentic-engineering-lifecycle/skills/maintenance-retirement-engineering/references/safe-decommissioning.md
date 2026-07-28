# Safe decommissioning

Decommission through stop-adoption, redirect, disable, observe, archive/revoke, remove and delete. Deletion is the final irreversible step after proving user continuity, dependency absence, data handling and restoration/rollback.

## Vocabulary
- **disable-observe-delete:** Sequence that stops behavior while preserving ability to detect hidden use before irreversible removal.
- **dark dependency:** Consumer or operational reliance absent from declared inventory.
- **watch window:** Time after disable/redirect during which traffic, incidents and obligations are monitored.
- **data disposition:** Retention, transfer, archive, anonymization or verified deletion of data and derived artifacts.
- **closure evidence:** Proof that users, contracts, security, cost, ownership, data and dependencies are resolved.

## Decision procedure
1. Approve retirement decision with rationale, user-need continuity, affected stakeholders, authority, reversal/delay criteria and dates.
2. Stop new adoption and writes; migrate/redirect users and agents; freeze nonessential change.
3. Test fallback/restoration, export/transfer, data retention/deletion and effect closure.
4. Disable capability or route to replacement; retain observability and run a risk-based watch window.
5. Resolve residual traffic, jobs, credentials, queues, webhooks, DNS, certificates, alerts, dashboards, docs, contracts, costs and ownership.
6. Archive required evidence, revoke identities/secrets, remove dependencies and monitors, then delete resources and verify closure.

## Decision table

| Stage | Reversible? | Gate |
|---|---|---|
| Stop adoption | Yes | no new consumers |
| Redirect/migrate | Mostly | outcomes preserved |
| Disable writes/effects | Yes if rehearsed | no unresolved effect/state |
| Watch | Yes | zero/understood traffic |
| Revoke/remove | Partly | dependencies and obligations closed |
| Delete | No/expensive | authority + closure evidence |

## Evidence obligations
- Observability remains until hidden dependencies and delayed work are disproven.
- Backups/archives have explicit retention, access and deletion responsibilities.
- External effects, credentials and billing are reconciled.
- Restoration is tested before irreversible removal when continuity matters.

## Review questions
1. What could still call, resume, replay or depend on this after disable?
2. What evidence proves the replacement preserves the user outcome?
3. Which data or legal obligation survives service deletion?
4. Can we restore during the watch window?

## Failure patterns
- Delete before disable and observe.
- Monitoring removed first: hidden use becomes invisible.
- Zombie closure: compute removed but data, secrets, contracts, costs or ownership remain.

## Research basis

Grounded in service-retirement and safe decommissioning guidance [R92] [R112].
