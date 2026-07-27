# Autonomy and exposure plan

## Learning/product decision
`{{decision}}`

## Current and target level
| Level | Enabled? | Evidence | Promotion gate |
|---|---:|---|---|
| replay/offline | `{{yes_no}}` | `{{evidence}}` | `{{gate}}` |
| observe-only | `{{yes_no}}` | `{{evidence}}` | `{{gate}}` |
| shadow/silent | `{{yes_no}}` | `{{evidence}}` | `{{gate}}` |
| recommendation-only | `{{yes_no}}` | `{{evidence}}` | `{{gate}}` |
| approval-gated action | `{{yes_no}}` | `{{evidence}}` | `{{gate}}` |
| bounded autonomy | `{{yes_no}}` | `{{evidence}}` | `{{gate}}` |
| broader autonomy | `{{yes_no}}` | `{{evidence}}` | `{{gate}}` |

## Ramp contract
- Exposure unit and eligible population: `{{unit_population}}`
- Cohorts/holdout: `{{cohorts}}`
- Steps and minimum observation windows: `{{steps}}`
- Blast-radius limits: users `{{users}}`; effect value `{{value}}`; duration `{{duration}}`; errors/ambiguity `{{errors}}`; cost `{{cost}}`
- Health, outcome, human-effort and guardrail gates: `{{gates}}`
- Data-quality validity gates: `{{validity}}`

## Oversight design
- Reviewer role/expertise: `{{reviewer}}`
- Preview/evidence shown: `{{preview}}`
- Expected review time and volume: `{{burden}}`
- Escalation/two-person control: `{{escalation}}`
- Sample of non-intervened successes: `{{success_sample}}`
- Approval-fatigue monitor: `{{fatigue}}`

## Emergency control
- Kill mechanism and authority: `{{kill}}`
- Rollback/reconciliation: `{{rollback}}`
- Incident communication: `{{incident}}`
