# Agent evaluations in Rust applications

Make agent behavior testable without network, non-deterministic providers or production side effects. Rust’s traits and typed state are well suited to deterministic scenario harnesses.

## Testkit ports

Provide fakes for model decisions/streams, tools/effects, state store, effect journal, clock, approval service, telemetry and random/ID generation. Script responses by expected semantic request rather than call order only, and fail unexpected calls.

## Scenario fixture

```yaml
objective: repair failing build
initial_state: ...
model_script: ...
tool_script:
  - expect: repository.search
    return: ...
  - expect: shell.test
    return: ...
faults: [timeout_after_dispatch]
expected:
  terminal: escalated
  actions: [...]
  forbidden_actions: [message.send]
  acceptance: [...]
```

## Grading

Use Rust assertions for state/effects/budgets/permissions and artifact tests for outputs. Model rubric graders may assess semantic quality from sanitized artifacts/traces, but deterministic gates remain authoritative for invariants.

## Adapter contract suites

Every real model/tool/protocol/store adapter runs the same contract cases: schema mapping, error taxonomy, cancellation/deadline, trace propagation, redaction, idempotency/effect ambiguity and version behavior.

## Live evals

Keep authorized, rate-bounded live suites separate from deterministic CI. Record model/provider configuration, seed where available, cost/latency and raw evidence under policy. Compare distributions, not a single run.

## Regression

Convert incidents and repeated Codex corrections into fixtures. Add should/should-not-trigger cases for skills and topology decisions. Gate critical safety/effect invariants at 100%; use thresholds/confidence intervals for stochastic semantic quality.
