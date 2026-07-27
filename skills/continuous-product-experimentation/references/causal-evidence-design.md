# Causal evidence design

Choose a design that can distinguish intervention effect from selection, time, learning, concurrent changes and interference. Observational telemetry is excellent for diagnosis but should not be presented as causality without defensible assumptions.

## Vocabulary
- **counterfactual:** Outcome that would have occurred for the same unit without the intervention.
- **intention-to-treat:** Effect of assignment regardless of actual exposure, preserving randomization.
- **interference:** One unit’s treatment changes another unit’s outcome.
- **carryover:** Prior treatment continues to influence later periods.
- **quasi-experiment:** Non-random design using a defensible assignment mechanism and explicit identification assumptions.

## Decision procedure
1. Write estimand, population, treatment, comparator, horizon and expected interference/carryover.
2. Prefer individual/cluster randomization when ethical and operationally feasible; select switchback, cluster or time designs for shared systems.
3. When randomization is unavailable, identify assignment mechanism and test assumptions for discontinuity, difference-in-differences, synthetic control or staggered adoption.
4. Plan exposure compliance, attrition, contamination, spillovers, novelty/learning, seasonality and concurrent changes.
5. Predeclare analysis and robustness/sensitivity checks; preserve assignment and version provenance.
6. Triangulate estimated effect with trajectories, qualitative evidence and mechanisms; limit claims to exercised conditions.

## Decision table

| Context | Design | Critical assumption |
|---|---|---|
| Independent users | user/account RCT | limited interference |
| Shared queue/capacity | cluster or switchback | period balance/carryover |
| Mandatory staged rollout | stepped wedge/holdout | time trends modeled |
| Threshold eligibility | regression discontinuity | no manipulation near cutoff |
| No randomization | DiD/synthetic control | parallel trend/comparable donor |

## Evidence obligations
- Randomization unit aligns with how treatment and interference operate.
- Analysis distinguishes assignment, exposure, compliance and per-protocol effects.
- Longitudinal holdouts are considered for adaptation, novelty, model drift and maintenance effects.
- Causal language is proportional to design and assumption checks.

## Review questions
1. What plausible confounder produces the same observed improvement?
2. Can treated behavior affect controls through teams, shared queues or copied outputs?
3. How long do learning and novelty effects last?
4. What evidence tests the identification assumptions?

## Failure patterns
- Before/after causality: time trend attributed to product.
- Unit mismatch: tasks randomized while users learn across variants.
- Complex method as credibility: sophisticated model with untested assumptions.

## Research basis

Grounded in Microsoft experimentation guidance, long-term pitfalls, and post-deployment field evidence [R79] [R81] [R82].
