# Lifecycle Decision-Continuity Review

## Purpose

Test whether the expanded plugin improves decision quality and evidence continuity across the full product lifecycle rather than producing isolated, polished documents.

## Case construction

Select at least eight product cases spanning:

- new agent product discovery;
- uncertain concept/feasibility;
- requirements and quality-attribute conflict;
- architecture and delivery tradeoff;
- construction defect or quality escape;
- secure release and progressive exposure;
- production incident or SLO breach;
- product experiment with ambiguous result;
- model/tool/dependency change;
- deprecation or retirement.

At least three cases should be Rust agent applications. Include incomplete and contradictory evidence rather than only clean textbook cases.

## Arms

### Baseline

Use a normal comprehensive product-development prompt without plugin skills, templates, references, or vocabulary.

### Plugin

Start with `$agentic-product-lifecycle`, then compose only the focused stage skills required by the case. Use fresh sessions and the same evidence package.

## Required lifecycle chain

Review whether outputs preserve semantic links across:

```text
stakeholder/work evidence
↔ opportunity and assumptions
↔ concept/feasibility evidence
↔ operational concept and mission threads
↔ requirements and quality scenarios
↔ architecture decisions and risk-retiring slices
↔ implementation and verification
↔ secure release and exact artifact
↔ production readiness/SLO/incident controls
↔ authentic-use observations and experiments
↔ maintenance/deprecation/retirement decisions
```

## Review dimensions

Score 1–5 with citations to the artifact:

1. **Decision framing:** current decision and alternatives are explicit.
2. **Epistemic discipline:** facts, inferences, assumptions, recommendations, and unknowns are separated.
3. **Representative evidence:** user/work and field evidence are not replaced by invented personas or benchmark proxies.
4. **Decision rights:** human, agent, service, operator, and governance authority are named.
5. **Traceability:** needs, requirements, architecture, implementation, verification, operations, and field evidence are linked.
6. **Quality attributes:** measurable scenarios drive architecture and verification.
7. **Risk retirement:** thin slices target high-consequence uncertainty rather than feature volume.
8. **Secure delivery:** threat, provenance, exact artifact, authorization, rollout, and rollback are connected.
9. **Production readiness:** ownership, SLO, capacity, observability, recovery, incident, and support evidence are complete.
10. **Experiment validity:** assignment/exposure, metric contracts, guardrails, data quality, causal limits, and decisions are predeclared.
11. **Maintenance and retirement:** material changes, revalidation, migration, effect reconciliation, data, credentials, and closure are addressed.
12. **Feedback:** field failures can revise discovery, requirements, architecture, tools, evals, and policy.
13. **Tailoring:** lifecycle depth matches risk instead of becoming a mandatory waterfall.
14. **Actionability:** owners, next slice, evidence, stop/revisit triggers, and durable artifacts are usable.
15. **Complexity discipline:** the output avoids unnecessary agents, stages, artifacts, or gates.

## Defects that cap a case score

A case cannot score above 2 when it:

- invents stakeholder or field evidence;
- accepts risk without a named human owner;
- claims causal product impact from unstructured observation;
- treats shadow evidence as proof of autonomous effect safety;
- omits rollback/reconciliation for consequential release;
- substitutes functional verification for intended-use validation;
- leaves a material model/tool/permission change outside configuration control;
- proposes retirement by deletion without migration, revocation, data, effect, and dependency handling.

## Continuity test

Give a fresh reviewer only the produced artifacts, not the chat transcript. Ask the reviewer to identify:

- current product/lifecycle posture;
- last consequential decision and evidence;
- active operating envelope;
- highest unresolved risk;
- next smallest evidence-generating slice;
- blocking readiness criteria;
- owner and revisit/stop trigger.

Record accuracy and time. This tests whether the artifact—not the conversation—is the unit of continuity.

## Positive-transfer rule

The plugin supports release when it improves median blind review score and continuity accuracy without unacceptable increases in artifact burden. Report per-dimension deltas, critical defects, reviewer agreement, time/cost, and cases where the baseline was better.
