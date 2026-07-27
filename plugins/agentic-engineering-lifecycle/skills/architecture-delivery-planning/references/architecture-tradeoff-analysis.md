# Architecture tradeoff analysis

Architecture is a set of consequential structural decisions made under quality-attribute tradeoffs. Analyze scenarios, risks, sensitivity points and alternatives before the cost of change makes assumptions invisible.

## Vocabulary
- **architectural driver:** High-priority requirement, constraint, risk or quality scenario shaping structure.
- **sensitivity point:** Decision where a small change has a large effect on a quality attribute.
- **tradeoff point:** Decision that improves one quality attribute while weakening another.
- **risk theme:** Recurring uncertainty across scenarios or components.
- **architectural tactic:** Design mechanism selected to achieve a quality response, such as isolation, queueing, redundancy, least privilege or checkpointing.

## Decision procedure
1. Collect business/mission drivers, operating envelope, lifecycle horizon, constraints and prioritized quality-attribute scenarios.
2. Describe candidate architectures and explicit assumptions, including model/tool/provider boundaries and human decision rights.
3. Walk scenarios through components, state, effects, failure/recovery, operations, security and evolution.
4. Identify sensitivity/tradeoff points, risks, non-risks and risk themes; compare at least one materially different alternative.
5. Choose reversible experiments or spikes for uncertain drivers; record ADRs and evidence.
6. Define architecture fitness evidence and field signals that trigger revisit.

## Decision table

| Driver | Potential tactic | Tradeoff to inspect |
|---|---|---|
| Effect safety | typed actions, approval, journal, reconciliation | latency and workflow burden |
| Reliability | supervision, bounded queues, checkpoints | complexity and cost |
| Adaptability | ports/adapters, versioned schemas | abstraction overhead |
| Low latency | parallelism, caching, smaller model | cost, consistency and quality |
| Auditability | durable trace/evidence | privacy, storage and cardinality |

## Evidence obligations
- Architecture claims are tied to measurable scenarios and operating conditions.
- Alternatives are structurally different, not cosmetic variants.
- The analysis includes deployment, operations, migration and retirement—not only code decomposition.
- Field evidence can update drivers and trigger a new review.

## Review questions
1. Which decision is hardest or most expensive to reverse?
2. What quality attribute loses when this one improves?
3. Which assumption lacks executable or field evidence?
4. Does an agent loop/graph/multi-agent topology earn its coordination cost?

## Failure patterns
- Diagram approval: boxes accepted without scenario walk-through.
- One-option analysis: rationale written after commitment.
- Quality attribute hand-waving: no response measure or tradeoff.

## Research basis

Grounded in SEI QAW/ATAM, lifecycle architecture practice, and agent control-plane engineering [R88] [R89].
