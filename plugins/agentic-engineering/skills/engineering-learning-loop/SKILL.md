---
name: engineering-learning-loop
description: "Use when observed agent or product outcomes should become governed changes to evals, tools, rules, prompts, or architecture."
---

# Engineering Learning Loop

## Core principle

Observed outcomes become durable engineering controls only after provenance, mechanism, counterevidence, held-out evaluation, ownership, and lifecycle are explicit. A justified no-change decision is preferable to an untested rule.

## Outcome

Produce one **Learning Adoption Record** that turns a grounded observation into the smallest governed improvement—or records why no durable change is justified.

This skill is advisory. It does not promote product claims, mutate an external policy authority, or turn an anecdote directly into a universal rule.

## Use it for

- recurring failures, near misses, interventions, recoveries, workarounds, or unexpectedly strong outcomes;
- a suspected harness, context, tool, verification, architecture, product, or lifecycle gap;
- deciding whether a correction belongs in a prompt, repository guide, skill, tool, validator, eval, policy, or architecture;
- refreshing, superseding, narrowing, or retiring an existing learning.

Do not use it merely to summarize a session, preserve raw telemetry, or document a one-off solution with no decision consequence.

## Workflow

1. **Bind the observation.** Record exact run, candidate, task, user/work population, environment, time, and evidence pointers. Separate direct facts from interpretation and hypothesis.
2. **Scope the operating envelope.** State where the observation applies and where evidence is absent. Do not generalize across users, repositories, models, tools, or consequence levels without support.
3. **Attribute the responsible layer.** Locate the earliest controllable cause across specification, context, tool, harness, loop, graph, runtime, repository, product, lifecycle, or human decision boundary. Preserve competing explanations.
4. **Test recurrence and contradiction.** Search for similar and counterexample trajectories. Classify the evidence as isolated, recurring, cross-context, causal, or unresolved.
5. **Choose the smallest intervention.** Prefer a precise test, tool response, repository map, or validator over broad prompt prose. Prefer a local rule over a universal one. A no-change decision is valid.
6. **Design anti-gaming evidence.** Establish a baseline, visible cases, held-out cases, negative controls, and—when the rule is consequential—semantic mutation or specification-evolution cases.
7. **Evaluate the mechanism.** Measure activation, following, composition, recovery, verified outcome, safety, authority compliance, and efficiency. Check for displaced failures and intervention burden.
8. **Decide and govern.** Return `adopt`, `hold`, `narrow`, `reject`, `supersede`, or `retire`; name the owner, review date, expiry or invalidation trigger, and rollback path.

## Output contract

Include:

- observation and provenance;
- operating envelope and evidence class;
- facts, interpretations, hypotheses, and counterevidence;
- responsible layer and mechanism hypothesis;
- recurrence, severity, user consequence, and intervention burden;
- existing rule/tool/eval overlap;
- proposed smallest intervention and rejected alternatives;
- baseline, held-out, negative, mutation, and evolution evaluation plan;
- before/after results or an explicit unexecuted-evidence state;
- decision, owner, review date, expiry, invalidation, rollback, and residual risk;
- authority handoff describing who may adopt the change.

## Hard rules

- One learning per record.
- Evidence of correlation is not evidence of the proposed mechanism.
- Reviewer agreement and model self-report are not adoption proof.
- Never create a second source of authority when an existing registry can own the decision.
- A learning without freshness, supersession, and deletion semantics becomes context debt.

## Common failures

- Turning one vivid success or failure into a universal rule.
- Recording telemetry or a retrospective without an adoption decision.
- Changing prompt prose when a tool, validator, repository map, or typed contract can enforce the behavior.
- Keeping stale and superseded learnings discoverable as if they were current.


## References

Read on demand:

- `references/learning-adoption-record.md`
- `references/failure-attribution-and-mechanism-hypotheses.md`
- `references/hidden-evals-mutation-spec-evolution.md`
- `references/knowledge-freshness-supersession.md`
- the canonical repository reference library (no-change-and-abstention.md)
- the canonical repository reference library (task-evidence-and-review-contracts.md)

Use the canonical repository template or schema library (templates/learning-adoption-record.md) and the canonical repository template or schema library (schemas/learning-adoption-record.schema.json) for durable output.
