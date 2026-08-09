# Field Pulse Contract

A Field Pulse is a compact, read-only, time-windowed projection of product value, system health, evidence quality, and operator burden.

Include:

- population and operating envelope;
- assignment, actual exposure, and missing-data counts;
- first-value and verified-outcome rates;
- latency, reliability, guardrails, severe events, and ambiguous effects;
- human interventions, review rounds, correction time, and abandonment;
- trace-to-outcome join completeness and metric-contract versions;
- subgroup or context differences;
- follow-up decisions, not automatic judgments.

Apply ingestion-lag buffers. Preserve `no data`, `insufficient integrity`, and `not comparable` states. Do not persist raw user content or identifiers unless separately authorized and necessary.

The NIST continuous-monitor communication is emerging research, not a normative
operating standard (`F-NIST-AGENT-INIT`). Historical lineage: R131, R133, R134,
R148.
