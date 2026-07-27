# Product experiment and decision contract

## Decision and hypothesis
- product decision: `{{decision}}`
- mechanism hypothesis: `{{hypothesis}}`
- estimand, population and horizon: `{{estimand}}`
- operating envelope and ethical/authority review: `{{envelope_authority}}`

## Design
- intervention and baseline/alternatives: `{{variants}}`
- randomization unit and assignment: `{{assignment}}`
- exposure logging and analysis population: `{{exposure}}`
- interference/carryover/contamination: `{{interference}}`
- ramp, holdout, duration/sample/stopping: `{{ramp}}`

## Metric contract
| Class | Metric/formula/population/window | Material threshold | Segment | Owner |
|---|---|---|---|---|
| primary outcome | `{{metric}}` | `{{threshold}}` | `{{segment}}` | `{{owner}}` |
| diagnostic | `{{metric}}` | `{{threshold}}` | `{{segment}}` | `{{owner}}` |
| guardrail | `{{metric}}` | `{{threshold}}` | `{{segment}}` | `{{owner}}` |
| data quality | `{{metric}}` | `{{threshold}}` | `{{segment}}` | `{{owner}}` |

## Validity and analysis
A/A, SRM, missingness, version consistency, peeking/multiple tests, attrition, novelty, long-term effects, qualitative/trace review and sensitivity: `{{validity}}`

## Predeclared decision
- win: `{{win}}`
- neutral: `{{neutral}}`
- loss: `{{loss}}`
- mixed/segment harm: `{{mixed}}`
- invalid experiment: `{{invalid}}`
