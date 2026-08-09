# Field instrumentation and evidence

Field instrumentation must reconstruct the joint human-agent-system trajectory, external effects, and product outcome without collecting unnecessary sensitive content or creating unbounded metric cardinality.

## Vocabulary
- **trajectory:** Ordered decisions, model/tool calls, state transitions, approvals, effects, retries, and recovery.
- **effect status:** Prepared, dispatched, confirmed, ambiguous, reconciled, compensated, or failed state of an external change.
- **intervention:** Human edit, override, escalation, cancellation, correction, recovery, or fallback.
- **trace completeness:** Whether required events and joins exist for the sampled field-learning unit.
- **evidence join:** Stable-key connection among telemetry, product outcome, experiment/cohort, support/incident, and change records.

## Decision procedure
1. Start from product, safety, operational, and learning questions; map each to minimum events and measures.
2. Define stable run/task/action/effect/approval/cohort/version identities and a closed event schema.
3. Capture context provenance and classifications rather than raw workload content by default.
4. Record outcome, trajectory, effects, interventions, recovery, human effort, latency/cost, and missingness.
5. Create sampling that retains severe/rare events, interventions, ambiguous effects, and representative successes.
6. Validate joins, event ordering, versioning, redaction, retention, access, exporter failure and query reproducibility.

## Decision table

| Signal class | Examples | Primary use |
|---|---|---|
| Outcome | task accepted, correction rate, time-to-value | Product value |
| Trajectory | tool choice, retries, state transitions | Mechanism diagnosis |
| Effect | external action and confirmation | Safety and reconciliation |
| Human work | review time, edits, override, abandonment | Workflow fit and hidden labor |
| Data quality | join rate, completeness, assignment mismatch | Validity |

## Evidence obligations
- High-cardinality identifiers belong in spans/events, not metric labels.
- Secrets, raw prompts/documents, and personal data are prohibited by default and require necessity plus explicit policy.
- Telemetry failure does not silently block or corrupt core effects; failure behavior is designed and tested.
- Observation schema versions and deployment/model/tool/harness versions accompany evidence.

## Review questions
1. Can we reconstruct why this outcome occurred?
2. Can we distinguish agent failure, tool failure, policy denial, user choice, and missing telemetry?
3. What sensitive data is unnecessary for the decision?
4. Which successes are sampled deeply enough to reveal hidden labor or unsafe shortcuts?

## Failure patterns
- Outcome-only telemetry: no mechanism or effect trail.
- Trace-only telemetry: no join to user outcome or human effort.
- Cardinality/privacy collapse: arbitrary content or IDs used as metric labels.

## Research basis

Uses agent trajectory evaluation, monitoring questions, OpenTelemetry, W3C trace
context, and privacy guidance. NIST AI 800-4 is descriptive rather than a
prescribed instrumentation method (`F-NIST-AI800-4`). Historical lineage: [R72]
[R75] [R118] [R119] [R121] [R123].
