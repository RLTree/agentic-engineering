# Field instrumentation contract

## Questions telemetry must answer
| Question | Evidence unit | Events/spans | Metric/query | Retention/access |
|---|---|---|---|---|
| `{{question}}` | `{{unit}}` | `{{events}}` | `{{metric}}` | `{{policy}}` |

## Stable identities and versions
- run/task/turn/action/tool-call/effect/approval/intervention: `{{ids}}`
- user/session/tenant pseudonym policy: `{{identity_policy}}`
- cohort/experiment/feature variant: `{{cohort}}`
- model/prompt/skill/harness/tool/deployment/schema versions: `{{versions}}`

## Required evidence classes
- outcome: `{{outcome}}`
- trajectory/state transitions: `{{trajectory}}`
- external effect status and reconciliation: `{{effects}}`
- human approval/edit/override/escalation/abandonment: `{{human_work}}`
- recovery, latency, cost and resource use: `{{operations}}`
- incident/near miss/support linkage: `{{incident_join}}`
- trace completeness and join quality: `{{data_quality}}`

## Privacy and cardinality
- prohibited-by-default fields: raw prompts/documents/tool payloads/secrets plus `{{other}}`
- redaction/minimization: `{{redaction}}`
- consent/notice: `{{consent}}`
- access/tenant isolation: `{{access}}`
- retention/deletion: `{{retention}}`
- metric-label allowlist/cardinality budget: `{{labels}}`

## Sampling
- representative baseline sample: `{{baseline}}`
- always/priority retain: severe errors, security events, ambiguous effects, interventions, rare high-risk tasks plus `{{priority}}`
- success sampling: `{{success}}`
- weighting/bias controls: `{{bias}}`

## Verification
Schema, context propagation, redaction, sampling, exporter failure/backpressure, shutdown flush, data-quality monitors and decision queries: `{{tests}}`
