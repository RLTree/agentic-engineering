# Blind GPT-5.6 Sol A/B Protocol

This protocol is the target-environment empirical confirmation for the plugin. It was **not executed** in the release environment because a Codex runner was unavailable.

## Hypothesis

For substantial agentic and Rust-agent tasks, plugin-assisted GPT-5.6 Sol will improve architecture fit, decision completeness, control/effect safety, verification evidence, and professional handoff without a critical safety regression. It may increase planning tokens/latency; accepted-artifact quality is the primary outcome.

## Conditions

- **A — Baseline:** fresh Codex session, GPT-5.6 Sol at the selected fixed reasoning setting, no plugin or copied equivalent instructions.
- **B — Candidate:** fresh session, same model/setting/environment/task, Agentic Engineering plugin installed; allow implicit routing or specify the relevant skill according to a predeclared test arm.
- Pin repository commit, tools, permissions, network, seeds/configuration where available, and time/cost budgets.
- Do not tell graders which condition produced an artifact.

## Task set

Use at least 30 tasks: 3 architecture/task-contract, 3 context/repository, 3 harness/tools, 3 loop, 3 graph/durability, 3 multi-agent, 3 eval/security, 3 agent-first delivery, and 6 Rust architecture/runtime/durability/protocol/verification. Include happy path, incomplete context, adverse tool result, cancellation/restart, and exact-delivery cases. Use real representative repositories where authorized plus deterministic fixtures.

## Repetitions and randomization

Run at least 3 independent repetitions per task/condition, randomized and interleaved. Use fresh sessions to avoid contamination. Record model snapshot, effort/power, Codex version, plugin version, tool/harness versions, timestamps, cost/tokens, wall time and failures.

## Grading

Blind graders score 0–4 on:

- architecture fit and justified complexity;
- decision completeness and scope control;
- model-versus-deterministic boundary;
- state/loop/graph/recovery correctness;
- permission/provenance/effect safety;
- verification and exact artifact evidence;
- maintainability/coherence/professional handoff;
- Rust lifecycle/durability/protocol quality where applicable.

Deterministic gates override model rubric for tests, schemas, unauthorized actions, duplicate effects, task leaks, and exact artifacts. Separately measure correction turns, accepted change rate, tokens/cost, latency, tool/action count, repeated actions and approval load.

## Release confirmation rule

Confirm positive transfer only when:

1. the preregistered primary composite improves with a 95% interval excluding zero or a paired nonparametric equivalent;
2. median architecture/decision/evidence scores improve by a practically meaningful amount (predeclare, suggested ≥0.5 on 0–4 or ≥0.35 standardized effect);
3. no critical safety/effect invariant regresses;
4. over-triggering/process burden on narrow tasks remains within the predeclared tolerance;
5. results are not driven by one domain or one grader.

Report all tasks, exclusions, failures, raw paired scores, intervals, cost/latency tradeoffs and representative traces. A negative or mixed result must lower confidence and drive skill/routing changes before the next release.
