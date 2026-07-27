# Controlled field learning

Controlled field learning exposes a product to representative real work at the lowest autonomy and blast radius capable of answering a product decision. It converts authentic use into governed evidence rather than anecdote or uncontrolled risk.

## Vocabulary
- **authentic use:** Work performed by intended users, roles, or operators under representative incentives, constraints, data, tools, and consequences.
- **learning decision:** The specific product or system choice that the exposure must inform.
- **field-learning unit:** A traceable task/run plus context, outcome, trajectory, effects, human work, and versions.
- **blast-radius budget:** Predeclared maximum exposure across users, value, effects, data, duration, errors, or cost.
- **kill criterion:** Observable condition that pauses or stops exposure without waiting for aggregate analysis.

## Decision procedure
1. Name the decision and uncertainty that simulation, replay, benchmarks, or anecdotes cannot resolve credibly.
2. Define intended population and representative task distribution; identify excluded/high-risk conditions.
3. Write operating envelope, autonomy level, cohort/comparator, blast-radius budget, approval, rollback, and kill criteria.
4. Instrument field-learning units and verify data quality before interpreting outcomes.
5. Review failures, near misses, interventions, abandonment, and representative successes; form mechanism hypotheses.
6. Translate material evidence into durable changes and decide ramp, hold, narrow, revert, redesign, or retire.

## Decision table

| Learning question | Minimum useful exposure | Typical decision |
|---|---|---|
| Can the agent generate viable actions? | Shadow/silent | Improve model/context/tooling before user exposure |
| Can humans use and trust recommendations? | Recommendation-only | Redesign workflow, explanation or review burden |
| Can effects execute safely? | Approval-gated | Strengthen preview, idempotency, reconciliation or permissions |
| Does bounded autonomy improve outcomes? | Controlled autonomous cohort | Ramp, narrow, hold, or revert |

## Evidence obligations
- Preflight offline and safety checks pass before representative exposure.
- The envelope and exposure level are encoded in controls where feasible, not only prose.
- Trace sampling includes apparent successes and non-completers, not just incidents.
- Every ramp step has a decision date, owner, comparator, validity check, rollback, and stop rule.

## Review questions
1. What product decision will this field exposure change?
2. How representative is the work, and who is missing?
3. Could we answer the question at a lower autonomy level?
4. What severe event stops the exposure immediately?
5. How will an observation become a test, tool, requirement, UX, policy, or architecture change?

## Failure patterns
- Production as research: uncontrolled exposure with no learning contract.
- Pilot theater: friendly users and curated tasks presented as representative evidence.
- Telemetry graveyard: collection without decision ownership or change closure.

## Research basis

Operationalizes agent-improvement loops, silent/shadow trials, deployed-AI monitoring, autonomy practice, and progressive release [R71] [R73] [R75] [R77] [R78] [R107].
