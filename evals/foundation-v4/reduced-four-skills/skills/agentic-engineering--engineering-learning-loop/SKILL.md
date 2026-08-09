---
name: engineering-learning-loop
description: "Explicit, proposal-only advice for turning a bounded engineering observation into a governed learning recommendation."
---

# Engineering Learning Loop

## Advisory scope

Produce a proposal only. This skill takes no effects, assigns no authority, adopts no policy, and makes no completion, efficacy, or product claim. Use recommendation, proposed owner, and proposed disposition language; leave execution and acceptance to the named authority.

## Decision procedure

1. Bind the observation to its candidate, task or population, environment, time, and evidence pointers. Separate facts from interpretations and mechanism hypotheses.
2. Define the operating envelope and evidence gaps. Do not generalize across users, repositories, models, tools, or consequence levels without supporting evidence.
3. Attribute the earliest controllable layer and preserve competing explanations. For each proposed mechanism, recommend a disconfirming probe, causal prediction, smallest repair operator, and displaced-failure check.
4. Recommend the smallest intervention that addresses the mechanism. Prefer a precise test, tool response, repository map, validator, or local rule over broad or universal prompt prose; `no_change` is a valid proposed disposition.
5. Propose an evaluation that distinguishes visible iteration from adoption evidence: baseline, held-out cases, negative controls, and, when consequential, semantic mutations and specification evolution. Evaluate the mechanism and displaced failures rather than self-report or reviewer agreement.
6. Propose a governed disposition: `adopt`, `hold`, `narrow`, `reject`, `supersede`, or `retire`, with a proposed owner, review date, expiry or invalidation trigger, rollback path, and residual risk.
7. Keep lifecycle explicit: propose how the recommendation relates to current guidance and how stale or contradicted guidance would cease to be default context.

## Proposal shape

- Bound observation, provenance, operating envelope, and evidence class.
- Facts, interpretations, competing mechanisms, and counterevidence.
- Recommended smallest intervention and rejected alternatives.
- Proposed baseline, held-out, negative-control, mutation, and evolution evaluation.
- Proposed disposition, owner, lifecycle, rollback, residual risk, and structural-evidence-only claim ceiling.

## Triggered frozen-source references

Read no reference by default. The parent selects any payload; do not load templates, schemas, or canonical libraries.

- `plugins/agentic-engineering/skills/engineering-learning-loop/references/failure-attribution-and-mechanism-hypotheses.md` — trigger: locating an earliest controllable cause or testing competing mechanisms.
- `plugins/agentic-engineering/skills/engineering-learning-loop/references/hidden-evals-mutation-spec-evolution.md` — trigger: designing held-out, negative-control, mutation, or evolution evaluation.
- `plugins/agentic-engineering/skills/engineering-learning-loop/references/knowledge-freshness-supersession.md` — trigger: proposing review, supersession, retirement, or deletion semantics.
