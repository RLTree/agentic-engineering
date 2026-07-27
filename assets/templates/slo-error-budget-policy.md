# SLO and error-budget policy

## Critical journeys
`{{journeys}}`

## SLI/SLO definitions
| Journey | SLI good/valid event | Population/window | SLO | Segments | Data-quality SLI |
|---|---|---|---:|---|---|
| `{{journey}}` | `{{definition}}` | `{{scope}}` | `{{target}}` | `{{segments}}` | `{{quality}}` |

Include service availability/latency plus task outcome quality, verified tool/effect success or ambiguity, safety/guardrails and human review burden where consequential.

## Error-budget actions
| Burn/condition | Release/ramp action | Reliability action | Authority |
|---|---|---|---|
| fast burn / severe event | stop or revert | incident response | `{{owner}}` |
| sustained burn | freeze/narrow | prioritized reliability work | `{{owner}}` |
| healthy budget | normal progressive change | preventive investment | `{{owner}}` |

## Interpretation controls
- missing/invalid telemetry: `{{missing}}`
- hard safety/security limits overriding budget: `{{hard_limits}}`
- denominator/gaming review: `{{gaming}}`
- target review and expiry: `{{review}}`
