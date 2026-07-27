# Rust agent observability contract

## Questions and evidence
Operator, product, safety and field-learning questions mapped to traces, events, metrics, exemplars and queries: `{{questions}}`

## Typed identity and schema
- run/task/turn/action/tool-call/effect/approval/intervention/outcome types: `{{types}}`
- cohort/experiment and model/prompt/skill/harness/tool/deployment versions: `{{versions}}`
- schema and semantic-convention versions: `{{schema_versions}}`
- absent/unknown/denied/failed/ambiguous semantics: `{{semantics}}`

## Span/context design
- span hierarchy and attributes: `{{spans}}`
- Tokio spawn/channel propagation: `{{tokio}}`
- HTTP/gRPC/MCP/A2A W3C propagation: `{{network}}`
- durable resume/replay links and domain IDs: `{{durable}}`

## Metrics and sampling
- bounded labels/cardinality budget: `{{labels}}`
- outcome/effect/intervention/runtime measures: `{{metrics}}`
- head/deterministic/tail sampling: `{{sampling}}`
- priority retention and representative successes: `{{priority}}`

## Privacy and operation
Redaction/minimization, consent, tenant isolation, retention/deletion, exporter queues/backpressure/failure, shutdown flush and cost: `{{privacy_operation}}`

## Verification matrix
Golden traces, schema compatibility, context integration, redaction/property tests, cardinality/load, exporter fault, shutdown, data-quality SLIs and field-query fixtures: `{{verification}}`
