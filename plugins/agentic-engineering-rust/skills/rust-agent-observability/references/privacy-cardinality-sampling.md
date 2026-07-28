# Privacy, cardinality, and sampling

Telemetry must be useful enough for diagnosis and field learning while minimizing sensitive content, bounded enough for backend reliability/cost, and sampled so rare severe events and representative successes remain observable.

## Vocabulary
- **data minimization:** Collect only fields necessary for declared questions and obligations.
- **pseudonymization:** Replacement of direct identifiers; still personal/sensitive where reidentification is possible.
- **cardinality:** Number of distinct values a metric label or indexed field can take.
- **head sampling:** Decision near trace start, before outcome is known.
- **tail sampling:** Decision after observing trace characteristics such as error, latency or intervention.

## Decision procedure
1. Classify each proposed field by necessity, sensitivity, tenant, retention, access and deletion requirements.
2. Redact/tokenize at source; prohibit secrets, raw prompts, documents and tool payloads by default; define approved diagnostic capture separately.
3. Set metric label allowlists and cardinality budgets; place IDs/details in spans/events with controlled indexing.
4. Define deterministic/head sampling for baseline representativeness and tail/priority retention for severe errors, ambiguous effects, interventions, security events and rare task classes.
5. Protect against sampling bias: retain weighted counts, trace-completeness/data-quality metrics and a sample of apparent successes.
6. Test leakage, cross-tenant isolation, deletion, cardinality under adversarial inputs, sampling decisions, exporter backpressure and cost.

## Decision table

| Signal | Retention tendency | Reason |
|---|---|---|
| Severe safety/security incident | retain under incident policy | forensics and correction |
| Ambiguous external effect | retain until reconciliation/expiry | authoritative outcome |
| Human override/abandonment | priority sample | workflow failure signal |
| Representative success | baseline sample | success deconstruction and denominator |
| Raw content | avoid/minimize | privacy and cost risk |

## Evidence obligations
- Hashing is treated as pseudonymization, not automatic anonymization.
- Sampling and redaction policies are versioned and observable.
- Telemetry access follows least privilege and tenant isolation.
- Exporter or backend failure has bounded memory/latency and does not silently bypass audit requirements for high-risk effects.

## Review questions
1. What product/operator decision requires this field?
2. Could untrusted input create unbounded label values?
3. Which failures disappear under current head sampling?
4. Are successful traces sampled enough to reveal unsafe shortcuts or hidden labor?

## Failure patterns
- Collect everything now: privacy and cost justified by hypothetical future analysis.
- Hash-and-forget: reidentifiable IDs treated as anonymous.
- Error-only sampling: no representative denominator or success mechanism.

## Research basis

Grounded in OpenTelemetry sensitive-data guidance and observability practice [R119] [R121].
