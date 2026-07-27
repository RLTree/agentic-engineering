# Rust tracing and context propagation

Use `tracing` spans/events and OpenTelemetry context to preserve causal structure across Tokio tasks, channels, services, queues and resumed agent runs. Context must be propagated deliberately; task spawning and durable replay can sever implicit parentage.

## Vocabulary
- **span:** Timed operation with attributes and parent/links.
- **event:** Point-in-time structured occurrence associated with context.
- **trace context:** Trace/span identity and flags propagated across process boundaries.
- **span link:** Association to another context when strict parent-child nesting is inaccurate.
- **context carrier:** HTTP headers, message metadata or durable record carrying propagation fields.

## Decision procedure
1. Define span hierarchy for service request, agent run, task/turn, model call, tool call, effect, approval, recovery and field observation.
2. Instrument functions with `#[instrument]` selectively; skip sensitive/high-cardinality arguments and record typed safe attributes.
3. Capture the current span/context when spawning Tokio tasks; instrument futures and propagate through channel envelopes.
4. Inject/extract W3C Trace Context over HTTP/gRPC and protocol transports; store trace linkage with durable work and use links on resume/replay when appropriate.
5. Record stable domain IDs in addition to trace IDs because sampling/export can remove trace data.
6. Test parent/link structure, cross-thread/task propagation, cancellation, retries, fan-out/fan-in, exporter failure and shutdown flush.

## Decision table

| Boundary | Propagation mechanism | Common bug |
|---|---|---|
| Tokio spawn | instrumented future or captured span | orphan task trace |
| mpsc/queue | typed envelope with domain + trace context | consumer starts unrelated trace |
| HTTP/gRPC | W3C inject/extract | trusting unvalidated baggage |
| durable resume | persist domain IDs + context/link | pretending replay is same live span |
| multi-agent fan-out | child spans/links per worker | lossy aggregate only |

## Evidence obligations
- Trace parentage reflects causality; do not force misleading nesting.
- Untrusted incoming trace/baggage is bounded and sanitized.
- Domain run/action/effect identities do not depend solely on telemetry backend IDs.
- Instrumentation avoids holding locks or performing blocking export on async hot paths.

## Review questions
1. Where can context disappear across spawn, queue, protocol or restart?
2. Should resumed work be a child, continuation with link, or new trace tied by domain ID?
3. Which attributes are sensitive or high-cardinality?
4. Can operators join an effect to the initiating run after sampling?

## Failure patterns
- Thread-local assumption: async task context expected to propagate automatically everywhere.
- Raw argument instrumentation: prompts, secrets or documents captured by macro defaults.
- Trace ID as business identity: durable reconciliation fails when traces are missing.

## Research basis

Grounded in the Rust `tracing` ecosystem, OpenTelemetry Rust, and W3C Trace Context [R118] [R119] [R123].
