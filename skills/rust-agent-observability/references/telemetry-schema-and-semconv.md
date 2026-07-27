# Telemetry schema and semantic conventions

Define typed, versioned telemetry for agent runs, decisions, tools, effects, approvals, interventions and outcomes. Adopt OpenTelemetry semantic conventions where stable and isolate experimental conventions behind adapters/version fields.

## Vocabulary
- **semantic convention:** Shared attribute/span/metric naming and meaning for interoperability.
- **schema version:** Identifier for the event contract used by producers and consumers.
- **domain event:** Business/control occurrence such as ActionProposed, EffectConfirmed or HumanOverride.
- **exemplar:** Metric sample linked to a representative trace.
- **attribute stability:** Whether a field is stable, experimental, deprecated or locally defined.

## Decision procedure
1. List operator/product/safety/field-learning questions and derive minimum events, spans and metrics.
2. Define enums and structs for run/task/action/effect/approval/intervention/outcome with stable IDs, timestamps, versions, cohort and privacy class.
3. Map stable OpenTelemetry resource/service and relevant GenAI attributes; namespace local fields and record semantic-convention version.
4. Separate low-cardinality metric labels from high-cardinality event/span attributes; attach exemplars where useful.
5. Create serialization/schema compatibility, unknown-value and redaction policies; keep provider SDK payloads behind adapters.
6. Validate producer/consumer compatibility, trace joins, event ordering, duplicate handling and query correctness.

## Decision table

| Data | Best representation | Reason |
|---|---|---|
| Run/task/action/effect ID | span/event attribute | high-cardinality join |
| Outcome class/tool result | bounded enum metric + event | aggregation plus detail |
| Raw prompt/tool argument | not collected by default or protected event | privacy/cardinality |
| Model/harness/deployment version | resource/span bounded field | evidence applicability |
| Intervention reason | structured enum + optional redacted detail | field-learning mechanism |

## Evidence obligations
- Schemas distinguish absent, unknown, denied, failed and ambiguous states.
- All behavior-producing versions are observable enough to attribute change.
- Experimental semantic conventions are pinned and migration-tested.
- Metric labels are bounded and reviewed for tenant/user/content leakage.

## Review questions
1. Can every field be interpreted consistently six months later?
2. Which event represents authoritative effect confirmation?
3. Can unknown enum values be handled without dropping the trace?
4. What query demonstrates the schema answers the learning question?

## Failure patterns
- Stringly telemetry: free text prevents reliable aggregation and policy.
- Vendor payload as domain schema: portability and privacy collapse.
- Metric-label explosion: IDs, URLs or error text used as labels.

## Research basis

Uses OpenTelemetry core/Rust and current GenAI semantic-convention guidance [R119] [R120] [R122].
