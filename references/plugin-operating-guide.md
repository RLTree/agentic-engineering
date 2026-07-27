# Plugin operating guide

## Route by the decision you need

- **Architecture uncertain:** `$agentic-engineering`.
- **Request vague or repeatedly repaired:** `$codex-task-contract`.
- **Repository/context problems:** `$context-repository-engineering`.
- **Tools, sandbox, state, approvals or recovery:** `$harness-engineering`.
- **Adaptive repeated action:** `$loop-engineering`.
- **Explicit branches/cycles/checkpoints/interrupts:** `$graph-workflow-engineering`.
- **Parallel agents or Ultra:** `$multi-agent-engineering`.
- **Measurement and traces:** `$agent-evals-observability`.
- **Untrusted input, tools, secrets or external effects:** `$agent-security-governance`.
- **Codex-ready repository/delivery:** `$agent-first-software-engineering`.
- **Rust domain/module design:** `$rust-agentic-architecture`.
- **Tokio execution:** `$rust-agent-runtime`.
- **Crash/retry/duplicate safety:** `$rust-agent-durability`.
- **MCP/A2A:** `$rust-agent-protocols`.
- **Rust verification:** `$rust-agent-verification`.

## Recommended combinations

Use the fewest skills that cover the consequential decisions:

- New agent feature: task contract → architecture router → harness → security → evals.
- Adaptive tool agent: loop + harness + security + evals.
- Human-approved long-running workflow: graph + durability + security + evals.
- Codex repository transformation: task contract + context/repository + agent-first software engineering.
- Rust agent service: Rust architecture + runtime + verification; add durability/protocols only when required.
- GPT-5.6 Ultra task: task contract + multi-agent + agent-first software engineering + evals.

## Progressive-disclosure rule

Do not load every reference into context. Start with the selected `SKILL.md`; open only the reference needed for the current decision. Summarize adopted constraints in the task plan or ADR so they remain durable after compaction.

## Completion rule

Every skill ends in an output contract. Treat that contract as required unless the user explicitly narrows it. A task is not complete until the evidence is tied to the exact acceptance criterion and artifact.
