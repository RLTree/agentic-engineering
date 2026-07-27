# Baseline Failure Findings

These are the recurring behaviors the plugin is designed to change. They are hypotheses grounded in the research and prior artifact work; they are not presented as results of a live GPT-5.6 Sol experiment in this build environment.

| Baseline behavior | Likely cause | Plugin mechanism | Measurement |
|---|---|---|---|
| “Agentic,” “robust,” or “professional” is interpreted inconsistently | adjective-only specification | task compiler and vocabulary translator | decision completeness; correction turns |
| Complex topology is selected because the task is difficult | architecture escalation not explicit | smallest-fitting topology router/table | architecture-fit grader; coordination cost |
| Prompt rewrites fail to repair permissions/state/tools/recovery | control-layer confusion | seven-layer diagnostic and harness blueprint | layer-placement accuracy; safety failures |
| Agent loops or researches indefinitely | no oracle/budget/convergence policy | loop contract, failure taxonomy, budget stop policy | repeated action rate; budget compliance |
| Graph resumes duplicate external effects | replay and effect state implicit | node/effect contracts, journal, idempotency/reconciliation | duplicate-effect and crash-point tests |
| Parallel agents overlap or produce incoherent synthesis | delegation/ownership/fan-in undefined | multi-agent entry gate and delegation contract | overlap, integration defects, global test failures |
| Completion is plausible but not proven | final narrative treated as evidence | acceptance-to-evidence and exact artifact handoff | unsupported claim rate; exact-delivery pass |
| Rust app couples domain to provider/framework | adapter boundary missing | typed state/effects and ports/adapters | replaceability/contract tests; dependency direction |
| Tokio work leaks or overloads | detached tasks/unbounded queues/cancellation blindness | structured runtime contract and fault matrix | leak, saturation, cancellation and shutdown tests |
| Timeout retries duplicate remote actions | failure phase/effect ambiguity lost | effect journal and reconciliation protocol | at-most-once semantic effect under replay |
