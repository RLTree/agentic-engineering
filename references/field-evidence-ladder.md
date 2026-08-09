# Field-evidence ladder

Use the ladder to match an evidence claim to the closest feasible observation of real work. Do not treat all evidence as interchangeable.

## Levels

| Level | Evidence | Useful for | Cannot establish alone |
|---|---|---|---|
| 0 | intuition, anecdote, demo, model self-report | hypothesis generation | prevalence, reliability, value, safety or causality |
| 1 | synthetic tasks and unit fixtures | deterministic correctness, regression, edge cases | representative workflow fit |
| 2 | recorded/replayed work | reproducibility and historical coverage | adaptation to live context or changed behavior |
| 3 | expert simulation or red-team exercises | rare/high-risk scenarios and adversarial discovery | ordinary user behavior or real incentives |
| 4 | observe-only workflow study | real task distribution, constraints, human work and baseline | agent impact |
| 5 | shadow/silent execution | trajectory, feasibility, latency, candidate actions without user-visible effect | human adoption, changed behavior or actual value |
| 6 | recommendation-only or approval-gated use | trust calibration, edits, interventions, workflow fit, bounded outcomes | unattended autonomy |
| 7 | bounded autonomous exposure | effect safety, recovery and value inside an envelope | broad generalization outside the envelope |
| 8 | randomized or strong quasi-experimental field evidence | causal effect on declared outcomes and guardrails | every long-term or rare effect |
| 9 | longitudinal operation across representative segments | durability, drift, adaptation, maintenance burden and long-term effects | future conditions or retired dependencies |

## Triangulation set

A consequential product decision should normally combine:

- outcome evidence: was the user/system result achieved?
- trajectory evidence: how did the agent and tools get there?
- effect evidence: what external changes occurred, with what ambiguity or recovery?
- human-work evidence: review, editing, intervention, escalation, abandonment and hidden labor;
- qualitative evidence: interviews, contextual inquiry, support/incident narratives and success deconstruction;
- quantitative evidence: segmented rates, distributions, reliability, cost, latency and data quality;
- comparison evidence: baseline, holdout, randomized assignment, staggered rollout or justified quasi-experiment;
- negative evidence: failures, near misses, excluded conditions, non-users and harmed cohorts.

## Representative sampling

Define the workload population before collecting convenient traces. Sample across task type, risk, novelty, frequency, user expertise, data sensitivity, tool/effect type, environment, time pressure, accessibility, language/locale, and known difficult segments. Over-sample rare severe conditions for safety analysis, but do not use that sample to estimate ordinary prevalence without weighting.

## Evidence-strength questions

1. Does the evidence observe the actual claim or a proxy?
2. Does the workload match the intended operating envelope?
3. Are missing events, selection, survivorship, intervention, and instrumentation effects understood?
4. Is the result segmented enough to expose heterogeneous harm or benefit?
5. Is the claim observational or causal?
6. What evidence would reverse the decision?
7. When does this evidence expire?

## Research basis

This ladder integrates agent outcome/trajectory evaluation, monitoring questions,
controlled field trials, human-AI workflow study, and experimentation validity.
NIST AI 800-4 is descriptive rather than a prescribed field-evidence method
(`F-NIST-AI800-4`). Historical lineage: [R72] [R74] [R75] [R77] [R78] [R79]
[R80].
