# Progressive rollout plan

## Release identity and scope
Exact source/artifact/model/prompt/skill/tool/config/schema versions, environment, migration and operating envelope: `{{identity_scope}}`

## Exposure and authorization
- exposure unit and eligibility: `{{unit}}`
- feature/variant mechanism: `{{feature}}`
- authorization policy independent of exposure: `{{authorization}}`
- cohort/holdout/segment plan: `{{cohorts}}`

## Ramp gates
| Step | Exposure | Minimum observation | Health/SLO | Outcome/guardrail/data quality | Authority | Action on fail |
|---:|---:|---|---|---|---|---|
| 0 | shadow/dark | `{{window}}` | `{{health}}` | `{{criteria}}` | `{{owner}}` | `{{action}}` |
| 1 | `{{percent}}` | `{{window}}` | `{{health}}` | `{{criteria}}` | `{{owner}}` | `{{action}}` |

## Recovery
- kill switch and off-hours authority: `{{kill}}`
- rollback/roll-forward and state/schema compatibility: `{{rollback}}`
- external effect reconciliation/compensation: `{{effects}}`
- incident communication/support: `{{incident}}`

## Closure
Expected stabilization signals, temporary flag/path/permission cleanup, final decision record and post-release field review: `{{closure}}`
