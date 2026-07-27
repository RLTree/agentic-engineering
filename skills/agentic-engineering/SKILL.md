---
name: agentic-engineering
description: Use when an AI or agent product needs architecture, lifecycle, assurance,
  field-learning, or Rust engineering decisions.
---

# Agentic Engineering

## Core principle

Choose the smallest architecture that satisfies the evidence, recovery, safety and operational requirements. Place each consequential decision in the specification, context, harness, loop, graph, runtime, repository or human boundary that can enforce it.

## Workflow

### 1. Frame the decision

Record the outcome, actors, environment, stakes, latency, scale, side effects, failure tolerance, human role and exact deliverable. Separate observed facts, assumptions, hypotheses and product decisions.

### 2. Map the seven layers

Inspect intent/specification, context, harness, loop, graph, system and agent-first software delivery. Name the layer responsible for every invariant and every recurring correction. Read [the seven-layer diagnostic](references/seven-layer-diagnostic.md) when symptoms are ambiguous.

### 3. Escalate architecture deliberately

Evaluate direct call → deterministic workflow → bounded loop → explicit graph → durable workflow → multi-agent. Move upward only for a named requirement the simpler topology cannot satisfy. Use [the architecture decision table](references/architecture-decision-table.md).

### 4. Separate judgment from control

Assign semantic interpretation, planning under ambiguity and generation to the model. Assign schemas, permissions, budgets, routing, validation, idempotency, irreversible effects and stop conditions to deterministic code whenever possible.

### 5. Write the control architecture

Define authoritative state, transitions, tools, effect boundary, verification oracle, budgets, checkpoints, approval gates, recovery and trace. Route to companion skills only for decisions that remain consequential.

### 6. Route product and lifecycle decisions

When the request spans product discovery, feasibility, requirements, architecture planning, construction quality, secure release, production readiness, experimentation, maintenance, retirement, or controlled authentic use, route those decisions to `$agentic-product-lifecycle` or the smallest relevant focused lifecycle skill. Do not force product-evidence questions into topology language.

### 7. Produce a falsifiable recommendation

State why the chosen topology is the smallest sufficient one, which alternatives were rejected, what obligations the choice introduces and which evaluation could prove it wrong.

## Output contract

Return an **Agentic Architecture Brief** with:

1. system outcome, actors, stakes and constraints;
2. seven-layer ownership map;
3. topology recommendation and rejected alternatives;
4. authoritative state and decision/effect boundaries;
5. loop or graph contract when applicable;
6. durability, human approval and security requirements;
7. verification/evaluation plan;
8. assumptions, open questions and revisit triggers.

## Common failures

- **Agentic by adjective:** adding tools or loops without a requirement. De-escalate to the smallest fitting form.
- **Prompt-only repair:** treating missing state, tests, permissions or recovery as wording problems. Move the decision to its enforceable layer.
- **Hidden control flow:** burying branches and retries inside prose. Externalize them when they affect correctness or recovery.
- **Deterministic work delegated to the model:** use code for validation, routing, aggregation and policy.
- **Architecture without an oracle:** no observable criterion can show success or regression. Define evidence before implementation.
- **Permanent complexity:** no revisit condition or decommission path. Record what evidence would simplify or replace the architecture.

## References

- [Seven-layer diagnostic](references/seven-layer-diagnostic.md)
- [Architecture decision table](references/architecture-decision-table.md)
- [Control architecture review](references/control-architecture-review.md)

## Shared references

- [Seven-layer map](../../references/seven-layer-map.md)
- [Architecture escalation](../../references/architecture-escalation.md)
- [GPT-5.6 Sol operating profile](../../references/gpt-5.6-sol-operating-profile.md)
- [Evidence and confidence](../../references/evidence-and-confidence.md)
- [Full lifecycle map](../../references/full-lifecycle-map.md)
- [Controlled field-learning system](../../references/controlled-field-learning-system.md)
- [Field-learning and full-lifecycle vocabulary](../../references/field-lifecycle-vocabulary.md)

## Version 3 cross-cutting gates

Before recommending implementation:

1. test whether the requested change is already satisfied and permit a typed no-change decision;
2. select a proportional assurance profile and Verification Mode Contract;
3. choose model, reasoning, Pro, Programmatic Tool Calling, or Ultra by measured task shape—not prestige;
4. require a repair budget and semantic circuit breaker for adaptive loops;
5. route observed outcomes through `engineering-learning-loop` before turning them into durable rules;
6. use `product-fitness-engineering` when a claim concerns real user value or continuance.

Read `../../references/no-change-and-abstention.md`, `../../references/proportional-assurance.md`, and `../../references/gpt-5.6-execution-selection.md` when these gates apply.
