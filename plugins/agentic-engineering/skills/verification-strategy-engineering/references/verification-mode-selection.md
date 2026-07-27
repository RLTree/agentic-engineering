# Verification Mode Selection

Choose modes by failure risk and oracle, not by ideology.

| Change shape | Primary evidence | Common complements |
|---|---|---|
| Already fixed or stale request | reproduction and no-change decision | targeted regression or documentation only |
| New deterministic behavior | test-first behavior proof | contract/integration test |
| Legacy behavior with weak specification | characterization-first | differential or golden-master review |
| Invariant-heavy domain | property or model-based test | mutation testing |
| Concurrent runtime | deterministic unit tests | schedule exploration, fault, saturation, cancellation |
| External effect | idempotency/effect journal test | sandbox, reconciliation, approval, rollback |
| User-visible journey | browser or device journey | accessibility, telemetry, recovery |
| Performance or reliability | workload and SLO evidence | profiling, fault injection, canary |
| Security boundary | abuse cases and authorization tests | provenance, red team, monitoring |

The selected set must detect the material failure classes and remain proportionate to consequence, reversibility, and change size.

Evidence basis: R135, R139, R141, R142.
