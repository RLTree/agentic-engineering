# GPT-5.6 Sol operating profile for Codex

**Research lock:** 2026-07-22. Re-check official model and Codex documentation before hard-coding model names, effort levels, pricing or surface availability.

## Model selection

Use GPT-5.6 Sol for ambiguous, difficult or high-value work that benefits from deeper analysis, judgment and polish. Keep narrow work focused by defining what done means. Use a cheaper/faster model when the task is clear, repeatable and strongly validated.

## Reasoning effort

Start with the default medium reasoning. Raise effort only for demonstrated need:

- **Low/light:** narrow, reversible and well-specified changes with strong tests.
- **Medium:** normal implementation, debugging and review that need planning.
- **High/xhigh:** difficult multi-step work, architecture tradeoffs, unfamiliar systems, broad evidence or consequential migrations.
- **Max:** the hardest single-agent problems where depth matters more than speed or usage.
- **Ultra:** only when the task has meaningful parallel workstreams and a deliberate delegation/integration contract.

Most tasks do not need Max or Ultra. Higher effort cannot repair missing context, an undefined oracle, unsafe tools or contradictory requirements.

## Sol-friendly task shape

Give Sol a decision-complete task rather than a long adjective list:

1. **Goal** — user or system outcome.
2. **Context** — relevant files, architecture, behavior, evidence and history.
3. **Constraints** — public interfaces, compatibility, security, performance and dependency boundaries.
4. **Done when** — observable acceptance criteria.
5. **Deliverables** — exact files, artifacts and integration points.
6. **Anti-goals** — plausible but unwanted expansions.
7. **Autonomy policy** — reversible assumptions allowed; consequence thresholds requiring approval.
8. **Verification contract** — commands, tests, traces, rendered behavior and exact-delivery checks.

## Tool use

Prefer a small, typed, well-described tool surface. Expose schemas, side effects, permissions, timeouts and actionable errors. Use deterministic code for filtering, aggregation, validation, deduplication and permission checks. Do not make the model parse unbounded prose when a structured result is available.

## Context and skills

Codex uses progressive disclosure for skills: name and description are initially visible; full instructions load only after selection. Keep each skill focused on one job and front-load trigger language. Store deep domain detail in references and deterministic behavior in scripts only when scripts add real value.

## Parallel work and subagents

Before using Ultra or explicit subagents, write:

- independent work packages and exclusions;
- authoritative owner for shared state;
- dependency and merge order;
- per-worker deliverables and evidence;
- cancellation and partial-failure handling;
- integration reviewer and final verification.

Parallelism is useful for independent research, tests, migrations by module or alternative implementations. It is harmful when workers edit the same files, decide the same architecture or depend on rapidly changing shared state.

## Completion discipline

Require Sol to distinguish:

- **observed fact** — supported by repository/tool/test evidence;
- **assumption** — reversible choice made to proceed;
- **hypothesis** — explanation still requiring a discriminating test;
- **decision** — chosen tradeoff with rationale and consequences;
- **residual risk** — uncertainty not eliminated by the available evidence.

A completion statement must cite the acceptance criterion, evidence source and exact artifact tested.
