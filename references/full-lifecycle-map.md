# Full-lifecycle map for agent-mediated products

Use this map as a set of concurrent decision systems, not as a one-way waterfall. A product may be operating while discovery revisits a weak assumption, architecture work removes an operational risk, and retirement work closes an obsolete path.

## The ten lifecycle decision systems

| System | Primary question | Minimum durable evidence | Typical exit or revisit trigger |
|---|---|---|---|
| Discover | Is there a consequential, recurring problem worth solving for identifiable people in a real workflow? | representative observations, workflow map, affected stakeholders, current alternatives, problem evidence | problem disproven, segment changes, outcome no longer valuable |
| Validate | Can a proposed intervention create value, fit the workflow, and be built/operated safely enough to justify investment? | assumption map, prototypes/spikes, feasibility findings, stop/pivot thresholds | critical assumption fails; evidence justifies next thin slice |
| Specify | What must the sociotechnical system do, under which conditions, and how will it be verified and validated? | operational concept, mission threads, quality-attribute scenarios, requirements and traceability | field learning or architecture invalidates a baseline |
| Architect and plan | Which structure and delivery sequence best manages the highest risks and irreversible commitments? | tradeoff record, thin-slice plan, dependency/capacity model, ADRs | new evidence changes a quality-attribute priority or constraint |
| Construct and verify | Can small, reviewable changes produce the claimed behavior with reproducible evidence? | source, tests, review, build artifacts, acceptance evidence, provenance | verification fails, defect pattern recurs, change grows beyond safe batch |
| Secure and release | Is the change safe to expose, attributable, reversible, and authorized? | threat model, supply-chain evidence, release manifest, ramp/rollback plan | guardrail breach, provenance gap, unauthorized effect, rollback failure |
| Operate and assure | Is the service reliable, supportable, observable, and within its operating envelope? | production-readiness review, SLOs, runbooks, capacity and dependency evidence | error budget breach, incident, saturation, unsupported operating condition |
| Experiment and learn | Did the change cause the intended outcome without unacceptable harm, burden, or data-quality failure? | experiment/decision contract, trace and qualitative evidence, causal analysis where feasible | invalid experiment, guardrail breach, heterogeneous harm, no decision value |
| Maintain and evolve | Does the capability still earn its complexity, risk, cost, and compatibility burden? | health/value review, debt and dependency plan, compatibility and migration evidence | declining value, security exposure, replacement, unsustainable support |
| Retire | Can the capability be removed while preserving user need, data rights, obligations, and reversibility? | consumer inventory, migration and communications, disable-observe-delete evidence | hidden dependency, unresolved data/contract obligation, failed fallback |

## Cross-lifecycle threads

Track these continuously rather than assigning them to one phase:

- user and stakeholder outcomes;
- safety, security, privacy, accessibility, compliance, and ethics;
- architecture and quality attributes;
- requirements and evidence traceability;
- agent/human decision rights;
- model, prompt, skill, tool, data, and harness versions;
- reliability, cost, latency, capacity, and operator effort;
- field observations, interventions, incidents, near misses, and representative successes;
- deprecation, migration, retention, and retirement obligations.

## Tailoring rule

For each stage ask: **what decision is at stake, how consequential is an error, what is uncertain, and what is the least expensive evidence that could change the decision?** Deepen work where consequence, novelty, irreversibility, or uncertainty is high. Combine stages for low-risk reversible changes, but never omit the underlying decision or evidence obligation.

## Agent-mediated operating rule

Agents may accelerate search, synthesis, trace maintenance, option generation, implementation, testing, evidence assembly, anomaly detection, and routine reversible operations. Named humans retain product value judgments, stakeholder tradeoffs, policy interpretation, risk acceptance, and approval of irreversible or high-impact changes. Automation does not erase accountability.

## Research basis

The map synthesizes lifecycle-process standards, requirements and systems
engineering, agile service development, secure-development frameworks, SRE,
agent evaluation, and monitoring questions. NIST AI 800-4 is descriptive rather
than a prescribed lifecycle method (`F-NIST-AI800-4`). Historical lineage:
[R75] [R83] [R84] [R85] [R90] [R91] [R95] [R102] [R110].
