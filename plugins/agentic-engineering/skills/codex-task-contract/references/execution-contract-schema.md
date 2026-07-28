# Codex execution contract schema

A high-quality Codex request is a compact engineering contract. It reduces back-and-forth by making consequential decisions explicit while leaving reversible implementation choices to the agent.

## Required fields

```markdown
# Execution Contract

## Objective
Describe the user or system outcome.

## Situation and evidence
Repository/component, current behavior, relevant files, prior decisions, observed defects, and source provenance.

## Deliverables
Exact durable artifacts, locations, formats, and integration points.

## Constraints and invariants
Public interfaces, compatibility, dependencies, security, performance, style, data, and operational boundaries.

## Anti-goals
Plausible but unwanted expansions or interpretations.

## Execution model
Smallest fitting topology, phases, ownership, state, and effect boundary.

## Autonomy and approval policy
Reversible assumptions allowed; choices requiring escalation; prohibited operations.

## Verification contract
Acceptance criterion → command/test/trace/rendered behavior/human review.

## Handoff
Decisions, files changed, evidence, assumptions, residual risks, and follow-up work.
```

## Field quality tests

**Objective** passes when it names who benefits and what changes. “Refactor the service” is an activity; “reduce failed resumptions while preserving the API” is an outcome.

**Situation** passes when claims are labeled observed, assumed, or hypothesized. Include only context likely to affect a decision.

**Deliverables** pass when an independent reviewer can enumerate what must exist. Specify exact-delivery artifacts such as a compiled binary, packaged plugin, migration, screenshots, or report.

**Constraints** pass when each invariant has an owner or check. Avoid adjective-only constraints such as “robust” unless translated into timeouts, recovery behavior, budgets, tests, or SLOs.

**Anti-goals** pass when they exclude likely failure modes: broad rewrite, framework migration, new dependency, silent API change, chat-only output, mock-only verification, or hidden scope expansion.

**Execution model** passes when complexity is justified by a requirement. Do not prescribe a graph or multiple agents without a reason.

**Autonomy policy** passes when Codex can proceed through reversible ambiguity but pauses before product-defining, privileged, externally visible, expensive, destructive, or hard-to-reverse choices.

**Verification** passes when “done” can be falsified. Every important criterion needs an evidence source and exact target.

## Compression rule

When the contract becomes long, keep decisions and remove narrative. Move stable repository guidance to AGENTS.md, repeatable workflow to a skill, deterministic checks to scripts/tests, and research detail to references. The task contract should contain what is specific to this run.

## Completion language

Require Codex to distinguish observed fact, assumption, hypothesis, decision, and residual risk. A completion statement should pair each major claim with the evidence that supports it and identify any criterion that could not be executed.
