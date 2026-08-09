# Agent-mediated product operating model

Use agents to increase the rate and quality of evidence production, not to obscure ownership or replace judgment with fluent output.

## Decision-rights matrix

| Work | Agent may lead | Human must own or explicitly delegate |
|---|---|---|
| evidence search and synthesis | retrieve, classify, summarize, expose disagreement and gaps | define the decision, approve source policy, judge transfer to local context |
| discovery | cluster observations, map workflows, draft hypotheses and research instruments | choose participants, interpret values and harms, decide whether the problem is worth solving |
| specification | draft operational concepts, requirements, scenarios, trace links and tests | approve stakeholder tradeoffs, policy meaning, risk tolerances and acceptance criteria |
| architecture | generate alternatives, analyze scenarios, maintain ADRs and dependency graphs | accept irreversible tradeoffs, budget, organizational and regulatory commitments |
| construction | implement bounded changes, run checks, assemble evidence | approve destructive/high-impact changes and exceptions to controls |
| release and operations | prepare manifests, analyze telemetry, recommend ramps or rollbacks | authorize exposure, accept production risk, own incidents and customer commitments |
| experimentation | draft contracts, inspect validity, analyze heterogeneity, generate follow-up hypotheses | approve ethical exposure, metrics, stopping rules and causal claims |
| retirement | inventory consumers, draft migration and closure plans | decide service end, obligations, user continuity and irreversible deletion |

## Work-object model

Prefer durable, reviewable objects over conversational memory:

- decision record;
- evidence item with source, date, conditions, strength and expiry;
- operational concept and representative mission thread;
- requirement and quality-attribute scenario;
- architecture alternative and tradeoff;
- thin-slice or experiment contract;
- observation, intervention, incident or near-miss record;
- implementation and verification artifact;
- release, rollout, rollback and production-readiness evidence;
- maintenance, deprecation, migration and retirement record.

Each object should have stable identity, version, owner, status, links, and a machine-checkable subset where feasible.

## Agent working protocol

1. Restate the decision and bounded claim before producing artifacts.
2. Separate observed fact, source-derived claim, inference, assumption, proposal, and commitment.
3. Ask for or discover the strongest available evidence; do not fill gaps with confidence language.
4. Generate at least one materially different alternative for consequential choices.
5. Preserve traceability from stakeholder need to field outcome.
6. Run deterministic checks and independent review where feasible.
7. Surface uncertainty, counterevidence, operating-envelope limits, and expired evidence.
8. Stop for named human authority when a value judgment, policy interpretation, risk acceptance, or irreversible effect is required.
9. Convert corrections into durable repository guidance, tests, schemas, evals, tools, or constraints.

## Governance against automation bias

- Require explicit human rationale for accepting high-impact recommendations.
- Show evidence and counterevidence, not only a synthesized answer.
- Record overrides and interventions as learning signals, not user error by default.
- Avoid approval interfaces that make “accept” easier than inspection.
- Periodically sample apparent successes; low intervention may mean trust, disengagement, or invisible failure.
- Test the joint human-agent workflow, including escalation and recovery, rather than the model in isolation.

## Research basis

This operating model draws on agent autonomy/evaluation guidance, human-AI
interaction methods, lifecycle standards, and monitoring questions. NIST AI
800-4 is descriptive rather than a prescribed operating model
(`F-NIST-AI800-4`). Historical lineage: [R71] [R73] [R74] [R75] [R93] [R94].
