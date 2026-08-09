# Observability verification

Treat telemetry as a tested interface. Verify that representative and failure trajectories produce complete, correctly joined, privacy-safe evidence and that observability failure does not destabilize the Tokio runtime or hide critical effects.

## Vocabulary
- **golden trace:** Expected span/event structure for a deterministic scenario.
- **telemetry contract test:** Test asserting schema, attributes, links, redaction and export semantics.
- **data-quality SLI:** Completeness, joinability, freshness, duplication or version consistency of evidence.
- **exporter backpressure:** Load/failure from telemetry pipeline that can affect the application.
- **shutdown flush:** Bounded attempt to deliver buffered telemetry during graceful termination.

## Decision procedure
1. Create golden scenarios: nominal run, tool denial, retry, timeout, cancellation, fan-out/fan-in, approval, override, ambiguous effect, reconcile, restart/resume and incident.
2. Use in-memory/test subscribers and exporters to assert spans, events, parentage/links, domain IDs, schema versions and redaction.
3. Property-test bounded labels/enums and arbitrary untrusted inputs; verify no secrets/content leak.
4. Inject exporter latency/failure, queue saturation and shutdown; assert bounded resource use and core behavior policy.
5. Test cross-process W3C propagation and durable context resume; validate dashboard/query results against fixtures.
6. Monitor production trace completeness, join rate, missing versions, dropped spans and cardinality/cost; page only on actionable evidence failures.

## Decision table

| Test | Assertion | Risk caught |
|---|---|---|
| Golden trajectory | expected spans/events/order/IDs | missing causal evidence |
| Redaction property | forbidden patterns absent | privacy/secrets leak |
| Cardinality load | bounded labels/queues | backend/runtime collapse |
| Exporter fault | core path policy maintained | observability-induced outage |
| Context integration | trace/domain joins across boundaries | orphan effects |
| Field query test | decision metric matches fixture | dashboard semantic drift |

## Evidence obligations
- Observability acceptance is mapped to operator and field-learning questions.
- Tests cover absent/partial telemetry and degraded exporters.
- The exact production configuration—sampling, processors, exporters and resource attributes—is reviewed.
- Data-quality regressions block causal or safety claims when evidence becomes unreliable.

## Review questions
1. Can a trace answer why an effect occurred and whether it completed?
2. What happens when the collector is slow or unavailable?
3. Which schema/query changes could silently alter metrics?
4. Can tests prove raw workload or secrets are excluded?

## Failure patterns
- Telemetry compile test only: events exist but do not answer decisions.
- Observability causes outage: unbounded synchronous export.
- Dashboard trust: query logic changes without fixture validation.

## Research basis

At the 2026-08-08 lock, OpenTelemetry 1.59.0 and semantic conventions 1.43.0
remain version-sensitive; experimental GenAI fields do not become domain
evidence (`F-OTEL-159`). Historical lineage: [R118] [R119] [R121] [R122]
[R123].
