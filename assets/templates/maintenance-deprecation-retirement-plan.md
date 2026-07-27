# Maintenance, deprecation, and retirement plan

## Continuing value and health
User need/task distribution, outcomes, SLOs, incidents, security/privacy, support/operator burden, cost, model/tool drift, dependencies, alternatives and affected vulnerable/critical users: `{{health}}`

## Sustainment backlog
| Item | Class | Consequence/recurrence | Evidence/expiry | Action/owner/date | Exit criterion |
|---|---|---|---|---|---|
| `{{item}}` | corrective/adaptive/perfective/preventive/security | `{{risk}}` | `{{evidence}}` | `{{action}}` | `{{exit}}` |

## Decision
Maintain / replace / consolidate / deprecate / retire; authority, rationale, reversal/delay criteria: `{{decision}}`

## Consumer and migration plan
Users, agents, APIs, jobs, data, credentials, queues, dashboards, alerts, runbooks, contracts, owners; replacement outcome, compatibility window, cohorts, tooling, support, communication and rollback: `{{migration}}`

## Disable–observe–delete
| Stage | Action | Evidence gate | Watch/owner | Restore/fallback |
|---|---|---|---|---|
| stop adoption | `{{action}}` | `{{gate}}` | `{{owner}}` | `{{fallback}}` |
| redirect/migrate | `{{action}}` | `{{gate}}` | `{{owner}}` | `{{fallback}}` |
| disable writes/effects | `{{action}}` | `{{gate}}` | `{{owner}}` | `{{fallback}}` |
| observe | `{{action}}` | `{{gate}}` | `{{owner}}` | `{{fallback}}` |
| revoke/remove/delete | `{{action}}` | `{{gate}}` | `{{owner}}` | `{{fallback}}` |

## Evidence continuity
Retention, redaction, archive access, data disposition, contracts/cost closure, ownership and destruction date: `{{continuity}}`
