---
name: rust-agent-observability
description: Use when a Rust agent needs typed telemetry identities, tracing, OpenTelemetry,
  privacy, sampling, or rollout evidence.
---

# Rust Agent Observability

## Core principle

Observability is a typed product and control contract, not printf logging. Model runs, tasks, decisions, actions, effects, approvals, interventions, and outcomes with stable identities; propagate context through Tokio and external tools; bound cardinality and sensitive data; and test that telemetry supports diagnosis and field-learning decisions.

## Workflow

### 1. Define evidence and operator questions

List the product, safety, performance, reliability, and field-learning questions telemetry must answer. Map each question to events, metrics, traces, exemplars, retention, and access—not to an undifferentiated log stream.

### 2. Define stable identities and event schemas

Use run, task, turn, action, tool-call, state-version, effect, approval, cohort, experiment, user/session pseudonym, model, prompt/skill, harness, artifact, and deployment versions as appropriate. Keep high-cardinality values in spans/events, not metric labels.

### 3. Structure spans and context propagation

Create spans around run, task, model call, tool call, effect, approval, and recovery boundaries. Propagate trace context across Tokio tasks, channels, HTTP/gRPC/MCP/A2A calls, durable queues, and resumed work. Make parentage explicit when work is spawned or replayed.

### 4. Design metrics and sampling

Measure task outcomes, tool/effect errors, ambiguous outcomes, retries, approvals, overrides, cancellations, timeouts, queue depth, saturation, latency, token/cost, and trace completeness. Define head/tail or deterministic sampling that retains errors, rare events, high-risk effects, interventions, and representative successes.

### 5. Apply privacy, security, and cardinality policy

Classify fields, minimize collection, redact at source, prohibit secrets and raw prompts by default, define consent/notice, retention, access, deletion, and cross-tenant isolation. Treat hashing as pseudonymization, not automatic anonymization.

### 6. Integrate rollout and field learning

Attach feature-flag/variant and cohort context without using flags as authorization. Emit decision and evidence events that can join to product outcomes, interventions, support/incidents, and the evidence-to-change ledger.

### 7. Verify and operate telemetry

Test schema stability, context propagation, redaction, sampling, exporter failure, non-blocking behavior, shutdown flush, data-quality monitors, and queries used in reviews. Record OpenTelemetry and crate maturity assumptions and pin versions downstream.

## Output contract

Return a **Rust Agent Observability Contract** with:

1. operator, product, safety, and field-learning questions;
2. stable identity and structured event/span schema;
3. Tokio and cross-process trace-context propagation plan;
4. metric, label/cardinality, exemplar, and sampling policy;
5. privacy, redaction, retention, access, and tenant-isolation rules;
6. rollout/experiment/cohort context and evidence-join design;
7. exporter, failure, performance, and graceful-shutdown behavior;
8. unit, integration, data-quality, and field-query verification matrix.

## Common failures

- **logs without causal context:** Emitting messages that cannot connect a product outcome to the run, decision, tool, effect, approval, version, or recovery path.
- **high-cardinality metrics:** Placing user, prompt, task, run, URL, or error text in metric labels and creating cost, privacy, or backend failure.
- **telemetry leaks the workload:** Capturing raw prompts, tool arguments, secrets, documents, or personal data without necessity, redaction, consent, retention, and access controls.

## References

- [Tracing And Context](references/tracing-and-context.md)
- [Telemetry Schema And Semconv](references/telemetry-schema-and-semconv.md)
- [Privacy Cardinality Sampling](references/privacy-cardinality-sampling.md)
- [Observability Verification](references/observability-verification.md)

## Shared references

- [Controlled Field Learning System](../../references/controlled-field-learning-system.md)
- [Metric And Causal Evidence](../../references/metric-and-causal-evidence.md)
- [Agent Mediated Product Operating Model](../../references/agent-mediated-product-operating-model.md)
- [Rust Agent Landscape](../../references/rust-agent-landscape.md)
- [Field-Learning and Full-Lifecycle Vocabulary](../../references/field-lifecycle-vocabulary.md)

## Version 3 control-plane observability

Emit stable identities for task evidence packets, review verdicts, repair attempts, no-change decisions, and learning records. Preserve high-cardinality identities in traces or structured events, not metric labels. Make it possible to join a repair decision to the exact validator feedback and final outcome without recording raw user content by default.
