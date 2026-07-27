# Operating envelope

**Envelope ID/version:** `{{id_version}}`  
**Owner/authority:** `{{owner}}`  
**Evidence basis and expiry:** `{{evidence_expiry}}`

## Allowed conditions
| Dimension | Allowed | Limits/controls | Evidence |
|---|---|---|---|
| users/roles/tenants | `{{users}}` | `{{user_controls}}` | `{{user_evidence}}` |
| task classes | `{{tasks}}` | `{{task_controls}}` | `{{task_evidence}}` |
| data classes/jurisdictions | `{{data}}` | `{{data_controls}}` | `{{data_evidence}}` |
| models/prompts/skills | `{{models}}` | `{{model_controls}}` | `{{model_evidence}}` |
| tools/dependencies | `{{tools}}` | `{{tool_controls}}` | `{{tool_evidence}}` |
| environments/hours/scale | `{{environment}}` | `{{scale_controls}}` | `{{scale_evidence}}` |
| effect classes/value | `{{effects}}` | `{{effect_controls}}` | `{{effect_evidence}}` |
| cost/latency/concurrency | `{{budgets}}` | `{{budget_controls}}` | `{{budget_evidence}}` |

## Explicit exclusions
| Condition | Detect | Response | Escalation owner |
|---|---|---|---|
| `{{excluded_condition}}` | `{{detector}}` | deny / degrade / request approval / stop | `{{owner}}` |

## Effect and authority policy
- Agent may propose: `{{propose}}`
- Agent may execute without synchronous approval: `{{execute}}`
- Human approval required: `{{approval}}`
- Prohibited effects: `{{prohibited}}`
- Idempotency/reconciliation/compensation: `{{effect_safety}}`

## Promotion, demotion and expiry
- Evidence required to expand: `{{promotion}}`
- Demotion/kill criteria: `{{demotion}}`
- Version or workload changes requiring reauthorization: `{{reauthorize}}`
- Next review: `{{review}}`
